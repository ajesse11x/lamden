"""The storage module for delegate is for bootstrapping the in-memory database for delegate nodes to store scratch and
execute smart contracts

Functions include:
-create_db
-execute (execute smart contract query)

Classes include:
-DBSingletonMeta
-DB (which inherits from DBSingletonMeta)
"""


import math
from cilantro.logger import get_logger
from cilantro.constants.testnet import TESTNET_DELEGATES, TESTNET_WITNESSES, TESTNET_MASTERNODES


log = get_logger("DB")


class VKBook:

    MASTERNODES = [node['vk'] for node in TESTNET_MASTERNODES]
    WITNESSES = [node['vk'] for node in TESTNET_WITNESSES]
    DELEGATES = [node['vk'] for node in TESTNET_DELEGATES]

    @staticmethod
    def get_all():
        return VKBook.MASTERNODES + VKBook.DELEGATES + VKBook.WITNESSES

    @staticmethod
    def get_masternodes():
        return VKBook.MASTERNODES

    @staticmethod
    def get_delegates():
        return VKBook.DELEGATES

    @staticmethod
    def get_witnesses():
        return VKBook.WITNESSES

    @staticmethod
    def get_delegate_majority():
        return math.ceil(len(VKBook.get_delegates()) * 2/3)
