from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('2-2-2.json')

from cilantro.messages.base.base import MessageBase
from cilantro.messages.envelope.envelope import Envelope
from cilantro.messages.consensus.sub_block_contender import SubBlockContender, SubBlockContenderBuilder
from cilantro.messages.consensus.merkle_signature import MerkleSignature, build_test_merkle_sig
from cilantro.messages.transaction.data import TransactionDataBuilder
from cilantro.constants.testnet import TESTNET_MASTERNODES, TESTNET_DELEGATES
from cilantro.protocol.structures.merkle_tree import MerkleTree
from unittest import TestCase
from cilantro.utils.keys import Keys

import unittest
from unittest.mock import MagicMock

import secrets
from unittest.mock import patch

DEL_SK = TESTNET_DELEGATES[0]['sk']
DEL_VK = TESTNET_DELEGATES[0]['vk']


class TestSubBlockContender(TestCase):

    def setUp(self):
        super().setUp()
        Keys.setup(DEL_SK)

    def test_builder(self):
        sbc = SubBlockContenderBuilder.create()
        self.assertEqual(sbc, SubBlockContender.from_bytes(sbc.serialize()))

    def test_create(self):
        txs = [TransactionDataBuilder.create_random_tx() for i in range(5)]
        raw_txs = [tx.serialize() for tx in txs]
        tree = MerkleTree.from_raw_transactions(raw_txs)

        input_hash = 'B' * 64  # in reality this would be the env hash. we can just make something up
        signature = build_test_merkle_sig(msg=tree.root)

        sbc1 = SubBlockContender.create(result_hash=tree.root_as_hex, input_hash=input_hash, merkle_leaves=tree.leaves,
                                        signature=signature, transactions=txs, sub_block_index=0, prev_block_hash='0'*64)
        sbc2 = SubBlockContender.create(result_hash=tree.root_as_hex, input_hash=input_hash, merkle_leaves=tree.leaves,
                                        signature=signature, transactions=txs, sub_block_index=0, prev_block_hash='0'*64)
        self.assertFalse(sbc1.is_empty)
        self.assertFalse(sbc2.is_empty)
        self.assertEqual(sbc1, sbc2)

    def test_serialize_deserialize(self):
        txs = [TransactionDataBuilder.create_random_tx() for i in range(5)]
        raw_txs = [tx.serialize() for tx in txs]
        tree = MerkleTree.from_raw_transactions(raw_txs)

        input_hash = 'B' * 64  # in reality this would be the env hash. we can just make something up
        signature = build_test_merkle_sig(msg=tree.root)

        sbc = SubBlockContender.create(result_hash=tree.root_as_hex, input_hash=input_hash, merkle_leaves=tree.leaves,
                                       signature=signature, transactions=txs, sub_block_index=0, prev_block_hash='0'*64)
        clone = SubBlockContender.from_bytes(sbc.serialize())

        self.assertEqual(clone, sbc)

    def test_empty_sub_block_contender(self):
        input_hash = 'B' * 64  # in reality this would be the env hash. we can just make something up
        signature = build_test_merkle_sig(msg=bytes.fromhex(input_hash), sk=DEL_SK, vk=DEL_VK)

        sbc = SubBlockContender.create_empty_sublock(input_hash=input_hash, signature=signature, sub_block_index=0,
                                                     prev_block_hash='0' * 64)

        self.assertTrue(sbc.is_empty)

    def test_sbc_handshake(self):
        txs = [TransactionDataBuilder.create_random_tx() for i in range(5)]
        raw_txs = [tx.serialize() for tx in txs]
        tree = MerkleTree.from_raw_transactions(raw_txs)

        input_hash = 'B' * 64  # in reality this would be the env hash. we can just make something up
        Keys.setup(DEL_SK)
        signature = build_test_merkle_sig(msg=tree.root)

        sbc1 = SubBlockContender.create(result_hash=tree.root_as_hex, input_hash=input_hash, merkle_leaves=tree.leaves,
                                       signature=signature, transactions=txs, sub_block_index=0, prev_block_hash='0'*64)
        self.assertFalse(sbc1.is_empty)
        msg_type = MessageBase.registry[type(sbc1)]
        sbc2 = MessageBase.registry[msg_type].from_bytes(sbc1.serialize())
        self.assertEqual(sbc1, sbc2)
        msg2 = Envelope.create_from_message(message=sbc2)
        es = msg2.serialize()
        env = Envelope.from_bytes(es)
        sbc = env.message
        if not sbc.signature.verify(bytes.fromhex(sbc.result_hash)):
            print("This SubBlockContender does not have a correct signature!")
        if len(sbc.merkle_leaves) > 0:
            print("This SubBlockContender have num of merkle leaves!")
            print(len(sbc.merkle_leaves))
            if MerkleTree.verify_tree_from_str(sbc.merkle_leaves, root=sbc.result_hash):
                for tx in sbc.transactions:
                    if not tx.hash in sbc.merkle_leaves:
                        print('Received malicious transactions that does not match any merkle leaves!')
                        break
                print('This SubBlockContender is valid!')
            else:
                print('This SubblockContender is INVALID!')
        else:
            print('This SubBlockContender is empty.')




if __name__ == '__main__':
    unittest.main()
