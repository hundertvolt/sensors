"""Isolated-driver device script: SPECIFICATION.md Part F.5.1's two rp2 claims, on a live bus.
Both were read out of the port's protocol tables and modelled in tests/machine.py and
digital_twin/machine.py, never observed on real silicon: machine.I2C/SPI .deinit() are silent
no-ops (the peripheral keeps running), and each bus id is a static singleton."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from crc_checks import CRC8

I2C_PORT, I2C_SCL, I2C_SDA = 0, 13, 12  # dev bench wiring, same as the other i2c0 device scripts
SPI_PORT, SPI_SCK, SPI_MOSI, SPI_MISO, SPI_CS = 0, 2, 3, 4, 5
CHUNK_SIZE = 32
PATTERN = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))
failures: list[str] = []


def check(msg: str, *, condition: bool) -> None:
    if not condition:
        failures.append(msg)


async def _main() -> None:
    # --- machine.I2C: deinit() exists at all (1.29 floor - it raises AttributeError on 1.28) ---
    check("machine.I2C has no deinit() - this build predates 1.29", condition=hasattr(machine.I2C, "deinit"))

    i2c = machine.I2C(I2C_PORT, scl=machine.Pin(I2C_SCL), sda=machine.Pin(I2C_SDA), freq=50000)
    before = sorted(i2c.scan())
    check("no I2C devices found before deinit() - bench wiring problem, not a deinit finding", condition=len(before) > 0)
    i2c.deinit()
    after = sorted(i2c.scan())
    check(
        f"I2C.deinit() actually stopped the bus - scan went from {before!r} to {after!r}; Part F.5.1 says it is a silent no-op on rp2",
        condition=after == before,
    )

    # --- machine.I2C/SPI are static per-bus singletons, so re-constructing reconfigures the same
    #     object rather than allocating a new one (nothing leaks, nothing is reclaimable). ---
    check("machine.I2C(id) did not return the same singleton object on re-construction", condition=machine.I2C(I2C_PORT, scl=machine.Pin(I2C_SCL), sda=machine.Pin(I2C_SDA), freq=50000) is i2c)

    # --- machine.SPI: the same no-op claim, proven against real FRAM traffic rather than a scan ---
    spi_wrapper = asy_spi_driver.SPI(SPI_PORT, SPI_SCK, SPI_MOSI, SPI_MISO)
    fram = AsyFramManager(spi_wrapper, SPI_CS, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding, cannot judge SPI deinit()")
        return
    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8())
    if chunk is None:
        print("RESULT: FAIL get_chunk() returned None")
        return
    check("baseline FRAM write before SPI deinit() failed", condition=await chunk.write(PATTERN) is True)

    raw_spi = spi_wrapper._spi  # the underlying machine.SPI, NOT the project wrapper's own deinit()
    check("asy_spi_driver.SPI has no underlying machine.SPI to test", condition=raw_spi is not None)
    if raw_spi is not None:
        check("machine.SPI(id) did not return the same singleton object on re-construction", condition=machine.SPI(SPI_PORT, sck=machine.Pin(SPI_SCK), mosi=machine.Pin(SPI_MOSI), miso=machine.Pin(SPI_MISO)) is raw_spi)
        raw_spi.deinit()
        check(
            "machine.SPI.deinit() actually stopped the bus - a real FRAM read failed afterwards; Part F.5.1 says it is a silent no-op on rp2",
            condition=bytes(await chunk.read() or b"") == PATTERN,
        )

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:6])}")
    else:
        print(f"RESULT: PASS I2C/SPI deinit() are silent no-ops on a live bus and both buses are per-id singletons (i2c scan {before!r} unchanged)")


asyncio.run(_main())
