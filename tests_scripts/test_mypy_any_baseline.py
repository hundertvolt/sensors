"""Pins the explicit-Any rule in all three mypy passes: each sets disallow_any_explicit in its main section and no
per-module override turns it off again (owner, 2026-09-28; SPECIFICATION.md B.15)."""

import configparser
from pathlib import Path

import pytest
import tomllib

_FLAG = "disallow_any_explicit"
_INI_PASSES = ("digital_twin/typecheck.ini", "host_typecheck.ini")


def _ini_pass(root: Path, name: str) -> "tuple[object, list[str]]":
    # (the flag's value in the main section, the modules a section exempts) of one .ini pass.
    parser = configparser.ConfigParser()
    parser.read(root / name)
    main = parser["mypy"]
    flag = main.getboolean(_FLAG) if _FLAG in main else None
    return flag, [s.removeprefix("mypy-") for s in parser.sections() if s.startswith("mypy-") and parser[s].getboolean(_FLAG) is False]


def _pyproject_pass(root: Path) -> "tuple[object, list[str]]":
    # The same two facts of pyproject.toml's main pass, its overrides holding any exemption.
    with (root / "pyproject.toml").open("rb") as f:
        mypy = tomllib.load(f)["tool"]["mypy"]
    exempt: list[str] = []
    for override in mypy.get("overrides", []):
        if override.get(_FLAG) is False:
            module = override["module"]
            exempt += [module] if isinstance(module, str) else list(module)
    return mypy.get(_FLAG), exempt


def _passes(root: Path) -> "dict[str, tuple[object, list[str]]]":
    return {"pyproject.toml": _pyproject_pass(root)} | {name: _ini_pass(root, name) for name in _INI_PASSES}


@pytest.mark.parametrize("config", ["pyproject.toml", *_INI_PASSES])
def test_every_pass_disallows_explicit_any(repo_root: Path, config: str) -> None:
    flag, exempt = _passes(repo_root)[config]
    assert flag is True, f"{config} must set {_FLAG} = true in its main mypy section"
    assert not exempt, f"{config} exempts {exempt} from {_FLAG}: type the module's Any instead"


def test_an_exemption_is_reported(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(f'[tool.mypy]\n{_FLAG} = true\n\n[[tool.mypy.overrides]]\nmodule = ["machine"]\n{_FLAG} = false\n', encoding="utf-8")
    (tmp_path / "host_typecheck.ini").write_text(f"[mypy]\n{_FLAG} = true\n\n[mypy-scripts.x]\n{_FLAG} = false\n", encoding="utf-8")
    assert _pyproject_pass(tmp_path) == (True, ["machine"])
    assert _ini_pass(tmp_path, "host_typecheck.ini") == (True, ["scripts.x"])
