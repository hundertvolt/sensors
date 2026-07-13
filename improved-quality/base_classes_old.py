import os
import json
from uasyncio import Lock
from typing import Type, Any, Dict, NamedTuple, List, Tuple, Union, Callable, Coroutine, TypeVar, Literal, TYPE_CHECKING
from micropython import const
from collections import deque
from crc_checks import CRC8
import struct

if TYPE_CHECKING:
    from asy_fram_manager import AsyFramManager

try:  # just for typing and unsupported from micropython yet
    from types import TracebackType
except Exception:
    pass


def str_cfg(str_in: str) -> List[str]:  # extract field names from config string
    try:
        if len(str_in) < 2 or str_in[0] != "|" or str_in[-1] != "|":
            return []
        val_list = str_in[1:-2].replace(": {", ":{").split("||")
        return [v.split(":{")[0].replace('"', "") for v in val_list]
    except Exception:
        pass
    return []


def name_cfg(str_in: str) -> str:
    str_list = str_cfg(str_in)
    if len(str_list) == 1:
        return str_list[0]
    return ""


def cfg_from_str(cfg_vals: str) -> Dict[str, Dict[str, int | float | str | bool | None]]:
    try:
        if len(cfg_vals) < 2 or cfg_vals[0] != "|" or cfg_vals[-1] != "|":
            return {}
        res = json.loads("{" + cfg_vals[1:-2].replace("||", ", ") + "}")
        if isinstance(res, dict):
            return res
    except Exception:
        pass
    return {}


def make_dict(nt: NamedTuple) -> Dict[str, Dict[str, int | float | str | None]]:
    try:
        [name, kvpairs] = repr(nt).split("(")[0:2]
        keys = [c.split("=")[0].strip() for c in kvpairs.replace(")", "").split(",")]
    except Exception:
        return {}
    if keys == [""]:
        return {name: {}}
    try:
        return {name: {key: getattr(nt, key) for key in keys}}
    except Exception:
        return {name: {key: None for key in keys}}


def type_or_range_error(
    check_val: Any, defaults: Dict[str, int | float | str | bool | None], check_special: bool = True
) -> bool:
    try:
        val_type = defaults.get("type", None)
        val_min = defaults.get("min", None)
        val_max = defaults.get("max", None)
        val_special = defaults.get("special", None)

        if val_type == "int":  # check for int and bounds
            if type(check_val) is not int:
                return True
            if val_special is not None:
                if type(val_special) is not int:
                    return True
                if check_special and check_val == val_special:
                    return False
            if type(val_max) is int and type(val_min) is int and val_min <= check_val <= val_max:
                return False
        elif val_type == "float":  # check for float and bounds
            if type(check_val) is not float:
                return True
            if val_special is not None:
                if type(val_special) is not float:
                    return True
                if check_special and check_val == val_special:
                    return False
            if type(val_max) is float and type(val_min) is float and val_min <= check_val <= val_max:
                return False
        elif val_type == "str":  # check for float and length bounds
            if type(check_val) is not str:
                return True
            if val_special is not None:
                if type(val_special) is not str:
                    return True
                if check_special and check_val == val_special:
                    return False
            if type(val_max) is int and type(val_min) is int and val_min <= len(check_val) <= val_max:
                return False
        elif val_type == "bool":  # check for bool
            if type(check_val) is bool:
                return False
    except Exception:
        pass
    return True


def check_cfg_get_default(
    defaults: Dict[str, int | float | str | bool | None],
) -> Tuple[bool, int | float | str | bool | None]:
    try:  # returns flag if value is used for storage and if the default, if valid
        if sorted(defaults) != ["def", "max", "min", "special", "type"]:
            return True, None  # error (wrong or missing key) in definition
        def_val = defaults["def"]
        use_value = True
        # special case: if default is None and special has a value, this is used to ignore the value
        # for storage, but uses the special value as mock-up current value for API use.
        # the special value must fulfill the min-max-(length) criteria in that case.
        if def_val is None and defaults["special"] is not None:
            def_val = defaults["special"]
            use_value = False
        if type_or_range_error(def_val, defaults, check_special=use_value):
            return True, None  # self-check of defaults
        return use_value, def_val
    except Exception:  # dict read error
        return True, None


LockableType = TypeVar("LockableType", bound="Lockable")


class Lockable:
    def __init__(self, asy_lock: Lock | None = None) -> None:
        if asy_lock is None:
            self.asy_lock = Lock()
        else:
            self.asy_lock = asy_lock

    async def __aenter__(self: LockableType) -> LockableType:
        await self.asy_lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        try:
            self.asy_lock.release()
        except RuntimeError:  # in case it's already released somehow
            pass
        return False


class LockableBuffer(Lockable):
    def __init__(self, size: int, data_start: int = 0, data_length: int | None = None) -> None:
        super().__init__()
        self.data_start = data_start
        data_length = size - data_start if data_length is None else data_length
        self.data_end = data_start + data_length
        if self.data_end > size:
            self.buf = None
        else:
            self.buf = bytearray(size)

    def get_buf(self) -> bytearray | None:
        return self.buf

    def get_data_buf(self) -> memoryview | None:
        if self.buf is None:
            return None
        return memoryview(self.buf)[self.data_start : self.data_end]


_50_YEARS_SEC = const(1576800000)  # seconds of 50 years(!!) perfectly fits into 32bit signed


class TimeCounterManager:
    def __init__(self, init_value: int = 0) -> None:
        self.uptime = init_value
        self.uptime_lock = Lock()

    async def set_counter(self, value: int) -> None:
        async with self.uptime_lock:
            self.uptime = value if value <= _50_YEARS_SEC else _50_YEARS_SEC

    async def get_counter(self) -> int:
        async with self.uptime_lock:
            ret = self.uptime
        return ret

    async def increment(self) -> int:
        async with self.uptime_lock:
            if self.uptime < _50_YEARS_SEC:
                self.uptime += 1
            ret = self.uptime
        return ret

    async def decrement(self) -> int:
        async with self.uptime_lock:
            if self.uptime > 0:
                self.uptime -= 1
            ret = self.uptime
        return ret


class LockedFlag:
    def __init__(self, init_value: bool = False) -> None:
        self.flag = init_value
        self.flag_lock = Lock()

    async def set_true(self) -> None:
        async with self.flag_lock:
            self.flag = True

    async def set_false(self) -> None:
        async with self.flag_lock:
            self.flag = False

    async def get_value(self) -> bool:
        async with self.flag_lock:
            ret = self.flag
        return ret


class LockedValue:
    def __init__(self, init_value: int | float) -> None:
        self.value = init_value
        self.value_lock = Lock()

    async def set_value(self, value: int | float) -> None:
        async with self.value_lock:
            self.value = value

    async def get_value(self) -> int | float:
        async with self.value_lock:
            ret = self.value
        return ret


# defs for PrintLog
_LOG_OFF = const(0)
_LOG_ERR = const(1)
_LOG_WARN = const(2)
_LOG_ONCE = const(3)
_LOG_EVENT = const(4)
_LOG_ALL = const(5)


class PrintLog:
    def __init__(self, level: int | None = None) -> None:
        self.level = _LOG_OFF
        self.set_level(level)

    def set_level(self, level: int | None) -> None:
        if level is None:
            self.level = _LOG_OFF
        elif level < _LOG_OFF:
            self.level = _LOG_OFF
        elif level > _LOG_ALL:
            self.level = _LOG_ALL
        else:
            self.level = level

    def get_level(self) -> int:
        return self.level

    @staticmethod
    def level_off() -> int:
        return _LOG_OFF

    @staticmethod
    def level_err() -> int:
        return _LOG_ERR

    @staticmethod
    def level_warn() -> int:
        return _LOG_WARN

    @staticmethod
    def level_once() -> int:
        return _LOG_ONCE

    @staticmethod
    def level_event() -> int:
        return _LOG_EVENT

    @staticmethod
    def level_info() -> int:
        return _LOG_ALL

    def err(self, *args: Any, **kwargs: Any) -> None:
        if self.level >= _LOG_ERR:
            print(*args, **kwargs)

    def wrn(self, *args: Any, **kwargs: Any) -> None:
        if self.level >= _LOG_WARN:
            print(*args, **kwargs)

    def one(self, *args: Any, **kwargs: Any) -> None:
        if self.level >= _LOG_ONCE:
            print(*args, **kwargs)

    def evt(self, *args: Any, **kwargs: Any) -> None:
        if self.level >= _LOG_EVENT:
            print(*args, **kwargs)

    def all(self, *args: Any, **kwargs: Any) -> None:
        if self.level >= _LOG_ALL:
            print(*args, **kwargs)


# defs for history logging
_NO_ERR = const(0x00)
_MAX_ERR = const(0x7F)
_NO_WRN = const(0x80)
_MAX_WRN = const(0xFF)
_MAX_CNT = const(0xFFFF)


class PrintLogHistory(PrintLog):
    def __init__(self, history_length: int = 10, level: int | None = None) -> None:
        super().__init__(level=level)
        self.hl = history_length
        self.history = deque([_NO_ERR] * history_length, history_length)
        self.err_count = 0

    async def setup(self) -> None:
        pass

    async def _store_err(self, min_e: int, max_e: int, errno: int) -> None:
        if self.err_count < _MAX_CNT:
            self.err_count += 1
        elif self.level > _LOG_OFF:
            print("PrintLog: Error count reached maximum value!")
        if errno <= _NO_ERR:
            return
        errno += min_e
        if errno <= max_e:
            self.history.append(errno)
        elif self.level > _LOG_OFF:
            print("PrintLog: Error number", errno - min_e, "is invalid!")

    async def err_s(self, *args: Any, errno: int = _NO_ERR, **kwargs: Any) -> None:
        await self._store_err(_NO_ERR, _MAX_ERR, errno)
        if self.level >= _LOG_ERR:
            print(*args, **kwargs)

    async def wrn_s(self, *args: Any, wrnno: int = _NO_ERR, **kwargs: Any) -> None:
        await self._store_err(_NO_WRN, _MAX_WRN, wrnno)
        if self.level >= _LOG_WARN:
            print(*args, **kwargs)

    async def reset(self) -> None:
        self.history.extend([_NO_ERR] * len(self.history))
        self.err_count = 0

    async def get_log(self, name: str) -> Dict[str, Dict[str, int | List[int] | List[str]]]:
        err_num = []
        err_type = []
        for errno in self.history:
            if errno == _NO_ERR or errno == _NO_WRN:
                err_num.append(errno)
                err_type.append("N")
            elif errno <= _MAX_ERR:
                err_num.append(errno - _NO_ERR)
                err_type.append("E")
            elif errno <= _MAX_WRN:
                err_num.append(errno - _NO_WRN)
                err_type.append("W")
        return {name: {"ErrCount": self.err_count, "ErrNum": err_num, "ErrType": err_type}}


class PrintLogHistStore(PrintLogHistory):
    def __init__(self, fram: "AsyFramManager", history_length: int = 10, level: int | None = None) -> None:
        super().__init__(history_length=history_length, level=level)
        self.initialized = False
        self.fram = fram.get_chunk(struct.calcsize("H" + "B" * len(self.history)), crc=CRC8())
        if self.fram is None and self.level > _LOG_OFF:
            print("PrintLog: FRAM allocation failed!")

    async def setup(self) -> None:
        if self.fram is None or self.initialized:
            return
        if await self._read_fram():
            self.initialized = True
        elif await self._write_fram():
            self.initialized = True
        elif self.level > _LOG_OFF:
            print("PrintLog: FRAM setup failed!")

    async def _write_fram(self) -> bool:
        if self.fram is None:
            return False
        buf = self.fram.get_buffer()
        dbuf = buf.get_data_buf()
        try:
            struct.pack_into("H", dbuf, 0, self.err_count)
            struct.pack_into("B" * len(self.history), dbuf, struct.calcsize("H"), *self.history)
            return await self.fram.write_into(buf)
        except Exception:
            return False

    async def _read_fram(self) -> bool:
        if self.fram is None:
            return False
        buf = self.fram.get_buffer()
        dbuf = buf.get_data_buf()
        if not await self.fram.read_into(buf):
            return False
        try:
            self.err_count = struct.unpack_from("H", dbuf, 0)[0]
            self.history.extend(struct.unpack_from("B" * len(self.history), dbuf, struct.calcsize("H")))
            return True
        except Exception:
            return False

    async def _store_err(self, min_e: int, max_e: int, errno: int) -> None:
        if self.err_count < _MAX_CNT:
            self.err_count += 1
        elif self.level > _LOG_OFF:
            print("PrintLog: Error count reached maximum value!")
        if errno <= _NO_ERR:
            return
        errno += min_e
        if errno <= max_e:
            self.history.append(errno)
        elif self.level > _LOG_OFF:
            print("PrintLog: Error number", errno - min_e, "is invalid!")
        if not self.initialized and self.level > _LOG_OFF:
            print("PrintLog: FRAM uninitialized, call setup first!")
            return
        if not await self._write_fram() and self.level > _LOG_OFF:
            print("PrintLog: FRAM write failed!")

    async def reset(self) -> None:
        if not self.initialized and self.level > _LOG_OFF:
            print("PrintLog: FRAM uninitialized, call setup first!")
            return
        self.history.extend([_NO_ERR] * len(self.history))
        self.err_count = 0
        if not await self._write_fram() and self.level > _LOG_OFF:
            print("PrintLog: FRAM write failed!")


WriteValidity = Dict[str, Literal["Invalid", "Unchanged", "Valid", "Failed"]]


class ConfigManager:
    def __init__(self, filename: str, cfg_vals: str, logger: PrintLog) -> None:
        self.pr = logger
        self.config_lock = Lock()
        self.config_file = filename
        self.valid = False
        data: Dict[str, Any] | None = None
        try:
            if (os.stat(self.config_file)[0] & 0x4000) == 0:  # file exists:
                with open(self.config_file, "r") as f:
                    try:
                        data = json.load(f)  # parse to json
                        if isinstance(data, dict):  # parsing resulted in a dict
                            self.pr.one("JSON Data in config file", self.config_file, "found.")
                        else:  # generally valid json but not a dict
                            data = None
                            self.pr.wrn("Data in config file", self.config_file, "has wrong format.")
                    except Exception as e:  # no valid json format at all
                        self.pr.wrn("JSON Data in config file", self.config_file, "is invalid:", e)
            else:  # filename exists but is e.g. a directory and cannot be used
                self.pr.err(self.config_file, "exists but is not a file, cannot write!")
                return
        except Exception as e:  # file does not exist at all
            self.pr.wrn("Config file", self.config_file, "not found:", e)

        defaults = cfg_from_str(cfg_vals)
        if len(defaults) == 0:  # default config contains no values
            self.pr.err(self.config_file, "- Defaults are empty, config is not valid!")
            return

        rewrite = False  # don't write file unless required
        valid_cfg = {}  # create surely valid config
        for key, default in defaults.items():  # iterate through default config
            use_value, default_val = check_cfg_get_default(default)  # read and selfcheck
            if default_val is None:  # invalid config, no default or special-alone value
                self.pr.err(self.config_file, "- Default Key", key, "Error or None, config is not valid!")
                return
            if not use_value:  # special-alone value
                continue  # not used for storage, skip loop iteration
            if data is None:  # no or invalid config file
                new_cfg = default_val  # immediately take default value
            else:  # file exists and is valid
                new_cfg = data.pop(key, None)  # remove all used and known keys from config
                if type_or_range_error(new_cfg, default):  # if new_cfg is None or any other error
                    rewrite = True
                    new_cfg = default_val
                    self.pr.wrn(self.config_file, "- Key", key, "has error or is missing, using default!")
            valid_cfg[key] = new_cfg
        if data is None:  # no file -> always create
            rewrite = True
        elif len(data) != 0:  # unexpected keys remaining from existing file
            rewrite = True
            self.pr.wrn(self.config_file, "- Removed invalid keys from config file!")

        if not rewrite:
            self.valid = True
            self.pr.one("Valid configuration data found in", self.config_file, "- config is ready.")
            return

        if len(valid_cfg) == 0:
            self.pr.wrn(self.config_file, "- Default config valid but no storage values!")

        self.pr.one(self.config_file, "- Writing configuration file!")
        try:
            with open(self.config_file, "w") as f:
                json.dump(valid_cfg, f)
            self.valid = True
            self.pr.one("Default data was written in", self.config_file, "- config is ready.")
            return
        except Exception as e:
            self.pr.err("Error writing config", self.config_file, "- config is not valid:", e)
            return

    async def get_dict(self, keys: List[str]) -> Dict[str, int | float | str | bool | None] | None:
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot read!")
            return None
        async with self.config_lock:
            ret_dict = {}
            self.pr.all(self.config_file, "- Reading config data into dict.")
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    self.pr.err(self.config_file, "- Config parse error!")
                    return None
                for key in keys:
                    ret_dict[key] = data[key]
                return ret_dict
            except Exception as e:  # mainly file errors, key errors
                self.pr.err(self.config_file, "- Config read error:", e)
                return None

    async def _get_values(self, keys: str) -> List[Any] | None:
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot read!")
            return None
        async with self.config_lock:
            ret_values = []
            self.pr.all(self.config_file, "- Reading config data into list.")
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    self.pr.err(self.config_file, "- Config parse error!")
                    return None
                for key in str_cfg(keys):
                    ret_values.append(data[key])
                return ret_values
            except Exception as e:  # mainly file errors, key errors
                self.pr.err(self.config_file, "- Config read error:", e)
                return None

    async def get_int_values(self, keys: str) -> List[int] | None:
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            ret_values = [int(v) for v in values]
        except Exception:
            ret_values = None
        return ret_values

    async def get_float_values(self, keys: str) -> List[float] | None:
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            ret_values = [float(v) for v in values]
        except Exception:
            ret_values = None
        return ret_values

    async def get_str_values(self, keys: str) -> List[str] | None:
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            ret_values = [str(v) for v in values]
        except Exception:
            ret_values = None
        return ret_values

    async def get_bool_values(self, keys: str) -> List[bool] | None:
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            ret_values = [bool(v) for v in values]
        except Exception:
            ret_values = None
        return ret_values

    async def write_config(
        self, data: Dict[str, int | float | str | bool | None], cfg_vals: str
    ) -> Tuple[bool, WriteValidity]:
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot write!")
            return False, {}
        async with self.config_lock:
            try:
                with open(self.config_file, "r") as f:
                    conf_data = json.load(f)
                if not isinstance(conf_data, dict):
                    self.pr.err(self.config_file, "- Config parse error!")
                    return False, {}
                changed = False
                defaults = cfg_from_str(cfg_vals)
                dict_results: WriteValidity = {}
                for key, value in data.items():
                    if key not in defaults:
                        self.pr.err(self.config_file, "- Key", key, "not found, skipping!")
                        dict_results[key] = "Invalid"
                        continue
                    use_value, default_val = check_cfg_get_default(defaults[key])
                    if default_val is None:
                        self.pr.err(self.config_file, "- Default Key", key, "Error or None, no data written!")
                        return False, {}
                    if not use_value:
                        dict_results[key] = "Valid"
                        self.pr.evt(self.config_file, "- Key", key, "is valid but not in storage, skipping.")
                        continue  # not used for storage
                    if key not in conf_data:
                        dict_results[key] = "Failed"
                        self.pr.err(self.config_file, "- Key", key, "not found in config file, ignoring!")
                        continue
                    if type_or_range_error(value, defaults[key]):
                        self.pr.err(self.config_file, "- Type / range error in", key, "- skipping!")
                        dict_results[key] = "Invalid"
                        continue
                    if conf_data[key] != value:
                        conf_data[key] = value
                        dict_results[key] = "Valid"
                        changed = True
                    else:
                        dict_results[key] = "Unchanged"
                if not changed:
                    self.pr.evt(self.config_file, "- No new / unchanged config data.")
                    return True, dict_results
                with open(self.config_file, "w") as f:
                    json.dump(conf_data, f)
                    self.pr.evt(self.config_file, "- Config data was written.")
                    return True, dict_results
            except Exception as e:  # mainly file errors, key errors
                self.pr.err(self.config_file, "- Error writing config data:", e)
                return False, {}


MeasDataType = TypeVar("MeasDataType", bound=Tuple[Union[int, float, None], ...])


class SensorReader:
    def __init__(
        self,
        init_data: NamedTuple,
        max_i2c_err: int,
        fram: "AsyFramManager" | None = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        if fram is None:
            self.pr = PrintLogHistory(history_length, debug)
            self.pr.one("Init with memory logging.")
        else:
            self.pr = PrintLogHistStore(fram, history_length, debug)
            self.pr.one("Init with FRAM logging.")
        self._datastruct = init_data
        self._datalock = Lock()
        self.max_i2c_err = max_i2c_err
        self._err_cnt_internal = 0

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def _error_check(self, results: MeasDataType, name: str, condition: bool = True) -> bool:
        if any(res is None for res in results) and condition:
            self._err_cnt_internal += 1
            await self.pr.err_s(name + " Fehlerzähler erhöht auf", self._err_cnt_internal, errno=1)
            if self._err_cnt_internal > self.max_i2c_err:
                await self.pr.err_s(name + " Maximale Fehleranzahl erreicht!", errno=2)
                return False  # Abbruch der Schleife führt zu Task-Reset
        else:
            if self._err_cnt_internal > 0:
                self._err_cnt_internal -= 1
                self.pr.err(name + " Fehlerzähler zurück auf", self._err_cnt_internal)
        return True

    async def _get_meas_data(self) -> NamedTuple:
        async with self._datalock:
            return self._datastruct

    async def _set_meas_data(self, data: NamedTuple) -> None:
        async with self._datalock:
            self._datastruct = data

    async def _get_mgr_cfg(self, cfg: List[str]) -> Dict[str, int | float | str | None] | None:
        return {}

    async def _get_dict_cfg(
        self,
        name: str,
        cfgstring: str,
        callback: Callable[[], Coroutine[Any, Any, Dict[str, int | float | str | None]]] | None = None,
    ) -> Dict[str, Dict[str, int | float | str | None]]:
        cfg = str_cfg(cfgstring)
        ret: Dict[str, Dict[str, int | float | str | None]] = {name: {key: None for key in cfg}}

        sensor_conf = await self._get_mgr_cfg(cfg)
        if sensor_conf is not None:
            try:
                ret[name].update(sensor_conf)
            except Exception as e:
                await self.pr.err_s("Error updating config dict:", e, errno=3)

        if callback is not None:
            try:
                sensor_callback = await callback()
                if not all(k in ret[name] for k in sensor_callback):
                    await self.pr.wrn_s("Warning: Sensor callback adds unknown keys to config dict!", wrnno=1)
                ret[name].update(sensor_callback)
            except Exception as e:
                await self.pr.err_s("Error reading config from sensor:", e, errno=4)

        return ret


class SensorReaderConfig(SensorReader):
    def __init__(
        self,
        init_data: NamedTuple,
        max_i2c_err: int,
        name: str,
        default_vals: str,
        cfg_path: str = "",
        fram: "AsyFramManager" | None = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(init_data, max_i2c_err, fram, history_length, debug)
        self.cfgmgr = ConfigManager(
            cfg_path + "config_" + name + ".cfg",
            default_vals,
            self.pr,
        )

    async def _get_mgr_cfg(self, cfg: List[str]) -> Dict[str, int | float | str | None] | None:
        return await self.cfgmgr.get_dict(cfg)
