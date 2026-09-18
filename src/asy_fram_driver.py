# SPDX-FileCopyrightText: 2018 Michael Schroeder for Adafruit Industries (original adafruit_fram,
# CircuitPython) - restructured/rewritten for asyncio + MicroPython, see THIRD_PARTY_LICENSES.md.
# SPDX-License-Identifier: MIT

"""Async SPI driver for one Fujitsu FRAM chip (MB85RS64V 8KB or MB85RS2MTA 256KB, RDID-detected via _KNOWN_PRODUCT_IDS): raw byte-addressed get_values()/set_values() plus write protection.
Opcode/register-constant naming and the write-enable/write/write-disable method shape follow Adafruit's Adafruit_CircuitPython_FRAM; RDID handling and dual-chip detection are this project's own addition, verified against the Fujitsu MB85RS64V (DS501-00015) and MB85RS2MTA (DS501-00032) datasheets.
"""
# CRC/dual-copy data-integrity recovery lives one layer up in asy_fram_manager.py - this file only
# detects device-ID mismatch, a write-enable latch that didn't set/clear, and a stale write-protect
# assumption, self-healing to a safe state without raising (except __init__()'s/setup()'s one-time
# setup errors).

import asyncio

from machine import Pin
from micropython import const

from asy_spi_driver import SPI, SPIDevice
from base_classes import Lockable
from print_log import PrintLogHistory

# RDID response (32 clock cycles after the opcode): manufacturer ID, then the JEDEC continuation-
# code byte, then the two Product ID bytes (1st byte is the more significant one) - all four are
# fixed values for this specific chip, confirmed against the datasheet.
_SPI_MANF_ID = const(0x04)  # Fujitsu
_SPI_CONT_CODE = const(0x7F)  # JEDEC continuation-code byte, fixed for Fujitsu's bank

# Product ID (RDID's 3rd+4th bytes) is chip-specific, unlike manufacturer ID/continuation code above
# (shared project-wide, confirmed against both datasheets below) - keyed by max_size so setup() can
# tell which of this codebase's two known SPI FRAM breakouts is actually wired.
_KNOWN_PRODUCT_IDS: dict[int, int] = {
    0x2000: 0x0302,  # MB85RS64V, 64Kbit/8KB - datasheets/fram/MB85RS64V-DS501-00015-4v0-E.pdf p.10
    0x40000: 0x4803,  # MB85RS2MTA, 2Mbit/256KB - datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10
}

_SPI_OPCODE_WREN = const(0x06)  # Set write enable latch
_SPI_OPCODE_WRDI = const(0x04)  # Reset write enable latch
_SPI_OPCODE_RDSR = const(0x05)  # Read status register
_SPI_OPCODE_WRSR = const(0x01)  # Write status register
_SPI_OPCODE_READ = const(0x03)  # Read memory code
_SPI_OPCODE_WRITE = const(0x02)  # Write memory code
_SPI_OPCODE_RDID = const(0x9F)  # Read device ID

# The four fixed single-byte commands, as module-level constants rather than a `bytearray([...])`
# built on every call - each of those lands in the 32-96 byte size class the heap-layout model
# cares about (HEAP_FRAGMENTATION_MEASUREMENTS.md section 0A.3), several times per stored byte.
_CMD_WREN = b"\x06"
_CMD_WRDI = b"\x04"
_CMD_RDSR = b"\x05"
_CMD_RDID = b"\x9f"

# Status register bits (datasheet): bit7 WPEN, bits6-4 unused, bit3 BP1, bit2 BP0, bit1 WEL, bit0
# fixed 0. Block protection always covers the whole array (BP0+BP1 together), never a sub-range.
_SR_WEL = const(0x02)
_SR_WP_MASK = const(0x8C)  # WPEN | BP1 | BP0
_SR_WP_SET = const(0x8C)
_SR_WP_CLEAR = const(0x00)

# Address-buffer geometry: one opcode byte plus the chip's own address width. A chip larger than
# a 16-bit address space needs three address bytes rather than two.
_ADDR_16BIT_MAX = const(0xFFFF)
_ADDR_BUF_24BIT = const(4)
_ADDR_BUF_16BIT = const(3)

# Generous headroom over a real transaction's low-single-digit-ms cost, while still bounding an
# accidental lock-reentry to a finite wait. Not test-monkeypatchable: MicroPython inlines const()
# at every use site regardless of name (verified directly), so the one test needing this waits it out.
_VERIFY_PRESENT_LOCK_TIMEOUT_S = const(1.0)

# Outcomes of the synchronous write bodies below, as a bit set. They decide what happened; the
# coroutine that owns the operation logs it, with the same wrnno/errno and message as before -
# awaiting a persisted log entry is not something a body holding the bus lock may do.
_W_OK = const(0)
_W_PROTECTED = const(1)  # wrnno 84
_W_WEL_NOT_SET = const(2)  # wrnno 82 (write) / 83 (write protection)
_W_WEL_STUCK = const(4)  # wrnno 81 - advisory: the operation itself still completed
_W_WP_MISMATCH = const(8)  # errno 95


class FRAM_SPI(Lockable):
    def __init__(
        self,
        spi_bus: SPI,
        spi_cs: int,
        logger: PrintLogHistory,
        *,
        wp: bool = False,
        wp_pin: int | None = None,
        max_size: int = 0x2000,
    ) -> None:
        super().__init__()
        self.pr = logger
        self._spidev = SPIDevice(spi_bus, spi_cs)
        self._max_size = max_size
        self._wp = wp  # write protect
        self._wp_pin = None if wp_pin is None else Pin(wp_pin)
        self.initialized = False
        # Pre-allocated scratch buffers, reused across calls instead of allocating fresh on every
        # one (matches SCD30_I2C's buffer-reuse pattern) - safe since every real caller only ever
        # reaches these through this object's own asy_lock (Lockable), serializing access.
        self._id_buf = bytearray(4)
        self._status_buf = bytearray(1)
        self._addr_buf = bytearray(_ADDR_BUF_24BIT) if self._max_size > _ADDR_16BIT_MAX else bytearray(_ADDR_BUF_16BIT)
        self._wrsr_buf = bytearray(2)  # WRSR opcode + target status byte, the one two-byte command
        # The innermost of the three locks, taken once per command rather than once per CS cycle:
        # a five-CS write envelope is indivisible on the wire, and the bus stays interleavable
        # between commands. SPIDevice's own async session takes this same lock for other callers.
        self._bus_lock = self._spidev.asy_lock

    # One CS cycle each, on a bus lock the caller already holds. Everything from here down to
    # _write() is synchronous: the chip is driven by blocking register writes, so a coroutine per
    # CS cycle bought nothing but allocations. The scheduling points live in the public coroutines
    # below, one per command - see HEAP_REMEDIATION_PLAN.md A.1.2.
    def _send_command(self, command: bytes | bytearray) -> None:
        # WREN/WRDI are each a complete, standalone one-byte command (datasheet timing diagrams
        # show CS low only for the opcode); WRSR is the one two-byte command that ends here too.
        spidev = self._spidev
        spidev.session_begin()
        try:
            spidev.write_sync(command)
        finally:
            spidev.session_end()

    def _send_and_read(self, command: bytes | bytearray, read_buffer: bytearray | memoryview) -> None:
        spidev = self._spidev
        spidev.session_begin()
        try:
            spidev.write_sync(command)
            spidev.readinto_sync(read_buffer)
        finally:
            spidev.session_end()

    def _send_and_write(self, command: bytes | bytearray, data: bytes | bytearray | memoryview) -> None:
        spidev = self._spidev
        spidev.session_begin()
        try:
            spidev.write_sync(command)
            spidev.write_sync(data)
        finally:
            spidev.session_end()

    def _check_device_id(self) -> bool:
        expected_prod_id = _KNOWN_PRODUCT_IDS.get(self._max_size)
        if expected_prod_id is None:
            raise ValueError(f"FRAM max_size {self._max_size:#x} has no known product ID to verify against - add it to _KNOWN_PRODUCT_IDS")
        self._send_and_read(_CMD_RDID, self._id_buf)
        prod_id = (self._id_buf[2] << 8) + self._id_buf[3]
        return self._id_buf[0] == _SPI_MANF_ID and self._id_buf[1] == _SPI_CONT_CODE and prod_id == expected_prod_id

    def _read_address(self, address: int, read_buffer: bytearray | memoryview) -> None:
        self._send_and_read(self._setup_addr_buffer(address, _SPI_OPCODE_READ), read_buffer)

    def _read_status(self) -> int:
        self._send_and_read(_CMD_RDSR, self._status_buf)
        return self._status_buf[0]

    def _wel_is_set(self) -> bool:
        return bool(self._read_status() & _SR_WEL)

    def _enable_write(self) -> bool:
        # Shared WREN-and-verify preamble for WRITE/WRSR (datasheet: WEL gates both). Verifying
        # via RDSR instead of trusting WREN blindly catches a corrupted WREN transfer, which the
        # chip would otherwise silently ignore the following WRITE/WRSR for.
        self._send_command(_CMD_WREN)
        return self._wel_is_set()

    def _disable_write(self) -> bool:
        # Shared WRDI-and-verify epilogue: WEL auto-clears after WRITE/WRSR anyway (datasheet), so
        # this is defense-in-depth against that mechanism itself glitching - one cheap retry, then
        # False, which the caller turns into a warning: a stuck latch doesn't undo the operation.
        self._send_command(_CMD_WRDI)
        if not self._wel_is_set():
            return True
        self._send_command(_CMD_WRDI)
        return not self._wel_is_set()

    def _is_write_protected(self) -> bool:
        # The value get_write_protected() reports, without its not-initialized guard: every caller
        # of this one has already passed that guard at the public entry point.
        return self._wp if self._wp_pin is None else not bool(self._wp_pin.value())  # WP active-low

    def _write(self, start_address: int, data: bytes | bytearray | memoryview) -> int:
        if self._is_write_protected():
            # WP8: persisted by the caller, matching AsyFramManager's own "communication paused,
            # not writing" precedent (asy_fram_manager.py, wrnno=60/70/80) for the same class of
            # condition - a refused-but-expected write against a deliberately-gated chip.
            return _W_PROTECTED
        if not self._enable_write():
            return _W_WEL_NOT_SET
        self._send_and_write(self._setup_addr_buffer(start_address, _SPI_OPCODE_WRITE), data)
        return _W_OK if self._disable_write() else _W_WEL_STUCK

    def _set_write_protected(self, *, value: bool) -> int:
        # Always protects the entire array (BP0+BP1) - per-block ranges are unused.
        target = _SR_WP_SET if value else _SR_WP_CLEAR
        if not self._enable_write():
            return _W_WEL_NOT_SET
        if self._wp_pin is not None:
            self._wp_pin.value(True)  # deassert WP first - WP=0 would else block this WRSR too
        self._wrsr_buf[0] = _SPI_OPCODE_WRSR
        self._wrsr_buf[1] = target
        self._send_command(self._wrsr_buf)
        ok = (self._read_status() & _SR_WP_MASK) == target  # verify the one way this can change
        status = _W_OK if self._disable_write() else _W_WEL_STUCK
        if not ok:
            if self._wp_pin is not None:
                self._wp_pin.value(not self._wp)  # unchanged - restore the pin to match reality
            return status | _W_WP_MISMATCH
        self._wp = value
        if self._wp_pin is not None:
            self._wp_pin.value(not value)  # WP active-low, see setup()
        return status

    def _setup_addr_buffer(self, addr: int, opcode: int) -> bytearray:
        # Buffer width is fixed once in __init__ from max_size, which is trusted, not re-derived
        # from _check_device_id() - see SPECIFICATION.md Part C.3.1's FRAM_SPI bullet.
        buffer = self._addr_buf
        if len(buffer) == _ADDR_BUF_24BIT:  # > 16bit address
            buffer[1] = (addr >> 16) & 0xFF
            buffer[2] = (addr >> 8) & 0xFF
            buffer[3] = addr & 0xFF
        else:  # <= 16bit address
            buffer[1] = (addr >> 8) & 0xFF
            buffer[2] = addr & 0xFF
        buffer[0] = opcode
        return buffer

    async def get_write_protected(self) -> bool:
        # With a wp_pin, protection is tied to that physical pin's own value; without one, this
        # is the cached value from the last verified set_write_protected() call (see there for
        # why re-reading the status register on every get isn't needed).
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=89)
            return False
        return self._is_write_protected()

    async def get_size(self) -> int:
        return self._max_size

    async def get_values(self, buf: bytearray | memoryview, addr_start: int = 0) -> bool:
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=90)
            return False
        if not self.asy_lock.locked():  # from Lockable class
            # WP8: an internal-contract violation (a caller failing to hold the lock the Lockable
            # base class requires), not a hardware fault - a real code defect if it ever fires, so
            # errno rather than wrnno, unlike the benign, expected refusals above/below.
            await self.pr.err_s("get_values: FRAM access not locked!", errno=99)
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            await self.pr.err_s("get_values: Invalid FRAM address range!", errno=91)
            return False
        await self._bus_lock.acquire()
        try:
            self._read_address(addr_start, buf)
        finally:
            self._bus_lock.release()
        await asyncio.sleep(0)  # the per-command yield, outside the CS window and outside the lock
        return True

    async def set_values(self, buf: bytes | bytearray | memoryview, addr_start: int) -> bool:
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=92)
            return False
        if not self.asy_lock.locked():  # from Lockable class
            # WP8: same internal-contract violation as get_values() above, own errno per the
            # "grouped by the raising method" convention (SPECIFICATION.md C.7.1) - matches how the
            # sibling "not initialized" check is already numbered separately per method here.
            await self.pr.err_s("set_values: FRAM access not locked!", errno=100)
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            await self.pr.err_s("set_values: Invalid FRAM address range!", errno=93)
            return False
        await self._bus_lock.acquire()
        try:
            status = self._write(addr_start, buf)
        finally:
            self._bus_lock.release()
        await asyncio.sleep(0)  # the per-command yield, outside the CS window and outside the lock
        if status & _W_PROTECTED:
            await self.pr.wrn_s("FRAM currently write protected.", wrnno=84)
            return False
        if status & _W_WEL_NOT_SET:
            await self.pr.wrn_s("FRAM write enable latch did not set, aborting write.", wrnno=82)
            return False
        if status & _W_WEL_STUCK:
            await self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=81)
        return True

    async def set_write_protected(self, *, value: bool) -> bool:
        # Always protects the entire array (BP0+BP1) - per-block ranges are unused.
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=94)
            return False
        await self._bus_lock.acquire()
        try:
            status = self._set_write_protected(value=value)
        finally:
            self._bus_lock.release()
        await asyncio.sleep(0)  # the per-command yield, outside the CS window and outside the lock
        if status & _W_WEL_NOT_SET:
            await self.pr.wrn_s("FRAM write enable latch did not set, write protection not changed.", wrnno=83)
            return False
        if status & _W_WEL_STUCK:
            await self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=81)
        if status & _W_WP_MISMATCH:
            await self.pr.err_s("FRAM write protection readback mismatch, not applied!", errno=95)
            return False
        self.pr.evt("FRAM Write Protection set to", value)
        return True

    async def setup(self) -> None:
        await self._spidev.setup()
        await self._bus_lock.acquire()
        try:
            present = self._check_device_id()
            if present:
                # WPEN/BP0/BP1 are nonvolatile (datasheet) - re-sync _wp from hardware, not the ctor's wp=.
                self._wp = (self._read_status() & _SR_WP_MASK) == _SR_WP_SET
        finally:
            self._bus_lock.release()
        await asyncio.sleep(0)
        if not present:
            raise OSError("FRAM SPI device not found.")
        if self._wp_pin is not None:
            self._wp_pin.init(self._wp_pin.OUT)
            self._wp_pin.value(not self._wp)  # WP is active-low (datasheet)
        self.initialized = True
        self.pr.one("SPI FRAM Driver Setup complete")

    async def verify_present(self) -> bool:
        # Re-probe entry point (cheaper than a full setup()); reverts to initialized=False on
        # failure. Wait is bounded, not a bare `async with self:`, since asyncio.Lock isn't
        # reentrant and a caller nesting this inside its own `async with fram:` would else hang.
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=96)
            return False
        try:
            await asyncio.wait_for(self.asy_lock.acquire(), _VERIFY_PRESENT_LOCK_TIMEOUT_S)
        except asyncio.TimeoutError:
            await self.pr.err_s("FRAM verify_present: lock busy, giving up.", errno=97)
            return False
        try:
            id_error: ValueError | None = None
            await self._bus_lock.acquire()
            try:
                present = self._check_device_id()
            except ValueError as e:
                id_error = e
                present = False
            finally:
                self._bus_lock.release()
            await asyncio.sleep(0)
            if id_error is not None:
                # Provably unreachable (self._max_size is fixed post-construction, and reaching here
                # already required a prior successful setup() with that same size) - kept per Part
                # E.5.1's documented precedent for this exact class of defensive branch, not chased.
                await self.pr.err_s("FRAM verify_present: device ID check failed.", id_error, errno=98)
            if not present:
                self.initialized = False
        finally:
            self.asy_lock.release()
        return present
