# Runs one tests/test_*.py file under sys.settrace, recording every line executed in src/ or digital_twin/
# only - this file and the test file's own body stay untraced - then dumps the recorded lines as JSON.
# Invoked by scripts/test.sh --coverage in place of running a test file directly.
#
# It runs under build-settrace, its OWN binary: the flag is not inert when unused - it allocates a
# frame and a code object per call, so the test rig is built without it (Part E.5.2). Not a
# test_*.py file itself, so scripts/test.sh's glob never picks it up.
#
# coverage.py never runs here, being a CPython tool. scripts/_render_coverage.py is the CPython-side
# counterpart turning this raw JSON into a real report - see SPECIFICATION.md Part E.5 for the pipeline.
# scripts/test.sh renders two reports from one dump, scoped to src/ and digital_twin/.
import json
import os
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

_TRACED_PREFIXES = ("src/", "digital_twin/")
_S_IFDIR = 0x4000  # os.ilistdir()'s entry type for a directory (extmod/vfs.h MP_S_IFDIR)


def _add_tables(tables: dict[str, bytearray], directory: str) -> None:
    # Subdirectories too (digital_twin/unixport/): a file without a table records through the allocating fallback.
    for entry in os.ilistdir(directory):
        path = directory + "/" + entry[0]
        if entry[1] == _S_IFDIR:
            _add_tables(tables, path)
        elif path.endswith(".py"):
            with open(path) as f:
                tables[path] = bytearray(f.read().count("\n") + 2)


def _line_tables() -> dict[str, bytearray]:
    # One byte per line of every traced file, sized before the test file runs: recording a line stores into it and
    # allocates nothing, so a test measuring its own heap never sees the tracer grow (SPECIFICATION.md Part E.5.2).
    tables: dict[str, bytearray] = {}
    for prefix in _TRACED_PREFIXES:
        _add_tables(tables, prefix[:-1])
    return tables


# The tracer's state lives in module globals and its two functions are module-level: a closure call with more than
# five closed-over values plus arguments heap-allocates its argument array on every call (py/objclosure.c), which is
# every traced line here (2.6x slower whole-file runs, 2026-10-07).
_TABLES: dict[str, bytearray] = {}
_HITS: dict[str, dict[int, bool]] = {}  # a traced file or line no table holds: recorded, at an allocation's cost


def _local_trace(frame: "FrameType", event: str, _arg: object) -> "Callable[..., object]":
    if event == "line":
        filename = frame.f_code.co_filename
        table = _TABLES.get(filename)
        lineno = frame.f_lineno
        if table is not None and lineno < len(table):
            table[lineno] = 1
        elif filename.startswith(_TRACED_PREFIXES):
            lines = _HITS.get(filename)
            if lines is None:
                lines = {}
                _HITS[filename] = lines
            lines[lineno] = True
    return _local_trace


def _global_trace(frame: "FrameType", event: str, _arg: object) -> "Callable[..., object] | None":
    if event == "call" and frame.f_code.co_filename.startswith(_TRACED_PREFIXES):
        return _local_trace
    return None


def _run() -> int:
    test_file = sys.argv[1]
    out_path = sys.argv[2]
    _TABLES.update(_line_tables())
    hits = _HITS

    sys.settrace(_global_trace)
    exit_code = 0
    try:
        with open(test_file) as f:
            source = f.read()
        code = compile(source, test_file, "exec")
        # A plain dict, not a real module namespace: the MicroPython Unix port doesn't register
        # the executed script in sys.modules["__main__"] the way CPython does (see
        # tests/microtest.py), so there's nothing else to exec() against.
        exec(code, {"__name__": "__main__", "__file__": test_file})  # noqa: S102
    except SystemExit as exc:
        # MicroPython's SystemExit has no .code attribute (unlike CPython's) -- .args is what's
        # actually populated, confirmed directly against the built interpreter.
        exit_code = exc.args[0] if exc.args else 0
    finally:
        sys.settrace(None)

    with open(out_path, "w") as f:
        for filename, table in _TABLES.items():
            for lineno in range(len(table)):
                if table[lineno]:
                    hits.setdefault(filename, {})[lineno] = True
        json.dump({filename: sorted(lines.keys()) for filename, lines in hits.items()}, f)

    return exit_code


sys.exit(_run())
