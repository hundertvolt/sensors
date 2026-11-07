"""Long network run with the board's stored Wi-Fi config (never printed): link drops seen by isconnected() each second,
getaddrinfo() every 60 s (wall time, failures, and whether a 10 ms soft Timer advanced: the VM held), an NTP query
every 120 s, and a full reconnect every 4 min, each counted with its worst time. DUR_S per run."""

import json
import os
import socket
import time

import machine
import network

DUR_S = 1200
CNT = [0]


def _count(_t: object) -> None:
    CNT[0] += 1


def stored() -> dict:
    out = {}
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict):
                out.update({k: v for k, v in d.items() if k in ("SSID", "PW", "Country", "NTPHost")})
    return out


def connect(wlan: network.WLAN, cfg: dict) -> int:
    wlan.active(False)
    time.sleep_ms(500)
    wlan.active(True)
    t = time.ticks_ms()
    wlan.connect(cfg["SSID"], cfg["PW"])
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t) < 30000:
        time.sleep_ms(50)
    return time.ticks_diff(time.ticks_ms(), t) if wlan.isconnected() else -1


cfg = stored()
if not cfg.get("SSID") or "PW" not in cfg:
    print("SUM L net no_stored_config=1")
    raise SystemExit
host = cfg.get("NTPHost") or "pool.ntp.org"
network.country(cfg.get("Country", "DE"))
wlan = network.WLAN(network.STA_IF)
s = {"connects": 0, "connect_fail": 0, "connect_worst_ms": 0, "drops": 0, "down_s": 0, "dns": 0, "dns_fail": 0,
     "dns_worst_ms": 0, "dns_vm_held": 0, "ntp": 0, "ntp_fail": 0, "ntp_worst_ms": 0, "ntp_sum_ms": 0, "skipped_down": 0}


def reconnect() -> None:
    ms = connect(wlan, cfg)
    s["connects"] += 1
    if ms < 0:
        s["connect_fail"] += 1
    else:
        s["connect_worst_ms"] = max(s["connect_worst_ms"], ms)


reconnect()
tim = machine.Timer(mode=machine.Timer.PERIODIC, period=10, callback=_count)
q = bytearray(48)
q[0] = 0x1B
now = time.ticks_ms()
end = time.ticks_add(now, DUR_S * 1000)
due_dns, due_ntp, due_rc = now, time.ticks_add(now, 5000), time.ticks_add(now, 240000)
up = wlan.isconnected()
while time.ticks_diff(end, time.ticks_ms()) > 0:
    now = time.ticks_ms()
    c = wlan.isconnected()
    if up and not c:
        s["drops"] += 1
    if not c:
        s["down_s"] += 1
    up = c
    if time.ticks_diff(now, due_rc) >= 0:
        reconnect()
        due_rc = time.ticks_add(now, 240000)
    elif time.ticks_diff(now, due_dns) >= 0:
        due_dns = time.ticks_add(now, 60000)
        if not c:
            s["skipped_down"] += 1
        else:
            c0, t = CNT[0], time.ticks_ms()
            try:
                socket.getaddrinfo(host, 123)
            except OSError:
                s["dns_fail"] += 1
            ms = time.ticks_diff(time.ticks_ms(), t)
            s["dns"] += 1
            s["dns_worst_ms"] = max(s["dns_worst_ms"], ms)
            s["dns_vm_held"] += ms >= 50 and CNT[0] - c0 == 0
    elif time.ticks_diff(now, due_ntp) >= 0:
        due_ntp = time.ticks_add(now, 120000)
        if not c:
            s["skipped_down"] += 1
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            t = time.ticks_ms()
            try:
                sock.sendto(q, socket.getaddrinfo(host, 123)[0][-1])
                sock.recv(48)
                ms = time.ticks_diff(time.ticks_ms(), t)
                s["ntp_worst_ms"] = max(s["ntp_worst_ms"], ms)
                s["ntp_sum_ms"] += ms
            except OSError:
                s["ntp_fail"] += 1
            finally:
                sock.close()
            s["ntp"] += 1
    time.sleep_ms(1000)
tim.deinit()
wlan.disconnect()
wlan.active(False)
print("SUM L net " + " ".join("%s=%d" % (k, v) for k, v in s.items()))
print("DONE=1")
