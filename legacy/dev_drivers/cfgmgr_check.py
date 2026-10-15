import asyncio
from uasyncio import ThreadSafeFlag
from collections import namedtuple
from base_classes import SensorReaderConfig, Lockable, make_dict
from typing import Dict, Tuple, Union, Any, List, Callable, cast, Coroutine
from base_classes import ConfigManager

_VAL_INT_BP = '|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|'
_VAL_INT_MAX = '|"BackupMaxAge": {"def": 7200, "type": "int", "min": 0, "max": 10080, "special": null}|'
_VAL_INT_WT = '|"WaitTimeNTP": {"def": 30, "type": "int", "min": 0, "max": 600, "special": null}|'
_NAME = "SGP40"


def test_cfgmgr(teststr, exp):
    print("*****")
    cfgmgr = ConfigManager("foo.cfg", teststr + _VAL_INT_MAX + _VAL_INT_WT, debug=5)
    print("***Expected:", exp, "\n\n")
    del cfgmgr
    
'''

cfgmgr = ConfigManager("foo.cfg", _VAL_INT_BP + _VAL_INT_MAX + _VAL_INT_WT, debug=5)


def test_cfgmgr(teststr, exp):
    print("*****")
    d={"BackupMaxAge": 200, "WaitTimeNTP": 520, "BackupPeriod": 1}
    print(asyncio.run(cfgmgr.write_config(d, _VAL_INT_MAX + teststr + _VAL_INT_WT)))

    print("***Expected:", exp, "\n\n")
    

test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "OK")



'''
test_cfgmgr('|"BackupPeriod": {"ddef": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR1")
test_cfgmgr('|"BackupPeriod": {"def": 1, "tydpe": "int", "min": 0, "max": 1440, "special": null}|', "ERR2")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "micn": 0, "max": 1440, "special": null}|', "ERR3")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "macx": 1440, "special": null}|', "ERR4")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "spxecial": null}|', "ERR5")
test_cfgmgr('|"BackupPeriod": {"def": null, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR6")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "foo", "min": 0, "max": 1440, "special": null}|', "ERR7")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": f, "max": 1440, "special": null}|', "ERR8")
test_cfgmgr('|: {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR9")
test_cfgmgr('|"BackupPeriod: {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR10")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 14g40, "special": null}|', "ERR11")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}', "ERR12")
test_cfgmgr('|"BackupPeriod": "def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR13")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null|', "ERR14")
test_cfgmgr(' |"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR15")
test_cfgmgr('|"BackupPeriod": {}|', "ERR16")
test_cfgmgr('|"BackupPeriod": {foo}|', "ERR17")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", min": 0, "max": 1440, "special": null}|', "ERR18")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special: null}|', "ERR19")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int" "min": 0, "max": 14d0, "special": null}|', "ERR21")
test_cfgmgr('|"BackupPeriod": {"type": "int", "min": 0, "max": 1440, "special": null}|', "ERR23")
test_cfgmgr('|"BackupPeriod": {"def": 1, "min": 0, "max": 1440, "special": null}|', "ERR24")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "max": 1440, "special": null}|', "ERR25")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "special": null}|', "ERR26")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, }|', "ERR27")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 5, "max": 1440, "special": null}|', "ERR28")
test_cfgmgr('|"BackupPeriod": {"def": 2000, "type": "int", "min": 5, "max": 1440, "special": null}|', "ERR29")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "bool", "min": 0, "max": 1440, "special": null}|', "ERR30")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "float", "min": 0, "max": 1440, "special": null}|', "ERR31")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "str", "min": 0, "max": 1440, "special": null}|', "ERR32")
test_cfgmgr('|"BackupPeriod": {"def": 1.0, "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR33")
test_cfgmgr('|"BackupPeriod": {"def": true, "type": "str", "min": 0, "max": 1440, "special": null}|', "ERR34")
test_cfgmgr('|"BackupPeriod": {"def": "foo", "type": "int", "min": 0, "max": 1440, "special": null}|', "ERR35")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0.0, "max": 1440, "special": null}|', "ERR36")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440.0, "special": null}|', "ERR37")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 5, "max": 1440, "special": 2}|', "ERR38")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": "foo", "special": 2}|', "ERR39")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": "0", "max": 1440, "special": 2}|', "ERR40")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": "2"}|', "ERR41")
test_cfgmgr('|"BackupPeriod": {"def": "fo", "type": "str", "min": 3, "max": 7, "special": null}|', "ERR42")
test_cfgmgr('|"BackupPeriod": {"def": "foobarbaz", "type": "str", "min": 3, "max": 7, "special": null}|', "ERR43")
test_cfgmgr('|"BackupPeriod": {"def": "foobarbaz", "type": "str", "min": 3, "max": 7, "special": foobabaz}|', "ERR44")
test_cfgmgr('|"BackupPeriod": {"def": "true", "type": "bool", "min": 3, "max": 7, "special": foobabaz}|', "ERR45")
test_cfgmgr('|"BackupPeriod": {"def": 5, "type": "bool", "min": 3, "max": 7, "special": foobabaz}|', "ERR46")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}| ', "ERR47")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}', "ERR48")


test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": 1, "type": "int", "min": 5, "max": 1440, "special": 1}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def" 1, "type": "int", "min": 0, "max": 1440, "special": null}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": 1.0, "type": "float", "min": 0.0, "max": 1440.0, "special": null}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": 1.0, "type": "float", "min": 5.0, "max": 1440.0, "special": 1.0}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": "foobar", "type": "str", "min": 3, "max": 7, "special": null}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": "foobarbaz", "type": "str", "min": 3, "max": 7, "special": "foobarbaz"}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": true, "type": "bool", "min": null, "max": null, "special": null}|', "OK")
test_cfgmgr('|"BackupPeriod": {"def": false, "type": "bool", "min": null, "max": null, "special": null}|', "OK")
'''

asyncio.run(cfgmgr.get_str_values(_VAL_INT_BP + _VAL_INT_MAX))
asyncio.run(cfgmgr.get_float_values(_VAL_INT_BP + _VAL_INT_MAX))
asyncio.run(cfgmgr.get_bool_values(_VAL_INT_BP + _VAL_INT_MAX))
asyncio.run(cfgmgr.get_int_values(_VAL_INT_BP + _VAL_INT_MAX))
'''