"""prims13.py: real flash writes (owner, 2026-10-29: "Try TCP with real flash once") under live TCP: an HTTP server shaped
like the webserver's hardening (5 s per-call timeout) serving small and 16 KB pages and taking 32 KB uploads, while one
scratch file is written three times like a config save and removed; a 5 kHz hard Timer times the interrupts-off windows."""
import gc, json, os, time, network, asyncio, machine
from array import array
from machine import Timer
PROBE = "/u35_flashprobe.json"
wdt = machine.WDT(timeout=8000)
mb0, mb1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(4): mb0[i] = 0
for i in range(3): mb1[i] = 0
def say(*a): print("SUM prims13", *a)
def creds():
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f: d = json.load(f)
            except (OSError, ValueError): continue
            if isinstance(d, dict) and d.get("SSID") and "PW" in d: return d["SSID"], d["PW"]
    return None
st = {}
def bump(k, n=1): st[k] = st.get(k, 0) + n
gp = array("i", (0, 0, 0))
win = array("i", range(24))
def tick(_):  # hard IRQ, no allocation: a gap over 2 ms is a stretch with interrupts held off
    n = time.ticks_us(); d = time.ticks_diff(n, gp[0]); gp[0] = n
    if d > gp[1]: gp[1] = d
    if d > 2000:
        if gp[2] < 24: win[gp[2]] = d
        gp[2] += 1
BIG = b"x" * 16384
buf = bytearray(1024)
async def handle(r, w):
    bump("accepted"); kind = "small"; clen = 0
    try:
        while True:
            line = await asyncio.wait_for_ms(r.readline(), 5000)
            if not line: raise OSError(-1)
            if line.startswith(b"GET /big"): kind = "big"
            elif line.startswith(b"POST"): kind = "up"
            elif line.lower().startswith(b"content-length:"): clen = int(line[15:].strip().decode())
            if line == b"\r\n": break
        got = 0
        while got < clen:
            n = await asyncio.wait_for_ms(r.readinto(memoryview(buf)[:min(1024, clen - got)]), 5000)
            if not n: raise OSError(-2)
            got += n
        w.write(b"HTTP/1.0 200 OK\r\n\r\n"); w.write(BIG if kind == "big" else b"ok %d\n" % got)
        await asyncio.wait_for_ms(w.drain(), 5000)
        bump("served_" + kind)
    except asyncio.TimeoutError:
        bump("timeouts")
    except Exception as e:
        bump("err_" + type(e).__name__)
    finally:
        try:
            w.close(); await asyncio.wait_for_ms(w.wait_closed(), 5000)
        except Exception:
            bump("close_errors")
async def feeder():
    t0 = time.ticks_ms()
    while True:
        wdt.feed(); mb0[0] = time.ticks_diff(time.ticks_ms(), t0) // 100; mb0[1] = st.get("accepted", 0); mb0[3] = gp[1]
        mb1[1] = st.get("lag_max", 0)
        await asyncio.sleep_ms(100)
async def lag():
    while True:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t0) - 10
        st["lag_max"] = max(st.get("lag_max", 0), d)
def flash_write(i):  # the shape of a config save: one json.dump() straight into the file, no temporary file
    d = {"Name": "u35probe", "round": i, "vals": [1.5 * i, 2.5, 3.5], "pad": "p" * 640}
    t = time.ticks_us()
    with open(PROBE, "w") as f: json.dump(d, f)
    return time.ticks_diff(time.ticks_us(), t)
async def main():
    say("probe_exists_before", PROBE[1:] in os.listdir("/"))
    c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True); wlan.connect(c[0], c[1])
    for _ in range(150):
        if wlan.isconnected(): break
        wdt.feed(); await asyncio.sleep_ms(100)
    srv = await asyncio.start_server(handle, "0.0.0.0", 80, backlog=5)
    for f in (feeder(), lag()): asyncio.create_task(f)
    gp[0] = time.ticks_us(); tim = Timer(mode=Timer.PERIODIC, freq=5000, callback=tick, hard=True)
    print("READY IP=%s" % wlan.ifconfig()[0])
    await asyncio.sleep(6)
    try:
        for i, name in enumerate(("baseline", "write1", "write2", "write3")):
            mb1[0] = i + 1; st.clear(); gp[1] = 0; gp[2] = 0
            await asyncio.sleep(2)
            print("MARK", name)
            dt = flash_write(i) if i else 0
            await asyncio.sleep(3)
            say(name, "write_us", dt, "irqoff_max_us", gp[1], "windows_us", [win[k] for k in range(min(gp[2], 24))], sorted(st.items()))
    finally:
        gp[1] = 0; gp[2] = 0; t = time.ticks_us()
        try: os.remove(PROBE)
        except OSError as e: say("remove_failed", e)
        dt = time.ticks_diff(time.ticks_us(), t)
        say("remove_us", dt, "irqoff_max_us", gp[1], "probe_exists_after", PROBE[1:] in os.listdir("/"))
    await asyncio.sleep(4)
    tim.deinit(); srv.close(); gc.collect(); say("mem_free", gc.mem_free())
asyncio.run(main())
print("DONE")
