"""Flash-tier: every float config field's stored form is idempotent on the board's single-precision
floats, and a repeat write after a reload from flash answers "Unchanged" (SPECIFICATION.md C.5). The
float fields are rendered into the device script from the src/ schemas, never copied by hand."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from harness import Board

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # the repo root, for buildgen

from buildgen.schema_ast import extract_field_schemas

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_2_reboot_settings_persistence",)

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
_SCRIPT = DEVICE_SCRIPTS / "config_float_round_trip.py"
_PLACEHOLDER = 'FLOAT_FIELDS: "tuple[tuple[str, float, float], ...]" = ()'
# asy_scd30_driver.py's float field lives in the chip's own NVM, not in a config file.
_CHIP_STORES = ("asy_scd30_driver.py",)
_SIGNAL_SCHEMA_RE = re.compile(r'"\(\("(\w+)", "float", ([-\d.]+), ([-\d.]+), ([-\d.]+), None\),\)"')
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def float_fields(repo_root: Path) -> list[tuple[str, float, float]]:
    # Every file-stored float field with both bounds: the src/ schemas, plus the notification signals'
    # thresholds the generator emits (buildgen/codegen.py's _KNOWN_SIGNALS).
    found: dict[str, tuple[float, float]] = {}
    for path in sorted((repo_root / "src").glob("*.py")):
        if path.name in _CHIP_STORES:
            continue
        for name, (kind, _default, lo, hi, _special) in extract_field_schemas(path).items():
            if kind == "float" and isinstance(lo, float) and isinstance(hi, float):
                found[name] = (lo, hi)
    for name, _default, lo, hi in _SIGNAL_SCHEMA_RE.findall((repo_root / "buildgen" / "codegen.py").read_text(encoding="utf-8")):
        found[name] = (float(lo), float(hi))
    return [(name, lo, hi) for name, (lo, hi) in sorted(found.items())]


def rendered_script(repo_root: Path) -> str:
    source = _SCRIPT.read_text(encoding="utf-8")
    assert source.count(_PLACEHOLDER) == 1, f"{_SCRIPT.name} no longer carries its FLOAT_FIELDS placeholder line"
    return source.replace(_PLACEHOLDER, f"FLOAT_FIELDS = {tuple(float_fields(repo_root))!r}")


@pytest.mark.persistence_write
def test_config_floats_round_trip_unchanged(board: Board, tmp_path: Path) -> None:
    script = tmp_path / _SCRIPT.name
    script.write_text(rendered_script(REPO_ROOT), encoding="utf-8")
    output = board.run_isolated(script)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{match.group(2).strip()}\nfull output:\n{output}"
