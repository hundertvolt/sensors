# Attribution, no formal SPDX identifier: this class's shape is close to karfas's AsyUDPClient
# (github.com/karfas/upy-simple-app), offered publicly by its author for exactly this reuse.
# THIRD_PARTY_LICENSES.md carries the full account and what was changed or added here.

"""Async, non-blocking UDP wrapper around one socket.socket, driven by a hand-rolled select.poll
loop. Two modes: mode="client" for a one-shot outbound request/response exchange, mode="server" for a bound socket answering inbound datagrams; also usable as `async with UDPSocket(...) as sock:`.
"""
# Every I/O method returns its documented None-shaped sentinel, never raises (__init__ excepted).
# Content-agnostic: never inspects datagram contents; mode="server" source-address trust is the
# caller's concern.

import asyncio
import select
import socket

from micropython import const

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal

    from typing_extensions import Self

_ADDR_TUPLE_LEN = const(2)  # a plain (host, port) address tuple
# @tunable udp.retry_backoff_s = 0.5
_RETRY_BACKOFF_S = const(0.5)  # pause between a failed connect()/bind() (or setup) attempt and the next


class UDPSocket:
    def __init__(
        self,
        addr: tuple[str, int],
        mode: 'Literal["client", "server"]' = "client",
        # @tunable udp.conn_tries_default = 1
        conn_tries: int = 1,
    ) -> None:
        # Fail fast, at construction - see module docstring's __init__ exception.
        if mode not in ("client", "server"):
            raise ValueError(f"mode must be 'client' or 'server', got {mode!r}")
        # addr may also be a pre-resolved opaque sockaddr (bytes/bytearray), not just a tuple -
        # this file passes it through untouched to connect()/bind()/sendto().
        if isinstance(addr, tuple):
            if not (len(addr) == _ADDR_TUPLE_LEN and isinstance(addr[0], str) and isinstance(addr[1], int)):
                raise TypeError(f"addr tuple must be (host: str, port: int), got {addr!r}")
        elif not isinstance(addr, (bytes, bytearray)):  # type: ignore[unreachable]  # real at runtime
            raise TypeError(f"addr must be a (host: str, port: int) tuple or a pre-resolved sockaddr, got {addr!r}")
        if not isinstance(conn_tries, int):
            raise TypeError(f"conn_tries must be an int, got {conn_tries!r}")

        self._addr = addr
        self._sock: socket.socket | None = None
        self.poller: select.poll | None = None
        self._mode = mode
        self.connected = False
        self._conn_tries = conn_tries
        self._connect_lock = asyncio.Lock()  # serialises setup and teardown of the one socket object

    async def __aenter__(self) -> "Self":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,  # `object`, not TracebackType: the precise name only exists under TYPE_CHECKING
    ) -> "Literal[False]":
        await self.disconnect()
        return False

    async def _connect(self) -> None:
        # Lazy, one-shot-per-socket setup, serialized against disconnect() via self._connect_lock.
        # Self-heals via _disconnect_locked() on any failure so the next call gets a fresh attempt.
        async with self._connect_lock:
            if self._sock is None:
                try:
                    self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._sock.setblocking(False)
                    self.poller = select.poll()
                    self.poller.register(self._sock, select.POLLIN | select.POLLOUT)

                    tries = 0
                    while (not self.connected) and (tries < self._conn_tries):
                        try:
                            if self._mode == "client":
                                self._sock.connect(self._addr)
                            else:
                                self._sock.bind(self._addr)
                            self.connected = True
                        except (MemoryError, OSError, TypeError):
                            tries += 1
                            await asyncio.sleep(_RETRY_BACKOFF_S)
                            self.connected = False
                except (MemoryError, OSError, TypeError):
                    # setup itself failed, or a non-int conn_tries raised from the while condition.
                    await asyncio.sleep(_RETRY_BACKOFF_S)

                if not self.connected:
                    await self._disconnect_locked()

    async def _disconnect_locked(self) -> bool:
        # Actual teardown, assuming self._connect_lock is already held - split out so _connect()'s
        # self-heal path can call this directly without deadlocking on the same non-reentrant lock.
        # State is cleared eagerly so a failure partway through can't leave it half-connected.
        if self._sock is None:
            return True
        sock, poller = self._sock, self.poller
        self._sock = None
        self.poller = None
        self.connected = False
        ok = True
        try:
            if poller is not None:
                poller.unregister(sock)
        except (MemoryError, OSError):
            ok = False
        try:
            sock.close()
        except (MemoryError, OSError):
            ok = False
        return ok

    async def _poll(self, mask: int, wait_time_ms: int) -> bool:
        # ipoll(0), then sleep_ms(wait_time_ms), until mask (or a real POLLERR/POLLHUP) is set; no
        # deadline of its own - ready() bounds it with asyncio.wait_for_ms() (SPECIFICATION.md F.2).
        while True:
            if self.poller is None:  # a concurrent disconnect() can null this mid-loop
                return False
            for _, event in self.poller.ipoll(0):
                if event & (mask | select.POLLERR | select.POLLHUP):
                    return True
            await asyncio.sleep_ms(wait_time_ms)

    async def disconnect(self) -> bool:
        # Serialized against _connect() through the same lock - a concurrent disconnect() could
        # otherwise crash an in-flight retry. Returns False if teardown raised (state is cleared
        # either way): this class owns no logger, so the caller logs it (Part C.7's bool rule).
        async with self._connect_lock:
            return await self._disconnect_locked()

    # @tunable udp.ready_poll_ms = 20
    async def ready(self, mask: int, timeout_ms: int = -1, wait_time_ms: int = 20) -> bool:
        # Polls until mask (or a real POLLERR/POLLHUP, always reported: the caller's socket call surfaces it)
        # is set; timeout_ms > 0 bounds the wait through wait_for_ms(), <= 0 waits forever. A malformed mask,
        # timeout_ms or wait_time_ms returns False: callers' excepts wrap only their own socket call.
        await self._connect()
        if not self.connected or self.poller is None:
            return False
        try:
            if timeout_ms <= 0:
                return await self._poll(mask, wait_time_ms)
            return await asyncio.wait_for_ms(self._poll(mask, wait_time_ms), timeout_ms)
        except asyncio.TimeoutError:
            return False
        except (MemoryError, OSError, TypeError):
            return False

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms) and self._sock is not None:
            try:
                # The 1.29 stub types recvfrom()'s address as socket's full _Address union
                # (AF_INET6's 4-tuple and AF_UNIX's str included). This socket is always
                # AF_INET/SOCK_DGRAM (see _open()), so the 2-tuple is the only reachable shape.
                return self._sock.recvfrom(buf)  # type: ignore[return-value]
            except (MemoryError, OSError, TypeError):  # TypeError: a malformed buf (e.g. a str)
                pass
        return None, None

    async def sendto(
        self,
        msg: bytes | bytearray,
        addr: tuple[str, int],
        timeout_ms: int = -1,
    ) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self._sock is not None:
            try:
                return self._sock.sendto(msg, addr)
            except (MemoryError, OSError, TypeError):  # TypeError: a malformed addr/msg, not just this instance's own _addr
                pass
        return None

    async def write(self, msg: bytes | bytearray, timeout_ms: int = -1) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self._sock is not None:
            try:
                return self._sock.write(msg)
            except (MemoryError, OSError, TypeError):  # TypeError: a malformed msg, matching sendto()'s reasoning
                pass
        return None

    async def write_and_recvfrom(
        self,
        msg: bytes | bytearray,
        buf: int,
        timeout_ms: int = -1,
        # @tunable udp.round_trip_tries_default = 1
        tries: int = 1,
    ) -> tuple[bytes | None, tuple[str, int] | None]:
        # Retries the full write+response round trip up to `tries` times, returning as soon as a
        # response arrives. range(tries) is guarded: a malformed tries raises TypeError from
        # range() itself, before the loop starts and before write()/recvfrom() ever see it.
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
