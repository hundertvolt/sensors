"""Bench-tier automated tests: the UART crossover link under the full production HTTP stack and
concurrent API load - the realistic deployed condition, where link work and request handling have
to coexist rather than each merely work alone (requirement H4)."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import http_client
import pytest
from error_log_helpers import get_errcount, reset_all_error_logs
from harness import wait_until

if TYPE_CHECKING:
    from harness import Board

_UART_MODULES = ("UART_INIT", "UART_RESP")
# GET only: every worker below hits a read-only endpoint, so nothing here can persist to flash in a
# loop. A PUT belongs in this tier only where it is documented command-only and never persisted.
_GET_WORKERS = 2
_GET_ITERATIONS_PER_WORKER = 10
# Generous next to a single request's own budget, but far below the point at which a stalled link
# would look like a slow one: the claim is coexistence, not a latency number.
_REQUEST_BUDGET_S = 15.0


def _require_uart_modules(dut_ip: str) -> None:
    # The link only exists in a firmware that actually contains asy_uart_comm, which today needs a
    # selectable `uart_crossover` module the auto-builder can include (BACKLOG.md). Until then the
    # two entries are simply absent from /status, which is a missing build dependency rather than a
    # failure - this test is written now and runs unchanged once such a firmware can be built.
    present = get_errcount(dut_ip)
    missing = [name for name in _UART_MODULES if name not in present]
    if missing:
        pytest.skip(
            f"this firmware exposes no {', '.join(missing)} error source - a selectable "
            "`uart_crossover` module is what makes the auto-builder include asy_uart_comm (BACKLOG.md)",
        )


def test_the_link_stays_healthy_while_the_api_is_hammered(board: Board, dut_ip: str) -> None:
    # H4.1: both sides have their own budget, and neither may be met by starving the other. The
    # API side is asserted on latency and status; the link side on its own error counters, which
    # is where a transfer that timed out under load would show up.
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip)

    errors: list[str] = []
    errors_lock = threading.Lock()

    def _record(msg: str) -> None:
        with errors_lock:
            errors.append(msg)

    def status_worker(worker_id: int) -> None:
        for i in range(_GET_ITERATIONS_PER_WORKER):
            started = time.monotonic()
            try:
                res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_REQUEST_BUDGET_S)
            except Exception as e:
                _record(f"worker {worker_id} iter {i}: {type(e).__name__}: {e}")
                continue
            elapsed = time.monotonic() - started
            if res.status_code != 200:
                _record(f"worker {worker_id} iter {i}: GET /status returned {res.status_code}: {res.body!r}")
            if elapsed > _REQUEST_BUDGET_S:
                _record(f"worker {worker_id} iter {i}: GET /status took {elapsed:.1f}s, past its own budget")

    threads = [threading.Thread(target=status_worker, args=(w,)) for w in range(_GET_WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120.0)
        assert not t.is_alive(), "a worker thread never finished within 120s - possible real deadlock under load"

    assert not errors, f"{len(errors)} issue(s) under concurrent API load: {'; '.join(errors[:10])}"

    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after the concurrent UART-load test",
    )

    counts = get_errcount(dut_ip)
    for name in _UART_MODULES:
        entry = counts.get(name, {})
        assert not entry.get("counter", 0), f"{name} logged errors while the API was under load: {entry!r}"


def test_an_api_overload_does_not_corrupt_the_link_or_the_reverse(board: Board, dut_ip: str) -> None:
    # The failure direction of the same claim: a burst past the server's comfortable concurrency
    # must degrade requests, never the link - and the link's own recovery must not show up as a
    # request failure either.
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip)

    completed: list[int] = []
    completed_lock = threading.Lock()

    def burst_worker() -> None:
        try:
            res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=_REQUEST_BUDGET_S)
        except Exception:  # a rejected connection under a deliberate overload is an accepted outcome
            return
        with completed_lock:
            completed.append(res.status_code)

    threads = [threading.Thread(target=burst_worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60.0)
        assert not t.is_alive(), "a burst worker never finished within 60s"

    assert any(code == 200 for code in completed), f"no request survived the burst at all: {completed!r}"

    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after the burst",
    )

    counts = get_errcount(dut_ip)
    for name in _UART_MODULES:
        entry = counts.get(name, {})
        assert not entry.get("counter", 0), f"{name} was disturbed by an API overload: {entry!r}"
