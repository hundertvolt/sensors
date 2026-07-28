"""Async, non-blocking DNS resolver (IPv4 A-records only) built on asy_udp_socket.py's AsyUDPSocket.

Inspired by github.com/vshymanskyy/aiodns (MIT license) after reading its design in detail, not a
port of it - deliberately narrower (no cache, no mDNS, IPv4 only) since this project's only caller
resolves one already-rarely-changing hostname roughly once per sync cycle. See BACKLOG.md for the
full comparison, attribution, and two correctness gaps found in aiodns and fixed here instead of
carried over.

Contract: resolve_ipv4() never raises - returns the resolved dotted-quad str, or None on any
failure (timeout, malformed/spoofed reply, NXDOMAIN/SERVFAIL, unreachable server, ...). A literal
IPv4 host is returned unchanged, untouched by the network.

Limitation: an answer's name is only followed when it's a bare compression pointer (RFC 1035
SS4.1.4), not a full label decompressor - matches captive_dns.py's own precedent. See BACKLOG.md.
"""

import os

from micropython import const

from asy_udp_socket import AsyUDPSocket

_DNS_PORT = const(53)
_DNS_TIMEOUT_MS = const(500)  # per-server, per-attempt budget - standalone default only, the real
# caller (asy_ntp_client.py) always overrides it explicitly. See BACKLOG.md.
_DNS_TRIES = const(1)  # per-server retry budget - resolve_ipv4() already tries multiple servers.
_DNS_RECV_BUF = const(512)  # RFC 1035 SS4.2.1's guaranteed-safe UDP message size.
_FALLBACK_DNS_SERVERS: tuple[str, ...] = ("8.8.8.8", "1.1.1.1")  # tried after caller-supplied
# servers. Not const()-wrapped so tests can monkeypatch it (const() inlines at compile time).

_QTYPE_A = const(b"\x00\x01")
_QCLASS_IN = const(b"\x00\x01")


def _is_ipv4_literal(host: str) -> bool:
    # Dotted-quad check, avoiding int()'s exceptions for control flow via isdigit().
    parts = host.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= 255):
            return False
    return True


def _build_query(host: bytes, txn_id: bytes) -> bytearray:
    # RFC 1035 SS4.1.1/4.1.2 message: 12-byte header + QNAME + QTYPE + QCLASS. QNAME is exactly
    # len(host) + 2 bytes on the wire regardless of label count - see BACKLOG.md for the exact-size
    # vs. aiodns's own off-by-one comparison.
    qname_len = len(host) + 2
    query = bytearray(12 + qname_len + 4)  # header + QNAME + QTYPE(2) + QCLASS(2)
    query[0:2] = txn_id
    query[2:4] = b"\x01\x00"  # QR=0 (query), Opcode=0 (standard), RD=1 (recursion desired)
    query[4:6] = b"\x00\x01"  # QDCOUNT=1 (ANCOUNT/NSCOUNT/ARCOUNT stay 0 - already zero-initialized)
    pos = 12
    for label in host.split(b"."):
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
    if len(rsp) < 12 or rsp[0:2] != query[0:2]:
        return None  # too short to be a real header, or a stale/spoofed reply (wrong transaction ID)
    if not (rsp[2] & 0x80):
        return None  # QR=0 - not actually a response
    if rsp[3] & 0x0F:
        return None  # RCODE != 0 (NXDOMAIN, SERVFAIL, ...) - a real error, not a usable answer
    answer_count = (rsp[6] << 8) | rsp[7]
    # Response's Question section mirrors the query's own (RFC 1035), so len(query) is the exact
    # answer-section offset.
    pos = len(query)
    for _ in range(answer_count):
        # Top-two-bits mask (RFC 1035 SS4.1.4: any 0xC0-0xFF leading byte), not `== 0xC0` - see
        # BACKLOG.md for the real bug this fixed (a valid pointer to offset >= 256 was misread).
        if pos + 12 > len(rsp) or (rsp[pos] & 0xC0) != 0xC0:
            break  # truncated, or a name that isn't a bare compression pointer
        rtype = (rsp[pos + 2] << 8) | rsp[pos + 3]
        rclass = (rsp[pos + 4] << 8) | rsp[pos + 5]
        rdlength = (rsp[pos + 10] << 8) | rsp[pos + 11]
        data_start = pos + 12
        if rtype == 1 and rclass == 1 and rdlength == 4 and data_start + 4 <= len(rsp):
            ip = rsp[data_start : data_start + 4]
            return f"{ip[0]}.{ip[1]}.{ip[2]}.{ip[3]}"
        pos = data_start + rdlength
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
    try:
        query = _build_query(host.lower().encode(), os.urandom(2))  # DNS names are case-insensitive (RFC 1035 SS2.3.3)
    except MemoryError:
        return None
    for server in dns_servers + _FALLBACK_DNS_SERVERS:
        if server == "0.0.0.0" or not _is_ipv4_literal(server):
            continue  # an unset/placeholder or malformed DNS server value - not worth a network attempt
        cli = AsyUDPSocket((server, port), mode="client")
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
