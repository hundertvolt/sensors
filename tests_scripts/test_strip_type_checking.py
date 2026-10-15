"""Tests scripts/_strip_type_checking.py's line-preserving `TYPE_CHECKING` strip in isolation, independent of
build_firmware.py's wiring (test_build_firmware.py): every form, every real src/ module, the error it raises."""

import ast
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_GUARD = "try:\n    from typing import TYPE_CHECKING\nexcept ImportError:\n    TYPE_CHECKING = False\n"


@pytest.fixture(scope="session")
def strip_module(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_strip_type_checking.py", "_strip_type_checking")


def _loads(source: "str | ast.Module") -> "list[int]":
    # The lines on which the name is still read (a Name or an attribute), the thing the board cannot do.
    found = []
    for node in ast.walk(ast.parse(source) if isinstance(source, str) else source):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        if name == "TYPE_CHECKING" and isinstance(getattr(node, "ctx", None), ast.Load):
            found.append(getattr(node, "lineno", 0))
    return found


def _run(source: str, **names: object) -> "dict[str, object]":
    # Executes stripped output with TYPE_CHECKING undefined, as on the board once the guard is gone.
    namespace: dict[str, object] = dict(names)
    exec(compile(source, "<stripped>", "exec"), namespace)  # noqa: S102 - the test's own fixture text
    return namespace


def test_no_type_checking_pattern_returns_source_byte_for_byte_unchanged(strip_module: ModuleType) -> None:
    source = "import os\n\n\ndef f(x: int) -> int:\n    return x + 1\n"
    assert strip_module.strip_type_checking_blocks(source) is source


def test_strips_bare_type_checking_block_and_its_import_guard_line_for_line(strip_module: ModuleType) -> None:
    source = "import asyncio\n\n" + _GUARD + "\nif TYPE_CHECKING:\n    from typing import Any\n\n    Alias = dict[str, Any]\n\n\ndef f() -> None:\n    pass\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert not _loads(output)
    assert output.count("\n") == source.count("\n")
    assert output.splitlines()[:2] == ["import asyncio", ""]
    assert output.splitlines()[-2:] == ["def f() -> None:", "    pass"]
    assert "Alias" not in output
    assert not output.splitlines()[2].strip(), "the guard's first line was not blanked"


def test_strips_module_attribute_type_checking_test(strip_module: ModuleType) -> None:
    source = "import typing\n\nif typing.TYPE_CHECKING:\n    X = 1\n\nY = 2\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert output.splitlines() == ["import typing", "", "", "", "", "Y = 2"]


def test_a_compound_condition_reads_false_in_place(strip_module: ModuleType) -> None:
    # The body stays, its test reads False where the name stood; the guard goes, so nothing reads the name.
    source = _GUARD + "if TYPE_CHECKING and extra_check():\n    Z = 1\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert output.splitlines()[4] == "if False and extra_check():"
    assert not _loads(output)
    assert "Z" not in _run(output, extra_check=lambda: True)


def test_an_if_else_keeps_its_else_branch_live(strip_module: ModuleType) -> None:
    source = _GUARD + "if TYPE_CHECKING:\n    W = 1\nelse:\n    W = 2\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert output.splitlines()[4:] == ["if False:", "    W = 1", "else:", "    W = 2"]
    assert not _loads(output)
    assert _run(output)["W"] == 2


def test_an_if_elif_keeps_the_elif_chain(strip_module: ModuleType) -> None:
    source = "if TYPE_CHECKING:\n    W = 1\nelif X:\n    W = 2\nelse:\n    W = 3\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert output.splitlines()[0] == "if False:"
    assert _run(output, X=True)["W"] == 2
    assert _run(output, X=False)["W"] == 3


def test_an_elif_type_checking_reads_false_in_place(strip_module: ModuleType) -> None:
    output = strip_module.strip_type_checking_blocks("if X:\n    W = 1\nelif TYPE_CHECKING:\n    W = 2\n")
    assert output.splitlines() == ["if X:", "    W = 1", "elif False:", "    W = 2"]


def test_any_other_read_becomes_false(strip_module: ModuleType) -> None:
    output = strip_module.strip_type_checking_blocks("x = TYPE_CHECKING or y\nz = not typing.TYPE_CHECKING  # kept comment\n")
    assert output == "x = False or y\nz = not False  # kept comment\n"


def test_a_read_after_a_multibyte_character_is_replaced_at_its_own_column(strip_module: ModuleType) -> None:
    # ast's column offsets count UTF-8 bytes, so a character before the name must not shift the edit.
    output = strip_module.strip_type_checking_blocks('s = "\u00b5s"; y = TYPE_CHECKING\n')
    assert output == 's = "\u00b5s"; y = False\n'


def test_a_suite_left_empty_gets_pass(strip_module: ModuleType) -> None:
    source = "def f():\n    if TYPE_CHECKING:\n        import x\n\n\nclass C:\n    if TYPE_CHECKING:\n        y: int\n    if TYPE_CHECKING:\n        z: int\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert output.splitlines() == ["def f():", "    pass", "", "", "", "class C:", "    pass", "", "", ""]
    ast.parse(output)


def test_a_guard_inside_a_function_leaves_pass_behind(strip_module: ModuleType) -> None:
    source = "def f():\n" + "".join(f"    {line}\n" for line in _GUARD.splitlines())
    output = strip_module.strip_type_checking_blocks(source)
    assert output.splitlines() == ["def f():", "    pass", "", "", ""]


def test_leaves_unrelated_try_except_importerror_untouched(strip_module: ModuleType) -> None:
    source = "try:\n    import ujson as json\nexcept ImportError:\n    import json\n"
    assert strip_module.strip_type_checking_blocks(source) is source


def test_strips_multiple_type_checking_blocks_in_one_file(strip_module: ModuleType) -> None:
    source = _GUARD + "\nif TYPE_CHECKING:\n    A = 1\n\ndef f():\n    pass\n\nif TYPE_CHECKING:\n    B = 2\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert "A = 1" not in output
    assert "B = 2" not in output
    assert "def f():" in output.splitlines()
    assert output.count("\n") == source.count("\n")


def test_a_read_the_strip_cannot_place_raises_naming_path_and_line(strip_module: ModuleType) -> None:
    # An attribute split across lines has no one-line span to replace; the re-parse check refuses the residue.
    source = "import typing\nx = (typing\n     .TYPE_CHECKING)\n"
    with pytest.raises(strip_module.StripError, match=r"^src/odd\.py:2: TYPE_CHECKING still read after stripping$"):
        strip_module.strip_type_checking_blocks(source, "src/odd.py")


def test_a_source_that_does_not_parse_raises_naming_path_and_line(strip_module: ModuleType) -> None:
    with pytest.raises(strip_module.StripError, match=r"^src/broken\.py:2: "):
        strip_module.strip_type_checking_blocks("x = 1\ndef (:\n", "src/broken.py")


def _guarded_lines(tree: ast.Module) -> "set[int]":
    # Every line of each bare `if TYPE_CHECKING:` statement and of each import guard: the lines a strip may blank.
    lines: set[int] = set()
    for node in ast.walk(tree):
        bare = isinstance(node, ast.If) and not node.orelse and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
        guard = isinstance(node, ast.Try) and any(isinstance(s, ast.ImportFrom) and s.module == "typing" for s in node.body)
        if (bare or guard) and isinstance(node, ast.stmt):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


@pytest.fixture(scope="module")
def stripped_src(strip_module: ModuleType, repo_root: Path) -> "dict[str, tuple[str, str]]":
    # Each real src/ module naming TYPE_CHECKING, as (source, stripped copy), stripped once for both cases below.
    sources = {p.name: p.read_text(encoding="utf-8") for p in sorted((repo_root / "src").glob("*.py"))}
    return {name: (text, strip_module.strip_type_checking_blocks(text, f"src/{name}")) for name, text in sources.items() if "TYPE_CHECKING" in text}


@pytest.fixture(scope="module")
def stripped_trees(stripped_src: "dict[str, tuple[str, str]]") -> "dict[str, tuple[ast.Module, ast.Module]]":
    # The same pairs parsed once, source and stripped copy, for both cases below.
    return {name: (ast.parse(text), ast.parse(output)) for name, (text, output) in stripped_src.items()}


def test_every_real_src_module_keeps_its_line_numbers_and_every_untouched_line(stripped_src: "dict[str, tuple[str, str]]", stripped_trees: "dict[str, tuple[ast.Module, ast.Module]]") -> None:
    # The shipped form: a field traceback's line numbers equal src/'s, and only the guarded lines change.
    assert stripped_src, "sanity: at least one real src/ file should use this pattern"
    for name, (text, output) in stripped_src.items():
        before, after = text.split("\n"), output.split("\n")
        assert len(after) == len(before), name
        tree, stripped = stripped_trees[name]
        touched, reads = _guarded_lines(tree), set(_loads(tree))
        for number, (old, new) in enumerate(zip(before, after, strict=True), start=1):
            if number in touched:
                assert new.strip() in ("", "pass"), f"src/{name}:{number}: {new!r}"
            elif number in reads:  # an if/else keeps both branches, its test reading False
                assert new == old.replace("TYPE_CHECKING", "False"), f"src/{name}:{number}: {old!r} -> {new!r}"
            else:
                assert new == old, f"src/{name}:{number} changed: {old!r} -> {new!r}"
        assert not _loads(stripped), f"src/{name}: a load is left at {_loads(stripped)}"


def test_every_src_guard_is_the_plain_two_line_form_and_is_removed(strip_module: ModuleType, stripped_trees: "dict[str, tuple[ast.Module, ast.Module]]") -> None:
    # D.6's guard form, the one the strip recognises: any other body would leave the name defined nowhere.
    for name, (tree, stripped) in stripped_trees.items():
        guards = [n for n in ast.walk(tree) if isinstance(n, ast.Try) and any(isinstance(s, ast.ImportFrom) and s.module == "typing" and any(a.name == "TYPE_CHECKING" for a in s.names) for s in n.body)]
        for guard in guards:
            assert strip_module._is_type_checking_import_guard(guard), f"{name}:{guard.lineno}: not the plain D.6 guard"
        assert not [n for n in ast.walk(stripped) if isinstance(n, ast.ImportFrom) and any(a.name == "TYPE_CHECKING" for a in n.names)], name
