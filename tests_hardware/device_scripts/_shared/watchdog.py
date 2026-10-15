"""Included into device scripts at render: arm() takes over the watchdog the harness armed - rp2 keeps one, and a
second construction re-enables it with the new timeout (ports/rp2/machine_wdt.c:45-62, v1.29.0) - and the fed waits
sleep in steps of at most _FEED_STEP_MS with a feed before each, so no wait a script makes outlasts it."""

import asyncio
import time

import machine

# @tunable wdt.timeout_ms = 8000
_WDT_TIMEOUT_MS = 8000
# @tunable l3.device_script_feed_step_ms = 2000
_FEED_STEP_MS = 2000


def arm() -> machine.WDT:
    return machine.WDT(timeout=_WDT_TIMEOUT_MS)


async def fed_sleep_ms(wdt: machine.WDT, total_ms: int) -> None:
    remaining = total_ms
    while remaining > 0:
        wdt.feed()
        step = min(_FEED_STEP_MS, remaining)
        await asyncio.sleep_ms(step)
        remaining -= step
    wdt.feed()


def fed_wait_ms(wdt: machine.WDT, total_ms: int) -> None:
    # The blocking form, for a script with no event loop running: the same steps, the same feeds.
    remaining = total_ms
    while remaining > 0:
        wdt.feed()
        step = min(_FEED_STEP_MS, remaining)
        time.sleep_ms(step)
        remaining -= step
    wdt.feed()
