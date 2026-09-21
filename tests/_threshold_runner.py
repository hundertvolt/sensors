# Runs one tests/test_*.py file with an explicit gc.threshold(), so the suite can be exercised at
# the value the firmware actually ships as well as at MicroPython's own reactive default.
# Not a test_*.py file, so scripts/test.sh's glob never runs it directly.
#
# CLAUDE.md's memory-safety rule has two stages: the whole suite must pass at gc.threshold(-1) (the
# design is stable on its own), and it must ALSO still pass with the shipped gc.threshold(32768)
# layered on top. This is what makes the second stage runnable - scripts/test.sh's GC_THRESHOLD.
import gc
import sys


def _run() -> int:
    test_file = sys.argv[1]
    gc.threshold(int(sys.argv[2]))
    try:
        with open(test_file) as f:
            source = f.read()
        # A plain dict, not a real module namespace, and __name__ == "__main__" so the file's own
        # microtest.run() entry point fires - the same shape tests/_coverage_runner.py uses.
        exec(compile(source, test_file, "exec"), {"__name__": "__main__", "__file__": test_file})  # noqa: S102
    except SystemExit as exc:
        # MicroPython's SystemExit carries .args, not CPython's .code (see _coverage_runner.py).
        return int(exc.args[0]) if exc.args else 0
    return 0


sys.exit(_run())
