"""A driven clock for chosen product modules (the runner's --test-uart-driven-clock): their ticks_ms() and sleeps run on
virtual time, which reaches the host's only while none of their tasks is runnable, so a task's compute and its turns on
the loop never spend a deadline, while a modelled flash hold still does (SPECIFICATION.md J.7)."""

import asyncio
import time as _time

import _flash_stall

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine, Iterable

    from _mpy_shed.time_mp import _TicksMs

# How long the driver waits before looking again at a compute still taking turns: a twin scheduler round is about 1 ms,
# so looking at every one would double a CRC16 frame's rounds.
# @tunable l2.twin_uart_clock_recheck_ms = 10
_BUSY_RECHECK_MS = 10


class _Sleeps:
    # A module's `asyncio` on the clock: only what the lent modules use at run time, so a new name fails here.
    get_event_loop = staticmethod(asyncio.get_event_loop)

    def __init__(self, clock: "DrivenClock") -> None:
        self._clock = clock

    def sleep(self, seconds: float) -> "Coroutine[object, object, None]":
        return self._clock.sleep_ms(int(seconds * 1000))  # as core.sleep(): sleep_ms(int(t * 1000))

    def sleep_ms(self, ms: int) -> "Coroutine[object, object, None]":
        return self._clock.sleep_ms(ms)


class _Ticks:
    # A module's `time` on the clock: ticks_ms() reads it; ticks_add(), ticks_diff() and every other name are its own.
    def __init__(self, clock: "DrivenClock", own: object) -> None:
        self._clock = clock
        self._own = own

    def __getattr__(self, name: str) -> object:
        return getattr(self._own, name)

    def ticks_ms(self) -> "_TicksMs":
        return self._clock.ticks_ms()


class _Wake:
    # One parked sleep: its virtual wake time, the event the clock sets then, and whether it is still listed.
    def __init__(self, at: int) -> None:
        self.at = at
        self.event = asyncio.Event()
        self.listed = True


class DrivenClock:
    # Virtual ms since construction. drive() moves them, once no lent task is runnable (none waits on its turn and none
    # was woken without having run), to each parked wake the host has reached, then to the host's ms; a flash hold at once.
    def __init__(self) -> None:
        self.elapsed = 0
        self._origin = _time.ticks_ms()  # virtual 0, and the host's reading there
        self._stalled = _flash_stall.stalled_ms
        self._sleepers: list[_Wake] = []  # one per sleeping task, so the list stays small
        self._turning: set[object] = set()  # lent tasks waiting on their turn on the loop
        self._woken: set[_Wake] = set()  # the wakes released whose task has not run since
        self._parked = asyncio.Event()  # set by every park, so a waiting driver reads the earliest wake again
        self._quiet = asyncio.Event()  # set when the last lent task runnable at this instant stops being so
        self._saved: list[tuple[object, object]] = []
        self._released: tuple[_TicksMs, int] | None = None  # the host's ticks and the virtual ms at release()

    async def _alarm(self, ms: int) -> None:
        # Wakes a waiting driver once ms have passed on the host, the earliest wake then due.
        await asyncio.sleep_ms(ms)
        self._parked.set()

    def _calm(self) -> None:
        if not self._turning and not self._woken:
            self._quiet.set()

    def _park(self, at: int) -> _Wake:
        # Listed after every wake due no later, so wakes due at one time run in the order they slept.
        wake = _Wake(at)
        index = len(self._sleepers)
        while index and self._sleepers[index - 1].at > at:
            index -= 1
        self._sleepers.insert(index, wake)
        self._parked.set()
        return wake

    def _release_due(self) -> None:
        while self._sleepers and self._sleepers[0].at <= self.elapsed:
            wake = self._sleepers.pop(0)
            wake.listed = False
            self._woken.add(wake)
            wake.event.set()

    async def drive(self) -> None:
        # Moves the clock until cancelled, then release()s it.
        try:
            while True:
                while self._turning or self._woken:
                    self._quiet.clear()
                    await self._quiet.wait()
                    if self._turning or self._woken:  # one task between two turns of its compute: look again later
                        await asyncio.sleep_ms(_BUSY_RECHECK_MS)
                stalled = _flash_stall.stalled_ms
                if stalled != self._stalled:  # a flash hold: device time passed with nothing running, all at once
                    self.elapsed += max(0, stalled - self._stalled)
                    self._stalled = stalled
                    self._release_due()
                    continue
                host = _time.ticks_diff(_time.ticks_ms(), self._origin)
                if self._sleepers and self._sleepers[0].at <= host:
                    self.elapsed = max(self.elapsed, self._sleepers[0].at)
                    self._release_due()
                    continue
                self.elapsed = max(self.elapsed, host)
                self._parked.clear()
                if not self._sleepers:
                    await self._parked.wait()
                    continue
                # Not wait_for_ms(): after its timeout it awaits its runner task, and a cancel landing then goes to that
                # runner, so the drive would go on (extmod/asyncio/funcs.py:49-51, extmod/modasyncio.c:208-211, v1.29.0).
                alarm = asyncio.create_task(self._alarm(self._sleepers[0].at - host))
                try:
                    await self._parked.wait()
                finally:
                    alarm.cancel()
        finally:
            self.release()

    def install(self, modules: "Iterable[object]") -> int:
        # Lends each module this clock's sleeps, and its ticks where it reads any; the number of modules lent to.
        for module in modules:
            own = getattr(module, "time", None)
            if own is not None:
                module.time = _Ticks(self, own)  # type: ignore[attr-defined]  # a module attribute swap, as tests/_fake_time.py's
            self._saved.append((module, module.asyncio))  # type: ignore[attr-defined]
            module.asyncio = _Sleeps(self)  # type: ignore[attr-defined]
        return len(self._saved)

    def release(self) -> None:
        # Each module's real asyncio back and every parked sleep woken now; the lent ticks run on at the host's rate from
        # the instant reached, so no stored deadline steps.
        if self._released is not None:
            return
        self._released = (_time.ticks_ms(), self.elapsed)
        for module, real in self._saved:
            module.asyncio = real  # type: ignore[attr-defined]
        wakes, self._sleepers = self._sleepers, []
        for wake in wakes:
            wake.listed = False
            wake.event.set()

    async def sleep_ms(self, ms: int) -> None:
        # Refused as core.sleep_ms()'s ticks_add() refuses it; a zero or negative delay is one real turn, its task listed
        # meanwhile (a set of the tasks themselves, never a count: none can be in two turns at once).
        _time.ticks_add(self._origin, ms)
        if self._released is not None:
            await asyncio.sleep_ms(ms)
            return
        if ms <= 0:
            task = asyncio.current_task()
            self._turning.add(task)
            try:
                await asyncio.sleep_ms(0)
            finally:
                self._turning.discard(task)
                self._calm()
            return
        wake = self._park(self.elapsed + ms)
        try:
            await wake.event.wait()
        finally:
            if wake.listed:  # cancelled while parked
                wake.listed = False
                self._sleepers.remove(wake)
            elif self._released is None:  # released by the clock: this task runs now
                self._woken.discard(wake)
                self._calm()

    def ticks_ms(self) -> "_TicksMs":
        if self._released is None:
            return _time.ticks_add(self._origin, self.elapsed)
        return _time.ticks_add(self._origin, self._released[1] + _time.ticks_diff(_time.ticks_ms(), self._released[0]))
