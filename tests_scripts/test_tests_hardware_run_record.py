"""Hardware runs write a run record (scripts/_pytest_run_record.py) that keeps what output alone
loses: collecting tests_hardware/ with nothing attached tells wear-gate deselections from -m ones,
and a note from tests_hardware/conftest.py's result_note or record_session_note reaches the record."""

import json
import os
import subprocess
import sys
from pathlib import Path

_FLOOR = "not long_soak and not multi_day_rollover"


def _pytest(repo_root: Path, *args: str, cwd: Path) -> "subprocess.CompletedProcess[str]":
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(repo_root / "scripts"), str(repo_root / "tests_hardware"))))
    return subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args], capture_output=True, text=True, check=False, cwd=cwd, env=env, timeout=120)


def test_collecting_the_hardware_levels_records_why_each_test_was_deselected(repo_root: Path, tmp_path: Path) -> None:
    record_path = tmp_path / "run_record.json"
    ran = _pytest(repo_root, "-p", "_pytest_run_record", f"--run-record={record_path}", "tests_hardware/flash", "tests_hardware/bench", "--collect-only", "-q", "-m", _FLOOR, cwd=repo_root)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    record = json.loads(record_path.read_text())
    assert record["collect_only"] is True
    by = {entry["nodeid"].rsplit("::", 1)[-1]: entry["by"] for entry in record["deselected"]}
    assert by.get("test_same_device_concurrent_sessions_never_corrupt_each_other") == "--allow-persistence-writes", by
    assert by.get("test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic") == "runner selection", "a -m exclusion is the runner's selection, never a wear gate"
    assert set(by.values()) == {"--allow-persistence-writes", "runner selection"}, by


_STUB_TEST = """
from conftest import record_session_note

def test_a_recovered_pass(result_note):
    result_note("graceful wait 150.0s")
    result_note("recovered via a fallback hard_reset()", recovery=True)

def test_a_session_note(request):
    record_session_note(request.config, "stale credentials repaired", recovery=True, source="dut_ip")
"""


def test_result_note_and_session_notes_land_in_the_record(repo_root: Path, tmp_path: Path) -> None:
    (tmp_path / "test_stub.py").write_text(_STUB_TEST)
    record_path = tmp_path / "run_record.json"
    ran = _pytest(repo_root, "-p", "conftest", "-p", "_pytest_run_record", f"--run-record={record_path}", str(tmp_path / "test_stub.py"), cwd=tmp_path)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    record = json.loads(record_path.read_text())
    props = next(e["user_properties"] for e in record["tests"] if e["nodeid"].endswith("test_a_recovered_pass"))
    assert ["result_note", "graceful wait 150.0s"] in props, props
    assert ["recovery", "recovered via a fallback hard_reset()"] in props, props
    assert {"text": "stale credentials repaired", "recovery": True, "source": "dut_ip"} in record["session_notes"], record["session_notes"]


def test_a_session_note_is_printed_when_no_record_is_written(repo_root: Path, tmp_path: Path) -> None:
    # A bare `pytest tests_hardware` loads no record plugin: the note reaches the terminal even
    # though pytest captures a passing test's own output.
    (tmp_path / "test_stub.py").write_text(_STUB_TEST)
    ran = _pytest(repo_root, "-p", "conftest", str(tmp_path / "test_stub.py"), cwd=tmp_path)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "RECOVERY (dut_ip): stale credentials repaired" in ran.stdout, ran.stdout
