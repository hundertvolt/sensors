"""Chunk-based storage manager for the FRAM chip (asy_fram_driver.py): dual-copy redundancy plus a busy/idle status byte
and CRC give each chunk resilience against a torn write and silent bit rot.

FRAMManager is a bump-pointer allocator (construction order is the on-chip layout, fixed within one build:
SPECIFICATION.md A.4/A.7); every method returns a well-defined value - never raises.
"""

import asyncio
import struct

from micropython import const

from asy_base_classes import RegionBuffer, utc_now
from asy_fram_driver import FRAM_SPI
from asy_print_log import DEFAULT_LOG, PrintLogHistory
from asy_spi_driver import SPI
from crc_checks import CRCBase, CRCPass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from asy_base_classes import ErrorSource, NtpSyncFct, TaskStarter, TimerStarter
    from asy_print_log import ErrorLog, LogConfig

_STATUS_UNINIT = const(0x00)
_STATUS_IDLE = const(0x01)
_STATUS_BUSY = const(0x02)
_ADDR_STATUS_1 = const(0)
_ADDR_STATUS_2 = const(1)
_NUM_STATUS_BYTES = const(2)
_TS_FMT = const("<Q")  # explicit little-endian, no padding - matches asy_print_log.py's own convention
_TS_UNINIT = const(b"\x00")
_NAME = const("FRAM")
_ERASE_UNIT = const(256)  # one erase write: 0.3 ms at 8 MHz, divides both chip sizes; the size class the webserver's chunked writes use (Part I.3)

# Error-catalog codes this module logs (buildgen/error_catalog.json, SPECIFICATION.md Part C.7.1).
_ERR_INIT = const(10)
_ERR_CALLBACK = const(14)
_ERR_BAD_ARG = const(21)
_ERR_UNEXPECTED = const(23)
_ERR_FRAM_STATUS_BYTE = const(46)
_ERR_FRAM_STATUS_DISAGREE = const(47)
_ERR_FRAM_CRC_FAILED = const(48)
_ERR_FRAM_DATA_CRC = const(49)
_ERR_FRAM_VERIFY = const(50)
_ERR_FRAM_COPIES_DIFFER = const(51)
_WRN_FRAM_PAUSED = const(25)
# The chunk layer's own entries for a failure an inner layer also persisted (C.7: each layer keeps its own).
_ERR_FRAM_BLOCK_WRITE = const(100)
_ERR_FRAM_STATUS_READ = const(101)
_ERR_FRAM_STATUS_WRITE = const(102)
_ERR_FRAM_PAYLOAD_WRITE = const(103)
_ERR_FRAM_READ = const(104)
_ERR_FRAM_CLEAR_WRITE = const(105)
_ERR_FRAM_CLEAR = const(106)
_WRN_FRAM_BLOCK_INVALID = const(63)

# The legal chip sizes; tests_scripts/test_buildgen_limits.py keeps them equal to asy_fram_driver's _KNOWN_PRODUCT_IDS.
# @limits max_size in {0x2000, 0x40000}


def _owner_seed(owner: str, crc: CRCBase) -> int:
    # Seeds each owner's CRC differently: after a reflash that shifts the layout by whole chunks, a
    # chunk another owner wrote fails its CRC and reads blank, never as this owner's history.
    width = min(crc.length(), 2)
    if width == 0:
        return 1  # a pass-through CRC ignores its seed
    folded = 0
    for byte in owner.encode():
        folded = (folded * 37 + byte) % 65521  # a prime below 2**16: every intermediate stays a small int
    return 1 + folded % ((1 << (8 * width)) - 2)  # never 0 (zero data would validate) nor all-ones (the unseeded default)


class _FRAMBaseChunk:
    # data chunk layout:
    # [...Data 0...][Status 0-1][Status 0-2][...Data 1...][Status 1-1][Status 1-2]
    def __init__(self, manager: "FRAMManager", base_addr: int, size: int, crc: CRCBase, crc_seed: int, verify: int = 0) -> None:
        self.pr = manager.pr
        self._mempause = manager.get_pause
        self.fram = manager.fram
        self.size = size
        self._verify = verify
        self._verify_counter = 0
        self.crc = crc  # add_into()/check_from() only, which keep no state
        self._crc_seed = crc_seed
        self._block_addr = (base_addr, base_addr + self.size + self.crc.length() + _NUM_STATUS_BYTES)
        # A chunk operation runs whole, never suspending (C.8), so one set of scratch buffers serves each of its steps.
        self._sb_buf = bytearray(1)  # one status byte, read back and written through
        self._pair_buf = bytearray(_NUM_STATUS_BYTES)  # block 1's status pair, read in one command before each write
        self._first = 1  # the block the write in progress took first (_write_chunk(buf, -1) picks it)
        self._read_fault = False  # the block read met a fault (bus, guard, status-byte transfer), not just bad content

    def _set_check_sb(self, st_addr: int, val: int, *, check_idle: bool) -> bool | None:
        stat = self._sb_buf  # one buffer per chunk: an operation runs whole, never suspending (C.8)
        if check_idle:
            if not self.fram.get_values(stat, st_addr):
                self.pr.err_s("Read status byte failed!", errno=_ERR_FRAM_STATUS_READ)
                self._read_fault = True
                return None
            if stat[0] == _STATUS_UNINIT:
                return True  # a blank block is never read, so it takes no busy marker and stays blank
            if stat[0] != _STATUS_IDLE:
                self.pr.err_s("Read status byte is not", _STATUS_IDLE, "but", stat[0], errno=_ERR_FRAM_STATUS_BYTE)
                return None
        stat[0] = val  # the read-back above is already consumed, so the same byte carries the write
        if not self.fram.set_values(stat, st_addr):
            self.pr.err_s("Write status byte failed!", errno=_ERR_FRAM_STATUS_WRITE)
            self._read_fault = True
            return None
        return False

    def _clear_chunk(self, addr: int) -> bool:
        try:
            if self._handle_status_bytes(addr, _STATUS_UNINIT, check_idle=False) is None:
                return False
            # bytearray(n) zero-fills directly (same content as `[_STATUS_UNINIT] * n`) without
            # building that list first - `[x] * n` can segfault uncatchably for large n (Part F.1).
            if not self.fram.set_values(bytearray(self.size + self.crc.length()), addr):
                self.pr.err_s("FRAM write failed in _clear_chunk!", errno=_ERR_FRAM_CLEAR_WRITE)
                return False
        except Exception as e:
            self.pr.err_s("General write error in _clear_chunk:", e, errno=_ERR_UNEXPECTED)
            return False
        return True

    def _compare_with(self, buf: bytearray, addr: int) -> tuple[bool, bool, bool, bool]:
        # The block at addr against buf, a valid copy, read into one buffer per compare: a read's cross-check and a verify,
        # never a log entry's write. Returns valid, uninit, match, fault.
        try:
            other = bytearray(len(buf))
        except MemoryError as e:
            self.pr.err("compare buffer allocation failed:", e)
            return False, False, False, True
        valid, uninit, match = self._read_chunk(other, addr, buf)
        return valid, uninit, match, self._read_fault

    def _handle_status_bytes(self, addr: int, val: int, *, check_idle: bool) -> bool | None:
        st_addr = addr + self.size + self.crc.length()
        uninit0 = self._set_check_sb(st_addr + _ADDR_STATUS_1, val, check_idle=check_idle)
        if uninit0 is None:
            return None
        uninit1 = self._set_check_sb(st_addr + _ADDR_STATUS_2, val, check_idle=check_idle)
        if uninit1 is None:
            return None
        if check_idle and uninit0 != uninit1:
            self.pr.err_s("Read status uninit bytes inconsistent!", errno=_ERR_FRAM_STATUS_DISAGREE)
            return None
        return uninit0

    def _read(self, buf: bytearray) -> bool | None:
        # True: valid data. False: read, and no copy usable (blank, invalid, or two differing copies).
        # None: not read (paused, a bad buffer, a fault without a valid copy beside it, a failed repair).
        if self._mempause():
            self.pr.wrn_s("FRAM communication paused, not reading FRAM!", wrnno=_WRN_FRAM_PAUSED)
            return None
        if len(buf) != self.size + self.crc.length():
            self.pr.err_s("Data size", len(buf), "does not match chunk size", self.size, "!", errno=_ERR_BAD_ARG)
            return None
        valid, uninit, fault = self._read_into(buf, self._block_addr[0])
        if not valid:  # if first copy is invalid, take second copy
            if uninit:
                self.pr.evt("Uninitialized data in block 0, reading block 1")
            elif fault:
                self.pr.wrn_s("Read fault in block 0, reading block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
            else:
                self.pr.wrn_s("Invalid data in block 0, reading block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
            valid, uninit1, fault1 = self._read_into(buf, self._block_addr[1])
            if not valid:
                if uninit1:
                    self.pr.evt("Uninitialized data in block 1")
                elif fault1:
                    self.pr.wrn_s("Read fault in block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
                else:
                    self.pr.wrn_s("Invalid data in block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
                # a fault: not read, so the stored bytes are kept
                return None if fault or fault1 else False
            self.pr.all("Valid data in block 1, overwriting block 0")
            # if block 1 is valid, overwrite invalid block 0 with valid data
            if not self._write_chunk(buf, self._block_addr[0]):
                self.pr.err_s("Writing block 0 failed!", errno=_ERR_FRAM_BLOCK_WRITE)
                return None  # writing failed, means something is really wrong, better do not use data
            self.pr.all("Data read successfully from block 1")
            return True
        self.pr.all("Data read successfully from block 0")
        valid, uninit, match, fault = self._compare_with(buf, self._block_addr[1])
        if not valid:  # check block 1 even if block 0 is valid
            if uninit:
                self.pr.evt("Uninitialized data in block 1, writing block 0 data")
            elif fault:
                self.pr.wrn_s("Read fault in block 1, overwriting with block 0 data", wrnno=_WRN_FRAM_BLOCK_INVALID)
            else:
                self.pr.wrn_s("Invalid data in block 1, overwriting with block 0 data", wrnno=_WRN_FRAM_BLOCK_INVALID)
            if not self._write_chunk(buf, self._block_addr[1]):
                self.pr.err_s("Writing block 1 failed!", errno=_ERR_FRAM_BLOCK_WRITE)
                return None  # writing failed, means something is really wrong, better do not use data
            self.pr.all("Data read successfully from block 0")
            return True
        if not match:
            # No generation counter says which block is newer, so a write torn between blocks leaves two valid
            # but differing copies: a hard failure, never a guess (owner, 2026-07-18). The next write heals it.
            self.pr.err_s("Both blocks valid but different data", errno=_ERR_FRAM_COPIES_DIFFER)
            return False
        self.pr.all("Both blocks valid and data verified")
        return True

    def _read_chunk(self, buf: bytearray, addr: int, against: bytearray | None = None) -> tuple[bool, bool, bool]:
        # The block whole into buf; its CRC runs after the closing status pair, and beside a valid copy (against) only on
        # a mismatch, equal bytes being valid. Returns valid, uninit, match; _read_fault tells a fault.
        self._read_fault = False
        try:
            uninit = self._handle_status_bytes(addr, _STATUS_BUSY, check_idle=True)
            if uninit is not False:  # an error (None), or no error but uninitialized (True)
                return False, uninit is True, False
            if not self.fram.get_values(buf, addr):
                self.pr.err_s("FRAM read error in _read_chunk!", errno=_ERR_FRAM_READ)
                self._read_fault = True
                return False, False, False
            if self._handle_status_bytes(addr, _STATUS_IDLE, check_idle=False) is None:
                return False, False, False
        except Exception as e:
            self.pr.err_s("General read error in _read_chunk:", e, errno=_ERR_UNEXPECTED)
            self._read_fault = True
            return False, False, False
        if against is not None and buf == against:
            return True, False, True
        if self.crc.check_from(buf, init=self._crc_seed) != self.size:
            self.pr.err_s("CRC error in _read_chunk!", errno=_ERR_FRAM_DATA_CRC)
            return False, False, False
        return True, False, against is None

    def _read_into(self, buf: bytearray, addr: int) -> tuple[bool, bool, bool]:
        valid, uninit, _match = self._read_chunk(buf, addr)
        return valid, uninit, self._read_fault

    def _write(self, buf: bytearray) -> bool:
        if self._mempause():
            self.pr.wrn_s("FRAM communication paused, not writing FRAM!", wrnno=_WRN_FRAM_PAUSED)
            return False
        if len(buf) != self.size + self.crc.length():
            self.pr.err_s("Data size", len(buf), "does not match chunk size", self.size, "!", errno=_ERR_BAD_ARG)
            return False
        if self.crc.add_into(buf, self.size, init=self._crc_seed) is None:  # once for both blocks
            self.pr.err_s("CRC computation failed!", errno=_ERR_FRAM_CRC_FAILED)
            return False
        self.pr.all("Writing both blocks, one not IDLE first")
        if not self._write_chunk(buf, -1):
            self.pr.err_s("Writing block", self._first, "failed!", errno=_ERR_FRAM_BLOCK_WRITE)
            return False
        second = 1 - self._first
        if not self._write_chunk(buf, self._block_addr[second]):
            self.pr.err_s("Writing block", second, "failed!", errno=_ERR_FRAM_BLOCK_WRITE)
            return False
        if self._verify > 0:
            self._verify_counter += 1
            if self._verify_counter >= self._verify:
                self._verify_counter = 0
                self.pr.evt("Verifying written data")
                for n in range(len(self._block_addr)):
                    valid, uninit, match, _fault = self._compare_with(buf, self._block_addr[n])
                    if not valid or uninit or not match:
                        self.pr.err_s("Block", n, "write verification error!", errno=_ERR_FRAM_VERIFY)
                        return False
                self.pr.evt("Write verification successful")
        return True

    def _write_chunk(self, buf: bytearray, addr: int) -> bool:
        # addr < 0: a write's first block, picked from block 1's status pair: block 0 only when the pair reads IDLE, a
        # whole copy a cut in block 0 cannot reach; else block 1, so one cut leaves at most one block not IDLE.
        try:
            if addr < 0:
                self._first = 1  # also for a failed read: no proof block 1 is whole, and its guard fails the next command too
                if not self.fram.get_values(self._pair_buf, self._block_addr[1] + self.size + self.crc.length()):
                    self.pr.err_s("Read status byte failed!", errno=_ERR_FRAM_STATUS_READ)
                elif self._pair_buf[0] == self._pair_buf[1] == _STATUS_IDLE:
                    self._first = 0
                addr = self._block_addr[self._first]
            if self._handle_status_bytes(addr, _STATUS_BUSY, check_idle=False) is None:
                return False
            if not self.fram.set_values(buf, addr):
                self.pr.err_s("_write_chunk failed!", errno=_ERR_FRAM_PAYLOAD_WRITE)
                return False
            if self._handle_status_bytes(addr, _STATUS_IDLE, check_idle=False) is None:
                return False
        except Exception as e:
            self.pr.err_s("General write error in _write_chunk:", e, errno=_ERR_UNEXPECTED)
            return False
        return True

    async def get_verify(self) -> int:
        return self._verify

    async def set_verify(self, value: int) -> None:
        self.pr.evt("FRAM verification set to", value, "write cycles.")
        self._verify_counter = 0
        self._verify = value

    def clear(self) -> bool:
        if self._mempause():
            self.pr.wrn_s("FRAM communication paused, not clearing FRAM!", wrnno=_WRN_FRAM_PAUSED)
            return False
        for n in range(len(self._block_addr)):
            if not self._clear_chunk(self._block_addr[n]):
                self.pr.err_s("Clearing chunks failed!", errno=_ERR_FRAM_CLEAR)
                return False
            self.pr.evt("Block", n, "cleared")
        return True

    def invalidate(self) -> bool:
        # Marks both blocks blank (their status bytes only); no pause check: only the erase calls it, with the storage
        # paused.
        return all(self._handle_status_bytes(addr, _STATUS_UNINIT, check_idle=False) is not None for addr in self._block_addr)


class FRAMChunkBuffer(RegionBuffer):
    def __init__(self, data_size: int, crc_size: int, logger: PrintLogHistory | None = None) -> None:
        super().__init__(data_size + crc_size, data_start=0, data_length=data_size, logger=logger)


class FRAMChunk(_FRAMBaseChunk):
    def get_buffer(self) -> FRAMChunkBuffer:
        return FRAMChunkBuffer(self.size, self.crc.length(), self.pr)

    def read(self) -> bytearray | None:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        if not self.read_into(buf):
            return None
        dbuf = buf.get_data_buf()
        if dbuf is None:
            return None
        return bytearray(dbuf)

    def read_into(self, buf: RegionBuffer) -> bool | None:
        dbuf = buf.get_buf()
        if dbuf is None:
            return None
        return self._read(dbuf)

    def write(self, data: bytes | bytearray) -> bool:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        databuf = buf.get_data_buf()
        if databuf is None:
            return False
        if len(data) > len(databuf):
            self.pr.err_s("Data size", len(data), "larger than buffer size", len(databuf), "!", errno=_ERR_BAD_ARG)
            return False
        databuf[0 : len(data)] = data
        del data  # free memory after using preallocated buffer
        return self.write_into(buf)

    def write_into(self, buf: RegionBuffer) -> bool:
        dbuf = buf.get_buf()
        if dbuf is None:
            return False
        return self._write(dbuf)


class FRAMChunkTimestampedBuffer(RegionBuffer):
    def __init__(self, ts_size: int, data_size: int, crc_size: int, logger: PrintLogHistory | None = None) -> None:
        super().__init__(ts_size + data_size + crc_size, data_start=ts_size, data_length=data_size, logger=logger)

    def get_ts_buf(self) -> memoryview | None:
        if self._buf is None:
            return None
        return memoryview(self._buf)[0 : self.data_start]


class FRAMTimestampedChunk(_FRAMBaseChunk):
    def __init__(
        self,
        manager: "FRAMManager",
        base_addr: int,
        size: int,
        ntp_sync_callback: "NtpSyncFct",
        crc: CRCBase,
        crc_seed: int,
        verify: int = 0,
    ) -> None:
        super().__init__(manager, base_addr, struct.calcsize(_TS_FMT) + size, crc, crc_seed, verify=verify)
        self._ntp_sync_callback = ntp_sync_callback

    def get_buffer(self) -> FRAMChunkTimestampedBuffer:
        return FRAMChunkTimestampedBuffer(
            struct.calcsize(_TS_FMT), self.size - struct.calcsize(_TS_FMT), self.crc.length(), self.pr,
        )  # uses ts size and data size separately

    async def read(self) -> tuple[int | None, int | None, bytearray | None]:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        valid, ts, age = await self.read_into(buf)
        if not valid:
            return None, None, None
        dbuf = buf.get_data_buf()
        if dbuf is None:
            return None, None, None
        return ts, age, bytearray(dbuf)

    async def read_into(self, buf: FRAMChunkTimestampedBuffer) -> tuple[bool | None, int | None, int | None]:
        bbuf = buf.get_buf()
        if bbuf is None:
            return None, None, None
        res = self._read(bbuf)
        if res is not True:
            return res, None, None
        age = None
        tbuf = buf.get_ts_buf()
        if tbuf is None:
            return None, None, None
        ts = int(struct.unpack_from(_TS_FMT, tbuf, 0)[0])
        if ts == _TS_UNINIT[0]:
            self.pr.evt("FRAM read data timestamp not valid")
            return True, None, None
        self.pr.evt("FRAM read data timestamp is valid")
        try:  # caller-supplied callback, typed as any Callable - guarded broadly since it isn't
            # guaranteed to be a specific, known-safe implementation
            ntp_synced = await self._ntp_sync_callback()
        except Exception as e:
            self.pr.err_s("NTP sync callback failed:", e, errno=_ERR_CALLBACK)
            ntp_synced = False
        now = utc_now() if ntp_synced else None
        if now is not None:
            # signed: negative after the RTC stepped back (NTP_Offset_S, a correction); the caller treats that as expired
            age = now - ts
            self.pr.evt("FRAM read current time is valid")
        return True, ts, age

    async def write(
        self, data: bytes | bytearray, *, require_ntp: bool = False,
    ) -> tuple[bool, bool, int | None]:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        dbuf = buf.get_data_buf()
        if dbuf is None:
            return False, False, None
        if len(data) > len(dbuf):
            self.pr.err_s("Data size", len(data), "larger than buffer size", len(dbuf), "!", errno=_ERR_BAD_ARG)
            return False, False, None
        dbuf[0 : len(data)] = data
        del data  # free memory after using preallocated buffer
        return await self.write_into(buf, require_ntp=require_ntp)

    async def write_into(
        self,
        buf: FRAMChunkTimestampedBuffer,
        *,
        require_ntp: bool = False,
    ) -> tuple[bool, bool, int | None]:
        try:  # caller-supplied callback, typed as any Callable - guarded broadly since it isn't
            # guaranteed to be a specific, known-safe implementation
            ntp_synced = await self._ntp_sync_callback()
        except Exception as e:
            self.pr.err_s("NTP sync callback failed:", e, errno=_ERR_CALLBACK)
            ntp_synced = False
        now = utc_now() if ntp_synced else None
        if now is None:  # not synced, or the NTP client has not set the clock yet this boot
            ntp_synced = False
            utc = _TS_UNINIT[0]
            self.pr.evt("FRAM write timestamp not valid")
            if require_ntp:
                return False, False, None
        else:
            utc = now
            self.pr.evt("FRAM write timestamp is valid")
        tbuf = buf.get_ts_buf()
        if tbuf is None:
            return False, False, None
        struct.pack_into(_TS_FMT, tbuf, 0, utc)
        bbuf = buf.get_buf()
        if bbuf is None:
            return False, False, None
        return self._write(bbuf), ntp_synced, utc


class FRAMManager:
    def __init__(
        self, spi_bus: SPI, spi_cs: int, max_size: int = 0x2000, log: "LogConfig" = DEFAULT_LOG,
    ) -> None:
        # RAM-only: the one module that never logs into FRAM is the FRAM module itself (owner, SPECIFICATION.md C.7.1).
        self.pr = PrintLogHistory(log.history_length, log.debug, name=_NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        self.size = max_size
        self._allocated_size = 0
        self._pause = False
        self._chunks: list[_FRAMBaseChunk] = []  # one entry per allocation, all made during construction
        self.initialized = False
        self.fram = FRAM_SPI(spi_bus, spi_cs, max_size=self.size, logger=self.pr)

    async def _watch_chip_loop(self) -> None:
        # Ends at once for a chip that never set up, so the supervisor restarts it and reboots past its budget, as for
        # any declared chip (owner, 2026-09-29: 'the same as all other chips'); a chip that set up parks it for the boot.
        if not self.initialized:
            self.pr.err("FRAM chip declared but not set up - escalating")
            return
        await asyncio.Event().wait()

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_watch_chip]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []

    def start_asy_watch_chip(self) -> asyncio.Task[None]:
        return asyncio.create_task(self._watch_chip_loop())

    def get_chunk(self, size: int, crc: CRCBase | None = None, verify: int = 0, *, owner: str) -> FRAMChunk | None:
        if size == 0:  # a chunk storing nothing is never a sensible request, regardless of crc (owner, 2026-07-18: reject generally at the top)
            self.pr.err("Zero-size chunk requested, rejected!")
            return None
        crc = CRCPass() if crc is None else crc
        full_size = 2 * (size + crc.length() + _NUM_STATUS_BYTES)
        # memsize + crc bytes + status bytes, 1-redundant
        self.pr.one(
            "Storage for",
            size,
            "bytes requested, allocating",
            full_size,
            "bytes allover.",
        )
        if (self._allocated_size + full_size) > self.size:
            self.pr.err("FRAM out of memory!")
            return None  # out of memory
        chunk = FRAMChunk(self, self._allocated_size, size, crc, _owner_seed(owner, crc), verify=verify)
        self._chunks.append(chunk)
        self._allocated_size += full_size
        self.pr.one(
            "Allocation successful, FRAM now has",
            self._allocated_size,
            "Bytes allocated.",
        )
        return chunk

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2) - matches asy_base_classes.py's
        # SensorReader.get_error_sources() shape, duck-typed rather than inherited (this class
        # isn't a SensorReader - no measurement data, no config schema).
        return [self]

    def get_loggers(self) -> list[PrintLogHistory]:
        return [self.pr]

    def get_pause(self) -> bool:
        return self._pause

    def get_timestamped_chunk(
        self,
        size: int,
        ntp_sync_callback: "NtpSyncFct",
        crc: CRCBase | None = None,
        verify: int = 0,
        *,
        owner: str,
    ) -> FRAMTimestampedChunk | None:
        if size == 0:  # a chunk storing nothing is never a sensible request, regardless of crc (owner, 2026-07-18: reject generally at the top)
            self.pr.err("Zero-size chunk requested, rejected!")
            return None
        crc = CRCPass() if crc is None else crc
        full_size = 2 * (struct.calcsize(_TS_FMT) + size + crc.length() + _NUM_STATUS_BYTES)
        # timestamp + memsize + crc bytes + status bytes, 1-redundant
        self.pr.one(
            "Storage for",
            size,
            "bytes and timestamp requested, allocating",
            full_size,
            "bytes allover.",
        )
        if (self._allocated_size + full_size) > self.size:
            self.pr.err("FRAM out of memory!")
            return None  # out of memory

        chunk = FRAMTimestampedChunk(
            self, self._allocated_size, size, ntp_sync_callback, crc, _owner_seed(owner, crc), verify=verify,
        )
        self._chunks.append(chunk)
        self._allocated_size += full_size
        self.pr.one(
            "Allocation successful, FRAM now has",
            self._allocated_size,
            "Bytes allocated.",
        )
        return chunk

    def set_pause(self, *, value: bool) -> None:
        # Finish all ongoing ops, reject new ones (owner, 2026-07-18)
        self.pr.evt("Storage pause set to", value)
        self._pause = value

    async def erase_chip(self, step_done: "Callable[[], None]") -> bool:
        # Erase FRAM (owner, 2026-09-30): every chunk's blocks are marked blank first, so no interrupted later
        # write can leave a block that validates; then every byte is zeroed, the blank status value (Part A.4).
        if not await self.erase_ready():
            self.pr.err("FRAM erase refused: chip not ready or write-protected")
            return False
        ok = True
        for chunk in self._chunks:
            ok = chunk.invalidate() and ok
            step_done()
        if not ok:
            self.pr.err("FRAM erase: a chunk could not be blanked, chip not overwritten")
            return False
        try:
            unit = bytearray(_ERASE_UNIT)
        except MemoryError as e:
            self.pr.err("FRAM erase: no buffer, chunks blanked only:", e)
            return False
        size = self.fram.get_size()
        for addr in range(0, size, _ERASE_UNIT):
            if not self.fram.set_values(unit, addr):
                self.pr.err("FRAM erase stopped at", addr)
                return False
            step_done()
            await asyncio.sleep(0)  # the loop stays served between the erase's units
        self.pr.evt("FRAM erased:", size, "bytes")
        return ok

    async def erase_ready(self) -> bool:
        return self.initialized and not self.fram.get_write_protected()

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def setup(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors
        try:
            await self.fram.setup()
        except Exception as e:
            self.pr.err_s("FRAM Setup failed:", e, errno=_ERR_INIT)
            return
        self.initialized = True
