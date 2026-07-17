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

# One special-only field per remaining type (int's is _VAL_SPECIAL above), to cover the sentinel
# mechanism end-to-end for every schema "type", not just int.
_VAL_FLOAT_SPECIAL: "cm.ConfigSchema" = (("FloatSpecial", "float", None, 0.0, 10.0, 99.0),)
_VAL_STR_SPECIAL: "cm.ConfigSchema" = (("StrSpecial", "str", None, 1, 5, "OFF"),)
_VAL_BOOL_SPECIAL: "cm.ConfigSchema" = (("BoolSpecial", "bool", None, None, None, True),)

# A same-type (8 int fields) and a mixed-type (4 types + 4 more int fields) schema larger than the
# 1-5 field schemas used elsewhere, to check behavior doesn't change with field count or type mix.
_VAL_I1: "cm.ConfigSchema" = (("I1", "int", 1, 0, 100, None),)
_VAL_I2: "cm.ConfigSchema" = (("I2", "int", 2, 0, 100, None),)
_VAL_I3: "cm.ConfigSchema" = (("I3", "int", 3, 0, 100, None),)
_VAL_I4: "cm.ConfigSchema" = (("I4", "int", 4, 0, 100, None),)
_VAL_I5: "cm.ConfigSchema" = (("I5", "int", 5, 0, 100, None),)
_VAL_I6: "cm.ConfigSchema" = (("I6", "int", 6, 0, 100, None),)
_VAL_I7: "cm.ConfigSchema" = (("I7", "int", 7, 0, 100, None),)
_VAL_I8: "cm.ConfigSchema" = (("I8", "int", 8, 0, 100, None),)
_LARGE_SAME_TYPE_SCHEMA: "cm.ConfigSchema" = (
    _VAL_I1 + _VAL_I2 + _VAL_I3 + _VAL_I4 + _VAL_I5 + _VAL_I6 + _VAL_I7 + _VAL_I8
)
_LARGE_MIXED_SCHEMA: "cm.ConfigSchema" = _VAL_INT + _VAL_FLOAT + _VAL_STR + _VAL_BOOL + _VAL_I1 + _VAL_I2 + _VAL_I3 + _VAL_I4


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


def test_name_cfg_malformed_input_returns_empty_string() -> None:
    assert cm.name_cfg(None) == ""  # type: ignore[arg-type]  # schema_names(None) -> [], len 0 -> ""
    assert cm.name_cfg(5) == ""  # type: ignore[arg-type]


def test_name_cfg_single_field_literally_named_empty_string_quirk() -> None:
    # Ambiguous but benign: a single field named "" (never a real driver's choice, but not rejected
    # by schema_names/schema_dict either) returns the exact same "" a malformed/empty schema does -
    # name_cfg can't distinguish "one field named empty string" from "no usable name" this way.
    # Never crashes; nothing in the codebase relies on telling these two apart.
    field: cm.ConfigSchema = (("", "int", 5, 0, 10, None),)
    assert cm.name_cfg(field) == ""


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


def test_make_dict_none_and_scalar_inputs_return_empty() -> None:
    # None/int/str all have a repr() with no "(" at all, so the unpack into [name, kvpairs] fails
    # the same way object()'s does above - never raises, regardless of the input's actual type.
    assert cm.make_dict(None) == {}  # type: ignore[arg-type]
    assert cm.make_dict(5) == {}  # type: ignore[arg-type]
    assert cm.make_dict("str") == {}  # type: ignore[arg-type]


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


def test_make_dict_comma_in_nested_value_repr_falls_back_to_none_quirk() -> None:
    # A different parsing fragility from the nested-tuple quirk above: here the initial
    # [name, kvpairs] split works fine (no stray "(" in the values), but a list-valued field's own
    # repr contains a comma (e.g. "items=[1, 2]"), which the naive comma-split on kvpairs mistakes
    # for a field separator - producing a garbage extra "key" ("2]") alongside the two real ones.
    # getattr(nt, "2]") then raises, and the outer except's fallback kicks in for ALL keys (not just
    # the garbage one) - every value comes back None rather than the two real fields' actual values.
    # Never raises either way, just silently loses data - same "document, don't fix" treatment as
    # the nested-tuple quirk above.
    from collections import namedtuple

    Meas = namedtuple("Meas", ["items", "count"])
    assert cm.make_dict(Meas([1, 2], 3)) == {"Meas": {"items": None, "2]": None, "count": None}}


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


def test_type_or_range_error_float_check_special_combos() -> None:
    # A genuinely valid float special, tested with both check_special values - the int/str
    # equivalents of this were already covered; float itself wasn't, until now.
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, 99.0)
    assert cm.type_or_range_error(99.0, field, check_special=True) is False  # bypasses [0.0, 10.0]
    assert cm.type_or_range_error(99.0, field, check_special=False) is True  # out of range, special not honored


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


def test_type_or_range_error_min_greater_than_max_rejects_every_value() -> None:
    # An authoring mistake (min/max swapped) makes `val_min <= check_val <= val_max` unsatisfiable
    # for any int, including the boundary values themselves - not just "genuinely out of range"
    # ones. Never crashes, just always returns True.
    field: cm.FieldSchema = ("X", "int", None, 10, 0, None)
    assert cm.type_or_range_error(5, field) is True
    assert cm.type_or_range_error(10, field) is True
    assert cm.type_or_range_error(0, field) is True


def test_type_or_range_error_str_min_greater_than_max_rejects_every_value() -> None:
    field: cm.FieldSchema = ("X", "str", None, 4, 2, None)
    assert cm.type_or_range_error("ab", field) is True
    assert cm.type_or_range_error("abc", field) is True


def test_type_or_range_error_asymmetric_wrong_typed_bound_rejected() -> None:
    # Only one of min/max wrong-typed (not both, unlike the existing "missing_or_wrong_typed_bounds"
    # test) - the `type(val_max) is int and type(val_min) is int` guard requires both, so either one
    # being wrong-typed alone is enough to reject a value that would otherwise be in range.
    assert cm.type_or_range_error(5, ("X", "int", None, "0", 10, None)) is True  # type: ignore[arg-type]  # only min wrong
    assert cm.type_or_range_error(5, ("X", "int", None, 0, "10", None)) is True  # type: ignore[arg-type]  # only max wrong


def test_type_or_range_error_bool_ignores_nonsensical_min_max() -> None:
    # A bool field has no range concept - min/max are simply never read, so garbage values there
    # (an authoring mistake, e.g. copy-pasted from an int field) don't affect a genuinely valid bool.
    field: cm.FieldSchema = ("X", "bool", None, 5, 10, None)
    assert cm.type_or_range_error(True, field) is False
    assert cm.type_or_range_error(False, field) is False


def test_type_or_range_error_bool_value_against_int_field_rejected() -> None:
    # `type(check_val) is not int` correctly distinguishes bool from int (unlike isinstance, which
    # would treat True/False as ints too, since bool subclasses int) - the reverse direction of the
    # existing "int value against a bool field" tests above.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(True, field) is True
    assert cm.type_or_range_error(False, field) is True


def test_type_or_range_error_str_length_counts_unicode_codepoints_not_bytes() -> None:
    # Confirmed against the real interpreter (this build has Unicode-aware str support): a 4-char
    # string with one multi-byte UTF-8 character has len() == 4, not the 5-byte UTF-8 encoding
    # length - str length bounds are codepoint bounds, not byte bounds, on this MicroPython build.
    field: cm.FieldSchema = ("X", "str", None, 4, 4, None)
    assert cm.type_or_range_error("café", field) is False  # 4 codepoints, satisfies [4, 4]


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


def test_type_or_range_error_type_field_wrong_type_rejected() -> None:
    # "type" itself isn't a string (an authoring mistake) - no branch matches, same fallthrough
    # result as an unrecognized type name.
    assert cm.type_or_range_error(5, ("X", 123, None, 0, 10, None)) is True  # type: ignore[arg-type]


def test_check_cfg_get_default_def_type_mismatched_from_declared_type_rejected() -> None:
    # "def" doesn't match its own declared "type" (int declared, float default given) - a common
    # authoring mistake, caught by the same self-check an out-of-range default is.
    assert cm.check_cfg_get_default(("X", "int", 1.5, 0, 10, None)) == (True, None)


def test_check_cfg_get_default_malformed_special_type_rejected_even_with_a_valid_default() -> None:
    # A different code path from the "used as default" test below: here "def" is present and
    # perfectly valid on its own (5, in [0, 10]), so the special-as-default substitution never
    # triggers - but type_or_range_error's own val_special type-check still runs unconditionally
    # whenever special is not None, rejecting the field regardless of check_val. Confirms a
    # malformed special can't slip through just because the field also has a normal, valid default.
    field: cm.FieldSchema = ("X", "int", 5, 0, 10, "99")  # special should be int, not str
    assert cm.check_cfg_get_default(field) == (True, None)


def test_check_cfg_get_default_bool_malformed_special_type_rejected_when_used_as_default() -> None:
    # A non-bool "special" (schema-authoring error) substituted in as the default (def=None) fails
    # type_or_range_error's own bool type check the same way any other wrong-typed value would.
    assert cm.check_cfg_get_default(("X", "bool", None, None, None, 1)) == (True, None)


def test_type_or_range_error_bool_ignores_malformed_special_for_a_genuinely_valid_bool_quirk() -> None:
    # Unlike int/float/str, the bool branch never inspects "special" at all - there's no range for
    # a bool to bypass - so a wrong-typed special only ever surfaces via check_cfg_get_default's
    # own self-check (previous test), never by rejecting an otherwise-valid bool value outright.
    # Longstanding, deliberate asymmetry (see BACKLOG.md), not new to the tuple schema.
    assert cm.type_or_range_error(True, ("X", "bool", None, None, None, 1)) is False


def test_schema_dict_non_string_name_quirk() -> None:
    # A non-string "name" (authoring mistake) isn't rejected by schema_dict/schema_names - it just
    # becomes a non-string dict key. Never crashes; see the matching ConfigManager-level test below
    # for what actually happens end-to-end (JSON forces the key to a string on write).
    field = ((123, "int", 5, 0, 10, None),)
    assert cm.schema_names(field) == [123]  # type: ignore[arg-type, comparison-overlap]
    assert cm.schema_dict(field) == {123: (123, "int", 5, 0, 10, None)}  # type: ignore[arg-type, comparison-overlap]


def test_schema_names_and_schema_dict_tolerate_a_non_tuple_element_among_good_ones() -> None:
    # A stray non-tuple element (e.g. a bare string) mixed in with otherwise-valid field records
    # doesn't raise - it's extracted/keyed the same lenient way test_schema_names_non_tuple_
    # iterable_quirk documents for a bare string on its own.
    mixed = _VAL_INT + ("not a field record",)
    assert cm.schema_names(mixed) == ["Count", "n"]  # type: ignore[arg-type]
    assert cm.schema_dict(mixed) == {"Count": ("Count", "int", 5, 0, 10, None), "n": "not a field record"}  # type: ignore[arg-type]


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


def test_configmanager_non_string_filename_returns_invalid_not_uncaught() -> None:
    # os.stat()/open() raise TypeError (not OSError) for a non-string path on this interpreter -
    # __init__ must treat that the same as "file not found" rather than letting it propagate.
    bad_filenames: list[Any] = [None, 123, ["x"], {}, 12.5]
    for bad_filename in bad_filenames:
        mgr = cm.ConfigManager(bad_filename, _VAL_INT, PrintLog())
        assert mgr.valid is False


def test_configmanager_none_or_non_iterable_schema_is_invalid() -> None:
    # schema_dict() already tolerates these (returns {}); __init__ must fail the same way an
    # explicitly empty schema (()) does, not just avoid crashing.
    mgr, path = _make("noneschema.cfg", cfg_vals=None)  # type: ignore[arg-type]
    try:
        assert mgr.valid is False
    finally:
        _remove(path)
    mgr, path = _make("intschema.cfg", cfg_vals=5)  # type: ignore[arg-type]
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


def test_configmanager_raw_nan_token_treated_as_corrupt_not_a_raise() -> None:
    # MicroPython's json module can write NaN/inf (json.dumps(float("nan")) -> "nan", no exception)
    # but can't read that same token back (json.loads("nan") raises ValueError) - confirmed directly
    # against the pinned interpreter, an asymmetry CPython doesn't have (it round-trips both ways).
    # A file containing this token (however it got there) must still take the same "corrupt file,
    # rebuild from defaults" path as any other malformed JSON, not raise.
    path = _tmp_path("nantoken.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write('{"Offset": nan}')
    try:
        mgr = cm.ConfigManager(path, _VAL_FLOAT, PrintLog())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Offset"])) == {"Offset": 1.5}  # rebuilt from the schema default
    finally:
        _remove(path)


def test_configmanager_value_omitted_json_quirk_self_heals() -> None:
    # A genuine MicroPython v1.28.0 json.load() leniency, confirmed directly against the pinned
    # interpreter and distinct from the already-tested "unterminated" case (fixed upstream in 2025,
    # commit 9ef16b466 - that fix only covers a missing closing brace/bracket). A value omitted
    # before a comma/closing brace doesn't raise here - it desyncs the parser into a wrong/mangled
    # dict instead (e.g. `{"Count": , "Offset": 1.5}` silently parses to `{"Count": "Offset"}`).
    # Not a bug in this file: every mangled key/value still goes through the normal per-key
    # type/range check and falls back to its own default, same as any other corrupt value.
    path = _tmp_path("mangled.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write('{"Count": , "Offset": 1.5, "Name": "abc", "Enabled": true}')
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # rebuilt from the schema default
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


def test_configmanager_float_special_only_field_not_persisted() -> None:
    mgr, path = _make("floatspecial.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "FloatSpecial" not in json.load(f)
        assert run(mgr.get_dict(["FloatSpecial"])) is None
    finally:
        _remove(path)


def test_configmanager_str_special_only_field_not_persisted() -> None:
    mgr, path = _make("strspecial.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "StrSpecial" not in json.load(f)
        assert run(mgr.get_dict(["StrSpecial"])) is None
    finally:
        _remove(path)


def test_configmanager_bool_special_only_field_not_persisted() -> None:
    mgr, path = _make("boolspecial.cfg", cfg_vals=_VAL_BOOL_SPECIAL)
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "BoolSpecial" not in json.load(f)
        assert run(mgr.get_dict(["BoolSpecial"])) is None
    finally:
        _remove(path)


def test_configmanager_schema_entirely_special_only_is_valid_with_empty_file() -> None:
    # A schema with zero storable fields (every field is special-only) is a valid, non-empty schema
    # (len(defaults) != 0, so the "Defaults are empty" check doesn't trigger) - init still succeeds
    # and writes an empty {} config file, rather than being treated as invalid.
    mgr, path = _make("allspecial.cfg", cfg_vals=_VAL_SPECIAL)
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert json.load(f) == {}
    finally:
        _remove(path)


def test_configmanager_single_field_schema() -> None:
    mgr, path = _make("singlefield.cfg", cfg_vals=_VAL_INT)
    try:
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
        ok, results = run(mgr.write_config({"Count": 7}, _VAL_INT))
        assert (ok, results) == (True, {"Count": "Valid"})
    finally:
        _remove(path)


def test_configmanager_large_same_type_schema() -> None:
    mgr, path = _make("largesame.cfg", cfg_vals=_LARGE_SAME_TYPE_SCHEMA)
    try:
        assert mgr.valid is True
        assert run(mgr.get_dict(["I1", "I4", "I8"])) == {"I1": 1, "I4": 4, "I8": 8}
        ok, results = run(mgr.write_config({"I3": 30}, _LARGE_SAME_TYPE_SCHEMA))
        assert (ok, results) == (True, {"I3": "Valid"})
        assert run(mgr.get_dict(["I3"])) == {"I3": 30}
    finally:
        _remove(path)


def test_configmanager_large_mixed_type_schema() -> None:
    mgr, path = _make("largemixed.cfg", cfg_vals=_LARGE_MIXED_SCHEMA)
    try:
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count", "Offset", "Name", "Enabled", "I1", "I4"])) == {
            "Count": 5,
            "Offset": 1.5,
            "Name": "abc",
            "Enabled": True,
            "I1": 1,
            "I4": 4,
        }
        ok, results = run(
            mgr.write_config(
                {"Count": 9, "Offset": 2.5, "Name": "xyz", "Enabled": False, "I1": 50}, _LARGE_MIXED_SCHEMA
            )
        )
        assert ok is True
        assert results == {
            "Count": "Valid",
            "Offset": "Valid",
            "Name": "Valid",
            "Enabled": "Valid",
            "I1": "Valid",
        }
    finally:
        _remove(path)


def test_schema_names_and_schema_dict_on_large_mixed_schema() -> None:
    assert cm.schema_names(_LARGE_MIXED_SCHEMA) == ["Count", "Offset", "Name", "Enabled", "I1", "I2", "I3", "I4"]
    assert len(cm.schema_dict(_LARGE_MIXED_SCHEMA)) == 8


def test_configmanager_one_malformed_field_among_valid_fields_invalidates_whole_config() -> None:
    # A single malformed field (wrong length, missing "special") among otherwise-good fields fails
    # check_cfg_get_default's self-check the same way write_config's per-key loop does - __init__
    # aborts for the whole schema, not just the bad field.
    bad_schema = _VAL_INT + (("Bad", "int", 1, 0, 10),)  # missing "special"
    mgr, path = _make("onebadfield.cfg", cfg_vals=bad_schema)  # type: ignore[arg-type]
    try:
        assert mgr.valid is False
    finally:
        _remove(path)


def test_configmanager_non_string_field_name_quirk() -> None:
    # A non-string "name" (schema-authoring mistake) is never rejected - init succeeds, and the
    # on-disk file has its int key silently stringified by json.dump. But get_dict/etc. now read
    # from _cache (see module docstring), which is keyed by the schema's own original (still-int)
    # name - never round-tripped through JSON - so a read using that same int key now succeeds,
    # not the reverse: the "123" string key that's actually on disk no longer matches anything,
    # since _cache is never rebuilt from the file after __init__. Never crashes either way; a real
    # driver would never author a name like this.
    bad_name_schema = ((123, "int", 5, 0, 10, None),)
    path = _tmp_path("badname.cfg")
    _remove(path)
    try:
        mgr = cm.ConfigManager(path, bad_name_schema, PrintLog())  # type: ignore[arg-type]
        assert mgr.valid is True
        with open(path) as f:
            assert json.load(f) == {"123": 5}
        assert run(mgr.get_dict([123])) == {123: 5}  # type: ignore[list-item, comparison-overlap]  # matches _cache's own int key
        assert run(mgr.get_dict(["123"])) is None  # the on-disk string key was never the cache's key
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


def test_get_int_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_int.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is False
        assert run(mgr.get_int_values(_VAL_INT)) is None
    finally:
        os.rmdir(path)


def test_get_float_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_float.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is False
        assert run(mgr.get_float_values(_VAL_FLOAT)) is None
    finally:
        os.rmdir(path)


def test_get_str_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_str.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is False
        assert run(mgr.get_str_values(_VAL_STR)) is None
    finally:
        os.rmdir(path)


def test_get_bool_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_bool.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, PrintLog())
        assert mgr.valid is False
        assert run(mgr.get_bool_values(_VAL_BOOL)) is None
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


def test_get_dict_serves_cached_value_even_if_file_deleted_after_init() -> None:
    # Deliberate consequence of _cache (see module docstring): get_dict never re-opens the file, so
    # deleting it out-of-band after a valid __init__ has no effect on subsequent reads at all -
    # unlike the pre-cache design, which re-read (and so would have failed) here.
    mgr, path = _make("deletedafterinit.cfg")
    try:
        assert mgr.valid is True
        os.remove(path)
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
    finally:
        _remove(path)


def test_get_dict_non_iterable_keys_returns_none_not_uncaught() -> None:
    # `for key in keys` raises TypeError for None/int/float/bool (non-iterable) - must come back
    # as the ordinary "read failed" None sentinel, not propagate.
    mgr, path = _make("noniterkeys.cfg")
    try:
        for bad_keys in (None, 5, 12.5, True):
            assert run(mgr.get_dict(bad_keys)) is None  # type: ignore[arg-type]
    finally:
        _remove(path)


def test_get_dict_serves_cached_value_even_if_file_corrupted_after_init() -> None:
    # Same reasoning as the deleted-file case above: _cache is the sole source of truth for reads.
    mgr, path = _make("corruptedafterinit.cfg")
    try:
        assert mgr.valid is True
        with open(path, "w") as f:
            f.write("{not valid json")
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
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


def test_get_int_values_duplicate_schema_field_name_returns_duplicated_value() -> None:
    # schema_names() preserves duplicates (documented, tested at the schema level already) - here
    # confirming that carries all the way through _get_values/get_int_values: the same stored value
    # is read and appended once per occurrence, not deduplicated.
    mgr, path = _make("duptypedread.cfg", cfg_vals=_VAL_INT)
    try:
        assert run(mgr.get_int_values(_VAL_INT + _VAL_INT)) == [5, 5]
    finally:
        _remove(path)


def test_get_int_values_mixed_schema_one_field_fails_conversion_aborts_whole_call() -> None:
    # All-or-nothing across a multi-field schema, matching get_dict's own "one missing key aborts
    # the whole read" behavior: even though "Count" alone would convert fine, "Name" ("abc") failing
    # int() conversion discards the entire result rather than returning a partial list.
    mgr, path = _make("mixedconvertfail.cfg")
    try:
        assert run(mgr.get_int_values(_VAL_INT + _VAL_STR)) is None
    finally:
        _remove(path)


def test_get_str_values_accepts_any_value() -> None:
    mgr, path = _make("strconvert.cfg")
    try:
        assert run(mgr.get_str_values(_VAL_INT)) == ["5"]  # str(v) never fails, unlike int()/float()
    finally:
        _remove(path)


def test_get_bool_values_wrong_cached_type_returns_none() -> None:
    # bool(v) never raises (unlike int()/float()/str()), so a wrong-typed cached value must be
    # rejected by explicit isinstance check instead of relying on a conversion exception. __init__
    # and write_config both validate before ever storing into _cache, so a real driver can't
    # actually get a wrong-typed value in there - poke _cache directly to exercise this
    # defense-in-depth path (reads must still reject it if it's ever there).
    mgr, path = _make("badconvertbool.cfg")
    try:
        mgr._cache["Enabled"] = "notabool"
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


def test_get_typed_values_none_keys_returns_empty_list_not_uncaught() -> None:
    # keys=None goes through schema_names(None) -> [] (already-tested malformed-input behavior),
    # so this takes the same "empty schema" path as the test above rather than raising or
    # returning None - never crashes regardless of which typed getter is used.
    mgr, path = _make("nonekeystyped.cfg")
    try:
        assert run(mgr.get_int_values(None)) == []  # type: ignore[arg-type]
        assert run(mgr.get_float_values(None)) == []  # type: ignore[arg-type]
        assert run(mgr.get_str_values(None)) == []  # type: ignore[arg-type]
        assert run(mgr.get_bool_values(None)) == []  # type: ignore[arg-type]
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


def test_write_config_nan_and_inf_rejected_end_to_end() -> None:
    # type_or_range_error's standalone NaN/inf rejection (tested above) must hold through the full
    # write_config path too: NaN/inf comparisons are always False, so they can never satisfy
    # val_min <= x <= val_max and are correctly marked Invalid, never persisted to _cache or disk.
    mgr, path = _make("writenan.cfg", cfg_vals=_VAL_FLOAT)
    try:
        for bad in (float("nan"), float("inf"), float("-inf")):
            ok, results = run(mgr.write_config({"Offset": bad}, _VAL_FLOAT))
            assert ok is True
            assert results == {"Offset": "Invalid"}
        assert run(mgr.get_dict(["Offset"])) == {"Offset": 1.5}  # untouched, still the default
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


def test_write_config_key_missing_from_cache_marked_failed() -> None:
    # write_config's "key not in <the current state>" check now reads _cache (see module
    # docstring), not the file - simulate the drift by poking _cache directly instead of the file.
    mgr, path = _make("writefailed.cfg")
    try:
        del mgr._cache["Count"]  # simulate _cache having lost a key out-of-band
        ok, results = run(mgr.write_config({"Count": 8}, _VAL_INT))
        assert ok is True
        assert results == {"Count": "Failed"}
    finally:
        _remove(path)


def test_write_config_value_both_out_of_range_and_missing_from_file_marked_invalid_not_failed() -> None:
    # The type/range check runs before the "is this key even present in conf_data" check, so
    # "Invalid" always wins over "Failed" when a submitted value is both out of range AND the key
    # has separately gone missing from the file - confirms the deterministic check ordering.
    mgr, path = _make("invalidbeatsfailed.cfg")
    try:
        with open(path) as f:
            data = json.load(f)
        del data["Count"]  # simulate the file having lost a key out-of-band
        with open(path, "w") as f:
            json.dump(data, f)
        ok, results = run(mgr.write_config({"Count": 999}, _VAL_INT))  # out of range, and also missing
        assert ok is True
        assert results == {"Count": "Invalid"}
    finally:
        _remove(path)


def test_write_config_wrong_type_value_for_ordinary_bool_field_marked_invalid() -> None:
    # Same "Invalid" outcome as the already-tested special-only bool field, but for a plain,
    # non-special bool field - confirms the wrong-type rejection isn't special-sentinel-specific.
    mgr, path = _make("boolwrongtype.cfg", cfg_vals=_VAL_BOOL)
    try:
        ok, results = run(mgr.write_config({"Enabled": 1}, _VAL_BOOL))
        assert (ok, results) == (True, {"Enabled": "Invalid"})
    finally:
        _remove(path)


def test_write_config_non_dict_data_returns_false_not_uncaught() -> None:
    # data.items() raises AttributeError for anything that isn't dict-like - must come back as the
    # ordinary "write failed" (False, {}) sentinel, not propagate.
    mgr, path = _make("nondictdata.cfg")
    try:
        for bad_data in (None, 5, 12.5, "abc", ["Count", 1]):
            ok, results = run(mgr.write_config(bad_data, _VAL_INT))  # type: ignore[arg-type]
            assert (ok, results) == (False, {})
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # untouched by any of the above
    finally:
        _remove(path)


def test_write_config_none_or_non_iterable_cfg_vals_marks_all_keys_invalid() -> None:
    # schema_dict(None) -> {} the same as an explicitly empty schema, so every key in data is
    # simply "not found" - the call still succeeds overall, nothing crashes or gets written.
    mgr, path = _make("noneschemawrite.cfg")
    try:
        ok, results = run(mgr.write_config({"Count": 1}, None))  # type: ignore[arg-type]
        assert (ok, results) == (True, {"Count": "Invalid"})
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # untouched
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
        del mgr._cache["Enabled"]  # simulate _cache drift, for the "Failed" case below

        ok, results = run(
            mgr.write_config(
                {
                    "Count": 8,  # valid, changed
                    "Offset": 1.5,  # valid, unchanged (matches existing default)
                    "Name": "toolong",  # invalid - exceeds max length 5
                    "Enabled": False,  # failed - key missing from _cache
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
        assert mgr._cache["Count"] == 8  # cache and file agree after the write
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


def test_write_config_repairs_a_file_corrupted_after_valid_init() -> None:
    # Deliberate consequence of _cache (see module docstring): write_config no longer reads the
    # file first, only writes it - so an externally-corrupted file doesn't block a write, it gets
    # silently overwritten (repaired) from _cache instead of the pre-cache design's "detect and
    # fail" behavior.
    mgr, path = _make("writecorrupted.cfg")
    try:
        assert mgr.valid is True
        with open(path, "w") as f:
            f.write("{not valid json")
        ok, results = run(mgr.write_config({"Count": 1}, _VAL_INT))
        assert (ok, results) == (True, {"Count": "Valid"})
        with open(path) as f:
            assert json.load(f)["Count"] == 1  # file is valid json again, repaired by the write
    finally:
        _remove(path)


def test_write_config_genuine_write_failure_leaves_cache_unchanged() -> None:
    # A real write failure (not just a pre-existing corrupt file, which the test above shows gets
    # silently repaired) - here the parent directory itself is removed after a valid init, so
    # open(path, "w") genuinely raises OSError. _cache must only ever be committed to *after* a
    # successful write (see write_config's own comment) - confirms it's still the old, unchanged
    # value afterwards, not left half-updated.
    subdir = _TMP_DIR + "/writefail_subdir"
    try:
        os.mkdir(subdir)
    except OSError:
        pass  # already exists
    path = subdir + "/writefail.cfg"
    _remove(path)
    mgr = cm.ConfigManager(path, _VAL_INT, PrintLog())
    try:
        assert mgr.valid is True
        os.remove(path)
        os.rmdir(subdir)  # parent directory gone - the write below will genuinely fail
        ok, results = run(mgr.write_config({"Count": 8}, _VAL_INT))
        assert (ok, results) == (False, {})
        assert mgr._cache == {"Count": 5}  # untouched - still the original default
    finally:
        _remove(path)
        try:
            os.rmdir(subdir)
        except OSError:
            pass  # already gone


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


def test_write_config_float_special_sentinel_matching_is_valid() -> None:
    mgr, path = _make("floatspecialsentinel.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"FloatSpecial": 99.0}, _VAL_FLOAT_SPECIAL))
        assert (ok, results) == (True, {"FloatSpecial": "Valid"})
    finally:
        _remove(path)


def test_write_config_float_special_wrong_type_is_invalid() -> None:
    mgr, path = _make("floatspecialwrongtype.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"FloatSpecial": "not a float"}, _VAL_FLOAT_SPECIAL))
        assert (ok, results) == (True, {"FloatSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_float_special_out_of_range_and_not_sentinel_is_invalid() -> None:
    mgr, path = _make("floatspecialoutofrange.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"FloatSpecial": 500.0}, _VAL_FLOAT_SPECIAL))  # neither [0,10] nor 99.0
        assert (ok, results) == (True, {"FloatSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_str_special_sentinel_matching_is_valid() -> None:
    mgr, path = _make("strspecialsentinel.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"StrSpecial": "OFF"}, _VAL_STR_SPECIAL))
        assert (ok, results) == (True, {"StrSpecial": "Valid"})
    finally:
        _remove(path)


def test_write_config_str_special_wrong_type_is_invalid() -> None:
    mgr, path = _make("strspecialwrongtype.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"StrSpecial": 123}, _VAL_STR_SPECIAL))
        assert (ok, results) == (True, {"StrSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_str_special_out_of_range_and_not_sentinel_is_invalid() -> None:
    mgr, path = _make("strspecialoutofrange.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        # 8 chars: outside [1, 5] and not "OFF"
        ok, results = run(mgr.write_config({"StrSpecial": "toolong!"}, _VAL_STR_SPECIAL))
        assert (ok, results) == (True, {"StrSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_bool_special_any_valid_bool_is_valid() -> None:
    # Unlike int/float/str, a bool field has no range to bypass - both True (the sentinel) and
    # False (not the sentinel, but still a structurally valid bool) come back "Valid", since
    # type_or_range_error's bool branch only ever checks type, never special, for either value.
    mgr, path = _make("boolspecialsentinel.cfg", cfg_vals=_VAL_BOOL_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"BoolSpecial": True}, _VAL_BOOL_SPECIAL))
        assert (ok, results) == (True, {"BoolSpecial": "Valid"})
        ok, results = run(mgr.write_config({"BoolSpecial": False}, _VAL_BOOL_SPECIAL))
        assert (ok, results) == (True, {"BoolSpecial": "Valid"})
    finally:
        _remove(path)


def test_write_config_bool_special_wrong_type_is_invalid() -> None:
    mgr, path = _make("boolspecialwrongtype.cfg", cfg_vals=_VAL_BOOL_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"BoolSpecial": 1}, _VAL_BOOL_SPECIAL))
        assert (ok, results) == (True, {"BoolSpecial": "Invalid"})
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
