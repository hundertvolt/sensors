"""Whether SDA held low by the BMP384 (bus 0, mid-read, bit-banged) survives machine.reset(), and whether a 9-clock clear
frees it (BACKLOG:301, the form of B4's boot clear). MODE "arm" holds and resets; MODE "check" reads, clears, rescans."""

import time

from machine import I2C, Pin

MODE = "arm"
SCL_PIN, SDA_PIN, BMP = 13, 12, 0x77


def od(n: int) -> Pin:
    return Pin(n, Pin.OPEN_DRAIN, pull=Pin.PULL_UP, value=1)


def pulse(scl: Pin) -> None:
    scl(1)
    time.sleep_us(20)
    scl(0)
    time.sleep_us(20)


if MODE == "arm":
    scl, sda = od(SCL_PIN), od(SDA_PIN)
    time.sleep_us(50)
    sda(0)  # START
    time.sleep_us(20)
    scl(0)
    time.sleep_us(20)
    for i in range(7, -1, -1):  # address, read
        sda((((BMP << 1) | 1) >> i) & 1)
        pulse(scl)
    sda(1)
    scl(1)
    time.sleep_us(20)
    ack = sda()
    scl(0)
    time.sleep_us(20)
    clocked = 0
    for _ in range(32):  # data bits until the slave drives a 0, acking each full byte
        if sda() == 0:
            break
        pulse(scl)
        clocked += 1
        if clocked % 8 == 0:
            sda(0)
            pulse(scl)
            sda(1)
    print("SUM sda_hold armed ack=%d bits_clocked=%d sda_now=%d" % (ack, clocked, sda()))
    time.sleep_ms(100)
    import machine

    machine.reset()
else:
    sda_in, scl_in = Pin(SDA_PIN, Pin.IN, Pin.PULL_UP), Pin(SCL_PIN, Pin.IN, Pin.PULL_UP)
    time.sleep_us(50)
    s0, c0 = sda_in(), scl_in()
    try:
        before = [hex(a) for a in I2C(0, scl=Pin(13), sda=Pin(12), freq=50000, timeout=200000).scan()]
    except OSError as e:
        before = repr(e)
    scl, sda = od(SCL_PIN), od(SDA_PIN)
    n = 0
    while sda() == 0 and n < 9:
        pulse(scl)
        n += 1
    sda(0)  # STOP
    time.sleep_us(20)
    scl(1)
    time.sleep_us(20)
    sda(1)
    time.sleep_us(50)
    s1 = sda()
    i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000, timeout=200000)
    try:
        after, chip = [hex(a) for a in i2c.scan()], hex(i2c.readfrom_mem(BMP, 0, 1)[0])
    except OSError as e:
        after, chip = repr(e), "-"
    print("SUM sda_hold after_reset sda=%d scl=%d scan_before_clear=%s clocks_to_free=%d sda_after_clear=%d scan_after=%s bmp_chip_id=%s" % (s0, c0, before, n, s1, after, chip))
print("DONE=1")
