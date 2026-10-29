"""prims10.py: an edge storm on a GPIO interrupt against the sensor drivers' soft-IRQ handler shapes (ISL29125 falling,
SCD30 rising). INOVER does not reach the edge detector (it samples the raw pad), so a free floating pin's pad pull-up and
pull-down are toggled from a hard timer instead: nothing is driven. Callbacks against edges, a soft Timer, the loop lag."""
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
    c = 0x40014004 + 8 * 6; base = mem32[c] & ~(3 << 16); n6 = [0]
    p6.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda _p: n6.__setitem__(0, n6[0] + 1))
    for ov in (3, 2, 3, 2): mem32[c] = base | ov << 16; time.sleep_ms(5)
    mem32[c] = base; p6.irq(handler=None)
    say("inover_on_gpio6 four_forced_edges callbacks", n6[0], "intr0_gpio6", hex(mem32[0x400140f0] >> 24 & 0xF))
    free = None
    for g in (22, 21, 20, 19, 17, 16, 10, 7, 26, 27, 28):
        q = Pin(g, Pin.IN, Pin.PULL_UP); time.sleep_us(200); up = q.value()
        q.init(Pin.IN, Pin.PULL_DOWN); time.sleep_us(200); dn = q.value()
        if up == 1 and dn == 0: free = g; break
    say("floating pin", free)
    if free is None: return
    pf = Pin(free, Pin.IN, Pin.PULL_DOWN)
    for f in (feeder(), lag(), waiter("isl", isl._read_event), waiter("scd", scd._read_event)): asyncio.create_task(f)
    ts = Timer(mode=Timer.PERIODIC, period=10, callback=scb)
    rates = (50, 500, 2500, 5000, 10000)
    cases = [("control_no_irq", 0, 10000)] + [("isl_shape_falling", 1, r) for r in rates] + [("scd_shape_rising", 2, r) for r in rates]
    for i, (name, pin, rate) in enumerate(cases):
        mb0[0] = i + 1
        ctrl = 0x4001C004 + 4 * free  # PADS_BANK0 GPIOn: bit 3 PUE, bit 2 PDE
        base = mem32[ctrl] & ~0xC; lo, hi = base | 0x4, base | 0x8
        if pin == 1: pf.irq(trigger=Pin.IRQ_FALLING, handler=isl._on_irq)
        elif pin == 2: pf.irq(trigger=Pin.IRQ_RISING, handler=lambda _b: scd.hit())
        isl.n = scd.n = 0; wakes["isl"] = wakes["scd"] = 0; lagst.clear(); flips = 0; limit = 2 * rate * WIN_MS // 1000
        await asyncio.sleep_ms(200); s0 = soft[0]; t0 = time.ticks_ms()
        tm = Timer(mode=Timer.PERIODIC, freq=2 * rate, callback=storm, hard=True)
        await asyncio.sleep_ms(WIN_MS)
        tm.deinit(); el = time.ticks_diff(time.ticks_ms(), t0); s1 = soft[0]; mem32[ctrl] = lo
        await asyncio.sleep_ms(300)
        pf.irq(handler=None)
        say(name, "edges_per_s", rate, "edges", flips // 2, "callbacks", isl.n + scd.n, "wakeups", wakes["isl"] + wakes["scd"],
            "soft_timer", s1 - s0, "of", el // 10, "lag_max", lagst.get("max"), "lag_over20", lagst.get("over20"), "lag_n", lagst.get("n"), "window_ms", el)
    ts.deinit()
asyncio.run(main())
print("DONE")
