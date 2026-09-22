"""Deterministic unit tests for digital_twin/_http_client.py's pure request/response parsing plus
one real end-to-end socket round trip - its own file since _http_client.py is shared by every
digital-twin entry point, not owned by any one of them."""

import asyncio
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import _http_client as http_client


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# build_request() - request byte assembly
# ---------------------------------------------------------------------------


def test_build_request_get_has_no_body_and_no_content_type() -> None:
    req = http_client.build_request("GET", "/status", "localhost")
    assert req.startswith(b"GET /status HTTP/1.1\r\n")
    assert b"Content-Type" not in req
    assert b"Content-Length: 0\r\n" in req
    assert req.endswith(b"\r\n\r\n")


def test_build_request_put_includes_a_json_body_and_content_type() -> None:
    req = http_client.build_request("PUT", "/notification", "localhost", {"WarnCO2": 1800})
    header, _, body = req.partition(b"\r\n\r\n")
    assert b"PUT /notification HTTP/1.1" in header
    assert b"Content-Type: application/json" in header
    assert body == b'{"WarnCO2": 1800}'
    assert f"Content-Length: {len(body)}".encode() in header


def test_build_request_always_asks_for_connection_close() -> None:
    # asy_webserver_service.py's own _mark_connection_close() always sets this on the response too -
    # this client never implements keep-alive (see this file's own module docstring).
    req = http_client.build_request("GET", "/", "localhost")
    assert b"Connection: close\r\n" in req


def test_build_request_includes_the_host_header() -> None:
    req = http_client.build_request("GET", "/measurements", "127.0.0.1")
    assert b"Host: 127.0.0.1\r\n" in req


# ---------------------------------------------------------------------------
# parse_status_line() - status-line parsing
# ---------------------------------------------------------------------------


def test_parse_status_line_extracts_the_numeric_code() -> None:
    assert http_client.parse_status_line(b"HTTP/1.1 200 OK\r\n") == 200
    assert http_client.parse_status_line(b"HTTP/1.1 404 Not found\r\n") == 404


def test_parse_status_line_rejects_a_malformed_line() -> None:
    try:
        http_client.parse_status_line(b"garbage\r\n")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_an_empty_status_line_is_a_refusal_not_a_malformed_response() -> None:
    # The server's reject-when-full branch closes without writing anything, so the client reads
    # b"". That is a connection outcome, not a broken response, and every caller already treats a
    # refusal as OSError - mirroring tests_hardware/http_client.py's CEILING_CLOSE, which covers
    # the same case by including http.client.BadStatusLine.
    try:
        http_client.parse_status_line(b"")
        raise AssertionError("expected CeilingRefusedError")
    except http_client.CeilingRefusedError:
        pass


def test_a_ceiling_refusal_is_catchable_as_a_plain_oserror() -> None:
    # Load-bearing: the concurrency scenarios classify a refusal with `except OSError`, and a
    # ValueError there escaped as a test failure under a burst big enough to make FIN-without-bytes
    # the common outcome rather than RST.
    assert issubclass(http_client.CeilingRefusedError, OSError)
    try:
        http_client.parse_status_line(b"")
        raise AssertionError("expected an OSError")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# parse_header_line() - header-line parsing
# ---------------------------------------------------------------------------


def test_parse_header_line_splits_name_and_value() -> None:
    assert http_client.parse_header_line(b"Content-Length: 42\r\n") == ("Content-Length", "42")


def test_parse_header_line_strips_surrounding_whitespace() -> None:
    assert http_client.parse_header_line(b"Content-Type:   application/json  \r\n") == ("Content-Type", "application/json")


def test_parse_header_line_returns_none_for_the_blank_terminator() -> None:
    assert http_client.parse_header_line(b"\r\n") is None
    assert http_client.parse_header_line(b"\n") is None
    assert http_client.parse_header_line(b"") is None  # EOF-truncated readline()


# ---------------------------------------------------------------------------
# _read_exact() - fills one right-sized buffer across as many partial readinto() rounds as the stream
# delivers, extmod/asyncio/stream.py's Stream.readinto() doing exactly one non-accumulating read per call.
# It replaces readexactly()'s `r += r2` growth, which made a multi-KB body an allocate-copy-discard cycle.
# ---------------------------------------------------------------------------


class _ChunkedReader:
    # A fake stream whose readinto() hands back one pre-scripted chunk per call, like a real socket
    # splitting a body across TCP segments - proving the loop actually loops, not just that it works when
    # the first call delivers everything.
    #
    # A scripted `None` models Stream.readinto()'s spurious-wake race - poll said readable, the read still
    # came back empty - which must be retried, never treated as EOF; only a real b"" may be.
    def __init__(self, chunks: "list[bytes | None]") -> None:
        self._chunks = list(chunks)

    async def readinto(self, buf: bytearray) -> "int | None":
        if not self._chunks:
            return 0
        chunk = self._chunks.pop(0)
        if chunk is None:
            return None
        n = len(chunk)
        buf[:n] = chunk
        return n


def test_read_exact_fills_the_buffer_across_multiple_partial_reads() -> None:
    reader = _ChunkedReader([b"abc", b"de", b"fgh"])
    result = run_timed(http_client._read_exact(reader, 8))
    assert bytes(result) == b"abcdefgh"


def test_read_exact_returns_a_right_sized_buffer_for_a_single_read() -> None:
    reader = _ChunkedReader([b"hello"])
    result = run_timed(http_client._read_exact(reader, 5))
    assert bytes(result) == b"hello"
    assert len(result) == 5


def test_read_exact_raises_eof_on_premature_stream_closure() -> None:
    # Only 2 of the 5 requested bytes ever arrive, then the stream reports EOF (readinto() -> 0) -
    # matches Stream.readexactly()'s own EOFError contract exactly (extmod/asyncio/stream.py).
    reader = _ChunkedReader([b"ab"])
    try:
        run_timed(http_client._read_exact(reader, 5))
        raise AssertionError("expected EOFError")
    except EOFError:
        pass


def test_read_exact_retries_a_spurious_none_read_instead_of_treating_it_as_eof() -> None:
    # The regression this exists to catch: Stream.readinto() can legitimately return None right after poll()
    # said the socket was readable, and Stream.read() one function up explicitly retries on that same race.
    #
    # A first version of _read_exact() conflated None with a real 0-byte EOF, which read as an intermittent,
    # false "connection closed" under exactly the scheduling jitter a busy CI runner produces more of.
    reader = _ChunkedReader([None, b"ab", None, b"c"])
    result = run_timed(http_client._read_exact(reader, 3))
    assert bytes(result) == b"abc"


# ---------------------------------------------------------------------------
# _read_until_close() - the unsized fallback path GET / actually takes (Microdot's send_file()
# passes a raw stream body, so no Content-Length is ever set - see this function's own comment).
# ---------------------------------------------------------------------------


class _EofReader:
    # Like _ChunkedReader, but readinto() always fills as much of the caller's buffer as the current chunk
    # allows, mirroring a real socket, which fills whatever room it is given rather than returning its chunk
    # verbatim - proving _read_until_close() bounds each read to len(buf), not the scripted chunk's length.
    def __init__(self, chunks: "list[bytes | None]") -> None:
        self._chunks = list(chunks)

    async def readinto(self, buf: bytearray) -> "int | None":
        if not self._chunks:
            return 0
        chunk = self._chunks.pop(0)
        if chunk is None:
            return None
        n = min(len(chunk), len(buf))
        buf[:n] = chunk[:n]
        if n < len(chunk):
            self._chunks.insert(0, chunk[n:])
        return n


def test_read_until_close_joins_chunks_across_multiple_reads() -> None:
    reader = _EofReader([b"abc", b"de", b"fgh"])
    result = run_timed(http_client._read_until_close(reader))
    assert result == b"abcdefgh"
    assert isinstance(result, bytes)


def test_read_until_close_retries_a_spurious_none_read() -> None:
    reader = _EofReader([None, b"ab", None, b"c"])
    result = run_timed(http_client._read_until_close(reader))
    assert result == b"abc"


def test_read_until_close_bounds_each_read_to_the_scratch_buffer_size() -> None:
    # A chunk bigger than the internal scratch buffer must be split across multiple readinto()
    # rounds, not silently truncated - proving the "reuse one fixed-size buffer" design actually
    # bounds allocation size the way it claims to, not just that the end result happens to be right.
    original = http_client._READ_UNTIL_CLOSE_CHUNK_BYTES
    http_client._READ_UNTIL_CLOSE_CHUNK_BYTES = 4
    try:
        reader = _EofReader([b"0123456789"])
        result = run_timed(http_client._read_until_close(reader))
    finally:
        http_client._READ_UNTIL_CLOSE_CHUNK_BYTES = original
    assert result == b"0123456789"


def test_read_until_close_returns_empty_bytes_for_an_immediately_closed_stream() -> None:
    reader = _EofReader([])
    result = run_timed(http_client._read_until_close(reader))
    assert result == b""


# ---------------------------------------------------------------------------
# _drain_exact()/_drain_until_close() - fetch(read_body=False)'s discard-everything siblings, and the real
# fix for a digital-twin CI regression: dev's largest frozen website, 7579 bytes, tipped
# _read_until_close()'s final b"".join() over a fragmented-heap edge the smaller sites did not.
#
# _soak() and _wait_until_serving() never look at a fetched body, so they must never materialize one.
# ---------------------------------------------------------------------------


def test_drain_exact_consumes_every_byte_without_returning_anything() -> None:
    reader = _ChunkedReader([b"abc", b"de", b"fgh"])
    result = run_timed(http_client._drain_exact(reader, 8))
    assert result is None


def test_drain_exact_raises_eof_on_premature_stream_closure() -> None:
    reader = _ChunkedReader([b"ab"])
    try:
        run_timed(http_client._drain_exact(reader, 5))
        raise AssertionError("expected EOFError")
    except EOFError:
        pass


def test_drain_exact_retries_a_spurious_none_read_instead_of_treating_it_as_eof() -> None:
    reader = _ChunkedReader([None, b"ab", None, b"c"])
    run_timed(http_client._drain_exact(reader, 3))  # no exception raised is the assertion


def test_drain_exact_bounds_its_own_scratch_buffer_to_the_shared_chunk_size() -> None:
    # A body bigger than _READ_UNTIL_CLOSE_CHUNK_BYTES must still drain correctly across multiple
    # bounded reads, not allocate one n-byte buffer up front - the exact allocation this function
    # exists to avoid (see this section's own comment).
    original = http_client._READ_UNTIL_CLOSE_CHUNK_BYTES
    http_client._READ_UNTIL_CLOSE_CHUNK_BYTES = 4
    try:
        reader = _EofReader([b"0123456789"])
        run_timed(http_client._drain_exact(reader, 10))
    finally:
        http_client._READ_UNTIL_CLOSE_CHUNK_BYTES = original


def test_drain_until_close_consumes_every_chunk_without_returning_anything() -> None:
    reader = _EofReader([b"abc", b"de", b"fgh"])
    result = run_timed(http_client._drain_until_close(reader))
    assert result is None


def test_drain_until_close_retries_a_spurious_none_read() -> None:
    reader = _EofReader([None, b"ab", None, b"c"])
    run_timed(http_client._drain_until_close(reader))  # no exception raised is the assertion


def test_drain_until_close_returns_for_an_immediately_closed_stream() -> None:
    reader = _EofReader([])
    run_timed(http_client._drain_until_close(reader))  # no exception raised is the assertion


# ---------------------------------------------------------------------------
# HttpResponse.json() - response-body decoding
# ---------------------------------------------------------------------------


def test_http_response_json_decodes_the_body() -> None:
    res = http_client.HttpResponse(200, {}, b'{"res": "OK"}')
    assert res.json() == {"res": "OK"}


# ---------------------------------------------------------------------------
# fetch() - one real end-to-end smoke test against a minimal hand-built asyncio.start_server(), proving the
# whole wire protocol round-trips: request bytes out, status, headers and body parsed back in.
#
# The same "does the mechanism work at all" spirit as the launch and machine suites' own smoke tests, not a
# claim about src/asy_webserver_service.py's behavior - that is the twin integration suite's job.
# ---------------------------------------------------------------------------


async def _canned_server(reader: "asyncio.StreamReader", writer: "asyncio.StreamWriter") -> None:
    await reader.readline()  # request line - ignored, this fake always answers the same way
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
    body = b'{"ok": true}'
    writer.write(f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body)
    await writer.drain()
    await writer.wait_closed()


def test_fetch_round_trips_a_real_request_through_a_real_socket() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_canned_server, "127.0.0.1", 18099)
        try:
            res = await http_client.fetch("127.0.0.1", 18099, "GET", "/anything")
            assert res.status_code == 200
            assert res.json() == {"ok": True}
        finally:
            server.close()
            await server.wait_closed()

    run_timed(scenario(), timeout_s=5.0)


async def _canned_server_split_body(reader: "asyncio.StreamReader", writer: "asyncio.StreamWriter") -> None:
    # Writes the body across two separate drain()s with a real yield between them, forcing fetch()'s
    # own _read_exact() to actually loop - proves the fix over a real socket, not only against
    # _ChunkedReader's own scripted fake.
    await reader.readline()
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
    body = b'{"a": 1, "b": 2}'
    half = len(body) // 2
    writer.write(f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body[:half])
    await writer.drain()
    await asyncio.sleep_ms(20)
    writer.write(body[half:])
    await writer.drain()
    await writer.wait_closed()


def test_fetch_reassembles_a_body_delivered_across_two_separate_writes() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_canned_server_split_body, "127.0.0.1", 18100)
        try:
            res = await http_client.fetch("127.0.0.1", 18100, "GET", "/anything")
            assert res.status_code == 200
            assert res.json() == {"a": 1, "b": 2}
        finally:
            server.close()
            await server.wait_closed()

    run_timed(scenario(), timeout_s=5.0)


async def _canned_server_no_content_length(reader: "asyncio.StreamReader", writer: "asyncio.StreamWriter") -> None:
    # Matches GET /'s real shape, the static-file route via Response.send_file() passing a raw stream body:
    # no Content-Length at all, body delivered across several writes, and EOF - this connection closing -
    # ends it. Exactly the shape that sent every real GET / through the unsized path.
    await reader.readline()
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
    body = b"x" * 3000  # bigger than _read_until_close()'s own default 1024-byte scratch buffer
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n")
    await writer.drain()
    for offset in range(0, len(body), 777):  # deliberately not a multiple of the scratch buffer
        writer.write(body[offset : offset + 777])
        await writer.drain()
    await writer.wait_closed()


def test_fetch_reads_a_body_with_no_content_length_until_the_connection_closes() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_canned_server_no_content_length, "127.0.0.1", 18101)
        try:
            res = await http_client.fetch("127.0.0.1", 18101, "GET", "/anything")
            assert res.status_code == 200
            assert "Content-Length" not in res.headers
            assert res.body == b"x" * 3000
        finally:
            server.close()
            await server.wait_closed()

    run_timed(scenario(), timeout_s=5.0)


# ---------------------------------------------------------------------------
# fetch(read_body=False) - the actual fix for the digital-twin CI regression the _drain_* tests above
# document. Both real-socket paths, sized via Content-Length and unsized via connection-close, must report
# the real status_code while never materializing a body: it comes back b"", which callers must not decode.
# ---------------------------------------------------------------------------


def test_fetch_with_read_body_false_drains_a_sized_response_without_materializing_it() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_canned_server, "127.0.0.1", 18102)
        try:
            res = await http_client.fetch("127.0.0.1", 18102, "GET", "/anything", read_body=False)
            assert res.status_code == 200
            assert res.body == b""
        finally:
            server.close()
            await server.wait_closed()

    run_timed(scenario(), timeout_s=5.0)


def test_fetch_with_read_body_false_drains_an_unsized_response_without_materializing_it() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_canned_server_no_content_length, "127.0.0.1", 18103)
        try:
            res = await http_client.fetch("127.0.0.1", 18103, "GET", "/anything", read_body=False)
            assert res.status_code == 200
            assert "Content-Length" not in res.headers
            assert res.body == b""
        finally:
            server.close()
            await server.wait_closed()

    run_timed(scenario(), timeout_s=5.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
