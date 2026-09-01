"""Flash-tier automated tests, Part 1 category A (tmp_hardware_test_candidates.md items 1-6): real
bus/electrical timing that no simulation (mock or digital twin) can produce. Isolated-driver mode
throughout (HARDWARE_TEST_PLAN.md §6.2) - each check is a small `mpremote run` script in
tests_hardware/device_scripts/, chosen so this file never needs to know it's talking over serial.

Run via `uv run pytest tests_hardware/flash/test_bus_electrical_timing.py` (fast items) or with
`--run-long-soak` for items 1 and 6, which are inherently multi-hour/multi-day passive observations,
not something a single mpremote invocation can force to happen on demand."""

from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

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
# Item 4 - SCD30 RDY pin real IRQ edge. DESCOPED - see finding below, not silently dropped.
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "Descoped, not just unimplemented - a real finding from this session's own datasheet/source "
        "cross-check, not an oversight: the physical SCD30 module does have a real RDY pin "
        "('Data ready pin. High when data is ready for read-out' - datasheets/scd30/"
        "Sensirion_CO2_Sensors_SCD30_Datasheet.pdf, Figure 2 pin-out), and digital_twin/_scd30_chip.py "
        "does model a simulated RDY-pin IRQ edge (Scd30Chip's rdy_pin/simulate_edge()) - but "
        "src/asy_scd30_driver.py never wires a GPIO to it: sensortask_wozi.py constructs "
        "SCD30_Reader(i2c0, 8, trigger_sec=3, ...) with no pin argument at all, and grepping "
        "asy_scd30_driver.py for 'rdy' finds nothing. The real driver polls the I2C 'get data ready "
        "status' command (0x0202) on a timer instead. So there is no real code path this candidate's "
        "own framing ('confirm a real rising edge... drives the same code path the twin's simulated "
        "RDY pin exercises') can actually test - the twin models a capability the real wiring never "
        "uses. Flagged to the project owner rather than silently dropped or silently faked: either "
        "wire a real RDY pin into asy_scd30_driver.py (a real src/ change, its own scoped decision) "
        "and reinstate this test, or treat digital_twin/_scd30_chip.py's rdy_pin support as covering "
        "a capability not currently exercised by any real wiring and adjust its own docstring "
        "accordingly - not this session's call to make either way."
    )
)
def test_scd30_rdy_pin_real_irq_edge() -> None:
    raise AssertionError("should never run - see skip reason")


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
    if not request.config.getoption("--run-long-soak"):
        pytest.skip("real SCD30 clock-stretch events are opportunistic (~once/day) - pass --run-long-soak to actually watch for one")
    # A multi-day watch: tails the live, already-running system's own log output (harness.Board.tail_log()
    # - never interrupts it, see that method's docstring for why exec()/run_isolated() can't be used
    # here) for an unexpected OSError/ETIMEDOUT line from the SCD30's own I2C bus. Absence of such a
    # line over the watch window is the pass condition - there's no positive "a stretch definitely
    # happened and was within budget" signal available without instrumenting asy_scd30_driver.py
    # itself (out of scope for a test-only change), so this is a "never observed to fail" soak, not a
    # "confirmed to have been exercised" one - worth being explicit about that limit, not overselling it.
    duration_s = request.config.getoption("--long-soak-seconds")
    lines = board.tail_log(duration_s=duration_s)
    suspicious = [ln for ln in lines if "ETIMEDOUT" in ln or ("SCD30" in ln and "OSError" in ln)]
    assert not suspicious, "observed a suspicious SCD30/I2C error during the soak window:\n" + "\n".join(suspicious)


# ---------------------------------------------------------------------------
# Item 6 - time.ticks_ms() real 2**30 rollover (~12.4 days). See harness docstrings for the open
# "does soft_reset() reset the underlying counter?" question this design depends on.
# ---------------------------------------------------------------------------


@pytest.mark.long_soak
def test_ticks_ms_real_2pow30_rollover(board, request) -> None:
    if not request.config.getoption("--run-long-soak"):
        pytest.skip("real ~12.4-day wait for the actual 2**30 rollover - pass --run-long-soak to actually run this")
    # NEEDS VERIFICATION FIRST (see harness.py's tail_log() docstring and this module's own header):
    # whether machine.soft_reset() resets the hardware counter time.ticks_ms() is derived from. If it
    # does, board.exec() calls spaced across this multi-day window would themselves corrupt the
    # measurement (each interrupts via Ctrl-C, though - not soft-reset - unless mpremote's own
    # _auto_soft_reset default fires one; confirm this on the very first real attempt before trusting
    # the result, per this file's own "flag, don't assume" standard applied to itself).
    before_output = board.exec("import time; print('RESULT: PASS ticks_ms=' + str(time.ticks_ms()))")
    before = int(before_output.strip().split("=")[-1])
    target_wait_s = ((2**30) - before) / 1000.0 + 60  # +60s headroom past the exact boundary
    deadline = time.monotonic() + target_wait_s
    wrapped = False
    poll_interval_s = max(request.config.getoption("--long-soak-seconds") / 20, 3600.0)  # coarse polling - this is a multi-day wait, not a tight loop
    while time.monotonic() < deadline:
        time.sleep(min(poll_interval_s, max(deadline - time.monotonic(), 0)))
        check_output = board.exec("import time; print('RESULT: PASS ticks_ms=' + str(time.ticks_ms()))")
        now = int(check_output.strip().split("=")[-1])
        if now < before:
            wrapped = True
            break
        before = now
    assert wrapped, f"time.ticks_ms() never wrapped below its own earlier value within {target_wait_s:.0f}s"
