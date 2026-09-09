"""Flash-tier automated tests: real bus/electrical timing that no simulation (mock or digital twin)
can reproduce, via isolated-driver `mpremote run` scripts. The clock-stretch check needs
`--soak-tier`; the ticks_ms rollover check needs `--allow-multi-day-rollover-wait` (~12.4-day wait)."""

from __future__ import annotations

import re
import time
from pathlib import Path

import pytest
from soak_tiers import SOAK_TIER_SECONDS

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def _parse_result(output: str) -> tuple[bool, str]:
    match = RESULT_RE.search(output)
    if match is None:
        raise AssertionError(f"device script printed no RESULT line - full output:\n{output}")
    return match.group(1) == "PASS", match.group(2).strip()


# ---------------------------------------------------------------------------
# Item 2 - soft Timer callback drop under real scheduler saturation.
# ---------------------------------------------------------------------------


def test_soft_timer_callback_drop_self_heals_under_scheduler_saturation(board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "scheduler_saturation_drop.py")
    ok, detail = _parse_result(output)
    assert ok, f"scheduler saturation probe failed: {detail}\nfull output:\n{output}"


# ---------------------------------------------------------------------------
# Item 3 - Timer.init() OSError(ENOMEM) under real hardware alarm-pool exhaustion.
# ---------------------------------------------------------------------------


def test_timer_init_raises_enomem_when_real_alarm_pool_is_exhausted(board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "timer_alarm_pool_exhaustion.py")
    ok, detail = _parse_result(output)
    assert ok, f"alarm-pool exhaustion probe failed: {detail}\nfull output:\n{output}"


# ---------------------------------------------------------------------------
# Item 4 - SCD30 real IRQ-pin edge. SCD30_Reader wires a real GPIO to IRQ_RISING plus a software
# self-healing fallback poll; can't fully disambiguate a genuine hardware edge from the fallback
# purely in software (a scope on the pin would be the only certain check).
# ---------------------------------------------------------------------------


def test_scd30_real_irq_edge_drives_a_real_read(board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "scd30_real_irq_edge.py", timeout_s=30.0)
    ok, detail = _parse_result(output)
    assert ok, f"SCD30 real IRQ-edge probe failed: {detail}\nfull output:\n{output}"


# ---------------------------------------------------------------------------
# Item 5 - single-precision float boundary (2**24), real hardware only.
# ---------------------------------------------------------------------------


def test_single_precision_float_boundary_at_2pow24(board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "float_boundary_2pow24.py")
    ok, detail = _parse_result(output)
    assert ok, f"float boundary probe failed: {detail}\nfull output:\n{output}"


# ---------------------------------------------------------------------------
# Item 1 - SCD30 real clock-stretch timing under genuine bus load. Opportunistic/long-duration:
# SCD30 stretches up to ~150ms roughly once per day for internal calibration (datasheets/scd30/
# ..._Interface_Description.pdf p.2, already cited in tests/test_sensortask_wozi.py's own
# test_scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it) - not something a script
# can force on demand, only watch for over an extended run.
# ---------------------------------------------------------------------------


@pytest.mark.long_soak
def test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout(board, request) -> None:
    tier = request.config.getoption("--soak-tier")
    if tier is None:
        pytest.skip("real SCD30 clock-stretch events are opportunistic (~once/day) - run via scripts/run_bench_soak_tests.sh --tier {short,mid,long} to actually watch for one")
    # Tails the live system's log (harness.Board.tail_log(), doesn't interrupt it) for an unexpected
    # OSError/ETIMEDOUT on SCD30's I2C bus - a "never observed to fail" soak, not "confirmed
    # exercised" (only the "long" tier runs long enough to likely observe the ~once/day event).
    duration_s = SOAK_TIER_SECONDS[tier]
    lines = board.tail_log(duration_s=duration_s)
    suspicious = [ln for ln in lines if "ETIMEDOUT" in ln or ("SCD30" in ln and "OSError" in ln)]
    assert not suspicious, "observed a suspicious SCD30/I2C error during the soak window:\n" + "\n".join(suspicious)


# ---------------------------------------------------------------------------
# Item 6 - time.ticks_ms() real 2**30 rollover (~12.4 days). See harness docstrings for the open
# "does soft_reset() reset the underlying counter?" question this design depends on.
# ---------------------------------------------------------------------------


@pytest.mark.multi_day_rollover
def test_ticks_ms_real_2pow30_rollover(board, request) -> None:
    # Deliberately its own separate marker/flag, never bundled with the long_soak/--soak-tier system
    # above - this wait is fixed by the real hardware counter's own current value (~12.4 days from
    # whenever it happens to run), not something any duration tier could meaningfully shorten.
    if not request.config.getoption("--allow-multi-day-rollover-wait"):
        pytest.skip("real ~12.4-day wait for the actual 2**30 rollover - pass --allow-multi-day-rollover-wait to actually run this (never bundled with --soak-tier)")
    # NEEDS VERIFICATION: whether machine.soft_reset() resets the ticks_ms() counter - see
    # BACKLOG.md's open question on this; confirm on the first real run before trusting the result.
    before_output = board.exec("import time; print('RESULT: PASS ticks_ms=' + str(time.ticks_ms()))")
    before = int(before_output.strip().split("=")[-1])
    target_wait_s = ((2**30) - before) / 1000.0 + 60  # +60s headroom past the exact boundary
    deadline = time.monotonic() + target_wait_s
    wrapped = False
    poll_interval_s = 3600.0  # coarse polling - this is a multi-day wait, not a tight loop
    while time.monotonic() < deadline:
        time.sleep(min(poll_interval_s, max(deadline - time.monotonic(), 0)))
        check_output = board.exec("import time; print('RESULT: PASS ticks_ms=' + str(time.ticks_ms()))")
        now = int(check_output.strip().split("=")[-1])
        if now < before:
            wrapped = True
            break
        before = now
    assert wrapped, f"time.ticks_ms() never wrapped below its own earlier value within {target_wait_s:.0f}s"
