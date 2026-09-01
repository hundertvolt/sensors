"""Isolated-driver device script for flash-tier candidate F.21: one real SCD30 reading, checked
against datasheet-sourced sane bounds (plausibility only, not an exact reference - see Part 2 item
9's manual reference-calibrated variant for that). Bounds sourced directly from
datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Datasheet.pdf Tables 1-3, not assumed from memory:
  CO2:      measurement range 400-10'000 ppm (Table 1)
  Humidity: measurement range 0-100 %RH (Table 2)
  Temperature: measurement range -40-70 degC (Table 3) - the sensor's own *measurement* range, not
              its 0-50 degC *accuracy-specified* range, since a real bench/office environment is
              expected to sit well inside the accuracy range anyway and this check is deliberately
              loose (plausibility, not precision).
Uses the exact same i2c0 construction sensortask_wozi.py's build_system() uses (frequency=50000,
timeout=200000 - see that file's own comment for why), so this exercises the real production wiring,
not an arbitrary one. Run via `mpremote run <this> soft-reset`."""

import asyncio

import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

CO2_MIN_PPM, CO2_MAX_PPM = 400, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0


async def _main() -> None:
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000, timeout=200000)
    reader = SCD30_Reader(i2c0, 8, trigger_sec=3, max_module_error=999, fram=None, debug=None)
    # A real SCD30 needs time after power-up before its first measurement is ready - trigger_sec=3
    # matches production; give it a few cycles' worth of headroom rather than reading immediately.
    # get_data() -> the SCD30 namedtuple (CO2, Temp, Hum, WetBulb, DewPoint, TS) - see
    # asy_scd30_driver.py's own `SCD30 = namedtuple(...)` definition; field names are capitalized,
    # not the lowercase attribute names a first guess from the datasheet's own prose might suggest.
    data = None
    for _ in range(30):  # ~15s at 0.5s polling - generous relative to the sensor's own ~2s default interval
        data = await reader.get_data()
        if data.CO2 is not None:
            break
        await asyncio.sleep(0.5)

    if data is None or data.CO2 is None:
        print("RESULT: FAIL no CO2 reading obtained within the wait window - sensor not responding or not wired to i2c0")
        return

    failures = []
    if not (CO2_MIN_PPM <= data.CO2 <= CO2_MAX_PPM):
        failures.append(f"CO2={data.CO2!r} outside [{CO2_MIN_PPM}, {CO2_MAX_PPM}] ppm")
    if data.Hum is not None and not (HUMIDITY_MIN_RH <= data.Hum <= HUMIDITY_MAX_RH):
        failures.append(f"Hum={data.Hum!r} outside [{HUMIDITY_MIN_RH}, {HUMIDITY_MAX_RH}] %RH")
    if data.Temp is not None and not (TEMP_MIN_C <= data.Temp <= TEMP_MAX_C):
        failures.append(f"Temp={data.Temp!r} outside [{TEMP_MIN_C}, {TEMP_MAX_C}] degC")

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS CO2={data.CO2} Hum={data.Hum} Temp={data.Temp}")


asyncio.run(_main())
