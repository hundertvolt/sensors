"""Isolated-driver device script: heap layout after BOTH one-time boot lists, not just
build_system() - the setup batch is the smaller half of the boot-confined placement reset's effect
(SPECIFICATION.md Part I.4(f.1), HEAP_FRAGMENTATION_MEASUREMENTS.md 7E.3). Report only, no floors."""

import asyncio
import gc
import time

import sensortask_dev

# Same doubling/halving bounds as heap_headroom_after_full_system_build.py, deliberately: the two
# scripts' largest_block figures are only comparable if the probe is identical.
_PROBE_MIN = 64
_PROBE_MAX = 192 * 1024

# The starter loop sleeps 1.0/len(starters) per starter, so 1.0 s in total whatever the count. 4 s
# clears it with margin and lets one or two supervisor passes run - deliberately: the supervisor is
# the run phase and carries no collect, which is the state a real unit is in seconds after boot.
_STARTER_SETTLE_MS = 4000
# start_timers() waits on every timer's first fire. Guarded rather than awaited bare so a timer that
# never fires fails this script honestly instead of hanging the suite (CLAUDE.md's known hang #2).
_TIMERS_TIMEOUT_S = 15


def _largest_block() -> int:
    gc.collect()
    low, high = 0, _PROBE_MAX
    while low < high:
        mid = (low + high + 1) // 2
        if mid < _PROBE_MIN:
            break
        try:
            probe = bytearray(mid)
        except MemoryError:
            high = mid - 1
        else:
            del probe
            low = mid
        gc.collect()
    return low


def _report(label: str) -> "tuple[int, int]":
    gc.collect()
    free, largest = gc.mem_free(), _largest_block()
    print(f"HEAP {label}: free={free} alloc={gc.mem_alloc()} largest_block={largest} pct={largest * 100 // max(free, 1)}")
    return free, largest


async def _main() -> None:
    _report("baseline")
    t0 = time.ticks_ms()
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    build_ms = time.ticks_diff(time.ticks_ms(), t0)
    _report("after_build_system")

    sysfunct = sensortask_dev.sysfunct
    if sysfunct is None:
        print("RESULT: FAIL build_system() completed but left sysfunct unset")
        return
    task_starters = sensortask_dev._collect_task_starters()
    timer_starters = sensortask_dev._collect_timer_starters()
    print(f"LISTS starters={len(task_starters)} timers={len(timer_starters)}")

    # main()'s own order, minus ntp_force_sync(): that one needs a reachable NTP server, and a
    # network-dependent wait in the middle would put the measurement at the mercy of the bench LAN.
    # It allocates during the gap between the two lists either way - stated, not measured here.
    t1 = time.ticks_ms()
    try:
        await asyncio.wait_for(sysfunct.start_timers(timer_starters), _TIMERS_TIMEOUT_S)
    except asyncio.TimeoutError:
        print(f"RESULT: FAIL start_timers() did not complete within {_TIMERS_TIMEOUT_S}s - a timer never fired")
        return
    timers_ms = time.ticks_diff(time.ticks_ms(), t1)
    _report("after_start_timers")

    t2 = time.ticks_ms()
    supervisor = asyncio.create_task(sysfunct.start_and_check_tasks(task_starters))
    await asyncio.sleep_ms(_STARTER_SETTLE_MS)
    starters_ms = time.ticks_diff(time.ticks_ms(), t2)
    free, largest = _report("after_starter_list")
    supervisor.cancel()

    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    _report("after_starter_list_production_threshold")

    print(f"BOOT build_system_ms={build_ms} start_timers_ms={timers_ms} starter_list_ms={starters_ms}")
    # No floor is asserted. No reading for this position exists yet on silicon, so a threshold here
    # would be invented rather than measured; the figure is the deliverable and the comparison is
    # between two firmware images at the same suite position (7D.2).
    print(f"RESULT: PASS heap after the whole boot sequence: {free} B free, {largest} B largest single block")


asyncio.run(_main())
