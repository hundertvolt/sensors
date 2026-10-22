"""Scratch proof (not committed): every load_device()/lwip_macros() refusal carries its rule and fix."""
from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.model import load_device, lwip_macros

CASES = [
    ("x = [\n", "toml.syntax"),
    ('instance = 5\n', "instance.not-an-array"),
    ('[instance]\ndriver = "scd30"\n', "instance.single-table"),
    ('[[instance]]\nbus = "i2c0"\n', "instance.driver-missing"),
    ('[[instance]]\ndriver = 3\n', "instance.driver-not-a-string"),
    ('[[instance]]\ndriver = "scd30"\nname_ext = 1\n', "instance.name-ext-not-a-string"),
    ('[[instance]]\ndriver = "scd30"\nwiring = "fram"\n', "instance.wiring-not-table"),
    ('[[instance]]\ndriver = "scd30"\n[[instance]]\ndriver = "scd30"\n', "instance.duplicate"),
]


@pytest.mark.parametrize(("text", "rule"), CASES)
def test_load_device_rule(tmp_path: Path, text: str, rule: str) -> None:
    path = tmp_path / "fixture.toml"
    path.write_text(text)
    with pytest.raises(BuildError) as raised:
        load_device(path)
    assert raised.value.rule == rule
    assert raised.value.fix and " - fix: " in str(raised.value)


def test_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(BuildError) as raised:
        load_device(tmp_path / "absent.toml")
    assert raised.value.rule == "toml.unreadable"


@pytest.mark.parametrize("text", ["[other]\nx = 1\n", "lwip = 5\n"])
def test_lwip_table(tmp_path: Path, text: str) -> None:
    path = tmp_path / "versions.toml"
    path.write_text(text)
    with pytest.raises(BuildError) as raised:
        lwip_macros(path)
    assert raised.value.rule == "toolchain.lwip-table"
