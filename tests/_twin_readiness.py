"""Readiness polls for the in-process twin tier: a bounded wait for a value in place of a fixed sleep, so a test waits
exactly as long as the code under test takes. The limit counts poll rounds, not the wall clock: under CPU starvation
every sleep overruns, so a wall-clock limit would fail sooner, never later."""

import asyncio

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

# @tunable l2.twin_readiness_poll_ms = 10
_POLL_MS = 10


async def wait_for_value(read: "Callable[[], object]", expected: object, limit_ms: int) -> bool:
    # True once read() equals `expected`, polled every _POLL_MS; False when limit_ms of rounds pass without it.
    if limit_ms < 0:
        raise ValueError("limit_ms must not be negative")
    waited = 0
    while read() != expected:
        if waited >= limit_ms:
            return False
        await asyncio.sleep_ms(_POLL_MS)
        waited += _POLL_MS
    return True
