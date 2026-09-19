import sys

import _tmp_scratch


def run(namespace: dict[str, object]) -> None:
    # A minimal test collector and runner, not the CPython stdlib `unittest`: that is not part of the Unix
    # port's default "standard" build, and pulling it in via mip would add a network dependency to every
    # test run. Just enough to run test_*() functions, report pass/fail, and exit nonzero on any failure.
    #
    # Takes a plain namespace dict (call as `microtest.run(globals())`), not a module object:
    # the MicroPython Unix port doesn't register the top-level script in `sys.modules["__main__"]`
    # the way CPython does, so there is no module object to look the test functions up on.
    total = 0
    failed = 0
    try:
        for name, value in namespace.items():
            if not name.startswith("test_") or not callable(value):
                continue
            total += 1
            try:
                value()
            except Exception as exc:
                failed += 1
                print(f"FAIL {name}:")
                sys.print_exception(exc)  # full traceback - a bare str(exc) is empty for AssertionError
            else:
                print(f"PASS {name}")
    finally:
        # Real per-file teardown for every tests/_tmp/<key>/ scratch dir this file's own
        # TmpScratch instance(s) created - see _tmp_scratch.py's own docstring. Runs even on a
        # test failure, so a file's scratch dir never outlives its own run.
        _tmp_scratch.teardown_all()
    print(f"{total - failed}/{total} passed")
    # Always exits explicitly, not just on failure: a test that spins up the real build_system() task graph
    # leaves independently-scheduled sibling tasks parked in the shared, process-wide asyncio task queue
    # after its own test function returns.
    #
    # Task.cancel() on the one Task a test explicitly awaited never cascades to those siblings, asyncio
    # tracking no parent/child relationships, so falling off the end of this script used to leave the
    # process waiting on that leftover queue instead of exiting. sys.exit() forces it down regardless.
    sys.exit(1 if failed else 0)
