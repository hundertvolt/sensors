"""prims3.py: I2C faults injected on silicon through the GPIO output override (a pad forced low, as a slave holding SCL or
SDA would), on bus 0 (BMP3xx 0x77): rp2's transfer timeout, the controller's state after it, and the driver's bus clear."""
import time, asyncio, machine, asy_i2c_driver as drv
from machine import Pin, I2C, Timer, mem32
SCL, SDA, ADDR = 13, 12, 0x77
_FORCE_LOW = (3 << 12) | (2 << 8)  # GPIOn_CTRL: OEOVER enable, OUTOVER drive low (RP2040 2.19.6.1)
_OVR = (3 << 12) | (3 << 8)
def ctrl(pin): return 0x40014004 + 8 * pin
wdt = machine.WDT(timeout=8000)
def say(*a): print("SUM prims3", *a)
def force(pin): mem32[ctrl(pin)] = (mem32[ctrl(pin)] & ~_OVR) | _FORCE_LOW
def free(pin): mem32[ctrl(pin)] = mem32[ctrl(pin)] & ~_OVR
_scl_ctrl, _sda_ctrl = ctrl(SCL), ctrl(SDA)
def rel_scl(_): mem32[_scl_ctrl] = mem32[_scl_ctrl] & ~_OVR
def rel_sda(_): mem32[_sda_ctrl] = mem32[_sda_ctrl] & ~_OVR
def hold_scl(_): mem32[_scl_ctrl] = (mem32[_scl_ctrl] & ~_OVR) | _FORCE_LOW
def hold_sda(_): mem32[_sda_ctrl] = (mem32[_sda_ctrl] & ~_OVR) | _FORCE_LOW
buf = bytearray(1)
def bus(t): return I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=50000, timeout=t)
def xfer(i2c):
    t0 = time.ticks_us()
    try:
        i2c.readfrom_mem_into(ADDR, 0x00, buf)
        r = "ok%02x" % buf[0]
    except OSError as e:
        r = "OSError(%s)" % e.args[0]
    return r, time.ticks_diff(time.ticks_us(), t0)
def remux():
    Pin(SCL, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
    Pin(SDA, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
def after(i2c, t):  # what it takes to get a working transfer back: none, a re-construct, a clear plus a re-construct
    r, _ = xfer(i2c)
    if r.startswith("ok"): return "same_object"
    r, _ = xfer(bus(t))
    if r.startswith("ok"): return "reconstruct(%s first)" % r
    st = drv._clear_bus(SCL, SDA, 50000); remux()
    r, _ = xfer(bus(t))
    return "clear_status %d then reconstruct %s" % (st, r)
try:
    say("baseline", xfer(bus(50000)))
    # SCL held low from before the START (a slave stretching), released by a hard one-shot timer after hold_ms
    for t in (50000, 200000):
        for hold in (2, 20, 45, 60, 150, 400, 3000):
            wdt.feed(); i2c = bus(t)
            force(SCL); tm = Timer(mode=Timer.ONE_SHOT, period=hold, callback=rel_scl, hard=True)
            r, us = xfer(i2c)
            time.sleep_ms(hold + 5); tm.deinit(); free(SCL)
            say("scl_hold timeout_us", t, "hold_ms", hold, "result", r, "call_us", us, "after", after(i2c, t))
    # SCL pulled low mid-transfer (0.25 ms in, inside the address byte at 50 kHz), released after hold_ms
    for t in (50000, 200000):
        for hold in (20, 100, 1000):
            wdt.feed(); i2c = bus(t)
            t1 = Timer(mode=Timer.ONE_SHOT, freq=4000, callback=hold_scl, hard=True)
            t2 = Timer(mode=Timer.ONE_SHOT, period=hold, callback=rel_scl, hard=True)
            r, us = xfer(i2c)
            time.sleep_ms(hold + 5); t1.deinit(); t2.deinit(); free(SCL)
            say("scl_mid timeout_us", t, "hold_ms", hold, "result", r, "call_us", us, "after", after(i2c, t))
    # SDA pulled low mid-transfer (a slave driving a 0 it should not), released after 5 ms
    for t in (50000, 200000):
        wdt.feed(); i2c = bus(t)
        t1 = Timer(mode=Timer.ONE_SHOT, freq=4000, callback=hold_sda, hard=True)
        t2 = Timer(mode=Timer.ONE_SHOT, period=5, callback=rel_sda, hard=True)
        r, us = xfer(i2c)
        time.sleep_ms(10); t1.deinit(); t2.deinit(); free(SDA)
        say("sda_mid timeout_us", t, "result", r, "call_us", us, "after", after(i2c, t))
    # SDA stuck low for good: a transfer, a scan, the driver's sync clear while held and once let go, and whether the
    # re-mux alone (clear() without init, as the driver's clear rung does) brings the old controller object back
    wdt.feed(); i2c = bus(50000); force(SDA)
    say("sda_stuck transfer", xfer(i2c))
    t0 = time.ticks_us(); found = i2c.scan(); say("sda_stuck scan", found, "us", time.ticks_diff(time.ticks_us(), t0))
    t0 = time.ticks_us(); st = drv._clear_bus(SCL, SDA, 50000)
    say("sda_stuck clear_while_held status", st, "us", time.ticks_diff(time.ticks_us(), t0))
    free(SDA); remux(); say("sda_stuck after_release_remux_only", xfer(i2c))
    st = drv._clear_bus(SCL, SDA, 50000)
    say("free_bus clear status", st, "old_object_pins_still_sio", xfer(i2c))
    remux(); say("free_bus remux_only old_object", xfer(i2c))
    # the driver itself: recover() with SCL held for good (the awaiting clear), and the loop lag it causes
    async def lag_probe(stop, out):
        while not stop[0]:
            t0 = time.ticks_ms(); await asyncio.sleep_ms(5)
            out[0] = max(out[0], time.ticks_diff(time.ticks_ms(), t0) - 5)
    async def rec(hold_scl_forever, hold_sda_forever):
        d = drv.I2C(0, SCL, SDA, 50000)
        if hold_scl_forever: force(SCL)
        if hold_sda_forever: force(SDA)
        stop, out = [False], [0]
        task = asyncio.create_task(lag_probe(stop, out))
        t0 = time.ticks_ms(); st = await d.recover(); ms = time.ticks_diff(time.ticks_ms(), t0)
        stop[0] = True; await task
        free(SCL); free(SDA)
        d2 = await d.recover()
        return st, ms, out[0], d2, xfer(d._i2c)
    for case in ((True, False), (False, True), (False, False)):
        wdt.feed()
        say("driver_recover scl_held", case[0], "sda_held", case[1], "status,ms,max_lag_ms,status_after_release,xfer", asyncio.run(rec(*case)))
finally:
    free(SCL); free(SDA)
print("DONE")
