# Each >30 ms overshoot of a 10 ms sleep: its CLOCK_MONOTONIC start, own CPU ms, voluntary switches, and the
# system-wide steal ms across it; a ThreadSafeFlag waiter keeps a non-fd object in the poll set.
import time, asyncio
def snap():
    f = open("/proc/self/stat"); st = f.read().split(); f.close()
    f = open("/proc/self/status"); s = f.read(); f.close()
    vol = int([l for l in s.split("\n") if l.startswith("voluntary")][0].split()[1])
    f = open("/proc/stat"); steal = int(f.readline().split()[8]); f.close()
    return int(st[13]) + int(st[14]), vol, steal
flag = asyncio.ThreadSafeFlag()
async def waiter():
    while True:
        await flag.wait()
async def main(secs):
    asyncio.create_task(waiter())
    end = time.ticks_add(time.ticks_ms(), secs * 1000); gaps = []
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        a = snap(); t0 = time.ticks_ms(); await asyncio.sleep(0.01); d = time.ticks_diff(time.ticks_ms(), t0) - 10; b = snap()
        if d > 30: gaps.append((t0, d, (b[0] - a[0]) * 10, b[1] - a[1], (b[2] - a[2]) * 10))
    print("gaps(start_ms, over_ms, cpu_ms, vol_switches, steal_ms_all_cpus)", gaps)
asyncio.run(main(300))
