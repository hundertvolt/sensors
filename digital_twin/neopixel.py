"""Digital-twin fake `neopixel` module — the Unix port has no real `neopixel` module at all. Independent copy from `tests/neopixel.py`, not shared.
Unlike WLAN, no behavioral change from the `tests/` shape was needed: real `NeoPixel.write()` is a single busy-wait call with no return value/error path, so this fake just records every committed frame."""

from collections import deque

_WRITES_MAXLEN = 200  # ad-hoc introspection aid, same shape as digital_twin/machine.py's own
# I2C.log/SPI.log (see that file's own _LOG_MAXLEN comment for the full reasoning) - write() runs
# on every tick of src/asy_neopixel_driver.py's own signal loop for the life of the process, so an
# unbounded list here is the identical latent risk, found by the same session's own audit rather
# than by reproducing a real failure for this specific one.


class NeoPixel:
    # `pin` is stored for introspection only and never touched - a real machine.Pin from
    # asy_neopixel_driver.py, None from the twin's own tests - so `object` covers both exactly.
    def __init__(self, pin: object, n: int, bpp: int = 3) -> None:
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
