"""Models a flash write on the twin: rp2 programs its flash with interrupts off (ports/rp2/rp2_flash.c:167-173, v1.29.0),
so a config flush holds the whole loop for the chip's erase and program time; installed from outside src/, as
_wall_clock.py is."""

import time as _time

from _twin_common import BoundedLog, saturating_add

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import IO

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
# The interrupts-off windows the stalls left, (start, end) in microseconds since EPOCH_US, newest last: the twin UART
# routes a byte whose wire time ends inside one past its RX interrupt (machine.UARTLink._advance()). CPython, which
# imports this through machine for the host tests, has no ticks clock and never reads the epoch.
EPOCH_US = _time.ticks_us() if hasattr(_time, "ticks_us") else 0
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
    setattr(module, "open", _open)  # noqa: B010 - `module` is any module object


def irqs_were_off(at_us: int) -> bool:
    # Whether `at_us` (microseconds since EPOCH_US) fell inside a stall's interrupts-off window.
    return any(start <= at_us < end for start, end in windows)


def reset_test_state() -> None:
    # Test-only: the recorded stalls and their windows back to none, the knob to the typical times
    # (machine.reset_test_state() calls it).
    global use_max, stalls, stalled_ms, longest_ms
    use_max = False
    stalls = stalled_ms = longest_ms = 0
    windows.clear()


def stall(nbytes: int) -> None:
    # Busy-waits the flush's time, nothing else running, and leaves its window to the UART model.
    global stalls, stalled_ms, longest_ms
    us = flush_us(nbytes)
    start = _time.ticks_us()
    while _time.ticks_diff(_time.ticks_us(), start) < us:
        pass
    windows.append((_time.ticks_diff(start, EPOCH_US), _time.ticks_diff(_time.ticks_us(), EPOCH_US)))
    ms = us // 1000
    stalls = saturating_add(stalls)
    stalled_ms = saturating_add(stalled_ms, ms)
    longest_ms = max(longest_ms, ms)
