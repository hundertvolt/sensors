# No formal license: the class's shape is close to karfas's AsyUDPClient (github.com/karfas/upy-simple-app),
# which its author posted as 'a starting point' in github.com/orgs/micropython/discussions/12967.
# THIRD_PARTY_LICENSES.md carries the full account and what was changed or added here.

"""Async, non-blocking UDP wrapper around one socket.socket, driven by a hand-rolled select.poll
loop. Two modes: mode="client" for a one-shot outbound request/response exchange,
mode="server" for a bound socket answering inbound datagrams.
"""
# Every I/O method returns its documented None-shaped sentinel, never raises (__init__ excepted).
# Content-agnostic: never inspects datagram contents; mode="server" source-address trust is the
# caller's concern.

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
    from typing import Literal

    from asy_print_log import PrintLog

_ADDR_TUPLE_LEN = const(2)  # a plain (host, port) address tuple
# @tunable udp.retry_backoff_ms = 500
_RETRY_BACKOFF_MS = const(500)  # pause after a failed socket setup, connect() or bind()
# @tunable udp.poll_wait_ms = 20
_POLL_WAIT_MS = const(20)  # a wait with a deadline: inside a DNS or NTP exchange
# @tunable udp.poll_idle_ms = 100
_POLL_IDLE_MS = const(100)  # a wait with no deadline: the captive DNS listen


class UDPSocket:
    def __init__(self, addr: tuple[str, int], mode: 'Literal["client", "server"]' = "client", logger: "PrintLog | None" = None) -> None:
        # Fail fast, at construction - see module docstring's __init__ exception. mode is mypy's Literal (D.2).
        if not (isinstance(addr, tuple) and len(addr) == _ADDR_TUPLE_LEN and isinstance(addr[0], str) and isinstance(addr[1], int)):
            raise TypeError(f"addr must be a (host: str, port: int) tuple, got {addr!r}")

        self._addr = addr
        self.logger = logger  # its builder's, not one of its own: a caught MemoryError prints through it; none, silent
        self._sock: socket.socket | None = None
        self.poller: select.poll | None = None
        self._mode = mode
        self.connected = False
        self._connect_lock = asyncio.Lock()  # serialises setup and teardown of the one socket object

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
                    if self._mode == "client":
                        self._sock.connect(self._addr)
                    else:
                        self._sock.bind(self._addr)
                    self.connected = True
                except (MemoryError, OSError, TypeError) as e:
                    self._nomem(e)
                    # setup, connect or bind failed
                    await asyncio.sleep_ms(_RETRY_BACKOFF_MS)

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
        except (MemoryError, OSError) as e:
            self._nomem(e)
            ok = False
        try:
            sock.close()
        except (MemoryError, OSError) as e:
            self._nomem(e)
            ok = False
        return ok

    def _nomem(self, e: BaseException) -> None:  # a caught MemoryError's line, through its builder's logger; none, silent
        if isinstance(e, MemoryError) and self.logger is not None:
            self.logger.err("UDPSocket:", e)

    async def disconnect(self) -> bool:
        # Serialized against _connect() through the same lock - a concurrent disconnect() could
        # otherwise crash an in-flight retry. Returns False if teardown raised (state is cleared
        # either way): this class owns no logger, so the caller logs it (Part C.7's bool rule).
        async with self._connect_lock:
            return await self._disconnect_locked()

    async def ready(self, mask: int, timeout_ms: int = -1) -> bool:
        # Polls ipoll(0) until mask or timeout_ms, sleeping _POLL_WAIT_MS with a deadline, _POLL_IDLE_MS with none (F.5.9's
        # shape). A real POLLERR/POLLHUP is always reported; returning True lets the caller's socket call surface it.
        await self._connect()
        if not self.connected or self.poller is None:
            return False
        wait_ms = _POLL_WAIT_MS if timeout_ms > 0 else _POLL_IDLE_MS
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
                await asyncio.sleep_ms(wait_ms)
            except (MemoryError, OSError) as e:
                self._nomem(e)
                return False

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms) and self._sock is not None:
            try:
                # A datagram longer than buf arrives cut to buf bytes, the rest dropped (extmod/modlwip.c:719-721, v1.29.0). The 1.29
                # stub types the address as socket's full _Address union; this AF_INET socket (_connect()) only returns a 2-tuple.
                # Remove the ignore once the stub narrows it (warn_unused_ignores then flags it).
                return self._sock.recvfrom(buf)  # type: ignore[return-value]
            except (MemoryError, OSError) as e:
                self._nomem(e)
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
            except (MemoryError, OSError, TypeError) as e:  # TypeError: an address form the port refuses (docs/library/socket.rst)
                self._nomem(e)
        return None

    async def write(self, msg: bytes | bytearray, timeout_ms: int = -1) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self._sock is not None:
            try:
                return self._sock.write(msg)
            except (MemoryError, OSError) as e:
                self._nomem(e)
        return None
