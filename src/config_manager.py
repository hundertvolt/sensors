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

`ConfigManager` reads the config file exactly once, at `__init__`, into an in-memory `_cache` dict
- every `get_*`/`write_config` call after that reads/writes `_cache` directly, never re-opening the
file, since a real driver's read path (e.g. asy_bmp3xx_driver.py's per-measurement-cycle
`get_float_values()` call) runs for the device's entire uptime and MicroPython has no async-native
file I/O to make a per-call re-read non-blocking. `write_config` still does a real (rare,
manual-interaction-driven) file write, and only commits its changes into `_cache` *after* that
write succeeds - so a failed write can't desync the two. Deliberate consequence: unlike the old
always-re-read design, a read no longer detects the config file being deleted/corrupted out-of-band
after a valid `__init__` - `_cache` is the sole source of truth for reads, and a subsequent write
silently repairs (overwrites) an externally-corrupted file from `_cache` rather than detecting and
failing on it. Acceptable here because this device is the file's only writer and manual-interaction
writes are rare - see BACKLOG.md for the full reasoning. `_get_values`/`get_dict` no longer need
`config_lock` at all: with no file I/O and no `await` in their bodies, there's no point at which
another coroutine could observe a `_cache` mutation half-applied - only `write_config` still needs
the lock, to serialize its own file write against a concurrent `write_config` call.
"""

import asyncio
import json
import os

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Literal, NamedTuple, TypeVar

    T = TypeVar("T", int, float, str)

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
        self._cache: dict[str, int | float | str | bool | None] = {}
        data: dict[str, Any] | None = None
        try:
            if (os.stat(self.config_file)[0] & 0x4000) == 0:  # not a directory: 0x4000 is MP_S_IFDIR, MicroPython's
                # own port-standardized stat-mode bit (extmod/vfs.h, confirmed current as of v1.28.0), applied
                # uniformly across VFS backends including littlefs - not a POSIX-convention guess.
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
        except (OSError, TypeError) as e:  # file doesn't exist/can't be opened, or filename isn't a string
            self.pr.wrn("Config file", self.config_file, "not found:", e)

        defaults = schema_dict(cfg_vals)
        if len(defaults) == 0:  # default config contains no values
            self.pr.err(self.config_file, "- Defaults are empty, config is not valid!")
            return

        rewrite = False  # don't write file unless required
        valid_cfg: dict[str, int | float | str | bool | None] = {}  # create surely valid config
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
            self._cache = valid_cfg
            self.valid = True
            self.pr.one("Valid configuration data found in", self.config_file, "- config is ready.")
            return

        if len(valid_cfg) == 0:
            self.pr.wrn(self.config_file, "- Default config valid but no storage values!")

        self.pr.one(self.config_file, "- Writing configuration file!")
        try:
            with open(self.config_file, "w") as f:
                json.dump(valid_cfg, f)
            self._cache = valid_cfg
            self.valid = True
            self.pr.one("Default data was written in", self.config_file, "- config is ready.")
            return
        except (OSError, TypeError) as e:  # write failed, or filename isn't a string
            self.pr.err("Error writing config", self.config_file, "- config is not valid:", e)
            return

    async def get_dict(self, keys: "list[str]") -> "dict[str, int | float | str | bool | None] | None":
        # Reads _cache directly (see module docstring) - no file I/O, no lock: nothing else ever
        # mutates _cache without also completing synchronously (write_config never awaits between
        # updating _cache and releasing config_lock), so there's no partial state a concurrent
        # caller could observe here even without holding the lock.
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot read!")
            return None
        self.pr.all(self.config_file, "- Reading config data into dict.")
        try:
            return {key: self._cache[key] for key in keys}
        except (KeyError, TypeError) as e:  # unknown key, or a non-iterable/malformed keys param
            self.pr.err(self.config_file, "- Config read error:", e)
            return None

    async def _get_values(self, keys: "ConfigSchema") -> "list[Any] | None":
        if not self.valid:
            self.pr.err(self.config_file, "- Config is not valid, cannot read!")
            return None
        self.pr.all(self.config_file, "- Reading config data into list.")
        try:
            return [self._cache[key] for key in schema_names(keys)]
        except KeyError as e:  # unknown key
            self.pr.err(self.config_file, "- Config read error:", e)
            return None

    async def _get_converted_values(self, keys: "ConfigSchema", converter: "Callable[[Any], T]") -> "list[T] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            return [converter(v) for v in values]
        except (TypeError, ValueError):
            return None

    async def get_int_values(self, keys: "ConfigSchema") -> "list[int] | None":
        return await self._get_converted_values(keys, int)

    async def get_float_values(self, keys: "ConfigSchema") -> "list[float] | None":
        return await self._get_converted_values(keys, float)

    async def get_str_values(self, keys: "ConfigSchema") -> "list[str] | None":
        return await self._get_converted_values(keys, str)

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
                new_cache = dict(self._cache)  # working copy - only committed to _cache after a successful write
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
                    if key not in new_cache:
                        dict_results[key] = "Failed"
                        self.pr.err(self.config_file, "- Key", key, "not found in config file, ignoring!")
                        continue
                    if new_cache[key] != value:
                        new_cache[key] = value
                        dict_results[key] = "Valid"
                        changed = True
                    else:
                        dict_results[key] = "Unchanged"
                if not changed:
                    self.pr.evt(self.config_file, "- No new / unchanged config data.")
                    return True, dict_results
                with open(self.config_file, "w") as f:
                    json.dump(new_cache, f)
                self._cache = new_cache  # only commit once the write has actually succeeded
                self.pr.evt(self.config_file, "- Config data was written.")
                return True, dict_results
            except (OSError, ValueError, AttributeError) as e:  # file errors, malformed json, non-dict data param
                self.pr.err(self.config_file, "- Error writing config data:", e)
                return False, {}
