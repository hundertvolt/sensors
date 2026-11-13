"""Included into device scripts at render: a real held SDA on silicon - START, a device's read address, its ACK clock,
SCL then stopped low while the device drives a 0 data bit - on the first bus with a discovered device to hold. No device
register is written."""

import time

from machine import Pin

import asy_i2c_driver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from bench_facts import BenchFacts, BusFacts

_HALF_PERIOD_US = 5  # 100 kHz bit-banged, inside every bench device's ceiling (SCD30 Interface Description p.2)
_START_POINTER = 0x00  # where the held read starts: its first data bit must be 0 (checked, never assumed)


def _hold_sda_low(bus: "BusFacts", address: int) -> bool:
    # START, the read address, the ACK clock; SCL is left low, so the device keeps driving data bit 7 (0) on SDA. The
    # pins go back to the controller's I2C function after, as the runtime clear hands them back. True when SDA is low.
    sda = Pin(bus["sda_pin"], Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    scl = Pin(bus["scl_pin"], Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)
    time.sleep_us(_HALF_PERIOD_US)
    sda.value(0)
    time.sleep_us(_HALF_PERIOD_US)
    scl.value(0)
    byte = (address << 1) | 1
    for bit in range(7, -1, -1):
        sda.value((byte >> bit) & 1)
        time.sleep_us(_HALF_PERIOD_US)
        scl.value(1)
        time.sleep_us(_HALF_PERIOD_US)
        scl.value(0)
    sda.value(1)  # released for the device's ACK
    time.sleep_us(_HALF_PERIOD_US)
    scl.value(1)
    time.sleep_us(_HALF_PERIOD_US)
    scl.value(0)  # the ACK clock ends: the device now drives the first data bit and holds it while SCL is low
    time.sleep_us(_HALF_PERIOD_US)
    held = sda.value() == 0
    Pin(bus["scl_pin"], Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
    Pin(bus["sda_pin"], Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)
    return held


def _pick(i2c: asy_i2c_driver.I2C, scan: "list[int]") -> "int | None":
    # The first discovered device that answers a read at _START_POINTER with its top bit clear.
    reply = bytearray(1)
    for address in scan:
        try:
            i2c.writeto(address, bytes((_START_POINTER,)))
            i2c.readfrom_into(address, reply)
            if not reply[0] & 0x80:
                return address
        except OSError:  # a device that refuses a pointer read (a command-based part) is not the one to hold
            continue
    return None


def _target(bench: "BenchFacts") -> "tuple[str, asy_i2c_driver.I2C, list[int], int] | None":
    # The first bus with a device to hold: (its id, its wrapper, the known devices it answers for, the held address).
    known = bench["addresses"].values()
    for bus_id in sorted(b for b in bench["bus"] if b.startswith("i2c")):
        i2c = _wrapper(bench["bus"][bus_id])
        scan = [a for a in i2c.scan() or [] if a in known]
        address = _pick(i2c, scan)
        if address is not None:
            return bus_id, i2c, scan, address
    return None


def _wrapper(bus: "BusFacts") -> asy_i2c_driver.I2C:
    return asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
