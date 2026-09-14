"""Tests scripts/_digital_twin_ci_suite.py's own pure Run 11 (soak) helpers - _parse_mem_samples()
and _mem_trend() - without a live twin subprocess/HTTP server. Host-driven request-cycling itself
(the actual fix - SPECIFICATION.md's "Driver/DUT process separation" Part) is exercised for real by
scripts/run_digital_twin_ci.sh's own end-to-end run, not re-mocked here."""

from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module


@pytest.fixture(scope="session")
def ci_suite(repo_root: Path) -> ModuleType:
    """Imports scripts/_digital_twin_ci_suite.py as a real module (it's a `uv run`-style
    standalone script, not a package member) so _parse_mem_samples()/_mem_trend() can be checked
    directly instead of only through a real subprocess run."""
    return load_script_module(repo_root / "scripts" / "_digital_twin_ci_suite.py", "_digital_twin_ci_suite")


# ---------------------------------------------------------------------------
# _parse_mem_samples() - the log-line-scraping half of the "gc.mem_free() has no other source"
# exception (SPECIFICATION.md Part I.4(e)) - reads digital_twin/run_generic_integration.py's own
# _mem_sampler() output ("MEM_SAMPLE <time.time()> <gc.mem_free()>") back out of the twin's
# captured stdout, the same pattern _would_have_triggered_count() already uses for that value.
# ---------------------------------------------------------------------------


def test_parse_mem_samples_extracts_timestamp_and_byte_count_pairs(ci_suite: ModuleType) -> None:
    log_text = (
        "digital_twin/run_generic_integration.py starting - device='wozi' ...\n"
        "MEM_SAMPLE 1789361162.123 1355680\n"
        "SYSTEM some other verbose log line\n"
        "MEM_SAMPLE 1789361162.456 1348800"
    )
    assert ci_suite._parse_mem_samples(log_text) == [(1789361162.123, 1355680), (1789361162.456, 1348800)]


def test_parse_mem_samples_returns_empty_list_when_sampler_was_never_armed(ci_suite: ModuleType) -> None:
    log_text = "digital_twin/run_generic_integration.py starting - device='wozi' ...\nOK: something"
    assert ci_suite._parse_mem_samples(log_text) == []


def test_parse_mem_samples_skips_a_malformed_line_instead_of_raising(ci_suite: ModuleType) -> None:
    # A truncated write (process killed mid-line) must not crash the whole parse - the surrounding
    # well-formed samples are still worth having.
    log_text = "MEM_SAMPLE 1789361162.123 1355680\nMEM_SAMPLE not-a-timestamp not-a-number\nMEM_SAMPLE 1789361162.456 1348800"
    assert ci_suite._parse_mem_samples(log_text) == [(1789361162.123, 1355680), (1789361162.456, 1348800)]


# ---------------------------------------------------------------------------
# _mem_trend() - the pure trend-vs-tolerance arithmetic split out of _run_11_soak() specifically so
# it's testable without a live process (mirrors the now-retired digital_twin-side _soak() tests'
# own _ScriptedGc mock, but host-side there's no gc module to mock - just a plain sample list).
# ---------------------------------------------------------------------------


def test_mem_trend_flags_a_genuine_steady_decline(ci_suite: ModuleType) -> None:
    # 20 samples (quarter_size=5), a steady decline of 15000 bytes/sample - early_avg (first
    # quarter) vs. late_avg (last quarter) trend is comfortably past the scaled tolerance
    # (8192 * sqrt(25/5) ~= 18318, matching the real 20-cycle default's own quarter size).
    samples = [200_000 - 15_000 * i for i in range(20)]
    result = ci_suite._mem_trend(samples)
    assert result is not None
    trend, tolerance, quarter, _early_avg, _late_avg = result
    assert quarter == 5
    assert trend > tolerance


def test_mem_trend_does_not_flag_a_flat_profile(ci_suite: ModuleType) -> None:
    samples = [100_000] * 20
    result = ci_suite._mem_trend(samples)
    assert result is not None
    trend, tolerance, _quarter, _early_avg, _late_avg = result
    assert trend <= tolerance


def test_mem_trend_does_not_flag_memory_that_increased(ci_suite: ModuleType) -> None:
    # A negative trend (memory went UP between quarters) must never itself be a failure - only a
    # genuine decline past tolerance is.
    samples = [100_000 + 15_000 * i for i in range(20)]
    result = ci_suite._mem_trend(samples)
    assert result is not None
    trend, tolerance, _quarter, _early_avg, _late_avg = result
    assert trend < 0
    assert trend <= tolerance


def test_mem_trend_returns_none_below_four_samples(ci_suite: ModuleType) -> None:
    # Needs at least 4 samples for quarter_size >= 1 to mean anything - the caller's own _check()
    # reports this case as its own failure rather than silently skipping the trend check.
    assert ci_suite._mem_trend([100_000, 90_000, 80_000]) is None


def test_mem_trend_tolerance_reduces_to_the_original_flat_constant_at_25_sample_quarters(ci_suite: ModuleType) -> None:
    # The scaled tolerance is defined to exactly reproduce the original flat 8192-byte constant at
    # its own original calibration sample size (100 samples = 25-sample quarters) - see
    # _MEM_TREND_TOLERANCE_BYTES_AT_25_SAMPLES's own module-level comment.
    samples = [0] * 100
    result = ci_suite._mem_trend(samples)
    assert result is not None
    _trend, tolerance, quarter, _early_avg, _late_avg = result
    assert quarter == 25
    assert tolerance == pytest.approx(8192)
