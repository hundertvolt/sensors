"""Async, non-blocking UDP wrapper around one MicroPython socket.socket - cooperative
send/receive driven by a hand-rolled select.poll loop (MicroPython's asyncio has no built-in
UDP-readiness primitive; open_connection()/start_server() are TCP-only). Two callers, two modes:
async_connect.py's NTP client (mode="client", one-shot object per sync attempt, connect() then
write_and_recvfrom()) and captive_dns.py's DNSServer (mode="server", one long-lived object,
bind() then a persistent recvfrom()/sendto() loop). Also usable as `async with AsyUDPSocket(...)
as sock:`, matching async_connect.py's actual acquire/use/release-in-finally usage.

Shared contract: every public I/O method (ready, sendto, write, recvfrom, write_and_recvfrom,
disconnect) returns its documented None-shaped sentinel on any socket failure (OSError) or
allocation failure (MemoryError - confirmed directly it is NOT an OSError subclass in
MicroPython, and realistic on RP2040's 264KB SRAM for a device meant to run unattended for years)
- neither is ever allowed to propagate from these methods. Unlike the I2C/SPI bus-driver carve-out
in src/README.md, no raw failure escapes here: network faults (unreachable host, a transient
route/DNS failure) and allocation pressure are expected, recoverable conditions, not hardware bugs
to surface upward.

The one deliberate exception is __init__ itself: mode/addr/conn_tries are validated eagerly and
raise ValueError/TypeError for a structurally invalid value - a bad constructor argument is a
programmer error, not a runtime network condition. Confirmed directly: an invalid mode used to
busy-loop forever with zero await points (a genuine unrecoverable lockup, not just a slow path -
the underlying coroutine never yields, so nothing else in the whole event loop can run either),
and a malformed addr/conn_tries used to raise an uncaught TypeError from deep inside _connect(),
bypassing every except clause in this file. Stored as _addr/_mode/_conn_tries (private) rather
than public attributes - __init__'s validation only runs once, at construction, so a direct
post-construction mutation of a public attribute would silently reintroduce the exact same
uncaught-TypeError risk through a different door (confirmed directly). The method-level except
clauses that touch these (see below) still widen to catch TypeError too, as a second line of
defense against whatever reaches them regardless of how it got there - not a reason to skip the
naming signal that these aren't meant to be reassigned from outside.

Concurrent calls into the same instance from multiple coroutines are supported for connect/
disconnect specifically: a per-instance asyncio.Lock serializes _connect()'s setup/retry phase
and disconnect()'s teardown against each other, so a second coroutine calling in while a first is
mid-retry joins/waits for that attempt instead of observing a premature "not ready" (confirmed
directly: without this, a concurrent caller got a spurious None while the first coroutine's retry
was still in progress), and a concurrent disconnect() can no longer yank self.sock/self.poller out
from under an in-flight retry (confirmed directly: this used to crash with an uncaught
AttributeError). The lock does not cover ready()'s own polling loop after a successful connect -
that phase is protected separately (see ready()'s own comment).

Content-agnostic transport: this module moves bytes and never inspects them - a datagram's
header/length validity (NTP, DNS, or otherwise) is entirely the caller's concern. Two POSIX-level
UDP properties this module relies on rather than reimplements, confirmed directly against this
project's MicroPython Unix-port build: (1) a datagram larger than the recv buffer is silently
truncated to that size with no error and no truncation signal (MSG_TRUNC/recvmsg() aren't exposed
by MicroPython's socket module) - callers needing to detect this must size their buffer
generously or add their own length-prefixed framing; (2) a connect()ed client socket has datagrams
from any address other than the connected peer filtered at the kernel level before they're ever
delivered - this is what makes mode="client" safe against off-path/spoofed senders without this
module doing any address checking of its own. mode="server" sockets are unconnected and receive
from anyone; source-address trust decisions there are the caller's (captive_dns.py checks nothing
today - out of scope for this transport-only module to fix).
"""

import asyncio
import select
import socket
import time

from micropython import const

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Literal

_RETRY_BACKOFF_S = const(0.5)  # pause between a failed connect()/bind() (or setup) attempt and the next


class AsyUDPSocket:
    def __init__(
        self,
        addr: tuple[str, int],
        mode: 'Literal["client", "server"]' = "client",
        conn_tries: int = 1,
    ) -> None:
        # Fail fast here rather than deep inside async code later - see the module docstring's
        # "one deliberate exception" paragraph for why this is the one place in the file allowed
        # to raise.
        if mode not in ("client", "server"):
            raise ValueError(f"mode must be 'client' or 'server', got {mode!r}")
        # addr is only validated when given as the documented tuple[str, int] shape - this file
        # only ever passes addr through untouched to socket.connect()/bind()/sendto() (see module
        # docstring), and a pre-resolved opaque sockaddr (bytes/bytearray - what some platforms'
        # socket.getaddrinfo() actually returns, confirmed directly on this project's own
        # MicroPython Unix-port test build) is just as legitimate as a plain tuple; this file has
        # no business inspecting its internals.
        if isinstance(addr, tuple):
            if not (len(addr) == 2 and isinstance(addr[0], str) and isinstance(addr[1], int)):
                raise TypeError(f"addr tuple must be (host: str, port: int), got {addr!r}")
        elif not isinstance(addr, (bytes, bytearray)):  # type: ignore[unreachable]  # mypy sees addr: tuple[str, int] and considers this branch unreachable; it's real at runtime for the reason above
            raise TypeError(f"addr must be a (host: str, port: int) tuple or a pre-resolved sockaddr, got {addr!r}")
        if not isinstance(conn_tries, int):
            raise TypeError(f"conn_tries must be an int, got {conn_tries!r}")

        self._addr = addr
        self.sock: socket.socket | None = None
        self.poller: select.poll | None = None
        self._mode = mode
        self.connected = False
        self._conn_tries = conn_tries
        self._connect_lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyUDPSocket":
        return self

    async def __aexit__(
        self,
        exc_type: "type[BaseException] | None",
        exc_val: "BaseException | None",
        exc_tb: "TracebackType | None",
    ) -> bool:
        await self.disconnect()
        return False

    async def _connect(self) -> None:
        # Lazy, one-shot-per-socket setup, serialized against both concurrent _connect() callers
        # and disconnect() via self._connect_lock (see module docstring) - self-heals via
        # _disconnect_locked() below on any failure (setup itself, e.g. resource exhaustion, or
        # every conn_tries attempt exhausted) so the next call gets a fresh attempt instead of a
        # permanently no-op _connect() or an uncaught exception, matching this file's own "never
        # raises" contract. MemoryError/TypeError are caught alongside OSError throughout this
        # method (see module docstring) - mode is guaranteed to already be "client" or "server" by
        # __init__'s validation, so the retry loop only needs the two real branches.
        async with self._connect_lock:
            if self.sock is None:
                try:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.sock.setblocking(False)
                    self.poller = select.poll()
                    self.poller.register(self.sock, select.POLLIN | select.POLLOUT)

                    tries = 0
                    while (not self.connected) and (tries < self._conn_tries):
                        try:
                            if self._mode == "client":
                                self.sock.connect(self._addr)
                            else:
                                self.sock.bind(self._addr)
                            self.connected = True
                        except (OSError, MemoryError, TypeError):
                            tries += 1
                            await asyncio.sleep(_RETRY_BACKOFF_S)
                            self.connected = False
                except (OSError, MemoryError, TypeError):
                    # socket()/setsockopt()/poll()/register() itself failed (OSError/MemoryError),
                    # or `tries < self._conn_tries` itself raised (TypeError - confirmed directly:
                    # the while loop's own condition is inside this try, not the inner one, so a
                    # non-int self._conn_tries raises here, not inside the per-attempt try below) -
                    # same backoff either way, so a persistent failure can't busy-loop.
                    await asyncio.sleep(_RETRY_BACKOFF_S)

                if not self.connected:
                    await self._disconnect_locked()

    async def ready(self, mask: int, timeout_ms: int = -1, wait_time_ms: int = 20) -> bool:
        # Connects lazily, then busy-polls ipoll(0) (allocation-free, non-blocking) and yields via
        # asyncio.sleep_ms(wait_time_ms) each cycle until mask (or a real POLLERR/POLLHUP - always
        # reported regardless of the registered mask, per POSIX poll() semantics) is satisfied, or
        # timeout_ms elapses (timeout_ms<=0 waits forever - matches captive_dns.py's persistent
        # recvfrom()). Returning True on an error condition lets the caller's real socket call run
        # and surface (and correctly convert) the actual OSError, instead of waiting out the full
        # timeout for an error that already happened - confirmed directly: a connected UDP socket
        # with a pending ICMP port-unreachable reports POLLERR without ever setting POLLIN.
        #
        # wait_time_ms defaults to 20, not 0: confirmed directly that 0 busy-polls ipoll(0)+
        # sleep_ms(0) ~9000x/sec while idle (~180x the rate at 20ms) - pure CPU churn on RP2040's
        # single core competing with other cooperative tasks (e.g. Neopixel timing) whenever a
        # caller waits a long time for a reply, which neither real caller overrides today (
        # captive_dns.py's persistent recvfrom() waits forever for the next query; async_connect.py's
        # NTP request waits out its full timeout on every dropped/lost packet).
        await self._connect()
        if not self.connected or self.poller is None:
            return False
        t0 = time.ticks_ms()
        while True:
            if self.poller is None:  # a concurrent disconnect() on this same instance can null
                return False  # type: ignore[unreachable]  # this mid-loop - confirmed directly (AttributeError otherwise); mypy's static narrowing can't see the mutation
            try:
                res = self.poller.ipoll(0)
                for _, event in res:
                    if event & (mask | select.POLLERR | select.POLLHUP):
                        return True
                if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                    return False
                await asyncio.sleep_ms(wait_time_ms)
            except (OSError, MemoryError, TypeError):
                # TypeError: a malformed mask/timeout_ms/wait_time_ms argument (confirmed directly -
                # e.g. timeout_ms=None raises from `timeout_ms > 0`, wait_time_ms=None raises from
                # inside asyncio.sleep_ms() itself, mask=None raises from `mask | select.POLLERR`) -
                # none of these are caught by sendto()/write()/recvfrom()'s own except clauses, since
                # those only wrap the real socket call, not this await self.ready(...) call itself.
                # OSError/MemoryError caught here too for the same defense-in-depth reason as
                # elsewhere in this file, even though empirical testing against this project's
                # MicroPython Unix-port build found no case where ipoll() itself actually raises.
                return False

    async def sendto(
        self,
        msg: bytes | bytearray,
        addr: tuple[str, int],
        timeout_ms: int = -1,
    ) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self.sock is not None:
            try:
                return self.sock.sendto(msg, addr)
            except (OSError, MemoryError, TypeError):  # TypeError: a malformed addr/msg (confirmed directly), not just this instance's own _addr
                pass
        return None

    async def write(self, msg: bytes | bytearray, timeout_ms: int = -1) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self.sock is not None:
            try:
                return self.sock.write(msg)
            except (OSError, MemoryError, TypeError):  # TypeError: a malformed msg, matching sendto()'s reasoning
                pass
        return None

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms) and self.sock is not None:
            try:
                return self.sock.recvfrom(buf)
            except (OSError, MemoryError, TypeError):  # TypeError: a malformed buf (confirmed directly, e.g. a str)
                pass
        return None, None

    async def write_and_recvfrom(
        self,
        msg: bytes | bytearray,
        buf: int,
        timeout_ms: int = -1,
        tries: int = 1,
    ) -> tuple[bytes | None, tuple[str, int] | None]:
        # Retries the full write+response round trip up to `tries` times, returning as soon as a
        # response arrives (used by async_connect.py's one-shot NTP request/response exchange).
        # range(tries) itself is guarded: a malformed tries (e.g. None or a str) raises TypeError
        # from range() before the loop ever starts - confirmed directly, and not caught by write()/
        # recvfrom()'s own except clauses since it never reaches either of them.
        try:
            tries_range = range(tries)
        except TypeError:
            return None, None
        for _ in tries_range:
            await self.write(msg, timeout_ms=timeout_ms)
            data, addr = await self.recvfrom(buf, timeout_ms=timeout_ms)
            if data is not None:
                return data, addr
        return None, None

    async def disconnect(self) -> None:
        # Serialized against _connect() via the same self._connect_lock (see module docstring) -
        # confirmed directly: without this, a disconnect() concurrent with another coroutine's
        # in-flight _connect() retry could null self.sock/self.poller out from under it, crashing
        # that retry with an uncaught AttributeError on its next connect()/bind() call.
        async with self._connect_lock:
            await self._disconnect_locked()

    async def _disconnect_locked(self) -> None:
        # The actual teardown, assuming self._connect_lock is already held - split out so
        # _connect()'s own self-heal path can call this directly instead of through disconnect()
        # (which would deadlock re-acquiring the same non-reentrant lock). Eagerly clears this
        # object's own state before attempting the actual teardown calls, so a failure partway
        # through can no longer leave it stuck in a broken half-connected state forever -
        # confirmed directly: a raising unregister() used to leave self.sock/self.poller/
        # self.connected exactly as they were, permanently, since the exception aborted the rest
        # of this method before sock.close()/self.sock = None ever ran.
        if self.sock is not None:
            sock, poller = self.sock, self.poller
            self.sock = None
            self.poller = None
            self.connected = False
            try:
                if poller is not None:
                    poller.unregister(sock)
            except (OSError, MemoryError):
                pass
            try:
                sock.close()
            except (OSError, MemoryError):
                pass
