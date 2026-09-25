"""The JS coverage report lands in a directory at the repo root, and its default name - `coverage`
- is importable as a namespace package, shadowing the real `coverage` distribution and turning
scripts/typecheck.sh red after a web-coverage run. This pins the name and ci.yml's two uses of it."""

import ast
import re
from pathlib import Path

_PYTHON_SCOPES = ("src", "tests", "tests_scripts", "tests_hardware", "scripts", "toolchain", "buildgen", "digital_twin")


def _reports_directory(repo_root: Path) -> str:
    text = (repo_root / "vitest.config.js").read_text()
    match = re.search(r'reportsDirectory:\s*"([^"]+)"', text)
    assert match is not None, "vitest.config.js no longer sets coverage.reportsDirectory - the default is `coverage`"
    return match.group(1)


def _top_level_imports(repo_root: Path) -> set[str]:
    """Every top-level module name this repo's own Python imports, `coverage` included - which is a
    `uv run` script dependency rather than a venv one, so importlib alone would not see it."""
    names: set[str] = set()
    for scope in _PYTHON_SCOPES:
        for path in sorted((repo_root / scope).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names.add(node.module.split(".")[0])
    return names


def test_the_report_directory_is_not_a_name_this_repo_imports(repo_root: Path) -> None:
    # Derived from the real import graph rather than blocklisting `coverage`, so the next name
    # that would shadow something fails here too.
    name = _reports_directory(repo_root)
    assert "/" not in name, f"a nested report directory cannot shadow anything, but ci.yml assumes a root one: {name!r}"
    assert name not in _top_level_imports(repo_root), f"the JS coverage report directory {name!r} shadows a module this repo imports"


def test_ci_uploads_the_directory_vitest_actually_writes(repo_root: Path) -> None:
    name = _reports_directory(repo_root)
    ci = (repo_root / ".github" / "workflows" / "ci.yml").read_text()
    assert f"hashFiles('{name}/index.html')" in ci, "ci.yml gates the JS coverage upload on a directory vitest no longer writes"
    assert f"path: {name}/" in ci, "ci.yml uploads a JS coverage directory vitest no longer writes"


def test_the_report_directory_is_gitignored(repo_root: Path) -> None:
    name = _reports_directory(repo_root)
    ignored = (repo_root / ".gitignore").read_text().splitlines()
    assert f"{name}/" in ignored, f"{name}/ is regenerated every run and must not be committable"
