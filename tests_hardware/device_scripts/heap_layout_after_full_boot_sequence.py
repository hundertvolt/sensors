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
# Rereads allowed when the probe pins its own buffer (see _report_checked). Three is generous: one
# has always been enough on the twin, at every heap size tried.
_PROBE_RETRIES = 3

# 4 s after the loop ENDS, so this reading is the run phase, not the list: the supervisor and the
# started tasks churn with no collect, and the twin says B's gain decays there within ~2 s
# (MEASUREMENTS 7F.9). ~1 s later than 7F.2's, which that decay makes immaterial.
_STARTER_SETTLE_MS = 4000
# How long to wait for the starter loop itself to finish before giving up on it. The loop sleeps
# 1.0 s in total whatever the starter count, plus each _start_task; 20 s is far above any plausible
# real value and only exists so a wedged starter fails honestly instead of hanging.
_STARTER_LOOP_TIMEOUT_MS = 20000
# Added to one inter-starter interval once the last starter lands, to cover the loop's final sleep
# and its final collect - ~41 ms on the RP2040 (MEASUREMENTS 7F.7), so 250 ms is ample.
_STARTER_LOOP_GRACE_MS = 250
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


def _report(label: str) -> "tuple[int, int, int]":
    gc.collect()
    free, base = gc.mem_free(), gc.mem_alloc()
    largest = _largest_block()
    gc.collect()
    retained = gc.mem_alloc() - base
    print(f"HEAP {label}: free={free} alloc={gc.mem_alloc()} largest_block={largest} retained={retained} pct={largest * 100 // max(free, 1)}")
    return free, largest, retained


def _report_checked(label: str) -> "tuple[int, int]":
    # A probe run can pin its own buffer through a stale root; every later attempt then fails and
    # the search converges on the pinned size - always _PROBE_MAX >> k, e.g. 49,152 (MEASUREMENTS
    # 7F.8). retained > 0 is that state, and a rerun from a fresh frame clears it.
    free, largest, retained = _report(label)
    attempt = 0
    while retained >= _PROBE_MIN and attempt < _PROBE_RETRIES:
        attempt += 1
        free, largest, retained = _report(f"{label}_retry{attempt}")
    if retained >= _PROBE_MIN:
        print(f"WARNING {label}: probe still holding {retained} B after {_PROBE_RETRIES} rereads - largest_block is a floor, not a figure")
    return free, largest


async def _main() -> None:
    _report_checked("baseline")
    t0 = time.ticks_ms()
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    build_ms = time.ticks_diff(time.ticks_ms(), t0)
    _report_checked("after_build_system")

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
    _report_checked("after_start_timers")

    # Count the starters as they land, so the loop's own end is observed rather than timed out at a
    # guessed constant. start_and_check_tasks() never returns - it falls into the supervisor - and
    # its task list is a local, so the seam is only visible from here.
    started = []
    inner_start_task = sysfunct._start_task

    async def _counting_start_task(starter: object, n: int) -> object:
        task = await inner_start_task(starter, n)
        started.append(n)
        return task

    sysfunct._start_task = _counting_start_task

    t2 = time.ticks_ms()
    supervisor = asyncio.create_task(sysfunct.start_and_check_tasks(task_starters))
    loop_deadline = time.ticks_add(t2, _STARTER_LOOP_TIMEOUT_MS)
    while len(started) < len(task_starters) and time.ticks_diff(loop_deadline, time.ticks_ms()) > 0:
        await asyncio.sleep_ms(20)
    if len(started) < len(task_starters):
        print(f"RESULT: FAIL only {len(started)} of {len(task_starters)} starters ran within {_STARTER_LOOP_TIMEOUT_MS} ms")
        return
    # The last starter has landed but the loop has not: one `await asyncio.sleep(1.0/len(starters))`
    # and the collect after it are still to come, and the collect IS the thing being measured. A
    # collect counter would be exact but reads zero on the A-only arm, so wait that tail out instead.
    await asyncio.sleep_ms(1000 // len(task_starters) + _STARTER_LOOP_GRACE_MS)
    starters_ms = time.ticks_diff(time.ticks_ms(), t2)
    # The reading measure B's second site is about: taken where the last collect of the starter list
    # just ran, before the run phase has had time to undo it (MEASUREMENTS 7F.9).
    _report_checked("after_starter_loop_end")

    await asyncio.sleep_ms(_STARTER_SETTLE_MS)
    free, largest = _report_checked("after_starter_list")
    supervisor.cancel()

    # Control first, at the unchanged threshold: without it a difference in the next line cannot be
    # told from a difference between two probe runs at the same position - which is exactly how
    # 7F.2's 49,152 was misread as a layout figure (MEASUREMENTS 7F.8).
    _report_checked("after_starter_list_control")
    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    _report_checked("after_starter_list_production_threshold")

    print(f"BOOT build_system_ms={build_ms} start_timers_ms={timers_ms} starter_loop_ms={starters_ms} settle_ms={_STARTER_SETTLE_MS}")
    # No floor is asserted. No reading for this position exists yet on silicon, so a threshold here
    # would be invented rather than measured; the figure is the deliverable and the comparison is
    # between two firmware images at the same suite position (7D.2).
    print(f"RESULT: PASS heap after the whole boot sequence: {free} B free, {largest} B largest single block")


asyncio.run(_main())
