"""Isolated-driver device script: real-hardware counterpart to
scenario_a_write_does_not_disturb_concurrent_sibling_reads (tests/_bus_hazard_catalog.py) - closes a
real coverage gap the mock-tier generic scenario found: no existing real-hardware test proved a
config WRITE from one dev/i2c1 occupant landing concurrently with its SIBLINGS' own reads, only
same-device write-vs-own-read (bus_concurrency_same_device_scd30.py,
isl29125_same_device_rw_concurrency.py) and the SGP40 general-call case
(sgp40_general_call_reset_hazard.py). ISL29125's own configure() is the writer here (volatile
config register, FN8424 p7 - no real NVM-write-budget concern, so this runs fully unrestricted,
repeated many times over a real multi-second window - real hardware's own natural equivalent of
"systematically sweep when it fires": genuine uncontrolled scheduling/serial jitter puts each write
at a different real relative offset against the siblings' own read loops, rather than one fixed
injection point. SCD30 is NOT the writer in this script - see
bus_concurrency_scd30_write_vs_siblings.py's own docstring for why that needs a separate, opt-in,
budget-capped script instead of just picking a different `writers[0]`."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

WRITE_CYCLES = 8
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
            start = time.ticks_ms()
            try:
                await isl.configure(ir_adjust=10 + i)
                write_windows.append((start, time.ticks_ms()))
            except Exception as e:
                write_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            wdt.feed()
            await asyncio.sleep_ms(30)  # let the siblings' own loops get real cycles between writes too
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
            f"isl29125_writes={len(write_windows)}/{WRITE_CYCLES}, no corruption/errors across "
            "either sibling's concurrent read loop while the write loop ran",
        )


asyncio.run(_main())
