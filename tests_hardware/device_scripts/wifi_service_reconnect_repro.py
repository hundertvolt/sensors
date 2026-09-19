"""Isolated-driver diagnostic script #2 (NOT part of the routine test suite) - diagnostic #1 found no
degradation at the raw `network` level, so this drives the real asy_wifi_service.AsyConnTime task
loop directly (bypassing only REST/webserver) to narrow down its own reconnect orchestration. Run via `mpremote run <this>` (no soft-reset chain); hard_reset() afterward."""

import asyncio
import os
import time

import asy_wifi_service

GARBAGE_SSID = "wozi-diag2-net-does-not-exist"
# Every persist this script makes goes here instead of config_WIFI.cfg. The repro is driven by the
# in-memory cache, so the production file never needed writing - and writing it is what stranded the
# bench (QUEUE F1). Same convention as reboot_persist_write.py's config_HWTEST_REBOOT.cfg.
_SCRATCH_CFG = "config_HWTEST_WIFI.cfg"

t0 = time.ticks_ms()


def log(msg: str) -> None:
    print(f"[{time.ticks_diff(time.ticks_ms(), t0) / 1000.0:8.2f}s] {msg}")


_PHASE_NAMES = {0: "STA_SEEKING", 1: "STA_ESTABLISHED", 2: "HOTSPOT", 3: "DEACTIVATED"}


async def _set_ssid(conn: "asy_wifi_service.AsyConnTime", ssid: str) -> object:
    return await conn._set_dict_cfg({"SSID": ssid}, conn.get_cfg_schema())


async def _read_live_ssid(conn: "asy_wifi_service.AsyConnTime") -> str:
    # Read the bench's own SSID through the real path rather than hardcoding it: this script writes
    # a garbage value into the RP2040 flash filesystem, and a wrong restore strands the board as
    # badly as none (QUEUE F1 - it happened). The snapshot carries the password, so it is never logged.
    snapshot = await conn._get_dict_cfg(conn.name, conn.get_cfg_schema())
    ssid = snapshot.get(conn.name, {}).get("SSID")
    return ssid if isinstance(ssid, str) else ""


async def main() -> None:
    conn = asy_wifi_service.AsyConnTime(debug=5)
    await conn.setup()
    await conn.pr.setup()
    log("AsyConnTime constructed and set up, cfg SSID/PW/Country/Hostname read from real config file")

    real_ssid = await _read_live_ssid(conn)
    if not real_ssid:
        log("ABORT: could not read the real SSID back, so it could not be restored - refusing to overwrite it")
        return
    # Read the production file first, then divert: from here on config_WIFI.cfg is never opened
    # again, so no crash, reset or racing deferred flush can leave the garbage SSID behind on flash.
    conn.cfgmgr.config_file = _SCRATCH_CFG
    log(f"real SSID captured; persists diverted to {_SCRATCH_CFG}, config_WIFI.cfg is now read-only for this run")

    task = conn.start_asy_wlan_connect()
    log("wlan_connect() task started")

    try:
        await _run_repro(conn, task, real_ssid)
    finally:
        # Re-read rather than tracking a flag: this has to be right whichever path left the repro,
        # including the two early returns and any exception inside it. The cache is what the live
        # service reads, so it is restored even though nothing production was ever written.
        if await _read_live_ssid(conn) != real_ssid:
            log("--- restoring the real SSID in the cache (the flow did not reach its own restore) ---")
            log(f"_set_dict_cfg(SSID=real) -> {await _set_ssid(conn, real_ssid)}")
        await _drop_scratch(conn)


async def _drop_scratch(conn: "asy_wifi_service.AsyConnTime") -> None:
    # The scratch file holds a full WIFI config, real password included - the same secret already on
    # this filesystem, but a second copy nothing else would ever clean up. Wait the deferred flush
    # out first, or the remove races it and the file comes back.
    try:
        await conn.cfgmgr.flush_pending()
        os.remove(_SCRATCH_CFG)
    except OSError as e:
        log(f"could not remove {_SCRATCH_CFG}: {e!r} - delete it by hand")


async def _run_repro(conn: "asy_wifi_service.AsyConnTime", task: "asyncio.Task[None]", real_ssid: str) -> None:
    log("--- overwriting SSID with a garbage value via the real _set_dict_cfg() path ---")
    log(f"_set_dict_cfg(SSID=garbage) -> {await _set_ssid(conn, GARBAGE_SSID)}")
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
            log(f"wlan_connect() TASK DIED: {task.data}")  # `data` is the terminating exception, set by asyncio/core.py's run_until_complete()
            return
        await asyncio.sleep(1)

    if not reached_hotspot:
        log("did not reach hotspot phase within 180s - aborting")
        return

    log("=== REACHED HOTSPOT PHASE ===")
    log("--- restoring the real SSID via the real _set_dict_cfg() path ---")
    log(f"_set_dict_cfg(SSID=real) -> {await _set_ssid(conn, real_ssid)}")
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
            log(f"wlan_connect() TASK DIED: {task.data}")  # `data` is the terminating exception, set by asyncio/core.py's run_until_complete()
            return
        await asyncio.sleep(1)

    log("=== TIMED OUT after 600s waiting for reconnect ===")


asyncio.run(main())
log("=== DIAGNOSTIC END - board has a real ad-hoc AsyConnTime task running, not the real system - "
    "hard_reset() next to resume normal main.py operation ===")
