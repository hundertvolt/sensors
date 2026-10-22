"""Twin-side fix for the Unix port's sockaddr quirks (micropython#6924: bind/connect/sendto take a packed sockaddr,
recvfrom returns one), so src/ only ever sees (host, port) tuples; it also refuses any UDP destination outside loopback
and TEST-NET-1, and binds a server's wildcard on the loopback.

Applied once, before any UDPSocket exists (digital_twin/README.md "_unix_port_udp_addr_shim.py")."""

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

_real_connect = asy_udp_socket.UDPSocket._connect
_real_recvfrom = asy_udp_socket.UDPSocket.recvfrom
_real_sendto = asy_udp_socket.UDPSocket.sendto
_patched = False

_ALLOWED_PREFIXES = ("127.", "192.0.2.")  # loopback and RFC 5737 TEST-NET-1
_ALLOWED_HOSTS = ("0.0.0.0",)  # the wildcard a server binds
# Every twin interface lives on the host loopback, so a server's wildcard is bound there: the host's wildcard would also
# claim its other interfaces, and fails beside any resolver holding one loopback address without SO_REUSEADDR.
_WILDCARD = "0.0.0.0"
_TWIN_HOST = "127.0.0.1"
# A 4-byte AF_INET sockaddr: the host kernel's connect()/bind()/sendto() reject it with EINVAL inside src/'s own try,
# so a refusal takes the product's handled failure path (backoff included) and nothing leaves the host
_REFUSED_SOCKADDR = struct.pack("<H", socket.AF_INET) + bytes(2)
# the project's counter cap (SPECIFICATION.md G.2), a local copy: this directory imports nothing from digital_twin/
_COUNTER_CAP = 0x3FFFFFFF
public_destinations_refused = 0  # twin-only test knob: refusals, saturating at _COUNTER_CAP
last_refused: "tuple[str, int] | None" = None  # twin-only test knob: the destination of the latest refusal
TEST_API = ("public_destinations_refused", "last_refused")


def _count(addr: "tuple[str, int] | None") -> None:
    global public_destinations_refused, last_refused
    if public_destinations_refused < _COUNTER_CAP:
        public_destinations_refused += 1
    if addr is not None:
        last_refused = addr


def _ipv4_literal(host: str) -> bool:
    # Four dot-separated decimal parts, each at most 255: what getaddrinfo() resolves without a lookup.
    parts = host.split(".")
    return len(parts) == 4 and all(part.isdigit() and int(part) <= 255 for part in parts)


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


async def _patched_connect(self: "asy_udp_socket.UDPSocket") -> None:
    # Each attempt at a refused destination counts; the first swaps in the refused sockaddr. An allowed destination is
    # an IPv4 literal, so this getaddrinfo() is local, never a DNS query, and runs once (a sockaddr is kept).
    addr: object = self._addr  # the refused sockaddr once swapped in: bytes, which the product's annotation does not name
    if addr == _REFUSED_SOCKADDR:
        _count(None)
    elif _refused(self._addr):
        _count(self._addr)
        self._addr = cast("tuple[str, int]", _REFUSED_SOCKADDR)
    else:
        if self._mode == "server" and self._addr[0] == _WILDCARD:
            self._addr = (_TWIN_HOST, self._addr[1])
        self._addr = _resolve_plain_addr(self._addr)
    await _real_connect(self)


async def _patched_recvfrom(self: "asy_udp_socket.UDPSocket", buf: int, timeout_ms: int = -1) -> "tuple[bytes | None, tuple[str, int] | None]":
    data, addr = await _real_recvfrom(self, buf, timeout_ms=timeout_ms)
    return data, _normalize_recvfrom_addr(addr)


async def _patched_sendto(self: "asy_udp_socket.UDPSocket", msg: "bytes | bytearray", addr: "tuple[str, int]", timeout_ms: int = -1) -> "int | None":
    if _refused(addr):
        _count(addr)
        return await _real_sendto(self, msg, cast("tuple[str, int]", _REFUSED_SOCKADDR), timeout_ms=timeout_ms)
    return await _real_sendto(self, msg, _resolve_plain_addr(addr), timeout_ms=timeout_ms)


def _refused(addr: object) -> bool:
    # A (host, port) tuple whose host is no IPv4 literal on loopback or TEST-NET-1, a name included (refused before any
    # lookup); any other shape passes on to src/, whose own try handles it.
    if not (isinstance(addr, tuple) and len(addr) == 2 and isinstance(addr[0], str) and isinstance(addr[1], int)):
        return False
    host = addr[0]
    return not (_ipv4_literal(host) and (host.startswith(_ALLOWED_PREFIXES) or host in _ALLOWED_HOSTS))


def _resolve_plain_addr(addr: "T") -> "T | tuple[str, int]":
    if isinstance(addr, tuple) and len(addr) == 2 and isinstance(addr[0], str):
        # getaddrinfo()'s sockaddr slot here is the opaque bytes object this Unix build's socket
        # needs; src/ only ever sees tuples (IPv4-only project).
        return cast("tuple[str, int]", socket.getaddrinfo(addr[0], addr[1])[0][-1])
    return addr


def patch_asy_udp_socket_for_unix_port() -> None:
    global _patched
    if _patched:
        return
    asy_udp_socket.UDPSocket._connect = _patched_connect  # type: ignore[method-assign]
    asy_udp_socket.UDPSocket.sendto = _patched_sendto  # type: ignore[method-assign]
    asy_udp_socket.UDPSocket.recvfrom = _patched_recvfrom  # type: ignore[method-assign]
    _patched = True
