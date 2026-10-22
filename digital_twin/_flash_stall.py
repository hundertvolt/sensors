"""Models a flash write on the twin: rp2 programs its flash with interrupts off (ports/rp2/rp2_flash.c:168-174,
v1.29.0), so a config flush holds the whole loop for the chip's erase and program time; installed from outside src/, as
_wall_clock.py is."""

import time as _time

from _twin_common import BoundedLog, saturating_add

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import IO

    from _mpy_shed.time_mp import _TicksMs, _TicksUs

# W25Q16JV AC timing, typical then maximum (datasheets/pico w/Winbond_W25Q16JV_Datasheet_RevF.pdf, AC Electrical
# Characteristics): tSE, one 4 KB sector erase, and tPP, one 256-byte page program.
_SECTOR_ERASE_US = (45_000, 400_000)
_PAGE_PROGRAM_US = (400, 3_000)
_PAGE_BYTES = 256  # littlefs's prog size on rp2 (VfsLfs2)
# One flush's littlefs operations beside the data pages, by its worst case: with the largest config file (~1.6 KB, 7
# pages) they make the 5 erases and 43 programs asy_uart_comm's _FLASH_HOLD_MAX_MS is derived from (SPECIFICATION.md N).
FLUSH_ERASES = 5
FLUSH_EXTRA_PAGES = 36
use_max = False  # twin-only test knob: each operation at its datasheet maximum
stalls = 0
stalled_ms = 0
longest_ms = 0
# A gap between two clock readings up to this is taken from ticks_us(), a longer one from ticks_ms(): 2**28 us keeps the
# us reading well inside ticks_diff()'s 2**29 reach on a 2**30-period build.
_US_GAP_MAX_MS = (1 << 28) // 1000
# The twin's plain clock (plain_us()), microseconds that never wrap: its last reading and the sum so far. CPython, which
# imports this through machine for the host tests, has no ticks clock and never reads it.
_last_us, _last_ms = (_time.ticks_us(), _time.ticks_ms()) if hasattr(_time, "ticks_us") else (0, 0)
_plain_us = 0
# The interrupts-off windows the stalls left, (start, length) on the plain clock, newest last: machine.UARTLink, whose
# wire time is read off the same clock, routes a byte due inside one past its RX interrupt.
windows: "BoundedLog[tuple[int, int]]" = BoundedLog(16)


def _open(path: str, mode: str = "r") -> object:
    f = open(path, mode)  # the wrapper owns the file and closes it with the flush
    return _StallingFile(f) if ("w" in mode or "a" in mode) else f


def flush_us(nbytes: int) -> int:
    # The interrupts-off time one flush of an nbytes config file holds the chip.
    which = 1 if use_max else 0
    pages = (nbytes + _PAGE_BYTES - 1) // _PAGE_BYTES + FLUSH_EXTRA_PAGES
    return FLUSH_ERASES * _SECTOR_ERASE_US[which] + pages * _PAGE_PROGRAM_US[which]


class _StallingFile:
    # A written config file whose close() is the flush: what it wrote decides the pages programmed.
    def __init__(self, f: "IO[str]") -> None:
        self._f = f
        self._written = 0

    def __enter__(self) -> "_StallingFile":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._f is not None:
            self._f.close()
            self._f = None  # type: ignore[assignment]
            stall(self._written)

    def write(self, data: str) -> int:
        self._written += len(data.encode())
        return self._f.write(data)


def install(module: object) -> None:
    # Rebinds the open() the given module's code calls (the config manager's): every write it closes stalls the twin.
    setattr(module, "open", _open)


def irqs_were_off(at_us: int) -> bool:
    # Whether `at_us`, on the plain clock, fell inside a stall's interrupts-off window: neither wraps, so a window holds
    # past any tick wrap and a time one whole tick period on misses it.
    return any(start <= at_us < start + length for start, length in windows)


def plain_us(us: "_TicksUs | int", ms: "_TicksMs | int") -> int:
    # A ticks_us() and ticks_ms() reading of this module's clock in plain microseconds: the sum moves on from the last
    # reading by the us ones across a gap up to _US_GAP_MAX_MS, by the ms ones across a longer one.
    global _last_us, _last_ms, _plain_us
    gap_ms = _time.ticks_diff(ms, _last_ms)
    _plain_us += _time.ticks_diff(us, _last_us) if gap_ms <= _US_GAP_MAX_MS else gap_ms * 1000
    _last_us, _last_ms = us, ms
    return _plain_us


def reset_test_state() -> None:
    # Test-only: the recorded stalls and their windows back to none, the knob to the typical times
    # (machine.reset_test_state() calls it).
    global use_max, stalls, stalled_ms, longest_ms
    use_max = False
    stalls = stalled_ms = longest_ms = 0
    windows.clear()


def restart(us: "_TicksUs | int", ms: "_TicksMs | int") -> None:
    # Test-only: the plain clock reads zero at the reading (us, ms), for a test that runs the twin on its own clock.
    global _last_us, _last_ms, _plain_us
    _last_us, _last_ms, _plain_us = us, ms, 0


def stall(nbytes: int) -> None:
    # Busy-waits the flush's time, nothing else running, and leaves its window to the UART model.
    global stalls, stalled_ms, longest_ms
    us = flush_us(nbytes)
    start, start_ms = _time.ticks_us(), _time.ticks_ms()
    while _time.ticks_diff(_time.ticks_us(), start) < us:
        pass
    windows.append((plain_us(start, start_ms), _time.ticks_diff(_time.ticks_us(), start)))
    ms = us // 1000
    stalls = saturating_add(stalls)
    stalled_ms = saturating_add(stalled_ms, ms)
    longest_ms = max(longest_ms, ms)
