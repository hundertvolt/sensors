"""The three mypy configs and every lint scope, pinned against each other: the same strictness in all three passes, ruff
and CI naming the eight scopes plus the generated tree, every Python file checked by some mypy run and by two runs only
where a named reason says why, and CI's typecheck.sh given no paths, so it checks a local run's files (B.15)."""

import configparser
import fnmatch
import re
import shlex
from pathlib import Path

import tomllib

_REPO = Path(__file__).resolve().parent.parent
# CLAUDE.md "Scope is eight directories", plus the generated device modules both gates check.
EIGHT_SCOPES = ("src", "tests", "digital_twin", "buildgen", "toolchain", "scripts", "tests_scripts", "tests_hardware")
_GENERATED = "build/generated_src"
_STRICT_FLAGS = ("strict", "no_implicit_optional", "warn_unreachable", "disallow_any_explicit")
# Each per-module override the main pass may carry, and why; a new one is triaged here first.
_OVERRIDE_REASONS = {
    "test_setter_microdot_integration": "the one file registering real Microdot routes, whose upstream stub leaves the decorators untyped",
    "frozen_html": "the frozen website the generated modules import only to mount it, on no search path",
}
_ANY_BASELINE = "disallow_any_explicit"  # the explicit-Any baseline sections: they only shrink (test_mypy_any_baseline.py)
# The runs that check one file alone, each with its config, because a second file of the same module name would join it.
_SINGLE_FILE_RUNS = (("pyproject.toml", "tests/network.py"), ("host_typecheck.ini", "tests_scripts/conftest.py"), ("host_typecheck.ini", "tests_hardware/bench/conftest.py"))
# Files two runs with different module resolution both check, and why both must stay clean.
_CHECKED_TWICE = {
    "digital_twin/": "a twin module needing none of the twin's own machine/network API: the main pass checks it against tests/'s fakes, the twin pass against its own",
}


def _main() -> "dict[str, object]":
    config = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mypy"]
    assert isinstance(config, dict)
    return config


def _ini(name: str) -> configparser.SectionProxy:
    parser = configparser.ConfigParser()
    parser.read(_REPO / name, encoding="utf-8")
    return parser["mypy"]


def _ini_list(value: str) -> "list[str]":
    return [part.strip() for part in value.split(",") if part.strip()]


def _truthy(value: object) -> bool:
    return value is True or str(value).strip().lower() == "true"


def test_the_three_passes_share_one_strictness() -> None:
    main, twin, host = _main(), _ini("digital_twin/typecheck.ini"), _ini("host_typecheck.ini")
    for name, config in (("pyproject.toml", main), ("digital_twin/typecheck.ini", twin), ("host_typecheck.ini", host)):
        for flag in _STRICT_FLAGS:
            assert _truthy(config.get(flag)), f"{name} does not set {flag}"
        codes = config.get("enable_error_code")
        listed = codes if isinstance(codes, list) else _ini_list(str(codes or ""))
        assert "ignore-without-code" in listed, f"{name}: a bare `# type: ignore` must itself be an error (enable_error_code)"
    assert main.get("no_implicit_reexport") is False, "the main pass mocks by reassigning imported names (CLAUDE.md)"
    assert twin.get("no_implicit_reexport") is None and host.get("no_implicit_reexport") is None, "only the main pass relaxes no_implicit_reexport"


def test_every_main_pass_override_is_a_named_one() -> None:
    overrides = _main().get("overrides", [])
    assert isinstance(overrides, list)
    for override in overrides:
        assert isinstance(override, dict)
        modules = override["module"] if isinstance(override["module"], list) else [override["module"]]
        if set(override) == {"module", _ANY_BASELINE}:
            assert override[_ANY_BASELINE] is False, override
            continue
        unnamed = [m for m in modules if m not in _OVERRIDE_REASONS]
        assert not unnamed, f"[[tool.mypy.overrides]] for {unnamed} has no reason in this test - name it with its reason, or drop it"


def _lint_ruff_paths() -> "list[str]":
    lines = [line.strip() for line in (_REPO / "scripts" / "lint.sh").read_text(encoding="utf-8").splitlines()]
    found = [line for line in lines if line.startswith("ruff check ")]
    assert len(found) == 1, found
    return shlex.split(found[0].split("||", 1)[0])[2:]


def _ci_run(fragment: str) -> "list[str]":
    # The words of the one `run:` line of the lint-and-typecheck job holding `fragment`.
    text = (_REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = text[text.index("\n  lint-and-typecheck:") :]
    job = job[: job.index("\n  shellcheck:")]
    runs = [line.split("run:", 1)[1].strip() for line in job.splitlines() if line.strip().startswith("run:") and fragment in line]
    assert len(runs) == 1, f"lint-and-typecheck has {len(runs)} run lines naming {fragment!r}"
    return shlex.split(runs[0])


def test_ruff_and_ci_name_the_eight_scopes_and_the_generated_tree() -> None:
    expected = sorted([*EIGHT_SCOPES, _GENERATED])
    assert sorted(_lint_ruff_paths()) == expected, "scripts/lint.sh's ruff call"
    words = _ci_run("ruff check")
    assert sorted(words[words.index("check") + 1 :]) == expected, "ci.yml's ruff step"
    assert "shellcheck scripts/*.sh || status=1" in (_REPO / "scripts" / "lint.sh").read_text(encoding="utf-8")


def test_ci_s_mypy_step_runs_typecheck_sh_with_no_arguments() -> None:
    # One scope for CI and a local run: with no paths the main pass checks exactly [tool.mypy]'s files, as locally.
    words = _ci_run("scripts/typecheck.sh")
    assert words[words.index("scripts/typecheck.sh") + 1 :] == [], "ci.yml's mypy step passes paths - run scripts/typecheck.sh bare, so it checks pyproject.toml's files"


def _main_files() -> "list[str]":
    files = _main()["files"]
    assert isinstance(files, list)
    return [str(f) for f in files]


def _scope_files() -> "list[str]":
    # Every Python file of the eight scopes, the gitignored scratch and caches aside.
    found = []
    for scope in EIGHT_SCOPES:
        for path in sorted((_REPO / scope).rglob("*.py")):
            rel = path.relative_to(_REPO).as_posix()
            if "__pycache__" in rel or rel.startswith("tests/_tmp/") or "/node_modules/" in rel:
                continue
            found.append(rel)
    return found


def _excluded(rel: str, pattern: str) -> bool:
    return re.search(pattern, rel) is not None


def _covered(rel: str, roots: "list[str]") -> bool:
    return any(rel == root or rel.startswith(root.rstrip("/") + "/") or fnmatch.fnmatch(rel, root) for root in roots)


def _runs() -> "dict[str, set[str]]":
    # Each mypy run's checked files among the scopes: the three passes (files minus exclude) and the single-file runs.
    files = _scope_files()
    main = _main()
    main_files = _main_files()  # parsed once: inside the comprehension it re-read pyproject.toml for every file
    exclude = main.get("exclude", [])
    main_exclude = [str(p) for p in exclude] if isinstance(exclude, list) else []
    host = _ini("host_typecheck.ini")
    host_exclude = host.get("exclude", "")
    twin = _ini("digital_twin/typecheck.ini")
    runs = {
        "main pass": {f for f in files if _covered(f, main_files) and not any(_excluded(f, p) for p in main_exclude)},
        "twin pass": {f for f in files if _covered(f, _ini_list(twin.get("files", "")))},
        "host pass": {f for f in files if _covered(f, _ini_list(host.get("files", ""))) and not (host_exclude and _excluded(f, host_exclude))},
    }
    for config, path in _SINGLE_FILE_RUNS:
        runs[f"{path} alone ({config})"] = {path}
    return runs


def test_every_python_file_is_checked_by_some_mypy_run() -> None:
    runs = _runs()
    unchecked = [f for f in _scope_files() if not any(f in checked for checked in runs.values())]
    assert not unchecked, f"no mypy run checks {unchecked} - name it in a pass's files or check it alone in scripts/typecheck.sh"


def test_a_file_two_runs_check_is_named_with_its_reason() -> None:
    runs = _runs()
    twice = sorted(f for f in _scope_files() if sum(f in checked for checked in runs.values()) > 1)
    unnamed = [f for f in twice if not any(f.startswith(prefix) for prefix in _CHECKED_TWICE)]
    assert not unnamed, f"checked by two runs with different resolution and named nowhere: {unnamed}"


def test_scripts_typecheck_sh_runs_the_passes_from_their_configs_and_the_single_files() -> None:
    text = (_REPO / "scripts" / "typecheck.sh").read_text(encoding="utf-8")
    assert re.search(r"mypy --config-file digital_twin/typecheck\.ini$", text, re.MULTILINE), "the twin pass takes its files from its ini, no path after it"
    for config, path in _SINGLE_FILE_RUNS:
        command = f"mypy {path}" if config == "pyproject.toml" else f"mypy --config-file {config} {path}"
        assert command in text, f"scripts/typecheck.sh never runs `{command}`"


def test_the_coverage_check_bites() -> None:
    # A planted file outside every run is reported, and one inside a pass is not.
    assert not _covered("tests/new_file.py", ["src"]) and _covered("tests/new_file.py", ["src", "tests"])
    assert _covered("tests/test_digital_twin_x.py", ["tests/test_digital_twin_*.py"])
    assert _excluded("tests/network.py", r"tests/network\.py$") and not _excluded("tests/networks.py", r"tests/network\.py$")
