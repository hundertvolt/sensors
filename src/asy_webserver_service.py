"""Registration-based Microdot REST/API service — modules hand it named callback groups and it auto-constructs the six external endpoints plus connection hardening (timeouts, reject-when-full).
`ext/microdot.py` is never edited; every behavior change wraps/calls it instead (CLAUDE.md hard rule). See SPECIFICATION.md Part A.5 (Microdot layer) and A.8 (full endpoint reference) for the complete design."""

import asyncio
import json

# Vendored ext/microdot.py isn't on this project's mypy search path (mypy_path=["typings","src"]) -
# real device firmware freezes ext/ and src/ flat together, so this resolves fine at runtime; see
# CLAUDE.md's vendoring hard rule.
from microdot import Request, Response, abort, redirect, send_file  # type: ignore[import-not-found]
from micropython import const

import api_response as ar
from base_classes import LockedCounter
from config_manager import type_or_range_error
from print_log import make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Iterable, Sequence
    from typing import Any, Protocol, TypeVar

    import config_manager as cm
    from api_response import _RequestLike  # the shared microdot.Request stand-in (Part G.1: reuse, never reimplement)
    from asy_fram_manager import AsyFramManager
    from print_log import ErrorLog, PrintLogHistory

    _T = TypeVar("_T")

    class _ModuleLike(Protocol):
        # Structural stand-in for a registered sensor/settings/error-source module - every
        # SensorReaderConfig subclass, NeopixelDriver, DNSServer and ConfigManager satisfies it
        # (SPECIFICATION.md Part C.10). Only the subset a registration group calls is ever used.
        name: str
        pr: "Any"

        def get_cfg_schema(self) -> "cm.ConfigSchema": ...
        async def get_dict_data(self) -> "dict[str, Any]": ...
        async def get_dict_cfg(self) -> "dict[str, Any]": ...
        async def _set_dict_cfg(self, data: "dict[str, Any]", cfg_vals: "cm.ConfigSchema") -> "dict[str, str]": ...
        async def get_error_counter(self) -> "ErrorLog": ...
        async def reset_error_counter(self) -> None: ...

    class _ClosableStream(Protocol):
        # _close_writer()'s own narrower view of the stream below - exactly the two methods it
        # calls, so a writer-only object (real or test double) satisfies it without a read half.
        def close(self) -> None: ...
        async def wait_closed(self) -> None: ...

    class _StreamLike(_ClosableStream, Protocol):
        # The single asyncio Stream object MicroPython hands a start_server() callback as both
        # reader and writer; typings/'s CPython-derived StreamReader/StreamWriter split models
        # neither half of it completely (no aclose() at all), so this is the real surface.
        async def readline(self) -> bytes: ...
        async def readexactly(self, n: int) -> bytes: ...
        async def awrite(self, data: bytes) -> None: ...
        async def aclose(self) -> None: ...
        def get_extra_info(self, name: str) -> object: ...

    RouteHandler = Callable[..., Any]  # per-route handler shapes differ by design - Microdot's own
    # dispatch_request() accepts a Response, a dict, a (body, status) tuple or a bare int from any
    # of them, and passes url_args through as keyword arguments only some routes declare.

    class _MicrodotApp(Protocol):
        # Structural stand-in for the ext/microdot.py Microdot instance routes are registered onto -
        # not on this project's mypy search path either (see the microdot import comment above, and
        # api_response.py's _RequestLike; SPECIFICATION.md Part C.10's typing convention).
        def get(self, url_pattern: str) -> "Callable[[RouteHandler], RouteHandler]": ...
        def put(self, url_pattern: str) -> "Callable[[RouteHandler], RouteHandler]": ...
        def after_request(self, f: "RouteHandler") -> "RouteHandler": ...
        def after_error_request(self, f: "RouteHandler") -> "RouteHandler": ...
        def errorhandler(self, status_code_or_exception_class: "int | type[Exception]") -> "Callable[[RouteHandler], RouteHandler]": ...
        async def handle_request(self, reader: "_StreamLike", writer: "_StreamLike") -> None: ...
        async def dispatch_request(self, req: "_RequestLike | None") -> "Response": ...  # not called
        # from this module - part of the surface because tests drive routes through it directly.

    StatusSourceFct = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
    MaintenanceFct = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
    SystemCmdFct = Callable[[str], Coroutine[Any, Any, bool]]
    NotificationLedFct = Callable[[dict[str, Any]], Coroutine[Any, Any, bool]]
    NotificationPauseFct = Callable[[int], Coroutine[Any, Any, bool]]
    HotspotActiveFct = Callable[[], bool]

_NAME = const("WEBSERVER")

# This service's one optional live cross-instance dependency (SPECIFICATION.md Part C.14): its FRAM
# error-log target, resolved from [device.wiring].fram_target implicitly because this is mandatory
# infra, never an [[instance]] entry - the same tag system_service/wifi/ntp carry.
# @wiring fram_target AsyFramManager fram optional kwarg

_SYSTEM_CMDS = ("reboot", "bootloader", "mempause")  # the only enum values ever forwarded to
# system_cmd() - never a client-supplied duration (mempause's fixed 300s lives in system_cmd()'s own
# implementation, e.g. SystemService.pause_permanent_storage() - see SPECIFICATION.md Part A.8).
_PAUSE_TIME_MAX = const(3600)  # inclusive upper bound for a client-supplied PauseTime - matches
# legacy's own pauseAutoLED command range and asy_notification_service.py's own
# LockedCounter(max_val=_MAX_OVERRIDE_TIME) clamp ceiling, kept here as its own constant (not
# imported) since this module has no other coupling to asy_notification_service.py.
_PAUSE_TIME_FIELD: "cm.FieldSchema" = ("PauseTime", "int", 0, 0, _PAUSE_TIME_MAX, None)  # dispatch-only, not schema-
# backed by a real ConfigManager - a synthetic FieldSchema record so _dispatch_notification_pause()
# can reuse config_manager.py's own type_or_range_error() (and its int<->float coercion policy,
# SPECIFICATION.md Part A.8) instead of a second, hand-rolled strict check.

_MAX_PENDING_FRAGMENTS = const(16)  # _PieceWriter's list never outgrows 16 slots (64 B on the RP2040)
_MAX_STATUS_PIECE_BYTES = const(256)  # _PieceWriter's per-piece cap for every streamed route. Sized
# to the holes a fragmented heap still has at gc.threshold(-1), not to its one large run: under load
# that run is gone and ~870 B pieces fail with ~100 KB free (SPECIFICATION.md Part I.3).

_ERROR_SHAPES = (  # (status_code, descr) - registered via @app.errorhandler for shaped JSON bodies,
    # per "Criteria for this step to finish": at least 400/404/405/413/500 wired.
    (400, "Bad request"),
    (404, "Not found"),
    (405, "Method not allowed"),
    (413, "Payload too large"),
    (500, "Internal server error"),
)


def _index_by_name(items: "Iterable[_ModuleLike]") -> "dict[str, _ModuleLike]":
    # Last-registration-wins, by construction - decision 6 (see SPECIFICATION.md Part A.8): the
    # simplest per-item loop already behaves this way, deliberately no dedup/guard code on top.
    result: dict[str, _ModuleLike] = {}
    for item in items:
        result[item.name] = item
    return result


def _index_pairs(items: "Iterable[tuple[str, MaintenanceFct]]") -> "dict[str, MaintenanceFct]":
    return dict(items)


class _PieceWriter:
    # Concatenates adjacent JSON text fragments into pieces of at most max_bytes, never splitting
    # one - so the largest allocation is bounded by the largest fragment, not by the response.
    def __init__(self, pieces: "list[str]", max_bytes: int = _MAX_STATUS_PIECE_BYTES) -> None:
        self._pieces = pieces
        self._group: list[str] = []
        self._size = 0
        self._max_bytes = max_bytes

    def add(self, fragment: str) -> None:
        if self._group and self._size + len(fragment) > self._max_bytes:
            self.flush()
        self._group.append(fragment)
        self._size += len(fragment)
        if len(self._group) == _MAX_PENDING_FRAGMENTS:
            # Collapsed, never left to grow: a piece of tiny fragments would otherwise need a list
            # array as large as the piece itself - the very block this writer exists to avoid.
            self._group = ["".join(self._group)]

    def flush(self) -> None:
        if self._group:
            self._pieces.append("".join(self._group))
            self._group = []
            self._size = 0

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
        else:
            self.add(json.dumps(value))


async def _stream_dict_response(result: "dict[str, Any]") -> "Response":
    # Memory-bounded streaming for any GET route whose response scales with device configuration
    # (SPECIFICATION.md Part I.3): the same bytes the old per-key json.dumps() fragments produced,
    # written value by value, so no allocation is a whole key's value, let alone the response.
    pieces: list[str] = []
    writer = _PieceWriter(pieces)
    writer.add("{")
    for index, (key, value) in enumerate(result.items()):
        writer.add(("," if index else "") + json.dumps(key) + ":")
        writer.add_value(value)
    writer.add("}")
    writer.flush()
    encoded = [p.encode() for p in pieces]
    content_length = sum(len(p) for p in encoded)
    return Response(
        iter(encoded),
        headers={"Content-Type": "application/json; charset=UTF-8", "Content-Length": str(content_length)},
    )


def _flatten_cfg_values(values: "dict[str, Any]") -> "dict[str, Any]":
    # get_dict_cfg() returns either a flat dict or config_manager.make_dict()'s nested
    # {type_name: {field: value}} shape - flattens to always give _get_settings_flat() top-level
    # keys either way. See digital_twin/README.md for the real production bug this fixed.
    flat: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, dict):
            flat.update(value)
        else:
            flat[key] = value
    return flat


class SettingsGroup:
    def __init__(
        self,
        module: "_ModuleLike",
        fields: "Sequence[str]",
        post_fct: "Callable[[], None] | None" = None,
        post_asy_fct: "Callable[[], Coroutine[Any, Any, None]] | None" = None,
    ) -> None:
        self.module = module
        self.fields = tuple(fields)
        self.post_fct = post_fct
        self.post_asy_fct = post_asy_fct


class _TimeoutStreamProxy:
    # Forwards every stream method ext/microdot.py calls, each bounded by timeout_s (a plain
    # asyncio.TimeoutError, not an OSError subclass - Part F.1). Microdot's read-phase catch
    # swallows it (Part A.5), so this proxy is the only place a read timeout is observable.
    def __init__(self, stream: "_StreamLike", timeout_s: float, pr: "PrintLogHistory") -> None:
        self._stream = stream
        self._timeout_s = timeout_s
        self._pr = pr

    async def _bounded(self, coro: "Awaitable[_T]") -> "_T":
        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError as e:
            await self._pr.wrn_s("Connection reclaimed (per-call timeout):", e, wrnno=2)
            raise

    async def readline(self) -> bytes:
        return await self._bounded(self._stream.readline())

    async def readexactly(self, n: int) -> bytes:
        return await self._bounded(self._stream.readexactly(n))

    async def awrite(self, data: bytes) -> None:
        await self._bounded(self._stream.awrite(data))

    async def aclose(self) -> None:
        await self._bounded(self._stream.aclose())

    def close(self) -> None:
        self._stream.close()

    async def wait_closed(self) -> None:
        await self._bounded(self._stream.wait_closed())

    def get_extra_info(self, name: str) -> object:
        return self._stream.get_extra_info(name)


class WebserverService:
    def __init__(
        self,
        app: "_MicrodotApp",  # a real ext/microdot.py Microdot() instance - routes are registered
        # onto it once, here; not itself importable for typing (see the microdot import comment above).
        sensors: "Sequence[_ModuleLike]" = (),
        settings: "dict[str, Sequence[SettingsGroup]] | None" = None,
        build_info: "dict[str, Any] | None" = None,  # verbatim "build" sub-entry on GET /system's
        # otherwise-flat response (firmwareVersion/websiteVersion/buildDate - SPECIFICATION.md
        # Part L.7) - a fixed, generator-supplied fact this class never computes itself; None
        # (default) omits the key entirely, matching every other optional constructor knob here.
        system_cmd: "SystemCmdFct | None" = None,
        notification_led: "NotificationLedFct | None" = None,
        notification_pause: "NotificationPauseFct | None" = None,
        status_sources: "dict[str, StatusSourceFct] | None" = None,
        maintenance_sensors: "Sequence[tuple[str, MaintenanceFct]]" = (),
        error_sources: "Sequence[_ModuleLike]" = (),
        max_content_length: int = 2048,  # 1.56x the largest schema-permitted body, ~9x real traffic (I.6)
        max_connections: int = 8,  # reject-when-full ceiling, kept below the firmware's own
        # MEMP_NUM_TCP_PCB (toolchain/versions.toml) with margin for TIME_WAIT churn - Part H.7
        # holds that as a RELATIONSHIP, not a number; buildgen passes the per-device value.
        backlog: int | None = None,  # listen queue depth; None derives max_connections + 1 so one
        # over-ceiling arrival is queued and refused by _serve() rather than dropped unseen by
        # lwIP's accept queue. Never below max_connections - see SPECIFICATION.md Part H.7.
        per_call_timeout_s: float = 5.0,
        outer_cap_s: float = 15.0,
        host: str = "0.0.0.0",
        port: int = 80,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
        static_mount: str | None = None,  # e.g. "/html" (see SPECIFICATION.md Part A.9) - the
        # freezefs mount point of an already-`import`ed frozen static-content module. None (default)
        # registers no static routes at all - every existing route/registration above is unaffected.
        static_index: str = "index.html",  # served for both "/" and "/<static_index>" verbatim.
        is_hotspot_active: "HotspotActiveFct | None" = None,  # e.g. AsyConnTime.is_hotspot_active
        # (see SPECIFICATION.md Part A.5) - only consulted by _serve_static()'s own
        # unmatched-path fallback, and only when static_mount is not None. None (default) reproduces
        # today's plain-404 fallback exactly - every existing call site omits this and is unaffected.
    ) -> None:
        self.pr: PrintLogHistory = make_logger(fram, history_length, debug, _NAME)
        self._app = app
        self._sensors = _index_by_name(sensors)
        self._settings: dict[str, list[SettingsGroup]] = {k: list(v) for k, v in (settings or {}).items()}
        self._build_info = build_info
        self._system_cmd = system_cmd
        self._notification_led = notification_led
        self._notification_pause = notification_pause
        self._status_sources: dict[str, StatusSourceFct] = dict(status_sources or {})
        self._maintenance_sensors = _index_pairs(maintenance_sensors)
        self._error_sources = _index_by_name(error_sources)
        self._max_connections = max_connections
        # Clamped rather than rejected, matching LockedCounter's own out-of-range convention: a
        # backlog under the ceiling silently caps concurrency below max_connections, which reads as
        # an application bug. buildgen rejects the same mistake in config, where it can be named.
        self._backlog = max_connections + 1 if backlog is None else max(backlog, max_connections)
        self._per_call_timeout_s = per_call_timeout_s
        self._outer_cap_s = outer_cap_s
        self._host = host
        self._port = port
        self._open_conns = LockedCounter(init_value=0, max_val=0xFFFFFFFF)
        self._static_mount = static_mount
        self._static_index = static_index
        self._is_hotspot_active = is_hotspot_active

        Request.max_content_length = max_content_length  # a Request *class* attribute, not
        # per-app-instance (ext/microdot.py's own module docstring example) - see
        # tests/test_asy_webserver_service.py's own boundary-test comment on this.

        # Bound to the same value, never microdot's own 16 KB default: Request.create() buffers the
        # body before dispatch_request() answers 413, so a larger cap here has an oversized body
        # read into one contiguous allocation and then thrown away (SPECIFICATION.md Part I.6).
        Request.max_body_length = max_content_length

        app.get("/measurements")(self._get_measurements)
        app.get("/sensors")(self._get_sensors)
        app.put("/sensors")(self._put_sensors)
        app.get("/networking")(self._get_networking)
        app.put("/networking")(self._put_networking)
        app.get("/system")(self._get_system)
        app.put("/system")(self._put_system)
        app.get("/status")(self._get_status)
        app.put("/status")(self._put_status)
        app.get("/notification")(self._get_notification)
        app.put("/notification")(self._put_notification)

        app.after_request(_mark_connection_close)
        app.after_error_request(_mark_connection_close)  # after_request alone misses every
        # error-response path (400/404/405/413/500) - dispatch_request() only runs after_request
        # handlers on its happy path (see SPECIFICATION.md Part A.8, decision 7).
        for status_code, descr in _ERROR_SHAPES:
            app.errorhandler(status_code)(_shaped_error_handler(status_code, descr))
        # Catch-all for logging/FRAM-history only - Microdot's own error_response() fallthrough
        # already gives the correct reply shape via the 500 handler above regardless (see
        # SPECIFICATION.md Part A.5); this just gets the exception into pr.err_s()/history.
        app.errorhandler(Exception)(self._handle_unhandled_exception)

        if static_mount is not None:
            # Registered last: "/<path:filename>"'s own regex also matches every fixed path above
            # (e.g. "/measurements") - Microdot's find_route() returns the first matching pattern,
            # so every exact-match API route must already be registered or it would be shadowed.
            app.get("/")(self._get_static_index)
            app.get("/<path:filename>")(self._get_static)

    # -- /measurements, /sensors --------------------------------------------------------------

    async def _get_measurements(self, _request: "_RequestLike") -> "Response":
        # Plain for-loop, not a dict comprehension - MicroPython doesn't support `await` inside one.
        # .update(), not result[name] = ... - see SPECIFICATION.md Part A.8 for the real
        # double-wrap production bug this avoids.
        result: dict[str, Any] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_data())
        return await _stream_dict_response(result)

    async def _get_sensors(self, _request: "_RequestLike") -> "Response":
        # .update(), not result[name] = ... - see _get_measurements()'s own comment above.
        result: dict[str, Any] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_cfg())
        return await _stream_dict_response(result)  # see _get_measurements()'s own comment above

    async def _put_sensors(self, request: "_RequestLike") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results: dict[str, Any] = {}
        for name, fields in body.items():
            module = self._sensors.get(name)
            if module is None or not isinstance(fields, dict):
                continue  # unknown sensor key, or a malformed per-sensor sub-object - silently
                # ignored, matches ConfigManager.write_config()'s own per-key "Invalid" convention
                # extended to the HTTP layer (see SPECIFICATION.md Part A.8, section B).
            results[name] = await module._set_dict_cfg(fields, module.get_cfg_schema())
        return ar.make_response(0, result=results)

    # -- flat settings endpoints (/networking, /system, /notification) ------------------------

    async def _get_settings_flat(self, endpoint: str) -> "dict[str, Any]":
        result: dict[str, Any] = {}
        for group in self._settings.get(endpoint, []):
            values = _flatten_cfg_values(await group.module.get_dict_cfg())
            for field in group.fields:
                if field in values:
                    result[field] = values[field]
        return result

    async def _apply_settings_groups(self, endpoint: str, body: "dict[str, Any]") -> "dict[str, str]":
        # Only a group whose field subset intersects the request body is dispatched: one with no
        # matching keys must never fire its post_fct/post_asy_fct, which is what "a partial-field
        # update triggers only the relevant post-write hook" means (SPECIFICATION.md Part A.8).
        results: dict[str, str] = {}
        for group in self._settings.get(endpoint, []):
            subset = {k: v for k, v in body.items() if k in group.fields}
            if not subset:
                continue
            envelope = await ar.handle_set_cmd(
                group.module,  # type: ignore[arg-type]  # structurally SensorReaderConfig-shaped
                # (get_cfg_schema()/_set_dict_cfg()/.pr) - _ModuleLike is a narrower Protocol, not
                # importable here without a real coupling to base_classes.py's concrete class.
                subset,
                group.module.get_cfg_schema(),
                group.post_fct,
                group.post_asy_fct,
            )
            if envelope.get("res") == "ERR":
                # handle_set_cmd()'s post-hook exception path returns an empty result dict, which
                # used to drop every field in `subset` from the response with no signal anywhere.
                # Nothing the group attempted can be trusted as applied, so report it all "Failed".
                for key in subset:
                    results[key] = "Failed"
                continue
            group_result = envelope.get("result")
            if isinstance(group_result, dict):
                results.update(group_result)
        return results

    async def _get_networking(self, _request: "_RequestLike") -> "Response":
        # Streamed via _stream_dict_response() - see that function's own comment: this scales with
        # however many SettingsGroup entries this device variant's own build wires up (CLAUDE.md's
        # memory-safety hard rule).
        return await _stream_dict_response(await self._get_settings_flat("networking"))

    async def _put_networking(self, request: "_RequestLike") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results = await self._apply_settings_groups("networking", body)
        return ar.make_response(0, result=results)

    async def _get_system(self, _request: "_RequestLike") -> "Response":
        result = await self._get_settings_flat("system")  # see _get_networking()'s own comment
        if self._build_info is not None:
            result["build"] = self._build_info
        return await _stream_dict_response(result)

    async def _put_system(self, request: "_RequestLike") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results: dict[str, Any] = dict(await self._apply_settings_groups("system", body))
        if "SystemCmd" in body:
            results["SystemCmd"] = await self._dispatch_system_cmd(body["SystemCmd"])
        return ar.make_response(0, result=results)

    async def _dispatch_system_cmd(self, cmd: object) -> str:
        # object, not a narrower type: cmd is whatever JSON value the client put in "SystemCmd".
        # The isinstance() guard is redundant at runtime (a non-str can never be in _SYSTEM_CMDS)
        # and only states that contract - same shape as the other two dispatchers below.
        if self._system_cmd is None or not isinstance(cmd, str) or cmd not in _SYSTEM_CMDS:
            return "Invalid"
        try:  # caller-supplied callback, could legitimately misbehave - same defensive shape every
            # other caller-supplied-callback site uses (Part G.2). Unguarded, a raise escaped
            # through the route handler instead of degrading to "Failed" with a persisted errno,
            # the way every comparable callback failure does.
            ok = await self._system_cmd(cmd)
        except Exception as e:
            await self.pr.err_s("system_cmd callback failed:", e, errno=2)
            return "Failed"
        return "Valid" if ok else "Failed"

    async def _get_notification(self, _request: "_RequestLike") -> "Response":
        return await _stream_dict_response(await self._get_settings_flat("notification"))  # see _get_networking()'s own comment

    async def _put_notification(self, request: "_RequestLike") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results: dict[str, Any] = dict(await self._apply_settings_groups("notification", body))
        if "lightCmdLED" in body:
            results["lightCmdLED"] = await self._dispatch_notification_led(body["lightCmdLED"])
        if "PauseTime" in body:
            results["PauseTime"] = await self._dispatch_notification_pause(body["PauseTime"])
        return ar.make_response(0, result=results)

    async def _dispatch_notification_led(self, payload: object) -> str:
        if self._notification_led is None or not isinstance(payload, dict):
            return "Invalid"
        try:  # caller-supplied callback, could legitimately misbehave - see _dispatch_system_cmd()'s
            # own comment on why this needs the same guard every comparable callback elsewhere in
            # this codebase already has.
            ok = await self._notification_led(payload)
        except Exception as e:
            await self.pr.err_s("notification_led callback failed:", e, errno=3)
            return "Failed"
        return "Valid" if ok else "Failed"

    async def _dispatch_notification_pause(self, payload: object) -> str:
        # Reuses type_or_range_error() against a synthetic FieldSchema rather than a second
        # hand-rolled check, so this field gets the same int<->float policy as every schema-backed
        # one (Part A.8): bool rejected, an integral float accepted and coerced.

        # LockedCounter.set_value() clamps out of range rather than raising, but legacy rejected an
        # out-of-range pauseTime as Invalid - so reject it here too, before the callback sees it,
        # rather than reporting a clamped value as a successful "Valid".
        if self._notification_pause is None or not isinstance(payload, (int, float)):
            return "Invalid"
        is_error, coerced_payload = type_or_range_error(payload, _PAUSE_TIME_FIELD)
        if is_error:
            return "Invalid"
        try:  # caller-supplied callback, could legitimately misbehave - see _dispatch_system_cmd()'s
            # own comment on why this needs the same guard every comparable callback elsewhere in
            # this codebase already has.
            ok = await self._notification_pause(coerced_payload)
        except Exception as e:
            await self.pr.err_s("notification_pause callback failed:", e, errno=5)
            return "Failed"
        return "Valid" if ok else "Failed"

    # -- /status ---------------------------------------------------------------------------------

    async def _get_status(self, _request: "_RequestLike") -> "Response":
        # Streams /status as small pre-built json.dumps() fragments through a plain sync iterator,
        # bounding the largest allocation whatever the aggregate's size (Part I). Never an
        # `async def ... yield` generator - that syntax segfaults the interpreter (Part F.1).

        # Content-Length is set explicitly rather than left to Response.complete()'s bytes-only
        # default: the size is known once every source is awaited, and without it a client falls
        # back to read-until-EOF, which real-socket soak testing timed out against.
        pieces = [p.encode() for p in await self._build_status_pieces()]
        content_length = sum(len(p) for p in pieces)
        return Response(
            iter(pieces),
            headers={"Content-Type": "application/json; charset=UTF-8", "Content-Length": str(content_length)},
        )

    async def _build_status_pieces(self) -> "list[str]":
        # One _PieceWriter, flushed at every top-level section: each section starts its own piece
        # and no piece exceeds the cap, whatever a section holds - one entry per registered error
        # source, for "errcount" (Part I.3). Values are written, never json.dumps()'d whole.
        pieces: list[str] = []
        writer = _PieceWriter(pieces)
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
        # This service's own entry (Part A.8's registration contract). WebserverService satisfies
        # only the error-counter subset of _ModuleLike, not the full sensor/settings surface, so it
        # is added here directly rather than registered into self._error_sources.
        writer.add(json.dumps(_NAME) + ":")
        await self._write_errcount_entry(writer, self.pr.get_log, _NAME)
        writer.add("}}")
        writer.flush()
        return pieces

    async def _write_status_source(self, writer: "_PieceWriter", key: str) -> None:
        source = self._status_sources.get(key)
        if source is None:
            writer.add("{}")
            return
        await self._write_guarded(writer, source, key)

    async def _write_guarded(self, writer: "_PieceWriter", fct: "Callable[[], Coroutine[Any, Any, dict[str, Any]]]", name: str) -> None:
        try:  # caller-supplied callback, could misbehave - degrades this one key instead of letting
            # one failing source discard every other section's already-fetched data.
            value = await fct()
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", name, e, errno=6)
            writer.add('{"error":"unavailable"}')
            return
        writer.add_value(value)

    async def _write_errcount_entry(self, writer: "_PieceWriter", get_log_fct: "Callable[[], Coroutine[Any, Any, ErrorLog]]", name: str) -> None:
        try:  # see _write_guarded()'s own comment - identical reasoning, different source kind.
            raw = await get_log_fct()
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", name, e, errno=6)
            writer.add('{"error":"unavailable"}')
            return
        writer.add_value(_shape_errcount_entry(raw, name))

    async def _put_status(self, request: "_RequestLike") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        if body.get("ResetErrors") is True:
            for module in self._error_sources.values():
                await module.reset_error_counter()
            await self.reset_error_counter()  # this service's own entry, see _build_status_pieces()
        return ar.make_response(0)

    # -- static content (see SPECIFICATION.md Part A.9) ----------------------------------------

    async def _get_static_index(self, _request: "_RequestLike") -> "Response":
        return self._serve_static(self._static_index)

    async def _get_static(self, _request: "_RequestLike", filename: str) -> "Response":
        return self._serve_static(filename)

    def _serve_static(self, filename: str) -> "Response":
        if ".." in filename:
            abort(404)  # guard-clause before touching the mounted filesystem - cheap and uniform
            # even though freezefs's own VfsFrozen already refuses to escape its mount root.
        assert self._static_mount is not None  # only ever registered as a route when it isn't
        try:
            return send_file(self._static_mount + "/" + filename, compressed=True, file_extension=".gz")
        except OSError:  # no such file in the mounted filesystem
            if self._is_hotspot_active is not None and self._is_hotspot_active():
                # Captive-portal redirect fallback, triggering phones' "Sign in to network" popup -
                # see SPECIFICATION.md Part A.5 for the full mechanism and why no try/except is needed.
                return redirect("/")
            abort(404)

    # -- error handling ----------------------------------------------------------------------------

    async def _handle_unhandled_exception(self, _request: "_RequestLike", exc: Exception) -> "tuple[dict[str, Any], int]":
        # Registered via app.errorhandler(Exception) in __init__, purely to persist the exception
        # into FRAM history - never to shape the reply. The 500 status-code handler already does
        # that on its own, whether or not this one is registered (Part A.5).
        await self.pr.err_s("Unhandled exception in route handler:", exc, errno=4)
        return ar.make_response(500, descr="Internal server error"), 500

    # -- connection lifecycle ---------------------------------------------------------------------

    async def _close_writer(self, writer: "_ClosableStream") -> None:
        try:
            writer.close()
        except Exception as e:  # best-effort cleanup, never load-bearing - still logged (Part C.7's
            # silent-failure-masking convention) since a repeatedly-failing close() could leak TCP
            # PCBs under this platform's tiny connection ceiling with no other trace.
            await self.pr.wrn_s("Error closing connection writer:", e, wrnno=4)
        try:
            await asyncio.wait_for(writer.wait_closed(), self._per_call_timeout_s)
        except Exception as e:  # bounds a hanging wait_closed() (F.6) as well as any raised error
            await self.pr.wrn_s("Error waiting for writer to close:", e, wrnno=5)

    async def _serve(self, reader: "Any", writer: "Any") -> None:
        # Any, not _StreamLike: asyncio.start_server() types its callback as
        # Callable[[StreamReader, StreamWriter], ...] (typings/'s CPython-shaped alias), and neither
        # of those stub classes satisfies the one real Stream surface _TimeoutStreamProxy forwards.
        current = await self._open_conns.increment()
        if current > self._max_connections:
            # Reject-when-full (decision 3): silently close, no accept, no response ever written -
            # cheapest, doesn't risk the rejection path itself becoming a resource consumer.
            await self._open_conns.decrement()
            await self._close_writer(writer)
            return
        try:
            proxy_reader = _TimeoutStreamProxy(reader, self._per_call_timeout_s, self.pr)
            proxy_writer = _TimeoutStreamProxy(writer, self._per_call_timeout_s, self.pr)
            try:
                await asyncio.wait_for(self._app.handle_request(proxy_reader, proxy_writer), self._outer_cap_s)
            except asyncio.CancelledError:
                raise  # never swallow a genuine task cancellation
            except EOFError as e:
                # Structurally unreachable today - Microdot's blanket catch around Request.create()
                # absorbs any EOFError raised there, the same shape as the TimeoutError case above -
                # but kept as defense in depth under this module's own "never raise" convention.
                await self.pr.wrn_s("Connection reclaimed (peer closed early):", e, wrnno=1)
            except asyncio.TimeoutError as e:
                # Either the outer wait_for() above (bounds a Slowloris-paced client no per-call
                # timeout alone would catch) or a write-phase proxy timeout - a read-phase one
                # already logged its own warning inside the proxy and never reaches this far.
                await self.pr.wrn_s("Connection reclaimed (timed out):", e, wrnno=2)
            except OSError as e:  # a genuine, real socket-level failure (e.g. a broken pipe) -
                # never actually raised by any of this module's own fakes/proxy, kept for real
                # hardware defense-in-depth.
                await self.pr.wrn_s("Connection reclaimed (socket error):", e, wrnno=3)
            except Exception as e:  # never raises out of this task - see module docstring
                await self.pr.err_s("Unexpected error serving connection:", e, errno=1)
        finally:
            await self._close_writer(writer)
            await self._open_conns.decrement()

    async def _run(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors, matches every other
        # module's own main-loop convention (see e.g. asy_wifi_service.py's wlan_connect()).
        # backlog is explicit, never MicroPython's own default of 5 (extmod/asyncio/stream.py):
        # inherited, it silently caps the accept queue below any raised max_connections.
        server = await asyncio.start_server(self._serve, self._host, self._port, backlog=self._backlog)
        await server.wait_closed()

    def _start_serving(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._run())

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self._start_serving]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape, kept
        # empty rather than omitted so callers can treat every driver/service uniformly - matches
        # asy_neopixel_driver.py's/asy_notification_service.py's own identical precedent; found
        # missing entirely during the Step 7 audit, unlike those two).

    def get_error_sources(self) -> "list[Any]":
        # Fan-in primitive (Part C.14/G.2), duck-typed rather than inherited. Not consulted by the
        # generated _collect_error_sources() - this service's /status entry is added directly in
        # _build_status_pieces() - but kept so no caller has to special-case this one module (D.10).
        return [self]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr]

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()


def _shape_errcount_entry(raw: "ErrorLog", name: str) -> "dict[str, Any]":
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


def _body_as_dict(request: "_RequestLike") -> "dict[str, Any] | None":
    # None covers both a request.json access raising (malformed/undecodable JSON, matches
    # api_response.py's parse_cmd_request() precedent) and a syntactically valid but non-dict body
    # (array/string/number/null) - both degrade to the same clean ERR envelope at the call site.
    try:
        data = request.json
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _mark_connection_close(_request: "_RequestLike", response: "Response") -> "Response":
    # ext/microdot.py speaks HTTP/1.0, whose default is already non-persistent, but RFC 7230 SS6.6
    # recommends saying so explicitly - added through Microdot's own supported hook, never by
    # editing the vendored file.
    response.headers["Connection"] = "close"
    return response


def _shaped_error_handler(status_code: int, descr: str) -> "Callable[[_RequestLike], tuple[dict[str, Any], int]]":
    def handler(_request: "_RequestLike") -> "tuple[dict[str, Any], int]":
        return ar.make_response(status_code, descr=descr), status_code

    return handler
