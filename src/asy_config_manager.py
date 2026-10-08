"""Per-sensor JSON config storage - each sensor gets its own `config_<name>.cfg` file (see asy_base_classes.py's SensorReaderConfig), validated against a schema of `_VAL_*` `const()` tuples: (name, type, default, min, max, special).
Every public function/method returns a documented "invalid" sentinel, never raises (for typed inputs; a malformed schema fails the static schema check).
"""
# `__init__` only stashes constructor args (cheap, synchronous); the file is read once, in
# `async def setup()`, into `self._cache`, and every later `get_*`/`write_config` works on `_cache`
# directly - SPECIFICATION.md A.4 has the cache-vs-external-corruption trade-off this implies.

import asyncio
import errno
import json
import os

from micropython import const

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Final, Literal, NamedTuple, TypeVar

    from asy_base_classes import JsonMapping
    from asy_print_log import ErrorLog, LogConfig, PrintLogHistory

    T = TypeVar("T", int, float, str, bool)

    # The project's canonical config/JSON scalar: every schema default, cached value, REST-supplied
    # field value and _push_* dispatch payload is one of these (SPECIFICATION.md Part C.5.2 / G.2).
    CfgValue = int | float | str | bool | None
    # A field's "special" slot as _special_bypass() accepts it: one bypass scalar (exact-match
    # exception to min/max, e.g. SCD30's AmbPres=0) or a discrete allowed-value set. Schema authors
    # write const()-folded tuples (FieldSchema below), but a plain list works just as well.
    CfgSpecial = int | float | str | tuple[int, ...] | tuple[float, ...] | tuple[str, ...] | list[int] | list[float] | list[str] | None

    # One schema field: (name, type, def, min, max, special) - see module docstring.
    FieldSchema = tuple[
        str,
        str,
        CfgValue,
        "int | float | None",
        "int | float | None",
        "int | float | str | tuple[int, ...] | tuple[float, ...] | tuple[str, ...] | None",
    ]
    ConfigSchema = tuple[FieldSchema, ...]

    # A driver's generator-facing metadata is deliberately not a Python value at all - it lives in
    # `# @wiring`/`# @value-wiring`/`# @limits` comment tags, so nothing the firmware reads becomes
    # frozen bytecode just to serve the generator (SPECIFICATION.md Part L.6.4).

from asy_print_log import DEFAULT_LOG, make_logger

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and CFGMGR's band.
_ERR_ALLOC = const(20)
_ERR_BAD_ARG = const(21)
_ERR_UNEXPECTED = const(23)
_ERR_CONTRACT = const(24)
_ERR_CFG_PATH_IS_DIR = const(30)
_ERR_CFG_NO_DEFAULTS = const(31)
_ERR_CFG_BAD_DEFAULT = const(32)
_ERR_CFG_FILE_WRITE = const(33)
_ERR_CFG_NOT_VALID = const(34)
_WRN_STORED_DEFAULT = const(10)
_WRN_CFG_FILE_NOT_OBJECT = const(20)
_WRN_CFG_FILE_JSON = const(21)
_WRN_CFG_FILE_UNREADABLE = const(22)
_WRN_CFG_KEYS_REMOVED = const(23)


def _as_bool(v: "CfgValue") -> bool | None:
    return v if type(v) is bool else None


def _as_str(v: "CfgValue") -> str | None:
    return v if type(v) is str else None


def _coerce_float(check_val: object) -> float | None:
    # Accepts only what is exactly a float (SPECIFICATION.md Part A.8): a float, or an int; bool is
    # excluded both ways by exact type (on MicroPython `bool` is not an `int` subclass). None refuses.
    if type(check_val) is float:
        return check_val
    if type(check_val) is int:
        # No exact-round-trip check on this direction, unlike _coerce_int(): an accepted gap (owner, 2026-08-24). A
        # value large enough to lose precision (past 2**24 on the real single-precision build, Part A.8) is
        # outside every float field's bounds: none passes 2**24 (tests_scripts/test_config_schemas.py).
        return float(check_val)
    return None


def _coerce_int(check_val: object) -> int | None:
    # Accepts only what is exactly an int (SPECIFICATION.md Part A.8): an int, or a float without a fractional
    # part, never truncated; bool is excluded both ways by exact type (on MicroPython `bool` is not an `int`
    # subclass). None refuses.
    if type(check_val) is int:
        return check_val
    if type(check_val) is float:
        try:
            as_int = int(check_val)  # MicroPython/CPython alike: ValueError for NaN, OverflowError
        except (OverflowError, ValueError):  # for +-inf (py/objint.c's mp_obj_new_int_from_float)
            return None
        if float(as_int) == check_val:  # exact round-trip - no fractional part was discarded
            return as_int
    return None


def _special_bypass(check_val: object, val_special: "CfgSpecial", scalar_type: type, *, check_special: bool) -> bool | None:
    # Shared by every non-bool branch of the validators: val_special is a single scalar or a
    # tuple/list of scalars (see CfgSpecial above). Returns True/False to short-circuit the
    # caller (malformed special, or a valid bypass match), or None to fall to the range check.
    if type(val_special) is tuple or type(val_special) is list:
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


def _stored_float(v: "CfgValue") -> "CfgValue":
    # The form a float takes back from the file (rp2 floats are single precision with an approximate repr):
    # compared and staged in it, so a repeat PUT after a reboot answers "Unchanged". Settles in one step only
    # while idempotent on rp2, which an on-device round-trip script proves; else compare the serialised text.
    stored: CfgValue = json.loads(json.dumps(v))
    return stored


def check_cfg_get_default(
    field: "FieldSchema",
) -> "tuple[bool, CfgValue]":
    # returns flag if value is used for storage and if the default, if valid
    _name, _type, def_val, _min, _max, special_val = field
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


# Per-kind validators: a caller that needs an int or a float gets one from the type, never by narrowing
# (SPECIFICATION.md C.10); the webserver's dispatch-only fields (asy_webserver_service.py) are checked here too.
def checked_float(check_val: object, field: "FieldSchema", *, check_special: bool = True) -> float | None:
    value = _coerce_float(check_val)
    if value is None:
        return None
    _name, _type, _def, val_min, val_max, val_special = field
    if val_special is not None:
        bypass = _special_bypass(value, val_special, float, check_special=check_special)
        if bypass is not None:
            return None if bypass else value
    if type(val_max) is float and type(val_min) is float and val_min <= value <= val_max:
        return value
    return None


def checked_int(check_val: object, field: "FieldSchema", *, check_special: bool = True) -> int | None:
    value = _coerce_int(check_val)
    if value is None:
        return None
    _name, _type, _def, val_min, val_max, val_special = field
    if val_special is not None:
        bypass = _special_bypass(value, val_special, int, check_special=check_special)
        if bypass is not None:
            return None if bypass else value
    if type(val_max) is int and type(val_min) is int and val_min <= value <= val_max:
        return value
    return None


def checked_numeric(check_val: object, field: "FieldSchema", *, check_special: bool = True) -> int | float | None:
    # Dispatches on the field's kind; any kind other than int or float refuses.
    if field[1] == "int":
        return checked_int(check_val, field, check_special=check_special)
    if field[1] == "float":
        return checked_float(check_val, field, check_special=check_special)
    return None


def compare_before_write(
    data: object,
    cfg_vals: "ConfigSchema",
    current: "dict[str, CfgValue]",
    *,
    always: tuple[str, ...] = (),
    resolution: "dict[str, Callable[[CfgValue], CfgValue]] | None" = None,
) -> "tuple[dict[str, CfgValue], WriteValidity] | None":
    # The shared compare-before-write primitive (SPECIFICATION.md Part G.2): per key of data, in its order,
    # the outcome and, for a "Valid" key, the coerced value to write. Logs nothing; the caller writes and
    # logs. None for a non-dict data; an `always` key is a command, never compared and never "Unchanged".
    if type(data) is not dict:
        return None
    fields = schema_dict(cfg_vals)
    write: dict[str, CfgValue] = {}
    results: WriteValidity = {}
    for key, value in data.items():
        field = fields.get(key)
        if field is None:
            results[key] = INVALID
            continue
        is_error, coerced = type_or_range_error(value, field)
        if is_error:
            results[key] = INVALID
            continue
        if key in always:
            write[key] = coerced
            results[key] = VALID
            continue
        if key not in current:
            results[key] = FAILED
            continue
        res = None if resolution is None else resolution.get(key)
        stored = current[key]
        if (coerced != stored) if res is None else (res(coerced) != res(stored)):
            write[key] = coerced
            results[key] = VALID
        else:
            results[key] = UNCHANGED
    return write, results


def config_filename(cfg_path: str, name: str) -> str:
    # The one builder of a module's config file name: `config_<name>.cfg` under cfg_path, name already
    # instance_name()-resolved (SPECIFICATION.md Part C.14).
    return cfg_path + "config_" + name + ".cfg"


def instance_name(base_name: str, name_ext: str) -> str:
    # Uniform per-instance naming (SPECIFICATION.md Part C.14): an empty name_ext reproduces
    # base_name unchanged, a non-empty one appends "_" + name_ext across REST keys, config filenames
    # and error-log keys at once. Collision detection over a device's instance list is buildgen's.
    if not name_ext:
        return base_name
    return base_name + "_" + name_ext


def make_dict(
    nt: "NamedTuple", fields: tuple[str, ...], name: str | None = None,
) -> dict[str, dict[str, int | float | str | None]]:  # {type_name: {field: value}} - fields is the same
    # literal tuple the caller's namedtuple(name, fields) was built from: rp2 builds at
    # MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES, one level below the EVERYTHING that _asdict()/_fields
    # need (confirmed against ports/rp2/mpconfigport.h), so neither is safe to rely on here.

    # name=None introspects the namedtuple's own type name, which every single-instance caller
    # relies on. A caller that can have more than one instance passes its resolved self.name: the
    # namedtuple TYPE is fixed at class-definition time and cannot vary per instance (Part C.14).
    if name is None:
        name = type(nt).__name__
    return {name: {field: getattr(nt, field) for field in fields}}


def name_cfg(schema: "ConfigSchema") -> str:  # single-field convenience wrapper around schema_names
    names = schema_names(schema)
    if len(names) == 1:
        return names[0]
    return ""


def schema_dict(schema: "ConfigSchema") -> "dict[str, FieldSchema]":  # {field_name: field_record}; duplicate names keep the last occurrence
    return {field[0]: field for field in schema}


def schema_names(schema: "ConfigSchema") -> list[str]:  # field names, in schema order (duplicates preserved)
    return [field[0] for field in schema]


if TYPE_CHECKING:
    WriteValidity = dict[str, Literal["Invalid", "Unchanged", "Valid", "Failed"]]

# The four per-field result words (SPECIFICATION.md G.2): plain module attributes, never const(), so every
# module imports them by name; mypy reads each as its Literal, which WriteValidity takes.
VALID: "Final" = "Valid"
UNCHANGED: "Final" = "Unchanged"
INVALID: "Final" = "Invalid"
FAILED: "Final" = "Failed"


def type_or_range_error(
    check_val: object, field: "FieldSchema", *, check_special: bool = True,
) -> "tuple[bool, CfgValue]":  # (True, None) if check_val fails field's own type/min/max(/special) entry,
    # (False, the accepted value) otherwise - coerced where int<->float coercion applied. The
    # schema-generic form: a caller that needs a number calls checked_int()/checked_float().
    val_type = field[1]
    if val_type in ("int", "float"):
        value = checked_numeric(check_val, field, check_special=check_special)
        return (True, None) if value is None else (False, value)
    _name, _type, _def, val_min, val_max, val_special = field
    if val_type == "str":  # check for str and length bounds
        if type(check_val) is not str:
            return True, None
        if val_special is not None:
            bypass = _special_bypass(check_val, val_special, str, check_special=check_special)
            if bypass is not None:
                return (True, None) if bypass else (False, check_val)
        if type(val_max) is int and type(val_min) is int and val_min <= len(check_val) <= val_max:
            return False, check_val
    elif val_type == "bool" and type(check_val) is bool:  # check for bool
        return False, check_val
    return True, None


class ConfigManager:
    def __init__(self, filename: str, cfg_vals: "ConfigSchema", name: str, log: "LogConfig" = DEFAULT_LOG) -> None:
        self.name = "CFGMGR_" + name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        # Inherits its owning module's logging config - FRAM-backed when the module is (the implicit FRAM-wiring
        # rule, SPECIFICATION.md A.7) - so its failure history survives a reboot like the module's own.
        self.pr: PrintLogHistory = make_logger(log, self.name)
        self._config_lock = asyncio.Lock()  # serialises the config file and its staged snapshot
        self._config_file = filename
        self._cfg_vals = cfg_vals
        self.valid = False
        self.writable = True  # False once setup() met a file it could not read: never overwritten this boot
        self.faulted = False  # setup() met a file it could not read or a damaged one (repaired, still listed)
        self.absent_at_boot = False  # setup() found no file and wrote the defaults (a fresh filesystem)
        self.unpersisted = False  # the latest file write failed: the store runs on values the flash lacks
        self.module_name = name  # the module name a config-fault report lists
        self._closed = False  # close_writes() before a commanded reset; one-way
        self._cache: dict[str, CfgValue] = {}
        # Staging slot for write_config()'s deferred flash write (SPECIFICATION.md Part F.2) - not
        # yet on disk, but the read path serves it first so a GET reflects a just-accepted PUT
        # immediately rather than waiting for the actual flash write to complete.
        self._staged: dict[str, CfgValue] | None = None
        self._pending_flush: asyncio.Task[None] | None = None
        self._commit_ready = asyncio.Event()  # cleared while a deferred snapshot waits for its commit()
        self._commit_ready.set()

    async def _get_typed_values(self, keys: "ConfigSchema", coerce: "Callable[[CfgValue], T | None]") -> "list[T] | None":
        # Each stored value through the getter's own exact-type coercer, all-or-nothing: a refusal is a
        # stored value of the wrong type, persisted once, and the caller gets None.
        values = await self._get_values(keys)
        if values is None:
            return None
        names = schema_names(keys)
        typed: list[T] = []
        for i, value in enumerate(values):
            checked = coerce(value)
            if checked is None:
                await self.pr.err_s(self._config_file, "- stored value has the wrong type:", names[i], errno=_ERR_CONTRACT)
                return None
            typed.append(checked)
        return typed

    async def _get_values(self, keys: "ConfigSchema") -> "list[CfgValue] | None":
        if not self.valid:
            await self.pr.err_s(self._config_file, "- Config is not valid, cannot read!", errno=_ERR_CFG_NOT_VALID)
            return None
        self.pr.all(self._config_file, "- Reading config data into list.")
        try:
            current = self._current()
            return [current[key] for key in schema_names(keys)]
        except KeyError as e:  # unknown key
            await self.pr.err_s(self._config_file, "- Config read error:", e, errno=_ERR_CONTRACT)
            return None

    def _closed_for_reset(self) -> bool:
        # write_config()'s check, before its lock and again under it: a closed store refuses every write.
        if self._closed:
            self.pr.evt(self._config_file, "- writes closed for reset")
        return self._closed

    def _current(self) -> "dict[str, CfgValue]":
        # write_config() always stages a full snapshot (dict(self._cache) plus the changed keys),
        # never a partial one, so a plain swap - not a per-key merge - is correct here: read-your-
        # write for a value not yet flushed, exactly as it would read once the flush completes.
        return self._staged if self._staged is not None else self._cache

    async def _flush_staged(self, staged: "dict[str, CfgValue]") -> None:
        # The still-synchronous, uninterruptible flash write, decoupled from whatever request triggered it;
        # a deferred snapshot first waits for its commit(). It re-acquires write_config()'s own lock, so at
        # most one write is in flight per ConfigManager.
        try:
            await self._commit_ready.wait()
            async with self._config_lock:
                if self._staged is not staged:
                    # A newer snapshot was staged while this one waited for its commit or the lock: writing this one
                    # would regress a replaced value (PrintLogHistoryStore._write() applies the same rule).
                    return
                try:
                    if staged != self._cache:  # equal: the file already holds it, nothing to write
                        text = json.dumps(staged)  # serialised before the open: a failure leaves the file intact
                        with open(self._config_file, "w") as f:
                            f.write(text)
                        self.unpersisted = False
                        self.pr.evt(self._config_file, "- Config data was written.")
                except (MemoryError, OSError, ValueError) as e:  # file errors, or the serialisation
                    # exhausting the heap: logged, never re-raised, and never retried here.
                    self.unpersisted = True
                    await self.pr.err_s(self._config_file, "- Error writing config data, running unpersisted:", e, errno=_ERR_CFG_FILE_WRITE)
                finally:
                    # The validated value stays in effect whether or not the write landed: its push
                    # already reached the module, and only persistence failed (SPECIFICATION.md C.7.3).
                    self._cache = staged
                    if self._staged is staged:  # nothing newer staged while this flush was running
                        self._staged = None
                    if self._pending_flush is asyncio.current_task():
                        self._pending_flush = None
        except Exception as e:  # an unsupervised task's top: its end is persisted, never left unretrieved
            self.unpersisted = True  # the finally above already made the unwritten snapshot the cache
            await self.pr.err_s(self._config_file, "- flush task failed:", e, errno=_ERR_UNEXPECTED)

    async def get_bool_values(self, keys: "ConfigSchema") -> list[bool] | None:
        return await self._get_typed_values(keys, _as_bool)

    async def get_dict(self, keys: list[str]) -> "dict[str, CfgValue] | None":
        # Reads _cache, or _staged when a write_config() is between staging and its flush landing
        # (read-your-write). No lock needed: neither write_config() nor _flush_staged() awaits
        # mid-mutation of the field this reads, so no partial state is observable.
        if not self.valid:
            await self.pr.err_s(self._config_file, "- Config is not valid, cannot read!", errno=_ERR_CFG_NOT_VALID)
            return None
        self.pr.all(self._config_file, "- Reading config data into dict.")
        try:
            current = self._current()
            return {key: current[key] for key in keys}
        except KeyError as e:  # unknown key
            await self.pr.err_s(self._config_file, "- Config read error:", e, errno=_ERR_CONTRACT)
            return None

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_float_values(self, keys: "ConfigSchema") -> list[float] | None:
        return await self._get_typed_values(keys, _coerce_float)

    async def get_int_values(self, keys: "ConfigSchema") -> list[int] | None:
        return await self._get_typed_values(keys, _coerce_int)

    async def get_str_values(self, keys: "ConfigSchema") -> list[str] | None:
        return await self._get_typed_values(keys, _as_str)

    def close_writes(self) -> None:
        # Before a commanded reset: every later write_config() is refused, so nothing new reaches the flash
        # between the last flush_pending() and the reset. One-way.
        self._closed = True

    def commit(self) -> None:
        # Releases a deferred write_config()'s flush (the caller's pushes have ended).
        self._commit_ready.set()

    async def delete_file(self) -> bool:
        # Reset to defaults (owner, 2026-09-30): deletes the file unread, readable or not (owner, 2026-10-01);
        # after the reboot each file is written once with its defaults. The SCD30's chip settings stay in its own NVM.
        self.close_writes()
        async with self._config_lock:
            failure: OSError | None = None
            for _attempt in range(2):  # one retry
                try:
                    os.remove(self._config_file)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        return True
                    failure = e
                else:
                    self.pr.evt(self._config_file, "- deleted, written with the defaults after the reboot")
                    return True
            self.pr.err(self._config_file, "- could not be deleted:", failure)
            return False

    async def flush_pending(self) -> None:
        # Releases a deferred flush, then awaits the latest flush task read under the lock, so a write_config()
        # that held the lock has finished staging first; an earlier, superseded task no-ops by its identity check.
        self._commit_ready.set()
        async with self._config_lock:
            pending = self._pending_flush
        if pending is not None:
            await pending

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def setup(self) -> bool:  # True when the store is valid (the self.valid gate)
        await self.pr.setup()  # required for every logged warning and error, like every other
        # FRAM-capable module's setup(): without it self.pr.initialized never becomes True and each later
        # err_s()/wrn_s() silently skips its own FRAM write (the implicit FRAM-wiring rule, SPECIFICATION.md A.7).
        data: dict[str, CfgValue] | None = None
        missing = False
        damaged = False  # unparseable, not an object, or a stored value the schema refuses: repaired, still listed
        try:
            if (os.stat(self._config_file)[0] & 0x4000) == 0:  # 0x4000 = MP_S_IFDIR, MicroPython's own
                # stat-mode bit (extmod/vfs.h), uniform across VFS backends incl. littlefs.
                with open(self._config_file) as f:
                    try:
                        data = json.load(f)  # parse to json
                        if not isinstance(data, dict):  # generally valid json but not a dict
                            data = None
                            damaged = True
                            await self.pr.wrn_s("Data in config file", self._config_file, "has wrong format.", wrnno=_WRN_CFG_FILE_NOT_OBJECT)
                    except ValueError as e:  # malformed json
                        damaged = True
                        await self.pr.wrn_s("JSON Data in config file", self._config_file, "is invalid:", e, wrnno=_WRN_CFG_FILE_JSON)
            else:  # filename exists but is a directory and cannot be used: a file fault
                self.faulted = True
                await self.pr.err_s(self._config_file, "exists but is not a file, cannot write!", errno=_ERR_CFG_PATH_IS_DIR)
                return False
        except (MemoryError, OSError) as e:  # absent, or unreadable (an I/O error, json.load() exhausting the heap)
            missing = isinstance(e, OSError) and e.errno == errno.ENOENT
            if missing:
                self.absent_at_boot = True
                # A genuinely absent file is written once with the defaults (owner, 2026-10-01); an unreadable one never is.
                self.pr.one("Config file", self._config_file, "not present - writing the defaults once")
            else:
                self.writable = False
                self.faulted = True
                await self.pr.wrn_s("Config file", self._config_file, "could not be read:", e, wrnno=_WRN_CFG_FILE_UNREADABLE)

        defaults = schema_dict(self._cfg_vals)
        if len(defaults) == 0:  # default config contains no values
            await self.pr.err_s(self._config_file, "- Defaults are empty, config is not valid!", errno=_ERR_CFG_NO_DEFAULTS)
            return self.valid

        rewrite = missing or damaged  # an absent file is written once, an unparseable or non-object one repaired
        valid_cfg: dict[str, CfgValue] = {}  # create surely valid config
        for key, field in defaults.items():  # iterate through default config
            use_value, default_val = check_cfg_get_default(field)  # read and selfcheck
            if default_val is None:  # invalid config, no default or special-alone value
                await self.pr.err_s(self._config_file, "- Default Key", key, "Error or None, config is not valid!", errno=_ERR_CFG_BAD_DEFAULT)
                return self.valid
            if not use_value:  # special-alone value
                continue  # not used for storage, skip loop iteration
            new_cfg: CfgValue
            if data is None:  # no, unreadable or damaged config file
                new_cfg = default_val  # immediately take default value
            else:  # file exists and is valid
                stored = key in data  # a refused stored value is damage; a missing key only schema drift
                new_cfg = data.pop(key, None)  # remove all used and known keys from config
                is_error, coerced_cfg = type_or_range_error(new_cfg, field)  # new_cfg=None or any other error -> is_error
                if is_error:
                    rewrite = True
                    damaged = damaged or stored
                    new_cfg = default_val
                    await self.pr.wrn_s(self._config_file, "- Key", key, "has error or is missing, using default!", wrnno=_WRN_STORED_DEFAULT)
                else:
                    if type(coerced_cfg) is not type(new_cfg):  # e.g. a hand-edited file's "5" for a
                        rewrite = True  # float field - persist the coerced shape back to disk too.
                        # (`!=` alone would miss this: 5 != 5.0 is False in Python despite the type
                        # differing - type() is the only reliable signal that coercion actually fired.)
                    new_cfg = coerced_cfg
            valid_cfg[key] = new_cfg
        if data:  # unexpected keys remaining from a readable file: schema drift, repaired, not a fault
            rewrite = True
            await self.pr.wrn_s(self._config_file, "- Removed invalid keys from config file!", wrnno=_WRN_CFG_KEYS_REMOVED)
        self.faulted = self.faulted or damaged

        if not (valid_cfg and self.writable and rewrite):  # a command-only schema (no values) creates no file
            self.pr.one(self._config_file, "- config is ready, nothing to write" if valid_cfg else "- schema stores no values, no file")
        else:  # this boot's one write: the defaults of an absent file, or the repair of a readable one
            self.pr.one(self._config_file, "- Writing configuration file!")
            try:
                text = json.dumps(valid_cfg)  # serialised before the open: a failure leaves the file intact
                with open(self._config_file, "w") as f:
                    f.write(text)
                self.pr.one("Default data was written in", self._config_file, "- config is ready.")
            except (MemoryError, OSError) as e:  # One attempt per setup(), never retried (C.7.3).
                self.unpersisted = True
                await self.pr.err_s("Error writing config", self._config_file, "- running unpersisted:", e, errno=_ERR_CFG_FILE_WRITE)
        # valid_cfg is validated either way: a failed write costs persistence, never the config -
        # refusing it ended every reader's task and looped the device through reboots (C.7.3).
        self._cache = valid_cfg
        self.valid = True
        return self.valid

    async def write_config(self, data: "JsonMapping", *, defer: bool = False) -> "tuple[bool, WriteValidity]":
        # Validates against the manager's own schema and stages synchronously, then hands the flash write to an
        # independent task (SPECIFICATION.md Part F.2): an RP2040 flash write disables interrupts port-wide. A
        # deferred write's task waits for commit(), so a PUT's flash write follows its pushes.
        if self._closed_for_reset():
            return False, {}
        if not self.valid:
            await self.pr.err_s(self._config_file, "- Config is not valid, cannot write!", errno=_ERR_CFG_NOT_VALID)
            return False, {}
        if not self.writable:
            self.pr.evt(self._config_file, "- unreadable at boot, writes refused until the next boot")
            return False, {}
        async with self._config_lock:
            if self._closed_for_reset():  # closed while this call waited for the lock
                return False, {}
            try:
                fields = schema_dict(self._cfg_vals)
                # Special-alone keys are commands, not stored values: the primitive never compares them.
                always = tuple(key for key, field in fields.items() if not check_cfg_get_default(field)[0])
                resolution: dict[str, Callable[[CfgValue], CfgValue]] = {key: _stored_float for key, field in fields.items() if field[1] == "float"}
                outcome = compare_before_write(data, self._cfg_vals, self._current(), always=always, resolution=resolution)
            except MemoryError as e:  # the compare exhausting the heap - no file I/O happens in this method
                await self.pr.err_s(self._config_file, "- Error validating config data:", e, errno=_ERR_ALLOC)
                return False, {}
            if outcome is None:
                await self.pr.err_s(self._config_file, "- write data is not an object", errno=_ERR_BAD_ARG)
                return False, {}
            write, dict_results = outcome
            # No bad-default check: the manager's own schema passed setup()'s self-check, and a malformed
            # schema fails tests_scripts/test_config_schemas.py.
            for key, result in dict_results.items():
                if result == INVALID:
                    if key not in fields:
                        await self.pr.err_s(self._config_file, "- Key", key, "not found, skipping!", errno=_ERR_BAD_ARG)
                    else:
                        await self.pr.err_s(self._config_file, "- Type / range error in", key, "- skipping!", errno=_ERR_BAD_ARG)
                elif result == FAILED:
                    await self.pr.err_s(self._config_file, "- Key", key, "not found in config file, ignoring!", errno=_ERR_CONTRACT)
                elif key in always:
                    del write[key]  # "Valid", nothing staged: the push stage dispatches it
                    self.pr.evt(self._config_file, "- Key", key, "is valid but not in storage, skipping.")
            if not write:
                self.pr.evt(self._config_file, "- No new / unchanged config data.")
                return True, dict_results
            try:
                # Built off _current(), not raw _cache: a second write_config() can enter here before an
                # earlier one's flush has run, and basing new_cache on the staged snapshot keeps a rapid pair of
                # writes additive. A float is staged in the form the file reloads as.
                new_cache = dict(self._current())
                for key, value in write.items():
                    new_cache[key] = _stored_float(value) if type(value) is float else value
                task = asyncio.create_task(self._flush_staged(new_cache))
            except MemoryError as e:  # nothing staged: the answer matches what is served
                await self.pr.err_s(self._config_file, "- Error staging config data:", e, errno=_ERR_ALLOC)
                return False, {}
            # No await from here to the return: the task cannot run before it is staged, and a deferred one
            # then waits for commit(); _cache stays "what the file holds" until _flush_staged() commits it.
            if defer:
                self._commit_ready.clear()
            else:
                self._commit_ready.set()
            self._staged = new_cache
            self._pending_flush = task
            self.pr.evt(self._config_file, "- Config data staged, flash write scheduled.")
            return True, dict_results
