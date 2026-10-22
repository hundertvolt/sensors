"""Isolated-driver device script: the generated main() over the bench build's scratch config, one callee of boot phase
PHASE (1-5) rebound to a blocking time.sleep_ms() that no feed follows, so the watchdog resets the board inside that
phase and the next boot must read code 10 + PHASE from the boot-phase mark; no flash write beyond the scratch setups."""

import asyncio
import errno
import os
import time

import _bench_device as device  # rendered: the bench device's generated module
import machine

from asy_ntp_client import NTPClient
from asy_print_log import PrintLog

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import fact
    from _shared.watchdog import _WDT_TIMEOUT_MS, arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py
# The product's own unretrieved-task report at the error level, so it prints whatever level the board's config holds.
_REPORT = PrintLog(level=1, name="UNRETRIEVED TASK EXCEPTION:")

_SCRATCH_CFG_PATH = "hwtest-scratch/"
_HANG_MS = _WDT_TIMEOUT_MS + 2000  # one blocking call past the watchdog period
# The callee main() reaches inside each boot phase: construction, setups, task starters, timer starters, the first sync.
_CALLEES = {1: (device, "SystemService"), 2: (device, "_collect_setups"), 3: (device, "_collect_task_starters"), 4: (device, "_collect_trigger_starters"), 5: (NTPClient, "ntp_force_sync")}


def _hang(*_args: object, **_kwargs: object) -> None:
    # Blocks the whole loop: nothing feeds, so on silicon the watchdog resets inside this call; a return is a survival.
    fact("marked_phase", machine.mem_backup(1)[1])  # the boot-phase mark the next boot decodes
    print("HANG")
    time.sleep_ms(_HANG_MS)
    fact("hang_returned_ms", _HANG_MS)
    raise SystemExit


async def _main() -> None:
    asyncio.get_event_loop().set_exception_handler(_REPORT.report_unretrieved)  # before main(): the firmware keeps it
    wdt = arm()
    phase = int(BENCH.get("PHASE", "1"))
    holder, name = _CALLEES[phase]
    fact("phase", phase)
    fact("callee", name)
    try:  # an aborted run's leftover first (none: ENOENT)
        for entry in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + entry)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    setattr(holder, name, _hang)  # from outside: the one rebound callee
    await device.main(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)


asyncio.run(_main())
