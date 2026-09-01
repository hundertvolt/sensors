"""Isolated-driver device script, flash-tier gap fix: one real BMP3xx reading, checked against
datasheet-sourced sane bounds (plausibility only, not exact reference - same convention as
scd30_plausibility_read.py). Bounds sourced from datasheets/bmp3xx/ (BST-BMP388-DS001/
BST-BMP384-DS003) Table 2's operating range: pressure 300-1250 hPa, temperature -40-85 degC -
also src/asy_bmp3xx_driver.py's own BMP3XX_I2C._read() already rejects a reading outside this
same range (ValueError), so a successful real read is redundantly checked here as independent
evidence, not because the driver could plausibly hand back an out-of-range value. SLPres
(math_helpers.altitude_baro(), sea-level-corrected pressure - despite the function's own name
being about altitude, it reduces station pressure to sea level, not the other way around; see
that function's own comment) uses the same 300-1250 hPa bound: loose/plausible, not exact.

This bench unit wires BMP3xx to I2C0 (scl=13, sda=12), not I2C1 (dev_legacy/README.md's own
wiring table - this bench's BMP3xx is on I2C0 alongside MPRLS, while wozi's deployed wiring puts
it on I2C1 instead). Confirmed directly against this bench's own live main.py (build_system())
and a real i2c.scan() (0x77 on I2C0, nothing on I2C1(19,18)) before fixing this script's earlier
wrong assumption that it was exercising "the real production wiring" - it wasn't; it was silently
probing an empty bus on this specific unit.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3xx_Reader

PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 85.0


async def _main() -> None:
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
    reader = BMP3xx_Reader(i2c0, max_module_error=999, fram=None, debug=None)
    reader.start_timer()  # wires the real 1s hardware timer driving _base_trigger()
    trigger_task = reader.start_asy_trigger()
    read_task = reader.start_asy_read()

    data = None
    for _ in range(30):  # ~15s at 0.5s polling - generous relative to a forced-mode conversion's own <=~130ms
        data = await reader.get_data()
        if data.Pres is not None:
            break
        await asyncio.sleep(0.5)

    for task in (trigger_task, read_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 - CancelledError (real hardware confirmed: MicroPython's, like CPython's, subclasses BaseException, not Exception - SPECIFICATION.md Part F.2) or whatever the loop itself raised, not this script's concern once we have our own answer above
            pass

    if data is None or data.Pres is None:
        print("RESULT: FAIL no pressure reading obtained within the wait window - sensor not responding or not wired to i2c0")
        return

    failures = []
    if not (PRESSURE_MIN_HPA <= data.Pres <= PRESSURE_MAX_HPA):
        failures.append(f"Pres={data.Pres!r} outside [{PRESSURE_MIN_HPA}, {PRESSURE_MAX_HPA}] hPa")
    if data.Temp is not None and not (TEMP_MIN_C <= data.Temp <= TEMP_MAX_C):
        failures.append(f"Temp={data.Temp!r} outside [{TEMP_MIN_C}, {TEMP_MAX_C}] degC")
    if data.SLPres is not None and not (PRESSURE_MIN_HPA <= data.SLPres <= PRESSURE_MAX_HPA):
        failures.append(f"SLPres={data.SLPres!r} outside [{PRESSURE_MIN_HPA}, {PRESSURE_MAX_HPA}] hPa")

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS Pres={data.Pres} Temp={data.Temp} SLPres={data.SLPres}")


asyncio.run(_main())
