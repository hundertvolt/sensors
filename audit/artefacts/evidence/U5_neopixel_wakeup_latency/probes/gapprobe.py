# Every >30 ms overshoot of a 10 ms asyncio sleep, with this process's CPU ticks and forced switches across it,
# while a second task waits on a ThreadSafeFlag (a non-fd object in the Unix port's poll set, as the overlay task).
import time, asyncio
def cpu():
    f = open("/proc/self/stat"); st = f.read().split(); f.close()
    f = open("/proc/self/status"); nv = [l for l in f.read().split("\n") if l.startswith("nonvoluntary")][0].split()[1]; f.close()
    return int(st[13]) + int(st[14]), int(nv)
flag = asyncio.ThreadSafeFlag()
async def waiter():
    while True:
        await flag.wait()
async def main(secs):
    asyncio.create_task(waiter())
    end = time.ticks_add(time.ticks_ms(), secs * 1000); gaps = []; n = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        c0 = cpu(); t0 = time.ticks_ms(); await asyncio.sleep(0.01); d = time.ticks_diff(time.ticks_ms(), t0) - 10; c1 = cpu(); n += 1
        if d > 30: gaps.append((d, (c1[0] - c0[0]) * 10, c1[1] - c0[1]))
    print("samples", n, "gaps(over_ms, cpu_ms, forced_switches)", gaps)
asyncio.run(main(300))
