import asyncio
import select
import socket
import sys
import time

sys.path.insert(0, "digital_twin")
import asy_print_log
import asy_udp_socket
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from asy_udp_socket import UDPSocket

patch_asy_udp_socket_for_unix_port()

_HOST = "127.0.0.1"
_next_port = 23000


def make_addr():
    global _next_port
    _next_port += 1
    return (_HOST, _next_port)


def run(coro):
    return asyncio.run(coro)


class _PrintRecorder:
    def __init__(self):
        self.lines = []
        asy_print_log.print = self

    def __call__(self, *args, **kwargs):
        self.lines.append(" ".join(str(a) for a in args))

    def restore(self):
        del asy_print_log.print


class _FailingSocketModule:
    AF_INET = socket.AF_INET
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOL_SOCKET = socket.SOL_SOCKET
    SO_REUSEADDR = socket.SO_REUSEADDR

    def __init__(self, exc):
        self._exc = exc

    def socket(self, _af, _sock_type):
        raise self._exc


class _FailingSocket:
    def __init__(self, real, method, exc):
        self._real = real
        self._method = method
        self._exc = exc

    def _call(self, name, *a):
        if name == self._method:
            raise self._exc
        return getattr(self._real, name)(*a)

    def sendto(self, *a):
        return self._call("sendto", *a)

    def write(self, *a):
        return self._call("write", *a)

    def recvfrom(self, *a):
        return self._call("recvfrom", *a)

    def close(self):
        return self._call("close")

    def __getattr__(self, name):
        return getattr(self._real, name)


class _FailingPoller:
    def __init__(self, real, method, exc):
        self._real = real
        self._method = method
        self._exc = exc

    def ipoll(self, *a):
        if self._method == "ipoll":
            raise self._exc
        return self._real.ipoll(*a)

    def register(self, *a):
        pass

    def unregister(self, *a):
        if self._method == "unregister":
            raise self._exc
        if self._real is not None:
            self._real.unregister(*a)


async def _arm_connect(exc):
    sock = UDPSocket(make_addr(), mode="server")
    original = asy_udp_socket.socket
    asy_udp_socket.socket = _FailingSocketModule(exc)
    try:
        t0 = time.ticks_ms()
        await sock._connect()
        elapsed = time.ticks_diff(time.ticks_ms(), t0)
    finally:
        asy_udp_socket.socket = original
    return (sock.connected, sock._sock is None, elapsed >= 450)


async def _arm_unregister(exc):
    sock = UDPSocket(make_addr(), mode="server")
    await sock._connect()
    sock.poller = _FailingPoller(sock.poller, "unregister", exc)
    ok = await sock.disconnect()
    return (ok, sock._sock is None, sock.connected)


async def _arm_close(exc):
    sock = UDPSocket(make_addr(), mode="server")
    await sock._connect()
    real = sock._sock
    sock._sock = _FailingSocket(real, "close", exc)
    ok = await sock.disconnect()
    real.close()
    return (ok, sock._sock is None, sock.connected)


async def _arm_ready(exc):
    sock = UDPSocket(make_addr(), mode="server")
    await sock._connect()
    real_poller = sock.poller
    sock.poller = _FailingPoller(None, "ipoll", exc)
    try:
        return await sock.ready(select.POLLIN, timeout_ms=50)
    finally:
        sock.poller = real_poller
        await sock.disconnect()


async def _arm_sendto(exc):
    addr = make_addr()
    sock = UDPSocket(addr, mode="server")
    await sock._connect()
    sock._sock = _FailingSocket(sock._sock, "sendto", exc)
    try:
        return await sock.sendto(b"x", addr)
    finally:
        await sock.disconnect()


async def _arm_write(exc):
    sock = UDPSocket(make_addr(), mode="client")
    await sock._connect()
    sock._sock = _FailingSocket(sock._sock, "write", exc)
    try:
        return await sock.write(b"x")
    finally:
        await sock.disconnect()


async def _arm_recvfrom(exc):
    addr = make_addr()
    sock = UDPSocket(addr, mode="server")
    await sock._connect()
    assert await sock.sendto(b"x", addr) == 1
    await asyncio.sleep(0.05)
    sock._sock = _FailingSocket(sock._sock, "recvfrom", exc)
    try:
        return await sock.recvfrom(64, timeout_ms=200)
    finally:
        await sock.disconnect()


_ARMS = (
    ("_connect", _arm_connect, (False, True, True)),
    ("unregister", _arm_unregister, (False, True, False)),
    ("close", _arm_close, (False, True, False)),
    ("ready", _arm_ready, False),
    ("sendto", _arm_sendto, None),
    ("write", _arm_write, None),
    ("recvfrom", _arm_recvfrom, (None, None)),
)


def test_an_allocation_failure_in_each_arm_prints_its_text_and_keeps_the_sentinel():
    wrong = []
    for arm, scenario, sentinel in _ARMS:
        rec = _PrintRecorder()
        try:
            got = run(scenario(MemoryError(f"injected for {arm}")))
        finally:
            rec.restore()
        if got != sentinel or rec.lines != [f"UDPSocket injected for {arm}"]:
            wrong.append((arm, got, rec.lines))
    assert not wrong, wrong


def test_an_os_error_in_each_arm_prints_nothing():
    for arm, scenario, sentinel in _ARMS:
        rec = _PrintRecorder()
        try:
            got = run(scenario(OSError(f"injected for {arm}")))
        finally:
            rec.restore()
        assert got == sentinel, (arm, got)
        assert rec.lines == [], (arm, rec.lines)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
