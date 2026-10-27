"""The Wi-Fi modes after a hotspot ran, on one driven clock: one boot of a generated device's real graph on the twin
walks the stations rule, the fresh-boot settings hook and the silent mode in turn, once per distinct wiring of the
Wi-Fi LED's NeoPixel and the FRAM WIFI's log persists to (SPECIFICATION.md Part E.2.1)."""

import asyncio
import sys

sys.path.insert(0, "ext")  # the vendored ext/microdot.py that every generated device module imports
sys.path.insert(0, "digital_twin")  # the twin's machine, network and neopixel fakes, ahead of tests/'s own
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

# Before any poll object is registered: the Unix port's pollfds growth corrupts non-fd entries
# already in it, a segfault rather than a failure (digital_twin/README.md "Known gaps").
prewarm_poll_set()
# Before CaptiveDNS's UDPSocket is constructed, inside WifiService: this Unix-port build rejects a plain
# (host, port) tuple in bind()/connect()/sendto() (SPECIFICATION.md Part A.10).
patch_asy_udp_socket_for_unix_port()

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import distinct_wirings, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim
from network import STAT_GOT_IP, set_access_point_up  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_wifi_service  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import ModuleType
    from typing import TypeVar

    from network import WLAN

    from asy_wifi_service import WifiService

    T = TypeVar("T")

# @tunable l2.wifi_modes_wait_poll_s = 0.1
_WAIT_POLL_S = 0.1
# @tunable l2.wifi_modes_wait_timeout_s = 25.0
_WAIT_TIMEOUT_S = 25.0
# @tunable l2.wifi_modes_run_bound_s = 200.0
_RUN_BOUND_S = 200.0
_POOL = 16  # rp2's alarm pool: digital_twin/machine.py's _ALARM_POOL_SIZE
# The WiFi service's own sleeps run this many times faster: its periods and settles are not under test, its transitions.
# @tunable l2.wifi_modes_sleep_scale = 5
_SLEEP_SCALE = 5
_WEB_PORT = 19200  # a range of its own beside the other twin files'; never bound, as the scenario starts no webserver

_scratch = TmpScratch("wifi_modes")
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)


class _ScaledAsyncio:
    # asy_wifi_service's view of asyncio, each sleep _SLEEP_SCALE times shorter and parked on the driven clock
    # (tests/_fake_time.py); everything else the real module.
    def __init__(self, clock: DrivenTime) -> None:
        self._clock = clock

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    async def sleep(self, seconds: float) -> None:
        await self._clock._sleep_ms(int(seconds / _SLEEP_SCALE * 1000))  # asyncio's own conversion (extmod/asyncio/core.py)

    async def sleep_ms(self, ms: int) -> None:
        await self._clock._sleep_ms(ms // _SLEEP_SCALE)


async def _await_failed_arm(clock: DrivenTime, conn: "WifiService", site: str, trigger: "Callable[[], None]") -> None:
    # `trigger` leads to the site's window arm, refused: one more E TIMER persisted, the streak fed, the timer not
    # running, and the "hotspot timer started" line never printed; conn.pr.evt is wrapped from before the trigger.
    lines: list[tuple[object, ...]] = []
    errors = (await _wifi_log(conn))[1].count(("E", code("E", "TIMER")))
    conn.pr.evt = lambda *args, **_kwargs: lines.append(args)  # type: ignore[method-assign]  # records, deleted below
    try:
        trigger()

        async def failed() -> bool:
            return (await _wifi_log(conn))[1].count(("E", code("E", "TIMER"))) > errors

        persisted = await _wait_until_async(clock, failed)
        assert persisted, site + ": the refused arm persisted no E TIMER"
        fed = await _wait_until(clock, lambda: conn._err_cnt_internal >= 1)
    finally:
        del conn.pr.evt
    assert fed, site + ": the refused arm never fed the hardware streak"
    assert not conn._hotspot_timer_running, site + ": the timer reads running after a refused arm"
    assert not any("hotspot timer started" in " ".join(str(a) for a in line) for line in lines), (site, lines)


async def _await_hotspot_window(clock: DrivenTime, conn: "WifiService", streak: str) -> None:
    # The streak under way fast-forwarded to its last attempt (set once it runs, after any reset zeroed the count), then
    # the hotspot up with its window armed - at once in the twin, whose AP reports no link.
    conn._connection_failures = conn._conn_fail_to_hotspot - 1
    armed = await _wait_until(clock, lambda: conn._hotspot_started_once and conn._hotspot_timer_running)
    assert armed and conn.is_hotspot_active(), streak + " never opened the hotspot's window"


async def _boot(device: str) -> "ModuleType":
    # The generated main()'s first two steps on the twin buses: build_system() with the watchdog the boot entry arms,
    # then the setup list. The wiring plan goes first: every twin bus construction reads it.
    machine.configure_wiring(wiring_plan(device))
    module = run_generic_integration.load_module("sensortask_" + device)
    watchdog = machine.WDT(timeout=run_generic_integration._WDT_TIMEOUT_MS)
    cfg_path = _scratch.dir()
    write_error_level_config(cfg_path)
    await module.build_system(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=_WEB_PORT)
    await module.sysfunct.run_setups(module._collect_setups())
    return module


async def _end_hotspot_window(clock: DrivenTime, conn: "WifiService") -> None:
    # The window's end fired through the twin Timer's stored callback, the streak after it fast-forwarded the same way
    # (the window's end keeps the count); returns once that streak has ended in the silent mode.
    silent = _wifi_const("_PHASE_SILENT")
    conn._connection_failures = conn._conn_fail_to_hotspot - 1
    _fire(conn._hotspot_timer)
    reached = await _wait_until(clock, lambda: conn._conn_phase == silent)
    assert reached, "(b) the streak after the hotspot window ended in phase " + str(conn._conn_phase) + ", not the silent mode"


def _fast_forward(conn: "WifiService") -> None:
    # The streak under way fast-forwarded to its last attempt, as _await_hotspot_window() does.
    conn._connection_failures = conn._conn_fail_to_hotspot - 1


def _fire(timer: "machine.Timer") -> None:
    # One period's end as the timer delivers it: the twin's Timer keeps the callback it was armed with.
    assert timer.callback is not None, "the window's timer is not armed"
    timer.callback(timer)


async def _driven(clock: DrivenTime, what: str, coro: "Coroutine[object, object, T]") -> "T":
    # `coro` as a task, the driven clock elapsed wake by wake until it ends (tests/test_digital_twin_hot_replug.py's own).
    task = asyncio.get_event_loop().create_task(coro)
    try:
        await clock.run_until(task.done, int(_WAIT_TIMEOUT_S * 1000))
    except AssertionError as e:
        raise AssertionError(f"{what} - {e}") from None
    return await task


def _driven_modules() -> "list[object]":
    # Every src module holding asyncio and the twin's machine and network: one clock for each sleep and tick read.
    return [m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio]


async def _first_attempt(clock: DrivenTime, conn: "WifiService") -> None:
    started = await _wait_until(clock, lambda: len(conn._wlan.connect_calls) > 0)
    assert started, "(c) the boot streak never made its first attempt"


def _run_scaled(device: str, scenario: "Callable[[str, DrivenTime], Coroutine[object, object, None]]") -> None:
    # The scenario on one driven clock over every module holding asyncio (the device's module loaded first), the WiFi
    # service's sleeps scaled down on it; each module's own view is back after it.
    run_generic_integration.load_module("sensortask_" + device)
    with DrivenTime(*_driven_modules(), sleeps=True) as clock:
        held = asy_wifi_service.asyncio  # type: ignore[attr-defined]
        asy_wifi_service.asyncio = _ScaledAsyncio(clock)  # type: ignore[assignment, attr-defined]
        try:
            run_timed(scenario(device, clock), timeout_s=_RUN_BOUND_S)
        finally:
            asy_wifi_service.asyncio = held  # type: ignore[attr-defined]


async def _stop_scenario(conn: "WifiService", tasks: "list[asyncio.Task[None]]") -> None:
    # The access point switched back, the window's timer stopped and every task the scenario or the service started
    # cancelled, so none outlives the scenario.
    set_access_point_up(up=True)
    conn._hotspot_timer.deinit()
    for task in tasks + [conn._dns_server_task, conn._ledflash]:
        if task is not None:
            await cancel(task)


async def _wait_until(clock: DrivenTime, predicate: "Callable[[], bool]", timeout_s: float = _WAIT_TIMEOUT_S, interval_s: float = _WAIT_POLL_S) -> bool:
    # Bounded polling for a multi-second transition, each poll elapsing the driven clock: counts poll iterations, so
    # what waits on the clock takes no real time.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await clock.elapse(int(interval_s * 1000))
        elapsed += interval_s
    return predicate()


async def _wait_until_async(clock: DrivenTime, predicate: "Callable[[], Coroutine[object, object, bool]]", timeout_s: float = _WAIT_TIMEOUT_S) -> bool:
    # _wait_until() for a predicate that must await (a module's error log).
    elapsed = 0.0
    while elapsed < timeout_s:
        if await predicate():
            return True
        await clock.elapse(int(_WAIT_POLL_S * 1000))
        elapsed += _WAIT_POLL_S
    return await predicate()


def _wifi_const(name: str) -> int:
    # A phase's value from src/asy_wifi_service.py's source: a const() is not a module attribute on MicroPython.
    with open("src/asy_wifi_service.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0])
    raise AssertionError(name + " not found in src/asy_wifi_service.py")


async def _wifi_log(conn: "WifiService") -> "tuple[int, list[tuple[str, int]]]":
    # WIFI's persisted history as (type, number) pairs, beside its count of every logged call.
    entry = (await conn.get_error_counter())["WIFI"]
    return entry["ErrCount"], list(zip(entry["ErrType"], entry["ErrNum"]))


def test_stations_rule_settings_change_and_silent_mode_in_one_boot() -> None:
    # (c) An unconfirmed stations check counts as no client (owner, 2026-10-08, paraphrase). (a) "Any change of
    # credentials, no matter from which side, lands in the same mode as "initial connection attempt after a fresh boot""
    # (owner, 2026-10-08). (b) "Don't permanently switch WiFi off, only stop retrying to connect." (owner, 2026-10-08)
    async def scenario(device: str, clock: DrivenTime) -> None:
        module = await _driven(clock, "the boot", _boot(device))
        conn, pixel, webserver = module.conn, module.neopixel, module.webserver
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet", "LEDWifiOn": False})
        assert persisted
        seeking, silent, established = _wifi_const("_PHASE_STA_SEEKING"), _wifi_const("_PHASE_SILENT"), _wifi_const("_PHASE_STA_ESTABLISHED")
        to_hotspot, unknown, silent_entry = ("W", code("W", "WLAN_TO_HOTSPOT")), ("W", code("W", "WLAN_STATIONS_UNKNOWN")), ("W", code("W", "WLAN_SILENT"))
        set_access_point_up(up=False)
        tasks = [pixel.start_asy_overlay(), conn.start_asy_hotspot_timeout(), conn.start_asy_connect()]
        ap: WLAN | None = None
        try:
            await _first_attempt(clock, conn)
            await _await_hotspot_window(clock, conn, "(c) the boot streak")
            # (c) rp2's answer with the radio down (32 unfilled entries) restarts the window a listed client had stopped,
            # persisted once however often it recurs.
            assert conn._ap_selected, "(c) the boot hotspot runs on another interface than the AP"
            ap = conn._wlan
            # An active AP reports STAT_GOT_IP, as on silicon (owner, 2026-09-29); one listed client is poked in, so the
            # stations check runs at all.
            assert ap.status() == STAT_GOT_IP, "(c) the active twin AP reports no link"
            ap._stations = [(b"\x02\x00\x00\x00\x00\x01",)]
            stopped = await _wait_until(clock, lambda: not conn._hotspot_timer_running)
            assert stopped, "(c) a listed client never stopped the hotspot window"
            ap.stations_chip_down = True
            rearmed = await _wait_until(clock, lambda: conn._hotspot_timer_running)
            assert rearmed and conn.is_hotspot_active(), "(c) an unconfirmed stations check left the window stopped"
            count, log = await _wifi_log(conn)
            assert log.count(unknown) == 1, ("(c)", log)

            async def checked_again() -> bool:
                return (await _wifi_log(conn))[0] > count

            again = await _wait_until_async(clock, checked_again)
            _count, log = await _wifi_log(conn)
            assert again and log.count(unknown) == 1 and conn._hotspot_timer_running, ("(c) a further check", log)
            # (a) A credentials change through the identity group's config-apply path, the one PUT /networking takes: its
            # failed streak reopens the hotspot once more. LEDWifiOn off keeps the pixel dark through both hotspot phases.
            results = await webserver._apply_settings_groups("networking", {"SSID": "OtherNet", "PW": "otherpassword"})
            assert results == {"SSID": "Valid", "PW": "Valid"}, ("(a)", results)
            left = await _wait_until(clock, lambda: not conn._reconnect_fresh and conn._conn_phase == seeking)
            assert left and not conn._hotspot_started_once, "(a) the settings change did not land in the fresh-boot state"
            # The window's arm failing (the alarm pool empty) is the iteration's hardware failure: one E TIMER, the
            # streak fed, no "timer started" line (owner, 2026-10-13: "Take option b for 2"); the pool back, it arms.
            machine.set_alarm_pool_free(0)
            await _await_failed_arm(clock, conn, "(a) the reopened hotspot's window", lambda: _fast_forward(conn))
            machine.set_alarm_pool_free(_POOL)
            await _await_hotspot_window(clock, conn, "(a) the settings change's failed streak")
            _count, log = await _wifi_log(conn)
            assert (log.count(to_hotspot), log.count(silent_entry)) == (2, 0), ("(a)", log)
            assert len(pixel._pixel.writes) > 0 and all(frame == [(0, 0, 0)] for frame in pixel._pixel.writes), ("(a) LEDWifiOn off", list(pixel._pixel.writes))
            # LEDWifiOn on through its own group, a live push that reconnects nothing: the silent mode is then dark although enabled.
            results = await webserver._apply_settings_groups("networking", {"LEDWifiOn": True})
            assert results == {"LEDWifiOn": "Valid"} and not conn._reconn_wifi, ("(b) LEDWifiOn on", results)
            # (b) The window ends and the second streak goes silent: no hotspot, the STA interface, the LED dark.
            await _end_hotspot_window(clock, conn)
            assert (conn.is_hotspot_active(), conn._dns_server_task, conn._ap_selected) == (False, None, False), "(b) a hotspot is left in the silent mode"
            pixel._pixel.writes.clear()  # every frame from here on is the silent mode's
            # A task restart keeps the mode and re-arms its period; with the pool empty that arm fails as the window's
            # does, the streak fed and the mode kept, and the pool back it arms (owner, 2026-10-13, as above).
            await cancel(tasks.pop())
            machine.set_alarm_pool_free(0)
            await _await_failed_arm(clock, conn, "(b) the silent mode's period", lambda: tasks.append(conn.start_asy_connect()))
            assert conn._conn_phase == silent, "(b) a failed period arm left the silent mode"
            machine.set_alarm_pool_free(_POOL)
            rearmed = await _wait_until(clock, lambda: conn._hotspot_timer_running)
            assert rearmed and conn._conn_phase == silent, "(b) a task restart in the silent mode lost the mode or its period"
            # One period with the network still down: one attempt, no link, still silent and dark.
            calls = len(conn._wlan.connect_calls)
            _fire(conn._hotspot_timer)
            tried = await _wait_until(clock, lambda: len(conn._wlan.connect_calls) > calls and not conn.wifi_mode_lock.locked())
            assert tried and len(conn._wlan.connect_calls) == calls + 1, "(b) a silent period made no single attempt"
            assert conn._conn_phase == silent and not conn.is_hotspot_active(), "(b) a failed silent attempt left the silent mode"
            assert len(pixel._pixel.writes) > 0 and all(frame == [(0, 0, 0)] for frame in pixel._pixel.writes), ("(b) LEDWifiOn on", list(pixel._pixel.writes))
            _count, log = await _wifi_log(conn)
            assert log.count(silent_entry) == 1, ("(b)", log)
            # The network back: the next period's attempt is an ordinary connection, its LED as LEDWifiOn says.
            set_access_point_up(up=True)
            _fire(conn._hotspot_timer)
            linked = await _wait_until(clock, lambda: conn._conn_phase == established and not conn._hotspot_timer_running)
            assert linked, "(b) the silent mode's attempt never linked once the access point was back"
            lit = await _wait_until(clock, lambda: pixel._pixel.writes[-1] != [(0, 0, 0)])
            assert lit, "(b) the link left the Wi-Fi LED dark although LEDWifiOn is on"
        finally:
            if ap is not None:
                ap.stations_chip_down = False
            await _stop_scenario(conn, tasks)

    # One run per distinct wiring of what the scenario reads, chosen by the generated plans, never by name: the Wi-Fi
    # LED's NeoPixel and the FRAM WIFI's log persists to (the Wi-Fi service itself is on every device).
    for device in distinct_wirings("neopixel", "fram"):
        machine.reset_test_state()  # the file's per-test reset: a run never inherits the previous device's board
        network.reset_test_state()
        _run_scaled(device, scenario)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
