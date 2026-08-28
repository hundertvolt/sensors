import sys


def run(namespace: dict) -> None:
    # A minimal test collector/runner, not the CPython stdlib `unittest`: it isn't part of the
    # MicroPython Unix port's default "standard" build, and pulling it in via mip would add a
    # network dependency to every test run. Just enough to run test_*() functions, report
    # pass/fail per test, and exit nonzero on any failure - which is all these tests need.
    #
    # Takes a plain namespace dict (call as `microtest.run(globals())`), not a module object:
    # the MicroPython Unix port doesn't register the top-level script in `sys.modules["__main__"]`
    # the way CPython does, so there is no module object to look the test functions up on.
    total = 0
    failed = 0
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
    print(f"{total - failed}/{total} passed")
    # Always exits explicitly, not just on failure: a test that spins up the real
    # sensortask_wozi.build_system()/start_and_check_tasks() task graph (the digital-twin
    # integration files) leaves independently-scheduled sibling tasks (WiFi, sensor readers, the
    # webserver, ...) parked in the shared, process-wide asyncio task queue after its own test
    # function returns - Task.cancel() on the one Task a test explicitly awaited (e.g. main_task in
    # digital_twin/run_wozi_integration.py) never cascades to those siblings, since asyncio doesn't
    # track parent/child task relationships. Falling off the end of this script used to leave the
    # Unix-port process waiting on that leftover queue instead of exiting - confirmed by direct
    # reproduction (system_service.py's own _timer_sequencer() fix was what first let a soak test
    # run its real task graph to a clean, non-cancelled completion instead of always timing out
    # first). sys.exit() forces the process down immediately regardless of what's still parked.
    sys.exit(1 if failed else 0)
