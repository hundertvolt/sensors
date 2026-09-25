"""Pins that nothing a twin PROCESS runs needs tests/ importable. _http_client.HttpResponse.json()
imports tests/_strict_json lazily, and the twin's own MICROPYPATH carries no tests/ - so a second
caller inside digital_twin/ would raise ImportError only on that path, at runtime."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TWIN = REPO_ROOT / "digital_twin"
CI_SUITE = REPO_ROOT / "scripts" / "_digital_twin_ci_suite.py"
RUNNER = REPO_ROOT / "scripts" / "run_unix_port_integration.sh"

_LAZY_MODULE = "_strict_json"
_LAZY_OWNER = "_http_client.py"  # the one file allowed to reach into tests/, and only from .json()
_JSON_METHOD = "json"


def _twin_sources() -> list[Path]:
    return sorted(TWIN.glob("*.py"))


def _micropypath_values() -> list[str]:
    # Every MICROPYPATH the twin is started with, from the two places that set one.
    found = [m.group(1) for m in re.finditer(r'MICROPYPATH\s*=\s*"([^"]+)"', CI_SUITE.read_text(encoding="utf-8"))]
    found += [m.group(1) for m in re.finditer(r'MICROPYPATH="([^"]+)"', RUNNER.read_text(encoding="utf-8"))]
    return found


def _imports_of(tree: ast.Module, module: str) -> list[tuple[int, bool]]:
    # (line, is_module_level) per import of `module`, by walking the body rather than ast.walk() so
    # nesting is known: a lazy import inside a function is the whole point of the exception below.
    found: list[tuple[int, bool]] = []
    for top in tree.body:
        module_level = isinstance(top, (ast.Import, ast.ImportFrom))
        for node in ast.walk(top):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            # `import x` names the module in .names; `from x import y` names it in .module.
            named = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module]
            if module in named:
                found.append((node.lineno, module_level))
    return found


def test_the_twins_own_micropypath_still_carries_no_tests_directory() -> None:
    # The premise of everything below. If tests/ is ever added to it, this guard is obsolete rather
    # than failing - delete it then, do not widen it.
    paths = _micropypath_values()
    assert paths, f"found no MICROPYPATH assignment in {CI_SUITE.name} or {RUNNER.name} - this guard cannot check its own premise"
    for value in paths:
        assert "tests" not in value.split(":"), f"MICROPYPATH {value!r} now carries tests/, so this guard is obsolete"


@pytest.mark.parametrize("source", _twin_sources(), ids=lambda p: p.name)
def test_no_twin_module_imports_from_tests_at_module_level(source: Path) -> None:
    for line, module_level in _imports_of(ast.parse(source.read_text(encoding="utf-8")), _LAZY_MODULE):
        assert not module_level, f"{source.name}:{line} imports {_LAZY_MODULE} at module level - the twin's MICROPYPATH has no tests/, so importing this module in a twin process would fail"
        assert source.name == _LAZY_OWNER, f"{source.name}:{line} imports {_LAZY_MODULE}; only {_LAZY_OWNER} may, and only from its own .{_JSON_METHOD}()"


@pytest.mark.parametrize("source", _twin_sources(), ids=lambda p: p.name)
def test_no_twin_module_calls_the_strict_checking_json_accessor(source: Path) -> None:
    # HttpResponse.json() is the tests/-dependent path. Twin processes read .body instead; every
    # .json() caller in the repo is a tests/ file, where tests/ IS on the path.
    calls = [
        node.lineno
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == _JSON_METHOD and not node.args
    ]
    assert not calls, f"{source.name} calls .{_JSON_METHOD}() at line(s) {calls} - if that is an HttpResponse it needs tests/_strict_json, which no twin process can import; parse response.body instead"
