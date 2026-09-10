"""Isolated-driver device script: proves SCD30+SGP40, sharing one physical I2C bus (I2C1 on this dev
bench), genuinely interleave rather than serialize - real-hardware counterpart to SPECIFICATION.md
Part C.8's bus-lock-is-per-transaction model. Timing-based: checks SCD30 reads landing inside an SGP40 window."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

SGP40_CYCLES = 6


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    scd = SCD30_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    await scd.setup()
    # Deliberately never calls set_ambient_pressure() here - see
    # scd30_same_device_rw_concurrency.py's own docstring for the one NVM-persisted write this
    # whole test group makes, exactly once per session, via tests_hardware/flash/conftest.py's
    # scd30_continuous_measurement_triggered fixture (which this test depends on).
    await sgp.setup()  # includes one initialize() call already - fine, just warms things up

    scd_windows = []  # (start_ms, end_ms) for each completed read_measurement()
    sgp_windows = []  # (start_ms, end_ms) for each completed initialize()
    scd_errors = []
    sgp_errors = []
    stop = False

    async def scd_loop() -> None:
        i = 0
        while not stop:
            start = time.ticks_ms()
            try:
                await scd.read_measurement()
                scd_windows.append((start, time.ticks_ms()))
            except Exception as e:  # noqa: BLE001 - a real bus fault here is itself worth surfacing
                scd_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            i += 1
            if i % 10 == 0:
                wdt.feed()

    async def sgp_loop() -> None:
        nonlocal stop
        for i in range(SGP40_CYCLES):
            start = time.ticks_ms()
            try:
                await sgp.initialize()
                sgp_windows.append((start, time.ticks_ms()))
            except Exception as e:  # noqa: BLE001 - see scd_loop()'s own comment
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            wdt.feed()
        stop = True

    await asyncio.wait_for(asyncio.gather(scd_loop(), sgp_loop()), 60.0)

    # For each completed SGP40 window, count SCD30 reads that both started and finished strictly
    # inside it - proof those reads' whole bus transaction ran while SGP40's device-session was
    # still open (blocked out only if the two never actually interleave).
    interleaved_total = 0
    windows_with_interleaving = 0
    for sgp_start, sgp_end in sgp_windows:
        # Ticks values wrap around - raw >=/<= comparison is unsafe across that boundary, hence
        # ticks_diff() (same convention every other timing check in this test tier already uses).
        count = sum(1 for s, e in scd_windows if time.ticks_diff(s, sgp_start) >= 0 and time.ticks_diff(sgp_end, e) >= 0)
        interleaved_total += count
        if count > 0:
            windows_with_interleaving += 1

    failures = []
    if scd_errors:
        failures.append(f"{len(scd_errors)} SCD30 read error(s): {'; '.join(scd_errors[:5])}")
    if sgp_errors:
        failures.append(f"{len(sgp_errors)} SGP40 initialize error(s): {'; '.join(sgp_errors[:5])}")
    if len(sgp_windows) != SGP40_CYCLES:
        failures.append(f"SGP40 only completed {len(sgp_windows)}/{SGP40_CYCLES} cycles")
    if not scd_windows:
        failures.append("SCD30 completed zero reads during the whole run - loop never progressed")
    if interleaved_total == 0:
        failures.append(
            "zero SCD30 reads completed inside any SGP40 initialize() window - bus/device-session "
            "locking is not allowing cross-device interleaving (possible regression: bus lock held "
            "too broadly, or device-session locks accidentally shared)"
        )
    elif interleaved_total < len(sgp_windows):
        failures.append(
            f"only {interleaved_total} interleaved SCD30 completions across {len(sgp_windows)} SGP40 "
            "windows - less interleaving than expected, worth a closer look even though not zero"
        )

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(
            f"RESULT: PASS scd30_reads={len(scd_windows)} sgp40_cycles={len(sgp_windows)} "
            f"interleaved_completions={interleaved_total} windows_with_interleaving={windows_with_interleaving}/{len(sgp_windows)}"
        )


asyncio.run(_main())
