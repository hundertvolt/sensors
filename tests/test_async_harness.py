"""tests/_async_harness.py: run() and run_timed() refuse to nest inside a running loop, end every task they created
whatever the coroutine does, name the ones they cannot end and keep no finished one; run_to_interrupt() refuses as well;
cancel() and cancel_all() end a task and wait for it."""

import asyncio
import asyncio.core as _core  # type: ignore[import-not-found]  # the scheduler queues; no stub covers them
import gc
import os
import sys
from time import ticks_diff, ticks_ms

import _async_harness
from _async_harness import cancel, cancel_all, run, run_timed, run_to_interrupt
from _tmp_scratch import TmpScratch

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine

_scratch = TmpScratch("async_harness")


class _Reboot(BaseException):  # stands in for the fakes' simulated reset, a BaseException
    pass


def _growth_over_awaited_tasks(*, keep: bool) -> int:
    # The heap a run gains over 100 created-and-awaited tasks, the test itself holding on to them or not.
    async def work() -> None:
        await asyncio.sleep(0)

    async def scenario() -> int:
        for _ in range(10):
            await asyncio.create_task(work())
        gc.collect()
        before = gc.mem_alloc()
        kept = []
        for _ in range(100):
            task = asyncio.create_task(work())
            await task
            if keep:
                kept.append(task)
        gc.collect()
        return gc.mem_alloc() - before

    return run(scenario())


def _scheduler_empty() -> bool:
    return _core._task_queue.peek() is None and not _core._io_queue.map


async def _sleeper() -> None:
    await asyncio.sleep(3600)


def _unended_message(coro: "Coroutine[object, object, None]", limit_ms: int) -> "tuple[str, int]":
    # run()'s RuntimeError for a task it could not end, and the run's milliseconds, under the reap bound `limit_ms`.
    saved = _async_harness._REAP_LIMIT_MS
    _async_harness._REAP_LIMIT_MS = limit_ms
    start = ticks_ms()
    try:
        run(coro)
    except RuntimeError as e:
        return str(e), ticks_diff(ticks_ms(), start)
    finally:
        _async_harness._REAP_LIMIT_MS = saved
    raise AssertionError("a task the reap could not end passed the run")


def test_run_returns_the_coroutines_value_and_a_bound_raises_timeout() -> None:
    async def answer() -> int:
        await asyncio.sleep(0)
        return 42

    assert run(answer()) == 42
    assert run(answer(), 5) == 42
    raised = False
    try:
        run(_sleeper(), 0.01)
    except asyncio.TimeoutError:
        raised = True
    assert raised
    assert _scheduler_empty()


def test_run_timed_bounds_the_coroutine_and_leaves_nothing_parked() -> None:
    raised = False
    try:
        run_timed(_sleeper(), 0.01)
    except asyncio.TimeoutError:
        raised = True
    assert raised
    assert _scheduler_empty()


def test_three_sleepers_the_coroutine_spawned_are_gone_after_run() -> None:
    tasks: list[asyncio.Task[None]] = []

    async def main() -> None:
        tasks.extend(asyncio.create_task(_sleeper()) for _ in range(3))
        await asyncio.sleep(0)

    run(main())
    assert len(tasks) == 3
    assert all(task.done() for task in tasks)
    assert _scheduler_empty()


def test_a_raising_coroutine_still_cancels_its_children() -> None:
    tasks: list[asyncio.Task[None]] = []

    async def main() -> None:
        tasks.append(asyncio.create_task(_sleeper()))
        await asyncio.sleep(0)
        raise ValueError("main failed")

    raised = ""
    try:
        run(main())
    except ValueError as e:
        raised = str(e)
    assert raised == "main failed"
    assert tasks[0].done()
    assert _scheduler_empty()


def test_a_child_raising_while_cancelled_fails_the_run() -> None:
    async def stubborn() -> None:
        try:
            await asyncio.sleep(3600)
        finally:
            raise OSError(5, "cleanup failed")  # the failure under test is the one raised on the way out

    left: list[asyncio.Task[None]] = []

    async def main() -> None:
        left.append(asyncio.create_task(stubborn()))
        await asyncio.sleep(0)

    raised = ""
    try:
        run(main())
    except OSError as e:
        raised = str(e)
    assert "cleanup failed" in raised
    assert _scheduler_empty()


def test_a_base_exception_ending_the_loop_leaves_a_later_run_possible() -> None:
    # A simulated reset escapes asyncio's loop with the raising task still marked running: the next run() must start.
    async def resets() -> None:
        await asyncio.sleep(0)
        raise _Reboot

    left: list[asyncio.Task[None]] = []

    async def main() -> None:
        left.append(asyncio.create_task(_sleeper()))
        await resets()

    raised = False
    try:
        run(main())
    except _Reboot:
        raised = True
    assert raised

    async def answer() -> int:
        return 7

    assert run(answer()) == 7
    assert _scheduler_empty()


def test_a_task_awaiting_the_one_a_base_exception_left_mid_step_is_ended() -> None:
    # Task.cancel() forwards to the awaited task, which the reset left unresumable: the waiter is cancelled on its own.
    async def resets() -> None:
        await asyncio.sleep(0)
        raise _Reboot

    async def waits_on(task: "asyncio.Task[None]") -> None:
        await task

    waiters: list[asyncio.Task[None]] = []

    async def main() -> None:
        child = asyncio.create_task(resets())
        waiters.append(asyncio.create_task(waits_on(child)))
        await asyncio.sleep(3600)

    raised = False
    try:
        run(main())
    except _Reboot:
        raised = True
    assert raised
    assert waiters[0].done()
    assert _scheduler_empty()


def test_a_task_whose_awaited_task_swallows_its_cancellation_is_still_ended() -> None:
    async def swallows() -> None:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            return

    async def carries_on(task: "asyncio.Task[None]") -> None:
        await task
        await asyncio.sleep(3600)

    outer: list[asyncio.Task[None]] = []

    async def main() -> None:
        outer.append(asyncio.create_task(carries_on(asyncio.create_task(swallows()))))
        await asyncio.sleep(0)

    run(main())
    assert outer[0].done()
    assert _scheduler_empty()


def test_a_task_nothing_can_wake_is_named_and_taken_off_without_waiting_out_the_bound() -> None:
    never = asyncio.Event()

    async def stuck() -> None:
        try:
            await asyncio.sleep(3600)
        finally:
            await never.wait()

    left: list[asyncio.Task[None]] = []

    async def main() -> None:
        left.append(asyncio.create_task(stuck()))
        await asyncio.sleep(0)

    message, took_ms = _unended_message(main(), 60_000)
    assert "'stuck'" in message, message
    assert took_ms < 60_000, took_ms
    assert not left[0].done()  # named and taken off, not ended: nothing could end it
    assert _scheduler_empty()


def test_a_task_running_on_after_its_cancellation_is_named_once_the_bound_passes() -> None:
    async def stubborn() -> None:
        while True:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                pass

    left: list[asyncio.Task[None]] = []

    async def main() -> None:
        left.append(asyncio.create_task(stubborn()))
        await asyncio.sleep(0)

    message, _took_ms = _unended_message(main(), 5)
    assert "'stubborn'" in message, message
    assert not left[0].done()
    assert _scheduler_empty()


def test_a_run_keeps_no_task_that_has_finished() -> None:
    # The same 100 awaited tasks with and without the test holding them: held, they show; released, the run frees them.
    held, released = _growth_over_awaited_tasks(keep=True), _growth_over_awaited_tasks(keep=False)
    assert released * 4 < held, (held, released)


def test_release_finished_leaves_the_running_call_tracking_only_its_unfinished_tasks() -> None:
    # Five finished tasks stay below the first compaction; a heap reading inside a run needs them gone.
    async def finishes() -> None:
        await asyncio.sleep(0)

    async def sleeps() -> None:
        await asyncio.sleep(3600)

    async def main() -> "tuple[int, bool]":
        for _ in range(5):
            await asyncio.create_task(finishes())
        sleeper = asyncio.create_task(sleeps())
        before = len(_async_harness._tracked)  # the run's own main task is tracked too
        _async_harness.release_finished()
        kept = _async_harness._tracked
        unfinished = sleeper in kept and not any(task.done() for task in kept)
        dropped = before - len(kept)
        await cancel(sleeper)
        return dropped, unfinished

    assert run(main()) == (5, True)


def test_a_task_already_due_when_the_run_returns_takes_its_step_before_the_reap() -> None:
    # The board's loop never stops: work the coroutine queued and left ready (a deferred flush) still runs once.
    stepped: list[bool] = []

    async def records() -> None:
        stepped.append(True)

    async def main() -> "asyncio.Task[None]":
        return asyncio.create_task(records())

    task = run(main())
    assert stepped == [True]
    assert task.done()
    assert _scheduler_empty()


def test_create_task_is_the_real_one_again_after_run_on_every_path() -> None:
    real, real_core = asyncio.create_task, _core.create_task

    async def fails() -> None:
        raise ValueError("x")

    try:
        run(fails())
    except ValueError:
        pass
    assert asyncio.create_task is real
    assert _core.create_task is real_core


def test_cancel_and_cancel_all_end_their_tasks_and_wait_for_them() -> None:
    async def main() -> "list[bool]":
        one = asyncio.create_task(_sleeper())
        many = [asyncio.create_task(_sleeper()) for _ in range(2)]
        await asyncio.sleep(0)
        await cancel(one)
        await cancel_all(many)
        return [one.done()] + [task.done() for task in many]

    assert run(main()) == [True, True, True]


def test_run_from_inside_a_coroutine_is_refused_not_crashed() -> None:
    # The nested call ends with no running task while the outer coroutine still runs: its next await crashes the port.
    # run()'s nesting case runs in a child interpreter, where the crash the refusal prevents ends only it.
    where = _scratch.dir()
    script = where + "nested.py"
    out = where + "out.txt"
    with open(script, "w") as f:
        f.write(
            "import asyncio\nfrom _async_harness import run\n\n\n"
            "async def _sleeper():\n    await asyncio.sleep(3600)\n\n\n"
            "async def _inner():\n    return 1\n\n\n"
            "async def _outer():\n    asyncio.create_task(_sleeper())\n    await asyncio.sleep(0)\n"
            "    coro = _inner()\n    try:\n        run(coro)\n    except RuntimeError as e:\n        print('REFUSED', e)\n"
            "    await asyncio.sleep(0)\n    print('RESUMED')\n\n\n"
            "run(_outer())\nprint('DONE')\n",
        )
    binary = sys.executable  # type: ignore[attr-defined]  # the Unix port's sys has it; the rp2 board stub does not
    status = os.system(binary + " " + script + " > " + out + " 2>&1")
    with open(out) as f:
        lines = f.read().split("\n")
    assert status == 0, f"exit status {status}: {lines}"
    assert "REFUSED run() called from inside a coroutine - build the fixture in the test's synchronous scope" in lines, lines
    assert "RESUMED" in lines, lines
    assert "DONE" in lines, lines


def test_the_interrupt_runner_refuses_to_nest_inside_a_running_loop() -> None:
    # As run() refuses: a nested asyncio.run() ends with no running task while the outer coroutine runs on (CLAUDE.md).
    started: list[bool] = []

    async def inner() -> None:
        started.append(True)

    async def outer() -> str:
        try:
            run_to_interrupt(inner())
        except RuntimeError as e:
            return str(e)
        return "not refused"

    assert run(outer()) == "run() called from inside a coroutine - build the fixture in the test's synchronous scope"
    assert started == []


def test_a_finished_task_another_awaited_is_passed_over_not_awaited_again() -> None:
    # The loop clears such a task's data once its queued failure is handled; awaiting it again crashes the port.
    where = _scratch.dir()
    script = where + "cleared.py"
    out = where + "cleared_out.txt"
    with open(script, "w") as f:
        f.write(
            "import asyncio\nfrom _async_harness import _await_each, cancel\n\n\n"
            "async def _fails():\n    raise OSError(5)\n\n\n"
            "async def _main():\n    task = asyncio.create_task(_fails())\n    await asyncio.sleep(0)\n"
            "    try:\n        await task\n    except OSError:\n        pass\n    await asyncio.sleep(0)\n"
            "    print('CLEARED', task.done(), task.data is None)\n    errors = []\n"
            "    await _await_each([task], errors)\n    await cancel(task)\n    print('PASSED OVER', errors)\n\n\n"
            "asyncio.run(_main())\n",
        )
    binary = sys.executable  # type: ignore[attr-defined]  # the Unix port's sys has it; the rp2 board stub does not
    status = os.system(binary + " " + script + " > " + out + " 2>&1")
    with open(out) as f:
        lines = f.read().split("\n")
    assert "CLEARED True True" in lines, lines
    assert status == 0, f"exit status {status}: {lines}"
    assert "PASSED OVER []" in lines, lines


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
