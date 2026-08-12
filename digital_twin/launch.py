"""Standalone CLI launcher/demo for the digital twin itself (FINAL_WIRING_PLAN.md's Step 3, item
G) - runnable directly (`micropython digital_twin/launch.py [options]`). Deliberately twin-only: no
`src/` import anywhere in this file (owner's explicit choice, same session) - Step 5's own entry
point is expected to reuse parse_args()/main() the same way, it just also imports
src/sensortask_wozi.py afterward, which this file does not.

Brings up the exact same bus/peripheral wiring src/sensortask_wozi.py's real build_system() uses -
same pin numbers/frequencies, confirmed directly against that file's own WDT(timeout=8000)/
I2C(0, 13, 12, frequency=50000)/I2C(1, 19, 18, frequency=50000)/SPI(0, 2, 3, 4) lines (asy_i2c_driver.I2C's
own (port_id, scl_pin, sda_pin, frequency) argument order, confirmed directly against
src/asy_i2c_driver.py, is what fixes scl=Pin(13)/sda=Pin(12) for i2c0 and scl=Pin(19)/sda=Pin(18)
for i2c1 below) - then runs a small asyncio loop that periodically performs one real bus-level read
per sensor (through actual writeto()/readfrom_into()/readfrom_mem()/writeto_mem() calls shaped like
the real drivers' own, not just inspecting each chip fake's internal state), attempts one
WLAN.connect() and prints its phase transitions, and feeds the WDT on its own short timer (unless
suppressed via --no-wdt-feed).

--fault DEVICE:OP[:TIMES] just exposes the existing scripted FaultInjector/raise_on API each chip
fake already has via CLI flags - owner's explicit choice over a new ambient/probabilistic "randomly
flaky bus" mode (same session): no new twin-side fault mechanism exists anywhere in this file.

argparse is importable on the pinned Unix-port build (confirmed directly: `import argparse`
succeeds against the actual built interpreter), but the vendored micropython-lib implementation
turned out not to support what this launcher actually needs - confirmed directly by reading
lib/micropython-lib/python-stdlib/argparse/argparse.py: no `action="append"` (so a *repeatable*
--fault/--wifi-outcome flag can't accumulate), no `choices=`, and a parse failure calls
sys.exit(2) directly rather than raising a catchable exception. Per FINAL_WIRING_PLAN.md's own
fallback instruction ("hand-roll if not [reliably available]"), parse_args() below is a small
hand-rolled flag loop instead - consistent with this package's existing preference for not
depending on modules that may not be frozen into the test binary (tests/microtest.py's own
hand-rolled runner is the precedent already cited for this fallback).
"""

import asyncio
import errno
import struct
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

import machine
import network
from machine import I2C, SPI, WDT, Pin

_FAULT_DEVICE_OPS = {
    "sgp40": ("writeto", "readfrom_into"),
    "scd30": ("writeto", "readfrom_into"),
    "bmp3xx": ("readfrom_mem", "writeto_mem"),
    "fram": ("write", "readinto"),
    "wlan": ("active", "connect", "disconnect", "deinit", "isconnected", "status", "config", "ifconfig"),
}

_WIFI_OUTCOME_MAP = {
    "success": network.STAT_GOT_IP,
    "no_ap": network.STAT_NO_AP_FOUND,
    "wrong_password": network.STAT_WRONG_PASSWORD,
    "connect_fail": network.STAT_CONNECT_FAIL,
}

_SSID = "digital-twin-ssid"
_PASSWORD = "digital-twin-password"
_WDT_FEED_INTERVAL_S = 1.0  # comfortably under the WDT's own 8000ms timeout
_SENSOR_POLL_INTERVAL_S = 2.0
_WIFI_POLL_INTERVAL_S = 0.1


def parse_fault_spec(spec: str) -> "tuple[str, str, int]":
    parts = spec.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"malformed --fault {spec!r} - expected DEVICE:OP[:TIMES]")
    device, op = parts[0], parts[1]
    if device not in _FAULT_DEVICE_OPS:
        raise ValueError(f"--fault device {device!r} not recognized - expected one of {sorted(_FAULT_DEVICE_OPS)}")
    if op not in _FAULT_DEVICE_OPS[device]:
        raise ValueError(f"--fault op {op!r} not recognized for device {device!r} - expected one of {_FAULT_DEVICE_OPS[device]}")
    if len(parts) == 2:
        return device, op, 1
    if device == "wlan":
        raise ValueError(
            "--fault wlan:... does not support :TIMES - network.WLAN.raise_on has no repeat limit of its own, "
            "the fault stays armed until cleared"
        )
    try:
        times = int(parts[2])
    except ValueError as e:
        raise ValueError(f"--fault TIMES {parts[2]!r} is not an integer") from e
    if times < 1:
        raise ValueError(f"--fault TIMES must be >= 1, got {times}")
    return device, op, times


def _parse_wifi_outcome(value: str) -> int:
    if value not in _WIFI_OUTCOME_MAP:
        raise ValueError(f"--wifi-outcome {value!r} not recognized - expected one of {sorted(_WIFI_OUTCOME_MAP)}")
    return _WIFI_OUTCOME_MAP[value]


class LaunchConfig:
    def __init__(
        self,
        seed: "int | None" = None,
        fram_state_path: "str | None" = None,
        faults: "list[tuple[str, str, int]] | None" = None,
        wifi_outcomes: "list[int] | None" = None,
        no_wdt_feed: bool = False,
        duration: "float | None" = None,
    ) -> None:
        self.seed = seed
        self.fram_state_path = fram_state_path
        self.faults = faults if faults is not None else []
        self.wifi_outcomes = wifi_outcomes if wifi_outcomes is not None else []
        self.no_wdt_feed = no_wdt_feed
        self.duration = duration


def _pop_value(remaining: "list[str]", flag: str) -> str:
    if not remaining:
        raise ValueError(f"{flag} requires a value")
    return remaining.pop(0)


def parse_args(argv: "list[str]") -> "LaunchConfig":
    remaining = list(argv)
    seed: int | None = None
    fram_state_path: str | None = None
    faults: list[tuple[str, str, int]] = []
    wifi_outcomes: list[int] = []
    no_wdt_feed = False
    duration: float | None = None

    while remaining:
        arg = remaining.pop(0)
        if arg == "--seed":
            seed = int(_pop_value(remaining, arg))
        elif arg == "--fram-state-path":
            fram_state_path = _pop_value(remaining, arg)
        elif arg == "--fault":
            faults.append(parse_fault_spec(_pop_value(remaining, arg)))
        elif arg == "--wifi-outcome":
            wifi_outcomes.append(_parse_wifi_outcome(_pop_value(remaining, arg)))
        elif arg == "--no-wdt-feed":
            no_wdt_feed = True
        elif arg == "--duration":
            duration = float(_pop_value(remaining, arg))
        else:
            raise ValueError(f"unrecognized argument: {arg!r}")

    return LaunchConfig(
        seed=seed,
        fram_state_path=fram_state_path,
        faults=faults,
        wifi_outcomes=wifi_outcomes,
        no_wdt_feed=no_wdt_feed,
        duration=duration,
    )


def _apply_fault(device: str, op: str, times: int, chips: "dict[str, Any]", wlan: "network.WLAN") -> None:
    message = f"digital_twin/launch.py --fault {device}:{op}"
    if device == "wlan":
        # network.WLAN.raise_on has no times/repeat-limit concept of its own (see parse_fault_spec()
        # above) - stays armed until the process exits, matching what --fault wlan:... can actually
        # express on this twin.
        wlan.raise_on[op] = OSError(errno.EIO, message)
        return
    chips[device].fault.inject_fault(op, OSError(errno.EIO, message), times=times)


def _decode_bmp3xx_calibration(raw: bytes) -> "tuple[tuple[float, float, float], tuple[float, ...]]":
    # Reproduces asy_bmp3xx_driver.py's own _read_coefficients()/compensation math independently
    # (no src/ import here - see module docstring) - same shape tests/test_digital_twin_bmp3xx.py's
    # own _decode_temp_pressure()/_forward() already use for the same reason.
    coeff = struct.unpack("<HHbhhbbHHbbhbb", raw)
    temp_calib = (coeff[0] / 2**-8.0, coeff[1] / 2**30.0, coeff[2] / 2**48.0)
    pressure_calib = (
        (coeff[3] - 2**14.0) / 2**20.0,
        (coeff[4] - 2**14.0) / 2**29.0,
        coeff[5] / 2**32.0,
        coeff[6] / 2**37.0,
        coeff[7] / 2**-3.0,
        coeff[8] / 2**6.0,
        coeff[9] / 2**8.0,
        coeff[10] / 2**15.0,
        coeff[11] / 2**48.0,
        coeff[12] / 2**48.0,
        coeff[13] / 2**65.0,
    )
    return temp_calib, pressure_calib


def _forward_bmp3xx(
    temp_calib: "tuple[float, float, float]", pressure_calib: "tuple[float, ...]", adc_p: int, adc_t: int
) -> "tuple[float, float]":
    t1, t2, t3 = temp_calib
    p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 = pressure_calib
    pd1 = adc_t - t1
    pd2 = pd1 * t2
    temperature = pd2 + pd1 * pd1 * t3
    pd1 = p6 * temperature
    pd2 = p7 * temperature**2.0
    pd3 = p8 * temperature**3.0
    po1 = p5 + pd1 + pd2 + pd3
    pd1 = p2 * temperature
    pd2 = p3 * temperature**2.0
    pd3 = p4 * temperature**3.0
    po2 = adc_p * (p1 + pd1 + pd2 + pd3)
    pd1 = adc_p**2.0
    pd2 = p9 + p10 * temperature
    pd3 = pd1 * pd2
    pd4 = pd3 + p11 * adc_p**3.0
    pressure_pa = po1 + po2 + pd4
    return pressure_pa / 100.0, temperature


def _read_scd30(i2c0: "I2C") -> "tuple[float, float, float] | None":
    i2c0.writeto(0x61, bytes([0x02, 0x02]))  # GET_DATA_READY
    ready_buf = bytearray(3)
    i2c0.readfrom_into(0x61, ready_buf)
    if not ((ready_buf[0] << 8) | ready_buf[1]):
        return None
    i2c0.writeto(0x61, bytes([0x03, 0x00]))  # READ_MEASUREMENT
    buf = bytearray(18)
    i2c0.readfrom_into(0x61, buf)
    co2 = struct.unpack(">f", bytes(buf[0:2]) + bytes(buf[3:5]))[0]
    temp = struct.unpack(">f", bytes(buf[6:8]) + bytes(buf[9:11]))[0]
    hum = struct.unpack(">f", bytes(buf[12:14]) + bytes(buf[15:17]))[0]
    return co2, temp, hum


def _read_sgp40(i2c1: "I2C") -> int:
    i2c1.writeto(0x59, b"\x26\x0f\x80\x00\xa2\x66\x66\x93")  # MEASURE_RAW, datasheet's own no-compensation example
    buf = bytearray(3)
    i2c1.readfrom_into(0x59, buf)
    return (buf[0] << 8) | buf[1]


def _read_bmp3xx(i2c1: "I2C") -> "tuple[float, float]":
    i2c1.writeto_mem(0x77, 0x1B, bytes([0x13]))  # CONTROL = forced mode, press+temp enabled
    cal_raw = i2c1.readfrom_mem(0x77, 0x31, 21)
    burst = i2c1.readfrom_mem(0x77, 0x04, 6)
    adc_p = burst[2] << 16 | burst[1] << 8 | burst[0]
    adc_t = burst[5] << 16 | burst[4] << 8 | burst[3]
    temp_calib, pressure_calib = _decode_bmp3xx_calibration(bytes(cal_raw))
    return _forward_bmp3xx(temp_calib, pressure_calib, adc_p, adc_t)


async def _wdt_feeder(watchdog: "WDT", no_wdt_feed: bool) -> None:
    while True:
        if not no_wdt_feed:
            watchdog.feed()
        await asyncio.sleep(_WDT_FEED_INTERVAL_S)


async def _wifi_watcher(wlan: "network.WLAN") -> None:
    last_status = None
    while True:
        status = wlan.status()
        if status != last_status:
            print("WLAN: status ->", status)
            last_status = status
        await asyncio.sleep(_WIFI_POLL_INTERVAL_S)


async def _sensor_loop(i2c0: "I2C", i2c1: "I2C", summary: "dict[str, Any]") -> None:
    # Each sensor's own read is isolated in its own try/except - a --fault-injected (or genuinely
    # unlucky) bus error on one sensor must not stop this loop from continuing to poll the other
    # two, matching this codebase's own established "one bad participant can't take down the rest"
    # convention (e.g. src/system_service.py's _apply_level() per-setter try/except).
    while True:
        try:
            scd30_reading = _read_scd30(i2c0)
        except OSError as e:
            print("SCD30: read failed:", e)
        else:
            if scd30_reading is not None:
                co2, temp, hum = scd30_reading
                summary["readings"] += 1
                print(f"SCD30: co2={co2:.1f}ppm temp={temp:.1f}C hum={hum:.1f}%")

        try:
            raw = _read_sgp40(i2c1)
        except OSError as e:
            print("SGP40: read failed:", e)
        else:
            summary["readings"] += 1
            print(f"SGP40: raw={raw} ticks")

        try:
            pressure_hpa, bmp_temp = _read_bmp3xx(i2c1)
        except OSError as e:
            print("BMP3XX: read failed:", e)
        else:
            summary["readings"] += 1
            print(f"BMP3XX: pressure={pressure_hpa:.1f}hPa temp={bmp_temp:.1f}C")

        await asyncio.sleep(_SENSOR_POLL_INTERVAL_S)


async def main(config: "LaunchConfig") -> "dict[str, Any]":
    if config.seed is not None:
        # MicroPython's `random` module has no instantiable Random class (confirmed directly:
        # `random.Random` doesn't exist on the pinned build, unlike CPython) - every chip fake's own
        # random_source=None default already falls back to this same module-level `random`, though,
        # so reseeding its one shared global generator here gives every wired chip's value walk the
        # same single seed without needing machine.configure_random_source()'s object-injection seam
        # at all (that seam still exists for a caller that genuinely wants a distinct random.Random-
        # shaped object - see its own docstring - just not needed for this simpler case).
        import random as _random_module

        _random_module.seed(config.seed)
    machine.configure_fram_state_path(config.fram_state_path)

    print(
        f"digital_twin/launch.py starting - seed={config.seed!r} fram_state_path={config.fram_state_path!r} "
        f"no_wdt_feed={config.no_wdt_feed!r} duration={config.duration!r} faults={config.faults!r} "
        f"wifi_outcomes={config.wifi_outcomes!r}"
    )

    watchdog = WDT(timeout=8000)
    i2c0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    i2c1 = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    spi0 = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    wlan = network.WLAN(network.STA_IF)

    chips = {"scd30": i2c0.devices[0x61], "sgp40": i2c1.devices[0x59], "bmp3xx": i2c1.devices[0x77], "fram": spi0.device}
    for device, op, times in config.faults:
        _apply_fault(device, op, times, chips, wlan)

    if config.wifi_outcomes:
        wlan.script_connect_outcomes(config.wifi_outcomes)

    summary: dict[str, Any] = {"readings": 0, "wifi_status": None, "would_have_triggered_count": 0}

    wlan.active(True)
    wlan.connect(_SSID, _PASSWORD)

    tasks = [
        asyncio.get_event_loop().create_task(_wdt_feeder(watchdog, config.no_wdt_feed)),
        asyncio.get_event_loop().create_task(_wifi_watcher(wlan)),
        asyncio.get_event_loop().create_task(_sensor_loop(i2c0, i2c1, summary)),
    ]
    try:
        if config.duration is not None:
            await asyncio.sleep(config.duration)
        else:
            while True:
                await asyncio.sleep(3600)
    finally:
        for task in tasks:
            task.cancel()
        summary["wifi_status"] = wlan.status()
        summary["would_have_triggered_count"] = watchdog.would_have_triggered_count
        machine.flush_fram()
        print("digital_twin/launch.py summary:", summary)

    return summary


if __name__ == "__main__":
    _config = parse_args(sys.argv[1:])
    try:
        asyncio.run(main(_config))
    except KeyboardInterrupt:
        print("digital_twin/launch.py: interrupted")
