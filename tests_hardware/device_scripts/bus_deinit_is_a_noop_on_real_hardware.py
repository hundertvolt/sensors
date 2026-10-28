"""Isolated-driver device script: SPECIFICATION.md Part F.5.1's two rp2 claims on a live bus - machine.I2C/SPI
.deinit() are silent no-ops and each bus id is a static singleton - read from the port's protocol tables and modelled
in the fakes, here observed on silicon over the bench TOML's buses. Reports facts; the host gives the verdict."""

import asyncio

import machine

import asy_spi_driver
from asy_crc_checks import CRC8
from asy_fram_manager import FRAMManager

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts, BusFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_CHUNK_SIZE = 32
_RP2_I2C_TIMEOUT_US = 50000  # machine.I2C's own default (ports/rp2/machine_i2c.c:38, v1.29.0)
_PATTERN = bytes((i * 7 + 3) % 256 for i in range(_CHUNK_SIZE))


def _i2c(bus: "BusFacts") -> machine.I2C:
    # A re-construction resets frequency and timeout for every user of the static per-id object
    # (ports/rp2/machine_i2c.c:38, 50, 72, 87, 110, v1.29.0), so it passes the TOML's own values.
    timeout = bus.get("timeout", _RP2_I2C_TIMEOUT_US)
    return machine.I2C(bus["id"], scl=machine.Pin(bus["scl_pin"]), sda=machine.Pin(bus["sda_pin"]), freq=bus["frequency"], timeout=timeout)


async def _spi_claims(wdt: machine.WDT) -> None:
    # The same no-op claim on SPI, proven against real FRAM traffic; the FRAM's first chunk is cleared after setup()
    # and again on the way out, so no pattern this script wrote survives it.
    chip = BENCH["instances"]["fram"]
    bus = BENCH["bus"][chip["bus"]]
    spi_wrapper = asy_spi_driver.SPI(bus["id"], bus["sck_pin"], bus["mosi_pin"], bus["miso_pin"])
    fram = FRAMManager(spi_wrapper, chip["cs_pin"], max_size=BENCH["fram_max_size"])
    fact("fram_setup", await fram.setup())
    chunk = fram.get_chunk(_CHUNK_SIZE, crc=CRC8(), owner="bus_deinit_is_a_noop_on_real_hardware")
    if chunk is None:
        fact("chunk", None)
        return
    try:
        fact("chunk_cleared_after_setup", await chunk.clear())
        fact("baseline_write", await chunk.write(_PATTERN))
        raw_spi = spi_wrapper._spi  # the underlying machine.SPI, not the project wrapper's own deinit()
        fact("raw_spi_present", raw_spi is not None)
        if raw_spi is not None:
            again = machine.SPI(bus["id"], sck=machine.Pin(bus["sck_pin"]), mosi=machine.Pin(bus["mosi_pin"]), miso=machine.Pin(bus["miso_pin"]))
            fact("spi_singleton", again is raw_spi)
            raw_spi.deinit()
            wdt.feed()
            fact("spi_read_after_deinit", bytes(await chunk.read() or b"") == _PATTERN)
    finally:
        fact("chunk_cleared", await chunk.clear())


async def _main() -> None:
    wdt = arm()
    # deinit() exists on machine.I2C from 1.29 (it raises AttributeError before); the pinned version is 1.29.0.
    fact("i2c_has_deinit", hasattr(machine.I2C, "deinit"))
    bus = BENCH["bus"][BENCH["instances"]["bmp3xx"]["bus"]]
    i2c = _i2c(bus)
    fact("scan_before", sorted(i2c.scan()))
    i2c.deinit()
    fact("scan_after", sorted(i2c.scan()))
    fact("i2c_singleton", _i2c(bus) is i2c)
    wdt.feed()
    await _spi_claims(wdt)
    done()


asyncio.run(_main())
