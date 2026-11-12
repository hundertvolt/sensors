"""BACKLOG's two resets with SDA held: the hold made as i2c_held_sda_recovery.py makes it (START, a read address, its
ACK clock, SCL stopped low while the chip drives a 0 bit) on dev's bus BUS, then MODE "machine_reset" or "watchdog".
The product boots after it: read /status (W15 BUS_RECOVERY once) and /sensors. Refuses until CONFIRM (sed)."""

import time

import machine
from machine import I2C, Pin

CONFIRM = False
MODE = "machine_reset"
BUS = 1
PINS = {0: (13, 12), 1: (15, 14)}  # (scl, sda), devices/dev.toml
HALF_US = 5

if not CONFIRM:
    print("SUM held_sda refused: CONFIRM is False (save errcount and the raw FRAM first)")
    print("DONE=1")
    raise SystemExit

wdt = machine.WDT(timeout=8000)
scl_pin, sda_pin = PINS[BUS]
i2c = I2C(BUS, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=50000, timeout=200000)


def pick() -> "int | None":
    reply = bytearray(1)
    for address in i2c.scan():
        try:
            i2c.writeto(address, b"\x00")
            i2c.readfrom_into(address, reply)
            if not reply[0] & 0x80:
                return address
        except OSError:
            continue
    return None


def hold(address: int) -> bool:
    sda = Pin(sda_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    scl = Pin(scl_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    time.sleep_us(HALF_US)
    sda.value(0)
    time.sleep_us(HALF_US)
    scl.value(0)
    byte = (address << 1) | 1
    for bit in range(7, -1, -1):
        sda.value((byte >> bit) & 1)
        time.sleep_us(HALF_US)
        scl.value(1)
        time.sleep_us(HALF_US)
        scl.value(0)
    sda.value(1)
    time.sleep_us(HALF_US)
    scl.value(1)
    time.sleep_us(HALF_US)
    scl.value(0)  # the chip now holds its first data bit, 0, while SCL stays low
    time.sleep_us(HALF_US)
    return sda.value() == 0


address = pick()
held = hold(address) if address is not None else False
print("SUM held_sda bus=%d address=%s held=%d mode=%s" % (BUS, hex(address) if address is not None else None, held, MODE))
print("DONE=1")
time.sleep_ms(200)
if MODE == "machine_reset":
    machine.reset()
machine.WDT(timeout=1000)  # MODE "watchdog": never fed again
while True:
    time.sleep_ms(10)
