"""Runs one test file at a given gc.threshold() stage: sets the threshold, executes the file as `__main__`, returns the
file's exit code (scripts/test.sh's GC_THRESHOLD stage, CLAUDE.md's memory rule). A file that never reaches microtest's
exit, exits with a message or raises fails; not a test_*.py file, so the suite's glob never runs it directly."""

import gc
import sys

_INCOMPLETE = "runner: {} ended without microtest's exit - no trailer, or it never ran"


def _run() -> int:
    test_file = sys.argv[1]
    gc.threshold(int(sys.argv[2]))
    sys.argv[:] = [test_file]  # what the file sees when run directly
    try:
        with open(test_file) as f:
            source = f.read()
        # A plain dict, not a real module namespace, and __name__ == "__main__" so the file's own
        # microtest.run() entry point fires - the same shape tests/_coverage_runner.py uses.
        exec(compile(source, test_file, "exec"), {"__name__": "__main__", "__file__": test_file})  # noqa: S102
    except SystemExit as exc:
        # MicroPython's SystemExit carries .args, not CPython's .code (see _coverage_runner.py).
        code = exc.args[0] if exc.args else 0
        if type(code) is int:
            return code
        print(code)  # sys.exit("message"): the message, then a failure
        return 1
    except BaseException as exc:  # every other escape is the file's failure, its traceback printed
        sys.print_exception(exc)
        return 1
    print(_INCOMPLETE.format(test_file))
    return 1


sys.exit(_run())
