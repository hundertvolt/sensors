"""js/definitions.js keeps its own copies of two generator bounds - the schema major it accepts and the
decimals ceiling - since the browser cannot import buildgen/. Read as text and pinned to their
sources here (the test_request_timeout_ceiling.py pattern: the source read, never imported)."""

import re
from pathlib import Path

from buildgen.definitions import SCHEMA_VERSION
from buildgen.web_tag import _MAX_DECIMALS

_DEFINITIONS_JS = Path(__file__).resolve().parent.parent / "js" / "definitions.js"


def _js_int_const(text: str, name: str) -> int:
    """A top-level `const NAME = <int>;` or `export const NAME = <int>;` in the module's text."""
    found = re.findall(rf"^(?:export )?const {name} = (\d+);$", text, re.MULTILINE)
    assert len(found) == 1, f"js/definitions.js declares {name} {len(found)} times as an integer constant - expected exactly once"
    return int(found[0])


def test_the_supported_schema_major_is_the_generators() -> None:
    assert _js_int_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "SUPPORTED_SCHEMA_MAJOR") == int(SCHEMA_VERSION.split(".")[0])


def test_the_decimals_ceiling_is_the_tag_parsers() -> None:
    assert _js_int_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "MAX_DECIMALS") == _MAX_DECIMALS


def test_the_constant_reader_takes_both_declaration_forms_and_nothing_else() -> None:
    assert _js_int_const("export const A = 1;\n", "A") == 1
    assert _js_int_const("const A = 100;\n", "A") == 100
    assert not re.findall(r"^(?:export )?const A = (\d+);$", "let A = 1;\n    const A = 2;\n", re.MULTILINE)
