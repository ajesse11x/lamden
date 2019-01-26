NETWORK_SIZE = '2-2-2'

MN_LOG_LVL = 11
WITNESS_LOG_LVL = 5
DELEGATE_LOG_LVL = 5
SENECA_LOG_LVL = 11

RESET_DB = True

from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('{}.json'.format(NETWORK_SIZE))

from cilantro.constants.vmnet import get_config_file
from vmnet.cloud.testcase import AWSTestCase
import unittest, time, random, vmnet, cilantro, os
from os.path import join, dirname
from cilantro.utils.test.mp_test_case import vmnet_test
from cilantro.utils.test.god import God
from cilantro.logger.base import get_logger
from cilantro.utils.test.god import God
from cilantro.logger import get_logger, overwrite_logger_level
import logging, os, shutil, time
from cilantro.constants.system_config import *

detached = True


class TestPump(AWSTestCase):

    NUM_BLOCKS = 2
    VOLUME = TRANSACTIONS_PER_SUB_BLOCK * NUM_SB_PER_BLOCK * NUM_BLOCKS  # Number of transactions to dum
    config_file = get_config_file('cilantro-aws-{}.json'.format(NETWORK_SIZE))
    keep_up = True
    logging = True

    # Avg number of transactions per second we will pump. Set to pump 1 block per BATCH_SLEEP_INTERVAL
    PUMP_RATE = (TRANSACTIONS_PER_SUB_BLOCK * NUM_SB_PER_BLOCK) // BATCH_SLEEP_INTERVAL
    MODEL_AS_POISSON = True
    PUMP_WAIT = 300  # how long to sleep before we start the pump

    def test_pump(self):
        log = get_logger("Pumpatron")

        log.important3("Masternode Groups: {}".format(self.groups['masternode']))

        # Bootstrap master
        for i, nodename in enumerate(self.groups['masternode']):
            self.execute_python(nodename, God.run_mn(i, log_lvl=MN_LOG_LVL, nonce_enabled=False, reset_db=RESET_DB))

        # Bootstrap witnesses
        for i, nodename in enumerate(self.groups['witness']):
            self.execute_python(nodename, God.run_witness(i, log_lvl=WITNESS_LOG_LVL, reset_db=RESET_DB))

        # Bootstrap delegates
        for i, nodename in enumerate(self.groups['delegate']):
            self.execute_python(nodename, God.run_delegate(i, log_lvl=DELEGATE_LOG_LVL, seneca_log_lvl=SENECA_LOG_LVL,
                                                           reset_db=RESET_DB))
        # Bootstrap pump
        # self.execute_python('mgmt', God.pump_it(rate=self.PUMP_RATE, use_poisson=self.MODEL_AS_POISSON, pump_wait=self.PUMP_WAIT,
        #                                        sleep_sometimes=True, active_bounds=(30, 120), sleep_bounds=(20, 30)))


if __name__ == '__main__':
    unittest.main()
