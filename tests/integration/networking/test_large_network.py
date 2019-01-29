from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('2-2-2.json')
from cilantro.constants.testnet import *
from cilantro.constants.test_suites import CI_FACTOR
from cilantro.messages.signals.poke import Poke

from cilantro.utils.test.mp_test_case import MPTestCase, vmnet_test, CILANTRO_PATH
from cilantro.utils.test.mp_testables import MPRouterAuth
from cilantro.utils.test.mp_testables import MPPubSubAuth
from cilantro.storage.vkbook import VKBook
import unittest, time


def config_sub(test_obj):
    from unittest.mock import MagicMock
    test_obj.handle_sub = MagicMock()
    return test_obj


def config_node(test_obj):
    from unittest.mock import MagicMock
    test_obj.handle_router_msg = MagicMock()
    return test_obj


class TestLargeNetwork(MPTestCase):
    config_file = '{}/cilantro/vmnet_configs/cilantro-nodes-6.json'.format(CILANTRO_PATH)
    # log_lvl = 19

    def config_router(self, node: MPRouterAuth, vk_list: list):
        self.log.test("Configuring node named {}".format(node.name))
        node.create_router_socket(identity=node.ip.encode(), secure=False)  # TODO change this back to True
        if node.name == 'node_1':
            time.sleep(30)
        node.bind_router_socket(ip=node.ip)
        for vk in vk_list:
            if node.vk == vk: continue
            node.connect_router_socket(vk=vk)

    @vmnet_test
    def test_pubsub(self):
        def assert_sub(test_obj):
            c_args = test_obj.handle_sub.call_args_list
            assert len(c_args) == 4, "Expected 4 messages (one from each node). Instead, got:\n{}".format(c_args)

        BLOCK = False
        time.sleep(1*CI_FACTOR)

        mn_0 = MPPubSubAuth(sk=TESTNET_MASTERNODES[0]['sk'], name='[node_1]MN_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        mn_1 = MPPubSubAuth(sk=TESTNET_MASTERNODES[1]['sk'], name='[node_2]MN_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)

        wit_0 = MPPubSubAuth(sk=TESTNET_WITNESSES[0]['sk'], name='[node_3]WITNESS_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        wit_1 = MPPubSubAuth(sk=TESTNET_WITNESSES[1]['sk'], name='[node_4]WITNESS_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)

        del_0 = MPPubSubAuth(sk=TESTNET_DELEGATES[0]['sk'], name='[node_5]DELEGATE_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)

        time.sleep(12*CI_FACTOR)  # Nap while nodes hookup

        all_nodes = (mn_0, mn_1, wit_0, wit_1, del_0)
        # all_nodes = (mn_0, mn_1, wit_0, wit_1, del_0, del_1, del_2, del_3)
        all_vks = (TESTNET_MASTERNODES[0]['vk'], TESTNET_MASTERNODES[1]['vk'], TESTNET_WITNESSES[0]['vk'],
                   TESTNET_WITNESSES[1]['vk'], TESTNET_DELEGATES[0]['vk'], TESTNET_DELEGATES[1]['vk'],)

        # Each node PUBS on its own IP
        for n in all_nodes:
            n.add_pub_socket(ip=n.ip, secure=True)

        time.sleep(5*CI_FACTOR)  # Nap while nodes add their pub sockets

        # Each node SUBs to everyone else (except themselves)
        for i, n in enumerate(all_nodes):
            n.add_sub_socket(secure=True)

        nsz = len(all_nodes)
        it = 1
        while it < nsz:
            for i in range(nsz):
                j = i + it
                if j >= nsz:
                    break
                m = all_nodes[i]
                m_vk = all_vks[i]
                n = all_nodes[j]
                n_vk = all_vks[j]
                m.connect_sub(vk=n_vk)
                n.connect_sub(vk=m_vk)
            it = it + 1

        time.sleep(12*CI_FACTOR)  # Allow time for VK lookups

        # Make each node pub a msg
        for n in all_nodes:
            n.send_pub("hi from {} with ip {}".format(n.name, n.ip).encode())

        self.start(timeout=30)

        time.sleep(2*CI_FACTOR)  # Allow time to shut down properly

    @vmnet_test(run_webui=False)  # TODO turn of web UI
    def test_router(self):
        def assert_router(test_obj):
            return
            c_args = test_obj.handle_router_msg.call_args_list
            assert len(c_args) == 4, "Expected 4 messages (one from each node). Instead, got:\n{}".format(c_args)

        BLOCK = False

        node1 = MPRouterAuth(sk=TESTNET_MASTERNODES[0]['sk'], name='node_1', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        node2 = MPRouterAuth(sk=TESTNET_MASTERNODES[1]['sk'], name='node_2', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        node3 = MPRouterAuth(sk=TESTNET_WITNESSES[0]['sk'], name='node_3', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        node4 = MPRouterAuth(sk=TESTNET_WITNESSES[1]['sk'], name='node_4', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        node5 = MPRouterAuth(sk=TESTNET_DELEGATES[0]['sk'], name='node_5', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)

        time.sleep(8*CI_FACTOR)  # Nap while nodes hookup

        all_vks = [TESTNET_MASTERNODES[0]['vk'], TESTNET_MASTERNODES[1]['vk'], TESTNET_WITNESSES[0]['vk'],
                   TESTNET_WITNESSES[1]['vk'], TESTNET_DELEGATES[0]['vk']]
        all_nodes = (node1, node2, node3, node4, node5)

        self.log.test("Configuring all nodes")
        for n in all_nodes:
            self.config_router(n, all_vks)

        # TODO try this without allowing time for VK lookups
        time.sleep(16*CI_FACTOR)  # Allow time for VK lookups

        # Everyone sends messages to everyone
        self.log.test("Sending messages from all nodes")
        for sender in (node1, node2, node3, node4, node5):
            for receiver in (node1, node2, node3, node4, node5):
                if sender == receiver: continue
                sender.send_msg(Poke.create(), receiver.ip.encode())

        self.start(timeout=20)


if __name__ == '__main__':
    # Hello CI, want to go for a run?
    unittest.main()
