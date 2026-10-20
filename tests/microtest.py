"""Minimal test runner for the MicroPython Unix port: runs each `test_*` function of a namespace, resets process state
after each, prints one summary line and always exits explicitly."""

import asyncio.core as _core  # type: ignore[import-not-found]  # the scheduler queues the parked-task check reads; no stub covers them
import gc
import sys

import _tmp_scratch

# The PC tiers' asyncio report lives with the twin's other Unix-port helpers; found from this file's own
# place, so a run from any working directory reaches it, and the path entry goes again once it is loaded.
sys.path.append((__file__.rsplit("/", 1)[0] if "/" in __file__ else ".") + "/../digital_twin")
import unix_port_unretrieved_report  # type: ignore[import-not-found, unused-ignore]  # unresolved only in CI's narrowed mypy pass

sys.path.pop()

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

_AFTER_EACH: "list[Callable[[], None]]" = []
_RETURNED = "returned a value - an async def test_* or a stray return; microtest runs synchronous functions only"
_PARKED = "left a task parked on the scheduler"
_FATAL = "left the C-stack fatal flag set"


class Skip(Exception):
    """Raised by a test that cannot run here; the message is the reason microtest prints and counts."""


def _call(name: str, value: "Callable[[], object]") -> "tuple[str, str]":
    # One test body: ("pass", ""), ("skip", reason) or ("fail", ""), its FAIL lines printed here. A BaseException
    # other than a simulated reset propagates: run() aborts the file on it.
    try:
        result = value()
    except Skip as exc:
        return "skip", str(exc)
    except Exception as exc:
        print(f"FAIL {name}:")
        sys.print_exception(exc)  # full traceback - a bare str(exc) is empty for AssertionError
        return "fail", ""
    except BaseException as exc:
        if not isinstance(exc, getattr(sys.modules.get("machine"), "SimulatedRebootError", ())):
            raise
        print(f"FAIL {name}: reset reached without a catch")
        sys.print_exception(exc)
        return "fail", ""
    if result is not None:
        if hasattr(result, "close"):
            result.close()  # a coroutine's generator, never started
        print(f"FAIL {name}: {_RETURNED}")
        return "fail", ""
    return "pass", ""


def _drain_scheduler() -> bool:
    # True when the test left a task on asyncio's run queue or a stream wait; each is cancelled and run to its end,
    # stream entries no task holds are dropped, and the prewarmed poller itself is kept (digital_twin/README.md).
    _core.cur_task = None  # a BaseException out of a loop leaves its task marked running; between tests none runs
    queue, io = _core._task_queue, _core._io_queue
    if queue.peek() is None and not io.map:
        return False
    for entry in list(io.map.values()):
        for task in entry[:2]:
            if task is not None and not task.done():
                task.cancel()  # IOQueue.remove() takes its stream entry and moves the task to the run queue
    for key in list(io.map):
        io.poller.unregister(io.map[key][2])
        del io.map[key]
    parked = []
    while queue.peek() is not None:
        parked.append(queue.pop())
    for task in parked:
        queue.push(task)
        if not task.done():
            task.cancel()
    _core.run_until_complete()  # no main task: returns once both queues are empty
    return True


def _reset_process_state(name: str, saved_path: "list[str]", saved_threshold: int) -> bool:
    # After every test: the scheduler check, each registered hook, sys.path and gc.threshold(), then the product's one-way
    # flags at their boot value (only for a module already loaded), the fatal flag failing a test that left it set.
    # True when the test FAILs here.
    failed = _drain_scheduler()
    if failed:
        print(f"FAIL {name}: {_PARKED}")
    for hook in _AFTER_EACH:
        try:
            hook()
        except Exception as exc:
            failed = True
            print(f"FAIL {name}: teardown: {exc!r}")
            sys.print_exception(exc)
    sys.path[:] = saved_path
    gc.threshold(saved_threshold)
    base_classes = sys.modules.get("asy_base_classes")
    if base_classes is not None:
        base_classes._utc_valid = False  # type: ignore[attr-defined]  # the pre-sync timestamp flag, as at boot
    print_log = sys.modules.get("asy_print_log")
    if print_log is not None and print_log._fatal:  # the C-stack fatal flag
        failed = True
        print(f"FAIL {name}: {_FATAL}")
        print_log._fatal = False  # type: ignore[attr-defined]  # as at boot
    return failed


def after_each(fn: "Callable[[], None]") -> None:
    _AFTER_EACH.append(fn)


def run(namespace: dict[str, object]) -> None:
    # A minimal collector and runner, not CPython's `unittest` (absent from the Unix port's standard build). Takes the
    # namespace dict (`microtest.run(globals())`): the Unix port registers no `__main__` module to look tests up on.
    unix_port_unretrieved_report.install()  # first: every unretrieved task exception prints, at every level (Part I.4(e))
    names = sorted(name for name, value in namespace.items() if name.startswith("test_") and callable(value))
    saved_path, saved_threshold = sys.path[:], gc.threshold()
    passed = failed = skipped = 0
    try:
        for name in names:
            # The after-each reset is inside the abort too: an interrupt (scripts/test.sh's per-file timeout) landing in
            # its drain or a hook still names the test it ends.
            try:
                outcome, reason = _call(name, namespace[name])  # type: ignore[arg-type]  # collected as callable above
                if _reset_process_state(name, saved_path, saved_threshold) and outcome != "fail":
                    outcome = "fail"
            except BaseException as exc:
                print(f"ABORT {name}:")
                sys.print_exception(exc)
                print(f"{passed}/{len(names)} passed, {failed + 1} failed, {skipped} skipped - aborted at {name}, later tests not run")
                sys.exit(1)
            if outcome == "pass":
                passed += 1
                print(f"PASS {name}")
            elif outcome == "skip":
                skipped += 1
                print(f"SKIP {name}: {reason}")
            else:
                failed += 1
    finally:
        # Per-file teardown for every tests/_tmp/<key>/ scratch dir this file created (_tmp_scratch.py), on every path.
        _tmp_scratch.teardown_all()
    if not names:
        # A file that checked nothing fails rather than passing empty (scripts/test.sh reads this line).
        print("0/0 passed, 0 failed, 0 skipped - no test_* function collected")
        failed = 1
    else:
        print(f"{passed}/{len(names)} passed, {failed} failed, {skipped} skipped")
    # Always exit explicitly: MicroPython's asyncio has no parent/child tracking, so tasks a test leaves parked would keep
    # the process alive after the summary line (SPECIFICATION.md E.3).
    sys.exit(1 if failed else 0)
