"""rp2's 16-alarm pool exhausted under the generated graph of the device named by TEST_DEVICE: each failed arm is
handled in place, none reboots (the uptime timer's rule: owner, 2026-07-18, paraphrase; a reader's:
SPECIFICATION.md C.9). The Timer finaliser case is not reachable here (digital_twin/README.md fidelity table)."""

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
from _async_harness import cancel, run, track_starts  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime, driven_modules  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_const, src_int  # noqa: E402 - imported after the prewarm and the UDP shim
from _task_names import task_names_of  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

_PHASE_ARMED, _PHASE_STARVED = (src_int("src/asy_system_service.py", f"_PHASE_{n}") for n in ("ARMED", "STARVED"))

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Protocol, TypeVar

    from machine import WDT
    from run_generic_integration import _Plan

    from asy_base_classes import TaskStarter, TimerStarter
    from asy_print_log import ErrorLog, PrintLogHistory

    T = TypeVar("T")

    class SensorReader(Protocol):
        # What a test here asks of a bus-attached reader: its starters, its timer's stop, its log and its sample.
        _datastruct: object
        pr: "PrintLogHistory"

        def get_task_starters(self) -> "list[TaskStarter]": ...
        def get_timer_starters(self) -> "list[TimerStarter]": ...
        def get_trigger_starters(self) -> "list[TimerStarter]": ...
        async def get_error_counter(self) -> "ErrorLog": ...
        def stop_timer(self) -> None: ...

_POOL = 16  # rp2's alarm pool: digital_twin/machine.py's _ALARM_POOL_SIZE
_RR_STARVE_ARM_FAILED = src_const("src/asy_system_service.py", "_RR_STARVE_ARM_FAILED")
_RR_MAGIC = src_const("src/asy_system_service.py", "_RR_MAGIC")
_WAIT_S = 20.0
_POLL_S = 0.1  # how often a real-time wait below looks again
# Soft callbacks lost in one spell: every callback of about three seconds of the booted graph (a count, no wait), so each
# one-second timer loses its ticks; _FAST_PERIOD_MS is the period of those (rp2's 1 s ticks, C.9).
_SPELL_CALLBACKS = 32
_FAST_PERIOD_MS = 1000
# The reading field that proves a driver read (as the bus-hazard tier's _I2C_DRIVER_HEALTH_FIELD).
_HEALTH_FIELD = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}

_scratch = TmpScratch("dt_timer_pool_" + device)  # per device: two devices' jobs of this file may run at once
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
module = load_device(device)
plan = wiring_plan(device)


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


def _count_fires(timers: "list[machine.Timer]") -> "list[int]":
    # Each timer's callback wrapped to count its fires into the list returned, in `timers`' order.
    fired = [0] * len(timers)
    for index, timer in enumerate(timers):
        callback = timer.callback

        def counted(armed: "machine.Timer", index: int = index, callback: "Callable[[machine.Timer], None] | None" = callback) -> None:
            fired[index] += 1
            if callback is not None:
                callback(armed)

        timer.callback = counted
    return fired


async def _driven(clock: "DrivenTime", what: str, coro: "Coroutine[object, object, T]") -> "T":
    # `coro` as a task, the driven clock elapsed until it ends: a step whose own sleeps run on that clock.
    task = asyncio.get_event_loop().create_task(coro)
    await _until(clock, what, task.done)
    return await task


async def _error_counts() -> "dict[str, int]":
    # Every ErrCount GET /status reports: each registered error source's logs and the webserver's own.
    webserver = module.webserver
    counts: dict[str, int] = {}
    for source in list(webserver._error_sources.values()) + [webserver]:
        for name, entry in (await source.get_error_counter()).items():
            counts[name] = entry["ErrCount"]
    return counts


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


async def _run_on_clock(scenario: "Callable[[DrivenTime], Coroutine[object, object, None]]") -> None:
    # `scenario` booted and run on one driven clock (tests/_fake_time.py), the modules put back after. A UART-wired plan
    # too: its link reads wire time off the twin's plain clock, digital_twin/_flash_stall.py's plain_us() (agent, 2026-10-22).
    with DrivenTime(*driven_modules(), sleeps=True) as clock:
        await scenario(clock)


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


async def _supervise(starters: "list[Callable[[], asyncio.Task[None]]]", names: "list[str]", triggers: "list[Callable[[], None]]", timers: "list[Callable[[], None]]") -> "list[asyncio.Task[None]]":
    # The named tasks and timers under the real supervisor, as main() starts them; returns the supervisor's task.
    sysfunct = module.sysfunct
    await sysfunct.start_tasks(starters, task_names=names)
    await sysfunct.start_timers(triggers, timers)
    return [asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())]


async def _until(clock: "DrivenTime | None", what: str, condition: "Callable[[], bool]", bound_ms: "int | None" = None) -> None:
    # The driven clock elapsed wake by wake until `condition` holds (within bound_ms, else _WAIT_S), or with none a
    # real-time poll; within _WAIT_S.
    if clock is not None:
        try:
            await clock.run_until(condition, int(_WAIT_S * 1000) if bound_ms is None else bound_ms)
        except AssertionError as e:
            raise AssertionError(f"{device}: {what} - {e}") from None
        return
    waited = 0.0
    while not condition():
        if waited >= _WAIT_S:
            raise AssertionError(f"{device}: {what} - not within {_WAIT_S} s")
        await asyncio.sleep(_POLL_S)
        waited += _POLL_S


def test_an_empty_alarm_pool_leaves_the_tick_cadences_running_and_arms_no_reset() -> None:
    # SYSTEM's, WiFi's and NTP's cadences are deadline sleeps, no Timer: with the pool empty, SYSTEM's uptime passes
    # still run, nothing is persisted for them, and no reset arms.
    async def scenario(clock: "DrivenTime") -> None:
        watchdog = await _driven(clock, "the boot never finished", _boot(_POOL))
        sysfunct, ntp, conn = module.sysfunct, module.ntp, module.conn
        machine.set_alarm_pool_free(0)
        modules = (sysfunct, ntp, conn)
        supervisor = await _driven(clock, "SYSTEM's, NTP's and WiFi's tasks never started", _supervise([s for m in modules for s in m.get_task_starters()], task_names_of(*modules), [], [s for m in modules for s in m.get_timer_starters()]))
        try:
            uptime = await sysfunct.get_uptime()
            await _until(clock, "SYSTEM's uptime stood still while its tick was unarmed", lambda: sysfunct._uptime.read() > uptime)
            assert await _errors(sysfunct, code("E", "TIMER")) == 0, f"{device}: SYSTEM persisted its failed uptime arm"
            machine.set_alarm_pool_free(_POOL)
            assert sysfunct._phase < _PHASE_ARMED and machine.reset_count == 0, f"{device}: an exhausted pool armed a reset"
            assert watchdog.would_have_triggered_count == 0
        finally:
            await _stop_graph(supervisor)

    run(_run_on_clock(scenario))


def test_a_full_scheduler_queue_loses_every_soft_callback_for_a_spell_and_every_timer_fires_again() -> None:
    # rp2's depth-8 soft-callback queue full for a spell (the twin's drop_next_soft_callbacks, every callback in it lost):
    # afterwards every periodic product timer armed before it keeps firing, every reader reads again, nothing logs and no
    # reset arms.
    armed: list[machine.Timer] = []
    real_init = machine.Timer.init

    def recording_init(timer: "machine.Timer", *args: object, **kwargs: object) -> None:
        real_init(timer, *args, **kwargs)  # type: ignore[arg-type]  # the twin Timer's own keywords, passed through
        if timer._pool and timer.mode == machine.Timer.PERIODIC and timer not in armed:
            armed.append(timer)

    async def scenario(clock: "DrivenTime") -> None:
        watchdog = await _driven(clock, "the boot never finished", _boot(_POOL))
        sysfunct = module.sysfunct
        supervisor = await _driven(clock, "the graph never started", _supervise(module._collect_task_starters(), module._collect_task_names(), module._collect_trigger_starters(), module._collect_timer_starters()))
        try:
            fired = _count_fires(armed)
            fast = [i for i, timer in enumerate(armed[: len(fired)]) if timer.period <= _FAST_PERIOD_MS]
            await _until(clock, "a one-second timer never fired before the spell", lambda: all(fired[i] for i in fast))
            for key, reader in _readers():  # each first read before the counts, the SGP40's boot-owed W SGP_NO_BACKUP with it
                await _until(clock, key + " never read before the spell", _read_after(reader, None, _HEALTH_FIELD[key.split("_", 1)[0]]))
            counts, spell_start = await _error_counts(), list(fired)
            machine.Timer.drop_next_soft_callbacks = _SPELL_CALLBACKS
            await _until(clock, "the spell's callbacks were never all lost", lambda: machine.Timer.drop_next_soft_callbacks == 0)
            spell_end, samples = list(fired), {key: reader._datastruct for key, reader in _readers()}
            # Every callback in the spell was lost: a one-second timer fired at most once, in the wake that ended it.
            assert all(spell_end[i] - spell_start[i] <= 1 for i in fast), f"{device}: fires went on in the spell: {spell_start} -> {spell_end}"

            # Each once more, a one-second one twice, so a timer its first wake after the spell stopped is caught.
            def refired() -> bool:
                return all(n >= m + (2 if i in fast else 1) for i, (n, m) in enumerate(zip(fired, spell_end)))

            await _until(clock, "a periodic timer stopped firing after the spell", refired, 2 * max(timer.period for timer in armed[: len(fired)]))
            for key, reader in _readers():
                await _until(clock, key + " never read again after the spell", _read_after(reader, samples[key], _HEALTH_FIELD[key.split("_", 1)[0]]))
            assert await _error_counts() == counts, f"{device}: the lost callbacks were logged: {counts} -> {await _error_counts()}"
            assert sysfunct._phase < _PHASE_ARMED and machine.reset_count == 0 and watchdog.would_have_triggered_count == 0, f"{device}: the spell ended in a reset"
        finally:
            await _stop_graph(supervisor)

    machine.Timer.init = recording_init  # type: ignore[assignment, method-assign]  # the class's own, put back in finally
    try:
        run(_run_on_clock(scenario))
    finally:
        machine.Timer.init = real_init  # type: ignore[method-assign]


def test_a_reboot_whose_reset_timer_cannot_arm_starves_the_watchdog_instead() -> None:
    # The reboot command with the pool empty: the shutdown runs, its one-shot cannot arm, so feeding stops for good and
    # the record reads 6; nothing calls machine.reset() itself (owner, 2026-09-30, paraphrase). Real time throughout:
    # `took` measures the run-out against the twin WDT's own clock (agent, 2026-10-22).
    async def scenario() -> None:
        watchdog = await _boot(_POOL)
        sysfunct = module.sysfunct
        sequences = track_starts(sysfunct, "_shutdown_sequence")
        supervisor = await _supervise(module._collect_task_starters(), module._collect_task_names(), module._collect_trigger_starters(), module._collect_timer_starters())
        try:
            machine.set_alarm_pool_free(0)
            assert await sysfunct.reboot_system() is True
            await _until(None, "the shutdown sequence never finished", lambda: bool(sequences) and sequences[-1].done())
            assert sysfunct._phase == _PHASE_STARVED, "the failed arm left the watchdog fed"
            record = machine.mem_backup(0)
            assert (record[0], record[1]) == (_RR_MAGIC, _RR_STARVE_ARM_FAILED), [hex(word) for word in record]
            last_feed = watchdog.feed_times[-1]
            await _until(None, "the starved watchdog never ran out", lambda: watchdog.would_have_triggered_count >= 1)
            took = time.ticks_diff(time.ticks_ms(), last_feed)
            assert took <= watchdog.timeout + 1000, f"{device}: the watchdog ran out {took} ms after the last feed"
            assert (machine.reset_count, machine.bootloader_count) == (0, 0), "the starve fallback reset the board itself"
        finally:
            sysfunct._reset_timer.deinit()  # asserted at the armed point: the in-process graph never takes the reset
            if sysfunct._reset_task is not None:
                await cancel(sysfunct._reset_task)
            await _stop_graph(supervisor)

    run(scenario())


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

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
