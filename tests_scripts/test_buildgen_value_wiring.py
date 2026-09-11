"""Tests for buildgen.value_wiring: the `# @value-wiring <toml_field> <source_kwarg> <field_kwarg>
<required|optional>` comment tag - per-value measurement wiring (matrix doc §2.9). Walks the same
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
    (field,) = _parse(tmp_path, f"# @value-wiring temperature_source temperature_source temperature_field {word}\n")
    assert field == ValueWiringField("temperature_source", "temperature_source", "temperature_field", required)


def test_parse_value_wiring_source_kwarg_may_differ_from_the_toml_field(tmp_path: Path) -> None:
    # The three names are independent by design - nothing requires the TOML field and the
    # constructor kwarg to be spelled the same, they just happen to be in src/ today.
    (field,) = _parse(tmp_path, "# @value-wiring temp_in comp_source comp_field required\n")
    assert field == ValueWiringField("temp_in", "comp_source", "comp_field", True)


@pytest.mark.parametrize(
    "source",
    [
        "#@value-wiring a b c required\n",
        "## @value-wiring a b c required\n",
        "#   @value-wiring   a   b   c   required\n",
        "#\t@value-wiring\ta\tb\tc\trequired\n",
        "X = 1  # @value-wiring a b c required\n",
        "_SCHEMA = (\n    # @value-wiring a b c required\n)\n",
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
        "# @value-wiring temperature_source temperature_source temperature_field required\n"
        "# @value-wiring humidity_source humidity_source humidity_field optional\n",
    )
    assert [f.toml_field for f in fields] == ["temperature_source", "humidity_source"]


def test_parse_value_wiring_duplicate_toml_field_rejected(tmp_path: Path) -> None:
    _parse_expecting(
        tmp_path,
        "# @value-wiring a b c required\n# @value-wiring a x y optional\n",
        "two @value-wiring tags for 'a'",
    )


@pytest.mark.parametrize(
    "source,match",
    [
        ("# @value-wirng a b c required\n", "misspelled @value-wiring tag"),
        ("# @value-wiiring a b c required\n", "misspelled @value-wiring tag"),
        ("# @VALUE-WIRING a b c required\n", "malformed @value-wiring tag"),
        # Sigil dropped: caught because a real name shape (snake_case) is present, which is what
        # the sigil-less path requires - see tag_comments._looks_like_wiring_payload.
        ("# value-wiring temperature_source temperature_source temperature_field required\n", "leading '@' missing"),
    ],
)
def test_parse_value_wiring_rejects_each_wording_mistake(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


@pytest.mark.parametrize(
    "source",
    [
        "# @value-wiring b c required\n",  # toml_field dropped
        "# @value-wiring a c required\n",  # source_kwarg dropped
        "# @value-wiring a b required\n",  # field_kwarg dropped
        "# @value-wiring a b c\n",  # requiredness dropped
        "# @value-wiring a b c maybe\n",  # requiredness not one of the two words
        "# @value-wiring a b c required extra\n",  # a fifth element
        "# @value-wiring a-b c d required\n",  # non-identifier field name
    ],
)
def test_parse_value_wiring_rejects_each_element_wrong_or_dropped(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "malformed @value-wiring tag")


@pytest.mark.parametrize(
    "source",
    [
        "class Foo:\n    # @value-wiring a b c required\n    X = 1\n",
        "def f():\n    # @value-wiring a b c required\n    pass\n",
    ],
)
def test_parse_value_wiring_rejects_locations_inside_a_body(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "module level")


@pytest.mark.parametrize(
    "source",
    [
        "# value wiring is described in the matrix doc, section 2.9\n",
        'X = "# @value-wiring a b c required"\n',
        '"""Doc.\n# @value-wiring a b c required\n"""\nX = 1\n',
    ],
)
def test_parse_value_wiring_leaves_non_tags_alone(tmp_path: Path, source: str) -> None:
    assert _parse(tmp_path, source) == ()


def test_parse_value_wiring_real_sgp40_driver(src_dir: Path) -> None:
    assert parse_value_wiring(src_dir / "asy_sgp40_driver.py", "dev", "sgp40") == (
        ValueWiringField("temperature_source", "temperature_source", "temperature_field", True),
        ValueWiringField("humidity_source", "humidity_source", "humidity_field", True),
    )


def test_sgp40_is_the_only_src_module_declaring_value_wiring(src_dir: Path) -> None:
    tagged = {p.name for p in sorted(src_dir.glob("*.py")) if parse_value_wiring(p, "dev", "x")}
    assert tagged == {"asy_sgp40_driver.py"}
