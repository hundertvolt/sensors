"""Isolated-driver diagnostic script #2 (NOT part of the routine test suite) - diagnostic #1 found no
degradation at the raw `network` level, so this drives the real asy_wifi_service.AsyConnTime task
loop directly (bypassing only REST/webserver) to narrow down its own reconnect orchestration. Run via `mpremote run <this>` (no soft-reset chain); hard_reset() afterward."""

import asyncio
import time

import asy_wifi_service

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

GARBAGE_SSID = "wozi-diag2-net-does-not-exist"
REAL_SSID = "sensors-bench-ap"

t0 = time.ticks_ms()


def log(msg: str) -> None:
    print(f"[{time.ticks_diff(time.ticks_ms(), t0) / 1000.0:8.2f}s] {msg}")


_PHASE_NAMES = {0: "STA_SEEKING", 1: "STA_ESTABLISHED", 2: "HOTSPOT", 3: "DEACTIVATED"}


async def _task_exception(task: "asyncio.Task[Any]") -> BaseException | None:
    # MicroPython's asyncio Task has no .exception()/.result() - awaiting a done task is the only
    # way to recover why it ended (system_service.py's own _log_dead_task() uses the same trick).
    try:
        await task
    except BaseException as e:  # noqa: BLE001 - re-caught verbatim to report, not handle
        return e
    return None


async def main() -> None:
    conn = asy_wifi_service.AsyConnTime(debug=5)
    await conn.setup()
    await conn.pr.setup()
    log("AsyConnTime constructed and set up, cfg SSID/PW/Country/Hostname read from real config file")

    task = conn.start_asy_wlan_connect()
    log("wlan_connect() task started")

    log("--- overwriting SSID with a garbage value via the real _set_dict_cfg() path ---")
    results = await conn._set_dict_cfg({"SSID": GARBAGE_SSID}, conn.get_cfg_schema())
    log(f"_set_dict_cfg(SSID=garbage) -> {results}")
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
            log(f"phase={_PHASE_NAMES.get(phase, phase)} status={status} reconn_wifi={conn.reconn_wifi} hw_op_failed={conn.hw_op_failed} conn_failures={conn.connection_failures}")
            last_phase, last_status = phase, status
        if phase == 2:
            reached_hotspot = True
            break
        if task.done():
            log(f"wlan_connect() TASK DIED: {await _task_exception(task)}")
            return
        await asyncio.sleep(1)

    if not reached_hotspot:
        log("did not reach hotspot phase within 180s - aborting")
        return

    log("=== REACHED HOTSPOT PHASE ===")
    log("--- restoring the real SSID via the real _set_dict_cfg() path ---")
    results = await conn._set_dict_cfg({"SSID": REAL_SSID}, conn.get_cfg_schema())
    log(f"_set_dict_cfg(SSID=real) -> {results}")
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
            log(f"phase={_PHASE_NAMES.get(phase, phase)} status={status} reconn_wifi={reconn} hw_op_failed={conn.hw_op_failed} isconnected={conn._wlan_isconnected_or_false()}")
            last_phase, last_status, last_reconn = phase, status, reconn
        if conn._wlan_isconnected_or_false():
            elapsed = time.ticks_diff(time.ticks_ms(), t_reconnect_trigger) / 1000.0
            log(f"=== RECONNECTED after {elapsed:.1f}s (measured from reconnect_wifi() call) ===")
            log(f"ifconfig: {conn.wlan.ifconfig()}")
            return
        if task.done():
            log(f"wlan_connect() TASK DIED: {await _task_exception(task)}")
            return
        await asyncio.sleep(1)

    log("=== TIMED OUT after 600s waiting for reconnect ===")


asyncio.run(main())
log("=== DIAGNOSTIC END - board has a real ad-hoc AsyConnTime task running, not the real system - "
    "hard_reset() next to resume normal main.py operation ===")
