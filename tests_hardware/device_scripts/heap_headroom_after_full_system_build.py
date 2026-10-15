"""Isolated-driver device script: the heap on real silicon once the bench build's whole object graph exists and its
setup batch has run - what the survivors cost, the largest contiguous block still obtainable, and the block map
(measured host-side by heap_map.py). Facts only: flash/test_memory_stress.py judges them (SPECIFICATION.md I)."""

import asyncio
import errno
import gc
import os

import _bench_device as device  # rendered: the bench device's generated module
import machine

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
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force, so the build runs
# at MicroPython's own reactive default, the (e) stage.
gc.threshold(-1)
# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
# Requirement, not a fitted floor: room for the worst case twice over, 12 % of the RP2040's 264 KB SRAM where the
# retired 80,000 B floor was 30 % (agent, 2026-09-19; owner-reviewed, 2026-10-02). Nothing is raised to fit a reading.
# @tunable l3.heap_headroom_after_full_system_build_worst_case_factor = 2
_WORST_CASE_FACTOR = 2
_MIN_LARGEST_BLOCK = _WORST_CASE_FACTOR * BENCH["worst_case_allocation"]
# Survivor volume: every reading of a fully built dev graph is 87,760-87,968 B, so this is ~14 % over the graph's own
# cost and catches a regression that adds permanent objects rather than one that scatters them.
# @tunable l3.heap_headroom_after_full_system_build_max_used = 100_000
_MAX_USED = 100_000


async def _main() -> None:
    stages = [gc.threshold()]
    free, largest = report_checked("baseline")
    fact("heap_baseline", {"free": free, "largest_block": largest, "alloc": gc.mem_alloc()})
    # The "before" half of the placement delta: what the BOOT adds up high is attributable only against what was
    # already there, which makes the host's placement check independent of the suite position.
    dump_map("baseline")
    wdt = arm()
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct = device.sysfunct
        assert sysfunct is not None, "the generated build constructs SystemService unconditionally"
        # main()'s next step: the measured graph is the one a real boot leaves, setup survivors included.
        await sysfunct.run_setups(device._collect_setups())
        # At MicroPython's own reactive default first: a headroom figure that only holds with a proactive threshold
        # is no headroom (CLAUDE.md's memory-safety ladder).
        free, largest = report_checked("after_build_system")
        used = gc.mem_alloc()  # read here, so the three checks share one position
        fact("heap_after_build_system", {"free": free, "largest_block": largest, "alloc": used})
        dump_map("after_build_system")
        # Control first at the unchanged threshold, so the next reading's difference is no difference between two
        # probe runs at one position.
        free_c, largest_c = report_checked("after_build_system_control")
        fact("heap_after_build_system_control", {"free": free_c, "largest_block": largest_c, "alloc": gc.mem_alloc()})
        # @tunable gc.threshold_bytes = 32768
        gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
        stages.append(gc.threshold())
        free_p, largest_p = report_checked("after_build_system_production_threshold")
        fact("heap_after_build_system_production_threshold", {"free": free_p, "largest_block": largest_p, "alloc": gc.mem_alloc()})
        fact("used", used)
        fact("max_used", _MAX_USED)
        fact("largest_block", largest)
        fact("min_largest_block", _MIN_LARGEST_BLOCK)
    finally:
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
