"""End-to-end integration tests for the setter generalization work: api_response.py's
parse_cmd_request()/handle_set_cmd() driven against mocked Microdot request data (fine/partial/
garbage), then against a real ext/microdot.py (v2.6.2) Microdot app wired the way sensortask-*.py
will eventually wire it - a real asy_conn_time (WiFi) reader for the setter path, a real
asy_ntp_client reader for the getter path. Only a test-local Microdot app is constructed here;
improved-quality/sensortask-wozi.py itself is never touched (see CLAUDE.md's hard rule on editing
improved-quality/ source files).
"""

import asyncio
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
from asy_ntp_client import asy_ntp_client
from asy_wifi_service import asy_conn_time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_TMP_DIR = "tests/_tmp"
_next_dir = 0


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
    for stale in ("config_WIFI.cfg", "config_NTP.cfg"):
        try:
            os.remove(path + "/" + stale)
        except OSError:
            pass  # no stale file - already fresh
    return path + "/"


def make_wifi_client() -> asy_conn_time:
    return asy_conn_time(led_pin=None, cfg_path=_tmp_cfg_dir())


def make_ntp_client() -> asy_ntp_client:
    wifi_mode_lock = asyncio.Lock()
    return asy_ntp_client(
        wifi_mode_lock,
        network_available=lambda: True,
        get_dns_server=lambda: None,
        cfg_path=_tmp_cfg_dir(),
    )


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
# ---------------------------------------------------------------------------


async def _simulated_set_network_endpoint(client: asy_conn_time, request: "Any") -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setNetwork"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}
    return await ar.handle_set_cmd(
        client, fields, client.get_cfg_schema(), post_fct=client.reconnect_wifi, ok_descr="Network settings updated"
    )


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


def _wifi_app(client: asy_conn_time) -> Microdot:
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

    req = _make_request(app, "PUT", "/boom", {})
    res = run(app.dispatch_request(req))
    assert res.status_code == 500


# ---------------------------------------------------------------------------
# Real Microdot end-to-end for the getter path (base_classes.py's _get_dict_cfg), same depth as
# the setter path above.
# ---------------------------------------------------------------------------


def _ntp_getter_app(client: asy_ntp_client) -> Microdot:
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
