"""scripts/_pytest_run_record.py writes one JSON run record per pytest session: a subprocess run over
a fabricated suite with a pass, a failure, a skip, a module-level skip, a -m deselection and a
flagged deselection yields every outcome, reason and deselection cause the summary block reads."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from _script_loader import load_script_module

REPO_ROOT = Path(__file__).resolve().parent.parent

_CONFTEST = """
import pytest
from _pytest_run_record import add_session_note


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: a runner -m exclusion")
    config.addinivalue_line("markers", "gated: a wear-gate deselection")


def pytest_collection_modifyitems(config, items):
    gated = [item for item in items if item.get_closest_marker("gated")]
    for item in gated:
        item.user_properties.append(("deselected_by", "--allow-gated"))
    if gated:
        items[:] = [item for item in items if item not in gated]
        config.hook.pytest_deselected(items=gated)


@pytest.fixture(scope="session", autouse=True)
def _note(request):
    add_session_note(request.config, "restored the bench", recovery=True, source="_note")
    add_session_note(request.config, "plain note")
"""

_TESTS = """
import pytest


def test_pass(record_property):
    record_property("recovery", "hard reset fallback")
    record_property("result_note", "graceful wait 1.0s")


def test_fail():
    assert 1 == 2, "one is not two"


def test_skip():
    pytest.skip("needs a board")


@pytest.mark.slow
def test_slow():
    pass


@pytest.mark.gated
def test_gated():
    pass


@pytest.fixture
def broken():
    raise RuntimeError("fixture broke")


def test_setup_error(broken):
    pass
"""

_MODULE_SKIP = """
import pytest

pytest.skip("whole module needs a toolchain", allow_module_level=True)


def test_never():
    pass
"""


def _run(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "conftest.py").write_text(_CONFTEST)
    (suite / "test_things.py").write_text(_TESTS)
    (suite / "test_module_skip.py").write_text(_MODULE_SKIP)
    record = tmp_path / "out" / "record.json"
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "scripts")}
    argv = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "_pytest_run_record", f"--run-record={record}", "--rootdir", str(suite), str(suite), *args]
    done = subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=120)
    return done, record


@pytest.fixture(scope="module")
def record(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    done, path = _run(tmp_path_factory.mktemp("run"), "-m", "not slow")
    assert done.returncode == 1, done.stdout + done.stderr
    loaded: dict[str, object] = json.loads(path.read_text())
    return loaded


def _tests(record: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(t["nodeid"]).split("::")[-1]: t for t in record["tests"]}  # type: ignore[attr-defined]


def test_every_outcome_is_recorded_once_per_test(record: dict[str, object]) -> None:
    tests = _tests(record)
    assert sorted(tests) == ["test_fail", "test_pass", "test_setup_error", "test_skip"]
    assert tests["test_pass"]["outcome"] == "passed"
    assert tests["test_fail"]["outcome"] == "failed"
    assert tests["test_fail"]["when"] == "call"
    assert "one is not two" in str(tests["test_fail"]["reason"])
    assert tests["test_setup_error"]["outcome"] == "error"
    assert tests["test_setup_error"]["when"] == "setup"
    assert tests["test_skip"]["outcome"] == "skipped"
    assert tests["test_skip"]["reason"] == "needs a board"


def test_user_properties_reach_the_record(record: dict[str, object]) -> None:
    assert _tests(record)["test_pass"]["user_properties"] == [["recovery", "hard reset fallback"], ["result_note", "graceful wait 1.0s"]]


def test_a_module_level_skip_is_a_collection_entry(record: dict[str, object]) -> None:
    collection = record["collection"]
    assert isinstance(collection, list)
    assert [(Path(str(c["nodeid"])).name, c["outcome"], c["reason"]) for c in collection] == [("test_module_skip.py", "skipped", "whole module needs a toolchain")]


def test_deselections_name_their_cause(record: dict[str, object]) -> None:
    deselected = {str(d["nodeid"]).split("::")[-1]: d for d in record["deselected"]}  # type: ignore[attr-defined]
    assert deselected["test_gated"]["by"] == "--allow-gated"
    assert deselected["test_gated"]["markers"] == ["gated"]
    assert deselected["test_slow"]["by"] == "runner selection"
    assert sorted(deselected) == ["test_gated", "test_slow"]


def test_the_options_the_effective_mark_expression_and_the_mode_are_recorded(record: dict[str, object]) -> None:
    assert record["markexpr"] == "not slow"
    assert record["collect_only"] is False
    assert record["exitstatus"] == 1
    options = record["options"]
    assert isinstance(options, dict)
    assert options["markexpr"] == "not slow"
    json.dumps(options)  # JSON-safe by construction


def test_session_notes_reach_the_record(record: dict[str, object]) -> None:
    assert record["session_notes"] == [{"text": "restored the bench", "recovery": True, "source": "_note"}, {"text": "plain note", "recovery": False, "source": ""}]


def test_collect_only_is_recorded(tmp_path: Path) -> None:
    done, path = _run(tmp_path, "--collect-only")
    assert done.returncode == 0, done.stdout + done.stderr
    loaded = json.loads(path.read_text())
    assert loaded["collect_only"] is True
    # Collected, never run: each test is listed with no outcome, which every reader takes as no verdict.
    assert sorted(t["nodeid"].split("::")[-1] for t in loaded["tests"]) == ["test_fail", "test_pass", "test_setup_error", "test_skip", "test_slow"]
    assert {t["outcome"] for t in loaded["tests"]} == {None}


def test_the_summary_reader_turns_the_record_into_the_block(record: dict[str, object], tmp_path: Path) -> None:
    emitter = load_script_module(REPO_ROOT / "scripts" / "_summary_block.py", "_summary_block_rr")
    path = tmp_path / "r.json"
    path.write_text(json.dumps(record))
    summary = emitter.from_run_record(path)
    counts = summary.counts()
    assert (counts.passed, counts.failed, counts.skipped, counts.deselected, counts.recovered) == (0, 2, 2, 2, 2)
    # Neither a test's result note nor a plain session note is dropped; both are listed, uncounted.
    assert [(name.split("::")[-1], text) for name, text in summary.notes] == [("test_pass", "graceful wait 1.0s"), ("session", "plain note")]
