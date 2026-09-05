"""Test suite for src/asy_webserver_service.py's WebserverService/SettingsGroup - see SPECIFICATION.md Part A.8 for the full endpoint design and the real class signatures for the current API contract (this file predates the implementation and no longer mirrors it exactly).
GET routes return the bare shaped dict; PUT routes return the existing api_response.py envelope - see SPECIFICATION.md Part A.8 for the PUT-shapes decision. Connection-lifecycle internals are exercised with hand-scripted fake reader/writer doubles, never a real select.poll()."""

import asyncio
import json
import os
import sys

# Same sys.path convention as tests/test_setter_microdot_integration.py (see its own module
# docstring for why: scripts/test.sh's MICROPYPATH deliberately excludes ext/, and extending
# sys.path here reaches the real, vendored ext/microdot.py without touching MICROPYPATH/
# pyproject.toml/scripts/test.sh - a "Pre-push verification" scope change this file must not need.
sys.path.insert(0, "ext")

from _shared_rest_roundtrip import drain_json_response_body  # noqa: E402
from freezefs.ffsmount import VfsFrozen  # type: ignore[import-not-found]  # noqa: E402
from microdot import Microdot, Request  # type: ignore[import-not-found]  # noqa: E402

import config_manager as cm
from asy_webserver_service import SettingsGroup, WebserverService, _TimeoutStreamProxy

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


def status_body(res: "Any") -> bytes:
    # GET /status streams from a plain list of already-json.dumps()-encoded fragments now (see
    # asy_webserver_service.py's _get_status()/_build_status_pieces()) - drains it the way a real
    # client naturally would, so every existing json.loads(...) assertion on a GET /status response
    # keeps working unchanged.
    return drain_json_response_body(res.body)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
    # Same defensive bound as test_asy_uart_driver.py's own run(): section F below deliberately
    # exercises timeout/hang scenarios, so a genuine bug in the implementation under test (or in
    # one of the fakes below) must surface as a fast FAIL, never a silent whole-suite stall.
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# Fakes - registered-module doubles. Deliberately lightweight (not the real drivers): sections A-E
# below test the webserver's own dispatch/aggregation/registration logic, not sensor-specific
# behavior (already covered by each driver's own test file and
# tests/test_setter_microdot_integration.py's real-Microdot end-to-end tests). _set_dict_cfg()
# mirrors config_manager.write_config()'s real per-field Invalid/Valid semantics closely enough to
# be a faithful stand-in (unknown key -> "Invalid", out-of-range -> "Invalid", else -> "Valid").
# ---------------------------------------------------------------------------


class _FakeLogger:
    def __init__(self, name: str) -> None:
        self.name = name
        self.err_count = 0
        self.history: list[tuple[int, str]] = []
        self.reset_calls = 0

    async def err_s(self, *args: "Any", errno: int = 0, **kwargs: "Any") -> None:
        self.err_count += 1
        if errno:
            self.history.append((errno, "E"))

    async def wrn_s(self, *args: "Any", wrnno: int = 0, **kwargs: "Any") -> None:
        self.err_count += 1
        if wrnno:
            self.history.append((wrnno, "W"))

    async def get_log(self) -> "dict[str, dict[str, Any]]":
        return {
            self.name: {
                "ErrCount": self.err_count,
                "ErrNum": [h[0] for h in self.history],
                "ErrType": [h[1] for h in self.history],
            }
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
# Fakes - reader/writer stream doubles standing in for asyncio.Stream, matching every method
# ext/microdot.py's Request.create()/Response.write() actually call (readline, readexactly, awrite,
# aclose, close, wait_closed, get_extra_info) plus what a per-call timeout-wrapping proxy needs to
# forward. Deliberately never backed by a real select.poll()/socket - see the module docstring and
# CLAUDE.md's CI-hang-investigation note for exactly why that's a hard requirement here.
# ---------------------------------------------------------------------------


class _ScriptedReader:
    # Feeds pre-scripted byte chunks to readline()/readexactly(), each preceded by an optional
    # asyncio.sleep(delay) - lets a test simulate a paced/Slowloris client without any real I/O.
    # After the scripted chunks are exhausted, further reads hang forever (never resolve) unless
    # eof=True, in which case they raise EOFError/return b"" - matching real Stream behavior for a
    # clean peer close vs. a genuinely wedged/silent one.
    def __init__(self, chunks: "list[tuple[float, bytes]]", eof: bool = False) -> None:
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

    async def readexactly(self, n: int) -> bytes:
        await asyncio.Event().wait()
        return b""  # unreachable


class _ClosedReader:
    # Opens then immediately closes before sending any bytes - readline() returns empty immediately
    # (matches real Stream.readline()'s no-raise-on-early-close behavior); readexactly() raises
    # EOFError immediately (matches Stream.readexactly()).
    async def readline(self) -> bytes:
        return b""

    async def readexactly(self, n: int) -> bytes:
        raise EOFError


class _ScriptedWriter:
    def __init__(self, hang_close: bool = False, fail_with: "Exception | None" = None) -> None:
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

    def get_extra_info(self, name: str) -> "Any":
        return ("127.0.0.1", 54321) if name == "peername" else None


def _request_bytes(method: str, path: str, body: bytes = b"", extra_headers: "dict[str, str] | None" = None) -> bytes:
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json", "Host": "device.local"}
    if extra_headers:
        headers.update(extra_headers)
    header_lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"{method} {path} HTTP/1.1\r\n{header_lines}\r\n".encode() + body


def _make_service(**kwargs: "Any") -> "tuple[WebserverService, Microdot]":
    app = Microdot()
    kwargs.setdefault("max_content_length", 4096)
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
    # _NestedCfgModule, not _FakeModule - real SCD30/SGP40/BMP3xx drivers' own get_dict_data()
    # always returns the self-wrapped {name: {...}} shape (config_manager.make_dict()), never
    # _FakeModule's flat one. See _NestedCfgModule's own docstring for why this distinction is the
    # whole point of this test, not incidental.
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    sgp = _NestedCfgModule("SGP40", values={}, data={"VOC": 120})
    service, app = _make_service(sensors=[scd, sgp])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(res.body) == {"SCD30": {"CO2": 800}, "SGP40": {"VOC": 120}}


def test_measurements_get_does_not_double_wrap_a_real_self_wrapped_sensor_shape() -> None:
    # Regression test for the real, confirmed production bug _NestedCfgModule's own docstring
    # describes: _get_measurements() used to index the already-self-wrapped get_dict_data() result
    # by name again, producing {"SCD30": {"SCD30": {"CO2": 800}}} for every real sensor.
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    body = json.loads(res.body)
    assert "SCD30" not in body["SCD30"]
    assert body == {"SCD30": {"CO2": 800}}


def test_measurements_get_empty_sensor_list_returns_empty_dict_not_a_crash() -> None:
    service, app = _make_service(sensors=[])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(res.body) == {}


def test_sensors_get_mirrors_measurements_structure_with_cfg_fields() -> None:
    scd = _NestedCfgModule("SCD30", values={"Interval": 10, "Offset": 2})
    service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "GET", "/sensors", None)))
    assert json.loads(res.body) == {"SCD30": {"Interval": 10, "Offset": 2}}


def test_sensors_get_does_not_double_wrap_a_real_self_wrapped_sensor_shape() -> None:
    # Same regression as test_measurements_get_does_not_double_wrap... above, via get_dict_cfg()/
    # _get_sensors() instead of get_dict_data()/_get_measurements().
    scd = _NestedCfgModule("SCD30", values={"Interval": 10, "Offset": 2})
    service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "GET", "/sensors", None)))
    body = json.loads(res.body)
    assert "SCD30" not in body["SCD30"]
    assert body == {"SCD30": {"Interval": 10, "Offset": 2}}


def test_sensors_put_empty_body_is_noop() -> None:
    scd = _FakeModule("SCD30")
    service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {})))
    assert res.status_code == 200
    assert json.loads(res.body)["result"] == {}
    assert scd.set_calls == []


def test_sensors_put_single_field_for_one_sensor() -> None:
    scd = _FakeModule("SCD30")
    sgp = _FakeModule("SGP40")
    service, app = _make_service(sensors=[scd, sgp])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {"SCD30": {"Interval": 10}})))
    body = json.loads(res.body)
    assert body["result"] == {"SCD30": {"Interval": "Valid"}}
    assert run(scd.get_dict_cfg())["Interval"] == 10
    assert sgp.set_calls == []  # untouched sensor never dispatched to


def test_sensors_put_all_fields_for_all_sensors() -> None:
    scd = _FakeModule("SCD30")
    sgp = _FakeModule("SGP40")
    service, app = _make_service(sensors=[scd, sgp])
    body_in = {"SCD30": {"Interval": 10, "Offset": 3}, "SGP40": {"Interval": 20, "Offset": -1}}
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", body_in)))
    body = json.loads(res.body)
    assert body["result"] == {
        "SCD30": {"Interval": "Valid", "Offset": "Valid"},
        "SGP40": {"Interval": "Valid", "Offset": "Valid"},
    }


def test_sensors_put_unknown_sensor_key_ignored() -> None:
    scd = _FakeModule("SCD30")
    service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {"BOGUS": {"Interval": 10}})))
    assert res.status_code == 200
    assert json.loads(res.body)["result"] == {}
    assert scd.set_calls == []


def test_sensors_put_unknown_field_within_known_sensor_reported_invalid_not_whole_request() -> None:
    scd = _FakeModule("SCD30")
    service, app = _make_service(sensors=[scd])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors", {"SCD30": {"Interval": 10, "Bogus": 1}})))
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"SCD30": {"Interval": "Valid", "Bogus": "Invalid"}}


def test_sensors_put_malformed_json_body_is_a_clean_rejection_not_a_crash() -> None:
    scd = _FakeModule("SCD30")
    service, app = _make_service(sensors=[scd])
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
    service, app = _make_service(settings={"networking": [group]})
    res = run(app.dispatch_request(_make_request(app, "GET", "/networking", None)))
    body = json.loads(res.body)
    assert body == {"SSID": "MyNet"}
    assert "Connected" not in body and "IP" not in body and "Rssi" not in body


class _NestedCfgModule:
    # Reproduces config_manager.make_dict()'s real {type_name: {field: value}} shape - the actual
    # shape AsyConnTime/AsyNtpClient/NotificationCoordinator's own get_dict_cfg() returns in
    # production (base_classes.py's SensorReaderConfig default, via ConfigManager.make_dict()),
    # unlike _FakeModule's own deliberately-flat get_dict_cfg() convention above (which matches
    # SystemService's own get_dict_cfg() override instead - see system_service.py's
    # self.cfgmgr.get_dict(...), a genuinely different, already-flat method). Found via
    # twin-based integration testing
    # (tests/test_digital_twin_sensortask_integration.py): _FakeModule's flat shape masked a real
    # bug where _get_settings_flat() never unwrapped this real shape at all, so /networking and
    # /notification always returned {} in production, and /system silently dropped every field not
    # sourced from SystemService's own flat override (DebugLevel) - see the regression test right
    # below.
    #
    # Also doubles as a registered-sensor fake for _get_measurements()/_get_sensors() themselves
    # (get_dict_data() added below, same nested convention) - real SCD30/SGP40/BMP3xx drivers
    # always return this self-wrapped shape for both, never _FakeModule's flat one, and
    # _get_measurements()/_get_sensors() had the identical class of bug _flatten_cfg_values() above
    # was written to fix: indexing the already-self-wrapped result by name again doubled it into
    # {"SCD30": {"SCD30": {...}}} for every real sensor - found via a real user report against the
    # real assembled system, not caught here (this file's own sensor tests used _FakeModule's flat
    # shape) or by tests/test_digital_twin_sensortask_integration.py's own real-HTTP GET test either
    # (that test only checked top-level keys, never the values - both gaps closed alongside this).
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
    service, app = _make_service(settings={"networking": [group]})
    res = run(app.dispatch_request(_make_request(app, "GET", "/networking", None)))
    assert json.loads(res.body) == {"SSID": "MyNet"}


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
    service, app = _make_service(settings={"networking": [net_group, ntp_group]})
    res = run(app.dispatch_request(_make_request(app, "PUT", "/networking", {"SSID": "NewNet"})))
    assert res.status_code == 200
    assert reconnect_calls == [1]
    assert resync_calls == []  # NTP_Host wasn't in this body - its own post_asy_fct must not fire


async def _record_async(sink: "list[int]") -> None:
    sink.append(1)


def test_networking_put_raising_post_fct_marks_every_attempted_field_in_that_group_failed() -> None:
    # Regression test for a real, confirmed gap (SPECIFICATION.md Part H.6's "Server-side
    # settings-group failure" rule, "silent result-swallow"): handle_set_cmd() (api_response.py)
    # discards its already-computed
    # per-field results when post_fct/post_asy_fct raises and returns an empty result dict -
    # _apply_settings_groups() used to just .update() that empty dict in, silently dropping every
    # field the group actually attempted from the overall response, with the top-level envelope
    # still reporting success. Every field in `subset` must now come back explicitly "Failed"
    # instead of vanishing.
    wifi = _FakeModule(
        "WIFI",
        schema=(("SSID", "str", "", 0, 32, None), ("PW", "str", "", 0, 63, None)),
        values={"SSID": "", "PW": ""},
    )

    def _raise() -> None:
        raise RuntimeError("simulated post_fct failure")

    net_group = SettingsGroup(wifi, ("SSID", "PW"), post_fct=_raise)
    service, app = _make_service(settings={"networking": [net_group]})
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
    service, app = _make_service(settings={"system": groups})
    res = run(app.dispatch_request(_make_request(app, "GET", "/system", None)))
    assert json.loads(res.body) == {"DebugLevel": 2, "GMTOffset": 3600, "DSTOffset": 3600}


def test_system_put_settings_only_body_no_systemcmd_takes_no_lifecycle_action() -> None:
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    sysm = _FakeModule("SYSTEM", schema=(("DebugLevel", "int", 0, 0, 5, None),), values={"DebugLevel": 0})
    service, app = _make_service(settings={"system": [SettingsGroup(sysm, ("DebugLevel",))]}, system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"DebugLevel": 3})))
    assert res.status_code == 200
    assert cmd_calls == []


def test_system_put_systemcmd_invalid_value_rejected_without_side_effects() -> None:
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    service, app = _make_service(system_cmd=system_cmd)
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

    service, app = _make_service(system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"SystemCmd": "reboot"})))
    assert res.status_code == 200
    assert cmd_calls == ["reboot"]


def test_system_put_mempause_never_accepts_a_client_supplied_duration() -> None:
    # Confirms the webserver layer only ever forwards the enum string, never a caller-suppliable
    # duration - system_cmd()'s own implementation (SystemService.pause_permanent_storage) is what
    # actually hardcodes the fixed 300s, this test just proves nothing upstream of it leaks a
    # duration field through even if one is present in the body.
    cmd_calls = []

    async def system_cmd(cmd: str) -> bool:
        cmd_calls.append(cmd)
        return True

    service, app = _make_service(system_cmd=system_cmd)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/system", {"SystemCmd": "mempause", "Duration": 9999})))
    assert res.status_code == 200
    assert cmd_calls == ["mempause"]


def test_system_put_systemcmd_raising_callback_returns_failed_not_an_exception() -> None:
    # system_cmd is a caller-supplied callback (like every other such callback in this codebase -
    # e.g. asy_notification_service.py's request_signal_cb) and could legitimately misbehave;
    # previously unguarded here, so a raise would escape all the way out of the route handler
    # instead of degrading to a clean "Failed" result with a persisted, diagnosable errno.
    async def system_cmd(cmd: str) -> bool:
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

    service, app = _make_service(
        status_sources={"networking": net_status, "system": sys_status, "notification": notif_status}
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

    service, app = _make_service(maintenance_sensors=[("SGP40", sgp_maint)])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body["sensors"] == {"SGP40": {"BackupTS": 111, "RestoreTS": 222}}


def test_status_get_sensors_subkey_empty_when_no_maintenance_sensors_registered() -> None:
    service, app = _make_service(maintenance_sensors=[])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    assert json.loads(status_body(res))["sensors"] == {}


def test_status_put_empty_and_false_reset_errors_are_both_noops() -> None:
    mod = _FakeModule("SGP40")
    run(mod.pr.err_s("boom", errno=1))
    service, app = _make_service(error_sources=[mod])
    for body_in in ({}, {"ResetErrors": False}):
        res = run(app.dispatch_request(_make_request(app, "PUT", "/status", body_in)))
        assert res.status_code == 200
    assert mod.pr.reset_calls == 0
    assert mod.pr.err_count == 1


def test_status_put_reset_errors_true_resets_every_module_counter_and_history() -> None:
    mod = _FakeModule("SGP40")
    run(mod.pr.err_s("boom", errno=1))
    service, app = _make_service(error_sources=[mod])
    res = run(app.dispatch_request(_make_request(app, "PUT", "/status", {"ResetErrors": True})))
    assert res.status_code == 200
    assert mod.pr.reset_calls == 1
    assert mod.pr.err_count == 0
    assert mod.pr.history == []


def test_notification_get_is_flat_settings_only_no_live_fields() -> None:
    notif = _FakeModule(
        "NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8}
    )
    service, app = _make_service(settings={"notification": [SettingsGroup(notif, ("OnH",))]})
    res = run(app.dispatch_request(_make_request(app, "GET", "/notification", None)))
    body = json.loads(res.body)
    assert body == {"OnH": 8}
    assert "Triggered" not in body and "TS" not in body and "PauseTime" not in body


def test_notification_put_light_cmd_led_round_trips_independently_of_flat_fields() -> None:
    led_calls = []

    async def notification_led(payload: "dict[str, Any]") -> bool:
        led_calls.append(payload)
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_led=notification_led
    )
    res = run(
        app.dispatch_request(
            _make_request(app, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 5}})
        )
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

    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60})))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Valid"
    assert pause_calls == [60]
    assert notif.set_calls == []  # OnH group never received a body with no matching keys


def test_notification_put_pause_time_reported_invalid_when_no_handler_registered() -> None:
    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(settings={"notification": [SettingsGroup(notif, ("OnH",))]})  # notification_pause=None
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60})))
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Invalid"


def test_notification_put_pause_time_reported_invalid_when_not_an_int() -> None:
    async def notification_pause(secs: int) -> bool:
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause
    )
    for bad_value in ("60", 1.5, True, None):
        res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": bad_value})))
        body = json.loads(res.body)
        assert body["result"]["PauseTime"] == "Invalid"


def test_notification_put_pause_time_accepts_integral_float_coerced_to_int() -> None:
    # Mirror of the fractional-rejected test above, in the accept direction: config_manager.py's
    # coerce_numeric() policy (SPECIFICATION.md Part A.8) accepts an integral float for PauseTime's
    # own synthetic int FieldSchema, and the callback must receive the coerced int, not the raw
    # float - a real client's json.dumps(60.0)-shaped body must not reach notification_pause() as
    # a float when its own signature (and the real coordinator behind it) expects int.
    pause_calls = []

    async def notification_pause(secs: int) -> bool:
        pause_calls.append(secs)
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60.0})))
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Valid"
    assert pause_calls == [60]
    assert type(pause_calls[0]) is int


def test_notification_put_pause_time_reported_invalid_when_out_of_range() -> None:
    # Legacy's own pauseAutoLED command (modules/sensortask-wozi.py, update_valid_json(...,
    # 0, 3600, ...)) rejects an out-of-range pauseTime as Invalid rather than silently clamping it -
    # LockedCounter.set_value() would clamp a too-large/negative value into [0, 3600] without
    # raising, so this dispatcher must reject it itself before ever calling the callback, the same
    # way every other numeric field in this codebase is range-checked server-side regardless of
    # what a client sends (config_manager.py's own type_or_range_error()).
    pause_calls = []

    async def notification_pause(secs: int) -> bool:
        pause_calls.append(secs)
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause
    )
    for bad_value in (-1, 3601):
        res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": bad_value})))
        body = json.loads(res.body)
        assert body["result"]["PauseTime"] == "Invalid"
    assert pause_calls == []  # the callback must never see an out-of-range value


def test_notification_put_pause_time_raising_callback_returns_failed_not_an_exception() -> None:
    # notification_pause is a caller-supplied callback and could legitimately misbehave, the same as
    # system_cmd/notification_led (see their own identical raising-callback tests above).
    async def notification_pause(secs: int) -> bool:
        raise RuntimeError("simulated notification_pause failure")

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_pause=notification_pause
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"PauseTime": 60})))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"]["PauseTime"] == "Failed"
    assert service.pr.err_count == 1


def test_notification_put_light_cmd_led_reported_invalid_when_no_handler_registered() -> None:
    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(settings={"notification": [SettingsGroup(notif, ("OnH",))]})  # notification_led=None
    res = run(
        app.dispatch_request(
            _make_request(app, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 5}})
        )
    )
    body = json.loads(res.body)
    assert body["result"]["lightCmdLED"] == "Invalid"


def test_notification_put_light_cmd_led_reported_invalid_when_payload_is_not_a_dict() -> None:
    async def notification_led(payload: "dict[str, Any]") -> bool:
        return True

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_led=notification_led
    )
    res = run(app.dispatch_request(_make_request(app, "PUT", "/notification", {"lightCmdLED": "not-a-dict"})))
    body = json.loads(res.body)
    assert body["result"]["lightCmdLED"] == "Invalid"


def test_notification_put_light_cmd_led_raising_callback_returns_failed_not_an_exception() -> None:
    # notification_led is a caller-supplied callback and could legitimately misbehave, the same as
    # system_cmd (see test_system_put_systemcmd_raising_callback_returns_failed_not_an_exception's
    # own comment) - previously unguarded here too.
    async def notification_led(payload: "dict[str, Any]") -> bool:
        raise RuntimeError("simulated notification_led failure")

    notif = _FakeModule("NOTIF", schema=(("OnH", "int", 8, 0, 23, None),), values={"OnH": 8})
    service, app = _make_service(
        settings={"notification": [SettingsGroup(notif, ("OnH",))]}, notification_led=notification_led
    )
    res = run(
        app.dispatch_request(
            _make_request(app, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 5}})
        )
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
        service, app, mod = _settings_service(endpoint)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/" + endpoint, {"Interval": 10})))
        assert res.status_code == 200, endpoint
        assert run(mod.get_dict_cfg())["Offset"] == 0, endpoint  # untouched, not reset to default


def test_b_unknown_top_level_key_silently_ignored_on_every_settings_endpoint() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        service, app, mod = _settings_service(endpoint)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/" + endpoint, {"Bogus": 1})))
        assert res.status_code == 200, endpoint
        body = json.loads(res.body)
        assert "Bogus" not in body.get("result", {}), endpoint


def test_b_wrong_top_level_json_type_is_a_clean_rejection_on_every_settings_endpoint() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        service, app, mod = _settings_service(endpoint)
        for bad_body in ([1, 2, 3], "a string", 42, None):
            req = _make_request(app, "PUT", "/" + endpoint, None)
            req._body = json.dumps(bad_body).encode()
            req.content_length = len(req._body)
            res = run(app.dispatch_request(req))
            assert res.status_code == 200, (endpoint, bad_body)  # our own precise ERR envelope, not a raised exception
            assert json.loads(res.body)["res"] == "ERR", (endpoint, bad_body)


def test_b_wrong_type_for_a_known_field_is_a_per_field_rejection_others_still_apply() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        service, app, mod = _settings_service(endpoint)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/" + endpoint, {"Interval": "not-an-int", "Offset": 5})))
        body = json.loads(res.body)
        assert body["result"] == {"Interval": "Invalid", "Offset": "Valid"}, endpoint
        assert run(mod.get_dict_cfg())["Offset"] == 5, endpoint


def test_b_malformed_json_body_handled_like_the_legacy_parse_cmd_request_path() -> None:
    for endpoint in _SETTINGS_ENDPOINTS:
        service, app, mod = _settings_service(endpoint)
        req = _make_request(app, "PUT", "/" + endpoint, {})
        req._body = b"{not valid json"
        req.content_length = len(req._body)
        res = run(app.dispatch_request(req))
        assert res.status_code == 200, endpoint
        assert json.loads(res.body) == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}, endpoint


def test_b_duplicate_keys_in_raw_json_text_last_wins() -> None:
    # MicroPython's json module deserializes the same way CPython's does for a duplicate-key
    # object literal - confirmed directly against the pinned interpreter, not assumed.
    service, app, mod = _settings_service("networking")
    req = _make_request(app, "PUT", "/networking", {})
    req._body = b'{"Interval": 1, "Interval": 10}'
    req.content_length = len(req._body)
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    assert run(mod.get_dict_cfg())["Interval"] == 10


def test_b_deeply_nested_json_body_degrades_to_a_clean_rejection_not_a_hard_fault() -> None:
    # Corrected during implementation: building the nested structure as a real Python object and
    # then calling json.dumps() on it (the original approach) recurses exactly as deeply as the
    # json.loads() this test means to exercise - it blew the interpreter's own recursion limit in
    # this test's own setup code, before ever reaching request.json/_body_as_dict(). Building the
    # raw JSON text directly via string repetition sidesteps that entirely: no recursive Python call
    # is involved in constructing the bytes, only json.loads() (inside the code under test) ever
    # walks this structure recursively.
    service, app, mod = _settings_service("system")
    depth = 2000  # deep enough to matter on an embedded stack; MicroPython's json.loads recursion
    # bound is confirmed well under this by direct testing against the pinned interpreter (raises
    # RecursionError/ValueError, not a hard interpreter fault).
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
    service, app, mod = _settings_service("networking")
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
    service, app = _make_service(sensors=[], settings={}, maintenance_sensors=[], error_sources=[])
    for path in ("/measurements", "/sensors", "/status"):
        res = run(app.dispatch_request(_make_request(app, "GET", path, None)))
        assert res.status_code == 200, path
        json.loads(status_body(res))  # well-formed JSON, no exception


def test_c_one_entry_behaves_identically_to_a_hand_constructed_single_item_list() -> None:
    single = _NestedCfgModule("SCD30", values={}, data={"CO2": 900})
    service, app = _make_service(sensors=[single])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert json.loads(res.body) == {"SCD30": {"CO2": 900}}


def test_c_duplicate_registration_last_registration_wins() -> None:
    first = _NestedCfgModule("SCD30", values={}, data={"CO2": 111})
    second = _NestedCfgModule("SCD30", values={}, data={"CO2": 222})
    service, app = _make_service(sensors=[first, second])
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert json.loads(res.body) == {"SCD30": {"CO2": 222}}


# ---------------------------------------------------------------------------
# Section D - error aggregation / reset tests.
# ---------------------------------------------------------------------------


def test_d_status_errcount_includes_one_entry_per_module_and_per_configmanager() -> None:
    module = _FakeModule("SGP40")
    cfgmgr = _FakeModule("CFGMGR_SGP40")
    service, app = _make_service(error_sources=[module, cfgmgr])
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
    service, app = _make_service(error_sources=[quiet, noisy_free])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["QUIET"]["counter"] == 1
    assert errcount["QUIET"]["history"] == [{"num": 3, "type": "E"}]
    assert errcount["FREE"]["counter"] == 0
    assert errcount["FREE"]["history"] == []


def test_d_reset_errors_calls_reset_error_counter_on_every_registered_module() -> None:
    mods = [_FakeModule(n) for n in ("SGP40", "BMP3XX", "NEOPIXEL", "DNS", "CFGMGR_SGP40")]
    for m in mods:
        run(m.pr.err_s("x", errno=1))
    service, app = _make_service(error_sources=mods)
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
    service, app = _make_service(error_sources=[a, b])
    run(app.dispatch_request(_make_request(app, "PUT", "/status", {"ResetErrors": True})))
    # Both reset together by this global action (decision: ResetErrors resets every module, not
    # scoped per-module) - the isolation property under test is that resetting doesn't cross-wire
    # one module's history into another's.
    assert a.pr.history == []
    assert b.pr.history == []
    assert a.pr.reset_calls == 1
    assert b.pr.reset_calls == 1


def test_d_webserver_own_errcount_entry_accumulates_a_warning_on_reclaim() -> None:
    service, app = _make_service(per_call_timeout_s=0.05, outer_cap_s=0.2, max_connections=2)
    reader = _HangingReader()
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=2.0)
    log = run(service.get_error_counter())
    entry = next(iter(log.values()))
    assert entry["ErrCount"] >= 1
    assert "W" in entry["ErrType"]  # a warning, not an error - decision 8's explicit distinction


def test_d_status_put_malformed_json_body_is_a_clean_rejection_not_a_crash() -> None:
    module = _FakeModule("SGP40")
    service, app = _make_service(error_sources=[module])
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
    service, app = _make_service(settings={"networking": [SettingsGroup(mod, ("Interval", "Offset"))]})

    async def scenario() -> None:
        put_task = asyncio.get_event_loop().create_task(
            app.dispatch_request(_make_request(app, "PUT", "/networking", {"Interval": 99, "Offset": 99}))
        )
        get_res = await app.dispatch_request(_make_request(app, "GET", "/networking", None))
        await put_task
        body = json.loads(get_res.body)
        # MicroPython's cooperative, non-preemptive scheduling means the synchronous dict-build in
        # get_dict_cfg() can't be interleaved by the PUT's own await points - either both fields are
        # the old values or both are the new ones, never a mix (CLAUDE.md Part F).
        assert body in ({"Interval": 1, "Offset": 0}, {"Interval": 99, "Offset": 99})

    run(scenario())


def test_e_scd30_bmp3xx_live_readback_torn_read_is_a_known_characterization_not_a_regression() -> None:
    # Deliberately demonstrates the known, already-flagged gap (see SPECIFICATION.md Part A.8 for
    # the GET-shapes note) rather than asserting it's fixed - a runnable characterization so a future fix has a red
    # test to turn green, instead of the gap only living in prose. Modeled here with a fake whose
    # get_dict_cfg() awaits mid-construction (the real SCD30_Reader/BMP3xx_Reader shape), unlike
    # every other fake in this file which builds its dict synchronously.
    class _LiveReadbackModule(_FakeModule):
        async def get_dict_cfg(self) -> "dict[str, Any]":
            result: dict[str, Any] = {}
            for key in ("Interval", "Offset"):
                await asyncio.sleep(0)  # a real await - the torn-read window
                result[key] = self._values[key]
            return result

    mod = _LiveReadbackModule("SCD30", values={"Interval": 1, "Offset": 0})
    service, app = _make_service(settings={"sensors_live": [SettingsGroup(mod, ("Interval", "Offset"))]})

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
    service, app = _make_service(sensors=[mod])
    d1 = run(mod.get_dict_data())
    d1["CO2"] = 0
    d2 = run(mod.get_dict_data())
    assert d2 == {"CO2": 800}


# ---------------------------------------------------------------------------
# Section F - connection-lifecycle robustness. Exercises WebserverService._serve() directly against
# the fake reader/writer doubles above - no real socket, matching decision 10 (Step 2's own tests
# stay independent of Step 3's digital twin) and the CI-hang-fix precedent (never a real
# select.poll()).
# ---------------------------------------------------------------------------

# F.1 - before/at accept


def test_f1_client_sends_nothing_ever_is_reclaimed_by_the_per_call_timeout() -> None:
    service, app = _make_service(per_call_timeout_s=0.05, outer_cap_s=2.0)
    writer = _ScriptedWriter()
    run_timed(service._serve(_HangingReader(), writer), timeout_s=2.0)
    assert run(service._open_conns.get_value()) == 0
    assert writer.close_called


def test_f1_client_opens_then_immediately_closes_before_any_bytes() -> None:
    service, app = _make_service()
    writer = _ScriptedWriter()
    run_timed(service._serve(_ClosedReader(), writer))
    assert run(service._open_conns.get_value()) == 0


def test_f1_rapid_connect_disconnect_churn_keeps_counter_accurate() -> None:
    service, app = _make_service()

    async def churn() -> None:
        for _ in range(50):
            await service._serve(_ClosedReader(), _ScriptedWriter())

    run_timed(churn(), timeout_s=10.0)
    assert run(service._open_conns.get_value()) == 0


def test_f1_connections_up_to_ceiling_accepted_beyond_ceiling_silently_closed() -> None:
    service, app = _make_service(max_connections=2, per_call_timeout_s=5.0, outer_cap_s=5.0)

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
    service, app = _make_service(max_connections=1, per_call_timeout_s=0.05, outer_cap_s=2.0)

    async def scenario() -> None:
        await service._serve(_HangingReader(), _ScriptedWriter())  # reclaimed by per-call timeout
        assert await service._open_conns.get_value() == 0
        second_reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
        second_writer = _ScriptedWriter()
        await service._serve(second_reader, second_writer)
        assert second_writer.written != b""  # actually served this time, no cooldown gap

    run_timed(scenario(), timeout_s=5.0)


# F.2 - mid-request, headers/request-line


def test_f2_trickled_request_line_is_reclaimed_by_the_outer_cap_not_a_single_per_call_timeout() -> None:
    # Corrected during implementation (see this file's own docstring: "refining only where writing
    # the real code reveals a genuine problem"). Each header LINE (not byte) arrives as one atomic
    # chunk, paced far enough apart that any single readline() call - the whole point of a *per-call*
    # timeout wrapping one logical stream-method invocation, per BACKLOG.md's design sketch step 2 -
    # finishes comfortably under the per-call timeout, defeating it; the outer per-connection
    # wall-clock cap (wrapping the *whole* handle_request() call) is what actually bounds the
    # connection regardless of how the client paces individual reads (see SPECIFICATION.md Part A.8,
    # connection-hardening item 1 / decision 2). A byte-by-byte trickle (this test's original shape) instead made a
    # *single* readline() call itself take far longer than the per-call timeout to assemble one
    # line - correctly reclaimed by the per-call timeout alone, never even reaching the outer cap,
    # which wasn't what this test was meant to isolate.
    line_delay = 0.02
    per_call = 1.0  # generous - no single line's own readline() call should ever approach this
    outer_cap = 0.05  # exceeded partway through line-by-line delivery (0.02s/line) regardless
    full_line = _request_bytes("GET", "/status")
    physical_lines = [part + b"\r\n" for part in full_line.split(b"\r\n")[:-1]]  # drop the trailing
    # split() artifact after the final \r\n - see full_line's own \r\n\r\n terminator
    chunks = [(line_delay, line) for line in physical_lines]
    service, app = _make_service(per_call_timeout_s=per_call, outer_cap_s=outer_cap)
    reader = _ScriptedReader(chunks)
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=outer_cap * 20)
    assert run(service._open_conns.get_value()) == 0
    assert writer.written == b""  # reclaimed before a response could ever be produced


def test_f2_malformed_request_line_degrades_safely_via_microdots_own_blanket_catch() -> None:
    service, app = _make_service()
    reader = _ScriptedReader([(0, b"NOT A VALID REQUEST LINE AT ALL\r\n\r\n")])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert run(service._open_conns.get_value()) == 0  # no exception escaped _serve()


def test_f2_content_length_larger_than_body_sent_then_silence_times_out() -> None:
    # Corrected during implementation, same root cause as the clean-EOF test above: the per-call
    # readexactly() timeout is an asyncio.TimeoutError, confirmed a plain Exception (not an OSError)
    # directly from the pinned interpreter's extmod/asyncio/core.py - so it's absorbed by
    # handle_request()'s own blanket except-Exception around Request.create(), which then writes its
    # own ordinary 400 and closes normally, rather than the connection being silently dropped.
    service, app = _make_service(per_call_timeout_s=0.05, outer_cap_s=1.0)
    headers = "PUT /networking HTTP/1.1\r\nContent-Length: 1000\r\nContent-Type: application/json\r\n\r\n"
    reader = _ScriptedReader([(0, headers.encode() + b'{"Interval":')])  # body truncated, then silence
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0
    assert b" 400 " in writer.written  # Microdot's own ordinary 400 response, not a silent drop


def test_f2_content_length_exceeding_max_content_length_returns_413() -> None:
    service, app = _make_service(max_content_length=64, per_call_timeout_s=2.0, outer_cap_s=2.0)
    body = json.dumps({"Interval": 1, "Padding": "x" * 200}).encode()
    reader = _ScriptedReader([(0, _request_bytes("PUT", "/networking", body))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0
    assert b"413" in writer.written


def test_f2_body_truncated_by_a_clean_peer_close_degrades_via_microdots_own_blanket_catch() -> None:
    # Corrected during implementation, once the real code revealed the actual behavior. Traced
    # directly against ext/microdot.py's handle_request(): the readexactly() call
    # for the body sits inside Request.create(), which handle_request() wraps in `except OSError ...
    # else: raise` *then* `except Exception as exc: print_exception(exc)` - EOFError isn't an
    # OSError, so it hits the second clause, which does not re-raise. req stays None and
    # handle_request() falls straight through to its own ordinary 400 response, written and closed
    # normally - exactly like the malformed-request-line case just above, not a silent drop. EOFError
    # structurally never reaches our own serve() wrapper here; a per-call *timeout* on the same read
    # (see the sibling "then silence times out" test above) is what actually reaches us, since a
    # timeout is an unmuted OSError and handle_request()'s first except clause re-raises those.
    headers = "PUT /networking HTTP/1.1\r\nContent-Length: 100\r\nContent-Type: application/json\r\n\r\n"
    service, app = _make_service(per_call_timeout_s=1.0, outer_cap_s=2.0)
    reader = _ScriptedReader([(0, headers.encode() + b'{"Interval": 1}')], eof=True)  # then a clean EOF, not silence
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0
    assert b" 400 " in writer.written  # Microdot's own ordinary 400 response, not a silent drop


# F.5 - after response / close


def test_f5_normal_close_decrements_counter_exactly_once() -> None:
    service, app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert run(service._open_conns.get_value()) == 0
    assert writer.close_called


def test_f5_connection_close_header_present_on_every_response_including_errors() -> None:
    service, app = _make_service()
    for method, path in (("GET", "/status"), ("GET", "/no/such/route"), ("DELETE", "/status")):
        writer = _ScriptedWriter()
        reader = _ScriptedReader([(0, _request_bytes(method, path))])
        run_timed(service._serve(reader, writer))
        assert b"Connection: close" in writer.written, path


def test_f5_double_close_paths_dont_raise_or_double_decrement() -> None:
    service, app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))  # our own finally + Microdot's own aclose() both run
    assert run(service._open_conns.get_value()) == 0


# F.6 - concurrency / resource-ceiling behavior


def test_f6_n_simultaneous_wedged_connections_are_each_independently_reclaimed() -> None:
    service, app = _make_service(max_connections=3, per_call_timeout_s=0.05, outer_cap_s=0.5)

    async def scenario() -> None:
        writers = [_ScriptedWriter() for _ in range(3)]
        await asyncio.gather(*(service._serve(_HangingReader(), w) for w in writers))
        assert await service._open_conns.get_value() == 0
        for w in writers:
            assert w.close_called

    run_timed(scenario(), timeout_s=5.0)


def test_f6_no_cooldown_gap_between_a_reclaim_and_the_next_accept() -> None:
    service, app = _make_service(max_connections=1, per_call_timeout_s=0.02, outer_cap_s=1.0)

    async def scenario() -> None:
        start = 0
        for _ in range(5):  # repeated reclaim/accept cycles, no artificial grace period between them
            await service._serve(_HangingReader(), _ScriptedWriter())
            assert await service._open_conns.get_value() == 0
            start += 1
        assert start == 5

    run_timed(scenario(), timeout_s=10.0)


def test_f6_pathological_repeated_rewedging_stays_bounded_never_escalates() -> None:
    service, app = _make_service(max_connections=2, per_call_timeout_s=0.02, outer_cap_s=0.2)

    async def scenario() -> None:
        for _ in range(30):  # a hostile client immediately reconnecting and rewedging
            await service._serve(_HangingReader(), _ScriptedWriter())
        # Worst case bounded to "ceiling slots occupied for at most one outer-cap duration,
        # repeatedly" - never an unbounded backlog, never a _TASK_FAIL_MAX-style escalation.
        assert await service._open_conns.get_value() == 0

    run_timed(scenario(), timeout_s=15.0)


def test_f6_a_hanging_cleanup_close_path_still_lets_the_connection_task_end() -> None:
    service, app = _make_service(per_call_timeout_s=0.05, outer_cap_s=0.2)
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
    service, app = _make_service()
    writer = _RaisingCloseWriter()
    run_timed(service._close_writer(writer))
    assert writer.wait_closed_called is True


def test_close_writer_logs_a_persisted_warning_when_close_raises() -> None:
    # Step 6 (silent-failure-masking finding): a raising close()/wait_closed() must not just be
    # swallowed silently - it needs a persisted signal, the same as every other connection-lifecycle
    # failure this file already logs (peer-closed-early, timed-out, socket-error).
    service, app = _make_service()
    writer = _RaisingCloseWriter()
    run_timed(service._close_writer(writer))
    assert service.pr.err_count == 1


class _RaisingWaitClosedWriter(_ScriptedWriter):
    async def wait_closed(self) -> None:
        self.wait_closed_called = True
        raise OSError("simulated wait_closed() failure")


def test_close_writer_logs_a_persisted_warning_when_wait_closed_raises() -> None:
    service, app = _make_service()
    writer = _RaisingWaitClosedWriter()
    run_timed(service._close_writer(writer))
    assert writer.close_called is True
    assert service.pr.err_count == 1


def test_timeout_stream_proxy_close_and_wait_closed_forward_to_the_wrapped_stream() -> None:
    # Direct unit coverage of the two Stream-forwarding methods ext/microdot.py's own request/
    # response handling never actually calls in any of Section F's protocol-level scenarios (close()
    # is sync, wait_closed() is only ever invoked by WebserverService._close_writer() on the raw
    # writer, not the proxy) - still real, real-Stream-matching forwards that must work correctly.
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

    async def _raise_eof(reader: "Any", writer: "Any") -> None:
        raise EOFError

    app.handle_request = _raise_eof
    run_timed(service._serve(_ScriptedReader([]), _ScriptedWriter()))
    assert run(service._open_conns.get_value()) == 0


def test_serve_absorbs_an_oserror_raised_directly_by_handle_request() -> None:
    # Never actually raised by any of this module's own fakes/proxy (see _serve()'s own comment) -
    # a genuine real-hardware socket failure is the only real trigger, so exercised directly here.
    service, app = _make_service()

    async def _raise_os(reader: "Any", writer: "Any") -> None:
        raise OSError("simulated socket failure")

    app.handle_request = _raise_os
    run_timed(service._serve(_ScriptedReader([]), _ScriptedWriter()))
    assert run(service._open_conns.get_value()) == 0


def test_serve_absorbs_an_unexpected_exception_raised_directly_by_handle_request() -> None:
    service, app = _make_service()

    async def _raise_boom(reader: "Any", writer: "Any") -> None:
        raise RuntimeError("simulated unexpected bug")

    app.handle_request = _raise_boom
    run_timed(service._serve(_ScriptedReader([]), _ScriptedWriter()))
    assert run(service._open_conns.get_value()) == 0
    log = run(service.get_error_counter())
    entry = next(iter(log.values()))
    assert "E" in entry["ErrType"]  # errno=1 path (err_s, not wrn_s) - a genuinely unexpected bug


# F.7 - adversarial/malformed-input shapes


def test_f7_unknown_path_returns_404_shaped_response() -> None:
    service, app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("GET", "/no/such/route"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert b" 404 " in writer.written


def test_f7_wrong_http_method_on_a_known_path_returns_405_shaped_response() -> None:
    service, app = _make_service()
    reader = _ScriptedReader([(0, _request_bytes("DELETE", "/status"))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer))
    assert b" 405 " in writer.written


def test_f7_extremely_long_url_path_is_handled_cleanly_not_a_crash() -> None:
    service, app = _make_service(per_call_timeout_s=2.0, outer_cap_s=2.0)
    long_path = "/status/" + ("a" * 8192)
    reader = _ScriptedReader([(0, _request_bytes("GET", long_path))])
    writer = _ScriptedWriter()
    run_timed(service._serve(reader, writer), timeout_s=3.0)
    assert run(service._open_conns.get_value()) == 0  # reclaimed or 404'd, never an escaped exception


def test_f7_dedicated_multi_connection_slowloris_simulation_all_reclaimed_and_slots_reused() -> None:
    per_call = 0.02
    outer_cap = 0.1
    service, app = _make_service(max_connections=3, per_call_timeout_s=per_call, outer_cap_s=outer_cap)

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
    service, app = _make_service()
    starters = service.get_task_starters()
    assert len(starters) == 1


def test_f8_start_serving_runs_a_real_asyncio_start_server_backed_task() -> None:
    # Section F elsewhere only ever calls service._serve() directly (its own reader/writer fakes) -
    # this is the one test exercising _run()/_start_serving() themselves, the real
    # asyncio.start_server() composition (never app.start_server()/app.shutdown() - decision 1).
    # Bound to an ephemeral loopback port, never the real host/port=0.0.0.0:80 default.
    service, app = _make_service(host="127.0.0.1", port=0)

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

    service, app = _make_service(max_connections=2, per_call_timeout_s=0.02, outer_cap_s=0.1)

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
# Section G - static-route serving (see SPECIFICATION.md Part A.9: gzip -> freezefs -> frozen
# module -> Microdot send_file(compressed=True, file_extension=".gz")). Exercises the generic
# route-wiring mechanism against a synthetic VfsFrozen fixture (see _mount_static_fixture below) -
# the real, built frozen_html.py artifact (scripts/build_frozen_html.sh's output) gets its own,
# separate real-pipeline integration test in tests/test_frozen_html_integration.py.
# ---------------------------------------------------------------------------

_next_static_mount = 0


def _mount_static_fixture(files: "dict[str, bytes]") -> str:
    # A hand-built VfsFrozen (freezefs 2.4's own runtime mount driver, ext/freezefs/ffsmount.py),
    # bypassing freezefs's own archive-generation step entirely - exercises exactly the same runtime
    # VFS a real `import frozen_html` produces, without depending on scripts/build_frozen_html.sh's
    # actual stub content. Entries deliberately store plain (non-gzip) bytes under a ".gz"-suffixed
    # name: VfsFrozen's own per-entry "compressed" flag (freezefs's own --compress, never used by
    # this project - see CLAUDE.md) is independent of our own gzip/Content-Encoding convention, and
    # send_file() never inspects file contents - a faithful stand-in for the route-wiring mechanism.
    # A unique mount point per call (os.mount() raises EEXIST on a repeat target) since every test in
    # this file runs in the same interpreter process.
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
    # Registration-order regression test: /<path:filename>'s own regex (`/(.+)`) also matches
    # "/measurements" - Microdot's find_route() returns the *first* matching route in registration
    # order (ext/microdot.py's find_route(), confirmed directly), so the static wildcard must be
    # registered after every real API route or it would silently swallow them.
    scd = _NestedCfgModule("SCD30", values={}, data={"CO2": 800})
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>", "measurements": b"not the real one"})
    service, app = _make_service(sensors=[scd], static_mount=mount)
    res = run(app.dispatch_request(_make_request(app, "GET", "/measurements", None)))
    assert res.status_code == 200
    assert json.loads(res.body) == {"SCD30": {"CO2": 800}}  # the real endpoint, not the static file


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


# G.2 - hotspot-mode captive-portal redirect fallback (see SPECIFICATION.md Part A.5).
# `is_hotspot_active` is an optional constructor callback; it only changes the *fallback* branch of
# _serve_static()'s `except OSError` - a real file hit or a real API route must stay unaffected
# regardless of its value, and its constructor default (None) must reproduce today's plain-404
# behavior byte for byte, since every existing WebserverService(...) call site doesn't pass it.


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
    assert json.loads(res.body) == {"SCD30": {"CO2": 800}}


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
    # Proves plan §2.4's "no bespoke try/except needed" decision directly: Part A.5's existing
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
    # Error-path/all-paths coverage: the ".." guard clause runs and aborts(404) BEFORE the
    # try/except OSError block that consults is_hotspot_active() is ever reached (see
    # _serve_static()'s own source order) - a traversal attempt must never be redirected, hotspot
    # mode or not.
    mount = _mount_static_fixture({"index.html": b"<h1>hi</h1>"})
    _, app = _make_service(static_mount=mount, is_hotspot_active=lambda: True)
    res = run(app.dispatch_request(_make_request(app, "GET", "/foo/../../index.html", None)))
    assert res.status_code == 404


def test_g2_put_to_unmatched_path_is_405_regardless_of_hotspot_state() -> None:
    # All-paths coverage: the wildcard route is registered GET-only (app.get("/<path:filename>")) -
    # ext/microdot.py's own find_route() resolves a PUT against a path-matching-but-method-mismatched
    # route to 405 before _get_static()/_serve_static() is ever invoked, so is_hotspot_active() is
    # never even consulted for a non-GET request. Confirms the redirect fallback can't leak into an
    # unrelated error path.
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


# H.1 - app.errorhandler(Exception) catch-all (Step 8 audit finding: closes BACKLOG.md's former
# "No @app.errorhandler registrations exist anywhere yet" item - the 400/404/405/413/500 status-code
# handlers section G already exercises were the reply-shape half; this is the still-missing logging
# half, since Microdot's own print_exception(exc) never reaches pr.err_s()/FRAM history on its own).


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
    # ErrNum/ErrType include print_log.py's own pre-filled "N" (no-error) deque padding ahead of
    # the one real entry (see print_log.py's PrintLogHistory.__init__) - matching every other
    # get_error_counter()-reading test in this file (e.g. test_d_webserver_own_errcount_entry_...),
    # not a list-equality check against the raw history.
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


# H.2 - /status JSON streaming (asy_webserver_service.py's _get_status()/_build_status_pieces() -
# BACKLOG.md's Microdot generator-streaming mitigation for the real-hardware MemoryError root cause:
# one small json.dumps() per already-independent source instead of one big buffer for the whole
# aggregate). Sections above (test_status_get_*, D, most of the earlier /status coverage) already
# exercise the resulting JSON's *shape* end to end via status_body() - these are specific to the
# streaming mechanism itself. Deliberately a plain list of pre-fetched fragments handed to a plain
# sync iterator, not an `async def ... yield` "async generator" - confirmed directly against the
# pinned MicroPython interpreter that the latter produces a broken runtime object (no
# __aiter__/__anext__ at all, and driving it past a real `await` via plain next() - exactly what
# ext/microdot.py's body_iter() would do with it - segfaults the interpreter). See
# SPECIFICATION.md Part F.1 for the full finding.


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
    # Observable proof of the actual memory-efficiency property this was built for: the body is
    # genuinely 5 separate pieces (one per top-level key), never one big string built up front for
    # the whole aggregate - but also never one piece per punctuation character (measured to regress
    # real throughput ~53% via this server's own per-write asyncio.wait_for() wrapping - see
    # _build_status_pieces()'s own comment for the full finding).
    service, app = _make_service(
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
    # Response.complete() only auto-sets Content-Length for isinstance(self.body, bytes), never a
    # generic iterator - _get_status() sets it explicitly instead, since the full size is already
    # known once every source has been awaited up front (nothing here is genuinely lazy streaming -
    # see _get_status()'s own comment). Real-hardware/real-socket regression coverage
    # (found via tests/test_digital_twin_run_wozi_integration.py's own soak test failing without
    # this): digital_twin/_http_client.py's fetch() falls back to a slow, effectively-untested
    # reader.read(-1)-until-EOF path whenever Content-Length is missing.
    service, app = _make_service()
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
    service, app = _make_service(
        maintenance_sensors=[("SGP40", _raising_source), ("BMP3XX", _const_source({"BackupTS": 1}))]
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body["sensors"]["SGP40"] == {"error": "unavailable"}
    assert body["sensors"]["BMP3XX"] == {"BackupTS": 1}  # a sibling source's failure never leaks into this one


def test_h2_stream_errcount_source_failure_is_isolated_to_that_one_module() -> None:
    good = _FakeModule("BMP3XX")
    bad = _RaisingErrorCounterModule("SGP40")
    service, app = _make_service(error_sources=[good, bad], history_length=0)  # see
    # test_h2_stream_yields_many_small_chunks_not_one_precomputed_buffer()'s own comment on why
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert errcount["SGP40"] == {"error": "unavailable"}
    assert errcount["BMP3XX"] == {"counter": 0, "history": []}
    # WEBSERVER's own counter reflects the SGP40 failure just logged (errno=6) - not zero, since that
    # failure genuinely happened and belongs in this service's own error history too (history_length=0
    # above keeps the ring buffer itself at zero capacity, so the detail entry never lands in
    # "history" - see test_h2_stream_status_source_failure_yields_an_error_marker_not_a_broken_stream()
    # for that same errno=6 detail checked with a real ring buffer instead).
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
    # The worst case this design has to survive: every single data source misbehaves. Even then, the
    # response must still be one complete, parseable JSON document with a plain 200 - each source's
    # own try/except (see _dump_status_source()'s own comment) keeps its exception from ever escaping
    # _build_status_pieces()/_get_status() itself, so Microdot's own blanket catch never even sees one.
    service, app = _make_service(
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
    # WEBSERVER's own entry is never itself an "error" marker (its own get_log() never raised here) -
    # its counter instead reflects the 5 other failures just logged (3 status sources + 1 maintenance
    # sensor + 1 errcount module, each its own errno=6 call) - not zero, and not one of the sources
    # under test itself blowing up this entry too.
    assert body["errcount"]["WEBSERVER"]["counter"] == 5
    assert body["errcount"]["WEBSERVER"]["history"] == []  # history_length=0 above, see comment above


# -- maximum achievable coverage ----------------------------------------------------------------


def test_h2_stream_empty_registration_everywhere_matches_the_old_all_empty_shape() -> None:
    service, app = _make_service(sensors=[], settings={}, maintenance_sensors=[], error_sources=[], history_length=0)  # see
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
    service, app = _make_service(
        maintenance_sensors=[("SGP40", _const_source({"A": 1})), ("BMP3XX", _const_source({"B": 2}))]
    )
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    body = json.loads(status_body(res))
    assert body["sensors"] == {"SGP40": {"A": 1}, "BMP3XX": {"B": 2}}


def test_h2_stream_two_error_sources_plus_the_own_entry_produce_valid_json_with_no_stray_commas() -> None:
    service, app = _make_service(error_sources=[_FakeModule("SGP40"), _FakeModule("BMP3XX")])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert set(errcount.keys()) == {"SGP40", "BMP3XX", "WEBSERVER"}


def test_h2_stream_module_names_with_special_characters_are_correctly_escaped() -> None:
    # Names go through json.dumps(name), never hand-rolled string concatenation - this is what makes
    # an unusual name safe rather than corrupting the surrounding document (see
    # _build_status_pieces()'s own comment on why every piece is its own list entry rather than
    # joined by hand).
    tricky = _FakeModule('SGP"40')
    service, app = _make_service(error_sources=[tricky])
    res = run(app.dispatch_request(_make_request(app, "GET", "/status", None)))
    errcount = json.loads(status_body(res))["errcount"]
    assert set(errcount.keys()) == {'SGP"40', "WEBSERVER"}


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
