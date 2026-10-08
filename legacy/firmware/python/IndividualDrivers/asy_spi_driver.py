import asyncio
from machine import SPI as _SPI
from machine import Pin

class SPI:
    def __init__(self, portId, sckPin, mosiPin, misoPin):
        """Initialize the Port"""
        self.init(portId, sckPin, mosiPin, misoPin)
        self.async_lock = asyncio.Lock()

    def init(self, portId, sckPin, mosiPin, misoPin):
        """Initialization"""
        self.deinit()
        self._spi = _SPI(portId,
                         sck=Pin(sckPin),
                         mosi=Pin(mosiPin),
                         miso=Pin(misoPin))

    def deinit(self):
        """Deinitialization"""
        try:
            self._spi.deinit()
            del self._spi
        except AttributeError:
            pass

    async def __aenter__(self):
        await self.async_lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            self.async_lock.release()
        except RuntimeError:   # in case it's already released somehow
            pass
        self.deinit()
        return False
    
    def configure(self, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=_SPI.MSB):
        if self.async_lock.locked():
            self._spi.init(baudrate=baudrate,
                           polarity=polarity,
                           phase=phase,
                           bits=bits,
                           firstbit=_SPI.MSB)
        else:
            raise RuntimeError("First acquire async lock!")
        
    def write(self, buf):
        """Write to the SPI device"""
        return self._spi.write(buf)

    def readinto(self, buf, write_value=0):
        """Read from the SPI device into a buffer"""
        return self._spi.readinto(buf, write_value)

    def write_readinto(self, buffer_out, buffer_in):
        """Perform a half-duplex write from buffer_out and then
        read data into buffer_in
        """
        self._spi.write_readinto(buffer_out, buffer_in)

class SPIDevice:
    """
    Represents a single SPI device and manages locking the bus and the device
    address.

    :param ~busio.SPI spi: The SPI bus the device is on
    :param ~digitalio.DigitalInOut chip_select: The chip select pin object that implements the
        DigitalInOut API.
    :param bool cs_active_value: Set to True if your device requires CS to be active high.
        Defaults to False.
    :param int baudrate: The desired SCK clock rate in Hertz. The actual clock rate may be
        higher or lower due to the granularity of available clock settings (MCU dependent).
    :param int polarity: The base state of the SCK clock pin (0 or 1).
    :param int phase: The edge of the clock that data is captured. First (0) or second (1).
        Rising or falling depends on SCK clock polarity.
    :param int extra_clocks: The minimum number of clock cycles to cycle the bus after CS is high.
        (Used for SD cards.)

    .. note:: This class is **NOT** built into CircuitPython. See
      :ref:`here for install instructions <bus_device_installation>`.

    Example:

    .. code-block:: python

        import busio
        import digitalio
        from board import *
        from adafruit_bus_device.spi_device import SPIDevice

        with busio.SPI(SCK, MOSI, MISO) as spi_bus:
            cs = digitalio.DigitalInOut(D10)
            device = SPIDevice(spi_bus, cs)
            bytes_read = bytearray(4)
            # The object assigned to spi in the with statements below
            # is the original spi_bus object. We are using the busio.SPI
            # operations busio.SPI.readinto() and busio.SPI.write().
            with device as spi:
                spi.readinto(bytes_read)
            # A second transaction
            with device as spi:
                spi.write(bytes_read)
    """

    def __init__(self,
                 spi: SPI,
                 cs_pin: int,
                 cs_active_value: bool = False,
                 baudrate: int = 1000000,
                 polarity: int = 0,
                 phase: int = 0,
                 bits: int = 8,
                 firstbit=_SPI.MSB) -> None:
        self.spi = spi
        self.cs_pin = Pin(cs_pin)
        self.cs_active_value = cs_active_value
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.bits = bits
        self.firstbit = firstbit

    async def setup(self) -> None:
        self.cs_pin.init(self.cs_pin.OUT)
        self.cs_pin.value(not self.cs_active_value)

    async def __aenter__(self) -> "SPIDevice":
        await self.spi.async_lock.acquire()
        self.spi.configure(baudrate=self.baudrate,
                           polarity=self.polarity,
                           phase=self.phase,
                           bits=self.bits,
                           firstbit=self.firstbit)
        self.cs_pin.value(self.cs_active_value)
        await asyncio.sleep_ms(1)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[type]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> bool:
        self.cs_pin.value(not self.cs_active_value)
        await asyncio.sleep_ms(1)
        try:
            self.spi.async_lock.release()
        except RuntimeError:   # in case it's already released somehow
            pass
        return False

    async def write(self, buf):
        """Write data from the buffer to SPI"""
        self.spi.write(buf)

    async def readinto(self, buf, write_value=0):
        """Read data from SPI and into the buffer"""
        self.spi.readinto(buf, write_value=write_value)

    async def write_readinto(self, buffer_out, buffer_in):
        """Perform a half-duplex write from buffer_out and then
        read data into buffer_in
        """
        self.spi.write_readinto(buffer_out, buffer_in)


