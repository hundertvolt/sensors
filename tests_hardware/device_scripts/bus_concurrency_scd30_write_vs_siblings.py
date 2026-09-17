"""Isolated-driver device script: real-hardware counterpart to
scenario_a_write_does_not_disturb_concurrent_sibling_reads (tests/_bus_hazard_catalog.py) for the
ONE case bus_concurrency_isl29125_write_vs_siblings.py deliberately doesn't cover - SCD30 itself as
the writer. SCD30's own NVM-persisted write (set_temperature_offset(), same shape as
scd30_same_device_rw_concurrency.py's set_ambient_pressure()) has a real write-wear budget, so this
script is NOT part of the routine flash-tier bus-hazard group - it is its own separate, explicitly
opt-in extra real write, AND-gated behind BOTH tests_hardware/conftest.py's --allow-persistence-writes
(the global "any real SCD30 write at all" permission) AND --allow-scd30-extra-write (this one extra
write specifically - see @pytest.mark.persistence_write/@pytest.mark.scd30_extra_write on the test that
wraps this script). Fires exactly ONCE per invocation, and must never be folded into the group's own
one-routine-write budget already spent by scd30_continuous_measurement_triggered.

Unlike bus_concurrency_isl29125_write_vs_siblings.py's own deliberately varied multi-offset sweep,
this fires at exactly ONE fixed, deliberately-chosen offset (0.3s in - both siblings well into their
own read loops, neither at the very first transaction) - the one-write budget makes a real sweep
across several distinct timings structurally impossible here, not a design choice to skip it. This
is the honest tradeoff the SCD30 write-budget restriction imposes, not something to silently omit."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

_MODE_RGB = 0x05


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    scd = SCD30_I2C(i2c1)
    isl = ISL29125_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    await scd.setup()  # real soft reset only - continuous measurement already active from the session fixture, no second set_ambient_pressure() call here
    await isl.setup()
    await isl.configure(mode=_MODE_RGB, range_fs=10000, resolution=16, threshold_interrupt=False)
    await sgp.setup()

    isl_windows = []  # (start_ms, end_ms) per completed read_counts()
    sgp_reads = 0
    isl_errors = []
    sgp_errors = []
    write_error = None
    write_done = False
    write_window = None
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
            await asyncio.sleep_ms(15)

    async def sgp_loop() -> None:
        nonlocal sgp_reads
        i = 0
        while not stop:
            try:
                await sgp.measure_raw(temperature=25, relative_humidity=50)
                sgp_reads += 1
            except Exception as e:
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            i += 1
            if i % 10 == 0:
                wdt.feed()
            await asyncio.sleep_ms(15)

    async def writer_loop() -> None:
        nonlocal write_error, write_done, write_window, stop
        await asyncio.sleep(0.3)  # let both siblings get real cycles running first
        start = time.ticks_ms()
        try:
            # THE one extra real NVM write this script makes - see its own module docstring. Fires
            # exactly once; this script must never be called more than once per opt-in run.
            await scd.set_temperature_offset(4.0)
            write_window = (start, time.ticks_ms())
        except Exception as e:
            write_error = f"{type(e).__name__}: {e}"
        write_done = True
        await asyncio.sleep(1.0)  # keep both siblings running a little longer after the write too
        stop = True

    await asyncio.wait_for(asyncio.gather(isl_loop(), sgp_loop(), writer_loop()), 60.0)

    failures = []
    if isl_errors:
        failures.append(f"{len(isl_errors)} ISL29125 read error(s): {'; '.join(isl_errors[:5])}")
    if sgp_errors:
        failures.append(f"{len(sgp_errors)} SGP40 read error(s): {'; '.join(sgp_errors[:5])}")
    if not write_done:
        failures.append("the concurrent set_temperature_offset() write never completed")
    if write_error is not None:
        failures.append(f"set_temperature_offset() failed: {write_error}")
    if not isl_windows:
        failures.append("ISL29125 completed zero reads during the whole run - loop never progressed")
    if sgp_reads == 0:
        failures.append("SGP40 completed zero reads during the whole run - loop never progressed")

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:10])}")
    else:
        print(f"RESULT: PASS isl29125_reads={len(isl_windows)} sgp40_reads={sgp_reads} write_window={write_window} - the one SCD30 write landed cleanly alongside both siblings' concurrent reads")


asyncio.run(_main())
