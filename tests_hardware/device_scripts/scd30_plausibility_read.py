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
This bench unit wires SCD30 to I2C1 (scl=15, sda=14) with IRQ/RDY on GPIO11, not I2C0/GPIO8 -
dev_legacy/README.md's own wiring table (wozi's deployed wiring puts SCD30 on I2C0/GPIO8 instead;
this bench moved it to I2C1 alongside SGP40). Confirmed directly against this bench's own live
main.py (build_system()) and a real i2c.scan() (0x61 on I2C1(15,14), nothing on I2C0(13,12) besides
BMP3xx/MPRLS) before fixing this script's earlier wrong assumption that it was exercising "the real
production wiring" - it wasn't; it was silently probing the wrong bus on this specific unit. The
`frequency=50000, timeout=200000` values themselves are unaffected by this fix (same on both buses,
per asy_i2c_driver.I2C's own construction and this bench's main.py).

Correction (see this session's own history): an earlier draft of this script polled get_data()
without ever starting read_loop()/scd_init_irq()/the IRQ timer - get_data() only ever returns
whatever _store_scd() last wrote via _set_meas_data(), which only ever happens from inside
read_loop() (base_classes.py's SensorReader._get_meas_data()/_set_meas_data(), confirmed by reading
both files directly), so that draft could only ever have printed FAIL, never a real reading. Fixed
by actually starting the reader's real task graph (start_timer() + read_loop() + scd_init_irq(), the
same three calls sensortask_wozi.py's own get_task_starters()/get_timer_starters() wiring makes)
before polling.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

CO2_MIN_PPM, CO2_MAX_PPM = 400, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0


async def _main() -> None:
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    reader = SCD30_Reader(i2c1, 11, trigger_sec=3, max_module_error=999, fram=None, debug=None)
    reader.start_timer()  # wires the real GPIO IRQ + the 500ms self-healing poll timer
    read_task = asyncio.create_task(reader.read_loop())
    init_irq_task = asyncio.create_task(reader.scd_init_irq())

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
