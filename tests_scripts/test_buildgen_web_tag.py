"""Tests for buildgen.web_tag: the `# @web <Field> key=value ...` / `# @web-group key=value ...`
comment-tag parsers (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar" - the same bar
test_buildgen_requires_tag.py already covers for `@requires`, mirrored here for the newer family).

Matrix dimensions:
  D1 field name     plain, CamelCase, digit-bearing, underscored (single-char "r"/"g"/"b" too)
  D2 key=value      quoted string, bareword, boolean (true/false), special:<value>="<meaning>"
                     (repeated), unknown key rejected, missing required key(s) rejected
  D3 format         spacing around "#"/the tag word/"="; "##" section style; quoted vs bareword
  D4 location       top of file, after a docstring, among imports, trailing inline, last line with
                     no trailing newline, inside a class/function body (rejected)
  D5 multiplicity   none, one, several fields, duplicate (section, submitGroup, field) rejected
  D6 web-group      required keys, submit=/submitLabel=, duplicate (section, submitGroup) rejected
  D7 near-miss      "@" dropped, field name dropped (web only), tag name typo'd, wrong-family
                     cross-contamination avoided
  D8 real drivers   every src/ file this session tagged parses to the exact expected tags
"""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.web_tag import WebFieldTag, WebGroupTag, parse_web_group_tags, parse_web_tags


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _parse(tmp_path: Path, source: str) -> "tuple[WebFieldTag, ...]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return parse_web_tags(path, "dev", "x")


def _parse_group(tmp_path: Path, source: str) -> "tuple[WebGroupTag, ...]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return parse_web_group_tags(path, "dev", "x")


def _parse_expecting(tmp_path: Path, source: str, match: str) -> None:
    with pytest.raises(BuildError, match=match):
        _parse(tmp_path, source)


def _parse_group_expecting(tmp_path: Path, source: str, match: str) -> None:
    with pytest.raises(BuildError, match=match):
        _parse_group(tmp_path, source)


# ---------------------------------------------------------------------------
# D1 x D2: field name shapes, key=value shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["AmbPres", "r", "pin0", "_reserved", "SGPResetVOC"])
def test_parse_web_tags_field_name_shapes(tmp_path: Path, field: str) -> None:
    (tag,) = _parse(tmp_path, f'# @web {field} section=sensors submitGroup=self label="Label"\n')
    assert tag.field_name == field


def test_parse_web_tags_quoted_and_bareword_values(tmp_path: Path) -> None:
    (tag,) = _parse(tmp_path, '# @web X section=sensors submitGroup=self label="A Label" unit=ppm description="Some text."\n')
    assert (tag.section, tag.submit_group, tag.label, tag.unit, tag.description) == ("sensors", "self", "A Label", "ppm", "Some text.")


def test_parse_web_tags_bareword_kind_and_flags(tmp_path: Path) -> None:
    (tag,) = _parse(tmp_path, '# @web X section=sensors submitGroup=self label="L" kind=toggle mask=true dispatch=true onLabel="On" offLabel="Off"\n')
    assert (tag.kind, tag.mask, tag.dispatch, tag.on_label, tag.off_label) == ("toggle", True, True, "On", "Off")


@pytest.mark.parametrize("raw,expected", [("true", True), ("42", 42), ("-1.5", -1.5), ("hello", "hello")])
def test_parse_web_tags_default_value_coercion(tmp_path: Path, raw: str, expected: object) -> None:
    (tag,) = _parse(tmp_path, f'# @web X section=sensors submitGroup=self label="L" defaultValue={raw}\n')
    assert tag.default_value == expected
    assert type(tag.default_value) is type(expected)


def test_parse_web_tags_repeated_special_entries(tmp_path: Path) -> None:
    (tag,) = _parse(tmp_path, '# @web X section=sensors submitGroup=self label="L" special:1="One" special:2="Two"\n')
    assert dict(tag.special) == {"1": "One", "2": "Two"}


def test_parse_web_tags_unknown_key_rejected(tmp_path: Path) -> None:
    _parse_expecting(tmp_path, '# @web X section=sensors submitGroup=self label="L" bogus=1\n', "unknown key")


@pytest.mark.parametrize(
    "source",
    [
        '# @web X submitGroup=self label="L"\n',  # section missing
        '# @web X section=sensors label="L"\n',  # submitGroup missing
        "# @web X section=sensors submitGroup=self\n",  # label missing
    ],
)
def test_parse_web_tags_missing_required_key_rejected(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "missing required key")


def test_parse_web_tags_invalid_kind_rejected(tmp_path: Path) -> None:
    _parse_expecting(tmp_path, '# @web X section=sensors submitGroup=self label="L" kind=bogus\n', "unknown kind")


def test_parse_web_tags_invalid_bool_rejected(tmp_path: Path) -> None:
    _parse_expecting(tmp_path, '# @web X section=sensors submitGroup=self label="L" mask=yes\n', "must be true or false")


# ---------------------------------------------------------------------------
# D3 format/spacing variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        '# @web X section=sensors submitGroup=self label="L"\n',  # canonical
        '#@web X section=sensors submitGroup=self label="L"\n',  # no space after hash
        '#   @web   X   section=sensors   submitGroup=self   label="L"\n',  # wide gaps
        '## @web X section=sensors submitGroup=self label="L"\n',  # section-style double hash
        '# @web X section=sensors submitGroup=self label="L"   \n',  # trailing whitespace
        '#\t@web X section=sensors submitGroup=self label="L"\n',  # tab instead of space
    ],
)
def test_parse_web_tags_format_variants(tmp_path: Path, source: str) -> None:
    (tag,) = _parse(tmp_path, source)
    assert (tag.field_name, tag.section, tag.submit_group, tag.label) == ("X", "sensors", "self", "L")


# ---------------------------------------------------------------------------
# D4 placement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        '# @web X section=sensors submitGroup=self label="L"\nx = 1\n',
        '"""Driver docstring."""\n\n# @web X section=sensors submitGroup=self label="L"\nx = 1\n',
        'import time\n\n# @web X section=sensors submitGroup=self label="L"\nimport struct\n',
        '_VAL_X = ()  # @web X section=sensors submitGroup=self label="L"\n',
        '_VAL_X = ()\n# @web X section=sensors submitGroup=self label="L"\n_VAL_Y = ()\n',
        '# @web X section=sensors submitGroup=self label="L"',  # last line, no trailing newline
    ],
)
def test_parse_web_tags_valid_locations(tmp_path: Path, source: str) -> None:
    (tag,) = _parse(tmp_path, source)
    assert tag.field_name == "X"


@pytest.mark.parametrize(
    "source",
    [
        'class Foo:\n    def __init__(self):\n        # @web X section=sensors submitGroup=self label="L"\n        pass\n',
        'class Foo:\n    # @web X section=sensors submitGroup=self label="L"\n    X = 1\n',
    ],
)
def test_parse_web_tags_rejects_locations_inside_a_body(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "module level")


# ---------------------------------------------------------------------------
# D5 multiplicity
# ---------------------------------------------------------------------------


def test_parse_web_tags_none_declared(tmp_path: Path) -> None:
    assert _parse(tmp_path, "class Plain_Reader:\n    pass\n") == ()


def test_parse_web_tags_several_distinct_fields_in_source_order(tmp_path: Path) -> None:
    tags = _parse(
        tmp_path,
        '# @web A section=sensors submitGroup=self label="A"\n# @web B section=sensors submitGroup=self label="B"\n',
    )
    assert [t.field_name for t in tags] == ["A", "B"]


def test_parse_web_tags_duplicate_field_in_same_section_group_rejected(tmp_path: Path) -> None:
    _parse_expecting(
        tmp_path,
        '# @web A section=sensors submitGroup=self label="A"\n# @web A section=sensors submitGroup=self label="A again"\n',
        "duplicate",
    )


def test_parse_web_tags_same_field_name_different_group_is_not_a_duplicate(tmp_path: Path) -> None:
    tags = _parse(
        tmp_path,
        '# @web A section=measurements submitGroup=self label="A"\n# @web A section=sensors submitGroup=self label="A"\n',
    )
    assert len(tags) == 2


# ---------------------------------------------------------------------------
# D6 @web-group
# ---------------------------------------------------------------------------


def test_parse_web_group_tags_basic(tmp_path: Path) -> None:
    (tag,) = _parse_group(tmp_path, '# @web-group section=sensors submitGroup=self label="Card" submit=true submitLabel="Save"\n')
    assert (tag.section, tag.submit_group, tag.label, tag.submit, tag.submit_label) == ("sensors", "self", "Card", True, "Save")


def test_parse_web_group_tags_submit_defaults_false(tmp_path: Path) -> None:
    (tag,) = _parse_group(tmp_path, '# @web-group section=measurements submitGroup=self label="Card"\n')
    assert tag.submit is False
    assert tag.submit_label is None


@pytest.mark.parametrize(
    "source",
    [
        '# @web-group submitGroup=self label="L"\n',
        '# @web-group section=sensors label="L"\n',
        "# @web-group section=sensors submitGroup=self\n",
    ],
)
def test_parse_web_group_tags_missing_required_key_rejected(tmp_path: Path, source: str) -> None:
    _parse_group_expecting(tmp_path, source, "missing required key")


def test_parse_web_group_tags_duplicate_section_group_rejected(tmp_path: Path) -> None:
    _parse_group_expecting(
        tmp_path,
        '# @web-group section=sensors submitGroup=self label="A"\n# @web-group section=sensors submitGroup=self label="B"\n',
        "duplicate",
    )


def test_parse_web_group_tags_different_submit_group_same_section_is_not_a_duplicate(tmp_path: Path) -> None:
    tags = _parse_group(
        tmp_path,
        '# @web-group section=networking submitGroup=identity label="Identity"\n# @web-group section=networking submitGroup=wifiLed label="LED"\n',
    )
    assert len(tags) == 2


# ---------------------------------------------------------------------------
# D7 near-miss / "present or close to present" enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source,match",
    [
        ('# web X section=sensors submitGroup=self label="L"\n', "leading '@' missing"),
        ('# @wb X section=sensors submitGroup=self label="L"\n', "misspelled @web tag"),
        ('# @web section=sensors submitGroup=self label="L"\n', "malformed @web tag"),  # field name dropped
        ('# @web X section=sensors submitGroup=self labell="L"\n', "unknown key"),  # typo'd key name
    ],
)
def test_parse_web_tags_rejects_near_misses(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


@pytest.mark.parametrize(
    "source",
    [
        "# web mentions the website but isn't a tag\n",
        '"""# @web X section=sensors submitGroup=self label="L""""\nx = 1\n',
        'X = "# @web X section=sensors submitGroup=self label=\\"L\\""\n',
    ],
)
def test_parse_web_tags_leaves_non_tags_alone(tmp_path: Path, source: str) -> None:
    assert _parse(tmp_path, source) == ()


def test_parse_web_tags_a_real_web_group_tag_is_not_a_near_miss_of_web(tmp_path: Path) -> None:
    # Cross-family safety: a well-formed @web-group line must never be flagged while scanning for
    # @web tags (and vice versa, covered by the symmetric group-side test below).
    assert _parse(tmp_path, '# @web-group section=sensors submitGroup=self label="Card"\n') == ()


def test_parse_web_group_tags_a_real_web_tag_is_not_a_near_miss_of_web_group(tmp_path: Path) -> None:
    assert _parse_group(tmp_path, '# @web X section=sensors submitGroup=self label="L"\n') == ()


@pytest.mark.parametrize(
    "source,match",
    [
        ('# web-group section=sensors submitGroup=self label="L"\n', "leading '@' missing"),
        ('# @wbe-group section=sensors submitGroup=self label="L"\n', "misspelled @web-group tag"),
    ],
)
def test_parse_web_group_tags_rejects_near_misses(tmp_path: Path, source: str, match: str) -> None:
    _parse_group_expecting(tmp_path, source, match)


# ---------------------------------------------------------------------------
# D8 real drivers - a spot check that every tagged src/ file parses as expected
# ---------------------------------------------------------------------------


def test_parse_web_tags_real_scd30_measurement_fields(src_dir: Path) -> None:
    tags = parse_web_tags(src_dir / "asy_scd30_driver.py", "dev", "scd30")
    measurement_fields = {t.field_name for t in tags if t.section == "measurements"}
    assert measurement_fields == {"CO2", "Temp", "Hum", "WetBulb", "DewPoint", "TS"}
    config_fields = {t.field_name for t in tags if t.section == "sensors"}
    assert config_fields == {"TempOffs", "MeasInt", "AmbPres", "Altitude", "ForceCalRef", "SelfCal", "ContMeas"}


def test_parse_web_tags_real_scd30_ambpres_special(src_dir: Path) -> None:
    tags = parse_web_tags(src_dir / "asy_scd30_driver.py", "dev", "scd30")
    amb_pres = next(t for t in tags if t.field_name == "AmbPres")
    assert dict(amb_pres.special) == {"0": "Compensation off / use Altitude"}


def test_parse_web_tags_real_scd30_contmeas_is_freestanding(src_dir: Path) -> None:
    tags = parse_web_tags(src_dir / "asy_scd30_driver.py", "dev", "scd30")
    cont_meas = next(t for t in tags if t.field_name == "ContMeas")
    assert cont_meas.kind == "toggle"
    assert cont_meas.default_value is True


def test_parse_web_tags_real_bmp3xx_enum_specials(src_dir: Path) -> None:
    tags = parse_web_tags(src_dir / "asy_bmp3xx_driver.py", "dev", "bmp3xx")
    filt_coeff = next(t for t in tags if t.field_name == "FiltCoeff")
    assert dict(filt_coeff.special) == {"0": "Off", "1": "1", "3": "3", "7": "7", "15": "15", "31": "31", "63": "63", "127": "127"}


@pytest.mark.parametrize(
    "driver,expected_key",
    [
        ("asy_scd30_driver.py", ("measurements", "self")),
        ("asy_sgp40_driver.py", ("measurements", "self")),
        ("asy_bmp3xx_driver.py", ("measurements", "self")),
        ("asy_wifi_service.py", ("networking", "identity")),
        ("asy_ntp_client.py", ("networking", "ntp")),
        ("system_service.py", ("system", "settings")),
        ("asy_notification_service.py", ("notification", "autoConfig")),
    ],
)
def test_parse_web_group_tags_real_drivers_declare_expected_group(src_dir: Path, driver: str, expected_key: "tuple[str, str]") -> None:
    tags = parse_web_group_tags(src_dir / driver, "dev", "x")
    assert any((t.section, t.submit_group) == expected_key for t in tags)


def test_no_other_src_driver_declares_an_unnoticed_web_tag(src_dir: Path) -> None:
    tagged = {p.name for p in sorted(src_dir.glob("*.py")) if parse_web_tags(p, "dev", "x")}
    assert tagged == {
        "asy_scd30_driver.py", "asy_sgp40_driver.py", "asy_bmp3xx_driver.py",
        "asy_wifi_service.py", "asy_ntp_client.py", "system_service.py", "asy_notification_service.py",
    }
