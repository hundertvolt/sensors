"""Async wrapper around machine.I2C: bus-level primitives (I2C) plus a per-device, lock-scoped
wrapper (I2CDevice) used by every I2C sensor driver.
"""
# A non-hardware failure (uninitialized bus, out-of-range field, malformed format) is None or False, never a
# raise; a real OSError propagates, and one-time setup (__init__/init(), the probe) may raise.
# clear()/recover() are the ladder's bus rungs, under the bus lock (SPECIFICATION.md F.2).

import asyncio
import errno
import struct
import time

from machine import I2C as _I2C
from machine import Pin
from micropython import const

from asy_base_classes import COUNTER_CAP, Lockable

# Covers every read the drivers actually make (BMP3XX's 21-byte calibration block is the largest;
# the hot paths are 1-6 bytes). A larger read still works - it falls back to the allocating call.
_SCRATCH_SIZE = const(32)
# @tunable i2c.probe_settle_s = 0.1
_PROBE_SETTLE_S = const(0.1)  # the settle before and after _probe_for_device()'s zero-byte write
# @tunable i2c.clear_half_period_us = 5
_CLEAR_HALF_PERIOD_US = const(5)  # 100 kHz clock-out, the SCD30's ceiling (Interface Description p.2)
_CLEAR_PULSES = const(9)  # one byte plus its acknowledge: an I2C protocol constant
_MAX_ADDRSIZE = const(32)  # machine.I2C's own addrsize ceiling, in bits (fill_memaddr_buf())
_DEFAULT_TIMEOUT_US = const(50000)  # rp2's machine.I2C default timeout (Part F.5.1): the SCL-release bound when none is configured
# Bus-recovery status bits returned by clear()/recover() and the boot clear (SPECIFICATION.md C.3)
_REC_SDA_LOW = const(1)
_REC_SDA_STUCK = const(2)
_REC_SCL_HELD = const(4)
_REC_NO_CONTROLLER = const(8)


def _clear_bus(scl_pin: int, sda_pin: int, timeout_us: int) -> int:
    # Frees a slave holding SDA mid-byte: up to nine SCL pulses then a STOP, before the controller
    # owns the pins (owner, 2026-09-30: clear at boot; F.2). Synchronous on purpose: it runs once per
    # bus inside the fed boot batch, before any task exists.
    sda = Pin(sda_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    scl = Pin(scl_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    if not _scl_released_sync(scl, timeout_us):  # as the runtime clear: a held SCL is no free bus
        return _REC_SCL_HELD
    if sda.value():
        return 0
    status = _REC_SDA_LOW
    for _ in range(_CLEAR_PULSES):
        scl.value(0)
        time.sleep_us(_CLEAR_HALF_PERIOD_US)
        scl.value(1)
        if not _scl_released_sync(scl, timeout_us):
            return status | _REC_SCL_HELD
        time.sleep_us(_CLEAR_HALF_PERIOD_US)
        if sda.value():
            break
    else:
        status |= _REC_SDA_STUCK
    scl.value(0)  # the STOP: SDA driven low while SCL is low, SCL released, then SDA released
    sda.value(0)
    time.sleep_us(_CLEAR_HALF_PERIOD_US)
    scl.value(1)
    if not _scl_released_sync(scl, timeout_us):
        sda.value(1)  # with SCL low this is no bus condition, only the line let go
        return status | _REC_SCL_HELD
    time.sleep_us(_CLEAR_HALF_PERIOD_US)
    sda.value(1)
    return status


async def _clear_bus_awaiting(scl_pin: int, sda_pin: int, timeout_us: int) -> int:
    # The runtime twin of _clear_bus(): the same steps and constants, each SCL wait awaited so a
    # stretching slave never holds the loop (Part F.3). A change to one is made to both.
    sda = Pin(sda_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    scl = Pin(scl_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    if not await _scl_released(scl, timeout_us):
        return _REC_SCL_HELD
    if sda.value():
        return 0
    status = _REC_SDA_LOW
    for _ in range(_CLEAR_PULSES):
        scl.value(0)
        time.sleep_us(_CLEAR_HALF_PERIOD_US)
        scl.value(1)
        if not await _scl_released(scl, timeout_us):
            return status | _REC_SCL_HELD
        time.sleep_us(_CLEAR_HALF_PERIOD_US)
        if sda.value():
            break
    else:
        status |= _REC_SDA_STUCK
    scl.value(0)
    sda.value(0)
    time.sleep_us(_CLEAR_HALF_PERIOD_US)
    scl.value(1)
    if not await _scl_released(scl, timeout_us):
        sda.value(1)
        return status | _REC_SCL_HELD
    time.sleep_us(_CLEAR_HALF_PERIOD_US)
    sda.value(1)
    return status


async def _scl_released(scl: Pin, timeout_us: int) -> bool:
    # A slave may stretch the clock: a released SCL that still reads low has clocked nothing yet.
    start = time.ticks_us()
    while not scl.value():
        if time.ticks_diff(time.ticks_us(), start) >= timeout_us:
            return False
        await asyncio.sleep_ms(1)
    return True


def _scl_released_sync(scl: Pin, timeout_us: int) -> bool:
    # _scl_released() for the boot clear, which runs before any task exists.
    start = time.ticks_us()
    while not scl.value():
        if time.ticks_diff(time.ticks_us(), start) >= timeout_us:
            return False
    return True


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
        self.bus_lock = asyncio.Lock()  # serialises the I2C peripheral: every device session on this bus holds it
        # One long-lived read buffer per bus, not a fresh bytes per register read (Part I). Sharing
        # it across this bus's devices is sound only because every method fills and decodes it with
        # no await between, and no Timer/Pin.irq callback here touches I2C - both checked (Part G.2).
        self._scratch = bytearray(_SCRATCH_SIZE)
        self.recoveries = 0  # a wrap-by-design sequence: compared for equality only
        self._boot_clear_status = _clear_bus(scl_pin, sda_pin, _DEFAULT_TIMEOUT_US if timeout is None else timeout)
        self.init(port_id, scl_pin, sda_pin, frequency, timeout)

    @staticmethod
    def _bitfield_range_ok(num_bits: int, start_bit: int, reg_width: int) -> bool:
        # Shared range guard for get_bits()/set_bits(): field must fit inside reg_width bytes.
        return num_bits > 0 and start_bit >= 0 and reg_width > 0 and start_bit + num_bits <= reg_width * 8

    @staticmethod
    def _bitmask(num_bits: int, start_bit: int) -> int:
        return ((1 << num_bits) - 1) << start_bit

    @staticmethod
    def _bytes_to_int(mem_value: bytes | memoryview, *, lsb_first: bool) -> int:
        # Shared byte-order reconstruction for get_bits()/set_bits(): lsb_first says whether
        # mem_value[0] is the least- or most-significant byte.
        reg = 0
        order = range(len(mem_value) - 1, -1, -1) if lsb_first else range(len(mem_value))
        for i in order:
            reg = (reg << 8) | mem_value[i]
        return reg

    async def _clear_locked(self) -> int:
        # The runtime bus clear, under a bus-lock hold the caller owns: wait for SCL, clear, then hand
        # both pins back to the controller's I2C function with their pull-ups (no block re-init).
        scl_pin, sda_pin, timeout = self._args[1], self._args[2], self._args[4]
        status = await _clear_bus_awaiting(scl_pin, sda_pin, _DEFAULT_TIMEOUT_US if timeout is None else timeout)
        Pin(scl_pin, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
        Pin(sda_pin, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
        return status

    @staticmethod
    def _fill_reg_addr(buf: bytearray, reg_addr: int, addrsize: int | None) -> int:
        # The register address as machine.I2C sends it (fill_memaddr_buf()): addrsize // 8 bytes, most
        # significant first, and its ValueError for an addrsize it refuses. Returns the byte count.
        bits = 8 if addrsize is None else addrsize
        if bits & 7 or not 0 <= bits <= _MAX_ADDRSIZE:
            raise ValueError("invalid addrsize")
        n = bits // 8
        for i in range(n):
            buf[i] = (reg_addr >> (8 * (n - 1 - i))) & 0xFF
        return n

    def _read_into_scratch(self, bus: _I2C, address: int, reg_addr: int, nbytes: int, addrsize: int | None) -> memoryview:
        # Returns a view over the first nbytes of the shared buffer - valid only until the next read
        # on this bus, so a caller that keeps the value must copy it out (struct.unpack already does).
        buf = self._scratch if nbytes <= len(self._scratch) else bytearray(nbytes)  # oversized read: allocate rather than refuse
        view = memoryview(buf)[:nbytes]
        # Not readfrom_mem_into(): it returns with the buffer untouched when the device NACKs the register
        # byte, so stale bytes would decode as fresh; here that is an EIO (SPECIFICATION.md F.5.1).
        n = self._fill_reg_addr(self._scratch, reg_addr, addrsize)
        self._write_all(bus, address, memoryview(self._scratch)[:n], stop=False)
        bus.readfrom_into(address, view)
        return view

    @staticmethod
    def _write_all(bus: _I2C, address: int, buf: bytes | bytearray | memoryview, *, stop: bool) -> int:
        # machine.I2C reports a data byte the device NACKed only as a short ACK count, so a short count is
        # an EIO here, as a NACKed address already is (SPECIFICATION.md F.5.1).
        n = bus.writeto(address, buf, stop)
        if n != len(buf):
            if not stop:
                try:  # the STOP read_mem() itself sends after a short no-stop write, its result ignored as there
                    bus.writeto(address, b"", True)
                except OSError:
                    pass  # the EIO below is the failure the caller reports
            raise OSError(errno.EIO)
        return n

    def _write_buffer(self, reg_addr: int, payload_len: int, addrsize: int | None) -> memoryview:
        # The register address filled in, room for payload_len bytes after it: a view of the scratch, or
        # of a fresh buffer when they do not fit (as an oversized read allocates). No await may follow.
        n = self._fill_reg_addr(self._scratch, reg_addr, addrsize)
        if n + payload_len <= len(self._scratch):
            return memoryview(self._scratch)[: n + payload_len]
        buf = bytearray(n + payload_len)
        buf[:n] = memoryview(self._scratch)[:n]
        return memoryview(buf)

    def get_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        *,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> int | None:
        # Reads an arbitrary bit-field out of a reg_width-byte register.
        if self._i2c is None or not self._bitfield_range_ok(num_bits, start_bit, reg_width):
            return None
        mem_value = self._read_into_scratch(self._i2c, address, reg_addr, reg_width, addrsize)
        reg = self._bytes_to_int(mem_value, lsb_first=lsb_first)
        return (reg & self._bitmask(num_bits, start_bit)) >> start_bit

    def get_register_bytes(self, address: int, reg_addr: int, length: int, addrsize: int | None = None) -> bytes | None:
        # Exactly length bytes, copied out of the scratch; None for no bus or length <= 0.
        if self._i2c is None or length <= 0:
            return None
        return bytes(self._read_into_scratch(self._i2c, address, reg_addr, length, addrsize))

    def get_register_struct(
        self, address: int, reg_addr: int, reg_format: str, addrsize: int | None = None,
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
        raw = self._read_into_scratch(self._i2c, address, reg_addr, size, addrsize)
        try:
            unpacked = struct.unpack(reg_format, raw)
        except ValueError:  # malformed reg_format
            return None
        if not unpacked:
            return None
        value = unpacked[0]
        if isinstance(value, (int, float, bytes)):
            return value
        return None

    def set_bits(
        self,
        address: int,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        value: int,
        reg_width: int = 1,
        *,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> bool:
        # Read-modify-write counterpart of get_bits(). Byte order is derived from lsb_first
        # alone. value is masked to num_bits before being shifted in, so an out-of-range value
        # can't corrupt the bits just above the intended field.
        if self._i2c is None or not self._bitfield_range_ok(num_bits, start_bit, reg_width):
            return False
        mem_value = self._read_into_scratch(self._i2c, address, reg_addr, reg_width, addrsize)
        reg = self._bytes_to_int(mem_value, lsb_first=lsb_first)
        reg &= ~self._bitmask(num_bits, start_bit)
        reg |= (value & self._bitmask(num_bits, 0)) << start_bit
        # Register address then value in one buffer, one writeto(): the transfer writeto_mem() makes.
        buf = self._write_buffer(reg_addr, reg_width, addrsize)
        n = len(buf) - reg_width
        for i in range(reg_width):
            buf[n + i] = (reg >> (8 * (i if lsb_first else reg_width - 1 - i))) & 0xFF
        self._write_all(self._i2c, address, buf, stop=True)
        return True

    def set_register_struct(
        self,
        address: int,
        reg_addr: int,
        reg_format: str,
        value: float | bytes | bytearray,
        addrsize: int | None = None,
    ) -> bool:
        # Byte order comes from reg_format's own prefix, matching get_register_struct(). Unlike
        # CPython, struct.pack silently truncates/zero-pads a value that doesn't fit reg_format
        # instead of raising; a type mismatch (e.g. int vs. "4s") raises TypeError, both caught below.
        if self._i2c is None:
            return False
        try:
            size = struct.calcsize(reg_format)
        except ValueError:  # malformed reg_format
            return False
        buf = self._write_buffer(reg_addr, size, addrsize)
        n = len(buf) - size
        try:
            struct.pack_into(reg_format, buf, n, value)
        except (TypeError, ValueError):
            return False
        self._write_all(self._i2c, address, buf, stop=True)
        return True

    async def clear(self) -> int:
        # The bus-clear rung: nine SCL pulses and a STOP at most, under the bus lock. Returns _REC_* bits.
        async with self.bus_lock:
            status = await self._clear_locked()
            self.recoveries = self.recoveries + 1 if self.recoveries < COUNTER_CAP else 0  # a wrap-by-design sequence: compared for equality only
        return status

    def deinit(self) -> bool:
        # machine.I2C.deinit() does NOT deactivate the rp2 bus - forwarded for portability, it cannot
        # fail at the pinned version (Part F.5.1), so this returns True; dropping self._i2c is what
        # makes the wrapper report the bus unavailable.
        if self._i2c is not None:
            self._i2c.deinit()
            self._i2c = None
        return True

    def init(
        self,
        port_id: int,
        scl_pin: int,
        sda_pin: int,
        frequency: int,
        timeout: int | None = None,
    ) -> None:
        # deinit() first, so a re-init goes through the same "bus unavailable" state a caller-visible
        # deinit() produces rather than swapping self._i2c under live readers. timeout=None omits the
        # kwarg instead of duplicating machine.I2C's own default, which could then drift.
        self._args = (port_id, scl_pin, sda_pin, frequency, timeout)
        self.deinit()
        if timeout is None:
            self._i2c = _I2C(port_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=frequency)
        else:
            self._i2c = _I2C(port_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=frequency, timeout=timeout)

    def readfrom_into(
        self,
        address: int,
        buf: bytearray,
        start: int = 0,
        end: int | None = None,
        *,
        stop: bool = True,
    ) -> bool:
        # machine.I2C.readfrom_into(), with a start/end slice instead of a pre-sliced buffer.
        if self._i2c is None:
            return False
        if end is None:
            end = len(buf)
        self._i2c.readfrom_into(address, memoryview(buf)[start:end], stop)
        return True

    async def recover(self) -> int:
        # The controller rung: the bus clear, then a re-construction with the stored arguments - rp2's only
        # controller re-init (Part F.5.1) - under one bus-lock hold. _REC_NO_CONTROLLER leaves no bus.
        async with self.bus_lock:
            status = await self._clear_locked()
            try:
                self.init(*self._args)
            except (OSError, ValueError):
                status |= _REC_NO_CONTROLLER
            self.recoveries = self.recoveries + 1 if self.recoveries < COUNTER_CAP else 0  # a wrap-by-design sequence: compared for equality only
        return status

    def scan(self) -> list[int] | None:
        # machine.I2C.scan(): every ACKing address in 0x08-0x77.
        if self._i2c is None:
            return None
        return self._i2c.scan()

    def take_boot_clear_status(self) -> int:
        # The construction-time clear's _REC_* bits, once: the first reader on the bus reports them.
        status = self._boot_clear_status
        self._boot_clear_status = 0
        return status

    def writeto(
        self,
        address: int,
        buf: bytes | bytearray | str,
        start: int = 0,
        end: int | None = None,
        *,
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
        return self._write_all(self._i2c, address, memoryview(buf)[start:end], stop=stop)

    def writeto_then_readfrom(
        self,
        address: int,
        buffer_out: bytes | bytearray,
        buffer_in: bytearray,
        *,
        out_stop: bool = True,
        in_stop: bool = True,
    ) -> bool:
        # Not a native machine.I2C primitive - a write then a read via writeto()/readfrom_into(); out_stop/in_stop are
        # independent so a repeated-start read is expressible (pass out_stop=False). The combined form takes whole
        # buffers; pass a memoryview slice for a region (Part G.2 buffer handoff).
        return self.writeto(address, buffer_out, stop=out_stop) is not None and self.readfrom_into(address, buffer_in, stop=in_stop)


class I2CDevice(Lockable):
    # Binds an I2C bus to one device address and the bus's shared asyncio lock, so consecutive
    # transactions from different devices on the same bus can't interleave.
    def __init__(self, i2c: I2C, device_address: int) -> None:
        self.i2c = i2c
        super().__init__(session_lock=self.i2c.bus_lock)
        self.device_address = device_address

    async def _probe_for_device(self) -> None:
        # Try to write zero bytes to the device address: an OSError means no device ACKed it.
        # writeto() returning None (bus not initialized, e.g. deinit() was called on the shared
        # I2C instance) is a distinct failure from "no device" and gets its own message.
        try:
            await asyncio.sleep(_PROBE_SETTLE_S)
            acked = self.i2c.writeto(self.device_address, b"")
        except OSError:
            raise ValueError(f"no I2C device at address: {self.device_address:#x}") from None
        finally:
            await asyncio.sleep(_PROBE_SETTLE_S)
        if acked is None:
            raise RuntimeError("I2C bus not initialized")

    async def get_bits(
        self,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        reg_width: int = 1,
        *,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> int | None:
        return self.i2c.get_bits(
            self.device_address, num_bits, reg_addr, start_bit, reg_width, lsb_first=lsb_first, addrsize=addrsize,
        )

    async def get_register_bytes(self, reg_addr: int, length: int, addrsize: int | None = None) -> bytes | None:
        return self.i2c.get_register_bytes(self.device_address, reg_addr, length, addrsize)

    async def get_register_struct(
        self, reg_addr: int, reg_format: str, addrsize: int | None = None,
    ) -> int | float | bytes | None:
        return self.i2c.get_register_struct(self.device_address, reg_addr, reg_format, addrsize)

    async def set_bits(
        self,
        num_bits: int,
        reg_addr: int,
        start_bit: int,
        value: int,
        reg_width: int = 1,
        *,
        lsb_first: bool = True,
        addrsize: int | None = None,
    ) -> bool:
        return self.i2c.set_bits(
            self.device_address,
            num_bits,
            reg_addr,
            start_bit,
            value,
            reg_width,
            lsb_first=lsb_first,
            addrsize=addrsize,
        )

    async def set_register_struct(
        self,
        reg_addr: int,
        reg_format: str,
        value: float | bytes | bytearray,
        addrsize: int | None = None,
    ) -> bool:
        return self.i2c.set_register_struct(self.device_address, reg_addr, reg_format, value, addrsize)

    async def readinto(
        self,
        buf: bytearray,
        start: int = 0,
        end: int | None = None,
    ) -> bool:
        # end=None passes straight through; I2C.readfrom_into() already defaults it to len(buf).
        return self.i2c.readfrom_into(self.device_address, buf, start=start, end=end)

    async def setup(self) -> bool:
        await self._probe_for_device()
        return True

    async def write(
        self,
        buf: bytes | bytearray | str,
        start: int = 0,
        end: int | None = None,
    ) -> bool:
        return self.i2c.writeto(self.device_address, buf, start=start, end=end) is not None

    async def write_then_readinto(
        self,
        buffer_out: bytes | bytearray,
        buffer_in: bytearray,
        *,
        out_stop: bool = True,
        in_stop: bool = True,
    ) -> bool:
        return self.i2c.writeto_then_readfrom(self.device_address, buffer_out, buffer_in, out_stop=out_stop, in_stop=in_stop)
