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
# @include _shared/held_sda.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.bus_reader_loops import Drivers, Seen, device_reader
    from _shared.facts import done, fact
    from _shared.held_sda import _START_POINTER, _hold_sda_low, _target, _wrapper
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py


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


def _stuck_errno(i2c: asy_i2c_driver.I2C, address: int) -> "int | None":
    # One byte on the controller's path: rp2 bit-bangs a zero-length write (ports/rp2/machine_i2c.c:127-145), whose ACK
    # read takes a held SDA as an ACK (extmod/machine_i2c.c:141). _pick's own pointer write, as a read could clear a
    # clear-on-read flag (ERR_REG, BMP388 sec 4.3.2). ETIMEDOUT or EIO expected; None when it went through.
    try:
        i2c.writeto(address, bytes((_START_POINTER,)))
    except OSError as e:
        return e.errno
    return None


async def _main() -> None:
    wdt = arm()
    target = _target(BENCH)
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
