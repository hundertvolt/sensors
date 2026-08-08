"""Async wrapper around machine.SPI: SPI (bus primitives) plus SPIDevice (per-device, lock-scoped
CS-pin wrapper). Sole consumer: asy_fram_driver.py's FRAM_SPI. Unlike I2C, real RP2040 SPI transfers
have no ACK/NAK concept once the bus is constructed, so write()/readinto() never raise;
write_readinto() is the one exception (ValueError on mismatched buffer lengths, caught and turned
into None). One-time setup (__init__/init(), configure()) is exempt and may raise.
"""

import asyncio

from machine import SPI as _SPI
from machine import Pin

from base_classes import Lockable

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import TracebackType


class SPI:
    def __init__(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        self._spi: _SPI | None = None
        self.async_lock = asyncio.Lock()
        self.init(port_id, sck_pin, mosi_pin, miso_pin)

    def init(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        # deinit() first so re-init can't leak a claimed peripheral/pins.
        self.deinit()
        self._spi = _SPI(port_id, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))

    def deinit(self) -> None:
        # Deactivates the real hardware bus; a bound method on a constructed object, so it
        # can't raise AttributeError.
        if self._spi is not None:
            self._spi.deinit()
            self._spi = None

    def configure(
        self,
        baudrate: int = 1000000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = _SPI.MSB,
    ) -> None:
        # Programmer-error guards: only ever called from SPIDevice.__aenter__, on an
        # initialized, lock-held bus.
        if self._spi is None:
            raise RuntimeError("SPI bus not initialized - call init() first")
        if not self.async_lock.locked():
            raise RuntimeError("First acquire async lock!")
        self._spi.init(baudrate=baudrate, polarity=polarity, phase=phase, bits=bits, firstbit=firstbit)

    def write(self, buf: bytes | bytearray | memoryview) -> None:
        if self._spi is None:
            return None
        self._spi.write(buf)  # rp2: always returns None (confirmed against extmod/machine_spi.c)
        return None

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        # SPI is full-duplex - reading still clocks write_value out on MOSI meanwhile.
        if self._spi is None:
            return None
        self._spi.readinto(buf, write_value)
        return None

    def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        # Full-duplex simultaneous transfer: buffer_out/buffer_in must match length, or
        # machine.SPI.write_readinto() raises ValueError, caught below and turned into None.
        if self._spi is None:
            return None
        try:
            self._spi.write_readinto(buffer_out, buffer_in)
        except ValueError:  # length mismatch
            return None
        return None


class SPIDevice(Lockable):
    # Binds an SPI bus to one device's CS pin and the bus's shared asyncio lock, so consecutive
    # transactions from different devices on the same bus can't interleave.
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
        super().__init__(asy_lock=self.spi.async_lock)
        self.cs_pin = Pin(cs_pin)
        self.cs_active_value = cs_active_value
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.bits = bits
        self.firstbit = firstbit
        self.initialized = False  # cs_pin isn't configured as an output until setup() runs

    async def __aenter__(self) -> "SPIDevice":
        # Pin.value() writes the GPIO register unconditionally regardless of direction, so
        # entering before setup() would silently fail to assert CS rather than raise.
        if not self.initialized:
            raise RuntimeError("SPIDevice not set up - call setup() first")
        await super().__aenter__()
        # __aenter__ raising means `async with` never calls __aexit__, so clean up here too.
        try:
            self.spi.configure(
                baudrate=self.baudrate,
                polarity=self.polarity,
                phase=self.phase,
                bits=self.bits,
                firstbit=self.firstbit,
            )
            self.cs_pin.value(self.cs_active_value)
            await asyncio.sleep(0.001)
        except BaseException:
            self.cs_pin.value(not self.cs_active_value)  # deassert if asserted
            self.asy_lock.release()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: "type[BaseException] | None",
        exc_val: "BaseException | None",
        exc_tb: "TracebackType | None",
    ) -> bool:
        # params are only forwarded to super().__aexit__(), never inspected. CS deassert runs
        # first, while the lock is still held.
        self.cs_pin.value(not self.cs_active_value)
        await asyncio.sleep(0.001)
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    async def setup(self) -> None:
        self.cs_pin.init(self.cs_pin.OUT)
        self.cs_pin.value(not self.cs_active_value)
        self.initialized = True

    async def write(self, buf: bytes | bytearray | memoryview) -> None:
        self.spi.write(buf)

    async def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self.spi.readinto(buf, write_value=write_value)

    async def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        # Full-duplex simultaneous transfer, not write-then-read - see SPI.write_readinto().
        self.spi.write_readinto(buffer_out, buffer_in)
