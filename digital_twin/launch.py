"""Standalone CLI launcher for the twin (micropython digital_twin/launch.py --wiring-plan PATH [options]), src/-free: it
builds the buses of the plan's device, periodically reads each wired sensor, attempts one WLAN connect and feeds a WDT.
--fault/--hang expose each chip fake's FaultInjector (owner, 2026-08-12: chosen over a probabilistic flaky mode)."""

import asyncio
import errno
import json
import random
import struct
import sys

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from typing import Protocol, TypedDict, TypeVar

    T = TypeVar("T")

    class _AttachmentKeys(TypedDict):
        # One chip of a plan bus, in buildgen.twin_wiring.compute_twin_wiring()'s shape.
        driver: str
        name_ext: str
        address: int

    class _Attachment(_AttachmentKeys, total=False):
        irq_pin: int  # scd30 and isl29125 only

    class _SpiAttachment(TypedDict):
        driver: str
        name_ext: str
        max_size: int

    class _UartPair(TypedDict):
        initiator_bus: str
        responder_bus: str

    class _Plan(TypedDict):
        device: str
        buses: dict[str, list[_Attachment]]
        spi: dict[str, _SpiAttachment]
        uart: _UartPair | None
        pins: dict[str, dict[str, int]]

    class _Injector(Protocol):
        # The FaultInjector calls the fault plumbing makes.
        def inject_fault(self, op: str, exc_type: type[BaseException], *args: object, times: int = 1, match: int | None = None) -> None: ...

        def inject_hang(self, op: str, seconds: float, times: int = 1) -> None: ...

        def pending(self, op: str) -> int: ...

    class _Chip(Protocol):
        # What the fault plumbing reads off every wired chip fake.
        @property
        def fault(self) -> _Injector: ...

    class _KnobChip(Protocol):
        # The mode setters and counted knobs a fault that is no queued exception sets.
        silent: bool
        drop_next_wren: int

        def configure_fault(self, op: str) -> None: ...

    FaultSpec = tuple[str, str, int, int | None, str]
    HangSpec = tuple[str, str, float, int]

import machine
import network
from _bmp3xx_chip import _decode_calibration
from _twin_common import Injections, StatePaths, saturating_add
from machine import I2C, SPI, WDT, Pin
from unix_port_unretrieved_report import install

_FAULT_DEVICE_OPS = {
    "scd30": ("writeto", "readfrom_into"),
    "sgp40": ("writeto", "readfrom_into", "general_call"),
    "bmp3xx": ("writeto", "readfrom_mem", "writeto_mem"),
    "isl29125": ("writeto", "readfrom_mem", "writeto_mem", "int_stuck_high"),
    "fram": ("readinto", "wren", "silent"),
    "uart_link": ("silent",),
    "wlan": ("active", "connect", "disconnect", "deinit", "isconnected", "status", "config", "ifconfig"),
}
# Modes, not counted faults: they stay set for the run, so TIMES and MATCH are refused.
_PERSISTENT_FAULT_OPS = (("isl29125", "int_stuck_high"), ("fram", "silent"), ("uart_link", "silent"))
_STACK_KIND = "stack"
_OSERROR_KIND = "oserror"
# twin-only test knob: no rp2 bus call raises this; it carries a C-stack overflow's exception
# (py/runtime.c:1786) into one read so the reboot path can be proven at L2
_STACK_EXHAUSTED_MESSAGE = "maximum recursion depth exceeded"

_HANG_DEVICE_OPS = {
    # Bus devices only: a WLAN fault is a synchronous raise_on[] check with no blocking HAL call underneath for
    # time.sleep() to stand in for, so wlan is in --fault's vocabulary and not in this one.
    "sgp40": ("writeto", "readfrom_into"),
    "scd30": ("writeto", "readfrom_into"),
    "bmp3xx": ("writeto", "readfrom_mem", "writeto_mem"),
    "isl29125": ("writeto", "readfrom_mem", "writeto_mem"),
    "fram": ("write", "readinto"),
}

_WIFI_OUTCOME_MAP = {
    "success": network.STAT_GOT_IP,
    "no_ap": network.STAT_NO_AP_FOUND,
    "wrong_password": network.STAT_WRONG_PASSWORD,
    "connect_fail": network.STAT_CONNECT_FAIL,
}

_SSID = "digital-twin-ssid"
_PASSWORD = "digital-twin-password"
# @tunable l2.twin_wdt_feed_interval_s = 1.0
_WDT_FEED_INTERVAL_S = 1.0  # well under the 8000 ms WDT timeout
# @tunable l2.launch_sensor_poll_interval_s = 2.0
_SENSOR_POLL_INTERVAL_S = 2.0
# @tunable l2.launch_wifi_poll_interval_s = 0.1
_WIFI_POLL_INTERVAL_S = 0.1
_I2C_FREQ_HZ = 50000
_SOURCE = "launch.py"

# The manual run's persistent defaults (owner, 2026-08-13); "" keeps a chip in memory only.
_FRAM_STATE_DEFAULT = "digital_twin/fram_state.json"
_SCD30_STATE_DEFAULT = "digital_twin/scd30_state.json"
_MEM_BACKUP_STATE_DEFAULT = "digital_twin/mem_backup_state.json"


_USAGE = f"""Usage: micropython digital_twin/launch.py --wiring-plan PATH [options]
  --wiring-plan PATH       the device's wiring-plan JSON (required)
  --seed N                 random seed for the chip fakes (default: none)
  --fram-state-path PATH   persist the FRAM image there (default: {_FRAM_STATE_DEFAULT}; "" in memory)
  --scd30-state-path PATH  persist the SCD30's NVM there (default: {_SCD30_STATE_DEFAULT}; "" in memory)
  --mem-backup-state-path PATH  the watchdog scratch registers' file (default: {_MEM_BACKUP_STATE_DEFAULT}; "" in memory)
  --fault DEVICE:OP[:TIMES[:MATCH]]  inject a fault (repeatable; TIMES default 1, or "stack"; MATCH hex)
  --hang DEVICE:OP:SECONDS[:TIMES]   inject a blocking hang (repeatable; TIMES default 1)
  --wifi-outcome OUTCOME   scripted connect outcome (repeatable): connect_fail, no_ap, success, wrong_password
  --no-wdt-feed            never feed the watchdog (default: fed)
  --duration SECONDS       stop after this long (default: run until interrupted)
  -h, --help               print this and exit 0"""


class LaunchConfig:
    def __init__(
        self, state: StatePaths, injections: Injections, *, wiring_plan_path: str, no_wdt_feed: bool = False, duration: "float | None" = None,
    ) -> None:
        self.state = state
        self.injections = injections
        self.wiring_plan_path = wiring_plan_path
        self.no_wdt_feed = no_wdt_feed
        self.duration = duration


def _read_scd30(bus: "I2C", addr: int) -> "str | None":
    bus.writeto(addr, bytes([0x02, 0x02]))  # GET_DATA_READY
    ready_buf = bytearray(3)
    bus.readfrom_into(addr, ready_buf)
    if not ((ready_buf[0] << 8) | ready_buf[1]):
        return None
    bus.writeto(addr, bytes([0x03, 0x00]))  # READ_MEASUREMENT
    buf = bytearray(18)
    bus.readfrom_into(addr, buf)
    co2 = struct.unpack(">f", bytes(buf[0:2]) + bytes(buf[3:5]))[0]
    temp = struct.unpack(">f", bytes(buf[6:8]) + bytes(buf[9:11]))[0]
    hum = struct.unpack(">f", bytes(buf[12:14]) + bytes(buf[15:17]))[0]
    return f"SCD30: co2={co2:.1f}ppm temp={temp:.1f}C hum={hum:.1f}%"


def _read_sgp40(bus: "I2C", addr: int) -> "str | None":
    bus.writeto(addr, b"\x26\x0f\x80\x00\xa2\x66\x66\x93")  # MEASURE_RAW, datasheet's own no-compensation example
    buf = bytearray(3)
    bus.readfrom_into(addr, buf)
    return f"SGP40: raw={(buf[0] << 8) | buf[1]} ticks"


def _read_bmp3xx(bus: "I2C", addr: int) -> "str | None":
    bus.writeto_mem(addr, 0x1B, bytes([0x13]))  # CONTROL = forced mode, press+temp enabled
    cal_raw = bus.readfrom_mem(addr, 0x31, 21)
    burst = bus.readfrom_mem(addr, 0x04, 6)
    adc_p = burst[2] << 16 | burst[1] << 8 | burst[0]
    adc_t = burst[5] << 16 | burst[4] << 8 | burst[3]
    temp_calib, pressure_calib = _decode_calibration(bytes(cal_raw))
    pressure_hpa, temp = _forward_bmp3xx(temp_calib, pressure_calib, adc_p, adc_t)
    return f"BMP3XX: pressure={pressure_hpa:.1f}hPa temp={temp:.1f}C"


_READERS = {"scd30": _read_scd30, "sgp40": _read_sgp40, "bmp3xx": _read_bmp3xx}


def _apply_fault(fault: "FaultSpec", chips: "dict[str, object]", wlan: "network.WLAN", *, source: str = _SOURCE) -> None:
    # A chip fake, or (in the runner) a UART link direction: each fault reaches it through the one seam it has.
    device, op, times, match, kind = fault
    driver = _driver_of(device)
    message = f"digital_twin/{source} --fault {device}:{op}"
    if driver == "wlan":
        wlan.raise_on[op] = (OSError, (errno.EIO, message), times)
        return
    _require_wired(device, chips, source=source)
    chip: _Chip = cast("_Chip", chips[device])
    knobs: _KnobChip = cast("_KnobChip", chips[device])
    if (driver, op) == ("isl29125", "int_stuck_high"):
        knobs.configure_fault(f"{driver}:{op}")
    elif op == "silent":
        knobs.silent = True
    elif (driver, op) == ("fram", "wren"):
        knobs.drop_next_wren += times
    elif kind == _STACK_KIND:
        chip.fault.inject_fault(op, RuntimeError, _STACK_EXHAUSTED_MESSAGE)
    else:
        chip.fault.inject_fault(op, OSError, errno.EIO, message, times=times, match=match)


def _apply_hang(hang: "HangSpec", chips: "dict[str, object]", *, source: str = _SOURCE) -> None:
    device, op, seconds, times = hang
    _require_wired(device, chips, source=source)
    chip: _Chip = cast("_Chip", chips[device])
    chip.fault.inject_hang(op, seconds, times=times)


def _build_buses(plan: "_Plan") -> "list[tuple[str, I2C, int]]":
    # Every I2C and SPI bus the plan lists, on the plan's pins; returns the sensors the loop reads.
    sensors: list[tuple[str, I2C, int]] = []
    for bus_name, attachments in plan["buses"].items():
        pins = plan["pins"][bus_name]
        bus = I2C(int(bus_name[3:]), scl=Pin(pins["scl"]), sda=Pin(pins["sda"]), freq=_I2C_FREQ_HZ)
        sensors.extend((a["driver"], bus, a["address"]) for a in attachments if a["driver"] in _READERS)
    for bus_name in plan["spi"]:
        pins = plan["pins"][bus_name]
        SPI(int(bus_name[3:]), sck=Pin(pins["sck"]), mosi=Pin(pins["mosi"]), miso=Pin(pins["miso"]))
    return sensors


def _collect_chips(plan: "_Plan") -> "dict[str, object]":
    # Every chip the plan wires, keyed by its instance key, found through machine.peripheral(); a bus the
    # booted code never constructed is skipped. The one implementation: the runner imports it.
    chips: dict[str, object] = {}
    for bus_name, attachments in plan["buses"].items():
        bus = machine.peripheral(bus_name)
        if not isinstance(bus, I2C):
            continue
        for attachment in attachments:
            chips[_instance_key(attachment["driver"], attachment["name_ext"])] = bus.devices[attachment["address"]]
    for bus_name, spi_attachment in plan["spi"].items():
        spi = machine.peripheral(bus_name)
        if isinstance(spi, SPI):
            chips[_instance_key(spi_attachment["driver"], spi_attachment["name_ext"])] = spi.device
    return chips


def _driver_of(key: str) -> "str | None":
    # A vocabulary key is a driver name or an instance key <driver>_<name_ext>; the longest match wins, so
    # uart_link_init resolves to uart_link.
    found: str | None = None
    for driver in _FAULT_DEVICE_OPS:
        if (key == driver or key.startswith(driver + "_")) and (found is None or len(driver) > len(found)):
            found = driver
    return found


def _forward_bmp3xx(
    temp_calib: "tuple[float, float, float]", pressure_calib: "tuple[float, ...]", adc_p: int, adc_t: int,
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


def _instance_key(driver: str, name_ext: str) -> str:
    return f"{driver}_{name_ext}" if name_ext else driver


def _parse_wifi_outcome(value: str) -> int:
    if value not in _WIFI_OUTCOME_MAP:
        raise ValueError(f"--wifi-outcome {value!r} not recognized - expected one of {sorted(_WIFI_OUTCOME_MAP)}")
    return _WIFI_OUTCOME_MAP[value]


def _pop_value(remaining: "list[str]", flag: str) -> str:
    if not remaining:
        raise ValueError(f"{flag} requires a value")
    return remaining.pop(0)


def _positive_int(flag: str, field: str, text: str) -> int:
    try:
        value = int(text)
    except ValueError as e:
        raise ValueError(f"{flag} {field} {text!r} is not an integer") from e
    if value < 1:
        raise ValueError(f"{flag} {field} must be >= 1, got {value}")
    return value


def _require_wired(device: str, chips: "dict[str, object]", *, source: str = _SOURCE) -> None:
    # A name in the vocabulary is not a chip this run wired: a device carries only what its TOML declares.
    # Without this the miss is a bare KeyError from inside the fault plumbing, naming nothing (Part L.5).
    if device not in chips:
        raise ValueError(f"digital_twin/{source}: --fault/--hang device {device!r} is not wired on this run - wired here: {sorted(chips)}")


def _resolve_device(flag: str, key: str, vocabulary: "dict[str, tuple[str, ...]]") -> str:
    driver = _driver_of(key)
    if driver is None or driver not in vocabulary:
        raise ValueError(f"{flag} device {key!r} not recognized - expected a driver or <driver>_<name_ext> of {sorted(vocabulary)}")
    return driver


async def _sensor_loop(sensors: "list[tuple[str, I2C, int]]", summary: "dict[str, int | None]") -> None:
    # Each sensor's read is isolated, so an injected or genuinely unlucky bus error on one does
    # not stop the loop polling the others - the same "one bad participant cannot take down the
    # rest" convention _apply_level()'s per-setter try/except follows.
    while True:
        for driver, bus, addr in sensors:
            try:
                line = _READERS[driver](bus, addr)
            except OSError as e:
                print(f"{driver.upper()}: read failed:", e)
                continue
            if line is not None:
                readings = summary["readings"]
                assert readings is not None  # set to 0 by main(), stepped only here
                summary["readings"] = saturating_add(readings)
                print(line)
        await asyncio.sleep(_SENSOR_POLL_INTERVAL_S)


def _shutdown_cleanup() -> None:
    # The one synchronous cleanup every twin exit path runs (SIGINT, a simulated reset in the runner)
    machine.flush_fram()
    machine.flush_scd30()


def _state_path(value: str) -> "str | None":
    # "" means in memory only, as machine.configure_fram_state_path(None) does.
    return value or None


async def _wdt_feeder(watchdog: "WDT", *, no_wdt_feed: bool) -> None:
    while True:
        if not no_wdt_feed:
            watchdog.feed()
        await asyncio.sleep(_WDT_FEED_INTERVAL_S)


async def _wifi_watcher(wlan: "network.WLAN") -> None:
    last_status = None
    while True:
        try:
            status = wlan.status()
        except OSError as e:
            print("WLAN: status read failed:", e)
        else:
            if status != last_status:
                print("WLAN: status ->", status)
                last_status = status
        await asyncio.sleep(_WIFI_POLL_INTERVAL_S)


async def main(config: "LaunchConfig") -> "dict[str, int | None]":
    install()  # every unretrieved task exception prints, at every level (Part I.4(e))
    injections = config.injections
    if injections.seed is not None:
        # MicroPython's random has no instantiable Random, but every chip fake falls back to this
        # module generator, so one seed seeds every walk; configure_random_source() remains for a distinct generator.
        random.seed(injections.seed)
    with open(config.wiring_plan_path) as f:
        plan: _Plan = json.load(f)
    machine.configure_wiring(plan)
    machine.configure_fram_state_path(config.state.fram)
    machine.configure_scd30_state_path(config.state.scd30)
    machine.configure_mem_backup_state_path(config.state.mem_backup)

    print(
        f"digital_twin/launch.py starting - wiring_plan={config.wiring_plan_path!r} seed={injections.seed!r} "
        f"state={config.state!r} no_wdt_feed={config.no_wdt_feed!r} duration={config.duration!r} "
        f"faults={injections.faults!r} hangs={injections.hangs!r} wifi_outcomes={injections.wifi_outcomes!r}",
    )

    # @tunable wdt.timeout_ms = 8000
    watchdog = WDT(timeout=8000)
    sensors = _build_buses(plan)
    wlan = network.WLAN(network.STA_IF)

    chips = _collect_chips(plan)
    for fault in injections.faults:
        _apply_fault(fault, chips, wlan)
    for hang in injections.hangs:
        _apply_hang(hang, chips)

    if injections.wifi_outcomes:
        wlan.script_connect_outcomes(injections.wifi_outcomes)

    summary: dict[str, int | None] = {"readings": 0, "wifi_status": None, "would_have_triggered_count": 0}

    try:
        wlan.active(True)
        wlan.connect(_SSID, _PASSWORD)
    except OSError as e:
        # A --fault wlan:... can target active()/connect() themselves, isolated the way
        # _sensor_loop() isolates each read - so one faulted WLAN op still leaves the feed and
        # read loops running and the demo exiting with a summary, rather than crashing main().
        print("WLAN: startup failed:", e)

    tasks = [
        asyncio.get_event_loop().create_task(_wdt_feeder(watchdog, no_wdt_feed=config.no_wdt_feed)),
        asyncio.get_event_loop().create_task(_wifi_watcher(wlan)),
        asyncio.get_event_loop().create_task(_sensor_loop(sensors, summary)),
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
        try:
            summary["wifi_status"] = cast("int", wlan.status())  # the no-argument form is the link state, an int
        except OSError as e:
            print("WLAN: status read failed:", e)
        summary["would_have_triggered_count"] = watchdog.would_have_triggered_count
        _shutdown_cleanup()
        print("digital_twin/launch.py summary:", summary)

    return summary


def parse_args(argv: "list[str]") -> "LaunchConfig":
    # Hand-rolled: micropython-lib's argparse supports only store/store_const (python-stdlib/argparse/argparse.py:91-124).
    # --help is answered before any other argument is read, so nothing else in the file runs.
    if "-h" in argv or "--help" in argv:
        print(_USAGE)
        sys.exit(0)
    remaining = list(argv)
    wiring_plan_path: str | None = None
    seed: int | None = None
    fram, scd30, mem_backup = _FRAM_STATE_DEFAULT, _SCD30_STATE_DEFAULT, _MEM_BACKUP_STATE_DEFAULT
    faults: list[FaultSpec] = []
    hangs: list[HangSpec] = []
    wifi_outcomes: list[int] = []
    no_wdt_feed = False
    duration: float | None = None

    while remaining:
        arg = remaining.pop(0)
        if arg == "--wiring-plan":
            wiring_plan_path = _pop_value(remaining, arg)
        elif arg == "--seed":
            seed = int(_pop_value(remaining, arg))
        elif arg == "--fram-state-path":
            fram = _pop_value(remaining, arg)
        elif arg == "--scd30-state-path":
            scd30 = _pop_value(remaining, arg)
        elif arg == "--mem-backup-state-path":
            mem_backup = _pop_value(remaining, arg)
        elif arg == "--fault":
            faults.append(parse_fault_spec(_pop_value(remaining, arg)))
        elif arg == "--hang":
            hangs.append(parse_hang_spec(_pop_value(remaining, arg)))
        elif arg == "--wifi-outcome":
            wifi_outcomes.append(_parse_wifi_outcome(_pop_value(remaining, arg)))
        elif arg == "--no-wdt-feed":
            no_wdt_feed = True
        elif arg == "--duration":
            duration = float(_pop_value(remaining, arg))
        else:
            raise ValueError(f"unrecognized argument: {arg!r}")
    if wiring_plan_path is None:
        raise ValueError("--wiring-plan PATH is required")

    return LaunchConfig(
        StatePaths(_state_path(fram), _state_path(scd30), _state_path(mem_backup)),
        Injections(seed, faults, hangs, wifi_outcomes),
        wiring_plan_path=wiring_plan_path,
        no_wdt_feed=no_wdt_feed,
        duration=duration,
    )


def parse_fault_spec(spec: str) -> "FaultSpec":
    # DEVICE:OP[:TIMES[:MATCH]] -> (device, op, times, match, kind); MATCH is hex, and the literal "stack" in the
    # TIMES place queues one stack-exhaustion fault instead of an OSError.
    parts = spec.split(":")
    if not 2 <= len(parts) <= 4:
        raise ValueError(f"malformed --fault {spec!r} - expected DEVICE:OP[:TIMES[:MATCH]]")
    device, op = parts[0], parts[1]
    driver = _resolve_device("--fault", device, _FAULT_DEVICE_OPS)
    if op not in _FAULT_DEVICE_OPS[driver]:
        raise ValueError(f"--fault op {op!r} not recognized for device {device!r} - expected one of {_FAULT_DEVICE_OPS[driver]}")
    if len(parts) == 2:
        return device, op, 1, None, _OSERROR_KIND
    if (driver, op) in _PERSISTENT_FAULT_OPS:
        raise ValueError(f"--fault {driver}:{op} is a mode that stays set for the run - it takes no TIMES or MATCH")
    queued = driver != "wlan" and (driver, op) != ("fram", "wren")  # the ops a FaultInjector queue carries
    if len(parts) == 4 and not queued:
        raise ValueError(f"--fault {driver}:{op} takes no MATCH - only a queued bus fault is matched by its key")
    if parts[2] == _STACK_KIND:
        if not queued or len(parts) == 4:
            raise ValueError(f"--fault {driver}:{op}:stack needs a queued bus fault and takes no MATCH")
        return device, op, 1, None, _STACK_KIND
    times = _positive_int("--fault", "TIMES", parts[2])
    if len(parts) == 3:
        return device, op, times, None, _OSERROR_KIND
    try:
        match = int(parts[3], 16)
    except ValueError as e:
        raise ValueError(f"--fault MATCH {parts[3]!r} is not a hexadecimal key") from e
    return device, op, times, match, _OSERROR_KIND


def parse_hang_spec(spec: str) -> "HangSpec":
    # --hang DEVICE:OP:SECONDS[:TIMES] queues a real blocking sleep, which _fault_injection.py's
    # docstring explains is the only faithful way to wedge a bus against the watchdog. TIMES
    # defaults to 1, since real hardware gets one 8388ms window before the WDT resets it.
    parts = spec.split(":")
    if len(parts) not in (3, 4):
        raise ValueError(f"malformed --hang {spec!r} - expected DEVICE:OP:SECONDS[:TIMES]")
    device, op = parts[0], parts[1]
    driver = _resolve_device("--hang", device, _HANG_DEVICE_OPS)
    if op not in _HANG_DEVICE_OPS[driver]:
        raise ValueError(f"--hang op {op!r} not recognized for device {device!r} - expected one of {_HANG_DEVICE_OPS[driver]}")
    try:
        seconds = float(parts[2])
    except ValueError as e:
        raise ValueError(f"--hang SECONDS {parts[2]!r} is not a number") from e
    if seconds <= 0:
        raise ValueError(f"--hang SECONDS must be > 0, got {seconds}")
    times = _positive_int("--hang", "TIMES", parts[3]) if len(parts) == 4 else 1
    return device, op, seconds, times


if __name__ == "__main__":
    _config = parse_args(sys.argv[1:])
    try:
        asyncio.run(main(_config))
    except KeyboardInterrupt:
        # Reached when the interrupt lands while main() is suspended: its finally never runs, so this is the only
        # cleanup (SPECIFICATION.md F.1, asyncio.run() catches only CancelledError and Exception).
        _shutdown_cleanup()
        print("digital_twin/launch.py: interrupted")
