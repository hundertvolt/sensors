import asyncio
import socket
import time

from asy_udp_socket import AsyUDPSocket
from captive_dns import DNSQuery, DNSServer, _ipv4_to_int
from print_log import PrintLog, PrintLogHistory

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_pr(level: int | None = None) -> PrintLogHistory:  # a fresh, independent logger per test/DNSQuery
    return PrintLogHistory(level=level, name="TESTDNS")


_next_port = 52000


def make_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


def resolve_addr(host: str, port: int) -> tuple[str, int]:
    # This project's MicroPython Unix-port "standard" build rejects a plain (host, port) tuple in
    # bind()/sendto() with "TypeError: object with buffer protocol required" - a known Unix-port-
    # only limitation (micropython/micropython#6924), not present on the real rp2 target. Tests
    # work around it the same way tests/test_asy_udp_socket.py does: resolve first.
    return socket.getaddrinfo(host, port)[0][-1]  # type: ignore[return-value]


def make_query(labels: list[str], query_id: bytes = b"\x12\x34") -> bytes:
    # A minimal, well-formed standard-query datagram: 12-byte header + length-prefixed labels +
    # QTYPE=A/QCLASS=IN, matching what DNSQuery.__init__ expects (RFC 1035 section 4.1.1/4.1.2).
    question = b"".join(bytes([len(label)]) + label.encode("ascii") for label in labels)
    question += b"\x00\x00\x01\x00\x01"
    header = query_id + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    return header + question


def malformed_query_cases() -> list[bytes]:
    # The 11 shapes found reachable from a truncated/malformed real UDP datagram (see BACKLOG.md):
    # too short for the opcode byte, too short for the question section, a length byte with
    # nothing following, a label truncated mid-way (both by 1 byte and entirely), an oversized
    # (attack-style) label-length claim, a label with an invalid UTF-8 byte, and a validly-
    # terminated label with QTYPE/QCLASS missing entirely.
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"  # standard query, QDCOUNT=1
    return [
        b"",
        b"\x00",
        b"\x00\x00",
        b"\x00\x00\x01",  # 3 bytes, opcode bits already say "standard query" but len < 13
        header,  # exactly 12 bytes - no question section at all
        header + b"\x05",  # a length byte promising 5 more bytes that never arrive
        header + b"\x01a",  # one label started, then truncated before its terminator
        header + b"\x03ab",  # a label claiming 3 bytes, truncated by exactly 1 byte (off-by-one)
        header + b"\xff",  # a 255-byte label claim (max byte value) with nothing following
        header + b"\x01\xff\x00",  # a 1-byte label containing an invalid UTF-8 byte
        header + b"\x01a\x00",  # valid label + terminator, but QTYPE/QCLASS never arrive
    ]


# ---------------------------------------------------------------------------
# _ipv4_to_int: pure dotted-quad -> int|None conversion used for subnet-membership math. Never
# raises for a malformed-but-str value (isdigit()-check style, matching asy_dns_client.py's
# _is_ipv4_literal()) - only a wrong-typed (non-str) value still raises, via ip.split().
# ---------------------------------------------------------------------------


def test_ipv4_to_int_valid() -> None:
    assert _ipv4_to_int("0.0.0.0") == 0
    assert _ipv4_to_int("255.255.255.255") == 0xFFFFFFFF
    assert _ipv4_to_int("192.168.4.1") == (192 << 24) | (168 << 16) | (4 << 8) | 1


def test_ipv4_to_int_rejects_wrong_octet_count() -> None:
    for bad in ("1.2.3", "1.2.3.4.5", "", "1.2.3.4."):
        assert _ipv4_to_int(bad) is None


def test_ipv4_to_int_rejects_out_of_range_octet() -> None:
    # A previously-silent gap: an out-of-range octet used to shift bits past its own byte position
    # instead of being rejected, risking a false subnet match rather than a clean "invalid" signal.
    for bad in ("256.0.0.0", "1.2.3.999", "-1.2.3.4"):
        assert _ipv4_to_int(bad) is None


def test_ipv4_to_int_rejects_non_numeric_octet() -> None:
    assert _ipv4_to_int("a.b.c.d") is None


def test_ipv4_to_int_rejects_single_invalid_parameter_type() -> None:
    # Real callers only ever pass str (network.WLAN.ifconfig()'s own return type, or a raw
    # sockaddr's addr[0]), but this is a module-level function - a wrongly-typed value must raise
    # one of the exact types every caller in this file already guards against, not something else.
    for bad in (None, 123, 1.5, [1, 2, 3, 4], b"1.2.3.4", ("1", "2", "3", "4")):
        try:
            _ipv4_to_int(bad)  # type: ignore[arg-type]
            raise AssertionError(f"expected an exception for {bad!r}")
        except (TypeError, AttributeError):
            pass


def test_ipv4_to_int_rejects_multiple_simultaneous_fault_recombinations() -> None:
    # Combines more than one fault within the same value - wrong octet count, out-of-range, and
    # non-numeric octets all at once - to prove the guard doesn't depend on faults appearing alone.
    for bad in ("300.-5.abc.999.1", "abc.def", "999.999", "1.2.a.999.-1"):
        assert _ipv4_to_int(bad) is None


# ---------------------------------------------------------------------------
# DNSQuery: raw datagram parsing.
# ---------------------------------------------------------------------------


def test_dns_query_parses_single_and_multi_label_domain() -> None:
    assert DNSQuery(make_query(["example"]), make_pr()).domain == "example."
    assert DNSQuery(make_query(["a", "io"]), make_pr()).domain == "a.io."


def test_dns_query_non_standard_opcode_yields_empty_domain() -> None:
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # opcode bits = 1 (not a standard query)
    assert DNSQuery(bytes(data), make_pr()).domain == ""


def test_dns_query_malformed_or_truncated_data_yields_empty_domain() -> None:
    for data in malformed_query_cases():
        assert DNSQuery(data, make_pr()).domain == ""  # never raises, degrades to the "don't respond" sentinel


def test_dns_query_reuses_the_given_logger_instead_of_constructing_its_own() -> None:
    # DNSQuery is constructed fresh per incoming request (see DNSServer.run()) - it must reuse the
    # caller's own logger identity/history, not get an independent PrintLogHistory of its own.
    pr = make_pr()
    dns = DNSQuery(make_query(["a", "io"]), pr)
    assert dns.pr is pr


# ---------------------------------------------------------------------------
# DNSQuery.response(): packet construction.
# ---------------------------------------------------------------------------


def test_response_builds_expected_packet_for_valid_domain() -> None:
    query = make_query(["a", "io"])
    packet = DNSQuery(query, make_pr()).response("192.168.4.1")
    assert packet is not None
    assert packet[:2] == query[:2]  # echoed transaction ID
    assert packet[2:4] == b"\x81\x80"  # standard response, recursion available
    assert packet[4:6] == b"\x00\x01"  # QDCOUNT=1
    assert packet[6:8] == b"\x00\x01"  # ANCOUNT=1
    assert packet[8:12] == b"\x00\x00\x00\x00"  # NSCOUNT, ARCOUNT
    question_len = len(query) - 12
    assert packet[12 : 12 + question_len] == query[12:]  # the one question, echoed
    offset = 12 + question_len
    assert packet[offset : offset + 2] == b"\xc0\x0c"  # compression pointer to the question name
    assert packet[offset + 2 : offset + 12] == b"\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"
    assert packet[offset + 12 : offset + 16] == bytes([192, 168, 4, 1])
    assert len(packet) == offset + 16


def test_response_ignores_trailing_data_after_the_question_and_hardcodes_counts() -> None:
    # A real-world shape: a query with a single question PLUS trailing data this class was never
    # meant to parse (most commonly a real client's EDNS0 OPT record in the additional section, or
    # - equally unhandled here - a second question). Before the _question_end fix, self.data[12:]
    # echoed that trailing data straight into what the header declares is pure question content,
    # while ANCOUNT was set equal to the *original* QDCOUNT rather than the one record actually
    # appended - producing a packet whose declared header counts didn't match its real byte layout
    # (a compliant parser, having read exactly the declared question(s), would try to parse the
    # leftover trailing bytes as the start of the answer section instead of the real answer, which
    # sits right after them).
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x01"  # QDCOUNT=1, ARCOUNT=1 (EDNS0)
    question = b"\x01a\x02io\x00\x00\x01\x00\x01"  # a.io, QTYPE=A, QCLASS=IN
    opt_record = b"\x00\x00\x29\x10\x00\x00\x00\x00\x00\x00\x00"  # root name, TYPE=41 (OPT), RDLENGTH=0
    query = header + question + opt_record

    dns = DNSQuery(query, make_pr())
    assert dns.domain == "a.io."
    packet = dns.response("192.168.4.1")
    assert packet is not None
    assert packet[4:6] == b"\x00\x01"  # QDCOUNT=1, not the original header's QDCOUNT
    assert packet[6:8] == b"\x00\x01"  # ANCOUNT=1 - matches the one record actually appended
    assert packet[8:12] == b"\x00\x00\x00\x00"  # NSCOUNT=0, ARCOUNT=0 - the OPT record is dropped
    question_len = len(question)
    assert packet[12 : 12 + question_len] == question  # exactly the one question, no OPT bytes
    offset = 12 + question_len
    assert packet[offset : offset + 2] == b"\xc0\x0c"  # the answer immediately follows the question
    assert len(packet) == offset + 16


def test_response_hardcodes_qdcount_even_when_original_header_declares_more_questions() -> None:
    # A query whose header claims QDCOUNT=2: __init__ only ever parses the first question (by
    # design, see its own comments), so the response must declare QDCOUNT=1 - matching the one
    # question it actually echoes - rather than blindly echoing the original header's claim of 2.
    header = b"\x12\x34\x01\x00\x00\x02\x00\x00\x00\x00\x00\x00"  # QDCOUNT=2
    question = b"\x01a\x02io\x00\x00\x01\x00\x01"
    second_question = b"\x01b\x00\x00\x01\x00\x01"
    query = header + question + second_question

    dns = DNSQuery(query, make_pr())
    assert dns.domain == "a.io."
    packet = dns.response("192.168.4.1")
    assert packet is not None
    assert packet[4:6] == b"\x00\x01"  # QDCOUNT=1, not the original header's declared 2
    question_len = len(question)
    assert packet[12 : 12 + question_len] == question  # only the first question, not the second


def test_response_returns_none_for_empty_domain() -> None:
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # non-standard query -> empty domain
    assert DNSQuery(bytes(data), make_pr()).response("192.168.4.1") is None


def test_response_answers_the_root_domain_query_not_indistinguishable_from_a_parse_failure() -> None:
    # Regression test for BACKLOG.md's "root-domain query can't be told apart from a failed parse"
    # entry: a root query (a single zero-length label, ".") parses to the same empty self.domain a
    # malformed/truncated datagram falls back to. Before this fix, response() used `if self.domain:`
    # to decide whether to answer, so both cases returned None - contradicting this module's own
    # docstring claim that every on-subnet query gets an answer. response() now tracks parse success
    # separately, so a genuine root query is answered like any other.
    query = make_query([])  # zero labels -> immediate zero-length terminator, i.e. the root domain
    dns = DNSQuery(query, make_pr())
    assert dns.domain == ""  # still the same empty representation as a parse failure...
    packet = dns.response("192.168.4.1")
    assert packet is not None  # ...but this is a successfully-parsed query, so it gets answered
    assert packet[:2] == query[:2]  # echoed transaction ID
    assert packet[4:6] == b"\x00\x01"  # QDCOUNT=1
    question_len = len(query) - 12
    assert packet[12 : 12 + question_len] == query[12:]  # the root question, echoed verbatim


def test_dns_query_rejects_question_truncated_right_before_qtype_qclass() -> None:
    # Boundary check either side of the QTYPE/QCLASS cutoff: a label + terminator with the full 4
    # trailing bytes present must still parse and answer normally (exact boundary accepted); the
    # same label + terminator with those 4 bytes missing entirely must be treated as malformed
    # (don't respond), not silently echoed as a short, misaligned question - self.data[12:end]
    # would otherwise truncate via ordinary slice semantics instead of raising.
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    complete = header + b"\x01a\x00" + b"\x00\x01\x00\x01"  # QTYPE=A, QCLASS=IN present
    truncated = header + b"\x01a\x00"  # terminator present, QTYPE/QCLASS entirely missing

    complete_query = DNSQuery(complete, make_pr())
    assert complete_query.domain == "a."
    assert complete_query.response("192.168.4.1") is not None

    truncated_query = DNSQuery(truncated, make_pr())
    assert truncated_query.domain == ""
    assert truncated_query.response("192.168.4.1") is None


# ---------------------------------------------------------------------------
# DNSServer: construction.
# ---------------------------------------------------------------------------


def test_dns_server_init_binds_the_standard_dns_port_in_server_mode() -> None:
    server = DNSServer(debug=PrintLog.level_info())
    assert server.udps._addr == ("0.0.0.0", 53)
    assert server.udps._mode == "server"
    assert server.udps.sock is None  # lazy - no real bind attempted at construction


def test_dns_server_uses_in_memory_logging_when_fram_is_none() -> None:
    server = DNSServer()
    assert isinstance(server.pr, PrintLogHistory)


def test_dns_server_logger_is_named_dnssrv() -> None:
    server = DNSServer()
    assert server.pr.name == "DNSSRV"


def test_dns_server_debug_level_is_forwarded_to_the_logger() -> None:
    server = DNSServer(debug=PrintLog.level_err())
    assert server.pr.get_level() == PrintLog.level_err()


def test_dns_server_debug_none_leaves_logger_at_off() -> None:
    server = DNSServer(debug=None)
    assert server.pr.get_level() == PrintLog.level_off()


def test_dns_server_default_logger_is_off() -> None:
    assert DNSServer().pr.get_level() == PrintLog.level_off()


def test_dns_server_get_error_counter_forwards_to_the_real_print_log() -> None:
    server = DNSServer()
    log = run(server.get_error_counter())
    assert log["DNSSRV"]["ErrCount"] == 0


def test_dns_server_get_error_counter_reflects_a_real_logged_error() -> None:
    server = DNSServer()
    run(server.pr.err_s("boom", errno=1))
    log = run(server.get_error_counter())
    assert log["DNSSRV"]["ErrCount"] == 1


# ---------------------------------------------------------------------------
# DNSServer.run(): driven through a controlled fake transport.
#
# DNSServer.udps is always bound via a resolved sockaddr in this Unix-port test build (the same
# workaround resolve_addr() above documents), which makes recvfrom() return an opaque raw sockaddr
# rather than a (host, port) tuple - this environment can never itself produce a real string
# addr[0] for a server-mode socket (confirmed directly; see BACKLOG.md). _FakeUDPS lets the actual
# subnet-membership/malformed-query/error-path branches inside run() be driven for real with
# well-formed (or deliberately bad) (host, port) tuples, while DNSQuery/response() still run
# unmocked. The real-socket test at the bottom of this file covers the genuine raw-sockaddr path.
# ---------------------------------------------------------------------------


class _FakeUDPS:
    def __init__(self, incoming: list[tuple[bytes | None, tuple[str, int] | None]]) -> None:
        self._incoming = list(incoming)
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.sendto_results: list[int | None] = []
        self.disconnect_called = False
        self.disconnect_ok = True  # real AsyUDPSocket.disconnect()'s success return, see Step 6 note
        # One entry per recvfrom() call, for backoff-timing assertions. "Any", not "int": mypy's
        # time.pyi types ticks_ms() as the opaque _TicksMs marker class (deliberately incompatible
        # with plain int to catch raw-arithmetic misuse) - these values are only ever fed back into
        # time.ticks_diff(), never used as plain ints.
        self.recv_call_times_ms: list[Any] = []

    async def recvfrom(self, bufsize: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        self.recv_call_times_ms.append(time.ticks_ms())
        if self._incoming:
            data, addr = self._incoming.pop(0)
            await asyncio.sleep(0)
            return data, addr
        await asyncio.sleep(3600)  # simulates "no more traffic" - cancellable, never busy-loops
        return None, None

    async def sendto(self, packet: bytes, addr: tuple[str, int], timeout_ms: int = -1) -> int | None:
        result = self.sendto_results.pop(0) if self.sendto_results else len(packet)
        self.sent.append((packet, addr))
        return result

    async def disconnect(self) -> bool:
        self.disconnect_called = True
        return self.disconnect_ok


async def _wait_until(predicate: "Any", timeout_ms: int = 1000) -> bool:
    t0 = time.ticks_ms()
    while not predicate():
        if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
            return False
        await asyncio.sleep_ms(10)
    return True


async def _cancel(task: "Any") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def test_run_answers_on_subnet_request() -> None:
    fake = _FakeUDPS([(make_query(["a", "io"]), ("127.0.0.5", 5000))])

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1)
            return fake.sent
        finally:
            await _cancel(task)

    sent = run(scenario())
    assert len(sent) == 1
    packet, addr = sent[0]
    assert addr == ("127.0.0.5", 5000)
    assert packet[:2] == b"\x12\x34"
    assert packet[-4:] == bytes([127, 0, 0, 1])


def test_run_ignores_off_subnet_request_then_answers_next_on_subnet_request() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (query, ("10.0.0.9", 5000)),  # off the configured 127.0.0.0/8 subnet
            (query, ("127.0.0.5", 5001)),  # on-subnet
        ]
    )

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1)
            await asyncio.sleep_ms(20)  # give a stray second reply a chance to show up, if any
            return fake.sent
        finally:
            await _cancel(task)

    sent = run(scenario())
    assert len(sent) == 1  # only the on-subnet request was ever answered
    assert sent[0][1] == ("127.0.0.5", 5001)


def test_run_ignores_source_address_that_is_not_a_valid_ipv4_string() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (query, ("not-an-ip", 5000)),
            (query, ("127.0.0.5", 5001)),
        ]
    )

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1)
            return fake.sent
        finally:
            await _cancel(task)

    sent = run(scenario())
    assert len(sent) == 1
    assert sent[0][1] == ("127.0.0.5", 5001)


def test_run_ignores_malformed_query_without_stalling() -> None:
    fake = _FakeUDPS(
        [
            (b"\x00\x00", ("127.0.0.5", 5000)),  # too short to parse
            (make_query(["a", "io"]), ("127.0.0.5", 5001)),
        ]
    )

    async def scenario() -> tuple[list[tuple[bytes, tuple[str, int]]], int]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        t0 = time.ticks_ms()
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1)
            return fake.sent, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await _cancel(task)

    sent, elapsed_ms = run(scenario())
    assert len(sent) == 1
    assert sent[0][1] == ("127.0.0.5", 5001)
    # A regression here (the malformed DNSQuery raising into run()'s broad except-Exception
    # handler) would incur its 3s backoff before answering the next request - well under that
    # margin proves the guard is actually what's preventing it, not just fast test scheduling.
    assert elapsed_ms < 1000


def test_run_rejects_invalid_server_ip_or_netmask_without_raising() -> None:
    server = DNSServer()

    async def scenario() -> None:
        await server.run("not-an-ip", "255.255.255.0")

    run(scenario())  # returns cleanly before ever touching udps - must not raise
    assert server.udps.sock is None


def test_run_rejects_invalid_server_ip_or_netmask_logs_a_persisted_error() -> None:
    server = DNSServer(debug=PrintLog.level_err())

    async def scenario() -> None:
        await server.run("not-an-ip", "255.255.255.0")

    run(scenario())
    assert server.pr.err_count == 1


def test_run_cancellation_disconnects_cleanly() -> None:
    fake = _FakeUDPS([])

    async def scenario() -> None:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(20)  # let it reach the pending recvfrom()
        await _cancel(task)  # run() catches CancelledError internally and returns normally

    run(scenario())
    assert fake.disconnect_called is True


def test_run_continues_after_sendto_reports_failure() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (query, ("127.0.0.5", 5000)),
            (query, ("127.0.0.5", 5001)),
        ]
    )
    fake.sendto_results = [None]  # first reply "fails", matching sendto()'s documented None sentinel

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 2)
            return fake.sent
        finally:
            await _cancel(task)

    sent = run(scenario())
    assert len(sent) == 2  # the "failed" first send didn't crash or stall the loop
    assert sent[1][1] == ("127.0.0.5", 5001)


def test_run_sendto_failure_logs_a_persisted_warning() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS([(query, ("127.0.0.5", 5000))])
    fake.sendto_results = [None]

    async def scenario() -> None:
        server = DNSServer(debug=PrintLog.level_warn())
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1)
            assert server.pr.err_count == 1
        finally:
            await _cancel(task)

    run(scenario())


def test_run_invalid_recvfrom_data_logs_a_persisted_warning() -> None:
    fake = _FakeUDPS([(None, None)])

    async def scenario() -> None:
        server = DNSServer(debug=PrintLog.level_warn())
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: server.pr.err_count >= 1)
        finally:
            await _cancel(task)

    run(scenario())


# ---------------------------------------------------------------------------
# One genuine end-to-end pass over a real loopback socket - proves DNSServer.run() actually binds,
# receives, and replies without crashing through AsyUDPSocket for real, not just via _FakeUDPS.
# ---------------------------------------------------------------------------


def test_run_handles_real_loopback_traffic_without_crashing() -> None:
    server_addr = resolve_addr("127.0.0.1", make_port())
    peer_addr = resolve_addr("127.0.0.1", make_port())

    async def scenario() -> bool:
        server = DNSServer()
        server.udps = AsyUDPSocket(server_addr, mode="server")
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer.bind(peer_addr)
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            await asyncio.sleep_ms(50)  # let the server bind
            peer.sendto(make_query(["a", "io"]), server_addr)
            await asyncio.sleep_ms(200)
            return not task.done()  # still running - no uncaught exception killed it
        finally:
            peer.close()
            await _cancel(task)

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# _ipv4_to_int: parameter-type configuration matrix (beyond the malformed-but-string cases above).
# ---------------------------------------------------------------------------


def _bad_ipv4_values() -> "list[Any]":
    # Every distinct fault shape a caller could plausibly hand to something expecting a dotted-quad
    # string: wrong Python type, and every malformed-string shape _ipv4_to_int is known to reject.
    return [
        None,
        123,
        1.5,
        [192, 168, 4, 1],
        b"127.0.0.1",
        "",
        "not-an-ip",
        "1.2.3",
        "1.2.3.4.5",
        "256.0.0.1",
        "1.2.3.-1",
        "a.b.c.d",
    ]


# ---------------------------------------------------------------------------
# DNSServer.run(): server_ip/netmask startup-configuration matrix. Every invalid case asserts
# run() returns without raising and never attempts to bind (sock stays None) - exercising
# _ipv4_to_int's never-raises None-check at the top of run() without a live socket (a non-str
# server_ip/netmask still raises via _ipv4_to_int's own ip.split(), same as before). The
# valid-configuration case does need a live loop iteration, so it goes through the fake transport
# and a real cancellable task, like the rest of this file's run() tests.
# ---------------------------------------------------------------------------


def _run_once_expect_clean_return(server: "DNSServer", server_ip: str, netmask: str) -> None:
    async def scenario() -> None:
        await server.run(server_ip, netmask)

    run(scenario())


def _run_briefly_and_cancel(server: "DNSServer", server_ip: str, netmask: str, wait_ms: int = 20) -> None:
    async def scenario() -> None:
        task = asyncio.create_task(server.run(server_ip, netmask))
        await asyncio.sleep_ms(wait_ms)
        await _cancel(task)

    run(scenario())


def test_run_accepts_all_valid_server_ip_netmask_configurations() -> None:
    for server_ip, netmask in (
        ("192.168.4.1", "255.255.255.0"),
        ("0.0.0.0", "0.0.0.0"),
        ("255.255.255.255", "255.255.255.255"),
        ("127.0.0.1", "255.0.0.0"),
    ):
        fake = _FakeUDPS([])
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        _run_briefly_and_cancel(server, server_ip, netmask)
        assert fake.disconnect_called is True  # reached the main loop, not the early-return path


def test_run_rejects_single_invalid_server_ip_parameter() -> None:
    for bad_ip in _bad_ipv4_values():
        if not isinstance(bad_ip, str):
            continue  # a non-str server_ip raises via _ipv4_to_int's own ip.split() - not this test's concern
        server = DNSServer()
        _run_once_expect_clean_return(server, bad_ip, "255.255.255.0")
        assert server.udps.sock is None  # never attempted to bind


def test_run_rejects_single_invalid_netmask_parameter() -> None:
    for bad_netmask in _bad_ipv4_values():
        if not isinstance(bad_netmask, str):
            continue
        server = DNSServer()
        _run_once_expect_clean_return(server, "192.168.4.1", bad_netmask)
        assert server.udps.sock is None


def test_run_rejects_multiple_simultaneous_invalid_server_ip_and_netmask_recombinations() -> None:
    # Both parameters invalid at once (but still str-typed - see the two tests above for the
    # non-str case), in several distinct malformed-string shapes - proves the guard doesn't depend
    # on only one parameter being bad at a time.
    for bad_ip, bad_netmask in (
        ("300.1.1.1", "abc"),
        ("1.2.3", "4.5.6.7.8"),
        ("", ""),
        ("not-an-ip", "255.0.0.0"),
    ):
        server = DNSServer()
        _run_once_expect_clean_return(server, bad_ip, bad_netmask)
        assert server.udps.sock is None


def test_run_rejects_non_str_server_ip_or_netmask() -> None:
    # A non-str value still raises (via _ipv4_to_int's own ip.split()) - this class's public
    # `str`-typed signature relies on that, same as asy_dns_client.py's _is_ipv4_literal() callers.
    for bad_ip, bad_netmask in ((None, "255.0.0.0"), ("192.168.4.1", 123), ([1, 2, 3, 4], b"255.0.0.0")):
        server = DNSServer()

        async def scenario(srv: "DNSServer" = server, ip: "Any" = bad_ip, netmask: "Any" = bad_netmask) -> None:
            await srv.run(ip, netmask)

        try:
            run(scenario())
            raise AssertionError(f"expected an exception for {bad_ip!r}, {bad_netmask!r}")
        except (TypeError, AttributeError):
            pass


# ---------------------------------------------------------------------------
# DNSQuery.__init__: data parameter configurations.
# ---------------------------------------------------------------------------


def test_dns_query_init_accepts_all_valid_data_configurations() -> None:
    assert DNSQuery(make_query(["single"]), make_pr()).domain == "single."
    assert DNSQuery(make_query(["multi", "label", "example"]), make_pr()).domain == "multi.label.example."


def _bad_dns_query_data_values() -> "list[Any]":
    # Wrong-type shapes for data, on top of the malformed-but-bytes shapes malformed_query_cases()
    # already covers. The real caller (run()) only ever passes bytes, but this constructor is
    # public and shouldn't rely on that discipline holding for every future/test caller.
    return [None, "a string, not bytes", 12345, 1.5, [1, 2, 3, 4], (1, 2, 3, 4)]


def test_dns_query_init_rejects_single_invalid_data_parameter_without_raising() -> None:
    for bad_data in _bad_dns_query_data_values():
        assert DNSQuery(bad_data, make_pr()).domain == ""


def test_dns_query_init_rejects_list_shaped_data_that_reaches_decode() -> None:
    # A sequence long enough to survive both integer-index lookups (data[2] and data[12]) but fail
    # specifically at self.domain += data[...].decode("utf-8") - a list slice has no .decode
    # method, exercising the AttributeError arm distinctly from the TypeError/IndexError arms the
    # shorter values above trigger.
    bad_data = [0] * 20
    bad_data[12] = 3  # claims a 3-byte label
    assert DNSQuery(bad_data, make_pr()).domain == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DNSQuery.response(): ip-parameter configuration matrix.
# ---------------------------------------------------------------------------


def test_response_accepts_edge_valid_ip_configurations() -> None:
    query = make_query(["a", "io"])
    for ip in ("0.0.0.0", "255.255.255.255", "10.0.0.1"):
        packet = DNSQuery(query, make_pr()).response(ip)
        assert packet is not None
        assert packet[-4:] == bytes(int(o) for o in ip.split("."))


def test_response_rejects_single_invalid_ip_parameter_without_raising() -> None:
    query = make_query(["a", "io"])
    for bad_ip in _bad_ipv4_values():
        if not isinstance(bad_ip, str):
            continue  # a non-str ip raises via _ipv4_to_int's own ip.split() - see the dedicated test below
        assert DNSQuery(query, make_pr()).response(bad_ip) is None


def test_response_rejects_non_str_ip_parameter() -> None:
    query = make_query(["a", "io"])
    for bad_ip in (None, 123, [1, 2, 3, 4], b"127.0.0.1"):
        try:
            DNSQuery(query, make_pr()).response(bad_ip)  # type: ignore[arg-type]
            raise AssertionError(f"expected an exception for {bad_ip!r}")
        except (TypeError, AttributeError):
            pass


def test_response_rejects_invalid_ip_combined_with_empty_domain_state() -> None:
    # domain=="" already short-circuits to None before ip is ever inspected - an invalid ip
    # combined with an already-invalid (empty-domain) object state must still just return None,
    # even for a wrong-typed ip that would otherwise raise via _ipv4_to_int.
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # non-standard opcode -> empty domain
    for bad_ip in _bad_ipv4_values():
        assert DNSQuery(bytes(data), make_pr()).response(bad_ip) is None


# ---------------------------------------------------------------------------
# Integration: DNSServer driven through a real AsyUDPSocket end to end (not the fake transport
# above) - exercises the whole pipeline against the actual dependency it imports, including that
# dependency's own real fault-handling contract (documented in asy_udp_socket.py's module
# docstring: every public I/O method returns its None-shaped sentinel rather than raising).
# ---------------------------------------------------------------------------


# A real server socket in this Unix-port test build is always bound via a resolved sockaddr (see
# resolve_addr()'s and _FakeUDPS's own comments above), which makes recvfrom() hand back an opaque
# raw sockaddr rather than a (host, port) tuple - so addr[0] can never be a real dotted-quad string
# here, and run()'s subnet check (correctly) rejects every real packet as off-subnet/malformed
# before a reply is ever sent. That's why the tests below assert liveness/rebind behavior against a
# real socket rather than reply content - reply *content* is already fully covered by
# test_response_builds_expected_packet_for_valid_domain, and the fake-transport tests above already
# drive the subnet-accept path for real with well-formed (host, port) tuples.


def test_run_reuses_same_dns_server_instance_across_multiple_hotspot_cycles() -> None:
    # Mirrors asy_wifi_service.py's real usage (AsyConnTime.__init__ constructs exactly one
    # self.dns_server = DNSServer(...), reused across every hotspot activation): one DNSServer
    # instance constructed once, with run() started, cancelled, and started again across repeated
    # hotspot activations - only safe because
    # AsyUDPSocket.disconnect() fully resets connected/sock state for _connect()'s next attempt.
    server_addr = resolve_addr("127.0.0.1", make_port())
    server = DNSServer()
    server.udps = AsyUDPSocket(server_addr, mode="server")

    async def one_cycle() -> bool:
        peer_addr = resolve_addr("127.0.0.1", make_port())
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer.bind(peer_addr)
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            await asyncio.sleep_ms(50)  # let it bind
            assert server.udps.sock is not None  # real bind succeeded this cycle
            peer.sendto(make_query(["cycle"]), server_addr)
            await asyncio.sleep_ms(100)
            return not task.done()  # still alive - no uncaught exception killed it
        finally:
            peer.close()
            await _cancel(task)

    assert run(one_cycle()) is True
    assert server.udps.sock is None  # first cycle's disconnect() really tore it down
    assert run(one_cycle()) is True  # second activation, on the exact same instance, rebinds fine
    assert server.udps.sock is None


def test_run_real_socket_survives_a_burst_of_consecutive_malformed_datagrams() -> None:
    # Real-world incident shape: a burst of bad traffic (not just one bad packet), sent over the
    # actual loopback network stack (not just handed to a fake transport) - proves no cumulative
    # state corruption or crash across repeated real, malformed datagrams.
    server_addr = resolve_addr("127.0.0.1", make_port())
    peer_addr = resolve_addr("127.0.0.1", make_port())

    async def scenario() -> bool:
        server = DNSServer()
        server.udps = AsyUDPSocket(server_addr, mode="server")
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer.bind(peer_addr)
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            await asyncio.sleep_ms(50)
            for bad in malformed_query_cases():
                peer.sendto(bad, server_addr)
            peer.sendto(make_query(["a", "io"]), server_addr)
            await asyncio.sleep_ms(200)
            return not task.done()  # still alive after the whole burst
        finally:
            peer.close()
            await _cancel(task)

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# Integration contract: replicates asy_wifi_service.py's real DNSServer usage exactly. It cannot be
# imported directly here - it depends on network.WLAN and other RP2040-only hardware this
# environment doesn't have. Confirmed directly against asy_wifi_service.py: one DNSServer built
# once in AsyConnTime.__init__, run() started via evtloop.create_task(self.dns_server.run(own_ip,
# own_netmask)), and shut down via a fire-and-forget self.dns_server_task.cancel() that the caller
# never awaits.
# ---------------------------------------------------------------------------


def test_integration_survives_async_connects_fire_and_forget_cancel_pattern() -> None:
    server_addr = resolve_addr("127.0.0.1", make_port())

    async def scenario() -> "DNSServer":
        server = DNSServer()
        server.udps = AsyUDPSocket(server_addr, mode="server")
        evtloop = asyncio.get_event_loop()
        task = evtloop.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(50)  # let it bind and reach the pending recvfrom()
        task.cancel()  # exactly async_connect.py's own pattern - never awaited by the caller
        # Nothing observes `task` from here on, matching the real caller exactly. Only give the
        # event loop a few ticks so the cancelled task's own cleanup actually gets to run, the way
        # it naturally would on a live device between this point and the next scheduler pass.
        for _ in range(10):
            await asyncio.sleep_ms(10)
        return server

    server = run(scenario())
    assert server.udps.sock is None  # cleanup completed on its own; nothing had to await it


# ---------------------------------------------------------------------------
# run()'s catch-all backoff: an unexpected (not malformed-data, not off-subnet) exception from a
# dependency must still degrade to the 3s backoff rather than crash or busy-loop, and must be
# logged as a real, persisted error. This is the one fault category that genuinely cannot be
# produced for real - nothing in the legitimate processing path throws mid-packet - so it's
# simulated with a monkeypatched DNSQuery, matching this project's "mock only what's necessary"
# precedent (mocking a dependency, not the run() logic under test).
# ---------------------------------------------------------------------------


def test_run_backs_off_on_a_genuinely_unexpected_exception_then_recovers() -> None:
    import captive_dns as captive_dns_module

    real_dns_query = captive_dns_module.DNSQuery
    calls = {"n": 0}

    class _FlakyDNSQuery:
        def __init__(self, data: bytes, pr: "Any") -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated unexpected failure")
            self._real = real_dns_query(data, pr)
            self.domain = self._real.domain

        def response(self, ip: str) -> "bytes | None":
            return self._real.response(ip)

    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (query, ("127.0.0.5", 5000)),
            (query, ("127.0.0.5", 5001)),
        ]
    )

    async def scenario() -> "tuple[list[tuple[bytes, tuple[str, int]]], int]":
        captive_dns_module.DNSQuery = _FlakyDNSQuery  # type: ignore[assignment,misc]
        try:
            server = DNSServer(debug=PrintLog.level_err())
            server.udps = fake  # type: ignore[assignment]
            t0 = time.ticks_ms()
            task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
            try:
                assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=5000)
                assert server.pr.err_count == 1  # the flaky first attempt logged a real, persisted error
                return fake.sent, time.ticks_diff(time.ticks_ms(), t0)
            finally:
                await _cancel(task)
        finally:
            captive_dns_module.DNSQuery = real_dns_query  # type: ignore[misc]

    sent, elapsed_ms = run(scenario())
    assert len(sent) == 1
    assert sent[0][1] == ("127.0.0.5", 5001)  # the second, real request got through
    assert elapsed_ms >= 3000  # proves the 3s backoff genuinely ran, unlike the malformed-data path


class _RaisingDisconnectUDPS(_FakeUDPS):
    def __init__(self, exc: BaseException) -> None:
        super().__init__([])
        self._exc = exc

    async def disconnect(self) -> bool:
        self.disconnect_called = True
        raise self._exc


def test_run_disconnect_reporting_a_genuine_exception_logs_a_persisted_error() -> None:
    fake = _RaisingDisconnectUDPS(RuntimeError("simulated disconnect failure"))

    async def scenario() -> None:
        server = DNSServer(debug=PrintLog.level_err())
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(20)
        await _cancel(task)  # disconnect()'s own exception must not escape cancellation either
        assert fake.disconnect_called is True
        assert server.pr.err_count == 1

    run(scenario())  # must not raise despite disconnect() itself failing


# ---------------------------------------------------------------------------
# run()'s recvfrom() empty-result backoff (SPECIFICATION.md Part C.9's cascading-recovery-storm
# convention): a persistently-failing recvfrom() that returns
# (None, None) without ever raising - e.g. a bind() that never actually succeeded - must not spin
# the loop at zero delay (the real end-to-end run measured ~5 wrn_s() lines/second before this fix).
# Distinct from the genuinely-unexpected-exception backoff tested above, which already had its own
# flat 3s pause; this is the normal, no-exception "no data" path, which previously had none at all.
# ---------------------------------------------------------------------------


def test_run_backs_off_with_increasing_delay_on_repeated_empty_recvfrom() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS([(None, None), (None, None), (None, None), (query, ("127.0.0.5", 5000))])

    async def scenario() -> list[int]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=15000)
            return fake.recv_call_times_ms
        finally:
            await _cancel(task)

    call_times = run(scenario())
    # >= 4: 3 empty results + the one that finally returns real data - possibly a 5th call too
    # (run() loops straight back into recvfrom() again after replying, racing this test's own
    # _wait_until poll), which is fine - only the first 3 backoff gaps are this test's concern.
    assert len(call_times) >= 4
    gaps = [time.ticks_diff(call_times[i + 1], call_times[i]) for i in range(3)]
    # gaps[i] is the pause *after* recvfrom() call i's (None, None) result, before call i+1 fires -
    # must grow across consecutive failures, not stay at the previous zero-delay spin.
    assert 400 <= gaps[0] < 800  # ~0.5s initial backoff
    assert 900 <= gaps[1] < 1400  # ~1.0s (doubled)
    assert 1900 <= gaps[2] < 2600  # ~2.0s (doubled again)


def test_run_recv_backoff_resets_after_a_successful_receive() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (None, None),
            (None, None),  # ramps the backoff up
            (query, ("127.0.0.5", 5000)),  # real data received - must reset the backoff
            (None, None),
            (None, None),
        ]
    )

    async def scenario() -> list[int]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.recv_call_times_ms) >= 5, timeout_ms=15000)
            return fake.recv_call_times_ms
        finally:
            await _cancel(task)

    call_times = run(scenario())
    gaps = [time.ticks_diff(call_times[i + 1], call_times[i]) for i in range(4)]
    assert 400 <= gaps[0] < 800  # first empty result -> ~0.5s
    assert 900 <= gaps[1] < 1400  # second empty result -> ~1.0s (doubled)
    assert gaps[2] < 300  # real data received - no backoff sleep before the next recvfrom()
    assert 400 <= gaps[3] < 800  # backoff restarted from the initial value, not continuing from ~2.0s


def test_run_recv_backoff_caps_at_the_ceiling() -> None:
    # Many consecutive failures must never grow the pause past the configured ceiling - a real,
    # bounded worst case, not just "slower than before." Uncapped doubling would reach 8.0s on the
    # 5th failure; the fix's ceiling is 5.0s.
    query = make_query(["a", "io"])
    fake = _FakeUDPS([(None, None)] * 5 + [(query, ("127.0.0.5", 5000))])

    async def scenario() -> list[int]:
        server = DNSServer()
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=20000)
            return fake.recv_call_times_ms
        finally:
            await _cancel(task)

    call_times = run(scenario())
    assert len(call_times) >= 6  # 5 empty results + the one that finally returns real data
    gaps = [time.ticks_diff(call_times[i + 1], call_times[i]) for i in range(5)]
    assert 4700 <= gaps[4] < 5400  # 5th failure's pause is capped at ~5.0s, not the uncapped ~8.0s


def test_run_disconnect_reporting_a_second_cancellation_does_not_raise_or_log() -> None:
    fake = _RaisingDisconnectUDPS(asyncio.CancelledError())

    async def scenario() -> None:
        server = DNSServer(debug=PrintLog.level_err())
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(20)
        await _cancel(task)
        assert fake.disconnect_called is True
        assert server.pr.err_count == 0  # a second CancelledError during cleanup isn't a real error

    run(scenario())  # a second CancelledError delivered during cleanup must not escape either


def test_run_logs_a_persisted_warning_when_disconnect_reports_incomplete_teardown() -> None:
    # Step 6 (silent-failure-masking finding): AsyUDPSocket.disconnect() never raises, but now
    # reports a failed unregister()/close() via its bool return - run() must actually check it and
    # log, not just call disconnect() and move on regardless of the result.
    fake = _FakeUDPS([])
    fake.disconnect_ok = False

    async def scenario() -> None:
        server = DNSServer(debug=PrintLog.level_warn())
        server.udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(20)
        await _cancel(task)
        assert fake.disconnect_called is True
        assert server.pr.err_count == 1

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
