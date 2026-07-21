import asyncio
import socket
import time

from asy_udp_socket import AsyUDPSocket
from captive_dns import DNSQuery, DNSServer, _ipv4_to_int

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
    # The 10 shapes found reachable from a truncated/malformed real UDP datagram (see BACKLOG.md):
    # too short for the opcode byte, too short for the question section, a length byte with
    # nothing following, a label truncated mid-way (both by 1 byte and entirely), an oversized
    # (attack-style) label-length claim, and a label with an invalid UTF-8 byte.
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
    ]


# ---------------------------------------------------------------------------
# _ipv4_to_int: pure dotted-quad -> int conversion used for subnet-membership math.
# ---------------------------------------------------------------------------


def test_ipv4_to_int_valid() -> None:
    assert _ipv4_to_int("0.0.0.0") == 0
    assert _ipv4_to_int("255.255.255.255") == 0xFFFFFFFF
    assert _ipv4_to_int("192.168.4.1") == (192 << 24) | (168 << 16) | (4 << 8) | 1


def test_ipv4_to_int_rejects_wrong_octet_count() -> None:
    for bad in ("1.2.3", "1.2.3.4.5", "", "1.2.3.4."):
        try:
            _ipv4_to_int(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass


def test_ipv4_to_int_rejects_out_of_range_octet() -> None:
    # A previously-silent gap: an out-of-range octet used to shift bits past its own byte position
    # instead of being rejected, risking a false subnet match rather than a clean "invalid" signal.
    for bad in ("256.0.0.0", "1.2.3.999", "-1.2.3.4"):
        try:
            _ipv4_to_int(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass


def test_ipv4_to_int_rejects_non_numeric_octet() -> None:
    try:
        _ipv4_to_int("a.b.c.d")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# DNSQuery: raw datagram parsing.
# ---------------------------------------------------------------------------


def test_dns_query_parses_single_and_multi_label_domain() -> None:
    assert DNSQuery(make_query(["example"])).domain == "example."
    assert DNSQuery(make_query(["a", "io"])).domain == "a.io."


def test_dns_query_non_standard_opcode_yields_empty_domain() -> None:
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # opcode bits = 1 (not a standard query)
    assert DNSQuery(bytes(data)).domain == ""


def test_dns_query_malformed_or_truncated_data_yields_empty_domain() -> None:
    for data in malformed_query_cases():
        assert DNSQuery(data).domain == ""  # never raises, degrades to the "don't respond" sentinel


# ---------------------------------------------------------------------------
# DNSQuery.response(): packet construction.
# ---------------------------------------------------------------------------


def test_response_builds_expected_packet_for_valid_domain() -> None:
    query = make_query(["a", "io"])
    packet = DNSQuery(query).response("192.168.4.1")
    assert packet is not None
    assert packet[:2] == query[:2]  # echoed transaction ID
    assert packet[2:4] == b"\x81\x80"  # standard response, recursion available
    assert packet[4:6] == query[4:6]  # QDCOUNT echoed
    assert packet[6:8] == query[4:6]  # ANCOUNT set equal to QDCOUNT
    assert packet[8:12] == b"\x00\x00\x00\x00"  # NSCOUNT, ARCOUNT
    question_len = len(query) - 12
    assert packet[12 : 12 + question_len] == query[12:]  # original question echoed
    offset = 12 + question_len
    assert packet[offset : offset + 2] == b"\xc0\x0c"  # compression pointer to the question name
    assert packet[offset + 2 : offset + 12] == b"\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"
    assert packet[offset + 12 : offset + 16] == bytes([192, 168, 4, 1])
    assert len(packet) == offset + 16


def test_response_returns_none_for_empty_domain() -> None:
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # non-standard query -> empty domain
    assert DNSQuery(bytes(data)).response("192.168.4.1") is None


# ---------------------------------------------------------------------------
# DNSServer: construction.
# ---------------------------------------------------------------------------


def test_dns_server_init_binds_the_standard_dns_port_in_server_mode() -> None:
    server = DNSServer(debug=True)
    assert server.udps._addr == ("0.0.0.0", 53)
    assert server.udps._mode == "server"
    assert server.udps.sock is None  # lazy - no real bind attempted at construction
    assert server.debug is True


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

    async def recvfrom(self, bufsize: int, timeout_ms: int = -1) -> tuple[bytes | None, tuple[str, int] | None]:
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

    async def disconnect(self) -> None:
        self.disconnect_called = True


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
        server = DNSServer(debug=False)
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
        server = DNSServer(debug=False)
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
        server = DNSServer(debug=False)
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
        server = DNSServer(debug=False)
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
    server = DNSServer(debug=False)

    async def scenario() -> None:
        await server.run("not-an-ip", "255.255.255.0")

    run(scenario())  # returns cleanly before ever touching udps - must not raise
    assert server.udps.sock is None


def test_run_cancellation_disconnects_cleanly() -> None:
    fake = _FakeUDPS([])

    async def scenario() -> None:
        server = DNSServer(debug=False)
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
        server = DNSServer(debug=False)
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


# ---------------------------------------------------------------------------
# One genuine end-to-end pass over a real loopback socket - proves DNSServer.run() actually binds,
# receives, and replies without crashing through AsyUDPSocket for real, not just via _FakeUDPS.
# ---------------------------------------------------------------------------


def test_run_handles_real_loopback_traffic_without_crashing() -> None:
    server_addr = resolve_addr("127.0.0.1", make_port())
    peer_addr = resolve_addr("127.0.0.1", make_port())

    async def scenario() -> bool:
        server = DNSServer(debug=False)
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
        try:
            _ipv4_to_int(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass


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
# DNSServer.__init__: constructor parameter configurations.
# ---------------------------------------------------------------------------


def test_dns_server_init_accepts_all_valid_debug_configurations() -> None:
    for debug in (True, False):
        server = DNSServer(debug=debug)
        assert server.debug is debug
        assert server.udps._addr == ("0.0.0.0", 53)
        assert server.udps._mode == "server"
    assert DNSServer().debug is False  # the default, omitted entirely


def test_dns_server_init_tolerates_non_bool_debug_values() -> None:
    # debug is only ever used in `if self.debug:` guards, never type-checked - a non-bool value
    # must not raise, and its truthiness must drive the same guard consistently. (__init__ takes
    # only this one parameter, so there is no "multiple invalid parameter" recombination to add.)
    for debug, expect_truthy in ((1, True), (0, False), ("x", True), ("", False), (None, False)):
        server = DNSServer(debug=debug)  # type: ignore[arg-type]
        assert bool(server.debug) is expect_truthy


# ---------------------------------------------------------------------------
# DNSServer.run(): server_ip/netmask startup-configuration matrix. Every invalid case asserts
# run() returns without raising and never attempts to bind (sock stays None) - exercising
# _ipv4_to_int's TypeError/ValueError/AttributeError guard at the top of run() without a live
# socket. The valid-configuration case does need a live loop iteration, so it goes through the
# fake transport and a real cancellable task, like the rest of this file's run() tests.
# ---------------------------------------------------------------------------


def _run_once_expect_clean_return(server: "DNSServer", server_ip: "Any", netmask: "Any") -> None:
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
        server = DNSServer(debug=False)
        server.udps = fake  # type: ignore[assignment]
        _run_briefly_and_cancel(server, server_ip, netmask)
        assert fake.disconnect_called is True  # reached the main loop, not the early-return path


def test_run_rejects_single_invalid_server_ip_parameter() -> None:
    for bad_ip in _bad_ipv4_values():
        server = DNSServer(debug=False)
        _run_once_expect_clean_return(server, bad_ip, "255.255.255.0")
        assert server.udps.sock is None  # never attempted to bind


def test_run_rejects_single_invalid_netmask_parameter() -> None:
    for bad_netmask in _bad_ipv4_values():
        server = DNSServer(debug=False)
        _run_once_expect_clean_return(server, "192.168.4.1", bad_netmask)
        assert server.udps.sock is None


def test_run_rejects_multiple_simultaneous_invalid_server_ip_and_netmask_recombinations() -> None:
    # Both parameters invalid at once, in several distinct fault-type combinations (not just the
    # same fault shape mirrored on both sides) - proves the guard doesn't depend on only one
    # parameter being bad at a time.
    for bad_ip, bad_netmask in (
        (None, "abc"),
        ("300.1.1.1", 123),
        ([1, 2, 3, 4], b"255.0.0.0"),
        ("1.2.3", "4.5.6.7.8"),
        ("", ""),
    ):
        server = DNSServer(debug=False)
        _run_once_expect_clean_return(server, bad_ip, bad_netmask)
        assert server.udps.sock is None


# ---------------------------------------------------------------------------
# DNSQuery.__init__: data/debug parameter configurations.
# ---------------------------------------------------------------------------


def test_dns_query_init_accepts_all_valid_data_configurations() -> None:
    assert DNSQuery(make_query(["single"])).domain == "single."
    assert DNSQuery(make_query(["multi", "label", "example"])).domain == "multi.label.example."
    assert DNSQuery(make_query(["a", "io"]), debug=True).domain == "a.io."
    assert DNSQuery(make_query(["a", "io"]), debug=False).domain == "a.io."


def _bad_dns_query_data_values() -> "list[Any]":
    # Wrong-type shapes for data, on top of the malformed-but-bytes shapes malformed_query_cases()
    # already covers. The real caller (run()) only ever passes bytes, but this constructor is
    # public and shouldn't rely on that discipline holding for every future/test caller.
    return [None, "a string, not bytes", 12345, 1.5, [1, 2, 3, 4], (1, 2, 3, 4)]


def test_dns_query_init_rejects_single_invalid_data_parameter_without_raising() -> None:
    for bad_data in _bad_dns_query_data_values():
        assert DNSQuery(bad_data).domain == ""


def test_dns_query_init_rejects_list_shaped_data_that_reaches_decode() -> None:
    # A sequence long enough to survive both integer-index lookups (data[2] and data[12]) but fail
    # specifically at self.domain += data[...].decode("utf-8") - a list slice has no .decode
    # method, exercising the AttributeError arm distinctly from the TypeError/IndexError arms the
    # shorter values above trigger.
    bad_data = [0] * 20
    bad_data[12] = 3  # claims a 3-byte label
    assert DNSQuery(bad_data).domain == ""  # type: ignore[arg-type]


def test_dns_query_init_rejects_multiple_invalid_parameter_recombinations() -> None:
    # Wrong-type data crossed with a wrong-type debug at the same time - two simultaneously
    # "invalid" (relative to their annotations) parameters, not just one at a time.
    for bad_data in _bad_dns_query_data_values():
        for bad_debug in (None, "yes", 1):
            assert DNSQuery(bad_data, debug=bad_debug).domain == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DNSQuery.response(): ip-parameter configuration matrix.
# ---------------------------------------------------------------------------


def test_response_accepts_edge_valid_ip_configurations() -> None:
    query = make_query(["a", "io"])
    for ip in ("0.0.0.0", "255.255.255.255", "10.0.0.1"):
        packet = DNSQuery(query).response(ip)
        assert packet is not None
        assert packet[-4:] == bytes(int(o) for o in ip.split("."))


def test_response_rejects_single_invalid_ip_parameter_without_raising() -> None:
    query = make_query(["a", "io"])
    for bad_ip in _bad_ipv4_values():
        assert DNSQuery(query).response(bad_ip) is None


def test_response_rejects_invalid_ip_combined_with_empty_domain_state() -> None:
    # domain=="" already short-circuits to None before ip is ever inspected - an invalid ip
    # combined with an already-invalid (empty-domain) object state must still just return None.
    data = bytearray(make_query(["a", "io"]))
    data[2] = 0x09  # non-standard opcode -> empty domain
    for bad_ip in _bad_ipv4_values():
        assert DNSQuery(bytes(data)).response(bad_ip) is None


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
    # Mirrors async_connect.py's real usage (confirmed directly against improved-quality/
    # async_connect.py): one DNSServer instance constructed once, with run() started, cancelled,
    # and started again across repeated hotspot activations - only safe because
    # AsyUDPSocket.disconnect() fully resets connected/sock state for _connect()'s next attempt.
    server_addr = resolve_addr("127.0.0.1", make_port())
    server = DNSServer(debug=False)
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
        server = DNSServer(debug=False)
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
# Integration contract: replicates async_connect.py's real DNSServer usage exactly. It cannot be
# imported directly here - it depends on network.WLAN and other RP2040-only hardware this
# environment doesn't have, and editing/testing it is out of scope per CLAUDE.md's promotion
# rules. Confirmed directly against improved-quality/async_connect.py: one DNSServer built once in
# __init__, run() started via evtloop.create_task(self.dns_server.run(own_ip, own_netmask)), and
# shut down via a fire-and-forget self.dns_server_task.cancel() that the caller never awaits.
# ---------------------------------------------------------------------------


def test_integration_survives_async_connects_fire_and_forget_cancel_pattern() -> None:
    server_addr = resolve_addr("127.0.0.1", make_port())

    async def scenario() -> "DNSServer":
        server = DNSServer(debug=False)
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
# dependency must still degrade to the 3s backoff rather than crash or busy-loop. This is the one
# fault category that genuinely cannot be produced for real - nothing in the legitimate processing
# path throws mid-packet - so it's simulated with a monkeypatched DNSQuery, matching this project's
# "mock only what's necessary" precedent (mocking a dependency, not the run() logic under test).
# ---------------------------------------------------------------------------


def test_run_backs_off_on_a_genuinely_unexpected_exception_then_recovers() -> None:
    import captive_dns as captive_dns_module

    real_dns_query = captive_dns_module.DNSQuery
    calls = {"n": 0}

    class _FlakyDNSQuery:
        def __init__(self, data: bytes, debug: bool = False) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated unexpected failure")
            self._real = real_dns_query(data, debug=debug)
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
            server = DNSServer(debug=False)
            server.udps = fake  # type: ignore[assignment]
            t0 = time.ticks_ms()
            task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
            try:
                assert await _wait_until(lambda: len(fake.sent) >= 1, timeout_ms=5000)
                return fake.sent, time.ticks_diff(time.ticks_ms(), t0)
            finally:
                await _cancel(task)
        finally:
            captive_dns_module.DNSQuery = real_dns_query  # type: ignore[misc]

    sent, elapsed_ms = run(scenario())
    assert len(sent) == 1
    assert sent[0][1] == ("127.0.0.5", 5001)  # the second, real request got through
    assert elapsed_ms >= 3000  # proves the 3s backoff genuinely ran, unlike the malformed-data path


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
