"""The lwIP send stall on silicon (SPECIFICATION.md B.14.4): clients that stop reading mid-response fill the stack, and
a non-blocking send that met ERR_MEM spun the VM in the pinned modlwip; the override returns EAGAIN instead. Proven
twice: the round's unpatched control image must stall, the normal image must not; one hammer and one set of bounds."""

import dataclasses
import fcntl
import json
import re
import socket
import struct
import termios
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
from error_log_helpers import assert_no_task_ended, save_errcount
from harness import _wait_for_slots_to_drain, boot_lines, configured_max_connections, crash_lines, get_routes, observe_during, reflash, save_fram_raw, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("webserver_concurrency",)

# @tunable l4.lwip_stall_settle_s = 2.0
_STALL_SETTLE_S = 2.0
# @tunable l4.lwip_slow_client_bytes_per_s = 256
_SLOW_CLIENT_BPS = 256
# A request served while the stack is full: well under the 5 s per-call timeout and the stall's up-to-10 s freeze.
# @tunable l4.lwip_spin_concurrent_request_max_s = 3.0
_REQUEST_MAX_S = 3.0
# @tunable l4.lwip_stall_hold_s = 10.0
_HOLD_S = 10.0
# @tunable l4.lwip_stall_status_poll_s = 0.5
_STATUS_POLL_S = 0.5
# @tunable l4.lwip_stall_stopped_answering_s = 5.0
_STOPPED_ANSWERING_S = 5.0
# @tunable l4.lwip_stall_raw_socket_timeout_s = 10.0
_RAW_SOCKET_TIMEOUT_S = 10.0
# @tunable l4.lwip_stall_drain_timeout_s = 30.0
_DRAIN_TIMEOUT_S = 30.0
# @tunable l4.lwip_stall_serving_timeout_s = 120.0
_SERVING_TIMEOUT_S = 120.0
# @tunable l4.lwip_stall_join_timeout_s = 30.0
_JOIN_TIMEOUT_S = 30.0
_MIN_ZERO_WINDOW = 2  # connections the stall needs at zero window, its precondition
_LARGEST_ASSET = "/js/app.js"  # the largest static file a page load fetches
_ASSET = re.compile(r'(?:src|href)="([^"#:?]+)"')
_FIONREAD = termios.FIONREAD
_REMOVAL_SIGNAL = "the hammer did not reach the ERR_MEM loop on the unpatched image, or the pin carries an upstream fix: re-check the modlwip_eagain override (SPECIFICATION.md B.14)"


@dataclasses.dataclass
class _Verdicts:
    # What one hammer run measured: each bound's verdict and the figures behind it, recorded either way.
    page_s: "float | None" = None
    zero_window: int = 0
    status_max_s: float = 0.0
    status_over: "list[str]" = dataclasses.field(default_factory=list)
    stopped_s: float = 0.0
    rebooted: bool = False
    crash: "list[str]" = dataclasses.field(default_factory=list)
    drained: bool = False
    page_after: bool = False
    edges: "dict[str, float]" = dataclasses.field(default_factory=dict)
    refused: "dict[str, int]" = dataclasses.field(default_factory=dict)  # dead clients the ceiling refused, per edge

    def failed_bounds(self) -> "list[str]":
        failed = [] if self.page_s is not None and self.page_s <= _REQUEST_MAX_S else [f"page load {self.page_s} s > {_REQUEST_MAX_S} s"]
        failed += [f"GET /status {over}" for over in self.status_over]
        failed += [f"stopped answering {self.stopped_s:.1f} s"] if self.stopped_s >= _STOPPED_ANSWERING_S else []
        failed += ["rebooted"] if self.rebooted else []
        failed += [f"crash lines {self.crash[:3]}"] if self.crash else []
        failed += [] if self.drained else ["the slots did not drain"]
        failed += [] if self.page_after else ["no full page load after the clients closed"]
        return failed


def test_no_send_stall_with_the_override(board: "Board", dut_ip: str, result_note: "_load.Note") -> None:
    # A failed bound goes to the owner as an override change (a short POLLOUT back-off), never a larger bound.
    verdicts = _measure(board, dut_ip)
    _note(result_note, "the normal image", verdicts)
    assert verdicts.zero_window >= _MIN_ZERO_WINDOW, f"only {verdicts.zero_window} connection(s) reached zero window: the patched branch was never proven reached"
    assert not verdicts.failed_bounds(), f"the override did not hold: {verdicts.failed_bounds()}"
    assert_no_task_ended(dut_ip, "the lwIP send-stall hammer")


@pytest.mark.flash_cycle
def test_send_stall_on_the_unpatched_image(board: "Board", bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # The control image the round built (--lwip-control-image) must stall where the normal image does not; both flash
    # cycles are this test's, and the FRAM evidence is saved first (a reflash is a clearing path).
    if not request.config.getoption("--allow-flash-cycle"):
        pytest.skip("flashes the control image and the normal one back - pass --allow-flash-cycle to deliberately run it")
    option = request.config.getoption("--lwip-control-image")
    assert option, "--lwip-control-image names no control image: the round builds it in a throwaway worktree (tests_hardware/README.md)"
    control = Path(option)
    assert control.is_file(), f"the control image {control} does not exist"
    record = json.loads(control.with_suffix(".json").read_text(encoding="utf-8"))
    assert isinstance(record, dict), f"no image record beside the control image: {control.with_suffix('.json')}"
    assert record.get("overrides") == [], f"the control image's record names overrides {record.get('overrides')!r}, not []: it is no unpatched image"
    reason = request.node.name
    save_errcount(dut_ip, reason)
    save_fram_raw(board, reason)
    release_uf2, release_record = _load.round_image(request)
    try:
        reflash(board, control)
        wait_until(lambda: _load.serving(dut_ip), timeout_s=_SERVING_TIMEOUT_S, description="the control image serving")
        assert _load.image_deviations(request, dut_ip, record) == [], f"the board does not run the control image: {_load.image_deviations(request, dut_ip, record)}"
        verdicts = _measure(board, dut_ip)
        _note(result_note, "the unpatched control image", verdicts)
    finally:
        reflash(board, release_uf2)
        wait_until(lambda: _load.serving(dut_ip), timeout_s=_SERVING_TIMEOUT_S, description="the round's image serving again")
        assert _load.image_deviations(request, dut_ip, release_record) == [], f"the board is not back on the round's image: {_load.image_deviations(request, dut_ip, release_record)}"
    assert verdicts.failed_bounds(), _REMOVAL_SIGNAL


def _boot(dut_ip: str) -> "tuple[object, object]":
    system = _load.as_object(_load.get_object(dut_ip, "/status").get("system"), "GET /status system")
    return system.get("BootSignature"), system.get("SysUptime")


def _hammer(dut_ip: str) -> _Verdicts:
    # The segment-pool edge (configured_max_connections() - 1 non-readers of the largest asset) with a timed page load,
    # then each JSON route and page asset with a dead and a slow client (the arena and per-pcb edges), then the drain.
    verdicts = _Verdicts()
    ceiling = configured_max_connections()
    sockets: list[socket.socket] = []
    try:
        sockets.extend(_non_reader(dut_ip, _LARGEST_ASSET) for _ in range(ceiling - 1))  # each kept as made, for the finally
        time.sleep(_STALL_SETTLE_S)
        first = [_queued(sock) for sock in sockets]
        time.sleep(_STALL_SETTLE_S)
        verdicts.zero_window = sum(1 for before, sock in zip(first, sockets, strict=True) if before and _queued(sock) == before)
        started = time.monotonic()
        try:
            page = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=_STOPPED_ANSWERING_S * 2)
            verdicts.page_s = time.monotonic() - started if page.status_code == 200 else None
        except (OSError, http_client.HTTP_ERROR):
            verdicts.page_s = None
        verdicts.edges["segment pool: page load"] = time.monotonic() - started
    finally:
        for sock in sockets:
            sock.close()
    for path in [*get_routes(), *_page_assets(dut_ip)]:
        _hold(dut_ip, verdicts, path, dead=[path], slow=[path])
    try:
        _wait_for_slots_to_drain(dut_ip, 80, ceiling, timeout_s=_DRAIN_TIMEOUT_S)
        verdicts.drained = True
    except AssertionError:
        verdicts.drained = False
    try:
        verdicts.page_after = all(http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_REQUEST_MAX_S * 2).status_code == 200 for path in ["/", *_page_assets(dut_ip)])
    except (OSError, http_client.HTTP_ERROR, AssertionError):
        verdicts.page_after = False
    return verdicts


def _hold(dut_ip: str, verdicts: _Verdicts, label: str, dead: "list[str]", slow: "list[str]") -> None:
    # `dead` non-readers and `slow` slow readers held for _HOLD_S while the /status loop measures; closed after.
    stop = threading.Event()
    sockets: list[socket.socket] = []
    threads = [threading.Thread(target=_status_loop, args=(dut_ip, stop, verdicts, label), name=f"status-{label}")]
    threads += [threading.Thread(target=_slow_reader, args=(dut_ip, path, stop), name=f"slow-{path}") for path in slow]
    try:
        for path in dead:
            try:
                sockets.append(_non_reader(dut_ip, path))
            except OSError:  # refused at the ceiling: counted, so an edge never driven shows in the record
                verdicts.refused[label] = verdicts.refused.get(label, 0) + 1
        for thread in threads:
            thread.start()
        stop.wait(_HOLD_S)
    finally:
        stop.set()
        alive = _load.join(threads, _JOIN_TIMEOUT_S)
        for sock in sockets:
            sock.close()
    assert not alive, f"{alive} still running after {label}"


def _measure(board: "Board", dut_ip: str) -> _Verdicts:
    # One hammer under observe_during(), with the boot read before and after: a reset, a crash line and every bound.
    boot_before = _boot(dut_ip)
    verdicts, lines = observe_during(board, lambda: _hammer(dut_ip))
    verdicts.crash = crash_lines(lines)
    try:
        signature, uptime = _boot(dut_ip)
        verdicts.rebooted = signature != boot_before[0] or not (isinstance(uptime, int) and isinstance(boot_before[1], int) and uptime > boot_before[1]) or bool(boot_lines(lines))
    except (OSError, http_client.HTTP_ERROR, AssertionError):
        verdicts.rebooted = True
    return verdicts


def _non_reader(dut_ip: str, path: str) -> socket.socket:
    # A client requesting `path` that never reads: a minimal receive buffer, so its window closes soon.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1)  # the kernel rounds it up to its own minimum
    sock.settimeout(_RAW_SOCKET_TIMEOUT_S)
    sock.connect((dut_ip, 80))
    sock.sendall(f"GET {path} HTTP/1.1\r\nHost: dut\r\n\r\n".encode())
    return sock


def _note(result_note: "_load.Note", image: str, verdicts: _Verdicts) -> None:
    result_note(f"{image}: page load {verdicts.page_s} s with {verdicts.zero_window} connection(s) at zero window; /status max {verdicts.status_max_s:.2f} s, longest silence {verdicts.stopped_s:.1f} s; per edge (s): {verdicts.edges}; refused dead clients: {verdicts.refused or 'none'}; failed bounds: {verdicts.failed_bounds() or 'none'}")


def _page_assets(dut_ip: str) -> "list[str]":
    # The served index.html's own asset paths, as a browser's page load requests them.
    index = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=_RAW_SOCKET_TIMEOUT_S)
    assert index.status_code == 200, f"the index page is unavailable: {index.status_code}"
    return sorted({"/" + a.lstrip("./") for a in _ASSET.findall(index.body.decode("utf-8", "replace"))})


def _queued(sock: socket.socket) -> int:
    # The host receive queue's byte count (FIONREAD): a non-reader's queue stops growing at zero window.
    return int(struct.unpack("i", fcntl.ioctl(sock.fileno(), _FIONREAD, b"\x00\x00\x00\x00"))[0])


def _slow_reader(dut_ip: str, path: str, stop: threading.Event) -> None:
    # A client reading `path` at _SLOW_CLIENT_BPS until it ends or the test stops.
    try:
        with socket.create_connection((dut_ip, 80), timeout=_RAW_SOCKET_TIMEOUT_S) as sock:
            sock.sendall(f"GET {path} HTTP/1.1\r\nHost: dut\r\nConnection: close\r\n\r\n".encode())
            while not stop.is_set() and sock.recv(_SLOW_CLIENT_BPS):
                stop.wait(1.0)
    except (OSError, http_client.HTTP_ERROR):
        pass  # a refusal or a reclaimed connection ends the slow client; the /status loop is what is judged


def _status_loop(dut_ip: str, stop: threading.Event, verdicts: _Verdicts, label: str) -> None:
    # GET /status every _STATUS_POLL_S while the clients hold: each response time against the bound, the longest
    # stretch with no answer at all.
    last_answer = time.monotonic()
    while not stop.wait(_STATUS_POLL_S):
        started = time.monotonic()
        try:
            ok = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_STOPPED_ANSWERING_S * 2).status_code == 200
        except (OSError, http_client.HTTP_ERROR):
            ok = False
        elapsed = time.monotonic() - started
        verdicts.status_max_s = max(verdicts.status_max_s, elapsed)
        verdicts.edges[label] = max(verdicts.edges.get(label, 0.0), elapsed)
        if ok:
            last_answer = time.monotonic()
            if elapsed > _REQUEST_MAX_S:
                verdicts.status_over.append(f"{elapsed:.2f} s under {label}")
        verdicts.stopped_s = max(verdicts.stopped_s, time.monotonic() - last_answer)
