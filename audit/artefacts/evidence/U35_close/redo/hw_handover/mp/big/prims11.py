"""prims11.py: an HTTP server on port 80 shaped like the webserver's hardening (asyncio.start_server, every read and drain
bounded by a 5 s per-call timeout, close on any failure) for the host's vanishing clients; every 5 s its open handlers,
served requests and timeouts, and every 30 s how many more TCP sockets lwIP will still create."""
import gc, json, os, time, socket, network, asyncio, machine
DUR_S = 600
wdt = machine.WDT(timeout=8000)
mb0, mb1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(4): mb0[i] = 0
for i in range(3): mb1[i] = 0
def creds():
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f: d = json.load(f)
            except (OSError, ValueError): continue
            if isinstance(d, dict) and d.get("SSID") and "PW" in d: return d["SSID"], d["PW"]
    return None
st = {"open": 0, "served": 0, "timeouts": 0, "errors": 0, "accepted": 0}
BIG = b"x" * 16384
async def handle(r, w):
    st["open"] += 1; st["accepted"] += 1; big = False
    try:
        while True:
            line = await asyncio.wait_for_ms(r.readline(), 5000)
            if not line: raise OSError(-1)
            if line.startswith(b"GET /big"): big = True
            if line == b"\r\n": break
        w.write(b"HTTP/1.0 200 OK\r\n\r\n"); w.write(BIG if big else b"ok\n")
        await asyncio.wait_for_ms(w.drain(), 5000)
        st["served"] += 1
    except asyncio.TimeoutError:
        st["timeouts"] += 1
    except Exception:
        st["errors"] += 1
    finally:
        try:
            w.close(); await asyncio.wait_for_ms(w.wait_closed(), 5000)
        except Exception:
            st["close_errors"] = st.get("close_errors", 0) + 1
        st["open"] -= 1
def pcb_room():
    s = []
    try:
        while len(s) < 12: s.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    except OSError:
        pass
    n = len(s)
    for x in s: x.close()
    return n
async def main():
    c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True); wlan.connect(c[0], c[1])
    for _ in range(150):
        if wlan.isconnected(): break
        wdt.feed(); await asyncio.sleep_ms(100)
    srv = await asyncio.start_server(handle, "0.0.0.0", 80, backlog=5)
    print("READY IP=%s pcb_room %d" % (wlan.ifconfig()[0], pcb_room()))
    t0 = time.ticks_ms(); k = 0
    while time.ticks_diff(time.ticks_ms(), t0) < DUR_S * 1000:
        for _ in range(5):
            wdt.feed(); mb0[0] = time.ticks_diff(time.ticks_ms(), t0) // 1000; mb0[1] = st["accepted"]; mb0[2] = st["open"]
            await asyncio.sleep(1)
        k += 1; room = pcb_room() if k % 6 == 0 else -1
        print("STAT t=%d %s room=%d mem=%d" % (time.ticks_diff(time.ticks_ms(), t0) // 1000, " ".join("%s=%d" % kv for kv in sorted(st.items())), room, gc.mem_free()))
    srv.close()
asyncio.run(main())
print("DONE")
