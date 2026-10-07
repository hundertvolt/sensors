"""End-to-end integration tests for the setter generalization work: asy_api_response.py's
parse_cmd_request()/handle_set_cmd() driven against mocked Microdot request data (fine/partial/garbage), then against a real ext/microdot.py (v2.7.0) Microdot app wired the same way src/asy_webserver_service.py's real registration-based routes are.
"""
# Covers a real WifiService for the setter path, a real NTPClient for both getter and setter, a real
# BMP3XX_Reader/SGP40_Reader for the schema-driven sensor setters, and a real SCD30_Reader whose config
# store is the chip itself.
#
# Only test-local Microdot apps are constructed here, independent of src/asy_webserver_service.py: any of
# its wiring that must be exercised is reimplemented locally, never imported, to keep this file's scope
# self-contained.

import asyncio
import errno as errno_mod
import json
import os
import struct
import sys
from collections import namedtuple

# scripts/test.sh's MICROPYPATH deliberately excludes ext/, and changing that would be a scripts/ change
# needing a full clean-chroot re-verification. Extending sys.path at runtime, scoped to this one file,
# reaches the same real ext/microdot.py without touching any of that.
sys.path.insert(0, "ext")

# microdot is typed via the vendored upstream stub (ext/typings/microdot/).
from _error_codes import code
from _tmp_scratch import TmpScratch
from microdot import Microdot, Request

import asy_api_response as ar
from asy_base_classes import ValueRef
from asy_bmp3xx_driver import BMP3XX_Reader
from asy_crc_checks import CRC8
from asy_i2c_driver import I2C
from asy_ntp_client import NTPClient, NtpTiming
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_wifi_service import WifiConfig, WifiService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    import asy_config_manager as cm
    from asy_base_classes import JsonValue

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("msi")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def make_wifi_client() -> WifiService:
    client = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), cfg_path=_tmp_cfg_dir())
    run(client.setup())
    return client


def make_ntp_client() -> NTPClient:
    wifi_mode_lock = asyncio.Lock()
    client = NTPClient(
        wifi_mode_lock,
        network_available_locked=lambda: True,
        get_dns_server=lambda: None,
        timing=NtpTiming(500, 1, 5000, 10, 600),
        cfg_path=_tmp_cfg_dir(),
    )
    run(client.setup())
    return client


class _FakeRequest:
    # Same minimal stand-in as test_asy_api_response.py's own - mocks only the .json property boundary.
    def __init__(self, json_value: object, *, raise_instead: bool = False) -> None:
        self._json_value = json_value
        self._raise_instead = raise_instead

    @property
    def json(self) -> object:  # matches asy_api_response.py's own _RequestLike Protocol
        if self._raise_instead:
            raise ValueError("malformed body")
        return self._json_value


# ---------------------------------------------------------------------------
# Simulated endpoint handler - combines parse_cmd_request() and handle_set_cmd() the way a real route does
# (one cmd, a fixed field list, one post_fct hook), driven against mocked request data of varying quality
# without a real Microdot app or real sockets.
#
# WifiService owns one schema/cfgmgr for all of SSID/PW/Country/Hostname/LEDWifiOn, but the real
# registration scopes them into two separate SettingsGroup entries - one for the four with
# post_fct=conn.reconnect_wifi, one for LEDWifiOn alone with none.
#
# Passing the whole field set as one group would let a LEDWifiOn-only change spuriously reconnect, and let
# the others reach LEDWifiOn's group with no reconnect at all. _scoped_set() below mirrors that scoping
# locally, the way the real SettingsGroup does, this file never importing the generated device module.
# ---------------------------------------------------------------------------


async def _scoped_set(
    client: WifiService, fields: "dict[str, JsonValue]", keys: "tuple[str, ...]", post_fct: "Callable[[], None] | None" = None,
) -> "dict[str, str]":
    # The route's own keys go to handle_set_cmd() with the module's schema (the store validates against all of
    # it); any other key answers Invalid, as a key outside every group of the real route does.
    result: dict[str, str] = dict.fromkeys([k for k in fields if k not in keys], "Invalid")
    result.update(await ar.handle_set_cmd(client, {k: v for k, v in fields.items() if k in keys}, client.get_cfg_schema(), post_fct=post_fct))
    return result


async def _simulated_set_network_endpoint(client: WifiService, request: "ar._RequestLike") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setNetwork"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    # The endpoint builds the one OK envelope around handle_set_cmd()'s per-field result, with its own text.
    result = await _scoped_set(client, fields, ("SSID", "PW", "Country", "Hostname"), post_fct=client.reconnect_wifi)
    return ar.make_response(0, descr="Network settings updated", result=result)


async def _simulated_set_wifi_led_endpoint(client: WifiService, request: "ar._RequestLike") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setWiFiLED"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    return ar.make_response(0, result=await _scoped_set(client, fields, ("LEDWifiOn",)))


def test_mocked_request_fine_data_applies_and_reports_ok() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "Hostname": "NewHost", "SSID": "MyNet", "PW": "supersecret", "Country": "US"})
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["code"] == 0
    assert resp["descr"] == "Network settings updated"
    assert resp["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Valid", "Country": "Valid"}
    assert client._reconn_wifi is True  # post_fct fired
    stored = run(client.cfgmgr.get_dict(["Hostname", "SSID", "PW", "Country"]))
    assert stored == {"Hostname": "NewHost", "SSID": "MyNet", "PW": "supersecret", "Country": "US"}


def test_mocked_request_partially_fine_data_reports_mixed_per_field_results() -> None:
    client = make_wifi_client()
    req = _FakeRequest(
        {"cmd": "setNetwork", "Hostname": "NewHost", "SSID": "MyNet", "PW": "short", "Country": "United States"},
    )
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"  # still overall OK - per-field detail lives in "result"
    assert resp["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Invalid", "Country": "Invalid"}
    assert client._reconn_wifi is True  # still fires: at least one field (Hostname/SSID) changed
    stored = run(client.cfgmgr.get_dict(["PW", "Country"]))
    assert stored == {"PW": "", "Country": "DE"}  # both rejected, left at their defaults


def test_mocked_request_garbage_body_is_rejected_before_dispatch() -> None:
    client = make_wifi_client()
    req = _FakeRequest([1, 2, 3])  # valid JSON, wrong shape entirely
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}
    assert client._reconn_wifi is False  # never reached the dispatch step at all


def test_mocked_request_unparseable_body_is_rejected_before_dispatch() -> None:
    client = make_wifi_client()
    req = _FakeRequest(None, raise_instead=True)
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["code"] == 1
    assert client._reconn_wifi is False


def test_mocked_request_missing_cmd_field_is_rejected_before_dispatch() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"Hostname": "NewHost"})  # no "cmd" key at all
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp == {"res": "ERR", "code": 2, "descr": "Command specifier missing", "result": {}}


def test_mocked_request_unrecognized_cmd_is_rejected_before_dispatch() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "bogusCommand", "Hostname": "NewHost"})
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp == {"res": "ERR", "code": 3, "descr": "Invalid command", "result": {}}


def test_mocked_request_unknown_field_key_reported_individually_not_whole_request() -> None:
    # (owner, 2026-09-26): an unrecognized field key (as opposed to an unrecognized *command*)
    # is just another per-field "Invalid" outcome, not a whole-request rejection.
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "Hostname": "NewHost", "Bogus": 1})
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["result"] == {"Hostname": "Valid", "Bogus": "Invalid"}
    assert run(client.cfgmgr.get_dict(["Hostname"])) == {"Hostname": "NewHost"}


def test_mocked_request_empty_body_dict_is_valid_but_changes_nothing() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork"})  # no fields at all beyond "cmd"
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp == {"res": "OK", "code": 0, "descr": "Network settings updated", "result": {}}
    assert client._reconn_wifi is False  # nothing changed, post_fct never fires


# ---------------------------------------------------------------------------
# setNetwork/setWiFiLED field scoping - regression coverage for the cross-route schema leakage this pattern
# avoids: WifiService owns one schema for both field groups, so passing the whole schema to either route,
# rather than that route's own subset, would blur them.
#
# setNetwork would then accept and persist LEDWifiOn, reconnecting spuriously for an LED-only change, and
# setWiFiLED would silently persist SSID/PW/Country/Hostname with no reconnect at all.
# ---------------------------------------------------------------------------


def test_mocked_set_network_rejects_led_wifi_on_and_does_not_reconnect() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "LEDWifiOn": False})  # not setNetwork's field
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["result"] == {"LEDWifiOn": "Invalid"}
    assert client._reconn_wifi is False  # nothing setNetwork actually owns changed


def test_mocked_set_network_hostname_change_still_reconnects_alongside_rejected_led_field() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "Hostname": "NewHost", "LEDWifiOn": False})
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["result"] == {"Hostname": "Valid", "LEDWifiOn": "Invalid"}
    assert client._reconn_wifi is True  # Hostname is a real setNetwork field and did change


def test_mocked_set_wifi_led_rejects_ssid_and_leaves_it_untouched() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setWiFiLED", "SSID": "Hacked"})  # not setWiFiLED's field
    resp = run(_simulated_set_wifi_led_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["result"] == {"SSID": "Invalid"}
    assert run(client.cfgmgr.get_dict(["SSID"])) == {"SSID": ""}  # untouched default, not "Hacked"


def test_mocked_set_wifi_led_applies_its_own_field_without_reconnecting() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setWiFiLED", "LEDWifiOn": False})
    resp = run(_simulated_set_wifi_led_endpoint(client, req))
    assert resp["result"] == {"LEDWifiOn": "Valid"}
    assert run(client.cfgmgr.get_dict(["LEDWifiOn"])) == {"LEDWifiOn": False}
    # setWiFiLED (unlike setNetwork) passes no post_fct at all - toggling the WiFi status LED must
    # never reconnect the WiFi connection.
    assert client._reconn_wifi is False


def test_real_microdot_set_network_rejects_led_field_end_to_end() -> None:
    # Reuses the module's own _wifi_app() helper (defined further below, alongside the other real-
    # Microdot setter tests) - already wires /net/cmd to _simulated_set_network_endpoint.
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(app, "PUT", "/net/cmd", {"cmd": "setNetwork", "LEDWifiOn": True})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"] == {"LEDWifiOn": "Invalid"}
    assert client._reconn_wifi is False


# ---------------------------------------------------------------------------
# Real ext/microdot.py (v2.7.0) end to end - a real Microdot() app with a real @app.put route, dispatched
# through the library's own dispatch_request() (routing, before/after hooks, exception handling, dict->JSON
# coercion - see CLAUDE.md's "Microdot / REST layer"), with a real Request object.
#
# No real TCP socket is opened: Request is constructed directly, in the same shape Request.create() builds
# from a socket stream.
# ---------------------------------------------------------------------------


def _make_request(app: Microdot, method: str, path: str, json_body: "dict[str, Any] | None") -> Request:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    return Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)


def _wifi_app(client: WifiService) -> Microdot:
    app = Microdot()

    @app.put("/net/cmd")
    async def network_cmd(request: Request) -> "ar.ResponseEnvelope":
        return await _simulated_set_network_endpoint(client, request)

    return app


def test_real_microdot_setter_end_to_end_valid_request() -> None:
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(
        app, "PUT", "/net/cmd", {"cmd": "setNetwork", "Hostname": "RealHost", "SSID": "RealNet", "PW": "supersecret", "Country": "US"},
    )
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Valid", "Country": "Valid"}
    assert client._reconn_wifi is True
    assert run(client.cfgmgr.get_dict(["Hostname"])) == {"Hostname": "RealHost"}


def test_real_microdot_setter_end_to_end_partial_failure_still_200() -> None:
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(app, "PUT", "/net/cmd", {"cmd": "setNetwork", "Hostname": "RealHost", "PW": "short"})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200  # overall HTTP success even with a per-field failure
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"Hostname": "Valid", "PW": "Invalid"}


def test_real_microdot_setter_end_to_end_garbage_body() -> None:
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(app, "PUT", "/net/cmd", {"cmd": "setNetwork"})
    req._body = b"{not valid json"  # type: ignore[attr-defined]  # force a real malformed body past Request's own parsing; the upstream stub omits _body - removal trigger: SPECIFICATION.md B.15
    req.content_length = len(req._body)  # type: ignore[attr-defined]  # the upstream stub omits Request's private _body - removal trigger: SPECIFICATION.md B.15
    res = run(app.dispatch_request(req))
    assert res.status_code == 200  # our own precise 200+ERR-envelope reply, not Microdot's bare 500
    body = json.loads(res.body)
    assert body == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}


def test_real_microdot_returns_404_for_an_unregistered_route() -> None:
    # Confirms real Microdot routing (find_route()), not just our own handler logic.
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(app, "GET", "/no/such/route", None)
    res = run(app.dispatch_request(req))
    assert res.status_code == 404


def test_real_microdot_wrong_method_returns_405() -> None:
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(app, "GET", "/net/cmd", None)  # only PUT is registered
    res = run(app.dispatch_request(req))
    assert res.status_code == 405


def test_real_microdot_handler_raising_is_caught_by_microdots_own_blanket_catch() -> None:
    # Defense-in-depth proof at the opposite end from handle_set_cmd's own hook guard: even a
    # handler that bypasses asy_api_response.py entirely and raises directly is still contained by
    # Microdot itself (see CLAUDE.md's "Microdot / REST layer" section) - the server never crashes.
    app = Microdot()

    @app.put("/boom")
    async def boom(_request: Request) -> None:  # Microdot passes it positionally
        raise RuntimeError("simulated handler bug")

    print("(expected) the traceback below is Microdot's own internal exception logging, triggered on purpose")
    req = _make_request(app, "PUT", "/boom", {})
    res = run(app.dispatch_request(req))
    assert res.status_code == 500


# ---------------------------------------------------------------------------
# Real Microdot end to end with a real sensor driver (BMP3xx), not just the software-only readers above -
# proving a genuine hardware fault (a wedged I2C bus, as a dead sensor produces) propagates through
# _set_dict_cfg's push callback, handle_set_cmd's per-field result and real dispatch as a per-field "Failed".
#
# Inside a normal 200 JSON response, never a raised exception or a bare Microdot 500. The one place
# CLAUDE.md's blanket-catch guarantee and SPECIFICATION.md Part C.4's layer-3 "never raises" contract are
# proven to hold together.
# ---------------------------------------------------------------------------


def _nak_i2c_address(i2c: I2C, address: int) -> None:
    # Same real-fake-I2C access as test_asy_bmp3xx_driver.py's fake() helper - i2c._i2c is typed I2C-or-None
    # (only None before setup()), so this narrows it the way fake()'s own return annotation does, rather
    # than an inline type: ignore, which mypy would flag as "union-attr" and is easy to get subtly wrong.
    from machine import I2C as _FakeI2C

    real_i2c = i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    real_i2c.nak_addresses.add(address)


def _fault_i2c_write(i2c: I2C, exc: Exception) -> None:
    # Narrower than _nak_i2c_address above: fails only the write half of a read-modify-write register
    # access (the next writeto with a stop - a read's address write has none), leaving reads and so a
    # registered _get_callbacks getter functional. Same i2c._i2c narrowing as _nak_i2c_address.
    from machine import I2C as _FakeI2C

    real_i2c = i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    real_writeto = real_i2c.writeto

    def fail_the_next_register_write(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        if stop:
            real_i2c.writeto = real_writeto  # type: ignore[method-assign]  # once only
            raise exc
        return real_writeto(address, buf, stop)

    real_i2c.writeto = fail_the_next_register_write  # type: ignore[method-assign]


def _register_device(i2c: I2C, address: int) -> None:
    # The fake routes a declared register device's address writes and reads through its registers.
    real_i2c = i2c._i2c
    assert real_i2c is not None
    real_i2c.register_device(address)


def _bmp_app(reader: BMP3XX_Reader) -> Microdot:
    app = Microdot()

    @app.put("/sensors/cmd")
    async def sensor_cmd(request: Request) -> "ar.ResponseEnvelope":
        data, err = ar.parse_cmd_request(request, ["setBMP"])
        if err is not None:
            return err
        assert data is not None
        fields = {k: v for k, v in data.items() if k != "cmd"}
        return ar.make_response(0, result=await ar.handle_set_cmd(reader, fields, reader.get_cfg_schema()))

    return app


def test_real_microdot_setter_end_to_end_i2c_bus_fault_surfaces_as_failed_not_500() -> None:
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = BMP3XX_Reader(i2c, address=0x77, cfg_path=_tmp_cfg_dir())
    run(reader.cfgmgr.setup())
    _nak_i2c_address(i2c, 0x77)  # bus genuinely unreachable, like a dead/disconnected sensor
    app = _bmp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setBMP", "PresOvers": 8})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200  # our own precise envelope, not a raised exception or bare 500
    body = json.loads(res.body)
    assert body["res"] == "OK"  # the request itself was validly processed and dispatched
    assert body["result"] == {"PresOvers": "Failed"}
    # asy_base_classes.py's failed-push recovery chain corrects the persisted value back rather than leaving it
    # at the requested-but-never-applied 8. This is a fresh reader with the bus dead from the start, so the
    # pre-write snapshot rung resolves to the schema default (1), the chain's last rung.
    #
    # Complements test_asy_bmp3xx_driver.py's own test, which distinguishes the pre-write-snapshot rung from
    # this one directly.
    assert run(reader.cfgmgr.get_dict(["PresOvers"])) == {"PresOvers": 1}


def test_real_microdot_setter_end_to_end_write_only_fault_recovers_via_live_getter() -> None:
    # Same real dispatch path as the test above, but with a narrower, more realistic fault - the write half
    # only - that leaves the registered getter functional, proving the getter rung resolves end to end
    # through a real Microdot request, not only when driven synthetically at the driver level.
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    _register_device(i2c, 0x77)
    reader = BMP3XX_Reader(i2c, address=0x77, cfg_path=_tmp_cfg_dir())
    run(reader.cfgmgr.setup())
    run(reader._bmp.set_pressure_oversampling(2))  # desync: real sensor register = 2, cfgmgr = 1 (default)
    assert run(reader.cfgmgr.get_dict(["PresOvers"])) == {"PresOvers": 1}

    _fault_i2c_write(i2c, OSError(errno_mod.EIO, "no ACK on write"))
    app = _bmp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setBMP", "PresOvers": 8})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"PresOvers": "Failed"}
    # Recovered via the live getter (2, the sensor's real state) - neither the requested-but-failed
    # 8 nor cfgmgr's own pre-write snapshot (1).
    assert run(reader.cfgmgr.get_dict(["PresOvers"])) == {"PresOvers": 2}


# ---------------------------------------------------------------------------
# Real Microdot end-to-end for the getter path (asy_base_classes.py's _get_dict_cfg), same depth as
# the setter path above.
# ---------------------------------------------------------------------------


def _ntp_getter_app(client: NTPClient) -> Microdot:
    app = Microdot()

    @app.get("/time/config")
    async def timing_config(_request: Request) -> "dict[str, dict[str, Any]]":  # Microdot passes it positionally
        return await client.get_dict_cfg()

    return app


def test_real_microdot_getter_end_to_end_returns_schema_defaults() -> None:
    client = make_ntp_client()
    app = _ntp_getter_app(client)
    req = _make_request(app, "GET", "/time/config", None)
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body == {
        "NTP": {
            "NTPHost": "pool.ntp.org",
            "NTPOffset": 0,
            "NTPInterval": 12,
            "GMTOffset": 3600,
            "DSTOffset": 3600,
        },
    }


def test_real_microdot_getter_end_to_end_reflects_a_prior_write() -> None:
    client = make_ntp_client()
    app = _ntp_getter_app(client)
    run(client._set_dict_cfg({"NTPHost": "time.example.org"}, client.get_cfg_schema()))
    req = _make_request(app, "GET", "/time/config", None)
    res = run(app.dispatch_request(req))
    body = json.loads(res.body)
    assert body["NTP"]["NTPHost"] == "time.example.org"


# ---------------------------------------------------------------------------
# Real Microdot end to end for NTPClient's SETTER path. asy_ntp_client.py's module docstring claims
# asy_base_classes.py's generic _set_dict_cfg() gives full setter support with no changes to that file, every
# field being persist-only.
#
# That claim was only ever exercised at the _set_dict_cfg() level; this proves it end to end through a real
# route shaped exactly like the real handler, post_asy_fct=ntp_force_sync included.
# ---------------------------------------------------------------------------


def _ntp_setter_app(client: NTPClient) -> Microdot:
    app = Microdot()

    @app.put("/time/cmd")
    async def timing_cmd(request: Request) -> "ar.ResponseEnvelope":
        data, err = ar.parse_cmd_request(request, ["setTiming"])
        if err is not None:
            return err
        assert data is not None
        fields = {k: v for k, v in data.items() if k != "cmd"}
        # post_asy_fct mirrors the real route: a changed NTP config must force an immediate resync
        # rather than waiting out the (up to 24h) NTPInterval window with the old settings.
        return ar.make_response(0, result=await ar.handle_set_cmd(client, fields, client.get_cfg_schema(), post_asy_fct=client.ntp_force_sync))

    return app


def test_real_microdot_ntp_setter_end_to_end_persists_and_forces_a_resync() -> None:
    client = make_ntp_client()
    client._ntp_retries = 3  # a failing-sync streak in progress; ntp_force_sync() clears it to 0
    app = _ntp_setter_app(client)
    req = _make_request(app, "PUT", "/time/cmd", {"cmd": "setTiming", "NTPHost": "time.example.org", "GMTOffset": 7200})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"NTPHost": "Valid", "GMTOffset": "Valid"}
    # Actually persisted, not just reported valid - the half of the docstring's "full setter
    # support" claim a response envelope alone can't prove.
    stored = run(client.cfgmgr.get_dict(["NTPHost", "GMTOffset", "DSTOffset"]))
    assert stored == {"NTPHost": "time.example.org", "GMTOffset": 7200, "DSTOffset": 3600}
    assert client._ntp_retries == 0  # post_asy_fct fired


def test_real_microdot_ntp_setter_end_to_end_out_of_range_field_is_rejected_per_field() -> None:
    # Per-field detail, whole-request still OK/200 - and, since nothing was actually applied, the
    # post_asy_fct resync hook must not fire either (handle_set_cmd only runs it on a real change).
    client = make_ntp_client()
    client._ntp_retries = 3
    app = _ntp_setter_app(client)
    req = _make_request(app, "PUT", "/time/cmd", {"cmd": "setTiming", "GMTOffset": 99999})  # max is 43200
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"GMTOffset": "Invalid"}
    assert run(client.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 3600}  # untouched default
    assert client._ntp_retries == 3  # no change, no forced resync


# ---------------------------------------------------------------------------
# Real Microdot end to end for SGP40's setter surface, the third _set_dict_cfg-backed sensor route.
# ResetVOC is the interesting one: a command-only, never-persisted trigger field dispatched through the
# same generic path as an ordinary persisted field, only ever driven directly before this.
# ---------------------------------------------------------------------------


_SgpComp = namedtuple("_SgpComp", ("Temp", "Hum"))


class _FakeCompSource:
    # Structural stand-in for temperature_source/humidity_source (SPECIFICATION.md Part C.14,
    # SPECIFICATION.md Part L.6.3) - only get_data() is exercised, matching
    # test_asy_sgp40_driver.py's own identical fixture.
    async def get_data(self) -> "Any":
        return _SgpComp(25.0, 50.0)


def make_sgp_reader() -> "tuple[SGP40_Reader, I2C]":
    # Same construction as test_asy_sgp40_driver.py's own make_reader()/test_notification_sgp40_
    # integration.py's make_sgp_reader(): a real SGP40_Reader over the real asy_i2c_driver.py I2C
    # wrapper, mocked only at tests/machine.py's raw-bus boundary.
    i2c = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    comp = _FakeCompSource()
    reader = SGP40_Reader(
        i2c,
        ValueRef(comp, "Temp"),
        ValueRef(comp, "Hum"),
        max_module_error=5,
        cfg_path=_tmp_cfg_dir(),
    )
    run(reader.cfgmgr.setup())
    return reader, i2c


def _break_cfg_file(path: str) -> None:
    # Replaces the config file with a directory of the same name, so write_config()'s own open(path, "w")
    # raises a real OSError (EISDIR) from the filesystem rather than a patched-in fake - the genuine
    # "persistence layer is broken" fault, and the SGP40 setter path's only real failure mode.
    os.remove(path)
    os.mkdir(path)


def _sgp_app(reader: SGP40_Reader) -> Microdot:
    app = Microdot()

    @app.put("/sensors/cmd")
    async def sensor_cmd(request: Request) -> "ar.ResponseEnvelope":
        data, err = ar.parse_cmd_request(request, ["setSGP"])
        if err is not None:
            return err
        assert data is not None
        fields = {k: v for k, v in data.items() if k != "cmd"}
        return ar.make_response(0, result=await ar.handle_set_cmd(reader, fields, reader.get_cfg_schema()))

    return app


def test_real_microdot_sgp40_setter_end_to_end_reset_voc_round_trips() -> None:
    reader, _i2c = make_sgp_reader()
    app = _sgp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSGP", "ResetVOC": True, "BackupPeriod": 5})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body == {"res": "OK", "code": 0, "descr": "Command executed", "result": {"ResetVOC": "Valid", "BackupPeriod": "Valid"}}
    assert reader._reset_pending is True  # the command-only field's push callback really fired
    # The ordinary field alongside it persisted; the trigger field never enters cfgmgr's storage at
    # all (get_dict() is all-or-nothing per key, so asking for it would return None for the pair).
    assert run(reader.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}
    assert run(reader.cfgmgr.get_dict(["ResetVOC"])) is None


def test_real_microdot_sgp40_setter_end_to_end_i2c_bus_fault_still_succeeds_and_never_500s() -> None:
    # Deliberate difference from the BMP3xx equivalent above, worth stating rather than leaving as an
    # untested assumption: SGP40's whole setter surface is bus-independent. Three fields are persist-only,
    # and ResetVOC's push callback only arms two in-RAM flags for _read_loop() to act on later.
    #
    # No I2C transaction happens anywhere in the request path, so a genuinely dead bus - the same fault that
    # makes BMP3xx report "Failed" - must still produce a plain 200/"Valid", and certainly never a raise or
    # a bare Microdot 500.
    reader, i2c = make_sgp_reader()
    _nak_i2c_address(i2c, 0x59)  # SGP40's own address stops acking, like a dead/disconnected sensor
    app = _sgp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSGP", "ResetVOC": True})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"ResetVOC": "Valid"}
    assert reader._reset_pending is True  # armed for _read_loop(), which is where the bus fault will surface


def test_real_microdot_sgp40_setter_end_to_end_write_fault_surfaces_as_failed_not_500() -> None:
    # SGP40's real broken-persistence-layer path, as opposed to the bus fault above. WP5 (SPECIFICATION.md
    # Part F.2): write_config() no longer touches the filesystem inline - it validates and stages, then
    # hands the open()/json.dump() to an independent task, decoupled from this request entirely.
    #
    # A broken persistence layer is therefore invisible to asy_base_classes.py's "persisted" check: the response
    # reports the ordinary Valid outcome, and the trigger field's push callback fires as it would on a
    # healthy write, its correctness not depending on a disk write it is unrelated to.
    #
    # The fault only surfaces later, as a logged errno - never back through this response, and never as a
    # raise or a bare Microdot 500.
    reader, _i2c = make_sgp_reader()
    _break_cfg_file(reader.cfgmgr._config_file)
    app = _sgp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSGP", "BackupPeriod": 5, "ResetVOC": True})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"  # the request itself was validly processed and dispatched
    assert body["result"] == {"BackupPeriod": "Valid", "ResetVOC": "Valid"}
    assert reader._reset_pending is True  # pushed live regardless of the still-pending, doomed flash write
    run(reader.cfgmgr.flush_pending())  # now the deferred flush actually runs, and fails (EISDIR)
    # Never made it to disk, but stays in effect (SPECIFICATION.md C.7.3) - and the failure is on record.
    assert run(reader.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}
    nums = run(reader.cfgmgr.pr.get_log())[reader.cfgmgr.name]["ErrNum"]
    assert isinstance(nums, list) and nums[-1] == code("E", "CFG_FILE_WRITE")


# ---------------------------------------------------------------------------
# Real Microdot end to end for SCD30, whose config store is the chip itself: the route hands the body to the
# real SCD30_Reader._set_dict_cfg(), which compares against a chip snapshot and writes only what changed, in
# a fixed order. Each snapshot is six register replies queued on the fake bus before the request.
# ---------------------------------------------------------------------------


async def _simulated_set_scd_endpoint(reader: SCD30_Reader, request: "ar._RequestLike") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setSCD"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    return ar.make_response(0, result=await reader._set_dict_cfg(fields, reader.get_cfg_schema()))


def _scd_app(reader: SCD30_Reader) -> Microdot:
    app = Microdot()

    @app.put("/sensors/cmd")
    async def sensor_cmd(request: Request) -> "ar.ResponseEnvelope":
        return await _simulated_set_scd_endpoint(reader, request)

    return app


def make_scd_reader() -> SCD30_Reader:
    # Same construction as test_asy_scd30_driver.py's own make_reader(): a real SCD30_Reader over
    # the real asy_i2c_driver.py I2C wrapper and tests/machine.py's fake bus/Pin.
    return SCD30_Reader(I2C(0, scl_pin=1, sda_pin=0, frequency=100000), irq_pin=5, trigger_s=3, max_module_error=5)


def _queue_scd_snapshot(reader: SCD30_Reader) -> None:
    # One config snapshot (word + CRC-8 each, Interface Description 1.1.3): TempOffset 0, MeasInterval 2,
    # AmbPres 0, Altitude 0, ForceCalRef 400, SelfCal 0 - the chip's own power-up values.
    real_i2c = reader._scd._i2c_scd30.i2c_device.i2c._i2c
    assert real_i2c is not None
    for value in (0, 2, 0, 0, 400, 0):
        payload = struct.pack(">H", value)
        crc = run(CRC8().add(bytearray(payload)))
        assert crc is not None
        real_i2c.read_queue.append(payload + bytes([crc[-1]]))


def _scd_writes(reader: SCD30_Reader) -> "list[bytes]":
    # The command frames that changed a setting (5-byte argument frames and the bare stop), in bus order;
    # the snapshot's own 2-byte register-address writes are left out.
    from machine import I2C as _FakeI2C

    real_i2c = reader._scd._i2c_scd30.i2c_device.i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    return [entry[2] for entry in real_i2c.log if entry[0] == "writeto" and (len(entry[2]) == 5 or entry[2] == b"\x01\x04")]


def _fault_next_i2c_write(reader: SCD30_Reader, exc: Exception) -> None:
    # One-shot: fails only the *next* writeto() on this bus (tests/machine.py's inject_fault is a FIFO
    # of one exception per matching call, unlike _nak_i2c_address's permanent per-address NAK).
    from machine import I2C as _FakeI2C

    real_i2c = reader._scd._i2c_scd30.i2c_device.i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    real_i2c.inject_fault("writeto", exc)


def test_real_microdot_scd30_put_writes_each_field_through_the_real_driver() -> None:
    # One request per field: "Valid" and that field's own command word on the bus (Interface Description 1.4).
    cases: tuple[tuple[str, cm.CfgValue, bytes], ...] = (
        ("TempOffset", 4.5, b"\x54\x03"),
        ("MeasInterval", 10, b"\x46\x00"),
        ("AmbPres", 1013, b"\x00\x10"),
        ("Altitude", 200, b"\x51\x02"),
        ("ForceCalRef", 500, b"\x52\x04"),
        ("SelfCal", True, b"\x53\x06"),
        ("ContMeas", False, b"\x01\x04"),
    )
    for key, value, word in cases:
        reader = make_scd_reader()
        _queue_scd_snapshot(reader)
        app = _scd_app(reader)
        res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", key: value})))
        assert res.status_code == 200
        assert json.loads(res.body)["result"] == {key: "Valid"}, key
        writes = _scd_writes(reader)
        assert len(writes) == 1, key
        assert writes[0][:2] == word, key


def test_real_microdot_scd30_put_applies_several_fields_in_the_fixed_order() -> None:
    reader = make_scd_reader()
    _queue_scd_snapshot(reader)
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "ForceCalRef": 500, "AmbPres": 1013, "MeasInterval": 10})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"MeasInterval": "Valid", "AmbPres": "Valid", "ForceCalRef": "Valid"}
    # The real command frames reached the bus in the driver's fixed order, each carrying its own value;
    # the CRC byte is covered byte for byte against the Interface Description in test_asy_scd30_driver.py.
    writes = _scd_writes(reader)
    assert len(writes) == 3
    assert writes[0][:4] == b"\x46\x00\x00\x0a"  # 0x4600 set measurement interval = 10 s
    assert writes[1][:4] == b"\x00\x10\x03\xf5"  # 0x0010 ambient pressure = 1013 mBar
    assert writes[2][:4] == b"\x52\x04\x01\xf4"  # 0x5204 forced recalibration reference = 500 ppm


def test_real_microdot_scd30_put_of_the_ambpres_bypass_value_is_sent() -> None:
    # AmbPres 0 is the documented "compensation off" special value: valid, and sent even though it
    # equals the stored 0 (the command also starts continuous measurement).
    reader = make_scd_reader()
    _queue_scd_snapshot(reader)
    app = _scd_app(reader)
    res = run(app.dispatch_request(_make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "AmbPres": 0})))
    assert res.status_code == 200
    assert json.loads(res.body)["result"] == {"AmbPres": "Valid"}
    assert _scd_writes(reader) == [b"\x00\x10\x00\x00\x81"]


def test_real_microdot_scd30_put_out_of_range_field_never_reaches_the_bus() -> None:
    reader = make_scd_reader()
    _queue_scd_snapshot(reader)
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "MeasInterval": 1, "ForceCalRef": 500})  # MeasInterval min is 2
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"] == {"MeasInterval": "Invalid", "ForceCalRef": "Valid"}
    writes = _scd_writes(reader)
    assert len(writes) == 1  # only the valid field was ever sent
    assert writes[0][:4] == b"\x52\x04\x01\xf4"


def test_real_microdot_scd30_put_bus_fault_surfaces_as_failed_not_500() -> None:
    # A faulted chip write must surface as that field's own "Failed" inside a normal 200 envelope while
    # the other field still applies. The snapshot is stubbed so the one-shot fault lands on the first
    # write, MeasInterval (first in the fixed order), and leaves AmbPres' write untouched.
    reader = make_scd_reader()

    async def stored() -> "tuple[float, int, int, int, int, bool]":
        return 0.0, 2, 0, 0, 400, False

    reader._scd.get_config_snapshot = stored  # type: ignore[method-assign]
    _fault_next_i2c_write(reader, OSError(errno_mod.EIO, "no ACK on write"))
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "MeasInterval": 10, "AmbPres": 1013})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"  # the request itself was validly processed and dispatched
    assert body["result"] == {"MeasInterval": "Failed", "AmbPres": "Valid"}
    writes = _scd_writes(reader)
    assert len(writes) == 1  # the faulted write never made it into the bus log at all
    assert writes[0][:4] == b"\x00\x10\x03\xf5"
    # The fault is real and counted on SCD30's own error log (CHIP_SET), not swallowed behind the 200.
    log = run(reader.get_error_counter())
    err_nums = log["SCD30"]["ErrNum"]
    assert isinstance(err_nums, list)
    assert err_nums[-1] == code("E", "CHIP_SET")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
