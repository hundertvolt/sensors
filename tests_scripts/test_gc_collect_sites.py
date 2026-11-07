"""SPECIFICATION.md I.4(e)/(f.1)'s gc policy rule, through scripts/_check_gc_collect_sites.py: gc.collect(), a
gc.threshold() set, gc.disable() and gc.enable() only at the allowance table's sites, reached by any name bound to gc or
to one of them; a new site, a stale row or a tree the checker cannot read fails - the live tree included."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Callable

_ALLOWED_SRC = "import gc\n\n\nclass SystemService:\n    async def run_setups(self) -> None:\n        gc.collect()\n\n    async def start_tasks(self) -> None:\n        gc.collect()\n"
_RULE = " is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))"
_SCOPES = ("src", "tests", "digital_twin", "tests_hardware")


def _stamped(tree: Path, module: str = "x = 1\n") -> Path:
    # A generated tree as scripts/_generate_sensortask_modules.py leaves it: one device's three files, then the stamp
    # recording every input's sha256 and every output's name.
    out = tree / "build" / "generated_src"
    out.mkdir(parents=True)
    (tree / "devices" / "x.toml").write_text("[device]\n", encoding="utf-8")
    (tree / "ext").mkdir()
    (tree / "ext" / "e.py").write_text("e = 1\n", encoding="utf-8")
    (tree / "toolchain").mkdir()
    (tree / "toolchain" / "versions.toml").write_text("[micropython]\n", encoding="utf-8")
    for name, text in (("sensortask_x.py", module), ("sensortask_x_main.py", "import gc\ngc.threshold(32768)\n"), ("sensortask_x_main_noautostart.py", "import gc\ngc.threshold(32768)\n")):
        (out / name).write_text(text, encoding="utf-8")
    inputs = [*(tree / "devices").glob("*.toml"), *(tree / "buildgen").glob("*.py"), *(tree / "src").glob("*.py"), *(tree / "ext").glob("*.py"), tree / "toolchain" / "versions.toml"]
    stamp = {"inputs": {p.relative_to(tree).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}, "outputs": sorted(p.name for p in out.iterdir())}
    (out / ".inputs_stamp.json").write_text(json.dumps(stamp), encoding="utf-8")
    return out


@pytest.fixture(scope="module")
def checker(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_check_gc_collect_sites.py", "_check_gc_collect_sites")


@pytest.fixture
def generated(checker: ModuleType) -> "list[object]":
    # One stand-in device: its module carries no gc policy call, its boot entry the one threshold.
    return [
        checker.Generated("build/generated_src/sensortask_x.py", "import gc\nfree = gc.mem_free()\n", boot_entry=False),
        checker.Generated("build/generated_src/sensortask_x_main.py", "import gc\ngc.threshold(32768)\n", boot_entry=True),
    ]


@pytest.fixture
def table(checker: ModuleType) -> "dict[tuple[str, str, str], str]":
    # The stand-in tree's own allowance: the two src/ rows and one baseline row in each other scope.
    return {
        ("src/asy_system_service.py", "SystemService.run_setups", "collect"): "placement reset: the stand-in setup list",
        ("src/asy_system_service.py", "SystemService.start_tasks", "collect"): "placement reset: the stand-in task list",
        ("tests/_probe.py", "measure", "collect"): "baseline: the stand-in reading",
        ("tests/_runner.py", "run", "threshold"): "stage: the stand-in runner",
    }


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    # A stand-in repo holding only the allowed sites and one plain file per scope: every case adds one file, so the
    # verdict is attributable to it.
    for scope in (*_SCOPES, "buildgen", "devices"):
        (tmp_path / scope).mkdir()
    for scope in _SCOPES[1:]:
        (tmp_path / scope / "_plain.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC, encoding="utf-8")
    (tmp_path / "tests" / "_probe.py").write_text("import gc\n\n\ndef measure() -> int:\n    gc.collect()\n    return gc.mem_alloc()\n", encoding="utf-8")
    (tmp_path / "tests" / "_runner.py").write_text("import gc\n\n\ndef run(n: int) -> None:\n    gc.threshold(n)\n", encoding="utf-8")
    (tmp_path / "buildgen" / "codegen.py").write_text('lines.append("    sysfunct.run_setups(_collect_setups())")\n', encoding="utf-8")
    return tmp_path


def test_the_allowed_sites_alone_are_clean(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    result = checker.scan_tree(tree, generated=generated, allowed=table)
    assert (result.findings, result.errors) == ([], []), (result.findings, result.errors)


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("import gc\ngc.collect()\n", 2),
        ("import gc as g\n\ndef run():\n    g.collect()\n", 4),
        ("from gc import collect\n\ndef run():\n    collect()\n", 4),
        ("from gc import collect as c\nc()\n", 2),
        ("import gc\nsweep = gc.collect\nsweep()\n", 3),
        ("from gc import *\ncollect()\n", 2),
    ],
    ids=["module-level", "module-alias", "imported-function", "function-alias", "assigned-alias", "star-import"],
)
def test_a_collect_outside_the_table_is_reported_whatever_its_spelling(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", source: str, line: int) -> None:
    (tree / "src" / "asy_other.py").write_text(source, encoding="utf-8")
    findings = checker.scan_tree(tree, generated=generated, allowed=table).findings
    assert len(findings) == 1 and findings[0].startswith(f"src/asy_other.py:{line}: gc.collect() in "), findings
    assert findings[0].endswith(_RULE), findings


def test_a_collect_in_a_test_body_is_reported_by_its_function(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    # A collect after a test body keeps a later build green: it reads nothing, so no row allows it.
    (tree / "tests" / "test_x.py").write_text("import gc\n\n\ndef test_build() -> None:\n    build()\n    gc.collect()\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == [f"tests/test_x.py:6: gc.collect() in test_build{_RULE}"]


@pytest.mark.parametrize(
    ("source", "call"),
    [
        ("import gc\n\n\ndef test_x() -> None:\n    gc.threshold(32768)\n", "gc.threshold(...)"),
        ("import gc\ngc.disable()\n", "gc.disable()"),
        ("from gc import enable\nenable()\n", "gc.enable()"),
        ("import gc as g\nset_stage = g.threshold\nset_stage(-1)\n", "gc.threshold(...)"),
    ],
    ids=["threshold-in-a-test-body", "disable", "enable", "assigned-threshold"],
)
def test_a_threshold_set_disable_or_enable_outside_the_table_is_reported(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", source: str, call: str) -> None:
    (tree / "src" / "asy_other.py").write_text(source, encoding="utf-8")
    findings = checker.scan_tree(tree, generated=generated, allowed=table).findings
    assert len(findings) == 1 and findings[0].startswith("src/asy_other.py:") and f": {call} in " in findings[0], findings


def test_a_threshold_read_is_not_a_set(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    (tree / "tests" / "test_x.py").write_text("import gc\n\n\ndef test_x() -> None:\n    assert gc.threshold() == -1\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == []


def test_a_device_script_sets_its_own_stage_but_collects_only_at_a_row(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    # Each device script sets and reports its own stage (tests_scripts/test_device_script_gc_threshold.py pins that).
    script = tree / "tests_hardware" / "device_scripts" / "probe.py"
    script.parent.mkdir()
    script.write_text("import gc\n\ngc.threshold(-1)\ngc.collect()\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == [f"tests_hardware/device_scripts/probe.py:4: gc.collect() in <module>{_RULE}"]


@pytest.mark.parametrize(
    "source",
    [
        "import gc\n\ngc.threshold(-1)\n\n\ndef main():\n    fact('gc_threshold', gc.threshold())\n",
        "import gc\n\n\ndef main():\n    gc.threshold(32768)\n    stages.append(gc.threshold())\n",
        "import gc\n\n\ndef stage(n):\n    gc.threshold(n)\n    result = {'gc_threshold': gc.threshold()}\n",
    ],
    ids=["module-level-literal-before-any-def", "switch-read-back-at-once", "variable-read-back-at-once"],
)
def test_a_device_script_sets_its_stage_in_the_forms_the_tree_uses(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", source: str) -> None:
    # The stage at the script's start, or a switch whose next statement reads the value back for the report.
    script = tree / "tests_hardware" / "device_scripts" / "probe.py"
    script.parent.mkdir()
    script.write_text(source, encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == []


@pytest.mark.parametrize(
    ("name", "source", "line"),
    [
        ("_shared/probe.py", "import gc\ngc.threshold(-1)\n", 2),
        ("probe.py", "import gc\n\n\ndef main():\n    fact('gc_threshold', gc.threshold())\n    gc.threshold(4096)\n    measure()\n", 6),
        ("probe.py", "import gc\n\n\ndef main():\n    pass\n\n\ngc.threshold(-1)\n", 8),
        ("probe.py", "import gc\nN = -1\ngc.threshold(N)\n", 3),
    ],
    ids=["in-shared", "mid-script-unreported", "module-level-after-a-def", "module-level-not-a-literal"],
)
def test_a_device_script_stage_set_in_any_other_form_is_reported(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", name: str, source: str, line: int) -> None:
    script = tree / "tests_hardware" / "device_scripts" / name
    script.parent.mkdir(parents=True)
    script.write_text(source, encoding="utf-8")
    findings = checker.scan_tree(tree, generated=generated, allowed=table).findings
    assert len(findings) == 1 and findings[0].startswith(f"tests_hardware/device_scripts/{name}:{line}: gc.threshold(...) in "), findings


@pytest.mark.parametrize("separator", ["\x0c", "\x0b", "\x1c", "\x85", "\u2028", "\u2029"], ids=["form-feed", "vertical-tab", "file-separator", "next-line", "line-separator", "paragraph-separator"])
def test_a_character_ast_does_not_count_as_a_line_break_never_hides_a_site(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", separator: str) -> None:
    # str.splitlines() breaks at these, the parser does not: the lines the check marks are ast's own.
    (tree / "src" / "asy_other.py").write_text(f"import gc\nx = 1  # a{separator}b\n\n\ndef run():\n    gc.collect()\n", encoding="utf-8")
    (tree / "buildgen" / "codegen.py").write_text(f'# a{separator}b\nlines.append("    gc.collect()")\n', encoding="utf-8")
    findings = checker.scan_tree(tree, generated=generated, allowed=table).findings
    assert [f.split(" ", 1)[0] for f in findings] == ["src/asy_other.py:6:", "buildgen/codegen.py:2:"], findings


@pytest.mark.parametrize("newline", ["\r\n", "\r"], ids=["crlf", "cr"])
def test_a_module_with_other_line_endings_is_numbered_as_ast_numbers_it(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", newline: str) -> None:
    # A generated module is checked as its text stands, never through read_text()'s newline translation.
    module = checker.Generated("build/generated_src/sensortask_x.py", newline.join(["import gc", "", "", "def run():", "    gc.collect()", ""]), boot_entry=False)
    assert checker.scan_tree(tree, generated=[module, generated[1]], allowed=table).findings == [f"build/generated_src/sensortask_x.py:5: gc.collect() in run{_RULE}"]


def _dangling(path: Path) -> None:
    path.symlink_to(path.parent / "gone.py")


def _undecodable(path: Path) -> None:
    path.write_bytes(b"import gc\nx = '\xff'\n")


@pytest.mark.parametrize("make", [_undecodable, _dangling], ids=["not-utf-8", "broken-symlink"])
def test_a_file_that_cannot_be_read_is_an_error_naming_it(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", make: "Callable[[Path], None]", capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    for scope in (*_SCOPES, "buildgen"):
        make(tree / scope / "asy_unreadable.py")
    errors = checker.scan_tree(tree, generated=generated, allowed=table).errors
    assert [e.split(" (")[0] for e in errors] == [f"{scope}/asy_unreadable.py: cannot read" for scope in (*_SCOPES, "buildgen")], errors
    real = checker.scan_tree
    monkeypatch.setattr(checker, "scan_tree", lambda root: real(root, generated=generated, allowed=table))
    assert checker.main(["--root", str(tree)]) == 2
    assert "src/asy_unreadable.py: cannot read" in capsys.readouterr().err


def test_a_threshold_outside_the_device_scripts_is_not_theirs(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    (tree / "tests_hardware" / "harness_x.py").write_text("import gc\ngc.threshold(-1)\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == [f"tests_hardware/harness_x.py:2: gc.threshold(...) in <module>{_RULE}"]


def test_an_unrelated_collect_method_is_not_the_gc_call(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    (tree / "src" / "asy_other.py").write_text("def f(bag):\n    bag.collect()\n    bag.gc.collect()\n    bag.threshold(1)\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == []


def test_a_site_in_another_function_of_the_allowed_file_is_reported_by_its_qualified_name(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    (tree / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC + "\n    def supervise(self) -> None:\n        gc.collect()\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == [f"src/asy_system_service.py:12: gc.collect() in SystemService.supervise{_RULE}"]


def test_a_row_allows_only_its_own_call(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    # The runner's threshold row is no collect row: the call is part of the site.
    (tree / "tests" / "_runner.py").write_text("import gc\n\n\ndef run(n: int) -> None:\n    gc.threshold(n)\n    gc.collect()\n", encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == [f"tests/_runner.py:6: gc.collect() in run{_RULE}"]


def test_a_renamed_allowed_function_leaves_a_stale_row_that_is_reported(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    (tree / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC.replace("start_tasks", "start_all"), encoding="utf-8")
    findings = checker.scan_tree(tree, generated=generated, allowed=table).findings
    assert "src/asy_system_service.py: the allowed site SystemService.start_tasks holds no gc.collect() call - restore it or remove its row" in findings
    assert any("SystemService.start_all is not an allowed site" in f for f in findings), findings


def test_a_row_whose_file_is_gone_is_stale(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    (tree / "tests" / "_probe.py").unlink()
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == ["tests/_probe.py: the allowed site measure names a file that is gone - remove its row"]


@pytest.mark.parametrize("filename", ["codegen.py", "sub/leaf.py"])
def test_a_collect_anywhere_in_buildgen_s_text_is_reported(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", filename: str) -> None:
    # The generator emits none: a collect in an emitted string is a violation like a call.
    (tree / "buildgen" / filename).parent.mkdir(exist_ok=True)
    (tree / "buildgen" / filename).write_text('lines.append("    gc.collect()")\n', encoding="utf-8")
    assert checker.scan_tree(tree, generated=generated, allowed=table).findings == [f"buildgen/{filename}:1: gc.collect( in buildgen/'s text - the generated modules carry none (SPECIFICATION.md I.4(f.1))"]


def test_every_scope_is_searched_subdirectories_included(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    for scope in _SCOPES:
        (tree / scope / "sub").mkdir()
        (tree / scope / "sub" / "leaf.py").write_text("import gc\ngc.collect()\n", encoding="utf-8")
    assert [f.split(":")[0] for f in checker.scan_tree(tree, generated=generated, allowed=table).findings] == [f"{scope}/sub/leaf.py" for scope in _SCOPES]


_NO_SET = "sensortask_x_main.py: the boot entry sets no gc.threshold(<int literal>) at module level"


@pytest.mark.parametrize(
    ("module", "entry", "expected"),
    [
        ("import gc\ngc.collect()\n", "import gc\ngc.threshold(32768)\n", ["sensortask_x.py:2: gc.collect() in <module>"]),
        ("import gc\ngc.threshold(32768)\n", "import gc\ngc.threshold(32768)\n", ["sensortask_x.py:2: gc.threshold(...) in <module>"]),
        ("x = 1\n", "import gc\ngc.threshold(32768)\ngc.threshold(4096)\n", ["sensortask_x_main.py:3: gc.threshold(...) in <module>"]),
        ("x = 1\n", "import gc\ngc.threshold(32768)\ngc.disable()\n", ["sensortask_x_main.py:3: gc.disable() in <module>"]),
        ("x = 1\n", "import gc\n\n\ndef boot():\n    gc.threshold(32768)\n", ["sensortask_x_main.py:5: gc.threshold(...) in boot", _NO_SET]),
        ("x = 1\n", "import gc\nN = 32768\ngc.threshold(N)\n", ["sensortask_x_main.py:3: gc.threshold(...) in <module>", _NO_SET]),
        ("x = 1\n", "import gc\n", [_NO_SET]),
    ],
    ids=["module-collect", "module-threshold", "second-threshold", "boot-entry-disable", "threshold-in-a-function", "threshold-not-a-literal", "no-threshold"],
)
def test_the_generated_module_sets_nothing_and_each_boot_entry_sets_one_literal_threshold(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", module: str, entry: str, expected: "list[str]") -> None:
    generated = [
        checker.Generated("build/generated_src/sensortask_x.py", module, boot_entry=False),
        checker.Generated("build/generated_src/sensortask_x_main.py", entry, boot_entry=True),
    ]
    findings = checker.scan_tree(tree, generated=generated, allowed=table).findings
    assert len(findings) == len(expected) and all(f.startswith(f"build/generated_src/{e}") for f, e in zip(findings, expected, strict=True)), findings


def test_a_file_that_does_not_parse_is_an_error_never_a_skip(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]") -> None:
    for scope in _SCOPES:
        (tree / scope / "asy_broken.py").write_text("def (:\n", encoding="utf-8")
    errors = checker.scan_tree(tree, generated=generated, allowed=table).errors
    assert [e.split(" (")[0] for e in errors] == [f"{scope}/asy_broken.py:1: cannot parse" for scope in _SCOPES], errors


def test_a_root_with_no_source_to_scan_cannot_look(checker: ModuleType, tmp_path: Path) -> None:
    # A --root naming the wrong directory finds nothing to check: an error per scope and for the devices, never a pass.
    result = checker.scan_tree(tmp_path)
    expected = [f"{scope}/: no Python file to scan - the gc check could not look" for scope in _SCOPES]
    assert result.errors == [*expected, "devices/: no device to generate - the gc check could not look at a generated module"], result.errors


@pytest.mark.parametrize("names", [(), ("zz_test_fixture",)], ids=["no-toml", "only-a-reserved-fixture"])
def test_no_generated_module_is_an_error(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", names: "tuple[str, ...]") -> None:
    # A check that generates nothing reads nothing: as an empty src/ is, an error (exit 2), never a clean pass.
    for name in names:
        (tree / "devices" / f"{name}.toml").write_text("[device]\n", encoding="utf-8")
    result = checker.scan_tree(tree, allowed=table)
    assert result.errors == ["devices/: no device to generate - the gc check could not look at a generated module"], result.errors
    assert result.generated == 0


def test_a_device_that_does_not_generate_is_an_error(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]") -> None:
    (tree / "devices" / "broken.toml").write_text("not = = toml\n", encoding="utf-8")
    result = checker.scan_tree(tree, allowed=table)
    assert len(result.errors) == 1 and result.errors[0].startswith("devices/broken.toml: cannot generate ("), result.errors


def test_a_current_generated_tree_is_read_not_generated_again(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]") -> None:
    # The lint run's own generation, checked as written: this stand-in device would not generate, so a finding proves the read.
    _stamped(tree, "import gc\ngc.collect()\n")
    result = checker.scan_tree(tree, allowed=table)
    assert result.fresh and result.generated == 3 and result.errors == [], (result.fresh, result.generated, result.errors)
    assert result.findings == [f"build/generated_src/sensortask_x.py:2: gc.collect() in <module>{_RULE}"], result.findings


def _add_input(tree: Path) -> None:
    (tree / "ext" / "f.py").write_text("f = 1\n", encoding="utf-8")


def _edit_input(tree: Path) -> None:
    (tree / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC + "\n", encoding="utf-8")


def _garble_stamp(tree: Path) -> None:
    (tree / "build" / "generated_src" / ".inputs_stamp.json").write_text("{", encoding="utf-8")


def _remove_output(tree: Path) -> None:
    (tree / "build" / "generated_src" / "sensortask_x_main_noautostart.py").unlink()


def _remove_recorded(tree: Path) -> None:
    (tree / "toolchain" / "versions.toml").unlink()


@pytest.mark.parametrize("change", [_add_input, _edit_input, _garble_stamp, _remove_output, _remove_recorded], ids=["added-input", "edited-input", "unreadable-stamp", "missing-output", "removed-input"])
def test_a_stale_generated_tree_is_never_read(checker: ModuleType, tree: Path, change: "Callable[[Path], None]") -> None:
    _stamped(tree)
    assert checker.fresh_tree(tree) is not None
    change(tree)
    assert checker.fresh_tree(tree) is None


def test_a_reserved_fixture_toml_is_no_new_input(checker: ModuleType, tree: Path) -> None:
    _stamped(tree)
    (tree / "devices" / "zz_test_fixture.toml").write_text("[device]\n", encoding="utf-8")
    assert [source.rel for source in checker.fresh_tree(tree)] == [f"build/generated_src/sensortask_x{tail}" for tail in (".py", "_main.py", "_main_noautostart.py")]


def test_every_row_names_its_category(checker: ModuleType) -> None:
    # A row is allowed for one reason the rule names (SPECIFICATION.md I.4(e)/(f.1)); a reason outside them is no row.
    stray = {row: why for row, why in checker.ALLOWED.items() if why.split(":", 1)[0] not in checker.CATEGORIES}
    assert not stray, stray
    assert all(call in ("collect", "threshold") for _path, _owner, call in checker.ALLOWED), "disable() and enable() are allowed nowhere"


def test_the_live_tree_passes_the_command_with_its_generated_modules(repo_root: Path) -> None:
    # The command lint.sh runs: exit 0 on the real tree, every scope and every derived device's module and entries checked.
    done = subprocess.run([sys.executable, str(repo_root / "scripts" / "_check_gc_collect_sites.py")], cwd=repo_root, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "generated modules checked: " in done.stdout and "generated modules checked: 0" not in done.stdout, done.stdout
    assert "not checked yet" not in done.stdout, done.stdout


@pytest.mark.parametrize(("planted", "code"), [("import gc\ngc.collect()\n", 1), ("def (:\n", 2)], ids=["finding", "unparsable"])
def test_the_command_exits_1_on_a_finding_and_2_when_it_cannot_look(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", generated: "list[object]", planted: str, code: int, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    real = checker.scan_tree
    monkeypatch.setattr(checker, "scan_tree", lambda root: real(root, generated=generated, allowed=table))
    (tree / "src" / "asy_other.py").write_text(planted, encoding="utf-8")
    assert checker.main(["--root", str(tree)]) == code
    assert "src/asy_other.py:" in capsys.readouterr().err


def test_the_command_exits_2_when_no_device_generates(checker: ModuleType, tree: Path, table: "dict[tuple[str, str, str], str]", capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    real = checker.scan_tree
    monkeypatch.setattr(checker, "scan_tree", lambda root: real(root, allowed=table))
    assert checker.main(["--root", str(tree)]) == 2
    assert "devices/: no device to generate" in capsys.readouterr().err
