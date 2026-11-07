"""Long I2C run for rare-event rates (REPORT 7 item 3): per chip and phase - register-pointer write, data read,
register write - the transactions, their OSErrors by errno, wrong values and bad CRCs, and the worst duration; the SGP40
at 1 Hz, its first measure after an idle minute counted apart. Volatile registers only; DUR_S per run."""

import time

from machine import I2C, Pin

DUR_S = 1200
BMP, ISL, SCD30, SGP40 = 0x77, 0x44, 0x61, 0x59
MEASURE = b"\x26\x0f\x80\x00\xa2\x66\x66\x93"  # the datasheet's default arguments and CRCs (sgp40 probe)


def crc8(data: bytes) -> int:
    c = 0xFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x31) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


class C:
    def __init__(self, chip: str, phase: str) -> None:
        self.chip, self.phase = chip, phase
        self.n = self.eio = self.eto = self.other = self.bad = self.worst = 0

    def run(self, fn) -> bool:
        t = time.ticks_us()
        ok = False
        try:
            ok = fn() is not False
            self.bad += not ok
        except OSError as e:
            code = e.args[0] if e.args else 0
            if code == 5:
                self.eio += 1
            elif code == 110:
                self.eto += 1
            else:
                self.other += 1
        self.n += 1
        self.worst = max(self.worst, time.ticks_diff(time.ticks_us(), t))
        return ok

    def report(self) -> None:
        print("SUM L i2c chip=%s phase=%s n=%d eio=%d etimedout=%d other=%d bad=%d worst_us=%d" % (self.chip, self.phase, self.n, self.eio, self.eto, self.other, self.bad, self.worst))


b0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000, timeout=200000)
b1 = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000, timeout=200000)
one, three = bytearray(1), bytearray(3)
ref = {}
for name, bus, addr, reg in (("bmp_id", b0, BMP, 0x00), ("bmp_osr", b0, BMP, 0x1C), ("isl_id", b1, ISL, 0x00), ("isl_c1", b1, ISL, 0x01)):
    ref[name] = bus.readfrom_mem(addr, reg, 1)[0]
print("REF", ref)
REG0, W_BMP, W_ISL = b"\x00", bytes((ref["bmp_osr"],)), bytes((ref["isl_c1"],))  # no allocation in timed calls
cs = {k: C(k.split("_")[0], k.split("_", 1)[1]) for k in ("bmp_reg", "bmp_data", "bmp_write", "isl_reg", "isl_data", "isl_write", "scd30_cmd", "scd30_data", "sgp40_cmd", "sgp40_data", "sgp40_first")}


def id_read(bus: I2C, addr: int, key: str, prefix: str) -> None:
    if cs[prefix + "_reg"].run(lambda: bus.writeto(addr, REG0, False)):
        cs[prefix + "_data"].run(lambda: bus.readfrom_into(addr, one) or one[0] == ref[key])


def crc_read(bus: I2C, addr: int, c: C) -> None:
    c.run(lambda: bus.readfrom_into(addr, three) or crc8(three[:2]) == three[2])


end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
scd_due = sgp_due = time.ticks_ms()
scd_read_at = sgp_read_at = 0
idle_until, first_pending, i = 0, False, 0
next_idle = time.ticks_add(time.ticks_ms(), 120000)
while time.ticks_diff(end, time.ticks_ms()) > 0:
    now = time.ticks_ms()
    id_read(b0, BMP, "bmp_id", "bmp")
    id_read(b1, ISL, "isl_id", "isl")
    i += 1
    if i % 10 == 0:
        cs["bmp_write"].run(lambda: b0.writeto_mem(BMP, 0x1C, W_BMP))
        cs["isl_write"].run(lambda: b1.writeto_mem(ISL, 0x01, W_ISL))
    if scd_read_at and time.ticks_diff(now, scd_read_at) >= 0:
        crc_read(b1, SCD30, cs["scd30_data"])
        scd_read_at = 0
    elif time.ticks_diff(now, scd_due) >= 0:
        if cs["scd30_cmd"].run(lambda: b1.writeto(SCD30, b"\x02\x02")):
            scd_read_at = time.ticks_add(now, 5)
        scd_due = time.ticks_add(now, 50)
    if idle_until and time.ticks_diff(now, idle_until) < 0:
        pass
    elif sgp_read_at and time.ticks_diff(now, sgp_read_at) >= 0:
        crc_read(b1, SGP40, cs["sgp40_first"] if first_pending else cs["sgp40_data"])
        sgp_read_at, first_pending = 0, False
    elif time.ticks_diff(now, next_idle) >= 0:
        b1.writeto(SGP40, b"\x36\x15")  # heater off for an idle minute
        idle_until, next_idle, first_pending = time.ticks_add(now, 60000), time.ticks_add(now, 180000), True
        sgp_due = idle_until
    elif time.ticks_diff(now, sgp_due) >= 0:
        idle_until = 0
        if cs["sgp40_cmd"].run(lambda: b1.writeto(SGP40, MEASURE)):
            sgp_read_at = time.ticks_add(now, 30)
        sgp_due = time.ticks_add(now, 1000)
    time.sleep_ms(1)
b1.writeto(SGP40, b"\x36\x15")
for c in cs.values():
    c.report()
print("DONE=1")
