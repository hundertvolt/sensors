"""Wrapper around machine.SPI: SPI (bus primitives) plus SPIDevice (per-device CS-pin wrapper, with an async lock-scoped
session and synchronous ones). Sole consumer: asy_fram_driver.py's FRAM_SPI, through a synchronous operation.
"""
# RP2040 SPI has no ACK/NAK, so write() cannot raise; a 32+ byte READ can raise OSError(EIO) on an
# RX overrun since 1.29. write_readinto() turns machine.SPI's mismatched-length ValueError into
# None; setup (__init__/init(), configure()) may raise. Raise sites: SPECIFICATION.md Part F.5.

import asyncio

from machine import SPI as _SPI
from machine import Pin

from asy_base_classes import Lockable

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from typing_extensions import Self

    # One synchronous operation's wiring: the CS pin's value(), its active level, and the bus's own write and readinto.
    Wiring = tuple[Callable[[bool], object], bool, Callable[[bytes | bytearray | memoryview], None], Callable[[bytearray | memoryview], None]]


class SPI:
    def __init__(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        self._spi: _SPI | None = None
        self.configured_for: object | None = None  # the device the bus was last configured for; None: not yet
        self.bus_lock = asyncio.Lock()  # held by every async session; a synchronous session runs only while it is free
        self.init(port_id, sck_pin, mosi_pin, miso_pin)

    def configure(
        self,
        baudrate: int = 1000000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = _SPI.MSB,
    ) -> None:
        # Programmer-error guard: only ever called from SPIDevice's session start, on an initialized bus.
        if self._spi is None:
            raise RuntimeError("SPI bus not initialized - call init() first")
        self._spi.init(baudrate=baudrate, polarity=polarity, phase=phase, bits=bits, firstbit=firstbit)

    def deinit(self) -> None:
        # machine.SPI.deinit() does NOT deactivate the rp2 hardware bus - it is forwarded for
        # portability only, and dropping self._spi is what actually puts this wrapper into its
        # documented "bus unavailable" state. See SPECIFICATION.md Part F.5.
        self.configured_for = None
        if self._spi is not None:
            self._spi.deinit()
            self._spi = None

    def init(self, port_id: int, sck_pin: int, mosi_pin: int, miso_pin: int) -> None:
        # deinit() first so a re-init always goes through the same "bus unavailable" state a
        # caller-visible deinit() produces, rather than swapping self._spi under live readers.
        self.deinit()
        self._spi = _SPI(port_id, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        # SPI is full-duplex - reading still clocks write_value out on MOSI meanwhile. An
        # OSError(EIO) from a 32+ byte RX overrun propagates uncaught, same as I2C's does.
        if self._spi is None:
            return
        self._spi.readinto(buf, write_value)

    def transfers(self) -> "tuple[Callable[[bytes | bytearray | memoryview], None], Callable[[bytearray | memoryview], None]]":
        # machine.SPI's own write and readinto, for a synchronous operation's commands; an RX overrun propagates as readinto() says.
        if self._spi is None:
            raise RuntimeError("SPI bus not initialized - call init() first")
        return self._spi.write, self._spi.readinto

    def write(self, buf: bytes | bytearray | memoryview) -> None:
        if self._spi is None:
            return
        self._spi.write(buf)  # rp2: always returns None (confirmed against extmod/machine_spi.c)

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
        super().__init__(session_lock=self.spi.bus_lock)
        self._cs_pin = Pin(cs_pin)
        self._cs_active_value = cs_active_value
        self._baudrate = baudrate
        self._polarity = polarity
        self._phase = phase
        self._bits = bits
        self._firstbit = firstbit
        self.initialized = False  # _cs_pin isn't configured as an output until setup() runs

    async def __aenter__(self) -> "Self":
        # Pin.value() writes the GPIO register unconditionally regardless of direction, so
        # entering before setup() would silently fail to assert CS rather than raise. Checked
        # before the lock is acquired, so a misuse never even contends for the bus.
        if not self.initialized:
            raise RuntimeError("SPIDevice not set up - call setup() first")
        await super().__aenter__()
        # __aenter__ raising means `async with` never calls __aexit__, so clean up here too.
        try:
            self._begin()
        except BaseException:
            self.session_lock.release()
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

    def _begin(self) -> None:
        # Configures the bus, then asserts CS.
        if not self.initialized:
            raise RuntimeError("SPIDevice not set up - call setup() first")
        try:
            self._configure()
            self._cs_pin.value(self._cs_active_value)
        except BaseException:
            self._cs_pin.value(not self._cs_active_value)  # deassert if asserted
            raise

    def _configure(self) -> None:
        # Configures the bus only when another device (or none) configured it last.
        spi = self.spi
        if spi.configured_for is not self:
            spi.configured_for = None  # until configure() returns: a half-applied init is no device's
            spi.configure(
                baudrate=self._baudrate,
                polarity=self._polarity,
                phase=self._phase,
                bits=self._bits,
                firstbit=self._firstbit,
            )
            spi.configured_for = self

    def begin_sync(self) -> "Wiring":
        # One synchronous operation's start, its checks once rather than per command (C.8): refused while an async session
        # holds the bus, whose CS may stay asserted across a suspension; the bus configured for this device. The operation
        # then frames each command itself with the returned CS and bus methods, never suspending in between.
        if self.session_lock.locked():
            raise RuntimeError("SPI bus held by an async session")
        if not self.initialized:
            raise RuntimeError("SPIDevice not set up - call setup() first")
        self._configure()
        write, readinto = self.spi.transfers()
        return self._cs_pin.value, self._cs_active_value, write, readinto

    async def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self.readinto_sync(buf, write_value=write_value)

    def readinto_sync(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self.spi.readinto(buf, write_value=write_value)

    def session_begin(self) -> None:
        # The synchronous session, for a caller that runs it whole without suspending (C.8). Refused while an async
        # session holds the bus, whose CS may stay asserted across a suspension.
        if self.session_lock.locked():
            raise RuntimeError("SPI bus held by an async session")
        self._begin()

    def session_end(self) -> None:
        # The caller's own try/finally is what guarantees this runs; __aexit__() is that caller for
        # `async with` users.
        self._cs_pin.value(not self._cs_active_value)

    async def setup(self) -> None:
        self._cs_pin.init(self._cs_pin.OUT, value=not self._cs_active_value)  # value= sets the level before the pad becomes an output: no CS glitch.
        self.initialized = True

    # The async transfers readinto()/write()/write_readinto() stay for `async with` callers (a future SPI sensor
    # driver), each expressed on its *_sync() primitive so the bus sequence has exactly one implementation.
    async def write(self, buf: bytes | bytearray | memoryview) -> None:
        self.write_sync(buf)

    async def write_readinto(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        self.write_readinto_sync(buffer_out, buffer_in)

    def write_readinto_sync(
        self,
        buffer_out: bytes | bytearray | memoryview,
        buffer_in: bytearray | memoryview,
    ) -> None:
        # Full-duplex simultaneous transfer, not write-then-read - see SPI.write_readinto().
        self.spi.write_readinto(buffer_out, buffer_in)

    def write_sync(self, buf: bytes | bytearray | memoryview) -> None:
        self.spi.write(buf)
