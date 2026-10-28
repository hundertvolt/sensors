"""Self-test of tests/_fake_time.py's DrivenTime with driven sleeps: virtual time moves only on elapse(), jump(),
run_until() or advance(), sleepers wake in order and never early, wait_for() bounds fire on that clock, and every
replaced name is restored."""

import asyncio
import asyncio.core as _core  # type: ignore[import-not-found]  # the run queue; no stub covers it
import time

from _async_harness import cancel, cancel_all, run
from _fake_time import DrivenTime
from _ticks30 import TICKS_PERIOD

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable

# The real-time hang bound around each driven run: the clock itself fails a stalled one in virtual time first.
# @tunable l1.driven_time_run_bound_s = 5
_RUN_BOUND_S = 5


class _Module:
    # A product module stand-in: DrivenTime replaces its `time` and, with sleeps, its `asyncio` for the block.
    def __init__(self) -> None:
        self.time = time
        self.asyncio = asyncio


class _ClocklessModule:
    # A product module that reads no clock (asy_udp_socket): with sleeps only its `asyncio` is driven, and no `time` is lent.
    def __init__(self) -> None:
        self.asyncio = asyncio


async def _awaits(sleep: "Awaitable[None]") -> None:
    # A task of its own for a driven sleep: as on the board, a sleep is no coroutine that create_task() would take.
    await sleep


def _names(module: _Module) -> "tuple[object, object]":
    return module.time, module.asyncio


async def _periodic(module: _Module, period_ms: int, woke: "list[int]") -> None:
    while True:
        await module.asyncio.sleep_ms(period_ms)
        woke.append(module.time.ticks_ms())


async def _settling(module: _Module, steps: "list[str]") -> None:
    # A cleanup that sleeps, as an I2C probe's settle in its `finally`: a cancel in the first sleep waits out the second.
    try:
        await module.asyncio.sleep_ms(100)
        steps.append("written")
    finally:
        await module.asyncio.sleep_ms(100)
        steps.append(f"settled at {module.time.ticks_ms()}")


async def _sleeper(module: _Module, ms: int, tag: str, woke: "list[tuple[str, int]]") -> None:
    await module.asyncio.sleep_ms(ms)
    woke.append((tag, module.time.ticks_ms()))


async def _swallowing(module: _Module) -> None:
    # Takes its first cancel as no end and sleeps on, a cleanup longer than any bound; a second cancel ends it.
    try:
        await module.asyncio.sleep_ms(100)
    except asyncio.CancelledError:
        await module.asyncio.sleep_ms(1000)


def test_two_sleepers_wake_in_deadline_order_each_at_its_own_time() -> None:
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> None:
        tasks = [asyncio.create_task(_sleeper(module, 20, "late", woke)), asyncio.create_task(_sleeper(module, 10, "early", woke))]
        await clock.elapse(30)
        await cancel_all(tasks)

    with DrivenTime(module, sleeps=True) as clock:
        run(scenario(clock), _RUN_BOUND_S)
    assert woke == [("early", 10), ("late", 20)], woke
    assert clock.now == 30


def test_elapse_never_wakes_a_sleeper_before_its_deadline() -> None:
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> "tuple[list[tuple[str, int]], list[int]]":
        tasks = [asyncio.create_task(_sleeper(module, 100, "due", woke)), asyncio.create_task(_sleeper(module, 101, "next", woke))]
        await clock.elapse(100)
        after_100 = (list(woke), clock.wakes())
        await clock.elapse(1)
        await cancel_all(tasks)
        return after_100

    with DrivenTime(module, sleeps=True) as clock:
        after_100 = run(scenario(clock), _RUN_BOUND_S)
    assert after_100 == ([("due", 100)], [101]), after_100
    assert woke == [("due", 100), ("next", 101)], woke


def test_a_ticks_diff_across_the_2_30_wrap_equals_the_elapsed_virtual_time() -> None:
    module = _Module()
    seen: list[int] = []

    async def sleeper() -> None:
        seen.append(module.time.ticks_ms())
        await module.asyncio.sleep_ms(25)
        seen.append(module.time.ticks_ms())

    async def scenario(clock: DrivenTime) -> None:
        task = asyncio.create_task(sleeper())
        await clock.elapse(25)
        await cancel(task)

    with DrivenTime(module, now=TICKS_PERIOD - 10, sleeps=True) as clock:
        run(scenario(clock), _RUN_BOUND_S)
        assert seen == [TICKS_PERIOD - 10, 15], seen
        assert clock.ticks_diff(seen[1], seen[0]) == 25


def test_every_replaced_name_is_restored_when_the_block_raises() -> None:
    module, plain = _Module(), _Module()
    try:
        with DrivenTime(module, sleeps=True) as clock, DrivenTime(plain) as plain_clock:
            inside = _names(module) + _names(plain)
            assert module.asyncio.Lock is asyncio.Lock  # every other name is the real asyncio's
            raise ValueError("block failed")
    except ValueError:
        pass
    assert inside[0] is clock and inside[1] is not asyncio, inside
    assert inside[2:] == (plain_clock, asyncio), inside  # without sleeps the module's asyncio stays the real one
    assert _names(module) + _names(plain) == (time, asyncio, time, asyncio)


def test_a_module_without_a_clock_gets_driven_sleeps_and_no_time() -> None:
    module, plain = _ClocklessModule(), _ClocklessModule()

    async def scenario(clock: DrivenTime) -> bool:
        sleeper = asyncio.create_task(_awaits(module.asyncio.sleep_ms(10)))
        await clock.elapse(10)
        return sleeper.done()

    with DrivenTime(module, sleeps=True) as clock:
        inside = (hasattr(module, "time"), module.asyncio is asyncio)
        woke = run(scenario(clock), _RUN_BOUND_S)
    assert (inside, woke) == ((False, False), True), (inside, woke)
    assert not hasattr(module, "time") and module.asyncio is asyncio
    try:
        with DrivenTime(plain):  # without sleeps nothing would be driven, so a module with no `time` is still refused
            refused = False
    except AttributeError:
        refused = True
    assert refused


def test_wait_for_times_out_after_its_bound_and_not_before() -> None:
    module = _Module()
    ended: list[str] = []

    async def slow() -> None:
        try:
            await module.asyncio.sleep_ms(5000)
        finally:
            ended.append("inner ended")

    async def bounded(seconds: bool) -> str:
        try:
            if seconds:
                await module.asyncio.wait_for(slow(), 1)
            else:
                await module.asyncio.wait_for_ms(slow(), 250)
        except asyncio.TimeoutError:
            return f"timed out at {module.time.ticks_ms()}"
        return "returned"

    async def scenario(clock: DrivenTime, seconds: bool, bound_ms: int) -> "tuple[bool, str, list[str]]":
        task = asyncio.create_task(bounded(seconds))
        await clock.elapse(bound_ms - 1)
        pending = not task.done()
        await clock.elapse(1)
        if not task.done():
            await cancel(task)
            return pending, f"still pending at {clock.now}", list(ended)
        return pending, await task, list(ended)

    for seconds, bound_ms in ((True, 1000), (False, 250)):
        ended.clear()
        with DrivenTime(module, sleeps=True) as clock:
            outcome = run(scenario(clock, seconds, bound_ms), _RUN_BOUND_S)
            assert clock.wakes() == [], clock.wakes()
        assert outcome == (True, f"timed out at {bound_ms}", ["inner ended"]), (seconds, outcome)


def test_wait_for_hands_back_the_result_or_the_failure_that_came_first() -> None:
    module = _Module()

    async def answer(ms: int, value: int) -> int:
        await module.asyncio.sleep_ms(ms)
        if value < 0:
            raise ValueError(f"refused at {module.time.ticks_ms()}")
        return value

    async def bounded(value: int) -> str:
        try:
            got = await module.asyncio.wait_for_ms(answer(100, value), 1000)
        except ValueError as e:
            return str(e)
        return f"{got} at {module.time.ticks_ms()}"

    async def scenario(clock: DrivenTime) -> "list[object]":
        good = asyncio.create_task(bounded(7))
        bad = asyncio.create_task(bounded(-1))
        await clock.elapse(100)
        return [await good, await bad, clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == ["7 at 100", "refused at 100", []]


def test_a_cancelled_wait_for_cancels_what_it_awaits() -> None:
    module = _Module()
    ended: list[str] = []

    async def slow() -> None:
        try:
            await module.asyncio.sleep_ms(5000)
        except asyncio.CancelledError:
            ended.append("inner cancelled")
            raise

    async def scenario(clock: DrivenTime) -> "list[object]":
        task = asyncio.create_task(module.asyncio.wait_for_ms(slow(), 1000))
        await clock.elapse(10)
        task.cancel()
        try:
            await task
            outcome = "returned"
        except asyncio.CancelledError:
            outcome = "cancelled"
        await clock.elapse(2000)
        return [outcome, list(ended), clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == ["cancelled", ["inner cancelled"], []]


def test_a_cancel_landing_before_the_runner_runs_still_cancels_the_wait() -> None:
    # The awaited task has already ended, so the runner's first step finds it done; that step runs after the cancel and
    # before the waiter resumes, where funcs.py's `waiter.data is None` leaves the pending cancel alone.
    async def at_once() -> int:
        return 7

    async def waiting(module: _Module, done: "asyncio.Task[int]") -> str:
        return f"returned {await module.asyncio.wait_for_ms(done, 1000)}"

    async def scenario(module: _Module) -> str:
        done = asyncio.create_task(at_once())
        await done
        task = asyncio.create_task(waiting(module, done))
        await asyncio.sleep(0)  # one yield: the waiter parks on its bound, its runner queued but not yet run
        task.cancel()  # queues the waiter after the runner: equal ticks pop in push order (py/pairheap.h:89, stable)
        try:
            return await task
        except asyncio.CancelledError:
            return "cancelled"

    assert run(scenario(_Module()), _RUN_BOUND_S) == "cancelled"  # the real asyncio
    module = _Module()
    with DrivenTime(module, sleeps=True) as clock:
        outcome = run(scenario(module), _RUN_BOUND_S)
        assert clock.wakes() == [], clock.wakes()
    assert outcome == "cancelled", outcome


def test_a_result_ready_before_its_released_bound_has_run_still_wins() -> None:
    # The awaited task ends and the bound passes before the runner runs: the runner finds the waiter released but not
    # yet resumed, as funcs.py's `waiter.data is None` finds an expired sleep, and hands it the result.
    module = _Module()
    gate = asyncio.Event()

    async def gated() -> int:
        await gate.wait()
        return 7

    async def scenario(clock: DrivenTime) -> "list[object]":
        task = asyncio.create_task(module.asyncio.wait_for_ms(gated(), 100))
        await clock.elapse(0)  # the waiter parks on its bound and its runner awaits the gated task
        gate.set()
        await asyncio.sleep(0)  # the gated task ends and queues the runner, which has not run yet
        clock.advance(100)  # the bound passes now, queuing the waiter after the runner
        return [await task, clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == [7, []]


def test_a_cancelled_sleeper_leaves_the_queue_and_never_wakes() -> None:
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> "list[int]":
        task = asyncio.create_task(_sleeper(module, 50, "cancelled", woke))
        await clock.elapse(10)
        parked = clock.wakes()
        await cancel(task)
        await clock.elapse(100)
        return parked + clock.wakes()

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == [50]
    assert woke == []


def test_a_task_woken_off_its_driven_sleep_ends_that_sleep_at_once() -> None:
    # Task.cancel()'s move with no exception, as the twin WDT wakes its countdown: off the wake's queue and pushed to run,
    # the task ends its sleep there, as a run-queue sleep woken early does, and the clock lists the wake no more.
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> "list[object]":
        task = asyncio.create_task(_sleeper(module, 50, "early", woke))
        await clock.elapse(10)
        task.data.remove(task)  # the wake the task awaits (modasyncio.c task_attr)
        _core._task_queue.push(task)
        await asyncio.sleep(0)
        return [task.done(), clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        outcome = run(scenario(clock), _RUN_BOUND_S)
    assert (outcome, woke) == ([True, []], [("early", 10)]), (outcome, woke)


def test_a_cancel_through_the_clock_drives_the_sleep_the_cancelled_task_cleans_up_with() -> None:
    # A canceller that drives nothing never sees such a task end: its cleanup's wake waits on this clock alone.
    module = _Module()
    steps: list[str] = []

    async def scenario(clock: DrivenTime) -> "list[object]":
        task = asyncio.create_task(_settling(module, steps))
        await clock.elapse(10)
        await clock.cancel(task, 1000)
        return [task.done(), clock.now, clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        outcome = run(scenario(clock), _RUN_BOUND_S)
    assert (outcome, steps) == ([True, 110, []], ["settled at 110"]), (outcome, steps)


def test_a_cancelled_task_that_outlasts_the_bound_fails_naming_the_virtual_time() -> None:
    module = _Module()

    async def scenario(clock: DrivenTime) -> str:
        task = asyncio.create_task(_swallowing(module))
        await clock.elapse(10)
        try:
            await clock.cancel(task, 500)
            said = "ended"
        except AssertionError as e:
            said = str(e)
        await cancel(task)
        return said

    with DrivenTime(module, sleeps=True) as clock:
        said = run(scenario(clock), _RUN_BOUND_S)
    assert said.endswith("never ended - run_until: the condition still fails at virtual t=510 ms, 500 ms after t=10"), said


def test_a_driven_sleep_is_its_listed_wake_from_the_call_on() -> None:
    # As core.sleep_ms() hands back its singleton, a driven sleep is no coroutine: the clock lists the wake at the call,
    # and the task awaiting it parks on it until the clock passes it, with no frame or Event built for the sleep.
    module = _Module()

    async def scenario(clock: DrivenTime) -> "list[object]":
        sleep = module.asyncio.sleep_ms(5)
        listed = clock.wakes()
        task = asyncio.create_task(_awaits(sleep))
        await clock.elapse(4)
        early = task.done()
        await clock.elapse(1)
        return [hasattr(sleep, "send"), listed, early, task.done(), clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        outcome = run(scenario(clock))
    assert outcome == [False, [5], False, True, []], outcome


def test_a_wake_its_awaiter_closes_or_throws_into_leaves_the_queue() -> None:
    # However an awaiter lets go of a parked wake, a close or an exception as a cancel does, the clock lists it no more.
    clock = DrivenTime(sleeps=True)
    closed, thrown = clock._park(5), clock._park(7)
    listed = clock.wakes()
    closed.close()
    try:
        thrown.throw(ValueError("let go"))
        said = "not raised"
    except ValueError as e:
        said = str(e)
    assert (listed, clock.wakes(), said) == ([5, 7], [], "let go"), (listed, clock.wakes(), said)


def test_run_until_stops_at_the_first_wake_that_makes_the_predicate_hold() -> None:
    module = _Module()
    woke: list[int] = []

    async def scenario(clock: DrivenTime) -> int:
        task = asyncio.create_task(_periodic(module, 100, woke))
        took = await clock.run_until(lambda: len(woke) >= 3, 1000)
        await cancel(task)
        return took

    with DrivenTime(module, now=5, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == 300
        assert clock.now == 305
    assert woke == [105, 205, 305], woke


def test_run_until_takes_a_wake_at_its_limit_and_fails_past_it_naming_the_virtual_time() -> None:
    module = _Module()

    async def scenario(clock: DrivenTime, due_ms: int) -> str:
        woke: list[tuple[str, int]] = []
        task = asyncio.create_task(_sleeper(module, due_ms, "once", woke))
        try:
            took = await clock.run_until(lambda: bool(woke), 500)
        except AssertionError as e:
            return str(e)
        finally:
            await cancel(task)
        return f"held after {took}"

    for due_ms, said in ((500, "held after 500"), (501, "run_until: the condition still fails at virtual t=500 ms, 500 ms after t=0")):
        with DrivenTime(module, sleeps=True) as clock:
            assert run(scenario(clock, due_ms), _RUN_BOUND_S) == said, (due_ms, said)


def test_jump_wakes_each_overdue_sleeper_once_at_the_jumped_time() -> None:
    module = _Module()
    ticks: list[int] = []
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> "list[int]":
        task = asyncio.create_task(_periodic(module, 1, ticks))
        once = [asyncio.create_task(_sleeper(module, 10_000, "at the target", woke)), asyncio.create_task(_sleeper(module, 10_001, "past it", woke))]
        await clock.jump(10_000)
        parked = clock.wakes()
        await cancel(task)
        await clock.elapse(1)
        await cancel_all(once)
        return parked

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == [10_001, 10_001]
        assert clock.now == 10_001, clock.now
    assert ticks == [10_000], ticks  # one wake for ten thousand periods: a stall, not a replay
    assert woke == [("at the target", 10_000), ("past it", 10_001)], woke


def test_a_plain_advance_releases_a_due_sleeper_late_never_early() -> None:
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> "list[tuple[str, int]]":
        task = asyncio.create_task(_sleeper(module, 100, "late", woke))
        await asyncio.sleep(0)
        clock.advance(99)
        await asyncio.sleep(0)
        early = list(woke)
        clock.advance(51)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await cancel(task)
        return early

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == []
    assert woke == [("late", 150)], woke


def test_a_busy_loop_fails_at_the_round_cap_naming_the_virtual_time() -> None:
    module = _Module()

    async def busy() -> None:
        while True:
            await module.asyncio.sleep(0)

    async def scenario(clock: DrivenTime) -> str:
        task = asyncio.create_task(busy())
        try:
            await clock.elapse(5)
        except AssertionError as e:
            return str(e)
        finally:
            await cancel(task)
        return "elapsed"

    with DrivenTime(module, now=1234, sleeps=True) as clock:
        said = run(scenario(clock), _RUN_BOUND_S)
    assert said == f"a task is still runnable after {DrivenTime.ROUNDS} rounds at virtual t=1234 ms: a busy loop", said


def test_the_parked_sleeper_queue_is_bounded() -> None:
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> str:
        tasks = [asyncio.create_task(_sleeper(module, 10, "parked", woke)) for _ in range(DrivenTime.SLEEPERS)]
        await clock.elapse(0)  # each one runs and parks
        try:
            await module.asyncio.sleep_ms(10)
        except AssertionError as e:
            return str(e)
        finally:
            await cancel_all(tasks)
        return "parked one more"

    with DrivenTime(module, sleeps=True) as clock:
        said = run(scenario(clock), _RUN_BOUND_S)
    assert said == f"more than {DrivenTime.SLEEPERS} driven sleepers parked at virtual t=0 ms", said
    assert woke == []


def test_a_zero_sleep_is_one_real_yield_and_a_float_sleep_ms_is_refused() -> None:
    module = _Module()

    async def scenario(clock: DrivenTime) -> "list[object]":
        await module.asyncio.sleep_ms(0)
        await module.asyncio.sleep(0)
        await module.asyncio.sleep_ms(-5)  # the real sleep_ms() clamps a negative delay to 0
        try:
            await module.asyncio.sleep_ms(2.0)  # a float on purpose: the device refuses it
            refused = "no error"
        except TypeError as e:
            refused = str(e)
        return [clock.now, clock.wakes(), refused]

    with DrivenTime(module, sleeps=True) as clock:
        assert run(scenario(clock), _RUN_BOUND_S) == [0, [], "can't convert float to int"]


def test_a_driven_sleep_or_bound_refuses_a_delay_rp2s_ticks_cannot_hold() -> None:
    # sleep_ms() hands its delay to ticks_add(), which refuses 2**29 ms and more on rp2's 2**30 period
    # (extmod/modtime.c:177-191, v1.29.0): the driven clock refuses it as the board does, never parks it.
    module = _Module()

    async def instant() -> int:
        return 1

    async def refused(bound: bool) -> str:
        try:
            if bound:
                await module.asyncio.wait_for_ms(instant(), 1 << 29)
            else:
                await module.asyncio.sleep_ms(1 << 29)
        except OverflowError as e:
            return str(e)
        return "accepted"

    async def scenario(clock: DrivenTime) -> "list[object]":
        longest = asyncio.create_task(_awaits(module.asyncio.sleep_ms((1 << 29) - 1)))
        await clock.elapse(0)
        parked = clock.wakes()
        await cancel(longest)
        return [parked, await refused(False), await refused(True), clock.wakes()]

    with DrivenTime(module, sleeps=True) as clock:
        said = run(scenario(clock), _RUN_BOUND_S)
    assert said == [[(1 << 29) - 1], "ticks interval overflow", "ticks interval overflow", []], said


def test_release_runs_the_clock_on_at_the_real_rate_and_wakes_each_parked_sleep_after_its_time_left() -> None:
    # Released at 100 ms, a sleeper parked until 300 ms wakes after 200 real ms, its stamp on the same clock; the module's
    # asyncio is the real one again, and the driven clock refuses to move once released.
    module = _Module()
    woke: list[tuple[str, int]] = []

    async def scenario(clock: DrivenTime) -> "tuple[int, bool, str]":
        task = asyncio.create_task(_sleeper(module, 300, "parked", woke))
        await clock.elapse(100)
        clock.release()
        start = time.ticks_ms()
        await task
        real_ms = time.ticks_diff(time.ticks_ms(), start)
        try:
            await clock.elapse(1)
        except AssertionError as e:
            return real_ms, module.asyncio is asyncio, str(e)
        return real_ms, module.asyncio is asyncio, "moved after release"

    with DrivenTime(module, sleeps=True) as clock:
        real_ms, restored, refused = run(scenario(clock), _RUN_BOUND_S)
        assert clock.wakes() == [], clock.wakes()
    assert 199 <= real_ms < 2000, f"the parked sleep ended {real_ms} real ms after release, not after the 200 it had left"
    assert len(woke) == 1 and 300 <= woke[0][1] < 300 + real_ms, woke
    assert restored, "the module's asyncio is still the driven one after release()"
    assert "after release()" in refused, refused


def test_a_bound_parked_at_release_keeps_awaiting_its_task_and_ends_on_the_real_clock() -> None:
    # Released at 100 ms: a 300 ms bound around a 150 ms sleep hands back the result; a 200 ms bound around a 5 s sleep
    # times out after the 100 ms it had left, and the sleep it awaited ends with it.
    module = _Module()
    ended: list[str] = []

    async def inner(ms: int) -> str:
        try:
            await module.asyncio.sleep_ms(ms)
            return f"slept {ms}"
        finally:
            ended.append(f"inner {ms} ended")

    async def bounded(ms: int, bound_ms: int) -> str:
        try:
            result: str = await module.asyncio.wait_for_ms(inner(ms), bound_ms)
        except asyncio.TimeoutError:
            return f"timed out at {module.time.ticks_ms()}"
        return result

    async def scenario(clock: DrivenTime) -> "list[str]":
        tasks = [asyncio.create_task(bounded(150, 300)), asyncio.create_task(bounded(5000, 200))]
        await clock.elapse(100)
        clock.release()
        results = []
        for task in tasks:  # no await inside a comprehension: MicroPython compiles one as its own function
            results.append(await task)
        return results

    with DrivenTime(module, sleeps=True) as clock:
        outcome = run(scenario(clock), _RUN_BOUND_S)
    assert outcome[0] == "slept 150", outcome
    assert outcome[1].startswith("timed out at ") and 200 <= int(outcome[1].split()[-1]) < 2000, outcome
    assert sorted(ended) == ["inner 150 ended", "inner 5000 ended"], ended


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
