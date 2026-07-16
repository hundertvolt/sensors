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


def test_make_dict_single_field_namedtuple() -> None:
    from collections import namedtuple

    Single = namedtuple("Single", ["x"])
    assert cm.make_dict(Single(42)) == {"Single": {"x": 42}}


def test_make_dict_none_valued_field_passes_through() -> None:
    from collections import namedtuple

    Meas = namedtuple("Meas", ["temp"])
    assert cm.make_dict(Meas(None)) == {"Meas": {"temp": None}}


def test_make_dict_nested_tuple_field_silently_dropped_quirk() -> None:
    # Documented quirk (see make_dict's own comment): repr()-parsing splits on the FIRST 2 "("
    # characters, so a field whose own value's repr contains "(" (e.g. a nested tuple) confuses the
    # split and silently drops every field after it - "b" never appears below, no exception raised.
    from collections import namedtuple

    Nested = namedtuple("Nested", ["a", "b"])
    assert cm.make_dict(Nested((1, 2), 3)) == {"Nested": {"a": (1, 2)}}  # type: ignore[comparison-overlap]


def test_str_cfg_empty_wrapped_schema_quirk() -> None:
    # "||" satisfies str_cfg's own "|...|" wrapper check but its (empty) interior splits into one
    # empty-string field name, unlike cfg_from_str("||") which parses to {} (see next test) - a
    # latent inconsistency between the two parsers for this exact degenerate input, never hit by
    # any real driver schema (every real schema has at least one field).
    assert cm.str_cfg("||") == [""]
    assert cm.cfg_from_str("||") == {}


def test_cfg_from_str_pipe_inside_string_value_corrupts_default_quirk() -> None:
    # Documented quirk (see str_cfg's own comment): cfg_from_str blindly replaces every "||" with
    # ", " to join fields, so a str-type field whose own default value contains "||" gets that
    # substring corrupted too, not just misparsed - "a||b" here becomes "a, b". Never hit by any
    # current driver constant (hand-authored, none use "||" in a default value).
    bad = '|"Name": {"def": "a||b", "type": "str", "min": 0, "max": 5, "special": null}|'
    assert cm.cfg_from_str(bad)["Name"]["def"] == "a, b"


def test_str_cfg_duplicate_field_names() -> None:
    dup = _VAL_INT + _VAL_INT
    assert cm.str_cfg(dup) == ["Count", "Count"]
    assert cm.cfg_from_str(dup) == {"Count": {"def": 5, "type": "int", "min": 0, "max": 10, "special": None}}


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


def test_type_or_range_error_int_missing_or_wrong_typed_bounds_rejected() -> None:
    assert cm.type_or_range_error(5, {"type": "int"}) is True  # no min/max at all
    assert cm.type_or_range_error(5, {"type": "int", "min": "0", "max": "10"}) is True  # bounds wrong type


def test_type_or_range_error_int_malformed_special_type_rejects_any_value() -> None:
    # A wrong-typed "special" (schema-authoring error, not a runtime data issue) makes this always
    # return True regardless of check_val or check_special - reachable in principle, but in
    # practice check_cfg_get_default's own self-check (see below) already rejects such a schema
    # before ConfigManager/write_config ever calls type_or_range_error against real data.
    schema: dict[str, int | float | str | bool | None] = {"type": "int", "min": 0, "max": 10, "special": "99"}
    assert cm.type_or_range_error(5, schema, check_special=True) is True
    assert cm.type_or_range_error(5, schema, check_special=False) is True


def test_type_or_range_error_float_missing_or_wrong_typed_bounds_rejected() -> None:
    assert cm.type_or_range_error(1.0, {"type": "float"}) is True  # no min/max at all
    assert cm.type_or_range_error(1.0, {"type": "float", "min": 0, "max": 10}) is True  # bounds wrong type (int)


def test_type_or_range_error_float_malformed_special_type_rejects_any_value() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "float", "min": 0.0, "max": 10.0, "special": 99}
    assert cm.type_or_range_error(5.0, schema, check_special=True) is True


def test_type_or_range_error_str_check_special_combos() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "str", "min": 2, "max": 4, "special": "SPECIAL"}
    assert cm.type_or_range_error("SPECIAL", schema, check_special=True) is False  # bypasses length bounds
    assert cm.type_or_range_error("SPECIAL", schema, check_special=False) is True  # 7 chars, out of [2, 4]


def test_type_or_range_error_str_malformed_special_type_rejects_any_value() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "str", "min": 1, "max": 5, "special": 1}
    assert cm.type_or_range_error("abc", schema, check_special=True) is True


def test_type_or_range_error_str_zero_length_boundary() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "str", "min": 0, "max": 4, "special": None}
    assert cm.type_or_range_error("", schema) is False  # empty string accepted at the min=0 boundary


def test_type_or_range_error_bool_additional_wrong_types() -> None:
    schema: dict[str, int | float | str | bool | None] = {"type": "bool", "min": None, "max": None, "special": None}
    assert cm.type_or_range_error(False, schema) is False
    assert cm.type_or_range_error(0, schema) is True  # int, not bool
    assert cm.type_or_range_error(1.0, schema) is True
    assert cm.type_or_range_error("true", schema) is True
    assert cm.type_or_range_error(None, schema) is True


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


def test_check_cfg_get_default_extra_key_rejected() -> None:
    extra: dict[str, int | float | str | bool | None] = {
        "def": 5,
        "type": "int",
        "min": 0,
        "max": 10,
        "special": None,
        "descr": "unexpected",
    }
    assert cm.check_cfg_get_default(extra) == (True, None)


def test_check_cfg_get_default_both_default_and_special_present() -> None:
    # "def" is non-null, so the special-only bypass never triggers - a real, storable default wins
    # even though the field also declares a reachable special sentinel (mirrors the AmbPres shape,
    # but with a real default instead of null - a field that is both normally stored and later
    # writable to its special value via the check_special bypass in type_or_range_error).
    schema: dict[str, int | float | str | bool | None] = {"def": 5, "type": "int", "min": 0, "max": 10, "special": 99}
    assert cm.check_cfg_get_default(schema) == (True, 5)


def test_check_cfg_get_default_none_default_and_none_special_invalid() -> None:
    schema: dict[str, int | float | str | bool | None] = {
        "def": None,
        "type": "int",
        "min": 0,
        "max": 10,
        "special": None,
    }
    assert cm.check_cfg_get_default(schema) == (True, None)


def test_check_cfg_get_default_bool_special_only() -> None:
    schema: dict[str, int | float | str | bool | None] = {
        "def": None,
        "type": "bool",
        "min": None,
        "max": None,
        "special": True,
    }
    assert cm.check_cfg_get_default(schema) == (False, True)


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


def test_configmanager_stale_special_only_key_removed_from_file() -> None:
    # A schema change (special added later) can leave a special-only field's old stored value
    # behind; check_cfg_get_default's use_value=False path skips popping it, so it's caught and
    # removed by the "unexpected keys remaining" cleanup instead - confirming both paths cooperate.
    path = _tmp_path("stalespecial.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True, "Special": 3}, f)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        with open(path) as f:
            assert "Special" not in json.load(f)
    finally:
        _remove(path)


def test_configmanager_file_is_json_array_not_dict() -> None:
    path = _tmp_path("array.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write("[1, 2, 3]")
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        with open(path) as f:
            assert json.load(f)["Count"] == 5  # rewritten with defaults
    finally:
        _remove(path)


def test_configmanager_file_is_json_scalar_not_dict() -> None:
    path = _tmp_path("scalar.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write("42")
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
    finally:
        _remove(path)


def test_configmanager_empty_file_falls_back_to_defaults() -> None:
    path = _tmp_path("emptyfile.cfg")
    _remove(path)
    open(path, "w").close()  # 0 bytes - not even "{}"
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        with open(path) as f:
            assert json.load(f)["Count"] == 5
    finally:
        _remove(path)


def test_configmanager_all_keys_missing_uses_all_defaults() -> None:
    path = _tmp_path("allmissing.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({}, f)  # valid dict, but zero of the schema's keys present
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count", "Offset", "Name", "Enabled"])) == {
            "Count": 5,
            "Offset": 1.5,
            "Name": "abc",
            "Enabled": True,
        }
    finally:
        _remove(path)


def test_configmanager_multiple_out_of_range_values_each_independently_defaulted() -> None:
    path = _tmp_path("multibad.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 999, "Offset": 999.9, "Name": "abc", "Enabled": True}, f)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count", "Offset"])) == {"Count": 5, "Offset": 1.5}
    finally:
        _remove(path)


def test_configmanager_wrong_type_stored_value_replaced_with_default() -> None:
    for bad_value in ("notanumber", [1, 2, 3], None):
        path = _tmp_path("wrongtype.cfg")
        _remove(path)
        with open(path, "w") as f:
            json.dump({"Count": bad_value, "Offset": 1.5, "Name": "abc", "Enabled": True}, f)
        try:
            mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
            assert mgr.valid is True
            assert run(mgr.get_dict(["Count"])) == {"Count": 5}
        finally:
            _remove(path)


def test_configmanager_extraneous_and_missing_key_combined() -> None:
    path = _tmp_path("extraandmissing.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Offset": 1.5, "Name": "abc", "Enabled": True, "Ghost": 1}, f)  # "Count" missing, "Ghost" extra
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        with open(path) as f:
            on_disk = json.load(f)
        assert "Ghost" not in on_disk
        assert on_disk["Count"] == 5
    finally:
        _remove(path)


def test_configmanager_parent_directory_missing_leaves_invalid() -> None:
    # Exercises both OSError paths in __init__: os.stat() fails on the initial read (line ~156),
    # and open(..., "w") also fails on the fallback write (line ~212) - neither is reachable in
    # isolation without a nonexistent parent directory, since every other test's tmp dir exists.
    path = _TMP_DIR + "/no_such_subdir/x.cfg"
    mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
    assert mgr.valid is False


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


def test_get_dict_empty_keys_list_returns_empty_dict() -> None:
    mgr, path = _make("emptykeys.cfg")
    try:
        assert run(mgr.get_dict([])) == {}
    finally:
        _remove(path)


def test_get_dict_multiple_keys_one_missing_aborts_whole_read() -> None:
    # No partial success: the loop raises KeyError on the first missing key and the whole call
    # returns None, even though "Count" alone would have read back fine.
    mgr, path = _make("partialmissing.cfg")
    try:
        assert run(mgr.get_dict(["Count", "NoSuchKey"])) is None
    finally:
        _remove(path)


def test_get_dict_file_deleted_after_valid_init_returns_none() -> None:
    mgr, path = _make("deletedafterinit.cfg")
    try:
        assert mgr.valid is True
        os.remove(path)
        assert run(mgr.get_dict(["Count"])) is None
    finally:
        _remove(path)


def test_get_dict_file_corrupted_after_valid_init_returns_none() -> None:
    mgr, path = _make("corruptedafterinit.cfg")
    try:
        assert mgr.valid is True
        with open(path, "w") as f:
            f.write("{not valid json")
        assert run(mgr.get_dict(["Count"])) is None
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


def test_get_int_values_unknown_key_in_schema_string_returns_none() -> None:
    mgr, path = _make("typedunknownkey.cfg")
    try:
        bad_schema = '|"NoSuchKey": {"def": 1, "type": "int", "min": 0, "max": 10, "special": null}|'
        assert run(mgr.get_int_values(bad_schema)) is None
    finally:
        _remove(path)


def test_get_values_empty_schema_string_returns_empty_list_not_none() -> None:
    mgr, path = _make("emptyschemaread.cfg")
    try:
        assert run(mgr.get_int_values("")) == []
        assert run(mgr.get_bool_values("")) == []
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


def test_write_config_empty_data_dict_is_a_noop_success() -> None:
    mgr, path = _make("emptywrite.cfg")
    try:
        ok, results = run(mgr.write_config({}, _VAL_INT))
        assert (ok, results) == (True, {})
    finally:
        _remove(path)


def test_write_config_multiple_keys_mixed_outcomes_in_one_call() -> None:
    # Exercises all four WriteValidity outcomes together, in the same call, to confirm they don't
    # interfere with each other and only the genuinely-valid change actually gets persisted.
    mgr, path = _make("mixedoutcomes.cfg")
    try:
        with open(path) as f:
            data = json.load(f)
        del data["Enabled"]  # simulate drift, for the "Failed" case below
        with open(path, "w") as f:
            json.dump(data, f)

        ok, results = run(
            mgr.write_config(
                {
                    "Count": 8,  # valid, changed
                    "Offset": 1.5,  # valid, unchanged (matches existing default)
                    "Name": "toolong",  # invalid - exceeds max length 5
                    "Enabled": False,  # failed - key missing from the file
                    "Ghost": 1,  # invalid - not in the schema at all
                },
                _SCHEMA,
            )
        )
        assert ok is True
        assert results == {
            "Count": "Valid",
            "Offset": "Unchanged",
            "Name": "Invalid",
            "Enabled": "Failed",
            "Ghost": "Invalid",
        }
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk["Count"] == 8
        assert on_disk["Name"] == "abc"  # untouched
        assert "Enabled" not in on_disk  # still missing, not resurrected
    finally:
        _remove(path)


def test_write_config_malformed_schema_entry_aborts_whole_call() -> None:
    # A schema self-check failure for ANY key hard-aborts the entire call (return False, {}),
    # discarding even an already-valid key's would-be result - matches __init__'s own all-or-
    # nothing treatment of a malformed schema, not a partial-failure design.
    mgr, path = _make("malformedschema.cfg")
    try:
        bad_schema = _VAL_INT + '|"Bad": {"def": 1, "type": "int", "min": 0, "max": 10}|'  # missing "special"
        ok, results = run(mgr.write_config({"Count": 8, "Bad": 1}, bad_schema))
        assert (ok, results) == (False, {})
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # untouched - no partial write
    finally:
        _remove(path)


def test_write_config_self_heals_corrupted_stored_value() -> None:
    mgr, path = _make("selfheal.cfg")
    try:
        with open(path) as f:
            data = json.load(f)
        data["Count"] = "corrupted"  # simulate out-of-band corruption of the stored value itself
        with open(path, "w") as f:
            json.dump(data, f)

        ok, results = run(mgr.write_config({"Count": 7}, _VAL_INT))
        assert ok is True
        assert results == {"Count": "Valid"}
        assert run(mgr.get_dict(["Count"])) == {"Count": 7}
    finally:
        _remove(path)


def test_write_config_file_corrupted_after_valid_init_returns_false() -> None:
    mgr, path = _make("writecorrupted.cfg")
    try:
        assert mgr.valid is True
        with open(path, "w") as f:
            f.write("{not valid json")
        ok, results = run(mgr.write_config({"Count": 1}, _VAL_INT))
        assert (ok, results) == (False, {})
    finally:
        _remove(path)


def test_write_config_special_only_value_matching_sentinel_is_valid() -> None:
    # The sentinel is always valid if it matches its own definition, independent of the ordinary
    # min/max range check (99 is outside _VAL_SPECIAL's declared [0, 10]) - type_or_range_error's
    # own check_special bypass is what makes this so, applied here just like any other key.
    mgr, path = _make("specialsentinel.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": 99}, _VAL_SPECIAL))
        assert (ok, results) == (True, {"Special": "Valid"})
    finally:
        _remove(path)


def test_write_config_special_only_value_wrong_type_is_invalid() -> None:
    mgr, path = _make("specialwrongtype.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": "not even an int"}, _VAL_SPECIAL))
        assert (ok, results) == (True, {"Special": "Invalid"})
    finally:
        _remove(path)


def test_write_config_special_only_value_out_of_range_and_not_sentinel_is_invalid() -> None:
    mgr, path = _make("specialoutofrange.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": 999}, _VAL_SPECIAL))  # neither in [0, 10] nor == 99
        assert (ok, results) == (True, {"Special": "Invalid"})
    finally:
        _remove(path)


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
