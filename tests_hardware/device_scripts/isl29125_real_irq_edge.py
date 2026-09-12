"""Isolated-driver device script: confirms a genuine FALLING edge on the ISL29125's INT pin (GP6,
open-drain, externally pulled up) drives a read faster than the periodic fallback would.
Also measures the two datasheet questions no document answers: whether a CONFIG1 write really
restarts the conversion, and whether PRST counts RGB cycles or channel integrations."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C, ISL29125_Reader

FAST_PATH_DEADLINE_S = 3.0  # well under the 30s periodic fallback configured below
TRIGGER_SEC = 30  # deliberately long: only a real interrupt can beat it
_CYCLE_MS_16BIT = 303  # 3 x tINT, tINT = 101ms typ (p3)
_MODE_RGB = 0x05
_INTSEL_GREEN = 0x01


async def _measure_config1_restart(isl: ISL29125_I2C, wdt: machine.WDT) -> str:
    # Question 1: Table 7 (p10) says the ADC starts on an I2C write to 0x01 with SYNC = 0, and
    # the mainline Linux IIO driver msleep(101)s after exactly that write. If the restart is
    # real, the data registers still hold the PREVIOUS cycle's values immediately afterwards and
    # only change once a full cycle has elapsed.
    await isl.configure(mode=_MODE_RGB, range_fs=10000, resolution=16, int_select=0)
    await asyncio.sleep_ms(2 * _CYCLE_MS_16BIT)
    wdt.feed()
    before = await isl.read_counts()
    await isl.configure(range_fs=375)  # a real CONFIG1 write
    immediately = await isl.read_counts()
    await asyncio.sleep_ms(_CYCLE_MS_16BIT + 50)
    wdt.feed()
    after_one_cycle = await isl.read_counts()
    restarted = immediately == before and after_one_cycle != immediately
    return (
        f"config1_restart={'yes' if restarted else 'inconclusive'} "
        f"before={before} immediately={immediately} after_one_cycle={after_one_cycle}"
    )


async def _measure_persist_unit(isl: ISL29125_I2C, pin: machine.Pin, wdt: machine.WDT) -> str:
    # Question 2: Table 12 (p11) calls PRST's unit an "integration cycle" without saying whether
    # that is one channel's integration (~101 ms) or one whole R-G-B cycle (~303 ms). INTSEL
    # selects ONE channel, which converts once per RGB cycle, so the reading should be cycles -
    # this times it rather than arguing about it.
    await isl.configure(mode=_MODE_RGB, range_fs=375, resolution=16, int_select=_INTSEL_GREEN, persist=4)
    await isl.set_thresholds(0, 1)  # essentially any light at all is "above the window"
    await isl.read_status()  # destructive: clears any flag already standing
    start = time.ticks_ms()
    fired_ms = -1
    for _ in range(30):
        if pin.value() == 0:
            fired_ms = time.ticks_diff(time.ticks_ms(), start)
            break
        wdt.feed()
        await asyncio.sleep_ms(50)
    await isl.read_status()  # release the line again
    if fired_ms < 0:
        return "persist_unit=inconclusive (the interrupt never asserted within 1.5s)"
    per_cycle_ms = 4 * _CYCLE_MS_16BIT  # ~1212 ms if PRST counts whole RGB cycles
    per_channel_ms = 4 * 101  # ~404 ms if it counts single-channel integrations
    closer = "rgb_cycles" if abs(fired_ms - per_cycle_ms) < abs(fired_ms - per_channel_ms) else "channel_integrations"
    return f"persist_unit={closer} (PRST=4 asserted after {fired_ms}ms; rgb_cycles~{per_cycle_ms}ms, channel_integrations~{per_channel_ms}ms)"


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)

    # Part A: the two datasheet measurements, against the protocol layer alone.
    isl = ISL29125_I2C(i2c1)
    await isl.setup()
    pin = machine.Pin(6, mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)
    restart_note = await _measure_config1_restart(isl, wdt)
    persist_note = await _measure_persist_unit(isl, pin, wdt)

    # Part B: the real fast path, through the real reader. A 30s periodic interval means a
    # reading inside 3s can only have come from the interrupt.
    reader = ISL29125_Reader(i2c1, 6, trigger_sec=TRIGGER_SEC, max_module_error=999, fram=None, debug=None)
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {
        "SampleInterv": TRIGGER_SEC, "Resolution": 16, "RangeAuto": True, "Range": 10000,
        "AutoRangeUp": 85.0, "AutoRangeDown": 1.5, "AutoRangeSettle": 1,
        "AutoRangePersist": 1, "AutoRangeDwell": 0.0,
        "IrCompOffset": 0, "IrCompAdjust": 40, "FiltCoeff": -1.0,
    }
    reader.start_timer()
    trigger_task = reader.start_asy_trigger()
    read_task = reader.start_asy_read()

    start = time.ticks_ms()
    data = None
    deadline_ms = int(FAST_PATH_DEADLINE_S * 1000)
    while time.ticks_diff(time.ticks_ms(), start) < deadline_ms:
        data = await reader.get_data()
        if data.Lux is not None:
            break
        wdt.feed()
        await asyncio.sleep_ms(100)

    for task in (trigger_task, read_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    if data is not None and data.Lux is not None:
        elapsed_s = time.ticks_diff(time.ticks_ms(), start) / 1000.0
        print(f"RESULT: PASS interrupt-driven reading arrived after {elapsed_s:.2f}s (periodic fallback was {TRIGGER_SEC}s) | {restart_note} | {persist_note}")
    else:
        print(f"RESULT: FAIL no reading within {FAST_PATH_DEADLINE_S}s - the INT line does not appear to reach GP6 | {restart_note} | {persist_note}")


asyncio.run(_main())
