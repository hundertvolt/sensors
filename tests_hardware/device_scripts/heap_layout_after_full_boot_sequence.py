"""Isolated-driver device script: heap layout after BOTH one-time boot lists in the generated order (build_system(),
run_setups(), start_tasks(), start_timers()), the supervisor never entered - the boot placement reset of
SPECIFICATION.md Part I.4(f.1). Report only: flash/test_heap_layout.py holds each arm to the twin's bound."""

import asyncio
import errno
import gc
import os
import time

import _bench_device as device  # rendered: the bench device's generated module
import machine

import asy_system_service
from asy_print_log import PrintLog

# @include _shared/facts.py
# @include _shared/heap_probe.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.heap_probe import dump_map, report_checked
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

    from asy_system_service import SystemService

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: mpremote's soft reset keeps whatever threshold main.py left, so the first arm runs at -1.
gc.threshold(-1)
# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
# 4 s after the timers start, so this reading is the run phase, not the list: the started tasks churn with no collect.
# @tunable l3.heap_layout_after_full_boot_sequence_starter_settle_ms = 4000
_STARTER_SETTLE_MS = 4000
# Bounds mirroring tests/_boot_contiguity_probe.py's, so a twin reading and a board reading share their positions; a
# feeder task keeps the watchdog fed across both bounded waits.
# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms = 20000
_STARTER_LOOP_TIMEOUT_MS = 20000
# @tunable l3.heap_layout_after_full_boot_sequence_timers_timeout_s = 15
_TIMERS_TIMEOUT_S = 15
_ARM_LIVE = "collects"
_ARM_SUPPRESSED = "suppressed"


class _ProbeGc:
    # Stands in for `gc` at asy_system_service.py's boot-list collects: dumps a map at the positions asked for, then
    # forwards to the real collect only on the live arm, as the twin's tests/_boot_contiguity_probe.py does. A dumped
    # position collects on both arms (dump_map() collects first), so the seam map anchors both arms at one place.

    def __init__(self, tag: str, *, live: bool, dump_at: "tuple[int, ...]") -> None:
        self.tag = tag
        self.live = live
        self.dump_at = dump_at
        self.calls = 0

    def collect(self) -> None:
        if self.calls in self.dump_at:
            dump_map(f"{self.tag}_{self.calls:02d}")
        if self.live:
            gc.collect()
        self.calls += 1


async def _boot_lists(sysfunct: "SystemService", starter_gc: _ProbeGc, wdt: "machine.WDT", stages: "list[int]") -> "dict[str, int]":
    # main()'s order after the setup batch: the task lists at the task starts, the trigger and timer lists once
    # start_tasks() returned, then the timers, the supervisor never entered; the readings and maps on the way, and
    # their durations returned.
    task_starters = device._collect_task_starters()
    task_names = device._collect_task_names()
    asy_system_service.gc = starter_gc  # type: ignore[assignment]
    t1 = time.ticks_ms()
    try:
        # start_tasks() returns right after its last collect, so the reading below is the loop's own end.
        await asyncio.wait_for_ms(sysfunct.start_tasks(task_starters, task_names=task_names), _STARTER_LOOP_TIMEOUT_MS)
        fact("starter_loop_done", True)
    except asyncio.TimeoutError:
        fact("starter_loop_done", False)
    starters_ms = time.ticks_diff(time.ticks_ms(), t1)
    free, largest = report_checked("after_starter_loop_end")
    fact("heap_after_starter_loop_end", {"free": free, "largest_block": largest})
    dump_map("after_starter_loop_end")
    trigger_starters = device._collect_trigger_starters()
    timer_starters = device._collect_timer_starters()
    fact("lists", {"starters": len(task_starters), "timers": len(timer_starters), "triggers": len(trigger_starters)})
    t2 = time.ticks_ms()
    try:
        await asyncio.wait_for(sysfunct.start_timers(trigger_starters, timer_starters), _TIMERS_TIMEOUT_S)
        fact("timers_done", True)
    except asyncio.TimeoutError:
        fact("timers_done", False)
    timers_ms = time.ticks_diff(time.ticks_ms(), t2)
    # A failed stagger arm or a starter that raised degrades and logs, so the reading states what SYSTEM recorded.
    fact("system", (await sysfunct.get_error_counter())["SYSTEM"])
    free, largest = report_checked("after_start_timers")
    fact("heap_after_start_timers", {"free": free, "largest_block": largest})
    await fed_sleep_ms(wdt, _STARTER_SETTLE_MS)
    free, largest = report_checked("after_starter_list")
    fact("heap_after_starter_list", {"free": free, "largest_block": largest})
    dump_map("after_starter_list")
    # Control first, at the unchanged threshold: without it a difference in the next reading cannot be told from a
    # difference between two probe runs at one position.
    free, largest = report_checked("after_starter_list_control")
    fact("heap_after_starter_list_control", {"free": free, "largest_block": largest})
    # @tunable gc.threshold_bytes = 32768
    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    stages.append(gc.threshold())
    free, largest = report_checked("after_starter_list_production_threshold")
    fact("heap_after_starter_list_production_threshold", {"free": free, "largest_block": largest})
    return {"starter_loop_ms": starters_ms, "start_timers_ms": timers_ms}


async def _main() -> None:
    wdt = arm()
    arm_name = BENCH.get("ARM", _ARM_LIVE)
    fact("arm", arm_name)
    if arm_name not in (_ARM_LIVE, _ARM_SUPPRESSED):
        done()
        return
    live = arm_name == _ARM_LIVE
    stages = [gc.threshold()]
    # The seam: run_setups()'s first collect, before the list's first unit. Both lists collect through
    # asy_system_service's own `gc`, so each probe stands in for it while its list runs.
    batch_gc = _ProbeGc("batch", live=live, dump_at=(0,))
    starter_gc = _ProbeGc("starter", live=live, dump_at=())
    free, largest = report_checked("baseline")
    fact("heap_baseline", {"free": free, "largest_block": largest})
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    # A task that dies unawaited is printed at every DebugLevel: start_tasks() keeps a handler already set.
    asyncio.get_event_loop().set_exception_handler(PrintLog(level=1, name="UNRETRIEVED").report_unretrieved)
    feeder = None
    try:
        t0 = time.ticks_ms()
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct = device.sysfunct
        assert sysfunct is not None, "the generated build constructs SystemService unconditionally"
        asy_system_service.gc = batch_gc  # type: ignore[assignment]
        await sysfunct.run_setups(device._collect_setups())
        build_ms = time.ticks_diff(time.ticks_ms(), t0)
        free, largest = report_checked("after_build_system")
        fact("heap_after_build_system", {"free": free, "largest_block": largest})
        dump_map("after_build_system")
        # main()'s own order, minus ntp_force_sync(): a network-dependent wait would put the reading at the bench LAN's
        # mercy. Fed by a task of its own across both bounded waits: the supervisor, which feeds in production, never runs.
        feeder = asyncio.create_task(fed_sleep_ms(wdt, _STARTER_LOOP_TIMEOUT_MS + _TIMERS_TIMEOUT_S * 1000 + _STARTER_SETTLE_MS))
        timings = await _boot_lists(sysfunct, starter_gc, wdt, stages)
        fact("counts", {"batch_collects": batch_gc.calls, "starter_collects": starter_gc.calls})
        timings["build_system_ms"] = build_ms
        timings["settle_ms"] = _STARTER_SETTLE_MS
        fact("boot_ms", timings)
    finally:
        if feeder is not None:
            feeder.cancel()
        asy_system_service.gc = gc
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        # The boot-phase mark build_system() left: cleared, so the next reset does not read as a boot failure.
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
    fact("gc_threshold", stages)
    done()


asyncio.run(_main())
