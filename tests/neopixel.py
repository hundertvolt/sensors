"""Fake `neopixel` module for the unit tier: the Unix port has none (`import neopixel` raises ImportError), and tests/
precedes .frozen on MICROPYPATH, as for tests/machine.py. Models micropython-lib's driver
(micropython/drivers/led/neopixel/neopixel.py:9-46): a bytearray in G-R-B order, so an unclamped value wraps or raises."""

from machine import Pin, _CallLog


class NeoPixel:
    # As the library: pin.init(OUT) at construction, buf the strip's bytes, ORDER mapping RGB(W) to G-R-B(-W) slots.
    # A real write() is one machine.bitstream() call with no error path (ports/rp2/machine_bitstream.c); the fake
    # keeps each written frame instead, decoded back to RGB tuples. Not modelled: the wire timing itself.
    TEST_API = ("writes", "raise_on_write")
    ORDER = (1, 0, 2, 3)

    def __init__(self, pin: Pin, n: int, bpp: int = 3, timing: int = 1) -> None:
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self.buf = bytearray(n * bpp)
        self.pin.init(pin.OUT)
        self.timing = timing
        # Every frame write() sent, newest 4096, as a list of RGB tuples - `writes[-1][0] == (r, g, b)` reads the
        # last colour of the first pixel; `writes.dropped` counts the frames a long run let go.
        self.writes = _CallLog()
        # Test-only knob: no silicon fault reaches write(), but a raise here is the only way a unit test
        # reaches the supervisor's restart of the driver.
        self.raise_on_write: Exception | None = None

    def __getitem__(self, i: int) -> "tuple[int, ...]":
        offset = i * self.bpp
        return tuple(self.buf[offset + self.ORDER[k]] for k in range(self.bpp))

    def __len__(self) -> int:
        return self.n

    def __setitem__(self, i: int, v: "tuple[int, ...]") -> None:
        # The library's store, one component at a time: a bytearray store wraps an int out of 0-255 (py/binary.c) and
        # raises TypeError on a float, the earlier components already written; a short tuple raises IndexError.
        offset = i * self.bpp
        for k in range(self.bpp):
            self.buf[offset + self.ORDER[k]] = v[k]

    def fill(self, v: "tuple[int, ...]") -> None:
        for i in range(self.n):
            self[i] = v

    def write(self) -> None:
        if self.raise_on_write is not None:
            raise self.raise_on_write
        self.writes.append([self[i] for i in range(self.n)])
