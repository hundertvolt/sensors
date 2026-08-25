"""Minimal hand-rolled HTTP/1.1 client over `asyncio.open_connection()` — no HTTP client library is frozen into the pinned MicroPython Unix-port build, so the twin's integration run hand-rolls one instead.
Every request it sends carries its own `Connection: close` (deliberately, for one-request-per-connection simplicity), which `WebserverService` honors regardless of whether it would otherwise offer keep-alive (`src/asy_webserver_service.py`'s `_decide_connection_header()`) — so this client itself needs no keep-alive support. `tests/test_digital_twin_webserver_concurrency.py`'s own `_keep_alive_client()` is the one place in this codebase that drives real keep-alive reuse instead. See `digital_twin/README.md`'s "What's here" section."""

import asyncio
import json

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


class HttpResponse:
    def __init__(self, status_code: int, headers: "dict[str, str]", body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self.body = body

    def json(self) -> "Any":
        return json.loads(self.body)


def build_request(method: str, path: str, host: str, json_body: "Any | None" = None) -> bytes:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host}", "Connection: close"]
    if json_body is not None:
        lines.append("Content-Type: application/json")
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


def parse_status_line(line: bytes) -> int:
    # e.g. b"HTTP/1.1 200 OK\r\n" -> 200
    parts = line.split(b" ", 2)
    if len(parts) < 2:
        raise ValueError(f"malformed HTTP status line: {line!r}")
    return int(parts[1])


def parse_header_line(line: bytes) -> "tuple[str, str] | None":
    # None is the header-block terminator: either the blank line ("\r\n") every real response
    # sends, or an EOF-truncated readline() (b"") from a connection that closed mid-headers.
    if line in (b"", b"\r\n", b"\n"):
        return None
    name, _, value = line.decode().partition(":")
    return name.strip(), value.strip()


async def fetch(host: str, port: int, method: str, path: str, json_body: "Any | None" = None) -> HttpResponse:
    # reader/writer are the same underlying Stream object on this build (two names kept only for
    # readability/symmetry with Microdot's own convention) - close() is a no-op here, the socket
    # only actually closes via wait_closed() in the finally below.
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(build_request(method, path, host, json_body))
        await writer.drain()

        status_code = parse_status_line(await reader.readline())
        headers: dict[str, str] = {}
        while True:
            parsed = parse_header_line(await reader.readline())
            if parsed is None:
                break
            name, value = parsed
            headers[name] = value

        content_length = headers.get("Content-Length")
        # read(-1) reads until EOF - a safe fallback for a missing Content-Length, though every real
        # response this client sees does carry one (Microdot sets it whenever missing).
        body = await reader.readexactly(int(content_length)) if content_length is not None else await reader.read(-1)

        return HttpResponse(status_code, headers, body)
    finally:
        await writer.wait_closed()
