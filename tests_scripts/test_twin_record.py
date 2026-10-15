"""Every hardware instrument has a current twin-run record (twin_record.json in tests_hardware, written only by
scripts/record_twin_instrument_runs.py): an entry per instrument, its three hashes the current files', every exception
named, no entry for a deleted file. A changed script, runner or src/ API it imports demands a re-run."""

import json
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
