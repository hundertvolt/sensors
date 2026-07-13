from print_log import PrintLog
from base_classes import Lockable
from micropython import const
from asy_spi_driver import SPI, SPIDevice
from machine import Pin

_SPI_MANF_ID = const(0x04)
_SPI_PROD_ID = const(0x302)

_SPI_OPCODE_WREN = const(0x6)  # Set write enable latch
_SPI_OPCODE_WRDI = const(0x4)  # Reset write enable latch
_SPI_OPCODE_RDSR = const(0x5)  # Read status register
_SPI_OPCODE_WRSR = const(0x1)  # Write status register
_SPI_OPCODE_READ = const(0x3)  # Read memory code
_SPI_OPCODE_WRITE = const(0x2)  # Write memory code
_SPI_OPCODE_RDID = const(0x9F)  # Read device ID


class FRAM_SPI(Lockable):
    """SPI class for FRAM.

    :param ~busio.SPI spi_bus: The SPI bus the FRAM is connected to.
    :param ~digitalio.DigitalInOut spi_cs: The SPI CS pin.
    :param bool wp: Turns on/off initial write protection.
        Default is ``False``.
    :param wp_pin: (Optional) Physical pin connected to the ``WP`` breakout pin.
        Must be a ``digitalio.DigitalInOut`` object.
    :param int max_size: Size of FRAM in Bytes. Default is ``8192``.
    """

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
        read_buffer = bytearray(4)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_RDID]))
            await spidev.readinto(read_buffer)
        prod_id = (read_buffer[3] << 8) + (read_buffer[2])
        if (read_buffer[0] != _SPI_MANF_ID) and (prod_id != _SPI_PROD_ID):
            raise OSError("FRAM SPI device not found.")
        if self._wp_pin is not None:
            self._wp_pin.init(self._wp_pin.OUT)
            self._wp_pin.value(self._wp)
        self.uninitialized = False
        self.pr.one("SPI FRAM Driver Setup complete")

    async def get_write_protected(self) -> bool:
        """The status of write protection. Default value on initialization is
        ``False``.

        When a ``WP`` pin is supplied during initialization, or using
        ``write_protect_pin``, the status is tied to that pin and enables
        hardware-level protection.

        When no ``WP`` pin is supplied, protection is only at the software
        level in this library.
        """
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return False
        return self._wp if self._wp_pin is None else bool(self._wp_pin.value())

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
            await spidev.write(self.setup_addr_buffer(address, _SPI_OPCODE_READ))
            await spidev.readinto(read_buffer)

    async def _write(self, start_address: int, data: bytes | bytearray | memoryview) -> bool:
        wp = await self.get_write_protected()
        if wp:
            self.pr.wrn("FRAM currently write protected.")
            return False
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WREN]))
        async with self._spidev as spidev:
            await spidev.write(self.setup_addr_buffer(start_address, _SPI_OPCODE_WRITE))
            await spidev.write(data)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WRDI]))
        return True

    async def set_write_protected(self, value: bool) -> None:
        # While it is possible to protect block ranges on the SPI chip,
        # it seems superfluous to do so. So, block protection always protects
        # the entire memory (BP0 and BP1).
        if self.uninitialized:
            self.pr.err("FRAM not initialized, run setup first!")
            return
        self._wp = value
        write_buffer = bytearray(2)
        write_buffer[0] = _SPI_OPCODE_WRSR
        if value:
            write_buffer[1] = 0x8C  # set WPEN, BP0, and BP1
        else:
            write_buffer[1] = 0x00  # clear WPEN, BP0, and BP1
        async with self._spidev as spidev:
            await spidev.write(write_buffer)
        if self._wp_pin is not None:
            self._wp_pin.value(value)
        self.pr.evt("FRAM Write Protection set to", value)

    def setup_addr_buffer(self, addr: int, opcode: int) -> bytearray:
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
