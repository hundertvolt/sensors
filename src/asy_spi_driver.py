"""Async wrapper around machine.SPI: bus-level primitives (SPI) plus a per-device, lock-scoped
wrapper (SPIDevice) used by this codebase's one current SPI consumer (asy_fram_driver.py's
FRAM_SPI, one SPIDevice per FRAM chip's CS pin).

Shared contract: a method returns None (or no-ops, for a None-typed method) only for a
non-hardware failure - the bus not being initialized (self._spi is None, e.g. after deinit()) or
a mismatched write_readinto() buffer pair. Unlike asy_i2c_driver.py's I2C, real RP2040 hardware
SPI transfers have no OSError-raising fault path at all (confirmed against extmod/machine_spi.c:
the blocking transfer HAL - spi_write_blocking()/spi_write_read_blocking(), reached via
mp_machine_spi_transfer() - has no error return once the bus is constructed). SPI has no ACK/NAK
concept the way I2C does, so a real bus fault such as a disconnected wire is invisible at this
layer, not surfaced as an exception. write()/readinto() therefore genuinely never raise, full
stop - not merely "in practice, let it propagate" the way I2C's OSError carve-out works.
write_readinto() is the one exception: machine.SPI.write_readinto() itself raises ValueError if
its two buffers differ in length (mp_machine_spi_write_readinto(), shared by hardware and soft
SPI alike) - caught here and turned into a None return, matching this project's established
"malformed non-hardware input -> None" convention (see asy_i2c_driver.py's
get_register_struct()/set_register_struct() for the same shape against a malformed reg_format).

This contract applies to ongoing operational calls, not one-time setup: SPI.__init__()/init()
(constructs real Pin/machine.SPI objects, which can raise ValueError for a bad pin/port number, or
NotImplementedError if firstbit=SPI.LSB is ever requested - rp2 hardware SPI only implements MSB,
confirmed against ports/rp2/machine_spi.c) is deliberately allowed to raise, the same "fail loudly
once at boot" precedent asy_i2c_driver.py's own docstring establishes for its constructor.
SPIDevice.configure()'s RuntimeError for being called without the bus lock held is the same kind
of programmer-error guard, not a data-dependent operational failure.
"""

import asyncio

from base_classes import Lockable
from machine import SPI as _SPI
from machine import Pin


class SPI:
    def __init__(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        self._spi: _SPI | None = None
        self.async_lock = asyncio.Lock()
        self.init(port_id, sck_pin, mosi_pin, miso_pin)

    def init(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        # deinit() first so re-init can't leak a claimed peripheral/pins, matching I2C.init()'s
        # own precedent.
        self.deinit()
        self._spi = _SPI(port_id, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))

    def deinit(self) -> None:
        # machine.SPI.deinit() actually deactivates the hardware bus - a bound method on a real
        # constructed _SPI object, so it can't raise AttributeError (confirmed, same reasoning as
        # the identical asy_i2c_driver.py fix).
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
        # Programmer-error guards, not operational failures: configure() is meant to be called
        # only from within SPIDevice.__aenter__, on an initialized bus, after the lock is held.
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
        # Full-duplex simultaneous transfer, not write-then-read: buffer_out/buffer_in must be
        # the same length (real machine.SPI.write_readinto() raises ValueError otherwise, caught
        # below and turned into this driver's usual non-hardware-failure None).
        if self._spi is None:
            return None
        try:
            self._spi.write_readinto(buffer_out, buffer_in)
        except ValueError:  # buffer_out/buffer_in length mismatch
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

    async def setup(self) -> None:
        self.cs_pin.init(self.cs_pin.OUT)
        self.cs_pin.value(not self.cs_active_value)

    async def __aenter__(self) -> "SPIDevice":
        await super().__aenter__()
        # A failure below means __aenter__ itself raises, so `async with` never calls __aexit__ -
        # the lock and (if asserted) CS pin must be released here or they leak permanently.
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
            self.cs_pin.value(not self.cs_active_value)  # deassert if it was ever asserted; a no-op otherwise
            self.asy_lock.release()
            raise
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool:
        # object-typed to satisfy Liskov substitution against Lockable.__aexit__ (only forwarded
        # below, never inspected). CS deassert + settle runs first, while the lock is still held -
        # only then does super().__aexit__() release it (swallowing a pre-released RuntimeError).
        self.cs_pin.value(not self.cs_active_value)
        await asyncio.sleep(0.001)
        return await super().__aexit__(exc_type, exc_val, exc_tb)

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
