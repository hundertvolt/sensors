"""Host-side HTTP client (CPython's urllib only) for the bench tier's live-system checks: synchronous, but of
digital_twin/_http_client.py's shape, pinned by tests_scripts/test_http_client_shape_parity.py, so a check written
against one runs against the other. Both rely on the server answering every request with `Connection: close`."""

import http.client
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from email.message import Message
    from typing import Protocol

    class _Body(Protocol):
        # What a body is read from: urlopen()'s response, or the HTTPError carrying a non-2xx one.
        def read(self, amt: int = ..., /) -> bytes: ...


# The REST payloads this client sends and decodes: JSON values, and the one object every endpoint answers with.
JSONValue: TypeAlias = bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"] | None
JSONObject: TypeAlias = dict[str, JSONValue]

# @tunable l4.http_client_fetch_timeout_s = 10.0
_FETCH_TIMEOUT_S = 10.0
_DRAIN_CHUNK_BYTES = 4096  # read_body=False reads the body off the connection in pieces this size, keeping none


class CeilingRefusedError(ConnectionError):
    # The server closed at its max_connections ceiling before writing any response byte (_serve()'s reject-when-full
    # branch); the cause is the transport error the client saw. The twin client's is the same refusal.
    pass


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    drained: bool = False  # read_body=False: the body was read off the connection and dropped

    def json(self) -> JSONObject:
        # Every endpoint this tier talks to answers with a JSON object: a drained body or any other JSON value raises.
        if self.drained:
            raise ValueError("json() on a drained response")
        decoded = json.loads(self.body)
        if not isinstance(decoded, dict):
            raise TypeError(f"the response body is a JSON {type(decoded).__name__}, not an object")
        return decoded


# A connection the server closed at its own max_connections ceiling, whose shape src/ does not choose: _serve()'s
# reject-when-full branch closes without ever writing a response, so the client sees FIN or RST depending on kernel
# TCP state (both measured on the bench).
CEILING_CLOSE = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, http.client.BadStatusLine)


# A malformed or cut-off answer - a body short of its Content-Length, a garbled status line. An
# HTTPException, not an OSError, so a caller catching transport failures has to name it too.
HTTP_ERROR = http.client.HTTPException


def _refused(exc: BaseException) -> bool:
    # A ceiling close seen before any response byte: a CEILING_CLOSE shape, bare or as URLError's reason - except a
    # BadStatusLine holding a line (an empty one it stores as its repr), whose garbled status line is an answer.
    cause = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    return isinstance(cause, CEILING_CLOSE) and not (isinstance(cause, http.client.BadStatusLine) and getattr(cause, "line", "") not in ("", repr("")))


def _response(status_code: int, headers: "Message", stream: "_Body", *, read_body: bool) -> HttpResponse:
    if read_body:
        return HttpResponse(status_code, dict(headers), stream.read())
    while stream.read(_DRAIN_CHUNK_BYTES):
        pass
    return HttpResponse(status_code, dict(headers), b"", drained=True)


def is_ceiling_close(exc: BaseException) -> bool:
    # For the callers that predate the class: fetch()'s refusal, never a transport failure or a response cut short.
    return isinstance(exc, CeilingRefusedError)


def fetch(host: str, port: int, method: str, path: str, json_body: JSONObject | None = None, timeout_s: float = _FETCH_TIMEOUT_S, *, read_body: bool = True) -> HttpResponse:
    # One request. A non-2xx answer is a response like any other (a validation failure carries a real JSON body); a
    # refusal before any response byte raises CeilingRefusedError, its cause kept. read_body=False drains the body unkept.
    url = f"http://{host}:{port}{path}"
    data = None
    headers = {}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        opened = urllib.request.urlopen(request, timeout=timeout_s)
    except urllib.error.HTTPError as exc:
        with exc:
            return _response(exc.code, exc.headers, exc, read_body=read_body)
    except (OSError, HTTP_ERROR) as exc:
        if _refused(exc):
            raise CeilingRefusedError(f"{method} {path}: {host}:{port} closed without any response byte ({exc!r})") from exc
        raise
    with opened as response:
        return _response(response.status, response.headers, response, read_body=read_body)
