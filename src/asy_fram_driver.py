"""Async SPI driver for one Fujitsu MB85RS64V FRAM chip (Adafruit's 8KB SPI FRAM breakout):
raw byte-addressed get_values()/set_values() plus write protection. Source: Fujitsu MB85RS64V
datasheet (DS501-00015), cross-checked against Adafruit's own Adafruit_FRAM_SPI reference driver.

Data-integrity recovery (CRC, dual-copy redundancy) lives one layer up in asy_fram_manager.py -
raw SPI write()/readinto() can't report a transfer fault, so this file only detects what it can
observe directly: device-ID mismatch, a write-enable latch that didn't set/clear as commanded,
and a stale write-protect assumption. All three self-heal to a safe state (uninitialized=True, or
a failed write/protect-change reported as False) without raising, so a caller can recover via a
fresh setup(), the same task-death-and-respawn pattern every sensor driver already relies on.

Contract: every method returns a well-defined value and never raises, except three deliberately-
allowed paths mirroring asy_spi_driver.py's own carve-outs, never silently caught here so upstream
callers must handle them: __init__()'s ValueError for a bad pin/port (one-time, at-boot
misconfiguration); setup()'s OSError for failed device identification (SPI's substitute for an
I2C NAK); and SPIDevice's "not set up"/deinitialized-bus RuntimeError, only reachable via a
caller-ordering bug or something else deinitializing the shared bus mid-operation. See BACKLOG.md
for the full rationale and history behind each.
"""

import asyncio

from machine import Pin
from micropython import const

from asy_spi_driver import SPI, SPIDevice
from base_classes import Lockable
from print_log import PrintLog

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

# Not const()-wrapped, unlike the datasheet-fixed values above - so a test can monkeypatch this
# to shorten the wait (see verify_present()). Generous headroom over a real transaction's
# low-single-digit-ms cost, while still bounding an accidental lock-reentry to a finite wait.
_VERIFY_PRESENT_LOCK_TIMEOUT_S = 1.0


class FRAM_SPI(Lockable):
    def __init__(
        self,
        spi_bus: SPI,
        spi_cs: int,
        logger: PrintLog,
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
        self.uninitialized = True

    async def setup(self) -> None:
        await self._spidev.setup()
        if not await self._check_device_id():
            raise OSError("FRAM SPI device not found.")
        # WPEN/BP0/BP1 are nonvolatile (datasheet), unlike WEL - re-sync _wp from hardware rather
        # than trusting the constructor's wp=, which is only ever a guess about a prior session.
        self._wp = (await self._read_status() & _SR_WP_MASK) == _SR_WP_SET
        if self._wp_pin is not None:
            self._wp_pin.init(self._wp_pin.OUT)
            # WP is active-low (datasheet "WRITING PROTECT" table): WP=0 additionally locks the
            # status register itself while WPEN=1, matching this class's own protect=True intent.
            self._wp_pin.value(not self._wp)
        self.uninitialized = False
        self.pr.one("SPI FRAM Driver Setup complete")

    async def verify_present(self) -> bool:
        # Re-probe entry point for a caller that suspects a bus disturbance: cheaper than a full
        # setup() (skips wp_pin re-init), and on failure reverts to uninitialized=True so every
        # other method safely refuses until a fresh setup() succeeds. See BACKLOG.md.
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return False
        # asyncio.Lock isn't reentrant - a bare `async with self:` would hang forever if a caller
        # invoked this from inside its own `async with fram:` block. Bounding the wait turns that
        # hang into the same well-defined False every sibling guard already returns. See BACKLOG.md.
        try:
            await asyncio.wait_for(self.asy_lock.acquire(), _VERIFY_PRESENT_LOCK_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.pr.err("FRAM verify_present: lock busy, giving up.")
            return False
        try:
            present = await self._check_device_id()
            if not present:
                self.uninitialized = True
        finally:
            self.asy_lock.release()
        return present

    async def _check_device_id(self) -> bool:
        read_buffer = bytearray(4)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_RDID]))
            await spidev.readinto(read_buffer)
        prod_id = (read_buffer[2] << 8) + read_buffer[3]
        return read_buffer[0] == _SPI_MANF_ID and read_buffer[1] == _SPI_CONT_CODE and prod_id == _SPI_PROD_ID

    async def get_write_protected(self) -> bool:
        # With a wp_pin, protection is tied to that physical pin's own value; without one, this
        # is the cached value from the last verified set_write_protected() call (see there for
        # why re-reading the status register on every get isn't needed).
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return False
        return self._wp if self._wp_pin is None else not bool(self._wp_pin.value())  # WP active-low

    async def get_size(self) -> int:
        return self._max_size

    async def get_values(self, buf: bytearray | memoryview, addr_start: int = 0) -> bool:
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return False
        if not self.asy_lock.locked():  # from Lockable class
            self.pr.wrn("FRAM access not locked!")
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            self.pr.err("get_values: Invalid FRAM address range!")
            return False
        await self._read_address(addr_start, buf)
        return True

    async def set_values(self, buf: bytes | bytearray | memoryview, addr_start: int) -> bool:
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return False
        if not self.asy_lock.locked():  # from Lockable class
            self.pr.wrn("FRAM access not locked!")
            return False
        if (addr_start < 0) or (addr_start + len(buf) > self._max_size):
            self.pr.err("set_values: Invalid FRAM address range!")
            return False
        return await self._write(addr_start, buf)

    async def _read_address(self, address: int, read_buffer: bytearray | memoryview) -> None:
        async with self._spidev as spidev:
            await spidev.write(self._setup_addr_buffer(address, _SPI_OPCODE_READ))
            await spidev.readinto(read_buffer)

    async def _read_status(self) -> int:
        read_buffer = bytearray(1)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_RDSR]))
            await spidev.readinto(read_buffer)
        return read_buffer[0]

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
                self.pr.wrn("FRAM write enable latch did not clear after WRDI retry.")

    async def _write(self, start_address: int, data: bytes | bytearray | memoryview) -> bool:
        if await self.get_write_protected():
            self.pr.wrn("FRAM currently write protected.")
            return False
        if not await self._enable_write():
            self.pr.wrn("FRAM write enable latch did not set, aborting write.")
            return False
        async with self._spidev as spidev:
            await spidev.write(self._setup_addr_buffer(start_address, _SPI_OPCODE_WRITE))
            await spidev.write(data)
        await self._disable_write()
        return True

    async def set_write_protected(self, value: bool) -> bool:
        # While it is possible to protect block ranges on the SPI chip,
        # it seems superfluous to do so. So, block protection always protects
        # the entire memory (BP0 and BP1).
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return False
        target = _SR_WP_SET if value else _SR_WP_CLEAR
        if not await self._enable_write():
            self.pr.wrn("FRAM write enable latch did not set, write protection not changed.")
            return False
        if self._wp_pin is not None:
            # Deassert WP first: per the datasheet's WRITING PROTECT table, WEL=1,WPEN=1,WP=0
            # makes the status register itself unwritable, so a pin left low from an earlier
            # protect=True would otherwise block this very WRSR - including the one clearing it.
            self._wp_pin.value(True)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WRSR, target]))
        # Read back rather than trusting the write blindly - the one WRSR transaction is the only
        # way this chip's write-protect state can actually change, so this is what catches it if
        # that specific transfer got corrupted by a bus disturbance.
        ok = (await self._read_status() & _SR_WP_MASK) == target
        await self._disable_write()
        if not ok:
            if self._wp_pin is not None:
                self._wp_pin.value(not self._wp)  # unchanged - restore the pin to match reality
            self.pr.err("FRAM write protection readback mismatch, not applied!")
            return False
        self._wp = value
        if self._wp_pin is not None:
            self._wp_pin.value(not value)  # WP active-low, see setup()
        self.pr.evt("FRAM Write Protection set to", value)
        return True

    def _setup_addr_buffer(self, addr: int, opcode: int) -> bytearray:
        # max_size is trusted as set up by the caller - this class's RDID check is hardwired to
        # one real 8KB chip (0x0000-0x1FFF); a wrong, too-large max_size here would validate
        # addresses beyond that and let them silently alias on real hardware. See BACKLOG.md.
        if self._max_size > 0xFFFF:  # > 16bit address
            buffer = bytearray(4)
            buffer[1] = (addr >> 16) & 0xFF
            buffer[2] = (addr >> 8) & 0xFF
            buffer[3] = addr & 0xFF
        else:  # <= 16bit address
            buffer = bytearray(3)
            buffer[1] = (addr >> 8) & 0xFF
            buffer[2] = addr & 0xFF
        buffer[0] = opcode
        return buffer
