"""prims.py: the firmware's small rp2 primitives on silicon (2026-10-29): the soft Timer + ThreadSafeFlag trigger every
driver uses, soft vs hard Pin IRQ delivery under a busy loop and gc (GP0 driven by PWM, read on GP9 over the bench's
crossover jumper), and NeoPixel write cost. Zero wear; a watchdog guards every stretch."""
import asyncio, gc, time, machine, micropython
from machine import Pin, Timer, PWM
wdt = machine.WDT(timeout=8000)
def say(*a): print("SUM prims", *a)
def busy_ms(ms):  # no yield, interrupts on
    t = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t) < ms: pass

# 1a: an unreferenced running soft Timer, after a collection
n = [0]
def tick(_): n[0] += 1
m = [0]
def tick_a(_): m[0] += 1
Timer(period=20, callback=tick_a); gc.collect(); time.sleep_ms(500); a = m[0]; time.sleep_ms(500)
say("timer_unreferenced_after_gc ticks_first_500ms", a, "next_500ms", m[0] - a, "(an orphan keeps a 20 ms tick for the rest of the run)")
# 1b: deinit of a bare, never-armed Timer; deinit twice
try:
    t = Timer(); t.deinit(); t.deinit(); say("bare_timer_deinit_twice ok")
except Exception as e: say("bare_timer_deinit_twice", repr(e))
# 1c: re-init of a running periodic Timer: one schedule or two?
n[0] = 0; t = Timer(); t.init(period=10, callback=tick); time.sleep_ms(10); t.init(period=10, callback=tick)
time.sleep_ms(1000); say("timer_reinit_running ticks_in_1s", n[0], "expected ~100"); t.deinit()
# 1d: soft Timer at 10 ms during a 300 ms busy block: delivered vs due
n[0] = 0; t.init(period=10, callback=tick); time.sleep_ms(5); busy_ms(300); d = n[0]; time.sleep_ms(50); t.deinit()
say("timer_10ms_during_300ms_busy delivered_by_end", d, "due 30")
# 1e: one soft Timer per driver: how many coexist (the firmware arms about 13)
ts = []
try:
    for i in range(40):
        x = Timer(); x.init(period=1000 + i, callback=tick); ts.append(x)
    say("soft_timers_armed", len(ts), "no error")
except Exception as e: say("soft_timers_armed", len(ts), "then", repr(e))
for x in ts: x.deinit()
ts = None; gc.collect(); wdt.feed()

# 2: ThreadSafeFlag as the drivers use it: set from a soft Timer, awaited by a task
async def tsf():
    f = asyncio.ThreadSafeFlag()
    for _ in range(5): f.set()
    t0 = time.ticks_us(); await f.wait(); w1 = time.ticks_diff(time.ticks_us(), t0)
    try:
        await asyncio.wait_for_ms(f.wait(), 100); second = "woke"
    except asyncio.TimeoutError: second = "timeout"
    say("tsf five_sets_then_wait us", w1, "second_wait", second)
    lat = []
    stamp = [0]
    def fire(_):
        stamp[0] = time.ticks_us(); f.set()
    tm = Timer()
    for _ in range(50):
        tm.init(mode=Timer.ONE_SHOT, period=7, callback=fire)
        await f.wait(); lat.append(time.ticks_diff(time.ticks_us(), stamp[0]))
    tm.deinit(); lat.sort()
    say("tsf timer_to_task_us median", lat[25], "p90", lat[45], "max", lat[-1])
    # the same with a sibling task hogging the loop in 20 ms slices
    stop = [False]
    async def hog():
        while not stop[0]:
            busy_ms(20); await asyncio.sleep_ms(0)
    h = asyncio.create_task(hog()); lat = []
    for _ in range(30):
        tm.init(mode=Timer.ONE_SHOT, period=7, callback=fire)
        await f.wait(); lat.append(time.ticks_diff(time.ticks_us(), stamp[0]))
    stop[0] = True; await h; tm.deinit(); lat.sort()
    say("tsf timer_to_task_us_with_20ms_hog median", lat[15], "max", lat[-1])
asyncio.run(tsf()); wdt.feed()

# 3: Pin IRQ delivery, GP0 PWM -> GP9 (crossover jumper), as the SCD30/ISL29125 data-ready pins use it
inp = Pin(9, Pin.IN); pwm = PWM(Pin(0), freq=200, duty_u16=32768)
time.sleep_ms(20); seen = 0
for _ in range(2000): seen |= 1 << inp.value()
say("jumper GP0->GP9 levels_seen", seen, "(3 = both: wired)")
if seen == 3:
    for hard in (False, True):
        c = [0]
        def edge(_): c[0] += 1
        inp.irq(edge, Pin.IRQ_RISING, hard=hard)
        c[0] = 0; time.sleep_ms(500); idle = c[0]
        c[0] = 0; busy_ms(500); busy = c[0]; time.sleep_ms(20); after = c[0]
        c[0] = 0; t0 = time.ticks_ms(); x = [bytearray(64) for _ in range(300)]; x = None; gc.collect(); g = time.ticks_diff(time.ticks_ms(), t0); time.sleep_ms(20)
        say("pin_irq hard=%s 200Hz idle_500ms" % hard, idle, "during_500ms_busy", busy, "by_20ms_after", after, "gc_window_ms", g, "edges_over_it", c[0])
        inp.irq(None)
    # re-registering the handler, as a driver's re-setup does: one callback per edge or two?
    c = [0]
    def edge2(_): c[0] += 1
    inp.irq(edge2, Pin.IRQ_RISING); inp.irq(edge2, Pin.IRQ_RISING); c[0] = 0; time.sleep_ms(500)
    say("pin_irq registered_twice edges_in_500ms", c[0], "expected ~100"); inp.irq(None)
    # latency: one edge, soft IRQ to callback
    pwm.deinit(); out = Pin(0, Pin.OUT, value=0); lat = []
    st = [0]
    def e3(_): st[0] = time.ticks_us()
    inp.irq(e3, Pin.IRQ_RISING)
    for _ in range(50):
        out(0); time.sleep_ms(2); t0 = time.ticks_us(); out(1)
        time.sleep_ms(2); lat.append(time.ticks_diff(st[0], t0))
    inp.irq(None); lat.sort(); say("pin_irq soft_latency_us median", lat[25], "max", lat[-1])
else:
    pwm.deinit()
wdt.feed()

# 4: NeoPixel write cost on GP18 (zeros: LED off)
try:
    import neopixel
    for npx in (1, 8, 60):
        np = neopixel.NeoPixel(Pin(18), npx); np.fill((0, 0, 0))
        t0 = time.ticks_us(); np.write(); w = time.ticks_diff(time.ticks_us(), t0)
        n[0] = 0; tm = Timer(); tm.init(period=1, callback=tick); t0 = time.ticks_ms()
        k = 0
        while time.ticks_diff(time.ticks_ms(), t0) < 200: np.write(); k += 1
        tm.deinit(); say("neopixel n=%d write_us" % npx, w, "writes_in_200ms", k, "1ms_timer_ticks", n[0], "of ~200")
except Exception as e: say("neopixel", repr(e))
print("DONE")
