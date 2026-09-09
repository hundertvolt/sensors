"""Isolated-driver device script: the ONE script in this test group allowed to issue a real
NVM-persisted write to the SCD30 (set_ambient_pressure(), doubling as "trigger continuous
measurement" - real write-wear budget). Also serves the same-device concurrency proof
(SPECIFICATION.md Part C.8) - see tests_hardware/flash/conftest.py's session-scoped fixture."""

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
