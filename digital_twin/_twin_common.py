"""Shared twin helpers: the value-walk bounds and the two runner config groups.
Imports nothing from digital_twin/ or src/, so every chip fake and both runners can import it."""

from collections import namedtuple

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import NamedTuple

    class Walk(NamedTuple):
        # A chip fake's value range and per-reading step; the step is not datasheet-derived (a plausibility bound).
        lo: float
        hi: float
        step: float

    class StatePaths(NamedTuple):
        # Persistent state files; None keeps a chip in memory only.
        fram: str | None
        scd30: str | None

    class Injections(NamedTuple):
        # Everything a run arms before boot.
        seed: int | None
        faults: list[tuple[str, str, int]]
        hangs: list[tuple[str, str, float, int]]
        wifi_outcomes: list[int]

else:
    Walk = namedtuple("Walk", ("lo", "hi", "step"))
    StatePaths = namedtuple("StatePaths", ("fram", "scd30"))
    Injections = namedtuple("Injections", ("seed", "faults", "hangs", "wifi_outcomes"))
