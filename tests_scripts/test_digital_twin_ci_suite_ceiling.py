"""Tests scripts/_digital_twin_ci_suite.py's Run 11b (the full-ceiling burst) without a live twin:
its ceiling read, _concurrent_get() against a loopback server, and the run's own verdict and
failure paths, with the subprocess side stubbed out."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

from buildgen.validate import device_max_connections

_REPO_ROOT = Path(__file__).resolve().parent.parent


class _JsonHandler(BaseHTTPRequestHandler):
    body = json.dumps({"ok": True}).encode()
    content_type = "application/json"

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", self.content_type)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the base class's own signature
        pass


class _TextHandler(_JsonHandler):
    body = b"not json at all"
    content_type = "text/plain"


class _HangUpHandler(_JsonHandler):
    def do_GET(self) -> None:
        self.close_connection = True  # read the request, answer nothing - the reject-when-full shape


def _serve(handler: type[BaseHTTPRequestHandler], ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(ci_suite, "HOST", "127.0.0.1")
    monkeypatch.setattr(ci_suite, "PORT", server.server_address[1])
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def json_server(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from _serve(_JsonHandler, ci_suite, monkeypatch)


@pytest.fixture
def text_server(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from _serve(_TextHandler, ci_suite, monkeypatch)


@pytest.fixture
def hang_up_server(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from _serve(_HangUpHandler, ci_suite, monkeypatch)


def _ctx(ci_suite: ModuleType, tmp_path: Path) -> object:
    return ci_suite.RunContext(
        micropython_bin="/nonexistent",
        logs_dir=tmp_path,
        device="wozi",
        module="sensortask_wozi",
        wiring_plan_path=tmp_path / "plan.json",
        drivers=frozenset(),
        gc_threshold=-1,
    )


@pytest.fixture
def stubbed_run(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Run 11b with every subprocess/state side effect stubbed; returns the spawn log and a fresh
    _FAILURES, so a test sees only what its own run recorded."""
    spawned: list[str] = []
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_clean_state", lambda: None)  # never touches the real digital_twin/ state
    monkeypatch.setattr(ci_suite, "_spawn", lambda _ctx, _args, log_path: spawned.append(str(log_path)))
    monkeypatch.setattr(ci_suite, "_wait_until_serving", lambda _proc: None)
    monkeypatch.setattr(ci_suite, "_shutdown", lambda _proc, _label: 0)
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    return spawned


def test_the_ceiling_is_buildgen_s_own_value(ci_suite: ModuleType) -> None:
    assert ci_suite._configured_max_connections("wozi") == device_max_connections(_REPO_ROOT / "devices" / "wozi.toml", _REPO_ROOT / "src")


@pytest.mark.usefixtures("json_server")
def test_concurrent_get_returns_status_and_parsed_body_for_every_request(ci_suite: ModuleType) -> None:
    results = ci_suite._concurrent_get(["/status", "/sensors", "/system"], timeout=5.0)
    assert results == [(200, {"ok": True})] * 3


@pytest.mark.usefixtures("hang_up_server")
def test_concurrent_get_records_a_refused_request_as_its_error_repr(ci_suite: ModuleType) -> None:
    results = ci_suite._concurrent_get(["/status", "/sensors"], timeout=5.0)
    assert all(isinstance(r, str) for r in results), results
    assert all("RemoteDisconnected" in r for r in results), results


@pytest.mark.usefixtures("json_server")
def test_run_11b_passes_a_ceiling_served_in_full(ci_suite: ModuleType, stubbed_run: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci_suite, "_configured_max_connections", lambda _device: 3)
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    assert ci_suite._FAILURES == []
    assert len(stubbed_run) == 1


@pytest.mark.usefixtures("text_server")
def test_run_11b_fails_a_200_without_a_parsed_json_body(ci_suite: ModuleType, stubbed_run: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The README's bar is "served 200 with a parsed body": a bare status would pass a truncated or
    # non-JSON reply from a contended endpoint.
    monkeypatch.setattr(ci_suite, "_configured_max_connections", lambda _device: 3)
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    rounds = [f for f in ci_suite._FAILURES if "Run 11b round" in f]
    assert len(rounds) == ci_suite._CEILING_ROUNDS, ci_suite._FAILURES
    assert all("got 0" in f and "(200, 'NoneType')" in f for f in rounds), rounds
    assert len(stubbed_run) == 1


def test_an_unreadable_ceiling_fails_the_run_once_and_never_spawns(ci_suite: ModuleType, stubbed_run: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def broken(_device: str) -> int:
        raise ValueError("devices/wozi.toml is not TOML")

    monkeypatch.setattr(ci_suite, "_configured_max_connections", broken)
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    assert len(ci_suite._FAILURES) == 1, ci_suite._FAILURES
    assert "cannot read the device's ceiling" in ci_suite._FAILURES[0]
    assert "is not TOML" in ci_suite._FAILURES[0]
    assert stubbed_run == []
