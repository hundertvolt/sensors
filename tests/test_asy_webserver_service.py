"""Test suite for src/asy_webserver_service.py's WebserverService/SettingsGroup - see SPECIFICATION.md Part A.8 for the full endpoint design and the real class signatures for the current API contract (this file predates the implementation and no longer mirrors it exactly).
GET routes return the bare shaped dict; PUT routes return the existing api_response.py envelope - see SPECIFICATION.md Part A.8 for the PUT-shapes decision. Connection-lifecycle internals are exercised with hand-scripted fake reader/writer doubles, never a real select.poll()."""

import asyncio
import gc
import json
import os
import sys

# Same sys.path convention as tests/test_setter_microdot_integration.py: scripts/test.sh's
# MICROPYPATH deliberately excludes ext/, so reaching the real vendored ext/microdot.py needs
# this rather than a build-environment scope change.
sys.path.insert(0, "ext")

from _shared_rest_roundtrip import drain_json_response_body
from freezefs.ffsmount import VfsFrozen  # type: ignore[import-not-found]
from microdot import Microdot, Request, Response  # type: ignore[import-not-found]

import config_manager as cm
from asy_webserver_service import SettingsGroup, WebserverService, _PieceWriter, _shape_errcount_entry, _stream_dict_response, _TimeoutStreamProxy

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def status_body(res: "Response") -> bytes:
    # GET /status streams a list of already-json.dumps()-encoded fragments (see
    # asy_webserver_service.py's _build_status_pieces()); draining it the way a real client would
    # keeps every json.loads(...) assertion on a /status response working unchanged.
    return drain_json_response_body(res.body)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
    # Same defensive bound as test_asy_uart_driver.py's own run(): section F below deliberately
    # exercises timeout/hang scenarios, so a genuine bug in the implementation under test (or in
    # one of the fakes below) must surface as a fast FAIL, never a silent whole-suite stall.
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# Fakes - registered-module doubles. Deliberately lightweight: sections A-E test the webserver's
# own dispatch/aggregation/registration logic, not sensor behavior. _set_dict_cfg() mirrors
# config_manager.write_config()'s per-field Invalid/Valid semantics closely enough to stand in.
# ---------------------------------------------------------------------------


class _FakeLogger:
    def __init__(self, name: str) -> None:
        self.name = name
        self.err_count = 0
        self.history: list[tuple[int, str]] = []
        self.reset_calls = 0

    async def err_s(self, *_args: object, errno: int = 0, **_kwargs: object) -> None:
        self.err_count += 1
        if errno:
            self.history.append((errno, "E"))

    async def wrn_s(self, *_args: object, wrnno: int = 0, **_kwargs: object) -> None:
        self.err_count += 1
        if wrnno:
            self.history.append((wrnno, "W"))

    async def get_log(self) -> "dict[str, dict[str, Any]]":
        return {
            self.name: {
                "ErrCount": self.err_count,
                "ErrNum": [h[0] for h in self.history],
                "ErrType": [h[1] for h in self.history],
            },
        }

    async def reset(self) -> None:
        self.reset_calls += 1
        self.err_count = 0
        self.history = []


_FAKE_SCHEMA: "cm.ConfigSchema" = (
    ("Interval", "int", 5, 1, 60, None),
    ("Offset", "int", 0, -10, 10, None),
)


class _FakeModule:
    # Doubles as both a "sensor" (name/get_dict_data/get_dict_cfg/_set_dict_cfg/get_cfg_schema/
    # get_error_counter/reset_error_counter) and a SettingsGroup's own module (get_cfg_schema/
    # _set_dict_cfg/get_dict_cfg) - the two roles need the same shape, so one fake class serves both.
    def __init__(
        self,
        name: str,
        schema: "cm.ConfigSchema" = _FAKE_SCHEMA,
        data: "dict[str, Any] | None" = None,
        values: "dict[str, Any] | None" = None,
    ) -> None:
        self.name = name
        self._schema = schema
        self._data = dict(data) if data is not None else {"Value": 42}
        self._values = dict(values) if values is not None else {f[0]: f[2] for f in schema}
        self.pr = _FakeLogger(name)
        self.set_calls: list[dict[str, Any]] = []

    def get_cfg_schema(self) -> "cm.ConfigSchema":
        return self._schema

    async def get_dict_data(self) -> "dict[str, Any]":
        return dict(self._data)

    async def get_dict_cfg(self) -> "dict[str, Any]":
        return dict(self._values)

    async def _set_dict_cfg(self, data: "dict[str, Any]", cfg_vals: "cm.ConfigSchema") -> "dict[str, str]":
        self.set_calls.append(dict(data))
        defaults = cm.schema_dict(cfg_vals)
        results: dict[str, str] = {}
        for key, value in data.items():
            if key not in defaults:
                results[key] = "Invalid"
                continue
            is_error, coerced_value = cm.type_or_range_error(value, defaults[key])
            if is_error:
                results[key] = "Invalid"
                continue
            self._values[key] = coerced_value
            results[key] = "Valid"
        return results

    async def get_error_counter(self) -> "dict[str, Any]":
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()


# ---------------------------------------------------------------------------
# Fakes - reader/writer stream doubles for asyncio.Stream, covering every method ext/microdot.py
# actually calls plus what a per-call timeout-wrapping proxy forwards. Never backed by a real
# select.poll()/socket - CLAUDE.md's CI-hang note says why that is a hard requirement here.
# ---------------------------------------------------------------------------


class _ScriptedReader:
    # Feeds pre-scripted byte chunks, each preceded by an optional asyncio.sleep(delay), so a test
    # can simulate a paced/Slowloris client with no real I/O. Once exhausted, reads hang forever
    # unless eof=True - matching real Stream behavior for a clean peer close vs. a wedged one.
    def __init__(self, chunks: "list[tuple[float, bytes]]", *, eof: bool = False) -> None:
        self._chunks = list(chunks)
        self._buf = b""
        self._eof = eof

    async def _pull(self) -> bool:  # returns False once genuinely exhausted (caller decides what that means)
        if not self._chunks:
            if self._eof:
                return False
            await asyncio.Event().wait()  # never set - simulates a silent/wedged connection
            return False  # unreachable, keeps type-checkers happy
        delay, chunk = self._chunks.pop(0)
        if delay:
            await asyncio.sleep(delay)
        self._buf += chunk
        return True

    async def readline(self) -> bytes:
        while b"\n" not in self._buf:
            if not await self._pull():
                line, self._buf = self._buf, b""
                return line  # readline() never raises on early close - just returns the partial buffer
        idx = self._buf.index(b"\n") + 1
        line, self._buf = self._buf[:idx], self._buf[idx:]
        return line

    async def readexactly(self, n: int) -> bytes:
        while len(self._buf) < n:
            if not await self._pull():
                raise EOFError  # matches extmod/asyncio/stream.py's Stream.readexactly()
        data, self._buf = self._buf[:n], self._buf[n:]
        return data


class _HangingReader:
    # Never yields any bytes at all, on any call - the "opens a TCP connection and sends nothing,
    # ever" shape from F.1, and the base for the outer-cap wedge tests in F.6/F.7.
    async def readline(self) -> bytes:
        await asyncio.Event().wait()
        return b""  # unreachable

    async def readexactly(self, _n: int) -> bytes:
        await asyncio.Event().wait()
        return b""  # unreachable


class _ClosedReader:
    # Opens then immediately closes before sending any bytes - readline() returns empty immediately
    # (matches real Stream.readline()'s no-raise-on-early-close behavior); readexactly() raises
    # EOFError immediately (matches Stream.readexactly()).
    async def readline(self) -> bytes:
        return b""

    async def readexactly(self, _n: int) -> bytes:
        raise EOFError


class _ScriptedWriter:
    def __init__(self, *, hang_close: bool = False, fail_with: "Exception | None" = None) -> None:
        self.written = b""
        self.close_called = False
        self.wait_closed_called = False
        self._hang_close = hang_close
        self._fail_with = fail_with

    async def awrite(self, data: bytes) -> None:
        if self._fail_with is not None:
            raise self._fail_with
        self.written += data

    def close(self) -> None:
        self.close_called = True

    async def aclose(self) -> None:
        self.close()

    async def wait_closed(self) -> None:
        self.wait_closed_called = True
        if self._hang_close:
            await asyncio.Event().wait()

    def get_extra_info(self, name: str) -> object:
        return ("127.0.0.1", 54321) if name == "peername" else None


def _request_bytes(method: str, path: str, body: bytes = b"", extra_headers: "dict[str, str] | None" = None) -> bytes:
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json", "Host": "device.local"}
    if extra_headers:
        headers.update(extra_headers)
    header_lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"{method} {path} HTTP/1.1\r\n{header_lines}\r\n".encode() + body


def _make_service(**kwargs: "Any") -> "tuple[WebserverService, Microdot]":  # Any: forwarded
    # verbatim into WebserverService's own 22 differently-typed keyword parameters, which no single
    # non-Any **kwargs element type can express before PEP 692's Unpack (3.11+).
    app = Microdot()
    kwargs.setdefault("max_content_length", 2048)  # tracks the shipped default, so these tests exercise it
    kwargs.setdefault("max_connections", 3)
    kwargs.setdefault("per_call_timeout_s", 0.2)
    kwargs.setdefault("outer_cap_s", 0.5)
    service = WebserverService(app, **kwargs)
    return service, app


def _make_request(app: "Microdot", method: str, path: str, json_body: "dict[str, Any] | list[Any] | None") -> Request:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    return Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)


# ---------------------------------------------------------------------------
# Section A - endpoint contract tests
# ---------------------------------------------------------------------------


def test_measurements_get_returns_merged_per_sensor_dict() -> None:
    # _NestedCfgModule, not _FakeModule - the real drivers' get_dict_data() always returns the
    # self-wrapped {name: {...}} shape (config_manager.make_dict()), never _FakeModule's flat one,
    # and that distinction is the whole point of this test.
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    sgp = _NestedCfgModule("SGP40", values={}, data={"VOC": 120})
    _service, app = _make_service(sensors=[scd, sgp])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(status_body(res)) == {"SCD30": {"CO2": 800}, "SGP40": {"VOC": 120}}


def test_measurements_get_does_not_double_wrap_a_real_self_wrapped_sensor_shape() -> None:
    # Regression test for the real, confirmed production bug _NestedCfgModule's own docstring
    # describes: _get_measurements() used to index the already-self-wrapped get_dict_data() result
    # by name again, producing {"SCD30": {"SCD30": {"CO2": 800}}} for every real sensor.
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    _service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    body = json.loads(status_body(res))
    assert "SCD30" not in body["SCD30"]
    assert body == {"SCD30": {"CO2": 800}}


def test_measurements_get_empty_sensor_list_returns_empty_dict_not_a_crash() -> None:
    _service, app = _make_service(sensors=[])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(status_body(res)) == {}


def test_sensors_get_mirrors_measurements_structure_with_cfg_fields() -> None:
    scd = _NestedCfgModule("SCD30", values={"Interval": 10, "Offset": 2})
    _service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "GET", "/sensors", None)))
    assert json.loads(status_body(res)) == {"SCD30": {"Interval": 10, "Offset": 2}}


def test_sensors_get_does_not_double_wrap_a_real_self_wrapped_sensor_shape() -> None:
    # Same regression as test_measurements_get_does_not_double_wrap... above, via get_dict_cfg()/
    # _get_sensors() instead of get_dict_data()/_get_measurements().
    scd = _NestedCfgModule("SCD30", values={"Interval": 10, "Offset": 2})
    _service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "GET", "/sensors", None)))
    body = json.loads(status_body(res))
    assert "SCD30" not in body["SCD30"]
    assert body == {"SCD30": {"Interval": 10, "Offset": 2}}


def test_sensors_put_empty_body_is_noop() -> None:
    scd = _FakeModule("SCD30")
    _service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {})))
    assert res.status_code == 200
    assert json.loads(res.body)["result"] == {}
    assert scd.set_calls == []


def test_sensors_put_single_field_for_one_sensor() -> None:
    scd = _FakeModule("SCD30")
    sgp = _FakeModule("SGP40")
    _service, app = _make_service(sensors=[scd, sgp])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {"SCD30": {"Interval": 10}})))
    body = json.loads(res.body)
    assert body["result"] == {"SCD30": {"Interval": "Valid"}}
    assert run(scd.get_dict_cfg())["Interval"] == 10
    assert sgp.set_calls == []  # untouched sensor never dispatched to


def test_sensors_put_all_fields_for_all_sensors() -> None:
    scd = _FakeModule("SCD30")
    sgp = _FakeModule("SGP40")
    _service, app = _make_service(sensors=[scd, sgp])
    body_in = {"SCD30": {"Interval": 10, "Offset": 3}, "SGP40": {"Interval": 20, "Offset": -1}}
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", body_in)))
    body = json.loads(res.body)
    assert body["result"] == {
        "SCD30": {"Interval": "Valid", "Offset": "Valid"},
        "SGP40": {"Interval": "Valid", "Offset": "Valid"},
    }


def test_sensors_put_unknown_sensor_key_ignored() -> None:
    scd = _FakeModule("SCD30")
    _service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {"BOGUS": {"Interval": 10}})))
    assert res.status_code == 200
    assert json.loads(res.body)["result"] == {}
    assert scd.set_calls == []


def test_sensors_put_unknown_field_within_known_sensor_reported_invalid_not_whole_request() -> None:
    scd = _FakeModule("SCD30")
    _service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {"SCD30": {"Interval": 10, "Bogus": 1}})))
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"SCD30": {"Interval": "Valid", "Bogus": "Invalid"}}


def test_sensors_put_malformed_json_body_is_a_clean_rejection_not_a_crash() -> None:
    scd = _FakeModule("SCD30")
    _service, app = _make_service(sensors=[scd])
    req = _make_request(app, "PUT", "/sensors", {})
    req._body = b"{not valid json"
    req.content_length = len(req._body)
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    assert json.loads(res.body) == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}
    assert scd.set_calls == []


def test_networking_get_is_flat_settings_only_no_live_fields() -> None:
    wifi = _FakeModule("WIFI", schema=(("SSID", "str", "", 0, 32, None),), values={"SSID": "MyNet"})
    group = SettingsGroup(wifi, ("SSID",))
    _service, app = _make_service(settings={"networking": [group]})
    res = run(app.dispatch_request(_make_request(app, "GET", "/networking", None)))
    body = json.loads(status_body(res))
    assert body == {"SSID": "MyNet"}
    assert "Connected" not in body and "IP" not in body and "Rssi" not in body


class _NestedCfgModule:
    # Reproduces config_manager.make_dict()'s real {type_name: {field: value}} shape - what
    # AsyConnTime/AsyNtpClient/NotificationCoordinator and the real sensor drivers return, unlike
    # _FakeModule's flat convention above (which matches SystemService's own flat override).
    #
    # Guards two real production bugs of one class: _get_settings_flat() never unwrapping this
    # shape (so /networking and /notification returned {}), and _get_measurements()/_get_sensors()
    # indexing an already-wrapped result again into {"SCD30": {"SCD30": {...}}}.
    def __init__(self, type_name: str, values: "dict[str, Any]", data: "dict[str, Any] | None" = None) -> None:
        self.name = type_name
        self._type_name = type_name
        self._values = values
        self._data = data if data is not None else {}

    async def get_dict_cfg(self) -> "dict[str, Any]":
        return {self._type_name: dict(self._values)}

    async def get_dict_data(self) -> "dict[str, Any]":
        return {self._type_name: dict(self._data)}


def test_networking_get_flattens_a_real_type_name_nested_get_dict_cfg_shape() -> None:
    # Regression test for the real, confirmed production bug described in _NestedCfgModule's own
    # docstring above.
    wifi = _NestedCfgModule("WIFI", {"SSID": "MyNet"})
    group = SettingsGroup(wifi, ("SSID",))  # type: ignore[arg-type]  # structurally _ModuleLike-shaped
    _service, app = _make_service(settings={"networking": [group]})
    res = run(app.dispatch_request(_make_request(app, "GET", "/networking", None)))
    assert json.loads(status_body(res)) == {"SSID": "MyNet"}


def test_networking_put_partial_field_update_triggers_only_relevant_post_hook() -> None:
    wifi = _FakeModule(
        "WIFI",
        schema=(("SSID", "str", "", 0, 32, None), ("NTP_Host", "str", "pool.ntp.org", 0, 64, None)),
        values={"SSID": "", "NTP_Host": "pool.ntp.org"},
    )
    reconnect_calls = []
    resync_calls: list[int] = []
    net_group = SettingsGroup(wifi, ("SSID",), post_fct=lambda: reconnect_calls.append(1))
    ntp_group = SettingsGroup(wifi, ("NTP_Host",), post_asy_fct=lambda: _record_async(resync_calls))
    _service, app = _make_service(settings={"networking": [net_group, ntp_group]})
    res = run(app.dispatch_request(_make_request(app, "PUT", "/networking", {"SSID": "NewNet"})))
    assert res.status_code == 200
    assert reconnect_calls == [1]
    assert resync_calls == []  # NTP_Host wasn't in this body - its own post_asy_fct must not fire


async def _record_async(sink: "list[int]") -> None:
    sink.append(1)


def test_networking_put_raising_post_fct_marks_every_attempted_field_in_that_group_failed() -> None:
    # Regression test for SPECIFICATION.md Part H.6's "silent result-swallow": handle_set_cmd()
    # discards its per-field results when post_fct/post_asy_fct raises, and _apply_settings_groups()
    # used to .update() that empty dict in. Every field in `subset` must now come back "Failed".
    wifi = _FakeModule(
        "WIFI",
        schema=(("SSID", "str", "", 0, 32, None), ("PW", "str", "", 0, 63, None)),
        values={"SSID": "", "PW": ""},
    )

    def _raise() -> None:
        raise RuntimeError("simulated post_fct failure")

    net_group = SettingsGroup(wifi, ("SSID", "PW"), post_fct=_raise)
    _service, app = _make_service(settings={"networking": [net_group]})
    res = run(app.dispatch_request(_make_request(app, "PUT", "/networking", {"SSID": "NewNet", "PW": "hunter2"})))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"  # per-field detail carries the failure, not the overall envelope
    assert body["result"] == {"SSID": "Failed", "PW": "Failed"}


def test_system_get_is_flat_debug_gmt_dst_only() -> None:
    sysm = _FakeModule(
        "SYSTEM",
        schema=(("DebugLevel", "int", 0, 0, 5, None),),
        values={"DebugLevel": 2},
    )
    ntp = _FakeModule(
        "NTP",
        schema=(("GMTOffset", "int", 3600, -50400, 50400, None), ("DSTOffset", "int", 3600, 0, 7200, None)),
        values={"GMTOffset": 3600, "DSTOffset": 3600},
    )
    groups = [SettingsGroup(sysm, ("DebugLevel",)), SettingsGroup(ntp, ("GMTOffset", "DSTOffset"))]
    _service, app = _make_service(settings={"system": groups})
    res = run(app.dispatch_request(_make_request(app, "GET", "/system", None)))
    assert json.loads(status_body(res)) == {"DebugLevel": 2, "GMTOffset": 3600, "DSTOffset": 3600}


def test_system_get_reports_build_info_verbatim_when_supplied() -> None:
    # SPECIFICATION.md Part L.7: buildgen supplies this dict at construction time (firmware/
    # website version + a real build timestamp) - WebserverService never computes any of it itself,
    # just relays it under one "build" sub-entry alongside the ordinary flat settings fields.
    build_info = {"firmwareVersion": "2.0b0", "websiteVersion": "2.0b0", "buildDate": "2026-09-12T10:00:00Z"}
    _service, app = _make_service(build_info=build_info)
    res = run(app.dispatch_request(_make_request(app, "GET", "/system", None)))
    assert json.loads(status_body(res)) == {"build": build_info}


def test_system_get_omits_build_key_when_build_info_not_supplied() -> None:
    _service, app = _make_service()
    res = run(app.dispatch_request(_make_request(app, "GET", "/system", None)))
    assert json.loads(status_body(res)) == {}


def test_system_get_combines_flat_settings_and_build_info_together() -> None:
    # The realistic shape every real generated device actually produces: ordinary flat
    # SettingsGroup-sourced fields alongside the one nested "build" sub-entry, neither one
    # clobbering the other.
    sysm = _FakeModule("SYSTEM", schema=(("DebugLevel", "int", 0, 0, 5, None),), values={"DebugLevel": 2})
    build_info = {"firmwareVersion": "2.0b0", "websiteVersion": "2.0b0", "buildDate": "2026-09-12T10:00:00Z"}
    _service, app = _make_service(settings={"system": [SettingsGroup(sysm, ("DebugLevel",))]}, build_info=build_info)
    res = run(app.dispatch_request(_make_request(app, "GET", "/system", None)))
    assert json.loads(status_body(res)) == {"DebugLevel": 2, "build": build_info}


def test_system_put_settings_only_body_no_systemcmd_takes_no_lifecycle_action() -> None:
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    sysm = _FakeModule("SYSTEM", schema=(("DebugLevel", "int", 0, 0, 5, None),), values={"DebugLevel": 0})
    _service, app = _make_service(settings={"system": [SettingsGroup(sysm, ("DebugLevel",))]}, system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"DebugLevel": 3})))
    assert res.status_code == 200
    assert cmd_calls == []


def test_system_put_systemcmd_invalid_value_rejected_without_side_effects() -> None:
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    _service, app = _make_service(system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"SystemCmd": "erase_flash"})))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"].get("SystemCmd") == "Invalid"
    assert cmd_calls == []


def test_system_put_systemcmd_reboot_fires_system_cmd_callback() -> None:
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    _service, app = _make_service(system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"SystemCmd": "reboot"})))
    assert res.status_code == 200
    assert cmd_calls == ["reboot"]


def test_system_put_mempause_never_accepts_a_client_supplied_duration() -> None:
    # The webserver layer only ever forwards the enum string, never a caller-suppliable duration -
    # system_cmd()'s implementation (SystemService.pause_permanent_storage) hardcodes the 300s, so
    # nothing upstream may leak a duration field through even if one is present in the body.
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    _service, app = _make_service(system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"SystemCmd": "mempause", "Duration": 9999})))
    assert res.status_code == 200
    assert cmd_calls == ["mempause"]


def test_system_put_systemcmd_raising_callback_returns_failed_not_an_exception() -> None:
    # system_cmd is a caller-supplied callback like every other in this codebase and could
    # legitimately misbehave; unguarded, a raise would escape the route handler instead of
    # degrading to a clean "Failed" result with a persisted, diagnosable errno.
    async def system_cmd(_cmd: str) -> bool:
        raise RuntimeError("simulated system_cmd failure")

    service, app = _make_service(system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"SystemCmd": "reboot"})))
    assert res.status_code == 200  # the overall request still succeeds - failure detail is per-field
    body = json.loads(res.body)
    assert body["result"]["SystemCmd"] == "Failed"
    assert service.pr.err_count == 1


def test_status_get_returns_exact_substructure_no_settings_fields_anywhere() -> None:
    async def net_status() -> "dict[str, Any]":
        return {"Connected": True, "Rssi": -50}

    async def sys_status() -> "dict[str, Any]":
        return {"SysUptime": 123}

    async def notif_status() -> "dict[str, Any]":
        return {"Triggered": False}

    _service, app = _make_service(
        status_sources={"networking": net_status, "system": sys_status, "notification": notif_status},
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert set(body.keys()) == {"networking", "system", "sensors", "notification", "errcount"}
    assert body["networking"] == {"Connected": True, "Rssi": -50}
    assert body["system"] == {"SysUptime": 123}
    assert body["notification"] == {"Triggered": False}


def test_status_get_sensors_subkey_omits_sensors_with_no_maintenance_data() -> None:
    async def sgp_maint() -> "dict[str, Any]":
        return {"BackupTS": 111, "RestoreTS": 222}

    _service, app = _make_service(maintenance_sensors=[("SGP40", sgp_maint)])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body["sensors"] == {"SGP40": {"BackupTS": 111, "RestoreTS": 222}}


def test_status_get_sensors_subkey_empty_when_no_maintenance_sensors_registered() -> None:
    _service, app = _make_service(maintenance_sensors=[])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    assert json.loads(status_body(res))["sensors"] == {}


def test_status_put_empty_and_false_reset_errors_are_both_noops() -> None:
    mod = _FakeModule("SGP40")
    run(mod.pr.err_s("boom", errno=1))
    _service, app = _make_service(error_sources=[mod])
    for body_in in ({}, {"ResetErrors": False}):
        res = run(app.dispatch_request(_make_request(app, "PUT", "/status", body_in)))
        assert res.status_code == 200
    assert mod.pr.reset_calls == 0
    assert mod.pr.err_count == 1


def test_status_put_reset_errors_true_resets_every_module_counter_and_history() -> None:
    mod = _FakeModule("SGP40")
    run(mod.pr.err_s("boom", errno=1))
    _service, app = _make_service(error_sources=[mod])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/status", {"ResetErrors": True})))
    assert res.status_code == 200
    assert mod.pr.reset_calls == 1
    assert mod.pr.err_count == 0
    assert mod.pr.history == []


def test_notification_get_is_flat_settings_only_no_live_fields() -> None:
    notif = _FakeModule(
        "NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8},
    )
    _service, app = _make_service(settings={"notification": [SettingsGroup(notif, ("OnH",))]})
    res = run(app.dispatch_request(_make_request(app, "GET", "/notification", None)))
    body = json.loads(status_body(res))
    assert body == {"OnH": 8}
    assert "Triggered" not in body and "TS" not in body and "PauseTime" not in body


def test_notification_put_light_cmd_led_round_trips_independently_of_flat_fields() -> None:
    led_calls = []

    async def notification_led(payload: "dict[str, Any]") -> bool:
        led_calls.append(payload)
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_led=notification_led,
    )
    res = run(
        app.dispatch_request(
            _make_request(app, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 5}}),
        ),
    )
    assert res.status_code == 200
    assert led_calls == [{"r": 10, "g": 20, "b": 30, "t": 5}]
    assert run(notif.get_dict_cfg())["OnH"] == 8  # flat field never touched by this body


def test_notification_put_pause_time_only_leaves_schedule_fields_untouched() -> None:
    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    pause_calls = []

    async def notification_pause(secs: int) -> bool:
        pause_calls.append(secs)
        return True

    _service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause,
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60})))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Valid"
    assert pause_calls == [60]
    assert notif.set_calls == []  # OnH group never received a body with no matching keys


def test_notification_put_pause_time_reported_invalid_when_no_handler_registered() -> None:
    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(settings={"notification": [SettingsGroup(notif, ("OnH",))]})  # notification_pause=None
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60})))
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Invalid"


def test_notification_put_pause_time_reported_invalid_when_not_an_int() -> None:
    async def notification_pause(_secs: int) -> bool:
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause,
    )
    for bad_value in ("60", 1.5, True, None):
        res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": bad_value})))
        body = json.loads(res.body)
        assert body["result"]["PauseTime"] == "Invalid"


def test_notification_put_pause_time_accepts_integral_float_coerced_to_int() -> None:
    # Mirror of the fractional-rejected test above, in the accept direction: coerce_numeric()
    # (SPECIFICATION.md Part A.8) accepts an integral float for PauseTime's synthetic int schema,
    # and the callback must receive the coerced int - notification_pause() expects int.
    pause_calls = []

    async def notification_pause(secs: int) -> bool:
        pause_calls.append(secs)
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause,
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60.0})))
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Valid"
    assert pause_calls == [60]
    assert type(pause_calls[0]) is int


def test_notification_put_pause_time_reported_invalid_when_out_of_range() -> None:
    # Legacy's own pauseAutoLED rejects an out-of-range pauseTime as Invalid rather than clamping
    # (modules/sensortask-wozi.py), but LockedCounter.set_value() would clamp silently - so this
    # dispatcher must range-check server-side itself before ever calling the callback.
    pause_calls = []

    async def notification_pause(secs: int) -> bool:
        pause_calls.append(secs)
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause,
    )
    for bad_value in (-1, 3601):
        res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": bad_value})))
        body = json.loads(res.body)
        assert body["result"]["PauseTime"] == "Invalid"
    assert pause_calls == []  # the callback must never see an out-of-range value


def test_notification_put_pause_time_raising_callback_returns_failed_not_an_exception() -> None:
    # notification_pause is a caller-supplied callback and could legitimately misbehave, the same as
    # system_cmd/notification_led (see their own identical raising-callback tests above).
    async def notification_pause(_secs: int) -> bool:
        raise RuntimeError("simulated notification_pause failure")

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause,
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60})))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Failed"
    assert service.pr.err_count == 1


def test_notification_put_light_cmd_led_reported_invalid_when_no_handler_registered() -> None:
    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(settings={"notification": [SettingsGroup(notif, ("OnH",))]})  # notification_led=None
    res = run(
        app.dispatch_request(
            _make_request(app, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 5}}),
        ),
    )
    body = json.loads(res.body)
    assert body["result"]["lightCmdLED"] == "Invalid"


def test_notification_put_light_cmd_led_reported_invalid_when_payload_is_not_a_dict() -> None:
    async def notification_led(_payload: "dict[str, Any]") -> bool:
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    _service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_led=notification_led,
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"lightCmdLED": "not-a-dict"})))
    body = json.loads(res.body)
    assert body["result"]["lightCmdLED"] == "Invalid"


def test_notification_put_light_cmd_led_raising_callback_returns_failed_not_an_exception() -> None:
    # notification_led is a caller-supplied callback and could legitimately misbehave, the same as
    # system_cmd (see test_system_put_systemcmd_raising_callback_returns_failed_not_an_exception's
    # own comment) - previously unguarded here too.
    async def notification_led(_payload: "dict[str, Any]") -> bool:
        raise RuntimeError("simulated notification_led failure")

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_led=notification_led,
    )
    res = run(
        app.dispatch_request(
            _make_request(app, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 5}}),
        ),
    )
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"]["lightCmdLED"] == "Failed"
    assert service.pr.err_count == 1


# ---------------------------------------------------------------------------
# Section B - cross-endpoint sparse-JSON PUT semantics, run against every settings endpoint so the
# convention is uniform by construction, not true by per-endpoint accident.
# ---------------------------------------------------------------------------

_SETTINGS_ENDPOINTS = ("networking", "system", "notification")


def _settings_service(endpoint: str) -> "tuple[WebserverService, Microdot, _FakeModule]":
    mod = _FakeModule(endpoint.upper(), values={"Interval": 5, "Offset": 0})
    service, app = _make_service(settings={endpoint: [SettingsGroup(mod, ("Interval", "Offset"))]})
    return service, app, mod


def test_b_missing_field_or_sub_object_left_untouched_on_every_settings_endpoint() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        _service, app, mod = _settings_service(endpoint)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/" + endpoint, {"Interval": 10})))
        assert res.status_code == 200, endpoint
        assert run(mod.get_dict_cfg())["Offset"] == 0, endpoint  # untouched, not reset to default


def test_b_unknown_top_level_key_silently_ignored_on_every_settings_endpoint() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        _service, app, _mod = _settings_service(endpoint)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/" + endpoint, {"Bogus": 1})))
        assert res.status_code == 200, endpoint
        body = json.loads(res.body)
        assert "Bogus" not in body.get("result", {}), endpoint


def test_b_wrong_top_level_json_type_is_a_clean_rejection_on_every_settings_endpoint() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        _service, app, _mod = _settings_service(endpoint)
        for bad_body in ([1, 2, 3], "a string", 42, None):
            req = _make_request(app, "PUT", "/" + endpoint, None)
            req._body = json.dumps(bad_body).encode()
            req.content_length = len(req._body)
            res = run(app.dispatch_request(req))
            assert res.status_code == 200, (endpoint, bad_body)  # our own precise ERR envelope, not a raised exception
            assert json.loads(res.body)["res"] == "ERR", (endpoint, bad_body)


def test_b_wrong_type_for_a_known_field_is_a_per_field_rejection_others_still_apply() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        _service, app, mod = _settings_service(endpoint)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/" + endpoint, {"Interval": "not-an-int", "Offset": 5})))
        body = json.loads(res.body)
        assert body["result"] == {"Interval": "Invalid", "Offset": "Valid"}, endpoint
        assert run(mod.get_dict_cfg())["Offset"] == 5, endpoint


def test_b_malformed_json_body_handled_like_the_legacy_parse_cmd_request_path() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        _service, app, _mod = _settings_service(endpoint)
        req = _make_request(app, "PUT", "/" + endpoint, {})
        req._body = b"{not valid json"
        req.content_length = len(req._body)
        res = run(app.dispatch_request(req))
        assert res.status_code == 200, endpoint
        assert json.loads(res.body) == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}, endpoint


def test_b_duplicate_keys_in_raw_json_text_last_wins() -> None:
    # MicroPython's json module deserializes the same way CPython's does for a duplicate-key
    # object literal - confirmed directly against the pinned interpreter, not assumed.
    _service, app, mod = _settings_service("networking")
    req = _make_request(app, "PUT", "/networking", {})
    req._body = b'{"Interval": 1, "Interval": 10}'
    req.content_length = len(req._body)
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    assert run(mod.get_dict_cfg())["Interval"] == 10


def test_b_deeply_nested_json_body_degrades_to_a_clean_rejection_not_a_hard_fault() -> None:
    # Building the nested structure as a Python object and calling json.dumps() recurses exactly as
    # deeply as the json.loads() under test, blowing the recursion limit in this test's own setup.
    # Repeating raw JSON text keeps recursion to the json.loads() inside the code under test.
    _service, app, _mod = _settings_service("system")
    # The deepest nesting that is actually REACHABLE: max_content_length caps the body at 2,048 B,
    # so 1,000 levels (2,001 B) is the worst case a client can submit, and a deeper one is a 413
    # before any of this runs. Previously 2,000, which stopped fitting when the cap was tightened.
    depth = 1000
    # An earlier comment here claimed MicroPython's json.loads() recursion bound is "well under"
    # this - measured false against the pinned interpreter, which parses depth 3,000 fine. What the
    # test really pins is the non-dict top level taking _body_as_dict()'s clean ERR path.
    req = _make_request(app, "PUT", "/system", {})
    req._body = b"[" * depth + b"1" + b"]" * depth
    req.content_length = len(req._body)
    res = run(app.dispatch_request(req))
    assert res.status_code == 200  # our own ERR envelope, never a raised exception escaping to Microdot's bare 500
    assert json.loads(res.body)["res"] == "ERR"


def test_b_body_at_and_over_max_content_length_boundary() -> None:
    # max_content_length is a Request *class* attribute in ext/microdot.py (Request.
    # max_content_length, per its own module docstring example), not an app-instance one -
    # WebserverService's constructor is expected to set it there.
    _service, app, _mod = _settings_service("networking")
    limit = Request.max_content_length
    under = _make_request(app, "PUT", "/networking", {"Interval": 5})
    assert len(under.body) < limit
    res_under = run(app.dispatch_request(under))
    assert res_under.status_code == 200

    over_body = json.dumps({"Interval": 5, "Padding": "x" * (limit + 1024)}).encode()
    over_headers = {"Content-Length": str(len(over_body)), "Content-Type": "application/json"}
    over = Request(app, ("127.0.0.1", 12345), "PUT", "/networking", "1.1", over_headers, body=None)
    res_over = run(app.dispatch_request(over))
    assert res_over.status_code == 413


# ---------------------------------------------------------------------------
# Section C - registration API tests (generator-readiness shape: lists at init).
# ---------------------------------------------------------------------------


def test_c_zero_entries_in_any_registration_group_produces_well_formed_empty_response() -> None:
    _service, app = _make_service(sensors=[], settings={}, maintenance_sensors=[], error_sources=[])
    for path in ("/measurements", "/sensors", "/status"):
        res = run(app.dispatch_request(_make_request(app, "GET", path, None)))
        assert res.status_code == 200, path
        json.loads(status_body(res))  # well-formed JSON, no exception


def test_c_one_entry_behaves_identically_to_a_hand_constructed_single_item_list() -> None:
    single = _NestedCfgModule("SCD30", values={}, data={"CO2": 900})
    _service, app = _make_service(sensors=[single])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert json.loads(status_body(res)) == {"SCD30": {"CO2": 900}}


def test_c_duplicate_registration_last_registration_wins() -> None:
    first = _NestedCfgModule("SCD30", values={}, data={"CO2": 111})
    second = _NestedCfgModule("SCD30", values={}, data={"CO2": 222})
    _service, app = _make_service(sensors=[first, second])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert json.loads(status_body(res)) == {"SCD30": {"CO2": 222}}


# ---------------------------------------------------------------------------
# Section D - error aggregation / reset tests.
# ---------------------------------------------------------------------------


def test_d_status_errcount_includes_one_entry_per_module_and_per_configmanager() -> None:
    module = _FakeModule("SGP40")
    cfgmgr = _FakeModule("CFGMGR_SGP40")
    _service, app = _make_service(error_sources=[module, cfgmgr])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    # "WEBSERVER" is this service's own entry (see SPECIFICATION.md Part A.8 for the
    # registration-API contract) - added directly in _build_status_pieces(), not via the error_sources registry, since
    # WebserverService can't register itself into its own not-yet-constructed error_sources list.
    assert set(errcount.keys()) == {"SGP40", "CFGMGR_SGP40", "WEBSERVER"}


def test_d_counter_always_present_history_present_for_both_populated_and_zero_cases() -> None:
    quiet = _FakeModule("QUIET")
    run(quiet.pr.err_s("boom", errno=3))
    noisy_free = _FakeModule("FREE")
    _service, app = _make_service(error_sources=[quiet, noisy_free])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["QUIET"]["counter"] == 1
    assert errcount["QUIET"]["history"] == [{"num": 3, "type": "E"}]
    assert errcount["FREE"]["counter"] == 0
    assert errcount["FREE"]["history"] == []


def test_d_a_module_whose_log_holds_no_entry_of_its_own_still_gets_the_empty_shape() -> None:
    # Distinct from the zero-counter case above, which returns a real entry reading 0: here the
    # module's own name is absent from the log entirely. Without the fallback the response would
    # carry a null that every js/ consumer would have to special-case.
    empty = _FakeModule("EMPTY")

    async def no_entry_at_all() -> "dict[str, Any]":
        return {}

    empty.get_error_counter = no_entry_at_all  # type: ignore[method-assign]
    _service, app = _make_service(error_sources=[empty])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["EMPTY"] == {"counter": 0, "history": []}


def test_d_get_error_sources_reports_the_service_itself_for_a_uniform_caller() -> None:
    # Part C.14's fan-in accessor. The generated _collect_error_sources() does not consult it - this
    # service's /status entry is added directly - but D.10 keeps the shape so no caller special-cases it.
    service, _app = _make_service()
    assert service.get_error_sources() == [service]


def test_d_reset_errors_calls_reset_error_counter_on_every_registered_module() -> None:
    mods = [_FakeModule(n) for n in ("SGP40", "BMP3XX", "NEOPIXEL", "DNS", "CFGMGR_SGP40")]
    for m in mods:
        run(m.pr.err_s("x", errno=1))
    _service, app = _make_service(error_sources=mods)
    run(app.dispatch_request(_make_request(app, "PUT", "/status", {"ResetErrors": True})))
    for m in mods:
        assert m.pr.reset_calls == 1, m.name


def test_d_own_errcount_entry_reflects_real_logged_warnings_and_resets_with_the_rest() -> None:
    # This service's own "WEBSERVER" entry uses the real PrintLogHistory (self.pr), not a
    # _FakeModule - exercised directly via a real per-call timeout reclaim (F.2-style), then
    # confirmed ResetErrors clears it same as every registered module.
    service, app = _make_service(error_sources=[], per_call_timeout_s=0.01)
    reader = _HangingReader()
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["WEBSERVER"]["counter"] >= 1
    run(app.dispatch_request(_make_request(app, "PUT", "/status", {"ResetErrors": True})))
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    assert json.loads(status_body(res))["errcount"]["WEBSERVER"]["counter"] == 0


def test_d_reset_on_one_module_never_affects_another() -> None:
    a = _FakeModule("A")
    b = _FakeModule("B")
    run(a.pr.err_s("x", errno=1))
    run(b.pr.err_s("y", errno=2))
    _service, app = _make_service(error_sources=[a, b])
    run(app.dispatch_request(_make_request(app, "PUT", "/status", {"ResetErrors": True})))
    # Both reset together by this global action (decision: ResetErrors resets every module, not
    # scoped per-module) - the isolation property under test is that resetting doesn't cross-wire
    # one module's history into another's.
    assert a.pr.history == []
    assert b.pr.history == []
    assert a.pr.reset_calls == 1
    assert b.pr.reset_calls == 1


def test_d_webserver_own_errcount_entry_accumulates_a_warning_on_reclaim() -> None:
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=0.2, max_connections=2)
    reader = _HangingReader()
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=2.0)
    log = run(service.get_error_counter())
    entry = next(iter(log.values()))
    assert entry["ErrCount"] >= 1
    assert "W" in entry["ErrType"]  # a warning, not an error - decision 8's explicit distinction


def test_d_status_put_malformed_json_body_is_a_clean_rejection_not_a_crash() -> None:
    module = _FakeModule("SGP40")
    _service, app = _make_service(error_sources=[module])
    req = _make_request(app, "PUT", "/status", {})
    req._body = b"{not valid json"
    req.content_length = len(req._body)
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    assert json.loads(res.body) == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}
    assert module.pr.reset_calls == 0  # never reached the ResetErrors dispatch at all


# ---------------------------------------------------------------------------
# Section E - GET snapshot/copy-safety tests.
# ---------------------------------------------------------------------------


def test_e_concurrent_put_during_get_never_produces_a_torn_response() -> None:
    mod = _FakeModule("WIFI", values={"Interval": 1, "Offset": 0})
    _service, app = _make_service(settings={"networking": [SettingsGroup(mod, ("Interval", "Offset"))]})

    async def scenario() -> None:
        put_task = asyncio.get_event_loop().create_task(
            app.dispatch_request(_make_request(app, "PUT", "/networking", {"Interval": 99, "Offset": 99})),
        )
        get_res = await app.dispatch_request(_make_request(app, "GET", "/networking", None))
        await put_task
        body = json.loads(status_body(get_res))
        # MicroPython's cooperative, non-preemptive scheduling means the synchronous dict-build in
        # get_dict_cfg() can't be interleaved by the PUT's own await points - either both fields are
        # the old values or both are the new ones, never a mix (CLAUDE.md Part F).
        assert body in ({"Interval": 1, "Offset": 0}, {"Interval": 99, "Offset": 99})

    run(scenario())


def test_e_scd30_bmp3xx_live_readback_torn_read_is_a_known_characterization_not_a_regression() -> None:
    # Characterizes the known, already-flagged gap (SPECIFICATION.md Part A.8's GET-shapes note)
    # rather than asserting it fixed, so a future fix has a red test to turn green. The fake's
    # get_dict_cfg() awaits mid-construction, the real SCD30_Reader/BMP3xx_Reader shape.
    class _LiveReadbackModule(_FakeModule):
        async def get_dict_cfg(self) -> "dict[str, Any]":
            result: dict[str, Any] = {}
            for key in ("Interval", "Offset"):
                await asyncio.sleep(0)  # a real await - the torn-read window
                result[key] = self._values[key]
            return result

    mod = _LiveReadbackModule("SCD30", values={"Interval": 1, "Offset": 0})
    _service, _app = _make_service(settings={"sensors_live": [SettingsGroup(mod, ("Interval", "Offset"))]})

    async def scenario() -> "dict[str, Any]":
        async def mutate_mid_read() -> None:
            await asyncio.sleep(0)
            mod._values["Offset"] = 99

        mutate_task = asyncio.get_event_loop().create_task(mutate_mid_read())
        result = await mod.get_dict_cfg()
        await mutate_task
        return result

    result = run(scenario())
    # A torn read: Interval read before the mutation, Offset read after it - exactly the documented,
    # accepted gap, not something this test suite is meant to fail on.
    assert result == {"Interval": 1, "Offset": 99}


def test_e_mutating_a_returned_getter_dict_never_affects_the_modules_own_state() -> None:
    mod = _FakeModule("SCD30", data={"CO2": 800})
    _service, _app = _make_service(sensors=[mod])
    d1 = run(mod.get_dict_data())
    d1["CO2"] = 0
    d2 = run(mod.get_dict_data())
    assert d2 == {"CO2": 800}


# ---------------------------------------------------------------------------
# Section F - connection-lifecycle robustness. Exercises WebserverService._serve() directly
# against the fake reader/writer doubles above - no real socket, and never a real select.poll()
# (the CI-hang-fix precedent).
# ---------------------------------------------------------------------------

# F.1 - before/at accept


def test_f1_client_sends_nothing_ever_is_reclaimed_by_the_per_call_timeout() -> None:
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=2.0)
    writer = _ScriptedWriter()
    run_timed(service._serve(_HangingReader(), writer), timeout_s=2.0)
    assert run(service._open_conns.get_value()) == 0
    assert writer.close_called


def test_f1_client_opens_then_immediately_closes_before_any_bytes() -> None:
    service, _app = _make_service()
    writer = _ScriptedWriter()
    run_timed(service._serve(_ClosedReader(), writer))
    assert run(service._open_conns.get_value()) == 0


def test_f1_rapid_connect_disconnect_churn_keeps_counter_accurate() -> None:
    service, _app = _make_service()

    async def churn() -> None:
        for _ in range(50):
            await service._serve(_ClosedReader(), _ScriptedWriter())

    run_timed(churn(), timeout_s=10.0)
    assert run(service._open_conns.get_value()) == 0


def test_f1_connections_up_to_ceiling_accepted_beyond_ceiling_silently_closed() -> None:
    service, _app = _make_service(max_connections=2, per_call_timeout_s=5.0, outer_cap_s=5.0)

    async def scenario() -> None:
        # Two long-lived (never-completing) connections occupy the ceiling.
        held_writers = [_ScriptedWriter() for _ in range(2)]
        held_tasks = [
            asyncio.get_event_loop().create_task(service._serve(_HangingReader(), w)) for w in held_writers
        ]
        await asyncio.sleep(0.01)
        assert await service._open_conns.get_value() == 2

        # A third, well-formed connection arrives while at the ceiling.
        extra_writer = _ScriptedWriter()
        extra_reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
        await service._serve(extra_reader, extra_writer)
        assert extra_writer.written == b""  # never accepted - no response ever written
        assert await service._open_conns.get_value() == 2  # unchanged by the rejection

        for t in held_tasks:
            t.cancel()

    run_timed(scenario(), timeout_s=5.0)


def test_f1_a_slot_freed_by_reclaim_accepts_the_next_connection_immediately() -> None:
    service, _app = _make_service(max_connections=1, per_call_timeout_s=0.05, outer_cap_s=2.0)

    async def scenario() -> None:
        await service._serve(_HangingReader(), _ScriptedWriter())  # reclaimed by per-call timeout
        assert await service._open_conns.get_value() == 0
        second_reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
        second_writer = _ScriptedWriter()
        await service._serve(second_reader, second_writer)
        assert second_writer.written != b""  # actually served this time, no cooldown gap

    run_timed(scenario(), timeout_s=5.0)


class _GatedCloseWriter(_ScriptedWriter):
    # wait_closed() returns only once the test opens the gate - a close lwIP is still finishing.
    def __init__(self, gate: "asyncio.Event") -> None:
        super().__init__()
        self._gate = gate

    async def wait_closed(self) -> None:
        self.wait_closed_called = True
        await self._gate.wait()


def test_f1_a_slot_is_held_until_the_close_completes_not_until_the_response_is_written() -> None:
    # Settled (SPECIFICATION.md H.7): the client already holds its whole response, yet the slot counts
    # until _close_writer() returns - its heap and pcb are still live, and the board is CPU-bound, so
    # an earlier admission serves nothing more. The ~70 % refusals of back-to-back clients follow.
    service, _app = _make_service(max_connections=1, per_call_timeout_s=5.0, outer_cap_s=5.0)

    async def scenario() -> None:
        gate = asyncio.Event()
        closing = _GatedCloseWriter(gate)
        reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))], eof=True)
        task = asyncio.get_event_loop().create_task(service._serve(reader, closing))
        try:  # the gate always opens: a task left parked on it would wake inside a later test's loop
            for _ in range(200):
                if closing.wait_closed_called:
                    break
                await asyncio.sleep(0.01)
            assert closing.wait_closed_called, "the connection never reached its close"
            assert closing.written.startswith(b"HTTP/1.") and b"\r\n\r\n" in closing.written, closing.written
            held = await service._open_conns.get_value()
            assert held == 1, f"the response is out but the close is not; the slot must still count, got {held}"

            refused = _ScriptedWriter()
            await service._serve(_ScriptedReader([(0, _request_bytes("GET", "/status"))], eof=True), refused)
            assert refused.written == b"" and refused.close_called  # refused like any over-ceiling client
        finally:
            gate.set()
            await task
        assert await service._open_conns.get_value() == 0
        admitted = _ScriptedWriter()
        await service._serve(_ScriptedReader([(0, _request_bytes("GET", "/status"))], eof=True), admitted)
        assert admitted.written.startswith(b"HTTP/1."), admitted.written

    run_timed(scenario(), timeout_s=5.0)


# F.2 - mid-request, headers/request-line


def test_f2_trickled_request_line_is_reclaimed_by_the_outer_cap_not_a_single_per_call_timeout() -> None:
    # Each header LINE arrives as one atomic chunk, paced so no single readline() approaches the
    # per-call timeout - the outer per-connection wall-clock cap is what must bound the connection
    # here (SPECIFICATION.md Part A.8, connection-hardening item 1).
    line_delay = 0.02
    per_call = 1.0  # generous - no single line's own readline() call should ever approach this
    outer_cap = 0.05  # exceeded partway through line-by-line delivery (0.02s/line) regardless
    full_line = _request_bytes("GET", "/status")
    physical_lines = [part + b"\r\n" for part in full_line.split(b"\r\n")[:-1]]  # drop the trailing
    # split() artifact after the final \r\n - see full_line's own \r\n\r\n terminator
    chunks = [(line_delay, line) for line in physical_lines]
    service, _app = _make_service(per_call_timeout_s=per_call, outer_cap_s=outer_cap)
    reader = _ScriptedReader(chunks)
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=outer_cap * 20)
    assert run(service._open_conns.get_value()) == 0
    assert writer.written == b""  # reclaimed before a response could ever be produced


def test_f2_malformed_request_line_degrades_safely_via_microdots_own_blanket_catch() -> None:
    service, _app = _make_service()
    reader = _ScriptedReader([(0, b"NOT A VALID REQUEST LINE AT ALL\r\n\r\n")])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert run(service._open_conns.get_value()) == 0  # no exception escaped _serve()


def test_f2_content_length_larger_than_body_sent_then_silence_times_out() -> None:
    # The per-call readexactly() timeout is an asyncio.TimeoutError, a plain Exception and not an
    # OSError (confirmed against the pinned interpreter's extmod/asyncio/core.py) - so it is
    # absorbed by handle_request()'s blanket catch, which writes its own ordinary 400.
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=1.0)
    headers = "PUT /networking HTTP/1.1\r\nContent-Length: 1000\r\nContent-Type: application/json\r\n\r\n"
    reader = _ScriptedReader([(0, headers.encode() + b'{"Interval":')])  # body truncated, then silence
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0
    assert b" 400 " in writer.written  # Microdot's own ordinary 400 response, not a silent drop


def test_f2_content_length_exceeding_max_content_length_returns_413() -> None:
    service, _app = _make_service(max_content_length=64, per_call_timeout_s=2.0, outer_cap_s=2.0)
    body = json.dumps({"Interval": 1, "Padding": "x" * 200}).encode()
    reader = _ScriptedReader([(0, _request_bytes("PUT", "/networking", body))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0
    assert b"413" in writer.written


def test_f2_body_truncated_by_a_clean_peer_close_degrades_via_microdots_own_blanket_catch() -> None:
    # EOFError isn't an OSError, so ext/microdot.py's handle_request() hits its non-re-raising
    # `except Exception` clause, leaves req None and falls through to its own ordinary 400 - it
    # never reaches our serve() wrapper, unlike a timeout, which is an unmuted OSError.
    headers = "PUT /networking HTTP/1.1\r\nContent-Length: 100\r\nContent-Type: application/json\r\n\r\n"
    service, _app = _make_service(per_call_timeout_s=1.0, outer_cap_s=2.0)
    reader = _ScriptedReader([(0, headers.encode() + b'{"Interval": 1}')], eof=True)  # then a clean EOF, not silence
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0
    assert b" 400 " in writer.written  # Microdot's own ordinary 400 response, not a silent drop


# F.2b - request-body buffering: an oversized body must never be read into memory at all.
#
# ext/microdot.py reads the body inside Request.create() (`:426`) and only answers 413 later, in
# dispatch_request() (`:1443`), so a body between max_body_length and max_content_length is
# allocated in full and then thrown away - the band WebserverService closes by binding the two.
#
# These tests pin the direct cause, not a memory heuristic the Unix-port heap could never show: the
# server must never ASK its reader for more than the cap (same framing as H.3/I.2's hammers). Why
# both caps had to move together, with the measured schema maxima: SPECIFICATION.md Part I.6.


class _BodySizeReader(_ScriptedReader):
    # Records every readexactly() size, which is exactly what Request.create() uses to pull a body
    # into one contiguous bytes object - so max_body_read is the largest single body allocation the
    # server attempted, observed without patching anything.
    def __init__(self, chunks: "list[tuple[float, bytes]]", *, eof: bool = False) -> None:
        super().__init__(chunks, eof=eof)
        self.body_reads: list[int] = []

    async def readexactly(self, n: int) -> bytes:
        self.body_reads.append(n)
        return await super().readexactly(n)

    @property
    def max_body_read(self) -> int:
        return max(self.body_reads) if self.body_reads else 0


_BODY_CAP = 2048  # what _make_service() sets, matching the shipped default


def _sized_put(payload_bytes: int, interval: int = 7) -> bytes:
    # A /networking PUT of exactly payload_bytes, carrying a REAL field ("Interval") next to the
    # padding - so an accepted one has to be genuinely applied, not merely not-rejected, and the
    # padding key is one no driver registers so it can never validate as real config.
    envelope = len(json.dumps({"Interval": interval, "Padding": ""}).encode())
    body = json.dumps({"Interval": interval, "Padding": "x" * (payload_bytes - envelope)}).encode()
    return _request_bytes("PUT", "/networking", body)


def _body_service() -> "tuple[WebserverService, Microdot, _FakeModule]":
    mod = _FakeModule("NETWORKING", values={"Interval": 5, "Offset": 0})
    service, app = _make_service(
        settings={"networking": [SettingsGroup(mod, ("Interval", "Offset"))]}, per_call_timeout_s=2.0, outer_cap_s=2.0,
    )
    return service, app, mod


def _serve_one(service: "WebserverService", body_bytes: int, interval: int = 7) -> "tuple[_BodySizeReader, _ScriptedWriter]":
    reader = _BodySizeReader([(0, _sized_put(body_bytes, interval))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    return reader, writer


def test_f2b_none_above_the_cap_every_body_is_buffered_and_applied() -> None:
    service, _app, mod = _body_service()
    for n, size in enumerate((64, 512, _BODY_CAP - 1, _BODY_CAP)):  # the cap is inclusive: `<=` in Request.create()
        reader, writer = _serve_one(service, size, interval=10 + n)
        assert b" 200 " in writer.written, (size, writer.written[:80])
        assert reader.max_body_read == size, (size, reader.body_reads)
        # Accepted means APPLIED: the real field next to the padding reached the module.
        assert mod.set_calls[-1]["Interval"] == 10 + n, (size, mod.set_calls[-1])
        assert run(service._open_conns.get_value()) == 0


def test_f2b_all_above_the_cap_are_rejected_without_the_body_ever_being_read() -> None:
    service, _app, mod = _body_service()
    for size in (_BODY_CAP + 1, _BODY_CAP * 2, _BODY_CAP * 8):
        reader, writer = _serve_one(service, size)
        assert b"413" in writer.written, (size, writer.written[:80])
        # The whole point: not "read then discarded", but never read. body_reads stays empty
        # because Request.create() takes its `else` branch and hands over the stream instead.
        assert reader.body_reads == [], (size, reader.body_reads)
        assert run(service._open_conns.get_value()) == 0
    assert mod.set_calls == []  # nothing was applied: every one was refused before any handler ran


def test_f2b_a_mixed_stream_handles_each_request_on_its_own_merits() -> None:
    # "some above": interleaved, so a rejection can never leave the next acceptance mis-parsed and
    # an acceptance can never let the next oversized one through.
    service, _app, mod = _body_service()
    sizes = [128, _BODY_CAP * 4, 700, _BODY_CAP + 1, _BODY_CAP, 64, _BODY_CAP * 16]
    applied = 0
    for n, size in enumerate(sizes):
        reader, writer = _serve_one(service, size, interval=20 + n)
        if size <= _BODY_CAP:
            applied += 1
            assert b" 200 " in writer.written, (size, writer.written[:80])
            assert reader.max_body_read == size, (size, reader.body_reads)
            assert mod.set_calls[-1]["Interval"] == 20 + n, (size, mod.set_calls[-1])
        else:
            assert b"413" in writer.written, (size, writer.written[:80])
            assert reader.body_reads == [], (size, reader.body_reads)
        assert len(mod.set_calls) == applied, (size, mod.set_calls)  # no rejected one slipped through
        assert run(service._open_conns.get_value()) == 0


def test_f2b_the_two_microdot_caps_are_bound_together_so_the_band_cannot_reopen() -> None:
    # Structural guard: the defect is not a value, it is the GAP between the two. A future change
    # that sets only one of them would silently reopen it, and every behavioural test above would
    # still pass for bodies under whichever cap ended up larger.
    _service, _app = _make_service(max_content_length=777)
    assert Request.max_content_length == 777
    assert Request.max_body_length == 777


def _body_service_with_connections(max_connections: int) -> "tuple[WebserverService, Microdot, _FakeModule]":
    mod = _FakeModule("NETWORKING", values={"Interval": 5, "Offset": 0})
    service, app = _make_service(
        settings={"networking": [SettingsGroup(mod, ("Interval", "Offset"))]},
        max_connections=max_connections, per_call_timeout_s=2.0, outer_cap_s=5.0,
    )
    return service, app, mod


def _hammer_mixed_bodies(service: "WebserverService", sizes: "list[int]") -> "list[_BodySizeReader]":
    readers = [_BodySizeReader([(0, _sized_put(size))]) for size in sizes]
    writers = [_ScriptedWriter() for _ in sizes]

    async def _all() -> None:  # index-based, not zip(): MicroPython's zip() has no strict= (B905)
        await asyncio.gather(*(service._serve(readers[i], writers[i]) for i in range(len(sizes))))

    run_timed(_all(), timeout_s=10.0)
    for i, size in enumerate(sizes):
        expected = b" 200 " if size <= _BODY_CAP else b"413"
        assert expected in writers[i].written, (size, writers[i].written[:80])
    return readers


def test_f2b_hammer_concurrent_mixed_bodies_bound_the_total_buffered_bytes() -> None:
    # The real-hardware shape this protects: max_connections bodies can be in flight at once, so
    # the simultaneous contiguous demand is that many buffers, not one. With the caps bound it is
    # bounded by connections x cap; with the band open it would be connections x 16 KB.
    orig_threshold = gc.threshold()
    gc.threshold(-1)  # I.4(e) first: the guarantee must hold at MicroPython's own real default
    try:
        service, _app, mod = _body_service_with_connections(64)
        sizes = [_BODY_CAP * 4 if i % 3 else 512 for i in range(60)]
        readers = _hammer_mixed_bodies(service, sizes)
        assert sum(r.max_body_read for r in readers) == sum(s for s in sizes if s <= _BODY_CAP)
        assert all(r.max_body_read <= _BODY_CAP for r in readers)
        assert len(mod.set_calls) == sum(1 for s in sizes if s <= _BODY_CAP)  # every under-cap one applied
        assert run(service._open_conns.get_value()) == 0
    finally:
        gc.threshold(orig_threshold)


def test_f2b_hammer_all_oversized_allocates_no_body_at_all() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(32768)  # and again at the shipped threshold, as H.3 does for its own pair
    try:
        service, _app, mod = _body_service_with_connections(64)
        readers = _hammer_mixed_bodies(service, [_BODY_CAP * 6] * 40)
        assert all(r.body_reads == [] for r in readers)
        assert mod.set_calls == []
        assert run(service._open_conns.get_value()) == 0
    finally:
        gc.threshold(orig_threshold)



# F.5 - after response / close


def test_f5_normal_close_decrements_counter_exactly_once() -> None:
    service, _app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert run(service._open_conns.get_value()) == 0
    assert writer.close_called


def test_f5_connection_close_header_present_on_every_response_including_errors() -> None:
    service, _app = _make_service()
    for method, path in (("GET", "/status"), ("GET", "/no/such/route"), ("DELETE", "/status")):
        writer = _ScriptedWriter()
        reader = _ScriptedReader([(0, _request_bytes(method, path))])
        run_timed(service._serve(reader, writer))
        assert b"Connection: close" in writer.written, path


def test_f5_double_close_paths_dont_raise_or_double_decrement() -> None:
    service, _app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))  # our own finally + Microdot's own aclose() both run
    assert run(service._open_conns.get_value()) == 0


# F.6 - concurrency / resource-ceiling behavior


def test_f6_n_simultaneous_wedged_connections_are_each_independently_reclaimed() -> None:
    service, _app = _make_service(max_connections=3, per_call_timeout_s=0.05, outer_cap_s=0.5)

    async def scenario() -> None:
        writers = [_ScriptedWriter() for _ in range(3)]
        await asyncio.gather(*(service._serve(_HangingReader(), w) for w in writers))
        assert await service._open_conns.get_value() == 0
        for w in writers:
            assert w.close_called

    run_timed(scenario(), timeout_s=5.0)


def test_f6_no_cooldown_gap_between_a_reclaim_and_the_next_accept() -> None:
    service, _app = _make_service(max_connections=1, per_call_timeout_s=0.02, outer_cap_s=1.0)

    async def scenario() -> None:
        start = 0
        for _ in range(5):  # repeated reclaim/accept cycles, no artificial grace period between them
            await service._serve(_HangingReader(), _ScriptedWriter())
            assert await service._open_conns.get_value() == 0
            start += 1
        assert start == 5

    run_timed(scenario(), timeout_s=10.0)


def test_f6_pathological_repeated_rewedging_stays_bounded_never_escalates() -> None:
    service, _app = _make_service(max_connections=2, per_call_timeout_s=0.02, outer_cap_s=0.2)

    async def scenario() -> None:
        for _ in range(30):  # a hostile client immediately reconnecting and rewedging
            await service._serve(_HangingReader(), _ScriptedWriter())
        # Worst case bounded to "ceiling slots occupied for at most one outer-cap duration,
        # repeatedly" - never an unbounded backlog, never a _TASK_FAIL_MAX-style escalation.
        assert await service._open_conns.get_value() == 0

    run_timed(scenario(), timeout_s=15.0)


def test_f6_a_hanging_cleanup_close_path_still_lets_the_connection_task_end() -> None:
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=0.2)
    writer = _ScriptedWriter(hang_close=True)  # wait_closed() itself never returns
    run_timed(service._serve(_HangingReader(), writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0  # the connection task still ended


class _RaisingCloseWriter(_ScriptedWriter):
    def close(self) -> None:
        raise RuntimeError("simulated close() failure")


def test_close_writer_swallows_a_raising_close_and_still_awaits_wait_closed() -> None:
    # writer.close() raising is real Stream-caller-supplied behavior this module must never let
    # escape (_close_writer()'s own try/except) - and the cleanup must still proceed to wait_closed()
    # afterward, not abort early.
    service, _app = _make_service()
    writer = _RaisingCloseWriter()
    run_timed(service._close_writer(writer))
    assert writer.wait_closed_called is True


def test_close_writer_logs_a_persisted_warning_when_close_raises() -> None:
    # Step 6 (silent-failure-masking finding): a raising close()/wait_closed() must not just be
    # swallowed silently - it needs a persisted signal, the same as every other connection-lifecycle
    # failure this file already logs (peer-closed-early, timed-out, socket-error).
    service, _app = _make_service()
    writer = _RaisingCloseWriter()
    run_timed(service._close_writer(writer))
    assert service.pr.err_count == 1


class _RaisingWaitClosedWriter(_ScriptedWriter):
    async def wait_closed(self) -> None:
        self.wait_closed_called = True
        raise OSError("simulated wait_closed() failure")


def test_close_writer_logs_a_persisted_warning_when_wait_closed_raises() -> None:
    service, _app = _make_service()
    writer = _RaisingWaitClosedWriter()
    run_timed(service._close_writer(writer))
    assert writer.close_called is True
    assert service.pr.err_count == 1


def test_a_close_whose_own_warning_runs_out_of_heap_still_frees_the_slot() -> None:
    # At the limit's extreme the heap empties (Part H.7), so the warning a failed close() logs can
    # itself raise MemoryError; the slot must be freed anyway, or every later connection is refused.
    service, _app = _make_service(max_connections=1)

    async def out_of_heap(*_args: "Any", **_kwargs: "Any") -> None:
        raise MemoryError("simulated exhausted heap")

    service.pr.wrn_s = out_of_heap  # type: ignore[method-assign]  # deliberate monkeypatch
    for _ in range(3):
        try:
            run_timed(service._serve(_ClosedReader(), _RaisingCloseWriter()))
        except MemoryError:
            pass  # escaping is acceptable here; keeping the slot is not
        assert run(service._open_conns.get_value()) == 0


class _HangingWriter(_ScriptedWriter):
    async def awrite(self, data: bytes) -> None:
        await asyncio.Event().wait()


def test_a_write_phase_timeout_is_logged_once_not_twice() -> None:
    # A write timeout escapes microdot (it catches OSError only) and reaches _serve()'s own log;
    # the proxy logging it as well counted one reclaimed connection as two warnings.
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=2.0)
    request = _request_bytes("GET", "/status")
    run_timed(service._serve(_ScriptedReader([(0.0, request)]), _HangingWriter()), timeout_s=2.0)
    entry = next(iter(run(service.get_error_counter()).values()))
    assert entry["ErrCount"] == 1, entry
    assert run(service._open_conns.get_value()) == 0


class _ResetReader:
    # A peer that reset mid-request: modlwip raises ECONNRESET on the read, then frees the pcb.
    async def readline(self) -> bytes:
        raise OSError(104, "ECONNRESET")

    async def readexactly(self, _n: int) -> bytes:
        raise OSError(104, "ECONNRESET")


def test_nothing_is_written_to_a_peer_whose_read_saw_a_reset() -> None:
    # microdot mutes the reset and answers 400 anyway; on silicon that write reaches tcp_write(NULL)
    # (state 6 passes modlwip's error check), logs a spurious warning and can spin a slot for 5 s.
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=1.0)
    writer = _ScriptedWriter()
    run_timed(service._serve(_ResetReader(), writer), timeout_s=2.0)
    assert writer.written == b"", writer.written
    assert writer.close_called is True
    assert service.pr.err_count == 0, service.pr.err_count
    assert run(service._open_conns.get_value()) == 0


def test_timeout_stream_proxy_close_and_wait_closed_forward_to_the_wrapped_stream() -> None:
    # Direct coverage of the two Stream-forwarding methods ext/microdot.py never calls in Section
    # F's scenarios (close() is sync; wait_closed() only ever reaches the raw writer, via
    # WebserverService._close_writer()) - still real forwards that must work correctly.
    writer = _ScriptedWriter()
    proxy = _TimeoutStreamProxy(writer, 1.0, _FakeLogger("X"))  # type: ignore[arg-type]
    proxy.close()
    assert writer.close_called is True
    run_timed(proxy.wait_closed())
    assert writer.wait_closed_called is True


def test_serve_absorbs_an_eoferror_raised_directly_by_handle_request() -> None:
    # Structurally unreachable through the real Microdot integration today (see _serve()'s own
    # comment) - this is the defense-in-depth branch itself, exercised directly by monkeypatching
    # app.handle_request() to prove _serve()'s except EOFError clause actually degrades cleanly.
    service, app = _make_service()

    async def _raise_eof(_reader: object, _writer: object) -> None:
        raise EOFError

    app.handle_request = _raise_eof
    run_timed(service._serve(_ScriptedReader([]), _ScriptedWriter()))
    assert run(service._open_conns.get_value()) == 0


def test_serve_absorbs_an_oserror_raised_directly_by_handle_request() -> None:
    # Never actually raised by any of this module's own fakes/proxy (see _serve()'s own comment) -
    # a genuine real-hardware socket failure is the only real trigger, so exercised directly here.
    service, app = _make_service()

    async def _raise_os(_reader: object, _writer: object) -> None:
        raise OSError("simulated socket failure")

    app.handle_request = _raise_os
    run_timed(service._serve(_ScriptedReader([]), _ScriptedWriter()))
    assert run(service._open_conns.get_value()) == 0


def test_serve_absorbs_an_unexpected_exception_raised_directly_by_handle_request() -> None:
    service, app = _make_service()

    async def _raise_boom(_reader: object, _writer: object) -> None:
        raise RuntimeError("simulated unexpected bug")

    app.handle_request = _raise_boom
    run_timed(service._serve(_ScriptedReader([]), _ScriptedWriter()))
    assert run(service._open_conns.get_value()) == 0
    log = run(service.get_error_counter())
    entry = next(iter(log.values()))
    assert "E" in entry["ErrType"]  # errno=1 path (err_s, not wrn_s) - a genuinely unexpected bug


# F.7 - adversarial/malformed-input shapes


def test_f7_unknown_path_returns_404_shaped_response() -> None:
    service, _app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/no/such/route"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert b" 404 " in writer.written


def test_f7_wrong_http_method_on_a_known_path_returns_405_shaped_response() -> None:
    service, _app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("DELETE", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert b" 405 " in writer.written


def test_f7_extremely_long_url_path_is_handled_cleanly_not_a_crash() -> None:
    service, _app = _make_service(per_call_timeout_s=2.0, outer_cap_s=2.0)
    long_path = "/status/" + ("a" * 8192)
    reader = _ScriptedReader([(0, _request_bytes("GET", long_path))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0  # reclaimed or 404'd, never an escaped exception


def test_f7_dedicated_multi_connection_slowloris_simulation_all_reclaimed_and_slots_reused() -> None:
    per_call = 0.02
    outer_cap = 0.1
    service, _app = _make_service(max_connections=3, per_call_timeout_s=per_call, outer_cap_s=outer_cap)

    def trickle_reader() -> _ScriptedReader:
        full_line = _request_bytes("GET", "/status")
        return _ScriptedReader([(per_call * 0.5, bytes([b])) for b in full_line])

    async def scenario() -> None:
        writers = [_ScriptedWriter() for _ in range(3)]
        await asyncio.gather(*(service._serve(trickle_reader(), w) for w in writers))
        assert await service._open_conns.get_value() == 0
        # A fresh, well-formed connection right after confirms slots are reusable, not permanently
        # poisoned by the Slowloris attempt.
        fresh_reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
        fresh_writer = _ScriptedWriter()
        await service._serve(fresh_reader, fresh_writer)
        assert fresh_writer.written != b""

    run_timed(scenario(), timeout_s=10.0)


# F.8 - server startup edge cases (largely resolved by section G's source research - these confirm
# our own code adds no incorrect special-casing on top of what asyncio.start_server()/Microdot
# already guarantee, not that a new mechanism is needed).


def test_f8_task_starters_exposes_exactly_one_server_task_for_the_supervisor() -> None:
    service, _app = _make_service()
    starters = service.get_task_starters()
    assert len(starters) == 1


def test_f8_start_serving_runs_a_real_asyncio_start_server_backed_task() -> None:
    # The one test exercising _run()/_start_serving() themselves - the real asyncio.start_server()
    # composition, never app.start_server()/app.shutdown(). Bound to an ephemeral loopback port,
    # never the real host/port=0.0.0.0:80 default.
    service, _app = _make_service(host="127.0.0.1", port=0)

    async def scenario() -> None:
        starters = service.get_task_starters()
        task = starters[0]()
        await asyncio.sleep(0.05)  # let _run() actually reach start_server()/wait_closed()
        assert not task.done()  # server.wait_closed() blocks forever until explicitly closed/cancelled
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run_timed(scenario(), timeout_s=3.0)


# F.9 - supervisor integration / soak (capstone)


def test_f9_soak_100_plus_start_wedge_reclaim_cycles_hold_counter_and_memory_flat() -> None:
    # The real 100+-cycle soak test this service's finish criteria calls for
    # ("gc.mem_free() flat") - not just the connection-counter invariant, mixing wedged and
    # well-formed connections across max_connections' full ceiling, never a restart step anywhere.
    import gc

    service, _app = _make_service(max_connections=2, per_call_timeout_s=0.02, outer_cap_s=0.1)

    async def one_cycle(i: int) -> None:
        if i % 3 == 0:
            await service._serve(_HangingReader(), _ScriptedWriter())
        else:
            reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
            await service._serve(reader, _ScriptedWriter())
        assert await service._open_conns.get_value() == 0

    async def scenario() -> None:
        for i in range(20):  # warm-up - let one-time allocations (first-use caches, etc.)
            await one_cycle(i)  # stabilize before the real memory baseline below is taken.
        gc.collect()
        baseline = gc.mem_free()
        for i in range(120):
            await one_cycle(i)
        gc.collect()
        after = gc.mem_free()
        # A real per-cycle leak grows roughly linearly with cycle count; a generous fixed tolerance
        # (not scaled per-cycle) catches that while tolerating ordinary allocator fragmentation.
        assert after >= baseline - 4096, f"gc.mem_free() dropped from {baseline} to {after} over 120 cycles"

    run_timed(scenario(), timeout_s=60.0)


# ---------------------------------------------------------------------------
# Section G - static-route serving (SPECIFICATION.md Part A.9). Exercises the generic route-wiring
# mechanism against a synthetic VfsFrozen fixture; the real built frozen_html.py artifact gets its
# own integration test in tests/test_website_build_integration.py.
# ---------------------------------------------------------------------------

_next_static_mount = 0


def _mount_static_fixture(files: "dict[str, bytes]") -> str:
    # A hand-built VfsFrozen (ext/freezefs/ffsmount.py) exercising the same runtime VFS a real
    # `import frozen_html` produces, without depending on any real website's content.
    # Entries store plain bytes under a ".gz" name: send_file() never inspects file contents.

    # A unique mount point per call - os.mount() raises EEXIST on a repeat target, and every test
    # in this file shares one interpreter process.
    global _next_static_mount
    _next_static_mount += 1
    mount_point = f"/test_static_{_next_static_mount}"
    direntries = [("/" + name + ".gz", (data, False, len(data))) for name, data in files.items()]
    fs = VfsFrozen(direntries, sum(len(d) for d in files.values()), len(files))
    os.mount(fs, mount_point, readonly=True)
    return mount_point


def test_g_static_root_serves_the_configured_index_file() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/", None)))
    assert res.status_code == 200
    assert res.body.read() == b"<h1>hi</h1>"
    assert res.headers["Content-Type"].startswith("text/html")
    assert res.headers["Content-Encoding"] == "gzip"


def test_g_static_wildcard_also_serves_the_index_file_by_its_own_name() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/index.html", None)))
    assert res.status_code == 200
    assert res.body.read() == b"<h1>hi</h1>"


def test_g_static_wildcard_serves_a_named_file_with_the_right_content_type() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>", "style.css": b"body{color:red}"})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/style.css", None)))
    assert res.status_code == 200
    assert res.body.read() == b"body{color:red}"
    assert res.headers["Content-Type"].startswith("text/css")
    assert res.headers["Content-Encoding"] == "gzip"


def test_g_static_binary_file_of_an_unmapped_type_falls_back_to_octet_stream() -> None:
    # favicon.ico is not in microdot's Response.types_map, so it must still serve, as binary.
    icon = bytes(range(256))
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>", "favicon.ico": icon})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/favicon.ico", None)))
    assert res.status_code == 200
    assert res.body.read() == icon
    assert res.headers["Content-Type"] == "application/octet-stream"


def test_g_static_missing_file_returns_404_via_the_shaped_error_handler() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/nope.txt", None)))
    assert res.status_code == 404
    assert json.loads(res.body) == {"res": "ERR", "code": 404, "descr": "Not found", "result": {}}


def test_g_static_directory_traversal_attempt_is_rejected_not_resolved() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/foo/../../index.html", None)))
    assert res.status_code == 404


def test_g_static_nested_path_not_found_since_the_stub_mount_is_flat() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/sub/deep/file.txt", None)))
    assert res.status_code == 404


def test_g_static_routes_never_shadow_a_real_api_endpoint() -> None:
    # Registration-order regression test: /<path:filename>'s regex also matches "/measurements",
    # and Microdot's find_route() returns the first matching route in registration order - so the
    # static wildcard must be registered after every real API route.
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>", "measurements": b"not the real one"})
    _service, app = _make_service(sensors=[scd], static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(status_body(res)) == {"SCD30": {"CO2": 800}}  # the real endpoint, not the static file


def test_g_static_routes_are_not_registered_at_all_when_static_mount_is_none() -> None:
    _, app = _make_service()  # static_mount defaults to None
    res = run(app.dispatch_request(_make_request(app, "GET", "/", None)))
    assert res.status_code == 404  # no route matches "/" at all - not even attempted as a static file


def test_g_static_index_filename_is_configurable() -> None:
    mount = _mount_static_fixture({"home.html": b"custom index"})
    _, app = _make_service(static_mount=mount, static_index="home.html")
    res = run(app.dispatch_request(_make_request(app, "GET", "/", None)))
    assert res.status_code == 200
    assert res.body.read() == b"custom index"


# The per-write bound on the wire (SPECIFICATION.md Part I.3). Build-independent: a synthetic
# mount and a stub sensor whose sizes span many far-below-chunk objects, every edge of the 256 B
# chunk, and objects that take many chunks - read back write by write, as a socket would see them.

_WIRE_CHUNK_BYTES = 256  # WebserverService's chunk_bytes default, as observed from outside
_TINY_SIZES = tuple(range(64))
_EDGE_SIZES = (127, 128, 129, 255, 256, 257, 511, 512, 513, 767, 768, 769)
_LARGE_SIZES = (1023, 1024, 1025, 9292, 65553)  # 9292: the real page the bench sitting saw cut off


class _ChunkRecordingWriter(_ScriptedWriter):
    # Keeps every awrite() apart: the bound under test is per write, which .written erases.
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[bytes] = []

    async def awrite(self, data: bytes) -> None:
        self.chunks.append(bytes(data))
        await super().awrite(data)


def _get_on_the_wire(service: "WebserverService", path: str) -> "tuple[str, dict[str, str], list[bytes]]":
    writer = _ChunkRecordingWriter()
    run_timed(service._serve(_ScriptedReader([(0, _request_bytes("GET", path))], eof=True), writer), timeout_s=5.0)
    head = writer.chunks[0]  # the whole header block is one write (_TimeoutStreamProxy.awrite)
    assert head.endswith(b"\r\n\r\n") and head.count(b"\r\n\r\n") == 1, head
    lines = head.decode().split("\r\n")
    headers = dict(line.split(": ", 1) for line in lines[1:] if line)
    return lines[0].split(" ")[1], {k.lower(): v for k, v in headers.items()}, writer.chunks[1:]


def _patterned(size: int) -> bytes:
    return bytes((i * 7 + size) & 0xFF for i in range(size))  # distinct per size, so no two files match


def test_g3_every_static_file_arrives_whole_with_its_length_in_writes_of_at_most_256_bytes() -> None:
    sizes = _TINY_SIZES + _EDGE_SIZES + _LARGE_SIZES
    mount = _mount_static_fixture({f"f{size}.bin": _patterned(size) for size in sizes})
    service, _app = _make_service(static_mount=mount)
    for size in sizes:
        status, headers, body = _get_on_the_wire(service, f"/f{size}.bin")
        assert status == "200", (size, status)
        # Without Content-Length this HTTP/1.0 body ends only at FIN, so a cut-off page looked whole.
        assert headers.get("content-length") == str(size), (size, headers)
        assert b"".join(body) == _patterned(size), size
        assert max(len(chunk) for chunk in body) <= _WIRE_CHUNK_BYTES, (size, [len(c) for c in body])
        assert all(len(chunk) == _WIRE_CHUNK_BYTES for chunk in body[:-1]), (size, [len(c) for c in body])
    assert run(service.get_error_counter())["WEBSERVER"]["ErrCount"] == 0


def test_g3_a_json_route_mixing_tiny_medium_and_huge_values_is_written_in_bounded_pieces() -> None:
    data: dict[str, Any] = {f"t{i}": i for i in range(300)}  # many fragments far below the cap
    data.update({f"m{width}": "x" * width for width in (40, 127, 128, 200, 240, 250)})  # near the cap
    data["huge_list"] = list(range(0, 28000, 7))  # one value worth ~80 pieces
    data["huge_dict"] = {f"k{i}": [i, "v" * (i % 50)] for i in range(150)}
    stub = _NestedCfgModule("STUB", values={}, data=data)
    service, _app = _make_service(sensors=[stub])
    status, headers, body = _get_on_the_wire(service, "/measurements")
    assert status == "200"
    assert headers.get("content-length") == str(sum(len(chunk) for chunk in body))
    assert json.loads(b"".join(body)) == {"STUB": data}
    assert max(len(chunk) for chunk in body) <= _WIRE_CHUNK_BYTES, sorted(len(c) for c in body)[-5:]
    assert len(body) > 100  # the huge values really were split, not merely absent


def test_g3_one_chunk_bytes_parameter_bounds_json_pieces_and_static_reads_alike() -> None:
    # The two must never drift apart: one constructor value drives both, at a size of neither default.
    mount = _mount_static_fixture({"page.bin": _patterned(1000)})
    stub = _NestedCfgModule("STUB", values={}, data={f"t{i}": "z" * (i % 30) for i in range(120)})
    service, _app = _make_service(sensors=[stub], static_mount=mount, chunk_bytes=100)
    for path in ("/page.bin", "/measurements"):
        _status, _headers, body = _get_on_the_wire(service, path)
        assert max(len(chunk) for chunk in body) <= 100, (path, sorted(len(c) for c in body)[-3:])
        assert len(body) > 5, path  # really chunked at 100, not merely small
    _status, _headers, body = _get_on_the_wire(service, "/page.bin")
    assert [len(chunk) for chunk in body] == [100] * 10 + [0]  # microdot reads on until a short read


class _BodyFailingWriter(_ChunkRecordingWriter):
    # Takes the first write, then fails like a peer that vanished mid-response.
    async def awrite(self, data: bytes) -> None:
        if self.chunks:
            raise OSError(104, "ECONNRESET")
        await super().awrite(data)


def test_g3_the_header_block_is_one_write_so_a_cut_response_still_carries_its_length() -> None:
    # microdot writes each header apart, and a client reading EOF mid-headers takes it as their end:
    # a 200 with no Content-Length and no body, read as complete (MEASUREMENTS archive §7R.5's empty 200).
    mount = _mount_static_fixture({"page.bin": _patterned(1000)})
    service, _app = _make_service(static_mount=mount)
    for path in ("/page.bin", "/status", "/measurements", "/no-such-page"):
        _status, headers, _body = _get_on_the_wire(service, path)  # asserts the one-write head itself
        assert "content-length" in headers, (path, headers)
    writer = _BodyFailingWriter()
    run_timed(service._serve(_ScriptedReader([(0, _request_bytes("GET", "/page.bin"))], eof=True), writer), timeout_s=5.0)
    assert len(writer.chunks) == 1, writer.chunks
    assert writer.chunks[0].startswith(b"HTTP/1.0 200 OK\r\n") and b"Content-Length: 1000\r\n" in writer.chunks[0], writer.chunks


def test_g3_a_zero_chunk_bytes_is_clamped_so_a_static_read_still_ends() -> None:
    mount = _mount_static_fixture({"page.bin": _patterned(5)})
    service, _app = _make_service(static_mount=mount, chunk_bytes=0)
    status, _headers, body = _get_on_the_wire(service, "/page.bin")  # a read(0) loop would time out here
    assert status == "200" and b"".join(body) == _patterned(5)


def test_g3_a_single_scalar_longer_than_the_cap_is_the_one_piece_allowed_past_it_and_stays_whole() -> None:
    # _PieceWriter never splits a fragment, so this is the documented limit, not a bound. Part
    # I.3's need table was measured at every field's DEFAULT value; the next test takes the worst
    # case a schema actually permits.
    stub = _NestedCfgModule("STUB", values={}, data={"small": 1, "scalar": "y" * 600, "after": 2})
    service, _app = _make_service(sensors=[stub])
    _status, _headers, body = _get_on_the_wire(service, "/measurements")
    assert [chunk for chunk in body if len(chunk) > _WIRE_CHUNK_BYTES] == [json.dumps("y" * 600).encode()]
    assert json.loads(b"".join(body)) == {"STUB": {"small": 1, "scalar": "y" * 600, "after": 2}}


def test_g3_a_scalar_at_ntp_hosts_own_bound_still_makes_exactly_one_whole_piece() -> None:
    # The longest string any schema permits: asy_ntp_client's NTP_Host, 1,024 characters. Mirrored
    # as a literal because const() leaves no module attribute to read - test_asy_ntp_client.py
    # pins the bound itself, and BACKLOG's NTP_Host entry lists every file a change must touch.
    longest = 1024
    stub = _NestedCfgModule("STUB", values={}, data={"host": "y" * longest})
    service, _app = _make_service(sensors=[stub])
    _status, _headers, body = _get_on_the_wire(service, "/measurements")
    over = [chunk for chunk in body if len(chunk) > _WIRE_CHUNK_BYTES]
    assert over == [json.dumps("y" * longest).encode()], [len(c) for c in over]
    assert len(over[0]) == longest + 2, len(over[0])  # the two quotes; no escaping in this value


# G.2 - hotspot-mode captive-portal redirect fallback (SPECIFICATION.md Part A.5).
# `is_hotspot_active` only changes _serve_static()'s `except OSError` fallback branch; its default
# (None) must reproduce today's plain-404 behavior, since no existing call site passes it.


def test_g2_hotspot_active_redirects_an_unmatched_path_to_root() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: True)
    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 302
    assert res.headers["Location"] == "/"


def test_g2_hotspot_inactive_unmatched_path_still_404s() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: False)
    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 404
    assert json.loads(res.body) == {"res": "ERR", "code": 404, "descr": "Not found", "result": {}}


def test_g2_default_is_hotspot_active_none_preserves_the_pre_existing_404_behavior() -> None:
    # The actual backward-compatibility guarantee, tested directly rather than just inferred from
    # reading the constructor default - every existing call site omits this kwarg entirely.
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount)  # is_hotspot_active defaults to None
    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 404


def test_g2_hotspot_active_does_not_affect_a_real_static_file_hit() -> None:
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: True)
    res = run(app.dispatch_request(_make_request(app, "GET", "/", None)))
    assert res.status_code == 200
    assert res.body.read() == b"<h1>hi</h1>"


def test_g2_hotspot_active_does_not_shadow_a_real_api_route() -> None:
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(sensors=[scd], static_mount=mount, is_hotspot_active=lambda: True)
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(status_body(res)) == {"SCD30": {"CO2": 800}}


def test_g2_hotspot_redirect_does_not_log_a_warning_or_error() -> None:
    # Matches _shaped_error_handler()'s own "a routine 404 must not show up as an error" convention
    # (see tests_hardware/bench/test_network_resilience.py's real-hardware equivalent) - a routine
    # hotspot-mode redirect must likewise be silent.
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    service, app = _make_service(static_mount=mount, is_hotspot_active=lambda: True)
    run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    log = run(service.get_error_counter())
    assert log["WEBSERVER"]["ErrCount"] == 0


def test_g2_is_hotspot_active_raising_gets_the_shaped_500_via_the_existing_catch_all() -> None:
    # Proves the "no bespoke try/except needed" decision directly: SPECIFICATION.md Part A.5's existing
    # blanket app.errorhandler(Exception) already safely contains a raise from this callback.
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})

    def _raise() -> bool:
        raise RuntimeError("simulated is_hotspot_active failure")

    service, app = _make_service(static_mount=mount, is_hotspot_active=_raise)
    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 500
    assert json.loads(res.body) == {"res": "ERR", "code": 500, "descr": "Internal server error", "result": {}}
    log = run(service.get_error_counter())
    assert log["WEBSERVER"]["ErrCount"] == 1


def test_g2_directory_traversal_still_404s_even_when_hotspot_active() -> None:
    # The ".." guard aborts(404) before the try/except OSError block that consults
    # is_hotspot_active() is ever reached - a traversal attempt must never be redirected, hotspot
    # mode or not.
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: True)
    res = run(app.dispatch_request(_make_request(app, "GET", "/foo/../../index.html", None)))
    assert res.status_code == 404


def test_g2_put_to_unmatched_path_is_405_regardless_of_hotspot_state() -> None:
    # The wildcard route is registered GET-only, so find_route() resolves a PUT to 405 before
    # _serve_static() is invoked and is_hotspot_active() is never consulted - the redirect
    # fallback cannot leak into an unrelated error path.
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: True)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/generate_204", None)))
    assert res.status_code == 405


def test_g2_dynamic_is_hotspot_active_value_change_is_reflected_per_request() -> None:
    # Dynamic-mode-switch coverage: is_hotspot_active is called fresh on every request, not read once
    # at construction/first-call and cached - proven with a stateful callable whose return value
    # changes between two successive requests on the same WebserverService/app instance.
    state = {"active": False}
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: state["active"])

    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 404  # inactive -> old behavior

    state["active"] = True
    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 302
    assert res.headers["Location"] == "/"

    state["active"] = False
    res = run(app.dispatch_request(_make_request(app, "GET", "/generate_204", None)))
    assert res.status_code == 404  # switched back live, not stuck on the first-seen value


def test_g2_static_mount_none_with_is_hotspot_active_set_registers_no_routes() -> None:
    # Defensive combo: is_hotspot_active is only ever consulted from inside _serve_static(), which is
    # only reachable through the static routes - passing it with static_mount=None (no static routes
    # registered at all) must not crash and must not somehow force route registration.
    _, app = _make_service(is_hotspot_active=lambda: True)  # static_mount defaults to None
    res = run(app.dispatch_request(_make_request(app, "GET", "/", None)))
    assert res.status_code == 404  # no route matches "/" at all - same as the plain static_mount=None case


# H.1 - app.errorhandler(Exception) catch-all. Section G's 400/404/405/413/500 status-code
# handlers were the reply-shape half; this is the logging half, since Microdot's own
# print_exception(exc) never reaches pr.err_s()/FRAM history on its own.


class _RaisingSensorModule(_FakeModule):
    async def get_dict_data(self) -> "dict[str, Any]":
        raise RuntimeError("simulated route-handler bug")


def test_h1_unhandled_exception_in_a_route_handler_gets_the_shaped_500_response() -> None:
    sensor = _RaisingSensorModule("SCD30")
    _, app = _make_service(sensors=[sensor])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 500
    assert json.loads(res.body) == {"res": "ERR", "code": 500, "descr": "Internal server error", "result": {}}


def test_h1_unhandled_exception_is_logged_via_pr_err_s_not_just_swallowed() -> None:
    # ErrNum/ErrType include print_log.py's pre-filled "N" padding ahead of the one real entry
    # (PrintLogHistory.__init__), matching every other get_error_counter()-reading test here
    # rather than being a list-equality check against the raw history.
    sensor = _RaisingSensorModule("SCD30")
    service, app = _make_service(sensors=[sensor])
    run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    log = run(service.get_error_counter())
    entry = log["WEBSERVER"]
    assert entry["ErrCount"] == 1
    assert entry["ErrNum"].count(4) == 1
    assert entry["ErrType"].count("E") == 1


def test_h1_a_second_unhandled_exception_from_a_different_route_is_logged_independently() -> None:
    # Confirms the registration is a real per-request catch-all, not a one-shot/latched handler.
    sensor = _RaisingSensorModule("SCD30")
    service, app = _make_service(sensors=[sensor])
    run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    log = run(service.get_error_counter())
    entry = log["WEBSERVER"]
    assert entry["ErrCount"] == 2
    assert entry["ErrNum"].count(4) == 2
    assert entry["ErrType"].count("E") == 2


def test_h1_abort_driven_404_is_unaffected_by_the_catch_all() -> None:
    # HTTPException (abort()) is caught separately by ext/microdot.py's dispatch_request() before
    # its except-Exception branch ever runs - the catch-all above must never fire for it, and the
    # existing shaped 404 (via the status-code handler, section G) must stay exactly as before.
    sensor = _RaisingSensorModule("SCD30")
    service, app = _make_service(sensors=[sensor])
    res = run(app.dispatch_request(_make_request(app, "GET", "/nope-not-a-route", None)))
    assert res.status_code == 404
    assert json.loads(res.body) == {"res": "ERR", "code": 404, "descr": "Not found", "result": {}}
    log = run(service.get_error_counter())
    assert log["WEBSERVER"]["ErrCount"] == 0  # the catch-all above never fired


# H.2 - /status JSON streaming (_get_status()/_build_status_pieces()): one small json.dumps() per
# source instead of one buffer for the whole aggregate. Sections above already cover the resulting
# JSON's shape end to end; these are specific to the streaming mechanism itself.

# Deliberately a plain list of pre-fetched fragments handed to a sync iterator, never an
# `async def ... yield`: that produces a broken runtime object here and segfaults the interpreter
# when driven past an await, as body_iter() would. SPECIFICATION.md Part F.1.


def _const_source(value: "dict[str, Any]") -> "Callable[[], Coroutine[Any, Any, dict[str, Any]]]":
    async def _source() -> "dict[str, Any]":
        return value

    return _source


async def _raising_source() -> "dict[str, Any]":
    raise RuntimeError("simulated status stream source failure")


class _RaisingErrorCounterModule(_FakeModule):
    async def get_error_counter(self) -> "dict[str, Any]":
        raise RuntimeError("simulated get_error_counter failure")


# -- functionality ----------------------------------------------------------------------------


def test_h2_stream_response_is_a_plain_iterator_with_explicit_json_content_type() -> None:
    # Response.__init__'s automatic Content-Type only fires for isinstance(body, (dict, list)) (see
    # ext/microdot.py, confirmed directly) - a non-dict/list body needs it set explicitly or it would
    # silently fall back to Response.default_content_type ("text/plain") once complete() runs.
    _, app = _make_service()
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    assert hasattr(res.body, "__next__")  # a plain sync iterator, not a dict/list/bytes body
    assert not hasattr(res.body, "__anext__")  # never a broken MicroPython "async generator" object
    assert res.headers["Content-Type"] == "application/json; charset=UTF-8"


def test_h2_stream_yields_one_piece_per_top_level_section_not_one_precomputed_buffer() -> None:
    # Proof of the memory property this was built for: the body is genuinely 5 separate pieces (one
    # per top-level key), never one string for the whole aggregate - but also never one piece per
    # punctuation character, measured to cost ~53% throughput via per-write asyncio.wait_for().
    _service, app = _make_service(
        status_sources={"networking": _const_source({"A": 1})},
        maintenance_sensors=[("SGP40", _const_source({"BackupTS": 1}))],
        error_sources=[_FakeModule("SGP40")],
        history_length=0,  # this service's own real PrintLogHistory (its "WEBSERVER" errcount entry)
        # otherwise pre-fills a fixed-size ring buffer with placeholder entries by default - unrelated
        # to this test, kept at zero so the expected shape below is exact.
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    chunks = list(res.body)
    assert len(chunks) == 5  # more than one - a single json.dumps() body would be exactly one - but
    # deliberately not one per punctuation character either
    joined = b"".join(c.encode() if isinstance(c, str) else c for c in chunks)
    assert json.loads(joined) == {
        "networking": {"A": 1},
        "system": {},
        "notification": {},
        "sensors": {"SGP40": {"BackupTS": 1}},
        "errcount": {"SGP40": {"counter": 0, "history": []}, "WEBSERVER": {"counter": 0, "history": []}},
    }


def test_h2_stream_response_has_an_explicit_correct_content_length_header() -> None:
    # Response.complete() only auto-sets Content-Length for a bytes body, so _get_status() sets it
    # explicitly - the full size is known once every source has been awaited. Without it,
    # digital_twin/_http_client.py's fetch() falls back to a slow read(-1)-until-EOF path.
    service, _app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert b" 200 " in writer.written
    assert b"Connection: close" in writer.written
    header_block, _, sent_body = writer.written.partition(b"\r\n\r\n")
    match = None
    for line in header_block.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            match = int(line.split(b":", 1)[1].strip())
    assert match is not None, "Content-Length header missing from a real, fully-written /status response"
    assert match == len(sent_body)


# -- stability / resilience --------------------------------------------------------------------


def test_h2_stream_status_source_failure_yields_an_error_marker_not_a_broken_stream() -> None:
    service, app = _make_service(status_sources={"networking": _raising_source})
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert set(body.keys()) == {"networking", "system", "sensors", "notification", "errcount"}
    assert body["networking"] == {"error": "unavailable"}
    log = run(service.get_error_counter())
    assert log["WEBSERVER"]["ErrNum"].count(6) == 1
    assert log["WEBSERVER"]["ErrType"][log["WEBSERVER"]["ErrNum"].index(6)] == "E"


def test_h2_stream_maintenance_source_failure_is_isolated_to_that_one_sensor() -> None:
    _service, app = _make_service(
        maintenance_sensors=[("SGP40", _raising_source), ("BMP3XX", _const_source({"BackupTS": 1}))],
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body["sensors"]["SGP40"] == {"error": "unavailable"}
    assert body["sensors"]["BMP3XX"] == {"BackupTS": 1}  # a sibling source's failure never leaks into this one


def test_h2_stream_errcount_source_failure_is_isolated_to_that_one_module() -> None:
    good = _FakeModule("BMP3XX")
    bad = _RaisingErrorCounterModule("SGP40")
    _service, app = _make_service(error_sources=[good, bad], history_length=0)  # see
    # test_h2_stream_yields_many_small_chunks_not_one_precomputed_buffer()'s own comment on why
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["SGP40"] == {"error": "unavailable"}
    assert errcount["BMP3XX"] == {"counter": 0, "history": []}
    # WEBSERVER's counter reflects the SGP40 failure just logged (errno=6) - that failure genuinely
    # happened and belongs in this service's own history too. history_length=0 above keeps the ring
    # at zero capacity, so the detail entry never lands in "history".
    assert errcount["WEBSERVER"]["counter"] == 1
    assert errcount["WEBSERVER"]["history"] == []


def test_h2_stream_own_webserver_errcount_source_failure_yields_an_error_marker() -> None:
    service, app = _make_service()

    async def _raise() -> "dict[str, Any]":
        raise RuntimeError("simulated own-log read failure")

    service.pr.get_log = _raise  # type: ignore[assignment]
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["WEBSERVER"] == {"error": "unavailable"}


def test_h2_stream_every_source_failing_still_produces_one_complete_valid_json_document() -> None:
    # The worst case this design has to survive: every data source misbehaves and the response must
    # still be one complete, parseable JSON document with a plain 200 - each source's own
    # try/except in _write_guarded() keeps its exception from escaping _build_status_pieces().
    _service, app = _make_service(
        status_sources={"networking": _raising_source, "system": _raising_source, "notification": _raising_source},
        maintenance_sensors=[("SGP40", _raising_source)],
        error_sources=[_RaisingErrorCounterModule("BMP3XX")],
        history_length=0,  # see test_h2_stream_yields_many_small_chunks_not_one_precomputed_buffer()'s
        # own comment on why
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    assert res.status_code == 200  # no per-source failure ever escapes far enough to change this
    body = json.loads(status_body(res))
    assert body["networking"] == body["system"] == body["notification"] == {"error": "unavailable"}
    assert body["sensors"]["SGP40"] == {"error": "unavailable"}
    assert body["errcount"]["BMP3XX"] == {"error": "unavailable"}
    # WEBSERVER's own entry is never itself an "error" marker (its get_log() never raised here);
    # its counter instead reflects the 5 other failures just logged - 3 status sources, 1
    # maintenance sensor, 1 errcount module, each its own errno=6 call.
    assert body["errcount"]["WEBSERVER"]["counter"] == 5
    assert body["errcount"]["WEBSERVER"]["history"] == []  # history_length=0 above, see comment above


# -- maximum achievable coverage ----------------------------------------------------------------


def test_h2_stream_empty_registration_everywhere_matches_the_old_all_empty_shape() -> None:
    _service, app = _make_service(sensors=[], settings={}, maintenance_sensors=[], error_sources=[], history_length=0)  # see
    # test_h2_stream_yields_many_small_chunks_not_one_precomputed_buffer()'s own comment on why
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body == {
        "networking": {},
        "system": {},
        "notification": {},
        "sensors": {},
        "errcount": {"WEBSERVER": {"counter": 0, "history": []}},
    }


def test_h2_stream_two_maintenance_sensors_produce_valid_json_with_no_stray_commas() -> None:
    _service, app = _make_service(
        maintenance_sensors=[("SGP40", _const_source({"A": 1})), ("BMP3XX", _const_source({"B": 2}))],
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body["sensors"] == {"SGP40": {"A": 1}, "BMP3XX": {"B": 2}}


def test_h2_stream_two_error_sources_plus_the_own_entry_produce_valid_json_with_no_stray_commas() -> None:
    _service, app = _make_service(error_sources=[_FakeModule("SGP40"), _FakeModule("BMP3XX")])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert set(errcount.keys()) == {"SGP40", "BMP3XX", "WEBSERVER"}


def test_h2_stream_module_names_with_special_characters_are_correctly_escaped() -> None:
    # Names go through json.dumps(name), never hand-rolled string concatenation - that is what
    # keeps an unusual name from corrupting the surrounding document.
    tricky = _FakeModule('SGP"40')
    _service, app = _make_service(error_sources=[tricky])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert set(errcount.keys()) == {'SGP"40', "WEBSERVER"}


_HAMMER_PIECE_BUDGET = 256  # the firmware's chunk_bytes default, restated: a const() is not a
# module attribute, so it cannot be imported. No margin - pieces are bounded by the cap itself.


def test_h2_stream_many_error_sources_are_coalesced_into_size_bounded_batches_not_one_growing_blob() -> None:
    # Real-hardware finding: 17 registered modules joined into one "errcount" piece reached ~4.9KB
    # - nearly the whole pre-streaming aggregate, and enough to cause a reproducible MemoryError.
    # Simulates that scale and checks the _PieceWriter splits it into bounded pieces.
    modules = []
    for i in range(20):
        m = _FakeModule(f"MODULE{i}")
        m.pr.err_count = 10
        m.pr.history = [(1, "E")] * 10
        modules.append(m)
    _service, app = _make_service(error_sources=modules, history_length=0)
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    chunks = list(res.body)
    encoded = [c.encode() if isinstance(c, str) else c for c in chunks]
    # Exactly the cap, no margin: every fragment here is far smaller than it, so any piece above it
    # means a whole module entry was built as one string again (SPECIFICATION.md Part I.3).
    assert all(len(c) <= _HAMMER_PIECE_BUDGET for c in encoded), [len(c) for c in encoded]
    assert len(chunks) > 5  # proof the errcount section really did split into multiple pieces
    body = json.loads(b"".join(encoded))
    assert len(body["errcount"]) == 21  # 20 fake modules + this service's own WEBSERVER entry
    for i in range(20):
        assert body["errcount"][f"MODULE{i}"] == {"counter": 10, "history": [{"num": 1, "type": "E"}] * 10}


def _errcount_log(name: str, count: int, nums: "list[int]", types: "list[str]") -> "dict[str, Any]":
    return {name: {"ErrCount": count, "ErrNum": nums, "ErrType": types}}


def _written(value: object, max_bytes: int = 256) -> "list[str]":
    pieces: list[str] = []
    writer = _PieceWriter(pieces, max_bytes=max_bytes)
    writer.add_value(value)
    writer.flush()
    return pieces


def test_h2_add_value_is_byte_identical_to_json_dumps() -> None:
    # The whole fix rests on this: MicroPython's OWN json.dumps() text - key order, ", "/": "
    # separators, escaping, float repr - reproduced by walking the value instead of dumping it.
    values: list[object] = [
        None, True, False, 0, -3, 12345678, 1.5, -0.25, 1e-7, "", "plain", 'q"x\\y\n\u00e9', [], {}, (), [[]], {"a": {}},
        [1, "two", None, 2.5, [3, [4, {"five": 5}]]],
        (1, (2, 3)),
        {"GainMeas": None, "CCT": None, "RGB": {"G": None, "B": 0.5, "R": 1}, "Lux": 12.25, "Flags": [True, False]},
        {1: 2, "k": {"nested": [{"deep": [1, 2, {"deeper": "yes"}]}]}},
        {True: 1, None: 2, 1.5: 3, -3: 4, (1, 2): 5, 'a"b': 6},  # json.dumps()'s own non-str key rule
    ]
    values.extend(
        _shape_errcount_entry(_errcount_log("M", count, [(i * 37) % 991 - 3 for i in range(length)], [kinds[i % len(kinds)] for i in range(length)]), "M")
        for count in (0, 1, 12345)
        for length in (0, 1, 10, 17)
        for kinds in (("N",), ("E", "W"), ('q"x', "\\", "E"))
    )
    for value in values:
        assert "".join(_written(value)) == json.dumps(value), value


def test_h2_add_value_bounds_every_piece_however_large_the_value() -> None:
    # A value far larger than the cap - the case one json.dumps() per value turned into one large
    # allocation per value - comes out in pieces no larger than the cap.
    big = {f"Sensor{i}": {"Reading": i * 1.5, "History": [{"num": n, "type": "E"} for n in range(12)]} for i in range(8)}
    pieces = _written(big, max_bytes=128)
    assert "".join(pieces) == json.dumps(big)
    assert max(len(p) for p in pieces) <= 128, [len(p) for p in pieces]
    assert len(pieces) > len(json.dumps(big)) // 128


def test_h2_errcount_entry_is_never_one_string() -> None:
    # The allocation this bounds on silicon: a whole 10-element entry is ~290 B, above the holes a
    # loaded heap keeps at gc.threshold(-1) (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.3).
    entry = _shape_errcount_entry(_errcount_log("M", 10, list(range(90, 100)), ["E"] * 10), "M")
    pieces = _written(entry, max_bytes=64)
    assert "".join(pieces) == json.dumps(entry)
    assert max(len(p) for p in pieces) <= 64


def test_h2_piece_writer_bounds_every_piece_and_never_splits_a_fragment() -> None:
    fragments = ["a" * n for n in (5, 100, 120, 30, 256, 1, 300, 7, 7)]
    pieces: list[str] = []
    writer = _PieceWriter(pieces, max_bytes=256)
    for fragment in fragments:
        writer.add(fragment)
    writer.flush()
    assert "".join(pieces) == "".join(fragments)
    # A fragment larger than the cap stands alone rather than being cut; everything else fits it.
    assert [len(p) for p in pieces] == [255, 256, 1, 300, 14]


def test_h2_piece_writer_never_holds_more_than_sixteen_pending_fragments() -> None:
    # Streamed values arrive as many tiny fragments (", ", ": ", single digits); left to grow, the
    # pending list's own array would be as large as the piece - the allocation the writer bounds.
    pieces: list[str] = []
    writer = _PieceWriter(pieces, max_bytes=256)
    fragments = [", ", "1", ": ", '"k"'] * 200
    for fragment in fragments:
        writer.add(fragment)
        assert len(writer._group) <= 16, len(writer._group)
    writer.flush()
    assert "".join(pieces) == "".join(fragments)
    assert max(len(p) for p in pieces) <= 256
    assert min(len(p) for p in pieces[:-1]) > 200  # still full pieces, not one per 16 fragments


def test_h2_piece_writer_flush_is_idempotent_and_an_empty_writer_adds_nothing() -> None:
    pieces: list[str] = []
    writer = _PieceWriter(pieces, _WIRE_CHUNK_BYTES)
    writer.flush()
    writer.add("x")
    writer.flush()
    writer.flush()
    assert pieces == ["x"]


# -- H.3: gc.threshold() companions to the real-hardware hammer-load investigation ---------------
#
# Unit-tier companions to the real-hardware hammer-load investigation: the same 5-concurrent-client
# pattern that produced 237 real MemoryErrors on real hardware before the streaming fix and 0
# after. A Unix-port heap can never reproduce an embedded-scale MemoryError - these are guards.

# Both gc settings are exercised: MicroPython's own real default, and the project owner's chosen
# gc.threshold(32768). That setting is process-global (py/modgc.c has no per-object/per-task
# scoping), so every test below saves and restores the value it finds already set.


def _make_hammer_service() -> "tuple[WebserverService, Microdot]":
    modules = []
    for i in range(17):  # matches the real registered-module count found on real hardware
        m = _FakeModule(f"MODULE{i}")
        m.pr.err_count = 5
        m.pr.history = [(1, "E")] * 5
        modules.append(m)
    return _make_service(
        status_sources={"networking": _const_source({"A": 1}), "system": _const_source({"B": 2})},
        maintenance_sensors=[("SGP40", _const_source({"BackupTS": 1}))],
        error_sources=modules,
        history_length=0,
    )


async def _hammer_status(app: "Microdot", n: int) -> None:
    async def _one() -> None:
        res = await app.dispatch_request(_make_request(app, "GET", "/status", None))
        # _assert_body_is_bounded_stream() (defined below) also confirms res.body is a genuinely
        # bounded stream: status_body()/drain_json_response_body() tolerates either body shape, so
        # this test alone would still pass with /status's streaming reverted to one plain dict.
        body = json.loads(_assert_body_is_bounded_stream(res, "/status"))
        assert set(body.keys()) == {"networking", "system", "notification", "sensors", "errcount"}
        assert len(body["errcount"]) == 18  # 17 fake modules + this service's own WEBSERVER entry

    await asyncio.gather(*(_one() for _ in range(n)))


def test_h3_hammer_concurrent_status_requests_stay_valid_with_gc_threshold_unset() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(-1)  # MicroPython's own real default (confirmed directly - no proactive collection)
    try:
        _, app = _make_hammer_service()
        run(_hammer_status(app, 200))
    finally:
        gc.threshold(orig_threshold)


def test_h3_hammer_concurrent_status_requests_stay_valid_with_the_chosen_gc_threshold() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(32768)  # the project owner's chosen value, see this section's own comment above
    try:
        _, app = _make_hammer_service()
        run(_hammer_status(app, 200))
    finally:
        gc.threshold(orig_threshold)


# -- I: _stream_dict_response() - the shared streaming primitive generalizing H.2's /status
# mitigation to every other dict-shaped GET route (CLAUDE.md's memory-safety hard rule,
# SPECIFICATION.md Part I). Those routes used to let Microdot json.dumps() the whole dict.

# I.1 exercises the shared primitive directly; I.2/I.3 hammer the newly-streamed routes the way
# H.3 hammers /status - Unix-port correctness guards, never an embedded-scale reproduction.


def test_i1_empty_dict_produces_the_same_valid_empty_object_as_plain_json_dumps() -> None:
    res = run(_stream_dict_response({}, _WIRE_CHUNK_BYTES))
    assert json.loads(status_body(res)) == {}


def test_i1_output_is_byte_identical_to_microdots_own_single_json_dumps_path() -> None:
    # The whole point of this primitive: identical JSON on the wire, just assembled without ever
    # holding one buffer sized to the full aggregate (see _stream_dict_response()'s own comment).
    result = {"A": 1, "B": {"nested": True}, "C": [1, 2, 3], "D": None}
    streamed = run(_stream_dict_response(result, _WIRE_CHUNK_BYTES))
    plain = Response(result)  # Microdot's own dict path - one json.dumps() over the whole thing
    assert json.loads(status_body(streamed)) == json.loads(plain.body)


def test_i1_sets_content_type_and_an_exact_content_length_header() -> None:
    res = run(_stream_dict_response({"A": 1}, _WIRE_CHUNK_BYTES))
    assert res.headers["Content-Type"] == "application/json; charset=UTF-8"
    body = status_body(res)
    assert res.headers["Content-Length"] == str(len(body))


def test_i1_many_entries_are_coalesced_into_size_bounded_batches_not_one_growing_blob() -> None:
    # Mirrors H.2's identical proof for /status's own "errcount" section - same _PieceWriter
    # mechanism, applied here to a flat top-level dict instead of /status's own nested section.
    result = {f"Field{i}": "x" * 100 for i in range(30)}  # ~30*(11+100) bytes, several times over
    # chunk_bytes if joined into one piece
    res = run(_stream_dict_response(result, _WIRE_CHUNK_BYTES))
    chunks = list(res.body)
    encoded = [c.encode() if isinstance(c, str) else c for c in chunks]
    assert all(len(c) < 1200 for c in encoded), [len(c) for c in encoded]
    assert len(chunks) > 1  # proof it really did split into multiple pieces
    assert json.loads(b"".join(encoded)) == result


def test_i1_a_two_level_measurement_value_serialises_correctly_and_is_not_re_wrapped() -> None:
    # asy_isl29125_driver.py is the first driver whose measurement body nests a level deeper, and
    # _stream_dict_response() does one json.dumps() per TOP-LEVEL value - so a nested value must
    # come through intact and exactly once, neither flattened nor double-encoded.
    result = {
        "ISL29125": {
            "Lux": 123.45,
            "RGB": {"R": 0.1234, "G": 0.2345, "B": 0.3456},
            "HSB": {"H": 217.4, "S": 0.512, "B": 0.3456},
            "CCT": None,
            "RangeAct": 10000,
            "TS": 1789230685,
        },
    }
    # status_body() drains res.body, which is a generator - read it once, assert on the result.
    body = json.loads(status_body(run(_stream_dict_response(result, _WIRE_CHUNK_BYTES))))
    assert body == result
    assert isinstance(body["ISL29125"]["RGB"], dict)  # a dict, not the string '{"R": 0.1234, ...}'
    assert body == json.loads(Response(result).body)  # byte-for-byte Microdot's own dict path


def test_i1_a_key_with_special_characters_is_correctly_escaped_not_hand_concatenated() -> None:
    result = {'Weird"Key': 1}
    res = run(_stream_dict_response(result, _WIRE_CHUNK_BYTES))
    assert json.loads(status_body(res)) == result




def _assert_body_is_bounded_stream(res: "Response", path: str) -> bytes:
    # status_body()/drain_json_response_body() accepts both a streamed and a single-json.dumps()
    # body so pre-existing tests need no branching - which means a route reverted to `return
    # result` still passes every other hammer test here. Hence this explicit check.

    # res.body must be a real streamed iterator, never a plain str/bytes, and every piece it yields
    # must stay under the same per-piece budget _stream_dict_response() itself enforces.
    body = res.body
    assert not isinstance(body, (str, bytes)), f"{path}: response body is not a streamed iterator (regressed to a single json.dumps() aggregate)"
    chunks = []
    for chunk in body:
        encoded = chunk.encode() if isinstance(chunk, str) else chunk
        assert len(encoded) <= _HAMMER_PIECE_BUDGET, f"{path}: piece of {len(encoded)} bytes exceeds the per-piece budget"
        chunks.append(encoded)
    return b"".join(chunks)


# -- I.2: hammer /measurements and /sensors specifically - the project owner's own named top
# candidate, since sensor-module configuration varies per device and its final size is not
# foreseeable - at the real registered-module count found on real hardware (17, H.3's own scale).


def _make_sensor_hammer_service() -> "tuple[WebserverService, Microdot]":
    modules = [_NestedCfgModule(f"SENSOR{i}", values={"Interval": 5, "Offset": 0}, data={"Value": i}) for i in range(17)]
    return _make_service(sensors=modules, history_length=0)


async def _hammer_route(app: "Microdot", path: str, n: int, expected_keys: "set[str]") -> None:
    async def _one() -> None:
        res = await app.dispatch_request(_make_request(app, "GET", path, None))
        assert res.status_code == 200, path
        body = json.loads(_assert_body_is_bounded_stream(res, path))
        assert set(body.keys()) == expected_keys

    await asyncio.gather(*(_one() for _ in range(n)))


_SENSOR_HAMMER_KEYS = {f"SENSOR{i}" for i in range(17)}


def test_i2_hammer_concurrent_measurements_requests_stay_valid_with_gc_threshold_unset() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(-1)  # MicroPython's own real default (confirmed directly - no proactive collection)
    try:
        _, app = _make_sensor_hammer_service()
        run(_hammer_route(app, "/measurements", 200, _SENSOR_HAMMER_KEYS))
    finally:
        gc.threshold(orig_threshold)


def test_i2_hammer_concurrent_measurements_requests_stay_valid_with_the_chosen_gc_threshold() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(32768)  # the project owner's chosen value, see H.3's own comment above
    try:
        _, app = _make_sensor_hammer_service()
        run(_hammer_route(app, "/measurements", 200, _SENSOR_HAMMER_KEYS))
    finally:
        gc.threshold(orig_threshold)


def test_i2_hammer_concurrent_sensors_requests_stay_valid_with_gc_threshold_unset() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(-1)
    try:
        _, app = _make_sensor_hammer_service()
        run(_hammer_route(app, "/sensors", 200, _SENSOR_HAMMER_KEYS))
    finally:
        gc.threshold(orig_threshold)


def test_i2_hammer_concurrent_sensors_requests_stay_valid_with_the_chosen_gc_threshold() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(32768)
    try:
        _, app = _make_sensor_hammer_service()
        run(_hammer_route(app, "/sensors", 200, _SENSOR_HAMMER_KEYS))
    finally:
        gc.threshold(orig_threshold)


# -- I.2b: /networking, /system, /notification each get the same dedicated per-hotspot hammer as
# /measurements and /sensors above; the combined I.3 set below is additional, not a substitute.
# Stressed at 17 groups so this set doesn't depend on today's small real field counts staying so.


def _make_settings_hammer_service(endpoint: str) -> "tuple[WebserverService, Microdot, set[str]]":
    # _get_settings_flat() merges every group's fields into one flat top-level dict with no
    # per-group namespacing (matching real production wiring), so each group here must contribute
    # distinct field names or later groups would overwrite earlier ones.
    groups = [
        SettingsGroup(_FakeModule(f"GROUP{i}", values={f"F{i}A": i, f"F{i}B": 0}), (f"F{i}A", f"F{i}B")) for i in range(17)
    ]
    service, app = _make_service(settings={endpoint: groups})
    return service, app, {f"F{i}{s}" for i in range(17) for s in ("A", "B")}


async def _hammer_settings_route(app: "Microdot", path: str, n: int, expected_key_count: int) -> None:
    async def _one() -> None:
        res = await app.dispatch_request(_make_request(app, "GET", path, None))
        assert res.status_code == 200, path
        body = json.loads(_assert_body_is_bounded_stream(res, path))
        assert len(body) == expected_key_count, path  # every group's fields present exactly once

    await asyncio.gather(*(_one() for _ in range(n)))


def _run_settings_hammer(endpoint: str, path: str, threshold: int) -> None:
    orig_threshold = gc.threshold()
    gc.threshold(threshold)
    try:
        _, app, keys = _make_settings_hammer_service(endpoint)
        run(_hammer_settings_route(app, path, 200, len(keys)))
    finally:
        gc.threshold(orig_threshold)


def test_i2b_hammer_concurrent_networking_requests_stay_valid_with_gc_threshold_unset() -> None:
    _run_settings_hammer("networking", "/networking", -1)


def test_i2b_hammer_concurrent_networking_requests_stay_valid_with_the_chosen_gc_threshold() -> None:
    _run_settings_hammer("networking", "/networking", 32768)


def test_i2b_hammer_concurrent_system_requests_stay_valid_with_gc_threshold_unset() -> None:
    _run_settings_hammer("system", "/system", -1)


def test_i2b_hammer_concurrent_system_requests_stay_valid_with_the_chosen_gc_threshold() -> None:
    _run_settings_hammer("system", "/system", 32768)


def test_i2b_hammer_concurrent_notification_requests_stay_valid_with_gc_threshold_unset() -> None:
    _run_settings_hammer("notification", "/notification", -1)


def test_i2b_hammer_concurrent_notification_requests_stay_valid_with_the_chosen_gc_threshold() -> None:
    _run_settings_hammer("notification", "/notification", 32768)


# -- I.3: every memory-bounded GET route hammered concurrently for longer, maxing out every
# situation this audit identified at once: 17 sensor modules (measurements/sensors), 17 error
# sources plus this service's own entry (status/errcount), one settings group per flat endpoint.


def _make_combined_hammer_service() -> "tuple[WebserverService, Microdot]":
    sensor_modules = [_NestedCfgModule(f"SENSOR{i}", values={"Interval": 5, "Offset": 0}, data={"Value": i}) for i in range(17)]
    error_modules = []
    for i in range(17):
        m = _FakeModule(f"MODULE{i}")
        m.pr.err_count = 5
        m.pr.history = [(1, "E")] * 5
        error_modules.append(m)
    net_mod = _FakeModule("WIFI", schema=(("SSID", "str", "", 0, 32, None),), values={"SSID": "MyNet"})
    sys_mod = _FakeModule("SYSTEM", schema=(("DebugLevel", "int", 0, 0, 5, None),), values={"DebugLevel": 2})
    notif_mod = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    return _make_service(
        sensors=sensor_modules,
        settings={
            "networking": [SettingsGroup(net_mod, ("SSID",))],
            "system": [SettingsGroup(sys_mod, ("DebugLevel",))],
            "notification": [SettingsGroup(notif_mod, ("OnH",))],
        },
        status_sources={"networking": _const_source({"A": 1}), "system": _const_source({"B": 2})},
        maintenance_sensors=[("SGP40", _const_source({"BackupTS": 1}))],
        error_sources=error_modules,
        history_length=0,
    )


_ALL_MEMORY_BOUNDED_GET_ROUTES = ("/status", "/measurements", "/sensors", "/networking", "/system", "/notification")


async def _hammer_all_routes(app: "Microdot", rounds: int) -> None:
    async def _one(path: str) -> None:
        res = await app.dispatch_request(_make_request(app, "GET", path, None))
        assert res.status_code == 200, path
        json.loads(_assert_body_is_bounded_stream(res, path))  # well-formed JSON, no exception, and
        # genuinely streamed in bounded pieces (not a reverted single json.dumps() aggregate)

    await asyncio.gather(*(_one(path) for _ in range(rounds) for path in _ALL_MEMORY_BOUNDED_GET_ROUTES))


def test_i3_hammer_every_memory_bounded_get_route_concurrently_with_gc_threshold_unset() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(-1)
    try:
        _, app = _make_combined_hammer_service()
        run(_hammer_all_routes(app, 40))  # 40 rounds * 6 routes = 240 concurrent requests
    finally:
        gc.threshold(orig_threshold)


def test_i3_hammer_every_memory_bounded_get_route_concurrently_with_the_chosen_gc_threshold() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(32768)
    try:
        _, app = _make_combined_hammer_service()
        run(_hammer_all_routes(app, 40))
    finally:
        gc.threshold(orig_threshold)


# -- I.4: /measurements and /sensors hammered concurrently with a real config write (PUT /sensors)
# in the mix - the unit-level counterpart to tests_hardware/bench/test_memory_stress_bench.py's
# real-hardware GET+write shape, which had no fast CI-run equivalent.

# ConfigManager's own asyncio.Lock already rules out a data race (SPECIFICATION.md Part C.7): this
# checks I.2/I.3's same bounded-stream property with a concurrent writer present, not a race hunt.


def _make_write_hammer_service() -> "tuple[WebserverService, Microdot]":
    modules = [_FakeModule(f"SENSOR{i}") for i in range(17)]
    return _make_service(sensors=modules, history_length=0)


async def _hammer_routes_with_concurrent_writes(app: "Microdot", rounds: int) -> None:
    async def _get_one(path: str) -> None:
        res = await app.dispatch_request(_make_request(app, "GET", path, None))
        assert res.status_code == 200, path
        json.loads(_assert_body_is_bounded_stream(res, path))

    async def _put_one(round_num: int) -> None:
        target = f"SENSOR{round_num % 17}"
        res = await app.dispatch_request(_make_request(app, "PUT", "/sensors", {target: {"Interval": 5 + (round_num % 10)}}))
        assert res.status_code == 200, "/sensors PUT"
        assert json.loads(res.body)["result"] == {target: {"Interval": "Valid"}}

    gets = (_get_one(path) for _ in range(rounds) for path in ("/measurements", "/sensors"))
    puts = (_put_one(i) for i in range(rounds))
    await asyncio.gather(*gets, *puts)


def test_i4_hammer_measurements_and_sensors_concurrently_with_a_real_config_write_with_gc_threshold_unset() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(-1)
    try:
        _, app = _make_write_hammer_service()
        run(_hammer_routes_with_concurrent_writes(app, 40))  # 40 rounds * 2 GET routes + 40 PUTs = 120 concurrent requests
    finally:
        gc.threshold(orig_threshold)


def test_i4_hammer_measurements_and_sensors_concurrently_with_a_real_config_write_with_the_chosen_gc_threshold() -> None:
    orig_threshold = gc.threshold()
    gc.threshold(32768)
    try:
        _, app = _make_write_hammer_service()
        run(_hammer_routes_with_concurrent_writes(app, 40))
    finally:
        gc.threshold(orig_threshold)



# ---------------------------------------------------------------------------
# Section G - the backlog knob and its coupling to max_connections
# (SPECIFICATION.md Part H.7; asyncio.start_server()'s own default is 5)
# ---------------------------------------------------------------------------


def test_backlog_defaults_to_one_above_max_connections() -> None:
    # Derived, not inherited: start_server()'s own default of 5 silently capped the accept queue
    # below any raised ceiling, dropping arrivals inside lwIP where src/ could never see them.
    for ceiling in (1, 3, 4, 7, 12):
        service, _app = _make_service(max_connections=ceiling)
        assert service._backlog == ceiling + 1, ceiling


def test_an_explicit_backlog_is_honoured_when_it_covers_the_ceiling() -> None:
    service, _app = _make_service(max_connections=4, backlog=9)
    assert service._backlog == 9


def test_a_backlog_below_the_ceiling_is_clamped_up_never_left_short() -> None:
    # Clamped rather than raised, matching LockedCounter's own out-of-range convention. buildgen
    # rejects the same mistake in config, where it can be named against the device that made it.
    service, _app = _make_service(max_connections=6, backlog=2)
    assert service._backlog == 6


def test_the_server_passes_its_own_backlog_to_start_server() -> None:
    # The whole point of the knob: inherited, the default of 5 resets the sixth of a burst landing
    # while the loop is busy, so the value has to reach start_server() rather than merely be stored.
    service, _app = _make_service(max_connections=7)
    recorded: dict[str, Any] = {}

    class _FakeServer:
        async def wait_closed(self) -> None:
            return

    async def fake_start_server(cb: "Any", host: str, port: int, backlog: int = 5) -> "_FakeServer":
        recorded["host"], recorded["port"], recorded["backlog"] = host, port, backlog
        return _FakeServer()

    real_start_server = asyncio.start_server
    asyncio.start_server = fake_start_server  # type: ignore[assignment]
    try:
        asyncio.run(service._run())
    finally:
        asyncio.start_server = real_start_server
    assert recorded["backlog"] == 8, recorded


# -- Mutation-found gaps: each test below fails against one specific plausible slip ---------------


def test_h2_piece_writer_keeps_a_piece_that_lands_exactly_on_the_cap_whole() -> None:
    # The cap is inclusive: two fragments summing to exactly max_bytes share one piece, and only
    # the next one starts a new piece - ">=" would split at the cap and double the write count.
    pieces: list[str] = []
    writer = _PieceWriter(pieces, max_bytes=4)
    for fragment in ("ab", "cd", "e"):
        writer.add(fragment)
    writer.flush()
    assert pieces == ["abcd", "e"], pieces


def test_h2_a_tuple_value_is_walked_like_a_list_never_dumped_as_one_string() -> None:
    # json.dumps() renders a tuple as a list, so dumping one whole produces the same text - as a
    # single allocation the size of the value, which is exactly what the writer exists to avoid.
    value = tuple(range(60))
    pieces = _written(value, max_bytes=16)
    assert "".join(pieces) == json.dumps(value)
    assert max(len(p) for p in pieces) <= 16, [len(p) for p in pieces]


def test_a_streamed_bodys_content_length_counts_bytes_not_characters() -> None:
    # A device or sensor name is free text; with any non-ASCII character in it, a character count
    # declares a short body and the client stops reading before the closing brace.
    res = run(_stream_dict_response({"Name": "Wohnzimmer \u00e4\u00f6\u00fc \u20ac"}, _WIRE_CHUNK_BYTES))
    body = status_body(res)
    assert int(res.headers["Content-Length"]) == len(body), (res.headers["Content-Length"], len(body))
    assert len(body) > len(body.decode())
    assert json.loads(body) == {"Name": "Wohnzimmer \u00e4\u00f6\u00fc \u20ac"}


def test_serve_never_swallows_its_own_tasks_cancellation_and_still_frees_the_slot() -> None:
    # A shutdown cancels every connection task; swallowed, the task would end "normally" and
    # whoever cancelled it could never tell - while the slot must be released either way.
    service, app = _make_service(outer_cap_s=10.0)

    async def _hang(_reader: object, _writer: object) -> None:
        await asyncio.Event().wait()

    app.handle_request = _hang
    writer = _ScriptedWriter()

    async def scenario() -> bool:
        task = asyncio.create_task(service._serve(_ScriptedReader([]), writer))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True
        return False

    assert run_timed(scenario()) is True, "the cancellation was swallowed"
    assert writer.close_called is True
    assert run(service._open_conns.get_value()) == 0


def test_a_body_that_never_arrives_is_logged_as_a_read_phase_timeout() -> None:
    # The body is read with readexactly(), not readline(): microdot swallows a timeout there as it
    # does for the headers, so the proxy's own log is the only trace this connection ever leaves.
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=2.0)
    request = _request_bytes("PUT", "/status", b"", {"Content-Length": "10"})
    run_timed(service._serve(_ScriptedReader([(0.0, request)]), _ScriptedWriter()), timeout_s=2.0)
    entry = next(iter(run(service.get_error_counter()).values()))
    assert entry["ErrCount"] == 1, entry
    assert run(service._open_conns.get_value()) == 0


class _ResetDuringBodyReader(_ScriptedReader):
    async def readexactly(self, _n: int) -> bytes:
        raise OSError(104, "ECONNRESET")


def test_nothing_is_written_to_a_peer_that_reset_while_its_body_was_read() -> None:
    # The same peer-gone rule as a reset during the headers, reached through the other read method.
    service, _app = _make_service(per_call_timeout_s=0.05, outer_cap_s=1.0)
    request = _request_bytes("PUT", "/status", b"", {"Content-Length": "10"})
    writer = _ScriptedWriter()
    run_timed(service._serve(_ResetDuringBodyReader([(0.0, request)]), writer), timeout_s=2.0)
    assert writer.written == b"", writer.written
    assert run(service._open_conns.get_value()) == 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())

