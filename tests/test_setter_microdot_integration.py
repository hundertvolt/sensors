"""End-to-end integration tests for the setter generalization work: api_response.py's
parse_cmd_request()/handle_set_cmd() driven against mocked Microdot request data (fine/partial/
garbage), then against a real ext/microdot.py (v2.6.2) Microdot app wired the way sensortask-*.py
will eventually wire it - a real AsyConnTime (WiFi) reader for the setter path, a real
AsyNtpClient reader for both the getter and the setter path, a real BMP3xx_Reader/SGP40_Reader for
the schema-driven sensor setters, and a real SCD30_Reader for the one sensor whose REST surface is
hand-rolled per field instead of schema-driven. Only test-local Microdot apps are constructed here;
improved-quality/sensortask-wozi.py itself is never touched (see CLAUDE.md's hard rule on editing
improved-quality/ source files) - anything of its wiring that has to be exercised is reimplemented
locally (_wifi_field_schema()/_SCD_SET_FIELDS/_scd_apply_field below), never imported.
"""

import asyncio
import errno as errno_mod
import json
import os
import sys

# scripts/test.sh's own MICROPYPATH ("src:tests:.frozen") deliberately doesn't include ext/ - that
# would be a scripts/ change, which CLAUDE.md's "Pre-push verification" requires a full clean-
# chroot re-verification for. Extending sys.path at runtime, scoped to this one file, reaches the
# same real ext/microdot.py without touching scripts/test.sh, MICROPYPATH, or pyproject.toml at
# all - confirmed directly against the pinned interpreter that a plain sys.path.insert() before the
# import resolves it correctly, the same as MICROPYPATH would.
sys.path.insert(0, "ext")

# ext/ isn't on this project's mypy search path yet (see pyproject.toml's [tool.mypy]) - same gap
# as the pre-existing improved-quality/api_helpers.py and improved-quality/sensortask-wozi.py
# imports of this module.
from microdot import Microdot, Request  # type: ignore[import-not-found]  # noqa: E402

import api_response as ar
import config_manager as cm
from asy_bmp3xx_driver import BMP3xx_Reader
from asy_i2c_driver import I2C
from asy_ntp_client import AsyNtpClient
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_wifi_service import AsyConnTime

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # Sweeps pre-existing <prefix>* scratch dirs left behind by an earlier scripts/test.sh run on
    # this machine - _next_dir always restarts at 0 per process, so without this a later run
    # silently reuses an earlier run's real, persisted config_*.cfg files instead of a genuinely
    # fresh directory. See tests/test_sensortask_wozi.py's own _sweep_stale_tmp_dirs() for the full
    # root-cause writeup (this exact _tmp_cfg_dir() shape is copy-pasted across every test file with
    # its own _TMP_DIR/_next_dir pair - same fix applied uniformly to each).
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return  # tests/_tmp itself doesn't exist yet - nothing to clean
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("msi_")


def _tmp_cfg_dir() -> str:
    # tests/_tmp is never wiped between local invocations of this file (unlike CI's always-fresh
    # checkout - same reasoning as test_asy_sgp40_driver.py's own _sgp_cfg_dir()) - _next_dir alone
    # isn't enough to guarantee a fresh config file, since a directory name repeats across runs of
    # the same process. Clear any config file left over from a previous local run explicitly.
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/msi_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    for stale in ("config_WIFI.cfg", "config_NTP.cfg", "config_BMP3XX.cfg", "config_SGP40.cfg"):
        try:
            os.remove(path + "/" + stale)
        except OSError:
            try:
                # _break_cfg_file() below deliberately leaves a *directory* behind under this name
                # (that's how it makes a real config write fail) - os.remove() can't clear that one,
                # and leaving it would make the next local run's ConfigManager.setup() reject the
                # config outright ("exists but is not a file") instead of starting fresh.
                os.rmdir(path + "/" + stale)
            except OSError:
                pass  # no stale file or directory - already fresh
    return path + "/"


def make_wifi_client() -> AsyConnTime:
    client = AsyConnTime(led_pin=None, cfg_path=_tmp_cfg_dir())
    run(client.cfgmgr.setup())
    return client


def make_ntp_client() -> AsyNtpClient:
    wifi_mode_lock = asyncio.Lock()
    client = AsyNtpClient(
        wifi_mode_lock,
        network_available=lambda: True,
        get_dns_server=lambda: None,
        cfg_path=_tmp_cfg_dir(),
    )
    run(client.cfgmgr.setup())
    return client


class _FakeRequest:
    # Same minimal stand-in as test_api_response.py's own - mocks only the .json property boundary.
    def __init__(self, json_value: "Any", raise_instead: bool = False) -> None:
        self._json_value = json_value
        self._raise_instead = raise_instead

    @property
    def json(self) -> "Any":
        if self._raise_instead:
            raise ValueError("malformed body")
        return self._json_value


# ---------------------------------------------------------------------------
# Simulated endpoint handler - combines parse_cmd_request()+handle_set_cmd() exactly the way a real
# sensortask-*.py route will (mirrors the real, existing /net/cmd "setNetwork" handler's shape:
# one cmd, a fixed field list, one post_fct hook) - driven against mocked request data of varying
# quality (fine/partial/garbage), without a real Microdot app or real sockets.
#
# AsyConnTime owns one schema/cfgmgr for all of SSID/PW/Country/Hostname/LedWifiOn, but the real
# /net/cmd (setNetwork) and /led/cmd (setWiFiLED) routes each only own their own subset of those
# fields (improved-quality/sensortask-wozi.py's own _cfg_subset()) - passing the *whole* schema to
# both would let setNetwork accept/persist LedWifiOn (and spuriously fire reconnect_wifi() for an
# LED-only change) and let setWiFiLED silently accept/persist SSID/PW/Country/Hostname with no
# reconnect at all. _wifi_field_schema() below mirrors that same scoping locally, since this file
# never imports sensortask-wozi.py itself (see its own module docstring).
# ---------------------------------------------------------------------------


def _wifi_field_schema(client: AsyConnTime, keys: "tuple[str, ...]") -> "cm.ConfigSchema":
    fields = cm.schema_dict(client.get_cfg_schema())
    return tuple(fields[k] for k in keys if k in fields)


async def _simulated_set_network_endpoint(client: AsyConnTime, request: "Any") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setNetwork"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    net_schema = _wifi_field_schema(client, ("SSID", "PW", "Country", "Hostname"))
    return await ar.handle_set_cmd(
        client, fields, net_schema, post_fct=client.reconnect_wifi, ok_descr="Network settings updated"
    )


async def _simulated_set_wifi_led_endpoint(client: AsyConnTime, request: "Any") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setWiFiLED"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    led_schema = _wifi_field_schema(client, ("LedWifiOn",))
    return await ar.handle_set_cmd(client, fields, led_schema)


def test_mocked_request_fine_data_applies_and_reports_ok() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "Hostname": "NewHost", "SSID": "MyNet", "PW": "supersecret", "Country": "US"})
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["code"] == 0
    assert resp["descr"] == "Network settings updated"
    assert resp["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Valid", "Country": "Valid"}
    assert client.reconn_wifi is True  # post_fct fired
    stored = run(client.cfgmgr.get_dict(["Hostname", "SSID", "PW", "Country"]))
    assert stored == {"Hostname": "NewHost", "SSID": "MyNet", "PW": "supersecret", "Country": "US"}


def test_mocked_request_partially_fine_data_reports_mixed_per_field_results() -> None:
    client = make_wifi_client()
    req = _FakeRequest(
        {"cmd": "setNetwork", "Hostname": "NewHost", "SSID": "MyNet", "PW": "short", "Country": "United States"}
    )
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"  # still overall OK - per-field detail lives in "result"
    assert resp["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Invalid", "Country": "Invalid"}
    assert client.reconn_wifi is True  # still fires: at least one field (Hostname/SSID) changed
    stored = run(client.cfgmgr.get_dict(["PW", "Country"]))
    assert stored == {"PW": "", "Country": "DE"}  # both rejected, left at their defaults


def test_mocked_request_garbage_body_is_rejected_before_dispatch() -> None:
    client = make_wifi_client()
    req = _FakeRequest([1, 2, 3])  # valid JSON, wrong shape entirely
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}
    assert client.reconn_wifi is False  # never reached the dispatch step at all


def test_mocked_request_unparseable_body_is_rejected_before_dispatch() -> None:
    client = make_wifi_client()
    req = _FakeRequest(None, raise_instead=True)
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["code"] == 1
    assert client.reconn_wifi is False


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
    # Final project decision: an unrecognized field key (as opposed to an unrecognized *command*)
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
    assert client.reconn_wifi is False  # nothing changed, post_fct never fires


# ---------------------------------------------------------------------------
# setNetwork/setWiFiLED field scoping - regression coverage for the cross-route schema leakage bug
# found in improved-quality/sensortask-wozi.py: AsyConnTime owns one schema for both routes'
# fields, so passing the *whole* schema to either route (instead of each route's own real subset)
# would let setNetwork accept/persist LedWifiOn (and spuriously reconnect for an LED-only change)
# and let setWiFiLED silently accept/persist SSID/PW/Country/Hostname with no reconnect at all.
# ---------------------------------------------------------------------------


def test_mocked_set_network_rejects_led_wifi_on_and_does_not_reconnect() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "LedWifiOn": False})  # not setNetwork's field
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["result"] == {"LedWifiOn": "Invalid"}
    assert client.reconn_wifi is False  # nothing setNetwork actually owns changed


def test_mocked_set_network_hostname_change_still_reconnects_alongside_rejected_led_field() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setNetwork", "Hostname": "NewHost", "LedWifiOn": False})
    resp = run(_simulated_set_network_endpoint(client, req))
    assert resp["result"] == {"Hostname": "Valid", "LedWifiOn": "Invalid"}
    assert client.reconn_wifi is True  # Hostname is a real setNetwork field and did change


def test_mocked_set_wifi_led_rejects_ssid_and_leaves_it_untouched() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setWiFiLED", "SSID": "Hacked"})  # not setWiFiLED's field
    resp = run(_simulated_set_wifi_led_endpoint(client, req))
    assert resp["res"] == "OK"
    assert resp["result"] == {"SSID": "Invalid"}
    assert run(client.cfgmgr.get_dict(["SSID"])) == {"SSID": ""}  # untouched default, not "Hacked"


def test_mocked_set_wifi_led_applies_its_own_field_without_reconnecting() -> None:
    client = make_wifi_client()
    req = _FakeRequest({"cmd": "setWiFiLED", "LedWifiOn": False})
    resp = run(_simulated_set_wifi_led_endpoint(client, req))
    assert resp["result"] == {"LedWifiOn": "Valid"}
    assert run(client.cfgmgr.get_dict(["LedWifiOn"])) == {"LedWifiOn": False}
    # setWiFiLED (unlike setNetwork) passes no post_fct at all - toggling the WiFi status LED must
    # never reconnect the WiFi connection.
    assert client.reconn_wifi is False


def test_real_microdot_set_network_rejects_led_field_end_to_end() -> None:
    # Reuses the module's own _wifi_app() helper (defined further below, alongside the other real-
    # Microdot setter tests) - already wires /net/cmd to _simulated_set_network_endpoint.
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(app, "PUT", "/net/cmd", {"cmd": "setNetwork", "LedWifiOn": True})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"] == {"LedWifiOn": "Invalid"}
    assert client.reconn_wifi is False


# ---------------------------------------------------------------------------
# Real ext/microdot.py (v2.6.2) end-to-end - a real Microdot() app with a real @app.put route,
# dispatched through the library's own real dispatch_request() (routing, before/after-request
# hooks, exception handling, dict->JSON Response coercion - see CLAUDE.md's "Microdot / REST
# layer" section), driven with a real Request object rather than a mock. No real TCP socket is
# opened - Request is constructed directly, the same shape Request.create() itself builds from a
# socket stream, without needing one here.
# ---------------------------------------------------------------------------


def _make_request(app: Microdot, method: str, path: str, json_body: "dict[str, Any] | None") -> Request:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    return Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)


def _wifi_app(client: AsyConnTime) -> Microdot:
    app = Microdot()

    @app.put("/net/cmd")
    async def network_cmd(request: Request) -> "ar.ResponseEnvelope":
        return await _simulated_set_network_endpoint(client, request)

    return app


def test_real_microdot_setter_end_to_end_valid_request() -> None:
    client = make_wifi_client()
    app = _wifi_app(client)
    req = _make_request(
        app, "PUT", "/net/cmd", {"cmd": "setNetwork", "Hostname": "RealHost", "SSID": "RealNet", "PW": "supersecret", "Country": "US"}
    )
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Valid", "Country": "Valid"}
    assert client.reconn_wifi is True
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
    req._body = b"{not valid json"  # force a real malformed body past Request's own parsing
    req.content_length = len(req._body)
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
    # Defense-in-depth proof at the opposite end from handle_set_cmd's own try/except: even a
    # handler that bypasses api_response.py entirely and raises directly is still contained by
    # Microdot itself (see CLAUDE.md's "Microdot / REST layer" section) - the server never crashes.
    app = Microdot()

    @app.put("/boom")
    async def boom(request: Request) -> None:
        raise RuntimeError("simulated handler bug")

    print("(expected) the traceback below is Microdot's own internal exception logging, triggered on purpose")
    req = _make_request(app, "PUT", "/boom", {})
    res = run(app.dispatch_request(req))
    assert res.status_code == 500


# ---------------------------------------------------------------------------
# Real Microdot end-to-end with a real sensor driver (BMP3xx), not just the software-only WiFi/NTP
# readers above - proves a genuine hardware/communication fault (a wedged I2C bus, the same failure
# mode a disconnected/dead sensor produces) propagates all the way through _set_dict_cfg's push
# callback, handle_set_cmd's envelope, and real Microdot dispatch as a per-field "Failed" status
# inside a normal 200 JSON response - never as a raised exception or a bare Microdot 500. This is
# the one place CLAUDE.md's "Microdot / REST layer" blanket-catch guarantee and SPECIFICATION.md Part C.4's
# layer-3 "never raises" contract are proven to hold *together*, end-to-end, not just individually.
# ---------------------------------------------------------------------------


def _nak_i2c_address(i2c: I2C, address: int) -> None:
    # Same real-fake-I2C access as test_asy_bmp3xx_driver.py's own fake() helper - i2c._i2c is
    # typed I2C-or-None (only None before setup()/first use), so this narrows it the same way
    # fake()'s own -> FakeI2C return annotation does, rather than an inline type: ignore at the
    # call site (which mypy would flag as "union-attr", not "attr-defined", and is easy to get
    # subtly wrong - confirmed directly by getting exactly that mismatch here first).
    from machine import I2C as _FakeI2C

    real_i2c = i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    real_i2c.nak_addresses.add(address)


def _fault_i2c_write(i2c: I2C, exc: Exception) -> None:
    # Narrower than _nak_i2c_address above: fails only the write half of a read-modify-write
    # register access (writeto_mem), leaving reads - and therefore a registered _get_callbacks
    # getter - fully functional. Same i2c._i2c narrowing as _nak_i2c_address.
    from machine import I2C as _FakeI2C

    real_i2c = i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    real_i2c.inject_fault("writeto_mem", exc)


def _bmp_app(reader: BMP3xx_Reader) -> Microdot:
    app = Microdot()

    @app.put("/sensors/cmd")
    async def sensor_cmd(request: Request) -> "ar.ResponseEnvelope":
        data, err = ar.parse_cmd_request(request, ["setBMP"])
        if err is not None:
            return err
        assert data is not None
        fields = {k: v for k, v in data.items() if k != "cmd"}
        return await ar.handle_set_cmd(reader, fields, reader.get_cfg_schema())

    return app


def test_real_microdot_setter_end_to_end_i2c_bus_fault_surfaces_as_failed_not_500() -> None:
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = BMP3xx_Reader(i2c, address=0x77, cfg_path=_tmp_cfg_dir())
    run(reader.cfgmgr.setup())
    _nak_i2c_address(i2c, 0x77)  # bus genuinely unreachable, like a dead/disconnected sensor
    app = _bmp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setBMP", "PressOvers": 8})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200  # our own precise envelope, not a raised exception or bare 500
    body = json.loads(res.body)
    assert body["res"] == "OK"  # the request itself was validly processed and dispatched
    assert body["result"] == {"PressOvers": "Failed"}
    # base_classes.py's failed-push recovery chain corrects the persisted value back rather than
    # leaving it at the requested-but-never-applied 8. This is a fresh reader with the bus dead
    # from the start (no successful prior write, no getter registered), so the pre-write snapshot
    # rung itself resolves to the schema default (1) - the fallback chain's last rung, complementing
    # test_asy_bmp3xx_driver.py's own test which distinguishes the pre-write-snapshot rung from this
    # one directly.
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 1}


def test_real_microdot_setter_end_to_end_write_only_fault_recovers_via_live_getter() -> None:
    # Same real dispatch path as the test above, but with a narrower, more realistic fault (the
    # write half only, see _fault_i2c_write) that leaves the registered _get_callbacks getter
    # functional - proving the getter rung actually resolves end to end through a real Microdot
    # request, not just when synthetically driven at the base_classes.py/driver level.
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = BMP3xx_Reader(i2c, address=0x77, cfg_path=_tmp_cfg_dir())
    run(reader.cfgmgr.setup())
    run(reader.bmp.set_pressure_oversampling(2))  # desync: real sensor register = 2, cfgmgr = 1 (default)
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 1}

    _fault_i2c_write(i2c, OSError(errno_mod.EIO, "no ACK on write"))
    app = _bmp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setBMP", "PressOvers": 8})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"PressOvers": "Failed"}
    # Recovered via the live getter (2, the sensor's real state) - neither the requested-but-failed
    # 8 nor cfgmgr's own pre-write snapshot (1).
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 2}


# ---------------------------------------------------------------------------
# Real Microdot end-to-end for the getter path (base_classes.py's _get_dict_cfg), same depth as
# the setter path above.
# ---------------------------------------------------------------------------


def _ntp_getter_app(client: AsyNtpClient) -> Microdot:
    app = Microdot()

    @app.get("/time/config")
    async def timing_config(request: Request) -> "dict[str, dict[str, Any]]":
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
            "NTP_Host": "pool.ntp.org",
            "NTP_Offset_S": 0,
            "NTP_Interv_H": 12,
            "GMTOffset": 3600,
            "DSTOffset": 3600,
        }
    }


def test_real_microdot_getter_end_to_end_reflects_a_prior_write() -> None:
    client = make_ntp_client()
    app = _ntp_getter_app(client)
    run(client._set_dict_cfg({"NTP_Host": "time.example.org"}, client.get_cfg_schema()))
    req = _make_request(app, "GET", "/time/config", None)
    res = run(app.dispatch_request(req))
    body = json.loads(res.body)
    assert body["NTP"]["NTP_Host"] == "time.example.org"


# ---------------------------------------------------------------------------
# Real Microdot end-to-end for AsyNtpClient's SETTER path. asy_ntp_client.py's own module
# docstring claims "base_classes.py's generic _set_dict_cfg() already provides full setter support
# with zero changes to this file (no self._push_callbacks entries registered)" - every field is
# persist-only. That claim was only ever exercised at the _set_dict_cfg() level (the getter section
# above, and test_asy_ntp_client.py's own tests); this proves it end to end through a real Microdot
# route shaped exactly like the real /time/cmd handler, post_asy_fct=ntp_force_sync included.
# ---------------------------------------------------------------------------


def _ntp_setter_app(client: AsyNtpClient) -> Microdot:
    app = Microdot()

    @app.put("/time/cmd")
    async def timing_cmd(request: Request) -> "ar.ResponseEnvelope":
        data, err = ar.parse_cmd_request(request, ["setTiming"])
        if err is not None:
            return err
        assert data is not None
        fields = {k: v for k, v in data.items() if k != "cmd"}
        # post_asy_fct mirrors the real route: a changed NTP config must force an immediate resync
        # rather than waiting out the (up to 24h) NTP_Interv_H window with the old settings.
        return await ar.handle_set_cmd(client, fields, client.get_cfg_schema(), post_asy_fct=client.ntp_force_sync)

    return app


def test_real_microdot_ntp_setter_end_to_end_persists_and_forces_a_resync() -> None:
    client = make_ntp_client()
    client.ntp_retries = 3  # a failing-sync streak in progress; ntp_force_sync() clears it to 0
    app = _ntp_setter_app(client)
    req = _make_request(app, "PUT", "/time/cmd", {"cmd": "setTiming", "NTP_Host": "time.example.org", "GMTOffset": 7200})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"NTP_Host": "Valid", "GMTOffset": "Valid"}
    # Actually persisted, not just reported valid - the half of the docstring's "full setter
    # support" claim a response envelope alone can't prove.
    stored = run(client.cfgmgr.get_dict(["NTP_Host", "GMTOffset", "DSTOffset"]))
    assert stored == {"NTP_Host": "time.example.org", "GMTOffset": 7200, "DSTOffset": 3600}
    assert client.ntp_retries == 0  # post_asy_fct fired


def test_real_microdot_ntp_setter_end_to_end_out_of_range_field_is_rejected_per_field() -> None:
    # Per-field detail, whole-request still OK/200 - and, since nothing was actually applied, the
    # post_asy_fct resync hook must not fire either (handle_set_cmd only runs it on a real change).
    client = make_ntp_client()
    client.ntp_retries = 3
    app = _ntp_setter_app(client)
    req = _make_request(app, "PUT", "/time/cmd", {"cmd": "setTiming", "GMTOffset": 99999})  # max is 43200
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"GMTOffset": "Invalid"}
    assert run(client.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 3600}  # untouched default
    assert client.ntp_retries == 3  # no change, no forced resync


# ---------------------------------------------------------------------------
# Real Microdot end-to-end for SGP40's own setter surface (the third and last _set_dict_cfg-backed
# sensor route, alongside WiFi's and BMP3xx's above). SGPResetVOC is the interesting one: a
# command-only, never-persisted trigger field (asy_sgp40_driver.py's _VAL_RESET) dispatched through
# the very same generic path as an ordinary persisted field - only ever exercised by direct
# _set_dict_cfg() calls in test_asy_sgp40_driver.py before this, never through a real route.
# ---------------------------------------------------------------------------


async def _sgp_comp_data() -> "list[int | float | None]":
    return [25.0, 50.0]


def make_sgp_reader() -> "tuple[SGP40_Reader, I2C]":
    # Same construction as test_asy_sgp40_driver.py's own make_reader()/test_notification_sgp40_
    # integration.py's make_sgp_reader(): a real SGP40_Reader over the real asy_i2c_driver.py I2C
    # wrapper, mocked only at tests/machine.py's raw-bus boundary.
    i2c = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    reader = SGP40_Reader(i2c, _sgp_comp_data, max_module_error=5, cfg_path=_tmp_cfg_dir())
    run(reader.cfgmgr.setup())
    return reader, i2c


def _break_cfg_file(path: str) -> None:
    # Replaces the config file with a directory of the same name, so ConfigManager.write_config()'s
    # own open(path, "w") raises a real OSError (EISDIR) from the filesystem rather than a patched-in
    # fake - the genuine "persistence layer is broken" fault, the SGP40 setter path's only real
    # failure mode (see the fault test below for why an I2C fault isn't one).
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
        return await ar.handle_set_cmd(reader, fields, reader.get_cfg_schema())

    return app


def test_real_microdot_sgp40_setter_end_to_end_reset_voc_round_trips() -> None:
    reader, _i2c = make_sgp_reader()
    app = _sgp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSGP", "SGPResetVOC": True, "BackupPeriod": 5})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body == {"res": "OK", "code": 0, "descr": "Command executed", "result": {"SGPResetVOC": "Valid", "BackupPeriod": "Valid"}}
    assert reader.reset is True  # the command-only field's push callback really fired
    # The ordinary field alongside it persisted; the trigger field never enters cfgmgr's storage at
    # all (get_dict() is all-or-nothing per key, so asking for it would return None for the pair).
    assert run(reader.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}
    assert run(reader.cfgmgr.get_dict(["SGPResetVOC"])) is None


def test_real_microdot_sgp40_setter_end_to_end_i2c_bus_fault_still_succeeds_and_never_500s() -> None:
    # Deliberate difference from the BMP3xx equivalent above, and worth stating explicitly rather
    # than leaving as an untested assumption: SGP40's whole setter surface is bus-independent.
    # BackupPeriod/BackupMaxAge/WaitTimeNTP are persist-only (no push callback at all), and
    # SGPResetVOC's own push callback (_push_reset_voc -> reset_voc) only arms two in-RAM flags for
    # read_loop() to act on later - no I2C transaction happens anywhere in the request path. So a
    # genuinely dead bus (the same fault that makes BMP3xx report "Failed") must still produce a
    # plain 200/"Valid" here, and must certainly never raise or surface as a bare Microdot 500.
    reader, i2c = make_sgp_reader()
    _nak_i2c_address(i2c, 0x59)  # SGP40's own address stops acking, like a dead/disconnected sensor
    app = _sgp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSGP", "SGPResetVOC": True})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"SGPResetVOC": "Valid"}
    assert reader.reset is True  # armed for read_loop(), which is where the bus fault will surface


def test_real_microdot_sgp40_setter_end_to_end_write_fault_surfaces_as_failed_not_500() -> None:
    # SGP40's real "Failed" path (see the bus-fault test above for why it isn't an I2C one): a
    # broken persistence layer. ConfigManager.write_config() catches its own OSError and reports the
    # whole write failed, so base_classes.py's _set_dict_cfg() marks every requested key "Failed" -
    # including the never-persisted trigger field, which correctly does *not* fire its push callback
    # off a failed write. Same assertion shape as the BMP3xx fault test: a normal 200 carrying
    # per-field detail, not a raised exception and not a bare Microdot 500.
    reader, _i2c = make_sgp_reader()
    _break_cfg_file(reader.cfgmgr.config_file)
    app = _sgp_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSGP", "BackupPeriod": 5, "SGPResetVOC": True})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"  # the request itself was validly processed and dispatched
    assert body["result"] == {"BackupPeriod": "Failed", "SGPResetVOC": "Failed"}
    assert reader.reset is False  # nothing was persisted, so nothing was pushed live either
    assert run(reader.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 1}  # still the default


# ---------------------------------------------------------------------------
# Real Microdot end-to-end for SCD30's bespoke per-field REST wiring. Unlike every other sensor,
# SCD30_Reader has no _set_dict_cfg/ConfigManager surface at all - its parameters live on the
# sensor's own NVM, not in a local cache (see asy_scd30_driver.py's "No local default either"
# comment) - so improved-quality/sensortask-wozi.py drives it through a hand-rolled
# (key, field, setter) loop instead. That loop is reimplemented locally below rather than imported,
# the same convention _wifi_field_schema() already follows in this file (see the module docstring);
# only the three fields this file actually exercises are mirrored, not all seven. Every SCD30 setter
# already returns bool and never raises (its own module docstring/SPECIFICATION.md Part C), so the
# Valid/Failed mapping is a plain bool check - the try/except is defense-in-depth against a future
# change to that contract, exactly as in the real file.
# ---------------------------------------------------------------------------

_FIELD_SCD_MEAS_INT: "cm.FieldSchema" = ("MeasInt", "int", 2, 2, 1800, None)
# special=0 matches SCD30's own documented AmbPres=0 "disable compensation" bypass value.
_FIELD_SCD_AMB_PRES: "cm.FieldSchema" = ("AmbPres", "int", 0, 700, 1400, 0)
_FIELD_SCD_FORCE_CAL_REF: "cm.FieldSchema" = ("ForceCalRef", "int", 400, 400, 2000, None)


def _scd_set_fields(
    reader: SCD30_Reader,
) -> "tuple[tuple[str, cm.FieldSchema, Callable[[Any], Coroutine[Any, Any, bool]]], ...]":
    # Bound per reader instance (the real file builds this once against its one module-level
    # scd_reader); iterated in a fixed order, which the one-shot bus fault below relies on.
    return (
        ("MeasInt", _FIELD_SCD_MEAS_INT, reader.set_measurement_interval),
        ("AmbPres", _FIELD_SCD_AMB_PRES, reader.set_ambient_pressure),
        ("ForceCalRef", _FIELD_SCD_FORCE_CAL_REF, reader.set_forced_recalibration_reference),
    )


async def _scd_apply_field(
    reader: SCD30_Reader,
    data: "dict[str, Any]",
    key: str,
    field: "cm.FieldSchema",
    setter: "Callable[[Any], Coroutine[Any, Any, bool]]",
) -> "str | None":
    if key not in data:
        return None  # not requested - omitted keys are left alone (project-wide convention)
    value = data[key]
    if cm.type_or_range_error(value, field):
        return "Invalid"
    try:
        applied = await setter(value)
    except Exception as e:  # setter is caller-supplied; its runtime behavior isn't statically known
        await reader.pr.err_s("Error setting", key, "on SCD30:", e, errno=30)
        applied = False
    return "Valid" if applied else "Failed"


async def _simulated_set_scd_endpoint(reader: SCD30_Reader, request: "Any") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setSCD"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    # Nothing here is persisted anywhere (the values live on the sensor), so there's no config file
    # to correct after a failed setter either - just validate, call, report.
    results: dict[str, Any] = {}
    for key, field, setter in _scd_set_fields(reader):
        status = await _scd_apply_field(reader, fields, key, field, setter)
        if status is not None:
            results[key] = status
    return ar.make_response(0, result=results)


def _scd_app(reader: SCD30_Reader) -> Microdot:
    app = Microdot()

    @app.put("/sensors/cmd")
    async def sensor_cmd(request: Request) -> "ar.ResponseEnvelope":
        return await _simulated_set_scd_endpoint(reader, request)

    return app


def make_scd_reader() -> SCD30_Reader:
    # Same construction as test_asy_scd30_driver.py's own make_reader(): a real SCD30_Reader over
    # the real asy_i2c_driver.py I2C wrapper and tests/machine.py's fake bus/Pin. No cfg_path -
    # SCD30_Reader has no ConfigManager of its own at all, which is the whole point of this section.
    return SCD30_Reader(I2C(0, scl_pin=1, sda_pin=0, frequency=100000), irq_pin=5, trigger_sec=3, max_module_error=5)


def _scd_writes(reader: SCD30_Reader) -> "list[bytes]":
    # The raw command frames that actually reached the bus, in order. Same fake-I2C access as
    # test_asy_scd30_driver.py's own reader_fake_i2c(), narrowed the way _nak_i2c_address does.
    from machine import I2C as _FakeI2C

    real_i2c = reader.scd.i2c_scd30.i2c_device.i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    return [entry[2] for entry in real_i2c.log if entry[0] == "writeto"]


def _fault_next_i2c_write(reader: SCD30_Reader, exc: Exception) -> None:
    # One-shot: fails only the *next* writeto() on this bus, so exactly one field of a multi-field
    # request faults while the rest still go through (tests/machine.py's inject_fault is a FIFO of
    # one exception per matching call, unlike _nak_i2c_address's permanent per-address NAK).
    from machine import I2C as _FakeI2C

    real_i2c = reader.scd.i2c_scd30.i2c_device.i2c._i2c
    assert isinstance(real_i2c, _FakeI2C)
    real_i2c.inject_fault("writeto", exc)


def test_real_microdot_scd30_per_field_setter_end_to_end_applies_every_field() -> None:
    reader = make_scd_reader()
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "MeasInt": 10, "AmbPres": 1013, "ForceCalRef": 500})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"
    assert body["result"] == {"MeasInt": "Valid", "AmbPres": "Valid", "ForceCalRef": "Valid"}
    # "Valid" alone would only prove the setter returned True - these confirm the real command
    # frames reached the real bus, in the loop's own field order, each carrying its own value
    # (command word + big-endian argument; the trailing CRC byte is already covered byte-for-byte
    # against the Interface Description's worked examples in test_asy_scd30_driver.py).
    writes = _scd_writes(reader)
    assert len(writes) == 3
    assert writes[0][:4] == b"\x46\x00\x00\x0a"  # 0x4600 set measurement interval = 10 s
    assert writes[1][:4] == b"\x00\x10\x03\xf5"  # 0x0010 ambient pressure = 1013 mBar
    assert writes[2][:4] == b"\x52\x04\x01\xf4"  # 0x5204 forced recalibration reference = 500 ppm


def test_real_microdot_scd30_per_field_setter_end_to_end_omitted_fields_are_left_alone() -> None:
    # The per-field loop walks all of its fields on every request; only the ones actually present in
    # the body may appear in the result envelope or touch the bus.
    reader = make_scd_reader()
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "AmbPres": 0})  # 0 = the documented bypass value
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    assert json.loads(res.body)["result"] == {"AmbPres": "Valid"}
    writes = _scd_writes(reader)
    assert len(writes) == 1
    assert writes[0][:4] == b"\x00\x10\x00\x00"


def test_real_microdot_scd30_per_field_setter_end_to_end_out_of_range_field_never_reaches_the_bus() -> None:
    reader = make_scd_reader()
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "MeasInt": 1, "ForceCalRef": 500})  # MeasInt min is 2
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["result"] == {"MeasInt": "Invalid", "ForceCalRef": "Valid"}
    writes = _scd_writes(reader)
    assert len(writes) == 1  # only the valid field was ever sent
    assert writes[0][:4] == b"\x52\x04\x01\xf4"


def test_real_microdot_scd30_per_field_setter_end_to_end_bus_fault_surfaces_as_failed_not_500() -> None:
    # SCD30's counterpart to the BMP3xx bus-fault test above, through the hand-rolled per-field loop
    # instead of handle_set_cmd(): a genuine bus fault on one field must surface as that field's own
    # "Failed" inside a normal 200 envelope - never a raised exception, never a bare Microdot 500 -
    # while every other field in the same request still applies. The fault is one-shot, so it lands
    # on MeasInt (the loop's first field) and leaves AmbPres' own write untouched.
    reader = make_scd_reader()
    _fault_next_i2c_write(reader, OSError(errno_mod.EIO, "no ACK on write"))
    app = _scd_app(reader)
    req = _make_request(app, "PUT", "/sensors/cmd", {"cmd": "setSCD", "MeasInt": 10, "AmbPres": 1013})
    res = run(app.dispatch_request(req))
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body["res"] == "OK"  # the request itself was validly processed and dispatched
    assert body["result"] == {"MeasInt": "Failed", "AmbPres": "Valid"}
    writes = _scd_writes(reader)
    assert len(writes) == 1  # the faulted write never made it into the bus log at all
    assert writes[0][:4] == b"\x00\x10\x03\xf5"
    # The fault is real and counted, on SCD30's own error log (errno=14, its set_measurement_interval
    # wrapper's own number) - not swallowed silently just because the response says 200.
    log = run(reader.get_error_counter())
    err_nums = log["SCD30"]["ErrNum"]
    assert isinstance(err_nums, list)
    assert err_nums[-1] == 14


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
