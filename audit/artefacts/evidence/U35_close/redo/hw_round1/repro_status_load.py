"""repro_status_load.py MODE READERS SECONDS [PATH] [SETTLE_S] [CONSOLE_FILE]: GET load on the board at $DUT_IP with its console tailed;
MODE hazard also sends PUT /status {"UartHazards": true}. Prints status codes, WEBSERVER counter, failed sizes, MemFree. No flash write."""
import json, os, re, sys, threading, time, urllib.request, urllib.error, collections
import serial
ip = os.environ["DUT_IP"]; mode, readers, dur = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
PATH = sys.argv[4] if len(sys.argv) > 4 else "/status"; settle = int(sys.argv[5]) if len(sys.argv) > 5 else 0; stop = threading.Event(); codes = collections.Counter(); lines = []; frees = []
def req(method, path, body=None, t=8):
    r = urllib.request.Request(f"http://{ip}{path}", data=None if body is None else json.dumps(body).encode(), method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=t) as a: return a.status, a.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
def tail():
    for _ in range(40):
        if os.path.exists("/dev/ttyACM0"): break
        time.sleep(0.5)
    with serial.Serial("/dev/ttyACM0", 115200, timeout=0.2) as p:
        p.dtr = True
        while not stop.is_set():
            b = p.readline()
            if b: lines.append(b.decode("utf-8", "replace").rstrip())
def reader():
    while not stop.is_set():
        try:
            c, b = req("GET", PATH); codes[c] += 1
            if c == 200 and PATH == "/status": frees.append(json.loads(b)["system"]["MemFree"])
        except Exception as e: codes[type(e).__name__] += 1
        time.sleep(0.05)
threading.Thread(target=tail, daemon=True).start()
for _ in range(60):
    try:
        if req("GET", "/status", t=3)[0] == 200: break
    except Exception: pass
    time.sleep(1)
s = json.loads(req("GET", "/status")[1]); w0 = s["errcount"]["WEBSERVER"]["counter"]; up = s["system"]["SysUptime"]
time.sleep(settle); s = json.loads(req("GET", "/status")[1]); w0 = s["errcount"]["WEBSERVER"]["counter"]; up = s["system"]["SysUptime"]
ts = [threading.Thread(target=reader, daemon=True) for _ in range(readers)]; [t.start() for t in ts]
put = req("PUT", "/status", {"UartHazards": True}, t=10)[0] if mode == "hazard" else None
time.sleep(dur); stop.set(); [t.join(12) for t in ts]; time.sleep(1)
s = json.loads(req("GET", "/status", t=10)[1])
mem = [l for l in lines if "memory allocation failed" in l and "Unhandled" in l]
sz = collections.Counter(re.search(r"allocating (\d+)", l).group(1) for l in mem)
open(sys.argv[6] if len(sys.argv) > 6 else os.devnull, "w").write("\n".join(lines))
print(mode, PATH, "readers", readers, "dur", dur, "uptime0", up, "put", put, "codes", dict(codes))
print(" WEBSERVER", w0, "->", s["errcount"]["WEBSERVER"]["counter"], "memfails", len(mem), "sizes", dict(sz.most_common(6)))
print(" MemFree min/med/max", (min(frees), sorted(frees)[len(frees)//2], max(frees)) if frees else None, "UART_init", json.dumps(s["sensors"].get("UART_init"))[:120], "Transfers", s["sensors"].get("UARTLINK"))
other = collections.Counter(re.sub(r"^\s*\d+\.\d+\s*", "", l)[:70] for l in lines if re.search(r"memory allocation|MemoryError", l) and "Unhandled" not in l and "Microdot caught" not in l)
print(" other mem lines", other.most_common(6))
