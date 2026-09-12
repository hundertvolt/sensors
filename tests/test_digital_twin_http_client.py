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
# HttpResponse.json() - response-body decoding
# ---------------------------------------------------------------------------


def test_http_response_json_decodes_the_body() -> None:
    res = http_client.HttpResponse(200, {}, b'{"res": "OK"}')
    assert res.json() == {"res": "OK"}


# ---------------------------------------------------------------------------
# fetch() - one real end-to-end smoke test against a minimal hand-built asyncio.start_server(),
# proving the whole wire protocol round-trips correctly (request bytes out, status/headers/body
# parsed back in) - same "does the mechanism work at all" spirit test_digital_twin_launch.py's own
# main() smoke test and test_digital_twin_machine.py's own Timer/WDT live-timing tests already use,
# not a claim about src/asy_webserver_service.py's own behavior (that's this file's other sibling,
# tests/test_digital_twin_sensortask_integration.py's, job).
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
