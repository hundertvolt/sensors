"""Covers tests_hardware/'s small shared helpers offline: harness.wait_for_script_server() and
restore_board_to_serving() against a faked http_client, error_log_helpers' all-modules check, and
that every bench thread worker calling http_client.fetch() survives a cut-off answer."""

from __future__ import annotations

import ast
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

TESTS_HARDWARE = Path(__file__).resolve().parent.parent / "tests_hardware"
sys.path.insert(0, str(TESTS_HARDWARE))

import error_log_helpers  # noqa: E402  (the sys.path line above is what makes these importable)
import harness  # noqa: E402
import http_client  # noqa: E402


def _fetch_answering(outcomes: list[int | None]) -> Callable[..., http_client.HttpResponse]:
    # Each call takes the next outcome: a status code, or None for a cut-off answer; the last repeats.
    def fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        outcome = outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]
        if outcome is None:
            raise http_client.HTTP_ERROR("cut off")
        return http_client.HttpResponse(outcome, {}, b"{}")

    return fetch


def test_wait_for_script_server_ends_at_once_when_its_test_has_already_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client, "fetch", _fetch_answering([200]))
    stop = threading.Event()
    stop.set()
    started = time.monotonic()
    assert harness.wait_for_script_server("dut", stop) is False
    assert time.monotonic() - started < 0.5


def test_wait_for_script_server_waits_out_main_pys_server_then_finds_the_scripts(monkeypatch: pytest.MonkeyPatch) -> None:
    # 200 from main.py's server, a gap while mpremote swaps it for the script, then the script's 200.
    monkeypatch.setattr(http_client, "fetch", _fetch_answering([200, None, 200]))
    started = time.monotonic()
    assert harness.wait_for_script_server("dut", threading.Event(), timeout_s=5.0, handover_s=5.0) is True
    assert 0.4 < time.monotonic() - started < 2.0, "it answered before main.py's server ever went quiet"


def test_wait_for_script_server_gives_up_when_nothing_ever_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client, "fetch", _fetch_answering([None]))
    started = time.monotonic()
    assert harness.wait_for_script_server("dut", threading.Event(), timeout_s=0.3, handover_s=0.1) is False
    assert time.monotonic() - started < 2.0


def test_restore_board_to_serving_kicks_the_stations_before_the_reset_and_then_waits_for_http(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeBoard:
        def hard_reset(self) -> None:
            calls.append("hard_reset")

    class FakeBench:
        def kick_all_stations(self) -> None:
            calls.append("kick_all_stations")

    def fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        calls.append("fetch")
        return http_client.HttpResponse(200, {}, b"{}")

    monkeypatch.setattr(http_client, "fetch", fetch)
    harness.restore_board_to_serving(FakeBoard(), FakeBench(), "dut")  # type: ignore[arg-type]
    assert calls == ["kick_all_stations", "hard_reset", "fetch"]


def test_a_module_absent_before_that_logs_now_is_a_new_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"SGP40": {"counter": 1}})
    with pytest.raises(AssertionError, match="'SGP40': \\(0, 1\\)"):
        error_log_helpers.assert_no_module_logged_a_new_error("dut", {}, "burst")


def test_an_unchanged_counter_is_no_new_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"SGP40": {"counter": 2}, "SYSTEM": {"counter": 0}})
    error_log_helpers.assert_no_module_logged_a_new_error("dut", {"SGP40": {"counter": 2}}, "burst")


def _catches(handler: ast.ExceptHandler) -> set[str]:
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type] if handler.type else []
    return {ast.unparse(kind) for kind in kinds}


def _unguarded_fetches(source: str) -> list[str]:
    """Thread-target functions whose try around http_client.fetch() names OSError but not HTTP_ERROR:
    a cut-off answer is an HTTPException, which then kills the thread and silently stops its load."""
    tree = ast.parse(source)
    targets = {ast.unparse(kw.value) for node in ast.walk(tree) if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("Thread") for kw in node.keywords if kw.arg == "target"}
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or fn.name not in targets:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Try) and "http_client.fetch" in ast.unparse(ast.Module(body=node.body, type_ignores=[])):
                caught = set().union(*(_catches(h) for h in node.handlers))
                if "OSError" in caught and not caught & {"http_client.HTTP_ERROR", "Exception", "BaseException"}:
                    found.append(f"{fn.name} (line {node.lineno})")
    return found


def test_the_worker_rule_sees_a_worker_that_catches_only_oserror() -> None:
    source = (
        "import threading\ndef worker():\n    try:\n        http_client.fetch('h', 80, 'GET', '/')\n    except OSError:\n        pass\n"
        "threading.Thread(target=worker)\n"
    )
    assert _unguarded_fetches(source) == ["worker (line 3)"]


@pytest.mark.parametrize("module", sorted((TESTS_HARDWARE / "bench").glob("test_*.py")), ids=lambda p: p.name)
def test_every_bench_thread_worker_survives_a_cut_off_answer(module: Path) -> None:
    assert _unguarded_fetches(module.read_text()) == [], module.name
