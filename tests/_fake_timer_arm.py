"""RaiseOnArm: for the `with` block, the machine fake's Timer.init() raises as rp2's does on an exhausted alarm pool
(OSError(ENOMEM)) or with the given class (MemoryError: src/ guards each arm with `except (OSError, MemoryError)`,
neither class covering the other, SPECIFICATION.md Part F); both knobs are back to what they were on exit."""

from machine import Timer


class RaiseOnArm:
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc
        self._saved: tuple[bool, type[BaseException]] = (Timer.raise_on_arm, Timer.raise_on_arm_exc)

    def __enter__(self) -> "RaiseOnArm":
        self._saved = (Timer.raise_on_arm, Timer.raise_on_arm_exc)
        Timer.raise_on_arm_exc = self._exc
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *_exc_info: object) -> None:
        Timer.raise_on_arm, Timer.raise_on_arm_exc = self._saved
