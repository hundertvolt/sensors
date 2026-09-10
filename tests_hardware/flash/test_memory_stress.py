"""Flash-tier automated tests: real single-core timing headroom under normal full task load (sensor
reads + webserver + WiFi hotspot-fallback + Neopixel, real 133MHz), matching SPECIFICATION.md Part
F.3. Flash tier has no network client; the real-HTTP-soak variant is bench/test_end_to_end_timing.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from soak_tiers import SOAK_TIER_SECONDS

if TYPE_CHECKING:
    from harness import Board


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
