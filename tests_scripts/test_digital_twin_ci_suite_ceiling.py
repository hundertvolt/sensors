"""Tests scripts/_digital_twin_ci_suite.py's Run 11b (the full-ceiling burst) without a live twin: its ceiling read, the
route set from the device's API reference, _concurrent_get() against a loopback server, and the run's own verdict and
failure paths, with the subprocess side stubbed out."""

import json
import threading
from collections import Counter
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import ClassVar

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.validate import device_max_connections

_REPO_ROOT = Path(__file__).resolve().parent.parent
# @tunable l0.ci_suite_ceiling_get_timeout_s = 5.0
_GET_TIMEOUT_S = 5.0
_ROUTES = ("/measurements", "/status", "/system")  # a fixture device's GET routes, as its API reference lists them


class _JsonHandler(BaseHTTPRequestHandler):
    body = json.dumps({"ok": True}).encode()
    content_type = "application/json"
    paths: ClassVar[list[str]] = []  # every path served, in arrival order, shared by every handler instance

    def do_GET(self) -> None:
        self.paths.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", self.content_type)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: object) -> None:  # the base class's own signature
        pass


class _TextHandler(_JsonHandler):
    body = b"not json at all"
    content_type = "text/plain"


class _HangUpHandler(_JsonHandler):
    def do_GET(self) -> None:
        self.close_connection = True  # read the request, answer nothing - the reject-when-full shape


def _ctx(ci_suite: ModuleType, tmp_path: Path) -> object:
    return ci_suite.RunContext(
        micropython_bin="/nonexistent",
        logs_dir=tmp_path,
        device="fixture_device",
        module="sensortask_fixture_device",
        wiring_plan_path=tmp_path / "plan.json",
        instances=(),
        gc_threshold=-1,
        routes=_ROUTES,
    )


def _serve(handler: type[BaseHTTPRequestHandler], ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    # A short poll step: shutdown() waits for the serving loop's next poll, half a second at the default.
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    monkeypatch.setattr(ci_suite, "HOST", "127.0.0.1")
    monkeypatch.setattr(ci_suite, "PORT", server.server_address[1])
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def hang_up_server(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from _serve(_HangUpHandler, ci_suite, monkeypatch)


@pytest.fixture
def json_server(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from _serve(_JsonHandler, ci_suite, monkeypatch)


@pytest.fixture
def stubbed_run(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    # Run 11b with every subprocess/state side effect stubbed; returns the spawn log and a fresh
    # _FAILURES, so a test sees only what its own run recorded.
    spawned: list[str] = []
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_archive_state", lambda _ctx, _label: None)  # never moves a real state directory
    monkeypatch.setattr(ci_suite, "_spawn", lambda _ctx, _args, log_path: spawned.append(str(log_path)))
    monkeypatch.setattr(ci_suite, "_wait_until_serving", lambda _proc: None)
    monkeypatch.setattr(ci_suite, "_shutdown", lambda _proc, _label: 0)
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    return spawned


@pytest.fixture
def text_server(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from _serve(_TextHandler, ci_suite, monkeypatch)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_ceiling_is_buildgen_s_own_value(ci_suite: ModuleType, device: str) -> None:
    assert ci_suite._configured_max_connections(device) == device_max_connections(device_toml(device), _REPO_ROOT / "src")


def test_the_route_set_is_every_get_route_of_the_devices_api_reference(ci_suite: ModuleType, tmp_path: Path) -> None:
    reference = tmp_path / "fixture_device.json"
    routes = [{"method": "GET", "path": "/measurements", "groups": []}, {"method": "PUT", "path": "/sensors", "groups": []}, {"method": "GET", "path": "/status", "groups": []}]
    reference.write_text(json.dumps({"device": "fixture_device", "routes": routes}), encoding="utf-8")
    assert ci_suite._get_routes(reference) == ("/measurements", "/status")


@pytest.mark.usefixtures("json_server")
def test_run_11b_bursts_over_every_get_route_of_the_device(ci_suite: ModuleType, stubbed_run: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(_JsonHandler, "paths", [])
    monkeypatch.setattr(ci_suite, "_configured_max_connections", lambda _device: len(_ROUTES))
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    assert ci_suite._FAILURES == []
    assert Counter(_JsonHandler.paths) == {**dict.fromkeys(_ROUTES, ci_suite._CEILING_ROUNDS), "/status": ci_suite._CEILING_ROUNDS + 1}, _JsonHandler.paths


@pytest.mark.usefixtures("json_server")
def test_concurrent_get_returns_status_and_parsed_body_for_every_request(ci_suite: ModuleType) -> None:
    results = ci_suite._concurrent_get(["/status", "/sensors", "/system"], timeout=_GET_TIMEOUT_S)
    assert results == [(200, {"ok": True})] * 3


@pytest.mark.usefixtures("hang_up_server")
def test_concurrent_get_records_a_refused_request_as_its_error_repr(ci_suite: ModuleType) -> None:
    results = ci_suite._concurrent_get(["/status", "/sensors"], timeout=_GET_TIMEOUT_S)
    assert len(results) == 2, results
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
        raise ValueError("devices/fixture_device.toml is not TOML")

    monkeypatch.setattr(ci_suite, "_configured_max_connections", broken)
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    assert len(ci_suite._FAILURES) == 1, ci_suite._FAILURES
    assert "cannot read the device's ceiling" in ci_suite._FAILURES[0]
    assert "is not TOML" in ci_suite._FAILURES[0]
    assert stubbed_run == []


def test_a_dut_that_never_serves_fails_the_run_once_and_still_shuts_it_down(ci_suite: ModuleType, stubbed_run: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The run's own catch: a crash here is one named failure, never an escape that skips the
    # shutdown and leaves a twin holding the port for every later run.
    def never_serves(_proc: object) -> None:
        raise TimeoutError("no answer on /status within 60s")

    shut_down: list[str] = []

    def shutdown(_proc: object, label: str) -> int:
        shut_down.append(label)
        return 0

    monkeypatch.setattr(ci_suite, "_configured_max_connections", lambda _device: 3)
    monkeypatch.setattr(ci_suite, "_wait_until_serving", never_serves)
    monkeypatch.setattr(ci_suite, "_shutdown", shutdown)
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    assert ci_suite._FAILURES == ["Run 11b (full-ceiling concurrency): TimeoutError('no answer on /status within 60s')"]
    assert shut_down == ["Run 11b"]


@pytest.mark.usefixtures("json_server")
def test_an_unclean_shutdown_after_a_served_ceiling_is_still_a_failure(ci_suite: ModuleType, stubbed_run: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci_suite, "_configured_max_connections", lambda _device: 3)
    monkeypatch.setattr(ci_suite, "_shutdown", lambda _proc, _label: 1)
    ci_suite._run_11b_full_ceiling_concurrency(_ctx(ci_suite, tmp_path))
    assert len(ci_suite._FAILURES) == 1, ci_suite._FAILURES
    assert "Run 11b: clean shutdown (exit code 1)" in ci_suite._FAILURES[0]
