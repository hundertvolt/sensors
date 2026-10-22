"""FixedRandom: the twin chips' random source. Scripted (any value list given), each call answers its kind's next value,
checked against the requested range, and a call beyond the script fails; unscripted, uniform() answers `value` or the
lower bound, randint() the lower bound, getrandbits() 0. Every uniform(a, b) call is recorded as (a, b) in `calls`."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterable


class FixedRandom:
    def __init__(
        self, uniform_values: "Iterable[float] | None" = None, *, randint_values: "Iterable[int] | None" = None,
        getrandbits_values: "Iterable[int] | None" = None, value: "float | None" = None,
    ) -> None:
        scripts = (uniform_values, randint_values, getrandbits_values)
        scripted = any(values is not None for values in scripts)  # a kind left out of a script has an empty one
        self.calls: list[tuple[float, float]] = []
        self._getrandbits = list(getrandbits_values or []) if scripted else None
        self._randint = list(randint_values or []) if scripted else None
        self._uniform = list(uniform_values or []) if scripted else None
        self._value = value

    def getrandbits(self, k: int) -> int:
        if self._getrandbits is None:
            return 0
        assert self._getrandbits, "getrandbits() called more times than scripted"
        result = self._getrandbits.pop(0)
        assert 0 <= result < (1 << k), f"scripted value {result} outside {k} bits"
        return result

    def randint(self, a: int, b: int) -> int:
        if self._randint is None:
            return a
        assert self._randint, "randint() called more times than scripted"
        result = self._randint.pop(0)
        assert a <= result <= b, f"scripted value {result} outside requested range [{a},{b}]"
        return result

    def uniform(self, a: float, b: float) -> float:
        self.calls.append((a, b))
        if self._uniform is None:
            return a if self._value is None else self._value
        assert self._uniform, "uniform() called more times than scripted"
        result = self._uniform.pop(0)
        assert a <= result <= b, f"scripted value {result} outside requested range [{a},{b}]"
        return result
