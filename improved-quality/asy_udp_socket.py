import time
import asyncio
import select
import socket
from typing import Literal, Tuple


class AsyUDPSocket:
    def __init__(
        self,
        addr: Tuple[str, int],
        mode: Literal["client", "server"] = "client",
        conn_tries: int = 1,
    ) -> None:
        self.addr = addr
        self.sock: socket.socket | None = None
        self.poller: select.poll | None = None
        self.mode = mode
        self.connected = False
        self.conn_tries = conn_tries

    async def _connect(self) -> None:
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
                except Exception:
                    tries += 1
                    await asyncio.sleep(0.5)
                    self.connected = False

    async def ready(self, mask: int, timeout_ms: int = -1, wait_time_ms: int = 0) -> bool:
        await self._connect()
        if not self.connected or self.poller is None:
            return False
        t0 = time.ticks_ms()
        while True:
            res = self.poller.ipoll(0)
            for sock, event in res:
                if event & mask:
                    return True
            if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                return False
            await asyncio.sleep(wait_time_ms)

    async def sendto(
        self,
        msg: bytes | bytearray,
        addr: Tuple[str, int],
        timeout_ms: int = -1,
    ) -> None:
        if self.sock is None:
            return None
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms):
            try:
                return self.sock.sendto(msg, addr)
            except Exception:
                pass
        return None

    async def write(self, msg: bytes | bytearray, timeout_ms: int = -1) -> int | None:
        if self.sock is None:
            return None
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms):
            try:
                return self.sock.write(msg)
            except Exception:
                pass
        return None

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> Tuple[bytes | None, Tuple[str, int] | None]:
        if self.sock is None:
            return None, None
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            try:
                return self.sock.recvfrom(buf)
            except Exception:
                pass
        return None, None

    async def write_and_recvfrom(
        self,
        msg: bytes | bytearray,
        buf: int,
        timeout_ms: int = -1,
        tries: int = 1,
    ) -> Tuple[bytes | None, Tuple[str, int] | None]:
        for _ in range(tries):
            await self.write(msg, timeout_ms=timeout_ms)
            return await self.recvfrom(buf, timeout_ms=timeout_ms)
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
            except Exception:
                pass
