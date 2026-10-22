"""Evidence is saved before anything clears it: ResetErrors reads and saves /status first and fails unless it cleared,
the evidence directory honours $EVIDENCE_DIR and never overwrites a file, and the raw FRAM dump script reads only -
no chunk, no write (CLAUDE.md's FRAM-log rule)."""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import error_log_helpers
import evidence
import http_client

TESTS_HARDWARE = Path(__file__).resolve().parent.parent / "tests_hardware"

_STATUS = {"errcount": {"SYSTEM": {"counter": 2, "history": [{"num": 4, "type": "E"}]}}, "ResetReason": 3}


def _fetch_recording(calls: "list[str]", evidence_dir: Path, put_answer: object) -> object:
    def fetch(_host: str, _port: int, method: str, path: str, json_body: object = None, timeout_s: float = 0.0) -> http_client.HttpResponse:
        calls.append(f"{method} {path} files={sorted(p.name for p in evidence_dir.glob('*'))}")
        body = _STATUS if method == "GET" else put_answer
        return http_client.HttpResponse(200, {}, json.dumps(body).encode())

    return fetch


@pytest.fixture
def evidence_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    return tmp_path / "evidence"


def test_reset_saves_the_verbatim_status_before_the_put(evidence_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(http_client, "fetch", _fetch_recording(calls, evidence_dir, {"res": "OK", "result": {"ResetErrors": "Valid"}}))
    error_log_helpers.reset_all_error_logs("dut", "test_x[param]")
    assert calls == ["GET /status files=[]", "PUT /status files=['errcount-test_x[param].json']"]
    assert json.loads((evidence_dir / "errcount-test_x[param].json").read_text(encoding="utf-8")) == _STATUS


@pytest.mark.parametrize("answer", [{"res": "OK", "result": {"ResetErrors": "Failed"}}, {"res": "ERR", "result": {}}, {"res": "OK", "result": {}}])
def test_a_reset_that_did_not_clear_raises(evidence_dir: Path, monkeypatch: pytest.MonkeyPatch, answer: object) -> None:
    monkeypatch.setattr(http_client, "fetch", _fetch_recording([], evidence_dir, answer))
    with pytest.raises(AssertionError, match="ResetErrors did not clear"):
        error_log_helpers.reset_all_error_logs("dut", "failed")


def test_evidence_honours_its_environment_directory_and_never_overwrites(evidence_dir: Path) -> None:
    assert evidence.evidence_dir() == evidence_dir
    first = evidence.save_json("errcount-x.json", {"a": 1})
    second = evidence.save_text("errcount-x.json", "raw")
    third = evidence.save_text("../escape/name.txt", "kept inside")
    assert (first.name, second.name) == ("errcount-x.json", "errcount-x-1.json")
    assert third.parent == evidence_dir and "/" not in third.name
    assert json.loads(first.read_text(encoding="utf-8")) == {"a": 1} and second.read_text(encoding="utf-8") == "raw"


def test_the_raw_fram_dump_script_reads_only() -> None:
    tree = ast.parse((TESTS_HARDWARE / "device_scripts" / "fram_raw_dump.py").read_text(encoding="utf-8"))
    called = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    forbidden = sorted(called & {"set_values", "set_values_sync", "get_chunk", "write", "set_write_protected", "reset"})
    assert not forbidden, f"fram_raw_dump.py calls {forbidden} - the evidence read must never write or allocate a chunk"
    assert "get_values_sync" in called, "the dump no longer reads through the driver's raw read"
