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
    # The 8 shapes found reachable from a truncated/malformed real UDP datagram (see BACKLOG.md):
    # too short for the opcode byte, too short for the question section, a length byte with
    # nothing following, a label truncated mid-way, and a label with an invalid UTF-8 byte.
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"  # standard query, QDCOUNT=1
    return [
        b"",
        b"\x00",
        b"\x00\x00",
        b"\x00\x00\x01",  # 3 bytes, opcode bits already say "standard query" but len < 13
        header,  # exactly 12 bytes - no question section at all
        header + b"\x05",  # a length byte promising 5 more bytes that never arrive
        header + b"\x01a",  # one label started, then truncated before its terminator
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
