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
# concatenated the same way every real _VAL_* driver constant is (see asy_bmp3xx_driver.py). Each
# field record is (name, type, def, min, max, special).
_VAL_INT: "cm.ConfigSchema" = (("Count", "int", 5, 0, 10, None),)
_VAL_FLOAT: "cm.ConfigSchema" = (("Offset", "float", 1.5, -10.0, 10.0, None),)
_VAL_STR: "cm.ConfigSchema" = (("Name", "str", "abc", 1, 5, None),)
_VAL_BOOL: "cm.ConfigSchema" = (("Enabled", "bool", True, None, None, None),)
_VAL_SPECIAL: "cm.ConfigSchema" = (("Special", "int", None, 0, 10, 99),)
_SCHEMA: "cm.ConfigSchema" = _VAL_INT + _VAL_FLOAT + _VAL_STR + _VAL_BOOL + _VAL_SPECIAL


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


def _make(name: str, cfg_vals: "cm.ConfigSchema" = _SCHEMA) -> "tuple[cm.ConfigManager, str]":
    path = _tmp_path(name)
    _remove(path)
    return cm.ConfigManager(path, cfg_vals, PrintLog()), path


# ---------------------------------------------------------------------------
# schema_names / name_cfg / schema_dict / make_dict - pure schema parsing
# ---------------------------------------------------------------------------


def test_schema_names_single_field() -> None:
    assert cm.schema_names(_VAL_INT) == ["Count"]


def test_schema_names_multi_field_concatenated() -> None:
    assert cm.schema_names(_SCHEMA) == ["Count", "Offset", "Name", "Enabled", "Special"]


def test_schema_names_malformed_input_returns_empty() -> None:
    assert cm.schema_names(()) == []
    assert cm.schema_names(None) == []  # type: ignore[arg-type]
    assert cm.schema_names((1, 2, 3)) == []  # type: ignore[arg-type]  # elements aren't field-record tuples


def test_schema_names_non_tuple_iterable_quirk() -> None:
    # A bare string isn't a real ConfigSchema (no real caller ever passes one), but iterating it
    # doesn't raise either - each character satisfies field[0] by returning itself. Documented, not
    # guarded against: nothing in the codebase relies on rejecting this shape.
    assert cm.schema_names("abc") == ["a", "b", "c"]  # type: ignore[arg-type]


def test_name_cfg_single_vs_multi() -> None:
    assert cm.name_cfg(_VAL_INT) == "Count"
    assert cm.name_cfg(_SCHEMA) == ""  # more than one field - no single name to return
    assert cm.name_cfg(()) == ""


def test_schema_dict_valid() -> None:
    assert cm.schema_dict(_VAL_INT) == {"Count": ("Count", "int", 5, 0, 10, None)}


def test_schema_dict_malformed_input_returns_empty() -> None:
    assert cm.schema_dict(()) == {}
    assert cm.schema_dict(None) == {}  # type: ignore[arg-type]
    assert cm.schema_dict((1, 2, 3)) == {}  # type: ignore[arg-type]


def test_schema_names_and_schema_dict_agree_on_empty_schema() -> None:
    assert cm.schema_names(()) == []
    assert cm.schema_dict(()) == {}


def test_schema_dict_str_value_containing_pipe_no_longer_corrupts() -> None:
    # The old pipe-delimited-string encoding corrupted a str default containing "||" (see git
    # history); a real tuple has no delimiter to corrupt, so this now just works.
    field: cm.ConfigSchema = (("Name", "str", "a||b", 0, 5, None),)
    assert cm.schema_dict(field)["Name"][2] == "a||b"


def test_schema_names_and_schema_dict_duplicate_field_names() -> None:
    dup = _VAL_INT + _VAL_INT
    assert cm.schema_names(dup) == ["Count", "Count"]  # order-preserving, duplicates kept
    assert cm.schema_dict(dup) == {"Count": ("Count", "int", 5, 0, 10, None)}  # dict dedups, last wins


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


# ---------------------------------------------------------------------------
# type_or_range_error / check_cfg_get_default
# ---------------------------------------------------------------------------


def test_type_or_range_error_int_in_and_out_of_range() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(5, field) is False
    assert cm.type_or_range_error(0, field) is False  # lower boundary accepted
    assert cm.type_or_range_error(10, field) is False  # upper boundary accepted
    assert cm.type_or_range_error(-1, field) is True
    assert cm.type_or_range_error(11, field) is True
    assert cm.type_or_range_error(5.0, field) is True  # wrong type (float, not int)


def test_type_or_range_error_special_value_bypasses_range() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, 99)
    assert cm.type_or_range_error(99, field, check_special=True) is False
    assert cm.type_or_range_error(99, field, check_special=False) is True  # out of [0, 10], special not honored


def test_type_or_range_error_int_missing_or_wrong_typed_bounds_rejected() -> None:
    assert cm.type_or_range_error(5, ("X", "int", None, None, None, None)) is True  # no min/max at all
    assert cm.type_or_range_error(5, ("X", "int", None, "0", "10", None)) is True  # type: ignore[arg-type]  # bounds wrong type


def test_type_or_range_error_int_malformed_special_type_rejects_any_value() -> None:
    # A wrong-typed "special" (schema-authoring error, not a runtime data issue) makes this always
    # return True regardless of check_val or check_special - reachable in principle, but in
    # practice check_cfg_get_default's own self-check (see below) already rejects such a schema
    # before ConfigManager/write_config ever calls type_or_range_error against real data.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, "99")
    assert cm.type_or_range_error(5, field, check_special=True) is True
    assert cm.type_or_range_error(5, field, check_special=False) is True


def test_type_or_range_error_float_missing_or_wrong_typed_bounds_rejected() -> None:
    assert cm.type_or_range_error(1.0, ("X", "float", None, None, None, None)) is True  # no min/max at all
    assert cm.type_or_range_error(1.0, ("X", "float", None, 0, 10, None)) is True  # bounds wrong type (int)


def test_type_or_range_error_float_malformed_special_type_rejects_any_value() -> None:
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, 99)
    assert cm.type_or_range_error(5.0, field, check_special=True) is True


def test_type_or_range_error_str_check_special_combos() -> None:
    field: cm.FieldSchema = ("X", "str", None, 2, 4, "SPECIAL")
    assert cm.type_or_range_error("SPECIAL", field, check_special=True) is False  # bypasses length bounds
    assert cm.type_or_range_error("SPECIAL", field, check_special=False) is True  # 7 chars, out of [2, 4]


def test_type_or_range_error_str_malformed_special_type_rejects_any_value() -> None:
    field: cm.FieldSchema = ("X", "str", None, 1, 5, 1)
    assert cm.type_or_range_error("abc", field, check_special=True) is True


def test_type_or_range_error_str_zero_length_boundary() -> None:
    field: cm.FieldSchema = ("X", "str", None, 0, 4, None)
    assert cm.type_or_range_error("", field) is False  # empty string accepted at the min=0 boundary


def test_type_or_range_error_bool_additional_wrong_types() -> None:
    field: cm.FieldSchema = ("X", "bool", None, None, None, None)
    assert cm.type_or_range_error(False, field) is False
    assert cm.type_or_range_error(0, field) is True  # int, not bool
    assert cm.type_or_range_error(1.0, field) is True
    assert cm.type_or_range_error("true", field) is True
    assert cm.type_or_range_error(None, field) is True


def test_type_or_range_error_float_nan_and_inf_rejected() -> None:
    field: cm.FieldSchema = ("X", "float", None, -10.0, 10.0, None)
    nan = float("nan")
    inf = float("inf")
    assert cm.type_or_range_error(1.0, field) is False
    assert cm.type_or_range_error(nan, field) is True
    assert cm.type_or_range_error(inf, field) is True
    assert cm.type_or_range_error(-inf, field) is True


def test_type_or_range_error_str_length_bounds() -> None:
    field: cm.FieldSchema = ("X", "str", None, 2, 4, None)
    assert cm.type_or_range_error("ab", field) is False
    assert cm.type_or_range_error("abcd", field) is False
    assert cm.type_or_range_error("a", field) is True
    assert cm.type_or_range_error("abcde", field) is True


def test_type_or_range_error_bool() -> None:
    field: cm.FieldSchema = ("X", "bool", None, None, None, None)
    assert cm.type_or_range_error(True, field) is False
    assert cm.type_or_range_error(1, field) is True  # int, not bool - `type() is bool` rejects it


def test_type_or_range_error_unknown_type_rejected() -> None:
    assert cm.type_or_range_error(1, ("X", "unknown", None, None, None, None)) is True


def test_type_or_range_error_wrong_length_field_rejected() -> None:
    assert cm.type_or_range_error(1, ()) is True  # type: ignore[arg-type]  # nothing to unpack
    assert cm.type_or_range_error(1, ("X", "int")) is True  # type: ignore[arg-type]  # too short


def test_check_cfg_get_default_normal() -> None:
    use_value, default = cm.check_cfg_get_default(("Count", "int", 5, 0, 10, None))
    assert (use_value, default) == (True, 5)


def test_check_cfg_get_default_special_only() -> None:
    use_value, default = cm.check_cfg_get_default(("AmbPres", "int", None, 0, 10, 99))
    assert (use_value, default) == (False, 99)


def test_check_cfg_get_default_malformed_schema() -> None:
    assert cm.check_cfg_get_default(()) == (True, None)  # type: ignore[arg-type]
    assert cm.check_cfg_get_default(("X", "int", 5)) == (True, None)  # type: ignore[arg-type]  # wrong length


def test_check_cfg_get_default_default_fails_its_own_range() -> None:
    # self-check: the schema's own "def" must satisfy its own min/max, or this is an invalid schema
    assert cm.check_cfg_get_default(("X", "int", 50, 0, 10, None)) == (True, None)


def test_check_cfg_get_default_wrong_length_rejected() -> None:
    extra = ("X", "int", 5, 0, 10, None, "extra")
    assert cm.check_cfg_get_default(extra) == (True, None)  # type: ignore[arg-type]


def test_check_cfg_get_default_both_default_and_special_present() -> None:
    # "def" is non-null, so the special-only bypass never triggers - a real, storable default wins
    # even though the field also declares a reachable special sentinel (mirrors the AmbPres shape,
    # but with a real default instead of null - a field that is both normally stored and later
    # writable to its special value via the check_special bypass in type_or_range_error).
    field: cm.FieldSchema = ("X", "int", 5, 0, 10, 99)
    assert cm.check_cfg_get_default(field) == (True, 5)


def test_check_cfg_get_default_none_default_and_none_special_invalid() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.check_cfg_get_default(field) == (True, None)


def test_check_cfg_get_default_bool_special_only() -> None:
    field: cm.FieldSchema = ("X", "bool", None, None, None, True)
    assert cm.check_cfg_get_default(field) == (False, True)


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
    mgr, path = _make("emptyschema.cfg", cfg_vals=())
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


def test_get_int_values_unknown_key_in_schema_returns_none() -> None:
    mgr, path = _make("typedunknownkey.cfg")
    try:
        bad_schema: cm.ConfigSchema = (("NoSuchKey", "int", 1, 0, 10, None),)
        assert run(mgr.get_int_values(bad_schema)) is None
    finally:
        _remove(path)


def test_get_values_empty_schema_returns_empty_list_not_none() -> None:
    mgr, path = _make("emptyschemaread.cfg")
    try:
        assert run(mgr.get_int_values(())) == []
        assert run(mgr.get_bool_values(())) == []
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
        bad_schema = _VAL_INT + (("Bad", "int", 1, 0, 10),)  # missing "special" - wrong length
        ok, results = run(mgr.write_config({"Count": 8, "Bad": 1}, bad_schema))  # type: ignore[arg-type]
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
