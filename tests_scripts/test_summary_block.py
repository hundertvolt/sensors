"""The runner summary block (SPECIFICATION.md E.10) has three emitters - scripts/_summary_block.sh,
scripts/_summary_block.py and tests_js/_summary_layout.js - and one layout: each renders the same
canned input byte for byte, and the block's rules hold in every one."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

REPO_ROOT = Path(__file__).resolve().parent.parent
_SH = REPO_ROOT / "scripts" / "_summary_block.sh"
_PY = REPO_ROOT / "scripts" / "_summary_block.py"
_JS = REPO_ROOT / "tests_js" / "_summary_layout.js"

# One canned input: (kind, name, detail) items in insertion order, plus the block's optional lines.
_ITEMS = [
    ("passed", "test_a.py", ""),
    ("passed", "test_b.py", ""),
    ("failed", "test_c.py", "MemoryError seen"),
    ("failed", "test_d.py", ""),
    ("skipped", "test_e.py", "not run under --coverage (the plain pass runs them)"),
    ("deselected", "scenarios[dev]::dns", "runner selection: needs exclusive port 53 (run_digital_twin_ci.sh)"),
    ("retried", "test_f.py", "2/3"),
    ("recovered", "test_g.py", "hard reset fallback"),
    ("vacuous", "pass gc.threshold=-1", ""),
]


@pytest.fixture(scope="module")
def emitter() -> ModuleType:
    return load_script_module(_PY, "_summary_block")


def _env(cwd: Path) -> dict[str, str]:
    env = dict(os.environ)
    # Keeps `git` from walking up out of a tmp dir into an enclosing repository.
    env["GIT_CEILING_DIRECTORIES"] = str(cwd.parent)
    return env


def _bash(lines: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    script = "\n".join(["set -euo pipefail", f"source {shlex.quote(str(_SH))}", *lines])
    return subprocess.run(["/bin/bash", "-c", script], cwd=cwd, env=_env(cwd), capture_output=True, text=True, check=False)


Opts = dict[str, object]  # unit, levels, gc_stage, reason (str), extra (list of (unit, seven counts)), notes (list of (name, text))


def _bash_render(cwd: Path, runner: str, exit_code: int, items: list[tuple[str, str, str]], opts: Opts | None = None) -> str:
    opts = opts or {}
    unit, levels, gc_stage, reason = (opts.get(k) for k in ("unit", "levels", "gc_stage", "reason"))
    extra: list[tuple[str, list[int]]] = opts.get("extra") or []  # type: ignore[assignment]
    lines = []
    if unit is not None:
        lines.append(f"summary_unit {shlex.quote(str(unit))}")
    if levels is not None:
        lines.append(f"summary_levels {shlex.quote(str(levels))}")
    if gc_stage is not None:
        lines.append(f"summary_gc_stage {shlex.quote(str(gc_stage))}")
    if reason is not None:
        lines.append(f"summary_result_reason {shlex.quote(str(reason))}")
    for extra_unit, values in extra:
        lines.append("summary_counts_line " + " ".join(shlex.quote(str(v)) for v in [extra_unit, *values]))
    for kind, name, detail in items:
        lines.append(f"summary_add {shlex.quote(kind)} {shlex.quote(name)} {shlex.quote(detail)}")
    notes: list[tuple[str, str]] = opts.get("notes") or []  # type: ignore[assignment]
    for name, text in notes:
        lines.append(f"summary_note {shlex.quote(name)} {shlex.quote(text)}")
    lines.append(f'rc=0; summary_print {shlex.quote(runner)} {exit_code} || rc=$?; echo "returned=$rc" >&2')
    result = _bash(lines, cwd)
    assert result.returncode == 0, result.stderr
    # summary_print returns the code it printed, which every caller exits with.
    returned = int(result.stderr.rsplit("returned=", 1)[1])
    assert result.stdout.endswith(f"Exit code: {returned}\n"), (returned, result.stdout)
    return result.stdout


def _py_render(emitter: ModuleType, cwd: Path, runner: str, exit_code: int, items: list[tuple[str, str, str]], opts: Opts | None = None) -> str:
    opts = opts or {}
    summary = emitter.Summary(runner) if opts.get("unit") is None else emitter.Summary(runner, unit=opts["unit"])
    summary.levels = opts.get("levels")
    summary.gc_stage = opts.get("gc_stage")
    summary.not_clean_reason = opts.get("reason")
    extra: list[tuple[str, list[int]]] = opts.get("extra") or []  # type: ignore[assignment]
    for extra_unit, values in extra:
        summary.extra_counts.append((extra_unit, emitter.Counts(*values)))
    for kind, name, detail in items:
        summary.add(kind, name, detail)
    notes: list[tuple[str, str]] = opts.get("notes") or []  # type: ignore[assignment]
    for name, text in notes:
        summary.note(name, text)
    old = Path.cwd()
    os.chdir(cwd)
    try:
        old_ceiling = os.environ.get("GIT_CEILING_DIRECTORIES")
        os.environ["GIT_CEILING_DIRECTORIES"] = str(cwd.parent)
        try:
            return str(summary.render(exit_code))
        finally:
            if old_ceiling is None:
                del os.environ["GIT_CEILING_DIRECTORIES"]
            else:
                os.environ["GIT_CEILING_DIRECTORIES"] = old_ceiling
    finally:
        os.chdir(old)


_FULL: Opts = {"unit": "files", "levels": "L0 PASS · L1 FAIL · L2 PASS", "gc_stage": "-1 (reactive default)", "extra": [("tests", [40, 2, 1, 0, 1, 0, 0])], "notes": [("test_h.py", "3 answered, 1 refused"), ("session (joined_hotspot)", "")]}

_EXPECTED_FULL = """== Summary: scripts/test.sh ==
Commit: unknown
Levels: L0 PASS · L1 FAIL · L2 PASS
GC stage: -1 (reactive default)
Counts (files): passed 2 · failed 2 · skipped 1 · deselected 1 · retried 1 · recovered 1 · vacuous 1
Counts (tests): passed 40 · failed 2 · skipped 1 · deselected 0 · retried 1 · recovered 0 · vacuous 0
Failed:
  - test_c.py: MemoryError seen
  - test_d.py
Skipped:
  - test_e.py: not run under --coverage (the plain pass runs them)
Deselected:
  - scenarios[dev]::dns: by runner selection: needs exclusive port 53 (run_digital_twin_ci.sh)
Passed only on retry:
  - test_f.py (attempt 2/3)
Recovery passes:
  - test_g.py: hard reset fallback
Notes:
  - test_h.py: 3 answered, 1 refused
  - session (joined_hotspot)
Checked nothing:
  - pass gc.threshold=-1
Result: FAIL
Exit code: 1
"""


def test_the_bash_emitter_prints_the_e10_layout(tmp_path: Path) -> None:
    assert _bash_render(tmp_path, "scripts/test.sh", 1, _ITEMS, _FULL) == _EXPECTED_FULL


def test_the_python_emitter_prints_the_e10_layout(emitter: ModuleType, tmp_path: Path) -> None:
    assert _py_render(emitter, tmp_path, "scripts/test.sh", 1, _ITEMS, _FULL) == _EXPECTED_FULL


_CASES: list[tuple[int, list[tuple[str, str, str]], Opts]] = [
    (0, [("passed", "a", "")], {}),
    (0, [], {"unit": "checks"}),
    (1, _ITEMS, _FULL),
    (2, [("failed", "usage", "unknown argument --x")], {}),
    (3, [("passed", "a", "")], {"gc_stage": "coverage run (settrace)"}),
    (4, [("passed", "a", "")], {"levels": "L3", "reason": "lower levels skipped: L0 L1 L2"}),
    (4, [("passed", "a", "")], {}),
    (130, [("failed", "t", "aborted by operator"), ("skipped", "u", "not run (run aborted)")], {"unit": "manual steps"}),
    (0, [("vacuous", "pass gc.threshold=32768", "")], {"unit": "checks"}),
    (0, [("", "test_x.py", "")], {}),
    (0, [("passed", "a", "")], {"notes": [("a", "graceful wait 150.0s")]}),
]


@pytest.mark.parametrize(("exit_code", "items", "kwargs"), _CASES)
def test_bash_and_python_render_the_same_input_byte_for_byte(emitter: ModuleType, tmp_path: Path, exit_code: int, items: list[tuple[str, str, str]], kwargs: Opts) -> None:
    kwargs = {"unit": "files", **kwargs}  # the bash default unit is "files", the Python one "tests"
    bash_out = _bash_render(tmp_path, "runner", exit_code, items, kwargs)
    py_out = _py_render(emitter, tmp_path, "runner", exit_code, items, kwargs)
    assert bash_out.encode() == py_out.encode()


def _js_input(runner: str, exit_code: int, items: list[tuple[str, str, str]], commit: str, kwargs: Opts) -> str:
    # The canned-input contract of `node tests_js/_summary_layout.js <json>`: one JSON argument, the
    # block on stdout. `commit` is passed in because the layout is pure (no git, no Node built-ins).
    extra = kwargs.get("extra") or []
    return json.dumps(
        {
            "runner": runner,
            "unit": kwargs.get("unit", "tests"),
            "levels": kwargs.get("levels"),
            "gc_stage": kwargs.get("gc_stage"),
            "not_clean_reason": kwargs.get("reason"),
            "commit": commit,
            "items": [list(item) for item in items],
            "extra_counts": [[u, list(v)] for u, v in extra],  # type: ignore[attr-defined]
            "notes": [list(note) for note in kwargs.get("notes") or []],  # type: ignore[attr-defined]
            "exit_code": exit_code,
        },
    )


@pytest.mark.parametrize(("exit_code", "items", "kwargs"), _CASES)
def test_the_js_layout_renders_the_same_input_byte_for_byte(emitter: ModuleType, tmp_path: Path, exit_code: int, items: list[tuple[str, str, str]], kwargs: Opts) -> None:
    node = shutil.which("node")
    assert node is not None, "node is a hard prerequisite of the host tier (scripts/test.sh runs npm's toolchain)"
    assert _JS.is_file(), f"{_JS} is missing"
    py_out = _py_render(emitter, tmp_path, "runner", exit_code, items, kwargs)
    result = subprocess.run([node, str(_JS), _js_input("runner", exit_code, items, "unknown", kwargs)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.encode() == py_out.encode()


def test_a_missing_verdict_counts_as_failed(emitter: ModuleType, tmp_path: Path) -> None:
    for out in (_bash_render(tmp_path, "r", 1, [("", "test_x.py", "")]), _py_render(emitter, tmp_path, "r", 1, [("", "test_x.py", "")])):
        assert "failed 1" in out
        assert "Failed:\n  - test_x.py: no verdict\n" in out


def test_a_missing_run_record_counts_as_failed(emitter: ModuleType, tmp_path: Path) -> None:
    summary = emitter.from_run_record(tmp_path / "absent.json")
    assert summary.failed == [(str(tmp_path / "absent.json"), "no verdict (run record missing or unreadable)")]
    (tmp_path / "garbled.json").write_text("{not json")
    assert emitter.from_run_record(tmp_path / "garbled.json").failed[0][1] == "no verdict (run record missing or unreadable)"


@pytest.mark.parametrize("kind", ["vacuous", "failed", ""])
@pytest.mark.parametrize("given", [0, 3, 4])
def test_a_failed_or_vacuous_item_raises_a_passing_code_to_1_in_the_block_and_the_status(emitter: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str, given: int) -> None:
    # The block and the process never disagree: a failure cannot leave with a green (0), a
    # tolerated (3, coverage render) or a NOT CLEAN (4) code. The returned code is the printed one.
    for out in (_bash_render(tmp_path, "r", given, [(kind, "x", "")]), _py_render(emitter, tmp_path, "r", given, [(kind, "x", "")])):
        assert out.endswith("Result: FAIL\nExit code: 1\n"), out
    summary = emitter.Summary("r")
    summary.add(kind, "x")
    assert summary.print(given) == 1
    assert capsys.readouterr().out.endswith("Exit code: 1\n")


@pytest.mark.parametrize("given", [1, 2, 124, 130])
def test_a_nonzero_failure_code_is_never_changed(emitter: ModuleType, tmp_path: Path, given: int) -> None:
    for out in (_bash_render(tmp_path, "r", given, [("failed", "x", "")]), _py_render(emitter, tmp_path, "r", given, [("failed", "x", "")])):
        assert out.endswith(f"Exit code: {given}\n"), out


@pytest.mark.parametrize(("exit_code", "result"), [(0, "PASS"), (1, "FAIL"), (2, "USAGE ERROR"), (3, "PASS (coverage report not rendered)"), (4, "NOT CLEAN (why)"), (124, "FAIL")])
def test_the_result_and_exit_code_lines_follow_the_given_code(emitter: ModuleType, tmp_path: Path, exit_code: int, result: str) -> None:
    for out in (_bash_render(tmp_path, "r", exit_code, [], {"reason": "why"}), _py_render(emitter, tmp_path, "r", exit_code, [], {"reason": "why"})):
        assert out.endswith(f"Result: {result}\nExit code: {exit_code}\n")


def _git(cwd: Path, *args: str) -> str:
    # The host's git config never reaches the scratch repository: a signing hook there fails the commit.
    env = {**_env(cwd), "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    git = shutil.which("git")
    assert git is not None
    return subprocess.run([git, *args], cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout.strip()


def test_the_commit_line_names_the_commit_and_uncommitted_changes(emitter: ModuleType, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "f").write_text("x\n")
    _git(repo, "add", "f")
    _git(repo, "commit", "-q", "-m", "c")
    sha = _git(repo, "rev-parse", "--short", "HEAD")
    for out in (_bash_render(repo, "r", 0, []), _py_render(emitter, repo, "r", 0, [])):
        assert f"\nCommit: {sha}\n" in out
    (repo / "g").write_text("y\n")
    for out in (_bash_render(repo, "r", 0, []), _py_render(emitter, repo, "r", 0, [])):
        assert f"\nCommit: {sha} (uncommitted changes)\n" in out


def test_an_unknown_kind_is_a_usage_error(emitter: ModuleType, tmp_path: Path) -> None:
    result = _bash(['rc=0; summary_add bogus name || rc=$?; echo "rc=$rc"'], tmp_path)
    assert "rc=2" in result.stdout
    assert "bogus" in result.stderr
    with pytest.raises(ValueError, match="bogus"):
        emitter.Summary("r").add("bogus", "name")


def test_the_bash_emitter_refuses_to_run_as_a_command(tmp_path: Path) -> None:
    result = subprocess.run(["/bin/bash", str(_SH)], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "error: source scripts/_summary_block.sh, do not run it" in result.stderr


@pytest.mark.parametrize("argv", [[], ["--bogus"], ["--from-run-record"], ["--from-run-record", "x.json"], ["--from-run-record", "x.json", "--list", "nope"]])
def test_the_python_cli_exits_2_on_a_usage_error(tmp_path: Path, argv: list[str]) -> None:
    result = subprocess.run([sys.executable, str(_PY), *argv], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 2, result.stdout + result.stderr


def test_the_python_cli_prints_counts_and_lists_from_a_run_record(tmp_path: Path) -> None:
    record = {
        "tests": [
            {"nodeid": "t.py::a", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": []},
            {"nodeid": "t.py::b", "outcome": "skipped", "when": "setup", "reason": "needs x", "markers": [], "user_properties": []},
            {"nodeid": "t.py::c", "outcome": "error", "when": "setup", "reason": "boom", "markers": [], "user_properties": []},
        ],
        "collection": [{"nodeid": "u.py", "outcome": "skipped", "reason": "module skip"}],
        "deselected": [{"nodeid": "t.py::d", "by": "runner selection", "markers": []}],
        "options": {},
        "markexpr": "",
        "collect_only": False,
        "session_notes": [],
        "exitstatus": 1,
    }
    path = tmp_path / "r.json"
    path.write_text(json.dumps(record))
    counts = subprocess.run([sys.executable, str(_PY), "--from-run-record", str(path), "--counts-only"], capture_output=True, text=True, check=True)
    assert counts.stdout == "1 1 2 1\n"
    skipped = subprocess.run([sys.executable, str(_PY), "--from-run-record", str(path), "--list", "skipped"], capture_output=True, text=True, check=True)
    assert skipped.stdout == "t.py::b\tneeds x\nu.py\tmodule skip\n"


@pytest.mark.parametrize(("exitstatus", "kind"), [(2, "failed"), (3, "failed"), (4, "failed"), (5, "vacuous")])
def test_an_aborted_or_empty_pytest_session_is_never_read_as_clean(emitter: ModuleType, tmp_path: Path, exitstatus: int, kind: str) -> None:
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"tests": [], "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": False, "session_notes": [], "exitstatus": exitstatus}))
    assert getattr(emitter.from_run_record(path), kind), f"exit status {exitstatus} left no {kind} item"


def test_a_nonzero_exit_with_no_failed_test_recorded_is_a_failure(emitter: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    tests = [{"nodeid": "t.py::a", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": []}]
    path.write_text(json.dumps({"tests": tests, "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": False, "session_notes": [], "exitstatus": 1}))
    assert emitter.from_run_record(path).failed


def test_recovery_notes_count_apart_from_passes(emitter: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    tests = [{"nodeid": "t.py::a", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": [["recovery", "hard reset fallback"]]}]
    notes = [{"text": "restored SSID", "recovery": True, "source": "joined_hotspot"}]
    path.write_text(json.dumps({"tests": tests, "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": False, "session_notes": notes, "exitstatus": 0}))
    summary = emitter.from_run_record(path)
    assert summary.passed == []
    assert summary.recovered == [("t.py::a", "hard reset fallback"), ("joined_hotspot", "restored SSID")]


def test_a_note_is_listed_but_never_counted_and_never_changes_the_result(emitter: ModuleType, tmp_path: Path) -> None:
    opts: Opts = {"unit": "files", "notes": [("a", "graceful wait 150.0s")]}
    for out in (_bash_render(tmp_path, "r", 0, [("passed", "a", "")], opts), _py_render(emitter, tmp_path, "r", 0, [("passed", "a", "")], opts)):
        assert "\nCounts (files): passed 1 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0\n" in out
        assert "\nRecovery passes: none\nNotes:\n  - a: graceful wait 150.0s\nChecked nothing: none\n" in out
        assert out.endswith("Result: PASS\nExit code: 0\n")
    for out in (_bash_render(tmp_path, "r", 0, []), _py_render(emitter, tmp_path, "r", 0, [])):
        assert "\nRecovery passes: none\nNotes: none\nChecked nothing: none\n" in out


def test_every_result_note_and_plain_session_note_reaches_the_notes_list(emitter: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    tests = [
        {"nodeid": "t.py::a", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": [["result_note", "3 answered"], ["result_note", "1 refused"]]},
        {"nodeid": "t.py::b", "outcome": "failed", "when": "call", "reason": "boom", "markers": [], "user_properties": [["recovery", "reset once"], ["result_note", "graceful wait 9.0s"]]},
        {"nodeid": "t.py::c", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": [["recovery", "hard reset"], ["recovery", "second reset"], ["result_note", "after the reset"]]},
    ]
    notes = [{"text": "restored SSID", "recovery": True, "source": "joined_hotspot"}, {"text": "bench idle", "recovery": False, "source": "bench"}, {"text": "unsourced", "recovery": False, "source": ""}]
    path.write_text(json.dumps({"tests": tests, "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": False, "session_notes": notes, "exitstatus": 1}))
    summary = emitter.from_run_record(path)
    assert summary.notes == [("t.py::a", "3 answered"), ("t.py::a", "1 refused"), ("t.py::b", "recovery: reset once"), ("t.py::b", "graceful wait 9.0s"), ("t.py::c", "after the reset"), ("session (bench)", "bench idle"), ("session", "unsourced")]
    # A recovery note is never dropped: a second one joins the pass's item, a failed test's becomes a note.
    assert summary.recovered == [("t.py::c", "hard reset; second reset"), ("joined_hotspot", "restored SSID")]
    assert summary.counts().passed == 1


def test_no_emitter_writes_the_github_step_summary() -> None:
    for path in (_SH, _PY):
        assert "GITHUB_STEP_SUMMARY" not in path.read_text(), path
