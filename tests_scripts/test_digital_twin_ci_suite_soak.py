"""Tests scripts/_digital_twin_ci_suite.py's Run 11 (soak) and main(): _parse_mem_samples(), _mem_trend(), the warm-up that
ends once the sampled floor holds, _run_11_soak()'s one-boot verdict over a stubbed twin, a missing API reference, a held
port and the log default. The real twin runs it in scripts/run_digital_twin_ci.sh (SPECIFICATION.md Part E.9)."""

import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# A fixture device's GET routes: each soak cycle walks them and the static site.
_ROUTES = ("/measurements", "/status")
_PER_CYCLE = len(_ROUTES) + 1
_SETTLED_AT = 30  # the cycle from which the settling fixture's floor holds

# ---------------------------------------------------------------------------
# _parse_mem_samples(): the log-scraping half of the "gc.mem_free() has no other source"
# exception (Part I.4(e)), reading _mem_sampler()'s MEM_SAMPLE lines back out of the twin's
# captured stdout - the pattern _would_have_triggered_count() already uses.
# ---------------------------------------------------------------------------


def test_parse_mem_samples_extracts_timestamp_and_byte_count_pairs(ci_suite: ModuleType) -> None:
    log_text = (
        "digital_twin/run_generic_integration.py starting - device='fixture_device' ...\n"
        "MEM_SAMPLE 1789361162.123 1355680\n"
        "SYSTEM some other verbose log line\n"
        "MEM_SAMPLE 1789361162.456 1348800"
    )
    assert ci_suite._parse_mem_samples(log_text) == [(1789361162.123, 1355680), (1789361162.456, 1348800)]


def test_parse_mem_samples_returns_empty_list_when_sampler_was_never_armed(ci_suite: ModuleType) -> None:
    log_text = "digital_twin/run_generic_integration.py starting - device='fixture_device' ...\nOK: something"
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


# ---------------------------------------------------------------------------
# The summary block (SPECIFICATION.md E.10): main() prints it on every exit, each check counted
# under its pass label, a pass that recorded no check counted as having checked nothing.
# ---------------------------------------------------------------------------


def _flat(i: int) -> int:
    return 1_000_000 + 10 * (i % 2)


@pytest.mark.usefixtures("own_lock_root")
def test_a_missing_wiring_plan_prints_the_block_and_fails(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _fresh_summary(ci_suite, monkeypatch)  # main() replaces it; registered so it is restored
    monkeypatch.setattr(ci_suite, "GENERATED_SRC_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["_digital_twin_ci_suite.py", "--micropython-bin", "mp", "--device", "fixture_device", "--logs-dir", str(tmp_path / "logs")])
    assert ci_suite.main() == 1
    out = capsys.readouterr().out
    block = out[out.index("== Summary: scripts/_digital_twin_ci_suite.py ==") :]
    assert "\nLevels: L2 (fixture_device)\nGC stage: both\n" in block
    assert f"Failed:\n  - wiring plan {tmp_path / 'sensortask_fixture_device_wiring_plan.json'} missing" in block
    assert block.endswith("Result: FAIL\nExit code: 1\n")


@pytest.mark.usefixtures("own_lock_root")
def test_a_missing_api_reference_prints_the_block_and_fails(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # The route sets come from the device's API reference: without it no run knows what to drive.
    _fresh_summary(ci_suite, monkeypatch)
    monkeypatch.setattr(ci_suite, "GENERATED_SRC_DIR", tmp_path)
    (tmp_path / "sensortask_fixture_device_wiring_plan.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["_digital_twin_ci_suite.py", "--micropython-bin", "mp", "--device", "fixture_device", "--logs-dir", str(tmp_path / "logs")])
    assert ci_suite.main() == 1
    out = capsys.readouterr().out
    assert f"API reference {tmp_path / 'api' / 'fixture_device.json'} missing" in out, out


def test_the_logs_default_to_the_devices_own_directory(ci_suite: ModuleType) -> None:
    args = ci_suite._build_parser().parse_args(["--micropython-bin", "mp", "--device", "fixture_device"])
    assert ci_suite._logs_dir(args) == ci_suite.REPO_ROOT / "digital_twin_ci_logs" / "fixture_device"
    given = ci_suite._build_parser().parse_args(["--micropython-bin", "mp", "--device", "fixture_device", "--logs-dir", "elsewhere"])
    assert ci_suite._logs_dir(given) == Path("elsewhere")


def test_a_held_product_port_fails_the_suite_at_once_naming_it(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], own_lock_root: Path) -> None:
    _fresh_summary(ci_suite, monkeypatch)
    passes: list[object] = []
    monkeypatch.setattr(ci_suite, "_run_both_passes", passes.append)
    holder = subprocess.Popen(["sleep", "60"])  # coreutils sleep, the stand-in holder's process
    lock = own_lock_root / "sensors-port-53.lock"
    lock.mkdir()
    (lock / "runner").write_text("another suite\n", encoding="utf-8")
    (lock / "pid").write_text(f"{holder.pid}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["_digital_twin_ci_suite.py", "--micropython-bin", "mp", "--device", "fixture_device"])
    try:
        assert ci_suite.main() == 1
    finally:
        holder.kill()
        holder.wait()
    captured = capsys.readouterr()
    assert passes == [] and "port 53 is held by another suite" in captured.err, captured


def _fresh_summary(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> object:
    summary = ci_suite.Summary("scripts/_digital_twin_ci_suite.py", unit="checks")
    monkeypatch.setattr(ci_suite, "_SUMMARY", summary)
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_CHECKS_PER_PASS", {})
    # Registered so the label run_suite() sets is restored: the module is shared across files.
    monkeypatch.setattr(ci_suite, "_CURRENT_PASS_LABEL", "")
    return summary


def test_each_check_is_recorded_under_its_pass_label(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    summary = _fresh_summary(ci_suite, monkeypatch)
    monkeypatch.setattr(ci_suite, "_CURRENT_PASS_LABEL", "[gc.threshold=-1] ")
    ci_suite._check(condition=True, msg="Run 1: served")
    ci_suite._check(condition=False, msg="Run 2: persisted")
    assert summary.passed == [("[gc.threshold=-1] Run 1: served", "")]  # type: ignore[attr-defined]
    assert summary.failed == [("[gc.threshold=-1] Run 2: persisted", "")]  # type: ignore[attr-defined]


def test_a_pass_that_recorded_no_check_checked_nothing(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    summary = _fresh_summary(ci_suite, monkeypatch)
    _stub_runs(ci_suite, monkeypatch, lambda *_args: {})
    ctx = ci_suite.RunContext(micropython_bin="mp", logs_dir=tmp_path, device="fixture_device", module="m", wiring_plan_path=tmp_path / "p.json", instances=(), gc_threshold=-1, routes=_ROUTES)
    ci_suite.run_suite(ctx)
    assert summary.vacuous == [("pass [gc.threshold=-1]", "")]  # type: ignore[attr-defined]


def test_an_aborted_pass_is_recorded_and_the_error_still_raised(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    summary = _fresh_summary(ci_suite, monkeypatch)

    def boom(*_args: object) -> object:
        raise RuntimeError("twin never started")

    _stub_runs(ci_suite, monkeypatch, boom)
    ctx = ci_suite.RunContext(micropython_bin="mp", logs_dir=tmp_path, device="fixture_device", module="m", wiring_plan_path=tmp_path / "p.json", instances=(), gc_threshold=32768, routes=_ROUTES)
    with pytest.raises(RuntimeError, match="twin never started"):
        ci_suite.run_suite(ctx)
    assert summary.failed == [("[gc.threshold=32768] suite aborted: RuntimeError: twin never started", "")]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# _run_11_soak(): one boot, one verdict. A pass on a second boot never covers a first boot's
# failing trend, since a retry is no race fix; the twin and its HTTP are stubbed, the trend is real.
# ---------------------------------------------------------------------------


# The runner's own shutdown line, every field it prints, after the GC summary it prints first (digital_twin/run_generic_integration.py).
_SHUTDOWN_LINE = (
    " No. of 1-blocks: 14, 2-blocks: 4, max blk sz: 9, max free sz: 64730\n"
    "digital_twin/run_generic_integration.py [fixture_device] shutdown: would_have_triggered_count=0 feed_count=1 largest_feed_gap_ms=1 "
    "wdt_timeout_ms=8000 mem_backup: r0=0x00000000,0x00000000,0x00000000,0x00000000 public_destinations_refused=0 flash_stall_longest_ms=0 "
    "gc_block_bytes=32"
)


def _leaking(i: int) -> int:
    return 1_000_000 - 1_000 * i


def _settling(i: int) -> int:
    # Free bytes falling one step a request until cycle _SETTLED_AT, then flat: a heap that reaches its plateau.
    return 1_000_000 - 1_000 * min(i, _SETTLED_AT * _PER_CYCLE)


def _soak_with_boots(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boots: "list[Callable[[int], int]]", *, warmup_cycles: int = 1) -> "tuple[object, list[Path], int]":
    # Runs _run_11_soak() over stubbed boots: boot k's request i, warm-up included, prints a MEM_SAMPLE of boots[k](i)
    # free bytes, as the twin's sampler does; returns the summary, the boots and the requests sent.
    summary = _fresh_summary(ci_suite, monkeypatch)
    monkeypatch.setattr(ci_suite, "_SOAK_WARMUP_CYCLES", warmup_cycles)
    monkeypatch.setattr(ci_suite, "_SOAK_CYCLES", 8)
    spawned: list[Path] = []
    calls = {"n": 0}

    def spawn(_ctx: object, _args: object, log_path: Path) -> object:
        spawned.append(log_path)
        log_path.write_text("", encoding="utf-8")
        calls["n"] = 0
        return object()

    def http(_method: str, _path: str) -> "tuple[int, dict[str, object]]":
        calls["n"] += 1
        free = boots[min(len(spawned), len(boots)) - 1](calls["n"])
        with spawned[-1].open("a", encoding="utf-8") as log:
            log.write(f"MEM_SAMPLE {ci_suite.time.time()} {free}\n")
        return ci_suite._HTTP_OK, {}

    def shutdown(_proc: object, _label: str) -> int:
        with spawned[-1].open("a", encoding="utf-8") as log:
            log.write(f"{_SHUTDOWN_LINE}\n")
        return 0

    monkeypatch.setattr(ci_suite, "_archive_state", lambda _ctx, _label: None)
    monkeypatch.setattr(ci_suite, "_spawn", spawn)
    monkeypatch.setattr(ci_suite, "_wait_until_serving", lambda _proc: None)
    monkeypatch.setattr(ci_suite, "_http", http)
    monkeypatch.setattr(ci_suite, "_shutdown", shutdown)
    ctx = ci_suite.RunContext(micropython_bin="mp", logs_dir=tmp_path, device="fixture_device", module="m", wiring_plan_path=tmp_path / "p.json", instances=(), gc_threshold=-1, routes=_ROUTES)
    ci_suite._run_11_soak(ctx)
    return summary, spawned, calls["n"]


def _stub_runs(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, body: "Callable[[object], object]") -> None:
    for name in [n for n in dir(ci_suite) if n.startswith("_run_") and n[5].isdigit()]:
        monkeypatch.setattr(ci_suite, name, body)


@pytest.fixture
def own_lock_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # main() takes the product's fixed ports: a lock root of the test's own and no inherited chain.
    for name in ("SENSORS_PORT_LOCKS_HELD", "SENSORS_PORT_LOCK_OWNER"):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "runtime"
    root.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(root))
    return root


def test_a_failing_trend_fails_the_suite_with_no_second_boot(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    summary, spawned, _sent = _soak_with_boots(ci_suite, tmp_path, monkeypatch, [_leaking, _flat])
    assert spawned == [tmp_path / "run11_soak.log"], "Run 11 boots exactly once"
    failed = [name for name, _ in summary.failed]  # type: ignore[attr-defined]
    assert len(failed) == 1, failed
    assert "Run 11" in failed[0] and "trend" in failed[0], failed
    out = capsys.readouterr().out.lower()
    assert "retry" not in out and "attempt" not in out, out


def test_a_trend_within_tolerance_passes_on_its_one_boot(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    summary, spawned, _sent = _soak_with_boots(ci_suite, tmp_path, monkeypatch, [_flat])
    assert spawned == [tmp_path / "run11_soak.log"]
    assert summary.failed == []  # type: ignore[attr-defined]
    assert any("trend" in name for name, _ in summary.passed), summary.passed  # type: ignore[attr-defined]


def test_the_warm_up_ends_once_the_sampled_floor_holds_for_its_window(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The floor is new on every cycle until _SETTLED_AT, then holds: the warm-up ends a window later, far inside its bound.
    summary, _spawned, sent = _soak_with_boots(ci_suite, tmp_path, monkeypatch, [_settling], warmup_cycles=100)
    warmed = sent // _PER_CYCLE - ci_suite._SOAK_CYCLES
    assert warmed == _SETTLED_AT + ci_suite._SOAK_PLATEAU_CYCLES, warmed
    assert summary.failed == []  # type: ignore[attr-defined]


def test_a_floor_that_never_holds_warms_up_to_the_bound(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _summary, _spawned, sent = _soak_with_boots(ci_suite, tmp_path, monkeypatch, [_leaking], warmup_cycles=40)
    assert sent // _PER_CYCLE - ci_suite._SOAK_CYCLES == 40
