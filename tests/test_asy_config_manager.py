import asyncio
import json
import os
from collections import namedtuple

from _error_codes import code
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen

import asy_config_manager as cm
import asy_print_log
from asy_print_log import LogConfig

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


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage. Every test
# below writes its own uniquely-named config file, so they can safely share this one directory.
_scratch = TmpScratch("asy_config_manager")
_SHARED_CFG_DIR = _scratch.dir()

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


class _PrintRecorder:
    # Shadows print() inside asy_print_log only, so every console line a logger emits is captured.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        asy_print_log.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def restore(self) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]


def _tmp_path(name: str) -> str:
    return _SHARED_CFG_DIR + name


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass  # already gone


def _newest_code(mgr: "cm.ConfigManager") -> int:
    nums = run(mgr.pr.get_log())[mgr.name]["ErrNum"]
    assert isinstance(nums, list)
    return int(nums[-1])


async def _write_flushed(mgr: "cm.ConfigManager", data: "dict[str, cm.CfgValue]") -> "tuple[bool, cm.WriteValidity]":
    # A write and its flush in one coroutine: deferred work never outlives a run() call.
    result = await mgr.write_config(data)
    await mgr.flush_pending()
    return result


def _make(name: str, cfg_vals: "cm.ConfigSchema" = _SCHEMA) -> "tuple[cm.ConfigManager, str]":
    path = _tmp_path(name)
    _remove(path)
    mgr = cm.ConfigManager(path, cfg_vals, "TEST")
    run(mgr.setup())
    return mgr, path


# ---------------------------------------------------------------------------
# instance_name() - per-instance naming (SPECIFICATION.md Part C.14)
# ---------------------------------------------------------------------------


def test_instance_name_empty_ext_reproduces_base_name_unchanged() -> None:
    # The single-instance-device no-op guarantee: every module today passes name_ext="", which
    # must leave REST dict keys/config filenames/error-log keys byte-identical to pre-name_ext
    # behavior.
    assert cm.instance_name("SCD30", "") == "SCD30"


def test_instance_name_non_empty_ext_appends_underscore_separated_suffix() -> None:
    assert cm.instance_name("SCD30", "fan_pressure") == "SCD30_fan_pressure"


def test_config_filename_builds_the_one_file_name_shape() -> None:
    assert cm.config_filename("p/", "SGP40_2") == "p/config_SGP40_2.cfg"
    assert cm.config_filename("", "SYSTEM") == "config_SYSTEM.cfg"


def test_instance_name_empty_base_name_with_non_empty_ext() -> None:
    # Not a realistic real-driver call (every base_name comes from a non-empty _NAME constant), but
    # instance_name() itself has no such precondition - must not raise on it.
    assert cm.instance_name("", "ext") == "_ext"


# ---------------------------------------------------------------------------
# schema_names / name_cfg / schema_dict / make_dict - pure schema parsing
# ---------------------------------------------------------------------------


def test_schema_names_single_field() -> None:
    assert cm.schema_names(_VAL_INT) == ["Count"]


def test_schema_names_multi_field_concatenated() -> None:
    assert cm.schema_names(_SCHEMA) == ["Count", "Offset", "Name", "Enabled", "Special"]


def test_schema_names_empty_schema_returns_empty() -> None:
    # A malformed schema is refused statically (tests_scripts/test_config_schemas.py), not at runtime.
    assert cm.schema_names(()) == []


def test_schema_names_non_tuple_iterable_quirk() -> None:
    # A bare string isn't a real ConfigSchema (no real caller ever passes one), but iterating it
    # doesn't raise either - each character satisfies field[0] by returning itself. Documented, not
    # guarded against: nothing in the codebase relies on rejecting this shape.
    assert cm.schema_names("abc") == ["a", "b", "c"]  # type: ignore[arg-type]


def test_name_cfg_single_vs_multi() -> None:
    assert cm.name_cfg(_VAL_INT) == "Count"
    assert cm.name_cfg(_SCHEMA) == ""  # more than one field - no single name to return
    assert cm.name_cfg(()) == ""


def test_name_cfg_single_field_literally_named_empty_string_quirk() -> None:
    # Ambiguous but benign: a single field named "" (never a real driver's choice, but not rejected by
    # schema_names/schema_dict either) returns the same "" a malformed or empty schema does. Never crashes,
    # and nothing relies on telling the two apart.
    field: cm.ConfigSchema = (("", "int", 5, 0, 10, None),)
    assert cm.name_cfg(field) == ""


def test_schema_dict_valid() -> None:
    assert cm.schema_dict(_VAL_INT) == {"Count": ("Count", "int", 5, 0, 10, None)}


def test_schema_dict_empty_schema_returns_empty() -> None:
    assert cm.schema_dict(()) == {}


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
    Meas = namedtuple("Meas", ["temp", "hum"])
    assert cm.make_dict(Meas(20.5, 55), ("temp", "hum")) == {"Meas": {"temp": 20.5, "hum": 55}}


def test_make_dict_explicit_name_overrides_type_introspection() -> None:
    # SPECIFICATION.md Part C.14: a caller that can have more than one instance passes its own
    # resolved self.name explicitly, since the namedtuple *type* itself is fixed at class-definition
    # time and can't itself carry a per-instance disambiguating suffix.
    Meas = namedtuple("Meas", ["temp", "hum"])
    assert cm.make_dict(Meas(20.5, 55), ("temp", "hum"), name="SCD30_fan_pressure") == {"SCD30_fan_pressure": {"temp": 20.5, "hum": 55}}


def test_make_dict_name_none_falls_back_to_type_introspection() -> None:
    # The default (every single-instance caller today) must reproduce pre-name-parameter behavior
    # unchanged - explicit None, not just omitting the argument.
    Meas = namedtuple("Meas", ["temp"])
    assert cm.make_dict(Meas(20.0), ("temp",), name=None) == {"Meas": {"temp": 20.0}}


def test_make_dict_zero_field_namedtuple() -> None:
    Empty = namedtuple("Empty", [])
    assert cm.make_dict(Empty(), ()) == {"Empty": {}}


def test_make_dict_single_field_namedtuple() -> None:
    Single = namedtuple("Single", ["x"])
    assert cm.make_dict(Single(42), ("x",)) == {"Single": {"x": 42}}


def test_make_dict_none_valued_field_passes_through() -> None:
    Meas = namedtuple("Meas", ["temp"])
    assert cm.make_dict(Meas(None), ("temp",)) == {"Meas": {"temp": None}}


def test_make_dict_nested_tuple_field_no_longer_confuses_field_extraction() -> None:
    # Regression test for the repr()-parsing landmine make_dict() used to have: a field whose value's repr
    # contains "(" desynced the parser and silently dropped every field after it. fields is now an explicit
    # tuple, so such a value round-trips like any other.
    Nested = namedtuple("Nested", ["a", "b"])
    assert cm.make_dict(Nested((1, 2), 3), ("a", "b")) == {"Nested": {"a": (1, 2), "b": 3}}


def test_make_dict_comma_in_list_value_repr_no_longer_corrupts_result() -> None:
    # Regression test for the sibling repr()-parsing landmine: a list-valued field's own repr
    # contains a comma (e.g. "items=[1, 2]"), which used to be misread as a field separator and
    # collapse the whole dict to all-None. fields is now explicit, so this is unaffected.
    Meas = namedtuple("Meas", ["items", "count"])
    assert cm.make_dict(Meas([1, 2], 3), ("items", "count")) == {"Meas": {"items": [1, 2], "count": 3}}


# ---------------------------------------------------------------------------
# Numeric coercion (SPECIFICATION.md C.10): the private halves behind checked_int()/checked_float(), which the
# webserver's pause and LED dispatch and the BMP3XX, SGP40 and (through checked_numeric()) ISL29125 drivers call.
# ---------------------------------------------------------------------------


def test_coerce_same_type_passthrough_is_a_true_identity() -> None:
    # Not just == - the returned value must be the exact same value, never a needlessly rebuilt one.
    assert cm._coerce_int(5) == 5
    assert cm._coerce_float(5.5) == 5.5
    assert cm._coerce_int(0) == 0
    assert cm._coerce_float(0.0) == 0.0


def test_coerce_int_to_float_always_accepted_and_coerced() -> None:
    coerced = cm._coerce_float(5)
    assert coerced == 5.0
    assert type(coerced) is float
    # Negative and zero are ordinary values here too - no special-casing around the sign or origin.
    assert cm._coerce_float(-5) == -5.0
    assert cm._coerce_float(0) == 0.0


def test_coerce_float_to_int_exact_round_trip_accepted() -> None:
    coerced = cm._coerce_int(5.0)
    assert coerced == 5
    assert type(coerced) is int
    assert cm._coerce_int(-5.0) == -5
    assert cm._coerce_int(0.0) == 0


def test_coerce_negative_zero_float_to_int_accepted_as_plain_zero() -> None:
    # -0.0 == 0.0 in IEEE-754 float comparison, and int(-0.0) is the plain int 0 (no negative-zero
    # int concept to worry about) - the exact-round-trip check (float(as_int) == check_val) holds,
    # so this is accepted like any other exact whole float, not a special case needing its own logic.
    coerced = cm._coerce_int(-0.0)
    assert coerced == 0
    assert type(coerced) is int


def test_coerce_float_to_int_fractional_rejected_not_truncated() -> None:
    # Never silently truncated/rounded: a refusal carries no value a caller could mistake for a coerced one.
    for bad in (5.5, 5.001, -0.5, 0.1):
        assert cm._coerce_int(bad) is None


def test_coerce_float_to_int_nan_and_inf_rejected_not_raised() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        assert cm._coerce_int(bad) is None


def test_coerce_bool_excluded_from_both_directions() -> None:
    # on MicroPython bool is not an int subclass (py/objbool.c), while CPython's is - type(x) is int states the
    # rule the same way on both: a bool never coerces into int or float.
    assert cm._coerce_int(True) is None
    assert cm._coerce_int(False) is None
    assert cm._coerce_float(True) is None
    assert cm._coerce_float(False) is None


def test_coerce_wrong_type_entirely_rejected() -> None:
    bad_values: list[object] = ["5", None, [5], {}, (5,)]
    for bad in bad_values:
        assert cm._coerce_int(bad) is None
        assert cm._coerce_float(bad) is None


def test_checked_numeric_refuses_a_non_numeric_kind() -> None:
    assert cm.checked_numeric(5, ("X", "str", None, 1, 5, None)) is None


def test_coerce_large_int_to_float_precision_limit_is_a_documented_accepted_gap() -> None:
    # int -> float is a blanket accept, with no exact-round-trip check unlike the other direction, on the
    # premise that every int is exactly representable as a float - true for any value a float field's bounds
    # let through (none passes 2**24, tests_scripts/test_config_schemas.py).
    #
    # Not true in general: float has a finite mantissa (24 bits on the real RP2040's single-precision build,
    # 52 on this Unix-port double-precision one) while MicroPython's int is arbitrary-precision on both.
    #
    # Accepted risk (owner, 2026-08-24): no registered float field's bounds go near this range; this build
    # cannot reproduce the single-precision threshold.
    exact = 2**53
    assert cm._coerce_float(exact) == float(exact)  # still exactly representable at 2**53 itself
    assert cm._coerce_float(exact + 1) == float(exact)  # the +1 is silently lost


def test_checked_int_and_checked_float_return_the_typed_value_or_none() -> None:
    int_field: cm.FieldSchema = ("I", "int", 5, 0, 10, 99)
    float_field: cm.FieldSchema = ("F", "float", 1.0, 0.0, 10.0, None)
    accepted_int = cm.checked_int(5.0, int_field)
    assert accepted_int == 5
    assert type(accepted_int) is int
    accepted_float = cm.checked_float(5, float_field)
    assert accepted_float == 5.0
    assert type(accepted_float) is float
    for bad in (11, -1, 5.5, "5", True, None):
        assert cm.checked_int(bad, int_field) is None, bad
    for bad in (10.5, -0.1, "5", False, None):
        assert cm.checked_float(bad, float_field) is None, bad
    assert cm.checked_int(99, int_field) == 99  # the special
    assert cm.checked_int(99, int_field, check_special=False) is None
    assert cm.checked_numeric(5.0, int_field) == 5
    assert cm.checked_numeric(5, float_field) == 5.0
    assert cm.checked_numeric(11, int_field) is None


def test_a_refusal_carries_no_value() -> None:
    assert cm.type_or_range_error(11, ("I", "int", 5, 0, 10, None)) == (True, None)
    assert cm.type_or_range_error(5.5, ("I", "int", 5, 0, 10, None)) == (True, None)
    assert cm.type_or_range_error("toolong", ("S", "str", "a", 1, 5, None)) == (True, None)
    assert cm.type_or_range_error(1, ("B", "bool", True, None, None, None)) == (True, None)


def test_a_list_or_dict_value_is_refused_by_every_validator() -> None:
    fields: list[cm.FieldSchema] = [
        ("I", "int", 5, 0, 10, None),
        ("F", "float", 1.0, 0.0, 10.0, None),
        ("S", "str", "a", 1, 5, None),
        ("B", "bool", True, None, None, None),
    ]
    for value in ([5], {"v": 5}):
        for field in fields:
            assert cm.checked_int(value, field) is None
            assert cm.checked_float(value, field) is None
            assert cm.checked_numeric(value, field) is None
            assert cm.type_or_range_error(value, field) == (True, None), (value, field)
    schema: cm.ConfigSchema = (("X", "int", 5, 0, 10, None),)
    assert cm.compare_before_write({"X": [5]}, schema, {"X": 5}) == ({}, {"X": "Invalid"})


# ---------------------------------------------------------------------------
# type_or_range_error / check_cfg_get_default
# ---------------------------------------------------------------------------


def test_type_or_range_error_int_in_and_out_of_range() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(5, field) == (False, 5)
    assert cm.type_or_range_error(0, field) == (False, 0)  # lower boundary accepted
    assert cm.type_or_range_error(10, field) == (False, 10)  # upper boundary accepted
    assert cm.type_or_range_error(-1, field)[0] is True
    assert cm.type_or_range_error(11, field)[0] is True


# ---------------------------------------------------------------------------
# type_or_range_error - int<->float coercion (SPECIFICATION.md Part A.8): a JSON int is always accepted for
# a float field (lossless), a JSON float for an int field only when it carries no fractional part - accept
# only what is exactly representable, never discard a digit.
# ---------------------------------------------------------------------------


def test_type_or_range_error_int_field_accepts_integral_float_coerced_to_int() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(5.0, field) == (False, 5)  # coerced, and the coerced value is a real int
    assert cm.type_or_range_error(0.0, field) == (False, 0)  # lower boundary, coerced form
    assert cm.type_or_range_error(10.0, field) == (False, 10)  # upper boundary, coerced form
    coerced = cm.type_or_range_error(5.0, field)[1]
    assert type(coerced) is int  # not just == 5 - must be a real int, not a float that compares equal


def test_type_or_range_error_int_field_rejects_fractional_float() -> None:
    # A fractional value is never truncated/rounded - rejected outright, same treatment as
    # out-of-range, so a fat-fingered "12.5" can't silently become a wrong stored "12".
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(5.7, field)[0] is True
    assert cm.type_or_range_error(9.999, field)[0] is True
    assert cm.type_or_range_error(0.1, field)[0] is True


def test_type_or_range_error_int_field_rejects_nan_and_inf_coercion_attempt() -> None:
    # A float attempting int-coercion that is NaN or an infinity must not raise: MicroPython's int(float)
    # raises ValueError for NaN and OverflowError for the infinities (confirmed against py/objint.c), and
    # both are caught and treated as a normal rejection.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(float("nan"), field)[0] is True
    assert cm.type_or_range_error(float("inf"), field)[0] is True
    assert cm.type_or_range_error(float("-inf"), field)[0] is True


def test_type_or_range_error_int_field_coerced_float_still_subject_to_range_check() -> None:
    # Coercion happens before the range check, not instead of it - an integral float outside the
    # field's own bounds is still rejected, exactly like an out-of-range plain int would be.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(11.0, field)[0] is True
    assert cm.type_or_range_error(-1.0, field)[0] is True


def test_type_or_range_error_float_field_accepts_int_coerced_to_float() -> None:
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, None)
    assert cm.type_or_range_error(5, field) == (False, 5.0)
    assert cm.type_or_range_error(0, field) == (False, 0.0)  # lower boundary, coerced form
    assert cm.type_or_range_error(10, field) == (False, 10.0)  # upper boundary, coerced form
    coerced = cm.type_or_range_error(5, field)[1]
    assert type(coerced) is float  # not just == 5.0 - must be a real float, not an int that compares equal


def test_type_or_range_error_float_field_coerced_int_still_subject_to_range_check() -> None:
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, None)
    assert cm.type_or_range_error(11, field)[0] is True
    assert cm.type_or_range_error(-1, field)[0] is True


def test_type_or_range_error_int_field_still_rejects_bool() -> None:
    # bool must never be coerced into an int field even though `type(True) is bool` sits in
    # Python's int-subclass hierarchy - type() (not isinstance()) already excludes it.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(check_val=True, field=field)[0] is True
    assert cm.type_or_range_error(check_val=False, field=field)[0] is True


def test_type_or_range_error_float_field_still_rejects_bool() -> None:
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, None)
    assert cm.type_or_range_error(check_val=True, field=field)[0] is True
    assert cm.type_or_range_error(check_val=False, field=field)[0] is True


def test_type_or_range_error_int_field_coerced_float_still_honors_special_bypass() -> None:
    # Coercion runs before the special-value bypass too - an integral float matching the special
    # sentinel bypasses range the same way the plain int form already does.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, 99)
    assert cm.type_or_range_error(99.0, field, check_special=True) == (False, 99)
    assert cm.type_or_range_error(99.0, field, check_special=False)[0] is True  # out of range, special not honored


def test_type_or_range_error_int_field_coerced_float_still_rejected_by_malformed_special() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, "99")  # malformed: special should be int
    assert cm.type_or_range_error(5.0, field, check_special=True)[0] is True


def test_type_or_range_error_special_value_bypasses_range() -> None:
    field: cm.FieldSchema = ("X", "int", None, 0, 10, 99)
    assert cm.type_or_range_error(99, field, check_special=True)[0] is False
    assert cm.type_or_range_error(99, field, check_special=False)[0] is True  # out of [0, 10], special not honored


def test_type_or_range_error_int_missing_or_wrong_typed_bounds_rejected() -> None:
    assert cm.type_or_range_error(5, ("X", "int", None, None, None, None))[0] is True  # no min/max at all
    assert cm.type_or_range_error(5, ("X", "int", None, "0", "10", None))[0] is True  # type: ignore[arg-type]  # bounds wrong type


def test_type_or_range_error_int_malformed_special_type_rejects_any_value() -> None:
    # A wrong-typed "special" is a schema-authoring error, not a runtime data issue, and makes this always
    # return True regardless of check_val - reachable in principle, but in practice check_cfg_get_default's
    # own self-check rejects such a schema first.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, "99")
    assert cm.type_or_range_error(5, field, check_special=True)[0] is True
    assert cm.type_or_range_error(5, field, check_special=False)[0] is True


def test_type_or_range_error_float_missing_or_wrong_typed_bounds_rejected() -> None:
    assert cm.type_or_range_error(1.0, ("X", "float", None, None, None, None))[0] is True  # no min/max at all
    assert cm.type_or_range_error(1.0, ("X", "float", None, 0, 10, None))[0] is True  # bounds wrong type (int)


def test_type_or_range_error_float_malformed_special_type_rejects_any_value() -> None:
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, 99)
    assert cm.type_or_range_error(5.0, field, check_special=True)[0] is True


def test_type_or_range_error_float_check_special_combos() -> None:
    # A genuinely valid float special, tested with both check_special values - the int/str
    # equivalents of this were already covered; float itself wasn't, until now.
    field: cm.FieldSchema = ("X", "float", None, 0.0, 10.0, 99.0)
    assert cm.type_or_range_error(99.0, field, check_special=True)[0] is False  # bypasses [0.0, 10.0]
    assert cm.type_or_range_error(99.0, field, check_special=False)[0] is True  # out of range, special not honored


def test_type_or_range_error_str_check_special_combos() -> None:
    field: cm.FieldSchema = ("X", "str", None, 2, 4, "SPECIAL")
    assert cm.type_or_range_error("SPECIAL", field, check_special=True)[0] is False  # bypasses length bounds
    assert cm.type_or_range_error("SPECIAL", field, check_special=False)[0] is True  # 7 chars, out of [2, 4]


def test_type_or_range_error_str_malformed_special_type_rejects_any_value() -> None:
    field: cm.FieldSchema = ("X", "str", None, 1, 5, 1)
    assert cm.type_or_range_error("abc", field, check_special=True)[0] is True


# ---------------------------------------------------------------------------
# type_or_range_error / check_cfg_get_default - the discrete allowed-value-set special (a tuple rather than
# a single scalar): covers BMP3xx's OSR/IIR settings (pure enumeration, min/max both None) and systemCmd-
# style closed string enums, without changing the FieldSchema tuple's shape.
# ---------------------------------------------------------------------------


def test_type_or_range_error_int_discrete_set_membership() -> None:
    # A pure enumeration field (e.g. BMP3xx's _OSR_SETTINGS): min/max disabled (None), special
    # holds every legal value as a tuple - membership in the tuple is the only way to pass.
    field: cm.FieldSchema = ("X", "int", None, None, None, (1, 2, 4, 8, 16, 32))
    assert cm.type_or_range_error(1, field)[0] is False
    assert cm.type_or_range_error(32, field)[0] is False
    assert cm.type_or_range_error(16, field)[0] is False
    assert cm.type_or_range_error(3, field)[0] is True  # not one of the allowed discrete values
    assert cm.type_or_range_error(0, field)[0] is True


def test_type_or_range_error_int_discrete_set_check_special_false_rejects_membership() -> None:
    field: cm.FieldSchema = ("X", "int", None, None, None, (1, 2, 4, 8, 16, 32))
    assert cm.type_or_range_error(8, field, check_special=False)[0] is True


def test_type_or_range_error_int_discrete_set_malformed_element_type_rejects_any_value() -> None:
    # Same "malformed special always rejects, regardless of check_val/check_special" contract as
    # the scalar-special case (test_type_or_range_error_int_malformed_special_type_rejects_any_value
    # above) - one wrong-typed element among otherwise-good ones is enough to reject the whole field.
    field: cm.FieldSchema = ("X", "int", None, None, None, (1, 2, "4", 8))  # type: ignore[assignment]
    assert cm.type_or_range_error(1, field, check_special=True)[0] is True
    assert cm.type_or_range_error(1, field, check_special=False)[0] is True


def test_type_or_range_error_int_discrete_set_bool_element_rejected_like_scalar_case() -> None:
    # `type(check_val) is not int` already distinguishes bool from int for the checked value; the
    # same distinction must hold for a discrete-set element (bool subclasses int in Python/
    # MicroPython, but `type(v) is int` still correctly excludes it).
    field: cm.FieldSchema = ("X", "int", None, None, None, (1, True, 8))  # bool subclasses int for mypy - no ignore needed here, only at runtime (type() is int excludes it)
    assert cm.type_or_range_error(1, field)[0] is True  # malformed set (a bool element) rejects everything


def test_type_or_range_error_str_discrete_set_membership() -> None:
    # systemCmd's shape: a closed string enum, no continuous length range at all.
    field: cm.FieldSchema = ("X", "str", None, None, None, ("reboot", "bootloader", "mempause"))
    assert cm.type_or_range_error("reboot", field)[0] is False
    assert cm.type_or_range_error("bootloader", field)[0] is False
    assert cm.type_or_range_error("mempause", field)[0] is False
    assert cm.type_or_range_error("unknown", field)[0] is True
    assert cm.type_or_range_error("", field)[0] is True


def test_type_or_range_error_str_discrete_set_malformed_element_type_rejects_any_value() -> None:
    field: cm.FieldSchema = ("X", "str", None, None, None, ("reboot", 1, "mempause"))  # type: ignore[assignment]
    assert cm.type_or_range_error("reboot", field)[0] is True


def test_type_or_range_error_float_discrete_set_membership() -> None:
    field: cm.FieldSchema = ("X", "float", None, None, None, (1.0, 2.5, 10.0))
    assert cm.type_or_range_error(2.5, field)[0] is False
    assert cm.type_or_range_error(3.0, field)[0] is True


def test_type_or_range_error_float_discrete_set_malformed_element_type_rejects_any_value() -> None:
    field: cm.FieldSchema = ("X", "float", None, None, None, (1.0, 2))  # int literal 2 is mypy-assignable to float (numeric tower) - no ignore needed; runtime type(2) is not float still rejects it
    assert cm.type_or_range_error(1.0, field)[0] is True


def test_type_or_range_error_discrete_set_alongside_a_real_range() -> None:
    # A range PLUS extra discrete bypass values outside it (not a pure enumeration) - the existing
    # single-scalar-special shape generalizes to "any of several" without disturbing the ordinary
    # range check for values that satisfy it directly.
    field: cm.FieldSchema = ("X", "int", None, 10, 20, (0, 99))
    assert cm.type_or_range_error(15, field)[0] is False  # in range, discrete set not even needed
    assert cm.type_or_range_error(0, field)[0] is False  # bypasses via the discrete set
    assert cm.type_or_range_error(99, field)[0] is False
    assert cm.type_or_range_error(5, field)[0] is True  # neither in range nor in the discrete set


def test_type_or_range_error_discrete_set_empty_tuple_rejects_every_value() -> None:
    # An empty discrete set is a valid (if degenerate) authoring shape - not None, so it's still
    # "special is not None", but nothing can ever be a member of an empty tuple. min/max also None,
    # so there is no other way to pass - every value is rejected.
    field: cm.FieldSchema = ("X", "int", None, None, None, ())
    assert cm.type_or_range_error(1, field)[0] is True
    assert cm.type_or_range_error(0, field)[0] is True


def test_type_or_range_error_discrete_set_accepts_a_list_not_just_a_tuple() -> None:
    # Schema authors write tuples (const()-folded) in practice, but the check itself shouldn't care
    # whether the special collection is a tuple or a plain list.
    field: cm.FieldSchema = ("X", "int", None, None, None, [1, 2, 4, 8])  # type: ignore[assignment]
    assert cm.type_or_range_error(4, field)[0] is False
    assert cm.type_or_range_error(5, field)[0] is True


def test_check_cfg_get_default_discrete_set_with_real_default() -> None:
    # A real, stored discrete-set field (e.g. BMPPressOvers) with a genuine scalar default that is
    # itself one of the allowed set's members.
    field: cm.FieldSchema = ("OSR", "int", 8, None, None, (1, 2, 4, 8, 16, 32))
    assert cm.check_cfg_get_default(field) == (True, 8)


def test_check_cfg_get_default_discrete_set_default_not_in_set_is_invalid() -> None:
    field: cm.FieldSchema = ("OSR", "int", 3, None, None, (1, 2, 4, 8, 16, 32))
    assert cm.check_cfg_get_default(field) == (True, None)  # 3 isn't a legal OSR value


def test_check_cfg_get_default_discrete_set_special_only_field_is_rejected() -> None:
    # def=None with a tuple special has no real scalar to fall back to, unlike the single-scalar special-
    # only case. The substituted "default" (the tuple itself) fails its own type_or_range_error self-check,
    # so this is correctly treated as a malformed schema.
    field: cm.FieldSchema = ("X", "int", None, None, None, (1, 2, 4, 8, 16, 32))
    assert cm.check_cfg_get_default(field) == (True, None)


def test_type_or_range_error_str_zero_length_boundary() -> None:
    field: cm.FieldSchema = ("X", "str", None, 0, 4, None)
    assert cm.type_or_range_error("", field)[0] is False  # empty string accepted at the min=0 boundary


def test_type_or_range_error_bool_additional_wrong_types() -> None:
    field: cm.FieldSchema = ("X", "bool", None, None, None, None)
    assert cm.type_or_range_error(check_val=False, field=field)[0] is False
    assert cm.type_or_range_error(0, field)[0] is True  # int, not bool
    assert cm.type_or_range_error(1.0, field)[0] is True
    assert cm.type_or_range_error("true", field)[0] is True
    assert cm.type_or_range_error(None, field)[0] is True


def test_type_or_range_error_float_nan_and_inf_rejected() -> None:
    field: cm.FieldSchema = ("X", "float", None, -10.0, 10.0, None)
    nan = float("nan")
    inf = float("inf")
    assert cm.type_or_range_error(1.0, field)[0] is False
    assert cm.type_or_range_error(nan, field)[0] is True
    assert cm.type_or_range_error(inf, field)[0] is True
    assert cm.type_or_range_error(-inf, field)[0] is True


def test_type_or_range_error_str_length_bounds() -> None:
    field: cm.FieldSchema = ("X", "str", None, 2, 4, None)
    assert cm.type_or_range_error("ab", field)[0] is False
    assert cm.type_or_range_error("abcd", field)[0] is False
    assert cm.type_or_range_error("a", field)[0] is True
    assert cm.type_or_range_error("abcde", field)[0] is True


def test_type_or_range_error_min_greater_than_max_rejects_every_value() -> None:
    # An authoring mistake (min/max swapped) makes `val_min <= check_val <= val_max` unsatisfiable
    # for any int, including the boundary values themselves - not just "genuinely out of range"
    # ones. Never crashes, just always returns True.
    field: cm.FieldSchema = ("X", "int", None, 10, 0, None)
    assert cm.type_or_range_error(5, field)[0] is True
    assert cm.type_or_range_error(10, field)[0] is True
    assert cm.type_or_range_error(0, field)[0] is True


def test_type_or_range_error_str_min_greater_than_max_rejects_every_value() -> None:
    field: cm.FieldSchema = ("X", "str", None, 4, 2, None)
    assert cm.type_or_range_error("ab", field)[0] is True
    assert cm.type_or_range_error("abc", field)[0] is True


def test_type_or_range_error_asymmetric_wrong_typed_bound_rejected() -> None:
    # Only one of min/max wrong-typed (not both, unlike the existing "missing_or_wrong_typed_bounds"
    # test) - the `type(val_max) is int and type(val_min) is int` guard requires both, so either one
    # being wrong-typed alone is enough to reject a value that would otherwise be in range.
    assert cm.type_or_range_error(5, ("X", "int", None, "0", 10, None))[0] is True  # type: ignore[arg-type]  # only min wrong
    assert cm.type_or_range_error(5, ("X", "int", None, 0, "10", None))[0] is True  # type: ignore[arg-type]  # only max wrong


def test_type_or_range_error_bool_ignores_nonsensical_min_max() -> None:
    # A bool field has no range concept - min/max are simply never read, so garbage values there
    # (an authoring mistake, e.g. copy-pasted from an int field) don't affect a genuinely valid bool.
    field: cm.FieldSchema = ("X", "bool", None, 5, 10, None)
    assert cm.type_or_range_error(check_val=True, field=field)[0] is False
    assert cm.type_or_range_error(check_val=False, field=field)[0] is False


def test_type_or_range_error_bool_value_against_int_field_rejected() -> None:
    # `type(check_val) is not int` correctly distinguishes bool from int (unlike isinstance, which
    # would treat True/False as ints too, since bool subclasses int) - the reverse direction of the
    # existing "int value against a bool field" tests above.
    field: cm.FieldSchema = ("X", "int", None, 0, 10, None)
    assert cm.type_or_range_error(check_val=True, field=field)[0] is True
    assert cm.type_or_range_error(check_val=False, field=field)[0] is True


def test_type_or_range_error_str_length_counts_unicode_codepoints_not_bytes() -> None:
    # Confirmed against the real interpreter (this build has Unicode-aware str support): a 4-char
    # string with one multi-byte UTF-8 character has len() == 4, not the 5-byte UTF-8 encoding
    # length - str length bounds are codepoint bounds, not byte bounds, on this MicroPython build.
    field: cm.FieldSchema = ("X", "str", None, 4, 4, None)
    assert cm.type_or_range_error("café", field)[0] is False  # 4 codepoints, satisfies [4, 4]


def test_type_or_range_error_bool() -> None:
    field: cm.FieldSchema = ("X", "bool", None, None, None, None)
    assert cm.type_or_range_error(check_val=True, field=field)[0] is False
    assert cm.type_or_range_error(1, field)[0] is True  # int, not bool - `type() is bool` rejects it


def test_type_or_range_error_unknown_type_rejected() -> None:
    assert cm.type_or_range_error(1, ("X", "unknown", None, None, None, None))[0] is True


def test_check_cfg_get_default_normal() -> None:
    use_value, default = cm.check_cfg_get_default(("Count", "int", 5, 0, 10, None))
    assert (use_value, default) == (True, 5)


def test_check_cfg_get_default_coerces_an_integral_float_default_to_int() -> None:
    # An authoring shape that used to be rejected outright (def declared "int" but written as a
    # float literal) is now accepted, and check_cfg_get_default returns the coerced int - not the
    # original float - as the usable default, same as type_or_range_error's own coercion.
    use_value, default = cm.check_cfg_get_default(("Count", "int", 5.0, 0, 10, None))
    assert (use_value, default) == (True, 5)
    assert type(default) is int


def test_check_cfg_get_default_coerces_an_int_default_to_float() -> None:
    use_value, default = cm.check_cfg_get_default(("Offset", "float", 5, -10.0, 10.0, None))
    assert (use_value, default) == (True, 5.0)
    assert type(default) is float


def test_check_cfg_get_default_special_only() -> None:
    use_value, default = cm.check_cfg_get_default(("AmbPres", "int", None, 0, 10, 99))
    assert (use_value, default) == (False, 99)


def test_check_cfg_get_default_default_fails_its_own_range() -> None:
    # self-check: the schema's own "def" must satisfy its own min/max, or this is an invalid schema
    assert cm.check_cfg_get_default(("X", "int", 50, 0, 10, None)) == (True, None)


def test_check_cfg_get_default_both_default_and_special_present() -> None:
    # "def" is non-null, so the special-only bypass never triggers and a real, storable default wins even
    # though the field also declares a reachable special sentinel - the AmbPres shape but with a real
    # default, so the field is both normally stored and writable to its special.
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
    assert cm.type_or_range_error(5, ("X", 123, None, 0, 10, None))[0] is True  # type: ignore[arg-type]


def test_check_cfg_get_default_def_type_mismatched_from_declared_type_rejected() -> None:
    # "def" doesn't match its own declared "type" (int declared, float default given) - a common
    # authoring mistake, caught by the same self-check an out-of-range default is.
    assert cm.check_cfg_get_default(("X", "int", 1.5, 0, 10, None)) == (True, None)


def test_check_cfg_get_default_malformed_special_type_rejected_even_with_a_valid_default() -> None:
    # A different code path from the "used as default" test below: "def" is present and valid, so the
    # special-as-default substitution never triggers - but type_or_range_error's val_special type-check runs
    # unconditionally whenever special is not None, so a malformed one cannot hide behind a valid default.
    field: cm.FieldSchema = ("X", "int", 5, 0, 10, "99")  # special should be int, not str
    assert cm.check_cfg_get_default(field) == (True, None)


def test_check_cfg_get_default_bool_malformed_special_type_rejected_when_used_as_default() -> None:
    # A non-bool "special" (schema-authoring error) substituted in as the default (def=None) fails
    # type_or_range_error's own bool type check the same way any other wrong-typed value would.
    assert cm.check_cfg_get_default(("X", "bool", None, None, None, 1)) == (True, None)


def test_type_or_range_error_bool_ignores_malformed_special_for_a_genuinely_valid_bool_quirk() -> None:
    # Unlike int/float/str, the bool branch never inspects "special" at all - there is no range for a bool
    # to bypass - so a wrong-typed special surfaces only via check_cfg_get_default's self-check, never by
    # rejecting an otherwise-valid bool. Deliberate, longstanding asymmetry.
    assert cm.type_or_range_error(check_val=True, field=("X", "bool", None, None, None, 1))[0] is False


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


def test_configmanager_writes_the_defaults_once_when_the_file_is_absent() -> None:
    path = _tmp_path("fresh.cfg")
    _remove(path)
    mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
    try:
        with WriteCountingOpen(cm) as counter:
            assert run(mgr.setup()) is True
        assert counter.writes == 1
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk == {"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True}
        assert mgr.pr._err_count == 0  # absence alone persists nothing: a console line only
        assert (mgr.absent_at_boot, mgr.faulted, mgr.unpersisted) == (True, False, False)
    finally:
        _remove(path)


def test_an_absent_file_is_written_once_per_boot_and_never_again() -> None:
    # One write per file per fresh filesystem: the next boot reads the file, and an unchanged PUT writes nothing.
    path = _tmp_path("oncefresh.cfg")
    _remove(path)
    try:
        with WriteCountingOpen(cm) as counter:
            run(cm.ConfigManager(path, _SCHEMA, "TEST").setup())
            assert counter.writes == 1
            with open(path) as f:
                assert json.load(f) == {"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True}
            again = cm.ConfigManager(path, _SCHEMA, "TEST")
            run(again.setup())
            assert run(_write_flushed(again, {"Count": 5})) == (True, {"Count": "Unchanged"})
        assert counter.writes == 1
        assert again.absent_at_boot is False
    finally:
        _remove(path)


def test_an_absent_files_refused_defaults_write_leaves_the_store_unpersisted() -> None:
    path = _tmp_path("absentrefused.cfg")
    _remove(path)
    mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
    with WriteCountingOpen(cm, fail_writes=True) as counter:
        run(mgr.setup())
    assert counter.writes == 1
    assert (mgr.valid, mgr.absent_at_boot, mgr.unpersisted, mgr.faulted) == (True, True, True, False)
    assert _log_entry(mgr) == (1, [code("E", "CFG_FILE_WRITE")])
    assert run(mgr.get_dict(["Count", "Name"])) == {"Count": 5, "Name": "abc"}  # the defaults, from RAM


def test_a_damaged_file_is_a_config_fault_still_listed_after_its_repair() -> None:
    # Unparseable, not an object, or holding a value the schema refuses: repaired by this boot's one write,
    # and still listed for the rest of the boot.
    path = _tmp_path("damaged.cfg")
    for content in ("{not valid json", "[1, 2]", '{"Count": 99, "Offset": 1.5, "Name": "abc", "Enabled": true}'):
        _remove(path)
        with open(path, "w") as f:
            f.write(content)
        try:
            mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
            with WriteCountingOpen(cm) as counter:
                run(mgr.setup())
            assert counter.writes == 1, content
            with open(path) as f:
                assert json.load(f) == {"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True}, content
            assert (mgr.valid, mgr.faulted, mgr.absent_at_boot, mgr.writable) == (True, True, False, True), content
        finally:
            _remove(path)


def test_schema_drift_is_repaired_without_a_config_fault() -> None:
    # A missing key or an unknown key is drift across a firmware update, not damage: one repair, no fault.
    path = _tmp_path("drift.cfg")
    for content in ('{"Offset": 1.5, "Name": "abc", "Enabled": true}', '{"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": true, "Ghost": 1}'):
        _remove(path)
        with open(path, "w") as f:
            f.write(content)
        try:
            mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
            with WriteCountingOpen(cm) as counter:
                run(mgr.setup())
            assert counter.writes == 1, content
            assert (mgr.faulted, mgr.absent_at_boot) == (False, False), content
        finally:
            _remove(path)


def test_an_absent_or_valid_file_is_no_config_fault() -> None:
    mgr, path = _make("nofault.cfg")
    try:
        assert mgr.faulted is False  # absent at its setup
        again = cm.ConfigManager(path, _SCHEMA, "TEST")
        with WriteCountingOpen(cm) as counter:
            run(again.setup())
        assert (counter.writes, again.faulted, again.absent_at_boot) == (0, False, False)
    finally:
        _remove(path)


class _LittlefsOs:
    # The Unix port's os.remove() is unlink(), which refuses a directory; littlefs's remove (vfs_lfsx.c's
    # remove) deletes an empty one and refuses a non-empty one. This stand-in gives the test that semantics.
    def stat(self, path: str) -> object:
        return os.stat(path)

    def remove(self, path: str) -> None:
        try:
            os.remove(path)
        except OSError as e:
            if e.errno != 21:  # EISDIR
                raise
            os.rmdir(path)


def test_a_config_path_that_is_a_directory_is_a_file_fault() -> None:
    path = _tmp_path("dirfault.cfg")
    _remove(path)
    os.mkdir(path)
    original_os = cm.os
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        assert run(mgr.setup()) is False
        assert mgr.faulted is True
        assert _log_entry(mgr) == (1, [code("E", "CFG_PATH_IS_DIR")])
        assert os.stat(path)[0] & 0x4000  # untouched: still the directory
        cm.os = _LittlefsOs()  # type: ignore[assignment]
        with open(path + "/inner", "w") as f:
            f.write("x")
        assert run(mgr.delete_file()) is False  # a non-empty directory stays
        os.remove(path + "/inner")
        assert run(cm.ConfigManager(path, _SCHEMA, "TEST").delete_file()) is True  # an empty one goes
        try:
            os.stat(path)
        except OSError:
            pass
        else:
            raise AssertionError("the empty directory was not removed")
    finally:
        cm.os = original_os
        _remove(path + "/inner")
        try:
            os.rmdir(path)
        except OSError:
            pass


def test_configmanager_directory_path_is_invalid() -> None:
    path = _tmp_path("adir.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        assert run(mgr.setup()) is False
        assert mgr.valid is False
    finally:
        os.rmdir(path)


def test_configmanager_empty_schema_is_invalid() -> None:
    mgr, path = _make("emptyschema.cfg", cfg_vals=())
    try:
        assert mgr.valid is False
        assert run(mgr.setup()) is False
    finally:
        _remove(path)


def test_configmanager_corrupt_json_falls_back_to_defaults() -> None:
    path = _tmp_path("corrupt.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write("{not valid json")
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        assert run(mgr.setup()) is True
        assert mgr.valid is True
        with open(path) as f:
            assert json.load(f)["Count"] == 5  # rewritten with defaults
    finally:
        _remove(path)


def test_configmanager_raw_nan_token_treated_as_corrupt_not_a_raise() -> None:
    # MicroPython's json module writes NaN/inf (json.dumps(float("nan")) -> "nan") but cannot read that
    # token back (json.loads("nan") raises ValueError), an asymmetry CPython does not have. A file holding
    # it must take the same "corrupt file, rebuild from defaults" path as any other malformed JSON.
    path = _tmp_path("nantoken.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write('{"Offset": nan}')
    try:
        mgr = cm.ConfigManager(path, _VAL_FLOAT, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Offset"])) == {"Offset": 1.5}  # rebuilt from the schema default
    finally:
        _remove(path)


def test_configmanager_value_omitted_json_quirk_self_heals() -> None:
    # MicroPython's json.load() pairs tokens in order (Part F.1), re-confirmed on the pinned v1.29.0 interpreter; distinct from the "unterminated" case
    # (fixed upstream in 2025, commit 9ef16b466, which only covers a missing closing brace or bracket).
    #
    # A value omitted before a comma or closing brace does not raise - it desyncs the parser into a mangled
    # dict instead. Not a bug in this file: every mangled key still goes through the normal per-key
    # type/range check and falls back to its own default.
    path = _tmp_path("mangled.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write('{"Count": , "Offset": 1.5, "Name": "abc", "Enabled": true}')
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 7}  # not overwritten back to the default (5)
    finally:
        _remove(path)


def test_configmanager_setup_coerces_and_rewrites_a_hand_edited_int_value_for_a_float_field() -> None:
    # A file storing a float field as a bare-integer JSON literal must be coerced to float on load - and
    # since the coerced shape differs in type from what was on disk, setup()'s `type(coerced_cfg) is not
    # type(new_cfg)` check (not `!=`, which 7 != 7.0 would miss) must fire and persist the fix.
    path = _tmp_path("setupintforfloat.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write('{"Count": 5, "Offset": 7, "Name": "abc", "Enabled": true}')  # Offset as a bare int
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Offset"])) == {"Offset": 7.0}
        assert type(mgr._cache["Offset"]) is float
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk["Offset"] == 7.0
        assert type(on_disk["Offset"]) is float  # rewritten with the corrected float shape
    finally:
        _remove(path)


def test_configmanager_setup_coerces_and_rewrites_a_hand_edited_integral_float_value_for_an_int_field() -> None:
    # Mirror of the test above, in the other direction: an int field's value hand-edited/stored as
    # "5.0" must coerce to the real int 5 and get rewritten back to disk in that shape too.
    path = _tmp_path("setupfloatforint.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write('{"Count": 5.0, "Offset": 1.5, "Name": "abc", "Enabled": true}')  # Count as an integral float
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
        assert type(mgr._cache["Count"]) is int
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk["Count"] == 5
        assert type(on_disk["Count"]) is int  # rewritten with the corrected int shape
    finally:
        _remove(path)


def test_configmanager_setup_matching_literal_shape_does_not_force_a_spurious_rewrite() -> None:
    # Negative-space companion to the two tests above: a file whose stored values already match their
    # field's declared type shape must NOT be flagged by the `type(coerced_cfg) is not type(new_cfg)` check
    # - it may only fire on an actual mismatch, not on every load.
    #
    # Proven directly by comparing the file's exact on-disk bytes before and after setup(): rewrite=True is
    # the only thing that ever calls json.dump() again there.
    path = _tmp_path("setupmatchingshape.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 7, "Offset": 2.5, "Name": "abc", "Enabled": True}, f)
    with open(path, "rb") as f:
        original_bytes = f.read()
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count", "Offset"])) == {"Count": 7, "Offset": 2.5}
        assert type(mgr._cache["Count"]) is int
        assert type(mgr._cache["Offset"]) is float
        with open(path, "rb") as f:
            assert f.read() == original_bytes  # untouched - no spurious rewrite
    finally:
        _remove(path)


def test_configmanager_missing_key_filled_with_default() -> None:
    path = _tmp_path("missingkey.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Offset": 1.5, "Name": "abc", "Enabled": True}, f)  # "Count" missing
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
    finally:
        _remove(path)


def test_configmanager_extraneous_key_removed_from_file() -> None:
    path = _tmp_path("extra.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True, "Ghost": 1}, f)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
    mgr, path = _make("floatspecial.cfg", cfg_vals=_VAL_INT + _VAL_FLOAT_SPECIAL)  # a stored field, so setup() writes a file
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "FloatSpecial" not in json.load(f)
        assert run(mgr.get_dict(["FloatSpecial"])) is None
    finally:
        _remove(path)


def test_configmanager_str_special_only_field_not_persisted() -> None:
    mgr, path = _make("strspecial.cfg", cfg_vals=_VAL_INT + _VAL_STR_SPECIAL)  # a stored field, so setup() writes a file
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "StrSpecial" not in json.load(f)
        assert run(mgr.get_dict(["StrSpecial"])) is None
    finally:
        _remove(path)


def test_configmanager_bool_special_only_field_not_persisted() -> None:
    mgr, path = _make("boolspecial.cfg", cfg_vals=_VAL_INT + _VAL_BOOL_SPECIAL)  # a stored field, so setup() writes a file
    try:
        assert mgr.valid is True
        with open(path) as f:
            assert "BoolSpecial" not in json.load(f)
        assert run(mgr.get_dict(["BoolSpecial"])) is None
    finally:
        _remove(path)


def test_configmanager_schema_entirely_special_only_creates_no_file() -> None:
    # A schema with zero storable fields (every field is special-only, a command-only schema) is valid but
    # stores nothing: no file after setup() nor after a write, and nothing persisted (a console line only).
    mgr, path = _make("allspecial.cfg", cfg_vals=_VAL_SPECIAL)
    try:
        assert mgr.valid is True
        assert run(_write_flushed(mgr, {"Special": 3})) == (True, {"Special": "Valid"})
        try:
            os.stat(path)
        except OSError:
            pass
        else:
            raise AssertionError("a command-only schema created a file")
        assert mgr.pr._err_count == 0
    finally:
        _remove(path)


def test_configmanager_single_field_schema() -> None:
    mgr, path = _make("singlefield.cfg", cfg_vals=_VAL_INT)
    try:
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
        ok, results = run(mgr.write_config({"Count": 7}))
        assert (ok, results) == (True, {"Count": "Valid"})
    finally:
        _remove(path)


def test_configmanager_large_same_type_schema() -> None:
    mgr, path = _make("largesame.cfg", cfg_vals=_LARGE_SAME_TYPE_SCHEMA)
    try:
        assert mgr.valid is True
        assert run(mgr.get_dict(["I1", "I4", "I8"])) == {"I1": 1, "I4": 4, "I8": 8}
        ok, results = run(mgr.write_config({"I3": 30}))
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
                {"Count": 9, "Offset": 2.5, "Name": "xyz", "Enabled": False, "I1": 50},
            ),
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


def test_configmanager_non_string_field_name_quirk() -> None:
    # A non-string "name" (a schema-authoring mistake) is never rejected: init succeeds and json.dump
    # silently stringifies the int key on disk. Reads now come from _cache, which is keyed by the schema's
    # own still-int name and never round-trips through JSON.
    #
    # So a read using that int key succeeds while the "123" string key actually on disk matches nothing,
    # _cache never being rebuilt from the file after setup(). Never crashes either way.
    bad_name_schema = ((123, "int", 5, 0, 10, None),)
    path = _tmp_path("badname.cfg")
    _remove(path)
    try:
        mgr = cm.ConfigManager(path, bad_name_schema, "TEST")  # type: ignore[arg-type]
        run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        assert run(mgr.setup()) is True
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
    finally:
        _remove(path)


def test_configmanager_empty_file_falls_back_to_defaults() -> None:
    path = _tmp_path("emptyfile.cfg")
    _remove(path)
    open(path, "w").close()  # 0 bytes - not even "{}"
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
            mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
            run(mgr.setup())
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
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        with open(path) as f:
            on_disk = json.load(f)
        assert "Ghost" not in on_disk
        assert on_disk["Count"] == 5
    finally:
        _remove(path)


def test_configmanager_parent_directory_missing_runs_on_defaults_unpersisted() -> None:
    # Exercises both OSError paths in setup(): os.stat() fails on the initial read, and
    # open(..., "w") also fails on the fallback write - neither is reachable in isolation without
    # a nonexistent parent directory, since every other test's tmp dir exists.
    path = _scratch.dir() + "no_such_subdir/x.cfg"
    mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
    run(mgr.setup())
    assert mgr.valid is True
    assert run(mgr.get_dict(["Count", "Offset", "Name", "Enabled"])) == {"Count": 5, "Offset": 1.5, "Name": "abc", "Enabled": True}
    assert _newest_code(mgr) == code("E", "CFG_FILE_WRITE")


def test_get_dict_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert run(mgr.get_dict(["Count"])) is None
    finally:
        os.rmdir(path)


def test_get_int_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_int.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is False
        assert run(mgr.get_int_values(_VAL_INT)) is None
    finally:
        os.rmdir(path)


def test_get_float_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_float.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is False
        assert run(mgr.get_float_values(_VAL_FLOAT)) is None
    finally:
        os.rmdir(path)


def test_get_str_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_str.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is False
        assert run(mgr.get_str_values(_VAL_STR)) is None
    finally:
        os.rmdir(path)


def test_get_bool_values_on_invalid_manager_returns_none() -> None:
    path = _tmp_path("invalidmgr_bool.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
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
    # deleting it out-of-band after a valid setup() has no effect on subsequent reads at all -
    # unlike the pre-cache design, which re-read (and so would have failed) here.
    mgr, path = _make("deletedafterinit.cfg")
    try:
        assert mgr.valid is True
        os.remove(path)
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
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


def _refused_with_one_contract_entry(mgr: "cm.ConfigManager", read: "Coroutine[Any, Any, object]") -> bool:
    # True when `read` returns None and leaves exactly one CONTRACT entry (setup()'s own entries cleared first).
    run(mgr.reset_error_counter())
    result = run(read)
    log = run(mgr.get_error_counter())[mgr.name]
    used = [log["ErrNum"][i] for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]
    return result is None and log["ErrCount"] == 1 and used == [code("E", "CONTRACT")]


def test_get_int_values_conversion_failure_returns_none() -> None:
    mgr, path = _make("badconvert.cfg")
    try:
        assert _refused_with_one_contract_entry(mgr, mgr.get_int_values(_VAL_STR))  # a str value is not an int
    finally:
        _remove(path)


def test_get_float_values_conversion_failure_returns_none() -> None:
    mgr, path = _make("badconvertfloat.cfg")
    try:
        assert _refused_with_one_contract_entry(mgr, mgr.get_float_values(_VAL_STR))  # a str value is not a float
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
    # the whole read" behavior: even though "Count" alone would read fine, "Name" (a str value is
    # not an int) discards the entire result rather than returning a partial list.
    mgr, path = _make("mixedconvertfail.cfg")
    try:
        assert _refused_with_one_contract_entry(mgr, mgr.get_int_values(_VAL_INT + _VAL_STR))
    finally:
        _remove(path)


def test_get_str_values_refuses_a_non_str_value() -> None:
    mgr, path = _make("strconvert.cfg")
    try:
        assert _refused_with_one_contract_entry(mgr, mgr.get_str_values(_VAL_INT))  # never str(5)
    finally:
        _remove(path)


def test_get_int_values_never_truncates_a_float() -> None:
    mgr, path = _make("notruncate.cfg")
    try:
        offset_as_int: cm.ConfigSchema = (("Offset", "int", 1, -10, 10, None),)  # reads the float field as int
        mgr._cache["Offset"] = 2.5
        assert _refused_with_one_contract_entry(mgr, mgr.get_int_values(offset_as_int))
        mgr._cache["Offset"] = 2.0
        assert run(mgr.get_int_values(offset_as_int)) == [2]
        enabled_as_int: cm.ConfigSchema = (("Enabled", "int", 1, 0, 1, None),)
        assert _refused_with_one_contract_entry(mgr, mgr.get_int_values(enabled_as_int))  # a bool is no int
    finally:
        _remove(path)


def test_get_bool_values_wrong_cached_type_returns_none() -> None:
    # the stored value's exact type is checked (a bool field holding a str is refused); setup() and
    # write_config both validate first, so _cache is poked directly here.
    mgr, path = _make("badconvertbool.cfg")
    try:
        mgr._cache["Enabled"] = "notabool"
        assert _refused_with_one_contract_entry(mgr, mgr.get_bool_values(_VAL_BOOL))
    finally:
        _remove(path)


def test_get_int_values_unknown_key_in_schema_returns_none() -> None:
    mgr, path = _make("typedunknownkey.cfg")
    try:
        bad_schema: cm.ConfigSchema = (("NoSuchKey", "int", 1, 0, 10, None),)
        assert _refused_with_one_contract_entry(mgr, mgr.get_int_values(bad_schema))
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
# compare_before_write() - the shared primitive every persistent-memory setter goes through: per key the
# outcome and the coerced value to write; it logs nothing and writes nothing itself.
# ---------------------------------------------------------------------------


def _tenths(value: "cm.CfgValue") -> "cm.CfgValue":
    assert isinstance(value, float)
    return round(value * 10)


def test_the_four_result_words_are_plain_module_constants() -> None:
    # Every src/ site that sets a per-field result imports these by name; tests keep the wire words literal.
    assert (cm.VALID, cm.UNCHANGED, cm.INVALID, cm.FAILED) == ("Valid", "Unchanged", "Invalid", "Failed")


def test_compare_before_write_outcome_rows() -> None:
    schema = _SCHEMA + _VAL_FLOAT_SPECIAL
    current: dict[str, cm.CfgValue] = {"Count": 5, "Offset": 1.5, "Name": "abc"}
    rows: list[tuple[str, object, str, bool, object]] = [  # key, value, outcome, written, value written
        ("Ghost", 1, "Invalid", False, None),  # unknown key
        ("Count", "7", "Invalid", False, None),  # type error
        ("Count", 11, "Invalid", False, None),  # range error
        ("Count", [7], "Invalid", False, None),  # a list value
        ("Name", {"a": 1}, "Invalid", False, None),  # a dict value
        ("Special", 99, "Valid", True, 99),  # always key: never compared
        ("Enabled", False, "Failed", False, None),  # valid, but missing from current
        ("Offset", 1.54, "Unchanged", False, None),  # equal at resolution (tenths)
        ("Offset", 1.66, "Valid", True, 1.66),  # different at resolution
        ("Count", 5, "Unchanged", False, None),  # equal without a resolution
        ("Name", "xyz", "Valid", True, "xyz"),  # different without a resolution
        ("FloatSpecial", 99, "Valid", True, 99.0),  # int for a float field, coerced
        ("Offset", 2, "Valid", True, 2.0),  # int for a float field, coerced before the compare
    ]
    for key, value, outcome, written, stored in rows:
        result = cm.compare_before_write({key: value}, schema, current, always=("Special", "FloatSpecial"), resolution={"Offset": _tenths})
        assert result is not None
        write, results = result
        assert results == {key: outcome}, (key, value)
        assert (key in write) is written, (key, value)
        if written:
            assert write[key] == stored and type(write[key]) is type(stored), (key, value, write)
    assert current == {"Count": 5, "Offset": 1.5, "Name": "abc"}  # the store's view is never touched


def test_compare_before_write_answers_every_key_of_a_multi_key_body() -> None:
    data = {"Name": "xyz", "Ghost": 1, "Count": 5, "Offset": 2.5}
    result = cm.compare_before_write(data, _SCHEMA, {"Count": 5, "Offset": 1.5, "Name": "abc"})
    assert result is not None
    write, results = result
    assert results == {"Name": "Valid", "Ghost": "Invalid", "Count": "Unchanged", "Offset": "Valid"}
    assert write == {"Name": "xyz", "Offset": 2.5}


def test_compare_before_write_refuses_a_non_object() -> None:
    for data in (None, 5, "abc", ["Count", 1], ("Count", 1)):
        assert cm.compare_before_write(data, _SCHEMA, {"Count": 5}) is None, data
    assert cm.compare_before_write({}, _SCHEMA, {"Count": 5}) == ({}, {})


# ---------------------------------------------------------------------------
# write_config
# ---------------------------------------------------------------------------


def test_write_config_valid_change_persists() -> None:
    mgr, path = _make("writevalid.cfg")
    try:
        ok, results = run(_write_flushed(mgr, {"Count": 8}))
        assert ok is True
        assert results == {"Count": "Valid"}
        assert run(mgr.get_dict(["Count"])) == {"Count": 8}
    finally:
        _remove(path)


def test_write_config_unchanged_value() -> None:
    mgr, path = _make("writeunchanged.cfg")
    try:
        ok, results = run(mgr.write_config({"Count": 5}))
        assert ok is True
        assert results == {"Count": "Unchanged"}
    finally:
        _remove(path)


def test_an_unchanged_put_schedules_no_flush() -> None:
    mgr, path = _make("unchangednoflush.cfg")
    try:
        with WriteCountingOpen(cm) as fake:
            assert run(mgr.write_config({"Count": 5, "Offset": 1.5, "Special": 99})) == (
                True, {"Count": "Unchanged", "Offset": "Unchanged", "Special": "Valid"},
            )
            assert mgr._pending_flush is None and mgr._staged is None
            run(mgr.flush_pending())
        assert (fake.writes, fake.reads) == (0, 0)
    finally:
        _remove(path)


def test_write_config_out_of_range_marked_invalid_but_call_succeeds() -> None:
    mgr, path = _make("writeinvalid.cfg")
    try:
        ok, results = run(mgr.write_config({"Count": 999}))
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
            ok, results = run(mgr.write_config({"Offset": bad}))
            assert ok is True
            assert results == {"Offset": "Invalid"}
        assert run(mgr.get_dict(["Offset"])) == {"Offset": 1.5}  # untouched, still the default
    finally:
        _remove(path)


def test_write_config_int_value_for_float_field_coerced_and_persisted_as_float() -> None:
    # End-to-end proof (not just type_or_range_error's own unit-level coverage above) that the
    # coerced value - not the caller's original int - is what actually lands in _cache and on disk.
    mgr, path = _make("writeintforfloat.cfg", cfg_vals=_VAL_FLOAT)
    try:
        ok, results = run(_write_flushed(mgr, {"Offset": 7}))
        assert (ok, results) == (True, {"Offset": "Valid"})
        assert run(mgr.get_dict(["Offset"])) == {"Offset": 7.0}
        assert type(mgr._cache["Offset"]) is float
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk["Offset"] == 7.0
        assert type(on_disk["Offset"]) is float  # written as "7.0", not "7" - real json.dump() shape
    finally:
        _remove(path)


def test_write_config_integral_float_value_for_int_field_coerced_and_persisted_as_int() -> None:
    mgr, path = _make("writefloatforint.cfg", cfg_vals=_VAL_INT)
    try:
        ok, results = run(_write_flushed(mgr, {"Count": 7.0}))
        assert (ok, results) == (True, {"Count": "Valid"})
        assert run(mgr.get_dict(["Count"])) == {"Count": 7}
        assert type(mgr._cache["Count"]) is int
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk["Count"] == 7
        assert type(on_disk["Count"]) is int  # written as "7", not "7.0"
    finally:
        _remove(path)


def test_write_config_fractional_float_value_for_int_field_rejected_end_to_end() -> None:
    mgr, path = _make("writefractionalforint.cfg", cfg_vals=_VAL_INT)
    try:
        ok, results = run(mgr.write_config({"Count": 7.5}))
        assert (ok, results) == (True, {"Count": "Invalid"})
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # untouched, still the default
    finally:
        _remove(path)


def test_write_config_int_value_for_float_field_equal_to_current_value_is_unchanged_not_valid() -> None:
    # The coerced value (7.0) must be compared against the cached value, not the caller's raw int
    # (7) - confirms new_cache[key] != value in write_config() sees the coerced shape, so a
    # would-be-genuine-no-op int PUT correctly reports "Unchanged" rather than "Valid".
    mgr, path = _make("writeintequalfloat.cfg", cfg_vals=_VAL_FLOAT)
    try:
        run(_write_flushed(mgr, {"Offset": 7}))  # first: 1.5 -> 7.0
        ok, results = run(mgr.write_config({"Offset": 7}))  # second: resubmit as an int again
        assert (ok, results) == (True, {"Offset": "Unchanged"})
    finally:
        _remove(path)


def test_write_config_unknown_key_marked_invalid() -> None:
    mgr, path = _make("writeunknown.cfg")
    try:
        ok, results = run(mgr.write_config({"NoSuchKey": 1}))
        assert ok is True
        assert results == {"NoSuchKey": "Invalid"}
    finally:
        _remove(path)


def test_write_config_special_only_key_reported_valid_but_not_stored() -> None:
    mgr, path = _make("writespecial.cfg")
    try:
        ok, results = run(_write_flushed(mgr, {"Special": 3}))
        assert ok is True
        assert results == {"Special": "Valid"}
        with open(path) as f:
            assert "Special" not in json.load(f)
    finally:
        _remove(path)


def test_write_config_key_missing_from_cache_marked_failed() -> None:
    # write_config's "key not in <the current state>" check now reads _current() (_staged if a
    # flush is pending, else _cache - see module docstring), not the file - simulate the drift by
    # poking _cache directly instead of the file.
    mgr, path = _make("writefailed.cfg")
    try:
        del mgr._cache["Count"]  # simulate _cache having lost a key out-of-band
        ok, results = run(mgr.write_config({"Count": 8}))
        assert ok is True
        assert results == {"Count": "Failed"}
    finally:
        _remove(path)


# ---------------------------------------------------------------------------
# write_config()'s deferred flush (SPECIFICATION.md Part F.2): the actual flash write is staged and handed
# to an independent asyncio.create_task(), never awaited inline - an RP2040 flash write disables interrupts
# port-wide, and inline it reset the HTTP connection whose PUT triggered it.
# ---------------------------------------------------------------------------


def test_get_dict_reads_the_staged_value_before_the_deferred_flush_lands() -> None:
    # The read-your-write guarantee this whole design exists to preserve: a GET must not have to
    # wait for the actual flash write to see a just-accepted PUT.
    mgr, path = _make("readyourwrite.cfg")
    try:

        async def write_then_read() -> "dict[str, cm.CfgValue] | None":
            # One coroutine, no intervening await on the happy path - see
            # test_write_config_genuine_write_failure_leaves_cache_unchanged's own comment for why
            # two separate top-level run() calls would race the independently-scheduled flush task.
            await mgr.write_config({"Count": 8})
            return await mgr.get_dict(["Count"])

        assert run(write_then_read()) == {"Count": 8}
        # Deliberately not asserting mgr._cache's exact value here: whether the deferred flush has
        # physically completed by this point is scheduling detail this harness's asyncio.run()-per-call
        # boundary makes non-deterministic, and get_dict()'s contract never promises it either way.
        run(mgr.flush_pending())
        assert run(mgr.get_dict(["Count"])) == {"Count": 8}  # still correct once actually flushed
        assert mgr._cache["Count"] == 8  # the default multi-field _SCHEMA - other keys stay defaulted
        with open(path) as f:
            assert json.load(f)["Count"] == 8
    finally:
        _remove(path)


def test_a_second_write_to_the_same_key_before_the_first_flush_lands_is_not_lost() -> None:
    # The "at most one unflushed staged value per sensor at a time" assumption WP5's design rests on: two
    # writes to the SAME key staged back to back, before either flush has run, must not let the first one's
    # flush clobber the second's value - exactly what _flush_staged()'s superseded-snapshot check closes.
    mgr, path = _make("doublestage.cfg")
    try:

        async def write_twice() -> None:
            await mgr.write_config({"Count": 7})
            await mgr.write_config({"Count": 9})

        run(write_twice())
        assert run(mgr.get_dict(["Count"])) == {"Count": 9}
        run(mgr.flush_pending())  # only ever holds the LATEST task - see flush_pending()'s own note
        assert mgr._cache["Count"] == 9  # the default multi-field _SCHEMA - other keys stay defaulted
        assert mgr._staged is None
        with open(path) as f:
            assert json.load(f)["Count"] == 9
    finally:
        _remove(path)


def test_write_config_value_both_out_of_range_and_missing_from_file_marked_invalid_not_failed() -> None:
    # The type/range check runs before the "is this key even present in the store" check, so
    # "Invalid" always wins over "Failed" when a submitted value is both out of range AND the key
    # has separately gone missing from the cache - confirms the deterministic check ordering.
    mgr, path = _make("invalidbeatsfailed.cfg")
    try:
        del mgr._cache["Count"]  # simulate the store having lost a key out-of-band
        ok, results = run(mgr.write_config({"Count": 999}))  # out of range, and also missing
        assert ok is True
        assert results == {"Count": "Invalid"}
    finally:
        _remove(path)


def test_write_config_wrong_type_value_for_ordinary_bool_field_marked_invalid() -> None:
    # Same "Invalid" outcome as the already-tested special-only bool field, but for a plain,
    # non-special bool field - confirms the wrong-type rejection isn't special-sentinel-specific.
    mgr, path = _make("boolwrongtype.cfg", cfg_vals=_VAL_BOOL)
    try:
        ok, results = run(mgr.write_config({"Enabled": 1}))
        assert (ok, results) == (True, {"Enabled": "Invalid"})
    finally:
        _remove(path)


def test_write_config_non_dict_data_returns_false_not_uncaught() -> None:
    # compare_before_write() answers None for anything that isn't a dict, and write_config() turns that
    # into the ordinary "write failed" (False, {}) sentinel with one BAD_ARG entry per call.
    mgr, path = _make("nondictdata.cfg")
    try:
        for bad_data in (None, 5, 12.5, "abc", ["Count", 1]):
            before = mgr.pr._err_count
            ok, results = run(mgr.write_config(bad_data))  # type: ignore[arg-type]
            assert (ok, results) == (False, {})
            assert mgr.pr._err_count - before == 1
            assert _newest_code(mgr) == code("E", "BAD_ARG")
        assert mgr._pending_flush is None
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # untouched by any of the above
    finally:
        _remove(path)


def test_write_config_on_invalid_manager_returns_false() -> None:
    path = _tmp_path("writeinvalidmgr.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        ok, results = run(mgr.write_config({"Count": 1}))
        assert (ok, results) == (False, {})
    finally:
        os.rmdir(path)


def test_write_config_empty_data_dict_is_a_noop_success() -> None:
    mgr, path = _make("emptywrite.cfg")
    try:
        ok, results = run(mgr.write_config({}))
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
            ),
        )
        assert ok is True
        assert results == {
            "Count": "Valid",
            "Offset": "Unchanged",
            "Name": "Invalid",
            "Enabled": "Failed",
            "Ghost": "Invalid",
        }
        run(mgr.flush_pending())  # the actual flash write is deferred (SPECIFICATION.md Part F.2) -
        # wait for it before inspecting the file/_cache directly, rather than get_dict()'s own
        # staged-read-through.
        with open(path) as f:
            on_disk = json.load(f)
        assert on_disk["Count"] == 8
        assert on_disk["Name"] == "abc"  # untouched
        assert "Enabled" not in on_disk  # still missing, not resurrected
        assert mgr._cache["Count"] == 8  # cache and file agree after the write
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

        ok, results = run(_write_flushed(mgr, {"Count": 7}))
        assert ok is True
        assert results == {"Count": "Valid"}
        assert run(mgr.get_dict(["Count"])) == {"Count": 7}
        with open(path) as f:
            assert json.load(f)["Count"] == 7  # the whole snapshot rewritten, the corruption gone
    finally:
        _remove(path)


def test_write_config_repairs_a_file_corrupted_after_valid_init() -> None:
    # Deliberate consequence of _cache: write_config no longer reads the file first, only writes it, so an
    # externally-corrupted file does not block a write - it is silently overwritten (repaired) from _cache
    # instead of the pre-cache design's "detect and fail".
    mgr, path = _make("writecorrupted.cfg")
    try:
        assert mgr.valid is True
        with open(path, "w") as f:
            f.write("{not valid json")
        ok, results = run(mgr.write_config({"Count": 1}))
        assert (ok, results) == (True, {"Count": "Valid"})
        run(mgr.flush_pending())  # the repair write is deferred (SPECIFICATION.md Part F.2)
        with open(path) as f:
            assert json.load(f)["Count"] == 1  # file is valid json again, repaired by the write
    finally:
        _remove(path)


def test_write_config_genuine_write_failure_keeps_the_new_value_in_effect() -> None:
    # A real write failure, unlike the pre-existing corrupt file above which gets silently repaired: the
    # parent directory is removed after a valid init, so open(path, "w") genuinely raises OSError inside the
    # deferred flush.
    #
    # write_config() itself no longer touches the filesystem (Part F.2), so it reports validation success
    # regardless and the failure only surfaces as a logged errno once the flush runs.
    #
    # The validated value stays in effect (C.7.3): its push already reached the module, so reverting the
    # read side to the old value would report a setting the device is no longer running.
    subdir = _scratch.dir() + "writefail_subdir"
    try:
        os.mkdir(subdir)
    except OSError:
        pass  # already exists
    path = subdir + "/writefail.cfg"
    _remove(path)
    mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
    run(mgr.setup())
    try:
        assert mgr.valid is True
        os.remove(path)
        os.rmdir(subdir)  # parent directory gone - the deferred flush below will genuinely fail

        async def write_read_flush() -> "tuple[bool, cm.WriteValidity, dict[str, cm.CfgValue] | None]":
            # One coroutine: the staged value is read before the flush task gets a turn, then the flush runs.
            ok, results = await mgr.write_config({"Count": 8})
            staged_view = await mgr.get_dict(["Count"])
            await mgr.flush_pending()  # now the deferred flush actually runs, and fails
            return ok, results, staged_view

        ok, results, staged_view = run(write_read_flush())
        assert (ok, results) == (True, {"Count": "Valid"})  # validation succeeded - write only staged so far
        assert staged_view == {"Count": 8}  # read-your-write, while the flush is still pending
        assert mgr._cache == {"Count": 8}
        assert mgr._staged is None
        assert run(mgr.get_dict(["Count"])) == {"Count": 8}
        assert _newest_code(mgr) == code("E", "CFG_FILE_WRITE")
    finally:
        _remove(path)  # a no-op here - the parent directory is gone, so there's nothing to remove
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
        ok, results = run(mgr.write_config({"Special": 99}))
        assert (ok, results) == (True, {"Special": "Valid"})
    finally:
        _remove(path)


def test_write_config_special_only_int_sentinel_accepts_a_coerced_integral_float() -> None:
    # Coercion runs before the special-value bypass for a special-only field too, not just an ordinary
    # ranged one (covered at the unit level by the type_or_range_error special-bypass test) - confirmed here
    # end to end through write_config()'s own "not used for storage" path.
    mgr, path = _make("specialsentinelcoerced.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": 99.0}))
        assert (ok, results) == (True, {"Special": "Valid"})
    finally:
        _remove(path)


def test_write_config_special_only_value_wrong_type_is_invalid() -> None:
    mgr, path = _make("specialwrongtype.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": "not even an int"}))
        assert (ok, results) == (True, {"Special": "Invalid"})
    finally:
        _remove(path)


def test_write_config_special_only_value_out_of_range_and_not_sentinel_is_invalid() -> None:
    mgr, path = _make("specialoutofrange.cfg")
    try:
        ok, results = run(mgr.write_config({"Special": 999}))  # neither in [0, 10] nor == 99
        assert (ok, results) == (True, {"Special": "Invalid"})
    finally:
        _remove(path)


def test_write_config_float_special_sentinel_matching_is_valid() -> None:
    mgr, path = _make("floatspecialsentinel.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"FloatSpecial": 99.0}))
        assert (ok, results) == (True, {"FloatSpecial": "Valid"})
    finally:
        _remove(path)


def test_write_config_float_special_wrong_type_is_invalid() -> None:
    mgr, path = _make("floatspecialwrongtype.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"FloatSpecial": "not a float"}))
        assert (ok, results) == (True, {"FloatSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_float_special_out_of_range_and_not_sentinel_is_invalid() -> None:
    mgr, path = _make("floatspecialoutofrange.cfg", cfg_vals=_VAL_FLOAT_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"FloatSpecial": 500.0}))  # neither [0,10] nor 99.0
        assert (ok, results) == (True, {"FloatSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_str_special_sentinel_matching_is_valid() -> None:
    mgr, path = _make("strspecialsentinel.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"StrSpecial": "OFF"}))
        assert (ok, results) == (True, {"StrSpecial": "Valid"})
    finally:
        _remove(path)


def test_write_config_str_special_wrong_type_is_invalid() -> None:
    mgr, path = _make("strspecialwrongtype.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"StrSpecial": 123}))
        assert (ok, results) == (True, {"StrSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_str_special_out_of_range_and_not_sentinel_is_invalid() -> None:
    mgr, path = _make("strspecialoutofrange.cfg", cfg_vals=_VAL_STR_SPECIAL)
    try:
        # 8 chars: outside [1, 5] and not "OFF"
        ok, results = run(mgr.write_config({"StrSpecial": "toolong!"}))
        assert (ok, results) == (True, {"StrSpecial": "Invalid"})
    finally:
        _remove(path)


def test_write_config_bool_special_any_valid_bool_is_valid() -> None:
    # Unlike int/float/str, a bool field has no range to bypass - both True (the sentinel) and
    # False (not the sentinel, but still a structurally valid bool) come back "Valid", since
    # type_or_range_error's bool branch only ever checks type, never special, for either value.
    mgr, path = _make("boolspecialsentinel.cfg", cfg_vals=_VAL_BOOL_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"BoolSpecial": True}))
        assert (ok, results) == (True, {"BoolSpecial": "Valid"})
        ok, results = run(mgr.write_config({"BoolSpecial": False}))
        assert (ok, results) == (True, {"BoolSpecial": "Valid"})
    finally:
        _remove(path)


def test_write_config_bool_special_wrong_type_is_invalid() -> None:
    mgr, path = _make("boolspecialwrongtype.cfg", cfg_vals=_VAL_BOOL_SPECIAL)
    try:
        ok, results = run(mgr.write_config({"BoolSpecial": 1}))
        assert (ok, results) == (True, {"BoolSpecial": "Invalid"})
    finally:
        _remove(path)


def test_concurrent_writes_are_serialized_not_lost() -> None:
    # Both write_config() calls read-modify-write the whole file; without _config_lock serializing
    # them, the second writer overwriting first's read would silently drop one field's update.
    mgr, path = _make("concurrent.cfg", cfg_vals=_VAL_INT + _VAL_FLOAT)

    async def scenario() -> None:
        await asyncio.gather(
            mgr.write_config({"Count": 9}),
            mgr.write_config({"Offset": 9.5}),
        )

    try:
        run(scenario())
        assert run(mgr.get_dict(["Count", "Offset"])) == {"Count": 9, "Offset": 9.5}
    finally:
        _remove(path)


# ---------------------------------------------------------------------------
# name identity / err_s/wrn_s error history / get_error_counter (name-baking and real
# error-history logging, applied to ConfigManager)
# ---------------------------------------------------------------------------


def test_configmanager_builds_its_own_cfgmgr_prefixed_name() -> None:
    mgr, path = _make("namecheck.cfg")
    try:
        assert mgr.pr.name == "CFGMGR_TEST"
    finally:
        _remove(path)


def test_get_error_counter_matches_pr_get_log_shape() -> None:
    mgr, path = _make("errcounter.cfg")
    try:
        assert run(mgr.get_error_counter()) == run(mgr.pr.get_log())
    finally:
        _remove(path)


def test_configmanager_setup_directory_path_error_recorded_via_err_s() -> None:
    # setup()'s own "exists but is not a file" branch uses err_s (real, counted history), not a
    # bare err() print that would leave get_error_counter()'s count at zero.
    path = _tmp_path("direrr.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is False
        log = run(mgr.get_error_counter())
        assert log["CFGMGR_TEST"]["ErrCount"] == 1
        assert _newest_code(mgr) == code("E", "CFG_PATH_IS_DIR")
    finally:
        os.rmdir(path)


def test_get_error_counter_accumulates_across_later_calls_too() -> None:
    # get_dict()'s own "Config is not valid, cannot read!" err_s() call (an already-async method,
    # unrelated to setup()'s own error above) adds to the same running count, not a separate one.
    path = _tmp_path("direrr2.cfg")
    _remove(path)
    os.mkdir(path)
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        run(mgr.get_dict(["Count"]))
        log = run(mgr.get_error_counter())
        assert log["CFGMGR_TEST"]["ErrCount"] == 2
        assert _newest_code(mgr) == code("E", "CFG_NOT_VALID")
    finally:
        os.rmdir(path)


def test_configmanager_corrupt_json_warning_recorded_via_wrn_s() -> None:
    # setup()'s "JSON Data ... is invalid" branch uses wrn_s (real, counted history) - the file
    # still self-heals to valid despite the recorded warning.
    path = _tmp_path("wrnhistory.cfg")
    _remove(path)
    with open(path, "w") as f:
        f.write("{not valid json")
    try:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        assert mgr.valid is True
        log = run(mgr.get_error_counter())
        assert log["CFGMGR_TEST"]["ErrCount"] == 1
        assert (_newest_code(mgr), log["CFGMGR_TEST"]["ErrType"][-1]) == (code("W", "CFG_FILE_JSON"), "W")
    finally:
        _remove(path)


# ---------------------------------------------------------------------------
# MemoryError fault injection at json.dump()/json.load() - the heap-exhaustion arm of write_config()'s and
# setup()'s except clauses. RP2040's 264KB SRAM makes a failed serialize/parse realistic, but no config file
# small enough to be safe in a test can provoke it.
#
# So asy_config_manager's own module-level `json` name is substituted instead, the same technique the UDP socket
# and UART driver suites use for their own otherwise-unreachable guards.
# ---------------------------------------------------------------------------


class _MemoryErrorJson:
    # Only the call under test raises - the others fall through to the real json module. dumps() is what the
    # store serialises with, before it opens the file; dump() stays for the fake's symmetry.
    def __init__(self, *, raise_on_dump: bool = False, raise_on_load: bool = False) -> None:
        self.raise_on_dump = raise_on_dump
        self.raise_on_load = raise_on_load

    # `stream` is `object`: it is only handed straight back to the real json module, whose own
    # stub types it as IOBase_mp | Incomplete. load() returns `object` for the same reason - every
    # consumer (asy_config_manager.setup()) isinstance-checks the result before using it.
    def dump(self, obj: "dict[str, cm.CfgValue]", stream: object) -> None:
        if self.raise_on_dump:
            raise MemoryError("simulated allocation failure")
        json.dump(obj, stream)

    def dumps(self, obj: object) -> str:
        if self.raise_on_dump:
            raise MemoryError("simulated allocation failure")
        return json.dumps(obj)

    def loads(self, text: str) -> object:
        decoded: object = json.loads(text)
        return decoded

    def load(self, stream: object) -> object:
        if self.raise_on_load:
            raise MemoryError("simulated allocation failure")
        decoded: object = json.load(stream)
        return decoded


def _file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        data: bytes = f.read()
    return data


def test_write_config_memoryerror_from_json_dump_keeps_the_new_value_in_effect() -> None:
    # MemoryError is not an OSError subclass (CLAUDE.md), _flush_staged's except clause lists it explicitly,
    # and this is the only way that arm is reached: the value stays in effect, only persistence failed.
    # The snapshot is serialised before the file is opened, so the failure leaves the file untouched.
    mgr, path = _make("memerrwrite.cfg", cfg_vals=_VAL_INT)
    try:
        assert mgr.valid is True
        before = _file_bytes(path)
        original_json = cm.json
        cm.json = _MemoryErrorJson(raise_on_dump=True)  # type: ignore[assignment]
        try:
            ok, results = run(_write_flushed(mgr, {"Count": 8}))
        finally:
            cm.json = original_json
        assert (ok, results) == (True, {"Count": "Valid"})
        assert mgr._cache == {"Count": 8}
        assert run(mgr.get_dict(["Count"])) == {"Count": 8}
        assert _file_bytes(path) == before  # setup's defaults, byte for byte
        assert json.loads(before) == {"Count": 5}
        assert _log_entry(mgr) == (1, [code("E", "CFG_FILE_WRITE")])
        ok, results = run(_write_flushed(mgr, {"Count": 8}))  # no fault injected this time
        assert (ok, results) == (True, {"Count": "Unchanged"})
        ok, results = run(_write_flushed(mgr, {"Count": 9}))
        assert (ok, results) == (True, {"Count": "Valid"})
        with open(path) as f:
            assert json.load(f) == {"Count": 9}
    finally:
        _remove(path)


def test_a_failed_serialisation_leaves_the_file_byte_identical() -> None:
    mgr, path = _make("memerrbytes.cfg")
    try:
        before = _file_bytes(path)
        original_json = cm.json
        cm.json = _MemoryErrorJson(raise_on_dump=True)  # type: ignore[assignment]
        try:
            with WriteCountingOpen(cm) as counter:
                run(_write_flushed(mgr, {"Count": 9, "Name": "xyz"}))
        finally:
            cm.json = original_json
        assert counter.writes == 0  # the open never happened
        assert _file_bytes(path) == before
    finally:
        _remove(path)


def test_configmanager_setup_memoryerror_from_json_load_serves_defaults_and_keeps_the_file() -> None:
    # A readable config file whose parse exhausts the heap is unreadable, never overwritten: the store
    # serves its defaults from RAM, refuses writes for this boot and reports its config fault.
    path = _tmp_path("memerrload.cfg")
    _remove(path)
    with open(path, "w") as f:
        json.dump({"Count": 7}, f)
    try:
        mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
        original_json = cm.json
        cm.json = _MemoryErrorJson(raise_on_load=True)  # type: ignore[assignment]  # dump() still delegates to the real module
        try:
            with WriteCountingOpen(cm) as counter:
                run(mgr.setup())
        finally:
            cm.json = original_json
        assert mgr.valid is True
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}  # the stored 7 was never actually read
        with open(path) as f:
            assert json.load(f) == {"Count": 7}  # kept, not rewritten
        assert counter.writes == 0
        log = run(mgr.get_error_counter())
        assert log["CFGMGR_TEST"]["ErrCount"] == 1  # recorded via wrn_s, not silently swallowed
        assert _newest_code(mgr) == code("W", "CFG_FILE_UNREADABLE")
        assert (mgr.writable, mgr.faulted) == (False, True)
        assert run(mgr.write_config({"Count": 8})) == (False, {})
    finally:
        _remove(path)


class _FailingOs:
    # Stands in for asy_config_manager's `os`: stat() raises the given errno, everything else is the real os.
    def __init__(self, errno_value: int) -> None:
        self.errno_value = errno_value

    def stat(self, path: str) -> object:
        raise OSError(self.errno_value)

    def remove(self, path: str) -> None:
        os.remove(path)


class _ReadFailingOpen(WriteCountingOpen):
    # Counts write-mode opens like its base, and fails every read-mode open with EIO.
    def __call__(self, path: str, mode: str = "r") -> object:
        if "w" not in mode:
            raise OSError(5)
        return super().__call__(path, mode)


def test_an_eio_on_stat_or_open_leaves_the_file_untouched() -> None:
    for stand_in in ("stat", "open"):
        path = _tmp_path("eio.cfg")
        _remove(path)
        with open(path, "w") as f:
            json.dump({"Count": 7}, f)
        before = _file_bytes(path)
        mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
        original_os = cm.os
        try:
            if stand_in == "stat":
                cm.os = _FailingOs(5)  # type: ignore[assignment]
                with WriteCountingOpen(cm) as counter:
                    run(mgr.setup())
            else:
                with _ReadFailingOpen(cm) as counter:
                    run(mgr.setup())
        finally:
            cm.os = original_os
        try:
            assert counter.writes == 0, stand_in
            assert _file_bytes(path) == before, stand_in
            assert _log_entry(mgr) == (0, []), stand_in
            assert run(mgr.get_error_counter())["CFGMGR_TEST"]["ErrCount"] == 1, stand_in  # the one W22
            assert _newest_code(mgr) == code("W", "CFG_FILE_UNREADABLE"), stand_in
            assert run(mgr.get_dict(["Count"])) == {"Count": 5}, stand_in
            assert run(mgr.write_config({"Count": 8})) == (False, {}), stand_in
            assert mgr.faulted is True, stand_in
        finally:
            _remove(path)


def test_an_enoent_from_the_same_stand_in_is_the_absent_file_path() -> None:
    path = _tmp_path("enoent.cfg")
    _remove(path)
    mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
    original_os = cm.os
    cm.os = _FailingOs(2)  # type: ignore[assignment]
    try:
        with WriteCountingOpen(cm) as counter:
            run(mgr.setup())
    finally:
        cm.os = original_os
    try:
        assert counter.writes == 1  # the absent file's one defaults write
        assert (mgr.absent_at_boot, mgr.faulted, mgr.writable) == (True, False, True)
        assert mgr.pr._err_count == 0
    finally:
        _remove(path)


def test_configmanager_setup_memoryerror_from_json_dump_runs_on_defaults_unpersisted() -> None:
    # setup()'s other MemoryError arm, around its one write: serialising first means a failure leaves no file
    # behind (absent) and the old bytes untouched (a repair). Both run on their validated values (C.7.3).
    path = _tmp_path("memerrsetupdump.cfg")
    for start in (None, '{"Count": 99}'):
        _remove(path)
        if start is not None:
            with open(path, "w") as f:
                f.write(start)
        try:
            mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
            original_json = cm.json
            cm.json = _MemoryErrorJson(raise_on_dump=True)  # type: ignore[assignment]
            try:
                run(mgr.setup())
            finally:
                cm.json = original_json
            assert mgr.valid is True  # degraded to unpersisted, not raised and not refused (C.7.3)
            assert run(mgr.get_dict(["Count"])) == {"Count": 5}
            assert _newest_code(mgr) == code("E", "CFG_FILE_WRITE")
            assert mgr.unpersisted is True
            if start is None:
                try:
                    os.stat(path)
                except OSError:
                    pass
                else:
                    raise AssertionError("a failed serialisation left a file behind")
            else:
                assert _file_bytes(path) == start.encode()
        finally:
            _remove(path)


# ---------------------------------------------------------------------------
# SPECIFICATION.md C.7.3: a failed write costs persistence, never the config, and nothing ever
# retries a write - so no failure, however persistent, can loop writes into the flash filesystem.
# ---------------------------------------------------------------------------


def _log_entry(mgr: "cm.ConfigManager") -> "tuple[int, list[int]]":
    # (count, codes) of the persisted errors; warnings are asserted by the tests that expect them.
    entry = run(mgr.pr.get_log())[mgr.name]
    nums, types = entry["ErrNum"], entry["ErrType"]
    assert isinstance(nums, list) and isinstance(types, list)
    errs = [int(n) for n, t in zip(nums, types) if t == "E"]  # noqa: B905 - MicroPython zip() rejects strict=
    return len(errs), errs


def test_setup_write_failure_attempts_exactly_one_write_and_serves_the_validated_config() -> None:
    path = _tmp_path("c73_setup_once.cfg")
    _remove(path)
    with WriteCountingOpen(cm, fail_writes=True) as fake:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
    assert fake.writes == 1
    assert mgr.valid is True
    assert run(mgr.get_int_values(_VAL_INT)) == [5]
    assert run(mgr.get_float_values(_VAL_FLOAT)) == [1.5]
    assert run(mgr.get_str_values(_VAL_STR)) == ["abc"]
    assert run(mgr.get_bool_values(_VAL_BOOL)) == [True]
    assert _log_entry(mgr) == (1, [code("E", "CFG_FILE_WRITE")])


def test_setup_write_failure_keeps_the_valid_keys_of_a_partly_bad_file() -> None:
    # The repair is computed before the write, so a failing write still runs on the repaired values:
    # the file's good keys, the default for its bad one.
    path = _tmp_path("c73_partial.cfg")
    with open(path, "w") as f:
        f.write('{"Count": 7, "Offset": "not-a-float", "Name": "xy", "Enabled": false}')
    try:
        with WriteCountingOpen(cm, fail_writes=True) as fake:
            mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
            run(mgr.setup())
        assert fake.writes == 1
        assert run(mgr.get_dict(["Count", "Offset", "Name", "Enabled"])) == {"Count": 7, "Offset": 1.5, "Name": "xy", "Enabled": False}
    finally:
        _remove(path)


def test_setup_with_a_valid_file_writes_nothing_at_all() -> None:
    path = _tmp_path("c73_nowrite.cfg")
    _remove(path)
    run(cm.ConfigManager(path, _VAL_INT, "TEST").setup())  # creates it
    try:
        with WriteCountingOpen(cm, fail_writes=True) as fake:
            mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
            run(mgr.setup())
        assert (fake.writes, fake.reads) == (0, 1)
        assert _log_entry(mgr) == (0, [])
    finally:
        _remove(path)


def test_setup_write_failure_for_each_error_class_is_logged_never_raised() -> None:
    for error in (OSError(28, "ENOSPC"), OSError(5, "EIO"), MemoryError("simulated heap exhaustion")):
        path = _tmp_path("c73_errclass.cfg")
        _remove(path)
        with WriteCountingOpen(cm, fail_writes=True, error=error) as fake:
            mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
            run(mgr.setup())
        assert (fake.writes, mgr.valid, _log_entry(mgr)) == (1, True, (1, [code("E", "CFG_FILE_WRITE")])), error


def test_no_read_path_ever_writes_after_a_failed_setup_write() -> None:
    # The write-loop guarantee on the read side: a thousand reads of every shape touch the flash zero
    # times, where a refused config used to end the reader's task and reboot into the same write.
    path = _tmp_path("c73_reads.cfg")
    _remove(path)
    with WriteCountingOpen(cm, fail_writes=True) as fake:
        mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
        run(mgr.setup())
        for _ in range(250):
            run(mgr.get_int_values(_VAL_INT))
            run(mgr.get_float_values(_VAL_FLOAT))
            run(mgr.get_dict(["Count", "Name"]))
            run(mgr.flush_pending())
        assert fake.writes == 1  # setup()'s single attempt, nothing since
    assert _log_entry(mgr) == (1, [code("E", "CFG_FILE_WRITE")])


def test_writes_follow_accepted_changes_only_never_failures() -> None:
    # One write per accepted CHANGE, zero for an unchanged, invalid or unknown value - and a failed
    # flush is not retried: the same value again is "Unchanged", so persistent failure cannot loop.
    path = _tmp_path("c73_puts.cfg")
    _remove(path)
    mgr, path = _make("c73_puts.cfg", cfg_vals=_VAL_INT)
    try:
        with WriteCountingOpen(cm, fail_writes=True) as fake:
            for value, want in ((8, "Valid"), (8, "Unchanged"), (8, "Unchanged"), (99, "Invalid"), (9, "Valid")):
                ok, results = run(mgr.write_config({"Count": value}))
                run(mgr.flush_pending())
                assert (ok, results) == (True, {"Count": want}), value
            ok, results = run(mgr.write_config({"Nope": 1}))
            run(mgr.flush_pending())
            assert results == {"Nope": "Invalid"}
            assert fake.writes == 2  # exactly the two changes
        assert run(mgr.get_dict(["Count"])) == {"Count": 9}
        expected = [code("E", "CFG_FILE_WRITE"), code("E", "BAD_ARG"), code("E", "CFG_FILE_WRITE"), code("E", "BAD_ARG")]
        assert _log_entry(mgr)[1] == expected  # failed flush, range, failed flush, unknown key
    finally:
        _remove(path)


def test_many_failed_flushes_still_write_once_per_change() -> None:
    mgr, path = _make("c73_many.cfg", cfg_vals=_VAL_INT)
    try:
        with WriteCountingOpen(cm, fail_writes=True) as fake:
            for value in (1, 2, 3, 4, 5, 6):
                run(mgr.write_config({"Count": value}))
                run(mgr.flush_pending())
                run(mgr.flush_pending())  # a second wait adds nothing
            assert fake.writes == 6
        assert mgr._staged is None and mgr._pending_flush is None
    finally:
        _remove(path)


def test_self_heals_a_failed_setup_write_on_the_next_accepted_change() -> None:
    # The flash comes back: the next real change writes the full snapshot, repaired defaults included,
    # and a fresh boot then finds a valid file and writes nothing.
    path = _tmp_path("c73_heal.cfg")
    _remove(path)
    try:
        with WriteCountingOpen(cm, fail_writes=True):
            mgr = cm.ConfigManager(path, _SCHEMA, "TEST")
            run(mgr.setup())
        with WriteCountingOpen(cm) as fake:
            assert run(mgr.write_config({"Count": 3})) == (True, {"Count": "Valid"})
            run(mgr.flush_pending())
            assert fake.writes == 1
        with open(path) as f:
            assert json.load(f) == {"Count": 3, "Offset": 1.5, "Name": "abc", "Enabled": True}
        with WriteCountingOpen(cm) as fake:
            again = cm.ConfigManager(path, _SCHEMA, "TEST")
            run(again.setup())
            assert fake.writes == 0
            assert run(again.write_config({"Count": 3})) == (True, {"Count": "Unchanged"})
            run(again.flush_pending())
            assert fake.writes == 0  # the same value after the reboot is compared, not written again
        assert run(again.get_int_values(_VAL_INT)) == [3]
    finally:
        _remove(path)


def test_self_heals_a_failed_setup_write_on_the_next_boot_with_one_write() -> None:
    path = _tmp_path("c73_reboot.cfg")
    _remove(path)
    try:
        with WriteCountingOpen(cm, fail_writes=True):
            run(cm.ConfigManager(path, _VAL_INT, "TEST").setup())
        with WriteCountingOpen(cm) as fake:
            mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
            run(mgr.setup())
            assert fake.writes == 1  # the next boot's one repair write
        with open(path) as f:
            assert json.load(f) == {"Count": 5}
    finally:
        _remove(path)


def test_self_heals_a_failed_flush_on_the_next_accepted_change() -> None:
    mgr, path = _make("c73_flushheal.cfg", cfg_vals=_VAL_INT)
    try:
        with WriteCountingOpen(cm, fail_writes=True):
            run(mgr.write_config({"Count": 7}))
            run(mgr.flush_pending())
        assert run(mgr.get_int_values(_VAL_INT)) == [7]  # still in effect while unpersisted
        with WriteCountingOpen(cm) as fake:
            run(mgr.write_config({"Count": 8}))
            run(mgr.flush_pending())
            assert fake.writes == 1
        with open(path) as f:
            assert json.load(f) == {"Count": 8}
    finally:
        _remove(path)


class _UnserialisableValue:
    # json.dump() renders an unknown object through its repr(), so a repr() that raises is what an
    # unexpected serialisation failure looks like here (MicroPython writes "<object>" for a plain one).
    def __repr__(self) -> str:
        raise RuntimeError("injected for the flush top")


def test_an_unserialisable_snapshot_ends_the_flush_task_with_one_unexpected_entry() -> None:
    mgr, path = _make("u10_unserialisable.cfg")
    try:
        mgr._cache["Name"] = _UnserialisableValue()  # type: ignore[assignment]  # planted past the schema
        before = mgr.pr._err_count

        async def write_and_flush() -> None:
            await mgr.write_config({"Count": 6})
            await mgr.flush_pending()  # the task's end is persisted, not re-raised into its waiter

        run(write_and_flush())
        assert mgr.pr._err_count == before + 1
        assert _newest_code(mgr) == code("E", "UNEXPECTED")
        assert mgr._pending_flush is None
        assert mgr.unpersisted is True  # the cache holds a snapshot the file never received
    finally:
        _remove(path)


def test_the_only_flash_writes_in_config_manager_are_the_two_known_sites() -> None:
    # Structural half of the write-loop guarantee: exactly setup()'s and _flush_staged()'s opens
    # for writing, and nothing in the module that could re-run one on its own - no timer, no sleep,
    # no loop that waits. A new write site or retry mechanism has to come through here.
    with open(cm.__file__) as f:
        source = f.read()
    assert source.count('open(self._config_file, "w")') == 2
    assert source.count('"w"') == 2
    assert source.count("json.dump(") == 0  # every write serialises first, then opens
    code = [line.split("#")[0] for line in source.split("\n")]  # comments may say anything
    for forbidden in ("Timer", "sleep", "while "):
        assert not any(forbidden in line for line in code), forbidden
    assert source.count("create_task(") == 1  # write_config()'s one deferred flush per accepted change
    start = source.index("def compare_before_write(")
    body = [line.split("#")[0] for line in source[start : source.index("\nclass ", start)].split("\n")]
    for forbidden in ("Timer", "sleep", "while ", '"w"', "open(", "create_task(", "await ", "self.pr"):
        assert not any(forbidden in line for line in body), forbidden  # the primitive neither writes nor logs


def test_a_float_equal_in_stored_form_is_unchanged() -> None:
    # A float is compared and staged in the form the file reloads as: a lossy store (3 decimals here) turns a
    # repeat of the same PUT into "Unchanged" with no write, the rp2 single-precision case in miniature.
    original = cm._stored_float
    cm._stored_float = lambda v: round(v, 3) if type(v) is float else v
    mgr, path = _make("storedform.cfg", cfg_vals=_VAL_FLOAT)
    try:
        assert run(_write_flushed(mgr, {"Offset": 1.23456})) == (True, {"Offset": "Valid"})
        assert mgr._cache["Offset"] == round(1.23456, 3)
        with WriteCountingOpen(cm) as counter:
            assert run(_write_flushed(mgr, {"Offset": 1.23456})) == (True, {"Offset": "Unchanged"})
        assert counter.writes == 0
    finally:
        cm._stored_float = original
        _remove(path)


class _NoTaskAsyncio:
    # Stands in for asy_config_manager's `asyncio` during a write: building the flush task fails by allocation.
    Lock = asyncio.Lock
    Event = asyncio.Event
    current_task = asyncio.current_task

    @staticmethod
    def create_task(coro: "Coroutine[Any, Any, None]") -> None:
        coro.close()
        raise MemoryError("injected for the flush task")


def test_a_failed_task_creation_stages_nothing() -> None:
    for defer in (False, True):
        mgr, path = _make("notask.cfg", cfg_vals=_VAL_INT)
        original = cm.asyncio
        cm.asyncio = _NoTaskAsyncio  # type: ignore[assignment]
        try:
            assert run(mgr.write_config({"Count": 8}, defer=defer)) == (False, {}), defer
        finally:
            cm.asyncio = original
        try:
            assert run(mgr.get_dict(["Count"])) == {"Count": 5}, defer
            assert mgr._staged is None and mgr._pending_flush is None, defer
            assert mgr._commit_ready.is_set(), defer  # a later deferred write is not held by this one
            assert _log_entry(mgr) == (1, [code("E", "ALLOC")]), defer
        finally:
            _remove(path)


def test_a_flush_equal_to_the_cache_opens_nothing() -> None:
    mgr, path = _make("flushequal.cfg", cfg_vals=_VAL_INT)
    try:
        staged = dict(mgr._cache)
        mgr._staged = staged
        with WriteCountingOpen(cm) as counter:
            run(mgr._flush_staged(staged))
        assert counter.writes == 0
        assert mgr._staged is None
    finally:
        _remove(path)


def test_two_deferred_writes_then_one_commit_write_the_second_once() -> None:
    mgr, path = _make("twodeferred.cfg", cfg_vals=_VAL_INT)
    try:

        async def scenario() -> "tuple[int, int]":
            with WriteCountingOpen(cm) as counter:
                await mgr.write_config({"Count": 7}, defer=True)
                first = mgr._pending_flush
                assert first is not None
                await mgr.write_config({"Count": 9}, defer=True)
                for _ in range(3):
                    await asyncio.sleep(0)
                held = counter.writes  # both wait for the commit
                mgr.commit()
                await mgr.flush_pending()
                await first  # superseded: returns without writing
            return held, counter.writes

        assert run(scenario()) == (0, 1)
        with open(path) as f:
            assert json.load(f) == {"Count": 9}
    finally:
        _remove(path)


def test_flush_pending_releases_an_uncommitted_deferred_write() -> None:
    mgr, path = _make("releasedeferred.cfg", cfg_vals=_VAL_INT)
    try:

        async def scenario() -> None:
            await mgr.write_config({"Count": 6}, defer=True)
            await mgr.flush_pending()  # no commit(): the flush is released here

        run(scenario())
        with open(path) as f:
            assert json.load(f) == {"Count": 6}
    finally:
        _remove(path)


def test_a_failed_flush_marks_the_store_unpersisted_until_a_good_flush() -> None:
    mgr, path = _make("unpersisted.cfg", cfg_vals=_VAL_INT)
    try:
        with WriteCountingOpen(cm, fail_writes=True) as counter:
            assert run(_write_flushed(mgr, {"Count": 7})) == (True, {"Count": "Valid"})
        assert counter.writes == 1  # one attempt, no retry
        states = [mgr.unpersisted]
        assert _log_entry(mgr) == (1, [code("E", "CFG_FILE_WRITE")])
        assert mgr._cache == {"Count": 7}  # in effect, unpersisted
        with WriteCountingOpen(cm) as counter:
            assert run(_write_flushed(mgr, {"Count": 7})) == (True, {"Count": "Unchanged"})
        assert counter.writes == 0
        states.append(mgr.unpersisted)  # an equal write changes nothing
        assert run(_write_flushed(mgr, {"Count": 8})) == (True, {"Count": "Valid"})
        states.append(mgr.unpersisted)
        with open(path) as f:
            assert json.load(f) == mgr._cache == {"Count": 8}
        with WriteCountingOpen(cm) as counter:
            assert run(_write_flushed(mgr, {"Count": 8})) == (True, {"Count": "Unchanged"})
        assert counter.writes == 0
        states.append(mgr.unpersisted)
        assert states == [True, True, False, False]
    finally:
        _remove(path)


# ---------------------------------------------------------------------------
# Closing for a reset, delete_file(), and the store-level interleavings; each interleaving is forced by a
# gate (the lock, or the logger the write path awaits inside it), never a sleep.
# ---------------------------------------------------------------------------


def test_a_closed_store_refuses_writes_and_opens_nothing() -> None:
    mgr, path = _make("closed.cfg", cfg_vals=_VAL_INT)
    try:
        mgr.close_writes()
        with WriteCountingOpen(cm) as counter:
            assert run(_write_flushed(mgr, {"Count": 8})) == (False, {})
        assert counter.writes == 0
        assert run(mgr.get_dict(["Count"])) == {"Count": 5}
    finally:
        _remove(path)


class _RemoveFailingOs:
    # asy_config_manager's `os` with a remove() that fails `failures` times with EIO, then removes for real.
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def stat(self, path: str) -> object:
        return os.stat(path)

    def remove(self, path: str) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise OSError(5)
        os.remove(path)


def _exists(path: str) -> bool:
    try:
        os.stat(path)
    except OSError:
        return False
    return True


def test_delete_file_removes_the_file_and_closes_the_store() -> None:
    mgr, path = _make("delete.cfg", cfg_vals=_VAL_INT)
    try:
        assert run(mgr.delete_file()) is True
        assert _exists(path) is False
        assert run(mgr.delete_file()) is True  # absent: nothing to do
        assert run(mgr.write_config({"Count": 8})) == (False, {})
    finally:
        _remove(path)


def test_delete_file_retries_once_then_reports_a_failure() -> None:
    for failures, deleted in ((1, True), (2, False)):
        path = _tmp_path("deleteretry.cfg")
        _remove(path)
        mgr = cm.ConfigManager(path, _VAL_INT, "TEST", log=LogConfig(None, 10, 1))
        run(mgr.setup())
        stand_in = _RemoveFailingOs(failures)
        original_os = cm.os
        cm.os = stand_in  # type: ignore[assignment]
        recorder = _PrintRecorder()
        try:
            assert run(mgr.delete_file()) is deleted, failures
        finally:
            recorder.restore()
            cm.os = original_os
        try:
            assert stand_in.calls == 2, failures  # the one retry
            assert _exists(path) is not deleted, failures
            failed_lines = [line for line in recorder.lines if "- could not be deleted:" in line]
            assert len(failed_lines) == (0 if deleted else 1), failures
            assert run(mgr.write_config({"Count": 8})) == (False, {}), failures
        finally:
            _remove(path)


def test_a_flush_held_at_the_lock_lands_after_close_and_flush_pending() -> None:
    mgr, path = _make("heldflush.cfg", cfg_vals=_VAL_INT)
    try:

        async def scenario() -> None:
            await mgr.write_config({"Count": 8})
            await mgr._config_lock.acquire()  # the flush task now waits at the lock
            for _ in range(3):
                await asyncio.sleep(0)
            mgr.close_writes()
            waiter = asyncio.create_task(mgr.flush_pending())
            for _ in range(3):
                await asyncio.sleep(0)
            mgr._config_lock.release()
            await waiter

        run(scenario())
        with open(path) as f:
            assert json.load(f) == {"Count": 8}
    finally:
        _remove(path)


def test_a_write_suspended_inside_the_lock_finishes_and_its_flush_is_awaited() -> None:
    mgr, path = _make("suspendedwrite.cfg", cfg_vals=_VAL_INT)
    try:
        gate = asyncio.Event()
        real_err_s = mgr.pr.err_s

        async def gated_err_s(*args: object, errno: int = 0, sep: str = " ", end: str = "\n") -> None:
            await gate.wait()
            await real_err_s(*args, errno=errno, sep=sep, end=end)

        mgr.pr.err_s = gated_err_s  # type: ignore[method-assign]

        async def scenario() -> "tuple[bool, cm.WriteValidity]":
            writer = asyncio.create_task(mgr.write_config({"Count": 8, "Ghost": 1}))
            for _ in range(3):
                await asyncio.sleep(0)  # the writer now waits in its err_s() for "Ghost", inside the lock
            mgr.close_writes()
            flusher = asyncio.create_task(mgr.flush_pending())
            for _ in range(3):
                await asyncio.sleep(0)
            gate.set()
            result = await writer
            await flusher
            return result

        assert run(scenario()) == (True, {"Count": "Valid", "Ghost": "Invalid"})
        with open(path) as f:
            assert json.load(f) == {"Count": 8}
    finally:
        _remove(path)


def test_a_write_queued_behind_the_lock_at_close_time_is_refused() -> None:
    mgr, path = _make("queuedwrite.cfg", cfg_vals=_VAL_INT)
    try:

        async def scenario() -> "tuple[bool, cm.WriteValidity]":
            await mgr._config_lock.acquire()
            writer = asyncio.create_task(mgr.write_config({"Count": 8}))
            for _ in range(3):
                await asyncio.sleep(0)  # past the pre-lock checks, waiting at the lock
            mgr.close_writes()
            mgr._config_lock.release()
            return await writer

        with WriteCountingOpen(cm) as counter:
            assert run(scenario()) == (False, {})
        assert counter.writes == 0
        with open(path) as f:
            assert json.load(f) == {"Count": 5}
    finally:
        _remove(path)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
