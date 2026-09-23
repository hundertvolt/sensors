"""Twin-tier coverage for digital_twin/unix_port_poll_prewarm.py's own port handling: it runs at
module import in several files that scripts/test.sh dispatches concurrently, so the port it binds
must never be one another process can already hold."""

import socket
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from microtest import run
from unix_port_poll_prewarm import _PORT_SCAN_BASE, _PORT_SCAN_WINDOW, _bind_free_listener, prewarm_poll_set


def _port_of(addr: "bytearray") -> int:
    # getaddrinfo() returns a packed sockaddr on this port, not the (host, port) tuple CPython
    # gives: bytes 2-3 are the port in network order, after the AF_INET family word.
    return (addr[2] << 8) | addr[3]


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
    holder = _hold(_PORT_SCAN_BASE)
    try:
        listener, addr = _bind_free_listener(_PORT_SCAN_BASE, 4)
        try:
            assert _port_of(addr) == _PORT_SCAN_BASE + 1, _port_of(addr)
        finally:
            listener.close()
    finally:
        holder.close()


def test_every_port_of_a_full_window_is_tried_before_giving_up() -> None:
    # A narrow scan would reintroduce the same failure at higher parallelism, so the whole window
    # has to be genuinely walked - proven by holding all but the last port of a small one.
    held = [_hold(p) for p in range(_PORT_SCAN_BASE, _PORT_SCAN_BASE + _PORT_SCAN_WINDOW - 1)]
    try:
        listener, addr = _bind_free_listener(_PORT_SCAN_BASE, 4)
        try:
            assert _port_of(addr) == _PORT_SCAN_BASE + _PORT_SCAN_WINDOW - 1, _port_of(addr)
        finally:
            listener.close()
    finally:
        for holder in held:
            holder.close()


def test_a_fully_occupied_window_fails_loudly_and_names_it() -> None:
    # Never a silent fallback onto some other port: an exhausted window means the run is far more
    # concurrent than this band was sized for, which is a thing to read in the log, not absorb.
    held = [_hold(p) for p in range(_PORT_SCAN_BASE, _PORT_SCAN_BASE + _PORT_SCAN_WINDOW)]
    try:
        raised = ""
        try:
            _bind_free_listener(_PORT_SCAN_BASE, 4)
        except OSError as e:
            raised = str(e)
        assert str(_PORT_SCAN_BASE) in raised, raised
        assert str(_PORT_SCAN_BASE + _PORT_SCAN_WINDOW - 1) in raised, raised
    finally:
        for holder in held:
            holder.close()


def test_the_prewarm_itself_still_grows_the_poll_set_when_its_base_is_taken() -> None:
    # End to end through the real entry point, not just the helper: the scan has to be reached from
    # prewarm_poll_set()'s own default, which is what every caller actually uses.
    holder = _hold(_PORT_SCAN_BASE)
    try:
        prewarm_poll_set(ceiling=8)
    finally:
        holder.close()


def test_the_band_stays_clear_of_the_canned_http_servers() -> None:
    # 18099-18103 belong to test_digital_twin_http_client.py, and the old fixed 18099 sat right on
    # the first of them - a second collision, between two different files, on top of the self-clash.
    assert _PORT_SCAN_BASE + _PORT_SCAN_WINDOW <= 18099, (_PORT_SCAN_BASE, _PORT_SCAN_WINDOW)


if __name__ == "__main__":
    run(globals())
