"""Isolated-driver device script: every float config field's stored form is idempotent on the board's single-precision
floats, and one value written through a scratch manager reloads from flash so that a repeat write answers "Unchanged"
(SPECIFICATION.md C.5); it reports what it saw and the host decides. Its one owned flash write is the test's."""

import asyncio
import errno
import os

import asy_config_manager as cm

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, errors, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_PATH = "config_HWTEST_FLOAT.cfg"
_STEPS = 200  # evenly spaced values per range, beside the two bounds themselves


async def _main() -> None:
    wdt = arm()
    try:  # an aborted run's leftover first (none: ENOENT)
        os.remove(_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_remove_errno", e.errno)
    try:
        fact("fields", len(BENCH["float_fields"]))
        bad = _non_idempotent()
        errors("non_idempotent", len(bad), bad)
        wdt.feed()
        key, (lo, hi) = min(BENCH["float_fields"].items())
        name = key.split(".")[-1]
        value = lo + (hi - lo) / 7  # a seventh of the range: rarely a short decimal, so a lossy store would show
        schema: cm.ConfigSchema = ((name, "float", lo, lo, hi, None),)
        writer = _primed(schema)
        ok, validity = await writer.write_config({name: value})
        await writer.flush_pending()
        fact("owned_write", {"field": key, "value": value, "ok": ok, "validity": validity.get(name)})
        reader = cm.ConfigManager(_PATH, schema, "HWTEST")
        fact("reloaded", await reader.setup())
        ok, validity = await reader.write_config({name: value})
        await reader.flush_pending()
        fact("repeat_validity", validity.get(name))
    finally:
        try:
            os.remove(_PATH)
        except OSError as e:
            if e.errno != errno.ENOENT:
                fact("remove_errno", e.errno)
        done()


def _non_idempotent() -> "list[str]":
    # Every probed value whose stored form changes when stored again.
    found: list[str] = []
    for key, (lo, hi) in sorted(BENCH["float_fields"].items()):
        for i in range(_STEPS + 2):
            v = lo if i == 0 else hi if i == _STEPS + 1 else lo + (hi - lo) * i / (_STEPS + 1)
            once = cm._stored_float(v)
            if cm._stored_float(once) != once:
                found.append(f"{key}={v!r}")
    return found


def _primed(schema: "cm.ConfigSchema") -> "cm.ConfigManager":
    # Primed in RAM from the schema, no setup(): the absent scratch file's defaults write is not spent.
    mgr = cm.ConfigManager(_PATH, schema, "HWTEST")
    mgr._cache = {field[0]: field[2] for field in schema}
    mgr.valid = True
    return mgr


asyncio.run(_main())
