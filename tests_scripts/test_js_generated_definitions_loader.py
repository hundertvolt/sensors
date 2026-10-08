"""tests_js/_generated_definitions.js reads every device's definitions from the directory
scripts/_generate_sensortask_modules.py writes them to: the generator run against a temporary root,
the loader's glob read as text, so a moved output fails here rather than in a browser tier."""

import re
from pathlib import Path
from types import ModuleType

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HELPER = _REPO_ROOT / "tests_js" / "_generated_definitions.js"
_JSON_GLOB = re.compile(r'import\.meta\.glob\(\s*"\.\./([^"*]+)/\*\.json"')


def _helper_definitions_dirs(text: str) -> "set[str]":
    # Every `definitions` directory the helper globs `*.json` from, relative to the repo root.
    return {d for d in _JSON_GLOB.findall(text) if d.rsplit("/", 1)[-1] == "definitions"}


@pytest.fixture
def generator(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_generate_sensortask_modules.py", "_generate_sensortask_modules")


def test_the_loader_globs_the_directory_the_generator_writes(generator: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The generator writes under a temporary root (test_generate_sensortask_modules.py's set-up),
    # so the directory it really fills is found from its output, not from its source text.
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    for name in ("devices", "src", "ext"):
        (tmp_path / name).symlink_to(repo_root / name)
    assert generator.main() == 0
    written = {str(p.parent.relative_to(tmp_path)) for d in DEVICE_NAMES for p in tmp_path.rglob(f"definitions/{d}.json")}
    assert len(written) == 1, f"the generator wrote the definitions into {sorted(written)} - expected exactly one directory"
    globbed = _helper_definitions_dirs(_HELPER.read_text(encoding="utf-8"))
    assert globbed == written, f"tests_js/_generated_definitions.js globs {sorted(globbed)}, but the generator writes {sorted(written)}"


def test_the_glob_reader_bites() -> None:
    loader = 'import.meta.glob("../build/generated_src/definitions/*.json", { eager: true, import: "default" })'
    assert _helper_definitions_dirs(loader) == {"build/generated_src/definitions"}
    assert _helper_definitions_dirs(loader.replace("generated_src", "generated")) == {"build/generated/definitions"}
    assert _helper_definitions_dirs(loader.replace("definitions/", "defs/")) == set()
