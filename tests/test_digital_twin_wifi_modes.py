"""The Wi-Fi modes after a hotspot ran, at the product's real waits: one boot of a generated device's real graph on the
twin walks the stations rule, the fresh-boot settings hook and the silent mode in turn. Its own file for those waits'
wall time; one device, picked from the generated plans, as SPECIFICATION.md Part E.2.1 says for the in-process tier."""

import asyncio
import json
import os
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

import machine  # noqa: E402
import run_generic_integration  # noqa: E402
from _error_codes import code  # noqa: E402
from _tmp_scratch import TmpScratch  # noqa: E402
from network import STAT_GOT_IP, set_access_point_up  # noqa: E402

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

# @tunable l2.wifi_modes_wait_poll_s = 0.25
_WAIT_POLL_S = 0.25
# @tunable l2.wifi_modes_wait_timeout_s = 25.0
_WAIT_TIMEOUT_S = 25.0
# @tunable l2.wifi_modes_run_bound_s = 200.0
_RUN_BOUND_S = 200.0
_WEB_PORT = 19200  # a range of its own beside the other twin files'; never bound, as the scenario starts no webserver

_scratch = TmpScratch("wifi_modes")


async def _await_hotspot_window(conn: "WifiService", streak: str) -> None:
    # The streak under way fast-forwarded to its last attempt (set once it runs, after any reset zeroed the count), then
    # the hotspot up with its window armed - at once in the twin, whose AP reports no link.
    conn._connection_failures = conn._conn_fail_to_hotspot - 1
    armed = await _wait_until(lambda: conn._hotspot_started_once and conn._hotspot_timer_running)
    assert armed and conn.is_hotspot_active(), streak + " never opened the hotspot's window"


async def _boot() -> "ModuleType":
    # The generated main()'s first two steps on the twin buses: build_system() with the watchdog the boot entry arms,
    # then the setup list. The wiring plan goes first: every twin bus construction reads it.
    plan = _scenario_plan()
    machine.configure_wiring(plan)
    module = run_generic_integration.load_module("sensortask_" + str(plan["device"]))
    watchdog = machine.WDT(timeout=run_generic_integration._WDT_TIMEOUT_MS)
    await module.build_system(watchdog=watchdog, cfg_path=_scratch.dir(), web_host="127.0.0.1", web_port=_WEB_PORT)
    await module.sysfunct.run_setups(module._collect_setups())
    return module


async def _cancel(task: "asyncio.Task[None]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _end_hotspot_window(conn: "WifiService") -> None:
    # The window's end fired through the twin Timer's stored callback, the streak after it fast-forwarded the same way
    # (the window's end keeps the count); returns once that streak has ended in the silent mode.
    silent = _wifi_const("_PHASE_SILENT")
    conn._connection_failures = conn._conn_fail_to_hotspot - 1
    _fire(conn._hotspot_timer)
    reached = await _wait_until(lambda: conn._conn_phase == silent)
    assert reached, "(b) the streak after the hotspot window ended in phase " + str(conn._conn_phase) + ", not the silent mode"


def _fire(timer: "machine.Timer") -> None:
    # One period's end as the timer delivers it: the twin's Timer keeps the callback it was armed with.
    assert timer.callback is not None, "the window's timer is not armed"
    timer.callback(timer)


async def _first_attempt(conn: "WifiService") -> None:
    started = await _wait_until(lambda: len(conn._wlan.connect_calls) > 0)
    assert started, "(c) the boot streak never made its first attempt"


def _run_timed(coro: "Coroutine[object, object, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


def _scenario_plan() -> "dict[str, object]":
    # The device comes from the generated plans, chosen by what the scenario reads, never by name: the Wi-Fi LED's
    # neopixel and the FRAM that WIFI's log persists to. The Wi-Fi service itself is mandatory on every device.
    for name in sorted(os.listdir("build/generated_src")):
        if name.endswith("_wiring_plan.json"):
            with open("build/generated_src/" + name) as f:
                plan: dict[str, object] = json.load(f)
            instances = plan.get("instances")
            if isinstance(instances, list) and "neopixel" in instances and "fram" in instances:
                return plan
    raise AssertionError("no generated device wires a neopixel and a FRAM")


async def _stop_scenario(conn: "WifiService", tasks: "list[asyncio.Task[None]]") -> None:
    # The access point switched back, the window's timer stopped and every task the scenario or the service started
    # cancelled, so none outlives the scenario.
    set_access_point_up(up=True)
    conn._hotspot_timer.deinit()
    for task in tasks + [conn._dns_server_task, conn._ledflash]:
        if task is not None:
            await _cancel(task)


async def _wait_until(predicate: "Callable[[], bool]", timeout_s: float = _WAIT_TIMEOUT_S, interval_s: float = _WAIT_POLL_S) -> bool:
    # Bounded polling for a real multi-second transition. Counts poll iterations, not wall clock: under CPU
    # starvation a wall-clock bound would fail sooner, not later, since every sleep overruns.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return predicate()


async def _wait_until_async(predicate: "Callable[[], Coroutine[object, object, bool]]", timeout_s: float = _WAIT_TIMEOUT_S) -> bool:
    # _wait_until() for a predicate that must await (a module's error log).
    elapsed = 0.0
    while elapsed < timeout_s:
        if await predicate():
            return True
        await asyncio.sleep(_WAIT_POLL_S)
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
    return entry["ErrCount"], list(zip(entry["ErrType"], entry["ErrNum"]))  # noqa: B905 - MicroPython zip() rejects strict=


def test_stations_rule_settings_change_and_silent_mode_in_one_boot() -> None:
    # (c) An unconfirmed stations check counts as no client (owner, 2026-10-08, paraphrase). (a) "Any change of credentials, no
    # matter from which side, lands in the same mode as "initial connection attempt after a fresh boot"" (owner, 2026-10-08).
    # (b) "Don't permanently switch WiFi off, only stop retrying to connect." (owner, 2026-10-08)
    async def scenario() -> None:
        module = await _boot()
        conn, pixel, webserver = module.conn, module.neopixel, module.webserver
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet", "LEDWifiOn": False})
        assert persisted
        seeking, silent, established = _wifi_const("_PHASE_STA_SEEKING"), _wifi_const("_PHASE_SILENT"), _wifi_const("_PHASE_STA_ESTABLISHED")
        to_hotspot, unknown, silent_entry = ("W", code("W", "WLAN_TO_HOTSPOT")), ("W", code("W", "WLAN_STATIONS_UNKNOWN")), ("W", code("W", "WLAN_SILENT"))
        set_access_point_up(up=False)
        tasks = [pixel.start_asy_overlay(), conn.start_asy_hotspot_timeout(), conn.start_asy_connect()]
        ap: WLAN | None = None
        try:
            await _first_attempt(conn)
            await _await_hotspot_window(conn, "(c) the boot streak")
            # (c) rp2's answer with the radio down (32 unfilled entries) restarts the window a listed client had stopped,
            # persisted once however often it recurs.
            assert conn._ap_selected, "(c) the boot hotspot runs on another interface than the AP"
            ap = conn._wlan
            # The twin's AP never reports a link (its AP-mode gap, digital_twin/README.md "What's here"), where an active
            # AP on silicon reports STAT_GOT_IP (owner, 2026-09-29): poked here, so the stations check runs at all.
            ap._status = STAT_GOT_IP
            ap._stations = [(b"\x02\x00\x00\x00\x00\x01",)]
            stopped = await _wait_until(lambda: not conn._hotspot_timer_running)
            assert stopped, "(c) a listed client never stopped the hotspot window"
            ap.stations_chip_down = True
            rearmed = await _wait_until(lambda: conn._hotspot_timer_running)
            assert rearmed and conn.is_hotspot_active(), "(c) an unconfirmed stations check left the window stopped"
            count, log = await _wifi_log(conn)
            assert log.count(unknown) == 1, ("(c)", log)

            async def checked_again() -> bool:
                return (await _wifi_log(conn))[0] > count

            again = await _wait_until_async(checked_again)
            _count, log = await _wifi_log(conn)
            assert again and log.count(unknown) == 1 and conn._hotspot_timer_running, ("(c) a further check", log)
            # (a) A credentials change through the identity group's config-apply path, the one PUT /networking takes: its
            # failed streak reopens the hotspot once more. LEDWifiOn off keeps the pixel dark through both hotspot phases.
            results = await webserver._apply_settings_groups("networking", {"SSID": "OtherNet", "PW": "otherpassword"})
            assert results == {"SSID": "Valid", "PW": "Valid"}, ("(a)", results)
            left = await _wait_until(lambda: not conn._reconnect_fresh and conn._conn_phase == seeking)
            assert left and not conn._hotspot_started_once, "(a) the settings change did not land in the fresh-boot state"
            await _await_hotspot_window(conn, "(a) the settings change's failed streak")
            _count, log = await _wifi_log(conn)
            assert (log.count(to_hotspot), log.count(silent_entry)) == (2, 0), ("(a)", log)
            assert len(pixel._pixel.writes) > 0 and all(frame == [(0, 0, 0)] for frame in pixel._pixel.writes), ("(a) LEDWifiOn off", list(pixel._pixel.writes))
            # LEDWifiOn on through its own group, a live push that reconnects nothing: the silent mode is then dark although enabled.
            results = await webserver._apply_settings_groups("networking", {"LEDWifiOn": True})
            assert results == {"LEDWifiOn": "Valid"} and not conn._reconn_wifi, ("(b) LEDWifiOn on", results)
            # (b) The window ends and the second streak goes silent: no hotspot, the STA interface, the LED dark.
            await _end_hotspot_window(conn)
            assert (conn.is_hotspot_active(), conn._dns_server_task, conn._ap_selected) == (False, None, False), "(b) a hotspot is left in the silent mode"
            while len(pixel._pixel.writes):  # every frame from here on is the silent mode's
                pixel._pixel.writes.popleft()
            # A task restart keeps the mode and re-arms its period.
            await _cancel(tasks.pop())
            tasks.append(conn.start_asy_connect())
            rearmed = await _wait_until(lambda: conn._hotspot_timer_running)
            assert rearmed and conn._conn_phase == silent, "(b) a task restart in the silent mode lost the mode or its period"
            # One period with the network still down: one attempt, no link, still silent and dark.
            calls = len(conn._wlan.connect_calls)
            _fire(conn._hotspot_timer)
            tried = await _wait_until(lambda: len(conn._wlan.connect_calls) > calls and not conn.wifi_mode_lock.locked())
            assert tried and len(conn._wlan.connect_calls) == calls + 1, "(b) a silent period made no single attempt"
            assert conn._conn_phase == silent and not conn.is_hotspot_active(), "(b) a failed silent attempt left the silent mode"
            assert len(pixel._pixel.writes) > 0 and all(frame == [(0, 0, 0)] for frame in pixel._pixel.writes), ("(b) LEDWifiOn on", list(pixel._pixel.writes))
            _count, log = await _wifi_log(conn)
            assert log.count(silent_entry) == 1, ("(b)", log)
            # The network back: the next period's attempt is an ordinary connection, its LED as LEDWifiOn says.
            set_access_point_up(up=True)
            _fire(conn._hotspot_timer)
            linked = await _wait_until(lambda: conn._conn_phase == established and not conn._hotspot_timer_running)
            assert linked, "(b) the silent mode's attempt never linked once the access point was back"
            lit = await _wait_until(lambda: pixel._pixel.writes[-1] != [(0, 0, 0)])
            assert lit, "(b) the link left the Wi-Fi LED dark although LEDWifiOn is on"
        finally:
            if ap is not None:
                ap.stations_chip_down = False
            await _stop_scenario(conn, tasks)

    _run_timed(scenario(), timeout_s=_RUN_BOUND_S)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
