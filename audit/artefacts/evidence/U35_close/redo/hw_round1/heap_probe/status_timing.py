"""status_timing.py: the real firmware under `mpremote run`, no flash write: GET /status's time per source, whole build, lock wait and send
(the await-inclusive spans, so a yield to another task counts), loop lag, three timed gc.collect() idle and three after load; 32768. Serves after DONE."""
import sys
sys.path.insert(0, ".frozen")
from machine import WDT
watchdog = WDT(timeout=8000)
import gc, micropython, asyncio, time
micropython.alloc_emergency_exception_buf(100)
import asy_webserver_service as ws
from sensortask_dev import main
gc.threshold(32768)
LOAD_S = 60
CAP = 300
us, diff = time.ticks_us, time.ticks_diff
stats = {}  # name: [n, total_ms, max_us]
rows = []  # (end_ms, build_ms, slowest source, its ms); GET_STATUS less BUILD is the lock wait
sends = []  # (start_ms, send_ms, pieces)
lags = []  # (at_ms, lag_ms) of LAG_ROW_MS or more
LAG_ROW_MS = 100
LAG_TOPS = (25, 50, 100, 200, 400, 800)  # lag_hist: below each top, then the rest
lag_hist = [0] * (len(LAG_TOPS) + 1)
lag_max = [0]
current = [None, 0]
def note(name, t):
    d = diff(us(), t)
    s = stats.get(name)
    if s is None:
        s = stats[name] = [0, 0, 0]
    s[0] += 1
    s[1] += d // 1000
    if d > s[2]:
        s[2] = d
    if d > current[1]:
        current[0], current[1] = name, d
_guarded = ws.WebserverService._write_guarded
async def guarded(self, writer, fct, name):
    t = us()
    try:
        await _guarded(self, writer, fct, name)
    finally:
        note(name, t)
ws.WebserverService._write_guarded = guarded
_entry = ws.WebserverService._write_errcount_entry
async def entry(self, writer, fct, name):
    t = us()
    try:
        await _entry(self, writer, fct, name)
    finally:
        note("err:" + name, t)
ws.WebserverService._write_errcount_entry = entry
_build = ws.WebserverService._build_status_pieces
async def build(self):
    t = us()
    current[0], current[1] = None, 0
    try:
        return await _build(self)
    finally:
        note("BUILD", t)
        if len(rows) < CAP:
            rows.append((time.ticks_ms(), diff(us(), t) // 1000, current[0], current[1] // 1000))
ws.WebserverService._build_status_pieces = build
_status = ws.WebserverService._get_status
async def status(self, request):
    t = us()
    r = await _status(self, request)
    note("GET_STATUS", t)
    return r
ws.WebserverService._get_status = status
_orig_drained = ws._drained
class Timed:
    def __init__(self, pieces):
        self.n = len(pieces)
        self.it = iter(_orig_drained(pieces))
        self.t = None
    def __iter__(self):
        return self
    def __next__(self):
        if self.t is None:
            self.t = us()
        try:
            return next(self.it)
        except StopIteration:
            d = diff(us(), self.t)
            note("SEND", self.t)
            if len(sends) < CAP:
                sends.append((time.ticks_ms(), d // 1000, self.n))
            raise
ws._drained = Timed
async def lag():
    while True:
        t0 = time.ticks_ms()
        await asyncio.sleep_ms(10)
        d = diff(time.ticks_ms(), t0) - 10
        for i, top_ms in enumerate(LAG_TOPS):
            if d < top_ms:
                lag_hist[i] += 1
                break
        else:
            lag_hist[-1] += 1
        if d > lag_max[0]:
            lag_max[0] = d
        if d >= LAG_ROW_MS and len(lags) < CAP:
            lags.append((time.ticks_ms(), d))
def timed_collects(tag):
    for i in range(3):
        before = gc.mem_free()
        t = us()
        gc.collect()
        print("COLLECT", tag, i, "us", diff(us(), t), "free", before, "->", gc.mem_free())
async def driver():
    await asyncio.sleep(45)
    timed_collects("IDLE")
    stats.clear(); rows.clear(); sends.clear(); lags.clear()
    lag_hist[:] = [0] * len(lag_hist); lag_max[0] = 0
    print("LOAD_NOW", time.ticks_ms())
    await asyncio.sleep(LOAD_S + 5)
    timed_collects("AFTER")
    print("LOAD_END", time.ticks_ms())
    print("LAG_MAX", lag_max[0], "HIST", LAG_TOPS, lag_hist)
    for name, s in sorted(stats.items()):
        print("STAT", name, "n", s[0], "total_ms", s[1], "max_us", s[2])
    await asyncio.sleep_ms(50)
    for i, r in enumerate(rows):
        print("BUILD_ROW", *r)
        if i % 20 == 19:
            await asyncio.sleep_ms(20)
    for i, r in enumerate(sends):
        print("SEND_ROW", *r)
        if i % 20 == 19:
            await asyncio.sleep_ms(20)
    for r in lags:
        print("LAG_ROW", *r)
    print("DONE")
async def top():
    asyncio.create_task(lag())
    asyncio.create_task(driver())
    await main(watchdog=watchdog)
asyncio.run(top())
