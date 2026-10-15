"""One way to drive a coroutine from a synchronous test: refuses to nest inside a running loop and, on every path, ends
each task the call created, cancelling each on its own and naming any it could not end within its bound. A task such a
cancellation starts is not tracked; microtest's after-each check is the backstop for it."""

import asyncio
import asyncio.core as _core  # type: ignore[import-not-found]  # cur_task, the queues and core's own create_task; no stub covers them
import sys
from time import ticks_add, ticks_diff, ticks_ms

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine, Iterable
    from typing import TypeVar

    from _mpy_shed.time_mp import _TicksMs

    T = TypeVar("T")
    CoroutineOf = Coroutine[object, object, T]
    _Task = asyncio.Task[object]  # the fields the reap reads and writes: extmod/modasyncio.c, task_attr()


_NESTED = "run() called from inside a coroutine - build the fixture in the test's synchronous scope"
_UNENDED = "the reap could not end a task the run created:"
# How long the reap lets a cancelled task go on running; a task nothing can wake again is named at once.
# @tunable l1.async_harness_reap_limit_ms = 5000
_REAP_LIMIT_MS = 5000
_COMPACT_MIN = 8
# The running call's tasks: the finished ones are dropped whenever the list doubles past its last compaction, so a
# create costs no scan. One call runs at a time (nesting is refused), so this is module state, emptied as a call ends.
_tracked: "list[_Task]" = []
_compact_at = _COMPACT_MIN
_core_create_task = _core.create_task  # core's own, and asyncio's below, as the running call found them
_real_create_task = asyncio.create_task


async def _await_each(pending: "list[_Task]", errors: "list[Exception]") -> None:
    # Awaits every task, keeping what any ended with but its cancellation; one another task's gather() holds is
    # polled instead, as awaiting it raises "can't wait".
    for task in pending:
        if _cleared(task):
            continue
        try:
            if callable(task.state):
                while not task.done():
                    await asyncio.sleep(0)
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # every kind a cancelled task can end with, returned to the caller
            errors.append(exc)


def _cancel_alone(task: "_Task") -> None:
    # Task.cancel() forwards to the task this one awaits (extmod/asyncio/task.py, cancel()), which a BaseException
    # may have left unresumable: a waiter leaves that task's queue and takes its own CancelledError instead.
    awaited = task.data
    if isinstance(awaited, asyncio.Task):
        awaited.state.remove(task)  # type: ignore[union-attr]  # a waited-on Task's state is its waiters' TaskQueue
        _core._task_queue.push(task)
        task.data = asyncio.CancelledError
    else:
        task.cancel()


def _cleared(task: "_Task") -> bool:
    # Finished, awaited, and its queued failure since handled: the loop leaves data None, and awaiting it then raises
    # None, which crashes the port (extmod/modasyncio.c, task_iternext). Its awaiter already took what it ended with.
    return task.done() and task.data is None


def _compact() -> None:
    # Keeps the unfinished tasks in place, allocating nothing, and sets the next compaction at twice their number.
    global _compact_at
    kept = 0
    for each in _tracked:
        if not each.done():
            _tracked[kept] = each
            kept += 1
    del _tracked[kept:]
    _compact_at = max(_COMPACT_MIN, 2 * kept)


def _drive(coro: "CoroutineOf[T]", limit_s: "float | None") -> "T":
    # A nested asyncio.run() swaps the queues the outer loop's parked tasks live on: the Unix port then crashes
    # (CLAUDE.md "Known segfault cause"). cur_task is the running task inside run_until_complete() only (core.py).
    global _core_create_task, _real_create_task
    if _core.cur_task is not None:
        coro.close()
        raise RuntimeError(_NESTED)
    aw = coro if limit_s is None else asyncio.wait_for(coro, limit_s)
    _real_create_task, _core_create_task = asyncio.create_task, _core.create_task
    asyncio.create_task = _core.create_task = _tracking  # type: ignore[assignment]  # put back by _end() on every path
    return _run_tracked(aw)


def _due(head: "_Task | None", now: "_TicksMs") -> bool:
    # A task on the run queue whose time has come: a step of an untracked task, or a finished one's exception report.
    return head is not None and ticks_diff(head.ph_key, now) <= 0


def _end(escaped: "_Task | None", *, failed: bool) -> None:
    # Puts create_task back and reaps what the call left unfinished or due, allocating nothing when there is neither.
    global _compact_at
    asyncio.create_task, _core.create_task = _real_create_task, _core_create_task
    _core.cur_task = None
    pending = _unfinished(escaped)
    _tracked.clear()
    _compact_at = _COMPACT_MIN
    if pending is not None or _due(_core._task_queue.peek(), ticks_ms()):
        _settle(pending or [], failed=failed)


def _failed(escaped: "_Task | None") -> None:
    _end(escaped, failed=True)


def _passed() -> None:
    _end(None, failed=False)


def _reap(pending: "list[_Task]") -> "tuple[list[Exception], list[_Task]]":
    # One loop round first, as the board's loop never stops (a due deferred flush completes), then each task still
    # unfinished is cancelled on its own and the loop runs until all have ended, nothing but the watch can run, or the
    # bound passes. Returns what they ended with but cancellation, and the unended, taken off every queue they were on.
    errors: list[Exception] = []
    asyncio.run(_round())
    for task in pending:
        if not task.done():
            _cancel_alone(task)
    reaper = asyncio.create_task(_await_each(pending, errors))  # the real create_task again
    asyncio.run(_watch(reaper, ticks_add(ticks_ms(), _REAP_LIMIT_MS)))
    unended = [task for task in pending if not task.done()]
    for task in unended if reaper.done() else unended + [reaper]:  # a [*a, b] display is a SyntaxError on MicroPython
        _unpark(task)
    return errors, unended


async def _round() -> None:
    await asyncio.sleep(0)


def _run_tracked(aw: "CoroutineOf[T]") -> "T":
    # Each frame on a call's path stays within MicroPython's on-stack limit (py/objfun.c, VM_MAX_STATE_ON_STACK): a
    # larger one is a heap block, which counts toward gc.threshold() even once freed. Hence two locals, no keywords.
    try:
        result = asyncio.run(aw)
    except BaseException:
        _failed(_core.cur_task)  # a BaseException leaves the loop with its task marked as running
        raise
    _passed()
    return result


def _settle(pending: "list[_Task]", *, failed: bool) -> None:
    # Reaps, names what it could not end and prints what the cancelled tasks failed with; a failed run keeps its own
    # exception, a passing one fails with the first of those failures, else with the unended tasks.
    errors, unended = _reap(pending)
    for task in unended:
        print(_UNENDED, task.coro)
    for exc in errors if failed else errors[1:]:
        print("a cancelled task also failed:")
        sys.print_exception(exc)
    if failed:
        return
    if errors:
        raise errors[0]  # the run itself succeeded: a child's failure is its result
    if unended:
        raise RuntimeError(_UNENDED + " " + ", ".join(str(task.coro) for task in unended))


def _tracking(aw: "Coroutine[object, object, object]") -> "_Task":
    task: _Task = _core_create_task(aw)
    _tracked.append(task)
    if len(_tracked) >= _compact_at:
        _compact()
    return task


def _unfinished(escaped: "_Task | None") -> "list[_Task] | None":
    # The call's unfinished tasks, None for none. The task a BaseException left mid-step is never resumed and is passed
    # over, unless it waits on something (an interrupt can land between steps, with the last task run still marked).
    pending: list[_Task] | None = None
    for task in _tracked:
        if not task.done() and (task is not escaped or task.data is not None):
            if pending is None:
                pending = []
            pending.append(task)
    return pending


def _unpark(task: "_Task") -> None:
    # Takes a task off whichever queue holds it - another task's waiters, an Event's or the stream waits, or the run
    # queue (a no-op for a task on none) - so no later loop waits on it.
    awaited = task.data
    if isinstance(awaited, asyncio.Task):
        awaited.state.remove(task)  # type: ignore[union-attr]  # as in _cancel_alone()
    elif hasattr(awaited, "remove"):
        awaited.remove(task)
    else:
        _core._task_queue.remove(task)


async def _watch(reaper: "_Task", deadline: "_TicksMs") -> None:
    # The reap's main task: returns once the reaper is done and nothing on the run queue is due, once nothing else can
    # ever run, or past the deadline; sleeps to the earliest wake-up between, a millisecond at most while a stream waits.
    while True:
        now = ticks_ms()
        head = _core._task_queue.peek()
        if reaper.done() and not _due(head, now):
            return
        step = ticks_diff(deadline, now)
        if step <= 0 or (head is None and not _core._io_queue.map):
            return
        if head is not None:
            step = min(step, max(0, ticks_diff(head.ph_key, now)))
        await asyncio.sleep_ms(min(step, 1) if _core._io_queue.map else step)


async def cancel(task: "asyncio.Task[T]") -> None:
    # Ends a task this test started and waits for it, its CancelledError expected and absorbed.
    task.cancel()
    if _cleared(task):
        return
    try:
        await task
    except asyncio.CancelledError:
        pass


async def cancel_all(tasks: "Iterable[asyncio.Task[T]]", settle_yields: int = 0) -> None:
    # cancel() for each, then `settle_yields` scheduler rounds for work a cancellation hands on (a runner's wait).
    for task in tasks:
        await cancel(task)
    for _ in range(settle_yields):
        await asyncio.sleep(0)


def release_finished() -> None:
    # Drops the finished tasks the running call still tracks, so a heap reading taken inside it holds only what the
    # code under test keeps; between compactions the list holds up to as many finished tasks as live ones.
    _compact()


def run(coro: "CoroutineOf[T]", limit_s: "float | None" = None) -> "T":
    # The coroutine's result; with `limit_s`, bounded by asyncio.wait_for() and TimeoutError past it.
    return _drive(coro, limit_s)


def run_timed(coro: "CoroutineOf[T]", timeout_s: float) -> "T":
    return _drive(coro, timeout_s)
