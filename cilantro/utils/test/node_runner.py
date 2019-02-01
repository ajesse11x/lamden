def wrap_func(fn, *args, **kwargs):
    def wrapper():
        return fn(*args, **kwargs)
    return wrapper


def log_create(name, vk, ip):
    from cilantro.logger import get_logger
    log = get_logger("{}Builder".format(name))
    delim = '=' * 64
    msg = '\n' + delim + '\n' + 'Creating {} with:\nvk={}\nip={}\n'.format(name, vk, ip) + delim
    log.test(msg)


def run_mn(slot_num=None, sk=None, log_lvl=11, reset_db=False, nonce_enabled=True):
    assert slot_num is not None or sk is not None, "SK or slot num must be provided"

    # Due to some Sanic BS, we cannot set the log level between [1,10]
    assert log_lvl not in range(1, 10), "Due to a Sanic logging bug, Masternode cant set log lvl in the range [1,10]"

    import os
    if not nonce_enabled:
        # We must set this env var before we import anything from cilantro
        os.environ["NONCE_DISABLED"] = "1"

    # os.environ['SSL_ENABLED'] = "True"

    from cilantro.logger import get_logger, overwrite_logger_level
    from cilantro.nodes.factory import NodeFactory
    from cilantro.constants.testnet import TESTNET_MASTERNODES
    from cilantro.utils.test.node_runner import log_create
    from cilantro.protocol import wallet

    overwrite_logger_level(log_lvl)

    if slot_num is not None and slot_num >= len(TESTNET_MASTERNODES):
        raise Exception("Slot num {} out of bounds for TESTNET_MASTERNODES {}".format(slot_num, TESTNET_MASTERNODES))
    ip = os.getenv('HOST_IP')
    if slot_num is not None:
        vk, sk = TESTNET_MASTERNODES[slot_num]['vk'],  TESTNET_MASTERNODES[slot_num]['sk']
    else:
        vk = wallet.get_vk(sk)

    log_create("Masternode", vk, ip)
    NodeFactory.run_masternode(ip=ip, signing_key=sk, reset_db=reset_db)


def run_witness(slot_num=None, sk=None, log_lvl=11, reset_db=False):
    assert slot_num is not None or sk is not None, "SK or slot num must be provided"
    from cilantro.logger import get_logger, overwrite_logger_level
    from cilantro.nodes.factory import NodeFactory
    from cilantro.constants.testnet import TESTNET_WITNESSES
    import os
    from cilantro.utils.test.node_runner import log_create
    from cilantro.protocol import wallet

    overwrite_logger_level(log_lvl)

    if slot_num is not None and slot_num >= len(TESTNET_WITNESSES):
        raise Exception("Slot num {} out of bounds for TESTNET_WITNESSES {}".format(slot_num, TESTNET_WITNESSES))
    if slot_num is not None:
        vk, sk = TESTNET_WITNESSES[slot_num]['vk'],  TESTNET_WITNESSES[slot_num]['sk']
    else:
        vk = wallet.get_vk(sk)

    ip = os.getenv('HOST_IP')
    log_create("Witness", vk, ip)
    NodeFactory.run_witness(ip=ip, signing_key=sk, reset_db=reset_db)


def run_delegate(slot_num=None, sk=None, log_lvl=11, seneca_log_lvl=11, bad_actor=False, reset_db=False, bad_sb_set={1}, num_succ_sbs=3):
    assert slot_num is not None or sk is not None, "SK or slot num must be provided"
    import os
    if bad_actor:
        os.environ["BAD_ACTOR"] = '1'
        os.environ["SB_IDX_FAIL"] = ','.join((str(i) for i in bad_sb_set))
        os.environ["NUM_SUCC_SBS"] = str(num_succ_sbs)

    from cilantro.logger import get_logger, overwrite_logger_level
    from seneca.libs.logger import overwrite_logger_level as sen_overwrite_log
    from cilantro.nodes.factory import NodeFactory
    from cilantro.constants.testnet import TESTNET_DELEGATES
    from cilantro.utils.test.node_runner import log_create
    from cilantro.protocol import wallet

    overwrite_logger_level(log_lvl)
    sen_overwrite_log(seneca_log_lvl)

    if slot_num is not None and slot_num >= len(TESTNET_DELEGATES):
        raise Exception("Slot num {} out of bounds for TESTNET_DELEGATES {}".format(slot_num, TESTNET_DELEGATES))
    if slot_num is not None:
        vk, sk = TESTNET_DELEGATES[slot_num]['vk'],  TESTNET_DELEGATES[slot_num]['sk']
    else:
        vk = wallet.get_vk(sk)

    ip = os.getenv('HOST_IP')
    log_create("Delegate", vk, ip)
    NodeFactory.run_delegate(ip=ip, signing_key=sk, reset_db=reset_db)


def dump_it(volume, delay=0):
    from cilantro.utils.test.god import God
    from cilantro.logger import get_logger, overwrite_logger_level
    import logging

    overwrite_logger_level(logging.WARNING)
    God._dump_it(volume=volume, delay=delay)


def pump_it(*args, **kwargs):
    from cilantro.utils.test.god import God
    from cilantro.logger import get_logger, overwrite_logger_level
    import logging, time

    overwrite_logger_level(logging.WARNING)

    log = get_logger("Pumper")
    log.important("Starting the pump..")
    God._pump_it(*args, **kwargs)
