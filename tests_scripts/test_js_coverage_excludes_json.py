"""The v8 coverage provider re-parses every file V8 reported coverage for as JavaScript, so a JSON
file left in the coverage set throws a rolldown parse stack per run before being dropped anyway.
This pins the `coverage.exclude` globs that keep every JSON this repo holds out of that set."""

import os
import re
from pathlib import Path

_PRUNED = {".git", ".venv", "__pycache__", "build", "node_modules", "typings"}
# The JSON the real website and its mock server fetch at runtime, which is what V8 reported and
# the provider then failed to parse - named here so a rename makes this guard fail loudly rather
# than quietly cover nothing.
_RUNTIME_JSON_DIRS = ("html/definitions", "mockdata")


def _coverage_exclude_globs(repo_root: Path) -> list[str]:
    text = (repo_root / "vitest.config.js").read_text()
    block = text.find("coverage: {")
    assert block != -1, "vitest.config.js no longer configures test.coverage at all"
    match = re.search(r"exclude:\s*\[([^\]]*)\]", text[block:])
    assert match is not None, "vitest.config.js's coverage block sets no exclude - every JSON V8 saw is re-parsed as JavaScript"
    return re.findall(r'"([^"]+)"', match.group(1))


def _glob_to_regex(pattern: str) -> "re.Pattern[str]":
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(f"^{out}$")


def _repo_json_files(repo_root: Path) -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _PRUNED and not d.startswith("htmlcov")]
        found.extend(str(Path(dirpath, name).relative_to(repo_root)) for name in filenames if name.endswith(".json"))
    return found


def test_every_json_file_this_repo_holds_is_excluded_from_js_coverage(repo_root: Path) -> None:
    matchers = [_glob_to_regex(glob) for glob in _coverage_exclude_globs(repo_root)]
    files = _repo_json_files(repo_root)
    assert len(files) >= 4, f"only {len(files)} JSON files found - this guard is walking the wrong tree"
    unexcluded = [f for f in files if not any(m.match(f) for m in matchers)]
    assert not unexcluded, f"JSON is never parseable as JavaScript, but these are left in the coverage set: {unexcluded}"


def test_the_runtime_json_the_provider_choked_on_is_still_there(repo_root: Path) -> None:
    for directory in _RUNTIME_JSON_DIRS:
        found = sorted((repo_root / directory).glob("*.json"))
        assert found, f"{directory}/ holds no JSON any more - re-point this guard at wherever the site's data moved"
