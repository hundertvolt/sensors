"""Workaround for a confirmed MicroPython Unix-port-only `extmod/modselect.c` segfault (traced at v1.28.0; that file is unchanged at the current v1.29.0 pin) (pollfds-array growth corrupts non-fd poll objects; confirmed rp2-immune) — full mechanism and the fix's verified evidence: see `digital_twin/README.md`'s "Known gaps" section.
Call `prewarm_poll_set()` as the very first statement of any entry point booting a `sensortask_<device>` module."""

# asyncio.core is a private implementation module (the whole point here is reaching into its
# _io_queue), not part of the public API the stubs package covers - see
# asy_webserver_service.py's own identical import comment for the same situation with microdot.
import asyncio.core as _core  # type: ignore[import-not-found]
import select
import socket

_DEFAULT_CEILING = 512  # ~28x every concurrent-registration count observed in this codebase's own
# soak/stress testing: max_connections=4 plus the background service sockets, peaking near 18 in
# an adversarial 8-client burst. Still a raised threshold rather than a fix, per the docstring's
# caveat, so the margin is generous - ~45ms of one-time startup is cheap enough not to cut close.


def prewarm_poll_set(ceiling: int = _DEFAULT_CEILING, port: int = 18099) -> None:
    """Grow asyncio's shared `select.poll()` pollfds array to `ceiling` slots via real loopback connections, then release them. Must run before any other code registers a poll object.
    `port` only needs to be free for the brief window this function runs."""
    _core.get_event_loop()  # idempotent - ensures _io_queue exists without assuming it already does
    poller = _core._io_queue.poller
    addr = socket.getaddrinfo("127.0.0.1", port)[0][-1]
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(addr)
    listener.listen(ceiling + 4)
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
