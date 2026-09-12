"""Isolated-driver device script: one real ISL29125 reading, checked against datasheet-sourced
sane bounds (FN8424 p1's own 0.0057-10000 lx span, 0-1 normalised RGB/HSB, McCamy's 2000-12500 K).
Primes reader.cfgmgr directly (no real flash I/O) - see tests_hardware/README.md's priming note."""

import asyncio

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_Reader

LUX_MIN, LUX_MAX = 0.0, 10000.0  # p1's own feature list: range 1 reaches 10000 lx
CCT_MIN_K, CCT_MAX_K = 2000.0, 12500.0  # McCamy (1992)'s own usable span
ROOM_LIGHT_MIN_LUX = 5.0  # a lit bench; below this the rig is in the dark, not the driver failing


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)  # matches src/system_service.py's own production value
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    reader = ISL29125_Reader(i2c1, 6, max_module_error=999, fram=None, debug=None)
    # Prime config directly rather than reader.cfgmgr.setup() - no real flash file I/O. Defaults
    # straight from asy_isl29125_driver.py's own _VAL_* schema entries.
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {
        "SampleInterv": 1, "Resolution": 16, "RangeAuto": True, "Range": 10000,
        "AutoRangeUp": 85.0, "AutoRangeDown": 1.5, "AutoRangeSettle": 1,
        "AutoRangePersist": 4, "AutoRangeDwell": 10.0,
        "IrCompOffset": 0, "IrCompAdjust": 40, "FiltCoeff": -1.0,
    }
    reader.start_timer()  # wires the real 1s hardware timer and the falling-edge INT handler
    trigger_task = reader.start_asy_trigger()
    read_task = reader.start_asy_read()

    data = None
    # One RGB cycle is ~303 ms at 16 bit, so this window is generous; ~15s worst case exceeds the
    # 8.388s hardware WDT ceiling, so this script feeds it rather than relying on anything else.
    for _ in range(30):
        data = await reader.get_data()
        if data.Lux is not None:
            break
        wdt.feed()
        await asyncio.sleep(0.5)

    for task in (trigger_task, read_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    if data is None or data.Lux is None:
        print("RESULT: FAIL no reading obtained within the wait window - sensor not responding or not wired to i2c1")
        return

    failures = []
    if not (LUX_MIN <= data.Lux <= LUX_MAX):
        failures.append(f"Lux={data.Lux!r} outside [{LUX_MIN}, {LUX_MAX}]")
    if data.Lux < ROOM_LIGHT_MIN_LUX:
        failures.append(f"Lux={data.Lux!r} below {ROOM_LIGHT_MIN_LUX} - is the sensor covered, or the bench dark?")
    for name, value in (("R", data.Red), ("G", data.Green), ("B", data.Blue), ("Sat", data.Sat), ("Bri", data.Bri)):
        if value is None or not (0.0 <= value <= 1.0):
            failures.append(f"{name}={value!r} outside the normalised 0-1 range")
    if data.Hue is None or not (0.0 <= data.Hue < 360.0):
        failures.append(f"Hue={data.Hue!r} outside [0, 360)")
    # CCT is legitimately None below the low-light floor - only an out-of-span NUMBER is a failure.
    if data.CCT is not None and not (CCT_MIN_K <= data.CCT <= CCT_MAX_K):
        failures.append(f"CCT={data.CCT!r} outside [{CCT_MIN_K}, {CCT_MAX_K}] K")
    if data.RangeAct not in (375, 10000):
        failures.append(f"RangeAct={data.RangeAct!r} is neither of the part's two ranges")
    # Coherence: Bri is HSB's own brightness, which is max(R, G, B) by construction.
    if data.Bri is not None and data.Red is not None and data.Green is not None and data.Blue is not None:
        peak = max(data.Red, data.Green, data.Blue)
        if abs(data.Bri - peak) > 1e-6:
            failures.append(f"Bri={data.Bri!r} does not match max(R,G,B)={peak!r} - the HSB triple is inconsistent with RGB")

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS Lux={data.Lux} RGB=({data.Red}, {data.Green}, {data.Blue}) HSB=({data.Hue}, {data.Sat}, {data.Bri}) CCT={data.CCT} RangeAct={data.RangeAct}")


asyncio.run(_main())
