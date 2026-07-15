"""Test-only fake `machine` module, per BACKLOG.md's mocking-boundary plan: mock only the raw
I2C/SPI bus-transaction level (readfrom_mem/writeto_mem/readfrom_into/writeto/scan/deinit for
I2C; write/readinto/write_readinto/deinit for SPI), so asy_i2c_driver.py's/asy_spi_driver.py's
own logic (bit-packing, byte order, buffer slicing, locking, error paths, CS-pin sequencing) runs
for real against this fake instead of unavailable real hardware - the MicroPython Unix port's own
`machine` module has no I2C/SPI/real Pin (confirmed directly: PinBase/Signal/mem8/mem16/mem32/
idle/time_pulse_us only). Only implements what these two drivers' own imports need; not a
general-purpose machine stub.

Real RP2040 I2C error codes (confirmed against ports/rp2/machine_i2c.c, not guessed): the
hardware I2C driver only ever raises OSError(errno.EIO) - covers a NAK/no response and any other
general bus fault, which is also what a real multi-master arbitration loss would surface as on
this port - or OSError(errno.ETIMEDOUT), the Pico SDK's own bus-busy/clock-stretch timeout. There
is no distinct errno for "arbitration lost" on this port; both fold into one of the two above.
`nak_addresses`/`busy` below model exactly those two real conditions.

Real RP2040 SPI error behavior (confirmed against extmod/machine_spi.c and ports/rp2/
machine_spi.c, not guessed): unlike I2C, SPI has no ACK/NAK concept, and the rp2 hardware SPI
transfer path (spi_write_blocking()/spi_write_read_blocking()) has no error return at all - once
constructed, `write()`/`readinto()` genuinely cannot raise anything. There is therefore no
NAK/busy-style fault-injection surface to model for those two methods, unlike `I2C` below.
`write_readinto()` is the one exception: it raises a real `ValueError("buffers must be the same
length")` (mp_machine_spi_write_readinto(), shared by hardware and soft SPI alike) when its two
buffers differ in length - modeled directly below since it's deterministic from the buffers a
test passes in, not something that needs fault injection to trigger.
"""

import errno


class Pin:
    IN = 0
    OUT = 1

    def __init__(self, id: int, mode: int = -1) -> None:
        self.id = id
        self.mode = mode
        self._value = 0

    def init(self, mode: int = -1, pull: int = -1) -> None:
        # Real machine.Pin.init(): omitted/-1 args leave the current setting untouched.
        if mode != -1:
            self.mode = mode

    def value(self, x: object = None) -> int | None:
        # Real rp2 Pin.value(): reads back gpio_get() even for an OUT pin (confirmed against
        # ports/rp2/machine_pin.c) - not "undefined" the way the cross-port docs hedge.
        if x is None:
            return self._value
        self._value = 1 if x else 0
        return None


class I2C:
    # Registers are a plain dict of (address, reg_addr) -> bytearray, seeded directly by a test
    # via .registers before exercising get_bits/set_bits/get_register_struct/set_register_struct
    # - a real round trip through readfrom_mem/writeto_mem, not a canned return value.
    def __init__(self, id: int, *, scl: Pin, sda: Pin, freq: int = 400000, timeout: int = 50000) -> None:
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.timeout = timeout
        self.deinit_called = False
        self.deinit_count = 0
        self.log: list[tuple] = []
        self.registers: dict[tuple[int, int], bytearray] = {}
        self.nak_addresses: set[int] = set()  # convenience: EIO (no ACK) on every op to this address
        self.busy = False  # convenience: ETIMEDOUT (bus/clock-stretch timeout) on every op, any address
        self._faults: dict[str, list[Exception]] = {}  # op name -> FIFO queue, one exception per matching call

    def inject_fault(self, op: str, exc: Exception, times: int = 1) -> None:
        # Queues `exc` to be raised on the next `times` calls to the named op (readfrom_into,
        # writeto, readfrom_mem, writeto_mem, or scan) - lets a test fail one specific step of a
        # multi-step operation (e.g. the read half of write_then_readinto) without affecting the
        # others, modeling a transfer interrupted partway through.
        self._faults.setdefault(op, []).extend([exc] * times)

    def _maybe_raise(self, op: str, address: int) -> None:
        if self.busy:
            raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
        if address in self.nak_addresses:
            raise OSError(errno.EIO, "no ACK from device")
        queue = self._faults.get(op)
        if queue:
            raise queue.pop(0)

    def deinit(self) -> None:
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def scan(self) -> list[int]:
        self.log.append(("scan",))
        if self.busy:
            raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
        queue = self._faults.get("scan")
        if queue:
            raise queue.pop(0)
        return sorted({addr for addr, _ in self.registers} - self.nak_addresses)

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        self._maybe_raise("readfrom_into", address)
        self.log.append(("readfrom_into", address, bytes(buf), stop))  # type: ignore[call-overload]

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        self._maybe_raise("writeto", address)
        data = bytes(buf)  # type: ignore[call-overload]
        self.log.append(("writeto", address, data, stop))
        return len(data)

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        self._maybe_raise("readfrom_mem", address)
        stored = bytes(self.registers.get((address, memaddr), bytearray(nbytes)))
        data = (stored + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw
        self.log.append(("readfrom_mem", address, memaddr, nbytes, addrsize))
        return data

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        self._maybe_raise("writeto_mem", address)
        self.registers[(address, memaddr)] = bytearray(buf)  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


class SPI:
    # No registers/addressing (SPI has none) - a test primes what readinto()/write_readinto()
    # "receive" from the simulated downstream device via read_queue, a FIFO of byte strings.
    MSB = 0
    LSB = 1

    def __init__(
        self,
        id: int,
        *,
        sck: Pin,
        mosi: Pin,
        miso: Pin,
        baudrate: int = 1000000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = 0,
    ) -> None:
        self.id = id
        self.sck = sck
        self.mosi = mosi
        self.miso = miso
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.bits = bits
        self.firstbit = firstbit
        self.deinit_called = False
        self.deinit_count = 0
        self.log: list[tuple] = []
        self.read_queue: list[bytes] = []

    def init(
        self,
        baudrate: int = -1,
        *,
        polarity: int = -1,
        phase: int = -1,
        bits: int = -1,
        firstbit: int = -1,
    ) -> None:
        # Real rp2 SPI.init(): -1/omitted args leave the current setting untouched (confirmed
        # against ports/rp2/machine_spi.c's allowed_args table - no "pins" kwarg accepted here,
        # only baudrate/polarity/phase/bits/firstbit).
        if firstbit == self.LSB:
            # Real rp2 hardware SPI only implements MSB-first (confirmed: machine_spi_init()'s
            # own `if (self->firstbit == SPI_LSB_FIRST) mp_raise_NotImplementedError(...)`).
            raise NotImplementedError("LSB")
        if baudrate != -1:
            self.baudrate = baudrate
        if polarity != -1:
            self.polarity = polarity
        if phase != -1:
            self.phase = phase
        if bits != -1:
            self.bits = bits
        if firstbit != -1:
            self.firstbit = firstbit
        self.log.append(("init", baudrate, polarity, phase, bits, firstbit))

    def deinit(self) -> None:
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def _next_read_bytes(self, nbytes: int) -> bytes:
        data = self.read_queue.pop(0) if self.read_queue else b""
        return (data + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw

    def write(self, buf: object) -> None:
        self.log.append(("write", bytes(buf)))  # type: ignore[call-overload]

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        data = self._next_read_bytes(len(buf))
        buf[:] = data
        self.log.append(("readinto", len(buf), write_value))

    def write_readinto(self, buffer_out: object, buffer_in: bytearray | memoryview) -> None:
        # Real machine.SPI.write_readinto() (mp_machine_spi_write_readinto(), shared by hardware
        # and soft SPI): raises ValueError before any transfer if the two buffers' lengths differ.
        if len(buffer_out) != len(buffer_in):  # type: ignore[arg-type]
            raise ValueError("buffers must be the same length")
        data = self._next_read_bytes(len(buffer_in))
        buffer_in[:] = data
        self.log.append(("write_readinto", bytes(buffer_out)))  # type: ignore[call-overload]
