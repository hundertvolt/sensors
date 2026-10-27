"""untraced(call): call() with the coverage tracer off, restored however it ends, so a test's call meant to exhaust the
C stack or take an interrupt cannot end tracing for the rest of its file (SPECIFICATION.md E.5.1). A plain call unless
tests/_coverage_runner.py set `tracer`: build-standard has no sys.settrace, so nothing else touches it."""

import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType
    from typing import TypeVar

    _T = TypeVar("_T")

tracer: "Callable[[FrameType, str, object], object] | None" = None  # the coverage runner's trace function, while it runs a file


def untraced(call: "Callable[[], _T]") -> "_T":
    if tracer is None:
        return call()
    sys.settrace(None)
    try:
        return call()
    finally:
        sys.settrace(tracer)
