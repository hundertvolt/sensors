import sys

import _tmp_scratch


class Skip(Exception):  # noqa: N818 - the outcome's name, as microtest prints it
    """Raised by a test that cannot run here; the message is the reason microtest prints and counts."""


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
    skipped = 0
    try:
        for name, value in namespace.items():
            if not name.startswith("test_") or not callable(value):
                continue
            total += 1
            try:
                value()
            except Skip as exc:
                skipped += 1
                print(f"SKIP {name}: {exc}")
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
    if total == 0:
        # A file that checked nothing fails rather than passing empty (scripts/test.sh reads this line).
        print("0/0 passed, 0 failed, 0 skipped - no test_* function collected")
        failed = 1
    else:
        print(f"{total - failed - skipped}/{total} passed, {failed} failed, {skipped} skipped")
    # Always exit explicitly: MicroPython's asyncio has no parent/child tracking, so tasks a test leaves parked would keep
    # the process alive after the summary line (SPECIFICATION.md E.3).
    sys.exit(1 if failed else 0)
