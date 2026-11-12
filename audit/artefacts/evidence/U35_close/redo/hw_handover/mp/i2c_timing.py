"""Bare-image I2C timing on dev's buses (constants from the conformance probes): answering addresses, BMP384 forced
conversions per OSR, the SGP40's measure-to-ready time and one unknown command, the SCD30 under five timeouts, then the
general call per bus (it may reset chips' volatile settings). No NVM write."""

import time

from machine import I2C, Pin

SCD30, SGP40, BMP = 0x61, 0x59, 0x77
SGP_MEASURE = b"\x26\x0f\x80\x00\xa2\x66\x66\x93"


def crc8(data: bytes) -> int:
    c = 0xFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x31) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def bus(n: int, timeout: int = 200000) -> I2C:
    return I2C(0, scl=Pin(13), sda=Pin(12), freq=50000, timeout=timeout) if n == 0 else I2C(1, scl=Pin(15), sda=Pin(14), freq=50000, timeout=timeout)


def scan() -> None:
    for n in (0, 1):
        t = time.ticks_us()
        found = bus(n).scan()
        print("SUM i2c_scan bus=%d addresses=%s scan_us=%d" % (n, [hex(a) for a in found], time.ticks_diff(time.ticks_us(), t)))


def scd30() -> None:
    for timeout in (200000, 50000, 20000, 5000, 1000):
        i2c = bus(1, timeout)
        buf = bytearray(3)
        worst_w = worst_r = errs = bad_crc = 0
        last = ""
        for k in range(50):
            cmd = b"\xd1\x00" if k % 2 else b"\x02\x02"  # firmware version, data ready
            try:
                t = time.ticks_us()
                i2c.writeto(SCD30, cmd)
                worst_w = max(worst_w, time.ticks_diff(time.ticks_us(), t))
                time.sleep_ms(5)
                t = time.ticks_us()
                i2c.readfrom_into(SCD30, buf)
                worst_r = max(worst_r, time.ticks_diff(time.ticks_us(), t))
                bad_crc += crc8(buf[:2]) != buf[2]
            except OSError as e:
                errs += 1
                last = repr(e)
            time.sleep_ms(20)
        print("SUM scd30 timeout_us=%d write_worst_us=%d read_worst_us=%d errors=%d bad_crc=%d last_error=%s" % (timeout, worst_w, worst_r, errs, bad_crc, last))


def bmp_conversions() -> None:
    i2c = bus(0)
    print("SUM bmp chip_id=0x%02x" % i2c.readfrom_mem(BMP, 0x00, 1)[0])
    for osr_p in (0, 1, 2, 3):
        i2c.writeto_mem(BMP, 0x1C, bytes([osr_p]))  # osr_t x1
        worst = 0
        for _ in range(10):
            t = time.ticks_us()
            i2c.writeto_mem(BMP, 0x1B, b"\x13")  # forced, pressure and temperature on
            while i2c.readfrom_mem(BMP, 0x03, 1)[0] & 0x60 != 0x60:
                if time.ticks_diff(time.ticks_us(), t) > 200000:
                    break
            worst = max(worst, time.ticks_diff(time.ticks_us(), t))
            i2c.readfrom_mem(BMP, 0x04, 6)
        print("SUM bmp_forced osr_p=x%d osr_t=x1 worst_us=%d (includes the polling reads)" % (1 << osr_p, worst))
    i2c.writeto_mem(BMP, 0x7E, b"\xb6")  # soft reset: every setting back to its default


def sgp40() -> None:
    i2c = bus(1)
    buf = bytearray(3)

    def measure() -> tuple:
        i2c.writeto(SGP40, SGP_MEASURE)
        t = time.ticks_us()
        while True:
            try:
                i2c.readfrom_into(SGP40, buf)
                return time.ticks_diff(time.ticks_us(), t), crc8(buf[:2]) == buf[2]
            except OSError:
                if time.ticks_diff(time.ticks_us(), t) > 200000:
                    return -1, False
                time.sleep_us(500)

    worst = 0
    for _ in range(20):
        worst = max(worst, measure()[0])
        time.sleep_ms(100)
    print("SUM sgp40 measure_to_ready_worst_us=%d (datasheet max 30 ms)" % worst)
    try:
        i2c.writeto(SGP40, b"\x12\x34")
        unknown = "acked"
    except OSError as e:
        unknown = "raised %r" % e
    time.sleep_ms(5)
    ready, crc_ok = measure()
    print("SUM sgp40 unknown_cmd=%s next_measure_us=%d crc_ok=%d" % (unknown, ready, crc_ok))
    i2c.writeto(SGP40, b"\x36\x15")  # heater off, its power-up idle mode


def general_call() -> None:
    for n in (0, 1):
        i2c = bus(n)
        before = i2c.scan()
        try:
            acks = i2c.writeto(0x00, b"\x06")
            res = "acked (%s)" % acks
        except OSError as e:
            res = "raised %r" % e
        time.sleep_ms(50)
        after = i2c.scan()
        print("SUM general_call bus=%d result=%s before=%s after=%s" % (n, res, [hex(a) for a in before], [hex(a) for a in after]))


scan()
bmp_conversions()
sgp40()
scd30()  # after the SGP40: a timeout cut short may leave bus 1 held
general_call()
print("DONE=1")
