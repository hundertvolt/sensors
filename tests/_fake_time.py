"""The shared fake time sources: FakeTime (a local-time callback's hour and minute), DrivenTime (rp2's 2**30 ticks the test
advances, installed as `time` in given modules for a block), Rp2Gmtime (rp2's 8-field gmtime()), tick() (one timer flag
wake-up per call) and UTCValid (the boot's first NTP clock set, for a block). Every 2**30 clock here is tests/_ticks30.py's Ticks30Time."""

import asyncio
import time

from _ticks30 import Ticks30Time

import asy_base_classes

_WALL_CLOCK = ("gmtime", "localtime", "mktime", "time")


class DrivenTime(Ticks30Time):
    # `now` and advance() as Ticks30Time's; inside the block each given module's `time` is this object. `strict`: any
    # wall-clock read raises (a test proving no RTC, time() or NTP value is used); every other name is the real module's.
    def __init__(self, *modules: object, now: int = 0, strict: bool = False) -> None:
        super().__init__(now)
        self._modules = modules
        self._saved: list[object] = []
        self._strict = strict

    def __enter__(self) -> "DrivenTime":
        self._saved = [module.time for module in self._modules]  # type: ignore[attr-defined]  # each a module reading `time`
        for module in self._modules:
            module.time = self  # type: ignore[attr-defined]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *_exc_info: object) -> None:
        for index, module in enumerate(self._modules):
            module.time = self._saved[index]  # type: ignore[attr-defined]

    def __getattr__(self, name: str) -> object:
        if self._strict and name in _WALL_CLOCK:
            raise AssertionError("the wall clock was read: time." + name)
        return getattr(time, name)


class FakeTime:
    # What a notification local-time callback answers: the hour and the minute.
    def __init__(self, hour: int, minute: int) -> None:
        self.hour = hour
        self.minute = minute


class Rp2Gmtime:
    # A module's `time` answering gmtime() in rp2's 8 fields (this Unix port's has 9), as the NTP client's cettime() checks.
    def gmtime(self, *secs: int) -> "tuple[int, ...]":
        return tuple(time.gmtime(*secs))[:8]

    def mktime(self, t: "tuple[int, ...]") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return time.time()


class UTCValid:
    # The NTP client's first clock set of the boot, as utc_now() sees it, undone on exit.
    def __enter__(self) -> "UTCValid":
        asy_base_classes.set_utc_valid()
        return self

    def __exit__(self, *_exc: object) -> None:
        asy_base_classes.set_utc_valid(valid=False)


async def tick(flag: "asyncio.ThreadSafeFlag", times: int = 1, clock: "DrivenTime | None" = None, step_ms: int = 1000) -> None:
    # One wake-up of a loop waiting on `flag` per time, a given clock advanced by `step_ms` before each; the second
    # yield lets the woken iteration's own awaits settle before the caller checks it.
    for _ in range(times):
        if clock is not None:
            clock.advance(step_ms)
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
