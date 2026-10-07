"""Isolated-driver device script: one real BMP3xx reading, checked against datasheet-sourced sane
bounds (300-1250 hPa, -40 to 85 degC - datasheets/bmp3xx/ Table 2). Primes reader.cfgmgr directly
(no real flash I/O) - see tests_hardware/README.md's device-script cfgmgr-priming note."""

import asyncio

import machine

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3xx_Reader

PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 85.0
# @tunable l3.bmp3xx_plausibility_read_poll_s = 0.5
_POLL_S = 0.5


async def _main() -> None:
    # @tunable wdt.timeout_ms = 8000
    wdt = machine.WDT(timeout=8000)  # matches src/system_service.py's own production value
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
    reader = BMP3xx_Reader(i2c0, max_module_error=999)
    # Prime config directly rather than reader.cfgmgr.setup() - no real flash file I/O. Derived from
    # the driver's own schema, so a new field can't leave this reading a default that no longer exists.
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {field[0]: field[2] for field in reader.cfg_schema if field[2] is not None}
    reader.start_timer()  # wires the real 1s hardware timer driving _base_trigger()
    trigger_task = reader.start_asy_trigger()
    read_task = reader.start_asy_read()

    data = None
    # ~15s worst case exceeds the 8.388s hardware WDT ceiling; soft-reset doesn't reset that timer,
    # so this script feeds it manually rather than relying on anything outside itself.
    for _ in range(30):  # ~15s at 0.5s polling - generous relative to a forced-mode conversion's own <=~130ms
        data = await reader.get_data()
        if data.Pres is not None:
            break
        wdt.feed()
        await asyncio.sleep(_POLL_S)

    died: list[str] = []
    for task in (trigger_task, read_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:  # a task that died on its own fails the run, never passes it
            died.append(repr(e))
    if died:
        print(f"RESULT: FAIL a background task died: {'; '.join(died)}")
        return

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
