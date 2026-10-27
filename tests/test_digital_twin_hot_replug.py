"""A sensor re-plugged on a running unit recovers without a reboot: the task ends, the supervisor restarts it, setup()
runs again (owner, 2026-07-13, paraphrase). Each bus-attached driver on one device the generated plans wire it on, alone
on its supervisor; FRAM's re-plug is tests/test_digital_twin_fram.py's booted silent-chip case."""

import sys

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_idle_poll import skip_idle_flag_polls
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")
skip_idle_flag_polls()  # no 1 ms poll wait per step while a flag waits, as on rp2 (digital_twin/README.md "unix_port_idle_poll.py")

import asyncio  # noqa: E402 - imported after the prewarm and the UDP shim

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _task_names import task_names_of  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import distinct_wirings, generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import ModuleType
    from typing import Protocol, TypeVar

    from launch import _Plan
    from machine import WDT

    from asy_base_classes import TaskStarter, TimerStarter
    from asy_print_log import PrintLogHistory

    T = TypeVar("T")

    class SensorReader(Protocol):
        # What a test here asks of a bus-attached reader: its starters, its log and its sample.
        _datastruct: object
        pr: "PrintLogHistory"

        def get_task_starters(self) -> "list[TaskStarter]": ...
        def get_timer_starters(self) -> "list[TimerStarter]": ...
        def get_trigger_starters(self) -> "list[TimerStarter]": ...

# @tunable l2.hot_replug_wait_s = 40.0
_WAIT_S = 40.0
# @tunable l2.hot_replug_run_bound_s = 90.0
_RUN_BOUND_S = 90.0
# The reading field that proves a driver read (as the bus-hazard tier's _I2C_DRIVER_HEALTH_FIELD).
_HEALTH_FIELD = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}

_scratch = TmpScratch("dt_hot_replug")
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)


def _attached_drivers() -> "list[str]":
    # Every I2C driver some generated plan wires, in name order.
    return sorted({a["driver"] for device in generated_devices() for attachments in wiring_plan(device)["buses"].values() for a in attachments})


async def _boot(module: "ModuleType", device: str) -> "WDT":
    # A new board on the device's plan: construction, the runner's UART pollers, then the setup list.
    plan = wiring_plan(device)
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(plan)
    cfg_path = _scratch.dir()
    write_offline_ntp_config(cfg_path)
    write_error_level_config(cfg_path)
    watchdog = boot_entry_watchdog(module, device)
    await module.build_system(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0)
    runner_plan: _Plan = cast("_Plan", plan)
    run_generic_integration._wire_uart_crossover(module, runner_plan)
    await module.sysfunct.run_setups(module._collect_setups())
    return watchdog


async def _driven(clock: "DrivenTime", what: str, coro: "Coroutine[object, object, T]") -> "T":
    # `coro` as a task, the driven clock elapsed until it ends: a step whose own sleeps run on that clock.
    task = asyncio.get_event_loop().create_task(coro)
    await _until(clock, what, task.done)
    return await task


def _driven_modules() -> "list[object]":
    # Every src service and driver holding asyncio, and the twin's machine (its Timers, WDT, chip clocks) and network:
    # one clock for all of them, so a tick one module reads is diffed by another on the same clock.
    return [m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio]


def _power_cycled_bmp3xx_on(device: str) -> None:
    # The test above on one device.
    plan = wiring_plan(device)
    ((bus_name, attachment),) = [(bus, a) for bus, attachments in sorted(plan["buses"].items()) for a in attachments if a["driver"] == "bmp3xx"][:1]

    async def scenario(module: "ModuleType", clock: "DrivenTime") -> None:
        watchdog = await _driven(clock, f"{device}'s boot never finished", _boot(module, device))
        reader = module.bmp3xx
        bus = machine.peripheral(bus_name)
        assert isinstance(bus, machine.I2C)
        chip = bus.devices[attachment["address"]]

        async def body() -> None:
            sysfunct = module.sysfunct
            await _until(clock, f"{device}'s BMP3XX never read", lambda: reader._datastruct.Pres is not None)
            osr, config = chip._osr, chip._config
            tasks = list(sysfunct._tasks)
            chip.power_cycle()
            before = reader._datastruct
            await _until(clock, f"{device}'s BMP3XX never read after the power cycle", lambda: reader._datastruct is not before and reader._datastruct.Pres is not None)
            log = (await reader.get_error_counter())["BMP3XX"]
            resets = [log["ErrNum"][i] for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "W"]
            assert resets == [code("W", "BMP_CHIP_RESET")], f"{device}: the power cycle left {log}"
            assert (chip._osr, chip._config) == (osr, config), f"{device}: OSR/CONFIG {chip._osr:#x}/{chip._config:#x} after the reset, not {osr:#x}/{config:#x}"
            assert list(sysfunct._tasks) == tasks, "a task ended over the power cycle"
            assert watchdog.would_have_triggered_count == 0

        await _supervised(clock, module, reader, body)

    run_timed(_run_on_clock(device, scenario), timeout_s=_RUN_BOUND_S)


def _replug(driver: str) -> None:
    for device in distinct_wirings(driver):
        machine.reset_test_state()  # the file's per-test reset: a run never inherits the previous device's board
        network.reset_test_state()
        _replug_on(device, driver)


def _replug_on(device: str, driver: str) -> None:
    # One device's replug of the driver's chip.
    plan = wiring_plan(device)
    ((bus_name, attachment),) = [(bus, a) for bus, attachments in sorted(plan["buses"].items()) for a in attachments if a["driver"] == driver][:1]
    key = driver + ("_" + attachment["name_ext"] if attachment["name_ext"] else "")
    field = _HEALTH_FIELD[driver]

    async def scenario(module: "ModuleType", clock: "DrivenTime") -> None:
        watchdog = await _driven(clock, f"{device}'s boot never finished", _boot(module, device))
        reader = getattr(module, key)
        bus = machine.peripheral(bus_name)
        assert isinstance(bus, machine.I2C)

        def read_after(before: object) -> "Callable[[], bool]":
            return lambda: reader._datastruct is not before and getattr(reader._datastruct, field) is not None

        async def body() -> None:
            sysfunct = module.sysfunct
            await _until(clock, f"{device}'s {key} never read before the unplug", read_after(None))
            first = list(sysfunct._tasks)
            bus.unplug(attachment["address"])
            await _until(clock, f"{device}'s {key} task never ended while its chip was unplugged", lambda: any(t is not None and t.done() for t in first))
            bus.plug(attachment["address"])
            ended = [i for i, t in enumerate(first) if t is not None and t.done()]
            await _until(clock, f"{device}'s {key} task was never restarted", lambda: all(sysfunct._tasks[i] not in (None, first[i]) for i in ended))
            await _until(clock, f"{device}'s {key} never read again after the re-plug", read_after(reader._datastruct))
            assert not sysfunct._reset_armed and machine.reset_count == 0, f"{device}: the re-plug of {key} armed a reset"
            assert watchdog.would_have_triggered_count == 0, f"{device}: the re-plug of {key} starved the watchdog"

        await _supervised(clock, module, reader, body)

    run_timed(_run_on_clock(device, scenario), timeout_s=_RUN_BOUND_S)


async def _run_on_clock(device: str, scenario: "Callable[[ModuleType, DrivenTime], Coroutine[object, object, None]]") -> None:
    # `scenario` on the device's module, booted and run on one driven clock (tests/_fake_time.py), the modules put back
    # after. A UART-wired plan too: its link reads wire time off the twin's plain clock, digital_twin/_flash_stall.py's
    # plain_us() (agent, 2026-10-22).
    module = load_device(device)
    with DrivenTime(*_driven_modules(), sleeps=True) as clock:
        await scenario(module, clock)


async def _supervised(clock: "DrivenTime", module: "ModuleType", reader: "SensorReader", body: "Callable[[], Coroutine[object, object, None]]") -> None:
    # The reader's own tasks and read trigger under the real supervisor, its value sources (an SGP40's compensation
    # inputs) running unsupervised beside it.
    sysfunct = module.sysfunct
    sources: list[SensorReader] = []
    for ref in (getattr(reader, "_temperature", None), getattr(reader, "_humidity", None)):
        if ref is not None and all(ref.source is not known for known in sources):
            sources.append(ref.source)
    feeding = [starter() for source in sources for starter in source.get_task_starters()]
    for source in sources:
        for starter in source.get_trigger_starters() + source.get_timer_starters():
            starter()
    await _driven(clock, "the reader's tasks never started", sysfunct.start_tasks(reader.get_task_starters(), task_names=task_names_of(reader)))
    await _driven(clock, "the reader's timers never started", sysfunct.start_timers(reader.get_trigger_starters(), reader.get_timer_starters()))
    supervisor = asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())
    try:
        await body()
    finally:
        for task in feeding:
            await cancel(task)
        await cancel(supervisor)
        if sysfunct._supervisor_task is not None:
            await cancel(sysfunct._supervisor_task)
        for task in sysfunct._tasks:
            if task is not None:
                await cancel(task)


async def _until(clock: "DrivenTime", what: str, condition: "Callable[[], bool]") -> None:
    # The driven clock elapsed wake by wake until `condition` holds, within _WAIT_S.
    try:
        await clock.run_until(condition, int(_WAIT_S * 1000))
    except AssertionError as e:
        raise AssertionError(f"{what} - {e}") from None


def test_every_bus_attached_driver_recovers_from_a_replug_without_a_reboot() -> None:
    drivers = _attached_drivers()
    assert drivers, "no generated plan wires an I2C chip"
    for driver in drivers:
        _replug(driver)


def test_a_power_cycled_bmp3xx_is_reconfigured_without_a_ladder_step() -> None:
    # A supply blip resets OSR/CONFIG behind the driver's back: the next cycle notices, persists one W BMP_CHIP_RESET
    # and writes its stored settings back; the task never ends (SPECIFICATION.md C.7's chip-reset row).
    for device in distinct_wirings("bmp3xx"):
        machine.reset_test_state()  # the file's per-test reset: a run never inherits the previous device's board
        network.reset_test_state()
        _power_cycled_bmp3xx_on(device)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
