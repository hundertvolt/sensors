"""Bench probe (lead, 2026-11-09): the SCD30's routine frames on dev's i2c1 (its bus settings), each transfer timed;
rp2's I2C holds the loop for a transfer's whole length. Reads only: data-ready and read-measurement, no NVM command."""
import time

import machine

wdt = machine.WDT(timeout=8000)
ADDR = 0x61
i2c = machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14), freq=50000, timeout=200000)
b3 = bytearray(3)
b18 = bytearray(18)
times = {"write_ready_cmd": [], "read_ready_3B": [], "write_meas_cmd": [], "read_meas_18B": []}
errors = []


def timed(key, fn, *args):
    t0 = time.ticks_us()
    fn(*args)
    times[key].append(time.ticks_diff(time.ticks_us(), t0))


end = time.ticks_add(time.ticks_ms(), 90000)
while time.ticks_diff(end, time.ticks_ms()) > 0:
    wdt.feed()
    try:
        timed("write_ready_cmd", i2c.writeto, ADDR, b"\x02\x02")
        time.sleep_ms(3)
        timed("read_ready_3B", i2c.readfrom_into, ADDR, b3)
        if b3[1] == 1:
            timed("write_meas_cmd", i2c.writeto, ADDR, b"\x03\x00")
            time.sleep_ms(3)
            timed("read_meas_18B", i2c.readfrom_into, ADDR, b18)
    except OSError as e:
        errors.append(e.args[0] if e.args else -1)
    time.sleep_ms(250)
for key, v in times.items():
    v.sort()
    n = len(v)
    print(key, "n", n, "min_us", v[0] if n else None, "median_us", v[n // 2] if n else None, "max_us", v[-1] if n else None)
print("errors", len(errors), errors[:10])
print("wire_only_us_at_50kHz", "write_cmd 540", "read_3B 720", "read_18B 3420")
print("done")
