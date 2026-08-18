"""Registration-based Microdot REST/API service (FINAL_WIRING_PLAN.md's Step 2) - modules hand this
service named sensor-data/system-state callback groups (SettingsGroup below), and it auto-constructs
the six external endpoints (/measurements, /sensors, /networking, /system, /status, /notification)
plus the connection-hardening scheme BACKLOG.md's "Microdot hardening design" settled on. Optionally
(static_mount, FINAL_WIRING_PLAN.md's Step 4) also serves a mounted frozen static-content filesystem
(freezefs's --on-import mount, see ext/freezefs/) via one generic `/` + `/<path:filename>` route pair,
using Microdot's own send_file(compressed=True, file_extension=".gz") - matches this project's
pre-gzip-by-hand convention (see scripts/build_frozen_html.sh), never freezefs's own --compress
(on-device deflate decompression, a different and incompatible scheme). Registered last, after every
API route above, so an exact-match API route always wins over the wildcard (Microdot's find_route()
returns the first registered pattern that matches, confirmed directly against ext/microdot.py).
composition around asyncio.start_server() (never app.start_server()/app.shutdown()), a per-call
timeout-wrapping reader/writer proxy (_TimeoutStreamProxy), one outer asyncio.wait_for() bounding
the whole per-connection handle_request() call, a LockedCounter-style open-connection count driving
reject-when-full (silently close a new connection at the ceiling, no accept/response), and no bespoke
whole-server-restart mechanism - this module's own task is registered as an ordinary task in
system_service.py's start_and_check_tasks() like every other module, per the owner's decision 1.

ext/microdot.py (vendored, unmodified) is never edited - every behavior change here happens by
wrapping/calling it (an after_request/after_error_request hook for "Connection: close", errorhandler
registrations for 400/404/405/413/500, the reader/writer proxy) per CLAUDE.md's hard rule. GET routes
return the bare shaped dict; PUT routes return api_response.py's {"res","code","descr","result"}
envelope, reusing make_response()/handle_set_cmd() directly - see tests/test_asy_webserver_service.py's
own module docstring for the full endpoint/registration-API contract this file builds to.
"""

import asyncio

# Vendored ext/microdot.py isn't on this project's mypy search path (mypy_path=["typings","src"]) -
# real device firmware freezes ext/ and src/ flat together, so this resolves fine at runtime; see
# CLAUDE.md's vendoring hard rule.
from microdot import Request, abort, send_file  # type: ignore[import-not-found]
from micropython import const

import api_response as ar
from base_classes import LockedCounter
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

_NAME = const("WEBSERVER")
_SYSTEM_CMDS = ("reboot", "bootloader", "mempause")  # the only enum values ever forwarded to
# system_cmd() - never a client-supplied duration (mempause's fixed 300s lives in system_cmd()'s own
# implementation, e.g. SystemService.pause_permanent_storage() - see FINAL_WIRING_PLAN.md's Step 2).

_ERROR_SHAPES = (  # (status_code, descr) - registered via @app.errorhandler for shaped JSON bodies,
    # per "Criteria for this step to finish": at least 400/404/405/413/500 wired.
    (400, "Bad request"),
    (404, "Not found"),
    (405, "Method not allowed"),
    (413, "Payload too large"),
    (500, "Internal server error"),
)


def _index_by_name(items: "Iterable[_ModuleLike]") -> "dict[str, _ModuleLike]":
    # Last-registration-wins, by construction - decision 6 (FINAL_WIRING_PLAN.md's Step 2): the
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
    # module returns - found and fixed via FINAL_WIRING_PLAN.md's Step 5 twin-based integration
    # testing (tests/test_digital_twin_sensortask_integration.py): without this, /networking and
    # /notification always returned {} in production (every field they source is nested-shaped),
    # and /system silently dropped GMTOffset/DSTOffset (sourced from ntp, also nested-shaped) while
    # DebugLevel (sourced from sysfunct, already flat) happened to work. Safe to merge any
    # dict-valued top-level entry unconditionally: every config schema in this codebase today is
    # flat scalar fields only (BACKLOG.md's own config_manager.py make_dict() note already tracks
    # this as the one place a future dict/list-valued field would need re-checking).
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
    # OSError subclass (correcting FINAL_WIRING_PLAN.md's Step 2, which had claimed otherwise). This
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
        status_sources: "dict[str, StatusSourceFct] | None" = None,
        maintenance_sensors: "Sequence[tuple[str, MaintenanceFct]]" = (),
        error_sources: "Sequence[_ModuleLike]" = (),
        max_content_length: int = 4096,
        max_connections: int = 3,  # reject-when-full ceiling - real margin below the confirmed
        # MEMP_NUM_TCP_PCB=5 rp2-port ceiling (BACKLOG.md's now-resolved companion open question).
        per_call_timeout_s: float = 5.0,
        outer_cap_s: float = 15.0,
        host: str = "0.0.0.0",
        port: int = 80,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
        static_mount: str | None = None,  # e.g. "/html" (FINAL_WIRING_PLAN.md's Step 4) - the
        # freezefs mount point of an already-`import`ed frozen static-content module. None (default)
        # registers no static routes at all - every existing route/registration above is unaffected.
        static_index: str = "index.html",  # served for both "/" and "/<static_index>" verbatim.
    ) -> None:
        self.pr: PrintLogHistory = make_logger(fram, history_length, debug, _NAME)
        self._app = app
        self._sensors = _index_by_name(sensors)
        self._settings: dict[str, list[SettingsGroup]] = {k: list(v) for k, v in (settings or {}).items()}
        self._system_cmd = system_cmd
        self._notification_led = notification_led
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
        # handlers on its happy path (see FINAL_WIRING_PLAN.md's Step 2, decision 7).
        for status_code, descr in _ERROR_SHAPES:
            app.errorhandler(status_code)(_shaped_error_handler(status_code, descr))

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
                # extended to the HTTP layer (FINAL_WIRING_PLAN.md's Step 2, section B).
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
        # FINAL_WIRING_PLAN.md's Step 2 "/networking PUT: partial-field update triggers only the
        # relevant post-write hook" requirement).
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
        ok = await self._system_cmd(cmd)
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
        return ar.make_response(0, result=results)

    async def _dispatch_notification_led(self, payload: "Any") -> str:
        if self._notification_led is None or not isinstance(payload, dict):
            return "Invalid"
        ok = await self._notification_led(payload)
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
        # "This service's own entry" (FINAL_WIRING_PLAN.md's Step 2 registration-API contract) -
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

    # -- static content (FINAL_WIRING_PLAN.md's Step 4) ----------------------------------------

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
            abort(404)

    # -- connection lifecycle ---------------------------------------------------------------------

    async def _close_writer(self, writer: "Any") -> None:
        try:
            writer.close()
        except Exception as e:  # writer is caller-supplied (real Stream or a test double) - could
            # legitimately misbehave; this is best-effort cleanup, never load-bearing, but still
            # worth a persisted signal rather than a bare pass (Step 6 silent-failure-masking
            # finding) - a repeatedly-failing close() could leak TCP PCBs under this platform's tiny
            # connection ceiling with no log trail ever pointing back here.
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
