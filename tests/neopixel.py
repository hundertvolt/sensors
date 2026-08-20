"""Fake `neopixel` module for asy_neopixel_driver.py's tests - the MicroPython Unix port build has
no real `neopixel` module (confirmed directly: `import neopixel` raises ImportError). Resolved ahead of any real module because tests/ precedes .frozen on MICROPYPATH, the same convention tests/machine.py/tests/network.py already establish.
"""
# Unlike I2C/SPI (tests/machine.py), there is no raw bus transaction to mock at the driver-boundary
# level here: a real rp2 NeoPixel.write() is a single busy-wait bit-bang call with no return value
# and no error path at all (confirmed against ports/rp2/machine_bitstream.c - see
# asy_neopixel_driver.py's own module docstring). So instead of modeling a transaction, this fake
# records every `NeoPixel[i] = rgb` / `.write()` call, letting tests assert on the actual sequence
# of colors committed to the pixel.

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
        # Every committed frame (i.e. every write() call), as a snapshot of the whole buffer at
        # that point - not just the single pixel a test happened to set, since a real strip could
        # have n > 1 (this driver only ever uses n=1, but the fake stays general).
        self.writes: list[list[tuple[int, ...]]] = []
        # Test-only fault injection, same spirit as tests/machine.py's Timer.raise_on_arm/
        # tests/network.py's WLAN.raise_on - kept even though a real rp2 NeoPixel.write() never
        # raises (see module docstring above), so a test can still exercise defensive code in
        # asy_neopixel_driver.py if it ever adds any.
        self.raise_on_write: Exception | None = None

    def __setitem__(self, i: int, value: "tuple[int, ...]") -> None:
        self._buf[i] = value

    def __getitem__(self, i: int) -> "tuple[int, ...]":
        return self._buf[i]

    def write(self) -> None:
        if self.raise_on_write is not None:
            raise self.raise_on_write
        self.writes.append(list(self._buf))
