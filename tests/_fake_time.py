"""Shared fake time sources: FakeTime (a local-time callback's hour and minute), DrivenTime (rp2's 2**30 ticks a test
advances, given modules' `time` for a block; with `sleeps`, their asyncio sleeps and wait_for()s run on it), Rp2Gmtime
(8-field gmtime()), tick() (a timer flag wake-up per call) and UTCValid (the boot's first NTP clock set for a block)."""

import asyncio
import asyncio.core as _core  # type: ignore[import-not-found]  # the run queue; no stub covers it
import time

from _fast_sleep import check_sleep_ms
from _ticks30 import Ticks30Time  # every 2**30 clock here is tests/_ticks30.py's Ticks30Time

import asy_base_classes

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    T = TypeVar("T")

_WALL_CLOCK = ("gmtime", "localtime", "mktime", "time")


class _DrivenAsyncio:
    # A module's `asyncio` under a driven clock: sleep()/sleep_ms() park until the clock reaches their wake and the
    # wait_for() bounds run on it; every other name is the real asyncio's, so tasks, locks and events stay real.
    def __init__(self, clock: "DrivenTime") -> None:
        self._clock = clock

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    def sleep(self, seconds: float) -> "Coroutine[object, object, None]":
        return self._clock._sleep_ms(int(seconds * 1000))  # as core.sleep(): sleep_ms(int(t * 1000))

    def sleep_ms(self, ms: int) -> "Coroutine[object, object, None]":
        return self._clock._sleep_ms(ms)

    def wait_for(self, aw: "Coroutine[object, object, T] | asyncio.Task[T]", timeout: "float | None") -> "Coroutine[object, object, T]":
        return self._clock._wait_ms(aw, None if timeout is None else int(timeout * 1000))

    def wait_for_ms(self, aw: "Coroutine[object, object, T] | asyncio.Task[T]", timeout_ms: int) -> "Coroutine[object, object, T]":
        return self._clock._wait_ms(aw, timeout_ms)


class _Wake:
    # One parked driven sleep: its virtual wake time and the event the clock sets then; `resumed` once its task ran on.
    def __init__(self, at: int) -> None:
        self.at = at
        self.event = asyncio.Event()
        self.listed = True
        self.resumed = False


class DrivenTime(Ticks30Time):
    # `now` and advance() as Ticks30Time's; inside the block each given module's `time` is this object. `strict`: any
    # wall-clock read raises (a test proving no RTC, time() or NTP value is used); every other name is the real module's.
    # `sleeps`: each module's `asyncio` is _DrivenAsyncio too, and elapse(), jump() and run_until() wake its sleepers.
    ROUNDS = 1000  # scheduler rounds one instant may take before a still-runnable task fails the test as a busy loop
    SLEEPERS = 64  # parked driven sleeps at once: one more fails the test rather than growing the list

    def __init__(self, *modules: object, now: int = 0, strict: bool = False, sleeps: bool = False) -> None:
        super().__init__(now)
        self._modules = modules
        self._saved: list[object] = []
        self._sleepers: list[_Wake] = []
        self._shim = _DrivenAsyncio(self) if sleeps else None
        self._strict = strict

    def __enter__(self) -> "DrivenTime":
        # With sleeps, a module that reads no clock (no `time`, saved as None) is lent none; without, it is refused.
        self._saved = [module.time if self._shim is None else getattr(module, "time", None) for module in self._modules]  # type: ignore[attr-defined]
        if self._shim is not None:
            self._saved += [module.asyncio for module in self._modules]  # type: ignore[attr-defined]  # and `asyncio`
        for index, module in enumerate(self._modules):
            if self._saved[index] is not None:
                module.time = self  # type: ignore[attr-defined]  # a module attribute swap, restored on exit
            if self._shim is not None:
                module.asyncio = self._shim  # type: ignore[attr-defined]  # likewise
        return self

    def __exit__(self, *_exc_info: object) -> None:
        count = len(self._modules)
        for index, module in enumerate(self._modules):
            if self._saved[index] is not None:
                module.time = self._saved[index]  # type: ignore[attr-defined]
            if self._shim is not None:
                module.asyncio = self._saved[count + index]  # type: ignore[attr-defined]

    def __getattr__(self, name: str) -> object:
        if self._strict and name in _WALL_CLOCK:
            raise AssertionError("the wall clock was read: time." + name)
        return getattr(time, name)

    def _park(self, ms: int) -> _Wake:
        # Lists a wake at now + ms after every one due no later, so equal times wake in the order they slept.
        if len(self._sleepers) >= self.SLEEPERS:
            raise AssertionError(f"more than {self.SLEEPERS} driven sleepers parked at virtual t={self.now} ms")
        wake = _Wake(self.now + ms)
        index = len(self._sleepers)
        while index and self._sleepers[index - 1].at > wake.at:
            index -= 1
        self._sleepers.insert(index, wake)
        return wake

    def _release_due(self) -> None:
        while self._sleepers and self._sleepers[0].at <= self.now:
            wake = self._sleepers.pop(0)
            wake.listed = False
            wake.event.set()

    async def _settle(self) -> None:
        # Yields until no task is due on the run queue: one parked on a real timed sleep (run()'s own bound) is not
        # runnable at this instant, so the queue's head is read against the real clock, as the loop itself reads it.
        for _ in range(self.ROUNDS):
            await _core.sleep_ms(0)
            head = _core._task_queue.peek()
            if head is None or time.ticks_diff(head.ph_key, time.ticks_ms()) > 0:
                return
        raise AssertionError(f"a task is still runnable after {self.ROUNDS} rounds at virtual t={self.now} ms: a busy loop")

    async def _sleep_ms(self, ms: int) -> None:
        # The delay refused as core.sleep_ms()'s ticks_add() refuses it on rp2: a float, or 2**29 ms and more. A zero or
        # negative sleep stays the real one-yield sleep, so the task never leaves the run queue.
        check_sleep_ms(ms)
        self.ticks_add(self.ticks_ms(), max(0, ms))
        if ms <= 0:
            await _core.sleep_ms(0)
            return
        wake = self._park(ms)
        try:
            await wake.event.wait()
        finally:
            self._unpark(wake)

    def _unpark(self, wake: _Wake) -> None:
        wake.resumed = True
        if wake.listed:
            self._sleepers.remove(wake)
            wake.listed = False

    async def _wait_ms(self, aw: "Coroutine[object, object, T] | asyncio.Task[T]", timeout_ms: "int | None") -> "T":
        # extmod/asyncio/funcs.py:7-51 (v1.29.0) with its sleep parked on this clock: the runner cancels the waiter only
        # while it still sleeps on the wake (parked, or released but not yet run), as that file's `waiter.data is None`,
        # so a cancel already pending on it stands. A zero bound is the real call.
        task: asyncio.Task[T] = aw if isinstance(aw, asyncio.Task) else asyncio.create_task(aw)  # as core._promote_to_task()
        if timeout_ms is None:
            return await task
        check_sleep_ms(timeout_ms)
        self.ticks_add(self.ticks_ms(), max(0, timeout_ms))  # the bound refused as its sleep_ms() would refuse it
        if timeout_ms <= 0:
            return await asyncio.wait_for_ms(task, timeout_ms)
        waiter = asyncio.current_task()
        assert waiter is not None  # wait_for() always runs inside a task
        wake = self._park(timeout_ms)
        runner = asyncio.create_task(_run(waiter, task, wake))
        try:
            await wake.event.wait()
        except asyncio.CancelledError as er:
            status = er.args[0] if er.args else None
            if status is None:
                runner.cancel()  # cancelled from outside: the awaited task goes too
                raise
            if isinstance(status, BaseException):
                raise status from None  # the awaited task's own failure
            return er.args[1]  # type: ignore[no-any-return]  # the awaited task's result, as funcs.py hands it on
        finally:
            self._unpark(wake)
        runner.cancel()
        await runner
        raise asyncio.TimeoutError

    def advance(self, ms: int) -> None:
        # Ticks30Time's move; a driven sleeper whose wake it passes is released, to run late at the caller's next yield.
        self.now += ms
        self._release_due()

    async def elapse(self, ms: int) -> None:
        # Moves the clock to each wake due within ms in order, letting what it wakes run there, then to now + ms.
        target = self.now + ms
        await self._settle()
        while self._sleepers and self._sleepers[0].at <= target:
            self.now = self._sleepers[0].at
            self._release_due()
            await self._settle()
        self.now = target

    async def jump(self, ms: int) -> None:
        # A stall: the clock moves by ms at once and every sleeper it passed wakes once, at the new time.
        await self._settle()
        self.advance(ms)
        await self._settle()

    async def run_until(self, condition: "Callable[[], bool]", limit_ms: int) -> int:
        # elapse() one wake at a time until condition() holds: the virtual ms it took, or a failure naming the time reached.
        start = self.now
        limit = start + limit_ms
        await self._settle()
        while not condition():
            if not self._sleepers or self._sleepers[0].at > limit:
                self.now = max(self.now, limit)
                await self._settle()
                if condition():
                    break
                raise AssertionError(f"run_until: the condition still fails at virtual t={self.now} ms, {limit_ms} ms after t={start}")
            self.now = self._sleepers[0].at
            self._release_due()
            await self._settle()
        return self.now - start

    def wakes(self) -> "list[int]":
        # The virtual wake time of every parked driven sleep, earliest first.
        return [wake.at for wake in self._sleepers]


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


async def _run(waiter: "asyncio.Task[object]", task: "asyncio.Task[object]", wake: _Wake) -> None:
    # funcs.py's runner: whatever ended the awaited task goes to a waiter still asleep, inside the CancelledError it gets.
    try:
        result = await task
        status: object = True
    except BaseException as er:  # every ending, its cancellation included, is the waiter's to raise
        result = None
        status = er
    data = waiter.data  # the wake's event queue while parked (event.py:33), None once released (a push resets it, modasyncio.c:118)
    if not wake.resumed and (data is None or data is wake.event.waiting) and waiter.cancel():  # type: ignore[attr-defined]  # Event's queue (event.py:11), in no stub
        waiter.data = asyncio.CancelledError(status, result)  # the field funcs.py sets


async def tick(flag: "asyncio.ThreadSafeFlag", times: int = 1, clock: "DrivenTime | None" = None, step_ms: int = 1000) -> None:
    # One wake-up of a loop waiting on `flag` per time, a given clock advanced by `step_ms` before each; the second
    # yield lets the woken iteration's own awaits settle before the caller checks it.
    for _ in range(times):
        if clock is not None:
            clock.advance(step_ms)
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
