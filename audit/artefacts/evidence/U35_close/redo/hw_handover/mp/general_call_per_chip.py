"""The general call per chip on dev's bus 1 (bus 0's lone BMP3xx is flash/test_bus_concurrency.py's): a volatile
marker in the ISL29125's CONFIG1, then 0x06 to 0x00, then for WATCH_MS which chips answer and whether the marker held;
the SCD30's restart shows as a run of NAKs. Volatile registers only, CONFIG1 put back; no NVM write."""

import time

import machine
from machine import I2C, Pin

SCD30, SGP40, ISL = 0x61, 0x59, 0x44
ISL_CONFIG1, MARKER = 0x01, 0x0D  # RGB mode, 10k lux range: any non-zero value a chip reset clears to 0x00
WATCH_MS, STEP_MS = 3000, 10
wdt = machine.WDT(timeout=8000)
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000, timeout=200000)


def answers(addr: int) -> bool:
    try:
        i2c.writeto(addr, b"")
        return True
    except OSError:
        return False


def config1() -> "int | None":
    try:
        return i2c.readfrom_mem(ISL, ISL_CONFIG1, 1)[0]
    except OSError:
        return None


present = [a for a in (SCD30, SGP40, ISL) if a in i2c.scan()]
saved = config1() if ISL in present else None
if saved is not None:
    i2c.writeto_mem(ISL, ISL_CONFIG1, bytes((MARKER,)))
print("SUM gc_chip present=%s isl_config1_before=%s marker=%s" % ([hex(a) for a in present], saved, config1()))
try:
    acks = i2c.writeto(0x00, b"\x06")
    sent = "acked (%s)" % acks
except OSError as e:
    sent = "raised %r" % e
naks = {a: [] for a in present}
t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < WATCH_MS:
    for a in present:
        if not answers(a):
            naks[a].append(time.ticks_diff(time.ticks_ms(), t0))
    wdt.feed()
    time.sleep_ms(STEP_MS)
after = config1() if ISL in present else None
for a in present:
    n = naks[a]
    print("SUM gc_chip addr=%s nak_polls=%d first_ms=%s last_ms=%s" % (hex(a), len(n), n[0] if n else None, n[-1] if n else None))
print("SUM gc_chip call=%s isl_config1_after=%s (0 = the ISL29125 took the reset)" % (sent, after))
if saved is not None:
    i2c.writeto_mem(ISL, ISL_CONFIG1, bytes((saved,)))
print("DONE=1")
