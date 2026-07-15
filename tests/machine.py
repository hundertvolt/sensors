"""Test-only fake `machine` module, per BACKLOG.md's mocking-boundary plan: mock only the raw
I2C bus-transaction level (readfrom_mem/writeto_mem/readfrom_into/writeto/scan/deinit), so
asy_i2c_driver.py's own logic (bit-packing, byte order, buffer slicing, locking, error paths)
runs for real against this fake instead of unavailable real hardware - the MicroPython Unix
port's own `machine` module has no I2C/SPI/real Pin (confirmed directly: PinBase/Signal/mem8/
mem16/mem32/idle/time_pulse_us only). Only implements what asy_i2c_driver.py's own imports need;
not a general-purpose machine stub.
"""


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
        self.log: list[tuple] = []
        self.registers: dict[tuple[int, int], bytearray] = {}
        self.nak_addresses: set[int] = set()  # addresses whose transactions raise OSError

    def _check_nak(self, address: int) -> None:
        # Mirrors a real no-ACK/bus failure: machine.I2C raises OSError for that.
        if address in self.nak_addresses:
            raise OSError(19, "ENODEV")

    def deinit(self) -> None:
        self.deinit_called = True
        self.log.append(("deinit",))

    def scan(self) -> list[int]:
        self.log.append(("scan",))
        return sorted({addr for addr, _ in self.registers} - self.nak_addresses)

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        self._check_nak(address)
        self.log.append(("readfrom_into", address, bytes(buf), stop))  # type: ignore[call-overload]

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        self._check_nak(address)
        data = bytes(buf)  # type: ignore[call-overload]
        self.log.append(("writeto", address, data, stop))
        return len(data)

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        self._check_nak(address)
        data = self.registers.get((address, memaddr), bytearray(nbytes))
        self.log.append(("readfrom_mem", address, memaddr, nbytes))
        return bytes(data[:nbytes])

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        self._check_nak(address)
        self.registers[(address, memaddr)] = bytearray(buf)  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf)))  # type: ignore[call-overload]
