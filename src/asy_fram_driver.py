"""Async SPI driver for one Fujitsu MB85RS64V FRAM chip (Adafruit's 8KB SPI FRAM breakout):
raw byte-addressed get_values()/set_values() plus write protection. Source: Fujitsu MB85RS64V
datasheet (DS501-00015), cross-checked against Adafruit's own Adafruit_FRAM_SPI reference driver
for the same chip. The chip pulls its own CS pin up internally (~50k ohm), so a disconnected CS
wire reads deselected on real hardware, not floating-asserted - one bus disturbance this file
never needs to defend against itself.

Data-integrity recovery (CRC, dual-copy redundancy) lives one layer up in asy_fram_manager.py, not
here - raw RP2040 SPI write()/readinto() genuinely cannot report a transfer fault (see
asy_spi_driver.py), so this file can only ever detect faults it can observe by other means:
mismatched device identification (setup()/verify_present()) and a write-enable latch that didn't
actually set/clear as commanded (_write()). Both self-heal back to a safe, well-defined state -
uninitialized=True (every other method already refuses cleanly) or a failed write reported as
False - without raising, so a caller can retry via a fresh setup() the same way every sensor
driver's task-death-and-respawn already works, without this file needing to know about that
policy itself.

Contract: every method returns a well-defined value (bool/None) and never raises, except setup()
- which deliberately raises OSError if device identification fails, mirroring how an I2C driver's
setup() naturally raises OSError on a NAK; SPI has no such signal, so this is the deliberate
substitute - and the raw SPI transaction calls themselves, which per asy_spi_driver.py's own
contract cannot raise on this port.
"""

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
        if self._wp_pin is not None:
            self._wp_pin.init(self._wp_pin.OUT)
            # WP is active-low (datasheet "WRITING PROTECT" table): WP=0 is what additionally
            # locks the status register itself while WPEN=1, matching this class's own
            # protect=True intent - so the pin is driven to the logical inverse of _wp throughout.
            self._wp_pin.value(not self._wp)
        self.uninitialized = False
        self.pr.one("SPI FRAM Driver Setup complete")

    async def verify_present(self) -> bool:
        # Re-probe entry point for a caller (e.g. a future health-check/retry policy) that
        # suspects a bus disturbance: cheaper than a full setup() (skips wp_pin re-init) and, on
        # failure, reverts to uninitialized=True so every other method safely refuses until a
        # fresh setup() succeeds - the same self-healing state setup()'s own OSError already
        # relies on. Must not be called before the first setup() (SPIDevice itself isn't ready).
        async with self:
            present = await self._check_device_id()
            if not present:
                self.uninitialized = True
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
        # Shared WREN-and-verify preamble: WRITE and WRSR both require WEL set first (datasheet:
        # WEL "indicates if FRAM array and status register are writable"). Verifying via RDSR
        # instead of trusting WREN blindly catches a corrupted/disturbed WREN transfer, which the
        # chip would otherwise silently ignore the following WRITE/WRSR for.
        await self._send_opcode(_SPI_OPCODE_WREN)
        return await self._wel_is_set()

    async def _disable_write(self) -> None:
        # Shared WRDI-and-verify epilogue for WRITE and WRSR. WEL already auto-clears at the CS
        # rising edge after either completes (datasheet), so this is defense-in-depth against
        # that auto-clear mechanism itself glitching, not the only thing keeping WEL in check -
        # hence one cheap, idempotent retry before just warning rather than failing the caller's
        # already-completed operation over leftover housekeeping.
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
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WRSR, target]))
        # Read back rather than trusting the write blindly - the one WRSR transaction is the only
        # way this chip's write-protect state can actually change, so this is what catches it if
        # that specific transfer got corrupted by a bus disturbance.
        ok = (await self._read_status() & _SR_WP_MASK) == target
        await self._disable_write()
        if not ok:
            self.pr.err("FRAM write protection readback mismatch, not applied!")
            return False
        self._wp = value
        if self._wp_pin is not None:
            self._wp_pin.value(not value)  # WP active-low, see setup()
        self.pr.evt("FRAM Write Protection set to", value)
        return True

    def _setup_addr_buffer(self, addr: int, opcode: int) -> bytearray:
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
