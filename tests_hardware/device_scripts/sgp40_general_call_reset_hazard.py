"""Isolated-driver device script: real-hardware regression test for the SGP40 general-call reset
hazard (SPECIFICATION.md Part C.8) - runs concurrent SCD30 reads against repeated SGP40
initialize() cycles and checks for CRC/OSError corruption plus measurement still advancing."""

import asyncio

import machine

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0

SGP40_RESET_CYCLES = 8


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
    await sgp.setup()

    scd_errors = []
    scd_completed = 0
    distinct_co2_values = set()
    stop = False

    async def scd_loop() -> None:
        nonlocal scd_completed
        i = 0
        while not stop:
            try:
                await scd.read_measurement()
                co2 = await scd.get_CO2()
                hum = await scd.get_relative_humidity()
                temp = await scd.get_temperature()
                if co2 is not None:
                    if not (CO2_MIN_PPM <= co2 <= CO2_MAX_PPM):
                        scd_errors.append(f"iter {i}: CO2={co2!r} outside plausible bounds")
                    distinct_co2_values.add(co2)
                if hum is not None and not (HUMIDITY_MIN_RH <= hum <= HUMIDITY_MAX_RH):
                    scd_errors.append(f"iter {i}: Hum={hum!r} outside plausible bounds")
                if temp is not None and not (TEMP_MIN_C <= temp <= TEMP_MAX_C):
                    scd_errors.append(f"iter {i}: Temp={temp!r} outside plausible bounds")
            except Exception as e:  # noqa: BLE001 - any exception is itself the corruption signal this script exists to catch
                scd_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            scd_completed += 1
            i += 1
            if i % 10 == 0:
                wdt.feed()

    sgp_errors = []
    sgp_completed = 0

    async def sgp_reset_loop() -> None:
        nonlocal stop, sgp_completed
        for i in range(SGP40_RESET_CYCLES):
            try:
                await sgp.initialize()  # real production path: ends with _reset()'s general-call broadcast
                sgp_completed += 1
            except Exception as e:  # noqa: BLE001 - SGP40's own init failing is worth surfacing too, though not this script's main question
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            wdt.feed()
        stop = True

    await asyncio.wait_for(asyncio.gather(scd_loop(), sgp_reset_loop()), 90.0)

    failures = []
    if sgp_completed != SGP40_RESET_CYCLES:
        failures.append(f"SGP40 only completed {sgp_completed}/{SGP40_RESET_CYCLES} reset cycles: {'; '.join(sgp_errors[:5])}")
    if scd_completed == 0:
        failures.append("SCD30 completed zero read cycles during the whole run - loop never progressed")
    failures.extend(scd_errors[:10])
    # The run spans several SCD30 measurement intervals, so genuinely advancing measurement should
    # produce >= 2 distinct CO2 values; a single unchanging value signals it silently stopped
    # advancing (e.g. an undocumented general-call reset) - not caught by a CRC failure alone, since
    # that only catches corruption of a transaction already in flight.
    if len(distinct_co2_values) < 2:
        failures.append(
            f"only {len(distinct_co2_values)} distinct CO2 value(s) seen across {scd_completed} reads over "
            f"{sgp_completed} SGP40 reset cycles - continuous measurement may have silently stopped advancing"
        )

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(
            f"RESULT: PASS scd30_reads={scd_completed} sgp40_reset_cycles={sgp_completed} "
            f"distinct_co2_values={len(distinct_co2_values)} - zero corruption/errors, measurement kept advancing"
        )


asyncio.run(_main())
