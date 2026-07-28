import asyncio
import select
import socket
import time

import asy_dns_client
from asy_dns_client import _build_query, _is_ipv4_literal, _parse_response, resolve_ipv4

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, Literal, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_HOST = "127.0.0.1"
_next_port = 54000


def make_port() -> int:  # a fresh loopback port per call, so tests never contend for the same address
    global _next_port
    _next_port += 1
    return _next_port


def _resolved(host: str, port: int) -> "Any":
    # Same Unix-port-only quirk as test_asy_udp_socket.py's own make_addr(): this build's raw
    # socket.bind()/connect()/sendto() reject a plain (host, port) tuple - only getaddrinfo()'s own
    # resolved (opaque, non-indexable) object works here. Used only for FakeDNSServer's real raw
    # socket below and by _ResolvingAsyUDPSocket - resolve_ipv4() itself is never handed anything
    # but plain host strings/int ports, matching its real typed signature.
    return socket.getaddrinfo(host, port)[0][-1]


class _ResolvingAsyUDPSocket:
    # Substitutes for asy_dns_client.py's own AsyUDPSocket import in these integration tests only.
    # resolve_ipv4() constructs AsyUDPSocket with a plain (host: str, port: int) tuple - the
    # correct, typed shape for real rp2 hardware, which has no such quirk - but this Unix-port test
    # build's connect() rejects that same plain tuple (see _resolved()'s comment above). Pre-
    # resolving it here proves resolve_ipv4()'s actual DNS-over-UDP behavior for real over loopback
    # without this unrelated interpreter-build quirk getting in the way; asy_dns_client.py's own
    # production code is completely unaware this wrapper exists.
    def __init__(self, addr: "tuple[str, int]", mode: 'Literal["client", "server"]' = "client", conn_tries: int = 1) -> None:
        self._real = _RealAsyUDPSocket(_resolved(addr[0], addr[1]), mode=mode, conn_tries=conn_tries)

    def __getattr__(self, name: str) -> "Any":
        return getattr(self._real, name)


_RealAsyUDPSocket = asy_dns_client.AsyUDPSocket  # captured before the module attribute below is overwritten
asy_dns_client.AsyUDPSocket = _ResolvingAsyUDPSocket  # type: ignore[misc, assignment]  # permanent for this test file's whole process - see _ResolvingAsyUDPSocket's own comment

# resolve_ipv4() always also tries asy_dns_client's own module-level _FALLBACK_DNS_SERVERS
# (the real 8.8.8.8/1.1.1.1) after whatever dns_servers a caller passes. Overridden here, for this
# whole test file's process, to a loopback-only value - every port used below comes from the
# strictly-incrementing make_port() counter, so this can never accidentally collide with a genuine
# test server bound elsewhere in this same run. Tests that want to prove the fallback list is
# actually reached override this further (and restore it back to this baseline, never to the real
# public list) so no test in this file ever makes a real call out to the public internet.
_UNREACHABLE_LOOPBACK_FALLBACK = (_HOST,)
asy_dns_client._FALLBACK_DNS_SERVERS = _UNREACHABLE_LOOPBACK_FALLBACK


# ---------------------------------------------------------------------------
# _is_ipv4_literal
# ---------------------------------------------------------------------------


def test_is_ipv4_literal_accepts_every_valid_dotted_quad() -> None:
    for host in ("0.0.0.0", "255.255.255.255", "192.168.1.1", "8.8.8.8", "127.0.0.1", "1.2.3.4"):
        assert _is_ipv4_literal(host) is True


def test_is_ipv4_literal_rejects_hostnames_and_malformed_input() -> None:
    for host in (
        "pool.ntp.org",
        "time.example.org",
        "256.0.0.1",  # octet out of range
        "1.2.3",  # too few parts
        "1.2.3.4.5",  # too many parts
        "1.2.3.-4",  # negative
        "1.2.3.",  # trailing dot -> empty last part
        "1..3.4",  # empty middle part
        "1.2.3.4a",  # trailing garbage
        "",
        "...",
        "1.2.3. 4",  # embedded whitespace
    ):
        assert _is_ipv4_literal(host) is False


# ---------------------------------------------------------------------------
# _build_query - RFC 1035 SS4.1.1/4.1.2 header + QNAME + QTYPE + QCLASS
# ---------------------------------------------------------------------------


def test_build_query_single_label_host_exact_bytes() -> None:
    txn_id = b"\xab\xcd"
    query = _build_query(b"localhost", txn_id)
    assert bytes(query[0:2]) == txn_id
    assert bytes(query[2:4]) == b"\x01\x00"  # standard query, recursion desired
    assert bytes(query[4:6]) == b"\x00\x01"  # QDCOUNT=1
    assert bytes(query[6:12]) == b"\x00\x00\x00\x00\x00\x00"  # ANCOUNT/NSCOUNT/ARCOUNT=0
    assert query[12] == 9  # label length for "localhost"
    assert bytes(query[13:22]) == b"localhost"
    assert query[22] == 0  # terminating null label
    assert bytes(query[23:25]) == b"\x00\x01"  # QTYPE=A
    assert bytes(query[25:27]) == b"\x00\x01"  # QCLASS=IN
    assert len(query) == 27


def test_build_query_multi_label_host_exact_bytes() -> None:
    txn_id = b"\x12\x34"
    query = _build_query(b"pool.ntp.org", txn_id)
    # QNAME wire length is len(host) + 2 regardless of label count (each "." becomes a 1-byte
    # length prefix) - see the module's own comment on this.
    assert len(query) == 12 + len(b"pool.ntp.org") + 2 + 4
    pos = 12
    for label in (b"pool", b"ntp", b"org"):
        assert query[pos] == len(label)
        pos += 1
        assert bytes(query[pos : pos + len(label)]) == label
        pos += len(label)
    assert query[pos] == 0
    pos += 1
    assert bytes(query[pos : pos + 2]) == b"\x00\x01"
    assert bytes(query[pos + 2 : pos + 4]) == b"\x00\x01"
    assert pos + 4 == len(query)


def test_build_query_size_matches_exactly_no_reliance_on_slice_autogrow() -> None:
    # The bug found in aiodns's own _build_dns_query() (see BACKLOG.md/module docstring): its
    # precomputed bytearray size was one byte short of what it actually wrote, only "working" via
    # bytearray slice-assignment silently growing the array. Prove our own version's precomputed
    # size is exact - the array never needs to grow past its initial allocation.
    for host in (b"a", b"a.b", b"pool.ntp.org", b"a.b.c.d.e.f"):
        query = _build_query(host, b"\x00\x00")
        expected_len = 12 + len(host) + 2 + 4
        assert len(query) == expected_len


def test_build_query_embeds_the_given_transaction_id_verbatim() -> None:
    for txn_id in (b"\x00\x00", b"\xff\xff", b"\x13\x37"):
        query = _build_query(b"example.com", txn_id)
        assert bytes(query[0:2]) == txn_id


# ---------------------------------------------------------------------------
# _parse_response - test fixture helpers build a realistic response by echoing the query's own
# header/question section, matching how a real DNS server (and captive_dns.py's own
# DNSQuery.response()) builds a reply.
# ---------------------------------------------------------------------------


def _be16(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _make_response(query: "bytes | bytearray", answers: bytes, ancount: int, flags: bytes = b"\x81\x80") -> bytes:
    header = bytes(query[0:2]) + flags + bytes(query[4:6]) + _be16(ancount) + b"\x00\x00\x00\x00"
    question = bytes(query[12:])
    return header + question + answers


def _a_answer(ip: str, name_ptr: bytes = b"\xc0\x0c", ttl: int = 60) -> bytes:
    ip_bytes = bytes(int(o) for o in ip.split("."))
    return name_ptr + b"\x00\x01" + b"\x00\x01" + ttl.to_bytes(4, "big") + _be16(4) + ip_bytes


def _cname_answer(target: bytes, name_ptr: bytes = b"\xc0\x0c", ttl: int = 60) -> bytes:
    return name_ptr + b"\x00\x05" + b"\x00\x01" + ttl.to_bytes(4, "big") + _be16(len(target)) + target


def test_parse_response_valid_single_a_answer() -> None:
    query = _build_query(b"pool.ntp.org", b"\x11\x22")
    rsp = _make_response(query, _a_answer("192.0.2.1"), ancount=1)
    assert _parse_response(rsp, query) == "192.0.2.1"


def test_parse_response_cname_then_a_answer_returns_the_a_records_ip() -> None:
    query = _build_query(b"time.example.org", b"\x33\x44")
    answers = _cname_answer(b"\xc0\x2a") + _a_answer("203.0.113.5", name_ptr=b"\xc0\x2a")
    rsp = _make_response(query, answers, ancount=2)
    assert _parse_response(rsp, query) == "203.0.113.5"


def test_parse_response_rejects_transaction_id_mismatch() -> None:
    query = _build_query(b"pool.ntp.org", b"\xaa\xbb")
    rsp = _make_response(query, _a_answer("192.0.2.1"), ancount=1)
    rsp = b"\xcc\xdd" + rsp[2:]  # a stale/spoofed reply carrying a different transaction ID
    assert _parse_response(rsp, query) is None


def test_parse_response_rejects_non_response_qr_bit() -> None:
    query = _build_query(b"pool.ntp.org", b"\x01\x02")
    rsp = _make_response(query, _a_answer("192.0.2.1"), ancount=1, flags=b"\x01\x00")  # QR=0
    assert _parse_response(rsp, query) is None


def test_parse_response_rejects_nxdomain_and_servfail_rcodes() -> None:
    query = _build_query(b"bogus.invalid", b"\x03\x04")
    for rcode_flags in (b"\x81\x83", b"\x81\x82"):  # NXDOMAIN=3, SERVFAIL=2
        rsp = _make_response(query, b"", ancount=0, flags=rcode_flags)
        assert _parse_response(rsp, query) is None


def test_parse_response_rejects_truncated_header() -> None:
    assert _parse_response(b"\x01\x02\x81\x80", b"\x01\x02" + b"\x00" * 10) is None


def test_parse_response_zero_answer_count_returns_none() -> None:
    query = _build_query(b"pool.ntp.org", b"\x05\x06")
    rsp = _make_response(query, b"", ancount=0)
    assert _parse_response(rsp, query) is None


def test_parse_response_answer_section_truncated_mid_record() -> None:
    query = _build_query(b"pool.ntp.org", b"\x07\x08")
    rsp = _make_response(query, b"\xc0\x0c\x00\x01", ancount=1)  # cut off right after the name pointer
    assert _parse_response(rsp, query) is None


def test_parse_response_uncompressed_answer_name_is_not_parsed() -> None:
    # Documented limitation (module docstring): only a bare 2-byte compression pointer is
    # supported for an answer's own name field - a literal/uncompressed label sequence stops
    # iteration cleanly instead of being decompressed or crashing.
    query = _build_query(b"pool.ntp.org", b"\x09\x0a")
    literal_name_answer = b"\x04pool\x00" + b"\x00\x01\x00\x01\x00\x00\x00\x3c" + _be16(4) + bytes([1, 2, 3, 4])
    rsp = _make_response(query, literal_name_answer, ancount=1)
    assert _parse_response(rsp, query) is None


def test_parse_response_rdlength_beyond_buffer_is_rejected_not_crashed() -> None:
    query = _build_query(b"pool.ntp.org", b"\x0b\x0c")
    bogus = b"\xc0\x0c" + b"\x00\x01" + b"\x00\x01" + b"\x00\x00\x00\x3c" + _be16(4)  # claims 4 bytes of rdata that were never appended
    rsp = _make_response(query, bogus, ancount=1)
    assert _parse_response(rsp, query) is None


def test_parse_response_skips_non_a_records_to_find_the_real_a_record() -> None:
    # AAAA (type 28) first, A record second - proves type filtering, not just "first answer wins".
    query = _build_query(b"dual-stack.example", b"\x0d\x0e")
    aaaa = b"\xc0\x0c" + b"\x00\x1c" + b"\x00\x01" + b"\x00\x00\x00\x3c" + _be16(16) + bytes(range(16))
    a = _a_answer("198.51.100.7")
    rsp = _make_response(query, aaaa + a, ancount=2)
    assert _parse_response(rsp, query) == "198.51.100.7"


def test_parse_response_accepts_a_compression_pointer_targeting_offset_256_or_above() -> None:
    # Regression test for a real bug found in this file's own review: RFC 1035 SS4.1.4 identifies a
    # compression pointer by its top two bits (0xC0 mask), not by the leading byte being literally
    # 0xC0 - that's only true for pointers whose target offset is < 256. A pointer to offset >= 256
    # (leading byte 0xC1-0xFF) is reachable within this file's own 512-byte _DNS_RECV_BUF (e.g. a
    # second answer in a CNAME chain pointing past byte 255) and was previously misidentified as an
    # uncompressed name, aborting parsing. The actual target offset is never followed (see module
    # docstring), so any 0xC1-0xFF leading byte must be accepted the same as 0xC0.
    query = _build_query(b"pool.ntp.org", b"\x11\x12")
    rsp = _make_response(query, _a_answer("192.0.2.200", name_ptr=b"\xc1\x2c"), ancount=1)
    assert _parse_response(rsp, query) == "192.0.2.200"


def test_parse_response_no_a_record_present_returns_none() -> None:
    query = _build_query(b"ipv6-only.example", b"\x0f\x10")
    aaaa = b"\xc0\x0c" + b"\x00\x1c" + b"\x00\x01" + b"\x00\x00\x00\x3c" + _be16(16) + bytes(range(16))
    rsp = _make_response(query, aaaa, ancount=1)
    assert _parse_response(rsp, query) is None


# ---------------------------------------------------------------------------
# resolve_ipv4 - literal-IP short circuit (no network I/O at all)
# ---------------------------------------------------------------------------


def test_resolve_ipv4_literal_ip_returns_immediately_without_touching_the_network() -> None:
    # dns_servers deliberately point nowhere real (and aren't even valid literals for two of the
    # three) - if resolve_ipv4() ever tried to actually use them, this would time out instead of
    # returning promptly.
    t0 = time.ticks_ms()
    result = run(resolve_ipv4("192.168.1.50", dns_servers=("not-an-ip", "")))
    elapsed = time.ticks_diff(time.ticks_ms(), t0)
    assert result == "192.168.1.50"
    assert elapsed < 200


# ---------------------------------------------------------------------------
# resolve_ipv4 - real UDP loopback fake DNS server, mirroring test_asy_udp_socket.py's own
# AdversarialPeer pattern (a genuine independent socket, not a mock of AsyUDPSocket).
# ---------------------------------------------------------------------------


class FakeDNSServer:
    def __init__(self, host: str, port: int) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(_resolved(host, port))
        self.sock.setblocking(False)
        self.received: list[bytes] = []

    async def answer_once(self, build_response: "Any", timeout_ms: int = 2000) -> None:
        # Waits for one query, records it, then replies with whatever build_response(query) returns.
        # Must check the actual returned event bitmask, not just ipoll()'s truthiness - confirmed
        # directly that this build's ipoll(0) reports a registered socket as "ready" on every tick
        # regardless of whether real data is pending (almost certainly POLLOUT, a UDP socket's send
        # buffer being available, not POLLIN) - the same reason asy_udp_socket.py's own ready()
        # checks `event & mask` rather than treating ipoll()'s result as a plain bool.
        poller = select.poll()
        poller.register(self.sock, select.POLLIN)
        t0 = time.ticks_ms()
        query: bytes | None = None
        addr: tuple[str, int] | None = None
        while query is None:
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                raise OSError("FakeDNSServer.answer_once() timed out waiting for a query")
            readable = any(event & select.POLLIN for _fd, event in poller.ipoll(0))
            if readable:
                try:
                    query, addr = self.sock.recvfrom(512)
                except OSError:
                    pass
            if query is None:
                await asyncio.sleep_ms(5)
        self.received.append(query)
        response = build_response(query)
        if response is not None:
            assert addr is not None  # always paired with query by a successful recvfrom() above
            self.sock.sendto(response, addr)

    def close(self) -> None:
        self.sock.close()


def test_resolve_ipv4_success_via_a_real_fake_dns_server() -> None:
    port = make_port()

    async def scenario() -> "str | None":
        server = FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("10.20.30.40"), ancount=1)))
            result = await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), port=port, timeout_ms=1000, tries=1)
            await responder
            return result
        finally:
            server.close()

    assert run(scenario()) == "10.20.30.40"


def test_resolve_ipv4_no_server_reachable_returns_none() -> None:
    port = make_port()  # nobody listens here

    async def scenario() -> "str | None":
        return await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), port=port, timeout_ms=100, tries=1)

    assert run(scenario()) is None


def test_resolve_ipv4_garbage_reply_returns_none_not_an_exception() -> None:
    port = make_port()

    async def scenario() -> "str | None":
        server = FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: b"\x00\x01not-a-real-dns-reply-at-all"))
            result = await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), port=port, timeout_ms=300, tries=1)
            await responder
            return result
        finally:
            server.close()

    assert run(scenario()) is None


def test_resolve_ipv4_nxdomain_returns_none() -> None:
    port = make_port()

    def nxdomain_response(query: bytes) -> bytes:
        return _make_response(query, b"", ancount=0, flags=b"\x81\x83")

    async def scenario() -> "str | None":
        server = FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(nxdomain_response))
            result = await resolve_ipv4("bogus.invalid", dns_servers=(_HOST,), port=port, timeout_ms=300, tries=1)
            await responder
            return result
        finally:
            server.close()

    assert run(scenario()) is None


def test_resolve_ipv4_falls_back_to_the_second_server_when_the_first_is_unreachable() -> None:
    real_server_port = make_port()
    # 10.255.255.254 is never a local interface address in this environment (same deterministic
    # unroutable address test_asy_udp_socket.py's own unbindable_addr() uses).
    unreachable_ip = "10.255.255.254"

    async def scenario() -> "str | None":
        server = FakeDNSServer(_HOST, real_server_port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("172.16.0.9"), ancount=1)))
            result = await resolve_ipv4(
                "pool.ntp.org",
                dns_servers=(unreachable_ip,),
                port=real_server_port,
                timeout_ms=200,
                tries=1,
            )
            await responder
            return result
        finally:
            server.close()

    # The first (genuinely unroutable) server attempt must time out and fall through to the
    # fallback list - proven by monkeypatching that list (already pointed at loopback-only for this
    # whole test file - see _UNREACHABLE_LOOPBACK_FALLBACK above) to the real fake server's address
    # instead, exactly like other test files monkeypatch a module-level name they don't own (see
    # test_asy_udp_socket.py's own asy_udp_socket.socket swap).
    asy_dns_client._FALLBACK_DNS_SERVERS = (_HOST,)
    try:
        assert run(scenario()) == "172.16.0.9"
    finally:
        asy_dns_client._FALLBACK_DNS_SERVERS = _UNREACHABLE_LOOPBACK_FALLBACK


def test_resolve_ipv4_skips_unset_and_malformed_dns_server_entries() -> None:
    port = make_port()

    async def scenario() -> "str | None":
        server = FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("192.0.2.99"), ancount=1)))
            # "0.0.0.0" (DHCP-unset sentinel), "" (empty), and a non-numeric hostname are all
            # skipped without a network attempt, falling through to the monkeypatched fallback.
            result = await resolve_ipv4(
                "pool.ntp.org",
                dns_servers=("0.0.0.0", "", "not-an-ip"),
                port=port,
                timeout_ms=200,
                tries=1,
            )
            await responder
            return result
        finally:
            server.close()

    asy_dns_client._FALLBACK_DNS_SERVERS = (_HOST,)
    try:
        assert run(scenario()) == "192.0.2.99"
    finally:
        asy_dns_client._FALLBACK_DNS_SERVERS = _UNREACHABLE_LOOPBACK_FALLBACK


def test_resolve_ipv4_no_servers_at_all_and_no_reachable_fallback_returns_none() -> None:
    # dns_servers empty, and the fallback list monkeypatched to a loopback port nobody listens
    # on - proves a total resolution failure still degrades to None, not an exception, without
    # depending on this sandboxed test environment's real internet reachability (the real
    # 8.8.8.8/1.1.1.1 fallback would be non-hermetic here - see the module's own fallback list).
    unreachable_port = make_port()

    async def scenario() -> "str | None":
        return await resolve_ipv4("pool.ntp.org", dns_servers=(), port=unreachable_port, timeout_ms=100, tries=1)

    asy_dns_client._FALLBACK_DNS_SERVERS = (_HOST,)
    try:
        assert run(scenario()) is None
    finally:
        asy_dns_client._FALLBACK_DNS_SERVERS = _UNREACHABLE_LOOPBACK_FALLBACK


class _RaisingOsModule:
    def urandom(self, n: int) -> bytes:
        raise MemoryError("simulated allocation failure")


def test_resolve_ipv4_memoryerror_building_the_query_returns_none() -> None:
    original_os = asy_dns_client.os
    asy_dns_client.os = _RaisingOsModule()  # type: ignore[assignment]
    try:
        result = run(resolve_ipv4("pool.ntp.org", dns_servers=(), timeout_ms=50, tries=1))
    finally:
        asy_dns_client.os = original_os
    assert result is None


def test_resolve_ipv4_cname_chain_end_to_end() -> None:
    port = make_port()

    def cname_then_a(query: bytes) -> bytes:
        answers = _cname_answer(b"\xc0\x2a") + _a_answer("203.0.113.77", name_ptr=b"\xc0\x2a")
        return _make_response(query, answers, ancount=2)

    async def scenario() -> "str | None":
        server = FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(cname_then_a))
            result = await resolve_ipv4("time.example.org", dns_servers=(_HOST,), port=port, timeout_ms=500, tries=1)
            await responder
            return result
        finally:
            server.close()

    assert run(scenario()) == "203.0.113.77"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
