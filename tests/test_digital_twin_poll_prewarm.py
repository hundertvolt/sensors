"""Twin-tier coverage for digital_twin/unix_port_poll_prewarm.py's own port handling: it runs at
module import in several files that scripts/test.sh dispatches concurrently, so the port it binds
must never be one another process can already hold."""

import socket
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import unix_port_poll_prewarm
from microtest import run
from unix_port_poll_prewarm import _PORT_SCAN_BASE, _PORT_SCAN_WINDOW, _bind_free_listener, prewarm_poll_set


def _port_of(addr: "bytearray") -> int:
    # getaddrinfo() returns a packed sockaddr on this port, not the (host, port) tuple CPython
    # gives: bytes 2-3 are the port in network order, after the AF_INET family word.
    return (addr[2] << 8) | addr[3]


# The helper tests scan a band of their own: the real one is live under every concurrently
# running file's import-time prewarm, and a test filling it would starve those of a port.
_TEST_BASE = 17500
_TEST_WINDOW = 8


def _hold(port: int) -> "socket.socket":
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    holder.bind(socket.getaddrinfo("127.0.0.1", port)[0][-1])
    holder.listen(1)
    return holder


def test_a_port_another_process_already_holds_is_skipped_not_fatal() -> None:
    # The real CI failure this exists for: two files calling prewarm_poll_set() within the same
    # ~45ms window both bound one fixed port, and the loser died with EADDRINUSE at import - before
    # any test body ran, in whichever lane happened to lose (OSError 98, SO_REUSEADDR notwithstanding).
    holder = _hold(_TEST_BASE)
    try:
        listener, addr = _bind_free_listener(_TEST_BASE, 4, _TEST_WINDOW)
        try:
            assert _port_of(addr) == _TEST_BASE + 1, _port_of(addr)
        finally:
            listener.close()
    finally:
        holder.close()


def test_a_port_lost_between_bind_and_listen_is_skipped_too() -> None:
    # The race a bind-only guard left open: under SO_REUSEADDR two processes can both bind, and the
    # one that listens second fails at listen() - which escaped the scan as an import-time crash.
    created: list[object] = []

    class _LosesTheFirstListen:
        def __init__(self, family: int, kind: int) -> None:
            self._sock = socket.socket(family, kind)
            created.append(self)

        def __getattr__(self, name: str) -> object:
            return getattr(self._sock, name)

        def listen(self, backlog: int) -> None:
            if len(created) == 1:
                raise OSError(98)  # EADDRINUSE: the peer that also bound listened first
            self._sock.listen(backlog)

    class _SocketModule:
        socket = _LosesTheFirstListen

        def __getattr__(self, name: str) -> object:
            return getattr(socket, name)

    unix_port_poll_prewarm.socket = _SocketModule()  # type: ignore[attr-defined, assignment]  # deliberate monkeypatch
    try:
        listener, addr = _bind_free_listener(_TEST_BASE, 4, _TEST_WINDOW)
    finally:
        unix_port_poll_prewarm.socket = socket  # type: ignore[attr-defined]
    try:
        assert _port_of(addr) == _TEST_BASE + 1, _port_of(addr)
        assert len(created) == 2, len(created)
    finally:
        listener.close()


def test_every_port_of_a_full_window_is_tried_before_giving_up() -> None:
    # A narrow scan would reintroduce the same failure at higher parallelism, so the whole window
    # has to be genuinely walked - proven by holding all but the last port of a small one.
    held = [_hold(p) for p in range(_TEST_BASE, _TEST_BASE + _TEST_WINDOW - 1)]
    try:
        listener, addr = _bind_free_listener(_TEST_BASE, 4, _TEST_WINDOW)
        try:
            assert _port_of(addr) == _TEST_BASE + _TEST_WINDOW - 1, _port_of(addr)
        finally:
            listener.close()
    finally:
        for holder in held:
            holder.close()


def test_a_fully_occupied_window_fails_loudly_and_names_it() -> None:
    # Never a silent fallback onto some other port: an exhausted window means the run is far more
    # concurrent than this band was sized for, which is a thing to read in the log, not absorb.
    held = [_hold(p) for p in range(_TEST_BASE, _TEST_BASE + _TEST_WINDOW)]
    try:
        raised = ""
        try:
            _bind_free_listener(_TEST_BASE, 4, _TEST_WINDOW)
        except OSError as e:
            raised = str(e)
        assert str(_TEST_BASE) in raised, raised
        assert str(_TEST_BASE + _TEST_WINDOW - 1) in raised, raised
    finally:
        for holder in held:
            holder.close()


def test_the_prewarm_itself_still_grows_the_poll_set_when_its_base_is_taken() -> None:
    # End to end through the real entry point, not just the helper: the scan has to be reached from
    # prewarm_poll_set()'s own default, which is what every caller actually uses.
    try:
        holder = _hold(_PORT_SCAN_BASE)
    except OSError:
        holder = None  # another file's prewarm holds it right now, which takes it just as well
    try:
        addr = prewarm_poll_set(ceiling=8)
        if holder is not None:  # held by this test, so the prewarm must have scanned past it
            assert _port_of(addr) != _PORT_SCAN_BASE, _port_of(addr)
        assert _PORT_SCAN_BASE <= _port_of(addr) < _PORT_SCAN_BASE + _PORT_SCAN_WINDOW, _port_of(addr)
    finally:
        if holder is not None:
            holder.close()


def test_the_band_stays_clear_of_the_canned_http_servers_and_this_files_own() -> None:
    # 18099-18103 belong to test_digital_twin_http_client.py, and the old fixed 18099 sat right on
    # the first of them - a second collision, between two different files, on top of the self-clash.
    assert _PORT_SCAN_BASE + _PORT_SCAN_WINDOW <= _TEST_BASE, (_PORT_SCAN_BASE, _PORT_SCAN_WINDOW)
    assert _TEST_BASE + _TEST_WINDOW <= 18099, (_TEST_BASE, _TEST_WINDOW)


if __name__ == "__main__":
    run(globals())
