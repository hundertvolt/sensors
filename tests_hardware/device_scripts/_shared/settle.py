"""Included into device scripts at render: wait for a task to finish while feeding the watchdog, polled in bounded
steps rather than asyncio.wait_for(), the one shape that both waits and feeds; False when it is still running."""

import asyncio

import machine

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _Finishing(Protocol):
        def done(self) -> bool: ...


# @tunable l3.settle_step_ms = 100
_SETTLE_STEP_MS = 100
# @tunable l3.settle_budget_ms = 2000
_SETTLE_BUDGET_MS = 2000


async def settled(wdt: machine.WDT, task: "_Finishing") -> bool:
    for _ in range(_SETTLE_BUDGET_MS // _SETTLE_STEP_MS):
        if task.done():
            return True
        wdt.feed()
        await asyncio.sleep_ms(_SETTLE_STEP_MS)
    return task.done()
