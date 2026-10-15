"""SCD30 conformance probe, run identically on the bench chip and on the twin's fake: raw machine.I2C only, KEY=VALUE
lines and DONE=1 for flash/test_chip_conformance.py to diff; replies go out raw, so CRCs are checked host-side.
Two soft resets, no NVM-backed command (Interface Description 1.4.10). Waits are awaited: the chip measures meanwhile."""

import asyncio
import time

from machine import I2C, Pin

# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# The command words (Interface Description 1.4.3, 1.4.4, 1.4.5, 1.4.9, 1.4.10).
CMD_INTERVAL, CMD_DATA_READY, CMD_READ_MEASUREMENT = 0x4600, 0x0202, 0x0300
CMD_FIRMWARE_VERSION, CMD_SOFT_RESET = 0xD100, 0xD304
_RP2_I2C_TIMEOUT_US = 50000  # machine.I2C's own default (ports/rp2/machine_i2c.c:38, v1.29.0)
# "the read header should be send with a delay of > 3ms following the write sequence" (1.4.4).
# @tunable l3.scd30_conformance_probe_read_delay_ms = 5
_READ_DELAY_MS = 5
# @tunable l3.scd30_conformance_probe_ready_poll_ms = 200
_READY_POLL_MS = 200
# Data ready may take one full interval after the probe's first read; slack for the read itself.
# @tunable l3.scd30_conformance_probe_ready_slack_ms = 2000
_READY_SLACK_MS = 2000
_BOOT_MAX_MS = 2000  # "The boot-up time is < 2 s" (1.1)
_INTERVAL_MAX_S = 1800  # source: "Available range: [2 ... 1800]" (1.4.3); a garbled word never stretches the wait
# @tunable l3.scd30_conformance_probe_recovery_poll_ms = 20
_RECOVERY_POLL_MS = 20


def _hex(data: bytes) -> str:
    return "".join(f"{b:02x}" for b in data)


class Probe:
    def __init__(self, i2c: I2C, address: int, wdt: "machine.WDT") -> None:
        self.i2c, self.address, self.wdt = i2c, address, wdt

    async def command(self, cmd: int, nbytes: int) -> bytes:
        # A command word, the read-header delay, then a separate read: the SCD30 takes no repeated start (1.1).
        self.i2c.writeto(self.address, bytes([cmd >> 8, cmd & 0xFF]))
        await fed_sleep_ms(self.wdt, _READ_DELAY_MS)
        return self.read(nbytes)

    def read(self, nbytes: int) -> bytes:
        buf = bytearray(nbytes)
        self.i2c.readfrom_into(self.address, buf)
        return bytes(buf)


async def _section_a_identity(p: Probe) -> int:
    emit("A01_firmware_version_word", _hex(await p.command(CMD_FIRMWARE_VERSION, 3)))
    interval = await p.command(CMD_INTERVAL, 3)
    emit("A02_interval_word", _hex(interval))
    return (interval[0] << 8) | interval[1]


async def _section_b_measurement(p: Probe, interval_s: int) -> None:
    # Data ready, the 18-byte read-out (three floats, six words, six CRCs), then data ready cleared by that read.
    deadline_ms = min(interval_s, _INTERVAL_MAX_S) * 1000 + _READY_SLACK_MS
    start = time.ticks_ms()
    ready = await p.command(CMD_DATA_READY, 3)
    while ready[1] != 1 and time.ticks_diff(time.ticks_ms(), start) < deadline_ms:
        await fed_sleep_ms(p.wdt, _READY_POLL_MS)
        ready = await p.command(CMD_DATA_READY, 3)
    emit("B01_data_ready_word", _hex(ready))
    emit("B02_data_ready_within_interval", "yes" if ready[1] == 1 else "no")
    emit("B03_measurement", _hex(await p.command(CMD_READ_MEASUREMENT, 18)) if ready[1] == 1 else "not_ready")
    emit("B04_data_ready_after_read", _hex(await p.command(CMD_DATA_READY, 3)))


async def _section_c_reset(p: Probe) -> None:
    # The recovery bound: from the reset command to the first answered firmware-version read, polled; a booting
    # chip refuses its header. Then a second reset and, after the datasheet's boot bound, a read with no command.
    emit("C01_soft_reset_acked", _soft_reset(p))
    start = time.ticks_ms()
    recovered = "none"
    while time.ticks_diff(time.ticks_ms(), start) < _BOOT_MAX_MS + _READY_SLACK_MS:
        await fed_sleep_ms(p.wdt, _RECOVERY_POLL_MS)
        try:
            await p.command(CMD_FIRMWARE_VERSION, 3)
        except OSError:
            continue
        recovered = str(time.ticks_diff(time.ticks_ms(), start))
        break
    emit("C02_soft_reset_recovery_ms", recovered)
    _soft_reset(p)
    await fed_sleep_ms(p.wdt, _BOOT_MAX_MS)
    try:
        emit("C03_read_before_a_command", _hex(p.read(3)))
    except OSError as exc:
        emit("C03_read_before_a_command", f"OSError:{exc.args[0]}")


def _soft_reset(p: Probe) -> str:
    try:
        p.i2c.writeto(p.address, bytes([CMD_SOFT_RESET >> 8, CMD_SOFT_RESET & 0xFF]))
    except OSError as exc:
        return f"OSError:{exc.args[0]}"
    return "yes"


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


async def main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["scd30"]
    bus = BENCH["bus"][chip["bus"]]
    i2c = I2C(bus["id"], scl=Pin(bus["scl_pin"]), sda=Pin(bus["sda_pin"]), freq=bus["frequency"], timeout=bus.get("timeout", _RP2_I2C_TIMEOUT_US))
    p = Probe(i2c, BENCH["addresses"]["scd30"], wdt)
    interval_s = await _section_a_identity(p)
    await _section_b_measurement(p, interval_s)
    await _section_c_reset(p)
    emit("DONE", "1")


asyncio.run(main())
