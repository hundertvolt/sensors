import asyncio
from machine import I2C as _I2C
from machine import Pin
import struct

class I2C():
    def __init__(self, portId, sclPin, sdaPin, frequency=100000):
        self.init(portId, sclPin, sdaPin, frequency)
        self.async_lock = asyncio.Lock()

    def init(self, portId, sclPin, sdaPin, frequency):
        """Initialization"""
        self.deinit()
        self._i2c = _I2C(portId, sda=Pin(sdaPin), scl=Pin(sclPin), freq=frequency)

    def deinit(self):
        """Deinitialization"""
        try:
            del self._i2c
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
        return False

    def scan(self):
        """Scan for attached devices"""
        return self._i2c.scan()

    def readfrom_into(self, address, buffer, *, start=0, end=None):
        """Read from a device at specified address into a buffer"""
        if start != 0 or end is not None:
            if end is None:
                end = len(buffer)
            buffer = memoryview(buffer)[start:end]
        return self._i2c.readfrom_into(address, buffer, True)

    def writeto(self, address, buffer, *, start=0, end=None):
        """Write to a device at specified address from a buffer"""
        if isinstance(buffer, str):
            buffer = bytes([ord(x) for x in buffer])
        if start != 0 or end is not None:
            if end is None:
                return self._i2c.writeto(address, memoryview(buffer)[start:], True)
            return self._i2c.writeto(address, memoryview(buffer)[start:end], True)
        return self._i2c.writeto(address, buffer, True)

    def writeto_then_readfrom(
        self,
        address,
        buffer_out,
        buffer_in,
        *,
        out_start=0,
        out_end=None,
        in_start=0,
        in_end=None,
        stop=False,
    ):
        """Write data from buffer_out to an address and then
        read data from an address and into buffer_in
        """
        if out_end:
            self.writeto(address, buffer_out[out_start:out_end], stop=stop)
        else:
            self.writeto(address, buffer_out[out_start:], stop=stop)

        if not in_end:
            in_end = len(buffer_in)
        read_buffer = memoryview(buffer_in)[in_start:in_end]
        self.readfrom_into(address, read_buffer, stop=stop)

    def get_bits(self, address, num_bits, reg_addr, start_bit, reg_width=1, lsb_first=True):
        mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)
        reg = 0
        order = range(len(mem_value) - 1, -1, -1)
        if not lsb_first:
            order = reversed(order)
        for i in order:
            reg = (reg << 8) | mem_value[i]
        return (reg & (((1 << num_bits) - 1) << start_bit)) >> start_bit

    def set_bits(self, address, num_bits, reg_addr, start_bit, value, reg_width=1, lsb_first=True, endian="little"):
        mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)
        reg = 0
        order = range(len(mem_value) - 1, -1, -1)
        if not lsb_first:
            order = reversed(order)
        for i in order:
            reg = (reg << 8) | mem_value[i]
        reg &= ~(((1 << num_bits) - 1) << start_bit)
        value <<= start_bit
        reg |= value
        self._i2c.writeto_mem(address, reg_addr, reg.to_bytes(reg_width, endian))

    def get_register_struct(self, address, reg_addr, reg_format):
        return struct.unpack(reg_format, memoryview(self._i2c.readfrom_mem(address, reg_addr, struct.calcsize(reg_format))))[0]

    def set_register_struct(self, address, reg_addr, reg_format, value, endian="little"):
        self._i2c.writeto_mem(address, reg_addr, value.to_bytes(struct.calcsize(reg_format), endian))


class I2CDevice:
    """
    Represents a single I2C device and manages locking the bus and the device
    address.

    :param ~busio.I2C i2c: The I2C bus the device is on
    :param int device_address: The 7 bit device address
    :param bool probe: Probe for the device upon object creation, default is true

    .. note:: This class is **NOT** built into CircuitPython. See
      :ref:`here for install instructions <bus_device_installation>`.

    Example:

    .. code-block:: python

        import busio
        from board import *
        from adafruit_bus_device.i2c_device import I2CDevice

        with busio.I2C(SCL, SDA) as i2c:
            device = I2CDevice(i2c, 0x70)
            bytes_read = bytearray(4)
            with device:
                device.readinto(bytes_read)
            # A second transaction
            with device:
                device.write(bytes_read)
    """

    def __init__(self, i2c: I2C, device_address: int) -> None:
        self.i2c = i2c
        self.device_address = device_address

    async def setup(self, probe: bool = True) -> None:
        if probe:
            await self.__probe_for_device()

    async def readinto(
        self, buf: WriteableBuffer, *, start: int = 0, end: Optional[int] = None) -> None:
        """
        Read into ``buf`` from the device. The number of bytes read will be the
        length of ``buf``.

        If ``start`` or ``end`` is provided, then the buffer will be sliced
        as if ``buf[start:end]``. This will not cause an allocation like
        ``buf[start:end]`` will so it saves memory.

        :param ~WriteableBuffer buffer: buffer to write into
        :param int start: Index to start writing at
        :param int end: Index to write up to but not include; if None, use ``len(buf)``
        """
        if end is None:
            end = len(buf)
        self.i2c.readfrom_into(self.device_address, buf, start=start, end=end)

    async def write(
        self, buf: ReadableBuffer, *, start: int = 0, end: Optional[int] = None) -> None:
        """
        Write the bytes from ``buffer`` to the device, then transmit a stop
        bit.

        If ``start`` or ``end`` is provided, then the buffer will be sliced
        as if ``buffer[start:end]``. This will not cause an allocation like
        ``buffer[start:end]`` will so it saves memory.

        :param ~ReadableBuffer buffer: buffer containing the bytes to write
        :param int start: Index to start writing from
        :param int end: Index to read up to but not include; if None, use ``len(buf)``
        """
        if end is None:
            end = len(buf)
        self.i2c.writeto(self.device_address, buf, start=start, end=end)

    async def write_then_readinto(
        self,
        out_buffer: ReadableBuffer,
        in_buffer: WriteableBuffer,
        *,
        out_start: int = 0,
        out_end: Optional[int] = None,
        in_start: int = 0,
        in_end: Optional[int] = None
    ) -> None:
        """
        Write the bytes from ``out_buffer`` to the device, then immediately
        reads into ``in_buffer`` from the device. The number of bytes read
        will be the length of ``in_buffer``.

        If ``out_start`` or ``out_end`` is provided, then the output buffer
        will be sliced as if ``out_buffer[out_start:out_end]``. This will
        not cause an allocation like ``buffer[out_start:out_end]`` will so
        it saves memory.

        If ``in_start`` or ``in_end`` is provided, then the input buffer
        will be sliced as if ``in_buffer[in_start:in_end]``. This will not
        cause an allocation like ``in_buffer[in_start:in_end]`` will so
        it saves memory.

        :param ~ReadableBuffer out_buffer: buffer containing the bytes to write
        :param ~WriteableBuffer in_buffer: buffer containing the bytes to read into
        :param int out_start: Index to start writing from
        :param int out_end: Index to read up to but not include; if None, use ``len(out_buffer)``
        :param int in_start: Index to start writing at
        :param int in_end: Index to write up to but not include; if None, use ``len(in_buffer)``
        """
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

    async def get_bits(self, num_bits, reg_addr, start_bit, reg_width=1, lsb_first=True):
        return self.i2c.get_bits(self.device_address, num_bits, reg_addr, start_bit, reg_width, lsb_first)

    async def set_bits(self, num_bits, reg_addr, start_bit, value, reg_width=1, lsb_first=True):
        self.i2c.set_bits(self.device_address, num_bits, reg_addr, start_bit, value, reg_width, lsb_first)

    async def get_register_struct(self, reg_addr, reg_format):
        return self.i2c.get_register_struct(self.device_address, reg_addr, reg_format)

    async def set_register_struct(self, reg_addr, reg_format, value):
       self.i2c.set_register_struct(self.device_address, reg_addr, reg_format, value)

    async def __aenter__(self) -> "I2CDevice":
        await self.i2c.async_lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[type]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        try:
            self.i2c.async_lock.release()
        except RuntimeError:   # in case it's already released somehow
            pass
        return False

    async def __probe_for_device(self) -> None:
        """
        Try to read a byte from an address,
        if you get an OSError it means the device is not there
        or that the device does not support these means of probing
        """
        await self.i2c.async_lock.acquire()
        try:
            self.i2c.writeto(self.device_address, b"")
        except OSError:
            # some OS's dont like writing an empty bytesting...
            # Retry by reading a byte
            try:
                result = bytearray(1)
                self.i2c.readfrom_into(self.device_address, result)
            except OSError:
                # pylint: disable=raise-missing-from
                raise ValueError("No I2C device at address: 0x%x" % self.device_address)
                # pylint: enable=raise-missing-from
        finally:
            self.i2c.async_lock.release()
