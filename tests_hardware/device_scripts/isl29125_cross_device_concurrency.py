"""Isolated-driver device script: proves the ISL29125 genuinely interleaves with the two devices it
shares I2C1 with on the dev bench (SGP40's long initialize() window and SCD30's own reads) rather
than serializing behind either - CLAUDE.md's standing cross-device requirement for a new bus device,
real-hardware tier. Counts ISL reads completing strictly inside an SGP40 device-session window."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

SGP40_CYCLES = 6
_MODE_RGB = 0x05


def _failures(isl_errors: "list[str]", scd_errors: "list[str]", sgp_errors: "list[str]", isl_reads: int, scd_reads: int, sgp_cycles: int, interleaved: int) -> "list[str]":
    failures: list[str] = []
    if isl_errors:
        failures.append(f"{len(isl_errors)} ISL29125 read error(s): {'; '.join(isl_errors[:5])}")
    if scd_errors:
        failures.append(f"{len(scd_errors)} SCD30 read error(s): {'; '.join(scd_errors[:5])}")
    if sgp_errors:
        failures.append(f"{len(sgp_errors)} SGP40 initialize error(s): {'; '.join(sgp_errors[:5])}")
    if sgp_cycles != SGP40_CYCLES:
        failures.append(f"SGP40 only completed {sgp_cycles}/{SGP40_CYCLES} cycles")
    if isl_reads == 0:
        failures.append("ISL29125 completed zero reads during the whole run - loop never progressed")
    if scd_reads == 0:
        failures.append("SCD30 completed zero reads - the third device never got the bus (or continuous measurement was never triggered)")
    if interleaved == 0:
        failures.append(
            "zero ISL29125 reads completed inside any SGP40 initialize() window - the new device is "
            "serializing behind its neighbour rather than interleaving (possible regression: bus "
            "lock held across the whole device session, or device-session locks accidentally shared)",
        )
    return failures


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    isl = ISL29125_I2C(i2c1)
    scd = SCD30_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    await isl.setup()
    await isl.configure(mode=_MODE_RGB, range_fs=10000, resolution=16, int_select=0)
    await scd.setup()  # no set_ambient_pressure() - that is the one NVM write this group makes, via the session fixture
    await sgp.setup()

    isl_windows = []  # (start_ms, end_ms) per completed read_counts()
    sgp_windows = []  # (start_ms, end_ms) per completed initialize()
    isl_errors: list[str] = []
    scd_errors: list[str] = []
    sgp_errors: list[str] = []
    scd_reads = 0
    stop = False

    async def isl_loop() -> None:
        i = 0
        while not stop:
            start = time.ticks_ms()
            try:
                green, red, blue = await isl.read_counts()
                if not all(0 <= channel <= 0xFFFF for channel in (green, red, blue)):
                    isl_errors.append(f"iter {i}: counts=({green}, {red}, {blue}) outside the 16-bit range - a torn burst")
                isl_windows.append((start, time.ticks_ms()))
            except Exception as e:
                isl_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            i += 1
            if i % 10 == 0:
                wdt.feed()
            await asyncio.sleep_ms(20)

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
            await asyncio.sleep_ms(20)

    async def sgp_loop() -> None:
        nonlocal stop
        for i in range(SGP40_CYCLES):
            start = time.ticks_ms()
            try:
                await sgp.initialize()
                sgp_windows.append((start, time.ticks_ms()))
            except Exception as e:
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            wdt.feed()
        stop = True

    await asyncio.wait_for(asyncio.gather(isl_loop(), scd_loop(), sgp_loop()), 60.0)

    # An ISL read that both starts and finishes strictly inside an SGP40 device-session window
    # proves its whole bus transaction ran while that session was still open.
    interleaved_total = 0
    windows_with_interleaving = 0
    for sgp_start, sgp_end in sgp_windows:
        count = sum(1 for s, e in isl_windows if time.ticks_diff(s, sgp_start) >= 0 and time.ticks_diff(e, sgp_end) <= 0)
        interleaved_total += count
        if count > 0:
            windows_with_interleaving += 1
    failures = _failures(isl_errors, scd_errors, sgp_errors, len(isl_windows), scd_reads, len(sgp_windows), interleaved_total)

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(
            f"RESULT: PASS isl_reads={len(isl_windows)} scd30_reads={scd_reads} sgp40_cycles={len(sgp_windows)} "
            f"interleaved_completions={interleaved_total} windows_with_interleaving={windows_with_interleaving}/{len(sgp_windows)}",
        )


asyncio.run(_main())
