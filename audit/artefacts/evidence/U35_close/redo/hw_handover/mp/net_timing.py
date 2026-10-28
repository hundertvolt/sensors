"""Bare-image network timing with the board's own stored Wi-Fi config (never printed): connect times, how long
getaddrinfo() holds the VM (a 10 ms soft Timer counts beside it), an immediate TCP and UDP rebind with and without
SO_REUSEADDR after a served connection, and NTP round trips. The host connects once to port 8080 after READY."""

import json
import os
import socket
import time

import machine
import network

CNT = [0]
NTP_HOST = "pool.ntp.org"


def _count(_t: object) -> None:
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
                return d["SSID"], d["PW"], d.get("Country", "DE")
    print("SUM wifi no stored config found")
    raise SystemExit


def connect(wlan: network.WLAN, ssid: str, pw: str) -> int:
    wlan.active(False)
    time.sleep_ms(500)
    wlan.active(True)
    t = time.ticks_ms()
    wlan.connect(ssid, pw)
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t) < 30000:
        time.sleep_ms(50)
    return time.ticks_diff(time.ticks_ms(), t) if wlan.isconnected() else -wlan.status()


def resolve(host: str) -> str:
    c0, t = CNT[0], time.ticks_ms()
    try:
        res = "ok" if socket.getaddrinfo(host, 123) else "empty"
    except OSError as e:
        res = repr(e)
    ms = time.ticks_diff(time.ticks_ms(), t)
    ticks = CNT[0] - c0
    return "host=%s result=%s wall_ms=%d timer_ticks=%d of %d" % (host, res, ms, ticks, ms // 10)


def set_dns(server: str | None) -> str:
    if hasattr(network, "ipconfig"):
        old = network.ipconfig("dns")
        if server:
            network.ipconfig(dns=server)
        return old
    return ""


def rebind(kind: int, port: int) -> str:
    out = []
    for reuse in (False, True):
        s = socket.socket(socket.AF_INET, kind)
        try:
            if reuse:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            out.append("reuse=%d ok" % reuse)
        except OSError as e:
            out.append("reuse=%d %r" % (reuse, e))
        finally:
            s.close()
    return ", ".join(out)


def ntp() -> str:
    addr = socket.getaddrinfo(NTP_HOST, 123)[0][-1]
    q = bytearray(48)
    q[0] = 0x1B
    ok, worst, rtts = 0, 0, []
    for _ in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        t = time.ticks_ms()
        try:
            s.sendto(q, addr)
            if len(s.recv(48)) == 48:
                ok += 1
                d = time.ticks_diff(time.ticks_ms(), t)
                rtts.append(d)
                worst = max(worst, d)
        except OSError:
            pass
        finally:
            s.close()
        time.sleep_ms(500)
    rtts.sort()
    return "answers=%d of 10 median_ms=%d worst_ms=%d" % (ok, rtts[len(rtts) // 2] if rtts else -1, worst)


ssid, pw, country = creds()
network.country(country)
wlan = network.WLAN(network.STA_IF)
times = [connect(wlan, ssid, pw) for _ in range(3)]
print("SUM wifi_connect_ms=%s (negative: failed with that status)" % times)
if wlan.isconnected():
    tim = machine.Timer(mode=machine.Timer.PERIODIC, period=10, callback=_count)
    print("SUM dns", resolve(NTP_HOST))
    print("SUM dns", resolve("nonexistent.invalid"))
    old = set_dns("203.0.113.1")
    if old:
        print("SUM dns unreachable_server", resolve("example.com"))
        set_dns(old)
    else:
        print("SUM dns unreachable_server skipped (no network.ipconfig)")
    tim.deinit()
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 8080))
    srv.listen(1)
    srv.settimeout(60)
    print("IP=%s" % wlan.ifconfig()[0])
    print("READY")
    try:
        c, _ = srv.accept()
        c.settimeout(5)
        c.recv(256)
        c.send(b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nok")
        c.close()
        served = "served"
    except OSError as e:
        served = repr(e)
    srv.close()
    print("SUM tcp_rebind_8080 after=%s %s" % (served, rebind(socket.SOCK_STREAM, 8080)))
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.bind(("0.0.0.0", 53))
    u.close()
    print("SUM udp_rebind_53", rebind(socket.SOCK_DGRAM, 53))
    print("SUM ntp", ntp())
wlan.disconnect()
wlan.active(False)
print("DONE=1")
