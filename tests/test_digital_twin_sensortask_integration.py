"""In-process twin tier for the device named by TEST_DEVICE: its generated graph booted on the twin buses with no HTTP
(requests are driven host-side by scripts/_digital_twin_scenarios.py). A driver-specific scenario runs once per distinct
wiring of its drivers, devices wiring them identically sharing one run (SPECIFICATION.md E.2.1)."""

import asyncio
import gc
import json
import os
import select
import socket
import sys
import time

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

import _unix_port_udp_addr_shim
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
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _fast_sleep import check_sleep_ms  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _src_const import src_const, src_int  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _twin_common import Walk  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _twin_devices import distinct_wirings, generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _twin_readiness import wait_for_value  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from _udp_step_fault import FailNextUdpSetup  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)

import asy_base_classes  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_captive_dns  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_neopixel_driver  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_notification_service  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_scd30_driver  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_sgp40_driver  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_system_service  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_udp_socket  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
import asy_wifi_service  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
from asy_config_manager import config_filename  # noqa: E402 - imported after the prewarm and the UDP shim (C4 order)
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

    from _mpy_shed.time_mp import _TicksMs
    from _scd30_chip import SCD30Chip
    from _sgp40_chip import SGP40Chip
    from launch import _Plan

    from asy_base_classes import TaskStarter, TickSeconds
    from asy_fram_manager import FRAMChunkTimestampedBuffer
    from asy_neopixel_driver import NeopixelDriver
    from asy_sgp40_driver import SGP40_Reader
    from asy_system_service import SystemService
    from asy_udp_socket import UDPSocket
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
_BURST = 6  # DNS queries sent with no yield between them: more than lwIP queues for one socket (asy_captive_dns.py)
_DNS_QUESTION = b"\x07captive\x07example\x00\x00\x01\x00\x01"  # one A record (RFC 1035 4.1.2)
_POLL_IDLE_MS = src_const("src/asy_udp_socket.py", "_POLL_IDLE_MS")
_STA_ESTABLISHED = src_const("src/asy_wifi_service.py", "_PHASE_STA_ESTABLISHED")
_HOTSPOT_PHASE = src_const("src/asy_wifi_service.py", "_PHASE_HOTSPOT")
_JOINED_NO_IP = src_int("src/asy_wifi_service.py", "_STAT_JOINED_NO_IP")
_WIFI_STORE = str(src_const("src/asy_wifi_service.py", "_NAME"))
_NO_CLOCK = src_const("src/asy_notification_service.py", "_STATE_NO_CLOCK")
_EVALUATED = src_const("src/asy_notification_service.py", "_STATE_EVALUATED")
_PARTIAL = src_const("src/asy_notification_service.py", "_STATE_PARTIAL")
# Past both age bounds a sample is unavailable: to the notification's checks and as the SGP40's compensation.
_STALE_AFTER_S = max(src_int("src/asy_notification_service.py", "_SAMPLE_MAX_AGE_S"), src_int("src/asy_sgp40_driver.py", "_COMP_MAX_AGE_S")) + 1
_FLASH_DUR_S = 0.5  # FlashDur's schema floor
_FLASH_HOLD_MS = round(_FLASH_DUR_S * 2000)  # the monitor's wait after a flash it asked for (asy_notification_service.py)
_MEASURE_RAW = b"\x26\x0f"  # the SGP40's measure command (datasheet Table 9), as asy_sgp40_driver.py sends it
_RUNG_AT = src_int("src/asy_base_classes.py", "_RECOVER_DEVICE_AT")  # consecutive failed iterations to the device rung
_WIFI_STEP_MS = src_int("src/asy_wifi_service.py", "_STA_CONNECT_POLL_MS")  # the connect poll's step: _SteppedAsyncio's cap
_NO_IP_STEP_MS = 100  # ten polls outlast the twin's 0.7 s join (digital_twin/network.py), so each attempt ends joined without an IP
_STREAK_JOIN_S = 0.05  # the hotspot streak's twin join, whose length no hotspot check reads: ten 10 ms polls outlast it
_STREAK_STEP_MS = 10
_WAIT_TIMEOUT_MS = int(_WAIT_TIMEOUT_S * 1000)
_IDLE_WINDOW_MS = int(_IDLE_WINDOW_S * 1000)
_STATUS_DEATHS = 10
_DECAY_PASSES = 110  # clean supervisor passes between two deaths: each decays the restart budget by one, a death adds 100
_PASS_YIELD_BOUND = 20000  # loop yields allowed for one wait below; a pass costs a few with the supervisor's fast sleep
# The collected heap across the deaths, in-loop with every real task live: measured within 64 B at both GC stages,
# while keeping each dead task and its exception measured 2.4 KB over the nine after the baseline (2026-10-14).
_HEAP_DRIFT_BYTES = 2048
# Per death, the median of every pairwise slope over the settled readings (Theil-Sen), each death on the driven clock
# reading the same heap: 36 healthy runs, six devices at both stages, read 0 B, a planted 32 or 64 B per death exactly
# that (agent, 2026-10-27).
_DRIFT_SLOPE_BYTES = 32  # one GC block a death on the twin, the least a leak can retain
_SETTLED_DEATH = 3  # the readings before it still settle: the second and third hold up to 0.8 KB the fourth does not
# @tunable l2.sensortask_integration_heap_floor_reads = 3
_FLOOR_READS = 3
# A seeded SCD30 reading: the compensation the SGP40 reads before it measures.
_SCD30_READING = SCD30(800, 22.0, 45.0, None, None, None, None, None)

_scratch = TmpScratch("dtsi_" + device)  # per device: two devices' jobs of this file may run at once
_ports = PortAllocator("dtsi", device)  # a fresh port per serving boot avoids any TIME_WAIT reuse flakiness
_UNSERVED_PORT = _ports.next()  # every boot that never starts the web server: nothing binds it (agent, 2026-10-21)
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
module = load_device(device)
plan = wiring_plan(device)
_links: "list[machine.UARTLink]" = []  # the booted device's jumpered UART link, when its plan wires one


async def _apply_window(on: int, off: int) -> None:
    # The notification window applied through the path PUT /notification calls.
    body = {"OnH": on, "OnM": 0, "OffH": off, "OffM": 0, "FlashDur": _FLASH_DUR_S}
    results = await module.webserver._apply_settings_groups("notification", body)
    assert set(results.values()) <= {"Valid", "Unchanged"}, results
    assert await module.notification.cfgmgr.get_dict(["OnH", "OffH"]) == {"OnH": on, "OffH": off}


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
        assert await _wait_until(lambda: bool(results), timeout_s=_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S), "the real VOC backup write never completed"
    finally:
        del storage.write_into
    assert results[0][0] and chip.writes_at.get(block, 0) > written, f"the VOC backup write {results[0]} never reached its chunk"


async def _boot(port: int = _UNSERVED_PORT, cfg_path: "str | None" = None) -> "machine.WDT":
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
    _wire_link()
    await module.sysfunct.run_setups(module._collect_setups())
    return watchdog


def _chip(driver: str) -> object:
    # The twin chip the plan attaches for a driver (its first attachment).
    bus_name, address = next((bus, a["address"]) for bus, attachments in plan["buses"].items() for a in attachments if a["driver"] == driver)
    return cast("machine.I2C", machine.peripheral(bus_name)).devices[address]


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
    # A socket's real poller with each ipoll() round inside a ready(POLLIN) counted: one per listener wake-up, a reply's
    # ready(POLLOUT) rounds left out. Installed on the socket instance; uninstall() restores both and the sleeps' view.
    def __init__(self, udps: "UDPSocket", clock: DrivenTime) -> None:
        self._udps, self._real, self._real_ready = udps, udps.poller, udps.ready
        self._listening = True  # installed on an idle listener, parked in its ready(POLLIN)
        self.listener: object = None  # the task that next calls ready(POLLIN): the listener's own
        self.rounds = 0
        self.sleeps = _ListenerSleeps(self, clock)
        udps.poller = self  # type: ignore[assignment]  # the same poller, its rounds counted
        udps.ready = self._ready  # type: ignore[method-assign]  # the instance's own, deleted by uninstall()

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)

    async def _ready(self, mask: int, timeout_ms: int = -1) -> bool:
        self._listening = mask == select.POLLIN
        if self._listening:
            self.listener = asyncio.current_task()
        return await self._real_ready(mask, timeout_ms=timeout_ms)

    def ipoll(self, timeout: int = -1) -> object:
        if self._listening:
            self.rounds += 1
        return self._real.ipoll(timeout)  # type: ignore[union-attr]  # a select.poll's own

    def uninstall(self) -> None:
        self._udps.poller = self._real
        del self._udps.ready
        self.sleeps.uninstall()


class _ListenerSleeps:
    # asyncio as the listener's two modules see it, the listener task's sleeps of one idle poll or more counted: a
    # listener sleeping before each read finds data on every ready() round, so its rounds alone miss it. The sleeps
    # park on the driven clock; uninstall() puts back the view each module had.
    def __init__(self, counter: _CountingPoller, clock: DrivenTime) -> None:
        self._counter, self._clock, self.count = counter, clock, 0
        self._held = (asy_udp_socket.asyncio, asy_captive_dns.asyncio)  # type: ignore[attr-defined]
        asy_udp_socket.asyncio = asy_captive_dns.asyncio = self  # type: ignore[assignment, attr-defined]

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    async def sleep(self, seconds: float) -> None:
        await self.sleep_ms(int(seconds * 1000))  # asyncio's own conversion (extmod/asyncio/core.py)

    async def sleep_ms(self, ms: int) -> None:
        if ms >= _POLL_IDLE_MS and asyncio.current_task() is self._counter.listener:  # type: ignore[operator]  # src_const() answers object
            self.count += 1
        await self._clock._sleep_ms(ms)

    def uninstall(self) -> None:
        asy_udp_socket.asyncio, asy_captive_dns.asyncio = self._held  # type: ignore[attr-defined]


async def _co2_above(limit: int) -> bool:
    co2 = (await module.scd30.get_data()).CO2
    return co2 is not None and co2 > limit


async def _dns_burst(counter: _CountingPoller, clock: DrivenTime) -> "tuple[int, int, int]":
    # _BURST queries from one host socket with no yield between them, so all are queued when the listener next wakes;
    # returns the distinct replies read, and the listener's wake-ups and idle sleeps until the last one came.
    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer.setblocking(False)
    poller = select.poll()
    poller.register(peer, select.POLLIN)
    replied: set[int] = set()
    try:
        addr = socket.getaddrinfo("127.0.0.1", 53)[0][-1]  # sendto() takes the resolved address (SPECIFICATION.md F.7)
        before, slept = counter.rounds, counter.sleeps.count
        for query_id in range(_BURST):
            peer.sendto(bytes([0, query_id]) + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + _DNS_QUESTION, addr)
        for _ in range(_WAIT_TIMEOUT_MS):
            for _sock, _event in poller.ipoll(0):
                replied.add(peer.recv(512)[1])
            if len(replied) == _BURST:
                break
            await clock.elapse(1)
        return len(replied), counter.rounds - before, counter.sleeps.count - slept
    finally:
        poller.unregister(peer)
        peer.close()


async def _driven(clock: DrivenTime, what: str, coro: "Coroutine[object, object, T]") -> "T":
    # `coro` as a task, the driven clock elapsed wake by wake until it ends (tests/test_digital_twin_hot_replug.py's own).
    task = asyncio.get_event_loop().create_task(coro)
    try:
        await clock.run_until(task.done, _WAIT_TIMEOUT_MS)
    except AssertionError as e:
        raise AssertionError(f"{what} - {e}") from None
    return await task


def _driven_modules() -> "list[object]":
    # Every src module holding asyncio and the twin's machine and network: one clock for each sleep and tick read.
    return [m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio]


def _driver_specific(*drivers: str) -> None:
    # A driver-specific scenario runs once per distinct wiring of its drivers, on the first device of each; devices wiring
    # them identically share that run, and none wiring them fails in devices_with() rather than skipping everywhere.
    chosen = distinct_wirings(*drivers)
    if device not in chosen:
        raise microtest.Skip(f"runs on {chosen}, one device per distinct wiring of {list(drivers)}")


async def _fed_cycle(sgp: "SGP40_Reader") -> None:
    # One read cycle of a running SGP40 task, its compensation seeded: it ends with its VOC sample count moved.
    samples = sgp._voc_samples
    sgp._read_event.set()
    assert await _wait_until(lambda: sgp._voc_samples != samples, _WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S), "a fed SGP40 cycle never measured"


def _fill_wire_logs() -> None:
    # The twin wire keeps up to 4 kB of delivered bytes a direction, growing until full: filled once, its later bytes
    # overwrite in place, so a running link's log is no heap drift.
    for link in _links:
        for end in link.endpoints:
            log = link.direction_from(end).wire_log
            log.extend(bytes(log.maxlen))


def _first_device_only() -> None:
    # A scenario of seconds of wall clock through a mechanism every device shares runs once, on the first generated
    # device, as the driver-specific ones run once per distinct wiring of their drivers (SPECIFICATION.md E.2.1).
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


async def _hotspot_boot(clock: DrivenTime) -> "tuple[WifiService, NeopixelDriver, list[asyncio.Task[None]]]":
    # SSID written, every connect scripted to fail: the boot streak fails for real until the hotspot opens, on the driven
    # clock, its to-hotspot W slot in WIFI's RAM ring and FRAM chunk. Returns the WiFi service, its LED's pixel driver
    # and the tasks started (the overlay, the connect loop).
    await _driven(clock, "the boot", _boot())
    conn, pixel = module.conn, module.neopixel
    persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
    assert persisted
    conn._wlan.script_connect_outcomes([network.STAT_NO_AP_FOUND] * 8)  # more than the streak to the hotspot needs
    held = asy_wifi_service.asyncio  # type: ignore[attr-defined]
    asy_wifi_service.asyncio = _SteppedAsyncio(_STREAK_STEP_MS, clock=clock)  # type: ignore[assignment, attr-defined]  # the streak's waits stepped
    join_s, network._CONNECT_DELAY_S = network._CONNECT_DELAY_S, _STREAK_JOIN_S
    try:
        tasks = [pixel.start_asy_overlay(), conn.start_asy_connect()]
        started = await _wait_until(lambda: conn._dns_server_task is not None, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S, clock=clock)
        assert started, "real hotspot activation never started the real DNSServer task"
        bound = await _wait_until(lambda: conn._dns_server._udps.connected, timeout_s=_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S, clock=clock)
        assert bound, "the real DNSServer never bound its port 53 socket"
        entry = (await conn.get_error_counter())["WIFI"]
        slots = [entry["ErrNum"][i] for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "W"]
        assert slots.count(code("W", "WLAN_TO_HOTSPOT")) == 1, f"the streak persisted no single to-hotspot slot: {entry}"
        await _ring_in_fram(clock, conn)
    finally:
        asy_wifi_service.asyncio = held  # type: ignore[attr-defined]
        network._CONNECT_DELAY_S = join_s
    return conn, pixel, tasks


async def _measured_above(chip: "SCD30Chip", limit: int) -> bool:
    # Each poll fires the chip's own measurement timer once (a reading and its RDY edge) until the driver has read one.
    async def fired() -> bool:
        timer = chip._timer
        if timer is not None and timer.callback is not None:
            timer.callback(timer)
        return await _co2_above(limit)

    return await _wait_until_async(fired, _WINDOW_WAIT_S, interval_s=_BIND_POLL_S)


async def _on_driven_clock(scenario: "Callable[[DrivenTime], Coroutine[object, object, None]]") -> None:
    # The scenario on one driven clock over every module holding asyncio (the boot's waits, the WiFi service's, the
    # twin's join and timers), so its seconds of waits take no real time; each module's own view is back on every path.
    with DrivenTime(*_driven_modules(), sleeps=True) as clock:
        await scenario(clock)


async def _one_backup(sgp: "SGP40_Reader", then: "Callable[[], Coroutine[object, object, None]] | None" = None) -> None:
    # One real VOC backup through the real chain: the read task started, its init done, one backup; `then` runs on the
    # same task before it is cancelled.
    task = sgp.start_asy_read()
    _step_sensor_waits(on=True)
    try:
        assert await wait_for_value(lambda: sgp._voc_init, 1, _WAIT_TIMEOUT_MS), "the SGP40 never finished its init"
        await _backup_now(sgp)
        if then is not None:
            await then()
    finally:
        _step_sensor_waits(on=False)
        await cancel(task)


def _radio_rung_bound_s(conn: "WifiService") -> float:
    # The fault to the link back at the service's own waits as _SteppedAsyncio caps them: each failed iteration and
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
    _step_sensor_waits(on=True)
    try:
        assert await wait_for_value(lambda: sgp._voc_init, 1, _WAIT_TIMEOUT_MS), "the SGP40 never finished its init"
        sgp._read_event.set()
        assert await _wait_until(lambda: sgp._restored_from is not None, timeout_s=_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S), f"the real VOC backup restore never completed {what}"
    finally:
        _step_sensor_waits(on=False)
        await cancel(task)


async def _ring_in_fram(clock: DrivenTime, conn: "WifiService") -> None:
    # WIFI's ring as its FRAM chunk holds it, read back through the store's own chunk read as the next boot's setup()
    # restores it: a write that never landed leaves the chip's older image, a RAM-only logger holds no chunk at all.
    ring = tuple(conn.pr.history)
    stored = await _driven(clock, "the WIFI chunk's read", conn.pr._read())
    assert isinstance(stored, tuple) and stored[1] == ring, f"WIFI's FRAM copy {stored} is not its RAM ring {ring}"


async def _seed_compensation() -> None:
    # The SCD30's reading the SGP40 compensates with, seeded through the store a real read cycle uses.
    await module.scd30._set_meas_data(_SCD30_READING)


async def _sgp40_cycle(sgp: "SGP40_Reader") -> None:
    # Triggers one read cycle of a running SGP40 task and waits until it has begun: of two in a row, the first has ended.
    before = sgp._backup_counter
    sgp._read_event.set()
    assert await _wait_until(lambda: sgp._backup_counter != before, _WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S), "an SGP40 read cycle never began"


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


class _SteppedAsyncio:
    # A module's view of asyncio, each sleep or sleep_ms at most one step (the WiFi connect poll's by default), one of
    # real_from_ms or longer kept whole: the stepped waits are not under test, what they gate is. With a clock, each
    # sleep parks on it (tests/_fake_time.py), as the 60 s retry does in the bus-hazard file.
    def __init__(self, step_ms: int = _WIFI_STEP_MS, real_from_ms: "int | None" = None, clock: "DrivenTime | None" = None) -> None:
        self._step_ms, self._real_from_ms, self._clock = step_ms, real_from_ms, clock

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    async def sleep(self, seconds: float) -> None:
        await self.sleep_ms(int(seconds * 1000))  # asyncio's own conversion (extmod/asyncio/core.py)

    async def sleep_ms(self, ms: int) -> None:
        check_sleep_ms(ms)
        real = self._real_from_ms is not None and ms >= self._real_from_ms
        step = ms if real else min(ms, self._step_ms)
        await (asyncio.sleep_ms(step) if self._clock is None else self._clock._sleep_ms(step))


def _step_sensor_waits(*, on: bool) -> None:
    # The SCD30's and SGP40's datasheet waits, the pixel's ramp frames and the monitor's hold after a flash, each one
    # yield (the twin chips answer at once, no assertion measures them); the monitor's cycle period stays real.
    asy_scd30_driver.asyncio = _SteppedAsyncio(0) if on else asyncio  # type: ignore[assignment, attr-defined]
    asy_sgp40_driver.asyncio = _SteppedAsyncio(0) if on else asyncio  # type: ignore[assignment, attr-defined]
    asy_neopixel_driver.asyncio = _SteppedAsyncio(0) if on else asyncio  # type: ignore[assignment, attr-defined]
    asy_notification_service.asyncio = _SteppedAsyncio(0, real_from_ms=_FLASH_HOLD_MS + 1) if on else asyncio  # type: ignore[assignment, attr-defined]


def test_sgp40_reading_before_scd30_has_measured_yet_logs_no_bogus_error() -> None:
    # Regression test for the SGP40 boot-race false error (SPECIFICATION.md Part C.14.2), found through a real
    # digital-twin CI run. Driver-specific (SGP40 compensated by an SCD30): its L1 suite covers every device. No
    # seeded SCD30 data: the point is the real startup race, the SCD30's Temp/Hum still None.
    _driver_specific("sgp40", "scd30")

    async def scenario() -> None:
        await _boot()
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


def test_watchdog_is_never_starved_while_the_real_supervisor_runs() -> None:
    # Watchdog escalation (owner, 2026-08-13, paraphrase: an automated assertion here, and a manually observable run
    # through digital_twin/run_generic_integration.py). Proven on the real supervisor's feed site; the planted-fault
    # halves are runner flags read host-side (--test-watchdog-fault). The same offline boot sends nothing public.
    phases: list[tuple[int, int, list[_TicksMs]]] = []  # each boot-phase mark with the feeds and feed stamps before it
    real_boot_phase = asy_system_service.SystemService.boot_phase

    async def scenario() -> None:
        machine.reset_peripherals()
        network.reset_interfaces()
        machine.configure_wiring(plan)
        cfg = _scratch.dir()
        write_offline_ntp_config(cfg)
        write_error_level_config(cfg)
        with open(config_filename(cfg, _WIFI_STORE), "w") as f:
            f.write(json.dumps({"SSID": "TestNet"}))  # a linked station: the NTP client's attempts go out
        watchdog = boot_entry_watchdog(module, device)
        done = asyncio.Event()
        _unix_port_udp_addr_shim.public_destinations_refused = 0  # the twin's knobs, read for this boot alone
        _unix_port_udp_addr_shim.last_refused = None

        def observed_boot_phase(self: "SystemService", phase: int) -> None:
            if phase == asy_system_service.BOOT_SETUP:
                _wire_link()
            phases.append((phase, watchdog.feed_count, list(watchdog.feed_times)))
            real_boot_phase(self, phase)
            if phase == asy_system_service.BOOT_DONE:
                done.set()

        asy_system_service.SystemService.boot_phase = observed_boot_phase  # type: ignore[method-assign]
        main_task = asyncio.create_task(module.main(watchdog=watchdog, cfg_path=cfg, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=_ports.next()))
        await done.wait()  # the boot's own pace; run() ends main() and every task it started
        _phase, fed, stamps = next(mark for mark in phases if mark[0] == asy_system_service.BOOT_TASKS)
        assert fed == len(module._collect_setups()) == len(stamps), (fed, len(stamps))
        assert all(time.ticks_diff(stamps[i + 1], stamps[i]) >= 0 for i in range(len(stamps) - 1)), stamps
        booted = watchdog.feed_count
        assert await _wait_until(lambda: watchdog.feed_count > booted, timeout_s=_WAIT_TIMEOUT_S), "the real supervisor never fed the watchdog"
        await asyncio.sleep(_WDT_OVERRUN_WAIT_S)  # one full period past its first feed, on the twin WDT's real clock
        assert watchdog.would_have_triggered_count == 0, list(watchdog.would_have_triggered_log)
        assert not main_task.done(), "main() ended: its supervisor never returns"
        ntp = module.ntp
        assert await _wait_until(lambda: ntp._retry_wait_s > ntp._retry_s, timeout_s=_WAIT_TIMEOUT_S), "the NTP client never sent a sync attempt"
        refused = (_unix_port_udp_addr_shim.public_destinations_refused, _unix_port_udp_addr_shim.last_refused)
        assert refused == (0, None), f"the offline boot sent outside the twin: {refused}"

    try:
        run(scenario())
    finally:
        asy_system_service.SystemService.boot_phase = real_boot_phase  # type: ignore[method-assign]


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
        asy_system_service.asyncio = _FastSupervisorAsyncio()  # type: ignore[assignment, attr-defined]  # a pass per yield
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
            asy_system_service.asyncio = asyncio  # type: ignore[attr-defined]
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

    async def scenario(clock: DrivenTime) -> None:
        watchdog = await _driven(clock, "the boot", _boot(_ports.next()))
        sysfunct: SystemService = module.sysfunct
        assert sysfunct.pr.set_level(0)
        # A linked station, its link awaited below: with no SSID the hotspot fallback would switch the radio and bind the
        # captive DNS instead (agent, 2026-10-14).
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
            assert await _yield_until(lambda: all(starts)), starts
            # Linked on the clock before the supervisor runs, whose passes are a yield each: under them it never settles.
            # The deaths then pass no virtual time, so every other task stays parked and each death reads the same heap.
            assert await _wait_until(lambda: module.conn._conn_phase == _STA_ESTABLISHED, timeout_s=_WAIT_TIMEOUT_S, clock=clock), "the station never linked"
            supervisor = asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())
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

    run(_on_driven_clock(scenario))
    assert (tap.reported, tap.traced, tap.wrong) == (_STATUS_DEATHS, _STATUS_DEATHS, []), (tap.reported, tap.traced, tap.wrong)
    assert machine.reset_count == resets  # the restart budget never escalated to a reset
    # The first reading still holds 0.9 KB the second no longer does (measured at both GC stages, 2026-10-14): the
    # baseline is the reading after it.
    assert max(drift[1:]) - drift[1] <= _HEAP_DRIFT_BYTES, drift
    settled = drift[_SETTLED_DEATH:]
    slopes = sorted((settled[j] - settled[i]) / (j - i) for i in range(len(settled)) for j in range(i + 1, len(settled)))
    slope = slopes[len(slopes) // 2]
    assert slope < _DRIFT_SLOPE_BYTES, f"{slope:.0f} B retained per supervised death: {drift}"


def test_a_dhcp_server_that_never_answers_leaves_a_persisted_trace() -> None:
    # Every join reaches the access point and never gets an address: each attempt ends with no verdict, persisted as one
    # W slot (the newest-entry rule, SPECIFICATION.md C.7.1), and the streak's end opens the hotspot with its own W. The
    # slots are read from RAM and back from WIFI's FRAM chunk: one run per distinct FRAM wiring (measured).
    _driver_specific("fram")

    async def scenario(clock: DrivenTime) -> None:
        await _driven(clock, "the boot", _boot())
        conn: WifiService = module.conn
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted
        streak = conn._conn_fail_to_hotspot
        station = conn._wlan
        station.script_connect_outcomes([_JOINED_NO_IP] * (streak + 2))  # more than the streak needs
        no_ip = [0]
        real_status = station.status

        def counted_status(param: "str | None" = None) -> "int | list[tuple[bytes]]":
            value = real_status(param)
            no_ip[0] += value == _JOINED_NO_IP
            return value

        station.status = counted_status  # type: ignore[method-assign]  # the instance's own, deleted in finally
        held = asy_wifi_service.asyncio  # type: ignore[attr-defined]
        asy_wifi_service.asyncio = _SteppedAsyncio(_NO_IP_STEP_MS, clock=clock)  # type: ignore[assignment, attr-defined]  # the poll's step is not under test
        task = conn.start_asy_connect()
        try:
            assert await _wait_until(lambda: conn._conn_phase == _HOTSPOT_PHASE, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S, clock=clock), "the no-verdict streak never opened the hotspot"
        finally:
            asy_wifi_service.asyncio = held  # type: ignore[attr-defined]
            await _stop_hotspot(conn, [task])
            del station.status
        assert no_ip[0] >= streak, f"only {no_ip[0]} polls read joined without an IP over {streak} attempts"
        entry = (await conn.get_error_counter())["WIFI"]
        slots = [entry["ErrNum"][i] for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "W"]
        counts = (slots.count(code("W", "WLAN_NO_VERDICT")), slots.count(code("W", "WLAN_TO_HOTSPOT")))
        assert counts == (1, 1), f"the streak persisted {counts} no-verdict and to-hotspot slots, not one each: {entry}"
        await _ring_in_fram(clock, conn)

    run(_on_driven_clock(scenario))


def test_a_failed_config_snapshot_is_the_unavailable_marker() -> None:
    # A chip-read fault on each config snapshot makes that module's get_dict_cfg() the unavailable marker alone, and the
    # next read, the fault spent, its field map; the REST half is the host harness's. Driver-specific (the three snapshot
    # drivers on one device); each driver's L1 suite covers every device wiring it.
    _driver_specific("bmp3xx", "scd30", "isl29125")

    async def scenario() -> None:
        await _boot()
        for driver, op in (("bmp3xx", "readfrom_mem"), ("scd30", "readfrom_into"), ("isl29125", "readfrom_mem")):  # each fake's read seam
            reader = getattr(module, driver)
            (bus_name, address) = next((bus, a["address"]) for bus, attachments in plan["buses"].items() for a in attachments if a["driver"] == driver)
            chip = machine.peripheral(bus_name).devices[address]  # type: ignore[union-attr]  # an I2C bus
            chip.fault.inject_fault(op, OSError, 5, "injected snapshot fault")  # EIO, on the next read: the snapshot's
            failed = await reader.get_dict_cfg()
            assert failed == {reader.name: {"error": "unavailable"}}, f"{driver}'s failed snapshot sent {failed}"
            served = await reader.get_dict_cfg()
            assert "error" not in served[reader.name], f"{driver}'s next snapshot, the fault spent, sent {served}"

    run(scenario())


def test_a_factory_state_unit_returns_to_the_hotspot_after_every_window() -> None:
    # No SSID: the boot opens the hotspot, and each window's end (its timer's callback, called as the twin Timer calls it)
    # leads straight back to it: with nothing to attempt there is no failure streak, so the silent mode is never reached.
    # After its boot it touches no wired part, no FRAM write and no LED frame among them (measured), so one device runs it.
    _first_device_only()

    async def scenario() -> None:
        await _boot()
        conn: WifiService = module.conn
        asy_wifi_service.asyncio = _SteppedAsyncio(1)  # type: ignore[assignment, attr-defined]  # no join, so no wait is under test
        tasks = [conn.start_asy_connect(), conn.start_asy_hotspot_timeout()]
        previous: asyncio.Task[None] | None = None

        def opened_after(last: "asyncio.Task[None] | None") -> "Callable[[], bool]":  # a new DNS task: a new activation
            return lambda: conn._dns_server_task not in (None, last) and conn._hotspot_timer_running

        try:
            for window in range(3):  # the boot's own window, then one after each of two ends
                assert await _wait_until(opened_after(previous), timeout_s=_HOTSPOT_WAIT_TIMEOUT_S), (
                    f"window {window}: the hotspot never opened, phase {conn._conn_phase}"
                )
                previous = conn._dns_server_task
                if window < 2:
                    timer = conn._hotspot_timer
                    timer.callback(timer)  # type: ignore[misc]  # the window's end
            assert conn._conn_phase == _HOTSPOT_PHASE and conn.is_hotspot_active(), conn._conn_phase
        finally:
            asy_wifi_service.asyncio = asyncio  # type: ignore[attr-defined]
            await _stop_hotspot(conn, tasks)

    run(scenario())


def test_a_failing_wlan_status_keeps_the_link_and_warns_once_per_unreadable_tick() -> None:
    # Two raising status() reads on a linked station: unreadable is not down (asy_wifi_service.py's uptime loop), so
    # the link and its uptime stand, no interface is rebuilt, and each unreadable tick persists one W.
    async def scenario() -> None:
        await _boot()
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
            timer = conn._counter_timer

            def ticked_and_read() -> bool:  # one uptime tick per poll, fired as the twin Timer fires it: its period is not under test
                timer.callback(timer)
                return "status" not in station.raise_on

            assert await _wait_until(ticked_and_read, timeout_s=_WAIT_TIMEOUT_S), "the service never read the station's status"
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
    # the radio is re-selected once (one deinit, one new STA interface, one W), then the link comes back. Its W and E
    # slots are read from RAM and back from WIFI's FRAM chunk: one run per distinct FRAM wiring (measured).
    _driver_specific("fram")

    async def scenario(clock: DrivenTime) -> None:
        await _driven(clock, "the boot", _boot())
        conn: WifiService = module.conn
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted
        conn.start_uptime_timer()
        held = asy_wifi_service.asyncio  # type: ignore[attr-defined]
        asy_wifi_service.asyncio = _SteppedAsyncio(clock=clock)  # type: ignore[assignment, attr-defined]
        tasks = [conn.start_asy_connect(), conn.start_asy_uptime()]
        station = conn._wlan  # the STA singleton, which a re-selection constructs again (one per interface, as on rp2)
        deinits = [0]
        real_deinit = station.deinit

        def counted_deinit() -> None:
            deinits[0] += 1
            real_deinit()

        station.deinit = counted_deinit  # type: ignore[method-assign]  # the instance's own, deleted in finally
        try:
            assert await _wait_until(lambda: conn._wifi_connected, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S, clock=clock), "the station never linked before the fault"
            built = network.constructions[network.STA_IF]
            station.raise_on["connect"] = (OSError, (5,), _RUNG_AT)  # EIO
            station.disconnect()  # the link lost: LINK_DOWN, as the bus-hazard file's single flap leaves it
            back = await _wait_until(lambda: conn._wifi_connected and conn._wlan.isconnected(), timeout_s=_radio_rung_bound_s(conn), clock=clock)
            assert network.constructions[network.STA_IF] == built + 1, f"{_RUNG_AT} failed joins re-selected the radio {network.constructions[network.STA_IF] - built} times, not once"
            assert deinits[0] == 1, f"the re-selection powered the radio down {deinits[0]} times, not once"
            assert back, "the link never came back after the radio was re-selected"
            entry = (await conn.get_error_counter())["WIFI"]
            recovered = [i for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "W" and entry["ErrNum"][i] == code("W", "DEVICE_RECOVERY")]
            assert len(recovered) == 1, f"the re-selection persisted {len(recovered)} W DEVICE_RECOVERY slots, not one: {entry}"
            await _ring_in_fram(clock, conn)
        finally:
            for task in tasks:
                await cancel(task)
            if conn._dns_server_task is not None:
                await cancel(conn._dns_server_task)
            del station.deinit
            asy_wifi_service.asyncio = held  # type: ignore[attr-defined]

    run(_on_driven_clock(scenario))


def test_hotspot_fallback_drives_the_status_led_and_binds_the_dns_server() -> None:
    # The in-process half of the hotspot scenario: real failure cycles open the hotspot, the WiFi-status LED wired by
    # build_system() writes real frames, the captive DNS binds; its answer and the captive redirect are the host
    # harness's. Per distinct wiring of the status LED and of the FRAM the hotspot's W slots are written to (measured).
    _driver_specific("neopixel", "fram")

    async def scenario(clock: DrivenTime) -> None:
        conn, pixel, tasks = await _hotspot_boot(clock)
        try:
            assert conn._led is pixel
            assert len(pixel._pixel.writes) > 0, "the real status LED never actually wrote a frame"
            assert conn.is_hotspot_active() is True
        finally:
            await _stop_hotspot(conn, tasks)

    run(_on_driven_clock(scenario))


def test_the_captive_dns_listener_idles_at_its_idle_rate() -> None:
    # With no DNS traffic for a window, the listener wakes once per udp.poll_idle_ms (its ready(POLLIN) rounds), the twin
    # half of that rate's basis, then answers a burst back to back (lwIP's drop past its queue shows on the bench). Its
    # hotspot boot drives the LED and writes WIFI's FRAM chunk (measured): one run per wiring of both (agent, 2026-10-27).
    _driver_specific("neopixel", "fram")

    async def scenario(clock: DrivenTime) -> None:
        conn, _pixel, tasks = await _hotspot_boot(clock)
        counter = _CountingPoller(conn._dns_server._udps, clock)
        try:
            start = clock.ticks_ms()
            await clock.elapse(_IDLE_WINDOW_MS)
            elapsed_ms = time.ticks_diff(clock.ticks_ms(), start)
            woke = counter.rounds
            answered, burst_rounds, burst_sleeps = await _dns_burst(counter, clock)
        finally:
            counter.uninstall()
            await _stop_hotspot(conn, tasks)
        assert elapsed_ms >= _IDLE_WINDOW_MS, f"the idle window lasted {elapsed_ms} ms of the listener's clock, not {_IDLE_WINDOW_MS}"
        expected = elapsed_ms // _POLL_IDLE_MS  # type: ignore[operator]  # src_const() answers object
        print(f"MEASURE udp.idle_wakeups_per_s={woke * 1000 / elapsed_ms:.2f}")
        print(f"MEASURE dnssrv.burst_answered={answered}/{_BURST}")
        assert expected - 1 <= woke <= expected + 1, f"{woke} listener wake-ups in {elapsed_ms} ms, not {expected} +-1 at {_POLL_IDLE_MS} ms"
        assert answered == _BURST, f"{answered} of {_BURST} queries sent together were answered"
        assert burst_rounds <= _BURST + 1, f"the burst took {burst_rounds} listener wake-ups, not back to back (at most {_BURST + 1})"
        assert burst_sleeps <= 1, f"the listener slept {burst_sleeps} idle polls during the burst, not back to back (at most 1)"

    run(_on_driven_clock(scenario))


def test_the_captive_dns_socket_whose_bind_fails_logs_once_then_rebuilds_binds_and_answers() -> None:
    # The listener's first bind refused: one E INIT, that socket torn down, and after the backoff the same UDPSocket builds
    # a fresh socket, binds it and answers a burst (asy_udp_socket.py's teardown and lazy rebuild). Wired as above.
    _driver_specific("neopixel", "fram")

    async def scenario(clock: DrivenTime) -> None:
        with FailNextUdpSetup("address", mode="server") as fault:
            conn, _pixel, tasks = await _hotspot_boot(clock)
        counter = _CountingPoller(conn._dns_server._udps, clock)
        try:
            answered, _rounds, _sleeps = await _dns_burst(counter, clock)
            entry = (await conn._dns_server.get_error_counter())["DNSSRV"]
        finally:
            counter.uninstall()
            await _stop_hotspot(conn, tasks)
        slots = [(kind, n) for kind, n in zip(entry["ErrType"], entry["ErrNum"]) if kind != "N"]
        assert fault.fired == 1, f"the fault failed {fault.fired} binds"
        assert fault.closed()[:1] == [True] and len(fault.made) == 2, f"sockets made, closed or not: {fault.closed()}"
        assert (entry["ErrCount"], slots) == (1, [("E", code("E", "INIT"))]), f"the refused bind logged {entry['ErrCount']}: {slots}"
        assert answered == _BURST, f"{answered} of {_BURST} queries answered by the rebuilt socket"

    run(_on_driven_clock(scenario))


async def _stop_hotspot(conn: "WifiService", tasks: "list[asyncio.Task[None]]") -> None:
    for task in tasks:
        await cancel(task)
    if conn._dns_server_task is not None:  # started inside the WiFi service, not here
        await cancel(conn._dns_server_task)


async def _wait_until(predicate: "Callable[[], bool]", timeout_s: float, interval_s: float = _WAIT_POLL_S, clock: "DrivenTime | None" = None) -> bool:
    # Bounded polling for a real multi-second state transition (mode switches, supervisor cycles). Counts poll
    # iterations, not wall clock: under CPU starvation a wall-clock bound would fail sooner, not later. With a clock,
    # each poll elapses it instead of sleeping, so what waits on it takes no real time.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await (asyncio.sleep(interval_s) if clock is None else clock.elapse(int(interval_s * 1000)))
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


async def _warn_co2() -> int:
    cfg = await module.notification.cfgmgr.get_dict(["WarnCO2"])
    assert cfg is not None
    warn_co2 = cfg["WarnCO2"]
    assert isinstance(warn_co2, int)
    return warn_co2


def _window_around(hour: int) -> "tuple[int, int]":
    # On later than Off, with the current hour (and the next) strictly inside, never on a bound.
    return (hour - 1, hour - 2) if hour >= 2 else (23, hour + 2)


def _wire_link() -> None:
    runner_plan: _Plan = cast("_Plan", plan)
    link = run_generic_integration._wire_uart_crossover(module, runner_plan)  # before the setups (CLAUDE.md "Known hang cause")
    _links[:] = [] if link is None else [link]


def test_sgp40_voc_backup_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    # A real timestamped backup write (SPECIFICATION.md Part A.7), the twin's FRAM image flushed, a new board over the
    # same state path, a real restore. Driver-specific (an SGP40 backed up to FRAM); its L1 suite covers every device.
    _driver_specific("sgp40", "fram")

    async def scenario() -> None:
        cfg_path = _scratch.dir()
        machine.configure_fram_state_path(cfg_path + "fram_state.json")
        await _boot(cfg_path=cfg_path)
        sgp1 = module.sgp40
        await _seed_compensation()
        # WaitTimeNTP at its minimum: the first backup needs no NTP sync.
        persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 1})
        assert persisted
        await _one_backup(sgp1)
        machine.flush_fram()  # the simulated reboot: persisted, then a new board reads the image back
        await _boot(cfg_path=cfg_path)
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
        await _boot(cfg_path=cfg_path)
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
        await _boot(cfg_path=cfg_path)  # the crash-reboot: the image still holds the first backup alone
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
        await _boot(cfg_path=cfg_path)
        await module.ntp._set_synced(value=True)
        asy_base_classes.set_utc_valid()
        module.ntp._clock_valid = True  # the rest of a real sync (_handle_ntp_sync_success()): the backup stamps on it
        sgp1 = module.sgp40
        await _seed_compensation()
        persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 0})
        assert persisted
        await _one_backup(sgp1)
        written = sgp1._last_backup
        assert written, f"the backup was written without a timestamp ({written}) although the clock was set"  # 0: the unset stamp
        machine.flush_fram()
        asy_base_classes.set_utc_valid(valid=False)
        await _boot(cfg_path=cfg_path)
        await _seed_compensation()
        await _restore(module.sgp40, "without NTP")
        status = await module._sgp_maintenance_status_sgp40()
        assert status["RestoreTS"] == written, f"RestoreTS {status['RestoreTS']} is not the backup's own {written}"

    run(scenario())


def test_a_restarted_sgp40_task_keeps_its_live_voc_state() -> None:
    # Fed cycles and one backup on FRAM, then the read task dies and the real supervisor restarts it: no restore, the VOC
    # state counts on, where a reboot restores (the simulated-reboot test above). Driver-specific as above.
    _driver_specific("sgp40", "fram")

    async def scenario() -> None:
        await _boot()
        sysfunct: SystemService = module.sysfunct
        sgp = module.sgp40
        await _seed_compensation()
        persisted, _results = await sgp.cfgmgr.write_config({"WaitTimeNTP": 1})
        assert persisted
        asy_system_service.asyncio = _FastSupervisorAsyncio()  # type: ignore[assignment, attr-defined]  # a pass per yield
        _step_sensor_waits(on=True)
        supervisor: asyncio.Task[None] | None = None
        try:
            await sysfunct.start_tasks([sgp.start_asy_read], task_names=["SGP40"])
            supervisor = asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())
            assert await wait_for_value(lambda: sgp._voc_init, 1, _WAIT_TIMEOUT_MS), "the SGP40 never finished its init"
            await _backup_now(sgp)  # the first cycle: nothing to restore yet, then one backup written
            await _fed_cycle(sgp)
            await _fed_cycle(sgp)
            samples, first = sgp._voc_samples, sysfunct._tasks[0]
            assert (samples, sgp._restored_from) == (3, None), f"{samples} VOC samples, restored from {sgp._restored_from}"
            assert first is not None
            first.cancel()  # the task dies: the supervisor reads only task.done()
            assert await _wait_until(lambda: sysfunct._tasks[0] is not first, _RESTART_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S), "the real supervisor never restarted the SGP40 task"
            await _fed_cycle(sgp)
            restarted = (sgp._voc_samples, sgp._restored_from)
            assert restarted == (samples + 1, None), f"the restarted task restored from FRAM: {restarted}, not ({samples + 1}, None)"
        finally:
            _step_sensor_waits(on=False)
            asy_system_service.asyncio = asyncio  # type: ignore[attr-defined]
            if supervisor is not None:
                await cancel(supervisor)
            if sysfunct._supervisor_task is not None:
                await cancel(sysfunct._supervisor_task)
            for task in sysfunct._tasks:
                if task is not None:
                    await cancel(task)

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
        await _boot()
        _wall_clock.install(run_generic_integration.product_modules())
        notif, ntp, pixel = module.notification, module.ntp, module.neopixel
        # No NTP server here; the clock is the host's. Synced and the RTC flag only: the window reads cettime(), and
        # nothing here reads ntp_clock_valid() (UTCTime, a VOC backup).
        await ntp._set_synced(value=True)
        asy_base_classes.set_utc_valid()
        local = await ntp.cettime()
        assert local is not None
        hour = local.hour
        on_h, off_h = _window_around(hour)
        warn_co2 = await _warn_co2()
        chip = cast("SCD30Chip", _chip("scd30"))
        chip.co2 = Walk(warn_co2 + 100, warn_co2 + 100, 0.0)
        _step_sensor_waits(on=True)
        tasks = [starter() for starter in module.scd30.get_task_starters()]

        async def triggered() -> bool:
            return bool((await notif.get_data()).Triggered)

        async def not_triggered() -> bool:
            return not await triggered()

        try:
            for starter in module.scd30.get_timer_starters():
                starter()
            assert await _measured_above(chip, warn_co2), "the SCD30 never read the CO2 above the warning"
            await _apply_window(on_h, off_h)
            tasks += [pixel.start_asy_signal(), notif.start_asy_monitor()]
            assert await _wait_until(lambda: len(_red_frames(list(pixel._pixel.writes))) > 0, _WINDOW_WAIT_S, interval_s=_BIND_POLL_S), (
                f"no red frame with the window {on_h}:00-{off_h}:00 around local {hour}:{local.minute:02d}"
            )
            assert await _wait_until_async(triggered, _WINDOW_WAIT_S, interval_s=_BIND_POLL_S), "the cycle that flashed never reported Triggered"
            await cancel(tasks.pop())  # the monitor now sleeps its whole FlashInterval; the next window gets a fresh cycle
            assert await _wait_until(lambda: not pixel._start_signal_event.is_set(), _WINDOW_WAIT_S, interval_s=_BIND_POLL_S)
            seen = len(pixel._pixel.writes)

            await _apply_window(off_h, on_h)  # the complementary, same-day window: the current hour is outside
            tasks.append(notif.start_asy_monitor())
            assert await _wait_until_async(not_triggered, _WINDOW_WAIT_S, interval_s=_BIND_POLL_S), "a cycle outside the window reported Triggered"
            assert _red_frames(list(pixel._pixel.writes)[seen:]) == [], "a cycle outside the window flashed"
        finally:
            for task in tasks:
                await cancel(task)
            _step_sensor_waits(on=False)
            asy_base_classes.set_utc_valid(valid=False)

    run(scenario())


def test_a_stopped_scd30_ends_its_alerts_and_sgp40_compensation() -> None:
    # CO2 above WarnCO2 read for real, then ContMeas off through the path PUT /sensors calls and the wall clock stepped
    # past both sample age bounds: the next monitor cycle flashes nothing and reports State 3, the SGP40's next reads send
    # no measure command. Driver-specific (an SCD30 feeding both); both modules' L1 suites cover every device.
    _driver_specific("notification", "scd30", "sgp40")

    async def partial() -> bool:
        data = await module.notification.get_data()
        return (data.State, data.Triggered) == (_PARTIAL, False)

    async def scenario() -> None:
        await _boot()
        clock = _wall_clock.install(run_generic_integration.product_modules())
        scd30, sgp, pixel = module.scd30, module.sgp40, module.neopixel
        # Synced and the RTC flag only: the SGP40's few cycles on a blank FRAM reach neither a backup nor a dated
        # restore, and nothing reads UTCTime, so ntp_clock_valid() is never asked.
        await module.ntp._set_synced(value=True)
        asy_base_classes.set_utc_valid()
        warn_co2 = await _warn_co2()
        chip = cast("SCD30Chip", _chip("scd30"))
        chip.co2 = Walk(warn_co2 + 100, warn_co2 + 100, 0.0)
        sgp_chip: SGP40Chip = cast("SGP40Chip", _chip("sgp40"))
        real_write = sgp_chip.handle_writeto
        measures: list[bytes] = []

        def handle_writeto(data: bytes) -> None:  # the chip's own, its measure commands recorded
            if data[0:2] == _MEASURE_RAW:
                measures.append(data)
            real_write(data)

        sgp_chip.handle_writeto = handle_writeto  # type: ignore[method-assign]  # the instance's own, deleted in finally
        _step_sensor_waits(on=True)
        tasks = [starter() for starter in scd30.get_task_starters()]
        try:
            for starter in scd30.get_timer_starters():
                starter()
            assert await _measured_above(chip, warn_co2), "the SCD30 never read the CO2 above the warning"
            tasks.append(sgp.start_asy_read())
            await _sgp40_cycle(sgp)
            await _sgp40_cycle(sgp)
            assert measures, "a fresh SCD30 sample never compensated an SGP40 measurement"
            results = await scd30._set_dict_cfg({"ContMeas": False}, scd30.get_cfg_schema())
            assert results == {"ContMeas": "Valid"}, results
            clock.step(_STALE_AFTER_S)
            local = await module.ntp.cettime()
            assert local is not None
            await _apply_window(*_window_around(local.hour))
            measured, seen = len(measures), len(pixel._pixel.writes)
            await _sgp40_cycle(sgp)
            await _sgp40_cycle(sgp)
            assert len(measures) == measured, "the SGP40 measured with a stale SCD30 sample"
            tasks += [pixel.start_asy_signal(), module.notification.start_asy_monitor()]
            assert await _wait_until_async(partial, _WINDOW_WAIT_S, interval_s=_BIND_POLL_S), f"a stale CO2 sample reported as {await module.notification.get_data()}"
            assert _red_frames(list(pixel._pixel.writes)[seen:]) == [], "a stale CO2 sample flashed"
        finally:
            for task in tasks:
                await cancel(task)
            del sgp_chip.handle_writeto
            _step_sensor_waits(on=False)
            asy_base_classes.set_utc_valid(valid=False)

    run(scenario())


def test_a_boot_without_ntp_reports_no_local_time() -> None:
    # Booted with no NTP responder, the notification's status data reports no clock (State 2) and no trigger; once a
    # sync has set the clock, the next cycle inside its window evaluates (State 0). Driver-specific (the signals' three
    # drivers); tests/test_asy_notification_service.py covers every device.
    _driver_specific("notification", "scd30", "sgp40")

    async def notified(state: object) -> bool:
        data = await module.notification.get_data()
        return (data.State, data.Triggered) == (state, False)

    async def scenario() -> None:
        await _boot()
        _wall_clock.install(run_generic_integration.product_modules())
        notif, ntp = module.notification, module.ntp
        await _seed_compensation()  # every signal's value present and below its warning
        await module.sgp40._set_meas_data(SGP40(100, None, None, None))
        task = notif.start_asy_monitor()
        try:
            assert await _wait_until_async(lambda: notified(_NO_CLOCK), _WINDOW_WAIT_S), f"no clock reported as {await notif.get_data()}"
        finally:
            await cancel(task)
        # Synced and the RTC flag only: the window reads cettime(), and nothing here reads ntp_clock_valid() (UTCTime,
        # a VOC backup).
        await ntp._set_synced(value=True)
        asy_base_classes.set_utc_valid()
        try:
            local = await ntp.cettime()
            assert local is not None
            await _apply_window(*_window_around(local.hour))
            task = notif.start_asy_monitor()
            assert await _wait_until_async(lambda: notified(_EVALUATED), _WINDOW_WAIT_S), f"a set clock reported as {await notif.get_data()}"
        finally:
            await cancel(task)
            asy_base_classes.set_utc_valid(valid=False)

    run(scenario())


async def _yield_until_above(read: "Callable[[], int]", floor: int) -> bool:
    return await _yield_until(lambda: read() > floor)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
