"""SCD30 bench state and readiness: its five stored settings read back (getters only: 0x5403, 0x4600, 0x5102, 0x5204,
0x5306, as src/asy_scd30_driver.py's snapshot; never 0x0010, which starts a measurement), then DUR_S of data-ready
polling every 100 ms: the interval between ready flags and the longest run of not-ready reads. Reads only, no NVM write."""

import time

from machine import I2C, Pin

DUR_S = 600
SCD30 = 0x61
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000, timeout=200000)


def word(cmd: int, n: int = 3) -> bytes:
    i2c.writeto(SCD30, bytes((cmd >> 8, cmd & 0xFF)))
    time.sleep_ms(5)
    buf = bytearray(n)
    i2c.readfrom_into(SCD30, buf)
    return bytes(buf)


for name, cmd in (("temp_offset", 0x5403), ("interval", 0x4600), ("altitude", 0x5102), ("frc", 0x5204), ("asc", 0x5306)):
    b = word(cmd)
    print("SUM scd30_state %s=%d raw=%s" % (name, (b[0] << 8) | b[1], b.hex()))
    time.sleep_ms(20)

end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
last_ready = None
gaps, run, worst_run, errors, polls = [], 0, 0, 0, 0
while time.ticks_diff(end, time.ticks_ms()) > 0:
    polls += 1
    try:
        r = word(0x0202)
        if r[1] == 1:
            now = time.ticks_ms()
            if last_ready is not None:
                gaps.append(time.ticks_diff(now, last_ready))
            last_ready = now
            worst_run = max(worst_run, run)
            run = 0
            word(0x0300, 18)  # read the measurement, which clears the flag
        else:
            run += 1
    except OSError:
        errors += 1
    time.sleep_ms(100)
gaps.sort()
if gaps:
    print("SUM scd30_ready n=%d interval_ms min=%d median=%d max=%d worst_not_ready_run=%d polls=%d errors=%d" % (len(gaps), gaps[0], gaps[len(gaps) // 2], gaps[-1], worst_run, polls, errors))
else:
    print("SUM scd30_ready no ready flag in %d polls, errors=%d" % (polls, errors))
print("DONE=1")
