"""Restores SYSTEM DebugLevel to the standard board state; run only by the standard-state fixture under
--repair-standard-state when no bench bridge is configured (one flash write). The schema is the production one,
rendered from src/asy_system_service.py; the host hard-resets afterwards."""

import asyncio

import asy_config_manager as cm

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import cast

    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

    from asy_config_manager import ConfigSchema
else:

    def cast(_typ: object, val: object) -> object:  # no typing module on MicroPython: the identity at run time
        return val

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py


async def _main() -> None:
    arm()
    # BENCH carries the production schema as plain facts (bench_facts.pyi types its fields as object), so it takes
    # ConfigManager's own schema type at this one boundary.
    schema: ConfigSchema = cast("ConfigSchema", tuple((name,) + tuple(spec) for name, spec in BENCH["system_schema"].items()))
    store = cm.ConfigManager("config_SYSTEM.cfg", schema, "SYSTEM")
    fact("valid", await store.setup())
    before = (await store.get_dict(["DebugLevel"]) or {}).get("DebugLevel")
    fact("before", before)
    written = False
    if before != BENCH["standard_debug_level"]:
        written, validity = await store.write_config({"DebugLevel": BENCH["standard_debug_level"]})
        fact("validity", validity)
        await store.flush_pending()
    fact("written", written)
    done()


asyncio.run(_main())
