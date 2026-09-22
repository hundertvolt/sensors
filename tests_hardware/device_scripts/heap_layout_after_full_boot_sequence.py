"""Isolated-driver device script: heap layout after BOTH one-time boot lists, not just
build_system() - the setup batch is the smaller half of the boot-confined placement reset's effect
(SPECIFICATION.md Part I.4(f.1), HEAP_FRAGMENTATION_MEASUREMENTS.md 7E.3). Report only, no floors."""

import asyncio
import gc
import time

import micropython
import sensortask_dev

import system_service

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

_ARM_LIVE = "collects"
_ARM_SUPPRESSED = "suppressed"


def _selected_arm() -> str:
    # mpremote run takes no argv but does share globals with an `exec` earlier in the same raw-REPL
    # session, which is how the suppressed arm is selected: exec "_ARM_OVERRIDE='suppressed'" first.
    # Verified on this board, 2026-09-22; assigning sys.argv raises there, appending to it works.
    arm = str(globals().get("_ARM_OVERRIDE", _ARM_LIVE))
    if arm not in (_ARM_LIVE, _ARM_SUPPRESSED):
        print(f"RESULT: FAIL unknown arm {arm!r} - expected {_ARM_LIVE!r} or {_ARM_SUPPRESSED!r}")
        raise SystemExit(1)
    return arm


class _ProbeGc:
    """Stands in for `gc` at the emitted collect sites: dumps a map at the positions asked for, then
    forwards to the real collect only on the live arm. Ported from tests/_boot_contiguity_probe.py
    so the board and the twin measure the same sequence at the same positions."""

    # A dumped position collects on BOTH arms, via _dump_map() - the seam map has to be post-collect
    # or the arms anchor at different places and nothing is comparable. The suppressed arm therefore
    # keeps the leading collect and loses the per-unit ones, which makes it a conservative control.

    def __init__(self, tag: str, *, live: bool, dump_at: "tuple[int, ...]") -> None:
        self.tag = tag
        self.live = live
        self.dump_at = dump_at
        self.calls = 0

    def collect(self) -> None:
        if self.calls in self.dump_at:
            _dump_map(f"{self.tag}_{self.calls:02d}")
        if self.live:
            gc.collect()
        self.calls += 1


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


def _dump_map(label: str) -> None:
    # The layout itself: mem_info(1) prints the per-block map and the exact largest free run,
    # allocating nothing - so it cannot perturb what it measures, and it cannot hit the probe's own
    # pinning artefact either. Parsed host-side by tests_hardware/heap_map.py.
    gc.collect()
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


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
    arm = _selected_arm()
    live = arm == _ARM_LIVE
    # The seam: the generated module's first emitted collect, which runs before the batch's first
    # setup unit. Without a map here heap_map.delta() has no `before` for the batch (7L).
    batch_gc = _ProbeGc("batch", live=live, dump_at=(0,))
    starter_gc = _ProbeGc("starter", live=live, dump_at=())
    sensortask_dev.gc = batch_gc  # type: ignore[assignment]
    system_service.gc = starter_gc  # type: ignore[assignment]
    print(f"ARM {arm}")

    _report_checked("baseline")
    t0 = time.ticks_ms()
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    build_ms = time.ticks_diff(time.ticks_ms(), t0)
    _report_checked("after_build_system")
    _dump_map("after_build_system")

    sysfunct = sensortask_dev.sysfunct
    if sysfunct is None:
        print("RESULT: FAIL build_system() completed but left sysfunct unset")
        return
    task_starters = sensortask_dev._collect_task_starters()
    timer_starters = sensortask_dev._collect_timer_starters()
    print(f"LISTS starters={len(task_starters)} timers={len(timer_starters)} batch_collects={batch_gc.calls}")

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
    _dump_map("after_starter_loop_end")

    await asyncio.sleep_ms(_STARTER_SETTLE_MS)
    free, largest = _report_checked("after_starter_list")
    _dump_map("after_starter_list")
    supervisor.cancel()

    # Control first, at the unchanged threshold: without it a difference in the next line cannot be
    # told from a difference between two probe runs at the same position - which is exactly how
    # 7F.2's 49,152 was misread as a layout figure (MEASUREMENTS 7F.8).
    _report_checked("after_starter_list_control")
    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    _report_checked("after_starter_list_production_threshold")

    print(f"COUNTS batch_collects={batch_gc.calls} starter_collects={starter_gc.calls}")
    print(f"BOOT arm={arm} build_system_ms={build_ms} start_timers_ms={timers_ms} starter_loop_ms={starters_ms} settle_ms={_STARTER_SETTLE_MS}")
    # No floor is asserted. No reading for this position exists yet on silicon, so a threshold here
    # would be invented rather than measured; the figure is the deliverable and the comparison is
    # between two firmware images at the same suite position (7D.2).
    print(f"RESULT: PASS heap after the whole boot sequence: {free} B free, {largest} B largest single block")


asyncio.run(_main())
