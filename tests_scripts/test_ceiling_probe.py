"""Covers tests_hardware/harness.py's discover_max_connections() and its drain wait offline, against a
loopback server shaped like _serve(): reject-when-full, an idle-read timeout, a whole-request cap and
a slot freed only once its connection closes (SPECIFICATION.md Part H.7.1)."""

import socket
import struct
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import harness
from harness import _still_open, _wait_for_slots_to_drain, discover_max_connections


class _CeilingServer:
    """Admits `ceiling` connections; each is closed after `idle_s` without a byte or `cap_s` in all.
    Options mimic the board: `serve_s` holds a slot that long after the client's EOF (microdot serving
    it), `answer` writes a response at once, `rst_refusals` refuses by RST rather than by FIN."""

    def __init__(self, ceiling: int, idle_s: float = 5.0, cap_s: float = 15.0, serve_s: float = 0.0, *, answer: bool = False, rst_refusals: bool = False) -> None:
        self.ceiling, self.idle_s, self.cap_s, self.serve_s = ceiling, idle_s, cap_s, serve_s
        self.answer, self.rst_refusals = answer, rst_refusals
        self.live = 0
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._server = socket.create_server(("127.0.0.1", 0))
        self._server.settimeout(0.05)
        self.port = self._server.getsockname()[1]
        self._threads = [threading.Thread(target=self._accept)]
        self._threads[0].start()

    def _accept(self) -> None:
        while not self._done.is_set():
            try:
                conn, _addr = self._server.accept()
            except TimeoutError:
                continue
            with self._lock:
                admitted = self.live < self.ceiling
                self.live += admitted
            if not admitted:
                if self.rst_refusals:
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                conn.close()  # reject-when-full: closed at once, nothing written
                continue
            thread = threading.Thread(target=self._hold, args=(conn,))
            self._threads.append(thread)
            thread.start()

    def _hold(self, conn: socket.socket) -> None:
        cap_at = time.monotonic() + self.cap_s
        conn.settimeout(min(self.idle_s, 0.05))
        quiet_since = time.monotonic()
        try:
            if self.answer:
                conn.sendall(b"HTTP/1.0 200 OK\r\n\r\n")
            while not self._done.is_set() and time.monotonic() < cap_at and time.monotonic() - quiet_since < self.idle_s:
                try:
                    if conn.recv(4096) == b"":
                        self._done.wait(self.serve_s)  # EOF ends microdot's headers: it serves, slot held
                        break
                    quiet_since = time.monotonic()
                except TimeoutError:
                    continue
        except OSError:
            pass
        finally:
            conn.close()
            with self._lock:
                self.live -= 1

    def close(self) -> None:
        self._done.set()
        for thread in self._threads:
            thread.join(timeout=5.0)
        self._server.close()


@pytest.fixture
def serve() -> Iterator[list[_CeilingServer]]:
    servers: list[_CeilingServer] = []
    yield servers
    for server in servers:
        server.close()


def test_the_walk_finds_the_servers_own_ceiling(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=4))
    assert discover_max_connections("127.0.0.1", server.port, settle_s=0.0, dwell_s=0.05) == 4


def test_the_walk_outlasts_the_idle_read_timeout_by_padding_every_held_connection(serve: list[_CeilingServer]) -> None:
    # 8 dwells of 0.1s against a 0.6s idle timeout: unpadded, the first slots free before the last is
    # taken and the walk never meets a refusal. The shape the walk had before it padded.
    serve.append(server := _CeilingServer(ceiling=8, idle_s=0.6))
    assert discover_max_connections("127.0.0.1", server.port, settle_s=0.0, dwell_s=0.1) == 8


def test_a_refused_connect_is_read_as_the_wall_never_raised_as_a_bare_socket_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Nothing listening: the stack refuses the connect itself, as a PCB-exhausted board does. The
    # walk counts it; only the drain wait after it may fail, and by name.
    walked: list[int] = []
    monkeypatch.setattr(harness, "_wait_for_slots_to_drain", lambda *_args, **_kwargs: walked.append(1))
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    assert discover_max_connections("127.0.0.1", port, settle_s=0.0, dwell_s=0.05) == 0
    assert walked == [1], "the drain wait must still run after a walk that ended at the connect"


def test_the_drain_wait_returns_once_a_slot_is_free(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=1))
    _wait_for_slots_to_drain("127.0.0.1", server.port, 1, timeout_s=2.0, release_s=0.0)


def test_the_drain_wait_never_mistakes_a_full_server_for_a_free_one(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=1))
    holder = socket.create_connection(("127.0.0.1", server.port))
    try:
        time.sleep(0.1)  # admitted, so every later connection is refused
        with pytest.raises(AssertionError, match="did not drain"):
            _wait_for_slots_to_drain("127.0.0.1", server.port, 1, timeout_s=0.8, release_s=0.0)
    finally:
        holder.close()


def test_the_drain_wait_never_mistakes_a_connect_timeout_for_a_free_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    # The old shape shared one 0.3s timeout between connect and read, so a slow handshake timing out
    # read as "held open, a slot is free" - on a board whose slots were all still taken.
    def slow_handshake(_sock: socket.socket, _address: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket.socket, "connect", slow_handshake)
    with pytest.raises(AssertionError, match="did not drain"):
        _wait_for_slots_to_drain("127.0.0.1", 9, 1, timeout_s=0.5, release_s=0.0)


def _held_at_once(port: int, count: int) -> int:
    socks = [socket.create_connection(("127.0.0.1", port)) for _ in range(count)]
    try:
        time.sleep(0.1)  # long enough for a refusal to land
        return sum(_still_open(sock) for sock in socks)
    finally:
        for sock in socks:
            sock.close()


def test_the_walk_returns_only_once_its_whole_ceiling_is_admittable_again(serve: list[_CeilingServer]) -> None:
    # Every closed probe is still served for a while, as microdot serves an EOF-ended request. Waiting
    # for one free slot returned with the rest still busy, and the drain's own probe holding another.
    serve.append(server := _CeilingServer(ceiling=4, serve_s=0.2))
    assert discover_max_connections("127.0.0.1", server.port, settle_s=0.5, dwell_s=0.05) == 4
    assert server.live == 0, f"{server.live} slots were still taken when the walk returned"
    assert _held_at_once(server.port, 4) == 4


def test_the_drain_wait_needs_the_whole_ceiling_not_one_slot(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=2))
    holder = socket.create_connection(("127.0.0.1", server.port))
    try:
        time.sleep(0.1)  # one of two slots taken: one more is admittable, the whole ceiling is not
        with pytest.raises(AssertionError, match="never held 2 connections at once"):
            _wait_for_slots_to_drain("127.0.0.1", server.port, 2, timeout_s=0.8, release_s=0.0)
    finally:
        holder.close()


def test_a_walk_the_server_answers_is_refused_as_no_ceiling(serve: list[_CeilingServer], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_wait_for_slots_to_drain", lambda *_args, **_kwargs: None)
    serve.append(server := _CeilingServer(ceiling=4, answer=True))
    with pytest.raises(AssertionError, match=r"answered .* instead of being held open"):
        discover_max_connections("127.0.0.1", server.port, settle_s=0.0, dwell_s=0.05)


def test_a_failing_drain_after_a_failed_walk_never_hides_the_walks_own_error(serve: list[_CeilingServer], monkeypatch: pytest.MonkeyPatch) -> None:
    def drain_fails(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the slots did not drain")

    monkeypatch.setattr(harness, "_wait_for_slots_to_drain", drain_fails)
    serve.append(server := _CeilingServer(ceiling=4, answer=True))
    with pytest.raises(AssertionError, match=r"instead of being held open.*the drain wait after it failed too: the slots did not drain"):
        discover_max_connections("127.0.0.1", server.port, settle_s=0.0, dwell_s=0.05)


def test_a_walk_that_exhausts_its_probe_limit_says_so_by_name(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=50))
    with pytest.raises(AssertionError, match="no connection was refused within 3 attempts"):
        discover_max_connections("127.0.0.1", server.port, probe_limit=3, settle_s=0.0, dwell_s=0.05)


def test_a_held_connection_the_server_closes_mid_walk_voids_the_count(serve: list[_CeilingServer]) -> None:
    # The whole-request cap firing mid-walk: the count so far was never held all at once.
    serve.append(server := _CeilingServer(ceiling=20, cap_s=0.3))
    with pytest.raises(AssertionError, match="no longer held"):
        discover_max_connections("127.0.0.1", server.port, settle_s=0.0, dwell_s=0.1)


def test_a_refusal_by_rst_is_read_as_the_wall(serve: list[_CeilingServer]) -> None:
    # The board refuses with an RST once a refused client's request bytes have arrived.
    serve.append(server := _CeilingServer(ceiling=3, rst_refusals=True))
    assert discover_max_connections("127.0.0.1", server.port, settle_s=0.0, dwell_s=0.05) == 3


def test_the_drain_wait_reads_an_rst_refusal_as_not_yet(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=1, rst_refusals=True))
    holder = socket.create_connection(("127.0.0.1", server.port))
    try:
        time.sleep(0.1)
        with pytest.raises(AssertionError, match="did not drain"):
            _wait_for_slots_to_drain("127.0.0.1", server.port, 1, timeout_s=0.8, release_s=0.0)
    finally:
        holder.close()
