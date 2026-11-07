"""Bare-image runtime timing: gc.collect() pauses by heap fill; at each GC stage, DUR_S of event-loop lag beside an
allocation churn task and two soft Timers (1000 ms, 100 ms); then the recursion depth limits. SUM lines summarise."""

import asyncio
import gc
import time

import machine
import micropython

DUR_S = 180  # per GC stage: the whole script stays under 10 minutes
BINS = (500, 1000, 2000, 5000, 10000, 20000, 50000)  # lag bin edges, us


class Stat:
    def __init__(self) -> None:
        self.n, self.mx = 0, 0
        self.h = [0, 0, 0, 0, 0, 0, 0, 0]

    def add(self, v: int) -> None:
        self.n += 1
        self.mx = max(self.mx, v)
        i = 0
        while i < len(BINS) and v >= BINS[i]:
            i += 1
        self.h[i] += 1


T1 = [0, 0, 0]  # fires, last tick, worst |jitter| us
T2 = [0, 0, 0]


def _tick(st: list, period_us: int) -> None:
    now = time.ticks_us()
    if st[1]:
        st[2] = max(st[2], abs(time.ticks_diff(now, st[1]) - period_us))
    st[1] = now
    st[0] += 1


def gc_pauses() -> None:
    gc.collect()
    total = gc.mem_free() + gc.mem_alloc()
    keep = []
    print("SUM heap_total=%d" % total)
    for f in (10, 30, 50, 70, 80):
        try:
            while gc.mem_alloc() * 100 < total * f:
                keep.append(bytearray(48))
        except MemoryError:
            print("SUM gc_fill=%d MemoryError at objects=%d" % (f, len(keep)))
            break
        worst = 0
        for _ in range(5):
            t = time.ticks_us()
            gc.collect()
            worst = max(worst, time.ticks_diff(time.ticks_us(), t))
        print("SUM gc_collect fill=%d%% objects=%d worst_us=%d" % (f, len(keep), worst))
    keep = None
    gc.collect()


async def lag(st: Stat, end: int) -> None:
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        t = time.ticks_us()
        await asyncio.sleep_ms(10)
        st.add(time.ticks_diff(time.ticks_us(), t) - 10000)


async def churn(end: int) -> None:
    ring = [None] * 64
    i = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        ring[i & 63] = bytearray(16 + (i * 37) % 497)
        i += 1
        if i % 8 == 0:
            await asyncio.sleep_ms(0)


def stage(threshold: int) -> None:
    gc.collect()
    gc.threshold(threshold)
    for s in (T1, T2):
        s[0] = s[1] = s[2] = 0
    ta = machine.Timer(mode=machine.Timer.PERIODIC, period=1000, callback=lambda t: _tick(T1, 1000000))
    tb = machine.Timer(mode=machine.Timer.PERIODIC, period=100, callback=lambda t: _tick(T2, 100000))
    st = Stat()
    end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)

    async def main() -> None:
        await asyncio.gather(lag(st, end), churn(end))

    asyncio.run(main())
    ta.deinit()
    tb.deinit()
    gc.threshold(-1)
    print("SUM loop_lag threshold=%d n=%d max_us=%d bins=%s edges=%s" % (threshold, st.n, st.mx, st.h, BINS))
    print("SUM timer_1000 threshold=%d fires=%d expected=%d worst_jitter_us=%d" % (threshold, T1[0], DUR_S, T1[2]))
    print("SUM timer_100 threshold=%d fires=%d expected=%d worst_jitter_us=%d" % (threshold, T2[0], DUR_S * 10, T2[2]))


DEPTH = [0]


def _rec() -> None:
    DEPTH[0] += 1
    _rec()


def recursion() -> None:
    use = micropython.stack_use() if hasattr(micropython, "stack_use") else -1
    DEPTH[0] = 0
    try:
        _rec()
    except RuntimeError as e:
        print("SUM recursion plain depth=%d stack_use_at_entry=%d error=%r" % (DEPTH[0], use, e))

    async def deep() -> None:
        DEPTH[0] = 0
        try:
            _rec()
        except RuntimeError as e:
            print("SUM recursion in_task depth=%d error=%r" % (DEPTH[0], e))

    asyncio.run(deep())
    e = RuntimeError("maximum recursion depth exceeded")
    t = time.ticks_us()
    for _ in range(1000):
        _ = isinstance(e, RuntimeError) and bool(e.args) and e.args[0] == "maximum recursion depth exceeded"
    print("SUM cstack_check cost_us_per_call=%.2f" % (time.ticks_diff(time.ticks_us(), t) / 1000))


gc_pauses()
stage(-1)
stage(32768)
recursion()
print("DONE=1")
