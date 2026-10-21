"""FastAsyncSleep: for the `with` block, asyncio.sleep() and sleep_ms() are one scheduler yield each, so a product wait costs no real
time; each request is recorded with its task, in seconds and in its form (the first CAP, the rest in `dropped`), and advances a given
clock; both names are restored however the block exits. check_sleep_ms() is the real sleep_ms()'s float refusal (the Unix port's tick range, not rp2's 2**29 ms), for every stand-in."""

import asyncio
import time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _Advancing(Protocol):
        def advance(self, ms: int) -> None: ...


def check_sleep_ms(ms: int) -> None:
    # sleep_ms() and wait_for_ms()'s bound pass the delay to ticks_add() (extmod/asyncio/core.py:55-57, v1.29.0), whose
    # mp_obj_get_int() refuses a float: one raises here as on rp2, where MicroPython's 500.0 == 500 would pass an int pin.
    time.ticks_add(time.ticks_ms(), max(0, ms))


class FastAsyncSleep:
    CAP = 512  # bounded: a loop spinning on fast sleeps must not grow the record

    def __init__(self, clock: "_Advancing | None" = None) -> None:
        self.dropped = 0
        self.slept: list[tuple[object, float, int | None]] = []  # (task, seconds, the int sleep_ms() got; None for sleep())
        self._clock = clock
        self._real = (asyncio.sleep, asyncio.sleep_ms)

    def __enter__(self) -> "FastAsyncSleep":
        self._real = (asyncio.sleep, asyncio.sleep_ms)
        real_sleep_ms = self._real[1]

        async def fast_sleep_ms(ms: int) -> None:
            check_sleep_ms(ms)
            self._record(ms / 1000, ms, ms)
            await real_sleep_ms(0)

        async def fast_sleep(seconds: float) -> None:
            self._record(seconds, None, int(seconds * 1000))
            await real_sleep_ms(0)

        asyncio.sleep = fast_sleep  # type: ignore[assignment]  # the block's stand-in, the real call shape, swapped back on exit
        asyncio.sleep_ms = fast_sleep_ms  # type: ignore[assignment]  # likewise, for the millisecond form
        return self

    def __exit__(self, *_exc_info: object) -> None:
        asyncio.sleep, asyncio.sleep_ms = self._real

    def _record(self, seconds: float, asked_ms: "int | None", ms: int) -> None:
        if len(self.slept) < self.CAP:
            self.slept.append((asyncio.current_task(), seconds, asked_ms))
        else:
            self.dropped += 1
        if self._clock is not None:
            self._clock.advance(ms)

    def of(self, task: object) -> "list[float]":
        # The seconds `task` asked to sleep, in order, either form.
        return [seconds for owner, seconds, _ms in self.slept if owner is task]

    def ms_of(self, task: object) -> "list[int]":
        # The ints `task` gave sleep_ms(), in order: a wait asked in seconds never shows here.
        return [ms for owner, _seconds, ms in self.slept if owner is task and ms is not None]
