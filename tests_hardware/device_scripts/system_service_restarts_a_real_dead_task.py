"""Isolated-driver device script: SystemService's supervisor (start_tasks(), then supervise_tasks()) restarts a task
that keeps dying, on real hardware. restart reports the starter calls and the logged ends; escalate and hold_console
keep it dying until the restart budget reboots the board, the host reading the reset from /status."""

import asyncio

from asy_print_log import LogConfig
from asy_system_service import SystemService

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.system_service_restarts_a_real_dead_task_watch_step_s = 0.9
_WATCH_STEP_S = 0.9
# @tunable l3.system_service_restarts_a_real_dead_task_wait_rounds = 4
_WAIT_ROUNDS = 4
# The escalation's own bound: _TASK_FAIL_MAX over _TASK_FAIL_INCREMENT deaths, one per _TASK_CHECK_TIME pass, then the
# reset delay; twice that keeps feeding well past the reboot the budget arms.
_ESCALATE_ROUNDS = 40
_HISTORY_LENGTH = 10
_LEVEL = 0  # source: src/asy_system_service.py _VAL_DEBUG_LEVEL default - a task's end reaches the log, never the console
_MODES = ("restart", "escalate", "hold_console")
call_count = [0]


async def _dies_at_once() -> None:
    return  # restarted on the supervisor's own next check pass


def _dying_starter() -> "asyncio.Task[None]":
    call_count[0] += 1
    return asyncio.create_task(_dies_at_once())


async def _main() -> None:
    wdt = arm()
    mode = BENCH.get("mode", "restart")
    fact("mode", mode)
    if mode not in _MODES:
        done()
        return
    sysfunct = SystemService(_ntp_never_synced, watchdog=wdt, log=LogConfig(None, _HISTORY_LENGTH, _LEVEL))
    if mode == "hold_console":
        print("HOLD_FROM_HERE")  # the bench test holds the console unread from here; nothing more is printed
    await sysfunct.start_tasks([_dying_starter], task_names=["dying"])
    supervisor = asyncio.create_task(sysfunct.supervise_tasks())
    rounds = _WAIT_ROUNDS if mode == "restart" else _ESCALATE_ROUNDS
    for n in range(rounds):
        await asyncio.sleep(_WATCH_STEP_S)
        wdt.feed()
        if mode == "escalate":
            fact(f"round_{n}", {"starter_calls": call_count[0], "system": (await sysfunct.get_error_counter())["SYSTEM"]})
    supervisor.cancel()
    try:
        await supervisor
    except asyncio.CancelledError:
        pass
    fact("starter_calls", call_count[0])
    fact("system", (await sysfunct.get_error_counter())["SYSTEM"])
    done()


async def _ntp_never_synced() -> bool:
    return False


asyncio.run(_main())
