"""Every path a config file names resolves to something tracked: ruff's per-file globs, mypy's files, mypy_path and
exclude entries in all three passes, the tsconfig include/exclude/extends lists, the repo scripts package.json, the
workflow and its actions name, and vitest.config.js's relative imports. A dead path silently checks nothing."""

import configparser
import fnmatch
import json
import re
from pathlib import Path

import pytest
import tomllib
from _repo_scan import REPO_ROOT, repo_files

# Made by the run itself, never tracked: typecheck.sh installs typings/ and generates build/generated_src/ first; the
# generated tree's ruff entries are test_ruff_exemptions_live.py's to prove.
_GENERATED = ("typings", "build/generated_src")
_SCRIPT_PATH = re.compile(r"(?<![\w./~-])(?:scripts|toolchain|tests_scripts)/[\w./-]+\.(?:sh|py|mjs|js|toml|json)\b")
_RELATIVE_IMPORT = re.compile(r"""\bfrom\s+["'](\.{1,2}/[^"']+)["']""")


def _comma_list(value: str) -> "list[str]":
    return [part.strip() for part in re.split(r"[,:]", value) if part.strip()]


def _exclude_alternatives(regex: str) -> "list[str]":
    # A verbose `(?x)(a|b|c)` exclude split into its top-level alternatives, each of which must match something.
    body = regex.removeprefix("(?x)").strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    parts, depth, current = [], 0, ""
    for ch in body:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "|" and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    return [p.strip() for p in [*parts, current] if p.strip()]


def _generated(entry: str) -> bool:
    return any(entry == g or entry.startswith(f"{g}/") for g in _GENERATED)


def _jsonc(path: Path) -> "dict[str, object]":
    # tsconfig files carry // comments, which JSON does not.
    text = re.sub(r"(?m)^\s*//.*$", "", path.read_text(encoding="utf-8"))
    loaded = json.loads(text)
    assert isinstance(loaded, dict)
    return loaded


def _path_problems(where: str, entries: "list[str]", tracked: "list[str]") -> "list[str]":
    # A file, a directory holding a tracked file, or a glob matching one.
    def resolves(entry: str) -> bool:
        entry = entry.rstrip("/")
        if entry == ".":
            return True  # the repository root itself
        # `**/` also matches no directory at all, as tsconfig and mypy globs read it.
        globs = {entry, entry.replace("**/", "")}
        return entry in tracked or any(p.startswith(f"{entry}/") for p in tracked) or any(fnmatch.fnmatchcase(p, g) for p in tracked for g in globs)

    return [f"{where}: {entry!r} resolves to nothing tracked" for entry in entries if not _generated(entry) and not resolves(entry)]


def _ruff_glob_problems(pyproject: Path, tracked: "list[str]") -> "list[str]":
    with pyproject.open("rb") as f:
        globs = tomllib.load(f)["tool"]["ruff"]["lint"]["per-file-ignores"]
    # ruff's globs: `*` crosses `/`, matched against the repo-relative path or the file name.
    dead = [g for g in globs if not _generated(g) and not any(fnmatch.fnmatchcase(p, g) or fnmatch.fnmatchcase(Path(p).name, g) for p in tracked)]
    return [f"{pyproject.name} [tool.ruff.lint.per-file-ignores]: {g!r} matches no tracked file" for g in dead]


@pytest.fixture(scope="module")
def tracked() -> "list[str]":
    return repo_files()


def test_every_ruff_per_file_glob_matches_a_tracked_file(tracked: "list[str]") -> None:
    problems = _ruff_glob_problems(REPO_ROOT / "pyproject.toml", tracked)
    assert not problems, "\n".join(problems)


def test_every_mypy_path_entry_resolves_in_all_three_passes(tracked: "list[str]") -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        mypy = tomllib.load(f)["tool"]["mypy"]
    problems = _path_problems("pyproject.toml [tool.mypy] files", list(mypy["files"]), tracked)
    problems += _path_problems("pyproject.toml [tool.mypy] mypy_path", list(mypy["mypy_path"]), tracked)
    problems += [f"pyproject.toml [tool.mypy] exclude: {rx!r} matches no tracked path" for rx in mypy["exclude"] if not any(re.search(rx, p) for p in tracked)]
    for ini in ("host_typecheck.ini", "digital_twin/typecheck.ini"):
        parser = configparser.ConfigParser()
        parser.read(REPO_ROOT / ini, encoding="utf-8")
        section = parser["mypy"]
        problems += _path_problems(f"{ini} files", _comma_list(section.get("files", "")), tracked)
        problems += _path_problems(f"{ini} mypy_path", _comma_list(section.get("mypy_path", "")), tracked)
        problems += [f"{ini} exclude: {alt!r} matches no tracked path" for alt in _exclude_alternatives(section.get("exclude", "")) if not any(re.search(f"(?x){alt}", p) for p in tracked)]
    assert not problems, "\n".join(problems)


def test_every_tsconfig_include_exclude_and_extends_entry_resolves(tracked: "list[str]") -> None:
    configs = sorted(p for p in tracked if re.fullmatch(r"tsconfig[\w.-]*\.json", p))
    assert configs, "no tracked tsconfig*.json - the check would pass on nothing"
    problems = []
    for name in configs:
        config = _jsonc(REPO_ROOT / name)
        for key in ("include", "exclude"):
            entries = config.get(key, [])
            assert isinstance(entries, list)
            problems += _path_problems(f"{name} {key}", [str(e) for e in entries], tracked)
        extends = config.get("extends")
        if isinstance(extends, str) and extends.startswith("."):
            problems += _path_problems(f"{name} extends", [str((Path(name).parent / extends).as_posix()).removeprefix("./")], tracked)
    assert not problems, "\n".join(problems)


def test_every_repo_script_a_workflow_action_or_npm_script_names_exists(tracked: "list[str]") -> None:
    sources = [p for p in tracked if p.startswith(".github/") and p.endswith((".yml", ".yaml"))]
    assert sources, "no tracked workflow or action - the check would pass on nothing"
    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    texts = [(p, (REPO_ROOT / p).read_text(encoding="utf-8")) for p in sources] + [("package.json scripts", "\n".join(package["scripts"].values()))]
    named = [(where, path) for where, text in texts for path in _SCRIPT_PATH.findall(text)]
    assert named, "no repo script path found in the workflow, its actions or package.json - the reader misses them"
    missing = [f"{where}: {path} is not a tracked file" for where, path in named if path not in tracked]
    assert not missing, "\n".join(missing)


def test_every_relative_import_of_vitest_config_exists(tracked: "list[str]") -> None:
    imports = _RELATIVE_IMPORT.findall((REPO_ROOT / "vitest.config.js").read_text(encoding="utf-8"))
    assert imports, "vitest.config.js shows no relative import - the reader misses them"
    missing = [i for i in imports if Path(i).as_posix().removeprefix("./") not in tracked]
    assert not missing, f"vitest.config.js imports files that are not tracked: {missing}"


def test_a_dead_glob_or_path_is_reported(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.ruff.lint.per-file-ignores]\n"src/**" = ["T20"]\n"src/gone.py" = ["S101"]\n"build/generated_src/**" = ["E402"]\n', encoding="utf-8")
    assert _ruff_glob_problems(pyproject, ["src/a.py"]) == ["pyproject.toml [tool.ruff.lint.per-file-ignores]: 'src/gone.py' matches no tracked file"]
    assert _path_problems("x", ["src", "src/**/*.py", "tests/test_*.py", "typings", "nowhere"], ["src/a.py"]) == ["x: 'tests/test_*.py' resolves to nothing tracked", "x: 'nowhere' resolves to nothing tracked"]
    assert _exclude_alternatives(r"(?x)(^a/|^b\.py$|^c/(d|e)$)") == ["^a/", r"^b\.py$", "^c/(d|e)$"]
