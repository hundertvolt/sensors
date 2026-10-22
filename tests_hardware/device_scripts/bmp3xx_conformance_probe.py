"""BMP3xx conformance probe, run identically on the bench chip and on the twin's fake: raw machine.I2C only, KEY=VALUE
lines and DONE=1 for flash/test_chip_conformance.py to diff. Volatile registers only, and the part is left as a soft
reset leaves it: sleep mode, every setting at its default (BMP384 datasheet 4.3.22)."""

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

# The register map (BMP384 datasheet 4.2, Table 24; 4.3.1-4.3.22), independent of the driver's own copy.
REG_CHIP_ID, REG_ERR, REG_STATUS, REG_DATA, REG_EVENT = 0x00, 0x02, 0x03, 0x04, 0x10
REG_PWR_CTRL, REG_OSR, REG_CONFIG, REG_CALIBRATION, REG_CMD = 0x1B, 0x1C, 0x1F, 0x31, 0x7E
CMD_SOFTRESET = 0xB6  # 4.3.22, Table 46
PWR_FORCED = 0x13  # press_en | temp_en | mode 01, forced (4.3.16)
STATUS_FLAGS = 0x70  # cmd_rdy | drdy_press | drdy_temp (4.3.3)
EVENT_POR = 0x01  # por_detected, clear-on-read (4.3.7)
OSR_WRITTEN, CONFIG_WRITTEN = 0x0B, 0x04  # osr_p x8 and osr_t x2; IIR coefficient 3 (4.3.17, 4.3.20)
_CALIBRATION_BYTES = 21  # T1 at 0x31 through P11 at 0x45 (3.11.1)
_STARTUP_MS = 2  # "Time to first communication", tstartup 2 ms (Table 2)
# A forced conversion at the reset OSR (x4, x1) takes ~11 ms (3.9.2); at x8, x2 ~21 ms: this covers both with margin.
# @tunable l3.bmp3xx_conformance_probe_conversion_ms = 50
_CONVERSION_MS = 50
_RP2_I2C_TIMEOUT_US = 50000  # machine.I2C's own default (ports/rp2/machine_i2c.c:38, v1.29.0)


def _hex(data: bytes) -> str:
    return "".join(f"{b:02x}" for b in data)


def _section_a_identity(p: "Probe") -> None:
    p.soft_reset()  # a known start, whatever the board last left in the registers
    p.rd(REG_EVENT)  # the reset's own por_detected, cleared before anything is read
    emit("A01_chip_id", _hex(p.rd(REG_CHIP_ID)))
    emit("A02_calibration", _hex(p.rd(REG_CALIBRATION, _CALIBRATION_BYTES)))
    emit("A03_err_reg", _hex(p.rd(REG_ERR)))


class Probe:
    def __init__(self, i2c: I2C, address: int, wdt: "machine.WDT") -> None:
        self.i2c, self.address, self.wdt = i2c, address, wdt

    def rd(self, reg: int, n: int = 1) -> bytes:
        return bytes(self.i2c.readfrom_mem(self.address, reg, n))

    def soft_reset(self) -> None:
        self.wr(REG_CMD, CMD_SOFTRESET)
        fed_wait_ms(self.wdt, _STARTUP_MS)

    def wr(self, reg: int, value: int) -> None:
        self.i2c.writeto_mem(self.address, reg, bytes([value]))


def _section_b_forced(p: "Probe") -> None:
    # Sleep after reset, one forced conversion (mode bits while it runs, sleep again after), data ready set by it and
    # cleared by reading the data (4.3.3, 3.3.2).
    emit("B01_status_after_reset", _hex(bytes([p.rd(REG_STATUS)[0] & STATUS_FLAGS])))
    emit("B02_pwr_ctrl_after_reset", _hex(p.rd(REG_PWR_CTRL)))
    p.wr(REG_PWR_CTRL, PWR_FORCED)
    emit("B03_pwr_ctrl_during_forced", _hex(p.rd(REG_PWR_CTRL)))
    fed_wait_ms(p.wdt, _CONVERSION_MS)
    emit("B04_status_after_conversion", _hex(bytes([p.rd(REG_STATUS)[0] & STATUS_FLAGS])))
    emit("B05_pwr_ctrl_after_conversion", _hex(p.rd(REG_PWR_CTRL)))
    emit("B06_data", _hex(p.rd(REG_DATA, 6)))
    emit("B07_status_after_data_read", _hex(bytes([p.rd(REG_STATUS)[0] & STATUS_FLAGS])))


def _section_c_reset(p: "Probe") -> None:
    # OSR and CONFIG written and read back, then a soft reset returns both to their defaults and raises por_detected.
    p.wr(REG_OSR, OSR_WRITTEN)
    p.wr(REG_CONFIG, CONFIG_WRITTEN)
    emit("C01_osr_config_written", _hex(p.rd(REG_OSR) + p.rd(REG_CONFIG)))
    p.soft_reset()
    emit("C02_osr_config_after_softreset", _hex(p.rd(REG_OSR) + p.rd(REG_CONFIG)))
    emit("C03_por_after_softreset", p.rd(REG_EVENT)[0] & EVENT_POR)
    emit("C04_por_after_second_read", p.rd(REG_EVENT)[0] & EVENT_POR)


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


def main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["bmp3xx"]["bus"]]
    i2c = I2C(bus["id"], scl=Pin(bus["scl_pin"]), sda=Pin(bus["sda_pin"]), freq=bus["frequency"], timeout=bus.get("timeout", _RP2_I2C_TIMEOUT_US))
    p = Probe(i2c, BENCH["addresses"]["bmp3xx"], wdt)
    _section_a_identity(p)
    _section_b_forced(p)
    _section_c_reset(p)
    emit("DONE", "1")


main()
