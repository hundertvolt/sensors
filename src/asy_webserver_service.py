"""Registration-based Microdot REST/API service — modules hand it named callback groups and it auto-constructs the six external endpoints plus connection hardening (timeouts, reject-when-full, a bounded request head).
`ext/microdot.py` is never edited; every behavior change wraps/calls it instead (CLAUDE.md hard rule). See SPECIFICATION.md Part A.5 (Microdot layer) and A.8 (full endpoint reference) for the complete design."""

import asyncio
import json
import math
from collections import namedtuple

# Typed via the vendored upstream stub (ext/typings/microdot/); firmware freezes ext/ and src/ flat together.
import microdot
from microdot import Request, Response, abort, redirect, send_file
from micropython import const

import asy_api_response as ar
from asy_base_classes import HourlyWindowCounter, LockedCounter
from asy_config_manager import FAILED, INVALID, VALID, checked_float, checked_int
from asy_print_log import DEFAULT_LOG, LogConfig, console, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
    from typing import NamedTuple, NoReturn, Protocol, TypeVar

    import asy_config_manager as cm
    from asy_api_response import ResponseEnvelope, _RequestLike  # the shared microdot.Request stand-in (Part G.1: reuse, never reimplement)
    from asy_base_classes import AsyncCallback, ErrorSource, JsonDict, JsonMapping, JsonValue, TaskStarter, TimerStarter
    from asy_print_log import ErrorLog, PrintLogHistory

    _T = TypeVar("_T")

    class _HasName(Protocol):
        name: str

    _Named = TypeVar("_Named", bound=_HasName)

    class _ModuleLike(Protocol):
        # Structural stand-in for a registered sensor/settings module - every SensorReaderConfig
        # subclass and SystemService satisfy it (SPECIFICATION.md Part C.10). Error sources are
        # typed by ErrorSource instead. Only the subset a registration group calls is ever used.
        name: str

        async def _set_dict_cfg(self, data: "JsonMapping", cfg_vals: "cm.ConfigSchema") -> dict[str, str]: ...
        def get_cfg_schema(self) -> "cm.ConfigSchema": ...
        async def get_dict_cfg(self) -> "dict[str, JsonDict]": ...
        async def get_dict_data(self) -> "dict[str, JsonDict]": ...
        async def get_error_counter(self) -> "ErrorLog": ...
        async def reset_error_counter(self) -> bool: ...

    class _Closable(Protocol):
        # What release() closes: the static file a route opened, held for the connection's end.
        def close(self) -> None: ...

    class _ClosableStream(_Closable, Protocol):
        # _close_writer()'s own narrower view of the stream below - exactly the two methods it
        # calls, so a writer-only object (real or test double) satisfies it without a read half.
        async def wait_closed(self) -> None: ...

    class _StreamLike(_ClosableStream, Protocol):
        # The single asyncio Stream object MicroPython hands a start_server() callback as both
        # reader and writer; typings/'s CPython-derived StreamReader/StreamWriter split models
        # neither half of it completely (no aclose() at all), so this is the surface the proxy calls.
        def get_extra_info(self, name: str) -> object: ...
        async def aclose(self) -> None: ...
        async def awrite(self, data: bytes) -> None: ...
        async def read(self, n: int) -> bytes: ...
        async def readexactly(self, n: int) -> bytes: ...

    # What this module registers: a route takes the request, and a static file route also its url_arg; an
    # after-request hook rewrites the response; an error handler answers a status, or an exception too.
    RouteHandler = Callable[[_RequestLike], Awaitable[object]] | Callable[[_RequestLike, str], Awaitable[object]]
    AfterRequestHook = Callable[[_RequestLike, Response], Response]
    ErrorHandler = Callable[[_RequestLike], object] | Callable[[_RequestLike, Exception], Awaitable[object]]

    class _MicrodotApp(Protocol):
        # The subset of the Microdot instance routes are registered onto; the vendored stub
        # (ext/typings/microdot/) leaves get/put/route unannotated (v2.7.0).
        def after_error_request(self, f: "AfterRequestHook") -> object: ...
        def after_request(self, f: "AfterRequestHook") -> object: ...
        async def dispatch_request(self, req: "_RequestLike | None") -> Response: ...  # not called
        # from this module - part of the surface because tests drive routes through it directly.
        def errorhandler(self, status_code_or_exception_class: int | type[Exception]) -> "Callable[[ErrorHandler], object]": ...
        def get(self, url_pattern: str) -> "Callable[[RouteHandler], object]": ...
        async def handle_request(self, reader: "_TimeoutStreamProxy", writer: "_TimeoutStreamProxy") -> None: ...
        def put(self, url_pattern: str) -> "Callable[[RouteHandler], object]": ...

    StatusSourceFct = Callable[[], Awaitable[JsonDict]]
    SystemCmdFct = Callable[[str], Awaitable[bool]]
    NotificationLedFct = Callable[[int, int, int, float], Awaitable[bool]]
    NotificationPauseFct = Callable[[int], Awaitable[bool]]
    HotspotActiveFct = Callable[[], bool]

_NAME = const("WEBSERVER")

_ERR_CALLBACK = const(14)
_ERR_UNEXPECTED = const(23)
_WRN_HTTP_PEER_RESET = const(48)
_WRN_HTTP_CALL_TIMEOUT = const(49)
_WRN_HTTP_REQUEST_CAP = const(50)
_WRN_HTTP_SOCKET_ERROR = const(51)
_WRN_HTTP_CLOSE_RAISED = const(52)
_WRN_HTTP_WAIT_CLOSED = const(53)
_WRN_HTTP_REFUSED = const(60)
_WRN_HTTP_BAD_HEAD = const(61)
_WRN_HTTP_START_FAILED = const(62)

# This service's one optional live cross-instance dependency (SPECIFICATION.md Part C.14): its FRAM
# error-log target, resolved from [device.wiring].fram_target implicitly because this is mandatory
# infra, never an [[instance]] entry - the same tag asy_system_service/wifi/ntp carry.
# @wiring fram_target FRAMManager log optional kwarg

# The only values ever forwarded to system_cmd(), matched as whole strings: the exact action word is what
# runs a command, so no alias, prefix or case variant does (owner, 2026-09-30). mempause's fixed 300 s lives in
# the callback (Part A.8).
_SYSTEM_CMDS = const(("reboot", "bootloader", "mempause"))
_PAUSE_TIME_MAX = const(3600)  # inclusive upper bound for a client-supplied PauseTime - matches
# legacy's own pauseAutoLED command range and asy_notification_service.py's own
# set_override_led() clamp ceiling (_MAX_OVERRIDE_TIME), kept here as its own constant (not
# imported) since this module has no other coupling to asy_notification_service.py.

# Dispatch-only fields validate through the per-kind validators against synthetic schemas, as schema-backed fields do
# (SPECIFICATION.md A.8); LightCmdLED's are legacy's own led_cmd() bounds, never schema-backed.
_PAUSE_TIME_FIELD: "cm.FieldSchema" = ("PauseTime", "int", 0, 0, _PAUSE_TIME_MAX, None)
_LIGHT_CMD_FIELDS: "tuple[cm.FieldSchema, ...]" = (
    ("R", "int", None, 0, 255, None),
    ("G", "int", None, 0, 255, None),
    ("B", "int", None, 0, 255, None),
    ("T", "float", None, 0.5, 60.0, None),
)
_LED_BUSY_DESCR = const("LED busy - retry later")  # the envelope's descr when a running signal refused LightCmdLED

# @tunable web.max_pending_fragments = 16
_MAX_PENDING_FRAGMENTS = const(16)  # _PieceWriter's list never outgrows 16 slots (64 B on the RP2040)
# Shipped defaults: buildgen reads each from here and passes it in ServingLimits/StaticSite.
# @tunable web.max_content_length = 2048
_DEFAULT_MAX_CONTENT_LENGTH = const(2048)  # 1.56x the largest schema-permitted body, ~9x real traffic (I.6)
# @tunable web.chunk_bytes = 256
_DEFAULT_CHUNK_BYTES = const(256)  # chunk_bytes' default: one bound for JSON pieces and static reads,
# sized to the holes a fragmented heap still has at gc.threshold(-1), not to its one large run -
# under load that run is gone and ~870 B pieces fail with ~100 KB free (SPECIFICATION.md Part I.3).
_DEFAULT_MAX_CONNECTIONS = const(6)  # three below the firmware's MEMP_NUM_TCP_PCB (toolchain/versions.toml), Part H.7
# @tunable web.per_call_timeout_s = 5.0
_DEFAULT_PER_CALL_TIMEOUT_S = const(5.0)
# @tunable web.outer_cap_s = 15.0
_DEFAULT_OUTER_CAP_S = const(15.0)
_DEFAULT_STATIC_INDEX = const("index.html")

# The request head's bounds, checked by the reader proxy before Microdot parses a line (SPECIFICATION.md A.5).
# @tunable web.max_header_lines = 32
_MAX_HEADER_LINES = const(32)  # browsers send about 15-20 headers, curl about 4
# @tunable web.max_head_bytes = 2048
_MAX_HEAD_BYTES = const(2048)  # the request line and headers together: no cookie or auth header on this device
_EPIPE = const(32)  # a refused head's errno: Microdot mutes 32 (ext/microdot.py:56-61); MicroPython's errno has no EPIPE
# A failed start_server() is retried across one lwIP close linger (MICROPY_PY_LWIP_TCP_CLOSE_TIMEOUT_MS, 10 s).
# @tunable web.start_retries = 3
_START_RETRIES = const(3)
# @tunable web.start_retry_s = 5
_START_RETRY_S = const(5)

_ERROR_STATUSES = const((400, 404, 405, 413, 500))  # the five shaped statuses SPECIFICATION.md A.5 names; each is its own envelope code (C.5.3)

# The one route table: registered in this order; buildgen reads it for the REST reference (SPECIFICATION.md A.8).
ROUTES = (
    ("GET", "/measurements", "_get_measurements"),
    ("GET", "/sensors", "_get_sensors"),
    ("PUT", "/sensors", "_put_sensors"),
    ("GET", "/networking", "_get_networking"),
    ("PUT", "/networking", "_put_networking"),
    ("GET", "/system", "_get_system"),
    ("PUT", "/system", "_put_system"),
    ("GET", "/status", "_get_status"),
    ("PUT", "/status", "_put_status"),
    ("GET", "/notification", "_get_notification"),
    ("PUT", "/notification", "_put_notification"),
)


def _body_as_dict(request: "_RequestLike") -> "dict[str, JsonValue] | None":
    # None covers both a request.json access raising (malformed/undecodable JSON, matches
    # asy_api_response.py's parse_cmd_request() precedent) and a syntactically valid but non-dict body
    # (array/string/number/null) - both degrade to the same clean ERR envelope at the call site.
    try:
        data = request.json
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _cfg_values(values: "Mapping[str, JsonDict]") -> "JsonDict":
    # Every module's get_dict_cfg() returns make_dict()'s {name: {field: value}}; this takes the one inner dict.
    for inner in values.values():
        return inner
    return {}


class _PieceWriter:
    # Concatenates adjacent JSON text fragments into pieces of at most max_bytes bytes, never splitting
    # one - so the largest allocation is bounded by the largest fragment, not by the response.
    def __init__(self, pieces: list[bytes], max_bytes: int) -> None:
        self._pieces = pieces
        self._group: list[bytes] = []
        self._size = 0
        self._max_bytes = max_bytes

    def add(self, fragment: str) -> None:
        data = fragment.encode()  # encoded once, here: a piece is counted and sent in bytes
        if self._group and self._size + len(data) > self._max_bytes:
            self.flush()
        self._group.append(data)
        self._size += len(data)
        if len(self._group) == _MAX_PENDING_FRAGMENTS:
            # Collapsed, never left to grow: a piece of tiny fragments would otherwise need a list
            # array as large as the piece itself - the very block this writer exists to avoid.
            self._group = [b"".join(self._group)]

    def add_value(self, value: object) -> None:
        # Exactly json.dumps(value)'s text, never built as one string: dicts, lists and tuples are
        # walked and only their keys and scalars dumped, with json.dumps()'s own ", "/": ".
        if isinstance(value, dict):
            self.add("{")
            for index, (key, item) in enumerate(value.items()):
                # json.dumps() quotes a non-str key's own JSON text (True -> "true"), never str(key).
                self.add((", " if index else "") + (json.dumps(key) if isinstance(key, str) else '"' + json.dumps(key) + '"') + ": ")
                self.add_value(item)
            self.add("}")
        elif isinstance(value, (list, tuple)):
            self.add("[")
            for index, item in enumerate(value):
                if index:
                    self.add(", ")
                self.add_value(item)
            self.add("]")
        elif isinstance(value, float) and not math.isfinite(value):
            self.add("null")  # json.dumps() writes bare nan/inf, which JSON rejects (Part G.2)
        else:
            self.add(json.dumps(value))

    def flush(self) -> None:
        if self._group:
            self._pieces.append(b"".join(self._group))
            self._group = []
            self._size = 0


def _index_by_name(items: "Iterable[_Named]") -> "dict[str, _Named]":
    # Last-registration-wins, by construction (owner, 2026-08-12; SPEC A.8): the
    # simplest per-item loop already behaves this way; no dedup/guard code on top (agent, 2026-08-12).
    result: dict[str, _Named] = {}
    for item in items:
        result[item.name] = item
    return result


def _index_pairs(items: "Iterable[tuple[str, StatusSourceFct]]") -> "dict[str, StatusSourceFct]":
    return dict(items)


def _mark_connection_close(_request: "_RequestLike", response: Response) -> Response:
    # ext/microdot.py speaks HTTP/1.0, whose default is already non-persistent, but RFC 7230 SS6.6
    # recommends saying so explicitly - added through Microdot's own supported hook, never by
    # editing the vendored file.
    response.headers["Connection"] = "close"
    return response


class SettingsGroup:
    def __init__(
        self,
        module: "_ModuleLike",
        fields: "Sequence[str]",
        post_fct: "Callable[[], None] | None" = None,
        post_asy_fct: "AsyncCallback | None" = None,
    ) -> None:
        self.module = module
        self.fields = tuple(fields)
        self.post_fct = post_fct
        self.post_asy_fct = post_asy_fct


class _HeadRefusedError(OSError):
    # A refused request head: errno 32 is in Microdot's muted list (ext/microdot.py:56-61), so it answers 400 with no
    # traceback.
    pass


class _TimeoutStreamProxy:
    # Forwards every stream method ext/microdot.py calls, each bounded by timeout_s (a plain asyncio.TimeoutError,
    # not an OSError subclass - Part F.1), and bounds the request head before Microdot parses it (SPECIFICATION.md A.5).
    # Microdot's read-phase catch swallows a read timeout (Part A.5), so this proxy is the only place it is observable.
    def __init__(
        self,
        stream: "_StreamLike",
        timeout_s: float,
        pr: "PrintLogHistory",
        peer_gone: list[bool],
        timed_out: list[bool],
        head_refused: list[bool] | None = None,
        chunk: int = _DEFAULT_CHUNK_BYTES,
    ) -> None:
        self._stream = stream
        self._timeout_s = timeout_s
        self._pr = pr
        self._peer_gone = peer_gone  # shared by one connection's pair
        self._timed_out = timed_out  # likewise: _serve() reads it
        self._head_refused = [False] if head_refused is None else head_refused  # the reader's: the writer parses no head
        self._chunk = chunk  # the largest single read, so no read allocates more than one piece
        self._head: list[bytes] | None = []  # the response's header block until its blank line
        self._rbuf = b""  # bytes read ahead of what Microdot asked for: the next head line or the body's start
        self._head_lines = 0  # the request line and headers returned so far
        self._head_bytes = 0
        self._length_seen = False
        self._held: _Closable | None = None

    async def _bounded(self, coro: "Awaitable[_T]") -> "_T":
        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError:
            self._timed_out[0] = True  # only non-read calls: a read's was logged already, below
            raise

    async def _bounded_read(self, coro: "Awaitable[_T]") -> "_T":
        # Logged here, and only for reads: a write-phase timeout escapes microdot and reaches
        # _serve(), which logs it itself - logging both counted one timeout twice.
        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError as e:
            await self._pr.wrn_s("Connection reclaimed (per-call timeout):", e, wrnno=_WRN_HTTP_CALL_TIMEOUT)
            raise
        except OSError:
            # A read that saw a reset leaves the socket in STATE_PEER_RST_HANDLED with its pcb freed
            # (extmod/modlwip.c:507, 843-844); a later write still goes through that NULL pcb (:751-760, Part H.7.1),
            # so writes stop here. Re-check at every pin move; remove once modlwip refuses them.
            self._peer_gone[0] = True
            raise

    def _check_head_line(self, line: bytes, limit: int) -> None:
        # Refuses, before Microdot parses it, what Microdot would buffer whole or raise and print on (ext/microdot.py
        # Request.create()); each rule is one refusal (SPECIFICATION.md A.5).
        self._head_bytes += len(line)
        if len(line) > limit or self._head_bytes > _MAX_HEAD_BYTES:  # one line over max_readline, or the whole head
            self._refuse()
        try:
            text = line.decode().strip()
        except UnicodeError:  # not UTF-8: Microdot's own decode would raise
            self._refuse()
        if not text:
            return  # the blank line ending the head, or EOF
        first = self._head_lines == 0
        if self._head_lines <= _MAX_HEADER_LINES:  # the request line, then at most _MAX_HEADER_LINES headers
            self._head_lines += 1
        else:
            self._refuse()
        if first:
            try:
                _method, _url, version = text.split()
            except ValueError:  # Microdot unpacks the request line into exactly three tokens
                self._refuse()
            if "/" not in version:  # and splits the version at "/"
                self._refuse()
            return
        colon = text.find(":")
        if colon < 0:  # Microdot unpacks a header's name and value at its first ":"
            self._refuse()
        name = text[:colon].lower()
        if name == "transfer-encoding":  # a body must carry a length: Microdot would read a chunked one as empty
            self._refuse()
        if name == "content-length":
            if self._length_seen or not text[colon + 1 :].strip().isdigit():  # ASCII digits, once: int() takes a sign
                self._refuse()
            self._length_seen = True

    def _refuse(self) -> "NoReturn":
        # Raised outside _bounded_read(), so peer_gone stays False; _serve() traces the flag once the request ends.
        self._head_refused[0] = True
        raise _HeadRefusedError(_EPIPE)

    def get_extra_info(self, name: str) -> object:
        return self._stream.get_extra_info(name)

    async def aclose(self) -> None:
        await self._bounded(self._stream.aclose())

    async def awrite(self, data: bytes) -> None:
        if self._peer_gone[0]:
            return
        if self._head is not None:
            # microdot writes the status line and each header apart; sent as one, a cut response
            # never ends mid-headers, which a client reads as a complete, empty 200 (Part I.3).
            self._head.append(data)
            if data != b"\r\n":
                return
            data = b"".join(self._head)
            self._head = None
        try:
            await self._bounded(self._stream.awrite(data))
        except OSError:
            # Microdot mutes ECONNRESET/EPIPE from a response write (ext/microdot.py:56-61, 689-705), so a client gone
            # mid-response is recorded here; the early return above then stops further writes.
            self._peer_gone[0] = True
            raise

    def close(self) -> None:
        self._stream.close()

    def hold(self, closable: "_Closable") -> None:
        self._held = closable  # one object: the static file a route opened, closed by release()

    async def readexactly(self, n: int) -> bytes:
        # The body: what the head's reads already took first, then the rest from the stream.
        buf = self._rbuf
        if len(buf) >= n:
            self._rbuf = buf[n:]
            return buf[:n]
        self._rbuf = b""
        try:
            rest = await self._bounded_read(self._stream.readexactly(n - len(buf)))
        except EOFError:  # the body ended before Content-Length bytes: refused like a bad head, not printed
            self._refuse()
        return buf + rest

    async def readline(self) -> bytes:
        # One head line, read in pieces of at most chunk bytes and never past max_readline + 1 bytes, so no read
        # allocates more than a piece (py/stream.c allocates the whole request up front). EOF returns the partial line.
        limit = Request.max_readline  # Microdot's own bound, read per call so a pin move carries it
        buf = self._rbuf
        while b"\n" not in buf:
            if len(buf) > limit:
                self._refuse()
            data = await self._bounded_read(self._stream.read(min(limit + 1 - len(buf), self._chunk)))
            if not data:
                break
            buf += data
        end = buf.find(b"\n") + 1 or len(buf)
        line = buf[:end]
        self._rbuf = buf[end:]
        self._check_head_line(line, limit)
        return line

    def release(self) -> None:
        held, self._held = self._held, None  # cleared first, so a second release() closes nothing
        if held is not None:
            held.close()

    async def wait_closed(self) -> None:
        await self._bounded(self._stream.wait_closed())


# Three config objects the generated module builds whole (every field passed): what the routes
# read, how connections are served, and the optional static website.
if TYPE_CHECKING:
    class RouteSources(NamedTuple):
        sensors: Sequence[_ModuleLike]
        settings: dict[str, Sequence[SettingsGroup]] | None
        build_info: JsonDict | None  # verbatim "build" sub-entry of GET /system (Part L.7); None omits it
        system_cmd: SystemCmdFct | None
        notification_led: NotificationLedFct | None
        notification_pause: NotificationPauseFct | None
        status_sources: dict[str, StatusSourceFct] | None
        maintenance_sensors: Sequence[tuple[str, StatusSourceFct]]
        error_sources: Sequence[ErrorSource]

    class ServingLimits(NamedTuple):
        max_content_length: int  # request body cap (Part I.6)
        chunk_bytes: int  # largest single write of any response body (Part I.3); clamped to >= 1
        max_connections: int  # reject-when-full ceiling; with backlog a relationship (Part H.7)
        backlog: int | None  # None derives max_connections + 1; clamped to >= max_connections
        per_call_timeout_s: float
        outer_cap_s: float
        host: str
        port: int

    class StaticSite(NamedTuple):
        mount: str  # freezefs mount of the frozen website (Part A.9)
        index_file: str  # served for "/" and "/<index_file>"
        is_hotspot_active: HotspotActiveFct | None  # the captive fallback's gate (Part A.5)

else:
    RouteSources = namedtuple("RouteSources", (
        "sensors", "settings", "build_info", "system_cmd", "notification_led", "notification_pause",
        "status_sources", "maintenance_sensors", "error_sources",
    ))
    ServingLimits = namedtuple("ServingLimits", (
        "max_content_length", "chunk_bytes", "max_connections", "backlog", "per_call_timeout_s", "outer_cap_s", "host", "port",
    ))
    StaticSite = namedtuple("StaticSite", ("mount", "index_file", "is_hotspot_active"))


class _StaticRoutes:
    # The frozen website's two GET routes (SPECIFICATION.md Part A.9), registered only when a StaticSite is given.
    def __init__(self, site: StaticSite, chunk_bytes: int) -> None:
        self._site = site
        self._chunk_bytes = chunk_bytes

    async def get_index(self, request: "_RequestLike") -> Response:
        return self.serve(request, self._site.index_file)

    async def get(self, request: "_RequestLike", filename: str) -> Response:
        return self.serve(request, filename)

    def serve(self, request: "_RequestLike", filename: str) -> Response:
        if ".." in filename:
            abort(404)  # guard-clause before touching the mounted filesystem - cheap and uniform
            # even though freezefs's own VfsFrozen already refuses to escape its mount root.
        try:
            stream = open(self._site.mount + "/" + filename + ".gz", "rb")
        except OSError:  # no such file in the mounted filesystem
            is_hotspot_active = self._site.is_hotspot_active
            if is_hotspot_active is not None and is_hotspot_active():
                # Captive-portal redirect fallback, triggering phones' "Sign in to network" popup -
                # see SPECIFICATION.md Part A.5 for the full mechanism and why no try/except is needed.
                return redirect("/")
            abort(404)
        request.sock[1].hold(stream)  # closed when the connection ends, a HEAD or aborted response included
        size = stream.seek(0, 2)  # sent as Content-Length: without it this HTTP/1.0 body ends only at FIN,
        stream.seek(0)  # so a write that fails after the 200 would reach the client as a complete page
        response = send_file(filename, compressed=True, stream=stream)
        response.headers["Content-Length"] = str(size)
        response.headers["Cache-Control"] = "no-cache"  # revalidate before reuse: a reflashed page is never served stale (agent, 2026-09-30; owner-reviewed, 2026-10-02)
        # Microdot v2.7.0 reads 1,024 B per send_file chunk (ext/microdot.py:567, 746); ours is the one write bound.
        # Re-check at a Microdot bump.
        response.send_file_buffer_size = self._chunk_bytes
        return response


class WebserverService:
    def __init__(
        self,
        app: "_MicrodotApp",  # a real ext/microdot.py Microdot() instance - routes are registered
        # onto it once, here; not itself importable for typing (see the microdot import comment above).
        routes: RouteSources,
        serving: ServingLimits,
        uptime_s: "Callable[[], Awaitable[int]]",  # the device's SysUptime reader: the drop window advances from it
        static: StaticSite | None = None,  # None registers no static routes at all
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        self.name = _NAME
        self.pr: PrintLogHistory = make_logger(log, _NAME)
        # ext/microdot.py prints an exception before our errorhandler runs (three call sites at v2.7.0); the name is
        # rebound here, never edited, so DebugLevel 0 keeps it off a console no host may be reading (CLAUDE.md).
        # The vendored stub (ext/typings/microdot/) declares no print_exception: the ignore goes once it does.
        microdot.print_exception = self._print_exception  # type: ignore[attr-defined]
        self._app = app
        self._uptime_s = uptime_s
        self._sensors = _index_by_name(routes.sensors)
        self._settings: dict[str, list[SettingsGroup]] = {k: list(v) for k, v in (routes.settings or {}).items()}
        self._build_info = routes.build_info
        self._system_cmd = routes.system_cmd
        self._notification_led = routes.notification_led
        self._notification_pause = routes.notification_pause
        self._status_sources: dict[str, StatusSourceFct] = dict(routes.status_sources or {})
        self._maintenance_sensors = _index_pairs(routes.maintenance_sensors)
        self._error_sources = _index_by_name(routes.error_sources)
        max_connections = serving.max_connections
        self._max_connections = max_connections
        self._chunk_bytes = max(serving.chunk_bytes, 1)  # a read of 0 would never end microdot's loop
        # Clamped rather than rejected, matching LockedCounter's own out-of-range convention: a
        # backlog under the ceiling resets part of a burst the ceiling admits, which reads as an
        # application bug. buildgen rejects the same mistake in config, where it can be named.
        self._backlog = max_connections + 1 if serving.backlog is None else max(serving.backlog, max_connections)
        self._per_call_timeout_s = serving.per_call_timeout_s
        self._outer_cap_s = serving.outer_cap_s
        self._host = serving.host
        self._port = serving.port
        self._open_conns = LockedCounter(init_value=0)  # the shared COUNTER_CAP; a gauge bounded by the backlog
        self._dropped = HourlyWindowCounter()  # HTTPDropped: the last 24 hours in hourly bins, allocated once here
        max_content_length = serving.max_content_length

        Request.max_content_length = max_content_length  # a Request *class* attribute, not
        # per-app-instance (ext/microdot.py's own module docstring example) - see
        # tests/test_asy_webserver_service.py's own boundary-test comment on this.

        # Bound to the same value, never microdot's own 16 KB default: Request.create() buffers the
        # body before dispatch_request() answers 413, so a larger cap here has an oversized body
        # read into one contiguous allocation and then thrown away (SPECIFICATION.md Part I.6).
        Request.max_body_length = max_content_length

        for method, path, handler in ROUTES:
            (app.get if method == "GET" else app.put)(path)(getattr(self, handler))

        app.after_request(_mark_connection_close)
        app.after_error_request(_mark_connection_close)  # after_request alone misses every
        # error-response path (400/404/405/413/500) - dispatch_request() only runs after_request
        # handlers on its happy path (SPECIFICATION.md Part A.8).
        for status_code in _ERROR_STATUSES:
            app.errorhandler(status_code)(_shaped_error_handler(status_code))
        # Catch-all for logging/FRAM-history only - Microdot's own error_response() fallthrough
        # already gives the correct reply shape via the 500 handler above regardless (see
        # SPECIFICATION.md Part A.5); this just gets the exception into pr.err_s()/history.
        app.errorhandler(Exception)(self._handle_unhandled_exception)

        if static is not None:
            # Registered last: "/<path:filename>"'s own regex also matches every fixed path above
            # (e.g. "/measurements") - Microdot's find_route() returns the first matching pattern,
            # so every exact-match API route must already be registered or it would be shadowed.
            site_routes = _StaticRoutes(static, self._chunk_bytes)
            app.get("/")(site_routes.get_index)
            app.get("/<path:filename>")(site_routes.get)

    async def _get_measurements(self, _request: "_RequestLike") -> Response:
        # Plain for-loop, not a dict comprehension - MicroPython doesn't support `await` inside one.
        # .update(), not result[name] = ... - see SPECIFICATION.md Part A.8 for the real
        # double-wrap production bug this avoids.
        result: dict[str, JsonValue] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_data())
        return await _stream_dict_response(result, self._chunk_bytes)

    async def _get_networking(self, _request: "_RequestLike") -> Response:
        # Streamed via _stream_dict_response(): this scales with however many SettingsGroup entries this device's own
        # build wires up (CLAUDE.md's memory-safety hard rule).
        return await _stream_dict_response(await self._get_settings_flat("networking"), self._chunk_bytes)

    async def _get_notification(self, _request: "_RequestLike") -> Response:
        return await _stream_dict_response(await self._get_settings_flat("notification"), self._chunk_bytes)  # see _get_networking()'s own comment

    async def _get_sensors(self, _request: "_RequestLike") -> Response:
        # .update(), not result[name] = ... - see _get_measurements()'s own comment above.
        result: dict[str, JsonValue] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_cfg())
        return await _stream_dict_response(result, self._chunk_bytes)  # see _get_measurements()'s own comment above

    async def _get_settings_flat(self, endpoint: str) -> "JsonDict":
        result: JsonDict = {}
        for group in self._settings.get(endpoint, []):
            values = _cfg_values(await group.module.get_dict_cfg())
            for field in group.fields:
                if field in values:
                    result[field] = values[field]
                elif "error" in values:  # the module's unavailable marker (Part C.6), sent in place of each field
                    result[field] = values
        return result

    async def _get_status(self, _request: "_RequestLike") -> Response:
        # Streamed like every configuration-sized route (Part I.3), its pieces built below.
        return _pieces_response(await self._build_status_pieces())

    async def _get_system(self, _request: "_RequestLike") -> Response:
        result = await self._get_settings_flat("system")  # see _get_networking()'s own comment
        if self._build_info is not None:
            result["build"] = self._build_info
        return await _stream_dict_response(result, self._chunk_bytes)

    async def _apply_settings_groups(self, endpoint: str, body: "JsonMapping", dispatch_keys: tuple[str, ...] = ()) -> dict[str, str]:
        # Only a group whose field subset intersects the request body is dispatched: one with no
        # matching keys must never fire its post_fct/post_asy_fct, which is what "a partial-field
        # update triggers only the relevant post-write hook" means (SPECIFICATION.md Part A.8).
        results: dict[str, str] = {}
        groups = self._settings.get(endpoint, [])
        for group in groups:
            subset = {k: v for k, v in body.items() if k in group.fields}
            if not subset:
                continue
            # handle_set_cmd() answers every key of the subset, a raising hook's group as "Failed" (Part H.6).
            results.update(
                await ar.handle_set_cmd(
                    group.module,  # type: ignore[arg-type]  # structurally SensorReaderConfig-shaped
                    # (get_cfg_schema()/_set_dict_cfg()/.pr) - _ModuleLike is a narrower Protocol, not
                    # importable here without a real coupling to asy_base_classes.py's concrete class.
                    subset,
                    group.module.get_cfg_schema(),
                    group.post_fct,
                    group.post_asy_fct,
                ),
            )
        for key in body:
            if key not in dispatch_keys and not any(key in group.fields for group in groups):
                results[key] = INVALID  # a key no group of this endpoint lists, and no dispatch key
        return results

    async def _build_status_pieces(self) -> list[bytes]:
        # One _PieceWriter, flushed at every top-level section: each section starts its own piece
        # and no piece exceeds the cap, whatever a section holds - one entry per registered error
        # source, for "errcount" (Part I.3). Values are written, never json.dumps()'d whole.
        pieces: list[bytes] = []
        writer = _PieceWriter(pieces, self._chunk_bytes)
        for prefix, key in (('{"networking":', "networking"), (',"system":', "system"), (',"notification":', "notification")):
            writer.add(prefix)
            await self._write_status_source(writer, key)
            writer.flush()

        writer.add(',"sensors":{')
        for index, (name, fct) in enumerate(self._maintenance_sensors.items()):
            writer.add(("," if index else "") + json.dumps(name) + ":")
            await self._write_guarded(writer, fct, name)
        writer.add("}")
        writer.flush()

        writer.add(',"errcount":{')
        for name, module in self._error_sources.items():
            writer.add(json.dumps(name) + ":")
            await self._write_errcount_entry(writer, module.get_error_counter, name)
            writer.add(",")
        # This service's own entry (Part A.8's registration contract), added here directly rather
        # than registered into self._error_sources: this service builds the routes that list them.
        writer.add(json.dumps(_NAME) + ":")
        await self._write_errcount_entry(writer, self.pr.get_log, _NAME)
        writer.add("}}")
        writer.flush()
        return pieces

    async def _close_writer(self, writer: "_ClosableStream") -> None:
        try:
            writer.close()
        except Exception as e:  # best-effort cleanup, never load-bearing - still logged (Part C.7's
            # silent-failure-masking convention) since a repeatedly-failing close() could leak TCP
            # PCBs under this platform's tiny connection ceiling with no other trace.
            await self.pr.wrn_s("Error closing connection writer:", e, wrnno=_WRN_HTTP_CLOSE_RAISED)
        try:
            await asyncio.wait_for(writer.wait_closed(), self._per_call_timeout_s)
        except Exception as e:  # bounds a hanging wait_closed() (F.6) as well as any raised error
            await self.pr.wrn_s("Error waiting for writer to close:", e, wrnno=_WRN_HTTP_WAIT_CLOSED)

    async def _dispatch_notification_led(self, payload: object) -> tuple[str, bool]:
        # The word, and whether a running signal refused the command: told apart from a raising callback, both "Failed".
        if self._notification_led is None or not isinstance(payload, dict) or len(payload) != len(_LIGHT_CMD_FIELDS):
            return INVALID, False
        red, green, blue, seconds = _LIGHT_CMD_FIELDS
        r = checked_int(payload.get(red[0]), red)  # a missing member reads None, which every validator refuses
        g = checked_int(payload.get(green[0]), green)
        b = checked_int(payload.get(blue[0]), blue)
        t = checked_float(payload.get(seconds[0]), seconds)
        if r is None or g is None or b is None or t is None:
            return INVALID, False
        try:  # caller-supplied callback, could legitimately misbehave - see _run_system_cmd()'s
            # own comment on why this needs the same guard every comparable callback elsewhere in
            # this codebase already has.
            ok = await self._notification_led(r, g, b, t)
        except Exception as e:
            await self.pr.err_s("notification_led callback failed:", e, errno=_ERR_CALLBACK)
            return FAILED, False
        # External LED commands are refused while a signal runs and told to retry; internal ones wait, bounded (owner, 2026-10-02).
        return (VALID, False) if ok else (FAILED, True)

    async def _dispatch_notification_pause(self, payload: object) -> str:
        # Out of range is Invalid, never clamped (legacy rejected it).
        if self._notification_pause is None:
            return INVALID
        pause = checked_int(payload, _PAUSE_TIME_FIELD)
        if pause is None:
            return INVALID
        try:  # caller-supplied callback, could legitimately misbehave - see _run_system_cmd()'s
            # own comment on why this needs the same guard every comparable callback elsewhere in
            # this codebase already has.
            ok = await self._notification_pause(pause)
        except Exception as e:
            await self.pr.err_s("notification_pause callback failed:", e, errno=_ERR_CALLBACK)
            return FAILED
        return VALID if ok else FAILED

    async def _dispatch_system_cmd(self, cmd: object) -> str:
        # object: whatever JSON value the client sent; membership in the enum is the whole check
        # (whole-string equality: no alias, prefix, case folding or number runs a command).
        for name in _SYSTEM_CMDS:
            if cmd == name:
                return await self._run_system_cmd(name)
        return INVALID

    async def _handle_unhandled_exception(self, _request: "_RequestLike", exc: Exception) -> "tuple[ResponseEnvelope, int]":
        # Registered via app.errorhandler(Exception) in __init__, purely to persist the exception
        # into FRAM history - never to shape the reply. The 500 status-code handler already does
        # that on its own, whether or not this one is registered (Part A.5).
        await self.pr.err_s("Unhandled exception in route handler:", exc, errno=_ERR_UNEXPECTED)
        return ar.make_response(500), 500

    async def _note_drop(self, wrnno: int, what: str) -> None:
        # One entry per event; a run of identical codes spends one history slot (print_log's newest-entry rule).
        self._dropped.add(await self._uptime_s())
        await self.pr.wrn_s(what, wrnno=wrnno)

    def _print_exception(self, exc: BaseException) -> None:
        # Microdot's own exception print (rebound in __init__): level-gated like every other line, except a
        # MemoryError's text, which stays on the console so the memory gates read it (CLAUDE.md memory rule).
        if isinstance(exc, MemoryError):
            console(_NAME, "Microdot caught:", exc)
        else:
            self.pr.err("Microdot caught:", exc)

    async def _put_networking(self, request: "_RequestLike") -> "ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        return ar.make_response(0, result=await self._apply_settings_groups("networking", body))

    async def _put_notification(self, request: "_RequestLike") -> "ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results = await self._apply_settings_groups("notification", body, ("LightCmdLED", "PauseTime"))
        busy = False
        if "LightCmdLED" in body:
            results["LightCmdLED"], busy = await self._dispatch_notification_led(body["LightCmdLED"])
        if "PauseTime" in body:
            results["PauseTime"] = await self._dispatch_notification_pause(body["PauseTime"])
        return ar.make_response(0, descr=_LED_BUSY_DESCR if busy else None, result=results)

    async def _put_sensors(self, request: "_RequestLike") -> "ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results: dict[str, JsonValue] = {}
        for name, fields in body.items():
            module = self._sensors.get(name)
            if module is None or not isinstance(fields, dict):
                # An unknown sensor, or a sensor entry that is not an object, answers "Invalid" in place of its field map.
                results[name] = INVALID
            else:
                # A field-to-word map is JSON, but dict is invariant: no JsonValue member takes a dict[str, str].
                results[name] = await module._set_dict_cfg(fields, module.get_cfg_schema())  # type: ignore[assignment]
        return ar.make_response(0, result=results)

    async def _put_status(self, request: "_RequestLike") -> "ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        result: dict[str, str] = {}
        for key, value in body.items():
            if key != "ResetErrors" or value is not True:
                result[key] = INVALID  # {"ResetErrors": true} is the one request (SPECIFICATION.md A.8)
                continue
            # Every source at once, this service's own entry included (_build_status_pieces()): "`ResetErrors`
            # resets the FRAM-backed logs concurrently rather than one after another" (owner, 2026-09-26).
            # One store whose write failed answers the whole key "Failed".
            ok = await asyncio.gather(*(m.reset_error_counter() for m in self._error_sources.values()), self.reset_error_counter())
            result[key] = VALID if all(ok) else FAILED
        return ar.make_response(0, result=result)

    async def _put_system(self, request: "_RequestLike") -> "ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results = await self._apply_settings_groups("system", body, ("SystemCmd",))
        if "SystemCmd" in body:
            results["SystemCmd"] = await self._dispatch_system_cmd(body["SystemCmd"])
        return ar.make_response(0, result=results)

    async def _run_system_cmd(self, name: str) -> str:
        if self._system_cmd is None:
            return INVALID
        try:  # caller-supplied callback, could legitimately misbehave - same defensive shape every
            # other caller-supplied-callback site uses (Part G.2): a raise degrades to "Failed" with a
            # persisted errno instead of escaping through the route handler.
            ok = await self._system_cmd(name)
        except Exception as e:
            await self.pr.err_s("system_cmd callback failed:", e, errno=_ERR_CALLBACK)
            return FAILED
        return VALID if ok else FAILED

    async def _serve(self, reader: "_StreamLike", writer: "_StreamLike") -> None:
        current = await self._open_conns.increment()
        if current > self._max_connections:
            # Reject-when-full (owner, 2026-08-12; SPEC A.8): accepted by asyncio, then closed with no response ever
            # written - cheapest, doesn't risk the rejection path itself becoming a resource consumer.
            await self._open_conns.decrement()
            try:
                await self._note_drop(_WRN_HTTP_REFUSED, "Connection refused at the ceiling")
            finally:  # a trace that cannot be written still closes the refused connection
                await self._close_writer(writer)
            return
        try:
            peer_gone = [False]
            timed_out = [False]
            head_refused = [False]
            proxy_reader = _TimeoutStreamProxy(reader, self._per_call_timeout_s, self.pr, peer_gone, timed_out, head_refused, self._chunk_bytes)
            proxy_writer = _TimeoutStreamProxy(writer, self._per_call_timeout_s, self.pr, peer_gone, timed_out)
            logged = False  # an arm below persisted this connection's one entry, so no drop trace follows it (C.7)
            try:
                await asyncio.wait_for(self._app.handle_request(proxy_reader, proxy_writer), self._outer_cap_s)
            except asyncio.CancelledError:
                raise  # never swallow a genuine task cancellation
            except asyncio.TimeoutError as e:
                # Either the outer wait_for() above (bounds a Slowloris-paced client no per-call
                # timeout alone would catch) or a write-phase proxy timeout, logged only here - a
                # read-phase one logged inside the proxy, and microdot swallowed it.
                await self.pr.wrn_s("Connection reclaimed (timed out):", e, wrnno=_WRN_HTTP_CALL_TIMEOUT if timed_out[0] else _WRN_HTTP_REQUEST_CAP)
                logged = True
            except OSError as e:  # a socket error Microdot does not mute (e.g. EHOSTUNREACH on a response
                # write); the resets it mutes end in peer_gone instead, traced below.
                await self.pr.wrn_s("Connection reclaimed (socket error):", e, wrnno=_WRN_HTTP_SOCKET_ERROR)
                logged = True
            except Exception as e:  # never raises out of this task (SPECIFICATION.md A.5)
                await self.pr.err_s("Unexpected error serving connection:", e, errno=_ERR_UNEXPECTED)
                logged = True
            finally:
                proxy_writer.release()  # a held static stream closes once, whatever ended the response
            if not logged:
                if head_refused[0]:
                    await self._note_drop(_WRN_HTTP_BAD_HEAD, "Request head refused")
                elif peer_gone[0]:
                    await self._note_drop(_WRN_HTTP_PEER_RESET, "Connection reset by the peer before or during its response")
        finally:
            try:  # _close_writer()'s own logging can raise MemoryError on an exhausted heap,
                await self._close_writer(writer)
            finally:  # and a slot skipped here would be lost until reboot
                await self._open_conns.decrement()

    async def _serve_loop(self) -> None:
        # backlog is explicit, never MicroPython's own default of 5 (extmod/asyncio/stream.py):
        # inherited, a burst of a raised max_connections would be reset past its fifth arrival.
        attempt = 0
        while True:
            try:
                # The stub splits MicroPython's one Stream into StreamReader/StreamWriter (extmod/asyncio/stream.py:92-93
                # aliases both to Stream); remove the ignore once the stub models the one class.
                server = await asyncio.start_server(self._serve, self._host, self._port, backlog=self._backlog)  # type: ignore[arg-type]
                break
            except (MemoryError, OSError) as e:
                attempt += 1
                if attempt >= _START_RETRIES:
                    await self.pr.wrn_s("Web server start failed:", e, wrnno=_WRN_HTTP_START_FAILED)
                    raise
                self.pr.wrn("Web server start failed, retrying:", e)
                # Retries span one lwIP close linger (10 s): a socket() failure holds nothing; a failed bind()/listen()
                # holds its pcb until a collection, up to two across the retries. The last failure ends the task (A.5).
                await asyncio.sleep(_START_RETRY_S)
        await server.wait_closed()

    async def _write_errcount_entry(self, writer: _PieceWriter, get_log_fct: "Callable[[], Awaitable[ErrorLog]]", name: str) -> None:
        try:  # see _write_guarded()'s own comment - identical reasoning, different source kind.
            raw = await get_log_fct()
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", name, e, errno=_ERR_CALLBACK)
            writer.add('{"error":"unavailable"}')
            return
        writer.add_value(_shape_errcount_entry(raw, name))

    async def _write_guarded(self, writer: _PieceWriter, fct: "StatusSourceFct", name: str) -> None:
        try:  # caller-supplied callback, could misbehave - degrades this one key instead of letting
            # one failing source discard every other section's already-fetched data.
            value = await fct()
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", name, e, errno=_ERR_CALLBACK)
            writer.add('{"error":"unavailable"}')
            return
        writer.add_value(value)

    async def _write_status_source(self, writer: _PieceWriter, key: str) -> None:
        source = self._status_sources.get(key)
        if source is None:
            writer.add("{}")
            return
        await self._write_guarded(writer, source, key)

    # -- starters ----------------------------------------------------------

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_serve]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # No machine.Timer in this module: kept empty, not omitted, so callers treat every module alike (SPECIFICATION.md C.9).

    def start_asy_serve(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._serve_loop())

    # -- getters -----------------------------------------------------------

    async def get_dropped_count(self) -> int:
        # HTTPDropped: the connections dropped in the last 24 hours, hourly resolution, capped at COUNTER_CAP.
        return self._dropped.total(await self._uptime_s())

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (Part C.14/G.2), duck-typed rather than inherited. Not consulted by the
        # generated _collect_error_sources() - this service's /status entry is added directly in
        # _build_status_pieces() - but kept so no caller has to special-case this one module (D.10).
        return [self]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr]

    # -- others ------------------------------------------------------------

    async def reset_error_counter(self) -> bool:
        self._dropped.reset()  # ResetErrors clears the drop window too (owner, 2026-10-01)
        return await self.pr.reset()

    async def setup(self) -> bool:
        await self.pr.setup()  # the logger is set up in the boot batch, never by the serve task
        return True


def _pieces_response(pieces: list[bytes]) -> Response:
    # A plain sync iterator with an exact Content-Length, never Response.complete()'s bytes-only
    # default: without it a client reads to EOF, which real-socket soak testing timed out against.
    # Never an `async def ... yield` generator - that syntax segfaults the interpreter (Part F.1).
    return Response(
        # The vendored stub types body as str | bytes (microdot.pyi:165), yet Microdot streams a sync
        # iterator (ext/microdot.py:734). Remove the ignore when the stub accepts one (warn_unused_ignores).
        iter(pieces),  # type: ignore[arg-type]
        headers={"Content-Type": "application/json; charset=UTF-8", "Content-Length": str(sum(len(p) for p in pieces))},
    )


def _shape_errcount_entry(raw: "ErrorLog", name: str) -> "JsonDict":
    entry = raw.get(name)
    if entry is None:  # module never logged anything - the same empty shape the old {} default produced
        return {"counter": 0, "history": []}
    err_num = entry.get("ErrNum", [])
    err_type = entry.get("ErrType", [])
    return {
        "counter": entry.get("ErrCount", 0),
        "history": [{"num": n, "type": t} for n, t in zip(err_num, err_type)],  # noqa: B905 - MicroPython zip() rejects strict=, ErrEntry keeps both lists in step
        # No strict= (ruff B905): MicroPython's zip() rejects it (CPython 3.10+-only) - see
        # src/asy_fram_manager.py's identical precedent.
    }


def _shaped_error_handler(status_code: int) -> "Callable[[_RequestLike], tuple[ResponseEnvelope, int]]":
    def handler(_request: "_RequestLike") -> "tuple[ResponseEnvelope, int]":
        return ar.make_response(status_code), status_code

    return handler


async def _stream_dict_response(result: "JsonMapping", chunk_bytes: int) -> Response:
    # Memory-bounded streaming for any GET route whose response scales with device configuration
    # (SPECIFICATION.md Part I.3): the same bytes the old per-key json.dumps() fragments produced,
    # written value by value, so no allocation is a whole key's value, let alone the response.
    pieces: list[bytes] = []
    writer = _PieceWriter(pieces, chunk_bytes)
    writer.add("{")
    for index, (key, value) in enumerate(result.items()):
        writer.add(("," if index else "") + json.dumps(key) + ":")
        writer.add_value(value)
    writer.add("}")
    writer.flush()
    return _pieces_response(pieces)
