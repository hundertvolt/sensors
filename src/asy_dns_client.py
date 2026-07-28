"""Async, non-blocking DNS resolver (A records only) built on asy_udp_socket.py's AsyUDPSocket.

Inspired by github.com/vshymanskyy/aiodns (SPDX: MIT, (c) 2024 Volodymyr Shymanskyy) after reading
its packet-building/parsing/resolution strategy in detail - not a port of its code, and not a
drop-in of its API. MIT permits this freely (reuse/modify with attribution, no copyleft); this
comment plus BACKLOG.md's writeup is that attribution. Rewritten from scratch, deliberately
narrower than aiodns: IPv4/A-record only, one hostname per call, no cache, no mDNS - this project's
networking is IPv4-only throughout (see asy_udp_socket.py, captive_dns.py) and the only caller
(asy_ntp_client.py) resolves one already-rarely-changing hostname roughly once per sync cycle, so
aiodns's IPv6/mDNS support and 32-entry LRU cache would be unused complexity here. Transport is
this project's own AsyUDPSocket (cooperative, poll-driven) instead of aiodns's hand-rolled
non-blocking socket+sleep_ms loop - one fewer non-blocking-socket implementation in the codebase.
See BACKLOG.md for the full aiodns comparison, including two real correctness gaps found in it and
fixed here (an off-by-one query-size calculation masked by bytearray auto-resize, and no RCODE
check on the response) rather than carried over.

Exists so asy_ntp_client.py's NTP-hostname resolution no longer needs socket.getaddrinfo() (a
real, synchronously-blocking call) - and therefore no longer needs async_connect.py's
get_long_block_lock() coordination either; see asy_ntp_client.py's and neopixel_signal.py's own
docstrings for that removal.

Contract: resolve_ipv4() never raises - returns the resolved dotted-quad str, or None on any
failure (timeout, malformed/spoofed reply, NXDOMAIN/SERVFAIL, unreachable server, ...). A literal
IPv4 address is returned unchanged without ever touching the network, so an NTP_Host config value
that's already a literal IP keeps working exactly as it did through socket.getaddrinfo().

Documented, accepted limitation (matches this project's existing DNS-parsing precedent in
captive_dns.py, which takes the same trade-off): an answer record's own name field is only handled
when it's a bare 2-byte compression pointer (RFC 1035 SS4.1.4) - the near-universal case for a
straightforward A-record answer to an A-record query - not a full label decompressor. An answer
using literal (uncompressed) labels stops iteration and falls back to whatever answer (if any) was
already found, rather than being parsed. Good enough for this project's real NTP hosts (pool.ntp.org
and similar), not a general-purpose resolver.
"""

import os

from micropython import const

from asy_udp_socket import AsyUDPSocket

_DNS_PORT = const(53)
_DNS_TIMEOUT_MS = const(500)  # per-server, per-attempt budget - these are just this function's own
# standalone defaults, used only when a caller doesn't override timeout_ms/tries (asy_ntp_client.py
# always does, with its own explicitly-configured values - see that file's own constructor). A real
# resolver on a working network answers in well under 100ms; 500ms already gives that a wide
# margin without needlessly stretching out the case where a server is genuinely unreachable
# (an earlier, much larger pair of defaults here - 2000ms x 2 tries x up to 3 servers - produced a
# worst case of several seconds to over ten, flagged as excessive - see BACKLOG.md).
_DNS_TRIES = const(1)  # write_and_recvfrom()'s own retry budget per server - see _DNS_TIMEOUT_MS's
# own comment; one try per server is enough given resolve_ipv4() already tries multiple servers.
_DNS_RECV_BUF = const(512)  # RFC 1035 SS4.2.1's guaranteed-safe UDP message size; no EDNS0 OPT is
# sent, so no larger response is ever solicited.
_FALLBACK_DNS_SERVERS: tuple[str, ...] = ("8.8.8.8", "1.1.1.1")  # tried, in order, after the caller-supplied servers
# (typically the network's own DHCP-assigned DNS server) - Google/Cloudflare public resolvers,
# reachable from virtually any network that has real internet access at all, same rationale
# aiodns's own default server set uses. Deliberately NOT const()-wrapped, unlike every other
# module-level tuple in this file: MicroPython's const() inlines the literal value at compile time
# (confirmed directly - see tests/test_asy_wifi_service.py's own comment on the same behavior for
# its _PHASE_* constants), so a const()-wrapped value can't be monkeypatched from a test the way a
# plain module global can (tests/test_asy_dns_client.py's own fallback-list tests rely on this
# being genuinely overridable to stay hermetic, never touching the real public internet). resolve_
# ipv4() only reads this once per call (roughly once per NTP sync cycle - hours apart), so skipping
# the const-fold costs nothing performance-wise here, unlike this file's other, frequently-read constants.

_QTYPE_A = const(b"\x00\x01")
_QCLASS_IN = const(b"\x00\x01")


def _is_ipv4_literal(host: str) -> bool:
    # Dotted-quad check - if host is already numeric there's nothing to resolve. Adapted from
    # aiodns's own _ip4(), but avoids using exceptions for control flow: isdigit() rejects a
    # non-numeric/negative/empty part without needing a try/except around int().
    parts = host.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= 255):
            return False
    return True


def _build_query(host: bytes, txn_id: bytes) -> bytearray:
    # RFC 1035 SS4.1.1/4.1.2 message format: 12-byte header + QNAME (length-prefixed labels, null-
    # terminated) + QTYPE + QCLASS. Adapted from aiodns's _build_dns_query(), but computes the
    # exact final size upfront instead of aiodns's `bytearray(17 + len(host))` - confirmed by
    # hand-tracing aiodns's own byte offsets that its precomputed size is one byte short of what it
    # actually writes (its trailing `query[pos + 2 : pos + 4] = ...` reaches one index past the
    # array as sized); it "works" there only because Python's bytearray slice assignment silently
    # grows the array when the assigned data is longer than the sliced range - a real, if harmless,
    # correctness smell (relying on an incidental resize instead of a correct size calculation), not
    # reproduced here. Each "." in host becomes a 1-byte length prefix in the wire format (so it
    # contributes the same byte count either way), plus one terminating null byte -> QNAME is
    # exactly len(host) + 2 bytes on the wire, independent of label count.
    qname_len = len(host) + 2
    query = bytearray(12 + qname_len + 4)  # header + QNAME + QTYPE(2) + QCLASS(2)
    query[0:2] = txn_id
    query[2:4] = b"\x01\x00"  # QR=0 (query), Opcode=0 (standard), RD=1 (recursion desired)
    query[4:6] = b"\x00\x01"  # QDCOUNT=1 (ANCOUNT/NSCOUNT/ARCOUNT stay 0 - bytearray is zero-initialized)
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
    # See module docstring for the compression-pointer-only limitation. RCODE/QR/transaction-ID
    # checks are real correctness additions over aiodns (which checks none of these - see BACKLOG.md).
    if len(rsp) < 12 or rsp[0:2] != query[0:2]:
        return None  # too short to be a real header, or a stale/spoofed reply (wrong transaction ID)
    if not (rsp[2] & 0x80):
        return None  # QR=0 - not actually a response
    if rsp[3] & 0x0F:
        return None  # RCODE != 0 (NXDOMAIN, SERVFAIL, ...) - a real error, not a usable answer
    answer_count = (rsp[6] << 8) | rsp[7]
    # The response's Question section mirrors the query's own, unchanged (RFC 1035) - reusing
    # len(query) as the exact answer-section offset avoids aiodns's fragile `rsp.find(b"\xc0",
    # pos)` heuristic search entirely for the first answer.
    pos = len(query)
    for _ in range(answer_count):
        # A compression pointer's own target offset is never followed (see module docstring) - only
        # its *format* matters here, so the check is the top-two-bits mask (RFC 1035 SS4.1.4: any
        # 0xC0-0xFF leading byte), not literal equality with 0xC0. The earlier `!= 0xC0` form was a
        # real bug, not the documented limitation: it silently misidentified a valid pointer to any
        # offset >= 256 (leading byte 0xC1-0xFF) as an uncompressed name and aborted parsing, even
        # though such an offset is reachable within this file's own 512-byte _DNS_RECV_BUF (e.g. a
        # second answer in a CNAME chain pointing past byte 255).
        if pos + 12 > len(rsp) or (rsp[pos] & 0xC0) != 0xC0:
            break  # truncated, or a name that isn't a bare compression pointer - see module docstring
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
