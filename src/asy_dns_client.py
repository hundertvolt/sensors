# SPDX-FileCopyrightText: Copyright (c) 2024 Volodymyr Shymanskyy
# SPDX-License-Identifier: MIT
# Inspired by github.com/vshymanskyy/aiodns, not a port - THIRD_PARTY_LICENSES.md compares the two.

"""Async, non-blocking IPv4 DNS resolver (A-records only) built on asy_udp_socket.py's UDPSocket; a
`.local` name is asked once over multicast DNS instead (RFC 6762 SS5.1, SPECIFICATION.md Part A.11)."""
# resolve_ipv4() never raises, returns the dotted-quad str or None; only bare compression-pointer
# names (RFC 1035 SS4.1.4) are followed, matching asy_captive_dns.py's precedent.

import os

from micropython import const

from asy_udp_socket import UDPSocket

_DNS_PORT = const(53)
# @tunable dns.timeout_ms = 500
_DNS_TIMEOUT_MS = const(500)  # per-server, per-attempt budget - a standalone default only; real
# callers are expected to override it explicitly with a value suited to their own timing budget.
# @tunable dns.tries = 1
_DNS_TRIES = const(1)  # per-server retry budget - resolve_ipv4() already tries multiple servers.
_DNS_RECV_BUF = const(512)  # RFC 1035 SS4.2.1's guaranteed-safe UDP message size.
_FALLBACK_DNS_SERVERS: tuple[str, ...] = ("8.8.8.8", "1.1.1.1")  # tried after caller-supplied
# servers. Not const()-wrapped so tests can monkeypatch it (const() inlines at compile time).
_MDNS_SUFFIX = ".local"  # RFC 6762 SS3: names under it are resolved by multicast, never by a unicast server
_MDNS_GROUP = "224.0.0.251"  # RFC 6762 SS3's IPv4 group; not const()-wrapped, so tests can point it at a fake
_MDNS_PORT = 5353  # the responders' port, likewise a plain name for the tests

_QTYPE_A = const(b"\x00\x01")
_QCLASS_IN = const(b"\x00\x01")

_IPV4_OCTETS = const(4)  # dotted-quad parts, and an A-record's RDLENGTH (RFC 1035 SS3.4.1)
_IPV4_OCTET_MAX = const(255)
_LABEL_MAX_OCTETS = const(63)  # RFC 1035 SS3.1's single-length-byte ceiling
_HEADER_LEN = const(12)  # RFC 1035 SS4.1.1 fixed message header
_PTR_MASK = const(0xC0)  # RFC 1035 SS4.1.4 compression-pointer top-two-bits marker
_CLASS_MASK = const(0x7FFF)  # a record's class without RFC 6762 SS10.2's cache-flush bit


def _is_ipv4_literal(host: str) -> bool:
    # Dotted-quad check, avoiding int()'s exceptions for control flow via isdigit().
    parts = host.split(".")
    if len(parts) != _IPV4_OCTETS:
        return False
    return all(part.isdigit() and 0 <= int(part) <= _IPV4_OCTET_MAX for part in parts)


def _build_query(host: bytes, txn_id: bytes, *, recursion: bool = True) -> bytearray:
    # RFC 1035 SS4.1.1/4.1.2 message: 12-byte header + QNAME + QTYPE + QCLASS. QNAME is exactly
    # len(host) + 2 bytes on the wire regardless of label count; an mDNS query clears RD (RFC 6762 SS18.6).
    labels = host.split(b".")
    # RFC 1035 SS3.1/4.1.2: a label is length-prefixed by one byte, so over 63 octets is not a real
    # label and over 255 cannot be encoded at all. host comes from a REST-settable config field with
    # no per-label check, so this is reachable - raised for resolve_ipv4() to catch, not defensive.
    if any(len(label) > _LABEL_MAX_OCTETS for label in labels):
        raise ValueError(f"DNS label too long ({max(len(label) for label in labels)} > {_LABEL_MAX_OCTETS} octets)")
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
    query[pos : pos + 2] = _QTYPE_A
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


async def _resolve_mdns(query: bytearray, timeout_ms: int, tries: int) -> str | None:
    # A one-shot query from an ephemeral port (RFC 6762 SS5.1): a responder answers by unicast with the ID and
    # question repeated (SS6.7), from its own address, so the socket is bound rather than connected.
    try:
        attempts = range(tries)
    except TypeError:
        return None
    sock = UDPSocket(("0.0.0.0", 0), mode="server")
    try:
        for _ in attempts:
            if await sock.sendto(query, (_MDNS_GROUP, _MDNS_PORT), timeout_ms=timeout_ms) is None:
                continue
            rsp, _addr = await sock.recvfrom(_DNS_RECV_BUF, timeout_ms=timeout_ms)
            if rsp is None:
                continue
            try:
                ip = _parse_response(rsp, query)
            except (IndexError, ValueError):  # the same residual bounds case as the unicast path
                ip = None
            if ip is not None:
                return ip
    finally:
        await sock.disconnect()  # never raises - see asy_udp_socket.py's own contract
    return None


async def resolve_ipv4(
    host: str,
    dns_servers: tuple[str, ...] = (),
    port: int = _DNS_PORT,
    timeout_ms: int = _DNS_TIMEOUT_MS,
    tries: int = _DNS_TRIES,
) -> str | None:
    if _is_ipv4_literal(host):
        return host
    name = host.lower()  # DNS names are case-insensitive (RFC 1035 SS2.3.3)
    mdns = name.endswith(_MDNS_SUFFIX)
    try:
        query = _build_query(name.encode(), os.urandom(2), recursion=not mdns)
    except (MemoryError, ValueError):  # ValueError: a label over 63 octets - not a real DNS name, nothing to resolve
        return None
    if mdns:
        return await _resolve_mdns(query, timeout_ms, tries)
    for server in dns_servers + _FALLBACK_DNS_SERVERS:
        if server == "0.0.0.0" or not _is_ipv4_literal(server):
            continue  # an unset/placeholder or malformed DNS server value - not worth a network attempt
        try:
            cli = UDPSocket((server, port), mode="client")
        except (TypeError, ValueError):  # malformed port - server is already validated above
            continue
        try:
            rsp, _addr = await cli.write_and_recvfrom(query, _DNS_RECV_BUF, timeout_ms=timeout_ms, tries=tries)
        finally:
            await cli.disconnect()  # never raises - see asy_udp_socket.py's own contract
        if rsp is None:
            continue
        try:
            ip = _parse_response(rsp, query)
        except (IndexError, ValueError):  # residual bounds-math edge case against untrusted network bytes
            ip = None
        if ip is not None:
            return ip
    return None
