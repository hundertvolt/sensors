import asyncio
from uasyncio import Lock
from machine import SPI as _SPI
from machine import Pin
from typing import Type

try:  # just for typing and unsupported from micropython yet
    from types import TracebackType
except Exception:
    pass


class SPI:
    def __init__(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        """Initialize the Port"""
        self.async_lock = Lock()
        self._spi: _SPI | None = None
        self.init(port_id, sck_pin, mosi_pin, miso_pin)

    def init(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        """Initialization"""
        self.deinit()
        self._spi = _SPI(port_id, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))

    def deinit(self) -> None:
        """Deinitialization"""
        if self._spi is not None:
            try:
                self._spi.deinit()
                self._spi = None
            except AttributeError:
                pass

    def configure(
        self,
        baudrate: int = 1000000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = _SPI.MSB,
    ) -> None:
        if self._spi is not None and self.async_lock.locked():
            # noinspection PyArgumentList
            self._spi.init(  # type: ignore[call-arg]
                baudrate=baudrate, polarity=polarity, phase=phase, bits=bits, firstbit=firstbit
            )  # micropython build for rp2 does not recognize "pins" keyword!
        else:
            raise RuntimeError("First acquire async lock!")

    def write(self, buf: bytes | bytearray | memoryview) -> int | None:
        """Write to the SPI device"""
        if self._spi is None:
            return None
        return self._spi.write(buf)

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> int | None:
        """Read from the SPI device into a buffer"""
        if self._spi is None:
            return None
        return self._spi.readinto(buf, write_value)

    def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        """Perform a half-duplex write from buffer_out and then
        read data into buffer_in
        """
        if self._spi is not None:
            self._spi.write_readinto(buffer_out, buffer_in)


class SPIDevice:
    """
    Represents a single SPI device and manages locking the bus and the device
    address.

    :param ~busio.SPI spi: The SPI bus the device is on
    :param ~digitalio.DigitalInOut cs_pin: The chip select pin object that implements the
        DigitalInOut API.
    :param bool cs_active_value: Set to True if your device requires CS to be active high.
        Defaults to False.
    :param int baudrate: The desired SCK clock rate in Hertz. The actual clock rate may be
        higher or lower due to the granularity of available clock settings (MCU dependent).
    :param int polarity: The base state of the SCK clock pin (0 or 1).
    :param int phase: The edge of the clock that data is captured. First (0) or second (1).
        Rising or falling depends on SCK clock polarity.
    """

    def __init__(
        self,
        spi: SPI,
        cs_pin: int,
        cs_active_value: bool = False,
        baudrate: int = 1000000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = _SPI.MSB,
    ) -> None:
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
        self.spi.configure(
            baudrate=self.baudrate,
            polarity=self.polarity,
            phase=self.phase,
            bits=self.bits,
            firstbit=self.firstbit,
        )
        self.cs_pin.value(self.cs_active_value)
        await asyncio.sleep(0.001)
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        self.cs_pin.value(not self.cs_active_value)
        await asyncio.sleep(0.001)
        try:
            self.spi.async_lock.release()
        except RuntimeError:  # in case it's already released somehow
            pass
        return False

    async def write(self, buf: bytes | bytearray | memoryview) -> None:
        """Write data from the buffer to SPI"""
        self.spi.write(buf)

    async def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        """Read data from SPI and into the buffer"""
        self.spi.readinto(buf, write_value=write_value)

    async def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        """Perform a half-duplex write from buffer_out and then
        read data into buffer_in
        """
        self.spi.write_readinto(buffer_out, buffer_in)
