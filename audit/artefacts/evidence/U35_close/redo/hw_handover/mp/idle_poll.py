"""The idle poll rate (BACKLOG, Part N udp.poll_idle_ms): a counter task runs flat out beside a UDP echo listener on
port 53 that polls with timeout 0 and sleeps POLL ms when idle, as src/asy_udp_socket.py's ready() does; the counter's
rate against Wi-Fi alone gives the listener's loop share. Then, after READY, the host times queries; stored config only."""

import asyncio
import json
import os
import select
import socket
import time

import network

PHASE_S = 20
HOST_S = 150  # the host's query phase, after READY
ST = {"run": True, "n": 0, "ans": 0, "poll": 100}


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
    print("SUM idle_poll no stored config found")
    raise SystemExit


async def counter() -> None:
    while ST["run"]:
        ST["n"] += 1
        await asyncio.sleep_ms(0)


async def listener(sock: socket.socket) -> None:
    p = select.poll()
    p.register(sock, select.POLLIN)
    while ST["run"]:
        if p.poll(0):
            data, addr = sock.recvfrom(512)
            sock.sendto(data, addr)
            ST["ans"] += 1
        elif ST["poll"] > 0:
            await asyncio.sleep_ms(ST["poll"])


async def phase(label: str, sock: "socket.socket | None", poll: int, seconds: int) -> int:
    ST["run"], ST["n"], ST["poll"] = True, 0, poll
    tasks = [asyncio.create_task(counter())]
    if sock is not None:
        tasks.append(asyncio.create_task(listener(sock)))
    await asyncio.sleep(seconds)
    ST["run"] = False
    n = ST["n"]
    await asyncio.sleep_ms(poll + 50)
    print("SUM idle_poll phase=%s poll_ms=%d counter_per_s=%d" % (label, poll, n // seconds))
    return n


async def main() -> None:
    ssid, pw = creds()
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, pw)
    t = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t) < 30000:
        await asyncio.sleep_ms(50)
    if not wlan.isconnected():
        print("SUM idle_poll wifi_failed status=%d" % wlan.status())
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 53))
    base = await phase("counter_alone", None, 0, PHASE_S)
    for poll in (100, 20, 500, 10):
        n = await phase("with_listener", sock, poll, PHASE_S)
        print("SUM idle_poll share poll_ms=%d loop_share_permille=%d" % (poll, (base - n) * 1000 // max(base, 1)))
    print("IP=%s" % wlan.ifconfig()[0])
    print("READY")
    ST["run"], ST["ans"], ST["poll"] = True, 0, 100
    lt = asyncio.create_task(listener(sock))
    await asyncio.sleep(HOST_S)
    ST["run"] = False
    await lt
    print("SUM idle_poll host_phase answered=%d" % ST["ans"])
    sock.close()
    wlan.disconnect()


asyncio.run(main())
print("DONE=1")
