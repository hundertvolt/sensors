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

    from asy_fram_manager import AsyFramManager
    from print_log import ErrorLog

    T = TypeVar("T", int, float, str)

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

    # A driver's own generator-facing metadata - what it can be wired to, and what domains its
    # TOML fields have - is NOT declared here, and deliberately isn't a Python value at all: it
    # lives in `# @wiring`/`# @value-wiring`/`# @limits` comment tags beside the schema it
    # describes, because nothing the running firmware reads should become a real frozen-bytecode
    # value just to serve the generator (SPECIFICATION.md Part L.5). See
    # SPECIFICATION.md Part C.14.2 for the grammars and buildgen/wiring.py for the parser.

from print_log import PrintLogHistory, make_logger


def _special_bypass(check_val: "CfgValue", val_special: "CfgSpecial", scalar_type: type, *, check_special: bool) -> "bool | None":
    # Shared by every non-bool branch of type_or_range_error: val_special is a single scalar or a
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


def instance_name(base_name: str, name_ext: str) -> str:
    # Uniform per-instance naming (SPECIFICATION.md Part C.14): an empty name_ext (the default -
    # every module today) reproduces base_name completely unchanged, so a single-instance device's
    # REST dict keys/config filenames/error-log keys stay byte-identical to today's. A non-empty
    # extension appends "_" + name_ext, disambiguating a second instance of the same driver type
    # (e.g. two SCD30s: "SCD30" and "SCD30_fan_pressure") across every one of those three surfaces
    # at once, since all three already key off this one resolved name. Collision detection across
    # a whole device's instance list is the generator's job (not built here), not this function's.
    if not name_ext:
        return base_name
    return base_name + "_" + name_ext


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
    nt: "NamedTuple", fields: "tuple[str, ...]", name: str | None = None,
) -> "dict[str, dict[str, int | float | str | None]]":  # {type_name: {field: value}} - fields is the same
    # literal tuple the caller's own namedtuple(name, fields) was built from (rp2's build ROM level
    # is MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES, one level below the MICROPY_CONFIG_ROM_LEVEL_
    # EVERYTHING that _asdict()/_fields require - confirmed against ports/rp2/mpconfigport.h - so
    # neither is safe to rely on here).
    # name=None (default) introspects the namedtuple's own type name, exactly as before this
    # parameter existed - every caller with only ever one instance relies on this. A caller that
    # can have more than one instance (SPECIFICATION.md Part C.14) passes its own resolved
    # self.name explicitly instead, since the namedtuple *type* itself is fixed at class-definition
    # time and can't vary per instance the way self.name (instance_name()'s result) can.
    if name is None:
        try:
            name = type(nt).__name__
        except Exception:
            return {}
    try:
        return {name: {field: getattr(nt, field) for field in fields}}
    except Exception:
        return {name: dict.fromkeys(fields)}


def coerce_numeric(check_val: "CfgValue", scalar_type: type) -> "tuple[bool, int | float | Any]":
    # Returned value: the coerced scalar when the flag is True (scalar_type is only ever int or
    # float here), the caller's own raw value untouched when it's False - hence the Any arm.
    # Intent: accept only what's exactly representable as scalar_type, in either direction (see
    # SPECIFICATION.md Part A.8) - float -> int is accepted only when the value carries no
    # fractional part, rejected otherwise, never truncated/rounded, so a fat-fingered "12.5" can't
    # silently become a stored "12". int -> float is a blanket accept instead (see the inline
    # comment on that branch below for the one known, accepted gap this leaves in the "exactly
    # representable" intent - not true in general, though every real field is unaffected today).
    # bool is deliberately excluded from both directions even though it's an int subclass in
    # Python/MicroPython - type() (not isinstance()) already keeps it out of every branch below,
    # same as the pre-coercion strict check did.
    #
    # Public (no leading underscore) and reused outside this module: sensortask_wozi.py's
    # lightCmdLED dispatch (dispatch-only, not schema-backed - no FieldSchema record to hand
    # type_or_range_error()) calls this directly for its r/g/b/t coercion instead of duplicating
    # the same int<->float acceptance logic a second time.
    if type(check_val) is scalar_type:
        return True, check_val
    if scalar_type is float and type(check_val) is int:
        # No exact-round-trip check on this direction (unlike float->int below): documented,
        # accepted gap, not a bug - a value large enough to lose precision here (beyond a float's
        # mantissa - 2**24 on the real RP2040 firmware's single-precision build, 2**53 on this
        # Unix-port test build's double precision, see SPECIFICATION.md Part A.8) would already be
        # rejected by every current schema field's own min/max bounds (the largest today is 5000.0)
        # long before reaching this line.
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
    check_val: "CfgValue", field: "FieldSchema", *, check_special: bool = True,
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
                bypass = _special_bypass(check_val, val_special, int, check_special=check_special)
                if bypass is not None:
                    return bypass, check_val
            if type(val_max) is int and type(val_min) is int and val_min <= check_val <= val_max:
                return False, check_val
        elif val_type == "float":  # check for float (coercing an int) and bounds
            ok, check_val = coerce_numeric(check_val, float)
            if not ok:
                return True, check_val
            if val_special is not None:
                bypass = _special_bypass(check_val, val_special, float, check_special=check_special)
                if bypass is not None:
                    return bypass, check_val
            if type(val_max) is float and type(val_min) is float and val_min <= check_val <= val_max:
                return False, check_val
        elif val_type == "str":  # check for str and length bounds
            if type(check_val) is not str:
                return True, check_val
            if val_special is not None:
                bypass = _special_bypass(check_val, val_special, str, check_special=check_special)
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
) -> "tuple[bool, CfgValue]":
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
    except Exception:  # malformed field record
        return True, None
    else:
        return use_value, coerced_val


if TYPE_CHECKING:
    WriteValidity = dict[str, Literal["Invalid", "Unchanged", "Valid", "Failed"]]


class ConfigManager:
    def __init__(self, filename: str, cfg_vals: "ConfigSchema", name: str, fram: "AsyFramManager | None" = None) -> None:
        # Inherits its owning module's FRAM durability (CLAUDE.md's implicit-FRAM-wiring rule: every
        # module gets optional FRAM logging, and this one is no exception) - falls back to the exact
        # same RAM-only PrintLogHistory as before whenever fram is None, so a caller that never
        # passes it sees no observable change at all.
        self.pr: PrintLogHistory = make_logger(fram, name="CFGMGR_" + name)
        self.name = "CFGMGR_" + name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        self.config_lock = asyncio.Lock()
        self.config_file = filename
        self.cfg_vals = cfg_vals
        self.valid = False
        self._cache: dict[str, CfgValue] = {}
        # Staging slot for write_config()'s deferred flash write (SPECIFICATION.md Part F.2) - not
        # yet on disk, but the read path serves it first so a GET reflects a just-accepted PUT
        # immediately rather than waiting for the actual flash write to complete.
        self._staged: dict[str, CfgValue] | None = None
        self._pending_flush: asyncio.Task[None] | None = None

    def _current(self) -> "dict[str, CfgValue]":
        # write_config() always stages a full snapshot (dict(self._cache) plus the changed keys),
        # never a partial one, so a plain swap - not a per-key merge - is correct here: read-your-
        # write for a value not yet flushed, exactly as it would read once the flush completes.
        return self._staged if self._staged is not None else self._cache

    async def _get_values(self, keys: "ConfigSchema") -> "list[Any] | None":
        if not self.valid:
            await self.pr.err_s(self.config_file, "- Config is not valid, cannot read!", errno=5)
            return None
        self.pr.all(self.config_file, "- Reading config data into list.")
        try:
            current = self._current()
            return [current[key] for key in schema_names(keys)]
        except KeyError as e:  # unknown key
            await self.pr.err_s(self.config_file, "- Config read error:", e, errno=6)
            return None

    async def _get_converted_values(self, keys: "ConfigSchema", converter: "Callable[..., T]") -> "list[T] | None":
        values = await self._get_values(keys)
        if values is None:
            return None
        try:
            return [converter(v) for v in values]
        except (TypeError, ValueError):
            return None

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def get_dict(self, keys: "list[str]") -> "dict[str, CfgValue] | None":
        # Reads _cache (or _staged, if a write_config() this instant is between staging and its own
        # flush actually landing - read-your-write) directly - no lock needed: neither write_config()
        # nor _flush_staged() ever awaits mid-mutation of the field this reads, so no partial state
        # is observable here (see module docstring for the cache design).
        if not self.valid:
            await self.pr.err_s(self.config_file, "- Config is not valid, cannot read!", errno=7)
            return None
        self.pr.all(self.config_file, "- Reading config data into dict.")
        try:
            current = self._current()
            return {key: current[key] for key in keys}
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
        self, data: "dict[str, CfgValue]", cfg_vals: "ConfigSchema",
    ) -> "tuple[bool, WriteValidity]":
        # Validates and stages synchronously, then hands the actual flash write to an independent
        # asyncio.create_task() instead of awaiting it inline (SPECIFICATION.md Part F.2): an
        # RP2040 flash write disables interrupts port-wide for its whole duration, and doing it
        # inline here reset the very HTTP connection whose PUT triggered it (BACKLOG.md, 2026-09-15
        # - a real bench-hardware finding). The write no longer needs to share a breath with the
        # response - by the time it actually runs, that connection is typically already closed.
        if not self.valid:
            await self.pr.err_s(self.config_file, "- Config is not valid, cannot write!", errno=9)
            return False, {}
        async with self.config_lock:
            try:
                # Built off _current(), not the raw _cache: a second write_config() call can enter
                # this block before an earlier one's own _flush_staged() has actually run (that task
                # is only scheduled, not started, by the time this one's own lock-holding stretch
                # begins) - basing new_cache on the not-yet-flushed staged snapshot instead is what
                # keeps a rapid pair of writes additive rather than the second one silently
                # clobbering the first's still-pending change.
                new_cache = dict(self._current())  # working copy - only staged/committed after validation
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
                    # coerced_value (not the caller's raw one) is the shape stored below - e.g. int->float
                    if not use_value:
                        dict_results[key] = "Valid"
                        self.pr.evt(self.config_file, "- Key", key, "is valid but not in storage, skipping.")
                        continue  # not used for storage
                    if key not in new_cache:
                        dict_results[key] = "Failed"
                        await self.pr.err_s(self.config_file, "- Key", key, "not found in config file, ignoring!", errno=13)
                        continue
                    if new_cache[key] != coerced_value:
                        new_cache[key] = coerced_value
                        dict_results[key] = "Valid"
                        changed = True
                    else:
                        dict_results[key] = "Unchanged"
                if not changed:
                    self.pr.evt(self.config_file, "- No new / unchanged config data.")
                    return True, dict_results
                # Staged, not yet on flash - get_dict()/_get_values() consult this first (read-your-
                # write), and _cache stays "what's actually on disk" until _flush_staged() commits it.
                self._staged = new_cache
                self._pending_flush = asyncio.create_task(self._flush_staged(new_cache))
                self.pr.evt(self.config_file, "- Config data staged, flash write scheduled.")
            except (MemoryError, AttributeError) as e:  # a non-dict `data` param (AttributeError on
                # .items()), or dict()/the validation loop exhausting the heap - no file I/O happens
                # in this method anymore (see _flush_staged), so OSError/ValueError no longer apply.
                await self.pr.err_s(self.config_file, "- Error validating config data:", e, errno=15)
                return False, {}
            else:
                return True, dict_results

    async def _flush_staged(self, staged: "dict[str, CfgValue]") -> None:
        # The actual, still-synchronous-and-uninterruptible flash write, now fully decoupled from
        # whatever request originally triggered it. Re-acquires the same lock write_config() uses,
        # so at most one write (validate-and-stage, or flush) is ever in flight per ConfigManager -
        # a later write_config() call simply queues behind this one, seeing the fresh _cache once it
        # resumes, exactly as if the two calls had run back-to-back synchronously.
        async with self.config_lock:
            if self._staged is not staged:
                # A newer write_config() call staged (and scheduled its own flush for) something
                # else while this task was waiting for the lock - this snapshot is superseded, and
                # writing it now would silently regress a value already replaced. Not reachable by
                # arrival order alone (create_task() runs tasks in creation order), only if this
                # task's own turn was ever skipped past whoever's flush already committed the newer
                # snapshot - defensive, so the "last write always wins" property never depends on
                # asyncio's own scheduling order being FIFO.
                return
            try:
                with open(self.config_file, "w") as f:
                    json.dump(staged, f)
                self._cache = staged  # only commit once the write has actually succeeded
                self.pr.evt(self.config_file, "- Config data was written.")
            except (MemoryError, OSError, ValueError, AttributeError) as e:  # file errors, or
                # json.dump() exhausting the heap; ValueError is defensive since dump() no longer
                # reads/reparses json here. _cache is deliberately left untouched - "what's on disk,
                # as far as we know" per the module docstring - this is the accepted, logged-only
                # residual-risk outcome (SPECIFICATION.md Part F.2), never re-raised into the caller.
                await self.pr.err_s(self.config_file, "- Error writing config data:", e, errno=14)
            finally:
                if self._staged is staged:  # nothing newer staged while this flush was running
                    self._staged = None
                if self._pending_flush is asyncio.current_task():
                    self._pending_flush = None

    async def flush_pending(self) -> None:
        # Waits for a write_config()-spawned flush to actually finish rather than merely being
        # scheduled. Most real callers tolerate the deferred write per this module's own design
        # (SPECIFICATION.md Part F.2) and never need this - the one exception is a commanded
        # reboot/bootloader (buildgen/codegen.py's generated _flush_pending_configs(), called from
        # _system_cmd_callback() before either action): that path is software-triggered and can
        # easily wait a flush out, so it should, rather than inheriting the power-loss-only residual
        # risk this module's design otherwise accepts.
        # Only ever holds the LATEST write_config() call's own task - a still-outstanding earlier
        # one it superseded is never awaited directly, but is always safe to leave unawaited: it
        # either already ran (in creation order, the common case) or will still run and detect
        # itself superseded via _flush_staged()'s own snapshot-identity check, a no-op either way.
        pending = self._pending_flush
        if pending is not None:
            await pending

    async def setup(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors, matches every other
        # FRAM-capable module's own setup() - a real gap before WP2 (CLAUDE.md's implicit-FRAM-
        # wiring rule): harmless no-op while self.pr was always RAM-only, but load-bearing now that
        # it can be a real PrintLogHistoryStore - without this, self.pr.initialized never becomes
        # True and every later err_s()/wrn_s() call here silently skips its own FRAM write.
        data: dict[str, CfgValue] | None = None
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
        valid_cfg: dict[str, CfgValue] = {}  # create surely valid config
        for key, field in defaults.items():  # iterate through default config
            use_value, default_val = check_cfg_get_default(field)  # read and selfcheck
            if default_val is None:  # invalid config, no default or special-alone value
                await self.pr.err_s(self.config_file, "- Default Key", key, "Error or None, config is not valid!", errno=3)
                return
            if not use_value:  # special-alone value
                continue  # not used for storage, skip loop iteration
            new_cfg: CfgValue
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
        except (MemoryError, OSError, TypeError) as e:  # write failed, filename isn't a string, or
            # json.dump() exhausts the heap serializing valid_cfg
            await self.pr.err_s("Error writing config", self.config_file, "- config is not valid:", e, errno=4)
