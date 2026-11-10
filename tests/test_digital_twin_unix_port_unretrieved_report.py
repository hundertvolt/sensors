"""Deterministic unit tests for digital_twin/unix_port_unretrieved_report.py: the PC tiers' asyncio exception
handler, the product's report at level 1, so every unretrieved task exception prints and the memory gates see a task
that died (SPECIFICATION.md Part I.4(e)). The report's own body is test_asy_system_service.py's to prove."""

import asyncio
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _async_harness import run
from unix_port_unretrieved_report import MARKER, install, report_unretrieved

import asy_print_log

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context, _ExceptionHandler

    from typing_extensions import Self

_UNRETRIEVED = "Task exception wasn't retrieved"  # asyncio's own message (extmod/asyncio/core.py:27 at v1.29.0)
_SETTLE_YIELDS = 8  # every death and its re-queued handler call land within these yields
_DEATHS = 5


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
    # Shadows print() and sys inside the logger's module, so the report's two outputs read back as calls.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        self.tracebacks: list[object] = []

    def __enter__(self) -> "Self":
        asy_print_log.print = self._print  # type: ignore[attr-defined]
        asy_print_log.sys = self  # type: ignore[assignment, attr-defined]
        return self

    def __exit__(self, *exc_info: object) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]
        asy_print_log.sys = sys  # type: ignore[attr-defined]

    def _print(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def print_exception(self, exc: object, *_file: object) -> None:
        self.tracebacks.append(exc)


def _context(exc: object) -> "_Context":
    return {"message": _UNRETRIEVED, "exception": exc, "future": object()}


def _deaths(n_tasks: int) -> None:
    # Detached tasks that die with nobody awaiting them: each reaches the loop's exception handler.
    async def scenario() -> None:
        tasks = [asyncio.create_task(_dies(n)) for n in range(n_tasks)]  # held, never awaited
        for _ in range(_SETTLE_YIELDS):
            await asyncio.sleep(0)
        assert all(task.done() for task in tasks)

    run(scenario())


async def _dies(n: int) -> None:
    raise ValueError("probe", n)


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
    exc = ValueError("probe")
    context = _context(exc)
    with _ReportRecorder() as recorder:
        report_unretrieved(None, context)
    assert recorder.lines == [(MARKER, _UNRETRIEVED)], recorder.lines
    assert recorder.tracebacks == [exc], recorder.tracebacks
    assert context == {"message": _UNRETRIEVED, "exception": None, "future": None}, context


def test_each_unretrieved_death_through_the_real_loop_is_reported_once() -> None:
    with _ReportRecorder() as recorder:
        _deaths(_DEATHS)
    assert recorder.lines == [(MARKER, _UNRETRIEVED)] * _DEATHS, recorder.lines
    assert len(recorder.tracebacks) == _DEATHS
    assert all(isinstance(exc, ValueError) for exc in recorder.tracebacks), recorder.tracebacks


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
