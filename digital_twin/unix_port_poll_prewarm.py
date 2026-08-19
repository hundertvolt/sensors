"""Workaround for a confirmed real bug in the pinned MicroPython v1.28.0 Unix port's
`extmod/modselect.c` (BACKLOG.md open question #7's real root cause, found via a direct DEBUG=1
gdb/core-dump investigation - not previously root-caused): `poll_set_add_fd()`'s "grow the pollfds
array" fallback path (taken whenever `m_renew_maybe()` can't extend the array in place, so a fresh
`m_new()` + `memcpy()` + `m_del()` is used instead) updates *every* currently-registered poll_obj_t's
`->pollfd` pointer unconditionally:

    poll_obj->pollfd = new_fds + (poll_obj->pollfd - poll_set->pollfds);

This is correct for fd-backed poll objects, but for a *non-fd* poll object (`pollfd == NULL` by
design - see that struct's own field comment) it silently recomputes `pollfd` from a bogus
`(NULL - old_pollfds_base)` pointer difference, turning a legitimately-NULL field into a small,
garbage non-NULL "pointer" (confirmed directly via gdb: two independent crashes showed `pollfd`
holding a small, heap-relative-looking value alongside `ioctl == iobase_ioctl`, i.e. exactly a
non-fd poll object). The next `poll()`/`ipoll()` call then dereferences that garbage pointer -
`poll_obj_get_revents()` at modselect.c:132, `return poll_obj->pollfd->revents;` - and segfaults.
Confirmed reproducible on demand (100% at a heap capped to <=800KB via `-X heapsize=`, and on the
very first attempt replicating the original discovery conditions at the stock default heap) as long
as at least one non-fd poll object is registered *at the moment* a pollfds-array growth event falls
back to the new-allocation path - which only takes crossing the fourth-concurrently-registered-fd
boundary (`POLL_SET_ALLOC_INCREMENT == 4`) while any object without a real file descriptor happens
to already be registered on the same shared `asyncio` poller. Confirmed via `git log` against a
freshly-fetched `origin/master` that no fix for this exists upstream yet, past this pinned v1.28.0.

**Confirmed Unix-port-only, not a rp2040 risk**: `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` (the macro
gating the entire `pollfd`/`pollfds`-array code path in modselect.c, including the exact buggy
line above) defaults to 0 in `py/mpconfig.h` and is only overridden to 1 by the Unix port's own
`ports/unix/variants/mpconfigvariant_common.h`; the rp2 port defines no such override, so this
whole code path - the vulnerable growth logic included - is compiled out of real rp2040 firmware
entirely. rp2's non-optimized poll_obj_t has no `pollfd` field and no `pollfds` array to grow, so
this specific bug class cannot occur there. This module and everything in it is therefore a
Unix-port test/dev-tooling concern only; it is deliberately not imported from anything in `src/`
(which is shared, frozen into real firmware too) - see CLAUDE.md's `digital_twin/` scope note.

**The workaround**: since we can't patch vendored/pinned MicroPython C source (CLAUDE.md's hard
rule), and the corruption only happens the *first* time a growth event's new-allocation fallback
runs while a non-fd poll object already exists, pre-registering (and then unregistering) enough
dummy real-fd objects - *before anything else in the process has registered even one poll
object* - grows `poll_set->pollfds` up to a generous ceiling while the map is still completely
empty (nothing non-fd yet exists to corrupt). Unregistering afterwards frees the slots
(`pollfd->fd = -1`, reusable) without ever shrinking `alloc` back down (modselect.c has no
compaction logic), so as long as real peak concurrent fd registrations never reach the ceiling
again, the buggy growth branch never executes again for the rest of the process's life - verified
directly: 20/20 clean runs (0 crashes) across both the deterministic small-heap repro and the
original-discovery-conditions repro, versus 100% reliable crash without this pre-warming, done with
identical timing but *after* other services had already started (confirming the "before anything
else registers" ordering is load-bearing, not incidental).

Call `prewarm_poll_set()` as the very first statement of any Unix-port test/stress entry point that
boots the real `sensortask_wozi` system, strictly before creating its task.
"""

# asyncio.core is a private implementation module (the whole point here is reaching into its
# _io_queue), not part of the public API the stubs package covers - see
# asy_webserver_service.py's own identical import comment for the same situation with microdot.
import asyncio.core as _core  # type: ignore[import-not-found]
import select
import socket

_DEFAULT_CEILING = 32  # comfortably above every concurrent-registration count observed in this
# codebase's own soak/stress testing (webserver max_connections=3, plus the fixed small set of
# background service sockets - DNS/NTP/wifi - peaking around 18 in a deliberately adversarial
# 8-concurrent-client burst; see BACKLOG.md open question #7's re-investigation note for the exact
# trace this number is based on).


def prewarm_poll_set(ceiling: int = _DEFAULT_CEILING, port: int = 18099) -> None:
    """Grow asyncio's shared `select.poll()` pollfds array to `ceiling` slots using real loopback
    connections, then release them. Must run before any other code in the process registers a poll
    object - see this module's own docstring for why the ordering matters. `port` only needs to be
    free for the brief window this function runs; it doesn't need to match anything else."""
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
