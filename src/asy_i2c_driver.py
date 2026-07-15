"""Async wrapper around machine.I2C: bus-level primitives (I2C) plus a per-device, lock-scoped
wrapper (I2CDevice) used by every I2C sensor driver in this codebase (asy_scd30_driver.py,
asy_sgp40_driver.py, asy_bmp3xx_driver.py).

Shared contract: a method returns None (or no-ops, for a None-typed method) only for a
non-hardware failure - the bus not being initialized (self._i2c is None, e.g. after deinit()),
an out-of-range bit-field request, or a malformed reg_format for the struct-based helpers. A
real I2C bus/device failure (OSError - NAK, timeout, no such device) is never caught here; it
propagates to the caller, matching every existing Reader class's own try/except around a full
read/write sequence (see e.g. asy_scd30_driver.py's SCD30_Reader._read_scd).
"""

import asyncio
import struct

from base_classes import Lockable
from machine import I2C as _I2C
from machine import Pin


class I2C:
    def __init__(self, port_id: int, scl_pin: int, sda_pin: int, frequency: int = 100000) -> None:
        self._i2c: _I2C | None = None
        self.async_lock = asyncio.Lock()
        self.init(port_id, scl_pin, sda_pin, frequency)

    def init(self, port_id: int, scl_pin: int, sda_pin: int, frequency: int) -> None:
        # Always deinit() any bus this instance previously held first, so re-init can't leak a
        # claimed peripheral/pins.
        self.deinit()
        self._i2c = _I2C(port_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=frequency)

    def deinit(self) -> None:
        # machine.I2C.deinit() actually deactivates the hardware bus - not just dropping the
        # Python reference, which left the peripheral/pins claimed.
        if self._i2c is not None:
            self._i2c.deinit()
            self._i2c = None

    def scan(self) -> list[int] | None:
        # machine.I2C.scan(): every ACKing address in 0x08-0x77.
        if self._i2c is None:
            return None
        return self._i2c.scan()

    def readfrom_into(
        self,
        address: int,
        buffer: bytearray,
        start: int = 0,
        end: int | None = None,
        stop: bool = True,
    ) -> None:
        # machine.I2C.readfrom_into(), with a start/end slice instead of a pre-sliced buffer.
        if self._i2c is None:
            return
        if end is None:
            end = len(buffer)
        self._i2c.readfrom_into(address, memoryview(buffer)[start:end], stop)

    def writeto(
        self,
        address: int,
        buffer: bytes | bytearray | str,
        start: int = 0,
        end: int | None = None,
        stop: bool = True,
    ) -> int | None:
        # machine.I2C.writeto(): returns the number of ACKs received.
        if self._i2c is None:
            return None
        if isinstance(buffer, str):
            buffer = bytes([ord(x) for x in buffer])
        if end is None:
            end = len(buffer)
        return self._i2c.writeto(address, memoryview(buffer)[start:end], stop)

    def writeto_then_readfrom(
        self,
        address: int,
        buffer_out: bytes | bytearray,
        buffer_in: bytearray,
        out_start: int = 0,
        out_end: int | None = None,
        in_start: int = 0,
        in_end: int | None = None,
        stop: bool = True,
    ) -> None:
        # Not a native machine.I2C primitive - a write, then a separate read (no repeated
        # start), built from this class's own writeto()/readfrom_into().
        self.writeto(address, buffer_out, out_start, out_end, stop=stop)
        self.readfrom_into(address, buffer_in, in_start, in_end, stop=stop)

    @staticmethod
    def _bitfield_range_ok(num_bits: int, start_bit: int, reg_width: int) -> bool:
        # Shared range guard for get_bits()/set_bits(): num_bits/start_bit must describe a
        # field that actually fits inside a reg_width-byte register.
        return num_bits > 0 and start_bit >= 0 and reg_width > 0 and start_bit + num_bits <= reg_width * 8

    @staticmethod
    def _bitmask(num_bits: int, start_bit: int) -> int:
        return ((1 << num_bits) - 1) << start_bit

    @staticmethod
    def _bytes_to_int(mem_value: bytes, lsb_first: bool) -> int:
        # Shared byte-order reconstruction for get_bits()/set_bits(): lsb_first says whether the
        # register's first byte (index 0) is the least- or most-significant.
        reg = 0
        order = range(len(mem_value) - 1, -1, -1) if lsb_first else range(len(mem_value))
        for i in order:
            reg = (reg << 8) | mem_value[i]
        return reg

    def get_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        lsb_first: bool = True,
    ) -> int | None:
        # Reads an arbitrary bit-field out of a reg_width-byte register.
        if self._i2c is None or not self._bitfield_range_ok(num_bits, start_bit, reg_width):
            return None
        mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)
        reg = self._bytes_to_int(mem_value, lsb_first)
        return (reg & self._bitmask(num_bits, start_bit)) >> start_bit

    def set_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        value: int,
        reg_width: int = 1,
        lsb_first: bool = True,
    ) -> None:
        # Read-modify-write counterpart of get_bits(). Byte order is derived from lsb_first
        # alone (this used to also take a separate `endian` param for the write-back, which
        # could silently disagree with lsb_first for reg_width > 1 - a single flag can't
        # disagree with itself).
        if self._i2c is None or not self._bitfield_range_ok(num_bits, start_bit, reg_width):
            return
        mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)
        reg = self._bytes_to_int(mem_value, lsb_first)
        reg &= ~self._bitmask(num_bits, start_bit)
        reg |= value << start_bit
        self._i2c.writeto_mem(address, reg_addr, reg.to_bytes(reg_width, "little" if lsb_first else "big"))

    def get_register_struct(self, address: int, reg_addr: int, reg_format: str) -> int | float | bytes | None:
        # struct-typed single-value register read; byte order comes entirely from reg_format's
        # own prefix character (e.g. ">H"), matching set_register_struct. Return type excludes
        # `bool`: confirmed directly against the real interpreter that MicroPython's struct
        # module doesn't support the '?' typecode at all (raises ValueError), unlike CPython's -
        # so struct.unpack here can never actually produce one.
        if self._i2c is None:
            return None
        try:
            size = struct.calcsize(reg_format)
        except ValueError:  # malformed reg_format
            return None
        raw = self._i2c.readfrom_mem(address, reg_addr, size)
        try:
            # struct.unpack declared to return Any, but int | float | bytes are possible. A
            # zero-field format (e.g. "", or pad-bytes-only like "2x") unpacks to an empty
            # tuple despite a nonzero calcsize - confirmed directly, not assumed - so indexing
            # [0] unconditionally would raise IndexError; the emptiness check below avoids that
            # rather than adding IndexError to this except clause.
            unpacked = struct.unpack(reg_format, memoryview(raw))
        except ValueError:  # malformed reg_format
            return None
        if not unpacked:
            return None
        value = unpacked[0]
        if isinstance(value, (int, float, bytes)):
            return value
        return None

    def set_register_struct(self, address: int, reg_addr: int, reg_format: str, value: int) -> None:
        # struct-typed single-value register write; byte order comes entirely from reg_format's
        # own prefix character, matching get_register_struct (this used to instead take a
        # separate `endian` param that could silently disagree with reg_format's own prefix).
        # Confirmed directly, an inherent MicroPython quirk rather than a bug here: unlike
        # CPython's struct.error, struct.pack silently truncates a value that doesn't fit
        # reg_format (e.g. pack("B", 999) -> b"\xe7"), and silently zero-pads/ignores a
        # reg_format needing a different number of values than the one `value` this method ever
        # supplies (e.g. pack(">HH", 5) -> b"\x00\x05\x00\x00", not an error) - the try/except
        # below only ever catches a genuinely malformed reg_format string itself. This method is
        # deliberately single-value-only (see its name/signature); a multi-field reg_format was
        # never a supported input, but silently writes a partially-zeroed register rather than
        # erroring - worth knowing if this is ever extended to accept multiple values.
        if self._i2c is None:
            return
        try:
            packed = struct.pack(reg_format, value)
        except ValueError:  # malformed reg_format
            return
        self._i2c.writeto_mem(address, reg_addr, packed)


class I2CDevice(Lockable):
    # Binds an I2C bus to one device address and the bus's shared asyncio lock, so consecutive
    # transactions from different devices on the same bus can't interleave.
    def __init__(self, i2c: I2C, device_address: int) -> None:
        self.i2c = i2c
        super().__init__(asy_lock=self.i2c.async_lock)
        self.device_address = device_address

    async def setup(self, probe: bool = True) -> None:
        if probe:
            await self.__probe_for_device()

    async def readinto(
        self,
        buf: bytearray,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        # end=None is passed straight through - I2C.readfrom_into() already defaults it to
        # len(buf) itself, so resolving it here too would just be the same computation twice.
        self.i2c.readfrom_into(self.device_address, buf, start=start, end=end)

    async def write(
        self,
        buf: bytes | bytearray | str,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        self.i2c.writeto(self.device_address, buf, start=start, end=end)

    async def write_then_readinto(
        self,
        out_buffer: bytes | bytearray,
        in_buffer: bytearray,
        out_start: int = 0,
        out_end: int | None = None,
        in_start: int = 0,
        in_end: int | None = None,
    ) -> None:
        self.i2c.writeto_then_readfrom(
            self.device_address,
            out_buffer,
            in_buffer,
            out_start=out_start,
            out_end=out_end,
            in_start=in_start,
            in_end=in_end,
        )

    async def get_bits(
        self,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        lsb_first: bool = True,
    ) -> int | None:
        return self.i2c.get_bits(self.device_address, num_bits, reg_addr, start_bit, reg_width, lsb_first)

    async def set_bits(
        self,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        value: int,
        reg_width: int = 1,
        lsb_first: bool = True,
    ) -> None:
        self.i2c.set_bits(
            self.device_address,
            num_bits,
            reg_addr,
            start_bit,
            value,
            reg_width,
            lsb_first,
        )

    async def get_register_struct(self, reg_addr: int, reg_format: str) -> int | float | bytes | None:
        return self.i2c.get_register_struct(self.device_address, reg_addr, reg_format)

    async def set_register_struct(self, reg_addr: int, reg_format: str, value: int) -> None:
        self.i2c.set_register_struct(self.device_address, reg_addr, reg_format, value)

    async def __probe_for_device(self) -> None:
        # Try to write zero bytes to the device address: an OSError means no device ACKed it.
        # writeto() returning None (bus not initialized, e.g. deinit() was called on the shared
        # I2C instance) is a distinct failure from "no device" and gets its own message.
        try:
            await asyncio.sleep(0.1)
            acked = self.i2c.writeto(self.device_address, b"")
        except OSError:
            raise ValueError(f"No I2C device at address: {self.device_address:#x}") from None
        finally:
            await asyncio.sleep(0.1)
        if acked is None:
            raise RuntimeError("I2C bus not initialized")
