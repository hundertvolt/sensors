"""Isolated-driver device script: each I2C chip's driver setup() on silicon, with every transfer the bus wrapper hands
its machine.I2C recorded, then one read through the set-up driver. The host test finds each soft reset in the record
(the clean state every setup episode starts from). Every write is a volatile command or register; no NVM is written."""

import asyncio
import binascii

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
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py


class _Recorder:
    # Stands in for the wrapper's machine.I2C: each transfer appended to log as [op, address, a write's bytes in hex],
    # then handed on with its arguments as passed (stop is positional-only there), so its result and OSError are real.
    def __init__(self, real: "machine.I2C", log: "list[list[object]]") -> None:
        self._real = real
        self.log = log

    def readfrom_into(self, address: int, buf: "bytearray | memoryview", *stop: bool) -> None:
        self.log.append(["r", address, ""])
        self._real.readfrom_into(address, buf, *stop)

    def scan(self) -> "list[int]":
        return self._real.scan()

    def writeto(self, address: int, buf: "bytes | bytearray | memoryview", *stop: bool) -> int:
        self.log.append(["w", address, binascii.hexlify(bytes(buf)).decode()])
        return self._real.writeto(address, buf, *stop)


async def _setups(wdt: "machine.WDT") -> "dict[str, dict[str, object]]":
    # Per I2C instance: its driver, its address, the transfers of its setup() and the read after it (None when valid).
    drivers = Drivers(SCD30_I2C, BMP3XX_I2C, SGP40_I2C, ISL29125_I2C)
    found: dict[str, dict[str, object]] = {}
    for bus_id in sorted(b for b in BENCH["bus"] if b.startswith("i2c")):
        bus = BENCH["bus"][bus_id]
        i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
        log: list[list[object]] = []
        i2c._i2c = _Recorder(i2c._i2c, log)  # type: ignore[arg-type, assignment]  # the recorder stands in for machine.I2C
        for label in sorted(name for name, instance in BENCH["instances"].items() if instance.get("bus") == bus_id):
            entry: dict[str, object] = {"driver": BENCH["instances"][label]["driver"], "address": BENCH["addresses"][label]}
            start = len(log)
            try:
                read = await device_reader(BENCH, label, i2c, Seen(), drivers)
                entry["log"] = log[start:]
                entry["answer"] = "no reader" if read is None else await read()
            except Exception as e:  # recorded per chip; the host gives the verdict
                entry["log"] = log[start:]
                entry["answer"] = repr(e)
            found[label] = entry
            wdt.feed()
            await asyncio.sleep(0)
    return found


async def _main() -> None:
    wdt = arm()
    fact("setups", await _setups(wdt))
    done()


asyncio.run(_main())
