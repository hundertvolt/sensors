"""Minimal HTTP/1.1 client over asyncio.open_connection(): real HTTP over real sockets (owner, 2026-08-13), hand-rolled
because the Unix-port build freezes no client library. tests_hardware/http_client.py keeps the same shape, pinned by
tests_scripts/test_http_client_shape_parity.py."""

import asyncio
import errno
import json

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    from asy_base_classes import JsonDict

    class _Reader(Protocol):
        # What the body readers take: one non-accumulating readinto() per call (extmod/asyncio/stream.py).
        async def readinto(self, buf: "bytearray | memoryview") -> "int | None": ...

    class _Stream(_Reader, Protocol):
        async def drain(self) -> None: ...
        # MicroPython's one Stream serves both directions (extmod/asyncio/stream.py).
        async def readline(self) -> bytes: ...
        async def wait_closed(self) -> None: ...
        def write(self, data: bytes) -> None: ...


class HttpResponse:
    def __init__(self, status_code: int, headers: "dict[str, str]", body: "bytes | bytearray", *, drained: bool = False) -> None:
        self.status_code = status_code
        self.headers = headers
        # bytearray on the sized path (_read_exact()'s right-sized buffer, never re-copied), bytes on the unsized one,
        # or b"" with `drained` set when read_body=False drained the response unkept. Nothing ever mutates it.
        self.body = body
        self.drained = drained

    # Every body this client decodes is a JSON object - the REST envelope or a flat settings dict.
    def json(self) -> "JsonDict":
        # Checked strictly first: the interpreter's json.loads() parses a separator slip the browser's JSON.parse() rejects.
        # The ignore below goes when micropython-stdlib-stubs types json.loads() for bytearray (a stub gap only:
        # mod_json_loads() reads any buffer, v1.29.0 extmod/modjson.c).
        from _strict_json import check_strict_json  # here, not at the top: tests/ is absent from a standalone twin's path

        if self.drained:
            raise ValueError("json() on a drained response")
        check_strict_json(self.body)
        decoded: JsonDict = json.loads(self.body)  # type: ignore[type-var]
        return decoded


async def _drain_exact(reader: "_Reader", n: int) -> None:
    # _read_exact()'s own discard-everything sibling, same reasoning as _drain_until_close() above -
    # one small reused scratch buffer, bounded reads, nothing accumulated or returned.
    scratch = bytearray(min(n, _READ_UNTIL_CLOSE_CHUNK_BYTES))
    got = 0
    while got < n:
        nread = await reader.readinto(memoryview(scratch)[: min(len(scratch), n - got)])
        if nread == 0:
            raise IncompleteResponseError("connection closed inside the body")
        if nread:
            got += nread


class CeilingRefusedError(OSError):
    # The server closed without writing any response at all - asy_webserver_service.py's
    # reject-when-full branch. An OSError subclass because that is what a refusal is to every caller,
    # and whether the peer sees FIN or RST is kernel TCP state that src/ does not choose.
    pass


class IncompleteResponseError(OSError):
    """The server began a response and closed before finishing its header block or body."""


async def _drain_until_close(reader: "_Reader") -> None:
    # _read_until_close()'s discard-everything sibling: each bounded chunk through one reused
    # scratch buffer, never accumulating or joining. For a caller that needs the connection
    # cleanly drained to EOF and never looks at the body (README.md).
    scratch = bytearray(_READ_UNTIL_CLOSE_CHUNK_BYTES)
    while True:
        nread = await reader.readinto(scratch)
        if nread == 0:
            break


async def _exchange(reader: "_Stream", writer: "_Stream", host: str, method: str, path: str, json_body: "dict[str, object] | None", *, read_body: bool) -> HttpResponse:
    # reader and writer are one Stream on this build; the socket closes only in fetch()'s wait_closed(). Every response
    # this client sees carries Connection: close, so one exchange is the whole connection.
    try:
        writer.write(build_request(method, path, host, json_body))
        await writer.drain()
        status_code = parse_status_line(await reader.readline())
    except CeilingRefusedError:
        raise
    except OSError as e:
        if e.errno == errno.ECONNREFUSED:
            raise  # nothing listening: the non-blocking connect's failure surfaces at the first write
        # A reset before any response byte is the same refusal as a close without one (no `from e`: MicroPython
        # prints "exception chaining not supported" for it).
        raise CeilingRefusedError(e.errno, "connection refused without a response (reject-when-full)")
    try:
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
    except IncompleteResponseError:
        raise
    except OSError as e:  # the response began: any later failure leaves it incomplete
        # No `from e`: MicroPython prints "exception chaining not supported" for it (py/vm.c, v1.29.0).
        raise IncompleteResponseError(e.errno, "connection failed inside the response")
    return HttpResponse(status_code, headers, body, drained=not read_body)


async def _read_exact(reader: "_Reader", n: int) -> bytearray:
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
            raise IncompleteResponseError("connection closed inside the body")
        if nread:
            got += nread
    return buf


_READ_UNTIL_CLOSE_CHUNK_BYTES = 1024


async def _read_until_close(reader: "_Reader") -> bytes:
    # The fallback for a body with no Content-Length, which EOF ends: the webserver sends the header on
    # every response, GET / included, so fetch() reads those through _read_exact(). Fixed-size
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


def build_request(method: str, path: str, host: str, json_body: "dict[str, object] | None" = None) -> bytes:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host}", "Connection: close"]
    if json_body is not None:
        lines.append("Content-Type: application/json")
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


async def fetch(
    host: str,
    port: int,
    method: str,
    path: str,
    json_body: "dict[str, object] | None" = None,
    timeout_s: "float | None" = None,
    *,
    read_body: bool = True,
) -> HttpResponse:
    # With timeout_s the whole exchange runs under asyncio.wait_for(), whose TimeoutError propagates; None waits as
    # long as the server does. open_connection()'s own OSError (nothing listening) propagates unchanged.
    reader, writer = await asyncio.open_connection(host, port)
    stream: _Stream = reader  # type: ignore[assignment]  # MicroPython's StreamReader is its one Stream, writer included
    try:
        exchange = _exchange(stream, stream, host, method, path, json_body, read_body=read_body)
        return await (exchange if timeout_s is None else asyncio.wait_for(exchange, timeout_s))
    finally:
        await writer.wait_closed()


def parse_header_line(line: bytes) -> "tuple[str, str] | None":
    # None ends the header block; an EOF before the blank line is an incomplete response.
    if not line:
        raise IncompleteResponseError("connection closed inside the header block")
    if line in (b"\r\n", b"\n"):
        return None
    name, _, value = line.decode().partition(":")
    return name.strip(), value.strip()


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
