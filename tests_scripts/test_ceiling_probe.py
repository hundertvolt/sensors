"""Covers tests_hardware/harness.py's discover_max_connections() and its drain wait offline, against a
loopback server shaped like _serve(): reject-when-full, an idle-read timeout, a whole-request cap and
a slot freed only once its connection closes (SPECIFICATION.md Part H.7.1)."""

import socket
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

from harness import _wait_for_slots_to_drain, discover_max_connections


class _CeilingServer:
    """Admits `ceiling` connections; each is closed after `idle_s` without a byte or `cap_s` in all."""

    def __init__(self, ceiling: int, idle_s: float = 5.0, cap_s: float = 15.0) -> None:
        self.ceiling, self.idle_s, self.cap_s = ceiling, idle_s, cap_s
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
            while not self._done.is_set() and time.monotonic() < cap_at and time.monotonic() - quiet_since < self.idle_s:
                try:
                    if conn.recv(4096) == b"":
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
    import harness

    walked: list[int] = []
    monkeypatch.setattr(harness, "_wait_for_slots_to_drain", lambda _host, _port: walked.append(1))
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    assert discover_max_connections("127.0.0.1", port, settle_s=0.0, dwell_s=0.05) == 0
    assert walked == [1], "the drain wait must still run after a walk that ended at the connect"


def test_the_drain_wait_returns_once_a_slot_is_free(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=1))
    _wait_for_slots_to_drain("127.0.0.1", server.port, timeout_s=2.0)


def test_the_drain_wait_never_mistakes_a_full_server_for_a_free_one(serve: list[_CeilingServer]) -> None:
    serve.append(server := _CeilingServer(ceiling=1))
    holder = socket.create_connection(("127.0.0.1", server.port))
    try:
        time.sleep(0.1)  # admitted, so every later connection is refused
        with pytest.raises(AssertionError, match="did not drain"):
            _wait_for_slots_to_drain("127.0.0.1", server.port, timeout_s=0.8)
    finally:
        holder.close()


def test_the_drain_wait_never_mistakes_a_connect_timeout_for_a_free_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    # The old shape shared one 0.3s timeout between connect and read, so a slow handshake timing out
    # read as "held open, a slot is free" - on a board whose slots were all still taken.
    def slow_handshake(_sock: socket.socket, _address: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket.socket, "connect", slow_handshake)
    with pytest.raises(AssertionError, match="did not drain"):
        _wait_for_slots_to_drain("127.0.0.1", 9, timeout_s=0.5)
