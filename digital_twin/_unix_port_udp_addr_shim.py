"""Workaround for three confirmed MicroPython-Unix-port-only `socket` quirks (BACKLOG.md's "Real-
hardware verification gap for asy_udp_socket.py/captive_dns.py" entry has the full source-level
account) - all three patched here, entirely from twin-side code, `src/` untouched and left correct
for real hardware:

1. `ports/unix/modsocket.c`'s `bind()`/`connect()` require a pre-resolved buffer-protocol sockaddr;
   the real rp2/lwIP socket module (`extmod/modlwip.c`) accepts a plain `(host: str, port: int)`
   tuple directly - the form `AsyUDPSocket` (correctly) always passes. Patches `_connect()` to
   pre-resolve via `socket.getaddrinfo()` first, same pattern `unix_port_poll_prewarm.py`'s
   `prewarm_poll_set()` already uses for a different call site.
2. `ports/unix/modsocket.c`'s `sendto()` has this exact same buffer-protocol requirement
   (`micropython/micropython#6924`, re-checked directly this session - it's specifically about
   `sendto()`, not bind()/connect() as first assumed) - but `sendto()`'s own destination address is
   a *per-call* argument (a DNS/NTP client's ephemeral reply address, learned dynamically from a
   real `recvfrom()`), not the constructor-time `self._addr` point 1 already covers, so it needs its
   own patch on `sendto()` specifically.
3. `ports/unix/modsocket.c`'s `recvfrom()` (confirmed directly against a real captured reply, not
   just the C source - this build's `mp_obj_from_sockaddr()` differs from what a first look at
   `ports/unix/modsocket.c`'s own `mod_socket_sockaddr()` utility function suggested) hands back the
   raw 16-byte packed C `struct sockaddr_in` as a plain `bytes` object - `sin_family` (2 bytes,
   native/little-endian on the x86_64 hosts this ever runs on), `sin_port` (2 bytes, network/
   big-endian), `sin_addr` (4 bytes), 8 bytes padding. `extmod/modlwip.c`'s `lwip_socket_recvfrom()`
   instead returns `(ip: str, port: int)` (`lwip_format_inet_addr()`) - a completely different
   shape, not just the same tuple in a different byte order. `captive_dns.py`'s own subnet check
   expects that `(str, int)` form (`addr[0]` is a dotted-decimal string) - correct for real
   hardware, confirmed directly against the source above - so under the Unix port `addr[0]` ends up
   being the raw bytes' own first byte (`0x02` == `AF_INET`, logged as "address 2"), degrading
   safely to the existing "off-subnet/malformed" fallback instead of ever matching. Patches
   `recvfrom()` to unpack the raw struct into the `(str, int)` shape whenever it sees this form -
   which is also what feeds `sendto()`'s own per-call address in a real request/reply cycle
   (captive_dns.py's own DNSServer echoes the client address recvfrom() gave it back into its reply
   sendto()), so point 3 normalizing recvfrom()'s output is what makes point 2's sendto() patch see
   an already-numeric, already-string address to resolve in the first place.

Call `patch_asy_udp_socket_for_unix_port()` once, early - before anything constructs an
`AsyUDPSocket`."""

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
