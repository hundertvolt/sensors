"""Flash-tier automated tests: real GC-heap headroom once the whole object graph exists, and real
single-core timing headroom under normal full task load (real 133MHz), matching SPECIFICATION.md
Parts I and F.3. The real-HTTP-soak variants live in bench/ - this tier has no network client."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from soak_tiers import SOAK_TIER_SECONDS

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def test_real_gc_heap_headroom_survives_a_full_system_build(board: Board) -> None:
    # The one memory figure no fake can produce: the RP2040's real 264KB SRAM minus the firmware's
    # own static footprint, measured after the real dev object graph exists. Its floors exist to
    # catch a regression in that footprint - notably a future MicroPython bump relocating more code
    # into SRAM, as 1.29 already did with the interpreter core (Part F.5.3's 12,918 B).
    output = board.run_isolated(DEVICE_SCRIPTS / "heap_headroom_after_full_system_build.py", timeout_s=120.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"real heap-headroom check failed: {match.group(2).strip()}\nfull output:\n{output}"


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
