import capnp
import enum
from cilantro_ee.protocol.wallet import Wallet, _verify
from cilantro_ee.protocol.pow import SHA3POW, SHA3POWBytes
from cilantro_ee.messages import capnp as schemas
import os
import capnp

blockdata_capnp = capnp.load(os.path.dirname(schemas.__file__) + '/blockdata.capnp')
subblock_capnp = capnp.load(os.path.dirname(schemas.__file__) + '/subblock.capnp')
envelope_capnp = capnp.load(os.path.dirname(schemas.__file__) + '/envelope.capnp')
transaction_capnp = capnp.load(os.path.dirname(schemas.__file__) + '/transaction.capnp')
signal_capnp = capnp.load(os.path.dirname(schemas.__file__) + '/signals.capnp')

# Message type registration
# Each type is a uint32 number (0 - 4294967295)
#     0 -  9999 = block data
# 10000 - 19999 = envelope
# 20000 - 29999 = transaction
# 30000 - 39999 = signals
# 40000 - 49999 = consensus

class Serializer:
    def __init__(self, capnp_type, sign=False, prove=False):
        self.capnp_type = capnp_type
        self.sign = sign
        self.prove = prove

    def unpack(self, msg):
        message = envelope_capnp.Message.from_bytes_packed(msg)

        if self.sign:
            valid = _verify(message.verifyingKey, message.payload, message.signature)
            if not valid:
                return None

        if self.prove:
            proven = SHA3POWBytes.check(message.payload, message.proof)
            if not proven:
                return None

        final_message = self.capnp_type.from_bytes_packed(message.payload)
        return final_message

    def pack(self, msg, wallet=None):
        message = envelope_capnp.Message.new_message(payload=msg)

        if self.sign:
            if wallet is None:
                return None
            message.verifyingKey = wallet.verifying_key()
            message.signature = wallet.sign(message.payload)

        if self.prove:
            message.proof = SHA3POWBytes.find(message.payload)

        packed_message = message.to_bytes_packed()

        return packed_message


class MessageTypes:
    MAKE_NEXT_BLOCK = 0
    PENDING_TRANSACTIONS = 1
    NO_TRANSACTIONS = 2
    EMPTY_BLOCK_MADE = 3
    NON_EMPTY_BLOCK_MADE = 4
    READY_INTERNAL = 5
    READY_EXTERNAL = 6
    UPDATED_STATE_SYNC = 7

    TRANSACTION_DATA = 40000
    MERKLE_PROOF = 40001
    SUBBLOCK_CONTENDER = 40002
    BLOCK_INDEX_REQUEST = 40003
    NEW_BLOCK_NOTIFICATION = 40004
    BLOCK_INDEX_REPLY = 40005
    BLOCK_DATA_REQUEST = 40006
    BLOCK_DATA_REPLY = 40007

    TRANSACTION_BATCH = 10000

# Default Serializers
INTERNAL_MESSAGE_SERIALIZER = Serializer(capnp_type=signal_capnp.Signal)

TYPE_MAP = {
    # Internal signals
    MessageTypes.MAKE_NEXT_BLOCK: INTERNAL_MESSAGE_SERIALIZER,
    MessageTypes.PENDING_TRANSACTIONS: INTERNAL_MESSAGE_SERIALIZER,
    MessageTypes.NO_TRANSACTIONS: INTERNAL_MESSAGE_SERIALIZER,
    MessageTypes.EMPTY_BLOCK_MADE: INTERNAL_MESSAGE_SERIALIZER,
    MessageTypes.NON_EMPTY_BLOCK_MADE: INTERNAL_MESSAGE_SERIALIZER,
    MessageTypes.READY_INTERNAL: INTERNAL_MESSAGE_SERIALIZER,
    MessageTypes.UPDATED_STATE_SYNC: INTERNAL_MESSAGE_SERIALIZER,

    # External Signals
    MessageTypes.READY_EXTERNAL: Serializer(capnp_type=signal_capnp.Signal, sign=True),

    MessageTypes.TRANSACTION_DATA: Serializer(capnp_type=transaction_capnp.TransactionData),
    MessageTypes.MERKLE_PROOF: Serializer(capnp_type=subblock_capnp.MerkleProof, sign=True),
    MessageTypes.SUBBLOCK_CONTENDER: Serializer(capnp_type=subblock_capnp.SubBlockContender),
    MessageTypes.BLOCK_INDEX_REQUEST: Serializer(capnp_type=blockdata_capnp.BlockIndexRequest, sign=True)
}


class MessageManager:
    @staticmethod
    def pack_dict(msg_type, arg_dict, wallet=None):
        serializer = TYPE_MAP.get(msg_type)
        if serializer is None:
            return None

        msg_payload = serializer.capnp_type.new_message(**arg_dict)
        msg = msg_payload.to_bytes_packed()

        return serializer.pack(msg=msg, wallet=wallet)

    @staticmethod
    def pack(msg_type, msg_payload, wallet=None):
        serializer = TYPE_MAP.get(msg_type)
        if serializer is None:
            return None

        return serializer.pack(msg=msg_payload, wallet=wallet)

    @staticmethod
    def unpack(msg_type, msg_payload):
        serializer = TYPE_MAP.get(msg_type)
        if serializer is None:
            return None

        return serializer.unpack(msg=msg_payload)
