"""Isolated-driver device script: makes a real held SDA on silicon - START, a device's read address, its ACK clock, SCL
then stopped low while the device drives a 0 data bit - and clears it twice: by the runtime bus rung (clear()), and by
the boot-time clear the I2C wrapper runs before it constructs the controller. No device register is written."""

import asyncio
import time

from machine import Pin

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/bus_reader_loops.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.bus_reader_loops import Drivers, Seen, device_reader
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts, BusFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_HALF_PERIOD_US = 5  # 100 kHz bit-banged, inside every bench device's ceiling (SCD30 Interface Description p.2)
_START_POINTER = 0x00  # where the held read starts: its first data bit must be 0 (checked, never assumed)


async def _answered(i2c: asy_i2c_driver.I2C, labels: "list[str]", wdt: "machine.WDT") -> "dict[str, str | None]":
    # Each device's identification (its driver's setup()) and one read: None per device that answered both.
    answers: dict[str, str | None] = {}
    drivers = Drivers(SCD30_I2C, BMP3XX_I2C, SGP40_I2C, ISL29125_I2C)
    for label in labels:
        try:
            read = await device_reader(BENCH, label, i2c, Seen(), drivers)
            answers[label] = "no reader" if read is None else await read()
        except Exception as e:  # recorded per device; the host gives the verdict
            answers[label] = repr(e)
        wdt.feed()
        await asyncio.sleep(0)
    return answers


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
            if i2c.writeto(address, bytes((_START_POINTER,))) and i2c.readfrom_into(address, reply) and not reply[0] & 0x80:
                return address
        except OSError:  # a device that refuses a pointer read (a command-based part) is not the one to hold
            continue
    return None


def _stuck_errno(i2c: asy_i2c_driver.I2C, address: int) -> "int | None":
    # A transfer on the held bus: ETIMEDOUT or EIO expected; None when it went through.
    try:
        i2c.writeto(address, b"")
    except OSError as e:
        return e.errno
    return None


def _target() -> "tuple[str, asy_i2c_driver.I2C, list[int], int] | None":
    # The first bus with a device to hold: (its id, its wrapper, the known devices it answers for, the held address).
    known = BENCH["addresses"].values()
    for bus_id in sorted(b for b in BENCH["bus"] if b.startswith("i2c")):
        i2c = _wrapper(BENCH["bus"][bus_id])
        scan = [a for a in i2c.scan() or [] if a in known]
        address = _pick(i2c, scan)
        if address is not None:
            return bus_id, i2c, scan, address
    return None


def _wrapper(bus: "BusFacts") -> asy_i2c_driver.I2C:
    return asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))


async def _main() -> None:
    wdt = arm()
    target = _target()
    if target is None:
        fact("held_device", None)
        done()
        return
    bus_id, i2c, scan, address = target
    bus = BENCH["bus"][bus_id]
    known = {a: label for label, a in BENCH["addresses"].items()}
    labels = [known[a] for a in scan]
    fact("held_device", {"bus": bus_id, "device": known[address], "register": _START_POINTER})
    # Case 1: the runtime rung. The hold is made under the wrapper's bus lock, as a session would hold the bus.
    async with i2c.bus_lock:
        held = _hold_sda_low(bus, address)
    stuck = _stuck_errno(i2c, address)
    start = time.ticks_ms()
    status = await i2c.clear()
    fact("runtime_clear", {"held": held, "stuck_errno": stuck, "status": status, "clear_ms": time.ticks_diff(time.ticks_ms(), start), "answered": await _answered(i2c, labels, wdt)})
    # Case 2: the boot-time clear - a fresh wrapper clears the bus before it constructs the controller.
    held = _hold_sda_low(bus, address)
    fresh = _wrapper(bus)
    boot_status = fresh.take_boot_clear_status()
    sda_high = Pin(bus["sda_pin"]).value() == 1
    fact("boot_clear", {"held": held, "status": boot_status, "sda_high": sda_high, "answered": await _answered(fresh, labels, wdt)})
    done()


asyncio.run(_main())
