"""Pins that nothing a twin PROCESS runs needs tests/ importable, and that every twin launch takes its MICROPYPATH from
scripts/micropypath.toml's twin: _http_client.HttpResponse.json() imports tests/_strict_json lazily, and the twin's path
carries no tests/ - so a second caller inside digital_twin/ would raise ImportError only on that path, at runtime."""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
TWIN = REPO_ROOT / "digital_twin"
_LAYOUT_FILE = REPO_ROOT / "scripts" / "micropypath.toml"
_LAUNCH_DIRS = ("scripts", "tests_scripts", "tests_js", "tests_hardware")
_LAUNCH_SUFFIXES = (".py", ".sh", ".js", ".mjs")
_READER_SUFFIXES = (".py", ".js", ".mjs")
# A quoted run of colon-separated path segments: a MICROPYPATH value, in any of the four forms (Python, f-string, shell,
# JS template), when it holds both the twin's directory and the frozen-module sentinel.
_PATH_VALUE = re.compile(r"[\"'`]((?:[^\"'`\s:]+:)+[^\"'`\s:]+)[\"'`]")
# A twin runner as a process argument: an array element or a named constant on its own line, or a shell word after the
# interpreter.
_SPAWN = re.compile(r'^(?:\w+\s*=\s*)?["\']digital_twin/run_(?:generic_integration|device_script)\.py["\'],?$|micropython_bin\}?"?\s+digital_twin/run_(?:generic_integration|device_script)\.py')
# The layout file's twin read directly (tomllib's ["twin"], a JS regex over its twin line), or through the shell reader.
_DIRECT_READ = re.compile(r"[\"']twin[\"']|\^twin = ")
_SHELL_READ = re.compile(r"\bmicropypath[\"']?,?\s*[\"']?twin\b")
# A value derived from the read layout (a replaced, split or rejoined segment), which says why beside it.
_DERIVED = re.compile(r"(?i)micropypath\w*(?:\(\))?\s*\.\s*(?:replace|split)\(")

_LAZY_MODULE = "_strict_json"
_LAZY_OWNER = "_http_client.py"  # the one file allowed to reach into tests/, and only from .json()
_JSON_METHOD = "json"


def _derived_lines(text: str) -> list[int]:
    # The lines deriving a MICROPYPATH from the read layout with no comment on them or on the line above.
    lines = text.splitlines()
    found = []
    for number, line in enumerate(lines, 1):
        code = line.strip()
        if code.startswith(("#", "//")) or not _DERIVED.search(code):
            continue
        above = lines[number - 2].strip() if number > 1 else ""
        if not (" #" in code or " //" in code or above.startswith(("#", "//"))):
            found.append(number)
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


def _launch_files(root: Path) -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for directory in _LAUNCH_DIRS
        for path in sorted((root / directory).rglob("*"))
        if path.suffix in _LAUNCH_SUFFIXES and "node_modules" not in path.parts and path.name != Path(__file__).name
    ]


def _launches_a_twin_runner(text: str) -> bool:
    lines = (line.strip() for line in text.splitlines())
    return any(_SPAWN.search(line) for line in lines if not line.startswith(("#", "//")))


def _layouts() -> dict[str, str]:
    layouts = tomllib.loads(_LAYOUT_FILE.read_text(encoding="utf-8"))
    assert all(isinstance(value, str) for value in layouts.values()), layouts
    return {str(name): str(value) for name, value in layouts.items()}


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


def _readers(root: Path) -> set[tuple[str, str]]:
    # (stem, language) of every non-test module that reads the layout file's twin itself: a launch site may import one.
    return {
        (path.stem, "js" if path.suffix in (".js", ".mjs") else "py")
        for path, text in _launch_files(root)
        if path.suffix in _READER_SUFFIXES and not path.name.startswith("test_") and "micropypath.toml" in text and _DIRECT_READ.search(text)
    }


def _reads_the_twin_layout(path: Path, text: str, readers: set[tuple[str, str]]) -> bool:
    if _SHELL_READ.search(text) or ("micropypath.toml" in text and _DIRECT_READ.search(text)):
        return True
    language = "js" if path.suffix in (".js", ".mjs") else "py"
    return any(re.search(rf"(?<![\w-]){re.escape(stem)}\b", text) for stem, lang in readers if lang == language and stem != path.stem)


def _twin_literals(text: str) -> list[tuple[int, str]]:
    return [(number, m.group(1)) for number, line in enumerate(text.splitlines(), 1) for m in _PATH_VALUE.finditer(line) if {"digital_twin", ".frozen"} <= set(m.group(1).split(":"))]


def _twin_sources() -> list[Path]:
    return sorted(TWIN.rglob("*.py"))


def test_the_layout_file_holds_the_unit_and_the_twin_layout() -> None:
    layouts = _layouts()
    assert sorted(layouts) == ["twin", "unit"], f"{_LAYOUT_FILE.name} holds {sorted(layouts)}"
    unit, twin = layouts["unit"].split(":"), layouts["twin"].split(":")
    assert "tests" in unit and not {"ext", "digital_twin"} & set(unit), f"unit {layouts['unit']!r}: tests/ on it, ext/ and digital_twin/ off it"
    assert {"digital_twin", "ext"} <= set(twin) and "tests" not in twin, f"twin {layouts['twin']!r}: digital_twin/ and ext/ on it, tests/ off it"
    assert unit[-1] == twin[-1] == ".frozen", "both end in .frozen, the interpreter's frozen-module token"


def test_the_twin_layout_still_carries_no_tests_directory_and_the_guard_sees_its_launch_sites() -> None:
    # The premise of everything below. If tests/ is ever added to it, this guard is obsolete rather
    # than failing - delete it then, do not widen it.
    assert "tests" not in _layouts()["twin"].split(":"), "the twin layout now carries tests/, so this guard is obsolete"
    sites = [path.relative_to(REPO_ROOT).as_posix() for path, text in _launch_files(REPO_ROOT) if _launches_a_twin_runner(text)]
    assert len(sites) >= 5, f"found only {sites} - this guard cannot check its own premise"  # the runners, the JS frame, the smoke, the boot test, the bench


def test_every_twin_launch_reads_the_layout_file() -> None:
    assert launch_site_problems(REPO_ROOT) == []


def test_a_literal_an_unread_launch_and_an_unexplained_derivation_are_caught(tmp_path: Path) -> None:
    plants = {
        "scripts/planted.py": 'cmd = [str(mp),\n    "digital_twin/run_generic_integration.py",\n]\n',
        "scripts/planted.sh": 'MICROPYPATH="src:tests:digital_twin:.frozen" "$micropython_bin" digital_twin/run_generic_integration.py\n',
        "scripts/reads.sh": 'MICROPYPATH="$(scripts/_unix_port.sh micropypath twin)" "$micropython_bin" digital_twin/run_generic_integration.py\n',
        "scripts/_layout.py": 'TWIN = tomllib.loads((ROOT / "scripts" / "micropypath.toml").read_text())["twin"]\n',
        "tests_hardware/board.py": 'from scripts._layout import TWIN\nRUNNER = "digital_twin/run_device_script.py"\n',
        "tests_js/_layout.js": 'const TWIN = /^twin = "([^"]+)"$/mu.exec(readFileSync("scripts/micropypath.toml", "utf8"));\n',
        "tests_js/derives.js": 'import { twinMicropypath } from "./_layout.js";\nconst p = twinMicropypath().replace("frozen_modules", site);\nconst argv = [\n    "digital_twin/run_generic_integration.py",\n];\n',
        "tests_js/explains.js": 'import { twinMicropypath } from "./_layout.js";\n// the device\'s own site in place of the frozen one\nconst p = twinMicropypath().replace("frozen_modules", site);\nconst argv = [\n    "digital_twin/run_generic_integration.py",\n];\n',
    }
    for name, text in plants.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    assert launch_site_problems(tmp_path) == [
        "scripts/planted.py launches a twin runner without reading scripts/micropypath.toml's twin",
        "scripts/planted.sh:1: MICROPYPATH 'src:tests:digital_twin:.frozen' carries tests/",
        "scripts/planted.sh:1: the twin MICROPYPATH literal 'src:tests:digital_twin:.frozen' - read scripts/micropypath.toml's twin instead",
        "scripts/planted.sh launches a twin runner without reading scripts/micropypath.toml's twin",
        "tests_js/derives.js:2: derives a MICROPYPATH from the twin layout with no reason beside it",
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
    # No twin MICROPYPATH literal under the launch directories, every file that starts a twin runner reads the layout
    # file's twin (itself or through a module that does), and every value it derives from it says why.
    problems = []
    readers = _readers(root)
    for path, text in _launch_files(root):
        rel = path.relative_to(root).as_posix()
        for line, value in _twin_literals(text):
            if "tests" in value.split(":"):
                problems.append(f"{rel}:{line}: MICROPYPATH {value!r} carries tests/")
            problems.append(f"{rel}:{line}: the twin MICROPYPATH literal {value!r} - read scripts/micropypath.toml's twin instead")
        if _launches_a_twin_runner(text):
            if not _reads_the_twin_layout(path, text, readers):
                problems.append(f"{rel} launches a twin runner without reading scripts/micropypath.toml's twin")
            problems += [f"{rel}:{line}: derives a MICROPYPATH from the twin layout with no reason beside it" for line in _derived_lines(text)]
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
