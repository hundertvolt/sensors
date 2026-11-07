"""Isolated-driver device script: SGP40 read cycles counted over ten minutes of the real dev task graph,
so a merged soft-timer tick shows as a lost algorithm sample (SPECIFICATION.md M.3). Report only, no
threshold; it writes the device's own SGP40 backup chunk and the booted modules' logs (FRAM: read first)."""

import asyncio
import time
from array import array

import _bench_device as device  # rendered: the bench device's generated module

# @tunable l3.sgp40_sample_cadence_window_s = 600
_WINDOW_S = 600
# Two slots per expected cycle: a run that somehow reads faster than 1 Hz still never grows the array.
# @tunable l3.sgp40_sample_cadence_slots = 1200
_SLOTS = 1200
# A gap this long means at least one 1 s tick was merged into the next one.
# @tunable l3.sgp40_sample_cadence_gap_ms = 1500
_GAP_MS = 1500
# Guarded like heap_layout_after_full_boot_sequence.py's: a stagger timer that never fires fails honestly.
# @tunable l3.sgp40_sample_cadence_timers_timeout_s = 15
_TIMERS_TIMEOUT_S = 15


async def _main() -> None:
    stamps = array("I", range(_SLOTS))  # ms since base, sized once from the range's length; a record allocates nothing
    count = [0]
    base = time.ticks_ms()
    try:
        await device.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    sgp40 = device.sgp40
    sysfunct = device.sysfunct
    if sgp40 is None or sysfunct is None:
        print("RESULT: FAIL build_system() completed but left sgp40 or sysfunct unset")
        return
    period = (await sgp40.get_dict_cfg())[sgp40.name].get("BackupPeriod")  # the device's own setting, not overridden
    inner_read = sgp40._read_sgp

    async def _counting_read(*args: object, **kwargs: object) -> object:
        if count[0] < _SLOTS:
            stamps[count[0]] = time.ticks_diff(time.ticks_ms(), base)  # well inside ticks_diff()'s horizon
            count[0] += 1
        return await inner_read(*args, **kwargs)  # type: ignore[arg-type]

    sgp40._read_sgp = _counting_read  # type: ignore[method-assign,assignment]
    try:
        await asyncio.wait_for(sysfunct.start_timers(device._collect_trigger_starters(), device._collect_timer_starters()), _TIMERS_TIMEOUT_S)
    except asyncio.TimeoutError:
        print(f"RESULT: FAIL start_timers() did not complete within {_TIMERS_TIMEOUT_S}s - a timer never fired")
        return
    supervisor = asyncio.create_task(sysfunct.start_and_check_tasks(device._collect_task_starters()))  # feeds the watchdog
    start = time.ticks_ms()
    await asyncio.sleep(_WINDOW_S)
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    supervisor.cancel()

    cycles = count[0]
    max_gap = 0
    over = 0
    for i in range(1, cycles):
        gap = stamps[i] - stamps[i - 1]
        max_gap = max(max_gap, gap)
        if gap > _GAP_MS:
            over += 1
    print(f"CADENCE cycles={cycles} elapsed_ms={elapsed} lost={round(elapsed / 1000) - cycles} max_gap_ms={max_gap} gaps_over_{_GAP_MS}={over} backup_period_min={period}")
    # No pass threshold: the owner rejected mitigating a dropped soft-timer tick (SPECIFICATION.md M.3), so the figures are the deliverable.
    print(f"RESULT: {'PASS' if cycles > 0 else 'FAIL'} {cycles} SGP40 read cycles in {elapsed} ms")


asyncio.run(_main())
