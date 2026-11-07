"""prims7.py: a UDP storm against the radio's power-save mode and the target port (bound or not): the loop lag per second,
a hard 1 kHz Timer (IRQs) and a soft 100 Hz Timer (scheduler) counted alongside, then an echo for the host's RTT probe."""
import json, os, time, select, socket, network, asyncio, machine
from machine import Timer
PM = "fw"
BOUND = True
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
hard = [0]; soft = [0]; lagw = [0]; rx = [0]
def hcb(_): hard[0] += 1
def scb(_): soft[0] += 1
async def feeder():
    while True: wdt.feed(); mb0[0] = now(); mb0[1] = rx[0]; mb0[2] = hard[0]; mb0[3] = soft[0]; await asyncio.sleep_ms(100)
async def lag():
    while True:
        t = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t) - 10
        lagw[0] = max(lagw[0], d); mb1[1] = max(mb1[1], d)
async def echo(s):
    p = select.poll(); p.register(s, select.POLLIN)
    while True:
        if p.poll(0):
            try: data, addr = s.recvfrom(512); rx[0] += 1; s.sendto(data, addr)
            except OSError: pass
            await asyncio.sleep_ms(0); continue
        await asyncio.sleep_ms(2)
async def main():
    c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True)
    wlan.config(pm={"fw": 0xA11140, "performance": network.WLAN.PM_PERFORMANCE, "powersave": network.WLAN.PM_POWERSAVE}[PM])
    wlan.connect(c[0], c[1])
    for _ in range(150):
        if wlan.isconnected(): break
        wdt.feed(); await asyncio.sleep_ms(100)
    mb1[0] = 1
    echo_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); echo_s.bind(("0.0.0.0", 5005)); echo_s.setblocking(False)
    th = Timer(mode=Timer.PERIODIC, freq=1000, callback=hcb, hard=True); ts = Timer(mode=Timer.PERIODIC, period=10, callback=scb)
    for f in (feeder(), lag(), echo(echo_s)): asyncio.create_task(f)
    await asyncio.sleep(1)
    print("FLOOD_START IP=%s PORT=%d" % (wlan.ifconfig()[0], 5005 if BOUND else 5006))
    for sec in range(28):
        lagw[0] = 0; h0, s0, t0 = hard[0], soft[0], now(); await asyncio.sleep(1); dt = now() - t0
        print("SUM prims7", PM, "bound" if BOUND else "unbound", "t", sec, "window_ms", dt, "lag_max_ms", lagw[0], "udp_rx", rx[0],
              "hard_per_s", (hard[0] - h0) * 1000 // dt, "soft_per_s", (soft[0] - s0) * 1000 // dt)
    th.deinit(); ts.deinit()
    print("SUM prims7", PM, "isconnected", wlan.isconnected(), "rssi", wlan.status("rssi"))
asyncio.run(main())
print("DONE")
