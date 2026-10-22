"""FRAM conformance probe, run identically on the bench chip and on the twin's fake: raw machine.SPI and the CS pin
only, KEY=VALUE lines and DONE=1 for flash/test_chip_conformance.py to diff. Writes only inside _SCRATCH_REGIONS,
above every chunk, and puts back the bytes it found there (MB85RS2MTA datasheet, the op-codes and status register)."""

from machine import SPI, Pin

# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_REGIONS = ((0x3FD00, 0x100),)  # 256 B below fram_command_hold_timing.py's top block, above every chunk
_BASE = _SCRATCH_REGIONS[0][0]
_PATTERN_BYTES = 16  # one short transfer: under rp2's 32-byte DMA path and its overrun check (SPECIFICATION.md Part F.5.2)
# The op-codes and status bits (MB85RS2MTA datasheet p.6, op-code table and status register).
OP_WREN, OP_WRDI, OP_RDSR, OP_READ, OP_WRITE, OP_RDID = 0x06, 0x04, 0x05, 0x03, 0x02, 0x9F
STATUS_WEL = 0x02
_WIDE_ADDRESS_ABOVE = 0xFFFF  # a part past 64 KB takes a 3-byte address (MB85RS2MTA p.9, READ and WRITE)


def _hex(data: "bytes | bytearray") -> str:
    return "".join(f"{b:02x}" for b in data)


def _section_a_identity(p: "Probe") -> None:
    # MISO's idle level with the chip deselected (its SO is High-Z, p.2): 0x00 on the pad's pull-down, 0xFF on a pull-up.
    buf = bytearray(1)
    p.spi.readinto(buf)
    emit("A01_miso_idle_byte", _hex(buf))
    emit("A02_rdid", _hex(p.transfer(bytes([OP_RDID]), 4)))


class Probe:
    def __init__(self, spi: SPI, cs: Pin, wdt: "machine.WDT") -> None:
        self.spi, self.cs, self.wdt = spi, cs, wdt
        self.wide = BENCH["fram_max_size"] > _WIDE_ADDRESS_ABOVE

    def header(self, op: int, address: int) -> bytes:
        tail = [(address >> 16) & 0xFF] if self.wide else []
        return bytes([op] + tail + [(address >> 8) & 0xFF, address & 0xFF])

    def op(self, op: int) -> None:
        self.cs.value(0)
        self.spi.write(bytes([op]))
        self.cs.value(1)

    def transfer(self, out: bytes, nbytes: int) -> bytes:
        # One CS-low session: the op-code (and address) written, then nbytes clocked in.
        buf = bytearray(nbytes)
        self.cs.value(0)
        self.spi.write(out)
        self.spi.readinto(buf)
        self.cs.value(1)
        self.wdt.feed()
        return bytes(buf)

    def wel(self) -> int:
        return 1 if self.transfer(bytes([OP_RDSR]), 1)[0] & STATUS_WEL else 0

    def write(self, address: int, data: bytes) -> None:
        self.cs.value(0)
        self.spi.write(self.header(OP_WRITE, address))
        self.spi.write(data)
        self.cs.value(1)


def _section_b_latch(p: "Probe") -> None:
    emit("B01_status", _hex(p.transfer(bytes([OP_RDSR]), 1)))
    p.op(OP_WREN)
    emit("B02_wel_after_wren", p.wel())
    p.op(OP_WRDI)
    emit("B03_wel_after_wrdi", p.wel())


def _section_c_round_trip(p: "Probe") -> None:
    # A write and read back; whether WEL survives a WRITE; a write with WEL reset ignored; the found bytes put back.
    found = p.transfer(p.header(OP_READ, _BASE), _PATTERN_BYTES)
    pattern = bytes((0xA5 + 3 * i) & 0xFF for i in range(_PATTERN_BYTES))
    p.op(OP_WREN)
    p.write(_BASE, pattern)
    emit("C01_round_trip", "yes" if p.transfer(p.header(OP_READ, _BASE), _PATTERN_BYTES) == pattern else "no")
    emit("C02_wel_after_write", p.wel())
    p.op(OP_WRDI)
    p.write(_BASE, bytes(b ^ 0xFF for b in pattern))
    emit("C03_write_without_wel_ignored", "yes" if p.transfer(p.header(OP_READ, _BASE), _PATTERN_BYTES) == pattern else "no")
    p.op(OP_WREN)
    p.write(_BASE, found)
    p.op(OP_WRDI)
    emit("C04_found_bytes_restored", "yes" if p.transfer(p.header(OP_READ, _BASE), _PATTERN_BYTES) == found else "no")


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


def main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["fram"]
    bus = BENCH["bus"][chip["bus"]]
    cs = Pin(chip["cs_pin"], Pin.OUT, value=1)
    spi = SPI(bus["id"], sck=Pin(bus["sck_pin"]), mosi=Pin(bus["mosi_pin"]), miso=Pin(bus["miso_pin"]))  # rp2's 1 MHz default
    p = Probe(spi, cs, wdt)
    try:
        _section_a_identity(p)
        _section_b_latch(p)
        _section_c_round_trip(p)
    finally:
        cs.value(1)
    emit("DONE", "1")


main()
