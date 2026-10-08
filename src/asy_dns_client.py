# SPDX-FileCopyrightText: Copyright (c) 2024 Volodymyr Shymanskyy
# SPDX-License-Identifier: MIT
# Inspired by github.com/vshymanskyy/aiodns, not a port - THIRD_PARTY_LICENSES.md compares the two.

"""Async, non-blocking IPv4 DNS resolver (A records only) built on asy_udp_socket.py's UDPSocket; a
`.local` name is asked once over multicast DNS instead (RFC 6762 SS5.1, SPECIFICATION.md Part A.11)."""
# resolve_ipv4() never raises: it tries the caller's servers in order (no built-in server) and returns
# the dotted-quad str or None; a name RFC 1035 cannot encode resolves to None. Only bare compression-pointer
# answer names (RFC 1035 SS4.1.4) are followed, matching asy_captive_dns.py's precedent.

import os

from micropython import const

from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_print_log import PrintLogHistory

_WRN_SOCKET_TEARDOWN = const(12)
_WRN_DNS_REPLY_TRUNCATED = const(16)

_DNS_PORT = const(53)
# @tunable dns.timeout_ms = 500
_DNS_TIMEOUT_MS = const(500)  # per-server, per-attempt budget - a standalone default only; real
# callers are expected to override it explicitly with a value suited to their own timing budget.
# @tunable dns.tries = 1
_DNS_TRIES = const(1)  # per-server retry budget - resolve_ipv4() already tries multiple servers.
DNS_UDP_MAX = const(512)  # RFC 1035 SS4.2.1: a DNS message over UDP is at most 512 octets.
_MDNS_SUFFIX = ".local"  # RFC 6762 SS3: names under it are resolved by multicast, never by a unicast server
_MDNS_GROUP = "224.0.0.251"  # RFC 6762 SS3's IPv4 group; not const()-wrapped, so tests can point it at a fake
_MDNS_PORT = 5353  # the responders' port, likewise a plain name for the tests

DNS_QTYPE_A = const(b"\x00\x01")
_QCLASS_IN = const(b"\x00\x01")

_IPV4_OCTETS = const(4)  # dotted-quad parts, and an A-record's RDLENGTH (RFC 1035 SS3.4.1)
_IPV4_OCTET_MAX = const(255)
DNS_LABEL_MAX = const(63)  # RFC 1035 SS3.1's single-length-byte ceiling
DNS_NAME_MAX = const(255)  # RFC 1035 SS3.1: a name is at most 255 octets on the wire
_HEADER_LEN = const(12)  # RFC 1035 SS4.1.1 fixed message header
_PTR_MASK = const(0xC0)  # RFC 1035 SS4.1.4 compression-pointer top-two-bits marker
_CLASS_MASK = const(0x7FFF)  # a record's class without RFC 6762 SS10.2's cache-flush bit


def _build_query(host: bytes, txn_id: bytes, *, recursion: bool = True) -> bytearray:
    # RFC 1035 SS4.1.1/4.1.2 message: 12-byte header + QNAME + QTYPE + QCLASS. QNAME is exactly
    # len(host) + 2 bytes on the wire regardless of label count; an mDNS query clears RD (RFC 6762 SS18.6).
    labels = host.split(b".")
    # resolve_ipv4() is public: a name RFC 1035 SS3.1 cannot encode (a label over 63 octets, an empty label, over 255
    # octets on the wire) is refused here whatever its caller checked; resolve_ipv4() maps it to None.
    if len(host) + 2 > DNS_NAME_MAX or b"" in labels:
        raise ValueError("not an encodable DNS name")
    if any(len(label) > DNS_LABEL_MAX for label in labels):
        raise ValueError(f"DNS label too long ({max(len(label) for label in labels)} > {DNS_LABEL_MAX} octets)")
    qname_len = len(host) + 2
    query = bytearray(_HEADER_LEN + qname_len + 4)  # header + QNAME + QTYPE(2) + QCLASS(2)
    query[0:2] = txn_id
    query[2:4] = b"\x01\x00" if recursion else b"\x00\x00"  # QR=0 (query), Opcode=0 (standard), RD as asked
    query[4:6] = b"\x00\x01"  # QDCOUNT=1 (ANCOUNT/NSCOUNT/ARCOUNT stay 0 - already zero-initialized)
    pos = _HEADER_LEN
    for label in labels:
        n = len(label)
        query[pos] = n
        pos += 1
        query[pos : pos + n] = label
        pos += n
    query[pos] = 0  # terminating null label
    pos += 1
    query[pos : pos + 2] = DNS_QTYPE_A
    query[pos + 2 : pos + 4] = _QCLASS_IN
    return query


def _parse_response(rsp: bytes | bytearray, query: bytes | bytearray) -> str | None:
    # See module docstring for the compression-pointer-only limitation.
    if len(rsp) < _HEADER_LEN or rsp[0:2] != query[0:2]:
        return None  # too short to be a real header, or a stale/spoofed reply (wrong transaction ID)
    if not (rsp[2] & 0x80):
        return None  # QR=0 - not actually a response
    if rsp[3] & 0x0F:
        return None  # RCODE != 0 (NXDOMAIN, SERVFAIL, ...) - a real error, not a usable answer
    answer_count = (rsp[6] << 8) | rsp[7]
    # Response's Question section mirrors the query's own (RFC 1035; RFC 6762 SS6.7 for mDNS), so
    # len(query) is the exact answer-section offset; a reply without it starts its answers at the header's end.
    pos = len(query) if (rsp[4] << 8) | rsp[5] else _HEADER_LEN
    for _ in range(answer_count):
        # Top-two-bits mask (RFC 1035 SS4.1.4: any 0xC0-0xFF leading byte), not `== 0xC0` - a
        # bare `== 0xC0` would misread any valid pointer to offset >= 256.
        if pos + 12 > len(rsp) or (rsp[pos] & _PTR_MASK) != _PTR_MASK:
            break  # truncated, or a name that isn't a bare compression pointer
        rtype = (rsp[pos + 2] << 8) | rsp[pos + 3]
        rclass = (rsp[pos + 4] << 8) | rsp[pos + 5]
        rdlength = (rsp[pos + 10] << 8) | rsp[pos + 11]
        data_start = pos + 12
        # The top class bit is mDNS's cache-flush flag (RFC 6762 SS10.2), never part of a unicast class.
        if rtype == 1 and rclass & _CLASS_MASK == 1 and rdlength == _IPV4_OCTETS and data_start + _IPV4_OCTETS <= len(rsp):
            ip = rsp[data_start : data_start + _IPV4_OCTETS]
            return f"{ip[0]}.{ip[1]}.{ip[2]}.{ip[3]}"
        pos = data_start + rdlength
    return None


def host_label_ok(label: str) -> bool:
    # RFC 1123 SS2.1 host label (letters, digits, '-'; not at either end); the caller bounds the length.
    if not label or label[0] == "-" or label[-1] == "-":
        return False
    return all("0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z" or ch == "-" for ch in label)


def ipv4_to_int(ip: str) -> int | None:
    # RFC 791 section 3.2 dotted-quad -> 32-bit big-endian form; never raises for a malformed str
    parts = ip.split(".")
    if len(parts) != _IPV4_OCTETS:
        return None
    octets = []
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= _IPV4_OCTET_MAX):
            return None
        octets.append(int(part))
    a, b, c, d = octets
    return (a << 24) | (b << 16) | (c << 8) | d


def host_name_ok(value: object) -> bool:
    # The hostName shape (js/mock-server.js mirrors it): an IPv4 literal, or dot-separated RFC 1123 labels of at most 63 characters.
    if type(value) is not str:
        return False
    return ipv4_to_int(value) is not None or all(len(label) <= DNS_LABEL_MAX and host_label_ok(label) for label in value.split("."))


async def _resolve_mdns(query: bytearray, timeout_ms: int, tries: int, pr: "PrintLogHistory") -> str | None:
    # A one-shot query from an ephemeral port (RFC 6762 SS5.1): a responder answers by unicast with the ID and
    # question repeated, as a conventional DNS reply (SS6.7), from its own address, so the socket is bound, not connected.
    try:
        attempts = range(tries)
    except TypeError:
        return None
    sock = UDPSocket(("0.0.0.0", 0), mode="server")
    try:
        for _ in attempts:
            if await sock.sendto(query, (_MDNS_GROUP, _MDNS_PORT), timeout_ms=timeout_ms) is None:
                continue
            rsp, _addr = await sock.recvfrom(DNS_UDP_MAX + 1, timeout_ms=timeout_ms)
            if rsp is None:
                continue
            if len(rsp) > DNS_UDP_MAX:  # the unicast path's cut-reply case (SS6.7's reply is a conventional one)
                await pr.wrn_s("DNS reply truncated, trying the next server:", _MDNS_GROUP, wrnno=_WRN_DNS_REPLY_TRUNCATED)
                continue
            try:
                ip = _parse_response(rsp, query)
            except (IndexError, ValueError):  # the same residual bounds case as the unicast path
                ip = None
            if ip is not None:
                return ip
    finally:
        if not await sock.disconnect():
            await pr.wrn_s("DNS socket teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)
    return None


async def resolve_ipv4(
    host: str,
    dns_servers: tuple[str, ...] = (),
    timeout_ms: int = _DNS_TIMEOUT_MS,
    tries: int = _DNS_TRIES,
    *,
    pr: "PrintLogHistory",
) -> str | None:
    if ipv4_to_int(host) is not None:
        return host
    name = host.lower()  # DNS names are case-insensitive (RFC 1035 SS2.3.3)
    mdns = name.endswith(_MDNS_SUFFIX)
    try:
        query = _build_query(name.encode(), os.urandom(2), recursion=not mdns)
    except (MemoryError, ValueError):  # ValueError: a name RFC 1035 cannot encode - nothing to resolve
        return None
    if mdns:
        return await _resolve_mdns(query, timeout_ms, tries, pr)
    for server in dns_servers:
        if server == "0.0.0.0" or ipv4_to_int(server) is None:
            continue  # an unset/placeholder or malformed DNS server value - not worth a network attempt
        cli = UDPSocket((server, _DNS_PORT), mode="client")
        try:
            rsp, _addr = await cli.write_and_recvfrom(query, DNS_UDP_MAX + 1, timeout_ms=timeout_ms, tries=tries)
        finally:
            if not await cli.disconnect():
                await pr.wrn_s("DNS socket teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)
        # A whole reply is at most DNS_UDP_MAX (RFC 1035 SS4.2.1, no EDNS sent); a fuller buffer means lwIP cut it (extmod/modlwip.c:719-721, v1.29.0).
        if rsp is not None and len(rsp) > DNS_UDP_MAX:
            await pr.wrn_s("DNS reply truncated, trying the next server:", server, wrnno=_WRN_DNS_REPLY_TRUNCATED)
            continue
        if rsp is None:
            continue
        try:
            ip = _parse_response(rsp, query)
        except (IndexError, ValueError):  # residual bounds-math edge case against untrusted network bytes
            ip = None
        if ip is not None:
            return ip
    return None
