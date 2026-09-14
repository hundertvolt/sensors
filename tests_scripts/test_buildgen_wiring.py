"""Tests for buildgen.wiring: the `# @wiring <toml_field> <ProducerClass> <target>
<required|optional> <kwarg|attr|setter>` comment tag (SPECIFICATION.md Part C.14.2). Covers the
real tags in src/ plus the whole accept/reject matrix BUILD_CHAIN_PLAN.md's quality bar requires."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.wiring import WiringField, parse_wiring

# Dimensions this file walks (BUILD_CHAIN_PLAN.md's standing matrix rule - accept side at full
# dimensionality, reject side one case per dimension without recombination):
#   D1 wording  - the tag name itself: exact, typo'd, mis-cased, sigil dropped
#   D2 format   - each of the five grammar elements individually wrong, and individually dropped
#   D3 location - module level (incl. bracketed continuation lines) vs inside a class/function body
#   D4 multiplicity - none / one / several tags per file, and a duplicate field
#   D5 spacing  - every legal whitespace and "#"-prefix variant
#   D6 verdict  - the parsed WiringField actually carries what the tag said

_REQUIREDNESS = [("required", True), ("optional", False)]
_MODES = ["kwarg", "attr", "setter"]


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _parse(tmp_path: Path, source: str) -> "tuple[WiringField, ...]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return parse_wiring(path, "dev", "x")


def _parse_expecting(tmp_path: Path, source: str, match: str) -> None:
    with pytest.raises(BuildError, match=match):
        _parse(tmp_path, source)


# --- D6/D2 accept side: the full requiredness x mode cross product ------------------------------


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("word,required", _REQUIREDNESS)
def test_parse_wiring_requiredness_mode_cross_product(tmp_path: Path, word: str, *, required: bool, mode: str) -> None:
    (field,) = _parse(tmp_path, f"# @wiring fram_target AsyFramManager fram {word} {mode}\n")
    assert field == WiringField("fram_target", "AsyFramManager", "fram", required, mode)


@pytest.mark.parametrize(
    "toml_field,producer,target",
    [
        ("fram_target", "AsyFramManager", "fram"),
        ("fram_target", "AsyFramManager", "fram_storage"),
        ("signal_sink", "NeopixelDriver", "request_signal"),
        ("led_target", "NeopixelDriver", "set_ext_led"),
        ("x", "A", "b"),  # single-character names are still names
        ("_leading_underscore", "_Private", "_target"),
        ("with9digits", "Bmp3xxReader", "t9"),
    ],
)
def test_parse_wiring_accepts_every_name_shape(tmp_path: Path, toml_field: str, producer: str, target: str) -> None:
    (field,) = _parse(tmp_path, f"# @wiring {toml_field} {producer} {target} optional kwarg\n")
    assert (field.toml_field, field.producer_class, field.target) == (toml_field, producer, target)


# --- D5 accept side: spacing and prefix variants ------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# @wiring fram_target AsyFramManager fram optional kwarg\n",
        "#@wiring fram_target AsyFramManager fram optional kwarg\n",
        "## @wiring fram_target AsyFramManager fram optional kwarg\n",
        "#   @wiring   fram_target   AsyFramManager   fram   optional   kwarg\n",
        "# @wiring fram_target AsyFramManager fram optional kwarg   \n",
        "#\t@wiring\tfram_target\tAsyFramManager\tfram\toptional\tkwarg\n",
        "X = 1  # @wiring fram_target AsyFramManager fram optional kwarg\n",
    ],
)
def test_parse_wiring_accepts_every_legal_spacing_variant(tmp_path: Path, source: str) -> None:
    (field,) = _parse(tmp_path, source)
    assert field.toml_field == "fram_target"


# --- D3 accept side: legal locations ------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# @wiring fram_target AsyFramManager fram optional kwarg\nX = 1\n",  # above a statement
        "X = 1\n# @wiring fram_target AsyFramManager fram optional kwarg\n",  # below one
        "import os\n\n# @wiring fram_target AsyFramManager fram optional kwarg\n\n\nclass Foo:\n    pass\n",
        "_SCHEMA = (\n    # @wiring fram_target AsyFramManager fram optional kwarg\n)\n",  # bracketed continuation
        "def f():\n    pass\n# @wiring fram_target AsyFramManager fram optional kwarg\n",  # after a body
    ],
)
def test_parse_wiring_accepts_every_module_level_location(tmp_path: Path, source: str) -> None:
    (field,) = _parse(tmp_path, source)
    assert field.target == "fram"


# --- D4 multiplicity ----------------------------------------------------------------------------


def test_parse_wiring_no_tags_is_not_an_error(tmp_path: Path) -> None:
    assert _parse(tmp_path, "X = 1  # an ordinary comment\n") == ()


def test_parse_wiring_several_tags_keep_source_order(tmp_path: Path) -> None:
    fields = _parse(
        tmp_path,
        "# @wiring signal_sink NeopixelDriver request_signal required attr\n"
        "# @wiring fram_target AsyFramManager fram optional kwarg\n"
        "# @wiring led_target NeopixelDriver set_ext_led optional setter\n",
    )
    assert [f.toml_field for f in fields] == ["signal_sink", "fram_target", "led_target"]


def test_parse_wiring_duplicate_toml_field_rejected(tmp_path: Path) -> None:
    # Two tags for one field is ambiguous, not additive - the second would silently win.
    _parse_expecting(
        tmp_path,
        "# @wiring fram_target AsyFramManager fram optional kwarg\n# @wiring fram_target AsyFramManager other required attr\n",
        "two @wiring tags for 'fram_target'",
    )


# --- D1 reject side: wording, one case per dimension --------------------------------------------


@pytest.mark.parametrize(
    "source,match",
    [
        ("# @wirng fram_target AsyFramManager fram optional kwarg\n", "misspelled @wiring tag"),  # deletion
        ("# @wiiring fram_target AsyFramManager fram optional kwarg\n", "misspelled @wiring tag"),  # insertion
        ("# @wiribg fram_target AsyFramManager fram optional kwarg\n", "misspelled @wiring tag"),  # substitution
        ("# @wiirng fram_target AsyFramManager fram optional kwarg\n", "misspelled @wiring tag"),  # transposition
        ("# @WIRING fram_target AsyFramManager fram optional kwarg\n", "malformed @wiring tag"),  # mis-cased
        ("# wiring fram_target AsyFramManager fram optional kwarg\n", "leading '@' missing"),  # sigil dropped
    ],
)
def test_parse_wiring_rejects_each_wording_mistake(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


def test_parse_wiring_leaves_a_word_outside_the_typo_boundary_alone(tmp_path: Path) -> None:
    # "wired" is three edits from "wiring" - past tolerance, so ordinary prose, not an attempt.
    # ("warning"/"writing"/"winning" are all only two edits away and DO get flagged, which is the
    # intended trade: inside the boundary, the "@" sigil plus a tag-shaped payload is enough.)
    assert _parse(tmp_path, "# @wired fram_target AsyFramManager fram optional kwarg\n") == ()


# --- D2 reject side: each grammar element wrong, then each one dropped ---------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# @wiring fram_target AsyFramManager fram maybe kwarg\n",  # requiredness not required/optional
        "# @wiring fram_target AsyFramManager fram optional bogus\n",  # mode outside the three
        "# @wiring fram-target AsyFramManager fram optional kwarg\n",  # non-identifier field name
        "# @wiring fram_target AsyFramManager fram optional kwarg extra\n",  # a sixth element
    ],
)
def test_parse_wiring_rejects_each_element_being_wrong(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "malformed @wiring tag")


@pytest.mark.parametrize(
    "source",
    [
        "# @wiring AsyFramManager fram optional kwarg\n",  # toml_field dropped
        "# @wiring fram_target fram optional kwarg\n",  # producer_class dropped
        "# @wiring fram_target AsyFramManager optional kwarg\n",  # target dropped
        "# @wiring fram_target AsyFramManager fram kwarg\n",  # requiredness dropped
        "# @wiring fram_target AsyFramManager fram optional\n",  # mode dropped
    ],
)
def test_parse_wiring_rejects_each_element_being_dropped(tmp_path: Path, source: str) -> None:
    # Deleting a piece must never leave a line that silently parses as "no tag declared" - that is
    # the exact silent miss the near-miss detector exists to prevent.
    _parse_expecting(tmp_path, source, "malformed @wiring tag")


def test_parse_wiring_bare_tag_name_with_no_payload_at_all_is_prose(tmp_path: Path) -> None:
    # The one deletion that does NOT abort, deliberately and consistently with @requires: a comment
    # that is only the tag name carries nothing to tell an abandoned tag apart from prose naming
    # the mechanism ("# @wiring - see BUILD_CHAIN_PLAN.md"). Every partial tag still aborts.
    assert _parse(tmp_path, "# @wiring\n") == ()


# --- D3 reject side: location -------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "class Foo:\n    # @wiring fram_target AsyFramManager fram optional kwarg\n    X = 1\n",
        "def f():\n    # @wiring fram_target AsyFramManager fram optional kwarg\n    pass\n",
        "def f():\n    x = (\n        # @wiring fram_target AsyFramManager fram optional kwarg\n    )\n",
    ],
)
def test_parse_wiring_rejects_locations_inside_a_body(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "module level")


# --- false positives ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# wiring is handled by the generator, see BUILD_CHAIN_PLAN.md\n",  # prose, no sigil, no payload
        "# @wiring\n".replace("@wiring", "@webhook"),  # an unrelated @-word
        'X = "# @wiring fram_target AsyFramManager fram optional kwarg"\n',  # inside a string literal
        '"""Doc.\n# @wiring fram_target AsyFramManager fram optional kwarg\n"""\nX = 1\n',  # inside a docstring
    ],
)
def test_parse_wiring_leaves_non_tags_alone(tmp_path: Path, source: str) -> None:
    assert _parse(tmp_path, source) == ()


# --- the real declarations in src/ --------------------------------------------------------------


@pytest.mark.parametrize(
    "driver,expected",
    [
        ("asy_bmp3xx_driver.py", (WiringField("fram_target", "AsyFramManager", "fram", False, "kwarg"),)),
        ("asy_neopixel_driver.py", (WiringField("fram_target", "AsyFramManager", "fram", False, "kwarg"),)),
        ("asy_scd30_driver.py", (WiringField("fram_target", "AsyFramManager", "fram", False, "kwarg"),)),
        ("asy_sgp40_driver.py", (WiringField("fram_target", "AsyFramManager", "fram_storage", False, "kwarg"),)),
        ("asy_wifi_service.py", (WiringField("led_target", "NeopixelDriver", "set_ext_led", False, "setter"),)),
        ("system_service.py", (WiringField("fram_target", "AsyFramManager", "fram", False, "kwarg"),)),
        (
            "asy_notification_service.py",
            (
                WiringField("signal_sink", "NeopixelDriver", "request_signal", True, "attr"),
                WiringField("fram_target", "AsyFramManager", "fram", False, "kwarg"),
            ),
        ),
    ],
)
def test_parse_wiring_real_drivers(src_dir: Path, driver: str, expected: "tuple[WiringField, ...]") -> None:
    assert parse_wiring(src_dir / driver, "dev", "x") == expected


def test_no_other_src_module_declares_an_unnoticed_wiring_tag(src_dir: Path) -> None:
    # A new tag appearing in a module nobody expected it in should fail this test, not go unnoticed.
    tagged = {p.name for p in sorted(src_dir.glob("*.py")) if parse_wiring(p, "dev", "x")}
    assert tagged == {
        "asy_bmp3xx_driver.py",
        "asy_neopixel_driver.py",
        "asy_notification_service.py",
        "asy_scd30_driver.py",
        "asy_sgp40_driver.py",
        "asy_wifi_service.py",
        "system_service.py",
    }
