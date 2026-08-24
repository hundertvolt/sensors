"""Per-sensor JSON config storage - each sensor gets its own `config_<name>.cfg` file (see
base_classes.py's SensorReaderConfig), validated against a schema of `_VAL_*` `const()` tuples: (name, type, default, min, max, special).
Every public function/method returns a documented "invalid" sentinel, never raises.
"""
# `__init__` only stashes constructor args (cheap, synchronous); `ConfigManager` reads the file
# once, in `async def setup()`, into `self._cache` - every later `get_*`/`write_config` call
# reads/writes `_cache` directly (see CLAUDE.md for the cache-vs-external-corruption trade-off this
# implies).

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

    # One schema field: (name, type, def, min, max, special) - see module docstring. "special" is
    # a single bypass value (exact-match exception to min/max, e.g. SCD30's AmbPres=0) or a tuple
    # of allowed values (a discrete set, e.g. BMP3xx's OSR/IIR settings - see type_or_range_error).
    FieldSchema = tuple[
        str,
        str,
        "int | float | str | bool | None",
        "int | float | None",
        "int | float | None",
        "int | float | str | tuple[int, ...] | tuple[float, ...] | tuple[str, ...] | None",
    ]
    ConfigSchema = tuple[FieldSchema, ...]

from print_log import PrintLogHistory


def _special_bypass(check_val: "Any", val_special: "Any", scalar_type: type, check_special: bool) -> "bool | None":
    # Shared by every non-bool branch of type_or_range_error: val_special is a single scalar or a
    # tuple/list of scalars (see ConfigSchema above). Returns True/False to short-circuit the
    # caller (malformed special, or a valid bypass match), or None to fall to the range check.
    if type(val_special) in (tuple, list):
        if any(type(v) is not scalar_type for v in val_special):
            return True  # malformed set (wrong-typed element) - reject regardless of check_val
        if check_special and check_val in val_special:
            return False
        return None
    if type(val_special) is not scalar_type:
        return True  # malformed scalar special - reject regardless of check_val
    if check_special and check_val == val_special:
        return False
    return None


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


def make_dict(
    nt: "NamedTuple", fields: "tuple[str, ...]"
) -> "dict[str, dict[str, int | float | str | None]]":  # {type_name: {field: value}} - fields is the same
    # literal tuple the caller's own namedtuple(name, fields) was built from (rp2's build ROM level
    # is MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES, one level below the MICROPY_CONFIG_ROM_LEVEL_
    # EVERYTHING that _asdict()/_fields require - confirmed against ports/rp2/mpconfigport.h - so
    # neither is safe to rely on here).
    try:
        name = type(nt).__name__
    except Exception:
        return {}
    try:
        return {name: {field: getattr(nt, field) for field in fields}}
    except Exception:
        return {name: {field: None for field in fields}}


def coerce_numeric(check_val: "Any", scalar_type: type) -> "tuple[bool, Any]":
    # Accept only what's exactly representable as scalar_type, in either direction (see
    # SPECIFICATION.md Part A.8): int -> float is a blanket accept (every int is exactly
    # representable as a float); float -> int is accepted only when the value carries no
    # fractional part - rejected otherwise, never truncated/rounded, so a fat-fingered "12.5"
    # can't silently become a stored "12". bool is deliberately excluded from both directions even
    # though it's an int subclass in Python/MicroPython - type() (not isinstance()) already keeps
    # it out of every branch below, same as the pre-coercion strict check did.
    #
    # Public (no leading underscore) and reused outside this module: sensortask_wozi.py's
    # lightCmdLED dispatch (dispatch-only, not schema-backed - no FieldSchema record to hand
    # type_or_range_error()) calls this directly for its r/g/b/t coercion instead of duplicating
    # the same int<->float acceptance logic a second time.
    if type(check_val) is scalar_type:
        return True, check_val
    if scalar_type is float and type(check_val) is int:
        return True, float(check_val)
    if scalar_type is int and type(check_val) is float:
        try:
            as_int = int(check_val)  # MicroPython/CPython alike: ValueError for NaN, OverflowError
        except (OverflowError, ValueError):  # for +-inf (py/objint.c's mp_obj_new_int_from_float)
            return False, check_val
        if float(as_int) == check_val:  # exact round-trip - no fractional part was discarded
            return True, as_int
    return False, check_val


def type_or_range_error(
    check_val: "Any", field: "FieldSchema", check_special: bool = True
) -> "tuple[bool, Any]":  # (True, check_val) if check_val doesn't satisfy field's own type/min/
    # max(/special) schema entry (coercion included) - (False, coerced_val) otherwise, where
    # coerced_val is check_val itself unless an int<->float coercion above actually applied.
    try:
        _name, val_type, _def, val_min, val_max, val_special = field

        if val_type == "int":  # check for int (coercing an integral float) and bounds
            ok, check_val = coerce_numeric(check_val, int)
            if not ok:
                return True, check_val
            if val_special is not None:
                bypass = _special_bypass(check_val, val_special, int, check_special)
                if bypass is not None:
                    return bypass, check_val
            if type(val_max) is int and type(val_min) is int and val_min <= check_val <= val_max:
                return False, check_val
        elif val_type == "float":  # check for float (coercing an int) and bounds
            ok, check_val = coerce_numeric(check_val, float)
            if not ok:
                return True, check_val
            if val_special is not None:
                bypass = _special_bypass(check_val, val_special, float, check_special)
                if bypass is not None:
                    return bypass, check_val
            if type(val_max) is float and type(val_min) is float and val_min <= check_val <= val_max:
                return False, check_val
        elif val_type == "str":  # check for str and length bounds
            if type(check_val) is not str:
                return True, check_val
            if val_special is not None:
                bypass = _special_bypass(check_val, val_special, str, check_special)
                if bypass is not None:
                    return bypass, check_val
            if type(val_max) is int and type(val_min) is int and val_min <= len(check_val) <= val_max:
                return False, check_val
        elif val_type == "bool":  # check for bool
            if type(check_val) is bool:
                return False, check_val
    except Exception:
        pass
    return True, check_val


def check_cfg_get_default(
    field: "FieldSchema",
) -> "tuple[bool, int | float | str | bool | None]":
    try:  # returns flag if value is used for storage and if the default, if valid
        _name, _type, def_val, _min, _max, special_val = field  # wrong length/shape -> ValueError, caught below
        use_value = True
        # special-alone field: def is None but special has a scalar value -> use special as a
        # non-stored mock default (check_special=True accepts it via the special-equality
        # shortcut). A tuple/list special has no scalar to substitute - flagged as malformed.
        if def_val is None and special_val is not None and not isinstance(special_val, (tuple, list)):
            def_val = special_val
            use_value = False
        is_error, coerced_val = type_or_range_error(def_val, field, check_special=True)
        if is_error:
            return True, None  # self-check of defaults
        return use_value, coerced_val
    except Exception:  # malformed field record
        return True, None


if TYPE_CHECKING:
    WriteValidity = dict[str, Literal["Invalid", "Unchanged", "Valid", "Failed"]]


class ConfigManager:
    def __init__(self, filename: str, cfg_vals: "ConfigSchema", name: str) -> None:
        self.pr = PrintLogHistory(name="CFGMGR_" + name)
        self.name = "CFGMGR_" + name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        self.config_lock = asyncio.Lock()
        self.config_file = filename
        self.cfg_vals = cfg_vals
        self.valid = False
        self._cache: dict[str, int | float | str | bool | None] = {}

    async def _get_values(self, keys: "ConfigSchema") -> "list[Any] | None":
        if not self.valid:
            await self.pr.err_s(self.config_file, "- Config is not valid, cannot read!", errno=5)
            return None
        self.pr.all(self.config_file, "- Reading config data into list.")
        try:
            return [self._cache[key] for key in schema_names(keys)]
        except KeyError as e:  # unknown key
            await self.pr.err_s(self.config_file, "- Config read error:", e, errno=6)
            return None

    async def _get_converted_values(self, keys: "ConfigSchema", converter: "Callable[[Any], T]") -> "list[T] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            return [converter(v) for v in values]
        except (TypeError, ValueError):
            return None

    async def get_error_counter(self) -> "dict[str, dict[str, int | list[int] | list[str]]]":
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def get_dict(self, keys: "list[str]") -> "dict[str, int | float | str | bool | None] | None":
        # Reads _cache directly - no lock needed (write_config never awaits mid-mutation, so no
        # partial state is observable here; see module docstring for the cache design).
        if not self.valid:
            await self.pr.err_s(self.config_file, "- Config is not valid, cannot read!", errno=7)
            return None
        self.pr.all(self.config_file, "- Reading config data into dict.")
        try:
            return {key: self._cache[key] for key in keys}
        except (KeyError, TypeError) as e:  # unknown key, or a non-iterable/malformed keys param
            await self.pr.err_s(self.config_file, "- Config read error:", e, errno=8)
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
            await self.pr.err_s(self.config_file, "- Config is not valid, cannot write!", errno=9)
            return False, {}
        async with self.config_lock:
            try:
                new_cache = dict(self._cache)  # working copy - only committed to _cache after a successful write
                changed = False
                defaults = schema_dict(cfg_vals)
                dict_results: WriteValidity = {}
                for key, value in data.items():
                    if key not in defaults:
                        await self.pr.err_s(self.config_file, "- Key", key, "not found, skipping!", errno=10)
                        dict_results[key] = "Invalid"
                        continue
                    use_value, default_val = check_cfg_get_default(defaults[key])
                    if default_val is None:
                        await self.pr.err_s(self.config_file, "- Default Key", key, "Error or None, no data written!", errno=11)
                        return False, {}
                    # Sentinel values are validated against their own definition (check_special bypass);
                    # non-sentinel values still go through the ordinary range check.
                    is_error, coerced_value = type_or_range_error(value, defaults[key])
                    if is_error:
                        await self.pr.err_s(self.config_file, "- Type / range error in", key, "- skipping!", errno=12)
                        dict_results[key] = "Invalid"
                        continue
                    value = coerced_value  # use the coerced (e.g. int->float) shape for storage below
                    if not use_value:
                        dict_results[key] = "Valid"
                        self.pr.evt(self.config_file, "- Key", key, "is valid but not in storage, skipping.")
                        continue  # not used for storage
                    if key not in new_cache:
                        dict_results[key] = "Failed"
                        await self.pr.err_s(self.config_file, "- Key", key, "not found in config file, ignoring!", errno=13)
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
            except (MemoryError, OSError, ValueError, AttributeError) as e:  # file errors, a non-dict
                # `data` param (AttributeError on .items()), or json.dump() exhausting the heap;
                # ValueError is defensive since dump() no longer reads/reparses json here.
                await self.pr.err_s(self.config_file, "- Error writing config data:", e, errno=14)
                return False, {}

    async def setup(self) -> None:
        data: dict[str, Any] | None = None
        try:
            if (os.stat(self.config_file)[0] & 0x4000) == 0:  # 0x4000 = MP_S_IFDIR, MicroPython's own
                # stat-mode bit (extmod/vfs.h), uniform across VFS backends incl. littlefs.
                with open(self.config_file) as f:
                    try:
                        data = json.load(f)  # parse to json
                        if isinstance(data, dict):  # parsing resulted in a dict
                            self.pr.one("JSON Data in config file", self.config_file, "found.")
                        else:  # generally valid json but not a dict
                            data = None
                            await self.pr.wrn_s("Data in config file", self.config_file, "has wrong format.", wrnno=1)
                    except ValueError as e:  # malformed json
                        await self.pr.wrn_s("JSON Data in config file", self.config_file, "is invalid:", e, wrnno=2)
            else:  # filename exists but is a directory and cannot be used
                await self.pr.err_s(self.config_file, "exists but is not a file, cannot write!", errno=1)
                return
        except (MemoryError, OSError, TypeError) as e:  # missing/unreadable file, bad filename type,
            # or json.load() exhausting the heap on a huge/corrupt file - same "degrade, don't
            # propagate" treatment as the other two causes.
            await self.pr.wrn_s("Config file", self.config_file, "not found:", e, wrnno=3)

        defaults = schema_dict(self.cfg_vals)
        if len(defaults) == 0:  # default config contains no values
            await self.pr.err_s(self.config_file, "- Defaults are empty, config is not valid!", errno=2)
            return

        rewrite = False  # don't write file unless required
        valid_cfg: dict[str, int | float | str | bool | None] = {}  # create surely valid config
        for key, field in defaults.items():  # iterate through default config
            use_value, default_val = check_cfg_get_default(field)  # read and selfcheck
            if default_val is None:  # invalid config, no default or special-alone value
                await self.pr.err_s(self.config_file, "- Default Key", key, "Error or None, config is not valid!", errno=3)
                return
            if not use_value:  # special-alone value
                continue  # not used for storage, skip loop iteration
            if data is None:  # no or invalid config file
                new_cfg = default_val  # immediately take default value
            else:  # file exists and is valid
                new_cfg = data.pop(key, None)  # remove all used and known keys from config
                is_error, coerced_cfg = type_or_range_error(new_cfg, field)  # new_cfg=None or any other error -> is_error
                if is_error:
                    rewrite = True
                    new_cfg = default_val
                    await self.pr.wrn_s(self.config_file, "- Key", key, "has error or is missing, using default!", wrnno=4)
                else:
                    if type(coerced_cfg) is not type(new_cfg):  # e.g. a hand-edited file's "5" for a
                        rewrite = True  # float field - persist the coerced shape back to disk too.
                        # (`!=` alone would miss this: 5 != 5.0 is False in Python despite the type
                        # differing - type() is the only reliable signal that coercion actually fired.)
                    new_cfg = coerced_cfg
            valid_cfg[key] = new_cfg
        if data is None:  # no file -> always create
            rewrite = True
        elif len(data) != 0:  # unexpected keys remaining from existing file
            rewrite = True
            await self.pr.wrn_s(self.config_file, "- Removed invalid keys from config file!", wrnno=5)

        if not rewrite:
            self._cache = valid_cfg
            self.valid = True
            self.pr.one("Valid configuration data found in", self.config_file, "- config is ready.")
            return

        if len(valid_cfg) == 0:
            await self.pr.wrn_s(self.config_file, "- Default config valid but no storage values!", wrnno=6)

        self.pr.one(self.config_file, "- Writing configuration file!")
        try:
            with open(self.config_file, "w") as f:
                json.dump(valid_cfg, f)
            self._cache = valid_cfg
            self.valid = True
            self.pr.one("Default data was written in", self.config_file, "- config is ready.")
            return
        except (MemoryError, OSError, TypeError) as e:  # write failed, filename isn't a string, or
            # json.dump() exhausts the heap serializing valid_cfg
            await self.pr.err_s("Error writing config", self.config_file, "- config is not valid:", e, errno=4)
            return
