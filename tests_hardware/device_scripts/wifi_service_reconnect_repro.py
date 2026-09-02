"""Isolated-driver diagnostic script #2 (NOT part of the routine test suite) for REAL FINDING #4 in
tests_hardware/bench/test_network_resilience.py. Diagnostic #1
(wifi_reconnect_after_failed_attempts_repro.py) drove raw `network` module calls directly and found
NO degradation (a real reconnect after 5 failed attempts + an AP round-trip completed in ~3s, same
as a clean control) - ruling out the CYW43 chip/firmware itself. This script instead drives the REAL
src/asy_wifi_service.py AsyConnTime class's own real task loop (wlan_connect(), its own locking,
its own config-read-then-connect sequencing) directly, bypassing only the REST/webserver layer and
the bench-side role-reversal dance - to narrow down whether the bug is in this class's own
orchestration around a real reconnect-after-hotspot-fallback sequence.

Debug level is forced to 5 (_LOG_ALL) so every internal `.all()`-level state transition prints, not
just event/warning/error-level ones - see this class's own _run_sta_mode()/_poll_sta_connect_status()
for what that surfaces (WLAN idle/connecting/obtaining IP/etc, once per wifi_refresh_sec cycle).

Uses the DUT's own real, already-persisted config file (cfg_path="") for Country/Hostname/PW - only
SSID is deliberately overwritten mid-run via the exact same _set_dict_cfg() persistence path the
real REST layer's _apply_settings_groups() uses, then restored the same way - never touches REST
or NetworkManager on the bench side at all.

Run via `mpremote run <this>` (no `soft-reset` chained - board is left with a REAL background
asyncio task running via this ad-hoc asy_wifi_service.AsyConnTime instance, NOT the real
sensortask_wozi.py-driven system - hard_reset() afterward to resume normal operation). Prints one
timestamped line per real state change, plus periodic heartbeats, until either reconnected or a
generous ceiling is hit.
"""

import asyncio
import time

import asy_wifi_service

GARBAGE_SSID = "wozi-diag2-net-does-not-exist"
REAL_SSID = "sensors-bench-ap"

t0 = time.ticks_ms()


def log(msg):
    print("[{:8.2f}s] {}".format(time.ticks_diff(time.ticks_ms(), t0) / 1000.0, msg))


_PHASE_NAMES = {0: "STA_SEEKING", 1: "STA_ESTABLISHED", 2: "HOTSPOT", 3: "DEACTIVATED"}


async def main():
    conn = asy_wifi_service.AsyConnTime(debug=5)
    await conn.setup()
    await conn.pr.setup()
    log("AsyConnTime constructed and set up, cfg SSID/PW/Country/Hostname read from real config file")

    task = conn.start_asy_wlan_connect()
    log("wlan_connect() task started")

    log("--- overwriting SSID with a garbage value via the real _set_dict_cfg() path ---")
    results = await conn._set_dict_cfg({"SSID": GARBAGE_SSID}, conn.get_cfg_schema())
    log("_set_dict_cfg(SSID=garbage) -> {}".format(results))
    conn.reconnect_wifi()
    log("reconnect_wifi() called (simulates the REST post_fct firing)")

    last_phase = None
    last_status = None
    deadline = time.ticks_add(time.ticks_ms(), 180_000)  # up to 3 minutes to reach hotspot
    reached_hotspot = False
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        phase = conn._conn_phase
        status = conn._wlan_status_or_none()
        if phase != last_phase or status != last_status:
            log("phase={} status={} reconn_wifi={} hw_op_failed={} conn_failures={}".format(
                _PHASE_NAMES.get(phase, phase), status, conn.reconn_wifi, conn.hw_op_failed, conn.connection_failures
            ))
            last_phase, last_status = phase, status
        if phase == 2:
            reached_hotspot = True
            break
        if task.done():
            log("wlan_connect() TASK DIED: {}".format(task.exception()))
            return
        await asyncio.sleep(1)

    if not reached_hotspot:
        log("did not reach hotspot phase within 180s - aborting")
        return

    log("=== REACHED HOTSPOT PHASE ===")
    log("--- restoring the real SSID via the real _set_dict_cfg() path ---")
    results = await conn._set_dict_cfg({"SSID": REAL_SSID}, conn.get_cfg_schema())
    log("_set_dict_cfg(SSID=real) -> {}".format(results))
    t_reconnect_trigger = time.ticks_ms()
    conn.reconnect_wifi()
    log("reconnect_wifi() called (simulates the REST post_fct firing again)")

    last_phase = None
    last_status = None
    last_reconn = None
    deadline = time.ticks_add(time.ticks_ms(), 600_000)  # up to 10 minutes
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        phase = conn._conn_phase
        status = conn._wlan_status_or_none()
        reconn = conn.reconn_wifi
        if phase != last_phase or status != last_status or reconn != last_reconn:
            log("phase={} status={} reconn_wifi={} hw_op_failed={} isconnected={}".format(
                _PHASE_NAMES.get(phase, phase), status, reconn, conn.hw_op_failed, conn._wlan_isconnected_or_false()
            ))
            last_phase, last_status, last_reconn = phase, status, reconn
        if conn._wlan_isconnected_or_false():
            elapsed = time.ticks_diff(time.ticks_ms(), t_reconnect_trigger) / 1000.0
            log("=== RECONNECTED after {:.1f}s (measured from reconnect_wifi() call) ===".format(elapsed))
            log("ifconfig: {}".format(conn.wlan.ifconfig()))
            return
        if task.done():
            log("wlan_connect() TASK DIED: {}".format(task.exception()))
            return
        await asyncio.sleep(1)

    log("=== TIMED OUT after 600s waiting for reconnect ===")


asyncio.run(main())
log("=== DIAGNOSTIC END - board has a real ad-hoc AsyConnTime task running, not the real system - "
    "hard_reset() next to resume normal main.py operation ===")
