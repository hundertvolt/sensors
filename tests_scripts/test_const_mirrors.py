"""Every test-side copy of a src/ const() is read or pinned: a module-level binding in tests/ named like a src/ const()
reads it with src_const() or a typed reader, or is a literal citing its outside source and equal to src/'s value, or is
the error catalog's code(); a copy under another name carries `# pins src/<file>.py <NAME>` and must equal it too."""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_CITATIONS = ("datasheet", "RFC", "SPEC", "p.", "§")
_PIN = "# pins "
_CATALOG_PREFIXES = ("_ERR_", "_WRN_")


def _readers() -> "frozenset[str]":
    # Every src_*(path, name) the tests' const helpers define: each returns one src/ const(), typed or not.
    names: set[str] = set()
    for helper in ("_src_const.py", "_src_schema.py"):
        tree = ast.parse((REPO_ROOT / "tests" / helper).read_text(encoding="utf-8"))
        names.update(node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("src_") and len(node.args.args) == 2)
    return frozenset(names)


_READERS = _readers()


def _check(binding: "tuple[str, str, ast.expr]", *, cited: bool, expected: "list[object]", consts: "dict[str, dict[str, object]]") -> "list[str]":
    # One binding (where, name, value): a src_*() read of an existing const, the catalog's code(), or a cited copy equal to src/.
    where, name, value = binding
    read = _src_const_call(value)
    if read is not None:
        file, read_name = read
        return [] if file.startswith("src/") and read_name in consts.get(file.removeprefix("src/"), {}) else [f"{where}: the read of {read} names no const() in src/"]
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "code" and name.startswith(_CATALOG_PREFIXES):
        return []
    try:
        literal = _value(value, {})
    except (NameError, TypeError):
        return [f"{where}: {name} = {ast.unparse(value)} is no literal - read src/'s {expected} with src_const()"]
    if cited and literal in expected:
        return []
    return [f"{where}: {name} = {ast.unparse(value)} copies src/'s {expected} - read it with src_const(), or cite its source and pin it"]


def _imported_src_files(tree: ast.Module, consts: "dict[str, dict[str, object]]") -> "set[str]":
    files: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            files.update(alias.name + ".py" for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            files.add(node.module + ".py")
    return files & set(consts)


def _src_const_call(node: ast.expr) -> "tuple[str, str] | None":
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _READERS and len(node.args) == 2:
        path, name = node.args
        if isinstance(path, ast.Constant) and isinstance(name, ast.Constant):
            return str(path.value), str(name.value)
    return None


def _value(node: ast.expr, names: "dict[str, object]") -> object:
    # A const() expression's value over the names bound before it: literals, names and operators only.
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Call, ast.Attribute, ast.Lambda, ast.Subscript, ast.NamedExpr)):
            raise TypeError(f"not a constant expression: {ast.unparse(node)}")
    return eval(compile(ast.Expression(node), "<const>", "eval"), {"__builtins__": {}}, dict(names))  # literals and earlier const() names only, checked above


def mirror_problems(src_dir: Path, tests_dir: Path) -> "tuple[list[str], int, int]":
    # (problems, src_const() bindings found, cited or pinned copies found) over every tests/*.py module-level binding.
    consts = src_consts(src_dir)
    by_name: dict[str, dict[str, object]] = {}
    for file, values in consts.items():
        for name, value in values.items():
            by_name.setdefault(name, {})[file] = value
    problems: list[str] = []
    reads = cited = 0
    for path in sorted(tests_dir.glob("*.py")):
        lines = path.read_text(encoding="utf-8").split("\n")
        tree = ast.parse("\n".join(lines))
        imported = _imported_src_files(tree, consts)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets: list[ast.expr] = node.targets
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
            else:
                continue
            text, above = lines[node.lineno - 1], lines[node.lineno - 2] if node.lineno > 1 else ""
            for target in (t for t in targets if isinstance(t, ast.Name)):
                binding = (f"tests/{path.name}:{node.lineno}", target.id, value)
                if _PIN in text:
                    file, _, pinned = text.split(_PIN, 1)[1].strip().partition(" ")
                    owner = consts.get(file.removeprefix("src/"), {})
                    found = _check(binding, cited=True, expected=[owner[pinned]], consts=consts) if pinned in owner else [f"{binding[0]}: the pin names no const() {pinned} in {file}"]
                elif target.id in by_name:
                    owners = by_name[target.id]
                    expected = [owners[file] for file in owners if file in imported] or list(owners.values())
                    found = _check(binding, cited=any(c in text or c in above for c in _CITATIONS), expected=expected, consts=consts)
                else:
                    continue
                problems += found
                is_read = _src_const_call(value) is not None
                reads += not found and is_read
                cited += not found and not is_read
    return problems, reads, cited


def src_consts(src_dir: Path) -> "dict[str, dict[str, object]]":
    # {file name: {NAME: value}} of every module-level `NAME = const(...)` in src/*.py, each over the names before it.
    found: dict[str, dict[str, object]] = {}
    for path in sorted(src_dir.glob("*.py")):
        values: dict[str, object] = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
                continue
            call = node.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "const":
                values[node.targets[0].id] = _value(call.args[0], values)
        found[path.name] = values
    return found


def test_every_test_copy_of_a_src_const_is_read_or_pinned() -> None:
    problems, reads, cited = mirror_problems(REPO_ROOT / "src", REPO_ROOT / "tests")
    assert problems == [], "\n".join(problems)
    assert reads >= 1, "no src_const() binding found - the scan reads nothing"
    assert cited >= 1, "no cited copy found - the scan reads nothing"
    assert {"src_const", "src_int", "src_schema"} <= _READERS, f"the reader scan found {sorted(_READERS)}"


def test_every_src_const_is_read() -> None:
    # The collection itself: every const() binding in src/ evaluates, so no copy can escape the comparison.
    assert sum(len(values) for values in src_consts(REPO_ROOT / "src").values()) > 700


_PLANTED = {
    "copy": "_LIMIT = 4\n",
    "wrong cited copy": "_LIMIT = 4  # datasheet p.9\n",
    "missing const": 'from _src_const import src_const\n_LIMIT = src_const("src/asy_x.py", "_OTHER")\n',
    "missing typed const": 'from _src_const import src_int\n_LIMIT = src_int("src/asy_x.py", "_OTHER")\n',
    "wrong pin": "_MY_LIMIT = 4  # pins src/asy_x.py _LIMIT\n",
    "pin to nothing": "_MY_LIMIT = 5  # pins src/asy_x.py _GONE\n",
}


@pytest.mark.parametrize("case", sorted(_PLANTED))
def test_a_planted_mirror_fails_and_its_read_or_cited_form_passes(tmp_path: Path, case: str) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "asy_x.py").write_text("_BASE = const(2)\n_LIMIT = const(_BASE + 3)\n", encoding="utf-8")
    (tmp_path / "tests" / "test_x.py").write_text(_PLANTED[case], encoding="utf-8")
    assert mirror_problems(tmp_path / "src", tmp_path / "tests")[0], f"the planted {case} passed"
    clean = 'from _src_const import src_const\n_LIMIT = src_const("src/asy_x.py", "_LIMIT")\n_BASE = 2  # datasheet p.9\n_MY = 5  # pins src/asy_x.py _LIMIT\n'
    (tmp_path / "tests" / "test_x.py").write_text(clean, encoding="utf-8")
    assert mirror_problems(tmp_path / "src", tmp_path / "tests") == ([], 1, 2)
