"""Workaround for the Unix port's extmod/modselect.c pollfds growth, which corrupts poll objects
registered over non-fd streams (rp2-immune: compiled out there): grow asyncio's poll set once, before anything
registers. A known limitation, not reported upstream (owner, 2026-09-29); SPECIFICATION.md F.7 states it."""

# asyncio.core is private: reaching its _io_queue is the point (the stubs cover only the public API).
import asyncio.core as _core  # type: ignore[import-not-found]
import select
import socket

# A raised threshold, not a fix: well above 3 x the largest max_connections of any devices/*.toml (the peak of accepted
# connections in any tier; tests_scripts/test_twin_entry_point_order.py checks it); ~45 ms at startup.
_DEFAULT_CEILING = 512

# Its own band (a fixed row of tests/_port_bands.py), clear of test_digital_twin_http_client.py's canned servers.
# Scanned rather than fixed: scripts/test.sh runs usable cores x 1-4 files at once, each calling this at import,
# and SO_REUSEADDR does not let two live listeners share a port (that is SO_REUSEPORT).
_PORT_SCAN_BASE = 17400
_PORT_SCAN_WINDOW = 64


def _bind_free_listener(port: int, ceiling: int, window: int = _PORT_SCAN_WINDOW) -> "tuple[socket.socket, tuple[str, int] | tuple[str, int, int, int]]":
    # The first free loopback port at or above `port`, already listening. A fresh socket per
    # attempt, because a bind that failed leaves nothing worth reusing - and the Unix port exposes no
    # getsockname(), so an ephemeral bind to port 0 could never be read back to connect to.
    for candidate in range(port, port + window):
        addr = socket.getaddrinfo("127.0.0.1", candidate)[0][-1]
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:  # listen() too: under SO_REUSEADDR two sockets can both bind, and the loser fails here
            listener.bind(addr)
            listener.listen(ceiling + 4)
        except OSError:
            listener.close()
            continue
        return listener, addr
    raise OSError(f"no free loopback port in {port}..{port + window - 1} to prewarm the poll set")


def prewarm_poll_set(ceiling: int = _DEFAULT_CEILING, port: int = _PORT_SCAN_BASE) -> "tuple[str, int] | tuple[str, int, int, int]":
    # Grow asyncio's shared `select.poll()` pollfds array to `ceiling` slots via real loopback connections, then release
    # them. Must run before any other code registers a poll object. `port` is the first of _PORT_SCAN_WINDOW candidates
    # tried and only has to be free while this runs.
    _core.get_event_loop()  # idempotent - ensures _io_queue exists without assuming it already does
    poller = _core._io_queue.poller
    listener, addr = _bind_free_listener(port, ceiling)
    servers = []
    try:
        for _ in range(ceiling):
            # Only the accepted server-side socket has to stay registered to force pollfds
            # growth; the client end is done once accept() returns. Closing it at once avoids
            # holding ~2x the ceiling open, which was raising OSError EMFILE here.
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.connect(addr)
            s, _peer = listener.accept()
            c.close()
            servers.append(s)
            poller.register(s, select.POLLIN)
    finally:
        for s in servers:
            poller.unregister(s)
            s.close()
        listener.close()
    # Returns the sockaddr it bound as getaddrinfo() gave it: typed as the stubs declare, packed bytes on the Unix port.
    return addr
