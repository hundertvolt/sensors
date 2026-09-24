"""Minimal hand-rolled HTTP/1.1 client over `asyncio.open_connection()` — no HTTP client library is frozen into the pinned MicroPython Unix-port build, so the twin's integration run hand-rolls one instead.
Every response it sees carries `Connection: close`, so no keep-alive support is needed. See `digital_twin/README.md`'s "What's here" section."""

import asyncio
import json

from _strict_json import check_strict_json

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


class HttpResponse:
    def __init__(self, status_code: int, headers: "dict[str, str]", body: "bytes | bytearray") -> None:
        self.status_code = status_code
        self.headers = headers
        # bytearray on the sized path (_read_exact()'s right-sized buffer, never re-copied),
        # bytes on the unsized one, or b"" when read_body=False drained the response instead of
        # materializing it - .json() must not be called on that. Nothing ever mutates it.
        self.body = body

    # Every body this client decodes is a JSON object - the REST envelope or a flat settings
    # dict - hence dict rather than a bare value. The value side stays Any because callers index
    # nested levels, which no non-Any JSON alias expresses without a cast at every site.
    def json(self) -> "dict[str, Any]":
        # Checked strictly first: the interpreter's json.loads() parses a separator slip the
        # browser's JSON.parse() rejects. Its stub types the argument AnyStr, refusing bytearray -
        # a stub gap only: mod_json_loads() reads any buffer (confirmed against the pinned source).
        check_strict_json(self.body)
        decoded: dict[str, Any] = json.loads(self.body)  # type: ignore[type-var]
        return decoded


def build_request(method: str, path: str, host: str, json_body: "dict[str, object] | None" = None) -> bytes:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host}", "Connection: close"]
    if json_body is not None:
        lines.append("Content-Type: application/json")
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


class CeilingRefusedError(OSError):
    """The server closed without writing any response at all - asy_webserver_service.py's
    reject-when-full branch. An OSError subclass because that is what a refusal is to every caller,
    and whether the peer sees FIN or RST is kernel TCP state that src/ does not choose."""


def parse_status_line(line: bytes) -> int:
    # e.g. b"HTTP/1.1 200 OK\r\n" -> 200. An EMPTY line is not a malformed response, it is a
    # connection closed before one was written - the same case tests_hardware/http_client.py's
    # CEILING_CLOSE covers by including http.client.BadStatusLine.
    if not line:
        raise CeilingRefusedError("server closed the connection without writing a response (reject-when-full)")
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


async def _read_exact(reader: "Any", n: int) -> bytearray:
    # One right-sized buffer filled through Stream.readinto(), never Stream.readexactly(), whose
    # `r += r2` accumulation is what fragments this heap under soak. README.md's
    # "_http_client.py's read paths" section has the full account and the measurements.

    # readinto() does one queue_read()+readinto() pair with no retry loop, so a spurious None -
    # poll said readable, the read came back empty - reaches here and must be retried. Only a
    # real 0 means the peer closed; conflating them reads as an intermittent false EOFError.
    buf = bytearray(n)
    view = memoryview(buf)
    got = 0
    while got < n:
        nread = await reader.readinto(view[got:])
        if nread == 0:
            raise EOFError
        if nread:
            got += nread
    return buf


_READ_UNTIL_CLOSE_CHUNK_BYTES = 1024


async def _read_until_close(reader: "Any") -> bytes:
    # The live path for GET /, not a rare fallback: send_file() hands the response a raw file
    # stream, so the automatic Content-Length never applies and EOF ends the body. Fixed-size
    # chunks joined once, for Stream.read(-1)'s same accumulation reason (README.md).

    # The b"".join(chunks) below is still one whole-body allocation, which is fine for a caller
    # that needs the bytes and wrong for one that does not - that caller takes
    # _drain_until_close(). README.md has the CI failure this distinction came from.
    chunks: list[bytes] = []
    scratch = bytearray(_READ_UNTIL_CLOSE_CHUNK_BYTES)
    while True:
        nread = await reader.readinto(scratch)
        if nread == 0:
            break
        if nread:
            chunks.append(bytes(scratch[:nread]))
    return b"".join(chunks)


async def _drain_until_close(reader: "Any") -> None:
    # _read_until_close()'s discard-everything sibling: each bounded chunk through one reused
    # scratch buffer, never accumulating or joining. For a caller that needs the connection
    # cleanly drained to EOF and never looks at the body (README.md).
    scratch = bytearray(_READ_UNTIL_CLOSE_CHUNK_BYTES)
    while True:
        nread = await reader.readinto(scratch)
        if nread == 0:
            break


async def _drain_exact(reader: "Any", n: int) -> None:
    # _read_exact()'s own discard-everything sibling, same reasoning as _drain_until_close() above -
    # one small reused scratch buffer, bounded reads, nothing accumulated or returned.
    scratch = bytearray(min(n, _READ_UNTIL_CLOSE_CHUNK_BYTES))
    got = 0
    while got < n:
        nread = await reader.readinto(memoryview(scratch)[: min(len(scratch), n - got)])
        if nread == 0:
            raise EOFError
        if nread:
            got += nread


async def fetch(
    host: str,
    port: int,
    method: str,
    path: str,
    json_body: "dict[str, object] | None" = None,
    *,
    read_body: bool = True,
) -> HttpResponse:
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
        # Sized bodies take _read_exact(), unsized ones _read_until_close(); neither accumulates
        # by concatenation. read_body=False takes the matching drain sibling, reading the same
        # bounded chunks but never materializing the body (README.md).
        body: bytes | bytearray = b""
        if read_body:
            body = await _read_exact(reader, int(content_length)) if content_length is not None else await _read_until_close(reader)
        elif content_length is not None:
            await _drain_exact(reader, int(content_length))
        else:
            await _drain_until_close(reader)

        return HttpResponse(status_code, headers, body)
    finally:
        await writer.wait_closed()
