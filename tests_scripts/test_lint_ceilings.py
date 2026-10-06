"""Every ruff ceiling in pyproject.toml sits at its measured maximum and only goes down; max-args is 8
with an exact set of external-API mirrors exempted per file, and every src/ constructor taking `log`
ends with the fixed tail (SPECIFICATION.md D.10, C.2). The ESLint half: tests_js/lint-ceilings.test.js."""

import ast
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import tomllib

if TYPE_CHECKING:
    from collections.abc import Iterator

_SCOPES = ("src", "tests", "digital_twin", "buildgen", "toolchain", "scripts", "tests_scripts", "tests_hardware")


@dataclass(frozen=True)
class _Ceiling:
    rule: str
    section: str
    option: str


_CEILINGS = (
    _Ceiling("C901", "mccabe", "max-complexity"),
    _Ceiling("PLR0911", "pylint", "max-returns"),
    _Ceiling("PLR0912", "pylint", "max-branches"),
    _Ceiling("PLR0913", "pylint", "max-args"),
    _Ceiling("PLR0915", "pylint", "max-statements"),
)

# Each mirrors an external API's parameter list (the pyproject.toml PLR0913 entries give the reasons).
_MAX_ARGS_EXEMPT = frozenset({
    ("src/asy_isl29125_driver.py", "ISL29125_I2C.configure"),
    ("src/asy_uart_driver.py", "UART.__init__"),
    ("src/asy_uart_driver.py", "UART.init"),
    ("digital_twin/machine.py", "SPI.__init__"),
    ("digital_twin/machine.py", "UART.__init__"),
    ("tests/machine.py", "SPI.__init__"),
    ("tests/machine.py", "UART.__init__"),
})

_TAIL = ("max_module_error", "name_ext", "cfg_path")
# The classes whose test-only `logger=` reach-through stays for now (C.7): no other constructor takes one.
_LOGGER_ALLOWED = frozenset({
    ("src/asy_uart_comm.py", "UART_Comm"),
    ("src/asy_uart_link_driver.py", "UartLinkExerciser"),
    ("src/base_classes.py", "SensorReader"),
})

# ruff's default dummy-variable-rgx: a parameter matching it is not counted by PLR0913.
_DUMMY = re.compile(r"^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$")
_UNCOUNTED_DECORATORS = frozenset({"overload", "override"})


def _ruff() -> str:
    found = shutil.which("ruff") or str(Path(sys.executable).with_name("ruff"))
    assert Path(found).is_file(), "ruff is not installed - run `uv sync` (it is a pinned dev dependency)"
    return found


def _lint_tables(repo_root: Path) -> "dict[str, dict[str, object]]":
    """pyproject.toml's [tool.ruff.lint.*] tables by name."""
    with (repo_root / "pyproject.toml").open("rb") as f:
        lint = tomllib.load(f)["tool"]["ruff"]["lint"]
    return {name: table for name, table in lint.items() if isinstance(table, dict)}


def _configured(repo_root: Path, ceiling: _Ceiling) -> int:
    value = _lint_tables(repo_root)[ceiling.section][ceiling.option]
    assert isinstance(value, int), f"pyproject.toml's {ceiling.option} is not an integer: {value!r}"
    return value


def _findings(repo_root: Path, ceiling: _Ceiling, value: int, paths: "tuple[str, ...]" = _SCOPES) -> "list[str]":
    """Ruff's findings for one ceiling at `value` - per-file ignores applied, no cache written."""
    cmd = [_ruff(), "check", "--no-cache", "--quiet", "--output-format", "concise", "--select", ceiling.rule,
           "--config", f"lint.{ceiling.section}.{ceiling.option}={value}", *paths]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode in {0, 1}, f"ruff itself failed: {result.stderr}"
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    # Anything else (a file ruff could not parse) would hide that file's functions from the probe.
    foreign = [line for line in lines if f" {ceiling.rule} " not in line]
    assert not foreign, f"ruff reported more than {ceiling.rule}: {foreign}"
    return lines


def _ceiling_problem(repo_root: Path, ceiling: _Ceiling, value: int) -> "str | None":
    """Why `value` is not the measured maximum for this ceiling, or None when it is."""
    at_value = _findings(repo_root, ceiling, value)
    if at_value:
        return f"{ceiling.option} = {value} is exceeded: {at_value}"
    if not _findings(repo_root, ceiling, value - 1):
        return f"{ceiling.option} = {value} sits above the measured maximum: lower it (nothing reaches {value})"
    return None


def _linted_files(repo_root: Path, paths: "tuple[str, ...]" = _SCOPES) -> "list[Path]":
    """The exact file set ruff checks (its own exclusions and .gitignore applied)."""
    result = subprocess.run([_ruff(), "check", "--no-cache", "--show-files", *paths], cwd=repo_root, capture_output=True, text=True, check=True)
    root = repo_root.resolve()
    return sorted(Path(line.strip()).resolve().relative_to(root) for line in result.stdout.splitlines() if line.strip().endswith(".py"))


def _decorator_names(node: "ast.FunctionDef | ast.AsyncFunctionDef") -> "set[str]":
    names = set()
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute):
            names.add(target.attr)
        elif isinstance(target, ast.Name):
            names.add(target.id)
    return names


def _functions(tree: ast.Module) -> "Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef, bool]]":
    """(qualified name, node, is_method) for every function, nested ones included."""
    def walk(node: ast.AST, prefix: str, *, in_class: bool) -> "Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef, bool]]":
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield f"{prefix}{child.name}", child, in_class
                yield from walk(child, f"{prefix}{child.name}.", in_class=False)
            elif isinstance(child, ast.ClassDef):
                yield from walk(child, f"{prefix}{child.name}.", in_class=True)
            else:
                yield from walk(child, prefix, in_class=in_class)
    yield from walk(tree, "", in_class=False)


def _arg_count(node: "ast.FunctionDef | ast.AsyncFunctionDef", *, is_method: bool) -> "int | None":
    """PLR0913's count: non-variadic parameters, dummies excluded, self/cls excluded; None = not counted."""
    decorators = _decorator_names(node)
    if decorators & _UNCOUNTED_DECORATORS:
        return None
    params = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    count = sum(1 for p in params if not _DUMMY.match(p.arg))
    if is_method and "staticmethod" not in decorators and params and not _DUMMY.match(params[0].arg):
        count -= 1
    return count


def _over_max_args(repo_root: Path, files: "list[Path]", limit: int) -> "set[tuple[str, str]]":
    over = set()
    for path in files:
        tree = ast.parse((repo_root / path).read_text(), filename=str(path))
        for name, node, is_method in _functions(tree):
            count = _arg_count(node, is_method=is_method)
            if count is not None and count > limit:
                over.add((path.as_posix(), name))
    return over


def _tail_problem(params: "list[str]", *, logger_allowed: bool) -> "str | None":
    """Why a constructor's parameter list breaks `(…[, max_module_error][, name_ext][, cfg_path], log[, logger])`."""
    rest = list(params)
    if rest and rest[-1] == "logger":
        if not logger_allowed:
            return "takes logger=, which only the classes C.7 names keep"
        rest.pop()
    if not rest or rest[-1] != "log":
        return "log is not its last parameter (logger= aside)"
    rest.pop()
    run: list[str] = []
    while rest and rest[-1] in _TAIL:
        run.insert(0, rest.pop())
    if any(p in _TAIL for p in rest):
        return f"a tail parameter is followed by a non-tail one: {params}"
    if run != [t for t in _TAIL if t in run]:
        return f"the tail is not in the order {_TAIL}: {run}"
    return None


def _constructor_tail_problems(repo_root: Path, files: "list[Path]") -> "list[str]":
    problems, checked = [], 0
    for path in files:
        tree = ast.parse((repo_root / path).read_text(), filename=str(path))
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for init in (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"):
                params = [p.arg for p in [*init.args.posonlyargs, *init.args.args, *init.args.kwonlyargs]][1:]
                if "log" not in params:
                    continue
                checked += 1
                problem = _tail_problem(params, logger_allowed=(path.as_posix(), cls.name) in _LOGGER_ALLOWED)
                if problem is not None:
                    problems.append(f"{path.as_posix()} {cls.name}.__init__: {problem}")
    if not checked:
        problems.append("no constructor takes log= - the check measures nothing")
    return problems


@pytest.mark.parametrize("ceiling", _CEILINGS, ids=[c.option for c in _CEILINGS])
def test_each_ruff_ceiling_sits_at_its_measured_maximum(repo_root: Path, ceiling: _Ceiling) -> None:
    problem = _ceiling_problem(repo_root, ceiling, _configured(repo_root, ceiling))
    assert problem is None, problem


def test_max_args_is_eight(repo_root: Path) -> None:
    assert _configured(repo_root, _Ceiling("PLR0913", "pylint", "max-args")) == 8  # owner, 2026-09-26: "8 is fine"


def test_every_function_above_max_args_is_exactly_the_exempt_set(repo_root: Path) -> None:
    over = _over_max_args(repo_root, _linted_files(repo_root), 8)
    assert over == _MAX_ARGS_EXEMPT, f"not exempt: {sorted(over - _MAX_ARGS_EXEMPT)}; exempt but no longer above 8: {sorted(_MAX_ARGS_EXEMPT - over)}"


def test_the_plr0913_per_file_entries_name_exactly_the_exempt_files(repo_root: Path) -> None:
    per_file = _lint_tables(repo_root)["per-file-ignores"]
    entries = {path for path, rules in per_file.items() if isinstance(rules, list) and "PLR0913" in rules}
    assert entries == {path for path, _ in _MAX_ARGS_EXEMPT}


def test_the_ast_count_agrees_with_ruff_on_every_file_without_an_exemption(repo_root: Path) -> None:
    # A lower probe limit gives both counters real work; the exempt files are hidden from ruff by their per-file entries.
    exempt_files = {path for path, _ in _MAX_ARGS_EXEMPT}
    files = [f for f in _linted_files(repo_root) if f.as_posix() not in exempt_files]
    ruff_sites = {line.split(":")[0] + ":" + line.split(":")[1] for line in _findings(repo_root, _CEILINGS[3], 4)}
    ast_sites = set()
    for path in files:
        tree = ast.parse((repo_root / path).read_text(), filename=str(path))
        for _, node, is_method in _functions(tree):
            count = _arg_count(node, is_method=is_method)
            if count is not None and count > 4:
                ast_sites.add(f"{path.as_posix()}:{node.lineno}")
    assert ruff_sites, "the probe found nothing at max-args 4 - it no longer measures anything"
    assert ast_sites == ruff_sites, f"only ruff: {sorted(ruff_sites - ast_sites)[:10]}; only the AST walk: {sorted(ast_sites - ruff_sites)[:10]}"


def test_every_src_constructor_with_a_log_parameter_ends_with_the_fixed_tail(repo_root: Path) -> None:
    assert _constructor_tail_problems(repo_root, _linted_files(repo_root, ("src",))) == []


def test_a_ceiling_raised_by_one_fails_the_check(repo_root: Path) -> None:
    ceiling = _Ceiling("PLR0911", "pylint", "max-returns")
    problem = _ceiling_problem(repo_root, ceiling, _configured(repo_root, ceiling) + 1)
    assert problem is not None
    assert "above the measured maximum" in problem


def test_a_ninth_parameter_on_a_non_exempt_function_fails_the_check(repo_root: Path, tmp_path: Path) -> None:
    planted = tmp_path / "planted.py"
    planted.write_text("class C:\n    def __init__(self, a, b, c, d, e, f, g, h, i):\n        pass\n\n\ndef ok(a, b, c, d, e, f, g, _h, i):\n    pass\n")
    over = _over_max_args(tmp_path, [Path("planted.py")], 8)
    assert over == {("planted.py", "C.__init__")}
    assert len(_findings(repo_root, _CEILINGS[3], 8, (str(planted),))) == 1


@pytest.mark.parametrize(
    ("params", "owner", "fragment"),
    [
        (["i2c", "max_module_error", "name_ext", "cfg_path", "log"], ("src/x.py", "X"), None),
        (["uart", "role", "name", "log", "logger"], ("src/asy_uart_comm.py", "UART_Comm"), None),
        (["i2c", "name_ext", "max_module_error", "log"], ("src/x.py", "X"), "order"),
        (["i2c", "log", "max_module_error"], ("src/x.py", "X"), "last parameter"),
        (["i2c", "cfg_path", "trigger_sec", "log"], ("src/x.py", "X"), "followed by a non-tail one"),
        (["i2c", "log", "logger"], ("src/x.py", "X"), "only the classes"),
    ],
)
def test_the_tail_check_accepts_the_tail_and_names_each_break(params: "list[str]", owner: "tuple[str, str]", fragment: "str | None") -> None:
    problem = _tail_problem(params, logger_allowed=owner in _LOGGER_ALLOWED)
    if fragment is None:
        assert problem is None
    else:
        assert problem is not None
        assert fragment in problem


def test_a_file_ruff_cannot_parse_fails_the_probe_rather_than_reading_as_no_finding(repo_root: Path, tmp_path: Path) -> None:
    planted = tmp_path / "broken.py"
    planted.write_text("def f(:\n")
    with pytest.raises(AssertionError, match="ruff reported more than PLR0913"):
        _findings(repo_root, _CEILINGS[3], 8, (str(planted),))
