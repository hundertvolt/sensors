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
            print(f"FAIL {name}: {exc}")
        else:
            print(f"PASS {name}")
    print(f"{total - failed}/{total} passed")
    if failed:
        sys.exit(1)
