"""Async, non-blocking UDP wrapper around one MicroPython socket.socket - cooperative
send/receive driven by a hand-rolled select.poll loop (MicroPython's asyncio has no built-in
UDP-readiness primitive; open_connection()/start_server() are TCP-only). Two callers, two modes:
async_connect.py's NTP client (mode="client", one-shot object per sync attempt, connect() then
write_and_recvfrom()) and captive_dns.py's DNSServer (mode="server", one long-lived object,
bind() then a persistent recvfrom()/sendto() loop).

Shared contract: every public method returns its documented None-shaped sentinel on any socket
failure (OSError) - never raises. Unlike the I2C/SPI bus-driver carve-out in src/README.md, no
raw OSError is ever allowed to propagate here: network faults (unreachable host, a transient
route/DNS failure) are expected, recoverable conditions, not hardware bugs to surface upward.
"""

import asyncio
import select
import socket
import time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal


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

    async def _connect(self) -> None:
        # Lazy, one-shot-per-socket setup. Self-heals via disconnect() below if conn_tries is
        # exhausted, so the next call gets a fresh attempt instead of a permanently no-op _connect().
        if self.sock is None:
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
                    await asyncio.sleep(0.5)
                    self.connected = False

            if not self.connected:
                await self.disconnect()

    async def ready(self, mask: int, timeout_ms: int = -1, wait_time_ms: int = 0) -> bool:
        # Connects lazily, then busy-polls ipoll(0) (allocation-free, non-blocking) and yields via
        # asyncio.sleep(wait_time_ms) each cycle until mask is satisfied or timeout_ms elapses
        # (timeout_ms<=0 waits forever - matches captive_dns.py's persistent recvfrom()).
        await self._connect()
        if not self.connected or self.poller is None:
            return False
        t0 = time.ticks_ms()
        while True:
            res = self.poller.ipoll(0)
            for _, event in res:
                if event & mask:
                    return True
            if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                return False
            await asyncio.sleep(wait_time_ms)

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
