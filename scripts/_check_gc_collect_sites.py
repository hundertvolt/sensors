#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The gc.collect() site check (SPECIFICATION.md I.4(f.1)): every call through a name bound to gc or to gc.collect,
aliases included, outside the one allowance table is reported with its enclosing function; the generated modules are
checked in memory, buildgen/'s text for an emitted collect, and a file that does not parse is an error, never a skip."""

# Usage: python3 scripts/_check_gc_collect_sites.py [--root DIR]
# Exit 0 when clean, 1 naming each site outside the table (or an allowed row with no site), 2 when a file or a device
# cannot be read.

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from buildgen.errors import BuildError  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.generate import generate_device  # noqa: E402 - the repo-root insert above makes it importable

# The whole allowance, (module, enclosing function) -> why: the boot-confined placement reset (SPECIFICATION.md I.4(f.1)).
ALLOWED = {
    ("src/asy_system_service.py", "SystemService.run_setups"): "between the units of the one-time setup list",
    ("src/asy_system_service.py", "SystemService.start_tasks"): "between the units of the one-time task-start list",
}
# Scopes whose measurement rows are not in the table yet: named as not checked in every run, never silently passed.
UNCHECKED = ("tests", "digital_twin", "tests_hardware")
_RULE = "is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))"


@dataclass
class ScanResult:
    findings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    generated: int = 0
    unchecked: tuple[str, ...] = UNCHECKED


def _bound_names(tree: ast.Module) -> "tuple[set[str], set[str]]":
    # (names bound to the gc module, names bound to gc.collect): import forms, aliases and plain assignments.
    modules: set[str] = set()
    collects: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == "gc")
        elif isinstance(node, ast.ImportFrom) and node.module == "gc":
            collects.update(alias.asname or alias.name for alias in node.names if alias.name == "collect")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr == "collect" and isinstance(node.value.value, ast.Name) and node.value.value.id in modules:
            collects.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return modules, collects


def collect_sites(tree: ast.Module) -> "list[tuple[int, str]]":
    # (line, qualified enclosing function, "<module>" at import time) of every gc.collect() call, by explicit descent so
    # each call is attributed to its nearest function.
    modules, collects = _bound_names(tree)
    sites: list[tuple[int, str]] = []

    def is_collect(call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name):
            return func.id in collects
        return isinstance(func, ast.Attribute) and func.attr == "collect" and isinstance(func.value, ast.Name) and func.value.id in modules

    def visit(node: ast.AST, owner: "tuple[str, ...]") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, (*owner, child.name))
                continue
            if isinstance(child, ast.Call) and is_collect(child):
                sites.append((child.lineno, ".".join(owner) or "<module>"))
            visit(child, owner)

    visit(tree, ())
    return sites


def _check_source(text: str, rel: str, result: ScanResult, seen: "set[tuple[str, str]]") -> None:
    try:
        tree = ast.parse(text, rel)
    except SyntaxError as e:
        result.errors.append(f"{rel}:{e.lineno}: cannot parse ({e.msg}) - the gc.collect() check could not look")
        return
    for line, owner in collect_sites(tree):
        if (rel, owner) in ALLOWED:
            seen.add((rel, owner))
        else:
            result.findings.append(f"{rel}:{line}: gc.collect() in {owner} {_RULE}")


def _check_generated(root: Path, result: ScanResult, seen: "set[tuple[str, str]]") -> None:
    # Every derived device's module and both boot entries, as the generator would write them, checked in memory.
    for toml in sorted((root / "devices").glob("*.toml")):
        if toml.stem.startswith("zz_test_"):
            continue
        try:
            generated = generate_device(toml, root / "src", root / "ext")
        except BuildError as e:
            result.errors.append(f"{toml.relative_to(root).as_posix()}: cannot generate ({e}) - the gc.collect() check could not look")
            continue
        names = (f"sensortask_{toml.stem}.py", f"sensortask_{toml.stem}_main.py", f"sensortask_{toml.stem}_main_noautostart.py")
        for name, text in zip(names, (generated.module_source, generated.boot_entry_source, generated.boot_entry_noautostart_source), strict=True):
            _check_source(text, f"build/generated_src/{name}", result, seen)
            result.generated += 1


def scan_tree(root: Path) -> ScanResult:
    result = ScanResult()
    seen: set[tuple[str, str]] = set()
    sources = sorted((root / "src").rglob("*.py"))
    if not sources:
        result.errors.append("src/: no Python file to scan - the gc.collect() check could not look")
    for path in sources:
        _check_source(path.read_text(encoding="utf-8"), path.relative_to(root).as_posix(), result, seen)
    for path in sorted((root / "buildgen").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "gc.collect(" in line:
                result.findings.append(f"{path.relative_to(root).as_posix()}:{number}: gc.collect( in buildgen/'s text - the generated modules carry none (SPECIFICATION.md I.4(f.1))")
    _check_generated(root, result, seen)
    present = {rel for rel, _owner in ALLOWED if (root / rel).is_file()}
    result.findings.extend(f"{rel}: the allowed site {owner} holds no gc.collect() call - restore it or remove its row" for rel, owner in sorted(ALLOWED) if rel in present and (rel, owner) not in seen)
    return result


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="the tree to check (default: this repository)")
    args = parser.parse_args(argv)
    result = scan_tree(args.root)
    for line in [*result.errors, *result.findings]:
        print(line, file=sys.stderr)
    print(f"gc.collect() sites: {len(ALLOWED)} allowed, {len(result.findings)} outside the table; generated modules checked: {result.generated}")
    print(f"not checked yet: {', '.join(f'{scope}/' for scope in result.unchecked)} (their measurement rows are not in the table)")
    if result.errors:
        return 2
    return 1 if result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
