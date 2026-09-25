"""Isolated-driver device script: the real-hardware counterpart to the mock tier's
scenario_a_write_does_not_disturb_concurrent_sibling_reads, with ISL29125's volatile configure()
as the writer across _WRITE_DELAYS_MS. Why delays, not yields: SPECIFICATION.md Part C.8."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

# Varied, not a fixed cadence: 5ms is back-to-back with a sibling's transaction, 120ms is mid
# another sibling's read. Cycled across WRITE_CYCLES so every run covers the whole spread rather
# than whichever phase natural jitter lands on.
_WRITE_DELAYS_MS = (5, 15, 40, 80, 120)
WRITE_CYCLES = len(_WRITE_DELAYS_MS) * 2  # each delay exercised twice, not just once
_MODE_RGB = 0x05


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    isl = ISL29125_I2C(i2c1)
    scd = SCD30_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    await isl.setup()
    await isl.configure(mode=_MODE_RGB, range_fs=10000, resolution=16, threshold_interrupt=False)
    await scd.setup()  # no set_ambient_pressure() here - real continuous measurement is triggered once, elsewhere, via the session fixture
    await sgp.setup()

    write_windows = []  # (start_ms, end_ms) per completed configure()
    scd_errors: list[str] = []
    sgp_errors: list[str] = []
    write_errors: list[str] = []
    scd_reads = 0
    sgp_reads = 0
    stop = False

    async def scd_loop() -> None:
        nonlocal scd_reads
        i = 0
        while not stop:
            try:
                await scd.read_measurement()
                scd_reads += 1
            except Exception as e:
                scd_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            i += 1
            if i % 10 == 0:
                wdt.feed()
            await asyncio.sleep_ms(15)

    async def sgp_loop() -> None:
        nonlocal sgp_reads
        i = 0
        while not stop:
            try:
                raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
                if raw is not None and not (0 <= raw <= 0xFFFF):
                    sgp_errors.append(f"iter {i}: raw={raw!r} outside the 16-bit range - a torn word")
                sgp_reads += 1
            except Exception as e:
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            i += 1
            if i % 10 == 0:
                wdt.feed()
            await asyncio.sleep_ms(15)

    async def writer_loop() -> None:
        nonlocal stop
        for i in range(WRITE_CYCLES):
            delay_ms = _WRITE_DELAYS_MS[i % len(_WRITE_DELAYS_MS)]
            await asyncio.sleep_ms(delay_ms)  # the systematically varied offset for this cycle
            start = time.ticks_ms()
            try:
                await isl.configure(ir_adjust=10 + i)
                write_windows.append((start, time.ticks_ms()))
            except Exception as e:
                write_errors.append(f"iter {i}: delay_ms={delay_ms}: {type(e).__name__}: {e}")
            wdt.feed()
        stop = True

    await asyncio.wait_for(asyncio.gather(scd_loop(), sgp_loop(), writer_loop()), 60.0)

    failures = []
    if scd_errors:
        failures.append(f"{len(scd_errors)} SCD30 read error(s): {'; '.join(scd_errors[:5])}")
    if sgp_errors:
        failures.append(f"{len(sgp_errors)} SGP40 read error(s): {'; '.join(sgp_errors[:5])}")
    if write_errors:
        failures.append(f"{len(write_errors)} ISL29125 configure() error(s): {'; '.join(write_errors[:5])}")
    if len(write_windows) != WRITE_CYCLES:
        failures.append(f"ISL29125 only completed {len(write_windows)}/{WRITE_CYCLES} configure() writes")
    if scd_reads == 0:
        failures.append("SCD30 completed zero reads during the whole run - loop never progressed")
    if sgp_reads == 0:
        failures.append("SGP40 completed zero reads during the whole run - loop never progressed")

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(
            f"RESULT: PASS scd30_reads={scd_reads} sgp40_reads={sgp_reads} "
            f"isl29125_writes={len(write_windows)}/{WRITE_CYCLES} across offsets {_WRITE_DELAYS_MS}ms, "
            "no corruption/errors across either sibling's concurrent read loop while the write loop ran",
        )


asyncio.run(_main())
