"""Every hardware instrument has a current twin-run record (tests_hardware/twin_record.json, written only by
scripts/record_twin_instrument_runs.py): an entry per instrument with an outcome at each GC stage, its three hashes the
current files', every exception named, none for a deleted file. A changed script, runner or src/ API needs a re-run."""

import json
import subprocess
import types
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module


@pytest.fixture(scope="module")
def record(recorder: ModuleType) -> "dict[str, dict[str, object]]":
    path = recorder.RECORD
    assert path.is_file(), f"no {path.name}: run scripts/record_twin_instrument_runs.py (it never writes by hand)"
    loaded: dict[str, dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _scratch_recorder(recorder: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, staged: bool) -> Path:
    # A scratch tree of two flash tests, each running its own script, and a pytest whose report breaks test_a only; with
    # `staged` its board takes each stage as the recorder's plugin reports it. Returns the reasons file.
    hardware = tmp_path / "tests_hardware"
    for name in ("device_scripts", "flash", "bench"):
        (hardware / name).mkdir(parents=True)
    for script in ("a.py", "b.py"):
        (hardware / "device_scripts" / script).write_text("print(1)\n", encoding="utf-8")
    (hardware / "flash" / "test_pair.py").write_text('def test_a(board):\n    board.run_isolated("a.py")\n\n\ndef test_b(board):\n    board.run_isolated("b.py")\n', encoding="utf-8")
    runner = tmp_path / "runner.py"
    runner.write_text("", encoding="utf-8")
    cases = '<testcase classname="tests_hardware.flash.test_pair" name="test_a"><failure message="planted: test_a broken"/></testcase><testcase classname="tests_hardware.flash.test_pair" name="test_b"/>'

    def fake_pytest(argv: "list[str]", **_kwargs: object) -> "subprocess.CompletedProcess[str]":
        Path(next(arg for arg in argv if arg.startswith("--junitxml=")).split("=", 1)[1]).write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>", encoding="utf-8")
        stage = argv[argv.index("--record-gc-threshold") + 1] if "--record-gc-threshold" in argv else None
        return subprocess.CompletedProcess(argv, 1, stdout=recorder.staged_line(int(stage)) if staged and stage else "", stderr="")

    for name, value in {"REPO_ROOT": tmp_path, "TESTS_HARDWARE": hardware, "DEVICE_SCRIPTS": hardware / "device_scripts", "RECORD": hardware / "twin_record.json", "RUNNER_FILES": (runner,)}.items():
        monkeypatch.setattr(recorder, name, value)
    monkeypatch.setattr(recorder, "subprocess", types.SimpleNamespace(run=fake_pytest, TimeoutExpired=subprocess.TimeoutExpired))
    monkeypatch.setattr(recorder.twin_board, "unix_port_binary", lambda: runner)
    reasons = tmp_path / "reasons.json"
    reasons.write_text(json.dumps({"tests_hardware/flash/test_pair.py": "planted: its test_a is broken", "tests_hardware/device_scripts/a.py": "planted: run by the broken test_a"}), encoding="utf-8")
    return reasons


def _stages(entry: "dict[str, object]") -> "dict[str, str]":
    stages = entry.get("stages")
    return {str(stage): str(outcome) for stage, outcome in stages.items()} if isinstance(stages, dict) else {}


@pytest.fixture(scope="module")
def recorder(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "record_twin_instrument_runs.py", "record_twin_instrument_runs")


def test_every_instrument_has_an_entry(recorder: ModuleType, record: "dict[str, dict[str, object]]") -> None:
    missing = sorted(path.relative_to(recorder.REPO_ROOT).as_posix() for path in recorder.instruments() if path.relative_to(recorder.REPO_ROOT).as_posix() not in record)
    assert not missing, f"instruments with no twin run recorded: {missing}"


def test_no_entry_names_a_deleted_file(recorder: ModuleType, record: "dict[str, dict[str, object]]") -> None:
    assert sorted(key for key in record if not (recorder.REPO_ROOT / key).is_file()) == []


def test_every_entrys_hashes_are_the_current_files(recorder: ModuleType, record: "dict[str, dict[str, object]]") -> None:
    stale = [f"{key}: {name}" for key, entry in sorted(record.items()) if (recorder.REPO_ROOT / key).is_file() for name, digest in recorder.entry_hashes(recorder.REPO_ROOT / key).items() if entry.get(name) != digest]
    assert not stale, f"changed since their twin run was recorded - re-run scripts/record_twin_instrument_runs.py: {stale}"


def test_every_entry_records_an_outcome_at_each_gc_stage(recorder: ModuleType, record: "dict[str, dict[str, object]]") -> None:
    stages = {str(stage) for stage in recorder.GC_THRESHOLDS}
    outcomes = {key: _stages(entry) for key, entry in record.items()}
    wrong = sorted(key for key, found in outcomes.items() if set(found) != stages or not set(found.values()) <= {"pass", "exception"})
    assert not wrong, f"entries without an outcome at each of gc.threshold {sorted(stages)}: {wrong}"
    mixed = sorted(key for key, entry in record.items() if entry.get("result") != ("exception" if "exception" in outcomes[key].values() else "pass"))
    assert not mixed, f"entries whose result is not their stages' (an exception at any stage is one): {mixed}"


def test_a_broken_flash_test_is_charged_only_to_the_scripts_it_runs(recorder: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    reasons = _scratch_recorder(recorder, tmp_path, monkeypatch, staged=True)
    assert recorder.main(["--reasons", str(reasons)]) == 0, capsys.readouterr().err
    record = json.loads(recorder.RECORD.read_text(encoding="utf-8"))
    results = {key.rsplit("/", 1)[-1]: entry["result"] for key, entry in record.items()}
    assert results == {"a.py": "exception", "b.py": "pass", "test_pair.py": "exception"}, record


def test_a_flash_run_whose_board_never_took_the_stage_is_refused(recorder: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reasons = _scratch_recorder(recorder, tmp_path, monkeypatch, staged=False)
    with pytest.raises(SystemExit, match=r"never took gc\.threshold\(-1\)"):
        recorder.main(["--reasons", str(reasons)])
    assert not recorder.RECORD.exists()


def test_the_flash_runs_twin_board_takes_the_stage(recorder: ModuleType) -> None:
    board = recorder.twin_board.TwinBoard()
    config = types.SimpleNamespace(getoption=lambda name: 32768 if name == "--record-gc-threshold" else None, stash=pytest.Stash())
    hook = recorder.pytest_fixture_setup(types.SimpleNamespace(argname="board"), types.SimpleNamespace(config=config))
    next(hook)
    with pytest.raises(StopIteration) as done:
        hook.send(board)
    assert done.value.value is board and board.gc_threshold == 32768


def test_every_exception_names_its_reason(record: "dict[str, dict[str, object]]") -> None:
    assert {entry.get("result") for entry in record.values()} <= {"pass", "exception"}
    unnamed = sorted(key for key, entry in record.items() if entry.get("result") == "exception" and not str(entry.get("reason", "")).strip())
    assert not unnamed, f"exceptions with no reason: {unnamed}"


def test_a_device_scripts_hash_covers_its_includes_and_the_src_modules_it_imports(recorder: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A change to an inlined include or to an imported src/ module must change the pinned hashes, or a re-run is never asked.
    scripts = tmp_path / "tests_hardware" / "device_scripts"
    (scripts / "_shared").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "asy_probe_driver.py").write_text("X = 1\n", encoding="utf-8")
    (scripts / "_shared" / "helper.py").write_text("import asy_probe_driver\n", encoding="utf-8")
    script = scripts / "probe.py"
    script.write_text("# @include _shared/helper.py\nprint(1)\n", encoding="utf-8")
    monkeypatch.setattr(recorder, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(recorder, "DEVICE_SCRIPTS", scripts)
    monkeypatch.setattr(recorder, "RUNNER_FILES", (script,))
    before = recorder.entry_hashes(script)
    (scripts / "_shared" / "helper.py").write_text("import asy_probe_driver\nY = 2\n", encoding="utf-8")
    after_include = recorder.entry_hashes(script)
    (tmp_path / "src" / "asy_probe_driver.py").write_text("X = 2\n", encoding="utf-8")
    after_api = recorder.entry_hashes(script)
    assert before["sha256"] != after_include["sha256"] and after_include["api_sha256"] != after_api["api_sha256"]
    assert before["api_sha256"] == after_include["api_sha256"], "an include's own text moved the API hash"


def test_the_recorder_refuses_to_run_without_a_built_unix_port(recorder: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path / "no-toolchain"))
    assert recorder.main([]) == 1
    assert "run scripts/test.sh once" in capsys.readouterr().err
