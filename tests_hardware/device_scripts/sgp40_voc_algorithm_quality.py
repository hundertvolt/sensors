"""Isolated-driver device script: real SGP40 raw-signal readings driven through the real
voc_algorithm.py end to end. Checks VOC in [0,500]/Raw in [0,65535] post-blackout (45s), and basic
stability (not stuck, no implausible single-step jump) - a sanity check, not an accuracy claim."""

import asyncio

import machine

import asy_i2c_driver
from asy_sgp40_driver import SGP40_Reader

VOC_MIN, VOC_MAX = 0, 500
RAW_MIN, RAW_MAX = 0, 65535
BLACKOUT_WAIT_S = 60.0  # 45s documented blackout + margin for a real 1s-cadence read loop to catch up
N_QUALITY_SAMPLES = 8
SAMPLE_INTERVAL_S = 2.0
MAX_SINGLE_STEP_JUMP = 300  # generous relative to the algorithm's own adaptive-lowpass smoothing
_WDT_FEED_INTERVAL_S = 2.0  # comfortably under the 8.388s hardware ceiling


async def _fixed_comp() -> list[float | None]:
    return [25.0, 50.0]  # datasheet Table 10 compensation defaults - fixed, not sensor-derived


async def _sleep_feeding_wdt(duration_s: float, wdt: machine.WDT) -> None:
    remaining = duration_s
    while remaining > 0:
        await asyncio.sleep(min(_WDT_FEED_INTERVAL_S, remaining))
        wdt.feed()
        remaining -= _WDT_FEED_INTERVAL_S


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)  # matches src/system_service.py's own production value
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)
    reader = SGP40_Reader(i2c1, _fixed_comp, max_module_error=999, fram_storage=None, fram_ntp_callback=None, debug=None)
    reader.start_timer()  # 1s fixed period - the algorithm's own sampling interval assumption
    read_task = reader.start_asy_read()

    async def _cancel() -> None:
        read_task.cancel()
        try:
            await read_task
        except (asyncio.CancelledError, Exception):
            pass

    # Wait out the documented blackout window before sampling for real data.
    await _sleep_feeding_wdt(BLACKOUT_WAIT_S, wdt)

    samples: list[tuple[int | None, int | None]] = []
    for _ in range(N_QUALITY_SAMPLES):
        data = await reader.get_data()
        samples.append((data.VOC, data.Raw))
        await _sleep_feeding_wdt(SAMPLE_INTERVAL_S, wdt)

    await _cancel()

    if any(voc is None or raw is None for voc, raw in samples):
        print(f"RESULT: FAIL one or more post-blackout samples had no VOC/Raw reading - sensor not responding or not wired to i2c1: {samples}")
        return

    failures = []
    voc_values = [voc for voc, _ in samples if voc is not None]
    raw_values = [raw for _, raw in samples if raw is not None]
    for voc in voc_values:
        if not (VOC_MIN <= voc <= VOC_MAX):
            failures.append(f"VOC={voc!r} outside [{VOC_MIN}, {VOC_MAX}]")
    for raw in raw_values:
        if not (RAW_MIN <= raw <= RAW_MAX):
            failures.append(f"Raw={raw!r} outside [{RAW_MIN}, {RAW_MAX}]")

    if len(set(voc_values)) == 1 and len(voc_values) > 1:
        failures.append(f"all {len(voc_values)} post-blackout VOC samples were identical ({voc_values[0]}) - algorithm may be frozen/not responding to real readings")

    for prev, cur in zip(voc_values, voc_values[1:]):  # noqa: B905 - MicroPython zip() rejects strict=, same list length by construction
        if abs(cur - prev) > MAX_SINGLE_STEP_JUMP:
            failures.append(f"implausible single-step VOC jump {prev} -> {cur} (> {MAX_SINGLE_STEP_JUMP})")

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS VOC samples={voc_values} Raw samples={raw_values}")


asyncio.run(_main())
