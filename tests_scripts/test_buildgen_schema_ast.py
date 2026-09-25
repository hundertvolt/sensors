"""Tests for buildgen.schema_ast: the never-imported AST extraction of a driver's real
`ConfigSchema`/`FieldSchema` constant (SPECIFICATION.md Part H.5.1). Covers both real assignment
shapes, every `_eval_literal` node kind, and the silent-skip behavior for anything else."""

from pathlib import Path

import pytest

from buildgen.schema_ast import FieldSchema, extract_field_schemas


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _extract(tmp_path: Path, source: str) -> "dict[str, FieldSchema]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return extract_field_schemas(path)


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


def test_extract_field_schemas_unresolvable_name_reference_is_silently_skipped(tmp_path: Path) -> None:
    # _UNDEFINED is never assigned anywhere in this file - a real gap this best-effort pass must
    # not crash on, and must not let poison an otherwise-valid sibling schema in the same file.
    source = (
        '_VAL_BAD = const((("Bad", "int", 1, None, None, _UNDEFINED),))\n'
        '_VAL_GOOD = const((("Good", "int", 1, None, None, None),))\n'
    )
    fields = _extract(tmp_path, source)
    assert fields == {"Good": ("int", 1, None, None, None)}


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


def test_extract_field_schemas_config_schema_of_one_with_malformed_inner_tuple_is_skipped(tmp_path: Path) -> None:
    fields = _extract(tmp_path, '_VAL_BAD = const((("X", "int", 1, None, None),))\n')
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


# ---------------------------------------------------------------------------
# Real drivers - a spot check that the Name/const()-unwrapping machinery works on real code, not
# just synthetic fixtures (mirrors every other buildgen module's own "D8 real drivers" convention).
# ---------------------------------------------------------------------------


def test_extract_field_schemas_real_bmp3xx_resolves_named_choice_sets(src_dir: Path) -> None:
    fields = extract_field_schemas(src_dir / "asy_bmp3xx_driver.py")
    assert fields["PressOvers"] == ("int", 1, None, None, (1, 2, 4, 8, 16, 32))
    assert fields["TempOvers"] == ("int", 1, None, None, (1, 2, 4, 8, 16, 32))
    assert fields["FiltCoeff"] == ("int", 0, None, None, (0, 1, 3, 7, 15, 31, 63, 127))


def test_extract_field_schemas_real_scd30_has_no_schema_entry_for_contmeas(src_dir: Path) -> None:
    # ContMeas is deliberately freestanding (no _VAL_* constant at all - see the driver's own
    # comment); confirms the AST scan doesn't invent one.
    fields = extract_field_schemas(src_dir / "asy_scd30_driver.py")
    assert "ContMeas" not in fields
    assert fields["AmbPres"] == ("int", None, 700, 1400, 0)
