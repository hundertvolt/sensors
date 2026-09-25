"""Tests scripts/_digital_twin_ci_suite.py's pure Run 11 (soak) helpers - _parse_mem_samples()
and _mem_trend() - with no live twin subprocess. Host-driven request cycling itself is exercised
end to end by scripts/run_digital_twin_ci.sh (SPECIFICATION.md Part E.9), not re-mocked here."""

from types import ModuleType

# ---------------------------------------------------------------------------
# _parse_mem_samples(): the log-scraping half of the "gc.mem_free() has no other source"
# exception (Part I.4(e)), reading _mem_sampler()'s MEM_SAMPLE lines back out of the twin's
# captured stdout - the pattern _would_have_triggered_count() already uses.
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
    # 20 samples at quarter_size 5, declining 15000 bytes a sample: the early-to-late trend of
    # 225000 is far past the ~63639 tolerance that decline's own within-quarter spread produces.
    # A genuine leak dwarfs even the noise its own progression adds to each quarter.
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


def test_mem_trend_tolerance_is_zero_for_a_perfectly_noiseless_flat_profile(ci_suite: ModuleType) -> None:
    # A degenerate edge worth pinning: zero within-quarter spread means zero tolerance, not a
    # historical floor. No real trace is this quiet, but the formula must degrade to exactly
    # this at the limit.
    samples = [123_456] * 100
    result = ci_suite._mem_trend(samples)
    assert result is not None
    trend, tolerance, quarter, _early_avg, _late_avg = result
    assert quarter == 25
    assert trend == 0
    assert tolerance == 0


def test_mem_trend_tolerance_scales_with_each_attempts_own_observed_noise(ci_suite: ModuleType) -> None:
    # The core property the design exists for: the SAME 200-byte decline gets a tighter
    # tolerance from a quiet quarter than a noisy one, each attempt tracking its own noise level
    # rather than a fixed constant real autocorrelated sampling never matched.
    quiet = [100_010, 99_990, 100_010, 99_990, 99_810, 99_790, 99_810, 99_790]
    noisy = [100_500, 99_500, 100_500, 99_500, 99_600, 100_400, 99_600, 100_400]
    quiet_result = ci_suite._mem_trend(quiet)
    noisy_result = ci_suite._mem_trend(noisy)
    assert quiet_result is not None
    assert noisy_result is not None
    _quiet_trend, quiet_tolerance, _q1, _e1, _l1 = quiet_result
    _noisy_trend, noisy_tolerance, _q2, _e2, _l2 = noisy_result
    assert noisy_tolerance > quiet_tolerance > 0
