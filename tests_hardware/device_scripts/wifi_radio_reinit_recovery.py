"""The WiFi radio re-init rung on silicon (SPECIFICATION.md C.7/F.2): the WiFi service, primed in RAM from the
production config_WIFI.cfg read only, connects, runs _recover_device() - deinit() powers the CYW43 off, the next
active(True) reloads its firmware - and connects again; facts out, no config write, the credentials never printed."""

import asyncio
import json
import time

from asy_wifi_service import WifiConfig, WifiService

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts
    from machine import WDT

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_PRODUCTION_CFG = "config_WIFI.cfg"  # read only: src/asy_config_manager.py config_filename("", "WIFI")
# Never set up, so nothing is ever written there: the manager is primed in RAM instead.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
# One attempt's own poll (5 s) plus the DHCP lease the bench AP gives.
# @tunable l3.wifi_radio_reinit_connect_budget_ms = 20000
_CONNECT_BUDGET_MS = 20000
_POLL_MS = 250
# The radio's identity comes from the primed production config; one connect and one recovery never reach the hotspot.
_STREAK, _WINDOW_MIN = 1, 1


async def _connect(conn: "WifiService") -> bool:
    # One production connect attempt, then the link polled up to the budget.
    await conn._attempt_sta_connect()
    started = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), started) < _CONNECT_BUDGET_MS:
        if conn._wlan_isconnected_or_false():
            return True
        await asyncio.sleep_ms(_POLL_MS)
    return conn._wlan_isconnected_or_false()


async def _feed(wdt: "WDT") -> None:
    # Fed beside the whole run, as production's supervisor feeds beside these awaits: a connect poll (up to 5 s), the
    # recovery's settles and firmware reload and a second poll run back to back, far past the 8 s period.
    while True:
        wdt.feed()
        await asyncio.sleep_ms(_POLL_MS)


async def _run() -> None:
    feeder = asyncio.create_task(_feed(arm()))
    try:
        with open(_PRODUCTION_CFG) as f:
            stored = json.load(f)
    except (OSError, ValueError):  # absent (a twin, a board never configured) or malformed: nothing to connect with
        stored = None
    fact("config_read", isinstance(stored, dict))
    fact("budget_ms", _CONNECT_BUDGET_MS)
    if isinstance(stored, dict):
        conn = WifiService(WifiConfig(str(stored.get("Hostname", "")), str(stored.get("HotspotPW", "")), _STREAK, _WINDOW_MIN), cfg_path=_SCRATCH_CFG_PATH)
        conn.cfgmgr.valid = True  # primed, never set up: no flash file is read or written through it
        conn.cfgmgr._cache = {field[0]: stored.get(field[0], field[2]) for field in conn.get_cfg_schema()}
        fact("connected_before", await _connect(conn))
        started = time.ticks_ms()
        fact("recover_returned", await conn._recover_device())
        reconnected = await _connect(conn)
        fact("elapsed_ms", time.ticks_diff(time.ticks_ms(), started))
        fact("reconnected", reconnected)
        fact("ip", conn._wlan.ifconfig()[0] if reconnected else "")
    feeder.cancel()
    done()


asyncio.run(_run())
