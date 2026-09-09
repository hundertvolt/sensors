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
    from collections.abc import Callable, Coroutine, Iterable, Sequence
    from typing import Any, Protocol

    import config_manager as cm
    from asy_fram_manager import AsyFramManager
    from print_log import PrintLogHistory

    class _ModuleLike(Protocol):
        # Structural stand-in for a registered sensor/settings/error-source module (real modules:
        # base_classes.py's SensorReaderConfig subclasses, asy_neopixel_driver.py's NeopixelDriver,
        # captive_dns.py's DNSServer, config_manager.py's ConfigManager - see
        # tests/test_asy_webserver_service.py's own module docstring, SPECIFICATION.md Part C.10's
        # typing convention). Only the subset a given registration group actually calls is used.
        name: str
        pr: "Any"

        def get_cfg_schema(self) -> "cm.ConfigSchema": ...
        async def get_dict_data(self) -> "dict[str, Any]": ...
        async def get_dict_cfg(self) -> "dict[str, Any]": ...
        async def _set_dict_cfg(self, data: "dict[str, Any]", cfg_vals: "cm.ConfigSchema") -> "dict[str, str]": ...
        async def get_error_counter(self) -> "dict[str, dict[str, Any]]": ...
        async def reset_error_counter(self) -> None: ...

    StatusSourceFct = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
    MaintenanceFct = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
    SystemCmdFct = Callable[[str], Coroutine[Any, Any, bool]]
    NotificationLedFct = Callable[[dict[str, Any]], Coroutine[Any, Any, bool]]
    NotificationPauseFct = Callable[[int], Coroutine[Any, Any, bool]]
    HotspotActiveFct = Callable[[], bool]

_NAME = const("WEBSERVER")
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

_MAX_STATUS_PIECE_BYTES = const(1024)  # _coalesce_json_fragments()'s own per-piece cap for
# /status's "sensors"/"errcount" sections - see that function's own comment and BACKLOG.md's
# real-hardware finding (2026-09-05) for why a per-*section* bound isn't enough on its own.

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
    result: dict[str, MaintenanceFct] = {}
    for name, fct in items:
        result[name] = fct
    return result


def _coalesce_json_fragments(parts: "list[str]", max_bytes: int = _MAX_STATUS_PIECE_BYTES) -> "list[str]":
    # Batches already-independent JSON fragments into as few pieces as practical under max_bytes -
    # see SPECIFICATION.md Part I.3 for why byte-budget batching, not per-module/per-section.
    batches: list[str] = []
    current = ""
    for part in parts:
        if not current:
            current = part
        elif len(current) + 1 + len(part) > max_bytes:
            batches.append(current)
            current = part
        else:
            current += "," + part
    if current:
        batches.append(current)
    return batches


def _append_coalesced_object(pieces: "list[str]", prefix: str, parts: "list[str]", suffix: str) -> None:
    # Appends a `{...}` object built from _coalesce_json_fragments(parts) to pieces, fusing
    # prefix/suffix onto the first/last batch rather than adding them as separate pieces - keeps
    # the common case (fits in one batch) down to exactly one piece per section.
    batches = _coalesce_json_fragments(parts)
    if not batches:
        pieces.append(prefix + suffix)
        return
    pieces.append(prefix + batches[0])
    pieces.extend("," + batch for batch in batches[1:])
    pieces[-1] += suffix


async def _stream_dict_response(result: "dict[str, Any]") -> "Any":
    # Memory-bounded streaming for any GET route whose response scales with device configuration
    # (not a fixed, small upper bound) - see SPECIFICATION.md Part I.3 for the full design and why
    # this produces byte-identical JSON to json.dumps(result). Not used for /status itself, whose
    # own sub-sections need their own per-fragment dumps first - see _build_status_pieces().
    parts = [json.dumps(k) + ":" + json.dumps(v) for k, v in result.items()]
    pieces: list[str] = []
    _append_coalesced_object(pieces, "{", parts, "}")
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
    # Forwards every stream method ext/microdot.py calls (readline/readexactly/awrite/aclose/close/
    # wait_closed/get_extra_info), each bounded by timeout_s (asyncio.TimeoutError, a plain
    # Exception not an OSError subclass - SPECIFICATION.md Part F.1). Microdot's own read-phase
    # catch silently swallows a resulting TimeoutError (see Part A.5), so this proxy is the only
    # place a per-call read timeout is ever observable - logged here, not in _serve().
    def __init__(self, stream: "Any", timeout_s: float, pr: "PrintLogHistory") -> None:
        self._stream = stream
        self._timeout_s = timeout_s
        self._pr = pr

    async def _bounded(self, coro: "Any") -> "Any":
        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError as e:
            await self._pr.wrn_s("Connection reclaimed (per-call timeout):", e, wrnno=2)
            raise

    async def readline(self) -> bytes:
        return await self._bounded(self._stream.readline())  # type: ignore[no-any-return]

    async def readexactly(self, n: int) -> bytes:
        return await self._bounded(self._stream.readexactly(n))  # type: ignore[no-any-return]

    async def awrite(self, data: bytes) -> None:
        await self._bounded(self._stream.awrite(data))

    async def aclose(self) -> None:
        await self._bounded(self._stream.aclose())

    def close(self) -> None:
        self._stream.close()

    async def wait_closed(self) -> None:
        await self._bounded(self._stream.wait_closed())

    def get_extra_info(self, name: str) -> "Any":
        return self._stream.get_extra_info(name)


class WebserverService:
    def __init__(
        self,
        app: "Any",  # a real ext/microdot.py Microdot() instance - routes are registered onto it
        # once, here; not itself importable for typing (see the microdot import comment above).
        sensors: "Sequence[_ModuleLike]" = (),
        settings: "dict[str, Sequence[SettingsGroup]] | None" = None,
        system_cmd: "SystemCmdFct | None" = None,
        notification_led: "NotificationLedFct | None" = None,
        notification_pause: "NotificationPauseFct | None" = None,
        status_sources: "dict[str, StatusSourceFct] | None" = None,
        maintenance_sensors: "Sequence[tuple[str, MaintenanceFct]]" = (),
        error_sources: "Sequence[_ModuleLike]" = (),
        max_content_length: int = 4096,
        max_connections: int = 4,  # reject-when-full ceiling, one slot of margin below the
        # confirmed MEMP_NUM_TCP_PCB=5 rp2-port ceiling - see SPECIFICATION.md Part H.7 for the
        # real-browser-testing rationale behind this value (raised from an original 3).
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
        self._system_cmd = system_cmd
        self._notification_led = notification_led
        self._notification_pause = notification_pause
        self._status_sources: dict[str, StatusSourceFct] = dict(status_sources or {})
        self._maintenance_sensors = _index_pairs(maintenance_sensors)
        self._error_sources = _index_by_name(error_sources)
        self._max_connections = max_connections
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

    async def _get_measurements(self, request: "Any") -> "Any":
        # Plain for-loop, not a dict comprehension - MicroPython doesn't support `await` inside one.
        # .update(), not result[name] = ... - see SPECIFICATION.md Part A.8 for the real
        # double-wrap production bug this avoids.
        result: dict[str, Any] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_data())
        return await _stream_dict_response(result)

    async def _get_sensors(self, request: "Any") -> "Any":
        # .update(), not result[name] = ... - see _get_measurements()'s own comment above.
        result: dict[str, Any] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_cfg())
        return await _stream_dict_response(result)  # see _get_measurements()'s own comment above

    async def _put_sensors(self, request: "Any") -> "ar.ResponseEnvelope":
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
        # Only a group whose own field subset actually intersects the request body is dispatched at
        # all - a group with no matching keys must never fire its post_fct/post_asy_fct (matches
        # the "/networking PUT: partial-field update triggers only the
        # relevant post-write hook" requirement (see SPECIFICATION.md Part A.8).
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
                # handle_set_cmd()'s own post_fct/post_asy_fct exception path (api_response.py)
                # discards its already-computed per-field results and returns an empty result dict -
                # previously this silently dropped every field in `subset` from the overall response
                # with no signal at any level (a "silent result-swallow" gap).
                # The group's post-write hook failed, so nothing it attempted can be trusted as
                # applied even if a field's own value would otherwise have validated - report every
                # field the group actually attempted as "Failed" instead of silently omitting them.
                for key in subset:
                    results[key] = "Failed"
                continue
            group_result = envelope.get("result")
            if isinstance(group_result, dict):
                results.update(group_result)
        return results

    async def _get_networking(self, request: "Any") -> "Any":
        # Streamed via _stream_dict_response() - see that function's own comment: this scales with
        # however many SettingsGroup entries this device variant's own build wires up (CLAUDE.md's
        # memory-safety hard rule).
        return await _stream_dict_response(await self._get_settings_flat("networking"))

    async def _put_networking(self, request: "Any") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results = await self._apply_settings_groups("networking", body)
        return ar.make_response(0, result=results)

    async def _get_system(self, request: "Any") -> "Any":
        return await _stream_dict_response(await self._get_settings_flat("system"))  # see _get_networking()'s own comment

    async def _put_system(self, request: "Any") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results: dict[str, Any] = dict(await self._apply_settings_groups("system", body))
        if "SystemCmd" in body:
            results["SystemCmd"] = await self._dispatch_system_cmd(body["SystemCmd"])
        return ar.make_response(0, result=results)

    async def _dispatch_system_cmd(self, cmd: "Any") -> str:
        if self._system_cmd is None or cmd not in _SYSTEM_CMDS:
            return "Invalid"
        try:  # caller-supplied callback, could legitimately misbehave - same defensive shape every
            # other caller-supplied-callback call site in this codebase already uses (e.g.
            # asy_notification_service.py's _trigger_signal()); previously unguarded here, so a
            # raise escaped straight through the route handler instead of degrading to "Failed"
            # with a persisted, diagnosable errno like every comparable callback failure elsewhere.
            ok = await self._system_cmd(cmd)
        except Exception as e:
            await self.pr.err_s("system_cmd callback failed:", e, errno=2)
            return "Failed"
        return "Valid" if ok else "Failed"

    async def _get_notification(self, request: "Any") -> "Any":
        return await _stream_dict_response(await self._get_settings_flat("notification"))  # see _get_networking()'s own comment

    async def _put_notification(self, request: "Any") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results: dict[str, Any] = dict(await self._apply_settings_groups("notification", body))
        if "lightCmdLED" in body:
            results["lightCmdLED"] = await self._dispatch_notification_led(body["lightCmdLED"])
        if "PauseTime" in body:
            results["PauseTime"] = await self._dispatch_notification_pause(body["PauseTime"])
        return ar.make_response(0, result=results)

    async def _dispatch_notification_led(self, payload: "Any") -> str:
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

    async def _dispatch_notification_pause(self, payload: "Any") -> str:
        # Reuses config_manager.py's own type_or_range_error() against a synthetic FieldSchema
        # (_PAUSE_TIME_FIELD) instead of a second, hand-rolled strict check - same int<->float
        # coercion policy every schema-backed field gets (SPECIFICATION.md Part A.8): a bool is
        # still rejected (type() excludes it, not isinstance()), and an integral float (e.g. 30.0)
        # is now accepted and coerced to int, same as any other int-typed field would be.
        # LockedCounter.set_value() (called via NotificationCoordinator.set_override_led()) clamps
        # an out-of-range value into [0, 3600] rather than raising, but legacy's own pauseAutoLED
        # command rejects an out-of-range pauseTime as Invalid (modules/sensortask-wozi.py's
        # update_valid_json(..., 0, 3600, ...)) - reject it here too, before the callback ever sees
        # it, rather than silently reporting a clamped value as a successful "Valid".
        if self._notification_pause is None:
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

    async def _get_status(self, request: "Any") -> "Any":
        # Streams /status as small pre-built json.dumps() fragments via a plain sync iterator,
        # bounding the largest single allocation regardless of the whole aggregate's size (~5.7KB on
        # real hardware, the original MemoryError root cause - SPECIFICATION.md Part I). Not an
        # `async def ... yield` generator - that syntax segfaults the interpreter here (Part F.1) -
        # so every source is awaited up front into a plain list first.
        #
        # Content-Length is set explicitly (not left to Response.complete()'s bytes-only default)
        # since the size is already fully known once every source is awaited - load-bearing, not
        # just tidiness: digital_twin/_http_client.py's fetch() falls back to a slow read-until-EOF
        # path whenever it's missing, which real-socket soak testing timed out against until this
        # was added.
        pieces = [p.encode() for p in await self._build_status_pieces()]
        content_length = sum(len(p) for p in pieces)
        return Response(
            iter(pieces),
            headers={"Content-Type": "application/json; charset=UTF-8", "Content-Length": str(content_length)},
        )

    async def _build_status_pieces(self) -> "list[str]":
        # Fixed pieces for the three small top-level keys, built with ordinary string concatenation
        # - not one piece per punctuation character (SPECIFICATION.md Part F.1's +53% finding).
        # "sensors"/"errcount" are variable-length, so they go through _coalesce_json_fragments()
        # instead (see that function's own comment, and Part I.3, for why byte-budget batching).
        pieces = ['{"networking":' + await self._dump_status_source("networking")]
        pieces.append(',"system":' + await self._dump_status_source("system"))
        pieces.append(',"notification":' + await self._dump_status_source("notification"))

        sensor_parts = []
        for name, fct in self._maintenance_sensors.items():
            sensor_parts.append(json.dumps(name) + ":" + await self._dump_maintenance(fct, name))
        _append_coalesced_object(pieces, ',"sensors":{', sensor_parts, "}")

        errcount_parts = []
        for name, module in self._error_sources.items():
            errcount_parts.append(json.dumps(name) + ":" + await self._dump_errcount_entry(module.get_error_counter, name))
        # "This service's own entry" (see SPECIFICATION.md Part A.8 for the registration-API contract) -
        # this module's own get_error_counter()/pr.get_log() aren't routed through
        # self._error_sources (WebserverService itself doesn't structurally satisfy _ModuleLike's
        # full sensor/settings surface, just the error-counter subset), so it's added directly here
        # instead of trying to register self into that dict.
        errcount_parts.append(json.dumps(_NAME) + ":" + await self._dump_errcount_entry(self.pr.get_log, _NAME))
        _append_coalesced_object(pieces, ',"errcount":{', errcount_parts, "}}")
        return pieces

    async def _dump_status_source(self, key: str) -> str:
        source = self._status_sources.get(key)
        if source is None:
            return "{}"
        try:  # caller-supplied callback, could misbehave - degrades this one key instead of letting
            # one failing source discard every other section's already-fetched data.
            return json.dumps(await source())
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", key, e, errno=6)
            return '{"error":"unavailable"}'

    async def _dump_maintenance(self, fct: "MaintenanceFct", name: str) -> str:
        try:  # see _dump_status_source()'s own comment - identical reasoning, different source kind.
            return json.dumps(await fct())
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", name, e, errno=6)
            return '{"error":"unavailable"}'

    async def _dump_errcount_entry(self, get_log_fct: "Callable[[], Coroutine[Any, Any, dict[str, dict[str, Any]]]]", name: str) -> str:
        try:  # see _dump_status_source()'s own comment - identical reasoning, different source kind.
            raw = await get_log_fct()
        except Exception as e:
            await self.pr.err_s("Status stream source failed:", name, e, errno=6)
            return '{"error":"unavailable"}'
        return json.dumps(_shape_errcount_entry(raw, name))

    async def _put_status(self, request: "Any") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        if body.get("ResetErrors") is True:
            for module in self._error_sources.values():
                await module.reset_error_counter()
            await self.reset_error_counter()  # this service's own entry, see _build_status_pieces()
        return ar.make_response(0)

    # -- static content (see SPECIFICATION.md Part A.9) ----------------------------------------

    async def _get_static_index(self, request: "Any") -> "Any":
        return self._serve_static(self._static_index)

    async def _get_static(self, request: "Any", filename: str) -> "Any":
        return self._serve_static(filename)

    def _serve_static(self, filename: str) -> "Any":
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

    async def _handle_unhandled_exception(self, request: "Any", exc: Exception) -> "tuple[dict[str, Any], int]":
        # Registered via app.errorhandler(Exception) in __init__ - see that call site's own comment
        # for why this exists purely to persist the exception into pr.err_s()/FRAM history, not to
        # shape the reply (the 500 status-code handler already does that on its own, since
        # ext/microdot.py's error_response() falls through to it regardless of whether this handler
        # is registered at all).
        await self.pr.err_s("Unhandled exception in route handler:", exc, errno=4)
        return ar.make_response(500, descr="Internal server error"), 500

    # -- connection lifecycle ---------------------------------------------------------------------

    async def _close_writer(self, writer: "Any") -> None:
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
                # Structurally unreachable today (Microdot's own blanket catch around
                # Request.create() already absorbs any EOFError raised there - see
                # _TimeoutStreamProxy's own module comment on the identical TimeoutError case) but
                # kept as defense-in-depth per the module's own "never raise" convention.
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
        server = await asyncio.start_server(self._serve, self._host, self._port)
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
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2), same shape as base_classes.py's
        # SensorReader.get_error_sources() - duck-typed, not inherited. Not actually consulted by
        # sensortask_wozi.py's own _collect_error_sources() (this service's own /status "errcount"
        # entry is added directly in _build_status_pieces() instead, see that method's own
        # comment) - kept for get_loggers()'s own sibling consistency (D.10) and so a future caller
        # doesn't have to special-case this one module.
        return [self]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr]

    async def get_error_counter(self) -> "dict[str, dict[str, Any]]":
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()


def _shape_errcount_entry(raw: "dict[str, dict[str, Any]]", name: str) -> "dict[str, Any]":
    entry = raw.get(name, {})
    err_num = entry.get("ErrNum", [])
    err_type = entry.get("ErrType", [])
    return {
        "counter": entry.get("ErrCount", 0),
        "history": [{"num": n, "type": t} for n, t in zip(err_num, err_type)],  # noqa: B905
        # No strict= (ruff B905): MicroPython's zip() rejects it (CPython 3.10+-only) - see
        # src/asy_fram_manager.py's identical precedent.
    }


def _body_as_dict(request: "Any") -> "dict[str, Any] | None":
    # None covers both a request.json access raising (malformed/undecodable JSON, matches
    # api_response.py's parse_cmd_request() precedent) and a syntactically valid but non-dict body
    # (array/string/number/null) - both degrade to the same clean ERR envelope at the call site.
    try:
        data = request.json
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _mark_connection_close(request: "Any", response: "Any") -> "Any":
    # ext/microdot.py speaks HTTP/1.0 (Response.write()'s literal status line) whose spec default is
    # already non-persistent, but RFC 7230 SS6.6 recommends a server that intends to close after
    # responding say so explicitly - added via Microdot's own supported hook, never by editing the
    # vendored file (decision 7).
    response.headers["Connection"] = "close"
    return response


def _shaped_error_handler(status_code: int, descr: str) -> "Callable[[Any], tuple[dict[str, Any], int]]":
    def handler(request: "Any") -> "tuple[dict[str, Any], int]":
        return ar.make_response(status_code, descr=descr), status_code

    return handler
