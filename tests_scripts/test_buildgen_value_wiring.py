"""Tests for buildgen.value_wiring: the `# @value-wiring <toml_field> <kwarg> <required|optional>`
comment tag - per-value measurement wiring (SPECIFICATION.md Part L.6.3). Walks the same
accept/reject dimensions as test_buildgen_wiring.py; see that file's own dimension index."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.value_wiring import ValueWiringField, parse_value_wiring


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _parse(tmp_path: Path, source: str) -> "tuple[ValueWiringField, ...]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return parse_value_wiring(path, "dev", "x")


def _parse_expecting(tmp_path: Path, source: str, match: str) -> None:
    with pytest.raises(BuildError, match=match):
        _parse(tmp_path, source)


@pytest.mark.parametrize("word,required", [("required", True), ("optional", False)])
def test_parse_value_wiring_both_requiredness_words(tmp_path: Path, word: str, *, required: bool) -> None:
    (field,) = _parse(tmp_path, f"# @value-wiring temperature_source temperature {word}\n")
    assert field == ValueWiringField("temperature_source", "temperature", required)


def test_parse_value_wiring_kwarg_may_differ_from_the_toml_field(tmp_path: Path) -> None:
    # The two names are independent: the TOML field names the {source, field} table, the
    # kwarg the constructor parameter that receives its ValueRef.
    (field,) = _parse(tmp_path, "# @value-wiring temp_in comp required\n")
    assert field == ValueWiringField("temp_in", "comp", True)


@pytest.mark.parametrize(
    "source",
    [
        "#@value-wiring a b required\n",
        "## @value-wiring a b required\n",
        "#   @value-wiring   a   b   required\n",
        "#\t@value-wiring\ta\tb\trequired\n",
        "X = 1  # @value-wiring a b required\n",
        "_SCHEMA = (\n    # @value-wiring a b required\n)\n",
    ],
)
def test_parse_value_wiring_accepts_every_legal_spacing_and_placement(tmp_path: Path, source: str) -> None:
    (field,) = _parse(tmp_path, source)
    assert field.toml_field == "a"


def test_parse_value_wiring_no_tags_is_not_an_error(tmp_path: Path) -> None:
    assert _parse(tmp_path, "X = 1\n") == ()


def test_parse_value_wiring_several_tags_keep_source_order(tmp_path: Path) -> None:
    fields = _parse(
        tmp_path,
        "# @value-wiring temperature_source temperature required\n"
        "# @value-wiring humidity_source humidity optional\n",
    )
    assert [f.toml_field for f in fields] == ["temperature_source", "humidity_source"]


def test_parse_value_wiring_duplicate_toml_field_rejected(tmp_path: Path) -> None:
    _parse_expecting(
        tmp_path,
        "# @value-wiring a b required\n# @value-wiring a x optional\n",
        "two @value-wiring tags for 'a'",
    )


@pytest.mark.parametrize(
    "source,match",
    [
        ("# @value-wirng a b required\n", "misspelled @value-wiring tag"),
        ("# @value-wiiring a b required\n", "misspelled @value-wiring tag"),
        ("# @VALUE-WIRING a b required\n", "malformed @value-wiring tag"),
        # Sigil dropped: caught because a real name shape (snake_case) is present, which is what
        # the sigil-less path requires - see tag_comments._looks_like_wiring_payload.
        ("# value-wiring temperature_source temperature required\n", "leading '@' missing"),
    ],
)
def test_parse_value_wiring_rejects_each_wording_mistake(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


@pytest.mark.parametrize(
    "source",
    [
        "# @value-wiring b required\n",  # toml_field or kwarg dropped
        "# @value-wiring a b\n",  # requiredness dropped
        "# @value-wiring a b maybe\n",  # requiredness not one of the two words
        "# @value-wiring a b required extra\n",  # a fourth element
        "# @value-wiring a b c required\n",  # the retired source/field kwarg pair
        "# @value-wiring a-b c required\n",  # non-identifier field name
    ],
)
def test_parse_value_wiring_rejects_each_element_wrong_or_dropped(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "malformed @value-wiring tag")


@pytest.mark.parametrize(
    "source",
    [
        "class Foo:\n    # @value-wiring a b required\n    X = 1\n",
        "def f():\n    # @value-wiring a b required\n    pass\n",
    ],
)
def test_parse_value_wiring_rejects_locations_inside_a_body(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "module level")


@pytest.mark.parametrize(
    "source",
    [
        "# value wiring is described in the matrix doc, section 2.9\n",
        'X = "# @value-wiring a b required"\n',
        '"""Doc.\n# @value-wiring a b required\n"""\nX = 1\n',
    ],
)
def test_parse_value_wiring_leaves_non_tags_alone(tmp_path: Path, source: str) -> None:
    assert _parse(tmp_path, source) == ()


def test_parse_value_wiring_real_sgp40_driver(src_dir: Path) -> None:
    assert parse_value_wiring(src_dir / "asy_sgp40_driver.py", "dev", "sgp40") == (
        ValueWiringField("temperature_source", "temperature", True),
        ValueWiringField("humidity_source", "humidity", True),
    )


def test_sgp40_is_the_only_src_module_declaring_value_wiring(src_dir: Path) -> None:
    tagged = {p.name for p in sorted(src_dir.glob("*.py")) if parse_value_wiring(p, "dev", "x")}
    assert tagged == {"asy_sgp40_driver.py"}
