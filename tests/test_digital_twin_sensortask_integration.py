"""In-process twin tier for the device named by TEST_DEVICE: its generated graph booted on the twin buses with no HTTP
(requests are driven host-side by scripts/_digital_twin_scenarios.py). Driver-specific scenarios run only on the device
tests/_twin_devices.py picks for them (SPECIFICATION.md E.2.1)."""

import asyncio
import gc
import os
import sys
import time

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why
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

import _wall_clock  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import machine  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import network  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import unix_port_unretrieved_report  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _async_harness import cancel, release_finished, run  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _fast_sleep import check_sleep_ms  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _src_const import src_const, src_int  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _twin_common import Walk  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _twin_devices import device_with, generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _twin_readiness import wait_for_value  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)

import asy_base_classes  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_system_service  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_wifi_service  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from asy_scd30_driver import SCD30  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from asy_sgp40_driver import SGP40  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from asy_uart_comm import ROLE_INITIATOR, UARTComm  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    from launch import _Plan

    from asy_base_classes import TaskStarter, TickSeconds
    from asy_fram_manager import FRAMChunkTimestampedBuffer
    from asy_neopixel_driver import NeopixelDriver
    from asy_sgp40_driver import SGP40_Reader
    from asy_system_service import SystemService
    from asy_wifi_service import WifiService

    T = TypeVar("T")

# Each wait counts its polls or loop yields, so no scenario carries a wall-clock bound a slow host would trip (agent,
# 2026-10-20); a hang is the per-file timeout's (scripts/test.sh), whose abort line names the test.
# @tunable l2.sensortask_integration_wait_poll_s = 0.25
_WAIT_POLL_S = 0.25
# @tunable l2.sensortask_integration_wait_timeout_s = 5.0
_WAIT_TIMEOUT_S = 5.0
# @tunable l2.sensortask_integration_restart_wait_timeout_s = 6.0
_RESTART_WAIT_TIMEOUT_S = 6.0
# Five real failure cycles at the WiFi loop's 5 s period, then the hotspot's own settles.
# @tunable l2.sensortask_integration_hotspot_wait_timeout_s = 40.0
_HOTSPOT_WAIT_TIMEOUT_S = 40.0
# @tunable l2.sensortask_integration_bind_poll_s = 0.01
_BIND_POLL_S = 0.01
# @tunable l2.sensortask_integration_window_wait_s = 10.0
_WINDOW_WAIT_S = 10.0
# @tunable l2.wdt_overrun_wait_s = 9.0
_WDT_OVERRUN_WAIT_S = 9.0
# @tunable l2.sensortask_integration_idle_window_s = 3.0
_IDLE_WINDOW_S = 3.0
_POLL_IDLE_MS = src_const("src/asy_udp_socket.py", "_POLL_IDLE_MS")
_STA_ESTABLISHED = src_const("src/asy_wifi_service.py", "_PHASE_STA_ESTABLISHED")
_RUNG_AT = src_int("src/asy_base_classes.py", "_RECOVER_DEVICE_AT")  # consecutive failed iterations to the device rung
_WIFI_STEP_MS = src_int("src/asy_wifi_service.py", "_STA_CONNECT_POLL_MS")  # the connect poll's step: _SteppedWifiAsyncio's cap
_WAIT_TIMEOUT_MS = int(_WAIT_TIMEOUT_S * 1000)
_STATUS_DEATHS = 10
_DECAY_PASSES = 110  # clean supervisor passes between two deaths: each decays the restart budget by one, a death adds 100
_PASS_YIELD_BOUND = 20000  # loop yields allowed for one wait below; a pass costs a few with the supervisor's fast sleep
# The collected heap across the deaths, in-loop with every real task live: measured within 64 B at both GC stages,
# while keeping each dead task and its exception measured 2.4 KB over the nine after the baseline (2026-10-14).
_HEAP_DRIFT_BYTES = 2048
# Per death between the least of three settled readings and the least of the last three: 0 B on every device at both
# stages, 72 B with a planted 16-byte bytearray per death (agent, 2026-10-20); the bound leaves two GC blocks of slack.
_DRIFT_SLOPE_BYTES = 32
_SETTLED_DEATH = 3  # the readings before it still settle: the second and third hold up to 0.8 KB the fourth does not
# @tunable l2.sensortask_integration_heap_floor_reads = 3
_FLOOR_READS = 3
# A seeded SCD30 reading: the compensation the SGP40 reads before it measures.
_SCD30_READING = SCD30(800, 22.0, 45.0, None, None, None, None, None)

_scratch = TmpScratch("dtsi_" + device)  # per device: two devices' jobs of this file may run at once
_ports = PortAllocator("dtsi", device)  # a fresh port per boot avoids any TIME_WAIT reuse flakiness
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
module = load_device(device)
plan = wiring_plan(device)
_links: "list[machine.UARTLink]" = []  # the booted device's jumpered UART link, when its plan wires one


async def _backup_now(sgp: "SGP40_Reader") -> None:
    # On a running read task past its init: the very next cycle reaches the 60-cycle threshold. Its write is seen to its
    # end through a wrapper around the chunk's own write_into(), and at the chunk's first block on the twin chip.
    chip = module.fram.fram._spidev.spi._spi.device
    storage = sgp._ts_storage
    assert chip is not None and storage is not None
    block = storage._block_addr[0]
    written = chip.writes_at.get(block, 0)
    real_write = storage.write_into
    results: list[tuple[bool, bool, int | None]] = []

    async def write_into(buf: "FRAMChunkTimestampedBuffer", *, require_ntp: bool = False) -> "tuple[bool, bool, int | None]":
        result = await real_write(buf, require_ntp=require_ntp)
        results.append(result)
        return result

    storage.write_into = write_into  # type: ignore[method-assign]  # the instance's own, deleted in finally
    try:
        sgp._backup_counter = 59  # BackupPeriod 1 (minute): the next cycle backs up
        sgp._read_event.set()
        assert await _wait_until(lambda: bool(results), timeout_s=_WAIT_TIMEOUT_S), "the real VOC backup write never completed"
    finally:
        del storage.write_into
    assert results[0][0] and chip.writes_at.get(block, 0) > written, f"the VOC backup write {results[0]} never reached its chunk"


async def _boot(port: int, cfg_path: "str | None" = None) -> "machine.WDT":
    # A new board on the device's plan, then the generated main()'s first steps: build_system() with the watchdog the
    # boot entry arms (the offline NTP config and ERROR_LEVEL first), the runner's UART pollers, the setup list.
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(plan)
    cfg = cfg_path if cfg_path is not None else _scratch.dir()
    write_offline_ntp_config(cfg)
    write_error_level_config(cfg)
    watchdog = boot_entry_watchdog(module, device)
    await module.build_system(watchdog=watchdog, cfg_path=cfg, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=port)
    runner_plan: _Plan = cast("_Plan", plan)
    link = run_generic_integration._wire_uart_crossover(module, runner_plan)  # before the setups (CLAUDE.md "Known hang cause")
    _links[:] = [] if link is None else [link]
    await module.sysfunct.run_setups(module._collect_setups())
    return watchdog


def _clear_twin_logs(watchdog: "machine.WDT") -> None:
    # The twin's routine bookkeeping (bus transactions, line levels, feeds, register accesses, frames, WLAN calls) emptied:
    # nothing in a running twin reads it, and it fills over minutes. A would-have-reset's log is evidence and stays.
    for name in plan["buses"]:
        cast("machine.I2C", machine.peripheral(name)).log.clear()
    for name in plan["spi"]:
        cast("machine.SPI", machine.peripheral(name)).log.clear()
    for log in machine.Pin._value_logs.values():
        log.clear()
    for wlan in network._INTERFACES.values():
        wlan.config_calls.clear()
        wlan.connect_calls.clear()
    module.neopixel._pixel.writes.clear()  # every devices/*.toml wires one
    watchdog.feed_times.clear()
    machine.mem32.log.clear()


class _CountingPoller:
    # A socket's real poller with each ipoll() round counted: one per listener wake-up.
    def __init__(self, real: object) -> None:
        self._real = real
        self.rounds = 0

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)

    def ipoll(self, timeout: int = -1) -> object:
        self.rounds += 1
        return self._real.ipoll(timeout)  # type: ignore[attr-defined]  # a select.poll's own


async def _co2_above(limit: int) -> bool:
    co2 = (await module.scd30.get_data()).CO2
    return co2 is not None and co2 > limit


def _driver_specific(*drivers: str) -> None:
    # A driver-specific scenario runs on the one device the plans pick for its drivers; every module's L1 suite covers
    # each device that wires it.
    chosen = device_with(*drivers)
    if device != chosen:
        raise microtest.Skip(f"runs on {chosen}, the first device wiring {list(drivers)}")


async def _feed_watchdog_periodically(watchdog: "machine.WDT") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


def _fill_wire_logs() -> None:
    # The twin wire keeps up to 4 kB of delivered bytes a direction, growing until full: filled once, its later bytes
    # overwrite in place, so a running link's log is no heap drift.
    for link in _links:
        for end in link.endpoints:
            log = link.direction_from(end).wire_log
            log.extend(bytes(log.maxlen))


def _first_device_only() -> None:
    # A scenario of seconds of wall clock through a mechanism every device shares runs once, on the first generated
    # device, as the driver-specific ones run on the device picked for them (SPECIFICATION.md E.2.1).
    first = generated_devices()[0]
    if device != first:
        raise microtest.Skip(f"runs on {first}, the first generated device: every device runs the same mechanism")


async def _heap_floor(watchdog: "machine.WDT") -> int:
    # The collected heap with no task caught mid-call, read between UART link exchanges: the least of a few readings (a
    # frame held mid-await is transient, a retained object is in every one). The harness's own finished tasks and the
    # twin's routine logs go first, with no await before the reading: neither is the device's heap.
    initiators = [s for s in module._collect_error_sources() if isinstance(s, UARTComm) and s._role == ROLE_INITIATOR]
    floor = -1
    for _ in range(_FLOOR_READS):
        idle = await _wait_until(lambda: not any(comm._busy for comm in initiators), timeout_s=_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S)
        assert idle, "a UART link exchange never ended"
        release_finished()
        _clear_twin_logs(watchdog)
        gc.collect()
        used = gc.mem_alloc()
        floor = used if floor < 0 else min(floor, used)
        await asyncio.sleep(0)
    return floor


async def _hotspot_boot() -> "tuple[WifiService, NeopixelDriver, list[asyncio.Task[None]]]":
    # SSID written, every connect scripted to fail: the boot streak fails for real until the hotspot opens. Returns the
    # WiFi service, its LED's pixel driver and the tasks started (the overlay, the connect loop).
    await _boot(_ports.next())
    conn, pixel = module.conn, module.neopixel
    persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
    assert persisted
    conn._wlan.script_connect_outcomes([network.STAT_NO_AP_FOUND] * 8)  # more than the streak to the hotspot needs
    tasks = [pixel.start_asy_overlay(), conn.start_asy_connect()]
    started = await _wait_until(lambda: conn._dns_server_task is not None, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S)
    assert started, "real hotspot activation never started the real DNSServer task"
    bound = await _wait_until(lambda: conn._dns_server._udps.connected, timeout_s=_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S)
    assert bound, "the real DNSServer never bound its port 53 socket"
    return conn, pixel, tasks


async def _one_backup(sgp: "SGP40_Reader", then: "Callable[[], Coroutine[object, object, None]] | None" = None) -> None:
    # One real VOC backup through the real chain: the read task started, its init done, one backup; `then` runs on the
    # same task before it is cancelled.
    task = sgp.start_asy_read()
    try:
        assert await wait_for_value(lambda: sgp._voc_init, 1, _WAIT_TIMEOUT_MS), "the SGP40 never finished its init"
        await _backup_now(sgp)
        if then is not None:
            await then()
    finally:
        await cancel(task)


def _radio_rung_bound_s(conn: "WifiService") -> float:
    # The fault to the link back at the service's own waits as _SteppedWifiAsyncio caps them: each failed iteration and
    # the one that joins at most a refresh, a join polled to its budget and the retry wait, the rung's three settles, a tick.
    def stepped(name: str) -> int:  # one of the service's whole-second waits, in ms as the stand-in caps it
        return min(src_int("src/asy_wifi_service.py", name) * 1000, _WIFI_STEP_MS)

    poll_budget = src_int("src/asy_wifi_service.py", "_STA_CONNECT_POLL_ITERS") * _WIFI_STEP_MS
    iteration = stepped("_WIFI_REFRESH_S") + poll_budget + stepped("_STA_RETRY_AFTER_LOSS_S")
    settles = stepped("_WLAN_DOWN_SETTLE_S") + stepped("_WLAN_DEINIT_SETTLE_S") + stepped("_WLAN_MODE_SETTLE_S")
    return ((_RUNG_AT + 1) * iteration + settles + conn._counter_timer.period) / 1000  # the uptime tick, armed in ms


def _red_frames(frames: "list[list[tuple[int, ...]]]") -> "list[list[tuple[int, ...]]]":
    return [frame for frame in frames if frame[0][0] > 0 and frame[0][1] == 0 and frame[0][2] == 0]


async def _restore(sgp: "SGP40_Reader", what: str) -> None:
    task = sgp.start_asy_read()
    try:
        assert await wait_for_value(lambda: sgp._voc_init, 1, _WAIT_TIMEOUT_MS), "the SGP40 never finished its init"
        sgp._read_event.set()
        assert await _wait_until(lambda: sgp._restored_from is not None, timeout_s=_WAIT_TIMEOUT_S), f"the real VOC backup restore never completed {what}"
    finally:
        await cancel(task)


async def _seed_compensation() -> None:
    # The SCD30's reading the SGP40 compensates with, seeded through the store a real read cycle uses.
    await module.scd30._set_meas_data(_SCD30_READING)


class _FastSupervisorAsyncio:
    # asy_system_service's view of asyncio, its sleeps reduced to one yield, so the supervisor's two-second pass
    # takes one; every other module keeps the real sleeps. While `hold` is set the supervisor parks in its sleep.
    def __init__(self) -> None:
        self.hold = False
        self.parked = False
        self._release = asyncio.Event()

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    def release(self) -> None:
        self.hold = False
        self._release.set()

    async def sleep(self, _seconds: float) -> None:
        if self.hold:
            self.parked = True
            await self._release.wait()
            self._release.clear()
            self.parked = False
        else:
            await asyncio.sleep(0)

    async def sleep_ms(self, ms: int) -> None:
        check_sleep_ms(ms)
        await asyncio.sleep(0)


class _ReportTap:
    # Checks each of the PC report's two outputs and passes it on to the real console. Counts rather than keeps
    # them: a kept exception or dead task would read as heap drift.
    def __init__(self) -> None:
        self.reported = 0
        self.traced = 0
        self.wrong: list[object] = []

    def __enter__(self) -> "_ReportTap":
        unix_port_unretrieved_report.print = self._print  # type: ignore[attr-defined]
        unix_port_unretrieved_report.sys = self  # type: ignore[assignment, attr-defined]
        return self

    def __exit__(self, *exc_info: object) -> None:
        del unix_port_unretrieved_report.print  # type: ignore[attr-defined]
        unix_port_unretrieved_report.sys = sys  # type: ignore[attr-defined]

    def _print(self, *args: object) -> None:
        if args == (unix_port_unretrieved_report.MARKER, "Task exception wasn't retrieved"):
            self.reported += 1
        else:
            self.wrong.append(args)
        print(*args)

    def print_exception(self, exc: BaseException) -> None:
        if isinstance(exc, RuntimeError) and exc.args == ("injected status fault",):
            self.traced += 1
        else:
            self.wrong.append(exc)
        sys.print_exception(exc)


class _StatusFault:
    # Stands in for SystemService._uptime: a read from the status task raises, so it dies at its next wake-up; any
    # other reader (the supervisor's task-end record) reads the real count.
    def __init__(self, real: "TickSeconds", status_task: "Callable[[], asyncio.Task[None] | None]") -> None:
        self._real, self._status_task = real, status_task

    def read(self) -> int:
        if asyncio.current_task() is self._status_task():
            raise RuntimeError("injected status fault")
        return self._real.read()


class _SteppedWifiAsyncio:
    # asy_wifi_service's view of asyncio, each sleep or sleep_ms at most one connect-poll step: its periods, settles,
    # retry wait and LED pattern are not under test, its transitions are; the poll keeps its real step, unstepped.
    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    async def sleep(self, seconds: float) -> None:
        await self.sleep_ms(int(seconds * 1000))  # asyncio's own conversion (extmod/asyncio/core.py)

    async def sleep_ms(self, ms: int) -> None:
        check_sleep_ms(ms)
        await asyncio.sleep_ms(min(ms, _WIFI_STEP_MS))


def test_sgp40_reading_before_scd30_has_measured_yet_logs_no_bogus_error() -> None:
    # Regression test for the SGP40 boot-race false error (SPECIFICATION.md Part C.14.2), found through a real
    # digital-twin CI run. Driver-specific (SGP40 compensated by an SCD30): its L1 suite covers every device. No
    # seeded SCD30 data: the point is the real startup race, the SCD30's Temp/Hum still None.
    _driver_specific("sgp40", "scd30")

    async def scenario() -> None:
        await _boot(_ports.next())
        sgp = module.sgp40
        assert (await module.scd30.get_data()).Temp is None  # the race precondition holds
        await sgp.pr.setup()
        buf, serialize, deserialize, _cfg_values = await sgp._check_storage()
        data, compensated, _serialized = await sgp._read_sgp(buf, serialize=serialize, deserialize=deserialize)
        assert compensated is False  # scd30 genuinely hasn't measured yet - real, expected timing
        assert data == SGP40(None, None, None, None)
        log = await sgp.get_error_counter()
        assert log["SGP40"]["ErrCount"] == 0, f"expected startup jitter must not log any E/W entry ({log!r})"

    run(scenario())


def test_watchdog_is_never_starved_while_every_real_task_runs_concurrently() -> None:
    # Watchdog escalation (owner, 2026-08-13, paraphrase: an automated assertion here, and a manually observable run
    # through digital_twin/run_generic_integration.py). The setup list fed once per unit; then every real task and
    # timer beside a feed loop of its own for just over one watchdog period, never a would-have-reset.
    async def scenario() -> None:
        watchdog = await _boot(_ports.next())
        stamps = list(watchdog.feed_times)
        assert watchdog.feed_count == len(module._collect_setups()) == len(stamps), (watchdog.feed_count, len(stamps))
        assert all(time.ticks_diff(stamps[i + 1], stamps[i]) >= 0 for i in range(len(stamps) - 1)), stamps
        await module.sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
        tasks = [starter() for starter in module._collect_task_starters()]
        tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(watchdog)))
        try:
            await asyncio.sleep(_WDT_OVERRUN_WAIT_S)  # just over the watchdog's timeout: a real stall would show
            assert watchdog.would_have_triggered_count == 0
        finally:
            for task in tasks:
                await cancel(task)
            if module.conn._dns_server_task is not None:  # started inside the WiFi service, never by this test
                await cancel(module.conn._dns_server_task)

    run(scenario())


def test_the_supervisor_restarts_a_real_dead_task() -> None:
    # A task of the real, full _collect_task_starters() list dies and the real supervisor rediscovers and restarts it.
    async def scenario() -> None:
        await _boot(_ports.next())
        sysfunct: SystemService = module.sysfunct
        task_starters = module._collect_task_starters()
        started: dict[int, list[asyncio.Task[None] | None]] = {}
        real_start_task = asy_system_service.SystemService._start_task

        async def _tracking_start_task(self: "SystemService", starter: "TaskStarter", n: int) -> "asyncio.Task[None] | None":
            # Observes the supervisor's own (re)starts without changing them (_sensortask_scenarios.py's class-wrap).
            task = await real_start_task(self, starter, n)
            started.setdefault(n, []).append(task)
            return task

        asy_system_service.SystemService._start_task = _tracking_start_task  # type: ignore[method-assign]
        supervisor: asyncio.Task[None] | None = None
        try:
            await sysfunct.start_tasks(task_starters, task_names=module._collect_task_names())
            supervisor = asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())
            target = task_starters.index(sysfunct.start_asy_status)  # any task: the supervisor reads only task.done()
            assert await _wait_until(lambda: target in started, timeout_s=_WAIT_TIMEOUT_S), "the real task was never started by the real supervisor at all"
            first = started[target][0]
            assert len(started[target]) == 1 and first is not None and not first.done()
            first.cancel()  # a real task genuinely ending: the supervisor never asks why
            assert await _wait_until(lambda: len(started[target]) == 2, timeout_s=_RESTART_WAIT_TIMEOUT_S), "supervise_tasks() never rediscovered and restarted the real dead task"
            second = started[target][1]
            assert second is not None and second is not first and not second.done()
        finally:
            asy_system_service.SystemService._start_task = real_start_task  # type: ignore[method-assign]
            if supervisor is not None:
                await cancel(supervisor)
            if sysfunct._supervisor_task is not None:
                await cancel(sysfunct._supervisor_task)
            for tasks in started.values():
                for task in tasks:
                    if task is not None:
                        await cancel(task)
            if module.conn._dns_server_task is not None:  # started inside the WiFi service, never by the supervisor
                await cancel(module.conn._dns_server_task)

    run(scenario())


def test_a_supervised_task_death_reaches_the_console_through_the_pc_report_at_level_0() -> None:
    tap = _ReportTap()
    drift = [0] * _STATUS_DEATHS  # sized up front: a growing list would read as heap drift
    resets = machine.reset_count

    async def scenario() -> None:
        watchdog = await _boot(_ports.next())
        sysfunct: SystemService = module.sysfunct
        assert sysfunct.pr.set_level(0)
        # A linked station, its link awaited below: with no SSID the hotspot fallback switches the radio and binds the
        # captive DNS 8-14 s in, a one-time step a slow runner's deaths straddle (agent, 2026-10-14).
        persisted, _results = await module.conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted
        task_starters = module._collect_task_starters()
        status_idx = task_starters.index(sysfunct.start_asy_status)  # SYSTEM's own task: every device has it
        starts = [0] * len(task_starters)
        latest: list[asyncio.Task[None] | None] = [None] * len(task_starters)  # only the live one: no dead task is kept
        real_start_task, real_uptime = sysfunct._start_task, sysfunct._uptime

        async def _tracking_start_task(starter: "TaskStarter", n: int) -> "asyncio.Task[None] | None":
            latest[n] = await real_start_task(starter, n)
            starts[n] += 1
            return latest[n]

        sysfunct._start_task = _tracking_start_task  # type: ignore[method-assign]
        fast = _FastSupervisorAsyncio()
        asy_system_service.asyncio = fast  # type: ignore[assignment, attr-defined]
        supervisor: asyncio.Task[None] | None = None
        try:
            await sysfunct.start_tasks(task_starters, task_names=module._collect_task_names())
            supervisor = asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())
            assert await _yield_until(lambda: all(starts)), starts
            assert await _wait_until(lambda: module.conn._conn_phase == _STA_ESTABLISHED, timeout_s=_WAIT_TIMEOUT_S), "the station never linked"
            assert asyncio.get_event_loop().get_exception_handler() is unix_port_unretrieved_report.report_unretrieved
            sysfunct._uptime = _StatusFault(real_uptime, lambda: latest[status_idx])  # type: ignore[assignment]
            _fill_wire_logs()
            with tap:
                for death in range(_STATUS_DEATHS):
                    # The death lands while the supervisor sleeps, as its two-second pass makes near certain on the
                    # board: a pass awaiting the dead task first would retrieve the exception, and no handler runs.
                    fast.hold = True
                    assert await _yield_until(lambda: fast.parked), "the supervisor never reached its sleep"
                    restarts, reported = starts[status_idx], tap.reported
                    sysfunct._uptime_event.set()
                    assert await _yield_until_above(lambda: tap.reported, reported), f"the death never reached the PC report: {tap.wrong}"
                    fast.release()
                    assert await _yield_until_above(lambda: starts[status_idx], restarts), "the dead status task was never restarted"
                    fed = watchdog.feed_count
                    assert await _yield_until_above(lambda: watchdog.feed_count, fed + _DECAY_PASSES - 1), "the supervisor stopped passing"
                    drift[death] = await _heap_floor(watchdog)
            assert asyncio.get_event_loop().get_exception_handler() is unix_port_unretrieved_report.report_unretrieved
        finally:
            sysfunct._uptime = real_uptime
            del sysfunct._start_task
            asy_system_service.asyncio = asyncio  # type: ignore[attr-defined]
            if supervisor is not None:
                await cancel(supervisor)
            if sysfunct._supervisor_task is not None:
                await cancel(sysfunct._supervisor_task)
            for task in latest:
                # A dead one stays: the supervisor awaited it already, and a second await of a task whose first
                # one raced asyncio's pending handler entry raises None, a segfault (SPECIFICATION.md Part F.1).
                if task is not None and not task.done():
                    await cancel(task)
            if module.conn._dns_server_task is not None:
                await cancel(module.conn._dns_server_task)

    run(scenario())
    assert (tap.reported, tap.traced, tap.wrong) == (_STATUS_DEATHS, _STATUS_DEATHS, []), (tap.reported, tap.traced, tap.wrong)
    assert machine.reset_count == resets  # the restart budget never escalated to a reset
    # The first reading still holds 0.9 KB the second no longer does (measured at both GC stages, 2026-10-14): the
    # baseline is the reading after it.
    assert max(drift[1:]) - drift[1] <= _HEAP_DRIFT_BYTES, drift
    slope = (min(drift[-3:]) - min(drift[_SETTLED_DEATH : _SETTLED_DEATH + 3])) / (_STATUS_DEATHS - 3 - _SETTLED_DEATH)
    assert slope < _DRIFT_SLOPE_BYTES, f"{slope:.0f} B retained per supervised death: {drift}"


def test_a_failing_wlan_status_keeps_the_link_and_warns_once_per_unreadable_tick() -> None:
    # Two raising status() reads on a linked station: unreadable is not down (asy_wifi_service.py's uptime loop), so
    # the link and its uptime stand, no interface is rebuilt, and each unreadable tick persists one W.
    async def scenario() -> None:
        await _boot(_ports.next())
        conn = module.conn
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted
        conn.start_uptime_timer()
        tasks = [conn.start_asy_connect(), conn.start_asy_uptime()]
        try:
            assert await _wait_until(lambda: conn._wifi_connected, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S), "the station never linked before the fault"
            station = network.WLAN(network.STA_IF)  # the service's own interface object: one per interface, as on rp2
            built = network.constructions[network.STA_IF]
            counted = (await conn.get_error_counter())["WIFI"]["ErrCount"]
            station.raise_on["status"] = (OSError, (5,), 2)  # EIO, twice
            assert await _wait_until(lambda: "status" not in station.raise_on, timeout_s=_WAIT_TIMEOUT_S), "the service never read the station's status"
            entry = (await conn.get_error_counter())["WIFI"]
            unreadable = [i for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "W" and entry["ErrNum"][i] == code("W", "WLAN_STATUS_UNREADABLE")]
            # The newest-entry rule (SPECIFICATION.md C.7.1): two consecutive ticks share one slot and count twice.
            assert (len(unreadable), entry["ErrCount"] - counted) == (1, 2), f"two unreadable ticks persisted {entry}"
            assert conn._wifi_connected and conn._wlan.isconnected(), "an unreadable status took the link down"
            assert network.constructions[network.STA_IF] == built, "an unreadable status rebuilt the station interface"
        finally:
            for task in tasks:
                await cancel(task)
            if conn._dns_server_task is not None:
                await cancel(conn._dns_server_task)

    run(scenario())


def test_two_failed_joins_re_select_the_radio_once_and_the_link_comes_back() -> None:
    # A linked station loses its link and each next join raises EIO, a failed hardware call, up to the rung's threshold:
    # the radio is re-selected once (one deinit, one new STA interface, one W), then the link comes back.
    _first_device_only()

    async def scenario() -> None:
        await _boot(_ports.next())
        conn: WifiService = module.conn
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted
        conn.start_uptime_timer()
        asy_wifi_service.asyncio = _SteppedWifiAsyncio()  # type: ignore[assignment, attr-defined]
        tasks = [conn.start_asy_connect(), conn.start_asy_uptime()]
        station = conn._wlan  # the STA singleton, which a re-selection constructs again (one per interface, as on rp2)
        deinits = [0]
        real_deinit = station.deinit

        def counted_deinit() -> None:
            deinits[0] += 1
            real_deinit()

        station.deinit = counted_deinit  # type: ignore[method-assign]  # the instance's own, deleted in finally
        try:
            assert await _wait_until(lambda: conn._wifi_connected, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S), "the station never linked before the fault"
            built = network.constructions[network.STA_IF]
            station.raise_on["connect"] = (OSError, (5,), _RUNG_AT)  # EIO
            station.disconnect()  # the link lost: LINK_DOWN, as the bus-hazard file's single flap leaves it
            back = await _wait_until(lambda: conn._wifi_connected and conn._wlan.isconnected(), timeout_s=_radio_rung_bound_s(conn))
            assert network.constructions[network.STA_IF] == built + 1, f"{_RUNG_AT} failed joins re-selected the radio {network.constructions[network.STA_IF] - built} times, not once"
            assert deinits[0] == 1, f"the re-selection powered the radio down {deinits[0]} times, not once"
            assert back, "the link never came back after the radio was re-selected"
            entry = (await conn.get_error_counter())["WIFI"]
            recovered = [i for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "W" and entry["ErrNum"][i] == code("W", "DEVICE_RECOVERY")]
            assert len(recovered) == 1, f"the re-selection persisted {len(recovered)} W DEVICE_RECOVERY slots, not one: {entry}"
        finally:
            for task in tasks:
                await cancel(task)
            if conn._dns_server_task is not None:
                await cancel(conn._dns_server_task)
            del station.deinit
            asy_wifi_service.asyncio = asyncio  # type: ignore[attr-defined]

    run(scenario())


def test_hotspot_fallback_drives_the_status_led_and_binds_the_dns_server() -> None:
    # The in-process half of the hotspot scenario: real failure cycles open the hotspot, the WiFi-status LED wired by
    # build_system() writes real frames, the captive DNS binds; its answer and the captive redirect are the host
    # harness's. Driver-specific (the status LED is a NeoPixel); tests/test_asy_wifi_service.py covers every device.
    _driver_specific("neopixel")

    async def scenario() -> None:
        conn, pixel, tasks = await _hotspot_boot()
        try:
            assert conn._led is pixel
            assert len(pixel._pixel.writes) > 0, "the real status LED never actually wrote a frame"
            assert conn.is_hotspot_active() is True
        finally:
            await _stop_hotspot(conn, tasks)

    run(scenario())


def test_the_captive_dns_listener_idles_at_its_idle_rate() -> None:
    # With no DNS traffic for a window, the listener wakes once per udp.poll_idle_ms (its socket's ipoll() rounds inside
    # one ready(), counted through a wrapper around the instance's poller): the twin half of that rate's measured basis.
    # Same boot as the hotspot test above, so the same device.
    _driver_specific("neopixel")

    async def scenario() -> None:
        conn, _pixel, tasks = await _hotspot_boot()
        udps = conn._dns_server._udps
        real_poller = udps.poller
        counter = _CountingPoller(real_poller)
        udps.poller = counter  # type: ignore[assignment]  # the same poller, its rounds counted; restored in finally
        try:
            start = time.ticks_ms()
            await asyncio.sleep(_IDLE_WINDOW_S)
            elapsed_ms = time.ticks_diff(time.ticks_ms(), start)
            woke = counter.rounds
        finally:
            udps.poller = real_poller
            await _stop_hotspot(conn, tasks)
        expected = elapsed_ms // _POLL_IDLE_MS  # type: ignore[operator]  # src_const() answers object
        print(f"MEASURE udp.idle_wakeups_per_s={woke * 1000 / elapsed_ms:.2f}")
        assert expected - 1 <= woke <= expected + 1, f"{woke} listener wake-ups in {elapsed_ms} ms, not {expected} +-1 at {_POLL_IDLE_MS} ms"

    run(scenario())


async def _stop_hotspot(conn: "WifiService", tasks: "list[asyncio.Task[None]]") -> None:
    for task in tasks:
        await cancel(task)
    if conn._dns_server_task is not None:  # started inside the WiFi service, not here
        await cancel(conn._dns_server_task)


async def _wait_until(predicate: "Callable[[], bool]", timeout_s: float, interval_s: float = _WAIT_POLL_S) -> bool:
    # Bounded polling for a real multi-second state transition (mode switches, supervisor cycles). Counts poll
    # iterations, not wall clock: under CPU starvation a wall-clock bound would fail sooner, not later.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return predicate()


async def _wait_until_async(predicate: "Callable[[], Coroutine[object, object, bool]]", timeout_s: float, interval_s: float = _WAIT_POLL_S) -> bool:
    # _wait_until() above for a predicate that must await (a module's get_data()).
    elapsed = 0.0
    while elapsed < timeout_s:
        if await predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return await predicate()


def test_sgp40_voc_backup_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    # A real timestamped backup write (SPECIFICATION.md Part A.7), the twin's FRAM image flushed, a new board over the
    # same state path, a real restore. Driver-specific (an SGP40 backed up to FRAM); its L1 suite covers every device.
    _driver_specific("sgp40", "fram")

    async def scenario() -> None:
        cfg_path = _scratch.dir()
        machine.configure_fram_state_path(cfg_path + "fram_state.json")
        await _boot(_ports.next(), cfg_path)
        sgp1 = module.sgp40
        await _seed_compensation()
        # WaitTimeNTP at its minimum: the first backup needs no NTP sync.
        persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 1})
        assert persisted
        await _one_backup(sgp1)
        machine.flush_fram()  # the simulated reboot: persisted, then a new board reads the image back
        await _boot(_ports.next(), cfg_path)
        assert module.sgp40 is not sgp1  # a fresh object: the persisted bytes, not Python state, carry the backup
        await _seed_compensation()
        await _restore(module.sgp40, "after the simulated reboot")

    run(scenario())


def test_sgp40_voc_backup_unflushed_write_is_lost_but_the_system_recovers_cleanly_to_the_last_flushed_state() -> None:
    # Recombination test (owner, 2026-09-04, paraphrase): a crash between a FRAM write and the next flush - the twin
    # analogue of tests_hardware/flash/test_bus_concurrency.py's hard-reset-race test. Driver-specific as above.
    _driver_specific("sgp40", "fram")

    async def scenario() -> None:
        cfg_path = _scratch.dir()
        state_path = cfg_path + "fram_state.json"
        machine.configure_fram_state_path(state_path)
        await _boot(_ports.next(), cfg_path)
        sgp1 = module.sgp40
        await _seed_compensation()
        persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 1})
        assert persisted
        flushed: list[str] = []

        async def flushed_then_backed_up_again() -> None:
            machine.flush_fram()
            with open(state_path) as f:
                flushed.append(f.read())
            await _backup_now(sgp1)  # a second backup that lands in the chip's memory, never flushed

        await _one_backup(sgp1, flushed_then_backed_up_again)
        flushed_state = flushed[0]
        with open(state_path) as f:
            assert f.read() == flushed_state, "the unflushed backup leaked onto disk: flush_fram() is no longer the only persistence trigger"
        await _boot(_ports.next(), cfg_path)  # the crash-reboot: the image still holds the first backup alone
        assert module.sgp40 is not sgp1
        await _seed_compensation()
        await _restore(module.sgp40, "after the simulated crash-reboot")

    run(scenario())


def test_a_restored_backup_reports_its_timestamp_without_ntp() -> None:
    # A backup written while NTP had set the clock, restored after a boot with WaitTimeNTP 0 and no sync: the reader's
    # status data (what /status serialises) reports the backup's own timestamp as RestoreTS on the first cycle.
    _driver_specific("sgp40", "fram")

    async def scenario() -> None:
        cfg_path = _scratch.dir()
        machine.configure_fram_state_path(cfg_path + "fram_state.json")
        await _boot(_ports.next(), cfg_path)
        await module.ntp._set_synced(value=True)
        asy_base_classes.set_utc_valid()
        sgp1 = module.sgp40
        await _seed_compensation()
        persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 0})
        assert persisted
        await _one_backup(sgp1)
        written = sgp1._last_backup
        assert written is not None, "the backup was written without a timestamp although the clock was set"
        machine.flush_fram()
        asy_base_classes.set_utc_valid(valid=False)
        await _boot(_ports.next(), cfg_path)
        await _seed_compensation()
        await _restore(module.sgp40, "without NTP")
        status = await module._sgp_maintenance_status_sgp40()
        assert status["RestoreTS"] == written, f"RestoreTS {status['RestoreTS']} is not the backup's own {written}"

    run(scenario())


async def _yield_until(predicate: "Callable[[], bool]") -> bool:
    for _ in range(_PASS_YIELD_BOUND):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


def test_the_notification_window_spanning_midnight_flashes_red() -> None:
    # The real coordinator, the real ntp.cettime() over the installed wall clock and the real pixel, one monitor cycle
    # per window; settings applied through the path PUT /notification calls. Driver-specific (a CO2 warning on the
    # pixel); tests/test_asy_notification_service.py covers every device.
    _driver_specific("notification", "scd30")

    async def scenario() -> None:
        await _boot(_ports.next())
        _wall_clock.install(run_generic_integration.product_modules())
        notif, ntp, pixel, webserver = module.notification, module.ntp, module.neopixel, module.webserver
        await ntp._set_synced(value=True)  # the twin has no NTP server here; the clock is the host's
        asy_base_classes.set_utc_valid()
        local = await ntp.cettime()
        assert local is not None
        hour = local.hour
        # On later than Off, with the current hour (and the next) strictly inside, never on a bound.
        on_h, off_h = (hour - 1, hour - 2) if hour >= 2 else (23, hour + 2)
        cfg = await notif.cfgmgr.get_dict(["WarnCO2"])
        assert cfg is not None
        warn_co2 = cfg["WarnCO2"]
        assert isinstance(warn_co2, int)
        (bus_name, address) = next((bus, a["address"]) for bus, attachments in plan["buses"].items() for a in attachments if a["driver"] == "scd30")
        chip = machine.peripheral(bus_name).devices[address]  # type: ignore[union-attr]  # an I2C bus
        chip.co2 = Walk(warn_co2 + 100, warn_co2 + 100, 0.0)
        scd30_tasks = [starter() for starter in module.scd30.get_task_starters()]
        for starter in module.scd30.get_timer_starters():
            starter()
        assert await _wait_until_async(lambda: _co2_above(warn_co2), _WINDOW_WAIT_S), "the SCD30 never read the CO2 above the warning"

        async def apply_window(on: int, off: int) -> None:
            body = {"OnH": on, "OnM": 0, "OffH": off, "OffM": 0, "FlashDur": 0.5}
            results = await webserver._apply_settings_groups("notification", body)
            assert set(results.values()) <= {"Valid", "Unchanged"}, results
            assert await notif.cfgmgr.get_dict(["OnH", "OffH"]) == {"OnH": on, "OffH": off}

        async def triggered() -> bool:
            return bool((await notif.get_data()).Triggered)

        async def not_triggered() -> bool:
            return not await triggered()

        await apply_window(on_h, off_h)
        tasks = [pixel.start_asy_signal(), notif.start_asy_monitor()]
        try:
            assert await _wait_until(lambda: len(_red_frames(list(pixel._pixel.writes))) > 0, _WINDOW_WAIT_S), (
                f"no red frame with the window {on_h}:00-{off_h}:00 around local {hour}:{local.minute:02d}"
            )
            assert await _wait_until_async(triggered, _WINDOW_WAIT_S), "the cycle that flashed never reported Triggered"
            await cancel(tasks.pop())  # the monitor now sleeps its whole FlashInterval; the next window gets a fresh cycle
            assert await _wait_until(lambda: not pixel._start_signal_event.is_set(), _WINDOW_WAIT_S)
            seen = len(pixel._pixel.writes)

            await apply_window(off_h, on_h)  # the complementary, same-day window: the current hour is outside
            tasks.append(notif.start_asy_monitor())
            assert await _wait_until_async(not_triggered, _WINDOW_WAIT_S), "a cycle outside the window reported Triggered"
            assert _red_frames(list(pixel._pixel.writes)[seen:]) == [], "a cycle outside the window flashed"
        finally:
            for task in tasks + scd30_tasks:
                await cancel(task)
            asy_base_classes.set_utc_valid(valid=False)

    run(scenario())


async def _yield_until_above(read: "Callable[[], int]", floor: int) -> bool:
    return await _yield_until(lambda: read() > floor)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
