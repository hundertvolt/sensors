"""Workaround for three confirmed MicroPython-Unix-port-only `socket` quirks that would otherwise break a real UDP round trip (DNS, NTP) here - entirely from twin-side code, `src/` untouched and correct for real hardware.
Full account: digital_twin/README.md's "`_unix_port_udp_addr_shim.py`" section.
Call `patch_asy_udp_socket_for_unix_port()` once, early, before constructing any `AsyUDPSocket`."""

import socket
import struct

import asy_udp_socket

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val

if TYPE_CHECKING:
    from typing import TypeVar

    # Both helpers below pass their argument straight back through when they can't improve on it,
    # so each is typed "same type in, plus the normalized (host, port) tuple it may return instead".
    T = TypeVar("T")

_real_connect = asy_udp_socket.AsyUDPSocket._connect
_real_recvfrom = asy_udp_socket.AsyUDPSocket.recvfrom
_real_sendto = asy_udp_socket.AsyUDPSocket.sendto
_patched = False


def _resolve_plain_addr(addr: "T") -> "T | tuple[str, int]":
    if isinstance(addr, tuple) and len(addr) == 2 and isinstance(addr[0], str):
        # getaddrinfo()'s stub-declared sockaddr slot is (host, port) or IPv6's 4-tuple; this
        # project is IPv4-only (AsyUDPSocket's own addr type), and on this build it is in fact the
        # opaque sockaddr bytes object src/asy_udp_socket.py already documents accepting.
        return cast("tuple[str, int]", socket.getaddrinfo(addr[0], addr[1])[0][-1])
    return addr


async def _patched_connect(self: "asy_udp_socket.AsyUDPSocket") -> None:
    # Every real call site already hands over a numeric (host, port) tuple, so this getaddrinfo()
    # is always local and never a DNS query. It also resolves once: afterwards self._addr is a
    # sockaddr bytes object, which the isinstance check skips on every later reconnect.
    self._addr = _resolve_plain_addr(self._addr)
    await _real_connect(self)


async def _patched_sendto(self: "asy_udp_socket.AsyUDPSocket", msg: "bytes | bytearray", addr: "tuple[str, int]", timeout_ms: int = -1) -> "int | None":
    return await _real_sendto(self, msg, _resolve_plain_addr(addr), timeout_ms=timeout_ms)


def _normalize_recvfrom_addr(addr: "T") -> "T | tuple[str, int]":
    # Only the raw 16-byte AF_INET struct this build's recvfrom() returns is normalized;
    # everything else passes through. The native family field and network-order port field cannot
    # share one format string - struct forbids mixing byte-order prefixes - hence two unpacks.
    if isinstance(addr, (bytes, bytearray)) and len(addr) >= 8:
        family = struct.unpack("<H", addr[0:2])[0]
        if family == socket.AF_INET:
            port = struct.unpack(">H", addr[2:4])[0]
            ip_str = ".".join(str(b) for b in addr[4:8])
            return (ip_str, port)
    return addr


async def _patched_recvfrom(self: "asy_udp_socket.AsyUDPSocket", buf: int, timeout_ms: int = -1) -> "tuple[bytes | None, tuple[str, int] | None]":
    data, addr = await _real_recvfrom(self, buf, timeout_ms=timeout_ms)
    return data, _normalize_recvfrom_addr(addr)


def patch_asy_udp_socket_for_unix_port() -> None:
    global _patched
    if _patched:
        return
    asy_udp_socket.AsyUDPSocket._connect = _patched_connect  # type: ignore[method-assign]
    asy_udp_socket.AsyUDPSocket.sendto = _patched_sendto  # type: ignore[method-assign]
    asy_udp_socket.AsyUDPSocket.recvfrom = _patched_recvfrom  # type: ignore[method-assign]
    _patched = True
