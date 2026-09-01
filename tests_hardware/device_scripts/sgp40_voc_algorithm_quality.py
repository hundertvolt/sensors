"""Isolated-driver device script, flash-tier gap fix: real SGP40 raw-signal readings driven through
the real voc_algorithm.py (src/voc_algorithm.py, Sensirion's Gas Index Algorithm port) end to end -
closes the "no automated SGP40 coverage" and "no automated VOC-algorithm-quality coverage" gaps
together, since this driver has no way to exercise one without the other (measure_index_and_raw()
always runs raw signal straight through the algorithm - see asy_sgp40_driver.py).

Two things checked, both datasheet/source-grounded, not exact-reference-calibrated (that needs a
human-supplied VOC stimulus - see tests_hardware/manual/manual_sensor_accuracy.py item 10):
  1. Plausibility: VOC index in [0, 500] (voc_algorithm.py's vocalgorithm_process() returns exactly
     0 during the documented 45s initial blackout - self.params.mvoc_index stays 0 - then clamps to
     >=0.5 -> round()s to >=1 after that; Sensirion's own datasheet documents the steady-state range
     as 1-500, Figure 8). Raw in [0, 65535] (a 16-bit I2C readout, structurally bounded).
  2. Basic quality/stability: once real post-blackout samples are captured, they must not be stuck
     (all-identical, suggesting a frozen/non-responsive algorithm or sensor) or erratic (a single-step
     jump implausibly larger than the algorithm's own adaptive-lowpass smoothing would ever produce
     for real, continuously-sampled air) - a sanity check on the algorithm actually running against
     real hardware, not a numerical-accuracy claim.

Uses the exact same i2c1 construction sensortask_wozi.py's build_system() uses for BMP3xx/SGP40.
No FRAM storage (fram_storage=None) - this script only exercises the algorithm/raw-signal path;
see fram-backed backup/restore coverage in fram_manager_roundtrip.py / sgp40_fram_backup_restore.py.
A fixed [25.0, 50.0] degC/%RH compensation callback stands in for the real SCD30 cross-callback
(sensortask_wozi.py's sgp_comp_callback) - datasheet-documented compensation defaults (Table 10),
not a value this driver treats specially.

Run via `mpremote run <this> soft-reset`. Takes ~70s (45s blackout + sampling window) - not
instant, unlike the other plausibility scripts in this directory."""

import asyncio

import asy_i2c_driver
from asy_sgp40_driver import SGP40_Reader

VOC_MIN, VOC_MAX = 0, 500
RAW_MIN, RAW_MAX = 0, 65535
BLACKOUT_WAIT_S = 60.0  # 45s documented blackout + margin for a real 1s-cadence read loop to catch up
N_QUALITY_SAMPLES = 8
SAMPLE_INTERVAL_S = 2.0
MAX_SINGLE_STEP_JUMP = 300  # generous relative to the algorithm's own adaptive-lowpass smoothing


async def _fixed_comp() -> list[float | None]:
    return [25.0, 50.0]  # datasheet Table 10 compensation defaults - fixed, not sensor-derived


async def _main() -> None:
    i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)
    reader = SGP40_Reader(i2c1, _fixed_comp, max_module_error=999, fram_storage=None, fram_ntp_callback=None, debug=None)
    reader.start_timer()  # 1s fixed period - the algorithm's own sampling interval assumption
    read_task = reader.start_asy_read()

    async def _cancel() -> None:
        read_task.cancel()
        try:
            await read_task
        except Exception:  # noqa: BLE001 - CancelledError or whatever the loop itself raised
            pass

    # Wait out the documented blackout window before sampling for real data.
    await asyncio.sleep(BLACKOUT_WAIT_S)

    samples: list[tuple[int | None, int | None]] = []
    for _ in range(N_QUALITY_SAMPLES):
        data = await reader.get_data()
        samples.append((data.VOC, data.Raw))
        await asyncio.sleep(SAMPLE_INTERVAL_S)

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
