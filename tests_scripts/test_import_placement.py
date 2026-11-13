"""Imports run once, at module load, and every import is static (SPECIFICATION.md F.1; agent, 2026-10-06): no import
inside a function body and no dynamic load anywhere in the nine lint scopes, outside _NAMED_EXCEPTIONS."""

import ast
import re
from collections import Counter
from pathlib import Path

from _repo_scan import REPO_ROOT, repo_files

SCOPES = ("src/", "buildgen/", "digital_twin/", "fakes/", "tests/", "tests_scripts/", "tests_hardware/", "scripts/", "toolchain/")
# tests/_tmp/ is scratch; this file's own fixtures are the patterns themselves.
_SKIPPED = ("tests/_tmp/", "tests_scripts/test_import_placement.py")
# The import-graph check plants dynamic loads as string fixtures; its code is still checked, its strings are not launchers.
_FIXTURE_LITERALS = frozenset({"tests_scripts/test_import_graph.py"})
# __import__ counts only as a bare call, importlib's names in any spelling. Executing a file by path
# (exec) is not an import (F.1): ruff's S102 and its per-file ignores govern it.
_BUILTIN_LOADS = frozenset({"__import__"})
_IMPORTLIB_LOADS = frozenset({"import_module", "spec_from_file_location", "module_from_spec", "exec_module"})
_EMBEDDED_TRIGGERS = tuple(f"{name}(" for name in (*_BUILTIN_LOADS, *_IMPORTLIB_LOADS))

Site = tuple[str, str, str]

# SPECIFICATION.md F.1's named host and test sites, each with the reason F.1 gives: a dynamic load in one
# of these files passes; a function-level import there does not.
_NAMED_EXCEPTIONS: dict[str, str] = {
    "buildgen/validate.py": "loads toolchain/micropython_overrides.py by path: it is no package",
    "digital_twin/run_generic_integration.py": "the module its device config names, or a twin test's plan-picked device",
    "ext/freezefs/ffsextract.py": "vendored, build-time only; its extract mode is never used",
    "tests/_boot_contiguity_probe.py": "a device module by its derived name",
    "tests/_digital_twin_construction_scenarios.py": "a device module by its derived name",
    "tests/_sensortask_scenarios.py": "a device module by its derived name",
    "tests/test_asy_isl29125_driver.py": '__import__("time") inside two test statements',
    "tests_scripts/_script_loader.py": "a scripts/ file by path",
    "tests_scripts/conftest.py": "sets the path that loader relies on; names importlib in a comment",
    "tests_scripts/test_buildgen_validate.py": "a test of the named loader in buildgen/validate.py",
    "tests_scripts/test_js_coverage_report_dir.py": "names importlib in a comment; reads import statements by AST",
}
_DYNAMIC_LOADS = _BUILTIN_LOADS | _IMPORTLIB_LOADS

def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr if func.attr in _IMPORTLIB_LOADS else None
    bare = func.id if isinstance(func, ast.Name) else None
    return bare if bare in _BUILTIN_LOADS or bare in _IMPORTLIB_LOADS else None


def is_named(site: Site) -> bool:
    return site[2] in _DYNAMIC_LOADS and site[0] in _NAMED_EXCEPTIONS


def sites_in_source(path: str, source: str) -> list[Site]:
    # Every function-level import (by module) and every dynamic load (by call), with the dotted name
    # of what encloses it - "<module>" at module level, where only a dynamic load counts. Source held in a
    # string literal (a launcher another interpreter runs) is parsed and checked the same way.
    sites: list[Site] = []

    def visit(node: ast.AST, scope: tuple[str, ...], *, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            qualname = ".".join(scope) or "<module>"
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, (*scope, child.name), in_function=in_function or not isinstance(child, ast.ClassDef))
                continue
            if in_function and isinstance(child, ast.Import):
                sites.extend((path, qualname, alias.name) for alias in child.names)
            elif in_function and isinstance(child, ast.ImportFrom):
                sites.append((path, qualname, "." * child.level + (child.module or "")))
            elif isinstance(child, ast.Call) and (call := _call_name(child)):
                sites.append((path, qualname, call))
            elif isinstance(child, ast.Constant) and isinstance(child.value, str) and path not in _FIXTURE_LITERALS and any(t in child.value for t in _EMBEDDED_TRIGGERS):
                sites.extend((path, qualname, name) for _, _, name in _embedded_sites(path, child.value))
            visit(child, scope, in_function=in_function)

    visit(ast.parse(source, filename=path), (), in_function=False)
    return sites


def _embedded_sites(path: str, text: str) -> list[Site]:
    try:
        return sites_in_source(path, text)
    except SyntaxError:
        return []


def collect_sites() -> Counter[Site]:
    found: Counter[Site] = Counter()
    for path in repo_files():
        if path.endswith(".py") and path.startswith(SCOPES) and not path.startswith(_SKIPPED):
            found.update(sites_in_source(path, (REPO_ROOT / path).read_text(encoding="utf-8")))
    return found


def test_no_function_level_or_dynamic_import_outside_the_named_lists() -> None:
    new = sorted(site for site in collect_sites().elements() if not is_named(site))
    assert not new, "imports belong at module top, static (SPECIFICATION.md F.1) - move these, or name them there:\n" + "\n".join(f"  {s}" for s in new)


def test_each_kind_of_site_is_caught(tmp_path: Path) -> None:
    source = (
        "import importlib\n"
        "def f():\n    import json\n    from . import sibling\n"
        "class C:\n    async def g(self):\n        from os import path\n"
        "def h(p):\n    spec = importlib.util.spec_from_file_location('m', p)\n    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n"
        "mod = __import__('time')\nimportlib.import_module('x')\nexec(compile(open('f').read(), 'f', 'exec'))\n"
    )
    probe = tmp_path / "probe.py"
    probe.write_text(source, encoding="utf-8")
    assert sorted(sites_in_source("probe.py", probe.read_text(encoding="utf-8"))) == sorted([
        ("probe.py", "f", "json"),
        ("probe.py", "f", "."),
        ("probe.py", "C.g", "os"),
        ("probe.py", "h", "spec_from_file_location"),
        ("probe.py", "h", "exec_module"),
        ("probe.py", "h", "module_from_spec"),
        ("probe.py", "<module>", "__import__"),
        ("probe.py", "<module>", "import_module"),
    ])


def test_a_named_file_passes_only_its_dynamic_loads() -> None:
    named = next(iter(_NAMED_EXCEPTIONS))
    source = "def f():\n    import json\n    return __import__('time')\n"
    sites = sites_in_source(named, source)
    assert [is_named(site) for site in sites] == [False, True], sites
    assert not any(is_named(site) for site in sites_in_source("src/unnamed.py", source))


def f1_named_paths() -> set[str]:
    # The files F.1's list names: code spans at parenthesis depth 0 between its colon and the exec
    # sentence (a reason's own code spans sit inside its parentheses).
    spec = (REPO_ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")
    listed = re.search(r"judges every listed one harmless \(owner, 2026-10-05\):\n(.*?)Executing a file by path", spec, re.DOTALL)
    assert listed is not None, "SPECIFICATION.md F.1's named list moved - re-anchor f1_named_paths()"
    paths, depth = set(), 0
    for index, part in enumerate(listed.group(1).split("`")):
        if index % 2:
            if depth == 0 and part.endswith(".py"):
                paths.add(part)
        else:
            depth += part.count("(") - part.count(")")
    return paths


def test_the_named_exceptions_mirror_specification_f1() -> None:
    assert set(_NAMED_EXCEPTIONS) == f1_named_paths(), "_NAMED_EXCEPTIONS and SPECIFICATION.md F.1's named list differ - one of them moved"
    missing = sorted(path for path in _NAMED_EXCEPTIONS if not (REPO_ROOT / path).is_file())
    assert not missing, f"named in F.1 but no such file: {missing}"


def test_module_level_and_type_checking_imports_pass() -> None:
    source = "import os\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import json\nclass C:\n    import re\n"
    assert sites_in_source("ok.py", source) == []
