"""Digital-twin fake `neopixel` module - the MicroPython Unix port build has no real `neopixel`
module (confirmed directly: `import neopixel` raises ImportError, same finding tests/neopixel.py's
own module docstring already recorded). Deliberately a separate, independent copy from
tests/neopixel.py (owner's explicit choice: full independence from tests/ at twin runtime, over reuse).

Unlike WLAN (see digital_twin/network.py), no behavioral change from the tests/ shape was needed:
a real rp2 NeoPixel.write() is a single busy-wait bit-bang call with no return value and no error
path at all (confirmed against ports/rp2/machine_bitstream.c), so there is no "does it eventually
succeed" state machine to simulate the way WLAN's connect() needed - this fake just records every
committed frame, identically to the unit-test fixture's own shape.
"""

from collections import deque

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_WRITES_MAXLEN = 200  # ad-hoc introspection aid, same shape as digital_twin/machine.py's own
# I2C.log/SPI.log (see that file's own _LOG_MAXLEN comment for the full reasoning) - write() runs
# on every tick of src/asy_neopixel_driver.py's own signal loop for the life of the process, so an
# unbounded list here is the identical latent risk, found by the same session's own audit rather
# than by reproducing a real failure for this specific one.


class NeoPixel:
    def __init__(self, pin: "Any", n: int, bpp: int = 3) -> None:
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self._buf: list[tuple[int, ...]] = [(0,) * bpp for _ in range(n)]
        self.writes: deque[list[tuple[int, ...]]] = deque((), _WRITES_MAXLEN)
        self.raise_on_write: Exception | None = None

    def __setitem__(self, i: int, value: "tuple[int, ...]") -> None:
        self._buf[i] = value

    def __getitem__(self, i: int) -> "tuple[int, ...]":
        return self._buf[i]

    def write(self) -> None:
        if self.raise_on_write is not None:
            raise self.raise_on_write
        self.writes.append(list(self._buf))
