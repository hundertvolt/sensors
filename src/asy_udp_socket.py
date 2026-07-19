"""Async, non-blocking UDP wrapper around one MicroPython socket.socket - cooperative
send/receive driven by a hand-rolled select.poll loop (MicroPython's asyncio has no built-in
UDP-readiness primitive; open_connection()/start_server() are TCP-only). Two callers, two modes:
async_connect.py's NTP client (mode="client", one-shot object per sync attempt, connect() then
write_and_recvfrom()) and captive_dns.py's DNSServer (mode="server", one long-lived object,
bind() then a persistent recvfrom()/sendto() loop). Also usable as `async with AsyUDPSocket(...)
as sock:`, matching async_connect.py's actual acquire/use/release-in-finally usage.

Shared contract: every public method returns its documented None-shaped sentinel on any socket
failure (OSError) - never raises. Unlike the I2C/SPI bus-driver carve-out in src/README.md, no
raw OSError is ever allowed to propagate here: network faults (unreachable host, a transient
route/DNS failure) are expected, recoverable conditions, not hardware bugs to surface upward.

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
        self.addr = addr
        self.sock: socket.socket | None = None
        self.poller: select.poll | None = None
        self.mode = mode
        self.connected = False
        self.conn_tries = conn_tries

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
        # Lazy, one-shot-per-socket setup. Self-heals via disconnect() below on any failure -
        # setup itself (e.g. resource exhaustion) or every conn_tries attempt exhausted - so the
        # next call gets a fresh attempt instead of a permanently no-op _connect() or an uncaught
        # exception, matching this file's own "never raises" contract.
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.setblocking(False)
                self.poller = select.poll()
                self.poller.register(self.sock, select.POLLIN | select.POLLOUT)

                tries = 0
                while (not self.connected) and (tries < self.conn_tries):
                    try:
                        if self.mode == "client":
                            self.sock.connect(self.addr)
                            self.connected = True
                        elif self.mode == "server":
                            self.sock.bind(self.addr)
                            self.connected = True
                        else:
                            self.connected = False  # type: ignore[unreachable]
                    except OSError:
                        tries += 1
                        await asyncio.sleep(_RETRY_BACKOFF_S)
                        self.connected = False
            except OSError:
                # socket()/setsockopt()/poll()/register() itself failed - same backoff as a
                # connect/bind failure, so a persistent failure (e.g. resource exhaustion) can't
                # busy-loop either.
                await asyncio.sleep(_RETRY_BACKOFF_S)

            if not self.connected:
                await self.disconnect()

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
            res = self.poller.ipoll(0)
            for _, event in res:
                if event & (mask | select.POLLERR | select.POLLHUP):
                    return True
            if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                return False
            await asyncio.sleep_ms(wait_time_ms)

    async def sendto(
        self,
        msg: bytes | bytearray,
        addr: tuple[str, int],
        timeout_ms: int = -1,
    ) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self.sock is not None:
            try:
                return self.sock.sendto(msg, addr)
            except OSError:
                pass
        return None

    async def write(self, msg: bytes | bytearray, timeout_ms: int = -1) -> int | None:
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms) and self.sock is not None:
            try:
                return self.sock.write(msg)
            except OSError:
                pass
        return None

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms) and self.sock is not None:
            try:
                return self.sock.recvfrom(buf)
            except OSError:
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
        for _ in range(tries):
            await self.write(msg, timeout_ms=timeout_ms)
            data, addr = await self.recvfrom(buf, timeout_ms=timeout_ms)
            if data is not None:
                return data, addr
        return None, None

    async def disconnect(self) -> None:
        if self.sock is not None:
            try:
                if self.poller is not None:
                    self.poller.unregister(self.sock)
                    self.poller = None
                self.sock.close()
                self.connected = False
                self.sock = None
            except OSError:
                pass
