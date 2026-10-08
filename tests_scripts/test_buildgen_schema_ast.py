"""Tests for buildgen.schema_ast: the never-imported AST extraction of a driver's real
`ConfigSchema`/`FieldSchema` constants (SPECIFICATION.md Part H.5.1). Covers both real assignment
shapes, every `_eval_literal` node kind, the raise for a broken schema constant and the skip for others."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.schema_ast import FieldSchema, extract_field_schemas


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _extract(tmp_path: Path, source: str) -> "dict[str, FieldSchema]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return extract_field_schemas(path)


def _extract_expecting(tmp_path: Path, source: str, match: str, rule: str) -> BuildError:
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    with pytest.raises(BuildError, match=match) as raised:
        extract_field_schemas(path, device="fixture", instance_label="x")
    assert (raised.value.rule, raised.value.device, raised.value.instance) == (rule, "fixture", "x")
    return raised.value


def test_extract_field_schemas_config_schema_of_one_shape(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_VAL_X = const((("X", "int", 5, 0, 100, None),))\n')
    assert fields == {"X": ("int", 5, 0, 100, None)}


def test_extract_field_schemas_bare_field_schema_ann_assign_shape(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_X: "cm.FieldSchema" = ("X", "int", 5, 0, 100, None)\n')
    assert fields == {"X": ("int", 5, 0, 100, None)}


def test_extract_field_schemas_plain_assign_bare_tuple_shape(tmp_path: Path) -> None:
    # Same 6-tuple shape, but a plain Assign rather than an AnnAssign - both are real src/ shapes.
    fields = _extract(tmp_path, '_X = ("X", "int", 5, 0, 100, None)\n')
    assert fields == {"X": ("int", 5, 0, 100, None)}


def test_extract_field_schemas_negative_number_literals(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_VAL_T = const((("Temp", "float", None, -40.0, 85.0, None),))\n')
    assert fields == {"Temp": ("float", None, -40.0, 85.0, None)}


def test_extract_field_schemas_negative_int_stays_int(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_VAL_O = const((("Offset", "int", 0, -100, 100, None),))\n')
    (min_v,) = (fields["Offset"][2],)
    assert min_v == -100
    assert type(min_v) is int


@pytest.mark.parametrize("brackets", [("(", ")"), ("[", "]")])
def test_extract_field_schemas_resolves_const_wrapped_name_reference(tmp_path: Path, brackets: "tuple[str, str]") -> None:
    # A real driver's discrete-choice set is itself a separate const()-wrapped module constant
    # (e.g. asy_bmp3xx_driver.py's _OSR_SETTINGS), referenced by Name from the schema tuple - and
    # may be a tuple or a list literal (both real Python, both handled identically).
    open_b, close_b = brackets
    source = (
        f"_CHOICES = const({open_b}1, 2, 4{close_b})\n"
        '_VAL_P = const((("P", "int", 1, None, None, _CHOICES),))\n'
    )
    fields = _extract(tmp_path, source)
    assert fields["P"] == ("int", 1, None, None, (1, 2, 4))


def test_extract_field_schemas_unresolvable_name_reference_in_another_constant_is_skipped(tmp_path: Path) -> None:
    # _UNDEFINED is never assigned anywhere in this file: a constant that is no schema by name or
    # annotation may hold it without poisoning a valid schema in the same file.
    source = (
        '_BAD = const((("Bad", "int", 1, None, None, _UNDEFINED),))\n'
        '_VAL_GOOD = const((("Good", "int", 1, None, None, None),))\n'
    )
    fields = _extract(tmp_path, source)
    assert fields == {"Good": ("int", 1, None, None, None)}


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('_VAL_BAD = const((("Bad", "int", 1, None, None, _UNDEFINED),))\n', id="unresolvable-name"),
        pytest.param('_BAD: "cm.ConfigSchema" = make_schema()\n', id="annotated-call"),
        pytest.param("_VAL_A = _VAL_B\n_VAL_B = _VAL_A\n", id="circular-names"),
        pytest.param("_VAL_SUM = 1 + 2\n", id="concatenating-non-tuples"),
    ],
)
def test_extract_field_schemas_an_unreadable_schema_constant_fails_the_build(tmp_path: Path, source: str) -> None:
    # A schema named by _VAL_* or by its ConfigSchema/FieldSchema annotation must evaluate: a
    # silently skipped one would drop its fields from the website without a word.
    error = _extract_expecting(tmp_path, source, "cannot be read at build time", "schema.unreadable")
    assert error.fix == "keep schema constants literal (numbers, strings, tuples, const(), names of other literal constants)"


@pytest.mark.parametrize(
    "source,why",
    [
        pytest.param('_VAL_BAD = const((("X", "int", 1, None, None),))\n', "5 items", id="five-item-record"),
        pytest.param('_VAL_BAD = const(((1, "int", 1, None, None, None),))\n', "name", id="non-str-name"),
        pytest.param('_VAL_BAD = const((("X", 1, 1, None, None, None),))\n', "type", id="non-str-type"),
        pytest.param('_VAL_BAD = const((("X", "integer", 1, None, None, None),))\n', "type", id="unknown-type-word"),
        pytest.param("_VAL_BAD = const(5)\n", "not a tuple", id="not-a-tuple"),
        pytest.param('_BAD: "FieldSchema" = ("X", "int", 1, None, None)\n', "5 items", id="annotated-five-item-record"),
    ],
)
def test_extract_field_schemas_a_malformed_schema_constant_fails_the_build(tmp_path: Path, source: str, why: str) -> None:
    error = _extract_expecting(tmp_path, source, "is malformed", "schema.malformed")
    assert why in error.message


def test_extract_field_schemas_a_schema_error_names_the_constant_and_its_line(tmp_path: Path) -> None:
    error = _extract_expecting(tmp_path, "_X = 1\n_VAL_BAD = const(5)\n", "is malformed", "schema.malformed")
    assert error.message.startswith(f"{tmp_path / 'asy_x_driver.py'}:2: schema constant _VAL_BAD ")


def test_extract_field_schemas_a_circular_reference_elsewhere_is_skipped_not_a_recursion_error(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_A = _B\n_B = _A\n_VAL_GOOD = const((("Good", "int", 1, None, None, None),))\n')
    assert fields == {"Good": ("int", 1, None, None, None)}


def test_extract_field_schemas_reads_a_concatenated_schema(tmp_path: Path) -> None:
    source = (
        '_VAL_A = const((("A", "int", 1, 0, 10, None),))\n'
        '_VAL_B = const((("B", "float", 1.0, 0.0, 2.0, None),))\n'
        "_VAL_ALL = _VAL_A + _VAL_B\n"
    )
    assert _extract(tmp_path, source) == {"A": ("int", 1, 0, 10, None), "B": ("float", 1.0, 0.0, 2.0, None)}


def test_extract_field_schemas_reads_every_record_of_a_multi_field_schema(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_VAL_TWO = const((("A", "int", 1, 0, 10, None), ("B", "bool", True, None, None, None)))\n')
    assert fields == {"A": ("int", 1, 0, 10, None), "B": ("bool", True, None, None, None)}


@pytest.mark.parametrize("annotation", ['"tuple[cm.FieldSchema, ...]"', "tuple[FieldSchema, ...]", '"tuple[FieldSchema]"'])
def test_extract_field_schemas_reads_every_record_of_an_annotated_tuple_of_field_schemas(tmp_path: Path, annotation: str) -> None:
    fields = _extract(tmp_path, f'_TWO: {annotation} = (("A", "int", None, 0, 255, None), ("B", "float", None, 0.5, 60.0, None))\n')
    assert fields == {"A": ("int", None, 0, 255, None), "B": ("float", None, 0.5, 60.0, None)}


def test_extract_field_schemas_an_unannotated_tuple_of_records_is_still_skipped(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_TWO = (("A", "int", None, 0, 255, None), ("B", "float", None, 0.5, 60.0, None))\n')
    assert fields == {}


@pytest.mark.parametrize("annotation", ['"tuple[int, ...]"', '"tuple[cm.FieldSchema"', '"tuple[()]"', '"list[cm.FieldSchema]"'])
def test_extract_field_schemas_a_tuple_annotation_of_another_type_is_no_schema(tmp_path: Path, annotation: str) -> None:
    fields = _extract(tmp_path, f'_TWO: {annotation} = (("A", "int", None, 0, 255, None), ("B", 1, None, 0.5, 60.0, None))\n')
    assert fields == {}


def test_extract_field_schemas_an_annotated_tuple_with_a_malformed_record_fails_the_build(tmp_path: Path) -> None:
    source = '_TWO: "tuple[cm.FieldSchema, ...]" = (("A", "int", None, 0, 255, None), ("B", "float", None, 0.5))\n'
    error = _extract_expecting(tmp_path, source, "is malformed", "schema.malformed")
    assert "4 items" in error.message


def test_extract_field_schemas_unsupported_node_shape_is_silently_skipped(tmp_path: Path) -> None:
    # A dict literal, an ordinary function call, and a binary op are all real constants a driver
    # file might have at module level that are simply not schema literals - none should raise.
    source = (
        "_D = {}\n"
        "_C = SomeClass()\n"
        "_B = 1 + 2\n"
        '_VAL_GOOD = const((("Good", "int", 1, None, None, None),))\n'
    )
    fields = _extract(tmp_path, source)
    assert fields == {"Good": ("int", 1, None, None, None)}


def test_extract_field_schemas_non_numeric_negation_is_silently_skipped(tmp_path: Path) -> None:
    # -("a", "b") is syntactically valid (ast.parse accepts USub on any factor) but not a numeric
    # literal - _eval_literal must raise TypeError (not crash uncaught), and extract_field_schemas
    # must swallow it the same as any other unsupported shape.
    source = (
        '_BAD = -("a", "b")\n'
        '_VAL_GOOD = const((("Good", "int", 1, None, None, None),))\n'
    )
    fields = _extract(tmp_path, source)
    assert fields == {"Good": ("int", 1, None, None, None)}


def test_extract_field_schemas_wrong_shaped_tuple_is_not_a_field_schema(tmp_path: Path) -> None:
    # A 6-tuple whose first two elements aren't both strings, and tuples of the wrong length
    # entirely, are ordinary module constants - not FieldSchema, so neither should be extracted.
    source = (
        "_NOT_A_SCHEMA = (1, 2, 3, 4, 5, 6)\n"
        '_ALSO_NOT = ("X", "int", 1, None, None)\n'
    )
    fields = _extract(tmp_path, source)
    assert fields == {}


def test_extract_field_schemas_six_string_tuple_is_not_a_field_schema(tmp_path: Path) -> None:
    # A plain tuple of six names (a key order, say) is no schema: the second item must be a type.
    fields = _extract(tmp_path, '_ORDER = const(("TempOffset", "MeasInterval", "AmbPres", "Altitude", "ForceCalRef", "SelfCal"))\n')
    assert fields == {}


def test_extract_field_schemas_another_constant_with_a_malformed_inner_tuple_is_skipped(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_BAD = const((("X", "int", 1, None, None),))\n')
    assert fields == {}


def test_extract_field_schemas_multiple_fields_across_multiple_constants(tmp_path: Path) -> None:
    source = (
        '_VAL_A = const((("A", "int", 1, 0, 10, None),))\n'
        '_VAL_B = const((("B", "bool", False, None, None, None),))\n'
        '_C: "cm.FieldSchema" = ("C", "str", "", None, None, None)\n'
    )
    fields = _extract(tmp_path, source)
    assert set(fields) == {"A", "B", "C"}


def test_extract_field_schemas_no_matching_constants_returns_empty_dict(tmp_path: Path) -> None:
    assert _extract(tmp_path, "class Plain_Reader:\n    pass\n") == {}


def test_extract_field_schemas_last_assignment_wins_on_a_name_collision(tmp_path: Path) -> None:
    # Two module-level assignments to the same Python name (e.g. reassigned further down the file)
    # - consts resolution walks tree.body in source order, so the later one must be the one used.
    source = (
        "_X = 1\n"
        '_X = const((("X", "int", 1, None, None, None),))\n'
    )
    fields = _extract(tmp_path, source)
    assert fields == {"X": ("int", 1, None, None, None)}


def test_extract_field_schemas_unreadable_file_is_a_build_error(tmp_path: Path) -> None:
    with pytest.raises(BuildError, match="cannot read") as raised:
        extract_field_schemas(tmp_path / "asy_x_driver.py", device="fixture", instance_label="x")
    assert (raised.value.rule, raised.value.device, raised.value.instance) == ("src.unreadable", "fixture", "x")


def test_extract_field_schemas_a_syntax_error_names_the_file(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text("class Broken(:\n")
    with pytest.raises(BuildError, match="has a syntax error") as raised:
        extract_field_schemas(path, device="fixture", instance_label="x")
    assert raised.value.rule == "source.syntax-error"
    assert str(path) in raised.value.message


def test_extract_field_schemas_places_its_errors_at_the_callers_field(tmp_path: Path) -> None:
    # A caller resolving one field (the validator's Wi-Fi bounds) gets that field named, whatever failed.
    with pytest.raises(BuildError, match="cannot read") as raised:
        extract_field_schemas(tmp_path / "asy_x_driver.py", field="HotspotPW")
    assert (raised.value.rule, raised.value.field) == ("src.unreadable", "HotspotPW")
    path = tmp_path / "asy_x_driver.py"
    for text, rule in (("class Broken(:\n", "source.syntax-error"), ('_VAL_A = const((("A", "int", 2, 0, 10),))\n', "schema.malformed")):
        path.write_text(text)
        with pytest.raises(BuildError) as raised:
            extract_field_schemas(path, field="HotspotPW")
        assert (raised.value.rule, raised.value.field, str(raised.value).startswith("[<src>.HotspotPW] ")) == (rule, "HotspotPW", True)


def test_extract_field_schemas_follows_a_file_rewritten_at_the_same_path(tmp_path: Path) -> None:
    # Cached by the file's text, never its path.
    assert _extract(tmp_path, '_VAL_A = const((("A", "int", 1, 0, 10, None),))\n') == {"A": ("int", 1, 0, 10, None)}
    assert _extract(tmp_path, '_VAL_A = const((("A", "int", 2, 0, 10, None),))\n') == {"A": ("int", 2, 0, 10, None)}
    with pytest.raises(BuildError, match="is malformed"):
        _extract(tmp_path, '_VAL_A = const((("A", "int", 2, 0, 10),))\n')


def test_extract_field_schemas_a_caller_mutating_its_result_changes_no_later_one(tmp_path: Path) -> None:
    first = _extract(tmp_path, '_VAL_A = const((("A", "int", 1, 0, 10, None),))\n')
    first["B"] = ("int", 0, None, None, None)
    del first["A"]
    assert _extract(tmp_path, '_VAL_A = const((("A", "int", 1, 0, 10, None),))\n') == {"A": ("int", 1, 0, 10, None)}


# ---------------------------------------------------------------------------
# Real drivers - a spot check that the Name/const()-unwrapping machinery works on real code, not
# just synthetic fixtures (mirrors every other buildgen module's own "D8 real drivers" convention).
# ---------------------------------------------------------------------------


def test_extract_field_schemas_real_bmp3xx_resolves_named_choice_sets(src_dir: Path) -> None:
    fields = extract_field_schemas(src_dir / "asy_bmp3xx_driver.py")
    assert fields["PresOvers"] == ("int", 1, None, None, (1, 2, 4, 8, 16, 32))
    assert fields["TempOvers"] == ("int", 1, None, None, (1, 2, 4, 8, 16, 32))
    assert fields["FiltCoeff"] == ("int", 0, None, None, (0, 1, 3, 7, 15, 31, 63, 127))


def test_extract_field_schemas_real_scd30_reads_contmeas_from_its_synthetic_field_schema(src_dir: Path) -> None:
    # ContMeas has no _VAL_* constant: its schema is the bare module-level FieldSchema _CONT_MEAS_FIELD,
    # which the AST scan reads like any other (SPECIFICATION.md H.5.1).
    fields = extract_field_schemas(src_dir / "asy_scd30_driver.py")
    assert fields["ContMeas"] == ("bool", None, None, None, None)
    assert fields["AmbPres"] == ("int", None, 700, 1400, 0)


def test_extract_field_schemas_real_webserver_reads_its_dispatch_validation_records(src_dir: Path) -> None:
    # The two dispatch-only fields' synthetic records: PauseTime's bare FieldSchema and LightCmdLED's tuple of them.
    fields = extract_field_schemas(src_dir / "asy_webserver_service.py")
    assert set(fields) == {"PauseTime", "R", "G", "B", "T"}
    assert fields["T"] == ("float", None, 0.5, 60.0, None)
