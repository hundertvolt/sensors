"""Pins that nothing a twin PROCESS runs needs tests/ importable. _http_client.HttpResponse.json()
imports tests/_strict_json lazily, and the twin's own MICROPYPATH carries no tests/ - so a second
caller inside digital_twin/ would raise ImportError only on that path, at runtime."""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TWIN = REPO_ROOT / "digital_twin"
_LAUNCH_DIRS = ("scripts", "tests_scripts", "tests_js", "tests_hardware")
_LAUNCH_SUFFIXES = (".py", ".sh", ".js", ".mjs")
# A quoted run of colon-separated path segments: a MICROPYPATH value, in any of the four forms (Python, f-string, shell,
# JS template), when it holds both the twin's directory and the frozen-module sentinel.
_PATH_VALUE = re.compile(r"[\"'`]((?:[^\"'`\s:]+:)+[^\"'`\s:]+)[\"'`]")
# The runner as a process argument: an array element on its own line, or a shell word after the interpreter.
_SPAWN = re.compile(r'^"digital_twin/run_generic_integration\.py",?$|micropython_bin\}?"?\s+digital_twin/run_generic_integration\.py')

_LAZY_MODULE = "_strict_json"
_LAZY_OWNER = "_http_client.py"  # the one file allowed to reach into tests/, and only from .json()
_JSON_METHOD = "json"


def _twin_sources() -> list[Path]:
    return sorted(TWIN.rglob("*.py"))


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


def _launches_the_runner(text: str) -> bool:
    lines = (line.strip() for line in text.splitlines())
    return any(_SPAWN.search(line) for line in lines if not line.startswith(("#", "//")))


def _micropypath_values() -> list[str]:
    # Every MICROPYPATH a twin is started with, found at every launch site under the launch directories.
    found: list[str] = []
    for directory in _LAUNCH_DIRS:
        for path in sorted((REPO_ROOT / directory).rglob("*")):
            if path.suffix in _LAUNCH_SUFFIXES and "node_modules" not in path.parts and path.name != Path(__file__).name:
                found += _twin_path_values(path.read_text(encoding="utf-8"))
    return found


def _module_constants(path: Path) -> "dict[str, object]":
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Call) and ast.unparse(value.func) == "const" and value.args:
                value = value.args[0]  # micropython.const(): the literal it wraps
            try:
                found[node.targets[0].id] = ast.literal_eval(value)
            except ValueError:
                continue
    return found


def _twin_path_values(text: str) -> list[str]:
    return [m.group(1) for m in _PATH_VALUE.finditer(text) if {"digital_twin", ".frozen"} <= set(m.group(1).split(":"))]


def test_the_twins_own_micropypath_still_carries_no_tests_directory() -> None:
    # The premise of everything below. If tests/ is ever added to it, this guard is obsolete rather
    # than failing - delete it then, do not widen it.
    paths = _micropypath_values()
    assert len(paths) >= 5, f"found only {paths} - this guard cannot check its own premise"  # the two runners, JS, boot, bench
    for value in paths:
        assert "tests" not in value.split(":"), f"MICROPYPATH {value!r} now carries tests/, so this guard is obsolete"


def test_every_launch_site_of_the_runner_sets_a_twin_micropypath() -> None:
    assert launch_site_problems(REPO_ROOT) == []


def test_a_launch_site_outside_the_guard_or_a_tests_segment_is_caught(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "planted.py").write_text('cmd = [str(mp),\n    "digital_twin/run_generic_integration.py",\n]\n', encoding="utf-8")
    (tmp_path / "scripts" / "planted.sh").write_text('MICROPYPATH="src:tests:digital_twin:.frozen" "$micropython_bin" digital_twin/run_generic_integration.py\n', encoding="utf-8")
    assert launch_site_problems(tmp_path) == [
        "scripts/planted.py launches the twin runner with no twin MICROPYPATH of its own",
        "scripts/planted.sh: MICROPYPATH 'src:tests:digital_twin:.frozen' carries tests/",
    ]


def test_the_twin_machine_module_imports_under_cpython() -> None:
    # CPython tooling imports it: no MicroPython-only import at its module scope.
    done = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(TWIN)!r}); import machine"], capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 0, done.stderr


def test_every_twin_directory_a_twin_module_puts_on_sys_path_is_scanned() -> None:
    # A twin process imports from each such directory too: digital_twin/unixport/ holds the UDP shim.
    scanned = set(_twin_sources())
    inserted = {d for p in scanned for d in re.findall(r'sys\.path\.insert\(0, "(digital_twin/[^"]+)"\)', p.read_text(encoding="utf-8"))}
    assert inserted, "no twin module inserts a digital_twin subdirectory into sys.path - this premise check finds nothing to check"
    missing = sorted(str(p.relative_to(REPO_ROOT)) for d in inserted for p in (REPO_ROOT / d).glob("*.py") if p not in scanned)
    assert not missing, f"twin modules outside this file's scan: {missing}"


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


def launch_site_problems(root: Path) -> list[str]:
    # Every twin MICROPYPATH under the launch directories carries no tests/, and every file that spawns the runner sets one.
    problems = []
    for directory in _LAUNCH_DIRS:
        for path in sorted((root / directory).rglob("*")):
            if path.suffix not in _LAUNCH_SUFFIXES or "node_modules" in path.parts or path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            values = _twin_path_values(text)
            problems += [f"{path.relative_to(root)}: MICROPYPATH {v!r} carries tests/" for v in values if "tests" in v.split(":")]
            if _launches_the_runner(text) and not values:
                problems.append(f"{path.relative_to(root)} launches the twin runner with no twin MICROPYPATH of its own")
    return problems


def writer_problems(source: str) -> list[str]:
    # The moved NTP writer names its file only through the product's config_filename() and its named copy of the
    # store's own name, never as a literal path (it may import nothing from tests/).
    problems = []
    if "config_filename(cfg_dir, _NTP_STORE_NAME)" not in source:
        problems.append("the NTP config file is not named by config_filename(cfg_dir, _NTP_STORE_NAME)")
    if re.search(r"[\"']config_\w*", source):
        problems.append("the NTP config file name is spelled as a literal")
    return problems


def test_the_twins_ntp_writer_derives_its_file_name_from_the_product() -> None:
    writer = TWIN / "unixport" / "_offline_ntp_config.py"
    store_name = _module_constants(REPO_ROOT / "src" / "asy_ntp_client.py")["_NAME"]
    assert _module_constants(writer)["_NTP_STORE_NAME"] == store_name, store_name
    assert writer_problems(writer.read_text(encoding="utf-8")) == []
    planted = writer.read_text(encoding="utf-8").replace("config_filename(cfg_dir, _NTP_STORE_NAME)", 'cfg_dir + "config_NTP.cfg"')
    assert len(writer_problems(planted)) == 2


def test_every_persistent_twin_state_default_is_git_ignored() -> None:
    # A manual run writes these by default: each is a .gitignore entry, so `git status` stays clean after a run.
    ignored = {line.strip() for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    defaults = {value for name, value in _module_constants(TWIN / "launch.py").items() if name.endswith("_STATE_DEFAULT")}
    defaults.add(_module_constants(TWIN / "run_generic_integration.py")["_CONFIG_DIR_DEFAULT"])
    assert len(defaults) == 4, defaults
    assert sorted(str(d) for d in defaults if d not in ignored) == []
