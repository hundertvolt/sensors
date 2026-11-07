"""Long runtime run at GC threshold GC: the event loop's 10 ms probe lag (histogram, worst) beside allocation churn,
and two soft Timers (1000 ms, 100 ms) counted against their expected fires with the worst jitter (F.1's dropped soft
callback); counts MemoryErrors in the churn, which must stay 0. DUR_S per run."""

import asyncio
import gc
import time

import machine

DUR_S = 1200
GC = -1
BINS = (500, 1000, 2000, 5000, 10000, 20000, 50000)  # lag bin edges, us
T1 = [0, 0, 0]  # fires, last tick, worst |jitter| us
T2 = [0, 0, 0]
H = [0, 0, 0, 0, 0, 0, 0, 0]
STAT = [0, 0, 0]  # probes, worst lag us, MemoryErrors


def _tick(st: list, period_us: int) -> None:
    now = time.ticks_us()
    if st[1]:
        st[2] = max(st[2], abs(time.ticks_diff(now, st[1]) - period_us))
    st[1] = now
    st[0] += 1


def _t1(_t: object) -> None:
    _tick(T1, 1000000)


def _t2(_t: object) -> None:
    _tick(T2, 100000)


async def lag(end: int) -> None:
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        t = time.ticks_us()
        await asyncio.sleep_ms(10)
        v = time.ticks_diff(time.ticks_us(), t) - 10000
        STAT[0] += 1
        STAT[1] = max(STAT[1], v)
        i = 0
        while i < len(BINS) and v >= BINS[i]:
            i += 1
        H[i] += 1


async def churn(end: int) -> None:
    ring, i = [None] * 64, 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        try:
            ring[i & 63] = bytearray(16 + (i * 37) % 497)
        except MemoryError:
            STAT[2] += 1
        i += 1
        if i % 8 == 0:
            await asyncio.sleep_ms(0)


async def main() -> None:
    end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
    await asyncio.gather(lag(end), churn(end))


gc.collect()
gc.threshold(GC)
ta = machine.Timer(mode=machine.Timer.PERIODIC, period=1000, callback=_t1)
tb = machine.Timer(mode=machine.Timer.PERIODIC, period=100, callback=_t2)
asyncio.run(main())
ta.deinit()
tb.deinit()
gc.threshold(-1)
print("SUM L loop threshold=%d probes=%d worst_lag_us=%d memoryerrors=%d" % (GC, STAT[0], STAT[1], STAT[2]))
print("SUM L lagbins threshold=%d lt500=%d lt1000=%d lt2000=%d lt5000=%d lt10000=%d lt20000=%d lt50000=%d ge50000=%d" % ((GC,) + tuple(H)))
print("SUM L timer period_ms=1000 threshold=%d fires=%d expected=%d worst_jitter_us=%d" % (GC, T1[0], DUR_S, T1[2]))
print("SUM L timer period_ms=100 threshold=%d fires=%d expected=%d worst_jitter_us=%d" % (GC, T2[0], DUR_S * 10, T2[2]))
print("DONE=1")
