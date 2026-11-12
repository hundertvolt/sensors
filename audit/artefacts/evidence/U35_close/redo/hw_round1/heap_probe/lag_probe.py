"""lag_probe.py: the real firmware under `mpremote run`, no flash write: asyncio loop lag binned over an idle window, then a load window; keeps serving after DONE."""
import sys
sys.path.insert(0, ".frozen")
from machine import WDT
watchdog = WDT(timeout=8000)
import gc, micropython, asyncio, time
from array import array
micropython.alloc_emergency_exception_buf(100)
from sensortask_dev import main
gc.threshold(32768)
IDLE_S = 60
LOAD_S = 70
STEP_MS = 10
EDGES = (5, 10, 20, 50, 100, 200, 500, 925)  # ms over the 10 ms sleep; 925 ms is con.uart_reply on dev
bins = array("i", [0] * (len(EDGES) + 1))
peak = array("i", [0, 0])  # the largest lag, ticks of it over 200 ms
async def lag():
    while True:
        t0 = time.ticks_ms()
        await asyncio.sleep_ms(STEP_MS)
        d = time.ticks_diff(time.ticks_ms(), t0) - STEP_MS
        i = 0
        while i < len(EDGES) and d >= EDGES[i]:
            i += 1
        bins[i] += 1
        if d > peak[0]:
            peak[0] = d
        if d >= 200:
            peak[1] += 1
def report(tag):
    print("LAG", tag, "edges_ms", EDGES, "bins", list(bins), "max_ms", peak[0], "over200", peak[1], "free", gc.mem_free(), "ms", time.ticks_ms())
    for i in range(len(bins)):
        bins[i] = 0
    peak[0] = 0
    peak[1] = 0
async def driver():
    await asyncio.sleep(45)
    report("BOOT")
    await asyncio.sleep(IDLE_S)
    report("IDLE")
    print("LOAD_NOW")
    await asyncio.sleep(LOAD_S)
    report("LOAD")
    await asyncio.sleep(30)
    report("AFTER")
    print("DONE")
async def top():
    asyncio.create_task(lag())
    asyncio.create_task(driver())
    await main(watchdog=watchdog)
asyncio.run(top())
