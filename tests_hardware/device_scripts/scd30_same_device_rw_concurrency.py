"""Isolated-driver device script, flash-tier: the ONE and only script in this whole bus-hazard test
group allowed to issue a real NVM-persisted write to the SCD30 (`set_ambient_pressure()`, which
doubles as "trigger continuous measurement" - see asy_scd30_driver.py's own comment). Real-hardware
safety constraint, explicit project-owner direction: the SCD30's own on-chip NVM has a real write-
wear budget, so this whole test group must write it "not more than once per test suite run" - every
other real SCD30 setter (measurement interval, temperature offset, altitude, forced recalibration,
self-calibration) is also NVM-persisted per that same file's own comments, so none of them are used
anywhere in this bus-hazard test group either, not just this one.

This single write also directly serves the "same-device concurrency: ongoing read, incoming write"
proof (SPECIFICATION.md Part C.8's device-session lock model) the project owner asked every device
be covered for: a burst of concurrent read_measurement() calls runs while this one write is issued
partway through, and the assertion is the same as every other same-device concurrency test in this
suite - zero exceptions/CRC failures across every read, proving the device-session lock serialized
the write against the in-flight reads rather than corrupting one of them.

Every OTHER flash-tier script that needs SCD30 producing real fresh data (bus_concurrency_cross_
device_scd30_sgp40.py, sgp40_general_call_reset_hazard.py, bus_topology_autodetect_and_hazard_
sweep.py) depends on tests_hardware/flash/conftest.py's own session-scoped
`scd30_continuous_measurement_triggered` fixture, which runs *this* script exactly once per pytest
session and never again - see that fixture's own docstring. Continuous measurement, once triggered,
is real on-chip NVM state that survives every subsequent separate `mpremote run` invocation for the
rest of the session (and beyond, until explicitly stopped or the chip is reset to factory defaults),
which is what makes triggering it exactly once here sufficient for the whole test group.

Uses the raw SCD30_I2C protocol class directly, never SCD30_Reader - no ConfigManager, no RP2040
flash file I/O anywhere in this script (the project owner's second real-hardware caveat: heavy
write/concurrency testing must exercise the real production driver that does the actual bus
arbitration/locking, without touching the RP2040's own persisted config storage). SCD30_I2C *is*
that production driver (the DUT for this whole test group) - SCD30_Reader is the higher config/
FRAM-owning layer this script deliberately never constructs.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import machine

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0

READ_ITERATIONS = 40


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    scd = SCD30_I2C(i2c1)
    await scd.setup()  # a real soft reset - RAM/operating-state only, not an NVM write, safe every run

    read_errors = []
    read_completed = 0
    write_error = None
    write_done = False

    async def reader() -> None:
        nonlocal read_completed
        for i in range(READ_ITERATIONS):
            try:
                await scd.read_measurement()
                co2 = await scd.get_CO2()
                if co2 is not None and not (CO2_MIN_PPM <= co2 <= CO2_MAX_PPM):
                    read_errors.append(f"iter {i}: CO2={co2!r} outside plausible bounds")
                hum = await scd.get_relative_humidity()
                if hum is not None and not (HUMIDITY_MIN_RH <= hum <= HUMIDITY_MAX_RH):
                    read_errors.append(f"iter {i}: Hum={hum!r} outside plausible bounds")
                temp = await scd.get_temperature()
                if temp is not None and not (TEMP_MIN_C <= temp <= TEMP_MAX_C):
                    read_errors.append(f"iter {i}: Temp={temp!r} outside plausible bounds")
            except Exception as e:  # noqa: BLE001 - any exception is itself the corruption signal this script exists to catch
                read_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            read_completed += 1
            if i % 10 == 0:
                wdt.feed()

    async def writer() -> None:
        nonlocal write_error, write_done
        await asyncio.sleep(0.2)  # let the reader get partway into its first few cycles first
        try:
            # THE one NVM write for this whole test group - see this script's own module docstring.
            await scd.set_ambient_pressure(1013)
        except Exception as e:  # noqa: BLE001 - see reader()'s own comment
            write_error = f"{type(e).__name__}: {e}"
        write_done = True

    await asyncio.wait_for(asyncio.gather(reader(), writer()), 60.0)

    failures = []
    if read_completed != READ_ITERATIONS:
        failures.append(f"reader only completed {read_completed}/{READ_ITERATIONS} iterations")
    if not write_done:
        failures.append("the concurrent set_ambient_pressure() write never completed")
    if write_error is not None:
        failures.append(f"set_ambient_pressure() failed: {write_error}")
    failures.extend(read_errors)

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:10])}")
    else:
        print(f"RESULT: PASS reader={read_completed}/{READ_ITERATIONS} concurrent write clean - continuous measurement now triggered for the rest of this session")


asyncio.run(_main())
