"""record_prints(): for the `with` block, every line asy_print_log prints (each logger's err/wrn/one/evt/all, its
console() and its diagnostics) is recorded with its arguments, and still printed when `echo` is set. Given a logger,
only that logger's lines are kept; a line's first argument is its logger's name."""

import asy_print_log

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_print_log import PrintLog


class _Recorder:
    # Shadows print() inside asy_print_log only; leaving the block removes the shadow.
    def __init__(self, pr: "PrintLog | None", *, echo: bool) -> None:
        self.kwargs: list[dict[str, object]] = []
        self.lines: list[tuple[object, ...]] = []
        self._echo = echo
        self._name = None if pr is None else pr.name

    def __call__(self, *args: object, **kwargs: object) -> None:
        if self._name is None or (args and args[0] == self._name):
            self.lines.append(args)
            self.kwargs.append(kwargs)
        if self._echo:
            print(*args, **kwargs)  # type: ignore[call-overload]  # the logger's own sep/end, passed through

    def __enter__(self) -> "_Recorder":
        if hasattr(asy_print_log, "print"):
            raise RuntimeError("asy_print_log's print is already recorded")
        asy_print_log.print = self  # type: ignore[attr-defined]  # a module-global shadow of the builtin
        return self

    def __exit__(self, *_exc_info: object) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]

    def text(self) -> str:
        # The recorded lines as printed with the default separator, one per line.
        return "\n".join(" ".join(str(arg) for arg in line) for line in self.lines)


def record_prints(pr: "PrintLog | None" = None, *, echo: bool = False) -> _Recorder:
    return _Recorder(pr, echo=echo)
