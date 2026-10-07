"""Isolated-driver device script: SystemService.start_and_check_tasks() really restarts a dead task
on real hardware, not just in mock/twin bookkeeping - the mechanism CLAUDE.md's memory-safety
discipline leans on when it says to trust the supervisor to restart a task that still dies."""

import asyncio

import machine

from system_service import SystemService

# @tunable wdt.timeout_ms = 8000
_WDT_TIMEOUT_MS = 8000
# @tunable l3.system_service_restarts_a_real_dead_task_watch_step_s = 0.9
_WATCH_STEP_S = 0.9
# @tunable l3.system_service_restarts_a_real_dead_task_wait_rounds = 4
_WAIT_ROUNDS = 4
call_count = 0


async def _ntp_never_synced() -> bool:
    return False


def _dying_starter() -> "asyncio.Task[None]":
    global call_count
    call_count += 1

    async def _c() -> None:
        return None  # dies immediately - restarted on the supervisor's own next check cycle

    return asyncio.create_task(_c())


async def _main() -> None:
    wdt = machine.WDT(timeout=_WDT_TIMEOUT_MS)
    sysfunct = SystemService(_ntp_never_synced, watchdog=wdt)
    supervisor = asyncio.create_task(sysfunct.start_and_check_tasks([_dying_starter]))

    # ~3.5s real time: two real restarts expected (task_errors capped at 200) but well short of
    # the ~7s a task that dies every ~2s cycle would need to trip a REAL reboot (_TASK_FAIL_MAX=300,
    # _TASK_FAIL_INCREMENT=100 per cycle) - not what this script is testing.
    for _ in range(_WAIT_ROUNDS):
        await asyncio.sleep(_WATCH_STEP_S)
        wdt.feed()

    supervisor.cancel()
    try:
        await supervisor
    except asyncio.CancelledError:
        pass

    if call_count < 2:
        print(f"RESULT: FAIL dying task starter was called {call_count} time(s) - expected at least 2 (initial start + a real restart)")
    else:
        print(f"RESULT: PASS dying task starter was called {call_count} times - the real task supervisor restarted it on real hardware")


asyncio.run(_main())
