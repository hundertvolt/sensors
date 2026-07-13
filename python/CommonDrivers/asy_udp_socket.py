import time
import asyncio
import select
import socket

class AsyUDPSocket:
    def __init__(self, addr, mode="client", conn_tries=1):
        self.addr = addr
        self.sock = None
        self.poller = None
        self.mode = mode
        self.connected = False
        self.conn_tries = conn_tries

    async def _connect(self):
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
                        self.connected = False
                except Exception as e:
                    tries += 1
                    await asyncio.sleep(0.5)

    async def ready(self, mask, timeout_ms=-1, wait_time_ms=0):
        await self._connect()
        if not self.connected:
            return False
        t0 = time.ticks_ms()
        while True:
            res = self.poller.ipoll(0)
            for sock, event in res:
                if (event & mask):
                    return True
            if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                return False
            await asyncio.sleep(wait_time_ms)

    async def sendto(self, msg, addr, timeout_ms=-1):
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms):
            return self.sock.sendto(msg, addr)
        return None
    
    async def write(self, msg, timeout_ms=-1):
        if await self.ready(select.POLLOUT, timeout_ms=timeout_ms):
            return self.sock.write(msg)
        return None

    async def recvfrom(self, buf, timeout_ms=-1):
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return self.sock.recvfrom(buf)
        return None, None

    async def write_and_recvfrom(self, msg, buf, timeout_ms=-1, tries=1):
        for _ in range(tries):
            await self.write(msg, timeout_ms=timeout_ms)
            return await self.recvfrom(buf, timeout_ms=timeout_ms)
        return None, None

    async def disconnect(self):
        if not (self.sock is None):
            self.poller.unregister(self.sock)
            self.sock.close()
            self.connected = False
            self.sock = None
