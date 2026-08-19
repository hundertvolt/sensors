"""Async, non-blocking UDP wrapper around one socket.socket, driven by a hand-rolled select.poll
loop. Two modes: mode="client" for a one-shot outbound request/response exchange, mode="server" for
a bound socket answering inbound datagrams; also usable as `async with AsyUDPSocket(...) as sock:`.
Every I/O method returns its documented None-shaped sentinel, never raises (__init__ excepted).
Content-agnostic: never inspects datagram contents; mode="server" source-address trust is the
caller's concern.
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
        # Fail fast, at construction - see module docstring's __init__ exception.
        if mode not in ("client", "server"):
            raise ValueError(f"mode must be 'client' or 'server', got {mode!r}")
        # addr may also be a pre-resolved opaque sockaddr (bytes/bytearray), not just a tuple -
        # this file passes it through untouched to connect()/bind()/sendto().
        if isinstance(addr, tuple):
            if not (len(addr) == 2 and isinstance(addr[0], str) and isinstance(addr[1], int)):
                raise TypeError(f"addr tuple must be (host: str, port: int), got {addr!r}")
        elif not isinstance(addr, (bytes, bytearray)):  # type: ignore[unreachable]  # real at runtime
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
        # Lazy, one-shot-per-socket setup, serialized against disconnect() via self._connect_lock.
        # Self-heals via _disconnect_locked() on any failure so the next call gets a fresh attempt.
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
                    # setup itself failed, or a non-int conn_tries raised from the while condition.
                    await asyncio.sleep(_RETRY_BACKOFF_S)

                if not self.connected:
                    await self._disconnect_locked()

    async def _disconnect_locked(self) -> bool:
        # Actual teardown, assuming self._connect_lock is already held - split out so _connect()'s
        # self-heal path can call this directly without deadlocking on the same non-reentrant lock.
        # State is cleared eagerly so a failure partway through can't leave it half-connected.
        if self.sock is None:
            return True
        sock, poller = self.sock, self.poller
        self.sock = None
        self.poller = None
        self.connected = False
        ok = True
        try:
            if poller is not None:
                poller.unregister(sock)
        except (OSError, MemoryError):
            ok = False
        try:
            sock.close()
        except (OSError, MemoryError):
            ok = False
        return ok

    async def ready(self, mask: int, timeout_ms: int = -1, wait_time_ms: int = 20) -> bool:
        # Busy-polls ipoll(0), yielding via sleep_ms(wait_time_ms) each cycle, until mask (or a
        # real POLLERR/POLLHUP, always reported) is satisfied or timeout_ms elapses (<=0 waits
        # forever). Returning True on an error lets the caller's real socket call surface it.
        await self._connect()
        if not self.connected or self.poller is None:
            return False
        t0 = time.ticks_ms()
        while True:
            if self.poller is None:  # a concurrent disconnect() can null this mid-loop
                return False  # type: ignore[unreachable]  # mypy can't see the mutation
            try:
                res = self.poller.ipoll(0)
                for _, event in res:
                    if event & (mask | select.POLLERR | select.POLLHUP):
                        return True
                if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                    return False
                await asyncio.sleep_ms(wait_time_ms)
            except (OSError, MemoryError, TypeError):
                # TypeError: a malformed mask/timeout_ms/wait_time_ms - not caught by callers' own
                # except clauses, since those only wrap the real socket call, not this await.
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
            except (OSError, MemoryError, TypeError):  # TypeError: a malformed addr/msg, not just this instance's own _addr
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
            except (OSError, MemoryError, TypeError):  # TypeError: a malformed buf (e.g. a str)
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

    async def disconnect(self) -> bool:
        # Serialized against _connect() via the same self._connect_lock - without this, a
        # disconnect() concurrent with an in-flight _connect() retry could crash it.
        # Returns True if teardown completed cleanly, False if unregister()/close() raised (state
        # is still always cleared either way - see _disconnect_locked()). This class deliberately
        # has no logger of its own (every I/O method is a plain sentinel-return, never-raises
        # primitive - see module docstring), so a caller that wants to log a failed teardown reads
        # this return value with its own logger, the same way it already does for every other
        # method here - never a silent bare `pass` with no signal at all (Step 6 finding).
        async with self._connect_lock:
            return await self._disconnect_locked()
