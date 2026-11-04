"""The DNS client: query building, reply parsing and its refusals, and IPv4 resolution against fake servers over a real
UDP socket on loopback."""

import asyncio
import errno
import select
import socket
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

from _async_harness import run
from _cancel_sweep import SocketLedger, cancel_at_each_await
from _fake_time import DrivenTime
from _port_bands import PortAllocator
from _recording_print import record_prints
from _src_const import src_const
from _udp_port_redirect import redirect_udp_port
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

import asy_dns_client
import asy_udp_socket
from asy_dns_client import _build_query, _parse_response, ipv4_to_int, resolve_ipv4
from asy_print_log import PrintLogHistory

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    T = TypeVar("T")


_PROMPT_RETURN_MAX_MS = 200
_FAKE_SERVER_WAIT_MS = 2000
_FAKE_SERVER_POLL_MS = 5
_REPLY_TIMEOUT_MS = 1000
_NO_REPLY_TIMEOUT_MS = 100
_BAD_REPLY_TIMEOUT_MS = 300
_FALLBACK_TIMEOUT_MS = 200
_CNAME_REPLY_TIMEOUT_MS = 500


_HOST = "127.0.0.1"
_DNS_PORT = src_const("src/asy_dns_client.py", "_DNS_PORT")
# This file's own band of tests/_port_bands.py: files run concurrently, and a UDP collision is a silent timeout.
_PORTS = PortAllocator("test_asy_dns_client")


def _a_answer(ip: str, name_ptr: bytes = b"\xc0\x0c", ttl: int = 60) -> bytes:
    ip_bytes = bytes(int(o) for o in ip.split("."))
    return name_ptr + b"\x00\x01" + b"\x00\x01" + ttl.to_bytes(4, "big") + _be16(4) + ip_bytes


def _be16(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _cname_answer(target: bytes, name_ptr: bytes = b"\xc0\x0c", ttl: int = 60) -> bytes:
    return name_ptr + b"\x00\x05" + b"\x00\x01" + ttl.to_bytes(4, "big") + _be16(len(target)) + target


def _make_port() -> int:  # a fresh loopback port per call, so tests never contend for the same address
    return _PORTS.next()


def _make_pr() -> PrintLogHistory:  # a fresh in-memory logger for one resolve_ipv4() call's logger=
    return PrintLogHistory(name="DNSTEST")


def _make_response(query: "bytes | bytearray", answers: bytes, ancount: int, flags: bytes = b"\x81\x80") -> bytes:
    header = bytes(query[0:2]) + flags + bytes(query[4:6]) + _be16(ancount) + b"\x00\x00\x00\x00"
    question = bytes(query[12:])
    return header + question + answers


def _resolved(host: str, port: int) -> "tuple[str, int]":
    # This Unix build's raw bind()/sendto() need getaddrinfo()'s opaque sockaddr (SPECIFICATION.md F.7);
    # only the fake server's own socket uses it.
    #
    # cast, not a bare return: the stub types getaddrinfo()'s sockaddr slot as the IPv4 2-tuple or IPv6's
    # 4-tuple, and this project is IPv4-only - the same narrowing digital_twin's own address shim makes.
    return cast("tuple[str, int]", socket.getaddrinfo(host, port)[0][-1])


# ---------------------------------------------------------------------------
# ipv4_to_int - RFC 791 dotted-quad -> int | None. Never raises for a str (isdigit() before int());
# only a wrong-typed (non-str) value still raises, via ip.split().
# ---------------------------------------------------------------------------


def test_ipv4_to_int_accepts_every_valid_dotted_quad() -> None:
    # Each value by hand (RFC 791 section 3.2): a.b.c.d is a * 2**24 + b * 2**16 + c * 2**8 + d.
    for host, value in (("0.0.0.0", 0), ("255.255.255.255", 4294967295), ("192.168.1.1", 3232235777), ("8.8.8.8", 134744072), ("127.0.0.1", 2130706433), ("1.2.3.4", 16909060)):
        assert ipv4_to_int(host) == value, host


def test_ipv4_to_int_rejects_hostnames_and_malformed_input() -> None:
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
        assert ipv4_to_int(host) is None


def test_ipv4_to_int_valid() -> None:
    assert ipv4_to_int("0.0.0.0") == 0
    assert ipv4_to_int("255.255.255.255") == 0xFFFFFFFF
    assert ipv4_to_int("192.168.4.1") == (192 << 24) | (168 << 16) | (4 << 8) | 1


def test_ipv4_to_int_rejects_wrong_octet_count() -> None:
    for bad in ("1.2.3", "1.2.3.4.5", "", "1.2.3.4."):
        assert ipv4_to_int(bad) is None


def test_ipv4_to_int_rejects_out_of_range_octet() -> None:
    # A previously-silent gap: an out-of-range octet used to shift bits past its own byte position
    # instead of being rejected, risking a false subnet match rather than a clean "invalid" signal.
    for bad in ("256.0.0.0", "1.2.3.999", "-1.2.3.4"):
        assert ipv4_to_int(bad) is None


def test_ipv4_to_int_rejects_non_numeric_octet() -> None:
    assert ipv4_to_int("a.b.c.d") is None


def test_ipv4_to_int_rejects_single_invalid_parameter_type() -> None:
    # Real callers only ever pass str (network.WLAN.ifconfig()'s values, a sockaddr's addr[0], a config
    # string), but this is a public function - a wrongly-typed value must raise AttributeError or
    # TypeError, never something else.
    for bad in (None, 123, 1.5, [1, 2, 3, 4], b"1.2.3.4", ("1", "2", "3", "4")):
        try:
            ipv4_to_int(bad)  # type: ignore[arg-type]
            raise AssertionError(f"expected an exception for {bad!r}")
        except (AttributeError, TypeError):
            pass


def test_ipv4_to_int_rejects_multiple_simultaneous_fault_recombinations() -> None:
    # Combines more than one fault within the same value - wrong octet count, out-of-range, and
    # non-numeric octets all at once - to prove the guard doesn't depend on faults appearing alone.
    for bad in ("300.-5.abc.999.1", "abc.def", "999.999", "1.2.a.999.-1"):
        assert ipv4_to_int(bad) is None


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
    # The bug found in aiodns's own _build_dns_query(): its precomputed bytearray size was one byte short of
    # what it actually wrote, only "working" because slice-assignment silently grew the array. This proves
    # our version's precomputed size is exact - the array never grows past its initial allocation.
    for host in (b"a", b"a.b", b"pool.ntp.org", b"a.b.c.d.e.f"):
        query = _build_query(host, b"\x00\x00")
        expected_len = 12 + len(host) + 2 + 4
        assert len(query) == expected_len


def test_build_query_embeds_the_given_transaction_id_verbatim() -> None:
    for txn_id in (b"\x00\x00", b"\xff\xff", b"\x13\x37"):
        query = _build_query(b"example.com", txn_id)
        assert bytes(query[0:2]) == txn_id


def test_build_query_accepts_a_label_at_the_exact_63_octet_rfc_limit() -> None:
    # RFC 1035 SS3.1/4.1.2's own boundary - the exact limit is a real, valid DNS name, not an
    # off-by-one over the guard added below.
    label = b"a" * 63
    query = _build_query(label, b"\x00\x00")
    assert query[12] == 63
    assert bytes(query[13 : 13 + 63]) == label


def test_build_query_raises_value_error_for_a_label_over_the_63_octet_rfc_limit() -> None:
    # A dot-free label of 64+ octets: RFC 1035 SS3.1's 63-octet limit refuses it here, whatever the caller
    # checked (resolve_ipv4() is public; the NTPHost PUT's hostName shape check refuses it earlier).
    try:
        _build_query(b"a" * 64, b"\x00\x00")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_build_query_raises_value_error_for_a_label_past_the_bytearray_byte_range() -> None:
    # A label past 255 octets: MicroPython stores n & 0xFF into the bytearray without raising (py/binary.c:45-47,
    # 565-567, v1.29.0), so the query would carry a wrong length byte; the guard rejects it before the store.
    try:
        _build_query(b"a" * 300, b"\x00\x00")
        raised = False
    except ValueError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# _parse_response - test fixture helpers build a realistic response by echoing the query's own
# header/question section, matching how a real DNS server (and asy_captive_dns.py's own
# DNSQuery.response()) builds a reply.
# ---------------------------------------------------------------------------


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
    # Regression test for a real bug found in review: RFC 1035 4.1.4 identifies a compression pointer by its
    # top two bits (0xC0 mask), not by the leading byte literally being 0xC0, which only holds for targets
    # below offset 256.
    #
    # A pointer to offset >= 256 is reachable within a whole 512-byte DNS message - a second answer
    # in a CNAME chain, say - and was misidentified as an uncompressed name, aborting parsing. The target
    # offset is never followed, so any 0xC1-0xFF leading byte must be accepted like 0xC0.
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
    # A literal host is its own answer: no socket is constructed even with a usable server in the list.
    t0 = time.ticks_ms()
    with redirect_udp_port(asy_dns_client, _DNS_PORT, _make_port()) as redirect:
        result = run(resolve_ipv4("192.168.1.50", dns_servers=(_HOST, "not-an-ip", "")))
    elapsed = time.ticks_diff(time.ticks_ms(), t0)
    assert result == "192.168.1.50"
    assert redirect.constructed == 0
    assert elapsed < _PROMPT_RETURN_MAX_MS


# ---------------------------------------------------------------------------
# resolve_ipv4 - real UDP loopback fake DNS server, mirroring test_asy_udp_socket.py's own
# AdversarialPeer pattern (a genuine independent socket, not a mock of UDPSocket).
# ---------------------------------------------------------------------------


class _Clocked:
    # A module stand-in for the fake server's waits: a DrivenTime with sleeps replaces its `time` and `asyncio`.
    def __init__(self) -> None:
        self.time = time
        self.asyncio = asyncio


_SERVER_CLOCK = _Clocked()  # the real modules, but inside a cancel sweep's block


class _FakeDNSServer:
    def __init__(self, host: str, port: int) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(_resolved(host, port))
        self.sock.setblocking(False)
        self.received: list[bytes] = []

    async def answer_once(self, build_response: "Callable[[bytes], bytes | None]", timeout_ms: int = _FAKE_SERVER_WAIT_MS) -> None:
        # Waits for one query, records it, then replies with build_response(query).
        # Checks each event's mask: poll.ipoll() returns the poll object itself, always truthy
        # (extmod/modselect.c:583-594, v1.29.0).
        poller = select.poll()
        poller.register(self.sock, select.POLLIN)
        t0 = _SERVER_CLOCK.time.ticks_ms()
        query: bytes | None = None
        addr: tuple[str, int] | None = None
        while query is None:
            if time.ticks_diff(_SERVER_CLOCK.time.ticks_ms(), t0) > timeout_ms:
                raise OSError("_FakeDNSServer.answer_once() timed out waiting for a query")
            readable = any(event & select.POLLIN for _fd, event in poller.ipoll(0))
            if readable:
                try:
                    query, addr = self.sock.recvfrom(512)  # type: ignore[assignment]  # AF_INET only, see asy_udp_socket.py
                except OSError as e:
                    if e.errno != errno.EAGAIN:  # only a wake-up with nothing to read is expected; anything else is the rig failing
                        raise
            if query is None:
                await _SERVER_CLOCK.asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)
        self.received.append(query)
        response = build_response(query)
        if response is not None:
            assert addr is not None  # always paired with query by a successful recvfrom() above
            self.sock.sendto(response, addr)

    def close(self) -> None:
        self.sock.close()


def test_resolve_ipv4_success_via_a_real_fake_dns_server() -> None:
    port = _make_port()

    async def scenario() -> "str | None":
        server = _FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("10.20.30.40"), ancount=1)))
            result = await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), timeout_ms=_REPLY_TIMEOUT_MS, tries=1)
            await responder
            return result
        finally:
            server.close()

    with redirect_udp_port(asy_dns_client, _DNS_PORT, port):
        assert run(scenario()) == "10.20.30.40"


def test_resolve_ipv4_no_server_reachable_returns_none() -> None:
    port = _make_port()  # nobody listens here: the query is sent and nothing answers

    async def scenario() -> "str | None":
        return await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), timeout_ms=_NO_REPLY_TIMEOUT_MS, tries=1)

    with redirect_udp_port(asy_dns_client, _DNS_PORT, port):
        assert run(scenario()) is None


def test_resolve_ipv4_garbage_reply_returns_none_not_an_exception() -> None:
    port = _make_port()

    async def scenario() -> "str | None":
        server = _FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda _q: b"\x00\x01not-a-real-dns-reply-at-all"))
            result = await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), timeout_ms=_BAD_REPLY_TIMEOUT_MS, tries=1)
            await responder
            return result
        finally:
            server.close()

    with redirect_udp_port(asy_dns_client, _DNS_PORT, port):
        assert run(scenario()) is None


def test_resolve_ipv4_tries_the_callers_servers_in_order() -> None:
    port = _make_port()
    # 10.255.255.254 is never a local interface address in this environment (same deterministic
    # unroutable address test_asy_udp_socket.py's own unbindable_addr() uses).
    unreachable_ip = "10.255.255.254"

    async def scenario() -> "str | None":
        server = _FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("172.16.0.9"), ancount=1)))
            result = await resolve_ipv4("pool.ntp.org", dns_servers=(unreachable_ip, _HOST), timeout_ms=_FALLBACK_TIMEOUT_MS, tries=1)
            await responder
            return result
        finally:
            server.close()

    # The unroutable first server times out (or fails to connect) and the second, the fake server, answers.
    with redirect_udp_port(asy_dns_client, _DNS_PORT, port) as redirect:
        assert run(scenario()) == "172.16.0.9"
    assert redirect.constructed == 2


def test_resolve_ipv4_skips_unset_and_malformed_dns_server_entries() -> None:
    port = _make_port()

    async def scenario() -> "str | None":
        server = _FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("192.0.2.99"), ancount=1)))
            # "0.0.0.0" (DHCP-unset sentinel), "" (empty), and a non-numeric hostname are all
            # skipped without a network attempt, before the one real server.
            result = await resolve_ipv4("pool.ntp.org", dns_servers=("0.0.0.0", "", "not-an-ip", _HOST), timeout_ms=_FALLBACK_TIMEOUT_MS, tries=1)
            await responder
            return result
        finally:
            server.close()

    with redirect_udp_port(asy_dns_client, _DNS_PORT, port) as redirect:
        assert run(scenario()) == "192.0.2.99"
    assert redirect.constructed == 1  # the skipped entries open nothing


def test_resolve_ipv4_with_no_servers_returns_none_and_opens_no_socket() -> None:
    # The resolver has no built-in server: an empty list is a total failure that touches no network.
    async def scenario() -> "str | None":
        return await resolve_ipv4("pool.ntp.org", dns_servers=(), timeout_ms=_NO_REPLY_TIMEOUT_MS, tries=1)

    with redirect_udp_port(asy_dns_client, _DNS_PORT, _make_port()) as redirect:
        assert run(scenario()) is None  # nothing was asked
    assert redirect.constructed == 0


class _RaisingOsModule:
    def urandom(self, _n: int) -> bytes:  # asy_dns_client.py calls os.urandom(2) positionally
        raise MemoryError("simulated allocation failure")


def test_resolve_ipv4_memoryerror_building_the_query_prints_its_text_at_level_1_and_answers_none() -> None:
    # The allocation failure's own text goes out through the caller's logger from level 1 up (the memory gates read it),
    # nothing at level 0; nothing is sent.
    original_os = asy_dns_client.os
    asy_dns_client.os = _RaisingOsModule()  # type: ignore[assignment]
    try:
        for level in (0, 1):
            pr = _make_pr()
            pr.set_level(level)
            with record_prints() as recorder:
                result = run(resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), timeout_ms=50, tries=1, logger=pr))
            assert result is None
            assert len(recorder.lines) == level, recorder.lines
    finally:
        asy_dns_client.os = original_os
    assert recorder.lines[0][0] == "DNSTEST", recorder.lines
    assert "simulated allocation failure" in recorder.text(), recorder.lines


def test_resolve_ipv4_hands_its_logger_to_each_socket() -> None:
    pr = _make_pr()
    with redirect_udp_port(asy_dns_client, _DNS_PORT, _make_port()) as redirect:
        run(resolve_ipv4("pool.ntp.org", dns_servers=(_HOST, _HOST), timeout_ms=_NO_REPLY_TIMEOUT_MS, tries=1, logger=pr))
    assert redirect.loggers == [pr, pr], redirect.loggers


def test_resolve_ipv4_overlong_dns_label_returns_none_not_an_exception() -> None:
    # A label over 63 octets cannot come from the NTPHost PUT (hostName shape); resolve_ipv4() is public and
    # refuses it itself (RFC 1035 SS3.1), before any socket.
    for host in ("a" * 64, "a" * 300, "pool." + "a" * 64 + ".org"):
        with redirect_udp_port(asy_dns_client, _DNS_PORT, _make_port()) as redirect:
            result = run(resolve_ipv4(host, dns_servers=(_HOST,), timeout_ms=50, tries=1))
        assert result is None, host
        assert redirect.constructed == 0, host


def test_resolve_ipv4_parse_response_raising_bounds_error_returns_none() -> None:
    # _parse_response()'s bounds checks are careful enough that no crafted malformed reply has ever been
    # found to reach this IndexError/ValueError guard through real bytes - faked directly here to prove
    # resolve_ipv4() itself degrades cleanly, moving on or returning None, if one ever did.
    original_parse = asy_dns_client._parse_response

    # rsp/query keep their names: this double is assigned onto asy_dns_client._parse_response,
    # so mypy checks its parameter NAMES against the real function's (an underscore prefix is
    # a hard [assignment] error). Both are unused by design - it raises before reading them.
    def raising_parse(rsp: "bytes | bytearray", query: "bytes | bytearray") -> "str | None":
        raise IndexError("simulated residual bounds-math failure")

    asy_dns_client._parse_response = raising_parse
    port = _make_port()

    async def scenario() -> "str | None":
        server = _FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("10.20.30.40"), ancount=1)))
            result = await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), timeout_ms=_REPLY_TIMEOUT_MS, tries=1)
            await responder
            return result
        finally:
            server.close()

    try:
        with redirect_udp_port(asy_dns_client, _DNS_PORT, port):
            result = run(scenario())
    finally:
        asy_dns_client._parse_response = original_parse
    assert result is None  # degrades cleanly instead of propagating the exception


def test_resolve_ipv4_cname_chain_end_to_end() -> None:
    port = _make_port()

    def cname_then_a(query: bytes) -> bytes:
        answers = _cname_answer(b"\xc0\x2a") + _a_answer("203.0.113.77", name_ptr=b"\xc0\x2a")
        return _make_response(query, answers, ancount=2)

    async def scenario() -> "str | None":
        server = _FakeDNSServer(_HOST, port)
        try:
            responder = asyncio.create_task(server.answer_once(cname_then_a))
            result = await resolve_ipv4("time.example.org", dns_servers=(_HOST,), timeout_ms=_CNAME_REPLY_TIMEOUT_MS, tries=1)
            await responder
            return result
        finally:
            server.close()

    with redirect_udp_port(asy_dns_client, _DNS_PORT, port):
        assert run(scenario()) == "203.0.113.77"


# ---------------------------------------------------------------------------
# resolve_ipv4 - cancelled at each await: the socket it opened is torn down on every path
# ---------------------------------------------------------------------------


class _SweptResolve:
    # One sweep count's fixture: a fresh fake server answering once, and the lookup's answer once it completed.
    def __init__(self, server: _FakeDNSServer, responder: "asyncio.Task[None]") -> None:
        self.server = server
        self.responder = responder
        self.result: str | None = None


def test_cancelling_a_resolve_at_each_await_leaves_no_socket_open() -> None:
    # Driven 1 ms turns, shorter than the server's and the socket's poll sleeps, so each wait is a cancel point. The
    # sockets are real loopback descriptors, so the socket's own poll stays real (the hang rule concerns non-fd objects).
    port = _make_port()
    ledger = SocketLedger(asy_udp_socket)
    built: list[_SweptResolve] = []
    received: list[int] = []

    async def build() -> _SweptResolve:
        server = _FakeDNSServer(_HOST, port)
        responder = asyncio.create_task(server.answer_once(lambda q: _make_response(q, _a_answer("10.20.30.42"), ancount=1)))
        built.append(_SweptResolve(server, responder))
        return built[-1]

    async def start(swept: _SweptResolve) -> None:
        swept.result = await resolve_ipv4("pool.ntp.org", dns_servers=(_HOST,), timeout_ms=_REPLY_TIMEOUT_MS, tries=1)

    def invariants(swept: _SweptResolve) -> None:
        ledger.assert_closed()
        received.append(len(swept.server.received))

    async def teardown(swept: _SweptResolve) -> None:
        swept.responder.cancel()
        try:
            await swept.responder
        except asyncio.CancelledError:
            pass
        swept.server.close()

    with DrivenTime(asy_udp_socket, _SERVER_CLOCK, sleeps=True) as clock, ledger, redirect_udp_port(asy_dns_client, _DNS_PORT, port):
        counts = cancel_at_each_await(build, start, invariants, turn=lambda: clock.elapse(1), teardown=teardown)
        assert clock.wakes() == [], clock.wakes()
    assert built[-1].result == "10.20.30.42"
    assert len(received) == counts
    assert (received[0], received[-1]) == (0, 1), received  # cancelled before the query left, and while its reply was awaited


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
