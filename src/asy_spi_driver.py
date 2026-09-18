"""Async wrapper around machine.SPI: SPI (bus primitives) plus SPIDevice (per-device, lock-scoped
CS-pin wrapper). Sole consumer: asy_fram_driver.py's FRAM_SPI.
"""
# RP2040 SPI has no ACK/NAK, so write() cannot raise; a 32+ byte READ can raise OSError(EIO) on an
# RX overrun since 1.29. write_readinto() turns machine.SPI's mismatched-length ValueError into
# None; setup (__init__/init(), configure()) may raise. Raise sites: SPECIFICATION.md Part F.5.

import asyncio
import time

from machine import SPI as _SPI
from machine import Pin
from micropython import const

from base_classes import Lockable

# Blocking CS settle. Both parts specify tCSU/tCSH >= 10 ns and tD >= 40 ns (MB85RS2MTA) / 60 ns
# (MB85RS64V), so 2 us is orders of magnitude clear of them; rp2's sleep_us() busy-waits on
# time_us_64(), where sleep_us(1) only promises an elapsed time in (0, 1] us and 2 promises >= 1.
_CS_SETTLE_US = const(2)

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal

    from typing_extensions import Self


class SPI:
    def __init__(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        self._spi: _SPI | None = None
        self.async_lock = asyncio.Lock()
        self.init(port_id, sck_pin, mosi_pin, miso_pin)

    def init(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        # deinit() first so a re-init always goes through the same "bus unavailable" state a
        # caller-visible deinit() produces, rather than swapping self._spi under live readers.
        self.deinit()
        self._spi = _SPI(port_id, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))

    def deinit(self) -> None:
        # machine.SPI.deinit() does NOT deactivate the rp2 hardware bus - it is forwarded for
        # portability only, and dropping self._spi is what actually puts this wrapper into its
        # documented "bus unavailable" state. See SPECIFICATION.md Part F.5.
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
            return
        self._spi.write(buf)  # rp2: always returns None (confirmed against extmod/machine_spi.c)
        return

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        # SPI is full-duplex - reading still clocks write_value out on MOSI meanwhile. An
        # OSError(EIO) from a 32+ byte RX overrun propagates uncaught, same as I2C's does.
        if self._spi is None:
            return
        self._spi.readinto(buf, write_value)
        return

    def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        # Full-duplex simultaneous transfer: buffer_out/buffer_in must match length, or
        # machine.SPI.write_readinto() raises ValueError, caught below and turned into None.
        # OSError(EIO) from a 32+ byte RX overrun is deliberately not caught - it propagates.
        if self._spi is None:
            return
        try:
            self._spi.write_readinto(buffer_out, buffer_in)
        except ValueError:  # length mismatch
            return
        return


class SPIDevice(Lockable):
    # Binds an SPI bus to one device's CS pin and the bus's shared asyncio lock, so consecutive
    # transactions from different devices on the same bus can't interleave.
    def __init__(
        self,
        spi: SPI,
        cs_pin: int,
        *,
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

    def session_begin(self) -> None:
        # Everything __aenter__ does between the lock operations, for a caller that already holds
        # the bus lock - configure()'s own guard enforces that contract. The settle blocks on
        # purpose: an awaited one here hands the loop to another task with CS asserted and the bus
        # locked. The scheduling points belong to the coroutine owning the operation instead.
        if not self.initialized:
            raise RuntimeError("SPIDevice not set up - call setup() first")
        try:
            self.spi.configure(
                baudrate=self.baudrate,
                polarity=self.polarity,
                phase=self.phase,
                bits=self.bits,
                firstbit=self.firstbit,
            )
            self.cs_pin.value(self.cs_active_value)
            time.sleep_us(_CS_SETTLE_US)
        except BaseException:
            self.cs_pin.value(not self.cs_active_value)  # deassert if asserted
            raise

    def session_end(self) -> None:
        # The caller's own try/finally is what guarantees this runs; the async form below is that
        # caller for `async with` users.
        self.cs_pin.value(not self.cs_active_value)
        time.sleep_us(_CS_SETTLE_US)

    async def __aenter__(self) -> "Self":
        # Pin.value() writes the GPIO register unconditionally regardless of direction, so
        # entering before setup() would silently fail to assert CS rather than raise. Checked
        # before the lock is acquired, so a misuse never even contends for the bus.
        if not self.initialized:
            raise RuntimeError("SPIDevice not set up - call setup() first")
        await super().__aenter__()
        # __aenter__ raising means `async with` never calls __aexit__, so clean up here too.
        try:
            self.session_begin()
        except BaseException:
            self.asy_lock.release()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,  # `object`, not TracebackType: the precise name only exists under TYPE_CHECKING
    ) -> "Literal[False]":
        # params are only forwarded to super().__aexit__(), never inspected. CS deassert runs
        # first, while the lock is still held; the yield afterwards is this path's one scheduling
        # point, placed after the release so a burst of sessions cannot starve the loop.
        self.session_end()
        released = await super().__aexit__(exc_type, exc_val, exc_tb)
        await asyncio.sleep(0)
        return released

    async def setup(self) -> None:
        self.cs_pin.init(self.cs_pin.OUT)
        self.cs_pin.value(not self.cs_active_value)
        self.initialized = True

    def write_sync(self, buf: bytes | bytearray | memoryview) -> None:
        self.spi.write(buf)

    def readinto_sync(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self.spi.readinto(buf, write_value=write_value)

    def write_readinto_sync(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        # Full-duplex simultaneous transfer, not write-then-read - see SPI.write_readinto().
        self.spi.write_readinto(buffer_out, buffer_in)

    # The async transfers stay for `async with` callers (a future SPI sensor driver), expressed on
    # the synchronous primitives above so the bus sequence has exactly one implementation.
    async def write(self, buf: bytes | bytearray | memoryview) -> None:
        self.write_sync(buf)

    async def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self.readinto_sync(buf, write_value=write_value)

    async def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        self.write_readinto_sync(buffer_out, buffer_in)
