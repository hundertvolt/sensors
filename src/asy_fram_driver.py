# SPDX-FileCopyrightText: 2018 Michael Schroeder for Adafruit Industries
# SPDX-License-Identifier: MIT
# From adafruit_fram (CircuitPython), restructured for asyncio + MicroPython - see THIRD_PARTY_LICENSES.md.

"""SPI driver for one Fujitsu FRAM chip (MB85RS64V 8KB or MB85RS2MTA 256KB, the part max_size names, checked by
RDID against _KNOWN_PRODUCT_IDS): raw byte-addressed get_values()/set_values() plus write protection.

Opcode/register-constant naming and the write-enable/write/write-disable method shape follow Adafruit's
Adafruit_CircuitPython_FRAM; RDID checking and the two-part table are this project's own addition, verified against the
Fujitsu MB85RS64V (DS501-00015) and MB85RS2MTA (DS501-00032) datasheets.
"""
# CRC/dual-copy recovery lives one layer up in asy_fram_manager.py. This file only detects a
# device-ID mismatch, a write-enable latch that didn't set/clear and a stale write-protect
# assumption, self-healing without raising (except __init__()/setup()'s one-time setup errors).

from machine import Pin
from micropython import const

from asy_print_log import PrintLogHistory
from asy_spi_driver import SPI, SPIDevice

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable


def _unbound(_arg: object) -> None:
    # The wiring before the first begin(): a command outside an operation is a programming error.
    raise RuntimeError("FRAM command outside an operation - call begin() first")


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

# Identification attempts setup() makes before it gives up, each its own CS cycle.
# @tunable fram.setup_id_attempts = 3
_ID_ATTEMPTS = const(3)

# Outcomes of the write bodies below, as a bit set: they decide what happened, and the public entry point logs it.
_W_OK = const(0)
_W_PROTECTED = const(1)  # wrnno 28
_W_WEL_NOT_SET = const(2)  # wrnno 26
_W_WEL_STUCK = const(4)  # wrnno 27 - advisory: the operation itself still completed
_W_WP_MISMATCH = const(8)  # errno 45
_W_WEL_RETRIED = const(256)  # console only: a recovered transient

# Error-catalog codes this module logs (buildgen/error_catalog.json, SPECIFICATION.md Part C.7.1).
_ERR_NOT_INIT = const(18)
_ERR_BAD_ARG = const(21)
_ERR_UNEXPECTED = const(23)
_ERR_FRAM_WP_MISMATCH = const(45)
_WRN_FRAM_WEL_NOT_SET = const(26)
_WRN_FRAM_WEL_STUCK = const(27)
_WRN_FRAM_WRITE_PROTECTED = const(28)
_WRN_FRAM_ID_RETRIED = const(29)


class FRAM_SPI:
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
        self.pr = logger
        self._spidev = SPIDevice(spi_bus, spi_cs, baudrate=8_000_000)  # 24 MHz (rp2's ceiling) / 3, exact (owner, 2026-11-02)
        self._max_size = max_size
        self._wp = wp  # write protect
        self._wp_pin = None if wp_pin is None else Pin(wp_pin)
        self.initialized = False
        # Pre-allocated scratch buffers: every command runs whole, never suspending, so one set serves every caller (C.8).
        self._id_buf = bytearray(4)
        self._status_buf = bytearray(1)
        self._addr_buf = bytearray(_ADDR_BUF_24BIT) if self._max_size > _ADDR_16BIT_MAX else bytearray(_ADDR_BUF_16BIT)
        self._wrsr_buf = bytearray(2)  # WRSR opcode + target status byte, the one two-byte command
        # The wiring begin() binds for one operation's commands: CS value() and its active level, the bus's write/readinto.
        self._cs: Callable[[bool], object] = _unbound
        self._cs_on = False
        self._bus_write: Callable[[bytes | bytearray | memoryview], None] = _unbound
        self._bus_readinto: Callable[[bytearray | memoryview], None] = _unbound

    def _is_write_protected(self) -> bool:
        # The value get_write_protected() reports, without its not-initialized guard: every caller
        # of this one has already passed that guard at the public entry point.
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
        ok = (self._send_and_read(_CMD_RDSR, self._status_buf)[0] & _SR_WP_MASK) == target  # verify the one way this can change
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

    def _disable_write(self) -> bool:
        # Shared WRDI-and-verify epilogue: the MB85RS64V clears WEL after WRITE/WRSR, the MB85RS2MTA keeps it set
        # (continual programming, p.6), so this WRDI is what clears it on both - one cheap retry, then False, which
        # the caller turns into a warning: a stuck latch doesn't undo the operation.
        self._send_command(_CMD_WRDI)
        if not self._send_and_read(_CMD_RDSR, self._status_buf)[0] & _SR_WEL:
            return True
        self._send_command(_CMD_WRDI)
        return not self._send_and_read(_CMD_RDSR, self._status_buf)[0] & _SR_WEL

    def _enable_write(self) -> int:
        # WREN-and-verify preamble for WRITE/WRSR (WEL gates both): RDSR catches a corrupted WREN the chip would
        # otherwise silently ignore the next WRITE/WRSR for. One retry, as _disable_write() retries WRDI; each
        # WREN is its own CS cycle, and the CS rising edge ends any half-received command (datasheet p.6).
        self._send_command(_CMD_WREN)
        if self._send_and_read(_CMD_RDSR, self._status_buf)[0] & _SR_WEL:
            return _W_OK
        self._send_command(_CMD_WREN)
        return _W_WEL_RETRIED if self._send_and_read(_CMD_RDSR, self._status_buf)[0] & _SR_WEL else _W_WEL_NOT_SET

    def _send_and_read(self, command: bytes | bytearray, read_buffer: bytearray | memoryview) -> bytearray | memoryview:
        # Answers read_buffer, so a status read indexes it in place: no helper level under the deepest FRAM chain (F.1).
        cs, on = self._cs, self._cs_on
        cs(on)
        try:
            self._bus_write(command)
            self._bus_readinto(read_buffer)
        finally:
            cs(not on)
        return read_buffer

    def _send_and_write(self, command: bytes | bytearray, data: bytes | bytearray | memoryview) -> None:
        cs, on = self._cs, self._cs_on
        cs(on)
        try:
            self._bus_write(command)
            self._bus_write(data)
        finally:
            cs(not on)

    # The _send_*() helpers are one synchronous CS cycle each, on the wiring begin() bound: the chip is driven by blocking
    # register writes, and an operation never suspends, so nothing can come between its commands (Part C.3.1, C.8).
    # No settle wait at a CS edge: tCSU/tCSH 10 ns, tD 40/60 ns (MB85RS2MTA p.15, MB85RS64V p.14) pass within one call.
    def _send_command(self, command: bytes | bytearray) -> None:
        # WREN/WRDI are each a complete, standalone one-byte command (datasheet timing diagrams
        # show CS low only for the opcode); WRSR is the one two-byte command that ends here too.
        cs, on = self._cs, self._cs_on
        cs(on)
        try:
            self._bus_write(command)
        finally:
            cs(not on)

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

    def get_size(self) -> int:
        return self._max_size

    def get_values(self, buf: bytearray | memoryview, addr_start: int = 0) -> bool:
        if not self.initialized:
            self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            self.pr.err_s("get_values: Invalid FRAM address range!", errno=_ERR_BAD_ARG)
            return False
        self._send_and_read(self._setup_addr_buffer(addr_start, _SPI_OPCODE_READ), buf)
        return True

    def get_write_protected(self) -> bool:
        # Without a wp_pin this is the value setup() read from the chip (A.4); with one, the pin's level (see
        # _is_write_protected()).
        if not self.initialized:
            self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        return self._is_write_protected()

    def set_values(self, buf: bytes | bytearray | memoryview, addr_start: int) -> bool:
        # A stuck write-enable latch is the one outcome that warns and still reports success: the payload landed, only
        # the housekeeping is stuck.
        if not self.initialized:
            self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            self.pr.err_s("set_values: Invalid FRAM address range!", errno=_ERR_BAD_ARG)
            return False
        status = self._write(addr_start, buf)
        if status & _W_PROTECTED:
            # Persisted: a refused-but-expected write against a chip gated on purpose, like the manager's paused
            # refusal (W25), not a hardware fault.
            self.pr.wrn_s("FRAM currently write protected.", wrnno=_WRN_FRAM_WRITE_PROTECTED)
            return False
        if status & _W_WEL_NOT_SET:
            self.pr.wrn_s("FRAM write enable latch did not set, aborting write.", wrnno=_WRN_FRAM_WEL_NOT_SET)
            return False
        if status & _W_WEL_RETRIED:
            self.pr.evt("FRAM write enable latch set on the second WREN")  # console only: a recovered transient
        if status & _W_WEL_STUCK:
            self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=_WRN_FRAM_WEL_STUCK)
        return True

    def set_write_protected(self, *, value: bool) -> bool:
        # Always protects the entire array (BP0+BP1); per-block ranges are unused.
        if not self.initialized:
            self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        self.begin()
        status = self._set_write_protected(value=value)
        if status & _W_WEL_NOT_SET:
            self.pr.wrn_s("FRAM write enable latch did not set, write protection not changed.", wrnno=_WRN_FRAM_WEL_NOT_SET)
            return False
        if status & _W_WEL_RETRIED:
            self.pr.evt("FRAM write enable latch set on the second WREN")
        if status & _W_WP_MISMATCH:  # before the stuck latch: one call persists the fault or the warning, never both
            self.pr.err_s("FRAM write protection readback mismatch, not applied!", errno=_ERR_FRAM_WP_MISMATCH)
            return False
        if status & _W_WEL_STUCK:
            self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=_WRN_FRAM_WEL_STUCK)
        self.pr.evt("FRAM Write Protection set to", value)
        return True

    def begin(self) -> None:
        # One bus session per operation, before its first command (C.8): raises while an async session holds the bus or the
        # bus is down; configures the bus when another device configured it last. get_values()/set_values() run inside one.
        self._cs, self._cs_on, self._bus_write, self._bus_readinto = self._spidev.begin_sync()

    async def setup(self) -> None:
        await self._spidev.setup()
        self.begin()
        attempt = 0
        present = False
        while not present and attempt < _ID_ATTEMPTS:
            attempt += 1
            present = self._check_device_id()  # each attempt its own CS cycle, which resets the chip's command state
        if not present:
            raise OSError("FRAM SPI device not found")
        # WPEN/BP0/BP1 are nonvolatile (datasheet) - re-sync _wp from hardware, not the ctor's wp=.
        self._wp = (self._send_and_read(_CMD_RDSR, self._status_buf)[0] & _SR_WP_MASK) == _SR_WP_SET
        if attempt > 1:
            self.pr.wrn_s("FRAM answered its identification only on attempt", attempt, wrnno=_WRN_FRAM_ID_RETRIED)
        if self._wp_pin is not None:
            self._wp_pin.init(self._wp_pin.OUT, value=not self._wp)  # level before direction: no glitch on WP
        self.initialized = True
        self.pr.one("SPI FRAM Driver Setup complete")

    def verify_present(self) -> bool:
        # A re-probe cheaper than setup(): a chip that no longer identifies leaves the driver uninitialized, every
        # other call refusing until setup() succeeds again.
        if not self.initialized:
            self.pr.err_s("FRAM not initialized, run setup first!", errno=_ERR_NOT_INIT)
            return False
        try:
            self.begin()
        except Exception as e:  # another device's async session holds the bus: refused, as the chunk layer's _begin()
            self.pr.err_s("FRAM bus not available:", e, errno=_ERR_UNEXPECTED)
            return False
        self.initialized = self._check_device_id()
        return self.initialized
