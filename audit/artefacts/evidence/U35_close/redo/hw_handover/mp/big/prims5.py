"""prims5.py: the driver's bus clear against an injected stuck SDA/SCL (re-applied after each Pin() construction, which
rewrites GPIOn_CTRL and so clears the override), a slave letting go after k clocks, and the ladder's rungs on a
controller wedged by a mid-transfer timeout."""
import time, asyncio, machine, asy_i2c_driver as drv
from machine import Pin, I2C, Timer, mem32
SCL, SDA, ADDR = 13, 12, 0x77
_LOW = (3 << 12) | (2 << 8); _OVR = (3 << 12) | (3 << 8)
def ctrl(p): return 0x40014004 + 8 * p
def force(p): mem32[ctrl(p)] = (mem32[ctrl(p)] & ~_OVR) | _LOW
def free(p): mem32[ctrl(p)] = mem32[ctrl(p)] & ~_OVR
_scl_ctrl = ctrl(SCL)
def hold_scl(_): mem32[_scl_ctrl] = (mem32[_scl_ctrl] & ~_OVR) | _LOW
wdt = machine.WDT(timeout=8000)
def say(*a): print("SUM prims5", *a)
held = set(); release_after = [0]; pulses = [0]
class WP:  # a Pin stand-in for the driver's clear: keeps the injected fault and counts SCL low pulses
    OPEN_DRAIN = Pin.OPEN_DRAIN; PULL_UP = Pin.PULL_UP; ALT = Pin.ALT; ALT_I2C = Pin.ALT_I2C; IN = Pin.IN; OUT = Pin.OUT
    def __init__(self, n, *a, **k):
        self.n = n; self.p = Pin(n, *a, **k)
        if n in held: force(n)
    def value(self, *a):
        if self.n == SCL and a and a[0] == 0:
            pulses[0] += 1
            if release_after[0] and pulses[0] >= release_after[0]: held.discard(SDA); free(SDA)
        return self.p.value(*a)
buf = bytearray(1)
def xfer(i2c):
    t0 = time.ticks_us()
    try: i2c.readfrom_mem_into(ADDR, 0, buf); r = "ok%02x" % buf[0]
    except OSError as e: r = "OSError(%s)" % e.args[0]
    return r, time.ticks_diff(time.ticks_us(), t0)
def remux():
    Pin(SCL, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C); Pin(SDA, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
def clear_case(name, hold, k):
    held.clear(); held.update(hold); release_after[0] = k; pulses[0] = 0
    drv.Pin = WP
    try:
        t0 = time.ticks_us(); st = drv._clear_bus(SCL, SDA, 50000); us = time.ticks_diff(time.ticks_us(), t0)
    finally:
        drv.Pin = Pin; held.clear(); free(SCL); free(SDA); remux()
    say("clear", name, "release_after_pulse", k, "status", st, "scl_low_pulses", pulses[0], "us", us)
try:
    clear_case("sda_stuck", (SDA,), 0)
    for k in (1, 2, 5, 8, 9, 10):
        clear_case("sda_lets_go", (SDA,), k)
    clear_case("scl_stuck", (SCL,), 0)
    clear_case("both_stuck", (SCL, SDA), 0)
    # the awaiting clear (the runtime rung) with SCL held: its wait and the loop lag it leaves
    async def aw():
        held.clear(); held.add(SCL); drv.Pin = WP; lagmax = [0]; stop = [False]
        async def lag():
            while not stop[0]:
                t = time.ticks_ms(); await asyncio.sleep_ms(2); lagmax[0] = max(lagmax[0], time.ticks_diff(time.ticks_ms(), t) - 2)
        tk = asyncio.create_task(lag()); t0 = time.ticks_ms()
        try: st = await drv._clear_bus_awaiting(SCL, SDA, 50000)
        finally: drv.Pin = Pin; held.clear(); free(SCL); remux()
        ms = time.ticks_diff(time.ticks_ms(), t0); stop[0] = True; await tk
        return st, ms, lagmax[0]
    say("clear_awaiting scl_stuck status,ms,max_lag_ms", asyncio.run(aw()))
    # a controller wedged by a mid-transfer SCL timeout: what each rung gives back
    for rung in ("retry", "retry_x3", "clear_remux", "reinit", "scan_then_retry"):
        wdt.feed(); i2c = I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=50000, timeout=50000)
        t1 = Timer(mode=Timer.ONE_SHOT, freq=4000, callback=hold_scl, hard=True)
        first = xfer(i2c); time.sleep_ms(80); t1.deinit(); free(SCL)
        if rung == "retry": out = [xfer(i2c)]
        elif rung == "retry_x3": out = [xfer(i2c) for _ in range(3)]
        elif rung == "clear_remux": out = [drv._clear_bus(SCL, SDA, 50000)]; remux(); out.append(xfer(i2c))
        elif rung == "reinit": out = [xfer(I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=50000, timeout=50000))]
        else: out = [i2c.scan(), xfer(i2c)]
        say("wedged rung", rung, "first", first, "then", out, "fresh_check", xfer(I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=50000, timeout=50000)))
finally:
    drv.Pin = Pin; free(SCL); free(SDA)
print("DONE")
