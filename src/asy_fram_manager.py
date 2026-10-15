"""Chunk-based storage manager for the FRAM chip (asy_fram_driver.py): dual-copy redundancy plus a
busy/idle status byte and CRC give each chunk resilience against a torn write and silent bit rot.
FRAMManager is a bump-pointer allocator (construction order is the on-chip layout, fixed within one build: SPECIFICATION.md A.4/A.7); every method returns a well-defined value - never raises.
"""

import asyncio
import struct

from micropython import const

from asy_base_classes import RegionBuffer, utc_now
from asy_crc_checks import CRCBase, CRCPass
from asy_fram_driver import FRAM_SPI
from asy_print_log import DEFAULT_LOG, PrintLogHistory
from asy_spi_driver import SPI

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
_ERASE_UNIT = const(256)  # one erase write: 2.1 ms at the 1 MHz bus, divides both chip sizes; the size class the webserver's chunked writes use (Part I.3)

# Error-catalog codes this module logs (buildgen/error_catalog.json, SPECIFICATION.md Part C.7.1).
_ERR_INIT = const(10)
_ERR_CALLBACK = const(14)
_ERR_ALLOC = const(20)
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
    def __init__(
        self, manager: "FRAMManager", base_addr: int, size: int, crc: CRCBase, crc_seed: int, verify: int = 0, check_length: int = 8,
    ) -> None:
        self.pr = manager.pr
        self._mempause = manager.get_pause
        self.fram = manager.fram
        self.size = size
        self._verify = verify
        self._verify_counter = 0
        # asy_crc_checks.py needs one instance per concurrent sequence - safe since fram's lock limits
        # this manager to one _read_chunk/_write_chunk/_clear_chunk body running at a time.
        self.crc = crc
        self._crc_seed = crc_seed
        self._check_length = check_length
        self._block_addr = (base_addr, base_addr + self.size + self.crc.length() + _NUM_STATUS_BYTES)
        # fram's lock only serializes one block at a time (released between block 0 and block 1).
        self._op_lock = asyncio.Lock()  # serialises this chunk's own write/read/clear end to end, across both blocks and the scratch buffers
        # Scratch buffers whose sizes are fixed for this chunk's whole life, so they are allocated
        # once here rather than on every call. _op_lock is what makes reusing them safe: only one
        # of this chunk's block operations runs at a time.
        self._sb_buf = bytearray(1)  # one status byte, read back and written through
        try:  # check_length is a caller-supplied int (get_chunk's own param), not hardware-bounded
            self._check_buf: bytearray | None = bytearray(self._check_length)
        except (MemoryError, OverflowError):
            # Degrades exactly as the per-call allocation did: _compare_with() then reports the
            # block as "not verifiably valid", and a read falls back to rewriting it.
            self._check_buf = None
        self._check_mv = None if self._check_buf is None else memoryview(self._check_buf)
        # What _read_into()'s and _compare_with()'s per-iteration closures used to hold in cells.
        self._read_valid = True
        self._read_match = True
        self._read_iters = 0
        self._read_fault = False  # the block read met a fault (bus, guard, status-byte transfer), not just bad content
        self._compare_against: memoryview | None = None

    async def _set_check_sb(self, fram: FRAM_SPI, st_addr: int, val: int, *, check_idle: bool) -> bool | None:
        stat = self._sb_buf  # one buffer per chunk, not one per call - _op_lock serializes its use
        if check_idle:
            # The synchronous driver entry point: the bus lock is held by the block operation
            # around this, so there is no acquisition and no coroutine per command. The driver
            # still logs its own guard errno, exactly as get_values() would have.
            read_status = fram.get_values_sync(stat, st_addr)
            if read_status:
                await fram.report_get_values(read_status)
                await self.pr.err_s("Read status byte failed!", errno=_ERR_FRAM_STATUS_READ)
                self._read_fault = True
                return None
            if stat[0] == _STATUS_UNINIT:
                return True  # a blank block is never read, so it takes no busy marker and stays blank
            if stat[0] != _STATUS_IDLE:
                await self.pr.err_s("Read status byte is not", _STATUS_IDLE, "but", stat[0], errno=_ERR_FRAM_STATUS_BYTE)
                return None
        stat[0] = val  # the read-back above is already consumed, so the same byte carries the write
        write_status = fram.set_values_sync(stat, st_addr)
        # A zero status is the common case and costs no coroutine at all; anything else is either
        # a guard, a refusal, or the stuck-latch warning, and the driver owns each one's message.
        if write_status and not await fram.report_set_values(write_status):
            await self.pr.err_s("Write status byte failed!", errno=_ERR_FRAM_STATUS_WRITE)
            self._read_fault = True
            return None
        return False

    async def _clear_chunk(self, addr: int) -> bool:
        async with self.fram as fram:
            try:
                if await self._handle_status_bytes(fram, addr, _STATUS_UNINIT, check_idle=False) is None:
                    return False
                await asyncio.sleep(0)  # after the status-byte pair; the bus lock is held, CS is not asserted
                # bytearray(n) zero-fills directly (same content as `[_STATUS_UNINIT] * n`) without building that list first
                # `[x] * n` can segfault uncatchably for large n (Part F.1).
                clear_status = fram.set_values_sync(bytearray(self.size + self.crc.length()), addr)
                if clear_status and not await fram.report_set_values(clear_status):
                    await self.pr.err_s("FRAM write failed in _clear_chunk!", errno=_ERR_FRAM_CLEAR_WRITE)
                    return False
            except Exception as e:
                await self.pr.err_s("General write error in _clear_chunk:", e, errno=_ERR_UNEXPECTED)
                return False
        return True

    async def _compare_with(self, buf: bytearray, addr: int) -> tuple[bool, bool, bool, bool]:
        if self._check_buf is None:  # the scratch allocation failed at construction
            await self.pr.err_s("No scratch buffer to check block at", addr, errno=_ERR_ALLOC)
            return False, False, False, True
        self._read_valid = True
        self._read_match = True
        self._read_iters = 0
        self._read_fault = False
        self._compare_against = memoryview(buf)
        try:
            uninit, valid_bytes = await self._read_chunk(self._check_buf, addr)
        finally:
            self._compare_against = None
        valid = self._read_valid and valid_bytes == self.size and self._read_iters > 0
        return valid, uninit, self._read_match, self._read_fault

    async def _handle_status_bytes(
        self, fram: FRAM_SPI, addr: int, val: int, *, check_idle: bool,
    ) -> bool | None:
        st_addr = addr + self.size + self.crc.length()
        uninit0 = await self._set_check_sb(fram, st_addr + _ADDR_STATUS_1, val, check_idle=check_idle)
        if uninit0 is None:
            return None
        uninit1 = await self._set_check_sb(fram, st_addr + _ADDR_STATUS_2, val, check_idle=check_idle)
        if uninit1 is None:
            return None
        if check_idle and uninit0 != uninit1:
            await self.pr.err_s("Read status uninit bytes inconsistent!", errno=_ERR_FRAM_STATUS_DISAGREE)
            return None
        return uninit0

    async def _read(self, buf: bytearray) -> bool | None:
        # True: valid data. False: read, and no copy usable (blank, invalid, or two differing copies).
        # None: not read (paused, lost, a bad buffer, a fault without a valid copy beside it, a failed repair).
        if self.fram.lost.is_set():
            return None
        async with self._op_lock:  # serializes this chunk's own writes/reads/clears end to end
            if self._mempause():
                await self.pr.wrn_s("FRAM communication paused, not reading FRAM!", wrnno=_WRN_FRAM_PAUSED)
                return None
            if len(buf) != self.size + self.crc.length():
                await self.pr.err_s("Data size", len(buf), "does not match chunk size", self.size, "!", errno=_ERR_BAD_ARG)
                return None
            valid, uninit, fault = await self._read_into(buf, self._block_addr[0])
            if not valid:  # if first copy is invalid, take second copy
                if uninit:
                    self.pr.evt("Uninitialized data in block 0, reading block 1")
                elif fault:
                    await self.pr.wrn_s("Read fault in block 0, reading block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
                else:
                    await self.pr.wrn_s("Invalid data in block 0, reading block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
                valid, uninit, fault1 = await self._read_into(buf, self._block_addr[1])
                if not valid:
                    if uninit:
                        self.pr.evt("Uninitialized data in block 1")
                    elif fault1:
                        await self.pr.wrn_s("Read fault in block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
                    else:
                        await self.pr.wrn_s("Invalid data in block 1", wrnno=_WRN_FRAM_BLOCK_INVALID)
                    return None if fault or fault1 else False  # a fault: not read, so the stored bytes are kept
                self.pr.all("Valid data in block 1, overwriting block 0")
                # if block 1 is valid, overwrite invalid block 0 with valid data
                if not await self._write_chunk(buf, self._block_addr[0]):
                    await self.pr.err_s("Writing block 0 failed!", errno=_ERR_FRAM_BLOCK_WRITE)
                    return None  # writing failed, means something is really wrong, better do not use data
                self.pr.all("Data read successfully from block 1")
                return True
            self.pr.all("Data read successfully from block 0")
            valid, uninit, match, fault = await self._compare_with(buf, self._block_addr[1])
            if not valid:  # check block 1 even if block 0 is valid
                if uninit:
                    self.pr.evt("Uninitialized data in block 1, writing block 0 data")
                elif fault:
                    await self.pr.wrn_s("Read fault in block 1, overwriting with block 0 data", wrnno=_WRN_FRAM_BLOCK_INVALID)
                else:
                    await self.pr.wrn_s("Invalid data in block 1, overwriting with block 0 data", wrnno=_WRN_FRAM_BLOCK_INVALID)
                if not await self._write_chunk(buf, self._block_addr[1]):
                    await self.pr.err_s("Writing block 1 failed!", errno=_ERR_FRAM_BLOCK_WRITE)
                    return None  # writing failed, means something is really wrong, better do not use data
                self.pr.all("Data read successfully from block 0")
                return True
            if not match:
                # No generation counter says which block is newer, so a write torn between blocks leaves two valid
                # but differing copies: a hard failure, never a guess (owner, 2026-07-18). The next write heals it.
                await self.pr.err_s("Both blocks valid but different data", errno=_ERR_FRAM_COPIES_DIFFER)
                return False
            self.pr.all("Both blocks valid and data verified")
            return True

    async def _read_chunk(self, buf: bytearray, addr: int) -> tuple[bool, int]:
        # Progress is reported to _read_progress() (chunk state, set up by _read_into()/
        # _compare_with()); returns: uninitialized, crc_valid_bytes.
        async with self.fram as fram:
            try:
                uninit = await self._handle_status_bytes(fram, addr, _STATUS_BUSY, check_idle=True)
                # Before the two early returns, not after: an uninitialized block is the blank
                # chip's whole read, so this is its only scheduling point.
                await asyncio.sleep(0)  # after the status-byte pair; the bus lock is held, CS is not asserted
                if uninit is None:  # error
                    self._read_progress(0, -1, 0)
                    return False, 0
                if uninit:  # no error but unitialized
                    self._read_progress(0, -1, 0)
                    return True, 0

                num_iterations = 0
                last_position = last_span = 0
                total_size = self.size + self.crc.length()
                position = 0
                mv = memoryview(buf)
                await self.crc.check_inc()  # Reset CRC

                while position < total_size:
                    chunk_size = min(len(buf), total_size - position)
                    if chunk_size <= 0:  # a zero-length buf (e.g. check_length=0) would never advance
                        await self.pr.err_s("Zero-length read buffer in _read_chunk!", errno=_ERR_BAD_ARG)
                        self._read_fault = True
                        self._read_progress(0, -1, num_iterations)
                        return False, 0
                    slice_mv = mv[0:chunk_size]  # always filled from the start of the buffer
                    read_status = fram.get_values_sync(slice_mv, addr + position)
                    if read_status:
                        await fram.report_get_values(read_status)
                        await self.pr.err_s("FRAM read error in _read_chunk!", errno=_ERR_FRAM_READ)
                        self._read_fault = True
                        self._read_progress(0, -1, num_iterations)
                        return False, 0
                    if not await self.crc.run_inc(slice_mv, init=self._crc_seed):
                        await self.pr.err_s("Incremental CRC failed in _read_chunk!", errno=_ERR_FRAM_CRC_FAILED)
                        self._read_fault = True
                        self._read_progress(0, -1, num_iterations)
                        return False, 0
                    last_position = position
                    last_span = chunk_size
                    position += chunk_size
                    num_iterations += 1
                    if position < total_size:
                        self._read_progress(last_position, last_span, num_iterations)
                    await asyncio.sleep(0)

                if await self._handle_status_bytes(fram, addr, _STATUS_IDLE, check_idle=False) is None:
                    self._read_progress(0, -1, num_iterations)
                    return False, 0

                length = await self.crc.check_inc()
                if length is None:
                    await self.pr.err_s("CRC error in _read_chunk!", errno=_ERR_FRAM_DATA_CRC)
                    self._read_progress(0, -1, num_iterations)
                    return False, 0
                self._read_progress(last_position, last_span, num_iterations)
            except Exception as e:
                await self.pr.err_s("General read error in _read_chunk:", e, errno=_ERR_UNEXPECTED)
                self._read_fault = True
                self._read_progress(0, -1, 0)
                return False, 0
            else:
                return False, length

    async def _read_into(self, buf: bytearray, addr: int) -> tuple[bool, bool, bool]:
        self._read_valid = True
        self._read_match = True
        self._read_iters = 0
        self._read_fault = False
        self._compare_against = None
        uninit, valid_bytes = await self._read_chunk(buf, addr)
        valid = self._read_valid and valid_bytes == self.size and self._read_iters == 1
        return valid, uninit, self._read_fault

    def _read_progress(self, global_start: int, span: int, n_iter: int) -> None:
        # One _read_chunk() iteration reported back; span < 0 means this read failed. With
        # _compare_against set, each slice is compared as it arrives, since the next iteration
        # refills the scratch buffer - which is why this cannot be a returned value.
        self._read_iters = n_iter
        if span < 0:
            self._read_valid = False
            self._read_match = False
            return
        target = self._compare_against
        if target is None or self._check_mv is None:
            return
        source = self._check_mv
        match = self._read_match
        for offset in range(span):
            match = match and (source[offset] == target[global_start + offset])
        self._read_match = match

    async def _write(self, buf: bytearray) -> bool:
        if self.fram.lost.is_set():
            return False  # no log: the loss is the driver's one FRAM_CHIP_LOST entry
        async with self._op_lock:  # serializes this chunk's own writes/reads/clears end to end
            if self._mempause():
                await self.pr.wrn_s("FRAM communication paused, not writing FRAM!", wrnno=_WRN_FRAM_PAUSED)
                return False
            if len(buf) != self.size + self.crc.length():
                await self.pr.err_s("Data size", len(buf), "does not match chunk size", self.size, "!", errno=_ERR_BAD_ARG)
                return False
            self.pr.all("Writing block 0 data")
            res = await self._write_chunk(buf, self._block_addr[0])
            if not res:
                await self.pr.err_s("Writing block 0 failed!", errno=_ERR_FRAM_BLOCK_WRITE)
                return False
            self.pr.all("Writing block 1 data")
            res = await self._write_chunk(buf, self._block_addr[1])
            if not res:
                await self.pr.err_s("Writing block 1 failed!", errno=_ERR_FRAM_BLOCK_WRITE)
                return False
            if self._verify > 0:
                self._verify_counter += 1
                if self._verify_counter >= self._verify:
                    self._verify_counter = 0
                    self.pr.evt("Verifying written data")
                    for n in range(len(self._block_addr)):
                        valid, uninit, match, _fault = await self._compare_with(buf, self._block_addr[n])
                        if not valid or uninit or not match:
                            await self.pr.err_s("Block", n, "write verification error!", errno=_ERR_FRAM_VERIFY)
                            return False
                    self.pr.evt("Write verification successful")
            return True

    async def _write_chunk(self, buf: bytearray, addr: int) -> bool:
        async with self.fram as fram:
            try:
                if await self._handle_status_bytes(fram, addr, _STATUS_BUSY, check_idle=False) is None:
                    return False
                await asyncio.sleep(0)  # after the status-byte pair; the bus lock is held, CS is not asserted
                if await self.crc.add_into(buf, self.size, init=self._crc_seed) is None:
                    await self.pr.err_s("CRC computation failed!", errno=_ERR_FRAM_CRC_FAILED)
                    return False
                payload_status = fram.set_values_sync(buf, addr)
                if payload_status and not await fram.report_set_values(payload_status):
                    await self.pr.err_s("_write_chunk failed!", errno=_ERR_FRAM_PAYLOAD_WRITE)
                    return False
                await asyncio.sleep(0)  # after the payload command
                if await self._handle_status_bytes(fram, addr, _STATUS_IDLE, check_idle=False) is None:
                    return False
            except Exception as e:
                await self.pr.err_s("General write error in _write_chunk:", e, errno=_ERR_UNEXPECTED)
                return False
        return True

    async def get_verify(self) -> int:
        return self._verify

    async def set_verify(self, value: int) -> None:
        self.pr.evt("FRAM verification set to", value, "write cycles.")
        self._verify_counter = 0
        self._verify = value

    async def clear(self) -> bool:
        if self.fram.lost.is_set():
            return False
        async with self._op_lock:  # serializes this chunk's own writes/reads/clears end to end
            if self._mempause():
                await self.pr.wrn_s("FRAM communication paused, not clearing FRAM!", wrnno=_WRN_FRAM_PAUSED)
                return False
            for n in range(len(self._block_addr)):
                if not await self._clear_chunk(self._block_addr[n]):
                    await self.pr.err_s("Clearing chunks failed!", errno=_ERR_FRAM_CLEAR)
                    return False
                self.pr.evt("Block", n, "cleared")
            return True

    async def invalidate(self) -> bool:
        # Marks both blocks blank (their status bytes only); no pause check: only the erase calls it, after
        # FRAMManager.quiesce() closed the chunk layer.
        if self.fram.lost.is_set():
            return False
        async with self._op_lock:
            for addr in self._block_addr:
                async with self.fram as fram:
                    if await self._handle_status_bytes(fram, addr, _STATUS_UNINIT, check_idle=False) is None:
                        return False
            return True

    async def wait_idle(self) -> None:
        # Returns once this chunk's operation in flight, if any, has ended; one queued behind it then
        # meets the pause FRAMManager.quiesce() set first.
        async with self._op_lock:
            pass


class FRAMChunkBuffer(RegionBuffer):
    def __init__(self, data_size: int, crc_size: int) -> None:
        super().__init__(data_size + crc_size, data_start=0, data_length=data_size)


class FRAMChunk(_FRAMBaseChunk):
    def get_buffer(self) -> FRAMChunkBuffer:
        return FRAMChunkBuffer(self.size, self.crc.length())

    async def read(self) -> bytearray | None:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        if not await self.read_into(buf):
            return None
        dbuf = buf.get_data_buf()
        if dbuf is None:
            # Unreachable: read_into() already failed on a missing buffer, and a RegionBuffer's buffer is fixed at
            # construction - kept to narrow the Optional for the type checker.
            return None
        return bytearray(dbuf)

    async def read_into(self, buf: RegionBuffer) -> bool | None:
        dbuf = buf.get_buf()
        if dbuf is None:
            await self.pr.err_s("No buffer for the chunk read", errno=_ERR_ALLOC)
            return None
        return await self._read(dbuf)

    async def write(self, data: bytes | bytearray) -> bool:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        databuf = buf.get_data_buf()
        if databuf is None:
            await self.pr.err_s("No buffer for the chunk write", errno=_ERR_ALLOC)
            return False
        if len(data) > len(databuf):
            await self.pr.err_s("Data size", len(data), "larger than buffer size", len(databuf), "!", errno=_ERR_BAD_ARG)
            return False
        databuf[0 : len(data)] = data
        del data  # free memory after using preallocated buffer
        return await self.write_into(buf)

    async def write_into(self, buf: RegionBuffer) -> bool:
        dbuf = buf.get_buf()
        if dbuf is None:
            await self.pr.err_s("No buffer for the chunk write", errno=_ERR_ALLOC)
            return False
        return await self._write(dbuf)


class FRAMChunkTimestampedBuffer(RegionBuffer):
    def __init__(self, ts_size: int, data_size: int, crc_size: int) -> None:
        super().__init__(ts_size + data_size + crc_size, data_start=ts_size, data_length=data_size)

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
        check_length: int = 8,
    ) -> None:
        super().__init__(manager, base_addr, struct.calcsize(_TS_FMT) + size, crc, crc_seed, verify=verify, check_length=check_length)
        self._ntp_sync_callback = ntp_sync_callback

    def get_buffer(self) -> FRAMChunkTimestampedBuffer:
        return FRAMChunkTimestampedBuffer(
            struct.calcsize(_TS_FMT), self.size - struct.calcsize(_TS_FMT), self.crc.length(),
        )  # uses ts size and data size separately

    async def read(self) -> tuple[int | None, int | None, bytearray | None]:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        valid, ts, age = await self.read_into(buf)
        if not valid:
            return None, None, None
        dbuf = buf.get_data_buf()
        if dbuf is None:
            # Unreachable: read_into() already failed on a missing buffer, and a RegionBuffer's buffer is fixed at
            # construction - kept to narrow the Optional for the type checker.
            return None, None, None
        return ts, age, bytearray(dbuf)

    async def read_into(self, buf: FRAMChunkTimestampedBuffer) -> tuple[bool | None, int | None, int | None]:
        bbuf = buf.get_buf()
        if bbuf is None:
            await self.pr.err_s("No buffer for the chunk read", errno=_ERR_ALLOC)
            return None, None, None
        res = await self._read(bbuf)
        if res is not True:
            return res, None, None
        age = None
        tbuf = buf.get_ts_buf()
        if tbuf is None:
            # Unreachable: the buffer above exists, and a RegionBuffer's buffer is fixed at construction - kept to
            # narrow the Optional for the type checker.
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
            await self.pr.err_s("NTP sync callback failed:", e, errno=_ERR_CALLBACK)
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
            await self.pr.err_s("No buffer for the chunk write", errno=_ERR_ALLOC)
            return False, False, None
        if len(data) > len(dbuf):
            await self.pr.err_s("Data size", len(data), "larger than buffer size", len(dbuf), "!", errno=_ERR_BAD_ARG)
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
            await self.pr.err_s("NTP sync callback failed:", e, errno=_ERR_CALLBACK)
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
            await self.pr.err_s("No buffer for the chunk write", errno=_ERR_ALLOC)
            return False, False, None
        struct.pack_into(_TS_FMT, tbuf, 0, utc)
        bbuf = buf.get_buf()
        if bbuf is None:
            # Unreachable: get_ts_buf() above found the buffer, and a RegionBuffer's buffer is fixed at construction -
            # kept to narrow the Optional for the type checker.
            return False, False, None
        return await self._write(bbuf), ntp_synced, utc


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
        # Ends when the chip is not up, so the supervisor restarts it and reboots past its budget, as for any
        # declared chip (owner, 2026-09-29: 'the same as all other chips'); a restart sets a lost chip up anew.
        if not self.initialized:
            self.pr.err("FRAM chip declared but not set up - escalating")
            return
        if self.fram.lost.is_set():
            if not await self.setup():
                return
            self.pr.one("FRAM chip answers again")
        await self.fram.lost.wait()

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_watch_chip]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []

    def start_asy_watch_chip(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._watch_chip_loop())

    def get_chunk(
        self, size: int, crc: CRCBase | None = None, verify: int = 0, check_length: int = 8, *, owner: str,
    ) -> FRAMChunk | None:
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
        chunk = FRAMChunk(self, self._allocated_size, size, crc, _owner_seed(owner, crc), verify=verify, check_length=check_length)
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
        check_length: int = 8,
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
            self, self._allocated_size, size, ntp_sync_callback, crc, _owner_seed(owner, crc), verify=verify, check_length=check_length,
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
            ok = await chunk.invalidate() and ok
            step_done()
        if not ok:
            self.pr.err("FRAM erase: a chunk could not be blanked, chip not overwritten")
            return False
        try:
            unit = bytearray(_ERASE_UNIT)
        except MemoryError:
            self.pr.err("FRAM erase: no buffer, chunks blanked only")
            return False
        size = await self.fram.get_size()
        for addr in range(0, size, _ERASE_UNIT):
            async with self.fram as fram:
                status = fram.set_values_sync(unit, addr)
            if status and not await self.fram.report_set_values(status):
                self.pr.err("FRAM erase stopped at", addr)
                return False
            step_done()
            await asyncio.sleep(0)
        self.pr.evt("FRAM erased:", size, "bytes")
        return ok

    async def erase_ready(self) -> bool:
        return self.initialized and not self.fram.lost.is_set() and not await self.fram.get_write_protected()

    async def quiesce(self, step_done: "Callable[[], None]") -> None:
        # Pauses the chunk layer, then waits out each chunk's operation in flight, calling step_done() after
        # each (a reset sequence feeds the watchdog there): afterwards no chunk operation runs until unpaused.
        self.set_pause(value=True)
        for chunk in self._chunks:
            await chunk.wait_idle()
            step_done()

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def setup(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        try:
            await self.fram.setup()
        except Exception as e:
            await self.pr.err_s("FRAM Setup failed:", e, errno=_ERR_INIT)
            return False
        self.initialized = True
        return True
