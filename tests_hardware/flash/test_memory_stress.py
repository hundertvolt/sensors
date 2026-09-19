"""Flash-tier automated tests: real GC-heap headroom once the whole object graph exists, and real
single-core timing headroom under normal full task load (real 133MHz), matching SPECIFICATION.md
Parts I and F.3. The real-HTTP-soak variants live in bench/ - this tier has no network client."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import heap_map
import pytest
from soak_tiers import SOAK_TIER_SECONDS

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)

# The largest contiguous allocation the firmware can be asked to make (MEASUREMENTS 7A.9): 4,096 B
# as configured, 16,384 B worst case reachable through microdot's own max_body_length default. Every
# figure below is a multiple of that, never of a board reading.
WORST_CASE_ALLOCATION = 16_384


def test_real_gc_heap_headroom_survives_a_full_system_build(board: Board) -> None:
    # The one memory figure no fake can produce: the RP2040's real 264KB SRAM minus the firmware's
    # own static footprint, measured after the real dev object graph exists. The device script
    # checks survivor volume and contiguity; the placement check below needs the block map, which
    # only the host can read back.
    output = board.run_isolated(DEVICE_SCRIPTS / "heap_headroom_after_full_system_build.py", timeout_s=120.0)
    # Print on pass too, not only in the assertions below: run_isolated() captures device stdout
    # into a string, so a PASSING run used to discard the figures and 7F.6 lost exactly that number.
    # Surface them with `scripts/run_flash_hardware_suite.sh -s`.
    for line in (ln for ln in output.splitlines() if ln.startswith("HEAP ")):
        print(line)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"real heap-headroom check failed: {match.group(2).strip()}\nfull output:\n{output}"

    maps = heap_map.parse_labelled(output)
    assert "after_build_system" in maps, f"no mem_info(1) block map in the device output - the layout cannot be checked:\n{output}"
    layout = maps["after_build_system"]
    print(f"MAP after_build_system: {layout.summary()}")
    # Cross-check, free: the probe allocates and the map does not, so they fail in different ways.
    # A disagreement means one of them is wrong - the probe's own pinning artefact looks exactly
    # like this (MEASUREMENTS 7F.8), and it always understates.
    probed = _probed_largest_block(output, "after_build_system")
    assert probed is not None, f"no HEAP after_build_system line to cross-check the map against:\n{output}"
    assert abs(layout.largest_free_run - probed) <= layout.block_bytes * 2, (
        f"the allocating probe says {probed} B and the block map says {layout.largest_free_run} B. They measure the same run, "
        f"so one is wrong; the probe understating by a power-of-two fraction of 192 KB is the known artefact.\nfull output:\n{output}"
    )
    # What the owner asked these tests to express (2026-09-19): long-lived objects must not colonise
    # the top of the heap. Asserted twice, because the two fail for different reasons and the
    # difference is the diagnosis (MEASUREMENTS 7G.5).
    assert "baseline" in maps, f"no baseline block map in the device output - the placement delta cannot be computed:\n{output}"
    placed = heap_map.delta(maps["baseline"], layout)
    print(f"DELTA boot placement: {placed.summary()}")
    # 1. Attributable, and independent of what the suite left on the heap before this ran: the BOOT
    #    must add nothing in the long heap. Zero, not a budget - 17 twin runs across 41-58% fill,
    #    perturbed, never placed one (7G.5).
    assert placed.new_above(WORST_CASE_ALLOCATION) == 0, (
        f"the boot placed {placed.new_above(WORST_CASE_ALLOCATION)} long-lived object(s) inside the top "
        f"{WORST_CASE_ALLOCATION} B of the heap, where a worst-case allocation has to fit. This one is the boot's own "
        f"doing, not the suite position's. {placed.summary()}"
    )
    # 2. Absolute, and position-dependent by nature: nothing at all may sit up there, whoever put it
    #    there. If this fails while 1 passes, the heap was already colonised before the boot ran.
    assert layout.free_above_top_survivor >= WORST_CASE_ALLOCATION, (
        f"long-lived objects reach into the top of the heap: only {layout.free_above_top_survivor} B free above the highest "
        f"allocated block, against the {WORST_CASE_ALLOCATION} B worst reachable allocation. The boot itself placed "
        f"{placed.new_above(WORST_CASE_ALLOCATION)} of them there, so read this with that number. Layout: {layout.summary()}"
    )


def _probed_largest_block(output: str, label: str) -> int | None:
    match = re.search(rf"^HEAP {re.escape(label)}(?:_retry\d+)?: .*largest_block=(\d+)", output, re.MULTILINE)
    return int(match.group(1)) if match else None


@pytest.mark.long_soak
def test_single_core_timing_headroom_holds_under_normal_full_task_load(board: Board, request: pytest.FixtureRequest) -> None:
    tier = request.config.getoption("--soak-tier")
    if tier is None:
        pytest.skip("passive soak, one of three named duration tiers - run via scripts/run_bench_soak_tests.sh --tier {short,mid,long}")
    duration_s = SOAK_TIER_SECONDS[tier]
    # Passive observation only (tail_log(), never exec()/run_isolated() - see harness.Board's own
    # docstrings for why). Pass condition: no unexpected reboot (boot-time log lines reappearing
    # mid-window) and no raised exception/traceback over the soak window.
    lines = board.tail_log(duration_s=duration_s)
    joined = "\n".join(lines)
    # "CFGMGR_" is a per-line module-tag prefix (fires on every routine config read), not a one-time
    # boot marker - use the two genuinely one-time-per-setup() ConfigManager/FRAM messages instead.
    reboot_markers = [ln for ln in lines if "config is ready" in ln or "FRAM SPI FRAM Driver Setup complete" in ln]
    traceback_markers = [ln for ln in lines if "Traceback" in ln or "MemoryError" in ln]
    assert not reboot_markers, f"observed what looks like an unexpected mid-soak reboot (WDT starvation?) - boot markers: {reboot_markers}\nfull log:\n{joined}"
    assert not traceback_markers, "observed an unexpected traceback/MemoryError during the soak window:\n" + "\n".join(traceback_markers)
