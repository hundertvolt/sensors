"""Unit tests for digital_twin/_driven_clock.py: the clock the twin runner's --test-uart-driven-clock puts the UART
link's modules on, whose virtual time reaches the host's only while none of their tasks is runnable, a flash hold
excepted."""

import asyncio
import sys
import time

sys.path.insert(0, "digital_twin")  # the twin's own modules: the clock and the flash-hold model it reads

import _flash_stall
import microtest
from _async_harness import run
from _driven_clock import DrivenClock

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    T = TypeVar("T")

# @tunable l2.driven_clock_run_limit_s = 10
_RUN_LIMIT_S = 10
# Scenario timings, virtual ms unless named host: test inputs, none a bound on how long a run may take.
_SLEEP_MS = 30
_POLL_MS = 2  # the waiter's round, as dev's link polls inside a transaction
_DEADLINE_MS = 100
_ANSWER_AT_MS = 10
_HOST_STALL_MS = _DEADLINE_MS + 50  # host ms, past the deadline: a deschedule, nothing the device does
_HOLD_AT_MS = 20  # a typical flush's hold starts here and outlasts the deadline (digital_twin/_flash_stall.py)
_COMPUTE_ROUNDS = 100  # each a 1 ms host step, then a turn on the loop
_PARKED_MS = 10_000_000  # a sleep no run here reaches
_END_ROUNDS = 20  # scheduler rounds a cancelled driver gets to end in: its own and its alarm's few

microtest.after_each(_flash_stall.reset_test_state)


class _Module:
    # Stands in for a product module holding `time` and `asyncio`, as the UART link's modules do.
    def __init__(self, *, with_time: bool = True) -> None:
        if with_time:
            self.time = time
        self.asyncio = asyncio


async def _answered_within(module: _Module, answered: "list[bool]", deadline_ms: int) -> bool:
    # A transaction's wait as the UART driver's ready() runs it: the answer first, then the deadline, then a round's sleep.
    t0 = module.time.ticks_ms()  # the clock's ticks, lent by install()
    while True:
        if answered:
            return True
        if time.ticks_diff(module.time.ticks_ms(), t0) > deadline_ms:
            return False
        await module.asyncio.sleep_ms(_POLL_MS)


async def _on_clock(module: _Module, scenario: "Callable[[DrivenClock], Coroutine[object, object, T]]") -> "T":
    # `scenario` with `module` on a driven clock whose driver runs beside it, released after.
    clock = DrivenClock()
    clock.install([module])
    driver = asyncio.create_task(clock.drive())
    try:
        return await scenario(clock)
    finally:
        driver.cancel()
        try:
            await driver
        except asyncio.CancelledError:  # the expected end; anything else is a real failure
            pass


def test_a_sleep_wakes_at_its_virtual_time_and_never_before_the_host_reaches_it() -> None:
    module = _Module()

    async def scenario(clock: DrivenClock) -> "tuple[int, int, int]":
        t0 = module.time.ticks_ms()
        await module.asyncio.sleep_ms(_SLEEP_MS)
        # The host read from the clock's origin, not from t0: virtual time lags the host while a task is runnable.
        return time.ticks_diff(module.time.ticks_ms(), t0), clock.elapsed, time.ticks_diff(time.ticks_ms(), clock._origin)

    slept, virtual, host = run(_on_clock(module, scenario), _RUN_LIMIT_S)
    assert slept == _SLEEP_MS, f"a {_SLEEP_MS} ms sleep woke at virtual +{slept} ms"
    assert host >= virtual, f"virtual time ran ahead of the host: {virtual} virtual ms at {host} host ms from the origin"


def test_sleeps_due_at_one_time_wake_in_the_order_they_slept() -> None:
    module = _Module()
    order: list[int] = []

    async def sleeper(index: int) -> None:
        await module.asyncio.sleep_ms(_SLEEP_MS)
        order.append(index)

    async def scenario(_clock: DrivenClock) -> None:
        tasks = [asyncio.create_task(sleeper(index)) for index in range(3)]
        for task in tasks:
            await task

    run(_on_clock(module, scenario), _RUN_LIMIT_S)
    assert order == [0, 1, 2], f"three sleeps due at one time woke in the order {order}"


def test_a_tasks_compute_and_its_turns_on_the_loop_spend_no_virtual_time() -> None:
    # A parked sleep keeps the driver moving meanwhile; the computing task reads the clock before it next waits.
    module = _Module()

    async def scenario(_clock: DrivenClock) -> "tuple[int, int]":
        other = asyncio.create_task(module.asyncio.sleep_ms(_ANSWER_AT_MS))
        t0, h0 = module.time.ticks_ms(), time.ticks_ms()
        for _ in range(_COMPUTE_ROUNDS):
            time.sleep_ms(1)  # a compute step holding the host
            await module.asyncio.sleep_ms(0)  # its turn on the loop
        spent, host = time.ticks_diff(module.time.ticks_ms(), t0), time.ticks_diff(time.ticks_ms(), h0)
        await other
        return spent, host

    spent, host = run(_on_clock(module, scenario), _RUN_LIMIT_S)
    assert host >= _COMPUTE_ROUNDS, f"the compute took only {host} host ms"
    assert spent == 0, f"{_COMPUTE_ROUNDS} compute rounds ({host} host ms) spent {spent} virtual ms"


def test_a_host_stall_before_an_answer_spends_none_of_the_deadline_the_answer_beats() -> None:
    # The answerer holds the host past the waiter's deadline, then answers at its next wake: on the host's clock, or with
    # the stall's host time spent before that wake, the waiter gives up first.
    module = _Module()
    answered: list[bool] = []

    async def answer() -> None:
        await module.asyncio.sleep_ms(_ANSWER_AT_MS)
        time.sleep_ms(_HOST_STALL_MS)
        await module.asyncio.sleep_ms(_ANSWER_AT_MS)
        answered.append(True)

    async def scenario(_clock: DrivenClock) -> bool:
        task = asyncio.create_task(answer())
        got = await _answered_within(module, answered, _DEADLINE_MS)
        await task
        return got

    assert run(_on_clock(module, scenario), _RUN_LIMIT_S) is True, f"a {_HOST_STALL_MS} ms host stall spent the waiter's {_DEADLINE_MS} ms deadline"


def test_a_flash_hold_spends_the_deadline_it_outlasts() -> None:
    # rp2 programs flash with interrupts off: no task runs for the hold, so every sleeper it passed wakes at its end and
    # the waiter, earliest, finds its deadline spent before the answerer can run.
    module = _Module()
    answered: list[bool] = []
    hold_ms = _flash_stall.flush_us(0) // 1000

    async def hold() -> None:
        await module.asyncio.sleep_ms(_HOLD_AT_MS)
        _flash_stall.stall(0)

    async def answer() -> None:
        await module.asyncio.sleep_ms(_HOLD_AT_MS * 2)
        answered.append(True)

    async def scenario(clock: DrivenClock) -> "tuple[bool, int]":
        tasks = [asyncio.create_task(hold()), asyncio.create_task(answer())]
        got = await _answered_within(module, answered, _DEADLINE_MS)
        for task in tasks:
            await task
        return got, clock.elapsed

    assert _HOLD_AT_MS + hold_ms > _DEADLINE_MS, f"the hold ({hold_ms} ms) does not outlast the deadline"
    got, elapsed = run(_on_clock(module, scenario), _RUN_LIMIT_S)
    assert got is False, f"a {hold_ms} ms flash hold at virtual {_HOLD_AT_MS} ms left the {_DEADLINE_MS} ms deadline unspent"
    assert elapsed >= _HOLD_AT_MS + hold_ms, f"the clock reached {elapsed} virtual ms, short of the hold's end"


def test_a_task_outside_the_lent_modules_that_never_stops_being_runnable_does_not_hold_the_clock() -> None:
    # Only the lent modules' compute stops it: a busy webserver beside the link must not freeze the link's time.
    module = _Module()
    spinning = [True]

    async def busy() -> None:
        while spinning[0]:
            await asyncio.sleep_ms(0)

    async def scenario(_clock: DrivenClock) -> int:
        spinner = asyncio.create_task(busy())
        t0 = module.time.ticks_ms()
        await module.asyncio.sleep_ms(_SLEEP_MS)
        woke = time.ticks_diff(module.time.ticks_ms(), t0)  # read at the wake: past it, the clock follows the host again
        spinning[0] = False
        await spinner
        return woke

    assert run(_on_clock(module, scenario), _RUN_LIMIT_S) == _SLEEP_MS, "a spinning task outside the lent modules held the clock"


def test_a_float_delay_is_refused_as_the_real_sleep_refuses_it() -> None:
    module = _Module()

    async def refusal(sleep_ms: "Callable[[float], Coroutine[object, object, None]]") -> str:
        try:
            await sleep_ms(1.5)
        except TypeError as e:
            return type(e).__name__
        return "accepted"

    async def scenario(_clock: DrivenClock) -> "tuple[str, str]":
        return await refusal(asyncio.sleep_ms), await refusal(module.asyncio.sleep_ms)

    real, lent = run(_on_clock(module, scenario), _RUN_LIMIT_S)
    assert real == lent == "TypeError", f"a 1.5 ms delay: the real sleep {real}, the lent one {lent}"


def test_only_what_the_uart_modules_use_is_lent_and_a_module_without_time_gets_the_sleeps_alone() -> None:
    timed, untimed = _Module(), _Module(with_time=False)
    clock = DrivenClock()
    assert clock.install([timed, untimed]) == 2
    assert timed.asyncio is not asyncio and untimed.asyncio is not asyncio, "a module's asyncio was not lent"
    assert timed.time is not time and not hasattr(untimed, "time"), "a module's time was lent wrongly"
    assert timed.asyncio.get_event_loop is asyncio.get_event_loop
    assert timed.time.ticks_diff is time.ticks_diff, "the module's own ticks_diff() was not kept"
    assert not hasattr(timed.asyncio, "wait_for_ms"), "the lent asyncio holds a name the UART modules do not use"
    clock.release()
    assert timed.asyncio is asyncio and untimed.asyncio is asyncio, "release() did not hand the real asyncio back"


def test_a_cancel_landing_as_the_drivers_timed_wait_ends_still_ends_the_drive() -> None:
    # asyncio.wait_for_ms() awaits its runner task after its timeout, and a cancel landing then went to that runner: the
    # drive went on and a booted twin's shutdown hung. The cancel lands once the driver awaits a task, or at the wake.
    module = _Module()

    async def go() -> "tuple[bool, bool]":
        clock = DrivenClock()
        clock.install([module])
        driver = asyncio.create_task(clock.drive())
        sleeper = asyncio.create_task(module.asyncio.sleep_ms(_SLEEP_MS))
        t0 = time.ticks_ms()
        while not isinstance(driver.data, type(driver)) and time.ticks_diff(time.ticks_ms(), t0) < 2 * _SLEEP_MS:
            await asyncio.sleep_ms(0)
        driver.cancel()
        for _ in range(_END_ROUNDS):
            if driver.done():
                break
            await asyncio.sleep_ms(0)
        ended = driver.done()
        if not ended:  # the drive went on: end it and hand the module back, so the failure below names the cause
            clock.release()
            driver.cancel()
        await sleeper
        return ended, module.asyncio is asyncio

    ended, handed_back = run(go(), _RUN_LIMIT_S)
    assert ended, f"a cancel of the driver at its timed wait's end did not end the drive within {_END_ROUNDS} rounds"
    assert handed_back, "the drive's end did not hand the real asyncio back"


def test_release_hands_the_sleeps_back_wakes_every_parked_one_and_steps_no_tick() -> None:
    module = _Module()

    async def go() -> "tuple[bool, bool, int]":
        clock = DrivenClock()
        clock.install([module])
        driver = asyncio.create_task(clock.drive())
        sleeper = asyncio.create_task(module.asyncio.sleep_ms(_PARKED_MS))
        await asyncio.sleep_ms(0)
        before = module.time.ticks_ms()
        driver.cancel()
        try:
            await driver
        except asyncio.CancelledError:  # the expected end; anything else is a real failure
            pass
        await asyncio.sleep_ms(0)  # the woken sleeper's turn
        woken = sleeper.done()
        if not woken:
            sleeper.cancel()
        return module.asyncio is asyncio, woken, time.ticks_diff(module.time.ticks_ms(), before)

    handed_back, woken, step = run(go(), _RUN_LIMIT_S)
    assert handed_back, "the driver's end did not hand the real asyncio back"
    assert woken, "a parked sleep stayed parked after the release"
    assert step >= 0, f"the ticks stepped back by {-step} ms at the release"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
