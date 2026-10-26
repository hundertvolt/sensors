"""tests/_untraced.py's untraced(): a plain call while no tracer is set; with one, the call runs with sys.settrace(None)
and the tracer is restored however the call ends, its result or exception passed on (SPECIFICATION.md E.5.1)."""

import _untraced
from _untraced import untraced

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType


class _RecordingSys:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def settrace(self, tracer: object) -> None:
        self.calls.append(tracer)


def _tracer(_frame: object, _event: str, _arg: object) -> None:
    return None


def _with(tracer: "Callable[[FrameType, str, object], object] | None", check: "Callable[[_RecordingSys], None]") -> None:
    real_sys, real_tracer = _untraced.sys, _untraced.tracer
    fake = _RecordingSys()
    _untraced.sys, _untraced.tracer = fake, tracer  # type: ignore[assignment]
    try:
        check(fake)
    finally:
        _untraced.sys, _untraced.tracer = real_sys, real_tracer


def test_with_no_tracer_set_it_is_a_plain_call_that_never_touches_settrace() -> None:
    def check(fake: _RecordingSys) -> None:
        assert untraced(lambda: 7) == 7
        assert fake.calls == [], fake.calls

    _with(None, check)


def test_with_a_tracer_set_the_call_runs_untraced_and_the_tracer_comes_back() -> None:
    def check(fake: _RecordingSys) -> None:
        during: list[list[object]] = []

        def call() -> int:
            during.append(list(fake.calls))
            return 8

        assert untraced(call) == 8
        assert during == [[None]], during
        assert fake.calls == [None, _tracer], fake.calls

    _with(_tracer, check)


def test_a_raising_call_still_gets_the_tracer_back_and_its_exception_escapes() -> None:
    def boom() -> None:
        raise ValueError("planted")

    def check(fake: _RecordingSys) -> None:
        try:
            untraced(boom)
        except ValueError as exc:
            assert str(exc) == "planted"
        else:
            raise AssertionError("untraced() swallowed the call's exception")
        assert fake.calls == [None, _tracer], fake.calls

    _with(_tracer, check)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
