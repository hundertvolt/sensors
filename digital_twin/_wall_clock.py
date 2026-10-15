"""The twin's wall clock: the built-in time module plus an offset that RTC().datetime(set) and the twin-only step()
move, as an RTC set moves time.time()/gmtime() on rp2 (ports/rp2/modtime.c:31-43, machine_rtc.c:64-97, v1.29.0).
Ticks never step; gmtime()/localtime() answer rp2's 8-field tuple (extmod/modtime.c:55-75), not the Unix port's 9."""

import time as _time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterable


class WallClock:
    TEST_API = ("step",)

    def __init__(self) -> None:
        self.offset_s = 0

    def __getattr__(self, name: str) -> object:
        # mktime, the ticks, the sleeps: the built-in's, so ticks never step with the wall clock.
        return getattr(_time, name)

    def set_wall(self, epoch_s: int) -> None:
        self.offset_s = epoch_s - int(_time.time())

    def gmtime(self, t: "int | None" = None) -> "tuple[int, ...]":
        return tuple(_time.gmtime(self.time() if t is None else t))[:8]

    def localtime(self, t: "int | None" = None) -> "tuple[int, ...]":
        # rp2 has no time zone: localtime is gmtime (extmod/modtime.c:203-204).
        return self.gmtime(t)

    def step(self, seconds: int) -> None:
        # Twin-only test knob: the wall clock jumps by `seconds`, as an NTP correction or a clock-jump test needs.
        self.offset_s += seconds

    def time(self) -> int:
        # Integral, as rp2's aon-timer seconds are (ports/rp2/modtime.c:39-43); the Unix port's is a float.
        return int(_time.time()) + self.offset_s


def epoch_seconds(year: int, month: int, day: int, hour: int, minute: int, second: int) -> int:
    # timeutils_mktime_1970()'s civil-date arithmetic (shared/timeutils/timeutils.h:72): no host time zone enters.
    y = year - (month <= 2)
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    days = era * 146097 + yoe * 365 + yoe // 4 - yoe // 100 + doy - 719468
    return days * 86400 + hour * 3600 + minute * 60 + second


_clock: "WallClock | None" = None
_rebound: "list[object]" = []  # every module install() rebound, for reset_test_state() to put back


def install(modules: "Iterable[object]") -> WallClock:
    # Bound from outside, as every test adapts a product seam: src/ stays unchanged. A module whose `time` is not the
    # built-in (already rebound, or never the module) is skipped, so a second call changes nothing.
    global _clock
    if _clock is None:
        _clock = WallClock()
    for module in modules:
        if getattr(module, "time", None) is _time:
            setattr(module, "time", _clock)  # noqa: B010 - `module` is any object with a `time` global
            _rebound.append(module)
    return _clock


def installed() -> "WallClock | None":
    return _clock


def reset_test_state() -> None:
    # Test-only: every rebound module gets the built-in time back and the clock is dropped (machine.reset_test_state()).
    global _clock
    for module in _rebound:
        setattr(module, "time", _time)  # noqa: B010 - as install()
    _rebound.clear()
    _clock = None
