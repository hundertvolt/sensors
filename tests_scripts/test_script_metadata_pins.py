"""Every PEP 723 script block in the repo asks for pyproject.toml's own Python and pins each dependency exactly as its
dependency groups do, so `uv run` on a script resolves the tool the venv holds, offline from a warm cache included
(agent, 2026-10-15)."""

import re

import pytest
import tomllib
from _repo_scan import REPO_ROOT, read_text, repo_files

# The PEP 723 reference expression for one metadata block.
_BLOCK = re.compile(r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$")
_PIN = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)(?:\[[^\]]*\])?==(?P<version>[^\s;]+)$")


def _group_pins(pyproject_text: str) -> dict[str, str]:
    # Every group's exact pins: a package pinned in two groups must agree, or a script could follow either.
    project = tomllib.loads(pyproject_text)
    pins: dict[str, str] = {}
    for requirements in project["dependency-groups"].values():
        for pin in (_PIN.match(r) for r in requirements if isinstance(r, str)):
            if pin:
                version = pins.setdefault(pin["name"].lower(), pin["version"])
                assert version == pin["version"], f"pyproject.toml pins {pin['name']} at {version} and {pin['version']}"
    return pins


def _findings(path: str, text: str, python: str, pins: dict[str, str]) -> list[str]:
    found = []
    for block in _BLOCK.finditer(text):
        if block["type"] != "script":
            continue
        meta = tomllib.loads("".join(line[2:] if line.startswith("# ") else line[1:] for line in block["content"].splitlines(keepends=True)))
        if meta.get("requires-python") != python:
            found.append(f"{path}: requires-python {meta.get('requires-python')!r}, pyproject.toml's is {python!r}")
        for requirement in meta.get("dependencies", []):
            pin = _PIN.match(requirement)
            name = (pin["name"] if pin else re.split(r"[\s<>=!~\[;]", requirement, maxsplit=1)[0]).lower()
            if name not in pins:
                found.append(f"{path}: {requirement!r} has no exact pin in pyproject.toml's dependency groups to follow")
            elif not pin or pin["version"] != pins[name]:
                found.append(f"{path}: {requirement!r} is not pyproject.toml's {name}=={pins[name]}")
    return found


def _script_files() -> list[str]:
    return [p for p in repo_files() if p.endswith(".py") and "# /// script" in (read_text(p) or "")]


def test_the_scan_finds_the_repos_script_blocks() -> None:
    # An empty scan would pass everything: the coverage renderer and the toolchain installer both carry one.
    found = _script_files()
    assert {"scripts/_render_coverage.py", "toolchain/setup_toolchain.py"} <= set(found), found


def test_every_script_block_follows_pyproject_toml() -> None:
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    python = tomllib.loads(pyproject_text)["project"]["requires-python"]
    pins = _group_pins(pyproject_text)
    found = [line for path in _script_files() for line in _findings(path, read_text(path) or "", python, pins)]
    assert not found, "\n".join(found)


@pytest.mark.parametrize(
    ("dependencies", "python", "expected"),
    [
        ('["coverage"]', ">=3.11", "is not pyproject.toml's coverage==7.0"),
        ('["coverage>=7"]', ">=3.11", "is not pyproject.toml's coverage==7.0"),
        ('["coverage==6.5"]', ">=3.11", "is not pyproject.toml's coverage==7.0"),
        ('["requests==2.0"]', ">=3.11", "has no exact pin in pyproject.toml's dependency groups"),
        ("[]", ">=3.10", "requires-python '>=3.10'"),
    ],
    ids=["unpinned", "ranged", "other-pin", "not-pinned-in-pyproject", "python"],
)
def test_a_planted_block_that_drifts_is_named(dependencies: str, python: str, expected: str) -> None:
    text = f'#!/usr/bin/env python3\n# /// script\n# requires-python = "{python}"\n# dependencies = {dependencies}\n# ///\n"""x"""\n'
    found = _findings("scripts/x.py", text, ">=3.11", {"coverage": "7.0"})
    assert len(found) == 1 and expected in found[0], found
    assert _findings("scripts/x.py", text.replace(dependencies, '["coverage==7.0"]').replace(python, ">=3.11"), ">=3.11", {"coverage": "7.0"}) == []


def test_two_groups_pinning_one_package_apart_are_named() -> None:
    text = '[dependency-groups]\na = ["coverage==7.0", {include-group = "b"}]\nb = ["coverage==6.5"]\n'
    with pytest.raises(AssertionError, match=re.escape("pins coverage at 7.0 and 6.5")):
        _group_pins(text)
    assert _group_pins(text.replace("6.5", "7.0")) == {"coverage": "7.0"}
