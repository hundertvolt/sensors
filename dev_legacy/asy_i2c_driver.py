from uasyncio import Lock
import asyncio
from base_classes import Lockable
from machine import I2C as _I2C
from machine import Pin
import struct
from typing import Literal, List


class I2C:
    def __init__(self, port_id: int, scl_pin: int, sda_pin: int, frequency: int = 100000) -> None:
        self._i2c: _I2C | None = None
        self.async_lock = Lock()
        self.init(port_id, scl_pin, sda_pin, frequency)

    def init(self, port_id: int, scl_pin: int, sda_pin: int, frequency: int) -> None:
        """Initialization"""
        self.deinit()
        self._i2c = _I2C(port_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=frequency)

    def deinit(self) -> None:
        """Deinitialization"""
        try:
            self._i2c = None
        except AttributeError:
            pass

    def scan(self) -> List[int]:
        """Scan for attached devices"""
        if self._i2c is None:
            return []
        return self._i2c.scan()

    def readfrom_into(
        self,
        address: int,
        buffer: bytearray,
        start: int = 0,
        end: int | None = None,
        stop: bool = True,
    ) -> None:
        """Read from a device at specified address into a buffer"""
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
    ) -> int:
        """Write to a device at specified address from a buffer"""
        if self._i2c is None:
            return 0
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
        """Write data from buffer_out to an address and then
        read data from an address and into buffer_in
        """
        self.writeto(address, buffer_out, out_start, out_end, stop=stop)
        self.readfrom_into(address, buffer_in, in_start, in_end, stop=stop)

    def get_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        lsb_first: bool = True,
    ) -> int:
        if self._i2c is None:
            return 0
        mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)
        reg = 0
        if lsb_first:
            order = range(len(mem_value) - 1, -1, -1)
        else:
            order = range(0, len(mem_value), 1)
        for i in order:
            reg = (reg << 8) | mem_value[i]
        return (reg & (((1 << num_bits) - 1) << start_bit)) >> start_bit

    def set_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        value: int,
        reg_width: int = 1,
        lsb_first: bool = True,
        endian: Literal["little", "big"] = "little",
    ) -> None:
        if self._i2c is None:
            return
        mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)
        reg = 0
        if lsb_first:
            order = range(len(mem_value) - 1, -1, -1)
        else:
            order = range(0, len(mem_value), 1)
        for i in order:
            reg = (reg << 8) | mem_value[i]
        reg &= ~(((1 << num_bits) - 1) << start_bit)
        value <<= start_bit
        reg |= value
        self._i2c.writeto_mem(address, reg_addr, reg.to_bytes(reg_width, endian))

    def get_register_struct(
        self, address: int, reg_addr: int, reg_format: str
    ) -> int | float | bytes | bool | None:
        if self._i2c is None:
            return None
        # struct.unpack declared to return Any, but int | float | bytes | bool are possible
        value = struct.unpack(
            reg_format,
            memoryview(self._i2c.readfrom_mem(address, reg_addr, struct.calcsize(reg_format))),
        )[0]
        if isinstance(value, (int, float, bytes, bool)):
            return value
        return None

    def set_register_struct(
        self,
        address: int,
        reg_addr: int,
        reg_format: str,
        value: int,
        endian: Literal["little", "big"] = "little",
    ) -> None:
        if self._i2c is None:
            return
        self._i2c.writeto_mem(
            address, reg_addr, value.to_bytes(struct.calcsize(reg_format), endian)
        )


class I2CDevice(Lockable):
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
        if end is None:
            end = len(buf)
        self.i2c.readfrom_into(self.device_address, buf, start=start, end=end)

    async def write(
        self,
        buf: bytes | bytearray | str,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        if end is None:
            end = len(buf)
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
        if out_end is None:
            out_end = len(out_buffer)
        if in_end is None:
            in_end = len(in_buffer)

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
    ) -> int:
        return self.i2c.get_bits(
            self.device_address, num_bits, reg_addr, start_bit, reg_width, lsb_first
        )

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

    async def get_register_struct(
        self, reg_addr: int, reg_format: str
    ) -> int | float | bytes | bool | None:
        return self.i2c.get_register_struct(self.device_address, reg_addr, reg_format)

    async def set_register_struct(self, reg_addr: int, reg_format: str, value: int) -> None:
        self.i2c.set_register_struct(self.device_address, reg_addr, reg_format, value)

    async def __probe_for_device(self) -> None:
        """
        Try to read a byte from an address,
        if you get an OSError it means the device is not there
        or that the device does not support these means of probing
        """
        try:
            await asyncio.sleep(0.1)
            self.i2c.writeto(self.device_address, b"")
        except OSError:
            raise ValueError("No I2C device at address: 0x%x" % self.device_address)
        finally:
            await asyncio.sleep(0.1)
