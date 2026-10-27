"""A held I2C line under the generated graph of the device named by TEST_DEVICE, planted with Pin.set_external_level():
the boot clear frees it before construction, the bus rungs reach a held SCL at runtime, and each bus reports it once
(SPECIFICATION.md F.2)."""

import errno
import os
import sys

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

PER_DEVICE = True
_device = os.getenv("TEST_DEVICE")
if not _device:
    raise RuntimeError("run through scripts/test.sh, or set TEST_DEVICE to one of devices/*.toml")
device: str = _device

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
from _src_const import src_int  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Protocol, TypeVar

    from launch import _Plan
    from machine import WDT

    from asy_print_log import PrintLogHistory

    T = TypeVar("T")

    class SensorReader(Protocol):
        # What a test here asks of a bus-attached reader: its sample, its streak and its log.
        _datastruct: object
        _err_cnt_internal: int
        pr: "PrintLogHistory"

    class Transfer(Protocol):
        # One of machine.I2C's transfer methods, whatever its arguments.
        def __call__(self, *args: object, **kwargs: object) -> object: ...


_REC_SDA_LOW = src_int("src/asy_i2c_driver.py", "_REC_SDA_LOW")
_REC_SCL_HELD = src_int("src/asy_i2c_driver.py", "_REC_SCL_HELD")
_RELEASE_AFTER = 3  # SCL pulses before the slave lets SDA go: a byte cut short mid-transfer
# @tunable l2.held_i2c_line_wait_s = 60.0
_WAIT_S = 60.0
# @tunable l2.held_i2c_line_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
# The reading field that proves a driver read (as the bus-hazard tier's _I2C_DRIVER_HEALTH_FIELD).
_HEALTH_FIELD = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}
_TRANSFERS = ("readfrom_into", "readfrom_mem", "writeto", "writeto_mem")  # every machine.I2C transfer; readfrom_mem_into delegates

_scratch = TmpScratch("dt_held_line_" + device)  # per device: two devices' jobs of this file may run at once
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
module = load_device(device)
plan = wiring_plan(device)


def _buses() -> "list[str]":
    return sorted(plan["buses"])  # a MicroPython dict keeps no order


async def _construct() -> "WDT":
    # build_system() on the lines as the test planted them, with the boot entry's watchdog.
    cfg_path = _scratch.dir()
    write_offline_ntp_config(cfg_path)
    write_error_level_config(cfg_path)
    watchdog = boot_entry_watchdog(module, device)
    await module.build_system(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0)
    return watchdog


async def _driven(clock: "DrivenTime", what: str, coro: "Coroutine[object, object, T]") -> "T":
    task = asyncio.get_event_loop().create_task(coro)
    await _until(clock, what, task.done)
    return await task


def _failing_while(held: "list[bool]", real: "Transfer") -> "Transfer":
    # A transfer on a held SCL: rp2's controller waits out its timeout and ends ETIMEDOUT (machine_i2c.c:150-152).
    def transfer(*args: object, **kwargs: object) -> object:
        if held[0]:
            raise OSError(errno.ETIMEDOUT)
        return real(*args, **kwargs)

    return transfer


def _line(bus_name: str, line: str) -> int:
    # The GPIO of an I2C bus's "scl" or "sda" line in the plan.
    return cast("dict[str, int]", plan["pins"][bus_name])[line]


def _new_board() -> None:
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.Pin.reset_registry()  # every line released and every value log empty before the plant
    machine.configure_wiring(plan)


def _on_clock(scenario: "Callable[[DrivenTime], Coroutine[object, object, T]]") -> "T":
    # One driven clock for every src module holding asyncio and the twin's machine and network (as the timer-pool tier).
    async def run() -> "T":
        with DrivenTime(*[m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio], sleeps=True) as clock:
            return await scenario(clock)

    return run_timed(run(), timeout_s=_RUN_BOUND_S)


def _read_since(readers: "list[tuple[str, SensorReader]]", marks: "dict[str, object]") -> "Callable[[], bool]":
    # True once every reader's streak is 0 and it stored a sample after its mark carrying its health field.
    def check() -> bool:
        return all(r._err_cnt_internal == 0 and r._datastruct is not marks.get(d) and getattr(r._datastruct, _HEALTH_FIELD[d]) is not None for d, r in readers)

    return check


def _readers(*bus_names: str) -> "list[tuple[str, SensorReader]]":
    found = []
    for bus_name in bus_names:
        for attachment in plan["buses"][bus_name]:
            key = attachment["driver"] + ("_" + attachment["name_ext"] if attachment["name_ext"] else "")
            found.append((attachment["driver"], getattr(module, key)))
    return found


def _recording(seen: "list[int]", real: "Callable[[], Coroutine[object, object, int]]") -> "Callable[[], Coroutine[object, object, int]]":
    async def rung() -> int:
        status = await real()
        seen.append(status)
        return status

    return rung


async def _reports(bus_name: str) -> int:
    # W BUS_RECOVERY slots across the bus's readers' logs: one per report.
    total = 0
    for _driver, reader in _readers(bus_name):
        log = (await reader.pr.get_log())[reader.pr.name]
        total += sum(1 for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "W" and log["ErrNum"][i] == code("W", "BUS_RECOVERY"))
    return total


async def _start() -> "asyncio.Task[None]":
    runner_plan: _Plan = cast("_Plan", plan)
    run_generic_integration._wire_uart_crossover(module, runner_plan)  # before the setups (CLAUDE.md "Known hang cause")
    sysfunct = module.sysfunct
    await sysfunct.run_setups(module._collect_setups())
    await sysfunct.start_tasks(module._collect_task_starters(), task_names=module._collect_task_names())
    await sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
    return asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())


async def _stop_graph(supervisor: "asyncio.Task[None]") -> None:
    sysfunct = module.sysfunct
    await cancel(supervisor)
    for task in sysfunct._tasks:
        if task is not None:
            await cancel(task)
    conn = getattr(module, "conn", None)
    if conn is not None and conn._dns_server_task is not None:  # started inside the WiFi service, not by start_tasks()
        await cancel(conn._dns_server_task)


async def _until(clock: "DrivenTime", what: str, condition: "Callable[[], bool]") -> None:
    try:
        await clock.run_until(condition, int(_WAIT_S * 1000))
    except AssertionError as e:
        raise AssertionError(f"{device}: {what} - {e}") from None


async def _boot_and_report(clock: "DrivenTime", plant: "Callable[[], None]", release: "Callable[[], None]") -> "dict[str, tuple[int, int, int, int]]":
    # A new board with `plant` on its lines; per bus: the boot clear's status, the SCL lows and all drives it put on
    # the lines, then, with `release` run and every reader read once, its readers' W BUS_RECOVERY reports.
    _new_board()
    plant()
    await _driven(clock, "the construction never finished", _construct())
    found: dict[str, tuple[int, int, int, int]] = {}
    for bus_name in _buses():
        scl, sda = (machine.Pin.value_log(_line(bus_name, line)) for line in ("scl", "sda"))
        found[bus_name] = (getattr(module, bus_name)._boot_clear_status, list(scl).count(0), len(scl) + len(sda), 0)
    release()
    supervisor = await _driven(clock, "the setups and the graph never started", _start())
    try:
        await _until(clock, "a reader never read after the held boot", _read_since(_readers(*_buses()), {}))
        for bus_name in _buses():
            found[bus_name] = found[bus_name][:3] + (await _reports(bus_name),)
    finally:
        await _driven(clock, "the graph never stopped", _stop_graph(supervisor))
    return found


def test_a_bus_held_at_power_up_is_clocked_free_before_construction_and_reported_once() -> None:
    # Every bus's slave holds SDA from power-up and lets go after _RELEASE_AFTER pulses: the boot clear frees it
    # before the controller takes the pins, the bus is built, and its first reader reports it once.
    freed_unbuilt: dict[str, bool] = {}

    def holding(bus_name: str) -> "Callable[[int, object], int]":
        port, scl = int(bus_name[len("i2c") :]), _line(bus_name, "scl")

        def sda_level(_pin: int, _log: object) -> int:
            if list(machine.Pin.value_log(scl)).count(0) < _RELEASE_AFTER:
                return 0
            freed_unbuilt.setdefault(bus_name, port not in machine._I2C_OBJECTS)
            return 1

        return sda_level

    def plant() -> None:
        for bus_name in _buses():
            machine.Pin.set_external_level(_line(bus_name, "sda"), holding(bus_name))

    found = _on_clock(lambda clock: _boot_and_report(clock, plant, lambda: None))
    for bus_name in _buses():
        where = f"{device} {bus_name}"
        status, lows, _drives, reports = found[bus_name]
        assert status == _REC_SDA_LOW, f"{where}: the boot clear returned {status}, expected {_REC_SDA_LOW} (SDA low, freed)"
        assert lows == _RELEASE_AFTER + 1, f"{where}: SCL driven low {lows} times, expected {_RELEASE_AFTER} pulses and the STOP"
        assert freed_unbuilt.get(bus_name) is True, f"{where}: the slave was freed after the controller took the pins ({freed_unbuilt})"
        assert reports == 1, f"{where}: {reports} W BUS_RECOVERY reports, expected one by its first reader"
        assert getattr(module, bus_name)._boot_clear_status == 0, f"{where}: the boot status was never taken"


def test_a_scl_held_at_power_up_pulses_nothing_and_is_reported_as_held() -> None:
    # Every bus's slave holds SCL and SDA from power-up: the boot clear waits out the bus timeout and drives neither
    # line, construction proceeds, and once the slave lets go (its own reset or a power cycle) the first reader reports it.
    async def scenario(clock: "DrivenTime") -> "dict[str, tuple[int, int, int, int]]":
        def spinning(_pin: int, _log: object) -> int:
            clock.advance(1)  # the boot clear's synchronous wait: the driven clock moves a millisecond per read of the line
            return 0

        def hold(scl: "int | Callable[[int, object], int]", sda: int) -> "Callable[[], None]":
            def plant() -> None:
                for bus_name in _buses():
                    machine.Pin.set_external_level(_line(bus_name, "scl"), scl)
                    machine.Pin.set_external_level(_line(bus_name, "sda"), sda)

            return plant

        return await _boot_and_report(clock, hold(spinning, 0), hold(1, 1))

    found = _on_clock(scenario)
    for bus_name in _buses():
        where = f"{device} {bus_name}"
        status, _lows, drives, reports = found[bus_name]
        assert status == _REC_SCL_HELD, f"{where}: the boot clear returned {status}, expected {_REC_SCL_HELD} (SCL held)"
        assert drives == 0, f"{where}: the boot clear drove a held bus's lines {drives} time(s), expected none"
        assert reports == 1, f"{where}: {reports} W BUS_RECOVERY reports, expected one by its first reader"


def test_a_slave_holding_scl_at_runtime_gets_a_clear_that_pulses_nothing_then_one_controller_rebuild() -> None:
    # The busiest bus's SCL held under the supervised graph: its transfers end ETIMEDOUT, the bus clear waits out the
    # timeout and pulses nothing, one controller rung rebuilds it; once the slave lets go, every reader on it recovers.
    bus_name = max(_buses(), key=lambda b: (len(plan["buses"][b]), b))
    scl = _line(bus_name, "scl")

    async def scenario(clock: "DrivenTime") -> "tuple[list[int], list[int], int, int, int, list[int], int]":
        _new_board()
        watchdog = await _driven(clock, "the construction never finished", _construct())
        readers = _readers(bus_name)  # this construction's readers
        bus = getattr(module, bus_name)
        held = [False]
        for name in _TRANSFERS:
            setattr(bus._i2c, name, _failing_while(held, getattr(bus._i2c, name)))
        clears: list[int] = []
        rebuilds: list[int] = []
        bus.clear = _recording(clears, bus.clear)  # each rung's status, recorded
        bus.recover = _recording(rebuilds, bus.recover)
        inits: list[object] = []
        real_init = bus.init

        def init(*args: object) -> None:
            inits.append(args)
            real_init(*args)

        bus.init = init  # each controller re-construction, counted
        supervisor = await _driven(clock, "the setups and the graph never started", _start())
        try:
            await _until(clock, "a reader on the bus never read before the hold", _read_since(readers, {}))
            mark, reported = bus.recoveries, await _reports(bus_name)
            log = machine.Pin.value_log(scl)
            drives = len(log) + log.dropped  # the value log is a ring: its len() stops at its capacity
            held[0] = True
            machine.Pin.set_external_level(scl, 0)
            await _until(clock, "the bus never ended its controller rung", lambda: len(rebuilds) > 0)  # recoveries steps before the rung runs
            new = len(log) + log.dropped - drives
            lows_while_held = list(log)[len(log) - new :] if new else []
            held[0] = False
            machine.Pin.set_external_level(scl, 1)
            marks = {d: r._datastruct for d, r in readers}
            await _until(clock, "a reader on the bus never recovered once SCL was let go", _read_since(readers, marks))
            return clears, rebuilds, bus.recoveries - mark, await _reports(bus_name) - reported, len(inits), lows_while_held, watchdog.would_have_triggered_count
        finally:
            await _driven(clock, "the graph never stopped", _stop_graph(supervisor))

    clears, rebuilds, rungs, reports, inits, lows, missed = _on_clock(scenario)
    where = f"{device} {bus_name}"
    assert clears == [_REC_SCL_HELD], f"{where}: bus clears returned {clears}, expected one reporting SCL held ({_REC_SCL_HELD})"
    assert (rebuilds, inits) == ([_REC_SCL_HELD], 1), f"{where}: controller rungs returned {rebuilds} with {inits} re-construction(s), expected one, SCL held, rebuilt once"
    assert (rungs, reports) == (2, 2), f"{where}: {rungs} bus rung(s) and {reports} W BUS_RECOVERY report(s), expected two of each"
    assert 0 not in lows, f"{where}: a clear drove the held SCL low ({lows})"
    assert missed == 0, f"{where}: the watchdog would have fired {missed} time(s)"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
