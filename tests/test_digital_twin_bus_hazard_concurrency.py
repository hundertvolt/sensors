"""Digital-twin tier: boots each generated device's real object graph against the real digital_twin buses and proves
SPECIFICATION.md Part C.8's locking model holds under genuine concurrent load, on every device whose plan shares a bus,
and the system commands' storage hazards; Part C.8 also covers this file's own device-scope rationale."""

import asyncio
import errno
import sys

sys.path.insert(0, "ext")  # same convention as test_digital_twin_sensortask_integration.py's own comment
sys.path.insert(0, "digital_twin")
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _crc8 import crc8  # noqa: E402 - imported after the prewarm and the UDP shim; the twin's own CRC-8, independent of src/
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim
from _fast_sleep import FastAsyncSleep  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_int  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import devices_with_shared_bus, distinct_wirings, generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_i2c_driver  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_wifi_service  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_bmp3xx_driver import BMP3XX_I2C  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_crc_checks import CRC8  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_isl29125_driver import ISL29125_I2C, ISL29125_Reader  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_scd30_driver import SCD30_I2C  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_sgp40_driver import SGP40_I2C  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import ModuleType
    from typing import TypeVar

    from _fram_chip import FRAMChip
    from _scd30_chip import SCD30Chip
    from _twin_common import BoundedLog
    from _twin_devices import I2CAttachment, TwinWiringPlan
    from launch import _Plan
    from machine import WDT

    from asy_base_classes import SensorReader
    from asy_fram_manager import FRAMChunk
    from asy_system_service import SystemService
    from asy_wifi_service import WifiService

    T = TypeVar("T")

# @tunable l2.twin_wdt_feed_interval_s = 1.0
_WDT_FEED_INTERVAL_S = 1.0
# @tunable l2.bus_hazard_concurrency_run_bound_s = 20.0
_RUN_BOUND_S = 20.0
# @tunable l2.bus_hazard_concurrency_run_seconds = 9.0
_RUN_SECONDS = 9.0
# @tunable l2.bus_hazard_concurrency_established_poll_s = 0.5
_ESTABLISHED_POLL_S = 0.5
# @tunable l2.bus_hazard_concurrency_reconnect_poll_s = 1.0
_RECONNECT_POLL_S = 1.0
# @tunable l2.bus_hazard_concurrency_flap_window_s = 75.0
_FLAP_WINDOW_S = 75.0
# @tunable l2.bus_hazard_concurrency_flap_run_bound_s = 95.0
_FLAP_RUN_BOUND_S = 95.0
# @tunable l2.bus_hazard_concurrency_state_run_bound_s = 30.0
_STATE_RUN_BOUND_S = 30.0
# @tunable l2.bus_hazard_recovery_offsets = 6
_RECOVERY_OFFSETS = 6
# @tunable l2.bus_hazard_recovery_reads = 6
_RECOVERY_READS = 6
# @tunable l2.bus_hazard_command_wait_s = 20.0
_COMMAND_WAIT_S = 20.0
_SEED = bytes(range(5, 45))  # 40 bytes: over rp2's 32-byte DMA threshold, the only SPI reads that can raise
_DROPPED_WRENS = 8  # more WRENs than one write's retry sends: the write fails rather than recovering inside the driver
_RUNG_OFFSETS = 6  # as many offsets as each loop has reads, the recovery case's own count
_CANCEL_TURNS = 40  # scheduler turns into the SGP40's setup and measurement, which end well before
_HOLD_SCD30_CYCLES = 3  # whole SCD30 cycles of real bus load the driven 60 s retry is held open for
_POLL_S = 0.1  # how often the ladder runs and the command waits look again
_POLL_MS = int(_POLL_S * 1000)  # the same look on a driven clock
_ERASE_UNIT: int = src_int("src/asy_fram_manager.py", "_ERASE_UNIT")
_STA_RETRY_S: int = src_int("src/asy_wifi_service.py", "_STA_RETRY_AFTER_LOSS_S")
_STA_ESTABLISHED: int = src_int("src/asy_wifi_service.py", "_PHASE_STA_ESTABLISHED")
_ERASE_US_PER_BYTE = 8  # the erase's real wire time at the 1 MHz bus (asy_fram_manager.py's _ERASE_UNIT comment)
_GENERAL_CALL_ENTRY = ("writeto", 0x00, b"\x06", True)
# Which get_data() field, per driver, proves that driver produced a real reading under load - the twin tier's much
# smaller analogue of tests/_bus_hazard_catalog.py's mock-tier adapters (Part C.8); a new driver needs an entry first.
_I2C_DRIVER_HEALTH_FIELD: "dict[str, str]" = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}
# The per-cycle register read a driver makes on its shared bus, each pointer write followed at once by its read.
_PER_CYCLE_REGISTER = {"bmp3xx": 0x10, "isl29125": 0x01}  # BMP3XX's EVENT, ISL29125's CONFIG snapshot
# Every (device, bus, occupants) whose plan puts two or more chips on one bus: the shared-bus cases run on each.
_SHARED = devices_with_shared_bus()
# FRAM sits alone on its SPI bus on every device; its same-device hazards run once per distinct FRAM wiring (its SPI
# pins, chip select and size), each on a fresh board.
_FRAM_DEVICES = distinct_wirings("fram")

_scratch = TmpScratch("dtbh")
_ports = PortAllocator("test_digital_twin_bus_hazard_concurrency")
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)


class _RetryOnDrivenClock:
    # asy_wifi_service's asyncio with only the 60 s loss retry's sleep on a driven clock (tests/_fake_time.py): every other
    # sleep, the connect polls and the loop's refresh among them, stays real, as do the bus load and the task graph.
    def __init__(self, clock: DrivenTime) -> None:
        self._clock = clock

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    def sleep(self, seconds: float) -> "Coroutine[object, object, None]":
        return self._clock._sleep_ms(int(seconds * 1000)) if seconds == _STA_RETRY_S else asyncio.sleep(seconds)  # as core.sleep() hands it on


async def _armed(sysfunct: "SystemService") -> None:
    # Returns once a command's reset is armed, before its Timer fires: the reset-and-relaunch is the suite's.
    waited = 0.0
    while not sysfunct._reset_armed:
        assert waited < _COMMAND_WAIT_S, "the command never reached its armed reset"
        await asyncio.sleep(_POLL_S)
        waited += _POLL_S


def _assert_no_rollover(chip: "FRAMChip") -> None:
    # Every unit the erase wrote lies inside the chip: none started past its last full unit, so none wrapped to 0.
    assert chip.writes_at_dropped == 0, "the chip's write record dropped addresses"
    assert max(chip.writes_at) + _ERASE_UNIT <= chip.size, f"a write started at {max(chip.writes_at):#x}, past the chip's last {_ERASE_UNIT}-byte unit"


async def _boot(device: str, *, port: int = 0, cfg_path: "str | None" = None) -> "tuple[ModuleType, WDT]":
    # A new board on the device's plan, then the generated main()'s first steps: build_system() with the watchdog the
    # boot entry arms, the runner's UART pollers, the setup list. Port 0 binds nothing: no listener starts.
    module = load_device(device)
    machine.reset_peripherals()  # the state files are kept
    network.reset_interfaces()
    machine.configure_wiring(wiring_plan(device))
    cfg = cfg_path if cfg_path is not None else _scratch.dir()
    write_offline_ntp_config(cfg)
    write_error_level_config(cfg)
    watchdog = boot_entry_watchdog(module, device)
    await module.build_system(watchdog=watchdog, cfg_path=cfg, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=port)
    plan: _Plan = cast("_Plan", wiring_plan(device))
    run_generic_integration._wire_uart_crossover(module, plan)  # before the setups (CLAUDE.md "Known hang cause")
    await module.sysfunct.run_setups(module._collect_setups())
    return module, watchdog


async def _cancel_started_tasks(module: "ModuleType") -> None:
    # Every task start_tasks() started, cancelled and awaited: nothing supervises them here.
    for task in module.sysfunct._tasks:
        if task is not None:
            await cancel(task)


def _chip(module: "ModuleType") -> "FRAMChip":
    chip = module.fram.fram._spidev.spi._spi.device
    assert chip is not None
    return cast("FRAMChip", chip)


async def _driven(clock: DrivenTime, coro: "Coroutine[object, object, T]") -> "T":
    # `coro` as a task, the driven clock elapsed a poll at a time until it ends: a step whose own sleeps run on it.
    task = asyncio.get_event_loop().create_task(coro)
    waited = 0
    while not task.done():
        assert waited < _COMMAND_WAIT_S * 1000, "a driven step never ended"
        await clock.elapse(_POLL_MS)
        waited += _POLL_MS
    return await task


def _driven_modules(device: str) -> "list[object]":
    # The device's generated module loaded, then every src service and driver holding asyncio, and the twin's machine
    # and network: one clock for all of them, the boot's waits and the pause's deadline among their reads.
    load_device(device)
    return [m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio]


async def _feed_watchdog_periodically(watchdog: "WDT") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(_WDT_FEED_INTERVAL_S)


def _fram_plan_by_size() -> "TwinWiringPlan":
    # The generated plan with the largest FRAM: the erase that takes longest.
    plans = [wiring_plan(device) for device in generated_devices()]
    return max((p for p in plans if p["spi"]), key=lambda p: max(a["max_size"] for a in p["spi"].values()))


def _keep_evidence(chip: "FRAMChip", name: str) -> None:
    with open(_scratch.path(name), "wb") as f:
        for start in range(0, len(chip.memory), 4096):
            f.write(chip.memory[start : start + 4096])


def _key(attachment: "I2CAttachment") -> str:
    # The generated module's global for an attachment: its driver, then "_" and its name extension if it has one.
    return attachment["driver"] + ("_" + attachment["name_ext"] if attachment["name_ext"] else "")


def _ladder_device() -> str:
    assert _LADDER, "no generated device shares a bus between an SGP40 and a BMP3XX"
    return _LADDER[0][0]


async def _ladder_run(device: str, faults: "dict[int, str]", until_recoveries: int) -> "tuple[ModuleType, int, int, int, int, bool]":
    # The device's graph with `faults` (chip address -> its read op) failing until the shared bus has run
    # `until_recoveries` bus rungs, then cleared; returns (module, rungs run, bus clears, controller rebuilds, W15
    # slots, chips kept).
    module, watchdog = await _boot(device, port=_ports.next())
    (bus_name,) = [bus for d, bus, _o in _SHARED if d == device]
    bus = getattr(module, bus_name)
    fake = bus._i2c
    assert fake is not None
    chips = dict(fake.devices)
    feeder = asyncio.get_event_loop().create_task(_feed_watchdog_periodically(watchdog))
    try:
        await module.sysfunct.start_tasks(module._collect_task_starters(), task_names=module._collect_task_names())
        await module.sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
        # Both readers set up and measuring first: the faults then hit read cycles, not setup.
        while (await module.sgp40.get_data()).VOC is None or (await module.bmp3xx.get_data()).Pres is None:
            await asyncio.sleep(_POLL_S)
        before = bus.recoveries
        calls = {"clear": 0, "recover": 0}
        for name in calls:
            real = getattr(bus, name)

            async def counted(real: "Callable[[], Coroutine[object, object, int]]" = real, name: str = name) -> int:
                calls[name] += 1
                return await real()

            setattr(bus, name, counted)
        for address, op in faults.items():
            chips[address].fault.inject_fault(op, OSError, errno.EIO, "no ACK", times=500)
        while bus.recoveries - before < until_recoveries:
            await asyncio.sleep(_POLL_S)
        for address in faults:
            chips[address].fault.clear()
        assert module.sgp40._err_cnt_internal > 0  # the streak the faults built, now unwinding
        while module.sgp40._err_cnt_internal or module.bmp3xx._err_cnt_internal:
            await asyncio.sleep(_POLL_S)
        assert watchdog.would_have_triggered_count == 0
        kept = fake.devices == chips and all(fake.devices[a] is chips[a] for a in chips)
        return module, bus.recoveries - before, calls["clear"], calls["recover"], await _w15(module.sgp40, module.bmp3xx), kept
    finally:
        await cancel(feeder)
        await _cancel_started_tasks(module)


def _on_each(devices: "list[str]", scenario: "Callable[[str], Coroutine[object, object, None]]", timeout_s: float) -> None:
    # One run per device, each after the file's per-test reset: no run inherits the previous device's board, its
    # constructed peripherals or its FRAM state path.
    for device in devices:
        machine.reset_test_state()
        network.reset_test_state()
        run_timed(scenario(device), timeout_s=timeout_s)


def _payload(entry: "tuple[object, ...]") -> bytes:
    # A bus-log transfer's bytes (its third field).
    data = entry[2]
    assert isinstance(data, (bytes, bytearray)), entry
    return bytes(data)


def _register_reads_on(log: "list[tuple[object, ...]]", address: int, register: int) -> int:
    # Register reads of `register` at `address`: each no-stop pointer write must be followed at once by its read.
    count = 0
    for i, entry in enumerate(log):
        if entry[:4] == ("writeto", address, bytes([register]), False):
            assert i + 1 < len(log) and log[i + 1][:2] == ("readfrom_into", address), f"a transfer split a register read: {log[i : i + 2]}"
            count += 1
    return count


async def _run_real_task_graph_and_assert_healthy(module: "ModuleType", watchdog: "WDT", shared_bus_log: "BoundedLog[tuple[object, ...]]", run_seconds: float) -> None:
    # Starts the real tasks and timers the generated main() itself would, then asserts the run produced fresh data from
    # every occupant of every bus the device's plan lists and never starved the watchdog - not just "didn't crash".
    device = module.__name__[len("sensortask_") :]
    plan = wiring_plan(device)
    feeder = asyncio.get_event_loop().create_task(_feed_watchdog_periodically(watchdog))
    try:
        await module.sysfunct.start_tasks(module._collect_task_starters(), task_names=module._collect_task_names())
        await module.sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
        await asyncio.sleep(run_seconds)
        assert watchdog.would_have_triggered_count == 0, device
        for bus_name, attachments in plan["buses"].items():
            for attachment in attachments:
                driver = attachment["driver"]
                field = _I2C_DRIVER_HEALTH_FIELD.get(driver)
                assert field is not None, f"no health-check field known for driver {driver!r} - add one to _I2C_DRIVER_HEALTH_FIELD before it can get generated digital-twin bus-hazard coverage"
                data = await getattr(module, _key(attachment)).get_data()
                assert getattr(data, field) is not None, f"{device}: {driver!r} never produced real data (missing {field!r}) under concurrent bus load on {bus_name}"
                if driver == "isl29125":  # its INT pin drives an extra cycle of its own: a sample still carries its range
                    assert data.RangeAct is not None, f"{device}: the ISL29125 reported a sample with no range attached"
        # FRAM has its own dedicated SPI bus (no interleaving hazard here) but must stay healthy through concurrent
        # sensor error-log/backup writes onto it.
        if "fram" in plan["instances"]:
            assert module.fram.fram.initialized is True, f"{device}: FRAM dropped out of the initialized state during concurrent bus load"
            assert await module.fram.fram.verify_present(), f"{device}: FRAM did not respond to a device-ID re-probe after concurrent bus load"
        # The bounded bus log kept the whole window, so a missing entry below is a missing transfer, never an evicted one.
        assert shared_bus_log.dropped == 0, f"{device}: the bus log dropped {shared_bus_log.dropped} entries - the window outran it"
        log = list(shared_bus_log)
        occupants = {a["driver"]: a["address"] for attachments in plan["buses"].values() for a in attachments}
        if "sgp40" in occupants:
            # SGP40_I2C._reset()'s general-call broadcast (Part C.8) fired concurrently with its siblings' startup, the
            # twin SGP40 took the reset, and the measure after it answered (its VOC above).
            assert _GENERAL_CALL_ENTRY in shared_bus_log, f"{device}: SGP40's general-call reset never fired during this run - test isn't exercising the real hazard window"
            sgp_bus = getattr(module, next(bus for bus, attachments in plan["buses"].items() if any(a["driver"] == "sgp40" for a in attachments)))
            assert sgp_bus._i2c.devices[occupants["sgp40"]].resets >= 1, f"{device}: the general call reached the bus but not the twin SGP40"
        for driver, register in _PER_CYCLE_REGISTER.items():
            address = occupants.get(driver)
            if address is not None and any(e[:2] == ("writeto", address) for e in log):
                assert _register_reads_on(log, address, register) > 0, f"{device}: no per-cycle read of {register:#04x} at {address:#04x} under load"
    finally:
        await cancel(feeder)
        await _cancel_started_tasks(module)


def _rung_across_offsets(device: str, bus_name: str, siblings: "tuple[str, ...]", rung: "Callable[[asy_i2c_driver.I2C], Coroutine[object, object, object]]", check: "Callable[[asy_i2c_driver.I2C], None]") -> None:
    for offset in range(_RUNG_OFFSETS):
        failures: list[str] = []
        built: list[asy_i2c_driver.I2C] = []

        async def scenario(failures: "list[str]" = failures, built: "list[asy_i2c_driver.I2C]" = built, offset: int = offset) -> None:
            bus = _shared_bus(device, bus_name)  # inside the run: the twin SCD30's refresh timer is a task, ended with it
            built.append(bus)

            async def fire() -> None:
                for _ in range(offset):
                    await asyncio.sleep(0)
                await rung(bus)

            await asyncio.gather(*(_sibling_reads(device, s, bus, failures) for s in siblings), fire())

        with FastAsyncSleep():
            run_timed(scenario(), timeout_s=_RUN_BOUND_S)
        assert not failures, f"{device} offset {offset}: a sibling read failed beside the rung: {failures}"
        check(built[0])


async def _scd30_cycle(chip: "SCD30Chip", count: int = 1) -> None:
    # Returns once the twin SCD30 has produced `count` readings inside the wait and the driver has read each out, each
    # within the four feed intervals the healthy window used to sleep: pending one read out first, then a new one made and read.
    for _ in range(count):
        waited = 0.0
        for ready in (False, True, False):
            while chip._data_ready is not ready:
                assert waited < _WDT_FEED_INTERVAL_S * 4, "no whole SCD30 measurement cycle inside the healthy window"
                await asyncio.sleep(_POLL_S)
                waited += _POLL_S


def _sgp40_measure_command(temperature: int, relative_humidity: int) -> bytes:
    # From the SGP40 datasheet, not the driver's tick helpers: 0x260F, then the RH and T words each with
    # its CRC-8 (Table 9); ticks per Table 10's formulas rounded half up, as its 50 % -> 0x8000 row needs.
    rh_ticks = (relative_humidity * 65535 * 2 + 100) // 200
    t_ticks = ((temperature + 45) * 65535 * 2 + 175) // 350
    rh_word = bytes([rh_ticks >> 8, rh_ticks & 0xFF])
    t_word = bytes([t_ticks >> 8, t_ticks & 0xFF])
    return b"\x26\x0f" + rh_word + bytes([crc8(rh_word)]) + t_word + bytes([crc8(t_word)])


def _shared_bus(device: str, bus_name: str) -> "asy_i2c_driver.I2C":
    # The device's bus on its own plan and pins, as its generated module builds it: a fresh bus and chips each time.
    plan = wiring_plan(device)
    pins = plan["pins"][bus_name]
    machine.reset_peripherals()
    machine.configure_wiring(plan)
    machine.Pin.reset_registry()
    return asy_i2c_driver.I2C(int(bus_name[3:]), pins["scl"], pins["sda"], frequency=50000, timeout=200000)  # type: ignore[typeddict-item]  # an I2C bus's pins


def _sibling_read(device: str, sibling: str, bus: "asy_i2c_driver.I2C") -> "Callable[[], Coroutine[object, object, object]]":
    # One read of `sibling` through a protocol instance of its own: None for a failed one, a BMP3XX's a wrong chip ID.
    if sibling == "bmp3xx":
        address = next(a["address"] for attachments in wiring_plan(device)["buses"].values() for a in attachments if a["driver"] == sibling)
        bmp = asy_i2c_driver.I2CDevice(bus, address)

        async def chip_id() -> object:
            raw = await bmp.get_register_bytes(0x00, 1)  # CHIP_ID
            return raw[0] if raw is not None and raw[0] in (0x50, 0x60) else None

        return chip_id
    reads: dict[str, Callable[[], Coroutine[object, object, object]]] = {
        "scd30": SCD30_I2C(bus).get_measurement_interval,
        "sgp40": SGP40_I2C(bus).measure_raw,
        "isl29125": ISL29125_I2C(bus).read_counts,
    }
    return reads[sibling]


async def _sibling_reads(device: str, sibling: str, bus: "asy_i2c_driver.I2C", failures: "list[str]", rounds: int = _RUNG_OFFSETS) -> None:
    # One valid read per round from a protocol instance of `sibling`; any raise or None is a failure.
    read = _sibling_read(device, sibling, bus)
    for _ in range(rounds):
        try:
            value = await read()
        except Exception as e:  # recorded with its class: the assertion names it
            failures.append(f"{sibling}: {type(e).__name__}: {e}")
        else:
            if value is None:
                failures.append(f"{sibling}: None")
        await asyncio.sleep(0)


async def _start_graph(module: "ModuleType") -> None:
    # The tasks and timers main() starts: start_tasks()'s stagger, then the timer sequencer.
    await module.sysfunct.start_tasks(module._collect_task_starters(), task_names=module._collect_task_names())
    await module.sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())


async def _supervised_graph(module: "ModuleType", clock: "DrivenTime | None" = None) -> "asyncio.Task[None]":
    # The tasks, timers and supervisor main() starts: the shutdown sequence parks and cancels the supervisor first. With
    # a clock the stagger and the sequencer run on it, released before the supervisor starts: a first pass run inside
    # the drive would sit one 2 s check away from where it parks for a command, which real time never makes it wait.
    if clock is None:
        await _start_graph(module)
    else:
        await _driven(clock, _start_graph(module))
        clock.release()
    return asyncio.get_event_loop().create_task(module.sysfunct.supervise_tasks())


async def _tear_down_at_the_armed_reset(sysfunct: "SystemService", supervisor: "asyncio.Task[None]") -> None:
    # From outside, each awaited: the reset timer and task, the supervisor and its own task.
    sysfunct._reset_timer.deinit()
    if sysfunct._reset_task is not None:
        await cancel(sysfunct._reset_task)
    await cancel(supervisor)
    if sysfunct._supervisor_task is not None:
        await cancel(sysfunct._supervisor_task)


def _three_concurrent_measurements(device: str) -> None:
    # Three sessions on one SGP40_I2C of the device's own bus, each with its own inputs; returns once each read its word.
    ((bus_name, address),) = [(bus, a["address"]) for bus, attachments in sorted(wiring_plan(device)["buses"].items()) for a in attachments if a["driver"] == "sgp40"][:1]
    inputs = ((25, 50), (10, 30), (35, 80))
    results: dict[tuple[int, int], int | None] = {}
    built: list[asy_i2c_driver.I2C] = []

    async def scenario() -> None:
        bus = _shared_bus(device, bus_name)  # inside the run: a neighbour chip's refresh timer is a task, ended with it
        built.append(bus)
        sgp = SGP40_I2C(bus)

        async def session(temperature: int, relative_humidity: int) -> None:
            results[(temperature, relative_humidity)] = await sgp.measure_raw(temperature=temperature, relative_humidity=relative_humidity)

        await asyncio.gather(*(session(t, rh) for t, rh in inputs))

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)
    i2c = built[0]._i2c
    assert i2c is not None
    log = [entry for entry in i2c.log if entry[0] in ("writeto", "readfrom_into") and entry[1] == address]
    assert [entry[0] for entry in log] == ["writeto", "readfrom_into"] * len(inputs), f"{device}: a session's write and read were not adjacent: {log}"
    sent = [_payload(log[i]) for i in range(0, len(log), 2)]
    assert sorted(sent) == sorted(_sgp40_measure_command(t, rh) for t, rh in inputs), f"{device}: a session's command was overwritten by another's: {[p.hex() for p in sent]}"
    word_after = {_payload(log[i]): (_payload(log[i + 1])[0] << 8) | _payload(log[i + 1])[1] for i in range(0, len(log), 2)}
    for t, rh in inputs:
        own = word_after[_sgp40_measure_command(t, rh)]
        assert results[(t, rh)] == own, f"{device}: the session at {t} C/{rh} % got {results[(t, rh)]}, not the word read after its own write ({own:#x})"


def test_the_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # Every device whose plan shares a bus: wozi's SGP40+BMP3xx pairing has no real-hardware proof (wozi is not flashed,
    # CLAUDE.md), dev's grouping has its bench proof too (tests_hardware/flash/test_bus_concurrency.py).
    for device, bus_name, _occupants in _SHARED:

        async def scenario(device: str = device, bus_name: str = bus_name) -> None:
            module, watchdog = await _boot(device, port=_ports.next())
            await _run_real_task_graph_and_assert_healthy(module, watchdog, getattr(module, bus_name)._i2c.log, run_seconds=_RUN_SECONDS)

        run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_fram_recovers_after_a_write_its_chip_never_enabled() -> None:
    # The twin is FRAM's only write-failure-then-recovery verification for a device never flashed. rp2's SPI write
    # never raises (ports/rp2/machine_spi.c), so the write fails as silicon can: WREN dropped.
    async def scenario(device: str) -> None:
        module, _watchdog = await _boot(device)
        fram_spi = module.fram.fram
        chip = _chip(module)
        assert fram_spi.initialized is True

        chip.drop_next_wren = _DROPPED_WRENS
        async with fram_spi:
            ok = await fram_spi.set_values(b"\x01\x02\x03\x04", addr_start=0x100)
        assert ok is False, "a write whose WREN never latched reported success"
        assert bytes(chip.memory[0x100:0x104]) != b"\x01\x02\x03\x04", "a write whose WREN never latched reached the array"
        chip.drop_next_wren = 0

        # Recovery: the chip was never disturbed, so verify_present() succeeds cleanly. Not wrapped in `async with
        # fram_spi:` since verify_present() self-acquires that (non-reentrant) lock internally.
        assert await fram_spi.verify_present(), "verify_present() failed to recover after a write its chip never enabled"

        buf = bytearray(4)
        async with fram_spi:
            ok = await fram_spi.set_values(b"\x01\x02\x03\x04", addr_start=0x100)
            assert ok, "set_values() failed on a clean retry after recovery"
            ok = await fram_spi.get_values(buf, addr_start=0x100)
            assert ok and bytes(buf) == b"\x01\x02\x03\x04", f"get_values() returned {bytes(buf)!r} on a clean retry after recovery, expected b'\\x01\\x02\\x03\\x04'"

    _on_each(_FRAM_DEVICES, scenario, _RUN_BOUND_S)


def test_fram_recovers_after_an_injected_spi_read_fault() -> None:
    # Read-side sibling of the write test above: _read_address() has no try/except of its own, so an rp2 read
    # error propagates raw from get_values(); its recovery needs its own proof.
    async def scenario(device: str) -> None:
        module, _watchdog = await _boot(device)
        fram_spi = module.fram.fram
        chip = _chip(module)
        assert fram_spi.initialized is True

        # Seed real, known bytes first, through a clean round trip - so a "recovered" read below
        # can be checked against real prior content, not just "returned without raising".
        async with fram_spi:
            ok = await fram_spi.set_values(_SEED, addr_start=0x200)
            assert ok, "seed write before the fault-injection scenario failed"

        chip.fault.inject_fault("readinto", OSError, errno.EIO)
        buf = bytearray(len(_SEED))  # a DMA-length read: rp2 raises on no shorter one
        raised: BaseException | None = None
        async with fram_spi:
            try:
                await fram_spi.get_values(buf, addr_start=0x200)
            except OSError as e:
                raised = e
        assert raised is not None, "expected the injected SPI fault to propagate as a raised exception from get_values()"

        # Recovery: the fault raises before FRAMChip.readinto() touches any chip state, so the chip was never disturbed.
        assert await fram_spi.verify_present(), "verify_present() failed to recover after one injected SPI read fault"

        async with fram_spi:
            ok = await fram_spi.get_values(buf, addr_start=0x200)
            assert ok and bytes(buf) == _SEED, f"get_values() returned {bytes(buf)!r} on a clean retry after recovery, not the pre-fault seeded content"

    _on_each(_FRAM_DEVICES, scenario, _RUN_BOUND_S)


def test_fram_chunk_loop_absorbs_a_transient_spi_rx_overrun() -> None:
    # Twin-tier form of the live-path mock tests in test_asy_fram_manager.py: the same fault, but against
    # the real twin bus and a chunk allocated from the real booted manager. One overrun costs nothing, _read
    # chunk-reading block 1 when block 0 fails.
    #
    # A persistent one degrades to None instead of propagating, and leaves the chunk marked BUSY by design -
    # destructive readout, SPECIFICATION.md Part A.4.
    async def scenario(device: str) -> None:
        module, _watchdog = await _boot(device)
        manager = module.fram
        bus = manager.fram._spidev.spi._spi
        assert bus is not None
        chunk = manager.get_chunk(40, crc=CRC8(), owner="HAZARD_OVERRUN")  # 41 B with the CRC byte - over the 32 B DMA threshold
        assert chunk is not None
        payload = bytes(range(40))
        assert await chunk.write(payload)

        bus.rx_overrun_remaining = 1  # one transient glitch, then the bus recovers
        assert await chunk.read() == bytearray(payload), "a single RX overrun should be absorbed by the block-1 copy"
        assert bus.rx_overrun_remaining == 0, "the injected overrun never actually fired"

        bus.rx_overrun = True  # persistent: both copies unreadable
        assert await chunk.read() is None, "an unrecoverable overrun must degrade, not propagate"
        bus.rx_overrun = False
        assert await chunk.read() is None, "an interrupted read deliberately keeps the chunk unreadable until rewritten"
        assert await chunk.write(payload), "a write is what clears the stuck BUSY status bytes"
        assert await chunk.read() == bytearray(payload)

    _on_each(_FRAM_DEVICES, scenario, _RUN_BOUND_S)


def test_the_system_survives_concurrent_bus_load_and_a_real_established_wifi_disconnect() -> None:
    # Recombination test (owner, 2026-09-04, paraphrase): the fully wired system tolerates a genuine 60 s wifi_mode_lock
    # hold (the real ESTABLISHED-branch retry) under concurrent bus load, on the first shared-bus device. The retry waits
    # outside the lock; a forced failed reconnect runs it, its sleep driven over real SCD30 cycles (agent, 2026-10-21).
    device, bus_name = _SHARED[0][0], _SHARED[0][1]
    scd30s = [a["address"] for a in wiring_plan(device)["buses"][bus_name] if a["driver"] == "scd30"]
    assert scd30s, f"{device}: no SCD30 on {bus_name} to count the retry's real bus cycles by"

    async def scenario() -> None:
        module, watchdog = await _boot(device, port=_ports.next())
        # A real configured SSID, written before the task graph starts so the wifi task's first connect attempt sees it.
        persisted, _results = await module.conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted

        feeder = asyncio.get_event_loop().create_task(_feed_watchdog_periodically(watchdog))
        bus = getattr(module, bus_name)._i2c
        flap_task = asyncio.get_event_loop().create_task(_wait_established_then_flap_once(module.conn, bus.devices[scd30s[0]], bus.log))
        try:
            await module.sysfunct.start_tasks(module._collect_task_starters(), task_names=module._collect_task_names())
            await module.sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
            try:  # the reconnect ends the window, never later than its old fixed length
                retry_ms, bus_work, held, polls = await asyncio.wait_for(flap_task, _FLAP_WINDOW_S)
            except asyncio.TimeoutError:
                raise AssertionError("WiFi never recovered from the real established-connection disconnect after its 60 s retry") from None
            assert retry_ms == _STA_RETRY_S * 1000, f"{device}: the link was back after a {retry_ms} ms retry on the driven clock: the {_STA_RETRY_S} s retry never ran"
            assert bus_work > 0, f"{device}: no {bus_name} transaction during the {_STA_RETRY_S} s retry"
            assert held * 2 < polls, f"{device}: wifi_mode_lock held through {held} polls in a row of the {polls} the {_STA_RETRY_S} s retry was open"
            assert watchdog.would_have_triggered_count == 0
            # Not _run_real_task_graph_and_assert_healthy(): its bus-log window check assumes a short run, and at this
            # length the bounded log wraps under ordinary traffic. The per-occupant health check is the same.
            for attachments in wiring_plan(device)["buses"].values():
                for attachment in attachments:
                    field = _I2C_DRIVER_HEALTH_FIELD[attachment["driver"]]
                    data = await getattr(module, _key(attachment)).get_data()
                    assert getattr(data, field) is not None, f"{device}: {attachment['driver']} never produced real data under concurrent bus load + a real wifi disconnect"
            assert module.fram.fram.initialized is True
            assert await module.fram.fram.verify_present()
            assert module.conn._wlan.isconnected() is True, "WiFi never recovered from the real established-connection disconnect within the real 60s retry window"
        finally:
            await cancel(flap_task)
            await cancel(feeder)
            await _cancel_started_tasks(module)

    run_timed(scenario(), timeout_s=_FLAP_RUN_BOUND_S)


def test_storage_pause_gates_the_real_twin_chip() -> None:
    # Twin-tier parity for the chunk-level gating the mock tier proves against a fake bus and the flash tier
    # against the real chip: the same claims, through the real booted manager on the twin bus. The
    # discriminating check unpauses and reads the chip back - a refused write would show new bytes.
    async def scenario(device: str) -> None:
        module, _watchdog = await _boot(device)
        manager = module.fram
        chunk = manager.get_chunk(16, crc=CRC8(), owner="HAZARD_PAUSE")
        assert chunk is not None
        first, second = bytes(range(16)), bytes(range(100, 116))
        assert await chunk.write(first)

        manager.set_pause(value=True)
        assert await chunk.write(second) is False
        assert await chunk.read() is None

        manager.set_pause(value=False)
        assert bytes(await chunk.read() or b"") == first, "the refused write still reached the twin chip"
        assert await chunk.write(second) is True
        assert bytes(await chunk.read() or b"") == second

    _on_each(_FRAM_DEVICES, scenario, _RUN_BOUND_S)


def test_a_timed_storage_pause_ends_by_itself_on_the_next_uptime_pass() -> None:
    # A pause through SYSTEM's own entry drops a logger write, and the first uptime pass past its deadline ends it: the
    # next write lands, nothing was deferred. `mempause` through the generated dispatch answers and pauses the same way.
    async def scenario(device: str) -> None:
        with DrivenTime(*_driven_modules(device), sleeps=True) as clock:  # the pause's deadline and the uptime passes too
            module, _watchdog = await _driven(clock, _boot(device))
            sysfunct, manager, chip = module.sysfunct, module.fram, _chip(module)
            assert await module._system_cmd_callback("mempause") is True
            assert manager.get_pause() is True, "mempause left the storage running"
            assert sysfunct.pause_permanent_storage(0) is True and manager.get_pause() is False
            status = sysfunct.start_asy_status()
            sysfunct.start_uptime_timer()
            try:
                assert sysfunct.pause_permanent_storage(2) is True and manager.get_pause() is True
                before = chip.write_count
                await _driven(clock, sysfunct.pr.err_s("dropped while paused", errno=code("E", "TEST_SEED_A")))
                assert chip.write_count == before, "a logger write reached the chip during the pause"
                waited = 0.0
                while manager.get_pause():
                    assert waited < _COMMAND_WAIT_S, "the timed pause never ended by itself"
                    await clock.elapse(_POLL_MS)
                    waited += _POLL_S
                await _driven(clock, sysfunct.pr.err_s("lands after the pause", errno=code("E", "TEST_SEED_B")))
                assert chip.write_count > before, "the write after the pause did not land"
            finally:
                await cancel(status)

    _on_each(_FRAM_DEVICES, scenario, _STATE_RUN_BOUND_S)


def test_write_protect_blocks_reads_too_and_the_data_survives_it() -> None:
    # Twin-tier parity for the mock tier's pair of write-protect tests, and the accepted, intended behavior
    # the flash tier confirms against real silicon: _read_chunk() has to WRITE a transient busy marker
    # before reading, so write protection gates read() as well as write().
    #
    # Different in kind from the pause gate above - that refuses before the bus, this at the chip - and,
    # crucially, non-destructive: the bytes come back once it is cleared.
    async def scenario(device: str) -> None:
        module, _watchdog = await _boot(device)
        manager = module.fram
        chunk = manager.get_chunk(16, crc=CRC8(), owner="HAZARD_WP")
        assert chunk is not None
        payload = bytes(range(16))
        assert await chunk.write(payload)

        assert await manager.fram.set_write_protected(value=True) is True
        assert await manager.fram.get_write_protected() is True
        assert await chunk.write(bytes(range(100, 116))) is False
        assert await chunk.read() is None, "a write-protected chunk read succeeded - the busy-marker write cannot have happened"

        assert await manager.fram.set_write_protected(value=False) is True
        assert bytes(await chunk.read() or b"") == payload, "the refusal damaged the stored bytes - it is supposed to be an access gate only"

    _on_each(_FRAM_DEVICES, scenario, _RUN_BOUND_S)


def test_storage_pause_short_circuits_before_the_bus_so_an_injected_fault_survives() -> None:
    # Twin-tier form of test_asy_fram_manager.py's ordering test: _read() consults the pause flag before
    # touching SPI, so a queued overrun must still be there afterwards. Uses the bus-level
    # rx_overrun_remaining knob, the only one modelling 1.29's 32-byte DMA threshold (Part F.5.2).
    async def scenario(device: str) -> None:
        module, _watchdog = await _boot(device)
        manager = module.fram
        bus = manager.fram._spidev.spi._spi
        assert bus is not None
        chunk = manager.get_chunk(40, crc=CRC8(), owner="HAZARD_PAUSE_FIRST")  # over the 32 B DMA threshold, so an overrun is reachable
        assert chunk is not None
        payload = bytes(range(40))
        assert await chunk.write(payload)

        bus.rx_overrun_remaining = 1
        manager.set_pause(value=True)
        assert await chunk.read() is None  # refused by the gate
        assert bus.rx_overrun_remaining == 1, "the paused read reached the bus and consumed the injected overrun"

        manager.set_pause(value=False)
        assert await chunk.read() == bytearray(payload)  # absorbed by the block-1 copy
        assert bus.rx_overrun_remaining == 0, "the overrun never fired once the bus was genuinely reachable"

    _on_each(_FRAM_DEVICES, scenario, _RUN_BOUND_S)


def test_storage_pause_does_not_survive_a_simulated_reboot() -> None:
    # FRAMManager.__init__ sets _pause = False and nothing restores it from FRAM, so the pause is RAM-only. The bench
    # tier proves this against a real reboot; this is the CI-gated counterpart, over the same state-file reboot the
    # SGP40 backup-survival test uses: chunk bytes carry across this boundary, the pause flag does not.
    async def scenario(device: str) -> None:
        cfg_path = _scratch.dir()
        machine.configure_fram_state_path(cfg_path + "fram_state.json")
        module, _watchdog = await _boot(device, cfg_path=cfg_path)
        chunk = module.fram.get_chunk(16, crc=CRC8(), owner="HAZARD_REBOOT")
        assert chunk is not None
        payload = bytes(range(16))
        assert await chunk.write(payload)
        module.fram.set_pause(value=True)
        assert module.fram.get_pause() is True
        machine.flush_fram()

        module, _watchdog = await _boot(device, cfg_path=cfg_path)
        assert module.fram.get_pause() is False, "the pause flag survived a reboot - it is supposed to be RAM-only"
        chunk2 = module.fram.get_chunk(16, crc=CRC8(), owner="HAZARD_REBOOT")  # the same owner: its seed must match
        assert chunk2 is not None
        assert bytes(await chunk2.read() or b"") == payload, "the chunk bytes should survive the same reboot the pause flag does not"

    _on_each(_FRAM_DEVICES, scenario, _STATE_RUN_BOUND_S)


def test_a_chunk_another_owner_wrote_reads_blank_after_a_simulated_reboot() -> None:
    # Chunks are found by address and CRC only, so the owner-seeded CRC is what keeps a reflash that moves
    # another owner's chunk onto this address from loading it as this owner's history (SPECIFICATION.md A.4).
    payload = bytes(range(16))

    async def chunk_after_boot(device: str, cfg_path: str, owner: str) -> "FRAMChunk":
        module, _watchdog = await _boot(device, cfg_path=cfg_path)
        chunk: FRAMChunk | None = module.fram.get_chunk(16, crc=CRC8(), owner=owner)
        assert chunk is not None
        return chunk

    async def scenario(device: str) -> None:
        cfg_path = _scratch.dir()
        machine.configure_fram_state_path(cfg_path + "fram_state.json")
        assert await (await chunk_after_boot(device, cfg_path, "HAZARD_OWNER_A")).write(payload)
        machine.flush_fram()

        foreign = await chunk_after_boot(device, cfg_path, "HAZARD_OWNER_B")  # same address, another owner
        assert await foreign.read_into(foreign.get_buffer()) is False, "another owner's chunk did not read blank or invalid"
        assert await foreign.read() is None
        machine.flush_fram()

        own = await chunk_after_boot(device, cfg_path, "HAZARD_OWNER_A")  # control: the bytes were never damaged
        assert bytes(await own.read() or b"") == payload, "the owner's own history did not survive the foreign read"

    _on_each(_FRAM_DEVICES, scenario, _STATE_RUN_BOUND_S)


def test_three_concurrent_sgp40_measurements_each_send_and_read_their_own_words() -> None:
    # The twin leg of the same-device race on the SGP40's shared measure command: three callers with distinct
    # compensation inputs on one instance, on the real twin chip and bus log (Part C.8), per distinct SGP40 wiring.
    assert _sgp40_measure_command(25, 50) == b"\x26\x0f\x80\x00\xa2\x66\x66\x93"  # Table 9's default command
    for device in distinct_wirings("sgp40"):
        _three_concurrent_measurements(device)


def test_a_bus_recovery_does_not_disturb_concurrent_sibling_reads() -> None:
    # The controller rung on the twin chips (Part C.8): recover() clears the bus and rebuilds its controller under the
    # bus lock while every occupant's read loop runs, at every offset into them, on every shared bus. Every sibling
    # read stays valid, the chips survive the re-construction, and no transfer runs inside the recovery.
    for device, bus_name, occupants in _SHARED:
        scl = wiring_plan(device)["pins"][bus_name]["scl"]  # type: ignore[typeddict-item]  # an I2C bus's pins
        for offset in range(_RECOVERY_OFFSETS):
            failures: list[str] = []
            outcome: list[object] = []

            async def scenario(offset: int = offset, failures: "list[str]" = failures, outcome: "list[object]" = outcome, device: str = device, bus_name: str = bus_name, occupants: "list[str]" = occupants, scl: int = scl) -> None:
                bus = _shared_bus(device, bus_name)  # inside the run: an SCD30 chip's refresh timer is a task, ended with it
                fake = bus._i2c
                assert fake is not None
                chips = dict(fake.devices)

                def scl_line(_pin_id: int, _value_log: object) -> int:
                    fake.log.append(("scl-read",))  # every SCL read the clear makes, marked in the bus log itself
                    return 1

                async def recovery() -> int:
                    for _ in range(offset):
                        await asyncio.sleep(0)
                    return await bus.recover()

                machine.Pin.set_external_level(scl, scl_line)  # the bus's SCL, released: the line reads high
                results = await asyncio.gather(recovery(), *(_sibling_reads(device, s, bus, failures) for s in occupants))
                outcome.extend((results[0], bus.recoveries, bus._i2c is fake and fake.devices == chips, [entry[0] for entry in fake.log]))

            try:
                run_timed(scenario(), timeout_s=_RUN_BOUND_S)
            finally:
                machine.Pin.reset_registry()
            status, recoveries, kept, kinds = outcome
            assert status == 0, f"{device} offset {offset}: a healthy bus's recovery reported status {status}"
            assert recoveries == 1, f"{device} offset {offset}: the recovery did not run once"
            assert kept, f"{device} offset {offset}: the re-construction lost the wired chips"
            assert not failures, f"{device} offset {offset}: a sibling read failed beside the recovery: {failures}"
            # This recovery's window runs from the previous rebuild to its own: every SCL read in it must sit in one
            # unbroken run right before the rebuild, so no transfer ran between the clear and the init.
            assert isinstance(kinds, list)
            rebuilt = len(kinds) - 1 - kinds[::-1].index("init")
            previous = rebuilt - 1 - kinds[rebuilt - 1 :: -1].index("init") if "init" in kinds[:rebuilt] else -1
            window = kinds[previous + 1 : rebuilt]
            assert "scl-read" in window, f"{device} offset {offset}: the recovery rebuilt the controller without clearing the bus first"
            first = window.index("scl-read")
            assert window[first:] == ["scl-read"] * (len(window) - first), f"{device} offset {offset}: a transfer ran between the clear's start and the rebuilt controller: {window[first:]}"


# ---------------------------------------------------------------------------
# The participant rungs mid-traffic on the twin chips (SPECIFICATION.md C.7, C.8): on every shared bus carrying the
# rung's chip, its recovery runs at every offset into its siblings' read loops.
# ---------------------------------------------------------------------------


def test_an_scd30_soft_reset_mid_read_leaves_every_twin_sibling_read_valid() -> None:
    async def rung(bus: "asy_i2c_driver.I2C") -> None:
        await SCD30_I2C(bus).reset()

    def check(bus: "asy_i2c_driver.I2C") -> None:
        assert bus._i2c is not None
        assert ("writeto", 0x61, b"\xd3\x04", True) in bus._i2c.log, "the soft reset never reached the SCD30"

    ran = [(d, b) for d, b, o in _SHARED if "scd30" in o]
    for device, bus_name, occupants in _SHARED:
        if "scd30" in occupants:
            _rung_across_offsets(device, bus_name, tuple(s for s in occupants if s != "scd30"), rung, check)
    assert ran, "no generated device shares a bus with an SCD30 - the case covers nothing"


def test_a_bmp3xx_setup_reset_mid_read_leaves_every_twin_sibling_read_valid() -> None:
    # The soft reset each BMP3XX setup sends (0xB6 to CMD, DS001 4.3.22), its cmd_rdy wait and settle included,
    # fired at every offset into its siblings' reads on a shared bus.
    async def rung(bus: "asy_i2c_driver.I2C") -> None:
        await BMP3XX_I2C(bus, address=0x77).reset()

    def check(bus: "asy_i2c_driver.I2C") -> None:
        assert bus._i2c is not None
        assert ("writeto", 0x77, b"\x7e\xb6", True) in bus._i2c.log, "the soft reset never reached the BMP3XX"

    ran = [(d, b) for d, b, o in _SHARED if "bmp3xx" in o]
    for device, bus_name, occupants in _SHARED:
        if "bmp3xx" in occupants:
            _rung_across_offsets(device, bus_name, tuple(s for s in occupants if s != "bmp3xx"), rung, check)
    assert ran, "no generated device shares a bus with a BMP3XX - the case covers nothing"


def test_sgp40_heater_off_mid_read_leaves_every_twin_sibling_read_valid() -> None:
    async def rung(bus: "asy_i2c_driver.I2C") -> None:
        sgp = SGP40_I2C(bus)
        await sgp.turn_heater_off()
        assert await sgp.measure_raw() is not None, "the SGP40 did not measure again after its heater-off"

    def check(bus: "asy_i2c_driver.I2C") -> None:
        assert bus._i2c is not None
        assert ("writeto", 0x59, b"\x36\x15", True) in bus._i2c.log, "the heater-off never reached the SGP40"

    ran = [(d, b) for d, b, o in _SHARED if "sgp40" in o]
    for device, bus_name, occupants in _SHARED:
        if "sgp40" in occupants:
            _rung_across_offsets(device, bus_name, tuple(s for s in occupants if s != "sgp40"), rung, check)
    assert ran, "no generated device shares a bus with an SGP40 - the case covers nothing"


def test_an_isl29125_reapply_mid_read_leaves_every_twin_sibling_read_valid() -> None:
    # The reader's own ladder runs the rung (one W DEVICE_RECOVERY); the chip's configuration then equals the shadow.
    readers: list[ISL29125_Reader] = []

    async def rung(bus: "asy_i2c_driver.I2C") -> None:
        reader = ISL29125_Reader(bus, 16, cfg_path=_scratch.dir())
        readers.append(reader)
        await reader.setup()
        reader._err_cnt_internal = 2  # the streak at the participant rung
        await reader._climb_ladder()

    def check(_bus: "asy_i2c_driver.I2C") -> None:
        reader = readers[-1]
        log = run_timed(reader.get_error_counter(), timeout_s=_RUN_BOUND_S)["ISL29125"]
        assert [log["ErrNum"][i] for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"] == [code("W", "DEVICE_RECOVERY")], log
        snapshot = run_timed(reader._isl.get_config_snapshot(), timeout_s=_RUN_BOUND_S)
        assert bytes(snapshot) == reader._isl.encode_shadow(), "the chip's CONFIG1-3 differ from the shadow after the re-apply"

    ran = [(d, b) for d, b, o in _SHARED if "isl29125" in o]
    for device, bus_name, occupants in _SHARED:
        if "isl29125" in occupants:
            _rung_across_offsets(device, bus_name, tuple(s for s in occupants if s != "isl29125"), rung, check)
    assert ran, "no generated device shares a bus with an ISL29125 - the case covers nothing"


def test_a_sensor_task_cancelled_inside_its_session_leaves_the_bus_usable() -> None:
    # The shutdown cancels each supervised task where it waits (Part C.8): the SGP40's setup and measurement on every
    # shared bus carrying one, cancelled at each turn, its bus and its device session among them. Both locks are free
    # after, the measure command restored, and each sibling's next read and the SGP40's own are valid.
    ran = [(d, b) for d, b, o in _SHARED if "sgp40" in o]
    for device, bus_name, occupants in _SHARED:
        if "sgp40" not in occupants:
            continue
        held = set()
        for turns in range(_CANCEL_TURNS):
            failures: list[str] = []
            state: list[object] = []

            async def scenario(turns: int = turns, failures: "list[str]" = failures, state: "list[object]" = state, device: str = device, bus_name: str = bus_name, occupants: "list[str]" = occupants) -> None:
                bus = _shared_bus(device, bus_name)  # inside the run: an SCD30 chip's refresh timer is a task, ended with it
                sgp = SGP40_I2C(bus)

                async def setup_and_measure() -> "int | None":
                    await sgp.setup()
                    return await sgp.measure_raw()

                cycle = asyncio.create_task(setup_and_measure())
                for _ in range(turns):
                    await asyncio.sleep(0)
                device_lock = sgp._i2c_sgp40.session_lock
                state.extend((bus.bus_lock.locked(), device_lock.locked(), cycle.done()))
                await cancel(cycle)
                where = f"{device} {bus_name}: the SGP40 cancelled {turns} turns in"
                assert not bus.bus_lock.locked(), f"{where}: the bus lock outlived the cancelled session"  # before a sibling waits on it
                assert not device_lock.locked(), f"{where}: the SGP40's session lock outlived its cancel"
                state.append(sgp._command_buffer is sgp._default_command_buffer)
                for sibling in occupants:
                    if sibling != "sgp40":
                        await _sibling_reads(device, sibling, bus, failures, rounds=1)
                state.append(await sgp.measure_raw())

            with FastAsyncSleep():
                run_timed(scenario(), timeout_s=_RUN_BOUND_S)
            held_bus, held_device, ended, restored, again = state
            where = f"{device} {bus_name}: the SGP40 cancelled {turns} turns in"
            assert restored, f"{where}: the measure command stayed staged"
            assert not failures, f"{where}: a sibling's next read failed: {failures}"
            assert again is not None, f"{where}: its own next measurement failed"
            if ended:
                break
            held.add((held_bus, held_device))
        else:
            raise AssertionError(f"{device} {bus_name}: the SGP40's cycle was still running after {_CANCEL_TURNS} turns")
        assert (True, True) in held, f"{device} {bus_name}: no cancel landed inside the SGP40's bus session: {held}"
        assert (False, True) in held, f"{device} {bus_name}: no cancel landed inside its device session alone: {held}"
    assert ran, "no generated device shares a bus with an SGP40 - the case covers nothing"


# ---------------------------------------------------------------------------
# The recovery ladder on the real task graph (SPECIFICATION.md C.7): a reader whose chip keeps failing climbs to
# the bus rungs, each run once per bus however many readers fail, and returns once the fault clears. It runs on the
# shared-bus device whose bus carries an SGP40 and a BMP3XX: the rung counts below assume that pair's speeds.
# ---------------------------------------------------------------------------

_LADDER = [(d, o) for d, _b, o in _SHARED if "sgp40" in o and "bmp3xx" in o]


def test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared() -> None:
    # The SGP40's reads fail until its reader has run the bus clear (its 3rd failed cycle); the BMP3XX on the same
    # bus keeps reading, and once the fault clears both streaks return to 0.
    device = _ladder_device()
    addresses = {a["driver"]: a["address"] for attachments in wiring_plan(device)["buses"].values() for a in attachments}
    module, rungs, clears, rebuilds, w15, kept = run_timed(_ladder_run(device, {addresses["sgp40"]: "readfrom_into"}, 1), timeout_s=_STATE_RUN_BOUND_S)
    assert (rungs, clears, rebuilds, w15) == (1, 1, 0, 1), f"expected one bus clear, no controller rebuild and one W15; got {rungs} rung(s), {clears} clear(s), {rebuilds} rebuild(s), {w15} W15 slot(s)"
    assert kept, "the bus rung lost the wired chips"
    bmp_log = run_timed(module.bmp3xx.get_error_counter(), timeout_s=_RUN_BOUND_S)["BMP3XX"]
    assert bmp_log["ErrCount"] == 0, f"the sibling BMP3XX failed beside the SGP40's fault: {bmp_log}"
    sgp_log = run_timed(module.sgp40.get_error_counter(), timeout_s=_RUN_BOUND_S)["SGP40"]
    heater_offs = [i for i in range(len(sgp_log["ErrNum"])) if sgp_log["ErrType"][i] == "W" and sgp_log["ErrNum"][i] == code("W", "DEVICE_RECOVERY")]
    assert len(heater_offs) == 1, f"the participant rung (heater-off) did not run once before the bus clear: {sgp_log}"


def test_two_failing_readers_on_one_bus_run_each_bus_rung_once() -> None:
    # Both chips of the shared bus fail: the bus gets one clear and one controller rebuild, both readers recover and
    # the chips stay wired. The faster SGP40 reaches both rungs first; a second reader's sharing of a rung its
    # sibling already ran is pinned at the unit tier (test_asy_base_classes.py).
    device = _ladder_device()
    addresses = {a["driver"]: a["address"] for attachments in wiring_plan(device)["buses"].values() for a in attachments}
    _module, rungs, clears, rebuilds, w15, kept = run_timed(_ladder_run(device, {addresses["sgp40"]: "readfrom_into", addresses["bmp3xx"]: "readfrom_mem"}, 2), timeout_s=_STATE_RUN_BOUND_S)
    assert (rungs, clears, rebuilds, w15) == (2, 1, 1, 2), f"expected one clear and one controller rung, each with one W15; got {rungs} rung(s), {clears} clear(s), {rebuilds} rebuild(s), {w15} W15 slot(s)"
    assert kept, "the bus rungs lost the wired chips"


def test_two_setups_failing_together_each_rebuild_the_controller_once_one_after_the_other() -> None:
    # Both chips of the shared bus fail their task's setup once. A sibling session holds the bus lock, so the first
    # rebuild parks on it while the second setup failure reaches _init_failed(): each failed setup still rebuilds the
    # controller once (its own episode), inside the lock one at a time, and the supervisor restarts both in budget.
    device = _ladder_device()
    addresses = {a["driver"]: a["address"] for attachments in wiring_plan(device)["buses"].values() for a in attachments}

    async def until(done: "Callable[[], bool]", what: str) -> None:
        for _ in range(int(_RUN_BOUND_S / _POLL_S)):
            if done():
                return
            await asyncio.sleep(_POLL_S)
        raise AssertionError(what)

    async def scenario() -> "tuple[int, int, int, int, bool]":
        module, watchdog = await _boot(device, port=_ports.next())
        (bus_name,) = [bus for d, bus, _o in _SHARED if d == device]
        bus = getattr(module, bus_name)
        fake = bus._i2c
        assert fake is not None
        chips = dict(fake.devices)
        real_recover: Callable[[], Coroutine[object, object, int]] = bus.recover
        real_clear: Callable[[], Coroutine[object, object, int]] = bus._clear_locked
        rebuilds, inside, arrived = [0], [0, 0, 0], []  # real rebuilds; in the lock now, most at once, beside the sibling; readers at the gate
        sibling, started = [False], [0]  # the test holds the bus lock; rebuilds released from the gate
        go = {reader.pr.name: asyncio.Event() for reader in (module.sgp40, module.bmp3xx)}

        async def counted() -> int:
            rebuilds[0] += 1
            return await real_recover()

        async def held() -> int:
            if sibling[0] or not bus.bus_lock.locked():
                inside[2] += 1  # a rebuild ran beside the sibling's session, or with no lock held
            inside[0] += 1
            inside[1] = max(inside[:2])
            try:
                return await real_clear()
            finally:
                inside[0] -= 1

        for name, wrapper in (("recover", counted), ("_clear_locked", held)):
            setattr(bus, name, wrapper)  # an instance attribute shadowing the method, as _ladder_run's
        for reader in (module.sgp40, module.bmp3xx):

            async def gated(real: "Callable[[], Coroutine[object, object, None]]" = reader._init_failed, name: str = reader.pr.name) -> None:
                arrived.append(name)
                await go[name].wait()
                await real()

            setattr(reader, "_init_failed", gated)  # noqa: B010 - the instance attribute the driver's _init_*() calls
        chips[addresses["sgp40"]].fault.inject_fault("readfrom_into", OSError, errno.EIO, "no ACK", times=1)
        chips[addresses["bmp3xx"]].fault.inject_fault("readfrom_mem", OSError, errno.EIO, "no ACK", times=1)
        feeder = asyncio.get_event_loop().create_task(_feed_watchdog_periodically(watchdog))
        supervisor = await _supervised_graph(module)
        try:
            await until(lambda: len(arrived) == 2, "both setups did not fail")
            mark = bus.recoveries
            await bus.bus_lock.acquire()  # the sibling session
            sibling[0] = True
            for name in arrived:
                go[name].set()
                started[0] += 1
                await until(lambda: bus.recoveries - mark == started[0], f"the rebuild of {name}'s failed setup never started")
            bus.bus_lock.release()
            sibling[0] = False
            while (await module.sgp40.get_data()).VOC is None or (await module.bmp3xx.get_data()).Pres is None:
                await asyncio.sleep(_POLL_S)
            assert watchdog.would_have_triggered_count == 0
            assert not module.sysfunct._reset_armed, "two setup failures spent the restart budget"
            for reader in (module.sgp40, module.bmp3xx):
                log = (await reader.pr.get_log())[reader.pr.name]
                kinds = [(log["ErrType"][i], log["ErrNum"][i]) for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]
                assert kinds == [("E", code("E", "INIT")), ("W", code("W", "BUS_RECOVERY"))], f"{reader.pr.name}: not one rebuild beside its own setup error: {log}"
            kept = fake.devices == chips and all(fake.devices[a] is chips[a] for a in chips)
            return rebuilds[0], inside[1], inside[2], await _w15(module.sgp40, module.bmp3xx), kept
        finally:
            if sibling[0]:
                bus.bus_lock.release()
            await cancel(supervisor)
            await cancel(feeder)
            await _cancel_started_tasks(module)

    rebuilds, most_inside, unlocked, w15, kept = run_timed(scenario(), timeout_s=_STATE_RUN_BOUND_S)
    assert (rebuilds, most_inside, unlocked, w15) == (2, 1, 0, 2), f"expected two rebuilds one at a time inside the bus lock, each with one W15; got {rebuilds} rebuild(s), {most_inside} at once, {unlocked} outside the lock, {w15} W15 slot(s)"
    assert kept, "the rebuilds lost the wired chips"


# ---------------------------------------------------------------------------
# System commands (SPECIFICATION.md Part A.8): each runs the real controlled shutdown on the real graph, stopped at
# its armed reset and torn down from outside. Before each command the chip memory is copied into the test's scratch
# (CLAUDE.md's FRAM-log rule, the twin case).
# ---------------------------------------------------------------------------


async def _w15(*readers: "SensorReader") -> int:
    # W BUS_RECOVERY slots across `readers`' logs: one per bus rung that reader ran.
    total = 0
    for reader in readers:
        log = (await reader.pr.get_log())[reader.pr.name]
        total += sum(1 for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "W" and log["ErrNum"][i] == code("W", "BUS_RECOVERY"))
    return total


async def _wait_established_then_flap_once(conn: "WifiService", chip: "SCD30Chip", bus_log: "BoundedLog[tuple[object, ...]]") -> "tuple[int, int, int, int]":
    # One loss of the ESTABLISHED link, its reconnect scripted to fail so the 60 s retry runs (Part E.5.1), parked on a
    # driven clock for _HOLD_SCD30_CYCLES real SCD30 cycles, then advanced by exactly its length.
    #
    # Returns that length, the bus log's growth and wifi_mode_lock's longest held run while it was open, and the polls;
    # real hardware: test_network_resilience.py.
    while not (conn._wlan.isconnected() and conn._conn_phase == _STA_ESTABLISHED):  # the service's phase, not just the link
        await asyncio.sleep(_ESTABLISHED_POLL_S)
    clock, cycles = DrivenTime(), None
    asy_wifi_service.asyncio = _RetryOnDrivenClock(clock)  # type: ignore[assignment, attr-defined]  # a module attribute swap, restored below
    try:
        conn._wlan.script_connect_outcomes([network.STAT_CONNECT_FAIL])
        conn._wlan.disconnect()
        while not clock.wakes():  # the failed reconnect not yet judged: the retry parks next
            if conn._wlan.isconnected() and not conn._wlan._scripted_outcomes:
                return 0, 0, 0, 0  # back without any retry
            await asyncio.sleep(_RECONNECT_POLL_S)
        logged, run, longest, polls = len(bus_log) + bus_log.dropped, 0, 0, 0
        cycles = asyncio.get_event_loop().create_task(_scd30_cycle(chip, _HOLD_SCD30_CYCLES))
        while not cycles.done():
            run = run + 1 if conn.wifi_mode_lock.locked() else 0
            longest, polls = max(longest, run), polls + 1
            await asyncio.sleep(_RECONNECT_POLL_S)
        await cycles  # its own bound's failure, if it had one
        bus_work, retry_ms = len(bus_log) + bus_log.dropped - logged, clock.wakes()[0] - clock.now
        clock.advance(retry_ms)
        while not conn._wlan.isconnected():
            assert not clock.wakes(), "the retry parked again after its 60 s: it never ended"
            await asyncio.sleep(_RECONNECT_POLL_S)
        return retry_ms, bus_work, longest, polls
    finally:
        asy_wifi_service.asyncio = asyncio  # type: ignore[attr-defined]  # the swap restored
        if cycles is not None:
            await cancel(cycles)


def test_the_erase_racing_a_logger_write_never_tears_a_chunk() -> None:
    # A logger write in flight when the erase starts completes; one after it is refused; the erase then zeroes the
    # whole chip, every unit inside it (no address rollover), and no ring reads back torn.
    async def scenario(device: str) -> None:
        with DrivenTime(*_driven_modules(device), sleeps=True) as clock:  # the boot's waits, released before the race
            module, _watchdog = await _driven(clock, _boot(device, port=_ports.next()))
            sysfunct, chip = module.sysfunct, _chip(module)
            supervisor = await _supervised_graph(module, clock)
            _keep_evidence(chip, "fram_before_erase.bin")
            before = chip.write_count
            units = {addr: chip.writes_at.get(addr, 0) for addr in range(0, chip.size, _ERASE_UNIT)}
            racing = asyncio.get_event_loop().create_task(sysfunct.pr.err_s("in flight at the erase", errno=code("E", "TEST_SEED_A")))
            try:
                assert await sysfunct.erase_fram() is True
                await racing
                assert chip.write_count > before, "the logger write in flight at the erase never landed"
                await _armed(sysfunct)
                erased = chip.write_count
                await sysfunct.pr.err_s("after the erase", errno=code("E", "TEST_SEED_B"))
                assert chip.write_count == erased, "a logger write after the erase reached the chip"
            finally:
                await _tear_down_at_the_armed_reset(sysfunct, supervisor)
                await _cancel_started_tasks(module)
        _assert_no_rollover(chip)
        unwritten = [hex(addr) for addr, count in units.items() if chip.writes_at.get(addr, 0) <= count]
        assert unwritten == [], f"the erase never wrote the units at {unwritten[:4]}: a blank byte there is the old one"
        assert all(byte == 0 for start in range(0, chip.size, 4096) for byte in chip.memory[start : start + 4096]), "the erase left a byte unzeroed - a torn chunk survived it"

    _on_each(_FRAM_DEVICES, scenario, _STATE_RUN_BOUND_S)


def test_the_erase_feeds_the_watchdog_at_bus_speed() -> None:
    # The largest generated FRAM erased at its real wire time (8 us/byte): the sequence's own feeds keep the watchdog
    # fed throughout, and every unit lands below the chip's size.
    plan = _fram_plan_by_size()
    device = plan["device"]

    async def scenario() -> None:
        module, watchdog = await _boot(device, port=_ports.next())
        sysfunct, chip = module.sysfunct, _chip(module)
        supervisor = await _supervised_graph(module)
        _keep_evidence(chip, "fram_before_timed_erase.bin")
        module.fram.fram._spidev.spi._spi.wire_time_us_per_byte = _ERASE_US_PER_BYTE
        try:
            assert await sysfunct.erase_fram() is True
            await _armed(sysfunct)
        finally:
            module.fram.fram._spidev.spi._spi.wire_time_us_per_byte = 0
            await _tear_down_at_the_armed_reset(sysfunct, supervisor)
            await _cancel_started_tasks(module)
        assert watchdog.would_have_triggered_count == 0, f"{device}: the erase at bus speed starved the watchdog"
        _assert_no_rollover(chip)

    run_timed(scenario(), timeout_s=_STATE_RUN_BOUND_S)


def test_no_scd30_write_reaches_the_chip_while_a_system_command_runs() -> None:
    # "No SCD30 write while the sequence runs" (owner, 2026-10-02, paraphrase): from acceptance to the armed reset
    # every SCD30 setter field sent through the path PUT /sensors takes answers "Failed" and the chip's NVM count
    # holds, for each of the four shutdown commands, per distinct SCD30 wiring, after a whole SCD30 cycle writing nothing.
    words = ("reboot", "bootloader", "resetconfig", "erasefram")
    ports = {word: _ports.next() for word in words}  # a word's port, reused by each device: one a boot overruns the band

    async def one(device: str, word: str) -> None:
        with DrivenTime(*_driven_modules(device), sleeps=True) as clock:  # the boot's waits, released before the command
            await _command_on(device, word, clock)

    async def _command_on(device: str, word: str, clock: DrivenTime) -> None:
        module, _watchdog = await _driven(clock, _boot(device, port=ports[word]))
        scd30 = module.scd30
        ((bus_name, address),) = [(bus, a["address"]) for bus, attachments in sorted(wiring_plan(device)["buses"].items()) for a in attachments if a["driver"] == "scd30"][:1]
        bus = machine.peripheral(bus_name)
        assert isinstance(bus, machine.I2C)
        chip = bus.devices[address]
        body: dict[str, object] = {}
        for name, kind, _default, low, _high, _choices in scd30.get_cfg_schema():
            body[name] = True if kind == "bool" else (low + 1.0 if kind == "float" else low + 1)
        supervisor = await _supervised_graph(module, clock)
        try:
            if word == words[0]:  # once: the healthy window, a whole SCD30 cycle writing no NVM at all
                writes = chip.nvm_writes
                await _scd30_cycle(chip)
                assert chip.nvm_writes == writes, f"{device}: the SCD30 wrote its NVM in an ordinary cycle"
            _keep_evidence(_chip(module), "fram_before_" + word + ".bin")
            writes = chip.nvm_writes
            assert await module._system_cmd_callback(word) is True, f"{device}: {word} was not accepted"
            while not module.sysfunct._reset_armed:
                results = await scd30._set_dict_cfg(body, scd30.get_cfg_schema())
                assert set(results.values()) == {"Failed"}, f"{device}: {word}: a setter answered {results} during the sequence"
                await asyncio.sleep(_POLL_S)
            assert chip.nvm_writes == writes, f"{device}: {word}: the SCD30's NVM was written during the sequence"
        finally:
            await _tear_down_at_the_armed_reset(module.sysfunct, supervisor)
            await _cancel_started_tasks(module)

    def on_each_device(word: str) -> "Callable[[str], Coroutine[object, object, None]]":
        return lambda device: one(device, word)

    for word in words:
        _on_each(distinct_wirings("scd30"), on_each_device(word), _STATE_RUN_BOUND_S)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
