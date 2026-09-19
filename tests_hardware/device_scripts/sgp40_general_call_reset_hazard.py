"""Isolated-driver device script: real-hardware regression test for the SGP40 general-call reset
hazard (SPECIFICATION.md Part C.8) - concurrent SCD30 AND ISL29125 reads against repeated SGP40
initialize() cycles, checking for CRC/OSError corruption and that measurements still advance."""

import asyncio

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0

SGP40_RESET_CYCLES = 8


def _failures(scd_errors: "list[str]", isl_errors: "list[str]", sgp_errors: "list[str]", scd_completed: int, isl_completed: int, sgp_completed: int, distinct_co2_values: "set[float]") -> "list[str]":
    failures: list[str] = []
    if sgp_completed != SGP40_RESET_CYCLES:
        failures.append(f"SGP40 only completed {sgp_completed}/{SGP40_RESET_CYCLES} reset cycles: {'; '.join(sgp_errors[:5])}")
    if scd_completed == 0:
        failures.append("SCD30 completed zero read cycles during the whole run - loop never progressed")
    if isl_completed == 0:
        failures.append("ISL29125 completed zero read cycles during the whole run - loop never progressed")
    failures.extend(scd_errors[:10])
    failures.extend(isl_errors[:10])
    # The run spans several SCD30 measurement intervals, so advancing measurement means >= 2
    # distinct CO2 values; one unchanging value means it silently stopped (an undocumented
    # general-call reset). A CRC failure cannot catch this - it only sees a transaction in flight.
    if len(distinct_co2_values) < 2:
        failures.append(
            f"only {len(distinct_co2_values)} distinct CO2 value(s) seen across {scd_completed} reads over "
            f"{sgp_completed} SGP40 reset cycles - continuous measurement may have silently stopped advancing",
        )
    return failures


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    scd = SCD30_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    isl = ISL29125_I2C(i2c1)
    await scd.setup()
    # No set_ambient_pressure() here: this group's one NVM-persisted write happens once per
    # session in flash/conftest.py's scd30_continuous_measurement_triggered fixture, which this
    # test depends on. scd30_same_device_rw_concurrency.py's docstring has the wear reasoning.
    await sgp.setup()
    await isl.setup()
    await isl.configure(mode=0x05, range_fs=10000, resolution=16, threshold_interrupt=False)

    scd_errors = []
    scd_completed = 0
    distinct_co2_values = set()
    isl_errors = []
    isl_completed = 0
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
            except Exception as e:
                scd_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            scd_completed += 1
            i += 1
            if i % 10 == 0:
                wdt.feed()

    async def isl_loop() -> None:
        nonlocal isl_completed
        i = 0
        while not stop:
            try:
                green, red, blue = await isl.read_counts()
                if not all(0 <= channel <= 0xFFFF for channel in (green, red, blue)):
                    isl_errors.append(f"iter {i}: counts=({green}, {red}, {blue}) outside the 16-bit range - a torn burst")
            except Exception as e:
                isl_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            isl_completed += 1
            i += 1
            if i % 10 == 0:
                wdt.feed()
            await asyncio.sleep_ms(15)

    sgp_errors = []
    sgp_completed = 0

    async def sgp_reset_loop() -> None:
        nonlocal stop, sgp_completed
        for i in range(SGP40_RESET_CYCLES):
            try:
                await sgp.initialize()  # real production path: ends with _reset()'s general-call broadcast
                sgp_completed += 1
            except Exception as e:
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            wdt.feed()
        stop = True

    await asyncio.wait_for(asyncio.gather(scd_loop(), isl_loop(), sgp_reset_loop()), 90.0)

    failures = _failures(scd_errors, isl_errors, sgp_errors, scd_completed, isl_completed, sgp_completed, distinct_co2_values)

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(
            f"RESULT: PASS scd30_reads={scd_completed} isl29125_reads={isl_completed} sgp40_reset_cycles={sgp_completed} "
            f"distinct_co2_values={len(distinct_co2_values)} - zero corruption/errors, measurement kept advancing",
        )


asyncio.run(_main())
