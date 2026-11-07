"""prims2.py: SPI reads across machine.SPI's 32-byte DMA switch and with the DMA pool exhausted (FRAM, read-only), the
gc pause against heap fill, lwIP's socket ceilings, and getaddrinfo's blocking time. Zero wear."""
import gc, json, os, time, machine, rp2, socket, network
from machine import Pin, SPI, Timer
wdt = machine.WDT(timeout=8000)
def say(*a): print("SUM prims2", *a)
cs = Pin(5, Pin.OUT, value=1)
def rd(spi, n, addr=0):
    b = bytearray(n); cs(0); spi.write(bytes((0x03, addr >> 16 & 0xFF, addr >> 8 & 0xFF, addr & 0xFF))); spi.readinto(b); cs(1); return b
spi = SPI(0, baudrate=1000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
ref = bytearray()
for a in range(0, 1024, 16): ref += rd(spi, 16, a)  # the software path, 16 bytes at a time
for baud in (1000000, 8000000, 20000000, 40000000):
    spi.init(baudrate=baud); bad = eio = 0; t0 = time.ticks_us()
    for i in range(100):
        n = (16, 31, 32, 33, 64, 256, 1024)[i % 7]
        try:
            if rd(spi, n) != ref[:n]: bad += 1
        except OSError as e: eio += 1; cs(1)
    say("spi baud", baud, "actual", spi, "reads 100 mismatched", bad, "oserror", eio, "ms", time.ticks_diff(time.ticks_us(), t0) // 1000)
    wdt.feed()
spi.init(baudrate=1000000)
held = []
try:
    while True: held.append(rp2.DMA())
except Exception as e: pass
try: ok = rd(spi, 64) == ref[:64]; say("spi with all", len(held), "free DMA channels claimed: 64-byte read correct", ok)
except Exception as e: say("spi with DMA pool exhausted raised", repr(e))
for d in held: d.close()
held = None; gc.collect(); wdt.feed()
# gc pause against heap fill (small objects, the firmware's typical survivors)
keep = []; free0 = gc.mem_free()
for target in (25, 50, 75, 90):
    while (free0 - gc.mem_free()) * 100 // free0 < target:
        keep.append(bytearray(24)); keep.append([1, 2])
    ts = []
    for _ in range(3):
        t0 = time.ticks_us(); gc.collect(); ts.append(time.ticks_diff(time.ticks_us(), t0))
    say("gc fill_pct", target, "objects", len(keep), "collect_us", ts)
    wdt.feed()
keep = None; gc.collect()
# lwIP ceilings: sockets until refusal, then whether new ones work once all are closed
for kind, typ in (("udp", socket.SOCK_DGRAM), ("tcp", socket.SOCK_STREAM)):
    ss = []; err = None
    try:
        for i in range(64):
            s = socket.socket(socket.AF_INET, typ); ss.append(s)
            if typ == socket.SOCK_DGRAM: s.bind(("0.0.0.0", 40000 + i))
    except Exception as e: err = repr(e)
    for s in ss: s.close()
    try: s = socket.socket(socket.AF_INET, typ); s.close(); again = True
    except Exception as e: again = repr(e)
    say("sockets", kind, "opened", len(ss), "stopped_by", err, "new_after_close", again)
tl = []
try:
    for i in range(16):
        s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("0.0.0.0", 41000 + i)); s.listen(2); tl.append(s)
except Exception as e: say("tcp listeners opened", len(tl), "stopped_by", repr(e))
for s in tl: s.close()
wdt.feed()
# getaddrinfo: blocking time (F.2: it cannot be timeout-wrapped), with a 10 ms soft Timer counting what it lets through
def creds():
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f: d = json.load(f)
            except (OSError, ValueError): continue
            if isinstance(d, dict) and d.get("SSID") and "PW" in d: return d["SSID"], d["PW"]
    return None
c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True)
if c:
    wlan.connect(c[0], c[1]); t0 = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < 20000: time.sleep_ms(100); wdt.feed()
    n = [0]
    def tick(_): n[0] += 1
    tm = Timer(); tm.init(period=10, callback=tick)
    for name in ("pool.ntp.org", "pool.ntp.org", "nonexistent-host.invalid", "192.168.1.1", "x" * 70 + ".example.com"):
        say("getaddrinfo start", name[:30]); n[0] = 0; t0 = time.ticks_ms()
        try: r = "ok %d" % len(socket.getaddrinfo(name, 123))
        except Exception as e: r = repr(e)
        ms = time.ticks_diff(time.ticks_ms(), t0); wdt.feed()
        say("getaddrinfo", name[:30], "ms", ms, "result", r, "10ms_ticks", n[0], "of", ms // 10)
    tm.deinit(); wlan.disconnect()
else: say("getaddrinfo skipped: no stored config")
wlan.active(False)
print("DONE")
