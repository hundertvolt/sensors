"""The skills' helpers (.claude/skills/), run as a session runs them: _log_verdict.py's reading of logs, consoles and
standard input; _errcount_digest.py's digest and diff; _failed_tests.py's rerun selection; _run_checks.sh's step
lines; _preflight.sh's readiness lines; _tidy.sh's report and the only deletions it makes."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = REPO_ROOT / "scripts"


def _run(script: str, *args: str, env: "dict[str, str] | None" = None, stdin: str = "", scripts: Path = _SCRIPTS) -> "subprocess.CompletedProcess[str]":
    command = ["bash", str(scripts / script)] if script.endswith(".sh") else [sys.executable, str(scripts / script)]
    return subprocess.run([*command, *args], cwd=REPO_ROOT, input=stdin, capture_output=True, text=True, timeout=120, check=False, env=env)


def _block(runner: str, *, result: str = "PASS", failed: "list[str] | None" = None, retried: "list[str] | None" = None, tag: str = "") -> str:
    lines = [f"== Summary: {runner} ==", "Commit: abc1234", "Levels: L1 PASS", "GC stage: -1", "Counts (files): passed 3 · failed 0 · skipped 2 · deselected 0 · retried 0 · recovered 0 · vacuous 0"]
    lines += ["Failed:", *(f"  - {f}" for f in failed)] if failed else ["Failed: none"]
    lines += ["Skipped:", "  - a: device wires no a", "  - b: device wires no b", "Deselected: none"]
    lines += ["Passed only on retry:", *(f"  - {r} (attempt 2/3)" for r in retried)] if retried else ["Passed only on retry: none"]
    lines += ["Recovery passes: none", "Notes: none", "Checked nothing: none", f"Result: {result}", f"Exit code: {0 if result == 'PASS' else 1}"]
    return "\n".join(tag + line for line in lines) + "\n"


def test_a_clean_block_is_one_line_and_not_notable(tmp_path: Path) -> None:
    (tmp_path / "a.log").write_text("noise\n" * 500 + _block("scripts/test.sh"), encoding="utf-8")
    run = _run("_log_verdict.py", str(tmp_path / "a.log"))
    assert run.returncode == 0, run.stdout
    assert run.stdout.splitlines()[1:] == ["PASS scripts/test.sh | L1 PASS | -1 | files: passed 3, skipped 2"]


def test_a_failed_block_is_shown_first_with_its_skips_folded(tmp_path: Path) -> None:
    text = _block("scripts/lint.sh") + _block("scripts/test.sh", result="FAIL", failed=["tests/test_x.py: 1 of 2 tests failed"])
    (tmp_path / "a.log").write_text(text, encoding="utf-8")
    run = _run("_log_verdict.py", str(tmp_path / "a.log"))
    assert run.returncode == 1
    assert run.stdout.index("Result: FAIL") < run.stdout.index("PASS scripts/lint.sh")
    assert "  - tests/test_x.py: 1 of 2 tests failed" in run.stdout
    assert "Skipped: 2 (listed in the log)" in run.stdout
    assert "device wires no" not in run.stdout


def test_a_pass_that_needed_a_retry_is_notable(tmp_path: Path) -> None:
    (tmp_path / "a.log").write_text(_block("scripts/test.sh", retried=["tests/test_y.py"]), encoding="utf-8")
    run = _run("_log_verdict.py", str(tmp_path / "a.log"))
    assert run.returncode == 1
    assert "  - tests/test_y.py (attempt 2/3)" in run.stdout


def test_interleaved_tagged_blocks_survive_progress_dots_and_a_cut_block_says_so(tmp_path: Path) -> None:
    first = _block("scripts/_digital_twin_scenarios.py", tag="[scenarios[x1]] ").replace("[scenarios[x1]] == Summary", "..[scenarios[x1]] == Summary")
    cut = _block("scripts/_digital_twin_scenarios.py", tag="[scenarios[x2]] ").splitlines()[:6]
    (tmp_path / "a.log").write_text(first + "\n".join(cut) + "\n", encoding="utf-8")
    out = _run("_log_verdict.py", str(tmp_path / "a.log")).stdout
    assert "PASS scripts/_digital_twin_scenarios.py | L1 PASS | -1 | files: passed 3, skipped 2" in out
    assert "(block cut off: the run ended before its Result and Exit code lines)" in out


def test_memory_markers_count_unquoted_ones_and_skip_a_gate_naming_them(tmp_path: Path) -> None:
    text = "OK: Run 1: log carries none of ('MemoryError', 'memory allocation failed')\nWEBSERVER caught: memory allocation failed, allocating 250 bytes\n"
    (tmp_path / "a.log").write_text(text, encoding="utf-8")
    run = _run("_log_verdict.py", str(tmp_path / "a.log"))
    assert run.returncode == 1
    assert "memory markers: 1 line(s)" in run.stdout
    assert "  line 2: WEBSERVER caught: memory allocation failed, allocating 250 bytes" in run.stdout
    assert "1 quoted mention(s) skipped" in run.stdout


def test_a_near_miss_is_a_gap_past_the_share_where_the_watchdog_never_fired(tmp_path: Path) -> None:
    line = "x [dev] shutdown: would_have_triggered_count={} feed_count=9 largest_feed_gap_ms={} wdt_timeout_ms=8000 mem_backup: r0=0x0\n"
    (tmp_path / "a.log").write_text(line.format(1, 9029) + line.format(0, 3458) + line.format(0, 6795), encoding="utf-8")
    out = _run("_log_verdict.py", str(tmp_path / "a.log")).stdout
    assert "largest feed gap 6795 of 8000 ms (85%) where the watchdog never fired; above 75%: 1; watchdog would have fired: 1" in out
    assert "  line 3: feed gap 6795 of 8000 ms" in out


def test_a_directory_shows_only_notable_files_and_unusable_logs_are_notable(tmp_path: Path) -> None:
    (tmp_path / "clean.log").write_text(_block("scripts/lint.sh"), encoding="utf-8")
    (tmp_path / "empty.out").write_text("", encoding="utf-8")
    (tmp_path / "blob.txt").write_bytes(bytes(range(128, 256)) * 8)
    run = _run("_log_verdict.py", str(tmp_path))
    assert run.returncode == 1
    assert "clean.log" not in run.stdout
    assert "empty log: no verdict" in run.stdout
    assert "not a UTF-8 text log: no verdict" in run.stdout
    assert run.stdout.splitlines()[-1] == "== 3 file(s) read, 2 notable, 2 shown"
    assert _run("_log_verdict.py", str(tmp_path / "missing.log")).returncode == 2


def _status(path: Path, **sources: "tuple[int, list[str]]") -> Path:
    table = {name: {"counter": counter, "history": [{"type": "N", "num": 0}] * 2 + [{"type": code[0], "num": int(code[1:])} for code in codes]} for name, (counter, codes) in sources.items()}
    path.write_text(json.dumps({"errcount": table}), encoding="utf-8")
    return path


def test_the_errcount_digest_lists_what_logged_and_the_diff_what_changed(tmp_path: Path) -> None:
    before = _status(tmp_path / "before.json", NTP=(0, []), SGP40=(17, ["W65", "W35"]), SYSTEM=(18, ["E126", "E125"]), WIFI=(3, ["W38"]))
    after = _status(tmp_path / "after.json", NTP=(1, ["E71"]), SGP40=(81, ["W65", "W35", "W33"]), SYSTEM=(2, ["E42"]), WIFI=(3, ["W38"]))
    single = _run("_errcount_digest.py", str(before))
    assert single.stdout.splitlines() == ["SGP40 counter=17 history=W65,W35", "SYSTEM counter=18 history=E126,E125", "WIFI counter=3 history=W38"]
    diff = _run("_errcount_digest.py", str(before), str(after))
    assert diff.returncode == 1
    assert diff.stdout.splitlines() == [
        "NTP counter 0->1 history - -> E71",
        "SGP40 counter 17->81 history W65,W35 -> W65,W35,W33",
        "SYSTEM counter 18->2 history E126,E125 -> E42 (cleared in between)",
        "1 source(s) unchanged",
    ]
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    assert _run("_errcount_digest.py", str(tmp_path / "bad.json")).returncode == 2


def test_failed_tests_select_failures_errors_and_collection_errors(tmp_path: Path) -> None:
    record = {
        "tests": [{"nodeid": "t.py::test_ok", "outcome": "passed"}, {"nodeid": "t.py::test_bad[2]", "outcome": "failed"}, {"nodeid": "t.py::test_bad[3]", "outcome": "failed"}, {"nodeid": "t.py::test_setup", "outcome": "error"}],
        "collection": [{"nodeid": "u.py", "outcome": "error"}],
    }
    (tmp_path / "run_record.json").write_text(json.dumps(record), encoding="utf-8")
    run = _run("_failed_tests.py", str(tmp_path / "run_record.json"))
    assert (run.returncode, run.stdout) == (1, "-k 'test_bad or test_setup or u.py'\n")
    exact = _run("_failed_tests.py", str(tmp_path / "run_record.json"), "--nodeids")
    assert exact.stdout.splitlines() == ["t.py::test_bad[2]", "t.py::test_bad[3]", "t.py::test_setup", "u.py"]
    (tmp_path / "green.json").write_text(json.dumps({"tests": record["tests"][:1]}), encoding="utf-8")
    assert _run("_failed_tests.py", str(tmp_path / "green.json")).returncode == 0


def test_the_runner_prints_one_line_and_a_verdict_per_step(tmp_path: Path) -> None:
    (tmp_path / "test_tiny.py").write_text("def test_one() -> None:\n    assert True\n\n\ndef test_two() -> None:\n    assert False\n", encoding="utf-8")
    env = {**os.environ, "VIRTUAL_ENV": str(Path(sys.executable).parent.parent), "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"}
    run = _run("_run_checks.sh", "-d", str(tmp_path / "logs"), f"py:{tmp_path / 'test_tiny.py'} -p no:randomly", env=env)
    assert run.returncode == 1, run.stdout + run.stderr
    head, *verdict = run.stdout.splitlines()
    assert head.startswith(f"py:{tmp_path / 'test_tiny.py'} -p no:randomly rc=1 ")
    assert verdict[0] == "  pytest: 1 failed, 1 passed in " + verdict[0].rsplit(" in ", 1)[1]
    assert any("test_tiny.py::test_two" in line for line in verdict)
    assert len(list((tmp_path / "logs").iterdir())) == 1


def test_standard_input_and_a_board_console_are_read(tmp_path: Path) -> None:
    console = "boot\nUART error: no ack\nWEBSERVER Unhandled exception in route handler: x\n"
    run = _run("_log_verdict.py", "-", stdin=console)
    assert (run.returncode, run.stdout.splitlines()[0]) == (1, "== <stdin> [NOTABLE]")
    assert "console: 1 'Unhandled exception' line(s), first at line 3" in run.stdout
    assert "console: 1 'UART error' line(s), first at line 2" in run.stdout
    assert _run("_log_verdict.py", "-", stdin="boot\nUART error: no ack\n").returncode == 0


def test_preflight_prints_one_verdict_line_per_fact_and_fails_only_on_a_fail_line() -> None:
    run = _run("_preflight.sh", "--bench")
    lines = run.stdout.splitlines()
    assert lines, run.stderr
    assert all(line.split(" ", 1)[0] in ("OK", "WARN", "FAIL") for line in lines), run.stdout
    assert run.returncode == (1 if any(line.startswith("FAIL") for line in lines) else 0)
    assert any(line.startswith(("OK bench:", "WARN bench:")) for line in lines)


def test_tidy_deletes_only_caches_and_old_check_logs(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    (tree / "scripts").mkdir(parents=True)
    shutil.copy(_SCRIPTS / "_tidy.sh", tree / "scripts" / "_tidy.sh")
    git = shutil.which("git")
    assert git, "git is not on PATH"
    subprocess.run([git, "init", "-q", str(tree)], check=True)
    for path in ("pkg/__pycache__/m.pyc", "tests/_tmp/t", "build/archive/run/record.json", "logs/x.log"):
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        (tree / path).write_text("x", encoding="utf-8")
    logs = tmp_path / "checks"
    (logs / "old").mkdir(parents=True)
    (logs / "new").mkdir()
    stamp = time.time() - 10 * 86400
    os.utime(logs / "old", (stamp, stamp))
    env = {**os.environ, "CHECK_LOG_DIR": str(logs)}
    report = _run("_tidy.sh", env=env, scripts=tree / "scripts")
    assert report.returncode == 0, report.stderr
    assert "caches: 1 folder(s)" in report.stdout
    assert (tree / "pkg/__pycache__").exists()
    clean = _run("_tidy.sh", "--caches", "--check-logs", "5", env=env, scripts=tree / "scripts")
    assert clean.returncode == 0, clean.stderr
    assert not (tree / "pkg/__pycache__").exists()
    assert not (tree / "tests/_tmp").exists()
    assert (tree / "build/archive/run/record.json").exists()
    assert (tree / "logs/x.log").exists()
    assert sorted(p.name for p in logs.iterdir()) == ["new"]
