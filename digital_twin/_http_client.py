"""Minimal hand-rolled HTTP/1.1 client over `asyncio.open_connection()` — no HTTP client library is frozen into the pinned MicroPython Unix-port build, so the twin's integration run hand-rolls one instead.
Every response it sees carries `Connection: close`, so no keep-alive support is needed. See `digital_twin/README.md`'s "What's here" section."""

import asyncio
import json

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
        # bytearray on the sized/common path (_read_exact()'s own right-sized buffer, never copied
        # into a fresh bytes object - see its own comment for why), bytes on the unsized fallback
        # (Stream.read(-1)'s own return type), or b"" when fetch()'s own read_body=False drained the
        # response instead of materializing it (see fetch()'s own comment - .json() must not be
        # called on a body fetched this way). Nothing here or in any caller mutates it either way.
        self.body = body

    # Every response body this client is ever asked to decode is a JSON *object* (the REST layer's
    # own make_response() envelope, or a flat settings dict) - hence dict, not a bare value. The
    # value side stays Any: callers index nested levels (res.json()["notification"]["PauseTime"]),
    # which no non-Any JSON alias can express without a cast at every call site.
    def json(self) -> "dict[str, Any]":
        # json.loads()'s stub types its argument AnyStr (str | bytes), rejecting bytearray - a stub
        # gap, not a real runtime restriction: extmod/modjson.c's own mod_json_loads() reads through
        # mp_get_buffer_raise(), the generic buffer protocol, which bytearray fully implements
        # (confirmed directly against the pinned interpreter's own source).
        decoded: dict[str, Any] = json.loads(self.body)  # type: ignore[type-var]
        return decoded


def build_request(method: str, path: str, host: str, json_body: "dict[str, object] | None" = None) -> bytes:
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


async def _read_exact(reader: "Any", n: int) -> bytearray:
    # extmod/asyncio/stream.py's own Stream.readexactly() accumulates via `r += r2` on every
    # partial read - a fresh, larger contiguous bytes object each time, immediately abandoning the
    # previous one. For a several-KB body arriving over several TCP reads that is several
    # progressively bigger allocate-copy-discard cycles per fetch(), which is exactly the pattern
    # that fragments this heap under repeated soak cycles (confirmed directly against the pinned
    # interpreter's own extmod/asyncio/stream.py). Reading into one right-sized buffer via
    # Stream.readinto() - which does exist, and does a single non-accumulating read per call, so it
    # must itself be looped to fill the buffer - costs exactly one allocation per fetch() instead,
    # done once we already know the final size. No explicit gc.collect() is needed anywhere for
    # this: py/gc.c's own gc_alloc() already runs a full collect-and-retry before ever raising
    # MemoryError (confirmed directly against the pinned interpreter's own source), so a stale
    # previous response's garbage is reclaimed automatically, exactly when an allocation actually
    # needs the room - forcing it early changes nothing but timing.
    # Stream.readinto() does exactly one queue_read()+readinto() pair, not Stream.read()'s own
    # retry-on-None loop (same file, a few lines up) - so a spurious None (poll said readable, the
    # actual read still came back empty - the exact race Stream.read()'s own loop is written to
    # ride out) reaches this caller directly and must be retried, never treated as EOF. Only a real
    # 0 means the peer closed. Getting this wrong reads as an intermittent, environment-dependent
    # false EOFError under scheduling jitter a quieter sandbox rarely reproduces - confirmed the
    # hard way, this file's own first version conflated the two.
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
    # The live path for GET / (the frozen website): ext/microdot.py's Response.send_file() passes a
    # raw file stream as the body, so Response.complete()'s auto-Content-Length (`len(self.body)`)
    # never applies - confirmed directly by reading it - and Connection: close (this client always
    # sends it) plus EOF is how the response actually ends. Not a rarely-taken fallback, as this
    # file's own first version of fetch() assumed. Same growth-by-concatenation problem as
    # Stream.readexactly() (`r += r2` on every partial read, extmod/asyncio/stream.py's own
    # Stream.read(-1)) and the same fix in spirit: fixed-size (bounded, never growing) chunks
    # collected in a list and joined exactly once, instead of one bigger contiguous copy per read.
    #
    # The final b"".join(chunks) below is still one allocation the size of the whole body (~7.5KB
    # for the largest real device's own frozen website) - fine for a caller that actually needs the
    # bytes (test_digital_twin_real_website_integration.py decompresses and verifies real content),
    # but real hardware never does this: production's own browser client assembles the body from
    # Microdot's own 1KB send_file_buffer_size chunks over the wire, so no real device process ever
    # holds one contiguous ~7.5KB buffer for this route. A caller with no use for the bytes
    # (_soak()/_wait_until_serving(), which only ever check status_code) should take
    # _drain_until_close() instead - see SPECIFICATION.md Part I.4(g): relieve the pressure at its
    # source (never materialize what nothing needs), not paper over an avoidable allocation with a
    # GC-policy change. Found via a real digital-twin CI failure this discipline itself caught: the
    # `dev` device's own frozen website (7579 bytes, ~168-483 bytes bigger than the other 5 real
    # devices') tipped this exact allocation over a fragmented-heap edge under gc.threshold(-1) that
    # wozi's/arzi's own, slightly smaller sites didn't - the fix is calling _drain_until_close() from
    # the hot soak loop, not shrinking anything or reaching for a threshold.
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
    # _read_until_close()'s own discard-everything sibling: reads and throws away each bounded
    # chunk via one reused scratch buffer, never accumulating a list or joining a final buffer - the
    # correct choice for a caller that only needs the connection fully, cleanly drained (so
    # Connection: close's own EOF is reached and the socket can close) and never looks at the body
    # itself. See _read_until_close()'s own comment for why this exists and the real regression it fixes.
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
        # Sized (JSON envelopes, most REST responses) takes _read_exact(); unsized (GET / - see
        # _read_until_close()'s own comment for why this is a live, heavily-used path, not a rare
        # fallback) takes _read_until_close(). Neither ever accumulates via growth-by-concatenation.
        # read_body=False (a caller that only checks status_code, e.g. _soak()) takes either drain
        # sibling instead - same bounded-chunk reads, but never materializing/returning the body -
        # see _read_until_close()'s own comment for the real regression this avoids.
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
