"""Async SPI driver for one Fujitsu MB85RS64V FRAM chip (Adafruit's 8KB SPI FRAM breakout):
raw byte-addressed get_values()/set_values() plus write protection. Source: Fujitsu MB85RS64V
datasheet (DS501-00015), cross-checked against Adafruit's Adafruit_FRAM_SPI reference driver.
CRC/dual-copy data-integrity recovery lives one layer up in asy_fram_manager.py - this file only
detects device-ID mismatch, a write-enable latch that didn't set/clear, and a stale write-protect
assumption, self-healing to a safe state without raising (except __init__()'s/setup()'s one-time
setup errors).
"""

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
_SPI_PROD_ID = const(0x0302)  # 64Kbit density (0x03) + proprietary byte (0x02)

_SPI_OPCODE_WREN = const(0x06)  # Set write enable latch
_SPI_OPCODE_WRDI = const(0x04)  # Reset write enable latch
_SPI_OPCODE_RDSR = const(0x05)  # Read status register
_SPI_OPCODE_WRSR = const(0x01)  # Write status register
_SPI_OPCODE_READ = const(0x03)  # Read memory code
_SPI_OPCODE_WRITE = const(0x02)  # Write memory code
_SPI_OPCODE_RDID = const(0x9F)  # Read device ID

# Status register bits (datasheet): bit7 WPEN, bits6-4 unused, bit3 BP1, bit2 BP0, bit1 WEL, bit0
# fixed 0. Block protection always covers the whole array (BP0+BP1 together), never a sub-range.
_SR_WEL = const(0x02)
_SR_WP_MASK = const(0x8C)  # WPEN | BP1 | BP0
_SR_WP_SET = const(0x8C)
_SR_WP_CLEAR = const(0x00)

# Generous headroom over a real transaction's low-single-digit-ms cost, while still bounding an
# accidental lock-reentry to a finite wait. Not test-monkeypatchable: MicroPython inlines const()
# at every use site regardless of name (verified directly), so the one test needing this waits it out.
_VERIFY_PRESENT_LOCK_TIMEOUT_S = const(1.0)


class FRAM_SPI(Lockable):
    def __init__(
        self,
        spi_bus: SPI,
        spi_cs: int,
        logger: PrintLogHistory,
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
        self._addr_buf = bytearray(4) if self._max_size > 0xFFFF else bytearray(3)

    async def _check_device_id(self) -> bool:
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_RDID]))
            await spidev.readinto(self._id_buf)
        prod_id = (self._id_buf[2] << 8) + self._id_buf[3]
        return self._id_buf[0] == _SPI_MANF_ID and self._id_buf[1] == _SPI_CONT_CODE and prod_id == _SPI_PROD_ID

    async def _read_address(self, address: int, read_buffer: bytearray | memoryview) -> None:
        async with self._spidev as spidev:
            await spidev.write(self._setup_addr_buffer(address, _SPI_OPCODE_READ))
            await spidev.readinto(read_buffer)

    async def _read_status(self) -> int:
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_RDSR]))
            await spidev.readinto(self._status_buf)
        return self._status_buf[0]

    async def _send_opcode(self, opcode: int) -> None:
        # WREN/WRDI are each a complete, standalone one-byte command (datasheet timing diagrams
        # show CS low only for the opcode) - the only two opcodes this driver ever sends alone.
        async with self._spidev as spidev:
            await spidev.write(bytearray([opcode]))

    async def _wel_is_set(self) -> bool:
        return bool(await self._read_status() & _SR_WEL)

    async def _enable_write(self) -> bool:
        # Shared WREN-and-verify preamble for WRITE/WRSR (datasheet: WEL gates both). Verifying
        # via RDSR instead of trusting WREN blindly catches a corrupted WREN transfer, which the
        # chip would otherwise silently ignore the following WRITE/WRSR for.
        await self._send_opcode(_SPI_OPCODE_WREN)
        return await self._wel_is_set()

    async def _disable_write(self) -> None:
        # Shared WRDI-and-verify epilogue: WEL auto-clears after WRITE/WRSR anyway (datasheet), so
        # this is defense-in-depth against that mechanism itself glitching - one cheap retry, then
        # only a warning, since a stuck latch doesn't undo the already-completed operation.
        await self._send_opcode(_SPI_OPCODE_WRDI)
        if await self._wel_is_set():
            await self._send_opcode(_SPI_OPCODE_WRDI)
            if await self._wel_is_set():
                await self.pr.wrn_s("FRAM write enable latch did not clear after WRDI retry.", wrnno=81)

    async def _write(self, start_address: int, data: bytes | bytearray | memoryview) -> bool:
        if await self.get_write_protected():
            self.pr.wrn("FRAM currently write protected.")
            return False
        if not await self._enable_write():
            await self.pr.wrn_s("FRAM write enable latch did not set, aborting write.", wrnno=82)
            return False
        async with self._spidev as spidev:
            await spidev.write(self._setup_addr_buffer(start_address, _SPI_OPCODE_WRITE))
            await spidev.write(data)
        await self._disable_write()
        return True

    def _setup_addr_buffer(self, addr: int, opcode: int) -> bytearray:
        # Buffer width is fixed once in __init__ from max_size, which is trusted, not re-derived
        # from _check_device_id() - see SPECIFICATION.md Part C.3.1's FRAM_SPI bullet.
        buffer = self._addr_buf
        if len(buffer) == 4:  # > 16bit address
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
        return self._wp if self._wp_pin is None else not bool(self._wp_pin.value())  # WP active-low

    async def get_size(self) -> int:
        return self._max_size

    async def get_values(self, buf: bytearray | memoryview, addr_start: int = 0) -> bool:
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=90)
            return False
        if not self.asy_lock.locked():  # from Lockable class
            self.pr.wrn("FRAM access not locked!")
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            await self.pr.err_s("get_values: Invalid FRAM address range!", errno=91)
            return False
        await self._read_address(addr_start, buf)
        return True

    async def set_values(self, buf: bytes | bytearray | memoryview, addr_start: int) -> bool:
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=92)
            return False
        if not self.asy_lock.locked():  # from Lockable class
            self.pr.wrn("FRAM access not locked!")
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            await self.pr.err_s("set_values: Invalid FRAM address range!", errno=93)
            return False
        return await self._write(addr_start, buf)

    async def set_write_protected(self, value: bool) -> bool:
        # Always protects the entire array (BP0+BP1) - per-block ranges are unused.
        if not self.initialized:
            await self.pr.err_s("FRAM not initialized, run setup first!", errno=94)
            return False
        target = _SR_WP_SET if value else _SR_WP_CLEAR
        if not await self._enable_write():
            await self.pr.wrn_s("FRAM write enable latch did not set, write protection not changed.", wrnno=83)
            return False
        if self._wp_pin is not None:
            self._wp_pin.value(True)  # deassert WP first - WP=0 would else block this WRSR too
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WRSR, target]))
        ok = (await self._read_status() & _SR_WP_MASK) == target  # verify the one way this can change
        await self._disable_write()
        if not ok:
            if self._wp_pin is not None:
                self._wp_pin.value(not self._wp)  # unchanged - restore the pin to match reality
            await self.pr.err_s("FRAM write protection readback mismatch, not applied!", errno=95)
            return False
        self._wp = value
        if self._wp_pin is not None:
            self._wp_pin.value(not value)  # WP active-low, see setup()
        self.pr.evt("FRAM Write Protection set to", value)
        return True

    async def setup(self) -> None:
        await self._spidev.setup()
        if not await self._check_device_id():
            raise OSError("FRAM SPI device not found.")
        # WPEN/BP0/BP1 are nonvolatile (datasheet) - re-sync _wp from hardware, not the ctor's wp=.
        self._wp = (await self._read_status() & _SR_WP_MASK) == _SR_WP_SET
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
            present = await self._check_device_id()
            if not present:
                self.initialized = False
        finally:
            self.asy_lock.release()
        return present
