"""Wi-Fi call costs on the bare image with the stored config (never printed): active(True/False), connect, how long
isconnected() takes to clear after disconnect() (polls at 1 ms), status('rssi') per call, a short AP with a random
password and the switch back to STA, and deinit() if present; a 10 ms soft Timer shows whether each call held the VM."""

import json
import os
import random
import time

import machine
import network

CNT = [0]


def _tick(_t: object) -> None:
    CNT[0] += 1


def creds() -> tuple:
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and d.get("SSID") and "PW" in d:
                return d["SSID"], d["PW"]
    raise SystemExit("no stored config")


def timed(label: str, fn) -> object:
    c0, t = CNT[0], time.ticks_us()
    r = fn()
    us = time.ticks_diff(time.ticks_us(), t)
    print("SUM wifi_call %s us=%d timer_ticks=%d expected=%d" % (label, us, CNT[0] - c0, us // 10000))
    return r


def wait(cond, limit_ms: int = 30000) -> int:
    t = time.ticks_ms()
    while not cond() and time.ticks_diff(time.ticks_ms(), t) < limit_ms:
        time.sleep_ms(10)
    return time.ticks_diff(time.ticks_ms(), t) if cond() else -1


ssid, pw = creds()
tim = machine.Timer(-1, period=10, callback=_tick)
sta = network.WLAN(network.STA_IF)
timed("sta_active_false", lambda: sta.active(False))
timed("sta_active_true", lambda: sta.active(True))
timed("connect_call", lambda: sta.connect(ssid, pw))
print("SUM wifi connected_after_ms=%d" % wait(sta.isconnected))
worst = total = 0
for _ in range(100):
    t = time.ticks_us()
    sta.status("rssi")
    d = time.ticks_diff(time.ticks_us(), t)
    worst, total = max(worst, d), total + d
print("SUM wifi rssi_call avg_us=%d worst_us=%d" % (total // 100, worst))
timed("disconnect_call", sta.disconnect)
t, polls = time.ticks_ms(), 0
while sta.isconnected() and polls < 5000:
    polls += 1
    time.sleep_ms(1)
print("SUM wifi isconnected_cleared_after_ms=%d polls=%d status=%d" % (time.ticks_diff(time.ticks_ms(), t), polls, sta.status()))
timed("sta_active_false_2", lambda: sta.active(False))
ap = network.WLAN(network.AP_IF)
key = "".join(random.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(16))
try:
    ap.config(ssid="bench-%04x" % random.getrandbits(16), password=key)
except (TypeError, ValueError, OSError):
    ap.config(ssid="bench-%04x" % random.getrandbits(16), key=key)
timed("ap_active_true", lambda: ap.active(True))
print("SUM wifi ap_active_after_ms=%d" % wait(ap.active, 10000))
time.sleep(5)
timed("ap_active_false", lambda: ap.active(False))
timed("sta_active_true_after_ap", lambda: sta.active(True))
sta.connect(ssid, pw)
print("SUM wifi sta_back_connected_after_ms=%d" % wait(sta.isconnected))
if hasattr(sta, "deinit"):
    sta.disconnect()
    timed("deinit", sta.deinit)
    sta = network.WLAN(network.STA_IF)
    timed("sta_active_true_after_deinit", lambda: sta.active(True))
    sta.connect(ssid, pw)
    print("SUM wifi connected_after_deinit_ms=%d" % wait(sta.isconnected))
else:
    print("SUM wifi deinit absent")
sta.disconnect()
sta.active(False)
tim.deinit()
print("DONE=1")
