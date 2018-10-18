from cilantro.protocol.overlay.kademlia.network import Network
from cilantro.protocol.overlay.auth import Auth
from cilantro.protocol.overlay.discovery import Discovery
from cilantro.protocol.overlay.handshake import Handshake
from cilantro.protocol.overlay.event import Event
from cilantro.protocol.overlay.ip import *
from cilantro.protocol.overlay.kademlia.utils import digest
from cilantro.protocol.overlay.ip import get_public_ip
from cilantro.constants.overlay_network import *
from cilantro.logger.base import get_logger
from cilantro.storage.db import VKBook
from cilantro.protocol.overlay.kademlia.node import Node

import asyncio, os, zmq.asyncio, zmq
from os import getenv as env
from enum import Enum, auto

import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class OverlayInterface:
    started = False
    log = get_logger('OverlayInterface')

    def __init__(self, sk_hex, loop=None, ctx=None):
        self.loop = loop or asyncio.get_event_loop()
        self.ctx = ctx or zmq.asyncio.Context()
        Auth.setup(sk_hex=sk_hex, reset_auth_folder=True)

        self.network = Network(loop=self.loop, storage=None)
        Discovery.setup(ctx=self.ctx)
        Handshake.setup(loop=self.loop, ctx=self.ctx)
        self.tasks = [
            Discovery.listen(),
            Handshake.listen(),
            self.network.listen(),
            self.bootup()
        ]

    def start(self):
        self.loop.run_until_complete(asyncio.gather(
            *self.tasks
        ))

    @property
    def neighbors(self):
        return {item[2]: Node(node_id=digest(item[2]), ip=item[0], port=item[1], vk=item[2]) \
            for item in self.network.bootstrappableNeighbors()}

    @property
    def authorized_nodes(self):
        return Handshake.authorized_nodes

    async def bootup(self):
        await self.discover()
        self.log.success('''
###########################################################################
#   DISCOVERY COMPLETE
###########################################################################\
        ''')
        Event.emit({ 'event': 'discovery', 'status': 'complete' })
        await self.bootstrap()
        self.log.success('''
###########################################################################
#   BOOTSTRAP COMPLETE
###########################################################################\
        ''')
        Event.emit({ 'event': 'service_status', 'status': 'ready' })
        self.started = True

    async def discover(self):
        if await Discovery.discover_nodes(Discovery.host_ip):
            return
        else:
            self.log.critical('''
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
x   DISCOVERY FAILED: Cannot find enough nodes ({}/{}) and not a masternode
x       Retrying...
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            '''.format(len(Discovery.discovered_nodes), MIN_BOOTSTRAP_NODES))

    async def bootstrap(self):
        addrs = [(Discovery.discovered_nodes[vk], self.network.port) \
            for vk in Discovery.discovered_nodes]
        await self.network.bootstrap(addrs)
        self.network.cached_vks.update(self.neighbors)

    async def authenticate(self, ip, vk, domain='*'):
        return await Handshake.initiate_handshake(ip, vk, domain)

    async def lookup_ip(self, vk):
        return await self.network.lookup_ip(vk)

    def teardown(self):
        self.log.important('Shutting Down.')
        for task in self.tasks:
            task.cancel()
        self.started = False
