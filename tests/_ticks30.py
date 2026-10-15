"""Ticks30Time: a `time` with rp2's 2**30 tick period, installed as a module's own `time` (restored in `finally`).
`now` is the uptime in ms: ticks_ms() is `now`, ticks_us() is `now * 1000`, both on the 2**30 period; ticks_diff() and
ticks_add() follow extmod/modtime.c:166-196 (v1.29.0); every other name is the real module's (SPECIFICATION.md F.1)."""

import time

TICKS_PERIOD = 1 << 30  # rp2: MP_SMALL_INT_POSITIVE_MASK + 1 on a 32-bit word (py/mpconfig.h:1925)
_HALF = TICKS_PERIOD // 2
_MASK = TICKS_PERIOD - 1


def _tick_arg(value: object) -> int:
    # The board reads a tick argument as a small int unchecked and computes a number from any other object
    # (`ticks_diff(None, 0)` returns one); here anything rp2 cannot hold as a small int raises instead.
    if type(value) is not int or not -TICKS_PERIOD <= value < TICKS_PERIOD:
        raise TypeError("not a ticks value: " + repr(value))
    return value


class Ticks30Time:
    def __init__(self, now: int = 0) -> None:
        self.now = now

    def __getattr__(self, name: str) -> object:
        return getattr(time, name)

    def advance(self, ms: int) -> None:
        self.now += ms

    def ticks_add(self, ticks: int, delta: int) -> int:
        # mp_obj_get_int() refuses a non-integer delta; the range check excludes both half-period ends.
        if type(delta) is not int and type(delta) is not bool:
            raise TypeError("can't convert " + repr(delta) + " to int")
        if not -_HALF < delta < _HALF:
            raise OverflowError("ticks interval overflow")
        return (_tick_arg(ticks) + delta) & _MASK

    def ticks_diff(self, end: int, start: int) -> int:
        return ((_tick_arg(end) - _tick_arg(start) + _HALF) & _MASK) - _HALF

    def ticks_ms(self) -> int:
        return self.now & _MASK

    def ticks_us(self) -> int:
        return (self.now * 1000) & _MASK
