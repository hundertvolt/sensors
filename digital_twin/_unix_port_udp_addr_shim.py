"""Workaround for three confirmed MicroPython-Unix-port-only `socket` quirks that would otherwise break a real UDP round trip (DNS, NTP) here - entirely from twin-side code, `src/` untouched and correct for real hardware.
Full account: digital_twin/README.md's "`_unix_port_udp_addr_shim.py`" section.
Call `patch_asy_udp_socket_for_unix_port()` once, early, before constructing any `AsyUDPSocket`."""

import socket
import struct

import asy_udp_socket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_real_connect = asy_udp_socket.AsyUDPSocket._connect
_real_recvfrom = asy_udp_socket.AsyUDPSocket.recvfrom
_real_sendto = asy_udp_socket.AsyUDPSocket.sendto
_patched = False


def _resolve_plain_addr(addr: "Any") -> "Any":
    if isinstance(addr, tuple) and len(addr) == 2 and isinstance(addr[0], str):
        return socket.getaddrinfo(addr[0], addr[1])[0][-1]
    return addr


async def _patched_connect(self: "asy_udp_socket.AsyUDPSocket") -> None:
    # Every real call site (captive_dns.py's "0.0.0.0", asy_ntp_client.py's already-DNS-resolved
    # NTP server IP - see this module's own docstring) already hands over a plain, already-numeric
    # (host: str, port: int) tuple, so this is always a fast, local, no-network-lookup
    # getaddrinfo() call - never a real DNS query. Only resolves once: after the first successful
    # resolution self._addr becomes the real sockaddr bytes object, which isn't a tuple, so
    # _resolve_plain_addr()'s own isinstance(addr, tuple) check naturally skips re-resolving on
    # every later reconnect attempt.
    self._addr = _resolve_plain_addr(self._addr)
    await _real_connect(self)


async def _patched_sendto(self: "asy_udp_socket.AsyUDPSocket", msg: "Any", addr: "Any", timeout_ms: int = -1) -> "int | None":
    return await _real_sendto(self, msg, _resolve_plain_addr(addr), timeout_ms=timeout_ms)


def _normalize_recvfrom_addr(addr: "Any") -> "Any":
    # Only the raw 16-byte AF_INET struct this build's recvfrom() actually returns is normalized -
    # anything else (None from a failed recv, an already-(str, int) tuple, IPv6) passes through
    # unchanged. struct's own "<H" + ">H" split (native family field, network-order port field)
    # can't be expressed as one format string (struct forbids mixing byte-order prefixes mid-string),
    # so the two are unpacked separately below instead.
    if isinstance(addr, (bytes, bytearray)) and len(addr) >= 8:
        family = struct.unpack("<H", addr[0:2])[0]
        if family == socket.AF_INET:
            port = struct.unpack(">H", addr[2:4])[0]
            ip_str = ".".join(str(b) for b in addr[4:8])
            return (ip_str, port)
    return addr


async def _patched_recvfrom(self: "asy_udp_socket.AsyUDPSocket", buf: int, timeout_ms: int = -1) -> "tuple[Any, Any]":
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
