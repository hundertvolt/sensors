"""Isolated-driver diagnostic script (NOT part of the routine test suite - a one-off repro built to
investigate REAL FINDING #4 in tests_hardware/bench/test_network_resilience.py's
test_garbage_ssid_via_rest_config_is_handled_gracefully: the DUT reconnecting to a real, known-good
SSID after a real STAT_NO_AP_FOUND failure history + AP-mode round-trip took 5-10+ minutes in
practice, versus ~20s for the exact same leave-AP-mode-and-reconnect mechanism triggered without any
real prior failed connection attempts.

This script isolates the variable directly at the `network` module level (no asy_wifi_service.py,
no REST, no webserver, no bench-side WiFi role-reversal) - CONTROL: connect to the real SSID from a
clean slate. TREATMENT, same session: 5 real failed connects to a nonexistent SSID (mirroring
asy_wifi_service.py's own _poll_sta_connect_status()/wifi_refresh_sec cadence exactly), then a real
AP-mode round-trip (mirroring _configure_hotspot_ap()/_switch_wlan_mode()), then reconnect to the
SAME real SSID again, timed the same way. Chatty: every poll prints a timestamp + wlan.status().

Run via `mpremote run <this>` (deliberately NOT chained with `soft-reset` at the end - see this
script's own final print for why leaving the board in this state, rather than triggering a reboot
via the chain, matters here). Recover the board afterward via a real hard_reset() (harness.py) to
resume normal main.py operation - this script never touches config files, so a normal boot reads
back the DUT's real, unmodified config."""

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
    print("[{:8.2f}s] {}".format(time.ticks_diff(time.ticks_ms(), t0) / 1000.0, msg))


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
    return names.get(status, "UNKNOWN({})".format(status))


def wait_for_outcome(wlan, max_polls, poll_ms, label):
    """Chatty poll loop, same shape as asy_wifi_service.py's own _poll_sta_connect_status() but
    logging every single poll (not just on entry) and returning the final status seen."""
    last = None
    for i in range(max_polls):
        try:
            status = wlan.status()
        except Exception as e:
            log("{}: wlan.status() raised {}: {}".format(label, type(e).__name__, e))
            return None
        if status != last:
            log("{}: poll {} -> {}".format(label, i, status_name(status)))
            last = status
        if status in (network.STAT_GOT_IP, network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND, network.STAT_CONNECT_FAIL):
            return status
        time.sleep_ms(poll_ms)
    log("{}: gave up after {} polls, last status {}".format(label, max_polls, status_name(last)))
    return last


log("=== DIAGNOSTIC START ===")
network.country(COUNTRY)
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
try:
    wlan.deinit()
except Exception as e:
    log("initial deinit() raised (expected if never active): {}: {}".format(type(e).__name__, e))
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(pm=0xA11140)
log("STA interface freshly (re)constructed and active")

# ---------------------------------------------------------------------------
# CONTROL: connect to the real SSID from this clean slate.
# ---------------------------------------------------------------------------
log("--- CONTROL: connecting to real SSID {!r} ---".format(REAL_SSID))
t_control_start = time.ticks_ms()
wlan.connect(REAL_SSID, REAL_PW)
outcome = wait_for_outcome(wlan, max_polls=240, poll_ms=500, label="CONTROL")  # up to 120s
control_elapsed_s = time.ticks_diff(time.ticks_ms(), t_control_start) / 1000.0
log("CONTROL result: {} after {:.1f}s".format(status_name(outcome) if outcome is not None else "ERROR", control_elapsed_s))
if outcome == network.STAT_GOT_IP:
    log("CONTROL ifconfig: {}".format(wlan.ifconfig()))

wlan.disconnect()
time.sleep(1)
log("CONTROL phase done, disconnected")

# ---------------------------------------------------------------------------
# TREATMENT: 5 real failed connects to a garbage SSID, mirroring asy_wifi_service.py's own
# wifi_refresh_sec=5s cadence between attempts and its own 0.5s poll interval within each attempt.
# ---------------------------------------------------------------------------
log("--- TREATMENT: 5 real failed connect attempts to {!r} ---".format(GARBAGE_SSID))
for attempt in range(5):
    log("TREATMENT attempt {}/5: wlan.connect({!r})".format(attempt + 1, GARBAGE_SSID))
    wlan.connect(GARBAGE_SSID, "irrelevant1")
    outcome = wait_for_outcome(wlan, max_polls=10, poll_ms=500, label="TREATMENT-attempt-{}".format(attempt + 1))
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
log("AP mode active: ifconfig={}".format(ap.ifconfig()))
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
log("--- TREATMENT-RECONNECT: connecting to real SSID {!r} again ---".format(REAL_SSID))
t_treatment_start = time.ticks_ms()
wlan.connect(REAL_SSID, REAL_PW)
outcome = wait_for_outcome(wlan, max_polls=1200, poll_ms=500, label="TREATMENT-RECONNECT")  # up to 600s
treatment_elapsed_s = time.ticks_diff(time.ticks_ms(), t_treatment_start) / 1000.0
log("TREATMENT-RECONNECT result: {} after {:.1f}s".format(status_name(outcome) if outcome is not None else "ERROR", treatment_elapsed_s))
if outcome == network.STAT_GOT_IP:
    log("TREATMENT-RECONNECT ifconfig: {}".format(wlan.ifconfig()))

log("=== SUMMARY: CONTROL={:.1f}s TREATMENT-RECONNECT={:.1f}s (ratio {:.1f}x) ===".format(
    control_elapsed_s, treatment_elapsed_s, treatment_elapsed_s / control_elapsed_s if control_elapsed_s > 0 else float("inf")
))
log("=== DIAGNOSTIC END - board left connected to the real network on this ad-hoc WLAN object, "
    "NOT via a normal reboot - hard_reset() the board next to resume normal main.py operation ===")
