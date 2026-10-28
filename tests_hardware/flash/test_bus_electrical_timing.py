"""Flash-tier tests of real bus/electrical timing no simulation reproduces, through isolated-driver scripts. The
clock-stretch soak needs --soak-duration."""

import errno
from typing import Protocol

import pytest
from harness import DEVICE_SCRIPTS_DIR, Board, crash_lines, parse_facts
from soak_durations import SOAK_DURATION_SECONDS


class _ResultNote(Protocol):
    # The root conftest's result_note fixture.
    def __call__(self, text: str, *, recovery: bool = False) -> None: ...


COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("scd30",)

# @tunable l3.bus_electrical_timing_irq_script_timeout_s = 30.0
_IRQ_SCRIPT_TIMEOUT_S = 30.0
# Twelve timers armed back to back: past this the arming itself, not the scheduler, would be what is measured.
# @tunable l3.bus_electrical_timing_arming_span_max_us = 1500
_ARMING_SPAN_MAX_US = 1500
# Three scans and two radio re-inits per value, three values.
# @tunable l3.bus_electrical_timing_country_script_timeout_s = 120.0
_COUNTRY_SCRIPT_TIMEOUT_S = 120.0


# The soft-Timer callback drop under a forced scheduler saturation.
def test_soft_timer_callback_drop_self_heals_under_scheduler_saturation(board: Board) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "scheduler_saturation_drop.py"))
    n_timers, depth, span = facts["n_timers"], facts["depth"], facts["arming_span_us"]
    assert isinstance(n_timers, int) and isinstance(depth, int) and isinstance(span, int), facts
    assert span <= _ARMING_SPAN_MAX_US, f"arming the timers took {span} us, bound {_ARMING_SPAN_MAX_US} us"
    dropped = facts["dropped"]
    assert isinstance(dropped, int) and dropped >= n_timers - depth, f"{dropped} of {n_timers} timers dropped with a scheduler depth of {depth}: the drop was not forced"
    assert facts["all_self_healed"] is True, f"a timer never fired again after the drop: busy {facts['counts_busy']}, heal {facts['counts_heal']}"


# Timer.init()'s OSError(ENOMEM) once the hardware alarm pool is exhausted.
def test_timer_init_raises_enomem_when_real_alarm_pool_is_exhausted(board: Board, result_note: _ResultNote) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "timer_alarm_pool_exhaustion.py"))
    result_note(f"constructed={facts['constructed']}: the alarms free beside the image's other pool users")
    assert facts["raised"] is True, f"no OSError after constructing {facts['constructed']} Timers"
    assert facts["errno"] == errno.ENOMEM, f"Timer.init() raised errno {facts['errno']}, expected ENOMEM ({errno.ENOMEM})"


# The SCD30 RDY edge driving a real read (a scope on the pin is the only certain check, E.6.6 row scd30-rdy-irq-vs-fallback).
def test_scd30_real_irq_edge_drives_a_real_read(board: Board, scd30_measuring: str) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "scd30_real_irq_edge.py", timeout_s=_IRQ_SCRIPT_TIMEOUT_S))
    assert facts["died"] == [], f"a reader task died: {facts['died']}"
    elapsed, deadline = facts["elapsed_ms"], facts["deadline_ms"]
    assert facts["co2"] is not None and isinstance(elapsed, int) and isinstance(deadline, int), f"no reading within the deadline (fallback {facts['trigger_s']} s): {facts}"
    assert elapsed <= deadline, f"the reading took {elapsed} ms, deadline {deadline} ms"


# The single-precision float boundary at 2**24, which only the real firmware's 24-bit mantissa shows.
def test_single_precision_float_boundary_at_2pow24(board: Board) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "float_boundary_2pow24.py"))
    assert facts["below_exact"] is True, f"2**24 - 1 did not round-trip: {facts}"
    assert facts["above_value"] == 2**24, f"2**24 + 1 came back as {facts['above_value']}, expected 2**24 (round to even on a 24-bit mantissa)"


# The radio's reaction to malformed country codes: recorded, never judged; the script restores what it found.
def test_a_malformed_country_code_reaction_is_recorded(board: Board, result_note: _ResultNote) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "wifi_country_code_reaction.py", timeout_s=_COUNTRY_SCRIPT_TIMEOUT_S))
    steps = [facts.get(f"value_{i}") for i in range(3)]
    assert all(isinstance(step, dict) and {"set", "radio_on", "readback"} <= set(step) for step in steps), f"a value's steps were not all reported: {steps}"
    result_note(f"country_before={facts['country_before']} reactions={steps}")
    assert facts["restored"] == "ok", f"the country and the radio were not restored: {facts['restored']}"


# The SCD30's real clock stretch under bus load: about once a day (Interface Description p.2), only watched for.
@pytest.mark.soak_duration
def test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout(board: Board, request: pytest.FixtureRequest) -> None:
    duration = request.config.getoption("--soak-duration")
    if duration is None:
        pytest.skip("real SCD30 clock stretches come about once a day - run scripts/run_bench_soak_tests.sh --duration {short,mid,long} to watch for one")
    # Proves only the absence of a failure over the window, never that a stretch happened inside it.
    lines = board.tail_log(duration_s=SOAK_DURATION_SECONDS[duration])
    suspicious = crash_lines(lines) + [line for line in lines if "ETIMEDOUT" in line or ("SCD30" in line and "OSError" in line)]
    assert not suspicious, "a crash or an SCD30/I2C error during the soak window:\n" + "\n".join(suspicious)
