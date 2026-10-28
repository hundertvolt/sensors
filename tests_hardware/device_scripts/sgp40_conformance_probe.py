"""SGP40 conformance probe, run identically on the bench chip and on the twin's fake: raw machine.I2C only, KEY=VALUE
lines and DONE=1 for flash/test_chip_conformance.py to diff; replies go out raw, so CRCs are checked host-side.
Ends with the heater off, the idle mode the chip powers up in (datasheet Table 14)."""

from machine import I2C, Pin

# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.watchdog import arm, fed_wait_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Command codes and their maximum durations (datasheet Table 8).
CMD_SERIAL, CMD_SELF_TEST, CMD_HEATER_OFF = b"\x36\x82", b"\x28\x0e", b"\x36\x15"
_SERIAL_MS, _SELF_TEST_MS, _MEASURE_MS, _HEATER_OFF_MS = 1, 320, 30, 1
# The measure command with the datasheet's own argument words and CRCs (Table 9: 50 %RH, 25 degC; Table 10).
CMD_MEASURE_DEFAULT = b"\x26\x0f\x80\x00\xa2\x66\x66\x93"
_RP2_I2C_TIMEOUT_US = 50000  # machine.I2C's own default (ports/rp2/machine_i2c.c:38, v1.29.0)


def _hex(data: bytes) -> str:
    return "".join(f"{b:02x}" for b in data)


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


class Probe:
    def __init__(self, i2c: I2C, address: int, wdt: "machine.WDT") -> None:
        self.i2c, self.address, self.wdt = i2c, address, wdt

    def command(self, frame: bytes, wait_ms: int, nbytes: int) -> bytes:
        # The frame, the command's maximum duration (Table 8), then the read: no polling of a NACKed header.
        self.i2c.writeto(self.address, frame)
        fed_wait_ms(self.wdt, wait_ms)
        buf = bytearray(nbytes)
        self.i2c.readfrom_into(self.address, buf)
        return bytes(buf)


def main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["sgp40"]["bus"]]
    i2c = I2C(bus["id"], scl=Pin(bus["scl_pin"]), sda=Pin(bus["sda_pin"]), freq=bus["frequency"], timeout=bus.get("timeout", _RP2_I2C_TIMEOUT_US))
    p = Probe(i2c, BENCH["addresses"]["sgp40"], wdt)
    try:
        serial = p.command(CMD_SERIAL, _SERIAL_MS, 9)
        emit("A01_serial", _hex(serial))
        # Hard-coded at production (3.4): the same three words on every read.
        emit("A02_serial_stable", "yes" if p.command(CMD_SERIAL, _SERIAL_MS, 9) == serial else "no")
        emit("B01_self_test", _hex(p.command(CMD_SELF_TEST, _SELF_TEST_MS, 3)))
        emit("C01_raw_signal", _hex(p.command(CMD_MEASURE_DEFAULT, _MEASURE_MS, 3)))
    finally:  # the self-test and the measurement leave the hotplate on (3.1, 3.3): off on every way out
        try:
            i2c.writeto(p.address, CMD_HEATER_OFF)
            heater_off = "yes"
        except OSError as exc:
            heater_off = f"OSError:{exc.args[0]}"
        fed_wait_ms(wdt, _HEATER_OFF_MS)
    emit("D01_heater_off_acked", heater_off)
    emit("DONE", "1")


main()
