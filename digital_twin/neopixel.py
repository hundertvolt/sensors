"""Twin fake of micropython-lib's neopixel module (the Unix port has none): a bytearray in GRB order as
drivers/led/neopixel/neopixel.py stores it, and a bounded log of every written frame, read back as RGB tuples as
tests/neopixel.py's are (an independent copy)."""

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
    TEST_API = ("writes", "raise_on_write", "power_dip", "displayed")
    ORDER = (1, 0, 2, 3)  # GRB(W), micropython-lib neopixel.py:9 (pinned version)

    def __init__(self, pin: "_OutPin", n: int, bpp: int = 3) -> None:
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self.buf = bytearray(n * bpp)
        self.pin.init(pin.OUT)
        self.writes: BoundedLog[list[tuple[int, ...]]] = BoundedLog(LOG_MAXLEN)  # each written frame, RGB per pixel
        self.raise_on_write: Exception | None = None  # twin-only test knob
        self._shown: list[tuple[int, ...]] | None = None  # what the physical pixels latched: the last frame written

    def __getitem__(self, i: int) -> "tuple[int, ...]":
        offset = i * self.bpp
        return tuple(self.buf[offset + self.ORDER[k]] for k in range(self.bpp))

    def __len__(self) -> int:
        return self.n

    def __setitem__(self, i: int, v: "tuple[int, ...]") -> None:
        # As micropython-lib neopixel.py:28-31: an int keeps its low byte (py/binary.c:512-521), a float raises TypeError
        # at its component, the earlier components already stored.
        offset = i * self.bpp
        for k in range(self.bpp):
            self.buf[offset + self.ORDER[k]] = v[k]

    def displayed(self) -> "list[tuple[int, ...]]":
        # Twin-only test knob: what the pixels show - the last written frame, or black after a power dip until the next write.
        if self._shown is None:
            return [(0,) * self.bpp for _ in range(self.n)]
        return self._shown

    def fill(self, v: "tuple[int, ...]") -> None:
        for i in range(self.n):
            self[i] = v

    def power_dip(self) -> None:
        # Twin-only test knob: the physical pixel loses its latched colour; the buffer keeps what the driver last set.
        self._shown = None

    def write(self) -> None:
        # The real write() is one blocking bitstream call with no return value (machine.bitstream, neopixel.py write()).
        if self.raise_on_write is not None:
            raise self.raise_on_write
        frame = [self[i] for i in range(self.n)]
        self.writes.append(frame)
        self._shown = frame
