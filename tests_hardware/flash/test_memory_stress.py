"""Flash-tier automated tests, Part 1 category D subset (tmp_hardware_test_candidates.md item 18
only - item 16 moved to bench, see below) - real single-core timing headroom under load, matching
SPECIFICATION.md Part F.3's "don't stall timing-sensitive work" principle on real silicon.

Item 16 (real-hardware memory-leak soak) moved to tests_hardware/bench/test_memory_stress_bench.py:
its own description explicitly requires "real firmware under HTTP soak traffic" - a real HTTP
client hammering the DUT's REST endpoints, which needs a reachable network client. Flash tier has
no network at all (HARDWARE_TEST_PLAN.md §2.3), so as tagged [USB] this candidate can't actually
run - the same tier-tagging gap as item 15 (see test_reboot_persistence.py's own note). Fixed here
by re-tagging rather than building an unrunnable test.

Item 18 itself is narrowed for the same reason: its own description also says "webserver + WiFi"
implying real HTTP soak traffic, but flash tier's WiFi service still runs its full normal state
machine even with no bench bridge to connect to (it just settles into its own hotspot fallback,
per src/asy_wifi_service.py's conn_fail_to_hotspot retry logic) - so "sensor reads + webserver +
WiFi + Neopixel animation all real, at real 133MHz" is achievable here MINUS actual external HTTP
client traffic. The bench-tier variant with real soak traffic added on top is
tests_hardware/bench/test_end_to_end_timing.py's job, not duplicated here."""

from __future__ import annotations

import pytest
from harness import Board
from soak_tiers import SOAK_TIER_SECONDS


@pytest.mark.long_soak
def test_single_core_timing_headroom_holds_under_normal_full_task_load(board: Board, request: pytest.FixtureRequest) -> None:
    tier = request.config.getoption("--soak-tier")
    if tier is None:
        pytest.skip("passive soak, one of three named duration tiers - run via scripts/run_bench_soak_tests.sh --tier {short,mid,long}")
    duration_s = SOAK_TIER_SECONDS[tier]
    # Passive observation only (tail_log(), never exec()/run_isolated() - see
    # harness.Board.run_isolated()'s own docstring for why those can't be trusted to leave the
    # live system's normal task graph undisturbed). The real, closable signal available without
    # instrumenting src/ itself for this test: no unexpected reboot (a real WDT-triggered reset -
    # SPECIFICATION.md Part F.2's 8388ms cap - would show up as the boot-time log lines this file's
    # test_reboot_persistence.py sibling already recognizes reappearing mid-window) and no raised
    # exception/traceback line, over an extended window of otherwise-normal live operation.
    lines = board.tail_log(duration_s=duration_s)
    joined = "\n".join(lines)
    # REAL FINDING, fixed (2026-09-04) - see test_memory_stress_bench.py's own sibling comment for
    # the full account: "CFGMGR_" is a per-log-line module-tag prefix, not a one-time boot marker -
    # it fires on every ordinary, routine config read (confirmed directly against a real soak run's
    # log, which showed it firing dozens of times with zero real reboots), not just at boot. Fixed
    # to the two genuinely one-time-per-setup() ConfigManager/FRAM messages instead.
    reboot_markers = [ln for ln in lines if "config is ready" in ln or "FRAM SPI FRAM Driver Setup complete" in ln]
    traceback_markers = [ln for ln in lines if "Traceback" in ln or "MemoryError" in ln]
    assert not reboot_markers, f"observed what looks like an unexpected mid-soak reboot (WDT starvation?) - boot markers: {reboot_markers}\nfull log:\n{joined}"
    assert not traceback_markers, "observed an unexpected traceback/MemoryError during the soak window:\n" + "\n".join(traceback_markers)
