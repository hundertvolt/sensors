import asyncio
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

class FRAM_SPI():
    """SPI class for FRAM.

    :param ~busio.SPI spi_bus: The SPI bus the FRAM is connected to.
    :param ~digitalio.DigitalInOut spi_cs: The SPI CS pin.
    :param bool write_protect: Turns on/off initial write protection.
        Default is ``False``.
    :param wp_pin: (Optional) Physical pin connected to the ``WP`` breakout pin.
        Must be a ``digitalio.DigitalInOut`` object.
    :param int baudrate: SPI baudrate to use. Default is ``1000000``.
    :param int max_size: Size of FRAM in Bytes. Default is ``8192``.
    """

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(self, spi_bus: SPI, spi_cs: int, wp: bool=False, wp_pin: Optional[int]=None, max_size: int=0x2000, debug: bool=False):
        self.async_lock = asyncio.Lock()
        self._spidev = SPIDevice(spi_bus, spi_cs)
        self._max_size = max_size
        self._wp = wp  # write protect
        self._wp_pin = None if wp_pin is None else Pin(wp_pin)
        self.debug = debug
        
    async def setup(self):
        await self._spidev.setup()
        read_buffer = bytearray(4)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_RDID]))
            await spidev.readinto(read_buffer)
        prod_id = (read_buffer[3] << 8) + (read_buffer[2])
        if (read_buffer[0] != _SPI_MANF_ID) and (prod_id != _SPI_PROD_ID):
            raise OSError("FRAM SPI device not found.")
        if not self._wp_pin is None:
            self._wp_pin.init(_wp_pin.OUT)
            self._wp_pin.value(self._wp)
        
    async def get_write_protected(self) -> bool:
        """The status of write protection. Default value on initialization is
        ``False``.

        When a ``WP`` pin is supplied during initialization, or using
        ``write_protect_pin``, the status is tied to that pin and enables
        hardware-level protection.

        When no ``WP`` pin is supplied, protection is only at the software
        level in this library.
        """
        return self._wp if self._wp_pin is None else self._wp_pin.value()

    async def get_size(self) -> int:
        return self._max_size

    async def get_values(self, addr_start: int, addr_end: int) -> bytearray:
        if not self.async_lock.locked():
            if self.debug: print("FRAM access not locked!")
            return None
        if addr_start is None: addr_start = 0
        if addr_end is None: addr_end = self._max_size - 1
        if (addr_start > addr_end) or (addr_start < 0) or (addr_end >= self._max_size):
            if self.debug: print("get_values: Invalid FRAM address range - start =", addr_start, " end =", addr_end)
            return None
        buffer = bytearray(addr_end - addr_start + 1)
        read_buffer = await self._read_address(addr_start, buffer)
        return read_buffer

    async def set_values(self, addr_start: int, values: bytearray):
        if not self.async_lock.locked():
            if self.debug: print("FRAM access not locked!")
            return False
        if not isinstance(values, bytearray):
            raise ValueError("Data must be bytearray.")
        addr_end = addr_start + len(values) - 1
        if (addr_start < 0) or (addr_end >= self._max_size):
            if self.debug: print("set_values: Invalid FRAM address range - start =", addr_start, " end =", addr_end)
            return False
        return await self._write(addr_start, values)
    
    async def __aenter__(self):
        await self.async_lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            self.async_lock.release()
        except RuntimeError:   # in case it's already released somehow
            pass
        return False
    
    async def _read_address(self, address: int, read_buffer: bytearray) -> bytearray:
        write_buffer = self.setup_addr_buffer(address, _SPI_OPCODE_READ)
        async with self._spidev as spidev:
            await spidev.write(write_buffer)
            await spidev.readinto(read_buffer)
        return read_buffer

    async def _write(self, start_address: int, data: bytearray) -> None:
        wp = await self.get_write_protected()
        if wp:
            if self.debug: print("FRAM currently write protected.")
            return False
        buffer = bytearray(4)
        data_length = len(data)
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WREN]))
        async with self._spidev as spidev:
            buffer = self.setup_addr_buffer(start_address, _SPI_OPCODE_WRITE)
            await spidev.write(buffer)
            for i in range(0, data_length):
                await spidev.write(bytearray([data[i]]))
        async with self._spidev as spidev:
            await spidev.write(bytearray([_SPI_OPCODE_WRDI]))
        return True

    async def set_write_protected(self, value: bool) -> None:
        # While it is possible to protect block ranges on the SPI chip,
        # it seems superfluous to do so. So, block protection always protects
        # the entire memory (BP0 and BP1).
        if not isinstance(value, bool):
            raise ValueError("Write protected value must be 'True' or 'False'.")
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

    def setup_addr_buffer(self, addr, opcode):
        if self._max_size > 0xFFFF:  # > 16bit address
            buffer = bytearray(4)
            buffer[1] = (addr >> 16) & 0xFF
            buffer[2] = (addr >> 8) & 0xFF
            buffer[3] = addr & 0xFF
        else:                        # <= 16bit address
            buffer = bytearray(3)
            buffer[1] = (addr >> 8) & 0xFF
            buffer[2] = addr & 0xFF
        buffer[0] = opcode
        return buffer
        