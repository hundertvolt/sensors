"""Isolated-driver diagnostic script (NOT part of the routine test suite) - a one-off repro of why
reconnecting to a known-good SSID after a failure history + AP-mode round-trip took 5-10+ minutes
versus ~20s with no prior failures. Run via `mpremote run <this>` (no soft-reset chain); recover afterward via hard_reset()."""

import time

import network

REAL_SSID = "sensors-bench-ap"
REAL_PW = "pta2ToWIVkFIYHm7SDne"
COUNTRY = "DE"
GARBAGE_SSID = "wozi-diag-net-does-not-exist"
HOTSPOT_HOSTNAME = "sensornode-dev"

_STAT_OBTAINING_IP = 2  # matches asy_wifi_service.py's own module-level constant

t0 = time.ticks_ms()


def log(msg):
    print(f"[{time.ticks_diff(time.ticks_ms(), t0) / 1000.0:8.2f}s] {msg}")


def status_name(status):
    names = {
        network.STAT_IDLE: "IDLE",
        network.STAT_CONNECTING: "CONNECTING",
        _STAT_OBTAINING_IP: "OBTAINING_IP",
        network.STAT_WRONG_PASSWORD: "WRONG_PASSWORD",
        network.STAT_NO_AP_FOUND: "NO_AP_FOUND",
        network.STAT_CONNECT_FAIL: "CONNECT_FAIL",
        network.STAT_GOT_IP: "GOT_IP",
    }
    return names.get(status, f"UNKNOWN({status})")


def wait_for_outcome(wlan, max_polls, poll_ms, label):
    """Chatty poll loop, same shape as asy_wifi_service.py's own _poll_sta_connect_status() but
    logging every single poll (not just on entry) and returning the final status seen."""
    last = None
    for i in range(max_polls):
        try:
            status = wlan.status()
        except Exception as e:
            log(f"{label}: wlan.status() raised {type(e).__name__}: {e}")
            return None
        if status != last:
            log(f"{label}: poll {i} -> {status_name(status)}")
            last = status
        if status in (network.STAT_GOT_IP, network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND, network.STAT_CONNECT_FAIL):
            return status
        time.sleep_ms(poll_ms)
    log(f"{label}: gave up after {max_polls} polls, last status {status_name(last)}")
    return last


log("=== DIAGNOSTIC START ===")
network.country(COUNTRY)
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
try:
    wlan.deinit()
except Exception as e:
    log(f"initial deinit() raised (expected if never active): {type(e).__name__}: {e}")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(pm=0xA11140)
log("STA interface freshly (re)constructed and active")

# ---------------------------------------------------------------------------
# CONTROL: connect to the real SSID from this clean slate.
# ---------------------------------------------------------------------------
log(f"--- CONTROL: connecting to real SSID {REAL_SSID!r} ---")
t_control_start = time.ticks_ms()
wlan.connect(REAL_SSID, REAL_PW)
outcome = wait_for_outcome(wlan, max_polls=240, poll_ms=500, label="CONTROL")  # up to 120s
control_elapsed_s = time.ticks_diff(time.ticks_ms(), t_control_start) / 1000.0
log("CONTROL result: {} after {:.1f}s".format(status_name(outcome) if outcome is not None else "ERROR", control_elapsed_s))
if outcome == network.STAT_GOT_IP:
    log(f"CONTROL ifconfig: {wlan.ifconfig()}")

wlan.disconnect()
time.sleep(1)
log("CONTROL phase done, disconnected")

# ---------------------------------------------------------------------------
# TREATMENT: 5 real failed connects to a garbage SSID, mirroring asy_wifi_service.py's own
# wifi_refresh_sec=5s cadence between attempts and its own 0.5s poll interval within each attempt.
# ---------------------------------------------------------------------------
log(f"--- TREATMENT: 5 real failed connect attempts to {GARBAGE_SSID!r} ---")
for attempt in range(5):
    log(f"TREATMENT attempt {attempt + 1}/5: wlan.connect({GARBAGE_SSID!r})")
    wlan.connect(GARBAGE_SSID, "irrelevant1")
    outcome = wait_for_outcome(wlan, max_polls=10, poll_ms=500, label=f"TREATMENT-attempt-{attempt + 1}")
    log("TREATMENT attempt {}/5 result: {}".format(attempt + 1, status_name(outcome) if outcome is not None else "ERROR"))
    time.sleep(5)  # wifi_refresh_sec cadence

# ---------------------------------------------------------------------------
# Real AP-mode round-trip, mirroring _configure_hotspot_ap() then _switch_wlan_mode(STA_IF).
# ---------------------------------------------------------------------------
log("--- switching to AP mode (mirrors _configure_hotspot_ap()) ---")
wlan.disconnect()
wlan.active(False)
time.sleep(2)
wlan.deinit()
time.sleep(1)
ap = network.WLAN(network.AP_IF)
network.hostname(HOTSPOT_HOSTNAME)
ap.config(essid=HOTSPOT_HOSTNAME, password="12345678")
ap.active(True)
ap.config(pm=0xA11140)
log(f"AP mode active: ifconfig={ap.ifconfig()}")
log("holding AP mode for 10s (mirrors a brief real hotspot dwell)")
time.sleep(10)

log("--- leaving AP mode, switching back to STA (mirrors _switch_wlan_mode(STA_IF)) ---")
ap.active(False)
time.sleep(2)
ap.deinit()
time.sleep(1)
wlan = network.WLAN(network.STA_IF)
time.sleep(1)
wlan.active(True)
wlan.config(pm=0xA11140)
log("STA interface reconstructed after AP round-trip")

# ---------------------------------------------------------------------------
# Reconnect to the SAME real SSID again - this is the step that took minutes in the full
# REST/asy_wifi_service.py-level repro. Timed the same way as CONTROL above for direct comparison.
# ---------------------------------------------------------------------------
log(f"--- TREATMENT-RECONNECT: connecting to real SSID {REAL_SSID!r} again ---")
t_treatment_start = time.ticks_ms()
wlan.connect(REAL_SSID, REAL_PW)
outcome = wait_for_outcome(wlan, max_polls=1200, poll_ms=500, label="TREATMENT-RECONNECT")  # up to 600s
treatment_elapsed_s = time.ticks_diff(time.ticks_ms(), t_treatment_start) / 1000.0
log("TREATMENT-RECONNECT result: {} after {:.1f}s".format(status_name(outcome) if outcome is not None else "ERROR", treatment_elapsed_s))
if outcome == network.STAT_GOT_IP:
    log(f"TREATMENT-RECONNECT ifconfig: {wlan.ifconfig()}")

log("=== SUMMARY: CONTROL={:.1f}s TREATMENT-RECONNECT={:.1f}s (ratio {:.1f}x) ===".format(
    control_elapsed_s, treatment_elapsed_s, treatment_elapsed_s / control_elapsed_s if control_elapsed_s > 0 else float("inf"),
))
log("=== DIAGNOSTIC END - board left connected to the real network on this ad-hoc WLAN object, "
    "NOT via a normal reboot - hard_reset() the board next to resume normal main.py operation ===")
