"""The captive DNS listener's idle poll on silicon, STA on the board's stored Wi-Fi config (never printed): a counter
task's rate flat out alone, then beside an idle CaptiveDNS (its loop share); then READY and IP= for the host's timed
queries (host_dns_query_timing.py), served for SERVE_S. No product boot; nothing written."""

import asyncio
import json
import os
import time

import machine
import network

from asy_captive_dns import CaptiveDNS

COUNT_S = 10
SERVE_S = 120
wdt = machine.WDT(timeout=8000)


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
    print("SUM dns_idle no stored config found")
    raise SystemExit


async def count(seconds: int) -> int:
    n, end = 0, time.ticks_add(time.ticks_ms(), seconds * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        n += 1
        if n % 1000 == 0:
            wdt.feed()
        await asyncio.sleep(0)
    return n


async def run() -> None:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    ssid, pw = creds()
    wlan.connect(ssid, pw)
    for _ in range(300):
        if wlan.isconnected():
            break
        wdt.feed()
        await asyncio.sleep_ms(100)
    if not wlan.isconnected():
        print("SUM dns_idle no link, status=%d" % wlan.status())
        return
    ip, mask = wlan.ifconfig()[:2]
    alone = await count(COUNT_S)
    asyncio.create_task(CaptiveDNS().run(ip, mask))
    await asyncio.sleep(1)
    beside = await count(COUNT_S)
    print("SUM dns_idle counts alone=%d beside=%d share_pct=%.2f" % (alone, beside, 100 * (alone - beside) / alone))
    print("IP=%s" % ip)
    print("READY")
    end = time.ticks_add(time.ticks_ms(), SERVE_S * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        wdt.feed()
        await asyncio.sleep_ms(500)


asyncio.run(run())
print("DONE=1")
machine.reset()  # ends the session in a hard reset, restoring the product (tests_hardware/README.md)
