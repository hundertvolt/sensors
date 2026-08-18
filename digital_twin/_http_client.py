"""Minimal hand-rolled HTTP/1.1 client over asyncio.open_connection() - FINAL_WIRING_PLAN.md's
Step 5 needs to drive real HTTP requests against src/asy_webserver_service.py's real
asyncio.start_server()-backed WebserverService ("full HTTP, real sockets, real server" - owner
decision 2), and no HTTP client library is frozen into (or otherwise reliably available on) the
pinned MicroPython Unix-port build - confirmed directly, no urequests/requests import anywhere in
this repo's own dependency set. Matches this project's established hand-roll-when-a-library-isn't-
reliably-available convention (digital_twin/launch.py's own argparse fallback is the precedent).

Every response this client will ever see has "Connection: close" set (asy_webserver_service.py's
own _mark_connection_close(), added via Microdot's after_request/after_error_request hooks - see
that module's own docstring) - so this client never needs to support keep-alive, and reading until
EOF (read(-1), confirmed against the pinned v1.28.0 extmod/asyncio/stream.py source: Stream.read()
with a negative count accumulates until the underlying read returns b"") is always a safe fallback
for a response with no Content-Length header, even though every real response this client actually
sees does carry one in practice (Microdot's own Response.__init__ sets it whenever missing, and
send_file() sets it for static content too).

asyncio.open_connection() returns the *same* Stream object for both reader and writer (confirmed
directly: extmod/asyncio/stream.py aliases StreamReader = StreamWriter = Stream, and
open_connection() returns `(ss, ss)`) - callers of this module still receive two names for
readability/symmetry with Microdot's own reader/writer convention, they just happen to be the same
object. Stream.close() is a no-op by design on this build (`def close(self): pass`) - the actual
socket only closes via `await stream.wait_closed()`, which this module always calls in a finally.
"""

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
        body = await reader.readexactly(int(content_length)) if content_length is not None else await reader.read(-1)

        return HttpResponse(status_code, headers, body)
    finally:
        await writer.wait_closed()
