"""Every dev tool is pinned exactly and the pin agrees with what uv.lock records and resolves, uv itself is pinned once,
and Node's majors agree (.nvmrc, @types/node, engines). Parsed, never run: `uv lock --check` passes a lock whose
manifest and resolved versions disagree; this catches it. The PEP 723 coverage pin is test_script_metadata_pins.py's."""

import json
import re

import pytest
import tomllib
from _repo_scan import REPO_ROOT, repo_files

_PIN = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[0-9][^\s;,]*)$")
# A uv version written into CI or an action besides pyproject.toml's own, as a pip/pipx requirement would carry it.
_UV_LITERAL = re.compile(r"(?<![\w-])uv\s*(?:==|>=|<=|~=|>|<)\s*v?\d", re.IGNORECASE)
_MAJOR = re.compile(r"\d+")


def _canonical(name: str) -> str:
    # PEP 503's normalised name, the form uv.lock records.
    return re.sub(r"[-_.]+", "-", name).lower()


def _group_entries() -> "list[str]":
    # Every entry of every [dependency-groups] list: the tools uv syncs.
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        groups = tomllib.load(f)["dependency-groups"]
    entries = [str(entry) for group in groups.values() for entry in group]
    assert entries, "pyproject.toml has no [dependency-groups] entry to check"
    return entries


def _first_major(text: str, what: str) -> int:
    found = _MAJOR.search(text)
    assert found, f"{what} names no version: {text!r}"
    return int(found.group())


def test_every_dev_tool_is_pinned_exactly() -> None:
    loose = [entry for entry in _group_entries() if _PIN.match(entry) is None]
    assert not loose, f"pyproject.toml's dependency groups must pin every tool as name==version, so no `uv sync` brings a rule or check nobody chose: {loose}"


def test_every_pin_agrees_with_the_locks_manifest_and_resolved_version() -> None:
    with (REPO_ROOT / "uv.lock").open("rb") as f:
        packages = tomllib.load(f)["package"]
    (project,) = [p for p in packages if p.get("source", {}).get("virtual") == "."]
    manifest = {_canonical(e["name"]): e.get("specifier", "") for group in project["metadata"]["requires-dev"].values() for e in group}
    problems = []
    for pin in (_PIN.match(entry) for entry in _group_entries()):
        if pin is None:
            continue  # the test above names it
        name, version = _canonical(pin["name"]), pin["version"]
        resolved = sorted({str(p["version"]) for p in packages if _canonical(str(p["name"])) == name})
        if manifest.get(name) != f"=={version}":
            problems.append(f"{name}: pyproject.toml pins =={version}, uv.lock's manifest records {manifest.get(name)!r}")
        if resolved != [version]:
            problems.append(f"{name}: pyproject.toml pins =={version}, uv.lock resolves {resolved}")
    assert not problems, "pyproject.toml and uv.lock disagree - re-run `uv lock`, then `uv sync`:\n" + "\n".join(problems)


def test_uv_itself_is_pinned_exactly_and_nowhere_else() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        required = tomllib.load(f).get("tool", {}).get("uv", {}).get("required-version")
    assert isinstance(required, str), "pyproject.toml's [tool.uv] has no required-version: any uv may sync this tree"
    assert re.fullmatch(r"==\d+\.\d+\.\d+", required), f"[tool.uv] required-version {required!r} is not one exact ==X.Y.Z pin"
    files = [p for p in repo_files() if p.startswith(".github/")]
    assert files, "no tracked .github/ file to scan - the check would pass on nothing"
    second = [f"{p}:{row}: {line.strip()}" for p in files for row, line in enumerate((REPO_ROOT / p).read_text(encoding="utf-8").splitlines(), 1) if _UV_LITERAL.search(line)]
    assert not second, "a uv version besides [tool.uv] required-version - read it from pyproject.toml instead:\n" + "\n".join(second)


def test_node_majors_agree() -> None:
    nvmrc = _first_major((REPO_ROOT / ".nvmrc").read_text(encoding="utf-8"), ".nvmrc")
    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((REPO_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    majors = {
        "package.json @types/node": _first_major(str(package["devDependencies"]["@types/node"]), "@types/node"),
        "package.json engines.node lower bound": _first_major(str(package["engines"]["node"]), "engines.node"),
        "package-lock.json resolved @types/node": _first_major(str(lock["packages"]["node_modules/@types/node"]["version"]), "the locked @types/node"),
    }
    wrong = {where: major for where, major in majors.items() if major != nvmrc}
    assert not wrong, f".nvmrc pins Node {nvmrc}, but: {wrong}"


@pytest.mark.parametrize(
    ("entry", "pinned"),
    [("ruff==0.16.10", True), ("pytest", False), ("mpremote>=1.29", False), ("types-pyserial==3.5.0.20260712", True), ("x==", False)],
)
def test_a_pin_is_one_exact_version(entry: str, *, pinned: bool) -> None:
    assert (_PIN.match(entry) is not None) is pinned


@pytest.mark.parametrize(
    ("line", "found"),
    [("run: pip install uv==0.8.17", True), ('run: pip install "uv>=0.8"', True), ("run: pip install uv", False), ("uses: astral-sh/setup-uv@v6", False), ("uv sync --locked", False)],
)
def test_a_second_uv_version_is_recognised(line: str, *, found: bool) -> None:
    assert (_UV_LITERAL.search(line) is not None) is found
