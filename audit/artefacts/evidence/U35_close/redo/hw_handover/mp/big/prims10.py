"""prims10.py: an edge storm on a sensor interrupt line (ISL29125 INT GPIO6 falling, SCD30 RDY GPIO11 rising) made by
toggling the pin's input override from a hard timer (the pad is never driven), against the drivers' soft-IRQ handler
shapes: callbacks against edges, a 100 Hz soft Timer's deliveries, a flag waiter's wakeups and the loop lag."""
import time, asyncio, machine
from machine import Pin, Timer, mem32
wdt = machine.WDT(timeout=8000)
mb0, mb1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(4): mb0[i] = 0
for i in range(3): mb1[i] = 0
def say(*a): print("SUM prims10", *a)
WIN_MS = 5000
class Isl:  # asy_isl29125_driver's _on_irq: an attribute store and ThreadSafeFlag.set(), bound once
    def __init__(self):
        self._irq_fired = False; self._read_event = asyncio.ThreadSafeFlag(); self.n = 0
    def _on_irq(self, _pin):
        self._irq_fired = True; self._read_event.set(); self.n += 1
class Scd:  # asy_scd30_driver's handler: a lambda calling the flag's set()
    def __init__(self):
        self._read_event = asyncio.ThreadSafeFlag(); self.n = 0
    def hit(self):
        self.n += 1; self._read_event.set()
ctrl = 0; lo = 0; hi = 0; flips = 0; limit = 0
def storm(_):  # stops toggling on its own at the edge budget, so a starved loop cannot prolong the storm
    global flips
    if flips < limit:
        flips += 1; mem32[ctrl] = lo if flips & 1 else hi
soft = [0]; lagst = {}
def scb(_): soft[0] += 1
async def feeder():
    while True:
        wdt.feed(); mb0[1] = flips; mb0[2] = soft[0]; mb1[1] = lagst.get("max", 0); await asyncio.sleep_ms(100)
async def lag():
    while True:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t0) - 10
        lagst["max"] = max(lagst.get("max", 0), d); lagst["n"] = lagst.get("n", 0) + 1; lagst["over20"] = lagst.get("over20", 0) + (d > 20)
wakes = {"isl": 0, "scd": 0}
async def waiter(name, flag):
    while True:
        await flag.wait(); wakes[name] += 1
async def main():
    global ctrl, lo, hi, flips, limit
    isl, scd = Isl(), Scd()
    p6, p11 = Pin(6, Pin.IN), Pin(11, Pin.IN)
    say("idle levels gpio6", p6.value(), "gpio11", p11.value())
    for f in (feeder(), lag(), waiter("isl", isl._read_event), waiter("scd", scd._read_event)): asyncio.create_task(f)
    ts = Timer(mode=Timer.PERIODIC, period=10, callback=scb)
    cases = [("control_no_irq", 6, 5000)] + [("gpio6_isl", 6, r) for r in (50, 500, 2500, 5000)] + [("gpio11_scd", 11, r) for r in (50, 500, 2500, 5000)]
    for i, (name, pin, rate) in enumerate(cases):
        mb0[0] = i + 1
        ctrl = 0x40014004 + 8 * pin
        base = mem32[ctrl] & ~(3 << 16); lo, hi = base | 2 << 16, base | 3 << 16
        if name.startswith("gpio6"): p6.irq(trigger=Pin.IRQ_FALLING, handler=isl._on_irq)
        elif name.startswith("gpio11"): p11.irq(trigger=Pin.IRQ_RISING, handler=lambda _b: scd.hit())
        isl.n = scd.n = 0; wakes["isl"] = wakes["scd"] = 0; lagst.clear(); flips = 0; limit = 2 * rate * WIN_MS // 1000
        await asyncio.sleep_ms(200); s0 = soft[0]; t0 = time.ticks_ms()
        tm = Timer(mode=Timer.PERIODIC, freq=2 * rate, callback=storm, hard=True)
        await asyncio.sleep_ms(WIN_MS)
        tm.deinit(); el = time.ticks_diff(time.ticks_ms(), t0); s1 = soft[0]; mem32[ctrl] = base
        await asyncio.sleep_ms(300)
        p6.irq(handler=None); p11.irq(handler=None)
        say(name, "edges_per_s", rate, "edges", flips // 2, "callbacks", isl.n + scd.n, "wakeups", wakes["isl"] + wakes["scd"],
            "soft_timer", s1 - s0, "of", el // 10, "lag_max", lagst.get("max"), "lag_over20", lagst.get("over20"), "lag_n", lagst.get("n"), "window_ms", el)
    ts.deinit()
asyncio.run(main())
print("DONE")
