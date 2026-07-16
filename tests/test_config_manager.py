import asyncio
import json
import os

import config_manager as cm
from print_log import PrintLog

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

# One field of each schema "type" (int/float/str/bool), plus a special-only (not persisted) field,
# concatenated the same way every real _VAL_* driver constant is (see asy_bmp3xx_driver.py).
_VAL_INT = '|"Count": {"def": 5, "type": "int", "min": 0, "max": 10, "special": null}|'
_VAL_FLOAT = '|"Offset": {"def": 1.5, "type": "float", "min": -10.0, "max": 10.0, "special": null}|'
_VAL_STR = '|"Name": {"def": "abc", "type": "str", "min": 1, "max": 5, "special": null}|'
_VAL_BOOL = '|"Enabled": {"def": true, "type": "bool", "min": null, "max": null, "special": null}|'
_VAL_SPECIAL = '|"Special": {"def": null, "type": "int", "min": 0, "max": 10, "special": 99}|'
_SCHEMA = _VAL_INT + _VAL_FLOAT + _VAL_STR + _VAL_BOOL + _VAL_SPECIAL


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


def _make(name: str, cfg_vals: str = _SCHEMA) -> "tuple[cm.ConfigManager, str]":
    path = _tmp_path(name)
    _remove(path)
    return cm.ConfigManager(path, cfg_vals, PrintLog()), path


# ---------------------------------------------------------------------------
# str_cfg / name_cfg / cfg_from_str / make_dict - pure string/schema parsing
# ---------------------------------------------------------------------------


def test_str_cfg_single_field() -> None:
    assert cm.str_cfg(_VAL_INT) == ["Count"]


def test_str_cfg_multi_field_concatenated() -> None:
    assert cm.str_cfg(_SCHEMA) == ["Count", "Offset", "Name", "Enabled", "Special"]


def test_str_cfg_invalid_wrapper_returns_empty() -> None:
    assert cm.str_cfg("") == []
    assert cm.str_cfg("|") == []
    assert cm.str_cfg("no pipes here") == []
    assert cm.str_cfg('{"Count": 1}') == []


def test_name_cfg_single_vs_multi() -> None:
    assert cm.name_cfg(_VAL_INT) == "Count"
    assert cm.name_cfg(_SCHEMA) == ""  # more than one field - no single name to return
    assert cm.name_cfg("") == ""


def test_cfg_from_str_valid() -> None:
    defaults = cm.cfg_from_str(_VAL_INT)
    assert defaults == {"Count": {"def": 5, "type": "int", "min": 0, "max": 10, "special": None}}


def test_cfg_from_str_invalid_returns_empty() -> None:
    assert cm.cfg_from_str("") == {}
    assert cm.cfg_from_str("|not json|") == {}


def test_make_dict_normal_namedtuple() -> None:
    from collections import namedtuple

    Meas = namedtuple("Meas", ["temp", "hum"])
    assert cm.make_dict(Meas(20.5, 55)) == {"Meas": {"temp": 20.5, "hum": 55}}


def test_make_dict_zero_field_namedtuple() -> None:
    from collections import namedtuple

    Empty = namedtuple("Empty", [])
    assert cm.make_dict(Empty()) == {"Empty": {}}


def test_make_dict_non_namedtuple_returns_empty() -> None:
    assert cm.make_dict(object()) == {}  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# type_or_range_error / check_cfg_get_default
# ---------------------------------------------------------------------------


def test_type_or_range_error_int_in_and_out_of_range() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "int", "min": 0, "max": 10, "special": None}
    assert cm.type_or_range_error(5, schema) is False
    assert cm.type_or_range_error(0, schema) is False  # lower boundary accepted
    assert cm.type_or_range_error(10, schema) is False  # upper boundary accepted
    assert cm.type_or_range_error(-1, schema) is True
    assert cm.type_or_range_error(11, schema) is True
    assert cm.type_or_range_error(5.0, schema) is True  # wrong type (float, not int)


def test_type_or_range_error_special_value_bypasses_range() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "int", "min": 0, "max": 10, "special": 99}
    assert cm.type_or_range_error(99, schema, check_special=True) is False
    assert cm.type_or_range_error(99, schema, check_special=False) is True  # out of [0, 10], special not honored


def test_type_or_range_error_float_nan_and_inf_rejected() -> None:
    schema: dict[str, int | float | str | bool | None] = {
        "type": "float",
        "min": -10.0,
        "max": 10.0,
        "special": None,
    }
    nan = float("nan")
    inf = float("inf")
    assert cm.type_or_range_error(1.0, schema) is False
    assert cm.type_or_range_error(nan, schema) is True
    assert cm.type_or_range_error(inf, schema) is True
    assert cm.type_or_range_error(-inf, schema) is True


def test_type_or_range_error_str_length_bounds() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "str", "min": 2, "max": 4, "special": None}
    assert cm.type_or_range_error("ab", schema) is False
    assert cm.type_or_range_error("abcd", schema) is False
    assert cm.type_or_range_error("a", schema) is True
    assert cm.type_or_range_error("abcde", schema) is True


def test_type_or_range_error_bool() -> None:
    schema: dict[str, int | float | str | bool | None] = {
        "type": "bool",
        "min": None,
        "max": None,
        "special": None,
    }
    assert cm.type_or_range_error(True, schema) is False
    assert cm.type_or_range_error(1, schema) is True  # int, not bool - `type() is bool` rejects it


def test_type_or_range_error_unknown_type_or_malformed_schema() -> None:
    assert cm.type_or_range_error(1, {"type": "unknown"}) is True
    assert cm.type_or_range_error(1, {}) is True  # missing "type" entirely


def test_check_cfg_get_default_normal() -> None:
    use_value, default = cm.check_cfg_get_default({"def": 5, "type": "int", "min": 0, "max": 10, "special": None})
    assert (use_value, default) == (True, 5)


def test_check_cfg_get_default_special_only() -> None:
    use_value, default = cm.check_cfg_get_default({"def": None, "type": "int", "min": 0, "max": 10, "special": 99})
    assert (use_value, default) == (False, 99)


def test_check_cfg_get_default_malformed_schema() -> None:
    assert cm.check_cfg_get_default({}) == (True, None)
    assert cm.check_cfg_get_default({"def": 5, "type": "int"}) == (True, None)  # missing min/max/special keys


def test_check_cfg_get_default_default_fails_its_own_range() -> None:
    # self-check: the schema's own "def" must satisfy its own min/max, or this is an invalid schema
    assert cm.check_cfg_get_default({"def": 50, "type": "int", "min": 0, "max": 10, "special": None}) == (True, None)


# ---------------------------------------------------------------------------
# ConfigManager - real file I/O under the Unix port, no mocking
# ---------------------------------------------------------------------------


def test_configmanager_creates_file_with_defaults_when_missing() -> None:
    mgr, path = _make("fresh.cfg")
    try:
        assert mgr.valid is True
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk == {"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True}
    finally:
        _remove(path)


def test_configmanager_directory_path_is_invalid() -> None:
    path = _tmp_path("adir.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is False
    finally:
        os.rmdir(path)


def test_configmanager_empty_schema_is_invalid() -> None:
    mgr, path = _make("emptyschema.cfg", cfg_vals="")
    try:
        assert mgr.valid is False
    finally:
        _remove(path)


def test_configmanager_corrupt_json_falls_back_to_defaults() -> None:
    path = _tmp_path("corrupt.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write("{not valid json")
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        with open(path) as f:
            assert json.load(f)["Count"] == 5  # rewritten with defaults
    finally:
        _remove(path)


def test_configmanager_valid_existing_non_default_value_preserved() -> None:
    path = _tmp_path("preserved.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 7, "Offset": 1.5, "Name": "abc", "Enabled": True}, f)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 7}  # not overwritten back to the default (5)
    finally:
        _remove(path)


def test_configmanager_missing_key_filled_with_default() -> None:
    path = _tmp_path("missingkey.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Offset": 1.5, "Name": "abc", "Enabled": True}, f)  # "Count" missing
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
    finally:
        _remove(path)


def test_configmanager_out_of_range_value_replaced_with_default() -> None:
    path = _tmp_path("outofrange.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 999, "Offset": 1.5, "Name": "abc", "Enabled": True}, f)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
    finally:
        _remove(path)


def test_configmanager_extraneous_key_removed_from_file() -> None:
    path = _tmp_path("extra.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True, "Ghost": 1}, f)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        with open(path) as f:
            assert "Ghost" not in json.load(f)
    finally:
        _remove(path)


def test_configmanager_special_only_field_not_persisted() -> None:
    mgr, path = _make("special.cfg")
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "Special" not in json.load(f)
        assert run(mgr.get_dict(["Special"])) is None  # never stored, so a KeyError -> None sentinel
    finally:
        _remove(path)


def test_get_dict_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert run(mgr.get_dict(["Count"])) is None
    finally:
        os.rmdir(path)


def test_get_dict_unknown_key_returns_none() -> None:
    mgr, path = _make("unknownkey.cfg")
    try:
        assert run(mgr.get_dict(["NoSuchKey"])) is None
    finally:
        _remove(path)


def test_get_typed_values_happy_path() -> None:
    mgr, path = _make("typedvalues.cfg")
    try:
        assert run(mgr.get_int_values(_VAL_INT)) == [5]
        assert run(mgr.get_float_values(_VAL_FLOAT)) == [1.5]
        assert run(mgr.get_str_values(_VAL_STR)) == ["abc"]
        assert run(mgr.get_bool_values(_VAL_BOOL)) == [True]
    finally:
        _remove(path)


def test_get_int_values_conversion_failure_returns_none() -> None:
    mgr, path = _make("badconvert.cfg")
    try:
        assert run(mgr.get_int_values(_VAL_STR)) is None  # int("abc") can't convert
    finally:
        _remove(path)


def test_get_float_values_conversion_failure_returns_none() -> None:
    mgr, path = _make("badconvertfloat.cfg")
    try:
        assert run(mgr.get_float_values(_VAL_STR)) is None  # float("abc") can't convert
    finally:
        _remove(path)


def test_get_str_values_accepts_any_value() -> None:
    mgr, path = _make("strconvert.cfg")
    try:
        assert run(mgr.get_str_values(_VAL_INT)) == ["5"]  # str(v) never fails, unlike int()/float()
    finally:
        _remove(path)


def test_get_bool_values_wrong_stored_type_returns_none() -> None:
    # bool(v) never raises (unlike int()/float()/str()), so a corrupted/wrong-typed on-disk value
    # must be rejected by explicit isinstance check instead of relying on a conversion exception.
    mgr, path = _make("badconvertbool.cfg")
    try:
        with open(path, "w") as f:
            json.dump({"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": "notabool"}, f)
        assert run(mgr.get_bool_values(_VAL_BOOL)) is None
    finally:
        _remove(path)


# ---------------------------------------------------------------------------
# write_config
# ---------------------------------------------------------------------------


def test_write_config_valid_change_persists() -> None:
    mgr, path = _make("writevalid.cfg")
    try:
        ok, results = run(mgr.write_config({"Count": 8}, _VAL_INT))
        assert ok is True
        assert results == {"Count": "Valid"}
        assert run(mgr.get_dict(["Count"])) == {"Count": 8}
    finally:
        _remove(path)


def test_write_config_unchanged_value() -> None:
    mgr, path = _make("writeunchanged.cfg")
    try:
        ok, results = run(mgr.write_config({"Count": 5}, _VAL_INT))
        assert ok is True
        assert results == {"Count": "Unchanged"}
    finally:
        _remove(path)


def test_write_config_out_of_range_marked_invalid_but_call_succeeds() -> None:
    mgr, path = _make("writeinvalid.cfg")
    try:
        ok, results = run(mgr.write_config({"Count": 999}, _VAL_INT))
        assert ok is True
        assert results == {"Count": "Invalid"}
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # untouched
    finally:
        _remove(path)


def test_write_config_unknown_key_marked_invalid() -> None:
    mgr, path = _make("writeunknown.cfg")
    try:
        ok, results = run(mgr.write_config({"NoSuchKey": 1}, _VAL_INT))
        assert ok is True
        assert results == {"NoSuchKey": "Invalid"}
    finally:
        _remove(path)


def test_write_config_special_only_key_reported_valid_but_not_stored() -> None:
    mgr, path = _make("writespecial.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": 3}, _VAL_SPECIAL))
        assert ok is True
        assert results == {"Special": "Valid"}
        with open(path) as f:
            assert "Special" not in json.load(f)
    finally:
        _remove(path)


def test_write_config_key_missing_from_file_marked_failed() -> None:
    mgr, path = _make("writefailed.cfg")
    try:
        with open(path) as f:
            data = json.load(f)
        del data["Count"]  # simulate the file having lost a key out-of-band
        with open(path, "w") as f:
            json.dump(data, f)
        ok, results = run(mgr.write_config({"Count": 8}, _VAL_INT))
        assert ok is True
        assert results == {"Count": "Failed"}
    finally:
        _remove(path)


def test_write_config_on_invalid_manager_returns_false() -> None:
    path = _tmp_path("writeinvalidmgr.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        ok, results = run(mgr.write_config({"Count": 1}, _VAL_INT))
        assert (ok, results) == (False, {})
    finally:
        os.rmdir(path)


def test_concurrent_writes_are_serialized_not_lost() -> None:
    # Both write_config() calls read-modify-write the whole file; without config_lock serializing
    # them, the second writer overwriting first's read would silently drop one field's update.
    mgr, path = _make("concurrent.cfg", cfg_vals=_VAL_INT + _VAL_FLOAT)

    async def scenario() -> None:
        await asyncio.gather(
            mgr.write_config({"Count": 9}, _VAL_INT),
            mgr.write_config({"Offset": 9.5}, _VAL_FLOAT),
        )

    try:
        run(scenario())
        assert run(mgr.get_dict(["Count", "Offset"])) == {"Count": 9, "Offset": 9.5}
    finally:
        _remove(path)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
