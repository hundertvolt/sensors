"""FastAsyncSleep: for the `with` block, asyncio.sleep() and sleep_ms() are one scheduler yield each, so a product wait
costs no real time; each request is recorded in seconds with its task (the first CAP, the rest counted in `dropped`),
and a given clock is advanced by it. Both names are restored however the block exits."""

import asyncio

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _Advancing(Protocol):
        def advance(self, ms: int) -> None: ...


class FastAsyncSleep:
    CAP = 512  # bounded: a loop spinning on fast sleeps must not grow the record

    def __init__(self, clock: "_Advancing | None" = None) -> None:
        self.dropped = 0
        self.slept: list[tuple[object, float]] = []
        self._clock = clock
        self._real = (asyncio.sleep, asyncio.sleep_ms)

    def __enter__(self) -> "FastAsyncSleep":
        self._real = (asyncio.sleep, asyncio.sleep_ms)
        real_sleep_ms = self._real[1]

        async def fast_sleep_ms(ms: int) -> None:
            self._record(ms / 1000, ms)
            await real_sleep_ms(0)

        async def fast_sleep(seconds: float) -> None:
            self._record(seconds, int(seconds * 1000))
            await real_sleep_ms(0)

        asyncio.sleep = fast_sleep  # type: ignore[assignment]  # the block's stand-in, the real call shape, swapped back on exit
        asyncio.sleep_ms = fast_sleep_ms  # type: ignore[assignment]  # likewise, for the millisecond form
        return self

    def __exit__(self, *_exc_info: object) -> None:
        asyncio.sleep, asyncio.sleep_ms = self._real

    def _record(self, seconds: float, ms: int) -> None:
        if len(self.slept) < self.CAP:
            self.slept.append((asyncio.current_task(), seconds))
        else:
            self.dropped += 1
        if self._clock is not None:
            self._clock.advance(ms)

    def of(self, task: object) -> "list[float]":
        # The seconds `task` asked to sleep, in order.
        return [seconds for owner, seconds in self.slept if owner is task]
