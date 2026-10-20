"""rp2's 16-alarm pool exhausted under the generated graph of the device named by TEST_DEVICE: each failed arm is handled
in place, none reboots (the uptime timer's rule: owner, 2026-07-18, paraphrase; a reader's: SPECIFICATION.md C.9). The
Timer finaliser case is not reachable here (digital_twin/README.md fidelity table)."""

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
import time  # noqa: E402 - imported after the prewarm and the UDP shim

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_const  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Protocol, TypeVar

    from launch import _Plan
    from machine import WDT

    from asy_base_classes import TaskStarter, TimerStarter
    from asy_print_log import ErrorLog

    T = TypeVar("T")

    class SensorReader(Protocol):
        # What a test here asks of a bus-attached reader: its starters, its timer's stop, its log and its sample.
        _datastruct: object

        def get_task_starters(self) -> "list[TaskStarter]": ...
        def get_timer_starters(self) -> "list[TimerStarter]": ...
        def get_trigger_starters(self) -> "list[TimerStarter]": ...
        async def get_error_counter(self) -> "ErrorLog": ...
        def stop_timer(self) -> None: ...

_POOL = 16  # rp2's alarm pool: digital_twin/machine.py's _ALARM_POOL_SIZE
_RR_STARVE_ARM_FAILED = src_const("src/asy_system_service.py", "_RR_STARVE_ARM_FAILED")
_RR_MAGIC = src_const("src/asy_system_service.py", "_RR_MAGIC")
# @tunable l2.timer_pool_wait_s = 20.0
_WAIT_S = 20.0
# @tunable l2.timer_pool_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
_POLL_S = 0.1  # how often a wait below looks again
# The reading field that proves a driver read (as the bus-hazard tier's _I2C_DRIVER_HEALTH_FIELD).
_HEALTH_FIELD = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}

_scratch = TmpScratch("dt_timer_pool_" + device)  # per device: two devices' jobs of this file may run at once
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
module = load_device(device)
plan = wiring_plan(device)


def _any_ended(tasks: "list[asyncio.Task[None] | None]") -> "Callable[[], bool]":
    def check() -> bool:
        return any(task is not None and task.done() for task in tasks)

    return check


async def _boot(pool_free: int) -> "WDT":
    # A new board with `pool_free` alarms left: construction, the runner's UART pollers, then the setup list.
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(plan)
    machine.set_alarm_pool_free(pool_free)
    cfg_path = _scratch.dir()
    write_offline_ntp_config(cfg_path)
    write_error_level_config(cfg_path)
    watchdog = boot_entry_watchdog(module, device)
    await module.build_system(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0)
    runner_plan: _Plan = cast("_Plan", plan)
    run_generic_integration._wire_uart_crossover(module, runner_plan)
    await module.sysfunct.run_setups(module._collect_setups())
    return watchdog


async def _errors(source: object, number: int) -> int:
    # How many slots of `source`'s persisted history hold E `number`.
    log = await source.get_error_counter()  # type: ignore[attr-defined]  # every product module has it
    (entry,) = log.values()
    return sum(1 for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "E" and entry["ErrNum"][i] == number)


def _read_after(reader: "SensorReader", before: object, field: str) -> "Callable[[], bool]":
    # True once the reader stored a sample after `before` carrying its health field.
    def check() -> bool:
        return reader._datastruct is not before and getattr(reader._datastruct, field) is not None

    return check


def _readers() -> "list[tuple[str, SensorReader]]":
    # Every plan instance whose reader arms a read trigger of its own: the trigger list's and the SCD30's timer.
    found = []
    for attachments in plan["buses"].values():
        for attachment in attachments:
            key = attachment["driver"] + ("_" + attachment["name_ext"] if attachment["name_ext"] else "")
            found.append((key, getattr(module, key)))
    return sorted(found, key=lambda pair: pair[0])  # a MicroPython dict keeps no order: the plan's buses come unsorted


def _restarted(first: "list[asyncio.Task[None] | None]", ended: "list[int]") -> "Callable[[], bool]":
    # True once the supervisor replaced every task of `ended` (indices into `first`, the tasks as they started).
    def check() -> bool:
        return all(module.sysfunct._tasks[i] not in (None, first[i]) for i in ended)

    return check


def _sources(reader: "SensorReader") -> "list[SensorReader]":
    # The readers whose values `reader` reads (its ValueRef inputs).
    sources: list[SensorReader] = []
    for ref in (getattr(reader, "_temperature", None), getattr(reader, "_humidity", None)):
        if ref is not None and all(ref.source is not known for known in sources):
            sources.append(ref.source)
    return sources


def _start_sources(reader: "SensorReader") -> "list[asyncio.Task[None]]":
    # `reader`'s sources running unsupervised: their tasks, their armed timers.
    sources = _sources(reader)
    tasks = [starter() for source in sources for starter in source.get_task_starters()]
    for source in sources:
        for starter in source.get_trigger_starters() + source.get_timer_starters():
            starter()
    return tasks


async def _stop_graph(supervisor: "list[asyncio.Task[None]]") -> None:
    sysfunct = module.sysfunct
    for task in supervisor:
        await cancel(task)
    if sysfunct._supervisor_task is not None:
        await cancel(sysfunct._supervisor_task)
    for task in sysfunct._tasks:
        if task is not None:
            await cancel(task)
    conn = getattr(module, "conn", None)
    if conn is not None and conn._dns_server_task is not None:  # started inside the WiFi service, not by start_tasks()
        await cancel(conn._dns_server_task)


async def _supervise(starters: "list[Callable[[], asyncio.Task[None]]]", triggers: "list[Callable[[], None]]", timers: "list[Callable[[], None]]") -> "list[asyncio.Task[None]]":
    # The named tasks and timers under the real supervisor, as main() starts them; returns the supervisor's task.
    sysfunct = module.sysfunct
    await sysfunct.start_tasks(starters)
    await sysfunct.start_timers(triggers, timers)
    return [asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())]


async def _until(what: str, condition: "Callable[[], bool]") -> None:
    waited = 0.0
    while not condition():
        if waited >= _WAIT_S:
            raise AssertionError(f"{device}: {what} - not within {_WAIT_S} s")
        await asyncio.sleep(_POLL_S)
        waited += _POLL_S


def test_a_reader_whose_trigger_cannot_arm_ends_restarts_and_reads_once_the_pool_frees() -> None:
    # Per reader, alone on its supervisor: the failed arm ends its task with one E TIMER, the supervisor restarts it,
    # and once the pool frees it reads. One at a time: every reader dying at once overruns the restart budget (below).
    async def scenario() -> None:
        watchdog = await _boot(_POOL)
        sysfunct = module.sysfunct
        for key, reader in _readers():
            feeding: list[asyncio.Task[None]] = []
            machine.set_alarm_pool_free(0)
            supervisor = await _supervise(reader.get_task_starters(), reader.get_trigger_starters(), reader.get_timer_starters())
            try:
                first = list(sysfunct._tasks)
                await _until(key + "'s task never ended on its failed arm", _any_ended(first))
                ended = [i for i, t in enumerate(first) if t is not None and t.done()]
                await _until(key + "'s task was never restarted", _restarted(first, ended))
                assert await _errors(reader, code("E", "TIMER")) >= 1, f"{device}: {key} persisted no E TIMER for its failed arm"
                machine.set_alarm_pool_free(_POOL)
                field = _HEALTH_FIELD[key.split("_", 1)[0]]
                before = reader._datastruct
                feeding = _start_sources(reader)  # an SGP40 measures only with its compensation inputs live
                await _until(key + " never read once the pool freed", _read_after(reader, before, field))
            finally:
                for task in feeding:
                    await cancel(task)
                await _stop_graph(supervisor)
                for armed in [reader] + _sources(reader):  # their alarms back to the pool before the next reader's case
                    armed.stop_timer()
            assert not sysfunct._reset_armed and machine.reset_count == 0, f"{device}: {key}'s failed arm armed a reset"
        assert watchdog.would_have_triggered_count == 0

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_the_tick_timers_degrade_in_place_and_rearm_once_the_pool_frees() -> None:
    # SYSTEM's uptime runs on its one-second fallback with one E TIMER (the boot signature it feeds resolves only after
    # system.ntp_wait_s offline); once the pool frees, SYSTEM's, NTP's and WiFi's tick timers re-arm. No reset arms.
    async def scenario() -> None:
        watchdog = await _boot(_POOL)
        sysfunct, ntp, conn = module.sysfunct, module.ntp, module.conn
        machine.set_alarm_pool_free(0)
        modules = (sysfunct, ntp, conn)
        supervisor = await _supervise([s for m in modules for s in m.get_task_starters()], [], [s for m in modules for s in m.get_timer_starters()])
        await ntp.ntp_force_sync()  # main()'s first sync request: the sync loop's wake, where it retries its arms
        try:
            uptime = await sysfunct.get_uptime()
            await _until("SYSTEM's uptime stood still on its fallback", lambda: sysfunct._uptime.read() > uptime)
            assert sysfunct._tick_failed is True, "the uptime tick armed from an empty pool"
            assert await _errors(sysfunct, code("E", "TIMER")) == 1, f"{device}: SYSTEM's failed uptime arm is not one E TIMER"
            assert (ntp._check_armed, ntp._tick_armed, conn._tick_armed) == (False, False, False), "a tick timer armed from an empty pool"
            machine.set_alarm_pool_free(_POOL)
            await _until("SYSTEM's uptime tick never re-armed", lambda: not sysfunct._tick_failed)
            await _until("NTP's timers never re-armed", lambda: ntp._tick_armed is True and ntp._check_armed is True)
            await _until("WiFi's uptime tick never re-armed", lambda: conn._tick_armed is True)
            assert not sysfunct._reset_armed and machine.reset_count == 0, f"{device}: an exhausted pool armed a reset"
            assert watchdog.would_have_triggered_count == 0
        finally:
            await _stop_graph(supervisor)

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_a_reboot_whose_reset_timer_cannot_arm_starves_the_watchdog_instead() -> None:
    # The reboot command with the pool empty: the shutdown runs, its one-shot cannot arm, so feeding stops for good and
    # the record reads 6; nothing calls machine.reset() itself (owner, 2026-09-30, paraphrase).
    async def scenario() -> None:
        watchdog = await _boot(_POOL)
        sysfunct = module.sysfunct
        supervisor = await _supervise(module._collect_task_starters(), module._collect_trigger_starters(), module._collect_timer_starters())
        try:
            machine.set_alarm_pool_free(0)
            assert await sysfunct.reboot_system() is True
            await _until("the shutdown sequence never finished", lambda: sysfunct._shutdown_task is not None and sysfunct._shutdown_task.done())
            assert sysfunct._force_watchdog_starve is True, "the failed arm left the watchdog fed"
            record = machine.mem_backup(0)
            assert (record[0], record[1]) == (_RR_MAGIC, _RR_STARVE_ARM_FAILED), [hex(word) for word in record]
            last_feed = watchdog.feed_times[-1]
            await _until("the starved watchdog never ran out", lambda: watchdog.would_have_triggered_count >= 1)
            took = time.ticks_diff(time.ticks_ms(), last_feed)
            assert took <= watchdog.timeout + 1000, f"{device}: the watchdog ran out {took} ms after the last feed"
            assert (machine.reset_count, machine.bootloader_count) == (0, 0), "the starve fallback reset the board itself"
        finally:
            sysfunct._reset_timer.deinit()  # asserted at the armed point: the in-process graph never takes the reset
            if sysfunct._reset_task is not None:
                await cancel(sysfunct._reset_task)
            await _stop_graph(supervisor)

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_mempause_with_the_pool_empty_answers_and_pauses() -> None:
    # The pause arms no timer (its end is a deadline the uptime pass tests), so an empty pool changes nothing; the 300 s
    # unpause itself is the unit tier's (tests/test_asy_system_service.py), this tier has no clock to drive SYSTEM's.
    if "fram" not in plan["instances"]:
        raise microtest.Skip(f"{device} wires no FRAM to pause")

    async def scenario() -> None:
        await _boot(_POOL)
        machine.set_alarm_pool_free(0)
        assert await module._system_cmd_callback("mempause") is True
        assert module.fram.get_pause() is True, "mempause left the storage running"

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
