"""prims6.py: what an unthrottled UDP flood leaves behind: the loop lag per second during it, then each later Wi-Fi/socket
call stepped with a reset-surviving marker (mem_backup(1)[0]) and its duration."""
import json, os, time, select, socket, network, asyncio, machine
wdt = machine.WDT(timeout=8000)
mb0, mb1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(4): mb0[i] = 0
for i in range(3): mb1[i] = 0
T0 = time.ticks_ms()
def now(): return time.ticks_diff(time.ticks_ms(), T0)
def creds():
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f: d = json.load(f)
            except (OSError, ValueError): continue
            if isinstance(d, dict) and d.get("SSID") and "PW" in d: return d["SSID"], d["PW"]
lagw = [0]; rx = [0]
async def feeder():
    while True: wdt.feed(); mb0[0] = now(); mb0[1] = rx[0]; await asyncio.sleep_ms(100)
async def lag():
    while True:
        t = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t) - 10
        lagw[0] = max(lagw[0], d); mb1[1] = max(mb1[1], d)
async def echo(s):
    p = select.poll(); p.register(s, select.POLLIN)
    while True:
        if p.poll(0):
            try:
                data, addr = s.recvfrom(512); rx[0] += 1; s.sendto(data, addr)
            except OSError: pass
            continue
        await asyncio.sleep_ms(2)
def step(n, name, fn):
    mb1[0] = n; wdt.feed(); t = time.ticks_us()
    try: r = fn()
    except Exception as e: r = repr(e)
    print("SUM prims6 step", n, name, "us", time.ticks_diff(time.ticks_us(), t), "->", r)
    return r
async def main():
    c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True); wlan.connect(c[0], c[1])
    for _ in range(150):
        if wlan.isconnected(): break
        wdt.feed(); await asyncio.sleep_ms(100)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", 5005)); s.setblocking(False)
    for f in (feeder(), lag(), echo(s)): asyncio.create_task(f)
    await asyncio.sleep(1)
    print("FLOOD_START IP=%s" % wlan.ifconfig()[0])
    for sec in range(30):
        lagw[0] = 0; await asyncio.sleep(1); print("SUM prims6 t", sec, "lag_max_ms", lagw[0], "udp_rx", rx[0], "at_ms", now())
    print("SUM prims6 isconnected", wlan.isconnected(), "status", wlan.status(), "rssi", wlan.status("rssi"))
    step(11, "close echo socket", s.close)
    step(12, "new udp socket", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).close())
    ap = network.WLAN(network.AP_IF)
    step(13, "ap.config", lambda: ap.config(ssid="bench-probe", key="probe-1234567"))
    step(14, "ap.active(True)", lambda: ap.active(True))
    await asyncio.sleep_ms(1500)
    socks = []
    def opener():
        try:
            while len(socks) < 12: socks.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        except OSError as e: return "%d opened, %r" % (len(socks), e)
        return "%d opened" % len(socks)
    step(15, "udp sockets with ap+sta", opener)
    for x in socks: x.close()
    step(16, "ap.active(False)", lambda: ap.active(False))
    step(17, "sta isconnected", wlan.isconnected)
asyncio.run(main())
print("DONE")
