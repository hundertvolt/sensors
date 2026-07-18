"""Chunk-based storage manager for the FRAM chip (asy_fram_driver.py): dual-copy redundancy plus
CRC gives each chunk resilience against a torn write (a status-byte busy/idle protocol detects a
write interrupted by power loss) and silent bit rot (CRC-checked on every read, self-healing the
other copy when only one is invalid). AsyFramManager is a bump-pointer allocator - get_chunk()/
get_timestamped_chunk() carve out fixed offsets in call order, so every device's *instantiation
order* of these calls is that device's on-chip layout and must stay identical across firmware
versions for existing stored data to still decode correctly.

Contract: every method returns a well-defined value (False/None, or an all-None/False tuple for
the timestamped variant) - never raises. All chunks allocated from one AsyFramManager share that
manager's own PrintLogHistory instance (passed as each chunk's `logger`), so error/warning codes
threaded through `errno`/`wrnno` must stay unique across this whole file, not just per class - see
BACKLOG.md for the full chunk-layout and error-numbering rationale, and for why "both copies valid
but different" (an interrupted 2-copy write, no generation counter to say which is newer) is a
deliberate hard failure rather than a guessed fallback.
"""

import asyncio
import struct
import time

from micropython import const

from asy_fram_driver import FRAM_SPI
from asy_spi_driver import SPI
from base_classes import LockableBuffer
from crc_checks import CRC_Base, CRC_Pass
from print_log import PrintLogHistory

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

_STATUS_UNINIT = const(0x00)
_STATUS_IDLE = const(0x01)
_STATUS_BUSY = const(0x02)
_ADDR_STATUS_1 = const(0)
_ADDR_STATUS_2 = const(1)
_NUM_STATUS_BYTES = const(2)
_TS_FMT = const("<Q")  # explicit little-endian, no padding - matches print_log.py's own convention
_TS_UNINIT = const(b"\x00")


class _AsyBaseFramChunk:
    # data chunk layout:
    # [...Data 0...][Status 0-1][Status 0-2][...Data 1...][Status 1-1][Status 1-2]
    def __init__(
        self,
        fram: FRAM_SPI,
        base_addr: int,
        size: int,
        mempause: "Callable[[], bool]",
        crc: CRC_Base,
        logger: PrintLogHistory,
        verify: int = 0,
        check_length: int = 8,
    ) -> None:
        self.pr = logger
        self.mempause = mempause
        self.fram = fram
        self.size = size
        self.verify = verify
        self.verify_counter = 0
        # crc_checks.py needs one instance per concurrent sequence; safe here since every chunk
        # shares fram's own lock, so at most one _read_chunk/_write_chunk/_clear_chunk body (on
        # any chunk this manager allocates) ever runs at a time.
        self.crc = crc
        self.check_length = check_length
        self.block_addr = (base_addr, base_addr + self.size + self.crc.length() + _NUM_STATUS_BYTES)
        # fram's own lock only serializes one block at a time, not a whole write()/read()/clear()
        # (each block re-acquires it separately) - this one serializes this chunk's own top-level
        # operations end to end, so concurrent callers can't interleave between its two blocks.
        self._op_lock = asyncio.Lock()

    async def set_verify(self, value: int) -> None:
        self.pr.evt("FRAM verification set to", value, "write cycles.")
        self.verify_counter = 0
        self.verify = value

    async def get_verify(self) -> int:
        return self.verify

    async def _write(self, buf: bytearray, override_pause: bool = False) -> bool:
        async with self._op_lock:  # serializes this chunk's own writes/reads/clears end to end
            if (not override_pause) and (self.mempause()):
                await self.pr.wrn_s("FRAM communication paused, not writing FRAM!", wrnno=60)
                return False
            if len(buf) != self.size + self.crc.length():
                await self.pr.err_s("Data size", len(buf), "does not match chunk size", self.size, "!", errno=60)
                return False
            self.pr.all("Writing block 0 data")
            res = await self._write_chunk(buf, self.block_addr[0])
            if not res:
                await self.pr.err_s("Writing block 0 failed!", errno=61)
                return False
            self.pr.all("Writing block 1 data")
            res = await self._write_chunk(buf, self.block_addr[1])
            if not res:
                await self.pr.err_s("Writing block 1 failed!", errno=62)
                return False
            if self.verify > 0:
                self.verify_counter += 1
                if self.verify_counter >= self.verify:
                    self.verify_counter = 0
                    self.pr.evt("Verifying written data")
                    for n in range(len(self.block_addr)):
                        valid, uninit, match = await self._compare_with(buf, self.block_addr[n])
                        if not valid or uninit or not match:
                            await self.pr.err_s("Block", n, "write verification error!", errno=63 + n)
                            return False
                    self.pr.evt("Write verification successful")
            return True

    async def _read(self, buf: bytearray, override_pause: bool = False) -> bool:
        async with self._op_lock:  # serializes this chunk's own writes/reads/clears end to end
            if (not override_pause) and (self.mempause()):
                await self.pr.wrn_s("FRAM communication paused, not reading FRAM!", wrnno=70)
                return False
            if len(buf) != self.size + self.crc.length():
                await self.pr.err_s("Data size", len(buf), "does not match chunk size", self.size, "!", errno=70)
                return False
            valid, uninit = await self._read_into(buf, self.block_addr[0])
            if not valid:  # if first copy is invalid, take second copy
                if uninit:
                    self.pr.evt("Uninitialized data in block 0, reading block 1")
                else:
                    await self.pr.wrn_s("Invalid data in block 0, reading block 1", wrnno=71)
                valid, uninit = await self._read_into(buf, self.block_addr[1])
                if not valid:
                    if uninit:
                        self.pr.evt("Uninitialized data in block 1")
                    else:
                        await self.pr.wrn_s("Invalid data in block 1", wrnno=72)
                    return False  # none of the copies is valid
                self.pr.all("Valid data in block 1, overwriting block 0")
                # if block 1 is valid, overwrite invalid block 0 with valid data
                res = await self._write_chunk(buf, self.block_addr[0])
                if not res:
                    await self.pr.err_s("Writing block 0 failed!", errno=71)
                    # writing failed, means something is really wrong, better do not use data
                    return False
                self.pr.all("Data read successfully from block 1")
                return True
            self.pr.all("Data read successfully from block 0")
            valid, uninit, match = await self._compare_with(buf, self.block_addr[1])
            if not valid:  # check block 1 even if block 0 is valid
                if uninit:
                    self.pr.evt("Uninitialized data in block 1, writing block 0 data")
                else:
                    await self.pr.wrn_s("Invalid data in block 1, overwriting with block 0 data", wrnno=73)
                # write valid data into block 1
                res = await self._write_chunk(buf, self.block_addr[1])
                if not res:
                    await self.pr.err_s("Writing block 1 failed!", errno=72)
                    # writing failed, means something is really wrong, better do not use data
                    return False
                self.pr.all("Data read successfully from block 0")
                return True
            if not match:
                # Deliberate: no generation counter records which block is newer, so a write torn
                # between finishing block 0 and starting block 1 leaves two self-consistent but
                # differing copies with no safe way to pick one - reported as failure, not guessed.
                await self.pr.err_s("Both blocks valid but different data", errno=73)
                return False
            self.pr.all("Both blocks valid and data verified")
            return True

    async def clear(self, override_pause: bool = False) -> bool:
        async with self._op_lock:  # serializes this chunk's own writes/reads/clears end to end
            if (not override_pause) and (self.mempause()):
                await self.pr.wrn_s("FRAM communication paused, not clearing FRAM!", wrnno=80)
                return False
            for n in range(len(self.block_addr)):
                if not await self._clear_chunk(self.block_addr[n]):
                    await self.pr.err_s("Clearing chunks failed!", errno=80)
                    return False
                self.pr.evt("Block", n, "cleared")
            return True

    async def get_pause(self) -> bool:
        return self.mempause()

    async def _read_into(self, buf: bytearray, addr: int) -> tuple[bool, bool]:
        valid = True
        n_iter = 0

        async def cb(bs: tuple[int, int] | None, gs: tuple[int, int] | None, ni: int) -> None:
            nonlocal valid, n_iter
            n_iter = ni
            valid = valid and not (bs is None or gs is None)

        uninit, valid_bytes = await self._read_chunk(buf, addr, cb)
        valid = valid and valid_bytes == self.size and n_iter == 1
        return valid, uninit

    async def _compare_with(self, buf: bytearray, addr: int) -> tuple[bool, bool, bool]:
        try:  # check_length is a caller-supplied int (get_chunk's own param), not hardware-bounded
            temp = bytearray(self.check_length)
        except (MemoryError, OverflowError):
            return False, False, False
        mvt = memoryview(temp)
        mvb = memoryview(buf)
        valid = match = True
        n_iter = 0

        async def cb(bs: tuple[int, int] | None, gs: tuple[int, int] | None, ni: int) -> None:
            nonlocal valid, match, n_iter, mvt, mvb
            n_iter = ni
            if bs is None or gs is None:
                valid = False
                match = False
            else:
                # No strict= (ruff B905): confirmed against the real MicroPython interpreter that
                # zip() rejects it (CPython 3.10+-only). bs/gs always span the same chunk_size by
                # construction (see _read_chunk) anyway, so there's no truncation risk.
                for bsi, gsi in zip(range(bs[0], bs[1]), range(gs[0], gs[1])):  # noqa: B905
                    match = match and (mvt[bsi] == mvb[gsi])

        uninit, valid_bytes = await self._read_chunk(temp, addr, cb)
        valid = valid and valid_bytes == self.size and n_iter > 0
        return valid, uninit, match

    async def _set_check_sb(self, fram: FRAM_SPI, st_addr: int, val: int, check_idle: bool, err: int) -> bool | None:
        uninit = False
        if check_idle:
            stat = bytearray(1)
            if not await fram.get_values(stat, st_addr):
                await self.pr.err_s("Read status byte failed!", errno=err)
                return None
            if stat[0] != _STATUS_IDLE:  # if required, check if byte is as expected
                if stat[0] != _STATUS_UNINIT:
                    await self.pr.err_s("Read status byte is not", _STATUS_IDLE, "but", stat[0], errno=err + 1)
                    return None
                uninit = True  # no error yet
        # set byte to desired value - check_idle=False has no read-back to fail against above, so
        # it has nothing to reserve err/err+1 for; only check_idle=True's callers need the 3-wide
        # spread (see _handle_status_bytes' own matching gap).
        write_errno = err + 2 if check_idle else err
        if not await fram.set_values(bytearray([val]), st_addr):
            await self.pr.err_s("Write status byte failed!", errno=write_errno)
            return None
        return uninit

    async def _handle_status_bytes(
        self, fram: FRAM_SPI, addr: int, val: int, check_idle: bool, err: int
    ) -> bool | None:
        st_addr = addr + self.size + self.crc.length()
        # check_idle=False can only ever fail at "write status byte failed", so it only needs 2
        # tightly packed errnos; check_idle=True (only _read_chunk's busy-set) can also disagree
        # between bytes, so it keeps the full spread - see BACKLOG.md for the errno-width rationale.
        gap = 3 if check_idle else 1
        uninit0 = await self._set_check_sb(fram, st_addr + _ADDR_STATUS_1, val, check_idle, err)
        if uninit0 is None:
            return None
        uninit1 = await self._set_check_sb(fram, st_addr + _ADDR_STATUS_2, val, check_idle, err + gap)
        if uninit1 is None:
            return None
        if check_idle and uninit0 != uninit1:
            await self.pr.err_s("Read status uninit bytes inconsistent!", errno=err + 2 * gap)
            return None
        return uninit0

    async def _write_chunk(self, buf: bytearray, addr: int) -> bool:
        async with self.fram as fram:
            try:
                # check_idle=False here, so _handle_status_bytes may only set err to err + 1
                if await self._handle_status_bytes(fram, addr, _STATUS_BUSY, False, 10) is None:
                    return False
                if await self.crc.add_into(buf, self.size) is None:
                    await self.pr.err_s("CRC computation failed!", errno=17)
                    return False
                if not await fram.set_values(buf, addr):
                    await self.pr.err_s("_write_chunk failed!", errno=18)
                    return False
                # check_idle=False here, so _handle_status_bytes may only set err to err + 1
                if await self._handle_status_bytes(fram, addr, _STATUS_IDLE, False, 19) is None:
                    return False
            except Exception as e:
                await self.pr.err_s("General write error in _write_chunk:", e, errno=26)
                return False
        return True

    async def _read_chunk(
        self,
        buf: bytearray,
        addr: int,
        cb: "Callable[[tuple[int, int] | None, tuple[int, int] | None, int], Coroutine[Any, Any, None]]",
    ) -> tuple[bool, int]:
        # callback: buf_slice, global_slice, num_iterations, return: uninitialized, crc_valid_bytes
        async with self.fram as fram:
            try:
                # check_idle=True here, so _handle_status_bytes may set err all the way to err + 6
                uninit = await self._handle_status_bytes(fram, addr, _STATUS_BUSY, True, 30)
                if uninit is None:  # error
                    await cb(None, None, 0)
                    return False, 0
                if uninit:  # no error but unitialized
                    await cb(None, None, 0)
                    return True, 0

                num_iterations = 0
                buf_slice = global_slice = None
                total_size = self.size + self.crc.length()
                position = 0
                mv = memoryview(buf)
                await self.crc.check_inc()  # Reset CRC

                while position < total_size:
                    chunk_size = min(len(buf), total_size - position)
                    if chunk_size <= 0:  # a zero-length buf (e.g. check_length=0) would never advance
                        await self.pr.err_s("Zero-length read buffer in _read_chunk!", errno=48)
                        await cb(None, None, num_iterations)
                        return False, 0
                    buf_slice = (0, chunk_size)  # Fill from start of buffer
                    global_slice = (position, position + chunk_size)
                    if not await fram.get_values(mv[buf_slice[0] : buf_slice[1]], addr + position):
                        await self.pr.err_s("FRAM read error in _read_chunk!", errno=37)
                        await cb(None, None, num_iterations)
                        return False, 0
                    if not await self.crc.run_inc(mv[buf_slice[0] : buf_slice[1]]):
                        await self.pr.err_s("Incremental CRC failed in _read_chunk!", errno=38)
                        await cb(None, None, num_iterations)
                        return False, 0
                    position += chunk_size
                    num_iterations += 1
                    if position < total_size:
                        await cb(buf_slice, global_slice, num_iterations)
                    await asyncio.sleep(0)

                # check_idle=False here, so _handle_status_bytes may only set err to err + 1
                if await self._handle_status_bytes(fram, addr, _STATUS_IDLE, False, 39) is None:
                    await cb(None, None, num_iterations)
                    return False, 0

                length = await self.crc.check_inc()
                if length is None:
                    await self.pr.err_s("CRC error in _read_chunk!", errno=46)
                    await cb(None, None, num_iterations)
                    return False, 0
                await cb(buf_slice, global_slice, num_iterations)
                return False, length
            except Exception as e:
                await self.pr.err_s("General read error in _read_chunk:", e, errno=47)
                await cb(None, None, 0)
                return False, 0
        # Unreachable in practice (every path above returns; Lockable.__aexit__ always returns
        # False, never suppresses) - kept because mypy's `-> bool` on __aexit__ can't statically
        # rule that out, so it treats falling through the `async with` as live.
        return False, 0

    async def _clear_chunk(self, addr: int) -> bool:
        async with self.fram as fram:
            try:
                # check_idle=False here, so _handle_status_bytes may only set err to err + 1
                if await self._handle_status_bytes(fram, addr, _STATUS_UNINIT, False, 50) is None:
                    return False
                # bytearray(n) zero-fills directly, same content as `[_STATUS_UNINIT] * n`
                # (0x00) without building that list first - the [x] * n shape can segfault the
                # interpreter uncatchably for large n (see BACKLOG.md); bytearray(n) can't.
                res = await fram.set_values(bytearray(self.size + self.crc.length()), addr)
                if not res:
                    await self.pr.err_s("FRAM write failed in _clear_chunk!", errno=57)
                    return False
            except Exception as e:
                await self.pr.err_s("General write error in _clear_chunk:", e, errno=58)
                return False
        return True


class AsyFramChunkBuffer(LockableBuffer):
    def __init__(self, data_size: int, crc_size: int) -> None:
        super().__init__(data_size + crc_size, data_start=0, data_length=data_size)
        self.crc_size = crc_size

    def get_crc_buf(self) -> memoryview | None:
        if self.buf is None:
            return None
        return memoryview(self.buf)[self.data_end : self.data_end + self.crc_size]


class AsyFramChunk(_AsyBaseFramChunk):
    def __init__(
        self,
        fram: FRAM_SPI,
        base_addr: int,
        size: int,
        mempause: "Callable[[], bool]",
        crc: CRC_Base,
        logger: PrintLogHistory,
        verify: int = 0,
        check_length: int = 8,
    ) -> None:
        super().__init__(fram, base_addr, size, mempause, crc, logger, verify=verify, check_length=check_length)

    async def get_size(self) -> int:
        return self.size

    def get_buffer(self) -> AsyFramChunkBuffer:
        return AsyFramChunkBuffer(self.size, self.crc.length())

    async def write(self, data: bytes | bytearray, override_pause: bool = False) -> bool:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        databuf = buf.get_data_buf()
        if databuf is None:
            return False
        if len(data) > len(databuf):
            # 84, not 80: 80 is _AsyBaseFramChunk.clear()'s own errno, sharing this chunk's logger
            await self.pr.err_s("Data size", len(data), "larger than buffer size", len(databuf), "!", errno=84)
            return False
        databuf[0 : len(data)] = data
        del data  # free memory after using preallocated buffer
        return await self.write_into(buf, override_pause=override_pause)

    async def write_into(self, buf: AsyFramChunkBuffer, override_pause: bool = False) -> bool:
        dbuf = buf.get_buf()
        if dbuf is None:
            return False
        return await self._write(dbuf, override_pause=override_pause)

    async def read(self, override_pause: bool = False) -> bytearray | None:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        if not await self.read_into(buf, override_pause=override_pause):
            return None
        dbuf = buf.get_data_buf()
        if dbuf is None:
            return None
        return bytearray(dbuf)

    async def read_into(self, buf: AsyFramChunkBuffer, override_pause: bool = False) -> bool:
        dbuf = buf.get_buf()
        if dbuf is None:
            return False
        return await self._read(dbuf, override_pause=override_pause)


class AsyFramChunkTimestampedBuffer(LockableBuffer):
    def __init__(self, ts_size: int, data_size: int, crc_size: int) -> None:
        super().__init__(ts_size + data_size + crc_size, data_start=ts_size, data_length=data_size)
        self.crc_size = crc_size

    def get_ts_buf(self) -> memoryview | None:
        if self.buf is None:
            return None
        return memoryview(self.buf)[0 : self.data_start]

    def get_crc_buf(self) -> memoryview | None:
        if self.buf is None:
            return None
        return memoryview(self.buf)[self.data_end : self.data_end + self.crc_size]


class AsyFramTimestampedChunk(_AsyBaseFramChunk):
    def __init__(
        self,
        fram: FRAM_SPI,
        base_addr: int,
        size: int,
        mempause: "Callable[[], bool]",
        ntp_sync_callback: "Callable[[], Coroutine[Any, Any, bool]]",
        crc: CRC_Base,
        logger: PrintLogHistory,
        verify: int = 0,
        check_length: int = 8,
    ) -> None:
        super().__init__(
            fram,
            base_addr,
            struct.calcsize(_TS_FMT) + size,
            mempause,
            crc,
            logger,
            verify=verify,
            check_length=check_length,
        )
        self.ntp_sync_callback = ntp_sync_callback

    async def get_size(self) -> int:
        return self.size - struct.calcsize(_TS_FMT)

    def get_buffer(self) -> AsyFramChunkTimestampedBuffer:
        return AsyFramChunkTimestampedBuffer(
            struct.calcsize(_TS_FMT), self.size - struct.calcsize(_TS_FMT), self.crc.length()
        )  # uses ts size and data size separately

    async def write(
        self, data: bytes | bytearray, require_ntp: bool = False, override_pause: bool = False
    ) -> tuple[bool, int | None, bool]:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        dbuf = buf.get_data_buf()
        if dbuf is None:
            return False, None, False
        if len(data) > len(dbuf):
            await self.pr.err_s("Data size", len(data), "larger than buffer size", len(dbuf), "!", errno=81)
            return False, None, False
        dbuf[0 : len(data)] = data
        del data  # free memory after using preallocated buffer
        return await self.write_into(buf, require_ntp=require_ntp, override_pause=override_pause)

    async def write_into(
        self,
        buf: AsyFramChunkTimestampedBuffer,
        require_ntp: bool = False,
        override_pause: bool = False,
    ) -> tuple[bool, int | None, bool]:
        try:  # caller-supplied callback (async_connect.py, not itself promoted/audited) - could legitimately misbehave
            ntp_synced = await self.ntp_sync_callback()
        except Exception as e:
            await self.pr.err_s("NTP sync callback failed:", e, errno=85)
            ntp_synced = False
        utc = _TS_UNINIT[0]
        if ntp_synced:
            try:
                utc = time.mktime(time.gmtime())
                self.pr.evt("FRAM write timestamp is valid")
            except (OverflowError, OSError) as e:  # rp2's mktime() raises OverflowError past its ~2037 32-bit epoch range
                await self.pr.err_s("Computing write timestamp failed:", e, errno=86)
                utc = _TS_UNINIT[0]
                ntp_synced = False
        if not ntp_synced:
            self.pr.evt("FRAM write timestamp not valid")
            if require_ntp:
                return False, None, False
        tbuf = buf.get_ts_buf()
        if tbuf is None:
            return False, None, False
        try:
            struct.pack_into(_TS_FMT, tbuf, 0, utc)
        except Exception as e:
            await self.pr.err_s("Unpacking Timestamp failed:", e, errno=82)
            tbuf[:] = _TS_UNINIT * struct.calcsize(_TS_FMT)  # uninit
        bbuf = buf.get_buf()
        if bbuf is None:
            return False, None, False
        res = await self._write(bbuf, override_pause=override_pause)
        return ntp_synced, utc, res

    async def read(self, override_pause: bool = False) -> tuple[int | None, int | None, bytearray | None]:
        buf = self.get_buffer()  # preallocate buffer for payload and crc length
        valid, ts, age = await self.read_into(buf, override_pause=override_pause)
        if not valid:
            return None, None, None
        dbuf = buf.get_data_buf()
        if dbuf is None:
            return None, None, None
        return ts, age, bytearray(dbuf)

    async def read_into(
        self, buf: AsyFramChunkTimestampedBuffer, override_pause: bool = False
    ) -> tuple[bool, int | None, int | None]:
        bbuf = buf.get_buf()
        if bbuf is None:
            return False, None, None
        if not await self._read(bbuf, override_pause=override_pause):
            return False, None, None
        age = None
        tbuf = buf.get_ts_buf()
        if tbuf is None:
            return False, None, None
        ts: int | None
        try:
            ts = int(struct.unpack_from(_TS_FMT, tbuf, 0)[0])
        except Exception:
            ts = _TS_UNINIT[0]
        if ts == _TS_UNINIT[0]:
            self.pr.evt("FRAM read data timestamp not valid")
            ts = None
        else:
            self.pr.evt("FRAM read data timestamp is valid")
            try:  # caller-supplied callback (async_connect.py, not itself promoted/audited) - could legitimately misbehave
                ntp_synced = await self.ntp_sync_callback()
            except Exception as e:
                await self.pr.err_s("NTP sync callback failed:", e, errno=87)
                ntp_synced = False
            if ntp_synced:
                try:
                    age = time.mktime(time.gmtime()) - ts
                    self.pr.evt("FRAM read current time is valid")
                except (OverflowError, OSError) as e:  # rp2's mktime() raises OverflowError past its ~2037 32-bit epoch range
                    await self.pr.err_s("Computing read age failed:", e, errno=88)
        return True, ts, age


class AsyFramManager:
    def __init__(
        self, spi_bus: SPI, spi_cs: int, max_size: int = 0x2000, history_length: int = 10, debug: int | None = None
    ) -> None:
        self.pr = PrintLogHistory(history_length, debug)
        self.size = max_size
        self.allocated_size = 0
        self.pause = False
        self.fram = FRAM_SPI(spi_bus, spi_cs, max_size=self.size, logger=self.pr)

    async def setup(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        try:
            await self.fram.setup()
        except Exception as e:
            await self.pr.err_s("FRAM Setup failed:", e, errno=83)
            return False
        return True

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log("FRAM")

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    def set_pause(self, value: bool) -> None:
        self.pr.evt("Storage pause set to", value)
        self.pause = value

    def get_pause(self) -> bool:
        return self.pause

    def get_chunk(
        self, size: int, crc: CRC_Base | None = None, verify: int = 0, check_length: int = 8
    ) -> AsyFramChunk | None:
        crc = CRC_Pass() if crc is None else crc
        full_size = 2 * (size + crc.length() + _NUM_STATUS_BYTES)
        # memsize + crc bytes + status bytes, 1-redundant
        self.pr.one(
            "Storage for",
            size,
            "bytes requested, allocating",
            full_size,
            "bytes allover.",
        )
        if (self.allocated_size + full_size) > self.size:
            self.pr.err("FRAM out of memory!")
            return None  # out of memory
        chunk = AsyFramChunk(
            self.fram,
            self.allocated_size,
            size,
            self.get_pause,
            crc,
            verify=verify,
            check_length=check_length,
            logger=self.pr,
        )
        self.allocated_size += full_size
        self.pr.one(
            "Allocation successful, FRAM now has",
            self.allocated_size,
            "Bytes allocated.",
        )
        return chunk

    def get_timestamped_chunk(
        self,
        size: int,
        ntp_sync_callback: "Callable[[], Coroutine[Any, Any, bool]]",
        crc: CRC_Base | None = None,
        verify: int = 0,
        check_length: int = 8,
    ) -> AsyFramTimestampedChunk | None:
        crc = CRC_Pass() if crc is None else crc
        full_size = 2 * (struct.calcsize(_TS_FMT) + size + crc.length() + _NUM_STATUS_BYTES)
        # timestamp + memsize + crc bytes + status bytes, 1-redundant
        self.pr.one(
            "Storage for",
            size,
            "bytes and timestamp requested, allocating",
            full_size,
            "bytes allover.",
        )
        if (self.allocated_size + full_size) > self.size:
            self.pr.err("FRAM out of memory!")
            return None  # out of memory

        chunk = AsyFramTimestampedChunk(
            self.fram,
            self.allocated_size,
            size,
            self.get_pause,
            ntp_sync_callback,
            crc,
            verify=verify,
            check_length=check_length,
            logger=self.pr,
        )
        self.allocated_size += full_size
        self.pr.one(
            "Allocation successful, FRAM now has",
            self.allocated_size,
            "Bytes allocated.",
        )
        return chunk
