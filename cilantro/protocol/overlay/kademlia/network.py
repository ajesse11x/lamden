"""
Package for interacting on the network at a high level.
"""
import random
import pickle
import asyncio
import logging
import time

from cilantro.constants.overlay_network import *
from cilantro.constants.ports import DHT_PORT
from cilantro.protocol.overlay.kademlia.protocol import KademliaProtocol
from cilantro.protocol.overlay.kademlia.utils import digest
from cilantro.protocol.overlay.kademlia.storage import ForgetfulStorage
from cilantro.protocol.overlay.kademlia.node import Node
from cilantro.protocol.overlay.kademlia.crawling import ValueSpiderCrawl
from cilantro.protocol.overlay.kademlia.crawling import NodeSpiderCrawl
from cilantro.protocol.overlay.kademlia.crawling import VKSpiderCrawl
from cilantro.protocol.overlay.auth import Auth

from cilantro.logger.base import get_logger
log = get_logger(__name__)

# TODO put this stuff in utils or something
from cilantro.storage.db import VKBook
VK_DIGEST_MAP = {digest(vk): vk for vk in VKBook.get_all()}
def add_vks(nodes):
    for n in nodes:
        # TODO instead of throwing an assert, we should handle this bad actor properly
        assert n.id in VK_DIGEST_MAP, "Node with id {} not found in VK_DIGEST_MAP {}".format(n.id, VK_DIGEST_MAP)
        n.vk = VK_DIGEST_MAP[n.id]
        # log.spam("looking up vk {} found a nearby node with vk {}".format(vk, n.vk))

def get_desired_node(vk, nodes):
    desired_node = list(filter(lambda n: n.vk == vk, nodes))
    node = desired_node[0] if desired_node else None
    return node


class Network(object):
    """
    High level view of a node instance.  This is the object that should be
    created to start listening as an active node on the network.
    """
    host_ip = HOST_IP
    port = DHT_PORT
    protocol_class = KademliaProtocol

    def __init__(self, ksize=20, alpha=3, loop=None, storage=None):
        """
        Create a server instance.  This will start listening on the given port.

        Args:
            ksize (int): The k parameter from the paper
            alpha (int): The alpha parameter from the paper
            vk: The vk for this node on the network.
            storage: An instance that implements
                     :interface:`~kademlia.storage.IStorage`
        """
        self.ksize = ksize
        self.alpha = alpha
        self.loop = loop or asyncio.get_event_loop()
        self.storage = storage or ForgetfulStorage()
        self.node = Node(node_id=digest(Auth.vk), ip=self.host_ip, port=self.port, vk=Auth.vk)
        self.transport = None
        self.protocol = None
        self.refresh_loop = None
        self.save_state_loop = None
        self.cached_vks = {}

    def stop(self):
        if self.transport is not None:
            self.transport.close()

        if self.refresh_loop:
            self.refresh_loop.cancel()

        if self.save_state_loop:
            self.save_state_loop.cancel()

    def _create_protocol(self):
        return self.protocol_class(self.node, self.storage, self.ksize)

    async def listen(self, interface='0.0.0.0'):
        """
        Start listening on the given port.

        Provide interface="::" to accept ipv6 address
        """
        loop = self.loop
        listen = loop.create_datagram_endpoint(self._create_protocol,
                                               local_addr=(interface, self.port))
        log.spam("Node %i listening on %s:%i",
                 self.node.long_id, interface, self.port)
        self.transport, self.protocol = await asyncio.ensure_future(listen)
        await self._refresh_table()

    async def _refresh_table(self):
        """
        Refresh buckets that haven't had any lookups in the last hour
        (per section 2.3 of the paper).
        """
        ds = []
        for node_id in self.protocol.getRefreshIDs():
            node = Node(node_id)
            nearest = self.protocol.router.findNeighbors(node, self.alpha)
            spider = NodeSpiderCrawl(self.protocol, node, nearest,
                                     self.ksize, self.alpha)
            ds.append(spider.find())

        # do our crawling
        await asyncio.gather(*ds)

        # now republish keys older than one hour
        for dkey, value in self.storage.iteritemsOlderThan(3600):
            await self.set_digest(dkey, value)

        await asyncio.sleep(3600)
        await self._refresh_table()

    def bootstrappableNeighbors(self):
        """
        Get a :class:`list` of (ip, port) :class:`tuple` pairs suitable for
        use as an argument to the bootstrap method.

        The server should have been bootstrapped
        already - this is just a utility for getting some neighbors and then
        storing them if this server is going down for a while.  When it comes
        back up, the list of nodes can be used to bootstrap.
        """
        neighbors = self.protocol.router.findNeighbors(self.node)
        return [tuple(n)[1:] for n in neighbors]

    async def bootstrap(self, addrs):
        """
        Bootstrap the server by connecting to other known nodes in the network.

        Args:
            addrs: A `list` of (ip, port) `tuple` pairs.  Note that only IP
                   addresses are acceptable - hostnames will cause an error.
        """
        log.spam("Attempting to bootstrap node with %i initial contacts",
                  len(addrs))
        cos = list(map(self.bootstrap_node, addrs))
        gathered = await asyncio.gather(*cos)
        nodes = [node for node in gathered if node is not None]
        spider = NodeSpiderCrawl(self.protocol, self.node, nodes,
                                 self.ksize, self.alpha)
        return await spider.find()

    async def bootstrap_node(self, addr):
        result = await self.protocol.ping(addr, self.node.id, self.node.vk)
        if result[0]:
            nodeid, vk = result[1]
            return Node(nodeid, addr[0], addr[1], vk)

    # TODO clean up this logic and make it more efficient
    async def lookup_ip(self, vk):
        log.spam('Attempting to look up node with vk="{}"'.format(vk))
        if Auth.vk == vk:
            return HOST_IP
        elif self.cached_vks.get(vk):
            node = self.cached_vks.get(vk)
            log.debug('"{}" found in cache resolving to {}'.format(vk, node))
            return node.ip
        else:
            desired_id = digest(vk)
            neighbors = self.protocol.router.findNeighbors(Node(desired_id))
            add_vks(neighbors)

            # First check if the ID is already in our neighbors
            # node = get_desired_node(vk, neighbors)
            # if node:
            #     log.important("VK {} already found in routing table".format(vk))
            #     return node.ip

            spider = NodeSpiderCrawl(self.protocol, self.node, neighbors,
                                     self.ksize, self.alpha)
            log.spam("Starting VK lookup with neighbors {}".format(neighbors))
            start = time.time()
            nearest = await spider.find()
            duration = round(time.time() - start, 2)
            log.spam("({}s elapsed) Looking up VK {} return nearest neighbors {}".format(duration, vk, nearest))

            # for n in nearest:
                # TODO instead of throwing an assert, we should handle this bad actor properly
                # assert n.id in VK_DIGEST_MAP, "Node with id {} not found in VK_DIGEST_MAP {}".format(n.id, VK_DIGEST_MAP)
                # n.vk = VK_DIGEST_MAP[n.id]
                # log.spam("looking up vk {} found a nearby node with vk {}".format(vk, n.vk))
            add_vks(nearest)

            log.important3("({}s elapsed) Looking up VK {} return nearest neighbors {}".format(duration, vk, nearest))  # TODO change log lvl
            node = get_desired_node(vk, nearest)
            # desired_node = list(filter(lambda n: n.vk == vk, nearest))
            # node = desired_node[0] if desired_node else None

            # END DEBUG
            if node:
                log.success('"{}" resolved to {}'.format(vk, node))
                return node.ip
            else:
                log.warning('"{}" cannot be resolved'.format(vk))
                return None
            # nearest = self.protocol.router.findNeighbors(Node(digest(vk)))
            # spider = VKSpiderCrawl(self.protocol, self.node, nearest,
            #                          self.ksize, self.alpha)
            # node = await spider.find(nodeid=digest(vk))
            # if node:
            #     log.debug('"{}" resolved to {}'.format(vk, node))
            #     return node.ip
            # else:
            #     log.warning('"{}" cannot be resolved'.format(vk))
            #     return None

    async def get(self, key):
        """
        Get a key if the network has it.

        Returns:
            :class:`None` if not found, the value otherwise.
        """
        log.spam("Looking up key %s", key)
        dkey = digest(key)
        # if this node has it, return it
        if self.storage.get(dkey) is not None:
            return self.storage.get(dkey)
        node = Node(dkey)
        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            log.warning("There are no known neighbors to get key %s", key)
            return None
        spider = ValueSpiderCrawl(self.protocol, node, nearest,
                                  self.ksize, self.alpha)
        return await spider.find()

    async def set(self, key, value):
        """
        Set the given string key to the given value in the network.
        """
        if not check_dht_value_type(value):
            raise TypeError(
                "Value must be of type int, float, bool, str, or bytes"
            )
        log.spam("setting '%s' = '%s' on network", key, value)
        dkey = digest(key)
        return await self.set_digest(dkey, value)

    async def set_digest(self, dkey, value):
        """
        Set the given SHA1 digest key (bytes) to the given value in the
        network.
        """
        node = Node(dkey)

        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            log.warning("There are no known neighbors to set key %s",
                        dkey.hex())
            return False

        spider = NodeSpiderCrawl(self.protocol, node, nearest,
                                 self.ksize, self.alpha)
        nodes = await spider.find()
        log.spam("setting '%s' on %s", dkey.hex(), list(map(str, nodes)))

        # if this node is close too, then store here as well
        biggest = max([n.distanceTo(node) for n in nodes])
        if self.node.distanceTo(node) < biggest:
            self.storage[dkey] = value
        ds = [self.protocol.callStore(n, dkey, value) for n in nodes]
        # return true only if at least one store call succeeded
        return any(await asyncio.gather(*ds))

    def saveState(self, fname):
        """
        Save the state of this node (the alpha/ksize/id/immediate neighbors)
        to a cache file with the given fname.
        """
        log.spam("Saving state to %s", fname)
        data = {
            'ksize': self.ksize,
            'alpha': self.alpha,
            'id': self.node.id,
            'neighbors': self.bootstrappableNeighbors()
        }
        if len(data['neighbors']) == 0:
            log.warning("No known neighbors, so not writing to cache.")
            return
        with open(fname, 'wb') as f:
            pickle.dump(data, f)

    @classmethod
    def loadState(self, fname):
        """
        Load the state of this node (the alpha/ksize/id/immediate neighbors)
        from a cache file with the given fname.
        """
        log.spam("Loading state from %s", fname)
        with open(fname, 'rb') as f:
            data = pickle.load(f)
        s = Network(data['ksize'], data['alpha'], data['id'])
        if len(data['neighbors']) > 0:
            s.bootstrap(data['neighbors'])
        return s

    def saveStateRegularly(self, fname, frequency=600):
        """
        Save the state of node with a given regularity to the given
        filename.

        Args:
            fname: File name to save retularly to
            frequency: Frequency in seconds that the state should be saved.
                        By default, 10 minutes.
        """
        self.saveState(fname)
        loop = asyncio.get_event_loop()
        self.save_state_loop = loop.call_later(frequency,
                                               self.saveStateRegularly,
                                               fname,
                                               frequency)


def check_dht_value_type(value):
    """
    Checks to see if the type of the value is a valid type for
    placing in the dht.
    """
    typeset = set(
        [
            int,
            float,
            bool,
            str,
            bytes,
        ]
    )
    return type(value) in typeset
