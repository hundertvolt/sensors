"""Test-only fake `machine` module, per BACKLOG.md's mocking-boundary plan: mock only the raw
I2C bus-transaction level (readfrom_mem/writeto_mem/readfrom_into/writeto/scan/deinit), so
asy_i2c_driver.py's own logic (bit-packing, byte order, buffer slicing, locking, error paths)
runs for real against this fake instead of unavailable real hardware - the MicroPython Unix
port's own `machine` module has no I2C/SPI/real Pin (confirmed directly: PinBase/Signal/mem8/
mem16/mem32/idle/time_pulse_us only). Only implements what asy_i2c_driver.py's own imports need;
not a general-purpose machine stub.

Real RP2040 I2C error codes (confirmed against ports/rp2/machine_i2c.c, not guessed): the
hardware I2C driver only ever raises OSError(errno.EIO) - covers a NAK/no response and any other
general bus fault, which is also what a real multi-master arbitration loss would surface as on
this port - or OSError(errno.ETIMEDOUT), the Pico SDK's own bus-busy/clock-stretch timeout. There
is no distinct errno for "arbitration lost" on this port; both fold into one of the two above.
`nak_addresses`/`busy` below model exactly those two real conditions.
"""

import errno


class Pin:
    IN = 0
    OUT = 1

    def __init__(self, id: int, mode: int = -1) -> None:
        self.id = id
        self.mode = mode


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
