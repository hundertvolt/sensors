"""Leveled console logging (PrintLog), the one ungated console line (console()), a bounded
error/warning history (PrintLogHistory) with optional FRAM-backed persistence (PrintLogHistoryStore), and the C-stack
fatal flag the supervisor reads.

A code equal to the history's newest entry is counted and written through but spends no new slot; the console prints
every call at its level and, below it, a caught MemoryError's own text through console(). Never raises: a FRAM chunk
operation raises only by allocation, which reads as unreadable or fails the write, its text printed through console().
"""

import asyncio
import struct
import sys
from collections import deque, namedtuple

from micropython import const

from asy_crc_checks import CRC8

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context  # asyncio's handler context, dict[str, Any] in the stub
    from typing import NamedTuple, Protocol, TypedDict

    # The envelope get_log()/get_error_counter() return project-wide - one entry per module name.
    # Declared here (their only shared definition) and imported by every module that returns one.
    class ErrEntry(TypedDict):
        ErrCount: int
        ErrNum: list[int]
        ErrType: list[str]

    ErrorLog = dict[str, ErrEntry]

    from asy_base_classes import RegionBuffer
    from asy_crc_checks import CRCBase

    # Narrow structural Protocols for the FRAM slice this file calls - kept even now that
    # asy_fram_manager.py is promoted to src/, avoiding a real runtime import cycle (it imports
    # PrintLogHistory from here) and decoupling from its concrete chunk shapes.
    class _FramChunk(Protocol):
        def get_buffer(self) -> "RegionBuffer": ...

        async def read_into(self, buf: "RegionBuffer") -> bool | None: ...

        async def write_into(self, buf: "RegionBuffer") -> bool: ...

    class _FramManager(Protocol):
        def get_chunk(
            self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8, *, owner: str,
        ) -> "_FramChunk | None": ...

        def get_pause(self) -> bool: ...


# defs for PrintLog
_LOG_OFF = const(0)
_LOG_ERR = const(1)
_LOG_WARN = const(2)
_LOG_ONCE = const(3)
_LOG_EVENT = const(4)
_LOG_ALL = const(5)

# defs for history logging
_NO_ERR = const(0x00)
_MAX_ERR = const(0x7F)
_NO_WRN = const(0x80)
_MAX_WRN = const(0xFF)
_MAX_CNT = const(0xFFFF)
_WRAP_MAX = const(0x3FFFFFFF)  # the wrapping counters' top, inside the small-int range: compared for equality or by masked difference
_RESETS_ALL = const(0x1FFFFFFF)  # one bit per store reset() in flight at once, its lowest-free-bit step inside the small-int range

# Code from the global catalog (buildgen/error_catalog.json): a shared one.
_ERR_LOG_RAM_ONLY = const(28)

# A C-stack overflow is a design defect, never a routine failure: any handler that catches it records it here, and the
# supervisor reboots at its next pass (SPECIFICATION.md F.1). The text is the interpreter's own (py/runtime.c:1786, v1.29.0).
_STACK_EXHAUSTED = const("maximum recursion depth exceeded")
_fatal = False  # one-way until the reboot: a handler caught a C-stack overflow


class PrintLog:
    def __init__(self, level: int | None = None, name: str = "") -> None:
        self.name = name
        self.level = _LOG_OFF
        if level is not None:  # None: not given, off; any other invalid level is refused like set_level()'s
            self.set_level(level)

    def _line(self, level: int, args: tuple[object, ...], sep: str, end: str) -> None:
        # Every gated line's one print. Below its level the first caught MemoryError among the arguments still prints its
        # own text through console(), as the memory gates read printed text only (CLAUDE.md memory rule; agent, 2026-10-23).
        # The arm allocates nothing: a tuple iterates on the VM stack (py/compile.c:1575), and console() has a fixed arity.
        if self.level >= level:
            print(self.name, *args, sep=sep, end=end)
            return
        for arg in args:
            if isinstance(arg, MemoryError):
                console(self.name, arg)
                return

    def set_level(self, level: int | None) -> bool:
        # Exact type, so bool, float and None are refused like an out-of-range int (on MicroPython bool is
        # no int subclass); the shared validator cannot be imported here (asy_config_manager imports this).
        if type(level) is int and _LOG_OFF <= level <= _LOG_ALL:
            self.level = level
            return True
        self.err("PrintLog: invalid level refused:", level)
        return False

    def all(self, *args: object, sep: str = " ", end: str = "\n") -> None:
        self._line(_LOG_ALL, args, sep, end)

    def err(self, *args: object, sep: str = " ", end: str = "\n") -> None:
        self._line(_LOG_ERR, args, sep, end)

    def evt(self, *args: object, sep: str = " ", end: str = "\n") -> None:
        self._line(_LOG_EVENT, args, sep, end)

    def one(self, *args: object, sep: str = " ", end: str = "\n") -> None:
        self._line(_LOG_ONCE, args, sep, end)

    def report_unretrieved(self, _loop: object, context: "_Context") -> None:
        # asyncio's handler(loop, context) for a task that ended raising with nobody awaiting it (SPECIFICATION.md F.1).
        # Fixed-argument print() and print_exception() take no heap, so it reports on an exhausted one too; nothing escapes
        # into the loop, and the finally releases the dead task and exception asyncio's own context dict would keep.
        try:
            try:
                if self.level >= _LOG_ERR:
                    print(self.name, context["message"])
                    sys.print_exception(context["exception"])
            finally:
                context["exception"] = None
                context["future"] = None
        except Exception:  # an escape would end asyncio.run(); the supervisor persists a supervised task's end
            pass

    def wrn(self, *args: object, sep: str = " ", end: str = "\n") -> None:
        self._line(_LOG_WARN, args, sep, end)


class PrintLogHistory(PrintLog):
    def __init__(self, history_length: int = 10, level: int | None = None, name: str = "") -> None:
        super().__init__(level=level, name=name)
        # Clamp to [0, _MAX_CNT] (err_count's own uint16 range) before allocating: `[x] * n` can segfault
        # the interpreter uncatchably in a size range bytearray()'s guards don't cover - see SPECIFICATION.md
        # Part F.1's `[x] * n` fact for the measured size boundaries.
        history_length = min(max(history_length, 0), _MAX_CNT)
        try:  # still reachable well below the overflow boundary on a genuinely memory-constrained device
            self.history = deque([_NO_ERR] * history_length, history_length)
        except MemoryError as e:  # a 0-length ring: get_log() then reports no slot, every call still counts
            history_length = 0
            self.history = deque([], 0)
            console(self.name, "PrintLog: history allocation failed:", e)
        self._err_count = 0
        self._pre_setup_slots = 0  # ring slots taken before setup(): RAM-only entries for setup() to keep
        self._write_failing = False  # a write after setup() failed and none has landed since: one LOG_RAM_ONLY per run
        self.initialized = False
        self.restored = False  # True once setup() loaded what an earlier boot stored; a RAM-only history never does
        self._kept = 0  # wrapping counts of _keep()'s appends and _count()'s calls: a reset keeps what arrived since it began
        self._counted = 0
        self._resets = 0  # one bit per store reset() in flight, so overlapping resets each keep their own window
        self._resets_fresh = 0  # those begun with nothing kept since: a repeat of the newest code marks each of them
        self._resets_repeat = 0  # those so marked: each keeps the repeated slot too

    def _clear(self, kept: int, counted: int, bit: int = 0) -> None:
        # A reset's clear, in place and allocation-free (deque item assignment): what arrived since it began stays newest.
        since = self._since_kept(kept, bit)
        for i in range(len(self.history) - since):
            self.history[i] = _NO_ERR
        self._err_count = self._since_counted(counted)
        self._pre_setup_slots = min(self._pre_setup_slots, since)

    def _count(self) -> None:
        self._counted = self._counted + 1 if self._counted < _WRAP_MAX else 0
        if self._err_count < _MAX_CNT:
            self._err_count += 1
        else:
            self._diag("PrintLog: Error count reached maximum value!")

    def _diag(self, *args: object) -> None:  # print-only: inside the logging layer itself; gated on any logging being enabled
        if self.level > _LOG_OFF:
            print(self.name, *args)

    def _keep(self, code: int) -> None:
        # The newest-entry rule, SPECIFICATION.md Part C.7.1. A repeat while a reset is in flight with nothing kept since
        # is marked, on that reset's own bit, rather than appended: a reset that clears keeps the slot it repeats, a
        # refused one leaves the ring as is.
        if not (len(self.history) and self.history[-1] == code):
            self.history.append(code)
            self._kept = self._kept + 1 if self._kept < _WRAP_MAX else 0
            self._resets_fresh = 0
            if not self.initialized and self._pre_setup_slots < len(self.history):
                self._pre_setup_slots += 1
        else:
            self._resets_repeat |= self._resets_fresh

    async def _read(self) -> tuple[int, tuple[int, ...]] | bool | None:
        return True

    def _since_counted(self, counted: int) -> int:  # the count a reset begun at `counted` leaves: its calls since, less once a later reset cleared
        return min((self._counted - counted) & _WRAP_MAX, self._err_count)

    def _since_kept(self, kept: int, bit: int) -> int:  # how many of the newest slots the reset begun at `kept` on `bit` keeps
        repeat = 1 if self._resets_repeat & bit else 0
        return min((self._kept - kept) & _WRAP_MAX, len(self.history) - repeat) + repeat

    async def _store_err(self, min_e: int, max_e: int, errno: int) -> None:
        # errno == _NO_ERR (0) is the shared "nothing to record" sentinel for err_s()/wrn_s() alike; a
        # negative or over-range code is a defect the catalog check prevents: counted, diagnosed, no slot.
        self._count()
        if errno == _NO_ERR:
            return
        code = errno + min_e
        if errno < 0 or code > max_e:
            self._diag("PrintLog: Error number", errno, "is invalid!")
        else:
            self._keep(code)
        if not self.initialized:
            # Return regardless of logging level - don't write stale state to FRAM before setup().
            self._diag("PrintLog: Uninitialized, call setup first!")
            return
        await self._write_through()

    async def _write(self) -> bool:
        return True

    async def _write_through(self) -> None:
        # A failed write after setup() starts a run: its first failure keeps one counted LOG_RAM_ONLY entry in RAM with
        # no second attempt, and the next write that lands persists that entry and ends the run.
        if await self._write():
            self._write_failing = False
            return
        self._diag("PrintLog: History write failed!")
        if not self._write_failing:
            self._write_failing = True
            self._count()
            self._keep(_ERR_LOG_RAM_ONLY)

    async def get_log(self, name: str | None = None) -> "ErrorLog":
        # Reverses _store_err()'s encoding: 0x00/0x80 are "nothing recorded" and report 0, never the
        # raw byte; else shift back by _NO_ERR/_NO_WRN to recover the code. name=None falls back to
        # self.name (every real src/ call site relies on this); tests still pass an explicit override.
        if name is None:
            name = self.name
        err_num = []
        err_type = []
        for errno in self.history:
            if errno in (_NO_ERR, _NO_WRN):
                err_num.append(_NO_ERR)
                err_type.append("N")
            elif errno <= _MAX_ERR:
                err_num.append(errno - _NO_ERR)
                err_type.append("E")
            elif errno <= _MAX_WRN:
                err_num.append(errno - _NO_WRN)
                err_type.append("W")
        return {name: {"ErrCount": self._err_count, "ErrNum": err_num, "ErrType": err_type}}

    async def err_s(self, *args: object, errno: int = _NO_ERR, sep: str = " ", end: str = "\n") -> None:
        await self._store_err(_NO_ERR, _MAX_ERR, errno)
        self._line(_LOG_ERR, args, sep, end)

    async def reset(self) -> bool:  # RAM only: nothing to write, so it clears at once and answers True
        self._clear(self._kept, self._counted)
        self._write_failing = False  # the cleared ring holds no run's entry: the next failed write records one
        self.initialized = True
        return True

    async def setup(self) -> bool:  # no persistence to load in the pure in-memory case
        self.initialized = True
        return True

    async def wrn_s(self, *args: object, wrnno: int = _NO_ERR, sep: str = " ", end: str = "\n") -> None:
        await self._store_err(_NO_WRN, _MAX_WRN, wrnno)
        self._line(_LOG_WARN, args, sep, end)


class PrintLogHistoryStore(PrintLogHistory):
    _HDR_FMT = "<H"  # explicit little-endian, no padding - bare format defaults to "@" here, not "<"
    _HDR_SIZE = struct.calcsize(_HDR_FMT)

    def __init__(self, fram: "_FramManager", history_length: int = 10, level: int | None = None, name: str = "") -> None:
        super().__init__(history_length=history_length, level=level, name=name)
        # len(self.history) is fixed for this object's lifetime (deque maxlen never changes), so
        # this format string is cached once here instead of being rebuilt on every _write()/_read().
        self._history_fmt = "<" + "B" * len(self.history)
        size = self._HDR_SIZE + len(self.history)  # each "B" is exactly 1 byte
        self._heap_failed = False  # the chunk's heap allocation raised; an allocator refusal (None) is not counted
        self._paused = fram.get_pause  # the manager's pause, which refuses every chunk write while it holds
        try:
            self.fram: _FramChunk | None = fram.get_chunk(size, crc=CRC8(), owner=name)
        except MemoryError as e:
            self.fram = None
            self._heap_failed = True
            console(self.name, "PrintLog: FRAM allocation failed:", e)
        if self.fram is None and not self._heap_failed:
            self._diag("PrintLog: FRAM allocation failed!")
        self._write_lock = asyncio.Lock()
        self._write_gen = 0  # one step per _write() call and per reset() write
        self._written_gen = 0  # the _write_gen whose state the last successful write packed

    def _pack_reset(self, dbuf: memoryview, kept: int, counted: int, bit: int) -> None:
        # The image reset() writes, byte by byte into the chunk's buffer (no tuple, no list): the entries since it began
        # (kept, counted) in the newest slots with their count, every other byte cleared.
        struct.pack_into(self._HDR_FMT, dbuf, 0, self._since_counted(counted))
        start = len(self.history) - self._since_kept(kept, bit)
        for i in range(len(self.history)):
            dbuf[self._HDR_SIZE + i] = self.history[i] if i >= start else _NO_ERR

    async def _read(self) -> tuple[int, tuple[int, ...]] | bool | None:
        # Applies nothing: (count, entries) when stored, False for a blank or invalid chunk, None when nothing was read.
        if self.fram is None:
            return None
        try:  # a chunk operation fails only by allocation (the module docstring)
            buf = self.fram.get_buffer()
            dbuf = buf.get_data_buf()
            if dbuf is None:  # the buffer's own allocation failed
                return None
            valid = await self.fram.read_into(buf)
            if valid is None:
                return None
            if not valid:
                return False
            count = struct.unpack_from(self._HDR_FMT, dbuf, 0)[0]
            entries = struct.unpack_from(self._history_fmt, dbuf, self._HDR_SIZE)
        except MemoryError as e:
            console(self.name, "PrintLog: FRAM history read failed:", e)
            return None
        return count, entries

    async def _write(self, kept: int = -1, counted: int = 0, bit: int = 0) -> bool:  # kept >= 0: reset()'s image, never skipped
        if self.fram is None:
            return False
        # The live state is packed and written under one lock, and a call whose state an earlier write already landed
        # skips, so the newest state lands last without relying on asyncio's lock hand-off order; a cancelled or failed
        # write leaves the next queued call to write (ConfigManager._flush_staged()'s rule, by count).
        self._write_gen = self._write_gen + 1 if self._write_gen < _WRAP_MAX else 0
        async with self._write_lock:
            if kept < 0 and self._written_gen == self._write_gen:
                return True
            gen = self._write_gen
            try:  # a chunk operation fails only by allocation (the module docstring)
                buf = self.fram.get_buffer()
                dbuf = buf.get_data_buf()
                if dbuf is None:  # the buffer's own allocation failed
                    return False
                if kept < 0:
                    struct.pack_into(self._HDR_FMT, dbuf, 0, self._err_count)
                    struct.pack_into(self._history_fmt, dbuf, self._HDR_SIZE, *self.history)
                else:
                    self._pack_reset(dbuf, kept, counted, bit)
                ok = bool(await self.fram.write_into(buf))
            except MemoryError as e:
                console(self.name, "PrintLog: FRAM history write failed:", e)
                return False
            if ok:
                self._written_gen = gen
            return ok

    async def reset(self) -> bool:  # False when the cleared state could not be written (ResetErrors then answers "Failed")
        # The state it leaves is written before RAM clears: a pause refusing that write, up front or at the chunk, clears
        # nothing, as "Failed" says (owner, 2026-10-13, paraphrase); any other failure still clears RAM. No setup() guard: what
        # it writes is what the caller asked to persist, and it stops setup() restoring over it (SPECIFICATION.md Part C.7).
        if self._paused():
            self._diag("PrintLog: History reset refused - storage paused")
            return False
        free = ~self._resets & _RESETS_ALL
        bit = free & -free  # the lowest free bit, none while _RESETS_ALL's bits are all in flight
        if not bit:
            self._diag("PrintLog: History reset refused - too many at once")
            return False
        kept = self._kept
        counted = self._counted
        failing = self._write_failing
        self._resets |= bit
        self._resets_fresh |= bit
        try:
            ok = await self._write(kept, counted, bit)
            if not ok and self._paused():  # no await since the write: the chunk refused it under the pause
                self._diag("PrintLog: History reset refused - storage paused")
                return False
            self._clear(kept, counted, bit)  # no await since the write returned either: a queued write packs the cleared ring
        finally:  # a cancelled reset frees its bit too
            self._resets &= ~bit
            self._resets_fresh &= ~bit
            self._resets_repeat &= ~bit
        if not ok:
            if failing:  # that run's entry went with the ring; one failing since the reset began kept its own
                self._write_failing = False
            self._diag("PrintLog: History reset write failed!")
            return False
        self._write_failing = False  # a write that failed meanwhile left its entry in what this write landed
        self.initialized = True
        return True

    async def setup(self) -> bool:  # False: RAM-only until reboot, with one entry saying so in this module's own ring
        if self.initialized:
            return True
        if self.fram is None:
            # An allocator refusal records nothing (owner, 2026-09-16: 'we do not even add errno/wrnno for the out of
            # FRAM memory … Handle via mpremote.'); a heap failure is runtime state and is recorded.
            if self._heap_failed:
                await self.err_s("FRAM history allocation failed - RAM-only until reboot", errno=_ERR_LOG_RAM_ONLY)
            return False
        stored = await self._read()
        if self.initialized:  # a reset() or another setup() won during the read
            return True  # type: ignore[unreachable]  # mypy can't see the mutation
        if stored is None:  # never re-initialised: the stored history stays for the next boot
            self._diag("PrintLog: FRAM unreadable - stored history kept, RAM-only until reboot")
            await self.err_s("FRAM history unreadable - RAM-only until reboot", errno=_ERR_LOG_RAM_ONLY)
            return False
        if isinstance(stored, tuple):  # the stored ring first, entries logged before setup() after it as the newest
            count, entries = stored
            self.restored = True
            if not (self._pre_setup_slots or self._err_count):  # the chunk already holds this state: no write back
                self.history.extend(entries)
                self._err_count = count
                self.initialized = True
                return True
            tail = list(self.history)[len(self.history) - self._pre_setup_slots :]
            self.history.extend(entries)
            self.history.extend(tail)
            self._err_count = count + self._err_count if self._err_count < _MAX_CNT - count else _MAX_CNT
        self._pre_setup_slots = 0
        count = self._err_count
        if await self._write():
            self.initialized = True
            if self._pre_setup_slots or self._err_count != count:  # logged during the write: in RAM only so far
                self._pre_setup_slots = 0
                await self._write_through()
        else:
            self._diag("PrintLog: FRAM setup failed!")
            await self.err_s("FRAM history setup write failed - RAM-only until reboot", errno=_ERR_LOG_RAM_ONLY)
        return self.initialized


_DEFAULT_HISTORY_LENGTH = const(10)

# One module's logging parameters, passed as one object to its constructor and on to make_logger():
# the FRAM manager (None: RAM-only), the history length and the console level (None: off).
if TYPE_CHECKING:

    class LogConfig(NamedTuple):
        fram: "_FramManager | None"
        history_length: int
        debug: int | None

else:
    LogConfig = namedtuple("LogConfig", ("fram", "history_length", "debug"))

DEFAULT_LOG = LogConfig(None, _DEFAULT_HISTORY_LENGTH, None)


def console(name: str, what: object, err: object = None) -> None:
    # The one ungated line, of a layer with no logger or of a logger's line below its level, never kept in a
    # history, so a caught MemoryError's own text reaches the memory gates (CLAUDE.md memory rule). Fixed arity, no
    # star-call: it allocates nothing and cannot raise in its arm (a frame falls back to the C stack, py/objfun.c:268-287).
    if err is None:
        print(name, what)
    else:
        print(name, what, err)


def fatal_reported() -> bool:
    return _fatal


def make_logger(log: LogConfig, name: str) -> PrintLogHistory:
    # Shared fram-vs-memory PrintLogHistory(Store) selection - every direct constructor (as opposed
    # to a logger= reach-through onto an already-built sibling instance) goes through this one place.
    if log.fram is None:
        pr = PrintLogHistory(log.history_length, log.debug, name=name)
        pr.one("Init with memory logging.")
    else:
        pr = PrintLogHistoryStore(log.fram, log.history_length, log.debug, name=name)
        pr.one("Init with FRAM logging.")
    return pr


def report_if_fatal(e: BaseException) -> None:
    # Every broad handler's first statement: it allocates nothing and prints nothing, since it may run with the C stack
    # nearly spent; a call that re-trips the check raises afresh, and the next handler up records it.
    global _fatal
    if isinstance(e, RuntimeError) and e.args and e.args[0] == _STACK_EXHAUSTED:
        _fatal = True
