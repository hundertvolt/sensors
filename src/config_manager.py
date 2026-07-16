"""Per-sensor JSON config storage. Each sensor gets its own `config_<name>.cfg` file (see
base_classes.py's SensorReaderConfig), validated against a schema every driver defines as
`_VAL_*` `const()` tuples (e.g. asy_bmp3xx_driver.py's
`_VAL_SI = const((("SampleInterv", "int", 2, 1, 3600, None),))` - one field per tuple: name, type,
def, min, max, special) and concatenated for a multi-field schema (`_VAL_SI + _VAL_POV + ...`).
Kept as real tuples rather than a hand-parsed string precisely because MicroPython (since v1.26,
current pin v1.28) const()-folds a literal tuple of immutables the same way it already did plain
string/int/float literals - a `const()`-wrapped, underscore-prefixed name costs no module-dict
entry and is never rebuilt on reference, confirmed directly against the real interpreter (see
BACKLOG.md), so this carries the same near-zero RAM footprint the old pipe-delimited-JSON-string
encoding did, without its hand-rolled parser's fragility.

Shared contract: every public function/method here returns a documented "invalid" sentinel
(`[]`/`""`/`{}`/`None`/`True` as noted per function) - never raises - for missing input,
malformed schema tuples, or a missing/corrupt/unreadable config file. Real file I/O (this file's
only external boundary - no hardware) is fully exercised by tests/test_config_manager.py under
the real MicroPython Unix-port interpreter, unlike the hardware-touching drivers.
"""

import asyncio
import json
import os

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Literal, NamedTuple

    # One schema field: (name, type, def, min, max, special) - see module docstring.
    FieldSchema = tuple[
        str,
        str,
        "int | float | str | bool | None",
        "int | float | None",
        "int | float | None",
        "int | float | str | None",
    ]
    ConfigSchema = tuple[FieldSchema, ...]

from print_log import PrintLog


def schema_names(schema: "ConfigSchema") -> "list[str]":  # field names, in schema order (duplicates preserved); malformed input -> []
    try:
        return [field[0] for field in schema]
    except Exception:
        return []


def name_cfg(schema: "ConfigSchema") -> str:  # single-field convenience wrapper around schema_names
    names = schema_names(schema)
    if len(names) == 1:
        return names[0]
    return ""


def schema_dict(schema: "ConfigSchema") -> "dict[str, FieldSchema]":  # {field_name: field_record}; duplicate names keep the last occurrence
    try:
        return {field[0]: field for field in schema}
    except Exception:
        return {}


def make_dict(nt: "NamedTuple") -> "dict[str, dict[str, int | float | str | None]]":  # {type_name: {field: value}} via repr() - MicroPython namedtuples have no _fields/_asdict()
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
    check_val: "Any", field: "FieldSchema", check_special: bool = True
) -> bool:  # True if check_val doesn't satisfy field's own type/min/max(/special) schema entry
    try:
        _name, val_type, _def, val_min, val_max, val_special = field

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
        elif val_type == "str":  # check for str and length bounds
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
    field: "FieldSchema",
) -> "tuple[bool, int | float | str | bool | None]":
    try:  # returns flag if value is used for storage and if the default, if valid
        _name, _type, def_val, _min, _max, special_val = field  # wrong length/shape -> ValueError, caught below
        use_value = True
        # special case: if default is None and special has a value, this is used to ignore the value
        # for storage, but uses the special value as mock-up current value for API use. The special
        # value is an out-of-band sentinel (e.g. asy_scd30_driver.py's AmbPres uses 0 = "disabled"
        # outside its 700-1400 hPa physical range), so it must NOT be forced through the ordinary
        # min/max check here - check_special=True lets type_or_range_error's own "equals the special
        # value" shortcut apply to it instead.
        if def_val is None and special_val is not None:
            def_val = special_val
            use_value = False
        if type_or_range_error(def_val, field, check_special=True):
            return True, None  # self-check of defaults
        return use_value, def_val
    except Exception:  # malformed field record
        return True, None


if TYPE_CHECKING:
    WriteValidity = dict[str, Literal["Invalid", "Unchanged", "Valid", "Failed"]]


class ConfigManager:
    def __init__(self, filename: str, cfg_vals: "ConfigSchema", logger: "PrintLog") -> None:
        self.pr = logger
        self.config_lock = asyncio.Lock()
        self.config_file = filename
        self.valid = False
        data: dict[str, Any] | None = None
        try:
            if (os.stat(self.config_file)[0] & 0x4000) == 0:  # not a directory (littlefs has no other node types)
                with open(self.config_file) as f:
                    try:
                        data = json.load(f)  # parse to json
                        if isinstance(data, dict):  # parsing resulted in a dict
                            self.pr.one("JSON Data in config file", self.config_file, "found.")
                        else:  # generally valid json but not a dict
                            data = None
                            self.pr.wrn("Data in config file", self.config_file, "has wrong format.")
                    except ValueError as e:  # malformed json
                        self.pr.wrn("JSON Data in config file", self.config_file, "is invalid:", e)
            else:  # filename exists but is a directory and cannot be used
                self.pr.err(self.config_file, "exists but is not a file, cannot write!")
                return
        except OSError as e:  # file doesn't exist or can't be opened
            self.pr.wrn("Config file", self.config_file, "not found:", e)

        defaults = schema_dict(cfg_vals)
        if len(defaults) == 0:  # default config contains no values
            self.pr.err(self.config_file, "- Defaults are empty, config is not valid!")
            return

        rewrite = False  # don't write file unless required
        valid_cfg = {}  # create surely valid config
        for key, field in defaults.items():  # iterate through default config
            use_value, default_val = check_cfg_get_default(field)  # read and selfcheck
            if default_val is None:  # invalid config, no default or special-alone value
                self.pr.err(self.config_file, "- Default Key", key, "Error or None, config is not valid!")
                return
            if not use_value:  # special-alone value
                continue  # not used for storage, skip loop iteration
            if data is None:  # no or invalid config file
                new_cfg = default_val  # immediately take default value
            else:  # file exists and is valid
                new_cfg = data.pop(key, None)  # remove all used and known keys from config
                if type_or_range_error(new_cfg, field):  # if new_cfg is None or any other error
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
        except OSError as e:
            self.pr.err("Error writing config", self.config_file, "- config is not valid:", e)
            return

    async def get_dict(self, keys: "list[str]") -> "dict[str, int | float | str | bool | None] | None":
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot read!")
            return None
        async with self.config_lock:
            ret_dict = {}
            self.pr.all(self.config_file, "- Reading config data into dict.")
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    self.pr.err(self.config_file, "- Config parse error!")
                    return None
                for key in keys:
                    ret_dict[key] = data[key]
                return ret_dict
            except (OSError, ValueError, KeyError) as e:  # file errors, malformed json, key errors
                self.pr.err(self.config_file, "- Config read error:", e)
                return None

    async def _get_values(self, keys: "ConfigSchema") -> "list[Any] | None":
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot read!")
            return None
        async with self.config_lock:
            ret_values = []
            self.pr.all(self.config_file, "- Reading config data into list.")
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    self.pr.err(self.config_file, "- Config parse error!")
                    return None
                for key in schema_names(keys):
                    ret_values.append(data[key])
                return ret_values
            except (OSError, ValueError, KeyError) as e:  # file errors, malformed json, key errors
                self.pr.err(self.config_file, "- Config read error:", e)
                return None

    async def get_int_values(self, keys: "ConfigSchema") -> "list[int] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            return [int(v) for v in values]
        except (TypeError, ValueError):
            return None

    async def get_float_values(self, keys: "ConfigSchema") -> "list[float] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            return [float(v) for v in values]
        except (TypeError, ValueError):
            return None

    async def get_str_values(self, keys: "ConfigSchema") -> "list[str] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            return [str(v) for v in values]
        except (TypeError, ValueError):
            return None

    async def get_bool_values(self, keys: "ConfigSchema") -> "list[bool] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        if any(not isinstance(v, bool) for v in values):  # bool(v) never raises, unlike int()/float()/str() - must reject wrong types explicitly
            return None
        return values

    async def write_config(
        self, data: "dict[str, int | float | str | bool | None]", cfg_vals: "ConfigSchema"
    ) -> "tuple[bool, WriteValidity]":
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot write!")
            return False, {}
        async with self.config_lock:
            try:
                with open(self.config_file) as f:
                    conf_data = json.load(f)
                if not isinstance(conf_data, dict):
                    self.pr.err(self.config_file, "- Config parse error!")
                    return False, {}
                changed = False
                defaults = schema_dict(cfg_vals)
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
                    # Validated the same way regardless of storage: the sentinel is always valid if it
                    # matches its own definition (type_or_range_error's check_special bypass), independent
                    # of the ordinary range check, which still applies to any non-sentinel submission.
                    if type_or_range_error(value, defaults[key]):
                        self.pr.err(self.config_file, "- Type / range error in", key, "- skipping!")
                        dict_results[key] = "Invalid"
                        continue
                    if not use_value:
                        dict_results[key] = "Valid"
                        self.pr.evt(self.config_file, "- Key", key, "is valid but not in storage, skipping.")
                        continue  # not used for storage
                    if key not in conf_data:
                        dict_results[key] = "Failed"
                        self.pr.err(self.config_file, "- Key", key, "not found in config file, ignoring!")
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
            except (OSError, ValueError) as e:  # file errors, malformed json
                self.pr.err(self.config_file, "- Error writing config data:", e)
                return False, {}
