"""Every ruff exemption in pyproject.toml still fires: one ruff run, every exemption lifted, over the eight lint scopes
and a device tree generated here, must show each global code, each per-file code in a file its glob matches, each
allowed confusable and an F401 naming each allowed-unused-imports module, else the entry goes (SPECIFICATION.md D.6).

A policy entry with no site is listed with its reason."""

import fnmatch
import json
import subprocess
from functools import cache
from pathlib import Path

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml
from _repo_scan import pinned_ruff

from buildgen.generate import _output_names, generate_device

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCOPES = ("src", "tests", "digital_twin", "buildgen", "toolchain", "scripts", "tests_scripts", "tests_hardware")
_GENERATED = "build/generated_src"
_CONFUSABLE_RULES = ("RUF001", "RUF002", "RUF003")

# Exempt with no site today, each reviewed like a suppression: (table, glob or "", code) -> reason.
_POLICY: "dict[tuple[str, str, str], str]" = {
    ("ignore", "", "D106"): "a nested class takes its notes as # comments, as D101's classes do; no public one exists today",
}

Finding = tuple[str, str, str]  # (repo-relative path, code, message)


def _entries() -> "list[tuple[str, str, str]]":
    # (table, glob, code) for every exemption pyproject.toml lists.
    lint = _lint_table()
    ignore, per_file = lint.get("ignore", []), lint.get("per-file-ignores", {})
    assert isinstance(ignore, list) and isinstance(per_file, dict), "pyproject.toml's ruff ignore tables have an unexpected shape"
    entries = [("ignore", "", str(code)) for code in ignore]
    entries += [("per-file-ignores", str(glob), str(code)) for glob, codes in per_file.items() for code in codes]
    return entries


def _glob_matches(glob: str, path: str) -> bool:
    # ruff's per-file globs: `*` crosses `/` (globset's default), matched against the repo-relative path or the file name.
    return fnmatch.fnmatchcase(path, glob) or fnmatch.fnmatchcase(Path(path).name, glob)


@cache
def _lint_table() -> "dict[str, object]":
    with (_REPO_ROOT / "pyproject.toml").open("rb") as f:
        table = tomllib.load(f)["tool"]["ruff"]["lint"]
    assert isinstance(table, dict)
    return table


def _live(table: str, glob: str, code: str, findings: "list[Finding]") -> bool:
    return any(_selects(code, found) and (table == "ignore" or _glob_matches(glob, path)) for path, found, _ in findings)


def _selects(selector: str, code: str) -> bool:
    # A selector names a rule (ARG002) or a prefix (PT, T20); PT must not select PTH105.
    rest = code[len(selector) :]
    return code.startswith(selector) and (not rest or rest[0].isdigit())


def _unused_import_of(module: str, message: str) -> bool:
    # An F401 message names the import's qualified name first; ruff's allowance covers a module and its submodules.
    name = message.partition("`")[2].partition("`")[0]
    return name == module or name.startswith(module + ".")


@pytest.fixture(scope="module")
def lifted(tmp_path_factory: pytest.TempPathFactory) -> "list[Finding]":
    # Every device's three generated files under <tmp>/build/generated_src, then one ruff run over them and the scopes
    # with every exemption lifted - inline ones included, so a central entry's liveness never depends on a shadowing noqa.
    root = tmp_path_factory.mktemp("lifted").resolve()
    generated = root / _GENERATED
    generated.mkdir(parents=True)
    for device in DEVICE_NAMES:
        result = generate_device(device_toml(device), _REPO_ROOT / "src", _REPO_ROOT / "ext")
        for name, text in zip(_output_names(device), (result.module_source, result.boot_entry_source, result.boot_entry_noautostart_source), strict=True):
            (generated / name).write_text(text, encoding="utf-8")
    cmd = [pinned_ruff(), "check", "--no-cache", "--ignore-noqa", "--exit-zero", "--output-format", "json", "--config", str(_REPO_ROOT / "pyproject.toml"),
           "--config", 'lint.select = ["ALL"]', "--config", "lint.per-file-ignores = {}", "--config", "lint.allowed-confusables = []",
           "--config", "lint.pyflakes.allowed-unused-imports = []", *_SCOPES, str(generated)]
    done = subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True, check=False)
    assert done.returncode == 0, f"ruff itself failed: {done.stderr}"
    findings: list[Finding] = []
    for item in json.loads(done.stdout):
        path = Path(item["filename"]).resolve()
        rel = path.relative_to(root) if path.is_relative_to(root) else path.relative_to(_REPO_ROOT.resolve())
        assert item["code"], f"ruff could not read {rel}: {item['message']} - its findings would be missing"
        findings.append((rel.as_posix(), item["code"], item["message"]))
    return findings


def test_the_run_reads_every_scope_and_every_generated_file(lifted: "list[Finding]") -> None:
    # Under select = ALL every file has a finding (CPY001 at least), so a file with none was never read.
    read = {path for path, _, _ in lifted}
    missing = [scope for scope in _SCOPES if not any(p.startswith(f"{scope}/") for p in read)]
    missing += [f"{_GENERATED}/{name}" for device in DEVICE_NAMES for name in _output_names(device) if f"{_GENERATED}/{name}" not in read]
    assert not missing, f"the lifted ruff run read nothing in: {missing}"


def test_every_global_ignore_still_fires(lifted: "list[Finding]") -> None:
    dead = [code for table, _, code in _entries() if table == "ignore" and (table, "", code) not in _POLICY and not _live(table, "", code, lifted)]
    assert not dead, "\n".join(f"pyproject.toml [tool.ruff.lint] ignore: {code} has no finding anywhere - remove it, or list it in _POLICY with its reason" for code in dead)


def test_every_per_file_code_still_fires_in_a_file_its_glob_matches(lifted: "list[Finding]") -> None:
    dead = [(glob, code) for table, glob, code in _entries() if table == "per-file-ignores" and (table, glob, code) not in _POLICY and not _live(table, glob, code, lifted)]
    assert not dead, "\n".join(f"pyproject.toml per-file-ignores {glob!r}: {code} has no finding in a file the glob matches - remove it, or list it in _POLICY with its reason" for glob, code in dead)


def test_every_allowed_confusable_still_appears_in_a_finding(lifted: "list[Finding]") -> None:
    allowed = _lint_table().get("allowed-confusables", [])
    assert isinstance(allowed, list)
    dead = [char for char in allowed if not any(code in _CONFUSABLE_RULES and f"`{char}`" in message for _, code, message in lifted)]
    assert not dead, f"pyproject.toml allowed-confusables {dead}: no RUF001-RUF003 finding names them - remove them"


def test_every_allowed_unused_import_is_still_imported_unused(lifted: "list[Finding]") -> None:
    pyflakes = _lint_table().get("pyflakes", {})
    assert isinstance(pyflakes, dict)
    allowed = pyflakes.get("allowed-unused-imports", [])
    assert isinstance(allowed, list)
    dead = [module for module in allowed if not any(code == "F401" and _unused_import_of(str(module), message) for _, code, message in lifted)]
    assert not dead, "\n".join(f"pyproject.toml [tool.ruff.lint.pyflakes] allowed-unused-imports: {module!r} is imported unused nowhere - remove it" for module in dead)


def test_every_policy_entry_names_a_listed_exemption_that_has_no_site(lifted: "list[Finding]") -> None:
    listed = set(_entries())
    stale = [entry for entry in _POLICY if entry not in listed]
    firing = [entry for entry in _POLICY if entry in listed and _live(*entry, lifted)]
    assert not stale, f"_POLICY names exemptions pyproject.toml no longer lists - drop them: {stale}"
    assert not firing, f"_POLICY entries that fire now, so the liveness check covers them - drop them from _POLICY: {firing}"


@pytest.mark.parametrize(
    ("selector", "code", "selected"),
    [("PT", "PT018", True), ("PT", "PTH105", False), ("T20", "T201", True), ("ARG002", "ARG002", True), ("ARG00", "ARG005", True), ("S1", "S101", True), ("E40", "E501", False)],
)
def test_a_selector_names_a_rule_or_a_code_prefix(selector: str, code: str, *, selected: bool) -> None:
    assert _selects(selector, code) is selected


@pytest.mark.parametrize(
    ("module", "imported", "covered"),
    [("frozen_html", "frozen_html", True), ("a.b", "a.b.c", True), ("manual_wifi", "pkg.manual_wifi", False), ("a", "ab", False), ("a.b", "a", False)],
)
def test_an_allowed_module_covers_its_submodules_as_ruffs_does(module: str, imported: str, *, covered: bool) -> None:
    assert _unused_import_of(module, f"`{imported}` imported but unused") is covered


def test_a_glob_crosses_directories_as_ruffs_does() -> None:
    assert _glob_matches("tests_hardware/**", "tests_hardware/device_scripts/x.py")
    assert _glob_matches("build/generated_src/sensortask_*_main.py", "build/generated_src/sensortask_fixture_main.py")
    assert not _glob_matches("src/asy_scd30_driver.py", "tests/asy_scd30_driver.py")
