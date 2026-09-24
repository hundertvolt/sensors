"""Workaround for a confirmed MicroPython Unix-port-only `extmod/modselect.c` segfault (traced at v1.28.0; that file is unchanged at the current v1.29.0 pin) (pollfds-array growth corrupts non-fd poll objects; confirmed rp2-immune) — full mechanism and the fix's verified evidence: see `digital_twin/README.md`'s "Known gaps" section.
Call `prewarm_poll_set()` as the very first statement of any entry point booting a `sensortask_<device>` module."""

# asyncio.core is a private implementation module (the whole point here is reaching into its
# _io_queue), not part of the public API the stubs package covers - see
# asy_webserver_service.py's own identical import comment for the same situation with microdot.
import asyncio.core as _core  # type: ignore[import-not-found]
import select
import socket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_DEFAULT_CEILING = 512  # ~28x the real peak: every device's max_connections is 6, and the hardest
# burst any tier drives is max(12, 3 x 6) = 18 clients (_webserver_concurrency_scenarios.py). A
# raised threshold, not a fix (see the docstring), so the margin stays generous; ~45ms at startup.

# Its own band, clear of test_digital_twin_http_client.py's canned servers at 18099-18103. Scanned
# rather than fixed: scripts/test.sh runs usable cores x 1-4 files at once, each calling this at
# import, and SO_REUSEADDR does not let two live listeners share a port (that is SO_REUSEPORT).
_PORT_SCAN_BASE = 17400
_PORT_SCAN_WINDOW = 64


def _bind_free_listener(port: int, ceiling: int, window: int = _PORT_SCAN_WINDOW) -> "tuple[Any, Any]":
    """The first free loopback port at or above `port`, already listening. A fresh socket per
    attempt, because a bind that failed leaves nothing worth reusing - and the Unix port exposes no
    getsockname(), so an ephemeral bind to port 0 could never be read back to connect to."""
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


def prewarm_poll_set(ceiling: int = _DEFAULT_CEILING, port: int = _PORT_SCAN_BASE) -> "Any":  # noqa: ANN401 - a packed sockaddr here, a tuple under CPython
    """Grow asyncio's shared `select.poll()` pollfds array to `ceiling` slots via real loopback connections, then release them. Must run before any other code registers a poll object.
    `port` is the first of _PORT_SCAN_WINDOW candidates tried and only has to be free while this runs; returns the packed sockaddr it actually bound."""
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
    return addr
