"""Registration-based Microdot REST/API service — modules hand it named callback groups and it auto-constructs the six external endpoints plus connection hardening (timeouts, reject-when-full).
`ext/microdot.py` is never edited; every behavior change wraps/calls it instead (CLAUDE.md hard rule). See SPECIFICATION.md Part A.5 (Microdot layer) and A.8 (full endpoint reference) for the complete design."""

import asyncio

# Vendored ext/microdot.py isn't on this project's mypy search path (mypy_path=["typings","src"]) -
# real device firmware freezes ext/ and src/ flat together, so this resolves fine at runtime; see
# CLAUDE.md's vendoring hard rule.
from microdot import Request, abort, redirect, send_file  # type: ignore[import-not-found]
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


def _flatten_cfg_values(values: "dict[str, Any]") -> "dict[str, Any]":
    # get_dict_cfg() has two real shapes across this codebase's registrable modules: a genuinely
    # flat dict (SystemService's own override, self.cfgmgr.get_dict(...)) or
    # config_manager.make_dict()'s {type_name: {field: value}} nesting (base_classes.py's
    # SensorReaderConfig default - AsyConnTime/AsyNtpClient/NotificationCoordinator among them).
    # _get_settings_flat() needs every field to be a top-level key regardless of which shape its
    # module returns - found and fixed via twin-based integration
    # testing (tests/test_digital_twin_sensortask_integration.py): without this, /networking and
    # /notification always returned {} in production (every field they source is nested-shaped),
    # and /system silently dropped GMTOffset/DSTOffset (sourced from ntp, also nested-shaped) while
    # DebugLevel (sourced from sysfunct, already flat) happened to work. Safe to merge any
    # dict-valued top-level entry unconditionally: every config schema in this codebase today is
    # flat scalar fields only.
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
    # Forwards every method ext/microdot.py's Request.create()/Response.write() actually call on a
    # reader/writer (readline, readexactly, awrite, aclose, close, wait_closed, get_extra_info) -
    # enumerated by grepping ext/microdot.py directly, not guessed - each async call individually
    # bounded by timeout_s (BACKLOG.md's "Microdot hardening design" step 2). A timeout raises
    # asyncio.TimeoutError - confirmed directly from the pinned v1.28.0 source
    # (extmod/asyncio/core.py: `class TimeoutError(Exception)`) to be a PLAIN Exception, *not* an
    # OSError subclass (see SPECIFICATION.md Part F.1). This
    # matters a lot: ext/microdot.py's handle_request() wraps Request.create() in `except OSError ...
    # else: raise` *then* `except Exception as exc: print_exception(exc)` - since a per-call read
    # timeout isn't an OSError, it hits the second clause, which does NOT re-raise. A per-call
    # *read*-phase timeout (request line/headers/body) is therefore silently absorbed by Microdot
    # itself, which then writes its own ordinary (aborted-request) response and closes normally -
    # never propagating to WebserverService._serve()'s own try/except at all. The one place that
    # genuinely still reaches _serve() is the *write* phase (handle_request()'s second try/except,
    # around res.write()+writer.aclose(), only catches OSError - a TimeoutError there propagates
    # straight out) and the outer per-connection asyncio.wait_for() in _serve() itself, whose own
    # cancellation-driven TimeoutError is unaffected by any of this (see _serve()'s own comment).
    # Since Microdot's own swallow means this proxy is the *only* place a per-call read timeout is
    # ever observable at all, it logs a warning here, at the point of the actual event, rather than
    # relying on catching a propagated exception in _serve() - decision 8's "warn on every per-call
    # or outer-cap reclaim" requirement would otherwise silently miss every read-phase reclaim.
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
        max_connections: int = 4,  # reject-when-full ceiling - one slot of margin below the
        # confirmed MEMP_NUM_TCP_PCB=5 rp2-port ceiling (lwIP's own compile-time default for this
        # build - confirmed directly against the vendored lwIP source and the rp2 port's own
        # lwipopts, no project override anywhere), for TIME_WAIT sockets from just-closed
        # connections (every response sends `Connection: close`) to drain without blocking a new
        # one. Raised from the original 3 once SPECIFICATION.md Part H.7's real-browser testing
        # showed a single page load's own concurrent connections (previously up to ~9: index.html +
        # style.css + 6 separate JS module files + definitions.json) could alone approach this
        # ceiling before any other client (e.g. an OpenHAB instance polling REST endpoints
        # alongside a browser session) even connects - see scripts/build_website.sh's own "Bundling"
        # comment for the matching fix on the JS-file-count side (6 files down to 1), which was the
        # bigger lever; this one small bump uses one more slot of the real remaining headroom.
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
        # (CAPTIVE_PORTAL_HOTSPOT_REDIRECT_PLAN.md) - only consulted by _serve_static()'s own
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
        # Catch-all for an exception ext/microdot.py's dispatch_request() catches but finds no
        # exception-class handler for (BACKLOG.md's "No @app.errorhandler registrations exist
        # anywhere yet" item, part 1) - Microdot's own except-Exception branch already falls
        # through to error_response(req, 500, ...), which already resolves through the 500
        # status-code handler just registered above (ext/microdot.py's error_response() checks
        # self.error_handlers[500] directly - confirmed by reading it), so the *response shape*
        # for an unhandled exception was already correct without this. What was still missing:
        # Microdot's own print_exception(exc) (dispatch_request()'s except-Exception branch) is a
        # bare stdout print that never reaches this module's own pr.err_s()/FRAM history - an
        # exception-class handler is the only registration shape that receives the actual
        # exception object (invoke_handler(handler, req, exc), confirmed directly against
        # ext/microdot.py), so this is purely for the logging/history side, not the reply shape.
        app.errorhandler(Exception)(self._handle_unhandled_exception)

        if static_mount is not None:
            # Registered last (see this module's own docstring): "/<path:filename>"'s own regex
            # (`/(.+)`) also matches every fixed path above (e.g. "/measurements") - Microdot's
            # find_route() returns the *first* registered pattern that matches, so every exact-match
            # API route must already be in app.url_map before this one is added, or it would be
            # silently shadowed.
            app.get("/")(self._get_static_index)
            app.get("/<path:filename>")(self._get_static)

    # -- /measurements, /sensors --------------------------------------------------------------

    async def _get_measurements(self, request: "Any") -> "dict[str, Any]":
        # A plain for-loop, not a dict comprehension - MicroPython doesn't support `await` inside a
        # comprehension (confirmed directly: raises SyntaxError at import time), unlike CPython.
        # .update(), not result[name] = ... : every real driver's own get_dict_data() (via
        # config_manager.make_dict()) already returns a {name: {...}}-shaped dict keyed by its own
        # name (the same name this loop's own `name` is bound to) - indexing by name here on top of
        # that doubled it into {"SCD30": {"SCD30": {...}}} for every sensor, on every real driver,
        # masked by tests/test_asy_webserver_service.py's own _FakeModule returning an already-flat
        # dict (confirmed directly: found via a real user report against the real assembled system,
        # not caught by tests/test_digital_twin_sensortask_integration.py's own real-HTTP GET test
        # either - that test only checked top-level keys, never the values, now closed alongside
        # this fix). Real hardware is affected too - this is not twin-specific.
        result: dict[str, Any] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_data())
        return result

    async def _get_sensors(self, request: "Any") -> "dict[str, Any]":
        # .update(), not result[name] = ... - see _get_measurements()'s own comment above, the exact
        # same double-wrap bug via get_dict_cfg()/base_classes._get_dict_cfg() instead of
        # get_dict_data()/make_dict().
        result: dict[str, Any] = {}
        for module in self._sensors.values():
            result.update(await module.get_dict_cfg())
        return result

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

    async def _get_networking(self, request: "Any") -> "dict[str, Any]":
        return await self._get_settings_flat("networking")

    async def _put_networking(self, request: "Any") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        results = await self._apply_settings_groups("networking", body)
        return ar.make_response(0, result=results)

    async def _get_system(self, request: "Any") -> "dict[str, Any]":
        return await self._get_settings_flat("system")

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

    async def _get_notification(self, request: "Any") -> "dict[str, Any]":
        return await self._get_settings_flat("notification")

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

    async def _get_status(self, request: "Any") -> "dict[str, Any]":
        # Plain for-loop, not a dict comprehension - see _get_measurements()'s comment on
        # MicroPython's lack of `await`-in-comprehension support.
        sensors: dict[str, Any] = {}
        for name, fct in self._maintenance_sensors.items():
            sensors[name] = await fct()
        return {
            "networking": await self._call_status_source("networking"),
            "system": await self._call_status_source("system"),
            "notification": await self._call_status_source("notification"),
            "sensors": sensors,
            "errcount": await self._build_errcount(),
        }

    async def _call_status_source(self, key: str) -> "dict[str, Any]":
        source = self._status_sources.get(key)
        return {} if source is None else await source()

    async def _build_errcount(self) -> "dict[str, Any]":
        result: dict[str, Any] = {}
        for name, module in self._error_sources.items():
            result[name] = _shape_errcount_entry(await module.get_error_counter(), name)
        # "This service's own entry" (see SPECIFICATION.md Part A.8 for the registration-API contract) -
        # this module's own get_error_counter()/pr.get_log() aren't routed through
        # self._error_sources (WebserverService itself doesn't structurally satisfy _ModuleLike's
        # full sensor/settings surface, just the error-counter subset), so it's added directly here
        # instead of trying to register self into that dict.
        result[_NAME] = _shape_errcount_entry(await self.pr.get_log(), _NAME)
        return result

    async def _put_status(self, request: "Any") -> "ar.ResponseEnvelope":
        body = _body_as_dict(request)
        if body is None:
            return ar.make_response(1)
        if body.get("ResetErrors") is True:
            for module in self._error_sources.values():
                await module.reset_error_counter()
            await self.reset_error_counter()  # this service's own entry, see _build_errcount()
        return ar.make_response(0)

    # -- static content (see SPECIFICATION.md Part A.9) ----------------------------------------

    async def _get_static_index(self, request: "Any") -> "Any":
        return self._serve_static(self._static_index)

    async def _get_static(self, request: "Any", filename: str) -> "Any":
        return self._serve_static(filename)

    def _serve_static(self, filename: str) -> "Any":
        if ".." in filename:
            abort(404)  # reject before ever touching the mounted filesystem - see D.2's
            # guard-clause-before-any-computation convention. VfsFrozen's own path resolution
            # (ext/freezefs/ffsmount.py) already refuses to escape its own mount root, but this
            # guard is cheap, correct regardless of the underlying VFS, and gives a uniform 404
            # instead of relying on that implementation detail.
        assert self._static_mount is not None  # only ever registered as a route when it isn't
        try:
            return send_file(self._static_mount + "/" + filename, compressed=True, file_extension=".gz")
        except OSError:  # no such file in the mounted filesystem (freezefs's VfsFrozen.open()
            # raises OSError(ENOENT), matching a real missing-file open() everywhere else)
            if self._is_hotspot_active is not None and self._is_hotspot_active():
                # Captive-portal OS probes (generate_204, hotspot-detect.html, connecttest.txt, ...)
                # hit exactly this branch while the device is its own hotspot - redirecting them back
                # to "/" (rather than a plain 404) is what makes phones' automatic "Sign in to
                # network" popup trigger (CAPTIVE_PORTAL_HOTSPOT_REDIRECT_PLAN.md §1.2). No
                # try/except needed here: any exception from is_hotspot_active() is already safely
                # caught and shaped by Microdot's own blanket app.errorhandler(Exception) (see
                # SPECIFICATION.md Part A.5) like every other route-handler exception.
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
        except Exception as e:  # writer is caller-supplied (real Stream or a test double) - could
            # legitimately misbehave; this is best-effort cleanup, never load-bearing, but still
            # worth a persisted signal rather than a bare pass (SPECIFICATION.md Part C.7's
            # silent-failure-masking convention) - a repeatedly-failing close() could leak TCP PCBs
            # under this platform's tiny connection ceiling with no log trail ever pointing back here.
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
                # Reaches here from exactly two places: the outer wait_for() immediately above
                # timing out itself (bounding a Slowloris-paced client no single per-call timeout
                # alone would catch - decision 2), or a per-call proxy timeout during the *write*
                # phase (handle_request()'s own except-OSError-only wrapping around res.write()/
                # writer.aclose() doesn't absorb this the way it absorbs a read-phase one - see
                # _TimeoutStreamProxy's own comment). A read-phase per-call timeout already logged
                # its own warning inside the proxy itself and never reaches this far.
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
