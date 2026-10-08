import asyncio
import socket
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

from _error_codes import code
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

import asy_captive_dns
from asy_captive_dns import CaptiveDNS, DNSQuery
from asy_dns_client import DNS_UDP_MAX
from asy_print_log import LogConfig, PrintLogHistory
from asy_udp_socket import UDPSocket

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, NoReturn, TypeVar

    T = TypeVar("T")


# The suite's waits, bounds and backoff-gap bands, one constant each (SPECIFICATION.md Part N).
# @tunable l1.captive_dns_wait_until_timeout_ms = 1000
_WAIT_UNTIL_TIMEOUT_MS = 1000
# @tunable l1.captive_dns_wait_until_poll_ms = 10
_WAIT_UNTIL_POLL_MS = 10
# @tunable l1.captive_dns_stray_reply_wait_ms = 20
_STRAY_REPLY_WAIT_MS = 20
# @tunable l1.captive_dns_no_backoff_elapsed_max_ms = 1000
_NO_BACKOFF_ELAPSED_MAX_MS = 1000
# @tunable l1.captive_dns_reach_recv_ms = 20
_REACH_RECV_MS = 20
# @tunable l1.captive_dns_bind_wait_ms = 50
_BIND_WAIT_MS = 50
# @tunable l1.captive_dns_cycle_wait_ms = 100
_CYCLE_WAIT_MS = 100
# @tunable l1.captive_dns_cleanup_tick_ms = 10
_CLEANUP_TICK_MS = 10
# @tunable l1.captive_dns_cleanup_tick_count = 10
_CLEANUP_TICK_COUNT = 10
# @tunable l1.captive_dns_backoff_wait_timeout_ms = 5000
_BACKOFF_WAIT_TIMEOUT_MS = 5000
# @tunable l1.captive_dns_backoff_series_timeout_ms = 15000
_BACKOFF_SERIES_TIMEOUT_MS = 15000
# @tunable l1.captive_dns_gap_initial_min_ms = 400
_GAP_INITIAL_MIN_MS = 400
# @tunable l1.captive_dns_gap_initial_max_ms = 800
_GAP_INITIAL_MAX_MS = 800
# @tunable l1.captive_dns_gap_doubled_min_ms = 900
_GAP_DOUBLED_MIN_MS = 900
# @tunable l1.captive_dns_gap_doubled_max_ms = 1400
_GAP_DOUBLED_MAX_MS = 1400
# @tunable l1.captive_dns_gap_quad_min_ms = 1900
_GAP_QUAD_MIN_MS = 1900
# @tunable l1.captive_dns_gap_quad_max_ms = 2600
_GAP_QUAD_MAX_MS = 2600
# @tunable l1.captive_dns_gap_no_backoff_max_ms = 300
_GAP_NO_BACKOFF_MAX_MS = 300
# @tunable l1.captive_dns_backoff_cap_timeout_ms = 20000
_BACKOFF_CAP_TIMEOUT_MS = 20000
# @tunable l1.captive_dns_gap_cap_min_ms = 4700
_GAP_CAP_MIN_MS = 4700
# @tunable l1.captive_dns_gap_cap_max_ms = 5400
_GAP_CAP_MAX_MS = 5400


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


async def _used_slots(server: CaptiveDNS) -> "list[tuple[int, str]]":  # DNSSRV's used (ErrNum, ErrType) slots, oldest first
    entry = (await server.get_error_counter())["DNSSRV"]
    return [(entry["ErrNum"][i], entry["ErrType"][i]) for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] != "N"]


def make_pr(level: int | None = None) -> PrintLogHistory:  # a fresh, independent logger per test/DNSQuery
    return PrintLogHistory(level=level, name="TESTDNS")


# Below the OS ephemeral range (32768-60999) so a concurrently-running ephemeral socket can
# never be assigned this port - see scripts/test.sh's own TEST_PARALLELISM comment.
_next_port = 22000


def make_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


def _resolved(host: str, port: int) -> tuple[str, int]:
    # This Unix build's raw bind()/sendto() need getaddrinfo()'s opaque sockaddr (SPECIFICATION.md F.7); only the peer sockets use it.
    return socket.getaddrinfo(host, port)[0][-1]  # type: ignore[return-value]


def _read_replies(peer: "socket.socket", replies: list[bytes]) -> bool:
    # Moves every datagram queued on the non-blocking peer into replies (recv() raises OSError once none is
    # left) and says whether one has arrived yet - a _wait_until() predicate.
    while True:
        try:
            replies.append(peer.recv(DNS_UDP_MAX))
        except OSError:
            return bool(replies)


def make_query(labels: list[str], query_id: bytes = b"\x12\x34", qtype: bytes = b"\x00\x01") -> bytes:
    # A minimal, well-formed standard-query datagram: 12-byte header + length-prefixed labels +
    # QTYPE (A unless given)/QCLASS=IN, matching what DNSQuery.__init__ expects (RFC 1035 section 4.1.1/4.1.2).
    question = b"".join(bytes([len(label)]) + label.encode("ascii") for label in labels)
    question += b"\x00" + qtype + b"\x00\x01"
    header = query_id + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    return header + question


def malformed_query_cases() -> list[bytes]:
    # The 16 shapes DNSQuery drops: too short for the header or the question, a label truncated or cut before QTYPE/QCLASS,
    # invalid UTF-8, a response (QR set), a question count other than one, and a compression pointer or reserved label
    # type as a length byte - the last five carry a question long enough to cover the bogus length.
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"  # standard query, QDCOUNT=1
    question = b"\x01a\x00\x00\x01\x00\x01"  # a., QTYPE=A, QCLASS=IN
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
        b"\x12\x34\x81\x80\x00\x01\x00\x00\x00\x00\x00\x00" + question,  # QR set: a response, not a query
        b"\x12\x34\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00" + question,  # QDCOUNT=0
        b"\x12\x34\x01\x00\x00\x02\x00\x00\x00\x00\x00\x00" + question + question,  # QDCOUNT=2
        header + b"\xc0\x0c" + b"a" * 191 + question[2:],  # a compression pointer as the first length byte (0xC0 = 192)
        header + b"\x40" + b"a" * 64 + question[2:],  # a reserved label type (0x40 = 64) as the first length byte
    ]


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


def test_a_name_of_255_octets_is_answered_and_256_is_dropped() -> None:
    # RFC 1035 SS3.1: a name is at most 255 octets on the wire, its length bytes and terminator included.
    longest = ["a" * 63, "b" * 63, "c" * 63, "d" * 61]  # 4 length bytes + 250 + the terminator = 255
    dns = DNSQuery(make_query(longest), make_pr())
    assert dns.domain == ".".join(longest) + "."
    assert dns.response("192.168.4.1") is not None
    too_long = DNSQuery(make_query(["a" * 63, "b" * 63, "c" * 63, "d" * 62]), make_pr())  # 256 octets
    assert too_long.domain == ""
    assert too_long.response("192.168.4.1") is None


def test_dns_query_reuses_the_given_logger_instead_of_constructing_its_own() -> None:
    # DNSQuery is constructed fresh per incoming request (see CaptiveDNS.run()) - it must reuse the
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
    # A real-world shape: a query with a single question plus trailing data this class was never meant to
    # parse - most commonly a client's EDNS0 OPT record.
    #
    # Before the _question_end fix, self.data[12:] echoed that trailing data into what the header declares
    # is pure question content, while ANCOUNT was set to the original QDCOUNT rather than the one record
    # appended - a packet whose declared counts did not match its byte layout.
    #
    # A compliant parser, having read exactly the declared questions, would then try to parse the leftover
    # trailing bytes as the start of the answer section instead of the real answer, which sits after them.
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


def test_a_query_declaring_two_questions_is_dropped() -> None:
    # DNSQuery parses exactly one question; a header declaring two is not answered as if it held one.
    header = b"\x12\x34\x01\x00\x00\x02\x00\x00\x00\x00\x00\x00"  # QDCOUNT=2
    question = b"\x01a\x02io\x00\x00\x01\x00\x01"
    second_question = b"\x01b\x00\x00\x01\x00\x01"
    dns = DNSQuery(header + question + second_question, make_pr())
    assert dns.domain == ""
    assert dns.response("192.168.4.1") is None


def test_an_a_or_any_query_gets_the_a_record() -> None:
    # Expected bytes from RFC 1035 SS4.1.1 (header) and SS4.1.3 (answer RR); QTYPE 1 is A (SS3.2.2), 255 is * (SS3.2.3).
    for qtype in (b"\x00\x01", b"\x00\xff"):
        query = make_query(["a", "io"], qtype=qtype)
        header = query[:2] + b"\x81\x80" + b"\x00\x01" + b"\x00\x01" + b"\x00\x00" + b"\x00\x00"  # flags, QD 1, AN 1, NS 0, AR 0
        answer = b"\xc0\x0c" + b"\x00\x01" + b"\x00\x01" + b"\x00\x00\x00\x3c" + b"\x00\x04" + bytes([192, 168, 4, 1])
        assert DNSQuery(query, make_pr()).response("192.168.4.1") == header + query[12:] + answer


def test_other_query_types_get_an_empty_noerror_reply() -> None:
    # RFC 1035 SS4.1.1 header, NOERROR, no answer (RFC 2308 2.2 NODATA); QTYPE 2 NS, 15 MX (SS3.2.2), 28 AAAA (RFC 3596), 65 HTTPS (RFC 9460).
    for labels, qtype in ((["a", "io"], 28), (["a", "io"], 65), (["a", "io"], 15), ([], 2)):
        query = make_query(labels, qtype=qtype.to_bytes(2, "big"))
        question = query[12:]
        packet = DNSQuery(query, make_pr()).response("192.168.4.1")
        assert packet is not None
        assert packet == query[:2] + b"\x81\x80" + b"\x00\x01" + b"\x00\x00" * 3 + question  # QD 1, AN/NS/AR 0, the question
        assert len(packet) == 12 + len(question)  # nothing after the echoed question


def test_response_returns_none_for_empty_domain() -> None:
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # non-standard query -> empty domain
    assert DNSQuery(bytes(data), make_pr()).response("192.168.4.1") is None


def test_response_answers_the_root_domain_query_not_indistinguishable_from_a_parse_failure() -> None:
    # Regression test for BACKLOG.md's "root-domain query can't be told apart from a failed parse" entry: a
    # root query (a single zero-length label) parses to the same empty self.domain a malformed datagram
    # falls back to, and response() used `if self.domain:` to decide whether to answer.
    #
    # Both cases therefore returned None, contradicting this module's docstring claim that every on-subnet
    # query gets an answer. response() now tracks parse success separately.
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
    # Boundary check either side of the QTYPE/QCLASS cutoff: a label plus terminator with the full 4
    # trailing bytes must still parse and answer normally, while the same without them must be treated as
    # malformed rather than silently echoed as a short, misaligned question.
    #
    # self.data[12:end] would otherwise truncate via ordinary slice semantics instead of raising.
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
# CaptiveDNS: construction.
# ---------------------------------------------------------------------------


def test_dns_server_init_binds_the_standard_dns_port_in_server_mode() -> None:
    server = CaptiveDNS(log=LogConfig(None, 10, 5))  # DebugLevel 5, everything (SPEC A.8's level numbers)
    assert server._udps._addr == ("0.0.0.0", 53)
    assert server._udps._mode == "server"
    assert server._udps._sock is None  # lazy - no real bind attempted at construction


def test_dns_server_error_source_and_logger_fan_in_report_itself() -> None:
    # Part C.14/G.2's duck-typed fan-in pair, which the generated boot list registers this module
    # through. Neither accessor was ever called: a wrong list here drops DNSSRV out of /status's
    # errcount and out of the level registry, both silently.
    server = CaptiveDNS()
    assert server.get_error_sources() == [server]
    assert server.get_loggers() == [server.pr]


def test_dns_server_uses_in_memory_logging_when_fram_is_none() -> None:
    server = CaptiveDNS()
    assert isinstance(server.pr, PrintLogHistory)


def test_dns_server_logger_is_named_dnssrv() -> None:
    server = CaptiveDNS()
    assert server.pr.name == "DNSSRV"


def test_dns_server_debug_level_is_forwarded_to_the_logger() -> None:
    server = CaptiveDNS(log=LogConfig(None, 10, 1))
    assert server.pr.level == 1


def test_dns_server_history_length_comes_from_the_log_config() -> None:
    server = CaptiveDNS(log=LogConfig(None, 3, None))
    assert len(server.pr.history) == 3


def test_dns_server_debug_none_leaves_logger_at_off() -> None:
    server = CaptiveDNS(log=LogConfig(None, 10, None))
    assert server.pr.level == 0


def test_dns_server_default_logger_is_off() -> None:
    assert CaptiveDNS().pr.level == 0


def test_dns_server_get_error_counter_forwards_to_the_real_print_log() -> None:
    server = CaptiveDNS()
    log = run(server.get_error_counter())
    assert log["DNSSRV"]["ErrCount"] == 0


def test_dns_server_get_error_counter_reflects_a_real_logged_error() -> None:
    server = CaptiveDNS()
    run(server.pr.err_s("boom", errno=code("E", "UNEXPECTED")))
    log = run(server.get_error_counter())
    assert log["DNSSRV"]["ErrCount"] == 1


def test_reset_error_counter_returns_true_and_clears() -> None:
    server = CaptiveDNS()
    run(server.pr.err_s("boom", errno=code("E", "UNEXPECTED")))
    assert run(server.reset_error_counter()) is True
    assert run(server.get_error_counter())["DNSSRV"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# CaptiveDNS.run(): driven through a controlled fake transport.
#
# _FakeUDPS hands run() chosen (data, addr) pairs - foreign or malformed source addresses, failed receives
# and refused sends no loopback socket produces on demand - while DNSQuery/response() run unmocked. The
# real-socket tests further down drive the same path through UDPSocket and the address shim.
# ---------------------------------------------------------------------------


class _FakeUDPS:
    def __init__(self, incoming: list[tuple[bytes | None, tuple[str, int] | None]]) -> None:
        self._incoming = list(incoming)
        self.connected = True  # run() reads it to tell a socket that never bound from a failed receive
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.sendto_results: list[int | None] = []
        self.disconnect_called = False
        self.disconnect_ok = True  # real UDPSocket.disconnect()'s success return, see Step 6 note
        self.bufsizes: list[int] = []
        # One entry per recvfrom() call, for backoff-timing assertions. "Any", not "int": mypy's time.pyi
        # types ticks_ms() as the opaque _TicksMs marker class, deliberately incompatible with plain int to
        # catch raw-arithmetic misuse, and these values are only ever fed back into time.ticks_diff().
        self.recv_call_times_ms: list[Any] = []
        # ("recv"/"send", loop_turns at the call): loop_turns is a test ticker's count of scheduler passes.
        self.calls: list[tuple[str, int]] = []
        self.loop_turns = 0

    # CaptiveDNS calls recvfrom(512)/sendto(packet, addr): the fake records the buffer size; the timeout is never passed.
    async def recvfrom(self, bufsize: int, _timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        self.bufsizes.append(bufsize)
        self.calls.append(("recv", self.loop_turns))
        self.recv_call_times_ms.append(time.ticks_ms())
        if self._incoming:
            data, addr = self._incoming.pop(0)
            await asyncio.sleep(0)
            return data, addr
        await asyncio.sleep(3600)  # simulates "no more traffic" - cancellable, never busy-loops
        return None, None

    async def sendto(self, packet: bytes, addr: tuple[str, int], _timeout_ms: int = -1) -> int | None:
        result = self.sendto_results.pop(0) if self.sendto_results else len(packet)
        self.sent.append((packet, addr))
        self.calls.append(("send", self.loop_turns))
        return result

    async def disconnect(self) -> bool:
        self.disconnect_called = True
        return self.disconnect_ok


async def _wait_until(predicate: "Callable[[], bool]", timeout_ms: int = _WAIT_UNTIL_TIMEOUT_MS) -> bool:
    t0 = time.ticks_ms()
    while not predicate():
        if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
            return False
        await asyncio.sleep_ms(_WAIT_UNTIL_POLL_MS)
    return True


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _count_loop_turns(fake: _FakeUDPS) -> None:
    # One count per scheduler pass: two fake calls recorded one count apart at most had no timed wait between them.
    while True:
        fake.loop_turns += 1
        await asyncio.sleep(0)


def test_run_answers_on_subnet_request() -> None:
    fake = _FakeUDPS([(make_query(["a", "io"]), ("127.0.0.5", 5000))])

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
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
        ],
    )

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1)
            await asyncio.sleep_ms(_STRAY_REPLY_WAIT_MS)  # give a stray second reply a chance to show up, if any
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
            (query, (0x7F000005, 5002)),  # type: ignore[list-item]  # a non-str host: ipv4_to_int() raises, read as off-subnet
            (query, ("127.0.0.5", 5001)),
        ],
    )

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
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
        ],
    )

    async def scenario() -> tuple[list[tuple[bytes, tuple[str, int]]], int]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
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
    assert elapsed_ms < _NO_BACKOFF_ELAPSED_MAX_MS


def test_run_rejects_invalid_server_ip_or_netmask_without_raising() -> None:
    server = CaptiveDNS()

    async def scenario() -> None:
        await server.run("not-an-ip", "255.255.255.0")

    run(scenario())  # returns cleanly before ever touching udps - must not raise
    assert server._udps._sock is None


def test_run_rejects_invalid_server_ip_or_netmask_logs_a_persisted_error() -> None:
    server = CaptiveDNS(log=LogConfig(None, 10, 1))

    async def scenario() -> None:
        await server.run("not-an-ip", "255.255.255.0")

    run(scenario())
    assert server.pr._err_count == 1
    assert run(_used_slots(server)) == [(code("E", "BAD_ARG"), "E")]
    assert server._udps._sock is None


def test_run_cancellation_disconnects_cleanly() -> None:
    fake = _FakeUDPS([])

    async def scenario() -> None:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(_REACH_RECV_MS)  # let it reach the pending recvfrom()
        await _cancel(task)  # run() cleans up and re-raises the cancellation; cancel() absorbs it

    run(scenario())
    assert fake.disconnect_called is True


def test_awaiting_a_cancelled_run_raises_after_disconnect() -> None:
    # The cancellation is re-raised, never turned into a normal return, and only after the socket was released.
    fake = _FakeUDPS([])

    async def scenario() -> "tuple[bool, bool]":
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(_REACH_RECV_MS)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True, fake.disconnect_called
        return False, fake.disconnect_called

    raised, disconnected_first = run(scenario())
    assert raised is True
    assert disconnected_first is True


def test_run_continues_after_sendto_reports_failure() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (query, ("127.0.0.5", 5000)),
            (query, ("127.0.0.5", 5001)),
        ],
    )
    fake.sendto_results = [None]  # first reply "fails", matching sendto()'s documented None sentinel

    async def scenario() -> list[tuple[bytes, tuple[str, int]]]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
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
    # Two refused replies: both counted, one slot (the central newest-entry rule, C.7.1).
    query = make_query(["a", "io"])
    fake = _FakeUDPS([(query, ("127.0.0.5", 5000)), (query, ("127.0.0.5", 5000))])
    fake.sendto_results = [None, None]

    async def scenario() -> None:
        server = CaptiveDNS(log=LogConfig(None, 10, 2))
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 2)
            assert server.pr._err_count == 2
            assert await _used_slots(server) == [(code("W", "DNS_REPLY_DROPPED"), "W")]
        finally:
            await _cancel(task)

    run(scenario())


def test_run_failed_receive_logs_one_warning_per_code() -> None:
    # Two failed receives on a bound socket: both counted, one slot (the central newest-entry rule, C.7.1).
    fake = _FakeUDPS([(None, None), (None, None)])

    async def scenario() -> None:
        server = CaptiveDNS(log=LogConfig(None, 10, 2))
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: server.pr._err_count >= 2)
            assert server.pr._err_count == 2
            assert await _used_slots(server) == [(code("W", "DNS_RECV_FAILED"), "W")]
        finally:
            await _cancel(task)

    run(scenario())


def test_run_reads_with_the_rfc_1035_udp_limit() -> None:
    # RFC 1035 SS2.3.4: a DNS message over UDP is at most 512 octets, so no receive asks for more.
    fake = _FakeUDPS([(make_query(["a", "io"]), ("127.0.0.5", 5000))])

    async def scenario() -> None:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1 and len(fake.bufsizes) >= 2)
        finally:
            await _cancel(task)

    run(scenario())
    assert fake.bufsizes == [512] * len(fake.bufsizes)


def test_run_answers_queued_queries_back_to_back() -> None:
    # Guard: four queued queries get four replies in order, each reply followed by the next recvfrom() within
    # one scheduler pass (a yield at most, never a timed wait), so a queue is drained before the socket sleeps.
    fake = _FakeUDPS([(make_query(["a", "io"], query_id=bytes([0, n])), ("127.0.0.5", 5000 + n)) for n in range(4)])

    async def scenario() -> None:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        ticker = asyncio.create_task(_count_loop_turns(fake))
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 4 and len(fake.bufsizes) >= 5)
        finally:
            await _cancel(task)
            await _cancel(ticker)

    run(scenario())
    assert [(packet[:2], addr) for packet, addr in fake.sent] == [(bytes([0, n]), ("127.0.0.5", 5000 + n)) for n in range(4)]
    assert [kind for kind, _ in fake.calls] == ["recv", "send"] * 4 + ["recv"]
    for i in range(1, 9, 2):  # each send, then the recvfrom() it was followed by
        assert fake.calls[i + 1][1] - fake.calls[i][1] <= 1


class _FloodUDPS(_FakeUDPS):
    # A socket that stays ready: each of the first `datagrams` recvfrom() calls returns a query at once,
    # with no await of its own; then the flood ends, so a loop that never yields cannot hold the test forever.
    def __init__(self, datagrams: int) -> None:
        super().__init__([])
        self._left = datagrams

    async def recvfrom(self, bufsize: int, _timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        self.bufsizes.append(bufsize)
        self.calls.append(("recv", self.loop_turns))
        if self._left > 0:
            self._left -= 1
            return make_query(["a", "io"]), ("127.0.0.5", 5000)
        await asyncio.sleep(3600)
        return None, None


def test_run_yields_once_per_datagram_while_the_socket_stays_ready() -> None:
    # A sustained flood keeps the socket ready, so nothing below run() yields: other tasks get a turn only
    # because run() gives one per datagram (on rp2, lwIP refills the queue from PendSV while Python runs).
    datagrams = 8
    fake = _FloodUDPS(datagrams)

    async def scenario() -> None:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        ticker = asyncio.create_task(_count_loop_turns(fake))
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= datagrams and len(fake.bufsizes) > datagrams)
        finally:
            await _cancel(task)
            await _cancel(ticker)

    run(scenario())
    sends = [turns for kind, turns in fake.calls if kind == "send"]
    assert len(sends) == datagrams
    for k in range(1, datagrams):
        assert sends[k] > sends[k - 1]  # the ticker ran between two served datagrams


class _HeapFailingParse:
    # As a datagram its indexing, as a sender host its split(), fails the way a heap-exhausted parse
    # would; the text keeps clear of the memory gates' markers.
    def __getitem__(self, _index: object) -> "NoReturn":
        raise MemoryError("injected for parse")

    def split(self, _sep: str) -> "NoReturn":
        raise MemoryError("injected for parse")


def test_a_heap_failure_while_parsing_is_persisted_not_dropped_as_malformed() -> None:
    # The query (DNSQuery) and the sender address (run()'s subnet check) each: one E UNEXPECTED slot, not
    # the silent "malformed input" drop every other parse exception still gets.
    query = make_query(["a", "io"])
    for incoming in ((_HeapFailingParse(), ("127.0.0.5", 5000)), (query, (_HeapFailingParse(), 5000))):
        fake = _FakeUDPS([incoming])  # type: ignore[list-item]

        async def scenario(fake: _FakeUDPS = fake) -> None:
            server = CaptiveDNS(log=LogConfig(None, 10, 1))
            server._udps = fake  # type: ignore[assignment]
            task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
            try:
                assert await _wait_until(lambda: server.pr._err_count >= 1)
                assert server.pr._err_count == 1
                assert await _used_slots(server) == [(code("E", "UNEXPECTED"), "E")]
            finally:
                await _cancel(task)

        run(scenario())
        assert fake.sent == []


class _TimedUDPSocket(UDPSocket):
    # Records each recvfrom()'s entry and return, in ms since construction, so the server's own pause
    # between two receives (next entry - previous return) excludes whatever the call itself waits.
    def __init__(self, addr: tuple[str, int]) -> None:
        super().__init__(addr, mode="server")
        self._t0 = time.ticks_ms()
        self.entered_ms: list[int] = []
        self.returned_ms: list[int] = []

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
        self.entered_ms.append(time.ticks_diff(time.ticks_ms(), self._t0))
        try:
            return await super().recvfrom(buf, timeout_ms)
        finally:
            self.returned_ms.append(time.ticks_diff(time.ticks_ms(), self._t0))


def test_run_bind_failure_logs_init_once_and_backs_off() -> None:
    # A socket that never bound is a local setup failure, never a client's datagram: E INIT, not
    # DNS_RECV_FAILED, one slot for every repeat, and the receive-failure backoff between attempts.
    port = make_port()
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(_resolved("127.0.0.1", port))  # no SO_REUSEADDR, so UDPSocket's own bind() gets EADDRINUSE
    udps = _TimedUDPSocket(("127.0.0.1", port))

    async def scenario() -> None:
        server = CaptiveDNS(log=LogConfig(None, 10, 1))
        server._udps = udps
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(udps.returned_ms) >= 3 and server.pr._err_count >= 3, timeout_ms=_BACKOFF_WAIT_TIMEOUT_MS)
            assert (await server.get_error_counter())["DNSSRV"]["ErrCount"] == 3
            assert await _used_slots(server) == [(code("E", "INIT"), "E")]
        finally:
            await _cancel(task)

    try:
        run(scenario())
    finally:
        blocker.close()
    assert udps.connected is False
    gaps = [udps.entered_ms[i + 1] - udps.returned_ms[i] for i in range(2)]
    assert _GAP_INITIAL_MIN_MS <= gaps[0] < _GAP_INITIAL_MAX_MS  # ~0.5 s after the first failure
    assert _GAP_DOUBLED_MIN_MS <= gaps[1] < _GAP_DOUBLED_MAX_MS  # ~1.0 s (doubled) after the second


# ---------------------------------------------------------------------------
# One genuine end-to-end pass over a real loopback socket - proves CaptiveDNS.run() actually binds,
# receives, and replies without crashing through UDPSocket for real, not just via _FakeUDPS.
# ---------------------------------------------------------------------------


def test_run_handles_real_loopback_traffic_without_crashing() -> None:
    server_port = make_port()
    peer_addr = _resolved("127.0.0.1", make_port())

    async def scenario() -> "tuple[bool, list[bytes]]":
        server = CaptiveDNS()
        server._udps = UDPSocket(("127.0.0.1", server_port), mode="server")
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer.bind(peer_addr)
        peer.setblocking(False)
        replies: list[bytes] = []
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            await asyncio.sleep_ms(_BIND_WAIT_MS)  # let the server bind
            peer.sendto(make_query(["a", "io"]), _resolved("127.0.0.1", server_port))
            await _wait_until(lambda: _read_replies(peer, replies))
            return not task.done(), replies  # still running - no uncaught exception killed it
        finally:
            peer.close()
            await _cancel(task)

    alive, replies = run(scenario())
    assert alive is True
    assert len(replies) == 1  # the shim hands run() each sender as a (host, port) tuple, so it is answered
    assert replies[0][:2] == b"\x12\x34"
    assert replies[0][-4:] == bytes([127, 0, 0, 1])


# ---------------------------------------------------------------------------
# Every distinct fault shape a caller could hand a dotted-quad parameter: wrong type, and every
# malformed string ipv4_to_int() rejects.
# ---------------------------------------------------------------------------


def _bad_ipv4_values() -> "list[Any]":
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
# CaptiveDNS.run(): the server_ip/netmask startup-configuration matrix. Every invalid case asserts run()
# returns without raising and never binds, exercising ipv4_to_int()'s never-raises None-check without a live
# socket. A non-str server_ip or netmask still raises via ipv4_to_int()'s own ip.split().
#
# The valid-configuration case does need a live loop iteration, so it goes through the fake transport and a
# real cancellable task, like the rest of this file's run() tests.
# ---------------------------------------------------------------------------


def _run_once_expect_clean_return(server: "CaptiveDNS", server_ip: str, netmask: str) -> None:
    async def scenario() -> None:
        await server.run(server_ip, netmask)

    run(scenario())


def _run_briefly_and_cancel(server: "CaptiveDNS", server_ip: str, netmask: str, wait_ms: int = _REACH_RECV_MS) -> None:
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
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        _run_briefly_and_cancel(server, server_ip, netmask)
        assert fake.disconnect_called is True  # reached the main loop, not the early-return path


def test_run_rejects_single_invalid_server_ip_parameter() -> None:
    for bad_ip in _bad_ipv4_values():
        if not isinstance(bad_ip, str):
            continue  # a non-str server_ip raises via ipv4_to_int()'s own ip.split() - not this test's concern
        server = CaptiveDNS()
        _run_once_expect_clean_return(server, bad_ip, "255.255.255.0")
        assert server._udps._sock is None  # never attempted to bind


def test_run_rejects_single_invalid_netmask_parameter() -> None:
    for bad_netmask in _bad_ipv4_values():
        if not isinstance(bad_netmask, str):
            continue
        server = CaptiveDNS()
        _run_once_expect_clean_return(server, "192.168.4.1", bad_netmask)
        assert server._udps._sock is None


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
        server = CaptiveDNS()
        _run_once_expect_clean_return(server, bad_ip, bad_netmask)
        assert server._udps._sock is None


def test_run_rejects_non_str_server_ip_or_netmask() -> None:
    # A non-str value still raises, via ipv4_to_int()'s own ip.split() - this class's public str-typed
    # signature relies on that, like resolve_ipv4()'s own ipv4_to_int() calls. Any lives on the bad-
    # value table, not on scenario()'s parameters, which keep run()'s declared str types.
    bad_pairs: tuple[tuple[Any, Any], ...] = ((None, "255.0.0.0"), ("192.168.4.1", 123), ([1, 2, 3, 4], b"255.0.0.0"))
    for bad_ip, bad_netmask in bad_pairs:
        server = CaptiveDNS()

        async def scenario(srv: "CaptiveDNS" = server, ip: str = bad_ip, netmask: str = bad_netmask) -> None:
            await srv.run(ip, netmask)

        try:
            run(scenario())
            raise AssertionError(f"expected an exception for {bad_ip!r}, {bad_netmask!r}")
        except (AttributeError, TypeError):
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


def test_dns_query_init_rejects_list_shaped_data_that_passes_every_index_lookup() -> None:
    # A sequence long enough for every index lookup (data[2], data[4:6], data[12]) but no bytes: a list
    # slice never equals the bytes QDCOUNT=1, so it stops at the one-question check, never a raise.
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
            continue  # a non-str ip raises via ipv4_to_int()'s own ip.split() - see the dedicated test below
        assert DNSQuery(query, make_pr()).response(bad_ip) is None


def test_response_rejects_non_str_ip_parameter() -> None:
    query = make_query(["a", "io"])
    for bad_ip in (None, 123, [1, 2, 3, 4], b"127.0.0.1"):
        try:
            DNSQuery(query, make_pr()).response(bad_ip)  # type: ignore[arg-type]
            raise AssertionError(f"expected an exception for {bad_ip!r}")
        except (AttributeError, TypeError):
            pass


def test_response_rejects_invalid_ip_combined_with_empty_domain_state() -> None:
    # domain=="" already short-circuits to None before ip is ever inspected - an invalid ip
    # combined with an already-invalid (empty-domain) object state must still just return None,
    # even for a wrong-typed ip that would otherwise raise via ipv4_to_int().
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # non-standard opcode -> empty domain
    for bad_ip in _bad_ipv4_values():
        assert DNSQuery(bytes(data), make_pr()).response(bad_ip) is None


# ---------------------------------------------------------------------------
# Integration: CaptiveDNS driven through a real UDPSocket end to end, not the fake transport above -
# exercising the whole pipeline against the actual dependency it imports, including that dependency's own
# fault-handling contract: every public I/O method returns its None-shaped sentinel rather than raising.
# ---------------------------------------------------------------------------


# The address shim hands run() each sender as a (host, port) tuple, so a loopback query is answered for real;
# the tests below assert liveness and rebinding, and the burst test which datagrams got a reply.


def test_run_reuses_same_dns_server_instance_across_multiple_hotspot_cycles() -> None:
    # Mirrors asy_wifi_service.py's real usage, where WifiService.__init__ builds one self._dns_server reused
    # across every hotspot activation: one instance, run() started, cancelled and started again - safe only
    # because UDPSocket.disconnect() fully resets state for the next _connect().
    server_port = make_port()
    server = CaptiveDNS()
    server._udps = UDPSocket(("127.0.0.1", server_port), mode="server")

    async def one_cycle() -> bool:
        peer_addr = _resolved("127.0.0.1", make_port())
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer.bind(peer_addr)
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            await asyncio.sleep_ms(_BIND_WAIT_MS)  # let it bind
            assert server._udps._sock is not None  # real bind succeeded this cycle
            peer.sendto(make_query(["cycle"]), _resolved("127.0.0.1", server_port))
            await asyncio.sleep_ms(_CYCLE_WAIT_MS)
            return not task.done()  # still alive - no uncaught exception killed it
        finally:
            peer.close()
            await _cancel(task)

    assert run(one_cycle()) is True
    assert server._udps._sock is None  # first cycle's disconnect() really tore it down
    assert run(one_cycle()) is True  # second activation, on the exact same instance, rebinds fine
    assert server._udps._sock is None


def test_run_real_socket_survives_a_burst_of_consecutive_malformed_datagrams() -> None:
    # Real-world incident shape: a burst of bad traffic (not just one bad packet), sent over the
    # actual loopback network stack (not just handed to a fake transport) - proves no cumulative
    # state corruption or crash across repeated real, malformed datagrams.
    server_port = make_port()
    peer_addr = _resolved("127.0.0.1", make_port())

    async def scenario() -> "tuple[bool, list[bytes]]":
        server = CaptiveDNS()
        server._udps = UDPSocket(("127.0.0.1", server_port), mode="server")
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer.bind(peer_addr)
        peer.setblocking(False)
        replies: list[bytes] = []
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            await asyncio.sleep_ms(_BIND_WAIT_MS)
            server_addr = _resolved("127.0.0.1", server_port)
            for bad in malformed_query_cases():
                peer.sendto(bad, server_addr)
            peer.sendto(make_query(["a", "io"], query_id=b"\x56\x78"), server_addr)
            await _wait_until(lambda: _read_replies(peer, replies))
            return not task.done(), replies  # still alive after the whole burst
        finally:
            peer.close()
            await _cancel(task)

    alive, replies = run(scenario())
    assert alive is True
    # Served in arrival order: the valid query, sent last, is the only one answered - every malformed shape was dropped.
    assert [reply[:2] for reply in replies] == [b"\x56\x78"]


# ---------------------------------------------------------------------------
# Integration contract: replicates asy_wifi_service.py's real CaptiveDNS usage exactly. That module cannot be
# imported here, depending on network.WLAN and other RP2040-only hardware this environment lacks.
#
# Confirmed directly against it: one CaptiveDNS built once in WifiService.__init__, run() started via
# evtloop.create_task(), and shut down via a fire-and-forget cancel() the caller never awaits.
# ---------------------------------------------------------------------------


def test_integration_survives_the_wifi_services_fire_and_forget_cancel_pattern() -> None:
    server_port = make_port()

    async def scenario() -> "CaptiveDNS":
        server = CaptiveDNS()
        server._udps = UDPSocket(("127.0.0.1", server_port), mode="server")
        evtloop = asyncio.get_event_loop()
        task = evtloop.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(_BIND_WAIT_MS)  # let it bind and reach the pending recvfrom()
        task.cancel()  # exactly WifiService's own pattern - never awaited by the caller
        # Nothing observes `task` from here on, matching the real caller exactly. Only give the
        # event loop a few ticks so the cancelled task's own cleanup actually gets to run, the way
        # it naturally would on a live device between this point and the next scheduler pass.
        for _ in range(_CLEANUP_TICK_COUNT):
            await asyncio.sleep_ms(_CLEANUP_TICK_MS)
        return server

    server = run(scenario())
    assert server._udps._sock is None  # cleanup completed on its own; nothing had to await it


# ---------------------------------------------------------------------------
# run()'s catch-all backoff: an unexpected exception from a dependency - neither malformed data nor off-
# subnet - must still degrade to the 3 s _ERROR_RETRY_WAIT_S pause rather than crash or busy-loop, and must
# be logged as a real, persisted error.
#
# The one fault category that genuinely cannot be produced for real, nothing in the legitimate processing
# path throwing mid-packet, so it is simulated by swapping asy_captive_dns.DNSQuery - mocking a dependency,
# not the run() logic under test.
# ---------------------------------------------------------------------------


def test_run_backs_off_on_a_genuinely_unexpected_exception_then_recovers() -> None:
    real_dns_query = asy_captive_dns.DNSQuery
    calls = {"n": 0}

    class _FlakyDNSQuery:
        def __init__(self, data: bytes, pr: "PrintLogHistory") -> None:
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
        ],
    )

    async def scenario() -> "tuple[list[tuple[bytes, tuple[str, int]]], int]":
        asy_captive_dns.DNSQuery = _FlakyDNSQuery  # type: ignore[assignment,misc]
        try:
            server = CaptiveDNS(log=LogConfig(None, 10, 1))
            server._udps = fake  # type: ignore[assignment]
            t0 = time.ticks_ms()
            task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
            try:
                assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=_BACKOFF_WAIT_TIMEOUT_MS)
                assert server.pr._err_count == 1  # the flaky first attempt logged a real, persisted error
                assert await _used_slots(server) == [(code("E", "UNEXPECTED"), "E")]
                return fake.sent, time.ticks_diff(time.ticks_ms(), t0)
            finally:
                await _cancel(task)
        finally:
            asy_captive_dns.DNSQuery = real_dns_query  # type: ignore[misc]

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
        server = CaptiveDNS(log=LogConfig(None, 10, 1))
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(_REACH_RECV_MS)
        await _cancel(task)  # disconnect()'s own exception must not escape cancellation either
        assert fake.disconnect_called is True
        assert server.pr._err_count == 1
        assert await _used_slots(server) == [(code("E", "UNEXPECTED"), "E")]

    run(scenario())  # must not raise despite disconnect() itself failing


# ---------------------------------------------------------------------------
# run()'s receive-failure backoff: a receive that keeps returning (None, None) on a bound socket logs
# DNS_RECV_FAILED and backs off 0.5, 1, 2 ... 5 s (SPECIFICATION.md Part C.9). A socket that never bound takes
# the same backoff with its own code: test_run_bind_failure_logs_init_once_and_backs_off.
# ---------------------------------------------------------------------------


def test_run_backs_off_with_increasing_delay_on_repeated_empty_recvfrom() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS([(None, None), (None, None), (None, None), (query, ("127.0.0.5", 5000))])

    async def scenario() -> list[int]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=_BACKOFF_SERIES_TIMEOUT_MS)
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
    assert _GAP_INITIAL_MIN_MS <= gaps[0] < _GAP_INITIAL_MAX_MS  # ~0.5s initial backoff
    assert _GAP_DOUBLED_MIN_MS <= gaps[1] < _GAP_DOUBLED_MAX_MS  # ~1.0s (doubled)
    assert _GAP_QUAD_MIN_MS <= gaps[2] < _GAP_QUAD_MAX_MS  # ~2.0s (doubled again)


def test_run_recv_backoff_resets_after_a_successful_receive() -> None:
    query = make_query(["a", "io"])
    fake = _FakeUDPS(
        [
            (None, None),
            (None, None),  # ramps the backoff up
            (query, ("127.0.0.5", 5000)),  # real data received - must reset the backoff
            (None, None),
            (None, None),
        ],
    )

    async def scenario() -> list[int]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.recv_call_times_ms) >= 5, timeout_ms=_BACKOFF_SERIES_TIMEOUT_MS)
            return fake.recv_call_times_ms
        finally:
            await _cancel(task)

    call_times = run(scenario())
    gaps = [time.ticks_diff(call_times[i + 1], call_times[i]) for i in range(4)]
    assert _GAP_INITIAL_MIN_MS <= gaps[0] < _GAP_INITIAL_MAX_MS  # first empty result -> ~0.5s
    assert _GAP_DOUBLED_MIN_MS <= gaps[1] < _GAP_DOUBLED_MAX_MS  # second empty result -> ~1.0s (doubled)
    assert gaps[2] < _GAP_NO_BACKOFF_MAX_MS  # real data received - no backoff sleep before the next recvfrom()
    assert _GAP_INITIAL_MIN_MS <= gaps[3] < _GAP_INITIAL_MAX_MS  # backoff restarted from the initial value, not continuing from ~2.0s


def test_run_recv_backoff_caps_at_the_ceiling() -> None:
    # Many consecutive failures must never grow the pause past the configured ceiling - a real,
    # bounded worst case, not just "slower than before." Uncapped doubling would reach 8.0s on the
    # 5th failure; the fix's ceiling is 5.0s.
    query = make_query(["a", "io"])
    fake = _FakeUDPS([(None, None)] * 5 + [(query, ("127.0.0.5", 5000))])

    async def scenario() -> list[int]:
        server = CaptiveDNS()
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        try:
            assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=_BACKOFF_CAP_TIMEOUT_MS)
            return fake.recv_call_times_ms
        finally:
            await _cancel(task)

    call_times = run(scenario())
    assert len(call_times) >= 6  # 5 empty results + the one that finally returns real data
    gaps = [time.ticks_diff(call_times[i + 1], call_times[i]) for i in range(5)]
    assert _GAP_CAP_MIN_MS <= gaps[4] < _GAP_CAP_MAX_MS  # 5th failure's pause is capped at ~5.0s, not the uncapped ~8.0s


def test_run_disconnect_reporting_a_second_cancellation_propagates_without_logging() -> None:
    fake = _RaisingDisconnectUDPS(asyncio.CancelledError())

    async def scenario() -> bool:
        server = CaptiveDNS(log=LogConfig(None, 10, 1))
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(_REACH_RECV_MS)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            propagated = True
        else:
            propagated = False
        assert fake.disconnect_called is True
        assert server.pr._err_count == 0  # a second CancelledError during cleanup is a cancel, not an error
        return propagated

    assert run(scenario()) is True


def test_run_logs_a_persisted_warning_when_disconnect_reports_incomplete_teardown() -> None:
    # Step 6 (silent-failure-masking finding): UDPSocket.disconnect() never raises, but now
    # reports a failed unregister()/close() via its bool return - run() must actually check it and
    # log, not just call disconnect() and move on regardless of the result.
    fake = _FakeUDPS([])
    fake.disconnect_ok = False

    async def scenario() -> None:
        server = CaptiveDNS(log=LogConfig(None, 10, 2))
        server._udps = fake  # type: ignore[assignment]
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        await asyncio.sleep_ms(_REACH_RECV_MS)
        await _cancel(task)
        assert fake.disconnect_called is True
        assert server.pr._err_count == 1
        assert await _used_slots(server) == [(code("W", "SOCKET_TEARDOWN"), "W")]

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
