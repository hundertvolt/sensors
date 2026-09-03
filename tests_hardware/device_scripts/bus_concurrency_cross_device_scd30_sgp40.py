"""Isolated-driver device script, flash-tier: proves two DIFFERENT devices sharing one physical I2C
bus (SCD30 + SGP40 on I2C1 on this dev bench - see sensortask_dev.py's own wiring comment: "i2c1
(15, 14) carries SCD30 + SGP40, sharing the bus") genuinely interleave under concurrent access rather
than fully serializing one behind the other - the real-hardware counterpart to SPECIFICATION.md
Part C.8's documented bus-lock-is-per-transaction-not-per-sequence design. Closes the gap that no
existing test (mock or real-hardware) proves the fine-grained bus lock actually allows this, only
that it doesn't crash.

Mechanism: SGP40_I2C.initialize() (src/asy_sgp40_driver.py) runs a serial-number read (~3ms delay),
a self-test (~500ms delay), then a soft reset (~1000ms delay) - each of those three steps only holds
the shared bus lock (I2C.async_lock) for the single short bus transaction itself; the long
delay_ms/await asyncio.sleep() windows in between run with the bus lock fully released (only SGP40's
OWN independent device-session lock, i2c_sgp40, is held across the whole call). SCD30's own
read_measurement() calls are gated by a completely independent device-session lock (i2c_scd30), so
if the bus-level locking is working as designed, several SCD30 read_measurement() calls should be
able to run to completion *during* SGP40's long self-test/reset sleep windows. If a regression ever
widened SGP40's bus-lock hold to span its whole initialize() call (or merged the two device-session
locks), SCD30 would be shut out for the full ~1.5s of every SGP40 cycle instead - this script proves
that isn't happening by recording wall-clock start/end timestamps for both sides (single-threaded
cooperative asyncio - safe to append to shared lists with no extra locking) and checking how many
SCD30 reads actually landed fully inside an SGP40 window.

This is a genuine interleaving proof (timing-based), not just a "nothing crashed" check - see
bus_concurrency_same_device_scd30.py for the complementary same-device serialization proof (CRC-
failure-based, since same-device interleaving is a correctness hazard, not a speed one).

Run via `mpremote run <this> soft-reset`."""

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
        count = sum(1 for s, e in scd_windows if s >= sgp_start and e <= sgp_end)
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
