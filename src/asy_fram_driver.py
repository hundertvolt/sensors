# SPDX-FileCopyrightText: 2018 Michael Schroeder for Adafruit Industries (original adafruit_fram,
# CircuitPython) - restructured/rewritten for asyncio + MicroPython, see THIRD_PARTY_LICENSES.md.
# SPDX-License-Identifier: MIT

"""Async SPI driver for one Fujitsu FRAM chip (MB85RS64V 8KB or MB85RS2MTA 256KB, the part max_size names, checked by RDID against _KNOWN_PRODUCT_IDS): raw byte-addressed get_values()/set_values() plus write protection.
Opcode/register-constant naming and the write-enable/write/write-disable method shape follow Adafruit's Adafruit_CircuitPython_FRAM; RDID checking and the two-part table are this project's own addition, verified against the Fujitsu MB85RS64V (DS501-00015) and MB85RS2MTA (DS501-00032) datasheets.
"""
# CRC/dual-copy recovery lives one layer up in asy_fram_manager.py. This file detects a device-ID mismatch, a write-enable
# latch that did not set (retried once) or clear, a partly protected status register, an unavailable bus and
# a chip lost mid-run, never raising (except __init__()/setup()'s one-time setup errors).

import asyncio

from machine import Pin
from micropython import const

from asy_base_classes import Lockable
from asy_print_log import PrintLogHistory
from asy_spi_driver import SPI, SPIDevice

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal

    from typing_extensions import Self

# RDID response (32 clock cycles after the opcode): manufacturer ID, then the JEDEC continuation-
# code byte, then the two Product ID bytes (1st byte is the more significant one) - all four are
# fixed values for this specific chip, confirmed against the datasheet.
_SPI_MANF_ID = const(0x04)  # Fujitsu
_SPI_CONT_CODE = const(0x7F)  # JEDEC continuation-code byte, fixed for Fujitsu's bank

# Product ID (RDID's 3rd+4th bytes) is chip-specific, unlike manufacturer ID/continuation code above
# (shared project-wide, confirmed against both datasheets below) - keyed by max_size: setup() checks
# that the wired chip is the part max_size implies; it does not detect the part.
_KNOWN_PRODUCT_IDS: dict[int, int] = {
    0x2000: 0x0302,  # MB85RS64V, 64Kbit/8KB - datasheets/fram/MB85RS64V-DS501-00015-4v0-E.pdf p.10
    0x40000: 0x4803,  # MB85RS2MTA, 2Mbit/256KB - datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10
}

_SPI_OPCODE_WRSR = const(0x01)  # Write status register
_SPI_OPCODE_READ = const(0x03)  # Read memory code
_SPI_OPCODE_WRITE = const(0x02)  # Write memory code

# WREN 0x06, WRDI 0x04, RDSR 0x05, RDID 0x9F (datasheet p.6), as module-level bytes rather than a
# bytearray built on every call - each of those lands in the 32-96 byte size class the heap-layout
# model cares about (HEAP_FRAGMENTATION_MEASUREMENTS.md section M1).
_CMD_WREN = const(b"\x06")
_CMD_WRDI = const(b"\x04")
_CMD_RDSR = const(b"\x05")
_CMD_RDID = const(b"\x9f")

# Status register bits (datasheet p.6): bit7 WPEN, bits6-4 unused, bit3 BP1, bit2 BP0, bit1 WEL, bit0
# fixed 0. This driver only ever writes BP0+BP1 together (the whole array); a partial value is foreign.
_SR_WEL = const(0x02)
_SR_FIXED_ZERO = const(0x01)  # bit 0 reads 0 on a live chip of either part (both datasheets p.6)
_SR_WP_MASK = const(0x8C)  # WPEN | BP1 | BP0
_SR_WP_SET = const(0x8C)
_SR_WP_CLEAR = const(0x00)
_SR_BP_MASK = const(0x0C)  # BP1 | BP0: any set bit protects part or all of the array

# Address-buffer geometry: one opcode byte plus the chip's own address width. A chip larger than
# a 16-bit address space needs three address bytes rather than two.
_ADDR_16BIT_MAX = const(0xFFFF)
_ADDR_BUF_24BIT = const(4)
_ADDR_BUF_16BIT = const(3)

# Headroom over a real transaction's low-single-digit-ms cost, bounding an accidental lock re-entry
# to a finite wait.
# @tunable fram.verify_lock_timeout_ms = 1000
_VERIFY_PRESENT_LOCK_TIMEOUT_MS = const(1000)
# Identification attempts setup() makes before it gives up, each its own CS cycle.
# @tunable fram.setup_id_attempts = 3
_ID_ATTEMPTS = const(3)
# Consecutive write-latch anomalies after which one RDID probe asks whether the chip is still there.
# @tunable fram.chip_probe_at = 2
_PROBE_AT = const(2)

# Outcomes of the synchronous write bodies below, as a bit set. They decide what happened; the
# coroutine that owns the operation logs it - awaiting a persisted log entry is not something a
# body holding the bus lock may do.
_W_OK = const(0)
_W_PROTECTED = const(1)  # wrnno 28
_W_WEL_NOT_SET = const(2)  # wrnno 26
_W_WEL_STUCK = const(4)  # wrnno 27 - advisory: the operation itself still completed
_W_WP_MISMATCH = const(8)  # errno 45
_W_WEL_RETRIED = const(256)  # console only: a recovered transient

# The guards get_values()/set_values() share, in the same bit set so one status carries whatever the
# synchronous body found; the two reporters below own every message.
_SV_OK = const(0)
_SV_NOT_INIT = const(16)  # errno 18
_SV_NOT_LOCKED = const(32)  # errno 24
_SV_BAD_RANGE = const(64)  # errno 21
_SV_BUS_DOWN = const(128)  # errno 52
_SV_CHIP_LOST = const(512)  # errno 54

# Error-catalog codes this module logs (buildgen/error_catalog.json, SPECIFICATION.md Part C.7.1).
_ERR_NOT_INIT = const(18)
_ERR_LOCK_TIMEOUT = const(19)
_ERR_BAD_ARG = const(21)
_ERR_CONTRACT = const(24)
_ERR_FRAM_WP_MISMATCH = const(45)
_ERR_FRAM_BUS_DOWN = const(52)
_ERR_FRAM_WP_PARTIAL = const(53)
_ERR_FRAM_CHIP_LOST = const(54)
_WRN_FRAM_WEL_NOT_SET = const(26)
_WRN_FRAM_WEL_STUCK = const(27)
_WRN_FRAM_WRITE_PROTECTED = const(28)
_WRN_FRAM_ID_RETRIED = const(29)


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
        # Optional, and no generated code passes it: without it WP is assumed tied high. With WPEN=1 a low WP
        # locks only the status register (MB85RS64V p.11); the array's protection is always BP1/BP0.
        self._wp_pin = None if wp_pin is None else Pin(wp_pin)
        self.initialized = False
        # Pre-allocated scratch buffers, reused under the driver lock and the bus lock, which every path takes (C.8).
        self._id_buf = bytearray(4)
        self._status_buf = bytearray(1)
        self._addr_buf = bytearray(_ADDR_BUF_24BIT) if self._max_size > _ADDR_16BIT_MAX else bytearray(_ADDR_BUF_16BIT)
        self._wrsr_buf = bytearray(2)  # WRSR opcode + target status byte, the one two-byte command
        # The innermost of the three locks, taken once per block operation by __aenter__ below:
        # holding the bus across the whole block is what lets the byte-level path be synchronous.
        # SPIDevice's own async session takes this same lock for any other caller of the bus.
        self._bus_lock = self._spidev.session_lock
        self._anomalies = 0  # consecutive write-latch anomalies, never above _PROBE_AT
        self.lost = asyncio.Event()  # set when the chip stops answering its identification after setup()

    async def __aenter__(self) -> "Self":
        # Driver lock then bus, both for one whole block operation, so the chunk layer's byte-level
        # commands run synchronously under a lock it already holds - a second SPI device then waits
        # ~25 CS rather than ~5 (owner, 2026-09-18; SPECIFICATION.md C.8).
        await super().__aenter__()
        try:
            await self._bus_lock.acquire()  # explicit: this hold spans __aenter__/__aexit__, which async with cannot express
        except BaseException:
            self.session_lock.release()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,  # `object`, not TracebackType: the precise name only exists under TYPE_CHECKING
    ) -> "Literal[False]":
        try:
            self._bus_lock.release()
        except RuntimeError:  # already released somehow - same tolerance Lockable's own exit has
            pass
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    def _is_write_protected(self) -> bool:
        # The value get_write_protected() reports, without its not-initialized guard: every caller has passed it. With a
        # pin, its level is read as the whole state because set_write_protected() always sets BP and the pin together.
        return self._wp if self._wp_pin is None else not bool(self._wp_pin.value())  # WP active-low

    def _set_write_protected(self, *, value: bool) -> int:
        # Always protects the entire array (BP0+BP1) - per-block ranges are unused.
        target = _SR_WP_SET if value else _SR_WP_CLEAR
        en = self._enable_write()
        if en & _W_WEL_NOT_SET:
            return en
        if self._wp_pin is not None:
            self._wp_pin.value(True)  # deassert WP first - WP=0 would else block this WRSR too
        self._wrsr_buf[0] = _SPI_OPCODE_WRSR
        self._wrsr_buf[1] = target
        self._send_command(self._wrsr_buf)
        ok = (self._read_status() & _SR_WP_MASK) == target  # verify the one way this can change
        status = en | (_W_OK if self._disable_write() else _W_WEL_STUCK)
        if not ok:
            if self._wp_pin is not None:
                self._wp_pin.value(not self._wp)  # unchanged - restore the pin to match reality
            return status | _W_WP_MISMATCH
        self._wp = value
        if self._wp_pin is not None:
            self._wp_pin.value(not value)  # WP active-low, see setup()
        return status

    def _check_device_id(self) -> bool:
        expected_prod_id = _KNOWN_PRODUCT_IDS.get(self._max_size)
        if expected_prod_id is None:
            raise ValueError(f"FRAM max_size {self._max_size:#x} has no known product ID to verify against - add it to _KNOWN_PRODUCT_IDS and to asy_fram_manager.py's @limits max_size set")
        self._send_and_read(_CMD_RDID, self._id_buf)
        prod_id = (self._id_buf[2] << 8) + self._id_buf[3]
        return self._id_buf[0] == _SPI_MANF_ID and self._id_buf[1] == _SPI_CONT_CODE and prod_id == expected_prod_id

    def _check_write_anomaly(self, status: int) -> int:
        # A silent chip reads a constant status byte, so every write ends in a latch fault: after _PROBE_AT in a row,
        # or at once when the last RDSR had the fixed-zero bit set (no live chip sends it), one synchronous RDID
        # under the caller's hold. A clean write reads no extra byte: the check is on _status_buf, already read.
        if not status & (_W_WEL_NOT_SET | _W_WEL_STUCK):
            self._anomalies = 0
            return status
        if not self._status_buf[0] & _SR_FIXED_ZERO and self._anomalies < _PROBE_AT - 1:
            self._anomalies += 1
            return status
        self._anomalies = 0
        if not self._check_device_id():
            self.initialized = False
            status |= _SV_CHIP_LOST
        return status

    def _disable_write(self) -> bool:
        # Shared WRDI-and-verify epilogue: the MB85RS64V clears WEL after WRITE/WRSR, the MB85RS2MTA keeps it set
        # (continual programming, p.6), so this WRDI is what clears it on both - one cheap retry, then False, which
        # the caller turns into a warning: a stuck latch doesn't undo the operation.
        self._send_command(_CMD_WRDI)
        if not self._wel_is_set():
            return True
        self._send_command(_CMD_WRDI)
        return not self._wel_is_set()

    def _enable_write(self) -> int:
        # WREN-and-verify preamble for WRITE/WRSR (WEL gates both): RDSR catches a corrupted WREN the chip would
        # otherwise silently ignore the next WRITE/WRSR for. One retry, as _disable_write() retries WRDI; each
        # WREN is its own CS cycle, and the CS rising edge ends any half-received command (datasheet p.6).
        self._send_command(_CMD_WREN)
        if self._wel_is_set():
            return _W_OK
        self._send_command(_CMD_WREN)
        return _W_WEL_RETRIED if self._wel_is_set() else _W_WEL_NOT_SET

    def _read_address(self, address: int, read_buffer: bytearray | memoryview) -> None:
        self._send_and_read(self._setup_addr_buffer(address, _SPI_OPCODE_READ), read_buffer)

    def _read_status(self) -> int:
        self._send_and_read(_CMD_RDSR, self._status_buf)
        return self._status_buf[0]

    async def _report_chip_lost(self) -> None:
        # The one entry per loss, from whichever path found it: `initialized` is already False, so every later
        # call stops at its guard before it could find the loss again.
        await self.pr.err_s("FRAM chip stopped answering its identification - access stopped", errno=_ERR_FRAM_CHIP_LOST)
        self.lost.set()

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

    # The _send_*() helpers are one CS cycle each, on a bus lock the caller already holds, and every
    # single-underscore method is synchronous: the chip is driven by blocking register writes, so a
    # coroutine per CS cycle bought only allocations. Scheduling points live in the public coroutines (SPECIFICATION.md Part C.3.1).
    def _send_command(self, command: bytes | bytearray) -> None:
        # WREN/WRDI are each a complete, standalone one-byte command (datasheet timing diagrams
        # show CS low only for the opcode); WRSR is the one two-byte command that ends here too.
        spidev = self._spidev
        spidev.session_begin()
        try:
            spidev.write_sync(command)
        finally:
            spidev.session_end()

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

    def _wel_is_set(self) -> bool:
        return bool(self._read_status() & _SR_WEL)

    def _write(self, start_address: int, data: bytes | bytearray | memoryview) -> int:
        if self._is_write_protected():
            # Persisted by the caller, like the manager's "communication paused" refusal (W25): a refused-but-expected
            # write against a chip gated on purpose.
            return _W_PROTECTED
        en = self._enable_write()
        if en & _W_WEL_NOT_SET:
            return en
        self._send_and_write(self._setup_addr_buffer(start_address, _SPI_OPCODE_WRITE), data)
        return en | (_W_OK if self._disable_write() else _W_WEL_STUCK)

    async def get_size(self) -> int:
        return self._max_size

    async def get_values(self, buf: bytearray | memoryview, addr_start: int = 0) -> bool:
        status = self.get_values_sync(buf, addr_start)
        await asyncio.sleep(0)  # the per-command yield; CS is deasserted and the bus lock is the caller's
        return await self.report_get_values(status)

    def get_values_sync(self, buf: bytearray | memoryview, addr_start: int = 0) -> int:
        # The byte-level read, on a bus lock the caller already holds (SPI.configure()'s own guard
        # enforces that). Returns _SV_OK, or a status the caller hands to report_get_values() -
        # a body holding the bus must not await, and a persisted log entry is an await.
        if not self.initialized:
            return _SV_NOT_INIT
        if not self.session_lock.locked():  # from Lockable class
            return _SV_NOT_LOCKED
        if not self._spidev.spi.available:  # checked once: the synchronous body below cannot lose the bus
            return _SV_BUS_DOWN
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            return _SV_BAD_RANGE
        self._read_address(addr_start, buf)
        return _SV_OK

    async def get_write_protected(self) -> bool:
        # Without a wp_pin this is the value setup() read from the chip (A.4); with one, the pin's level (see
        # _is_write_protected()).
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        return self._is_write_protected()

    async def set_values(self, buf: bytes | bytearray | memoryview, addr_start: int) -> bool:
        status = self.set_values_sync(buf, addr_start)
        await asyncio.sleep(0)  # the per-command yield; CS is deasserted and the bus lock is the caller's
        return await self.report_set_values(status)

    def set_values_sync(self, buf: bytes | bytearray | memoryview, addr_start: int) -> int:
        # The byte-level write, on a bus lock the caller already holds. Same contract as
        # get_values_sync(): the status goes to report_set_values(), which owns every message.
        if not self.initialized:
            return _SV_NOT_INIT
        if not self.session_lock.locked():  # from Lockable class
            # Same internal-contract violation as get_values_sync() above.
            return _SV_NOT_LOCKED
        if not self._spidev.spi.available:
            return _SV_BUS_DOWN
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            return _SV_BAD_RANGE
        return self._check_write_anomaly(self._write(addr_start, buf))

    async def set_write_protected(self, *, value: bool) -> bool:
        # Always protects the entire array (BP0+BP1). Takes both FRAM locks itself like setup(): never call it
        # inside `async with fram:` (asyncio.Lock is not reentrant).
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        async with self.session_lock, self._bus_lock:
            status = _SV_BUS_DOWN if not self._spidev.spi.available else self._check_write_anomaly(self._set_write_protected(value=value))
        await asyncio.sleep(0)  # the per-command yield, outside the CS window and outside the locks
        if status & _SV_CHIP_LOST:
            await self._report_chip_lost()
            return False
        if status & _SV_BUS_DOWN:
            await self.pr.err_s("SPI bus not initialized", errno=_ERR_FRAM_BUS_DOWN)
            return False
        if status & _W_WEL_NOT_SET:
            await self.pr.wrn_s("FRAM write enable latch did not set, write protection not changed.", wrnno=_WRN_FRAM_WEL_NOT_SET)
            return False
        if status & _W_WEL_RETRIED:
            self.pr.evt("FRAM write enable latch set on the second WREN")
        if status & _W_WP_MISMATCH:  # before the stuck latch: one call persists the fault or the warning, never both
            await self.pr.err_s("FRAM write protection readback mismatch, not applied!", errno=_ERR_FRAM_WP_MISMATCH)
            return False
        if status & _W_WEL_STUCK:
            await self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=_WRN_FRAM_WEL_STUCK)
        self.pr.evt("FRAM Write Protection set to", value)
        return True

    async def report_get_values(self, status: int) -> bool:
        # get_values()' own numbers and messages, in the one place that has them, whichever path
        # decided the status. Returns what get_values() returns.
        if status & _SV_NOT_INIT:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
        elif status & _SV_NOT_LOCKED:
            # An internal-contract violation (a caller not holding the lock Lockable requires), not a hardware
            # fault - a real code defect if it ever fires, so an errno, unlike the expected refusals elsewhere.
            await self.pr.err_s("get_values: FRAM access not locked!", errno=_ERR_CONTRACT)
        elif status & _SV_BUS_DOWN:
            await self.pr.err_s("SPI bus not initialized", errno=_ERR_FRAM_BUS_DOWN)
        elif status & _SV_BAD_RANGE:
            await self.pr.err_s("get_values: Invalid FRAM address range!", errno=_ERR_BAD_ARG)
        else:
            return True
        return False

    async def report_set_values(self, status: int) -> bool:
        # set_values()' own numbers and messages. A stuck write-enable latch is the one status that
        # warns and still reports success: the payload landed, only the housekeeping is stuck.
        if status & _SV_CHIP_LOST:
            await self._report_chip_lost()
            return False
        if status & _SV_NOT_INIT:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        if status & _SV_NOT_LOCKED:
            await self.pr.err_s("set_values: FRAM access not locked!", errno=_ERR_CONTRACT)
            return False
        if status & _SV_BUS_DOWN:
            await self.pr.err_s("SPI bus not initialized", errno=_ERR_FRAM_BUS_DOWN)
            return False
        if status & _SV_BAD_RANGE:
            await self.pr.err_s("set_values: Invalid FRAM address range!", errno=_ERR_BAD_ARG)
            return False
        if status & _W_PROTECTED:
            # Persisted: a refused-but-expected write against a chip gated on purpose, like the manager's paused
            # refusal (W25), not a hardware fault.
            await self.pr.wrn_s("FRAM currently write protected.", wrnno=_WRN_FRAM_WRITE_PROTECTED)
            return False
        if status & _W_WEL_NOT_SET:
            await self.pr.wrn_s("FRAM write enable latch did not set, aborting write.", wrnno=_WRN_FRAM_WEL_NOT_SET)
            return False
        if status & _W_WEL_RETRIED:
            self.pr.evt("FRAM write enable latch set on the second WREN")  # console only: a recovered transient
        if status & _W_WEL_STUCK:
            await self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=_WRN_FRAM_WEL_STUCK)
        return True

    async def setup(self) -> bool:
        # Takes both FRAM locks, like set_write_protected(); raises only for a chip that never identifies.
        await self._spidev.setup()
        if not self._spidev.spi.available:
            raise OSError("SPI bus not initialized")
        attempt = 0
        present = False
        wp_bits = _SR_WP_CLEAR
        async with self.session_lock, self._bus_lock:
            while not present and attempt < _ID_ATTEMPTS:
                attempt += 1
                present = self._check_device_id()  # each attempt its own CS cycle, which resets the chip's command state
            if present:
                # WPEN/BP0/BP1 are nonvolatile: re-sync from the chip, not the constructor's wp=
                wp_bits = self._read_status() & _SR_WP_MASK
                self._wp = bool(wp_bits & _SR_BP_MASK)
        await asyncio.sleep(0)
        if not present:
            raise OSError("FRAM SPI device not found")
        if attempt > 1:
            await self.pr.wrn_s("FRAM answered its identification only on attempt", attempt, wrnno=_WRN_FRAM_ID_RETRIED)
        if wp_bits not in (_SR_WP_SET, _SR_WP_CLEAR):
            await self.pr.err_s(
                "FRAM status register partly write-protected:", hex(wp_bits), "- writes refused until set_write_protected() rewrites it",
                errno=_ERR_FRAM_WP_PARTIAL,
            )
        if self._wp_pin is not None:
            self._wp_pin.init(self._wp_pin.OUT, value=not self._wp)  # level before direction: no glitch on WP
        self.initialized = True
        self._anomalies = 0
        self.lost.clear()
        self.pr.one("SPI FRAM Driver Setup complete")
        return True

    async def verify_present(self) -> bool:
        # Re-probe entry point (cheaper than a full setup()); reverts to initialized=False on
        # failure. Wait is bounded, not a bare `async with self:`, since asyncio.Lock isn't
        # reentrant and a caller nesting this inside its own `async with fram:` would else hang.
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        try:
            await asyncio.wait_for_ms(self.session_lock.acquire(), _VERIFY_PRESENT_LOCK_TIMEOUT_MS)  # explicit: a bounded wait on the acquire
        except asyncio.TimeoutError:
            await self.pr.err_s("FRAM verify_present: lock busy, giving up.", errno=_ERR_LOCK_TIMEOUT)
            return False
        try:
            if not self._spidev.spi.available:
                await self.pr.err_s("SPI bus not initialized", errno=_ERR_FRAM_BUS_DOWN)
                return False
            async with self._bus_lock:
                present = self._check_device_id()
            await asyncio.sleep(0)
            if not present:
                self.initialized = False
        finally:
            self.session_lock.release()
        if not present:
            await self._report_chip_lost()
        return present
