"""Isolated-driver device script: with the alarm pool exhausted, SystemService._reboot() cannot arm its reset timer and
must fall back to starving the real watchdog. Feeds only through feed_watchdog(), as the supervisor does; never returns
on success - the reset ends the run and the host reads the banner lines before it."""

import asyncio
import errno
import time

import machine

from asy_system_service import SystemService

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact

# @tunable l3.starvation_wdt_ms = 1500
_WATCHDOG_TIMEOUT_MS = 1500  # short, as watchdog_starvation_reset.py: the host bounds the whole run
# @tunable l3.reboot_fallback_starves_the_watchdog_feed_attempt_ms = 250
_FEED_ATTEMPT_MS = 250
# asy_system_service.py's _RR_REBOOT: a const() whose name starts with "_" is no module global on
# MicroPython, so it cannot be imported and is restated here.
_RR_REBOOT = 3


async def _never_synced() -> bool:
    return False


def _release(timers: "list[machine.Timer]", failure: str) -> None:
    # An early failure: the pool released so the board survives to report it, the reason as a fact, then DONE.
    for t in timers:
        t.deinit()
    fact("failure", failure)
    done()


def main() -> None:
    wdt = machine.WDT(timeout=_WATCHDOG_TIMEOUT_MS)
    fact("armed_ms", _WATCHDOG_TIMEOUT_MS)
    svc = SystemService(_never_synced, watchdog=wdt)
    timers: list[machine.Timer] = []
    try:
        for _ in range(64):  # the real pool is small and fixed (timer_alarm_pool_exhaustion.py)
            wdt.feed()
            t = machine.Timer()
            t.init(period=60_000, callback=lambda _t: None)
            timers.append(t)
    except OSError as exc:
        if not exc.args or exc.args[0] != errno.ENOMEM:
            _release(timers, f"exhausting the alarm pool raised {exc!r}, not ENOMEM")
            return
    else:
        _release(timers, "the alarm pool never ran out - _reboot()'s fallback is unreachable this way")
        return
    fact("pool_timers", len(timers))
    fired = []
    asyncio.run(svc._reboot(_RR_REBOOT, "reboot requested with the alarm pool exhausted", lambda: fired.append(True)))
    if not svc._force_watchdog_starve:
        _release(timers, "_reboot() did not set _force_watchdog_starve")
        return
    print("STARVE flag set, feeding only through feed_watchdog() now")
    t0 = time.ticks_ms()
    while True:  # the supervisor's own feed site, called on schedule; the watchdog must still fire
        svc.feed_watchdog()
        print(f"FEED_CALLED t={time.ticks_diff(time.ticks_ms(), t0)}ms action_fired={bool(fired)}")
        time.sleep_ms(_FEED_ATTEMPT_MS)


main()
