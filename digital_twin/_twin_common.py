"""Shared twin helpers: the bounded bookkeeping log, the saturating counter cap, the buffer fill every fake read uses,
the value-walk bounds and the two runner config groups. Imports nothing from digital_twin/ or src/, so every chip
fake, network.py, neopixel.py and both runners can import it."""

from collections import namedtuple

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Generic, NamedTuple, TypeVar, overload

    _T = TypeVar("_T")

    class Walk(NamedTuple):
        # A chip fake's value range and per-reading step; the step is not datasheet-derived (a plausibility bound).
        lo: float
        hi: float
        step: float

    class StatePaths(NamedTuple):
        # Persistent state files; None keeps a chip (or the backup regions) in memory only.
        fram: str | None
        scd30: str | None
        mem_backup: str | None

    class Injections(NamedTuple):
        # Everything a run arms before boot.
        seed: int | None
        faults: list[tuple[str, str, int, int | None, str]]  # (device, op, times, match, kind), as launch parses them
        hangs: list[tuple[str, str, float, int]]
        wifi_outcomes: list[int]

else:

    class _Unsubscripted:
        # typing is absent at runtime: Generic[_T] below reads as a plain object base there.
        def __getitem__(self, _item: object) -> type:
            return object

    Generic = _Unsubscripted()
    _T = None
    Walk = namedtuple("Walk", ("lo", "hi", "step"))
    StatePaths = namedtuple("StatePaths", ("fram", "scd30", "mem_backup"))
    Injections = namedtuple("Injections", ("seed", "faults", "hangs", "wifi_outcomes"))

# 2**30 - 1, the project's shared counter cap (SPECIFICATION.md G.2), kept as the twin's own copy: it imports nothing
# from src/.
COUNTER_CAP = 0x3FFFFFFF
LOG_MAXLEN = 200  # every twin bookkeeping log's default bound, as asy_print_log.py's PrintLogHistory keeps the last N


def fill_buffer(buf: "bytearray | memoryview", data: "bytes | bytearray | memoryview", idle: int = 0x00) -> None:
    # Copies what fits and writes `idle` into the rest, so a read never resizes a bytearray or raises on a memoryview;
    # the level an idle MISO/SDA reads is the fake's documented choice: 0x00 (idle line, fidelity table).
    n = min(len(buf), len(data))
    buf[:n] = data if n == len(data) else memoryview(data)[:n]
    if n < len(buf):
        buf[n:] = bytes([idle]) * (len(buf) - n)


def saturating_add(value: int, n: int = 1) -> int:
    # Every twin counter steps through this (or an `if x < COUNTER_CAP` guard): it never leaves the small-int range.
    return value + n if value <= COUNTER_CAP - n else COUNTER_CAP


class BoundedLog(Generic[_T]):
    # Keep-last-N bookkeeping with a visible drop count; nothing in a running twin reads it. Once full it overwrites its
    # oldest entry in place, so a long run neither grows the heap nor frees half of it at once; reads see oldest first.
    def __init__(self, maxlen: int = LOG_MAXLEN) -> None:
        self.maxlen = maxlen
        self.dropped = 0
        self._items: list[_T] = []
        self._head = 0  # once full: the slot holding the oldest entry

    def __contains__(self, entry: object) -> bool:
        return entry in self._items

    def __eq__(self, other: object) -> bool:
        return self._ordered() == other

    if TYPE_CHECKING:

        @overload
        def __getitem__(self, index: int) -> _T: ...
        @overload
        def __getitem__(self, index: "slice[int | None, int | None, int | None]") -> "list[_T]": ...

    def __getitem__(self, index: "int | slice[int | None, int | None, int | None]") -> "_T | list[_T]":
        if isinstance(index, slice):
            return self._ordered()[index]
        n = len(self._items)
        position = index + n if index < 0 else index
        if not 0 <= position < n:
            raise IndexError("log index out of range")
        return self._items[(self._head + position) % n]

    def __iter__(self) -> "Iterator[_T]":
        return iter(self._ordered())

    def __len__(self) -> int:
        return len(self._items)

    def _ordered(self) -> "list[_T]":
        # Joined by extend(), not +: the ticks-wrap scan reads `slice + slice` of a log that may hold ticks as tick arithmetic.
        ordered = self._items[self._head :]
        ordered.extend(self._items[: self._head])
        return ordered

    def append(self, entry: _T) -> None:
        if len(self._items) < self.maxlen:
            self._items.append(entry)
            return
        self._items[self._head] = entry
        self._head = (self._head + 1) % self.maxlen
        self.dropped = saturating_add(self.dropped)

    def clear(self) -> None:
        self._items = []
        self._head = 0

    def count(self, entry: object) -> int:
        return sum(1 for item in self._items if item == entry)
