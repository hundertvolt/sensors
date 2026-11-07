"""Scratch proof (not committed): a non-table [instance.wiring] fails load_device() with its rule."""
import sys
from pathlib import Path

import pytest

ROOT = Path(sys.argv[0]).resolve()  # unused


def test_instance_wiring_not_a_table_names_its_rule(tmp_path: Path) -> None:
    from buildgen.errors import BuildError
    from buildgen.model import load_device

    path = tmp_path / "dev.toml"
    path.write_text('[[instance]]\ndriver = "scd30"\nwiring = "fram"\n')
    with pytest.raises(BuildError) as excinfo:
        load_device(path)
    assert excinfo.value.rule == "instance.wiring-not-table"
    assert excinfo.value.field == "wiring"
    assert excinfo.value.instance == "scd30"
    assert str(excinfo.value) == "[dev/scd30.wiring] scd30's wiring must be a table, got 'fram' - fix: write it as a [instance.wiring] table under this [[instance]]"
