"""Isolated-driver device script: every float config field's stored form is idempotent on the board's
single-precision floats, and one value written through a scratch manager reloads from flash so that a
repeat write answers "Unchanged" (SPECIFICATION.md C.5). Its one owned flash write is the test's."""

import asyncio
import errno
import os

import asy_config_manager as cm

# (name, min, max) per float field, rendered from the src/ schemas by
# tests_hardware/flash/test_config_float_round_trip.py: this script never reads a host file.
FLOAT_FIELDS: "tuple[tuple[str, float, float], ...]" = ()
_PATH = "config_HWTEST_FLOAT.cfg"
_STEPS = 200  # evenly spaced values per range, beside the two bounds themselves
_MAX_REPORTED = 8  # non-idempotent values named in the result line; the count is always complete


def _remove_scratch() -> str | None:
    # A leftover from an aborted run is removed first, and the file again on every path out.
    try:
        os.remove(_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            return f"removing {_PATH} failed with errno {e.errno}"
    return None


def _non_idempotent() -> "list[str]":
    found: list[str] = []
    for name, lo, hi in FLOAT_FIELDS:
        for i in range(_STEPS + 2):
            v = lo if i == 0 else hi if i == _STEPS + 1 else lo + (hi - lo) * i / (_STEPS + 1)
            once = cm._stored_float(v)
            if cm._stored_float(once) != once:
                found.append(f"{name}={v!r}")
    return found


def _primed(schema: "cm.ConfigSchema") -> "cm.ConfigManager":
    # Primed in RAM from the schema, no setup(): the absent scratch file's defaults write is not spent.
    mgr = cm.ConfigManager(_PATH, schema, "HWTEST")
    mgr._cache = {field[0]: field[2] for field in schema}
    mgr.valid = True
    return mgr


async def _round_trip() -> "list[str]":
    name, lo, hi = FLOAT_FIELDS[0]
    value = lo + (hi - lo) / 3  # a third of the range: rarely a short decimal, so a lossy store would show
    schema: cm.ConfigSchema = ((name, "float", lo, lo, hi, None),)
    failures: list[str] = []
    writer = _primed(schema)
    ok, validity = await writer.write_config({name: value})
    await writer.flush_pending()
    if not ok or validity.get(name) != "Valid":
        failures.append(f"the owned write of {name}={value!r} answered {ok}, {validity!r}")
    reader = cm.ConfigManager(_PATH, schema, "HWTEST")
    if not await reader.setup():
        failures.append(f"the manager rebuilt from {_PATH} did not set up")
    ok, validity = await reader.write_config({name: value})
    await reader.flush_pending()
    if not ok or validity.get(name) != "Unchanged":
        failures.append(f"the repeat write after the reload answered {ok}, {validity!r}, not Unchanged")
    return failures


async def _main() -> None:
    if not FLOAT_FIELDS:
        print("RESULT: FAIL no float fields were rendered into this script")
        return
    failures: list[str] = []
    leftover = _remove_scratch()
    if leftover is not None:
        print(f"RESULT: FAIL {leftover}")
        return
    try:
        bad = _non_idempotent()
        if bad:
            failures.append(f"{len(bad)} stored forms not idempotent: {', '.join(bad[:_MAX_REPORTED])}")
        failures += await _round_trip()
    finally:
        removed = _remove_scratch()
        if removed is not None:
            failures.append(removed)
    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS {len(FLOAT_FIELDS)} float fields idempotent in stored form, and a repeat write after the reload answered Unchanged")


asyncio.run(_main())
