from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('2-2-2.json')
from cilantro.constants.testnet import *
from cilantro.constants.test_suites import CI_FACTOR

from cilantro.utils.test.mp_test_case import MPTestCase, vmnet_test, CILANTRO_PATH
from cilantro.utils.test.mp_testables import MPRouterAuth
from cilantro.messages.signals.poke import Poke
import unittest, time


PUB1_SK, PUB1_VK = TESTNET_MASTERNODES[0]['sk'], TESTNET_MASTERNODES[0]['vk']
PUB2_SK, PUB2_VK = TESTNET_MASTERNODES[1]['sk'], TESTNET_MASTERNODES[1]['vk']


def config_node(test_obj):
    from unittest.mock import MagicMock
    test_obj.handle_router_msg = MagicMock()
    return test_obj


class TestRouterSecure(MPTestCase):
    config_file = '{}/cilantro/vmnet_configs/cilantro-nodes-2.json'.format(CILANTRO_PATH)

    @vmnet_test
    def test_one_bind_other_connect(self):
        def assert_router(test_obj):
            test_obj.handle_router_msg.assert_called_once()

        BLOCK = False
        time.sleep(1*CI_FACTOR)

        router1 = MPRouterAuth(sk=PUB1_SK, name='ROUTER 1', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        router2 = MPRouterAuth(sk=PUB2_SK, name='ROUTER 2', block_until_rdy=True)

        time.sleep(5*CI_FACTOR)

        for r in (router1, router2):
            r.create_router_socket(identity=r.vk.encode(), secure=True)

        router1.bind_router_socket(ip=router1.ip)
        router2.connect_router_socket(vk=PUB1_VK)

        # Give time for VK lookup (technically this is not necessary)
        time.sleep(3*CI_FACTOR)

        router2.send_msg(Poke.create(), router1.vk.encode())

        self.start(timeout=10*CI_FACTOR)

    @vmnet_test(run_webui=False)  # TODO turn of web UI
    def test_both_bind(self):
        def assert_router(test_obj):
            test_obj.handle_router_msg.assert_called_once()

        BLOCK = False
        time.sleep(1*CI_FACTOR)

        router1 = MPRouterAuth(sk=PUB1_SK, name='ROUTER 1', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        router2 = MPRouterAuth(sk=PUB2_SK, name='ROUTER 2', config_fn=config_node, assert_fn=assert_router, block_until_rdy=True)

        time.sleep(5*CI_FACTOR)

        for r in (router1, router2):
            r.create_router_socket(identity=r.vk.encode(), secure=True, name='Router-{}'.format(r.ip))
            r.bind_router_socket(ip=r.ip)

        router1.connect_router_socket(vk=PUB2_VK)
        router2.connect_router_socket(vk=PUB1_VK)

        # Give time for VK lookup (technically this is not necessary)
        time.sleep(3*CI_FACTOR)

        router2.send_msg(Poke.create(), router1.vk.encode())
        router1.send_msg(Poke.create(), router2.vk.encode())

        self.start(timeout=10*CI_FACTOR)

    @vmnet_test(run_webui=False)  # TODO turn of web UI
    def test_both_bind_no_wait_after_vk_lookup(self):
        def assert_router(test_obj):
            test_obj.handle_router_msg.assert_called_once()

        BLOCK = False
        time.sleep(1*CI_FACTOR)

        router1 = MPRouterAuth(sk=PUB1_SK, name='ROUTER 1', config_fn=config_node, assert_fn=assert_router, block_until_rdy=BLOCK)
        router2 = MPRouterAuth(sk=PUB2_SK, name='ROUTER 2', config_fn=config_node, assert_fn=assert_router, block_until_rdy=True)

        time.sleep(5*CI_FACTOR)

        for r in (router1, router2):
            r.create_router_socket(identity=r.vk.encode(), secure=True, name='Router-{}'.format(r.ip))
            r.bind_router_socket(ip=r.ip)

        router1.connect_router_socket(vk=PUB2_VK)
        router2.connect_router_socket(vk=PUB1_VK)
        router2.send_msg(Poke.create(), router1.vk.encode())
        router1.send_msg(Poke.create(), router2.vk.encode())

        self.start(timeout=10*CI_FACTOR)


if __name__ == '__main__':
    unittest.main()
