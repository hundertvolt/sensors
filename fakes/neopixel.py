"""Fake of micropython-lib's neopixel module for both tiers (the Unix port has none): a bytearray in GRB order as
drivers/led/neopixel/neopixel.py stores it, and a bounded log of every written frame, read back as RGB tuples."""

from _twin_common import LOG_MAXLEN, BoundedLog

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _OutPin(Protocol):
        # What the library asks of its pin: init(OUT) at construction (neopixel.py:16).
        OUT: int

        def init(self, mode: int) -> None: ...


class NeoPixel:
    TEST_API = ("writes", "raise_on_write")
    ORDER = (1, 0, 2, 3)  # GRB(W), micropython-lib neopixel.py:9 (pinned version)

    def __init__(self, pin: "_OutPin", n: int, bpp: int = 3, timing: int = 1) -> None:
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self.timing = timing
        self.buf = bytearray(n * bpp)
        self.pin.init(pin.OUT)
        self.writes: BoundedLog[list[tuple[int, ...]]] = BoundedLog(LOG_MAXLEN)  # each written frame, RGB per pixel
        # Test-only knob: no silicon fault reaches write(), but a raise here is how a test reaches the driver's restart.
        self.raise_on_write: Exception | None = None

    def __getitem__(self, i: int) -> "tuple[int, ...]":
        offset = i * self.bpp
        return tuple(self.buf[offset + self.ORDER[k]] for k in range(self.bpp))

    def __len__(self) -> int:
        return self.n

    def __setitem__(self, i: int, v: "list[int] | tuple[int, ...]") -> None:
        # As micropython-lib neopixel.py:28-31: an int keeps its low byte (py/binary.c:512-521), a float raises TypeError
        # at its component, the earlier components already stored.
        offset = i * self.bpp
        for k in range(self.bpp):
            self.buf[offset + self.ORDER[k]] = v[k]

    def fill(self, v: "tuple[int, ...]") -> None:
        for i in range(self.n):
            self[i] = v

    def write(self) -> None:
        # The real write() is one blocking bitstream call with no return value (machine.bitstream, neopixel.py write()).
        if self.raise_on_write is not None:
            raise self.raise_on_write
        self.writes.append([self[i] for i in range(self.n)])
