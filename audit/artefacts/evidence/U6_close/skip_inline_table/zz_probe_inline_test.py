from pathlib import Path
import pytest
from _toml_fixtures import base_doc, dump_toml
from buildgen.errors import BuildError
from buildgen.validate import build_model

@pytest.mark.parametrize("table", ['{ target = "neopixel" }', '{}'])
def test_inline_table_led_target(tmp_path: Path, repo_root: Path, table: str) -> None:
    doc = base_doc()
    doc["device"]["wiring"]["led_target"] = "__PLACEHOLDER__"
    text = dump_toml(doc).replace('led_target = "__PLACEHOLDER__"', f"led_target = {table}")
    assert table in text
    p = tmp_path / "dev.toml"; p.write_text(text)
    with pytest.raises(BuildError, match="must be a string instance reference"):
        build_model(p, repo_root / "src")
