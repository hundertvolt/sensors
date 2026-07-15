# Runs one tests/test_*.py file under sys.settrace, recording every line executed in src/ (only
# -- everything else, including this file itself and the test file's own body, is left untraced),
# then dumps the recorded lines as JSON. Invoked by scripts/test.sh --coverage in place of running
# a test file directly -- under the same MicroPython Unix port binary the non-coverage run uses,
# since build_unix_port() (see toolchain/setup_toolchain.py) always compiles in
# MICROPY_PY_SYS_SETTRACE=1 (an inert hook check when unused, not a behavior change). Not a
# test_*.py file itself, so scripts/test.sh's glob never picks it up directly.
#
# coverage.py itself never runs here: it's a CPython tool and can't execute under MicroPython.
# scripts/_render_coverage.py is the CPython-side counterpart that turns the raw JSON this file
# writes into an actual coverage.py report -- see that file and tests/README.md for the full
# pipeline.
import json
import sys

_SRC_PREFIX = "src/"


def _run() -> int:
    test_file = sys.argv[1]
    out_path = sys.argv[2]
    hits: dict[str, dict[int, bool]] = {}

    def local_trace(frame, event, arg):  # type: ignore[no-untyped-def]
        if event == "line":
            filename = frame.f_code.co_filename
            if filename.startswith(_SRC_PREFIX):
                lines = hits.get(filename)
                if lines is None:
                    lines = {}
                    hits[filename] = lines
                lines[frame.f_lineno] = True
        return local_trace

    def global_trace(frame, event, arg):  # type: ignore[no-untyped-def]
        if event == "call" and frame.f_code.co_filename.startswith(_SRC_PREFIX):
            return local_trace
        return None

    sys.settrace(global_trace)
    exit_code = 0
    try:
        with open(test_file) as f:
            source = f.read()
        code = compile(source, test_file, "exec")
        # A plain dict, not a real module namespace: the MicroPython Unix port doesn't register
        # the executed script in sys.modules["__main__"] the way CPython does (see
        # tests/microtest.py), so there's nothing else to exec() against.
        exec(code, {"__name__": "__main__", "__file__": test_file})
    except SystemExit as exc:
        # MicroPython's SystemExit has no .code attribute (unlike CPython's) -- .args is what's
        # actually populated, confirmed directly against the built interpreter.
        exit_code = exc.args[0] if exc.args else 0
    finally:
        sys.settrace(None)

    with open(out_path, "w") as f:
        json.dump({filename: sorted(lines.keys()) for filename, lines in hits.items()}, f)

    return exit_code


sys.exit(_run())
