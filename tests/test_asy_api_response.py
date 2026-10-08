import asyncio
import os
from collections import namedtuple

from _error_codes import code
from _tmp_scratch import TmpScratch

import asy_api_response as ar
from asy_base_classes import SensorReaderConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    import asy_config_manager as cm

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("asy_api_response")
Meas = namedtuple("Meas", ["temp", "hum"])
_VAL_SI: "cm.ConfigSchema" = (("SampleInterval", "int", 2, 1, 3600, None),)


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass  # already gone


class _FakeRequest:
    # Minimal stand-in for microdot.Request, mocking only the one boundary parse_cmd_request
    # actually touches (the .json property) - same mocking-boundary convention tests/machine.py
    # uses for real hardware buses.
    def __init__(self, json_value: object, *, raise_instead: bool = False) -> None:
        self._json_value = json_value
        self._raise_instead = raise_instead
        self.sock = (_NoopHolder(), _NoopHolder())

    @property
    def json(self) -> object:  # matches asy_api_response.py's own _RequestLike Protocol
        if self._raise_instead:
            raise ValueError("malformed body")
        return self._json_value


class _NoopHolder:
    # The writer side of Request.sock as the static routes use it; nothing here opens a stream.
    def hold(self, closable: object) -> None:
        pass


# ---------------------------------------------------------------------------
# make_response - envelope/catalog primitive
# ---------------------------------------------------------------------------


def _catalogued_codes() -> list[int]:
    # _STANDARD_CODES' keys as the source writes them: each "<int>:" line of its dict block.
    codes: list[int] = []
    inside = False
    with open("src/asy_api_response.py") as f:
        for line in f:
            if line.startswith("_STANDARD_CODES"):
                inside = True
            elif inside and line.startswith("}"):
                return codes
            elif inside:
                codes.append(int(line.split(":", 1)[0]))
    raise AssertionError("_STANDARD_CODES block not found in src/asy_api_response.py")


def _produced_codes() -> list[int]:
    # Each literal code src/ passes first to make_response() outside a comment, plus the webserver's shaped
    # statuses, read from their source line: an underscore const() is not a module attribute on MicroPython.
    codes: list[int] = []
    for name in sorted(os.listdir("src")):
        if not name.endswith(".py"):
            continue
        with open("src/" + name) as f:
            for line in f:
                if line.startswith("_ERROR_STATUSES = const(("):
                    codes.extend(int(c) for c in line.split("const((", 1)[1].split("))", 1)[0].split(","))
                comment_at = line.find("#")
                for tail in (line if comment_at < 0 else line[:comment_at]).split("make_response(")[1:]:
                    digits = ""
                    for ch in tail:
                        if not ch.isdigit():
                            break
                        digits += ch
                    if digits:
                        codes.append(int(digits))
    return codes


def test_make_response_standard_success_code_uses_catalog_text() -> None:
    assert ar.make_response(0) == {"res": "OK", "code": 0, "descr": "Command executed", "result": {}}


def test_make_response_success_text_can_be_overridden() -> None:
    resp = ar.make_response(0, descr="Custom OK text")
    assert resp == {"res": "OK", "code": 0, "descr": "Custom OK text", "result": {}}


def test_make_response_standard_error_code_uses_catalog_text() -> None:
    assert ar.make_response(1) == {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}


def test_make_response_standard_error_text_can_be_overridden() -> None:
    resp = ar.make_response(404, descr="Custom not-found text")
    assert resp == {"res": "ERR", "code": 404, "descr": "Custom not-found text", "result": {}}


def test_make_response_every_standard_code_present() -> None:
    # The whole catalog with its texts: a shaped HTTP error's code is its status (SPECIFICATION.md C.5.3).
    catalog = {
        0: "Command executed",
        1: "Invalid JSON request",
        2: "Command specifier missing",
        3: "Invalid command",
        400: "Bad request",
        404: "Not found",
        405: "Method not allowed",
        413: "Payload too large",
        500: "Internal server error",
    }
    assert sorted(ar._STANDARD_CODES) == sorted(catalog)
    for status, descr in catalog.items():
        assert ar.make_response(status) == {"res": "OK" if status == 0 else "ERR", "code": status, "descr": descr, "result": {}}


def test_every_catalogued_code_has_a_producer_and_every_produced_code_is_catalogued() -> None:
    catalogued = _catalogued_codes()
    assert sorted(catalogued) == sorted(ar._STANDARD_CODES)  # the source read sees the live catalog
    produced = _produced_codes()
    never_produced = [c for c in catalogued if c not in produced]
    uncatalogued = [c for c in produced if c not in catalogued]
    assert never_produced == [] and uncatalogued == [], (never_produced, uncatalogued)


def test_make_response_unknown_code_without_descr_falls_back_to_unknown_error() -> None:
    resp = ar.make_response(999)
    assert resp == {"res": "ERR", "code": 999, "descr": "Unknown error", "result": {}}


def test_make_response_unknown_code_with_descr_keeps_the_given_descr() -> None:
    # Totality only: an uncatalogued code keeps the given text; the catalog itself is closed (C.5.3).
    resp = ar.make_response(42, descr="LED is busy")
    assert resp == {"res": "ERR", "code": 42, "descr": "LED is busy", "result": {}}


def test_make_response_result_payload_is_passed_through() -> None:
    resp = ar.make_response(0, result={"SampleInterval": "Valid"})
    assert resp["result"] == {"SampleInterval": "Valid"}


def test_make_response_result_none_defaults_to_empty_dict() -> None:
    assert ar.make_response(0, result=None)["result"] == {}


def test_make_response_result_can_carry_partial_failures_under_an_overall_ok() -> None:
    # (owner, 2026-09-26): per-field failures don't demote the overall response - res not OK
    # would mean the request itself was broken; individual field outcomes live in "result".
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
# handle_set_cmd - drives SensorReaderConfig._set_dict_cfg and the post-write hook and returns the per-field result;
# a raising hook turns its group's fields "Failed", caught as defense in depth on top of Microdot's own
# per-request catch (agent, 2026-08-03: prior field experience with Microdot behaving unexpectedly).
# ---------------------------------------------------------------------------


def _make_reader(name: str, cfg_vals: "cm.ConfigSchema" = _VAL_SI) -> "tuple[SensorReaderConfig, str]":
    path = _scratch.path("config_" + name + ".cfg")
    path_prefix = path.rsplit("/", 1)[0] + "/"
    reader = SensorReaderConfig(Meas(20.0, 50), name, cfg_vals, max_module_error=3, cfg_path=path_prefix)
    run(reader.cfgmgr.setup())
    return reader, path


def test_handle_set_cmd_valid_change_returns_its_per_field_result() -> None:
    reader, path = _make_reader("handleok")
    try:
        assert run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, _VAL_SI)) == {"SampleInterval": "Valid"}
    finally:
        _remove(path)


def test_handle_set_cmd_partial_failure_returns_the_mixed_result() -> None:
    reader, path = _make_reader("handlepartial")
    try:
        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 9999, "Ghost": 1}, _VAL_SI))
        assert result == {"SampleInterval": "Invalid", "Ghost": "Invalid"}
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_fires_only_when_something_actually_changed() -> None:
    reader, path = _make_reader("handlepostfct")
    try:
        calls = []
        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, _VAL_SI, post_fct=lambda: calls.append(1)))
        assert result == {"SampleInterval": "Valid"}
        assert calls == [1]
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_does_not_fire_when_unchanged() -> None:
    reader, path = _make_reader("handlepostfctunchanged")
    try:
        calls = []
        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 2}, _VAL_SI, post_fct=lambda: calls.append(1)))  # 2 is the default already
        assert result == {"SampleInterval": "Unchanged"}
        assert calls == []
    finally:
        _remove(path)


def test_handle_set_cmd_async_post_fct_fires_only_when_something_actually_changed() -> None:
    reader, path = _make_reader("handleasyncpostfct")
    try:
        calls = []

        async def post() -> None:
            calls.append(1)

        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, _VAL_SI, post_asy_fct=post))
        assert result == {"SampleInterval": "Valid"}
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

        result = run(
            ar.handle_set_cmd(
                reader, {"SampleInterval": 42}, _VAL_SI, post_fct=lambda: sync_calls.append(1), post_asy_fct=post,
            ),
        )
        assert result == {"SampleInterval": "Valid"}
        assert sync_calls == [1]
        assert async_calls == [1]
    finally:
        _remove(path)


def _entries(reader: "SensorReaderConfig") -> "list[tuple[int, str]]":
    # The reader's own history: a raising hook is persisted on the logger of the module it ran against.
    log = run(reader.pr.get_log())[reader.pr.name]
    return [(n, t) for n, t in zip(log["ErrNum"], log["ErrType"]) if t != "N"]  # noqa: B905 - MicroPython zip() rejects strict=


def test_handle_set_cmd_sync_post_fct_raising_fails_its_group() -> None:
    # A raising post-write hook is caller-supplied code outside _set_dict_cfg(): its failure is its group's outcome.
    reader, path = _make_reader("handlepostfctraise")
    try:

        def bad_post() -> None:
            raise RuntimeError("reconnect failed")

        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, _VAL_SI, post_fct=bad_post))
        assert result == {"SampleInterval": "Failed"}
        assert reader.pr._err_count == 1
        assert _entries(reader) == [(code("E", "CALLBACK"), "E")]
    finally:
        _remove(path)


def test_handle_set_cmd_async_post_fct_raising_fails_its_group() -> None:
    reader, path = _make_reader("handleasyncpostfctraise")
    try:

        async def bad_post() -> None:
            raise RuntimeError("ntp sync failed")

        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, _VAL_SI, post_asy_fct=bad_post))
        assert result == {"SampleInterval": "Failed"}
        assert reader.pr._err_count == 1
        assert _entries(reader) == [(code("E", "CALLBACK"), "E")]
    finally:
        _remove(path)


def test_handle_set_cmd_sync_post_fct_raising_never_schedules_the_async_hook() -> None:
    # Both hooks supplied at once, with the synchronous one raising: post_fct() fires first and the async
    # hook is only awaited afterwards, so it must never run, not even be scheduled. Pins that order as real
    # behaviour, and the group's fields read Failed.
    reader, path = _make_reader("handlebothhooksraise")
    try:
        async_calls = []

        def bad_post() -> None:
            raise RuntimeError("reconnect failed")

        async def post() -> None:
            async_calls.append(1)

        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, _VAL_SI, post_fct=bad_post, post_asy_fct=post))
        assert result == {"SampleInterval": "Failed"}
        assert async_calls == []  # never invoked - post_fct raised before it could be awaited
        assert reader.pr._err_count == 1
        assert _entries(reader) == [(code("E", "CALLBACK"), "E")]
    finally:
        _remove(path)


def test_handle_set_cmd_hook_raising_after_a_mixed_result_fails_every_key() -> None:
    reader, path = _make_reader("handlemixedraise")
    try:

        def bad_post() -> None:
            raise RuntimeError("reconnect failed")

        result = run(ar.handle_set_cmd(reader, {"SampleInterval": 42, "Ghost": 1}, _VAL_SI, post_fct=bad_post))
        assert result == {"SampleInterval": "Failed", "Ghost": "Failed"}
        assert _entries(reader) == [(code("E", "CALLBACK"), "E")]
    finally:
        _remove(path)


def test_handle_set_cmd_never_calls_a_hook_when_nothing_is_valid() -> None:
    reader, path = _make_reader("handlenovalid")
    try:
        sync_calls = []
        async_calls = []

        async def post() -> None:
            async_calls.append(1)

        result = run(
            ar.handle_set_cmd(
                reader, {"SampleInterval": 9999}, _VAL_SI, post_fct=lambda: sync_calls.append(1), post_asy_fct=post,
            ),
        )
        assert result == {"SampleInterval": "Invalid"}
        assert sync_calls == []
        assert async_calls == []
    finally:
        _remove(path)


def test_handle_set_cmd_whole_persist_failure_marks_every_field_failed() -> None:
    # A whole-operation persistence failure is per-field detail ("Failed"), not a top-level protocol
    # error - the request itself was validly processed and dispatched.
    reader, path = _make_reader("handlewholefail", cfg_vals=())
    try:
        assert reader.cfgmgr.valid is False
        assert run(ar.handle_set_cmd(reader, {"SampleInterval": 42}, ())) == {"SampleInterval": "Failed"}
    finally:
        _remove(path)


def test_handle_set_cmd_empty_data_returns_an_empty_result() -> None:
    reader, path = _make_reader("handleempty")
    try:
        assert run(ar.handle_set_cmd(reader, {}, _VAL_SI)) == {}
    finally:
        _remove(path)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
