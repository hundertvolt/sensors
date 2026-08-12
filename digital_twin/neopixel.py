"""Digital-twin fake `neopixel` module - the MicroPython Unix port build has no real `neopixel`
module (confirmed directly: `import neopixel` raises ImportError, same finding tests/neopixel.py's
own module docstring already recorded). Deliberately a separate, independent copy from
tests/neopixel.py (owner's explicit choice, FINAL_WIRING_PLAN.md's Step 3 clarifying-question
round: full independence from tests/ at Step 5 runtime, over reuse).

Unlike WLAN (see digital_twin/network.py), no behavioral change from the tests/ shape was needed:
a real rp2 NeoPixel.write() is a single busy-wait bit-bang call with no return value and no error
path at all (confirmed against ports/rp2/machine_bitstream.c), so there is no "does it eventually
succeed" state machine to simulate the way WLAN's connect() needed - this fake just records every
committed frame, identically to the unit-test fixture's own shape.
"""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


class NeoPixel:
    def __init__(self, pin: "Any", n: int, bpp: int = 3) -> None:
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self._buf: list[tuple[int, ...]] = [(0,) * bpp for _ in range(n)]
        self.writes: list[list[tuple[int, ...]]] = []
        self.raise_on_write: Exception | None = None

    def __setitem__(self, i: int, value: "tuple[int, ...]") -> None:
        self._buf[i] = value

    def __getitem__(self, i: int) -> "tuple[int, ...]":
        return self._buf[i]

    def write(self) -> None:
        if self.raise_on_write is not None:
            raise self.raise_on_write
        self.writes.append(list(self._buf))
