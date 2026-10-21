"""Pins the explicit-Any rule in all three mypy passes: each sets disallow_any_explicit, exempts only
modules its residual list names, so a new exemption fails, and every module it exempts exists - a
renamed or deleted module cannot linger in the list it should have left (SPECIFICATION.md B.15)."""

import configparser
import re
from pathlib import Path

import pytest
import tomllib

_FLAG = "disallow_any_explicit"
_INI_PASSES = ("digital_twin/typecheck.ini", "host_typecheck.ini")
# The modules each pass may still exempt, every one holding explicit Any today: a module leaves its
# pass's baseline once cleared, with no edit here, and one not named here cannot join it.
_RESIDUAL = {
    "pyproject.toml": frozenset(
        {
            "_boot_contiguity_probe",
            "_bus_hazard_catalog",
            "_sensortask_scenarios",
            "_uart_link_contract",
            "asy_system_service",
            "machine",
            "serving_at_default_gc",
            "test_asy_uart_comm",
            "test_asy_uart_driver",
            "test_bus_hazard_generated",
            "test_bus_hazard_multi_device",
        },
    ),
    "digital_twin/typecheck.ini": frozenset({"machine", "test_digital_twin_bus_hazard_concurrency"}),
    "host_typecheck.ini": frozenset({"conftest", "scripts._hardware_verdict", "test_cross_browser_smoke_probe"}),
}


def _ini_pass(root: Path, name: str) -> "tuple[object, list[str], list[str]]":
    # (the flag's value, the search bases, the exempted modules) of one .ini pass; its own directories count as
    # bases too.
    parser = configparser.ConfigParser()
    parser.read(root / name)
    main = parser["mypy"]
    flag = main.getboolean(_FLAG) if _FLAG in main else None
    bases = [b.strip() for b in re.split(r"[,:]", main.get("mypy_path", "")) if b.strip()]
    bases += [b.strip() for b in main.get("files", "").split(",") if b.strip()]
    bases += [str(Path(name).parent)]
    exempt = [s.removeprefix("mypy-") for s in parser.sections() if s.startswith("mypy-") and parser[s].getboolean(_FLAG) is False]
    return flag, bases, exempt


def _passes(root: Path) -> "dict[str, tuple[object, list[str], list[str]]]":
    return {"pyproject.toml": _pyproject_pass(root)} | {name: _ini_pass(root, name) for name in _INI_PASSES}


def _pyproject_pass(root: Path) -> "tuple[object, list[str], list[str]]":
    # The same three facts of pyproject.toml's main pass, its overrides holding the exemptions.
    with (root / "pyproject.toml").open("rb") as f:
        mypy = tomllib.load(f)["tool"]["mypy"]
    exempt: list[str] = []
    for override in mypy.get("overrides", []):
        if override.get(_FLAG) is False:
            module = override["module"]
            exempt += [module] if isinstance(module, str) else list(module)
    return mypy.get(_FLAG), [*mypy.get("mypy_path", []), *mypy.get("files", [])], exempt


def _resolves(root: Path, bases: "list[str]", module: str) -> bool:
    relative = Path(*module.split("."))
    return any((root / base / relative).with_suffix(".py").is_file() or (root / base / relative / "__init__.py").is_file() for base in bases)


def _unlisted(config: str, exempt: "list[str]") -> "list[str]":
    # The modules config exempts that its residual list does not name.
    return sorted(set(exempt) - _RESIDUAL[config])


@pytest.mark.parametrize("config", ["pyproject.toml", *_INI_PASSES])
def test_every_pass_disallows_explicit_any(repo_root: Path, config: str) -> None:
    flag, _, _ = _passes(repo_root)[config]
    assert flag is True, f"{config} must set {_FLAG} = true in its main mypy section"


@pytest.mark.parametrize("config", ["pyproject.toml", *_INI_PASSES])
def test_every_baseline_module_still_exists(repo_root: Path, config: str) -> None:
    _, bases, exempt = _passes(repo_root)[config]
    missing = [m for m in exempt if not _resolves(repo_root, bases, m)]
    assert not missing, f"{config}'s explicit-Any baseline names modules no longer on its search path: {missing} - drop them from the list"


@pytest.mark.parametrize("config", ["pyproject.toml", *_INI_PASSES])
def test_no_pass_exempts_an_unlisted_module(repo_root: Path, config: str) -> None:
    _, _, exempt = _passes(repo_root)[config]
    unlisted = _unlisted(config, exempt)
    assert not unlisted, f"{config} exempts {unlisted} from {_FLAG}, which its residual list does not name - clear the module's explicit Any instead"


def test_an_unlisted_exemption_is_reported(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(f'[tool.mypy]\n{_FLAG} = true\n\n[[tool.mypy.overrides]]\nmodule = ["machine", "brand_new"]\n{_FLAG} = false\n', encoding="utf-8")
    (tmp_path / "host_typecheck.ini").write_text(f"[mypy]\n{_FLAG} = true\n\n[mypy-conftest]\n{_FLAG} = false\n\n[mypy-brand_new]\n{_FLAG} = false\n", encoding="utf-8")
    assert _unlisted("pyproject.toml", _pyproject_pass(tmp_path)[2]) == ["brand_new"]
    assert _unlisted("host_typecheck.ini", _ini_pass(tmp_path, "host_typecheck.ini")[2]) == ["brand_new"]


def test_a_vanished_module_is_reported(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "kept.py").write_text("", encoding="utf-8")
    assert _resolves(tmp_path, ["src"], "kept")
    assert not _resolves(tmp_path, ["src"], "renamed")
