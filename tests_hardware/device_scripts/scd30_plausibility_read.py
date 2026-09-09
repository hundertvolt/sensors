"""Isolated-driver device script: one real SCD30 reading checked against datasheet-sourced sane
bounds (CO2 200-10000 ppm, below the datasheet's 400 floor since sub-400 readings are real and
unremarkable; Hum 0-100%RH; Temp -40-70 degC). Discards readings during the post-reset settle window (tau63% >10s)."""

import asyncio

import machine

import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0
_SETTLE_S = 45.0  # datasheet-bound response-time window (see docstring) plus margin


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)  # matches src/system_service.py's own production value
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    reader = SCD30_Reader(i2c1, 11, trigger_sec=3, max_module_error=999, fram=None, debug=None)
    reader.start_timer()  # wires the real GPIO IRQ + the 500ms self-healing poll timer
    read_task = asyncio.create_task(reader.read_loop())
    init_irq_task = asyncio.create_task(reader.scd_init_irq())

    # Let the sensor's own post-reset response-time settle (see module docstring) before trusting
    # any reading - readings seen during this window are deliberately discarded.
    for _ in range(int(_SETTLE_S / 0.5)):
        wdt.feed()
        await asyncio.sleep(0.5)

    # get_data() -> the SCD30 namedtuple (CO2, Temp, Hum, WetBulb, DewPoint, TS) - see
    # asy_scd30_driver.py's own `SCD30 = namedtuple(...)` definition; field names are capitalized,
    # not the lowercase attribute names a first guess from the datasheet's own prose might suggest.
    data = None
    for _ in range(30):  # ~15s at 0.5s polling - generous relative to the sensor's own ~2s default interval
        data = await reader.get_data()
        if data.CO2 is not None:
            break
        wdt.feed()
        await asyncio.sleep(0.5)

    read_task.cancel()
    init_irq_task.cancel()
    for task in (read_task, init_irq_task):
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 - CancelledError (real hardware confirmed: MicroPython's, like CPython's, subclasses BaseException, not Exception - SPECIFICATION.md Part F.2) or whatever the loop itself raised, not this script's concern once we have our own answer above
            pass

    if data is None or data.CO2 is None:
        print("RESULT: FAIL no CO2 reading obtained within the wait window - sensor not responding or not wired to i2c1")
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
