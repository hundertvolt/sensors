"""Workaround for a confirmed MicroPython v1.28.0 Unix-port-only `extmod/modselect.c` segfault (pollfds-array growth corrupts non-fd poll objects; confirmed rp2-immune) — full mechanism and the fix's verified evidence: see `digital_twin/README.md`'s "Known gaps" section.
Call `prewarm_poll_set()` as the very first statement of any entry point booting `sensortask_wozi`."""

# asyncio.core is a private implementation module (the whole point here is reaching into its
# _io_queue), not part of the public API the stubs package covers - see
# asy_webserver_service.py's own identical import comment for the same situation with microdot.
import asyncio.core as _core  # type: ignore[import-not-found]
import select
import socket

_DEFAULT_CEILING = 512  # ~28x every concurrent-registration count observed in this codebase's own
# soak/stress testing (webserver max_connections=3, plus the fixed small set of background service
# sockets - DNS/NTP/wifi - peaking around 18 in a deliberately adversarial 8-concurrent-client burst).
# This workaround is still fundamentally a raised threshold, not an unconditional fix - see the
# module docstring's "as long as real peak concurrent fd registrations never reach the ceiling again"
# caveat - so the margin is deliberately generous rather than just-above-observed: measured at ~45ms
# of one-time startup cost (well under a second, loopback-only, no realistic risk of exhausting the
# host's fd limit), which is cheap enough that there is no real reason to cut it closer.


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
    clients = []
    servers = []
    try:
        for _ in range(ceiling):
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.connect(addr)
            s, _peer = listener.accept()
            clients.append(c)
            servers.append(s)
            poller.register(s, select.POLLIN)
    finally:
        for s in servers:
            poller.unregister(s)
            s.close()
        for c in clients:
            c.close()
        listener.close()
