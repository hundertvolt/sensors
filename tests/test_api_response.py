import asyncio
import os
from collections import namedtuple

import api_response as ar
import config_manager as cm
from base_classes import SensorReaderConfig

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
Meas = namedtuple("Meas", ["temp", "hum"])
_VAL_SI: "cm.ConfigSchema" = (("SampleInterv", "int", 2, 1, 3600, None),)


def _tmp_path(name: str) -> str:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    return _TMP_DIR + "/" + name


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass  # already gone


class _FakeRequest:
    # Minimal stand-in for microdot.Request, mocking only the one boundary parse_cmd_request
    # actually touches (the .json property) - same mocking-boundary convention tests/machine.py
    # uses for real hardware buses.
    def __init__(self, json_value: "Any", raise_instead: bool = False) -> None:
        self._json_value = json_value
        self._raise_instead = raise_instead

    @property
    def json(self) -> "Any":
        if self._raise_instead:
            raise ValueError("malformed body")
        return self._json_value


# ---------------------------------------------------------------------------
# make_response - envelope/catalog primitive
# ---------------------------------------------------------------------------


def test_make_response_standard_success_code_uses_catalog_text() -> None:
    assert ar.make_response(0) == {"res": "OK", "code": 0, "descr": "Command executed", "result": {}}


def test_make_response_success_text_can_be_overridden() -> None:
    resp = ar.make_response(0, descr="Custom OK text")
    assert resp == {"res": "OK", "code": 0, "descr": "Custom OK text", "result": {}}


def test_make_response_standard_error_code_uses_catalog_text() -> None:
    assert ar.make_response(1) == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}


def test_make_response_standard_error_text_can_be_overridden() -> None:
    resp = ar.make_response(2, descr="Custom missing-cmd text")
    assert resp == {"res": "ERR", "code": 2, "descr": "Custom missing-cmd text", "result": {}}


def test_make_response_every_standard_code_present() -> None:
    for code in (0, 1, 2, 3, 4, 5, 100):
        resp = ar.make_response(code)
        assert resp["code"] == code
        assert resp["descr"] != ""
    assert ar.make_response(0)["res"] == "OK"
    for code in (1, 2, 3, 4, 5, 100):
        assert ar.make_response(code)["res"] == "ERR"


def test_make_response_unknown_code_without_descr_falls_back_to_unknown_error() -> None:
    resp = ar.make_response(999)
    assert resp == {"res": "ERR", "code": 999, "descr": "Unknown error", "result": {}}


def test_make_response_unknown_code_with_descr_is_a_real_custom_code() -> None:
    # The generalization the legacy special_err closed enum didn't support: any caller-defined
    # code outside the standard catalog, with its own message.
    resp = ar.make_response(42, descr="LED is busy")
    assert resp == {"res": "ERR", "code": 42, "descr": "LED is busy", "result": {}}


def test_make_response_result_payload_is_passed_through() -> None:
    resp = ar.make_response(0, result={"SampleInterv": "Valid"})
    assert resp["result"] == {"SampleInterv": "Valid"}


def test_make_response_result_none_defaults_to_empty_dict() -> None:
    assert ar.make_response(0, result=None)["result"] == {}


def test_make_response_result_can_carry_partial_failures_under_an_overall_ok() -> None:
    # Final project decision: per-field failures don't demote the overall response - the request
    # was validly processed, individual field outcomes live in "result".
    resp = ar.make_response(0, result={"A": "Valid", "B": "Invalid", "C": "Failed"})
    assert resp["res"] == "OK"
    assert resp["code"] == 0
    assert resp["result"] == {"A": "Valid", "B": "Invalid", "C": "Failed"}


# ---------------------------------------------------------------------------
# parse_cmd_request
# ---------------------------------------------------------------------------


def test_parse_cmd_request_valid_command_returns_the_json_and_no_error() -> None:
    req = _FakeRequest({"cmd": "setThing", "Value": 1})
    data, err = ar.parse_cmd_request(req, ["setThing", "getThing"])
    assert data == {"cmd": "setThing", "Value": 1}
    assert err is None


def test_parse_cmd_request_body_raises_returns_invalid_json_error() -> None:
    req = _FakeRequest(None, raise_instead=True)
    data, err = ar.parse_cmd_request(req, ["setThing"])
    assert data is None
    assert err == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}


def test_parse_cmd_request_body_is_none_returns_invalid_json_error() -> None:
    req = _FakeRequest(None)
    data, err = ar.parse_cmd_request(req, ["setThing"])
    assert data is None
    assert err is not None
    assert err["code"] == 1


def test_parse_cmd_request_body_is_a_non_dict_json_value_returns_invalid_json_error() -> None:
    # More precise than treating a valid-but-non-dict JSON body (e.g. a bare list) as merely
    # "missing cmd field" - it's a fundamentally wrong-shaped request.
    for bad_body in ([1, 2, 3], "just a string", 42, True):
        req = _FakeRequest(bad_body)
        data, err = ar.parse_cmd_request(req, ["setThing"])
        assert data is None
        assert err is not None
        assert err["code"] == 1


def test_parse_cmd_request_missing_cmd_key_returns_missing_error() -> None:
    req = _FakeRequest({"Value": 1})
    data, err = ar.parse_cmd_request(req, ["setThing"])
    assert data is None
    assert err == {"res": "ERR", "code": 2, "descr": "Command specifier missing", "result": {}}


def test_parse_cmd_request_cmd_not_in_allowed_keys_returns_invalid_command_error() -> None:
    req = _FakeRequest({"cmd": "unknownCmd"})
    data, err = ar.parse_cmd_request(req, ["setThing", "getThing"])
    assert data is None
    assert err == {"res": "ERR", "code": 3, "descr": "Invalid command", "result": {}}


def test_parse_cmd_request_empty_keys_list_rejects_every_cmd() -> None:
    req = _FakeRequest({"cmd": "anything"})
    data, err = ar.parse_cmd_request(req, [])
    assert data is None
    assert err is not None
    assert err["code"] == 3


# ---------------------------------------------------------------------------
# handle_set_cmd - orchestrates SensorReaderConfig._set_dict_cfg + post-write hook + envelope,
# with its own try/except as defense-in-depth on top of Microdot's own blanket per-request catch
# (project decision, based on prior field experience with Microdot behaving unexpectedly).
# ---------------------------------------------------------------------------


def _make_reader(name: str, cfg_vals: "cm.ConfigSchema" = _VAL_SI) -> "tuple[SensorReaderConfig, str]":
    path_prefix = _tmp_path("") + "/"
    path = path_prefix + "config_" + name + ".cfg"
    _remove(path)
    reader = SensorReaderConfig(Meas(20.0, 50), 3, name, cfg_vals, cfg_path=path_prefix)
    run(reader.cfgmgr.setup())
    return reader, path


def test_handle_set_cmd_valid_change_returns_ok_with_per_field_result() -> None:
    reader, path = _make_reader("handleok")
    try:
        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI))
        assert resp == {"res": "OK", "code": 0, "descr": "Command executed", "result": {"SampleInterv": "Valid"}}
    finally:
        _remove(path)


def test_handle_set_cmd_ok_descr_override() -> None:
    reader, path = _make_reader("handleokdescr")
    try:
        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI, ok_descr="Network settings updated"))
        assert resp["descr"] == "Network settings updated"
        assert resp["res"] == "OK"
    finally:
        _remove(path)


def test_handle_set_cmd_partial_failure_stays_overall_ok() -> None:
    reader, path = _make_reader("handlepartial")
    try:
        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 9999, "Ghost": 1}, _VAL_SI))
        assert resp["res"] == "OK"
        assert resp["code"] == 0
        assert resp["result"] == {"SampleInterv": "Invalid", "Ghost": "Invalid"}
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_fires_only_when_something_actually_changed() -> None:
    reader, path = _make_reader("handlepostfct")
    try:
        calls = []
        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI, post_fct=lambda: calls.append(1)))
        assert resp["res"] == "OK"
        assert calls == [1]
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_does_not_fire_when_unchanged() -> None:
    reader, path = _make_reader("handlepostfctunchanged")
    try:
        calls = []
        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 2}, _VAL_SI, post_fct=lambda: calls.append(1)))  # 2 is the default already
        assert resp["result"] == {"SampleInterv": "Unchanged"}
        assert calls == []
    finally:
        _remove(path)


def test_handle_set_cmd_async_post_fct_fires_only_when_something_actually_changed() -> None:
    reader, path = _make_reader("handleasyncpostfct")
    try:
        calls = []

        async def post() -> None:
            calls.append(1)

        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI, post_asy_fct=post))
        assert resp["res"] == "OK"
        assert calls == [1]
    finally:
        _remove(path)


def test_handle_set_cmd_both_hooks_fire_together_when_provided() -> None:
    reader, path = _make_reader("handlebothhooks")
    try:
        sync_calls = []
        async_calls = []

        async def post() -> None:
            async_calls.append(1)

        run(
            ar.handle_set_cmd(
                reader, {"SampleInterv": 42}, _VAL_SI, post_fct=lambda: sync_calls.append(1), post_asy_fct=post
            )
        )
        assert sync_calls == [1]
        assert async_calls == [1]
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_raising_is_caught_and_reports_generic_error() -> None:
    # Defense-in-depth: post_fct is caller-supplied and lives outside _set_dict_cfg's own
    # try/except entirely - this is exactly the kind of escaping exception handle_set_cmd's own
    # wrapper exists for.
    reader, path = _make_reader("handlepostfctraise")
    try:

        def bad_post() -> None:
            raise RuntimeError("reconnect failed")

        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI, post_fct=bad_post))
        assert resp == {"res": "ERR", "code": 100, "descr": "Generic command error", "result": {}}
        assert reader.pr.err_count == 1
    finally:
        _remove(path)


def test_handle_set_cmd_async_post_fct_raising_is_caught_and_reports_generic_error() -> None:
    reader, path = _make_reader("handleasyncpostfctraise")
    try:

        async def bad_post() -> None:
            raise RuntimeError("ntp sync failed")

        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI, post_asy_fct=bad_post))
        assert resp == {"res": "ERR", "code": 100, "descr": "Generic command error", "result": {}}
        assert reader.pr.err_count == 1
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_raising_never_schedules_the_async_hook() -> None:
    # Both hooks supplied at once, with the synchronous one raising: post_fct() fires first and
    # post_asy_fct() is only awaited afterwards (see handle_set_cmd's own ordering), so the async
    # hook must never run at all - not even be scheduled. Pins that firing order down as real
    # behaviour rather than an incidental statement order, and confirms the response still degrades
    # into the same generic-error envelope the two single-hook-raises tests above expect.
    reader, path = _make_reader("handlebothhooksraise")
    try:
        async_calls = []

        def bad_post() -> None:
            raise RuntimeError("reconnect failed")

        async def post() -> None:
            async_calls.append(1)

        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, _VAL_SI, post_fct=bad_post, post_asy_fct=post))
        assert resp == {"res": "ERR", "code": 100, "descr": "Generic command error", "result": {}}
        assert async_calls == []  # never invoked - post_fct raised before it could be awaited
        assert reader.pr.err_count == 1
    finally:
        _remove(path)


def test_handle_set_cmd_whole_persist_failure_still_returns_ok_envelope_with_failed_fields() -> None:
    # A whole-operation persistence failure is per-field detail ("Failed" in result), not a
    # top-level protocol error - the request itself was validly processed and dispatched.
    reader, path = _make_reader("handlewholefail", cfg_vals=())
    try:
        assert reader.cfgmgr.valid is False
        resp = run(ar.handle_set_cmd(reader, {"SampleInterv": 42}, ()))
        assert resp["res"] == "OK"
        assert resp["code"] == 0
        assert resp["result"] == {"SampleInterv": "Failed"}
    finally:
        _remove(path)


def test_handle_set_cmd_empty_data_returns_ok_with_empty_result() -> None:
    reader, path = _make_reader("handleempty")
    try:
        resp = run(ar.handle_set_cmd(reader, {}, _VAL_SI))
        assert resp == {"res": "OK", "code": 0, "descr": "Command executed", "result": {}}
    finally:
        _remove(path)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
