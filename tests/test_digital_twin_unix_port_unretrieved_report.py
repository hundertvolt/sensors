"""Deterministic unit tests for digital_twin/unix_port_unretrieved_report.py: the PC tiers' asyncio exception
handler, which prints every unretrieved task exception at every level so the memory gates see a task that died,
and releases the dead task asyncio's own context dict would otherwise keep (SPECIFICATION.md Part I.4(e))."""

import asyncio
import asyncio.core as asyncio_core  # type: ignore[import-not-found]  # asyncio's own context dict, read back below
import gc
import sys

import micropython

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import unix_port_unretrieved_report
from unix_port_unretrieved_report import MARKER, install, report_unretrieved

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context, _ExceptionHandler

    from typing_extensions import Self

_UNRETRIEVED = "Task exception wasn't retrieved"  # asyncio's own message (extmod/asyncio/core.py:27 at v1.29.0)
_LARGE_LOCAL = 2048  # a dead task's frame holding this much is what a retained context would keep
_DRIFT_BYTES = _LARGE_LOCAL // 4  # below one large local, so a single retained dead task fails the bound
_SETTLE_YIELDS = 8  # every death and its re-queued handler call land within these yields
_DEATHS = 5


class _ExhaustionError(MemoryError):
    """A MemoryError printed under its own name, so printing one stays clear of the memory gate's words."""


class _HandlerSlot:
    # Sets the loop's exception handler for the block and puts back whatever was set before.
    def __init__(self, handler: "_ExceptionHandler | None") -> None:
        self._handler = handler
        self._saved: _ExceptionHandler | None = None

    def __enter__(self) -> "Self":
        loop = asyncio.get_event_loop()
        self._saved = loop.get_exception_handler()
        loop.set_exception_handler(self._handler)
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.get_event_loop().set_exception_handler(self._saved)


class _ReportRecorder:
    # Shadows print() and sys inside the report's module, so its two outputs read back as calls; `fail` makes
    # the print raise instead.
    def __init__(self, fail: "Exception | None" = None) -> None:
        self.lines: list[tuple[object, ...]] = []
        self.tracebacks: list[object] = []
        self._fail = fail

    def __enter__(self) -> "Self":
        unix_port_unretrieved_report.print = self._print  # type: ignore[attr-defined]
        unix_port_unretrieved_report.sys = self  # type: ignore[attr-defined, assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        del unix_port_unretrieved_report.print  # type: ignore[attr-defined]
        unix_port_unretrieved_report.sys = sys  # type: ignore[attr-defined]

    def _print(self, *args: object, **_kwargs: object) -> None:
        if self._fail is not None:
            raise self._fail
        self.lines.append(args)

    def print_exception(self, exc: object, *_file: object) -> None:
        self.tracebacks.append(exc)


def _raised(exc: BaseException) -> BaseException:
    # The exception as asyncio hands it over: raised once, so it carries a traceback.
    try:
        raise exc
    except BaseException as caught:
        return caught


def _context(exc: object) -> "_Context":
    return {"message": _UNRETRIEVED, "exception": exc, "future": object()}


async def _dies(n: int) -> None:
    held = bytearray(_LARGE_LOCAL if n % 2 == 0 else 16)
    raise ValueError("probe", len(held))


def _deaths(n_tasks: int) -> None:
    # Detached tasks that die with nobody awaiting them: each reaches the loop's exception handler.
    async def scenario() -> None:
        tasks = [asyncio.create_task(_dies(n)) for n in range(n_tasks)]  # held, never awaited
        for _ in range(_SETTLE_YIELDS):
            await asyncio.sleep(0)
        assert all(task.done() for task in tasks)

    asyncio.run(scenario())


def _settled_alloc() -> int:
    # Read after asyncio.run() returned, so the run's own main task and any stale queue link it held are gone.
    gc.collect()
    return gc.mem_alloc()


def test_microtest_installed_the_report_before_any_test_ran() -> None:
    assert asyncio.get_event_loop().get_exception_handler() is report_unretrieved


def test_the_marker_carries_neither_memory_gate_word() -> None:
    # Only the printed exception may carry them, or every file whose own test crashes a task on purpose would fail the gate.
    for word in ("MemoryError", "memory allocation failed"):
        assert word not in MARKER, MARKER


def test_install_sets_the_report_and_is_idempotent() -> None:
    with _HandlerSlot(None):
        install()
        install()
        assert asyncio.get_event_loop().get_exception_handler() is report_unretrieved


def test_the_report_always_prints_the_marker_and_the_traceback_and_releases_the_task() -> None:
    exc = _raised(ValueError("probe"))
    context = _context(exc)
    with _ReportRecorder() as recorder:
        report_unretrieved(None, context)
    assert recorder.lines == [(MARKER, _UNRETRIEVED)], recorder.lines
    assert recorder.tracebacks == [exc], recorder.tracebacks
    assert context == {"message": _UNRETRIEVED, "exception": None, "future": None}, context


def test_the_report_returns_and_releases_the_task_with_the_heap_locked() -> None:
    for exc in (_raised(ValueError("probe")), _raised(_ExhaustionError("simulated allocation failure"))):
        context = _context(exc)
        micropython.heap_lock()
        try:
            report_unretrieved(None, context)
        finally:
            micropython.heap_unlock()
        assert context["exception"] is None and context["future"] is None, exc


def test_the_reports_outputs_allocate_nothing() -> None:
    # Its two calls under a locked heap with no handler to swallow a failure, then the whole report open.
    exc = _raised(ValueError("probe"))
    micropython.heap_lock()
    try:
        print(MARKER, _UNRETRIEVED)
        sys.print_exception(exc)
    finally:
        micropython.heap_unlock()
    context = _context(exc)
    gc.collect()
    before = gc.mem_alloc()
    report_unretrieved(None, context)
    after = gc.mem_alloc()
    assert after == before, after - before


def test_a_report_that_cannot_print_still_releases_the_task_and_never_raises() -> None:
    context = _context(_raised(ValueError("probe")))
    with _ReportRecorder(fail=RuntimeError("console gone")):
        report_unretrieved(None, context)
    assert context["exception"] is None and context["future"] is None
    bare: _Context = {}
    report_unretrieved(None, bare)  # the missing "message" raises before anything prints
    assert bare == {"exception": None, "future": None}, bare
    report_unretrieved(None, None)  # type: ignore[arg-type]  # not even a dict: the clearing raises too


def test_each_unretrieved_death_through_the_real_loop_is_reported_once() -> None:
    with _ReportRecorder() as recorder:
        _deaths(_DEATHS)
    assert recorder.lines == [(MARKER, _UNRETRIEVED)] * _DEATHS, recorder.lines
    assert len(recorder.tracebacks) == _DEATHS
    assert all(isinstance(exc, ValueError) for exc in recorder.tracebacks), recorder.tracebacks


def test_unretrieved_deaths_through_the_real_loop_retain_nothing() -> None:
    # Printed for real: the probes are worded clear of the gate. Default handler kept for the contrast.
    _deaths(1)  # first-use allocations land before the baseline
    before = _settled_alloc()
    _deaths(_DEATHS)
    released = _settled_alloc() - before
    try:
        with _HandlerSlot(None):
            before = _settled_alloc()
            _deaths(1)
            kept = _settled_alloc() - before
    finally:
        report_unretrieved(None, asyncio_core._exc_context)  # later tests start from a clear context
    assert released <= _DRIFT_BYTES, released
    assert kept >= _LARGE_LOCAL, kept


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
