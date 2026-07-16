"""Async wrapper around machine.I2C: bus-level primitives (I2C) plus a per-device, lock-scoped
wrapper (I2CDevice) used by every I2C sensor driver in this codebase (asy_scd30_driver.py,
asy_sgp40_driver.py, asy_bmp3xx_driver.py).

Shared contract: a method returns None (or no-ops, for a None-typed method) only for a
non-hardware failure - the bus not being initialized (self._i2c is None, e.g. after deinit()),
an out-of-range bit-field request, or a malformed reg_format for the struct-based helpers. A
real I2C bus/device failure (OSError - NAK, timeout, no such device) is never caught here; it
propagates to the caller, matching every existing Reader class's own try/except around a full
read/write sequence (see e.g. asy_scd30_driver.py's SCD30_Reader._read_scd).

This contract applies to ongoing operational calls, not one-time setup: I2C.__init__()/init()
(constructs real Pin/machine.I2C objects, which can raise ValueError for a bad pin/port number -
confirmed against current MicroPython docs) and I2CDevice.setup()'s probe (raises ValueError/
RuntimeError - see its own comment) are deliberately allowed to raise. A misconfigured bus should
fail loudly once at boot, the same way setup()'s probe already does, not silently produce a
permanently-nonfunctional driver that then degrades every later call to None.
"""

import asyncio
import struct

from machine import I2C as _I2C
from machine import Pin

from base_classes import Lockable


class I2C:
    def __init__(
        self,
        port_id: int,
        scl_pin: int,
        sda_pin: int,
        frequency: int = 100000,
        timeout: int | None = None,
    ) -> None:
        self._i2c: _I2C | None = None
        self.async_lock = asyncio.Lock()
        self.init(port_id, scl_pin, sda_pin, frequency, timeout)

    def init(
        self,
        port_id: int,
        scl_pin: int,
        sda_pin: int,
        frequency: int,
        timeout: int | None = None,
    ) -> None:
        # deinit() first so re-init can't leak a claimed peripheral/pins. timeout=None omits the
        # kwarg entirely instead of duplicating machine.I2C's own default, so it can't drift out
        # of sync with whatever that default actually is.
        self.deinit()
        if timeout is None:
            self._i2c = _I2C(port_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=frequency)
        else:
            self._i2c = _I2C(port_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=frequency, timeout=timeout)

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
        buf: bytearray,
        start: int = 0,
        end: int | None = None,
        stop: bool = True,
    ) -> None:
        # machine.I2C.readfrom_into(), with a start/end slice instead of a pre-sliced buffer.
        if self._i2c is None:
            return
        if end is None:
            end = len(buf)
        self._i2c.readfrom_into(address, memoryview(buf)[start:end], stop)

    def writeto(
        self,
        address: int,
        buf: bytes | bytearray | str,
        start: int = 0,
        end: int | None = None,
        stop: bool = True,
    ) -> int | None:
        # machine.I2C.writeto() return value is the ACK count. str input assumes Latin-1
        # (single byte per char); a codepoint above 255 raises ValueError, caught below and
        # turned into a None return instead of propagating.
        if self._i2c is None:
            return None
        if isinstance(buf, str):
            try:
                buf = bytes([ord(x) for x in buf])
            except ValueError:  # character outside 0-255
                return None
        if end is None:
            end = len(buf)
        return self._i2c.writeto(address, memoryview(buf)[start:end], stop)

    def writeto_then_readfrom(
        self,
        address: int,
        buffer_out: bytes | bytearray,
        buffer_in: bytearray,
        out_start: int = 0,
        out_end: int | None = None,
        in_start: int = 0,
        in_end: int | None = None,
        out_stop: bool = True,
        in_stop: bool = True,
    ) -> None:
        # Not a native machine.I2C primitive - a write then a read via this class's own
        # writeto()/readfrom_into(). out_stop/in_stop are independent so a repeated-start read
        # (write without a stop, then a read that does stop) is expressible; pass out_stop=False.
        self.writeto(address, buffer_out, out_start, out_end, stop=out_stop)
        self.readfrom_into(address, buffer_in, in_start, in_end, stop=in_stop)

    @staticmethod
    def _bitfield_range_ok(num_bits: int, start_bit: int, reg_width: int) -> bool:
        # Shared range guard for get_bits()/set_bits(): field must fit inside reg_width bytes.
        return num_bits > 0 and start_bit >= 0 and reg_width > 0 and start_bit + num_bits <= reg_width * 8

    @staticmethod
    def _bitmask(num_bits: int, start_bit: int) -> int:
        return ((1 << num_bits) - 1) << start_bit

    @staticmethod
    def _bytes_to_int(mem_value: bytes, lsb_first: bool) -> int:
        # Shared byte-order reconstruction for get_bits()/set_bits(): lsb_first says whether
        # mem_value[0] is the least- or most-significant byte.
        reg = 0
        order = range(len(mem_value) - 1, -1, -1) if lsb_first else range(len(mem_value))
        for i in order:
            reg = (reg << 8) | mem_value[i]
        return reg

    @staticmethod
    def _readfrom_mem(bus: _I2C, address: int, reg_addr: int, nbytes: int, addrsize: int | None) -> bytes:
        # addrsize=None omits the kwarg instead of duplicating machine.I2C's own default (8).
        if addrsize is None:
            return bus.readfrom_mem(address, reg_addr, nbytes)
        return bus.readfrom_mem(address, reg_addr, nbytes, addrsize=addrsize)

    @staticmethod
    def _writeto_mem(bus: _I2C, address: int, reg_addr: int, buf: bytes, addrsize: int | None) -> None:
        if addrsize is None:
            bus.writeto_mem(address, reg_addr, buf)
        else:
            bus.writeto_mem(address, reg_addr, buf, addrsize=addrsize)

    def get_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> int | None:
        # Reads an arbitrary bit-field out of a reg_width-byte register.
        if self._i2c is None or not self._bitfield_range_ok(num_bits, start_bit, reg_width):
            return None
        mem_value = self._readfrom_mem(self._i2c, address, reg_addr, reg_width, addrsize)
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
        addrsize: int | None = None,
    ) -> None:
        # Read-modify-write counterpart of get_bits(). Byte order is derived from lsb_first
        # alone. value is masked to num_bits before being shifted in, so an out-of-range value
        # can't corrupt the bits just above the intended field.
        if self._i2c is None or not self._bitfield_range_ok(num_bits, start_bit, reg_width):
            return
        mem_value = self._readfrom_mem(self._i2c, address, reg_addr, reg_width, addrsize)
        reg = self._bytes_to_int(mem_value, lsb_first)
        reg &= ~self._bitmask(num_bits, start_bit)
        reg |= (value & self._bitmask(num_bits, 0)) << start_bit
        self._writeto_mem(
            self._i2c, address, reg_addr, reg.to_bytes(reg_width, "little" if lsb_first else "big"), addrsize
        )

    def get_register_struct(
        self, address: int, reg_addr: int, reg_format: str, addrsize: int | None = None
    ) -> int | float | bytes | None:
        # Byte order comes from reg_format's own prefix (e.g. ">H"). MicroPython's struct has no
        # '?' typecode, so bool never appears in the return. A zero-field format ("" or "2x")
        # unpacks to an empty tuple despite nonzero calcsize; the check below guards that.
        if self._i2c is None:
            return None
        try:
            size = struct.calcsize(reg_format)
        except ValueError:  # malformed reg_format
            return None
        raw = self._readfrom_mem(self._i2c, address, reg_addr, size, addrsize)
        try:
            unpacked = struct.unpack(reg_format, memoryview(raw))
        except ValueError:  # malformed reg_format
            return None
        if not unpacked:
            return None
        value = unpacked[0]
        if isinstance(value, (int, float, bytes)):
            return value
        return None

    def set_register_struct(
        self,
        address: int,
        reg_addr: int,
        reg_format: str,
        value: int | float | bytes | bytearray,
        addrsize: int | None = None,
    ) -> None:
        # Byte order comes from reg_format's own prefix, matching get_register_struct(). Unlike
        # CPython, struct.pack here silently truncates/zero-pads a value that doesn't fit
        # reg_format instead of raising; it raises TypeError (not ValueError) for a type
        # mismatch (e.g. int value against a bytes-format like "4s") - both caught below.
        if self._i2c is None:
            return
        try:
            packed = struct.pack(reg_format, value)
        except (ValueError, TypeError):
            return
        self._writeto_mem(self._i2c, address, reg_addr, packed, addrsize)


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
        # end=None passes straight through; I2C.readfrom_into() already defaults it to len(buf).
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
        buffer_out: bytes | bytearray,
        buffer_in: bytearray,
        out_start: int = 0,
        out_end: int | None = None,
        in_start: int = 0,
        in_end: int | None = None,
        out_stop: bool = True,
        in_stop: bool = True,
    ) -> None:
        self.i2c.writeto_then_readfrom(
            self.device_address,
            buffer_out,
            buffer_in,
            out_start=out_start,
            out_end=out_end,
            in_start=in_start,
            in_end=in_end,
            out_stop=out_stop,
            in_stop=in_stop,
        )

    async def get_bits(
        self,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> int | None:
        return self.i2c.get_bits(
            self.device_address, num_bits, reg_addr, start_bit, reg_width, lsb_first, addrsize
        )

    async def set_bits(
        self,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        value: int,
        reg_width: int = 1,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> None:
        self.i2c.set_bits(
            self.device_address,
            num_bits,
            reg_addr,
            start_bit,
            value,
            reg_width,
            lsb_first,
            addrsize,
        )

    async def get_register_struct(
        self, reg_addr: int, reg_format: str, addrsize: int | None = None
    ) -> int | float | bytes | None:
        return self.i2c.get_register_struct(self.device_address, reg_addr, reg_format, addrsize)

    async def set_register_struct(
        self,
        reg_addr: int,
        reg_format: str,
        value: int | float | bytes | bytearray,
        addrsize: int | None = None,
    ) -> None:
        self.i2c.set_register_struct(self.device_address, reg_addr, reg_format, value, addrsize)

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
