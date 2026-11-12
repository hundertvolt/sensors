"""Runs one test file under `sys.settrace` and dumps the executed lines of the traced prefixes as JSON for
`scripts/_render_coverage.py` (SPECIFICATION.md E.5), on every path; its own build-settrace binary, the flag not being
inert (Part E.5.2). Exit rules as tests/_threshold_runner.py's; not a test_*.py file, so the suite's glob skips it."""

import errno
import json
import os
import sys

import _untraced  # beside this runner: its `tracer` is what untraced() restores, so an exhausting call cannot end tracing

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType
    from typing import TypeAlias

    _Trace: TypeAlias = "Callable[[FrameType, str, object], _Trace | None]"  # what sys.settrace() takes and each call returns

_TRACED_PREFIXES = ("src/", "digital_twin/", "build/generated_src/")
_INCOMPLETE = "runner: {} ended without microtest's exit - no trailer, or it never ran"
_S_IFDIR = 0x4000  # os.ilistdir()'s entry type for a directory (extmod/vfs.h MP_S_IFDIR)
# One line under a traced name, run after the file: unrecorded, the tracer ended early (_tracing_ended()).
_PROBE_FILE = "src/<tracer probe>"
_PROBE = compile("_ = 1\n", _PROBE_FILE, "exec")
_ENDED = "runner: tracing ended after {} - every traced line the file ran after it is missing from its coverage"


def _add_tables(tables: dict[str, bytearray], directory: str) -> None:
    # Subdirectories too (digital_twin/unixport/): a file without a table records through the allocating fallback.
    for entry in os.ilistdir(directory):
        path = directory + "/" + entry[0]
        if entry[1] == _S_IFDIR:
            _add_tables(tables, path)
        elif path.endswith(".py"):
            with open(path) as f:
                tables[path] = bytearray(f.read().count("\n") + 2)


def _dump(out_path: str) -> None:
    with open(out_path, "w") as f:
        for filename, table in _TABLES.items():
            for lineno in range(len(table)):
                if table[lineno]:
                    _HITS.setdefault(filename, {})[lineno] = True
        json.dump({filename: sorted(lines.keys()) for filename, lines in _HITS.items()}, f)


# The tracer's state lives in module globals and its two functions are module-level: a closure call with more than
# five closed-over values plus arguments heap-allocates its argument array on every call (py/objclosure.c), which is
# every traced line here (2.6x slower whole-file runs, 2026-10-07).
_TABLES: dict[str, bytearray] = {}
_HITS: dict[str, dict[int, bool]] = {}  # a traced file or line no table holds: recorded, at an allocation's cost
# This build allocates a frame and a code object of several blocks on every call and resume, and the allocator starts
# a search after the last single-block allocation only: one float per call keeps each search short (SPECIFICATION.md
# Part E.5.2). Garbage at the next collection: a collected heap measures the same, a collection-free window 32 B more.
_SCAN_STEP = 1.0
_SCAN_MARK = [_SCAN_STEP]
_last_file = ""  # the last traced line, which a note of an ended tracer names: two stores per line, nothing allocated
_last_line = 0


def _global_trace(frame: "FrameType", event: str, _arg: object) -> "_Trace | None":
    try:
        _SCAN_MARK[0] = _SCAN_STEP + _SCAN_STEP
    except MemoryError:  # a test's own full heap: an exception escaping here would leave the tracer switched off
        pass
    if event == "call" and frame.f_code.co_filename.startswith(_TRACED_PREFIXES):
        return _local_trace
    return None


def _line_tables() -> dict[str, bytearray]:
    # One byte per line of every traced file, sized before the test file runs: recording a line stores into it and
    # allocates nothing, so a test measuring its own heap never sees the tracer grow (SPECIFICATION.md Part E.5.2).
    tables: dict[str, bytearray] = {}
    for prefix in _TRACED_PREFIXES:
        try:
            _add_tables(tables, prefix[:-1])
        except OSError as e:
            if e.errno != errno.ENOENT:  # an absent prefix (no generated tree yet) has nothing to trace
                raise
    return tables


def _local_trace(frame: "FrameType", event: str, _arg: object) -> "_Trace":
    global _last_file, _last_line
    if event == "line":
        filename = frame.f_code.co_filename
        table = _TABLES.get(filename)
        lineno = frame.f_lineno
        _last_file = filename
        _last_line = lineno
        if table is not None and lineno < len(table):
            table[lineno] = 1
        elif filename.startswith(_TRACED_PREFIXES):
            lines = _HITS.get(filename)
            if lines is None:
                lines = {}
                _HITS[filename] = lines
            lines[lineno] = True
    return _local_trace


def _run() -> int:
    test_file = sys.argv[1]
    out_path = sys.argv[2]
    _TABLES.update(_line_tables())
    sys.argv[:] = [test_file]  # what the file sees when run directly

    _untraced.tracer = _global_trace
    sys.settrace(_global_trace)
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
        if type(exit_code) is not int:
            print(exit_code)  # sys.exit("message"): the message, then a failure
            exit_code = 1
    except BaseException as exc:  # every other escape is the file's failure, its traceback printed
        sys.print_exception(exc)
        exit_code = 1
    else:
        print(_INCOMPLETE.format(test_file))
        exit_code = 1
    finally:
        try:
            ended = _tracing_ended()
        finally:
            sys.settrace(None)
            _dump(out_path)  # every path: a failing or incomplete file's lines still count
        if ended is not None:
            print(_ENDED.format(ended))
            with open(out_path + ".incomplete", "w") as f:
                f.write(_ENDED.format(ended) + "\n")
    return exit_code


def _tracing_ended() -> "str | None":
    # A raise inside the trace callback (a C-stack limit, an interrupt) leaves its is-executing flag set, and from then
    # on nothing is traced (py/profile.c:168-173, py/vm.c:161-185, v1.29.0): the last traced line, or None if alive.
    last = "{}:{}".format(_last_file or "<none>", _last_line)  # read first: the probe's own line replaces it
    exec(_PROBE, {})
    return None if _HITS.pop(_PROBE_FILE, None) is not None else last


sys.exit(_run())
