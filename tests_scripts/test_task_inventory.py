"""Every task src/ creates is a starter or a row of SPECIFICATION.md C.9's task table: each `create_task(`/
`start_server(` sits in a method a `get_task_starters()`/`get_timer_starters()` returns, or in the function a
row's "Created by" cell names with its file; an untabled site fails, and so does a row with no site."""

import ast
import re
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
SPEC = REPO_ROOT / "SPECIFICATION.md"
_BEGIN, _END = "<!-- tasks:begin -->", "<!-- tasks:end -->"
# A "Created by" cell names the enclosing function first (`Class.method()`) and its file (`asy_*.py`).
_FUNCTION_RE = re.compile(r"`(\w+)\.(\w+)\(\)`")
_FILE_RE = re.compile(r"`(\w+\.py)`")
_TASK_CALLS = frozenset({"create_task", "start_server"})
_STARTER_LISTS = frozenset({"get_task_starters", "get_timer_starters"})

Site = tuple[str, str, str]  # (file, class, function)


def table_rows(spec_text: str) -> dict[Site, str]:
    start, end = spec_text.index(_BEGIN), spec_text.index(_END)
    rows: dict[Site, str] = {}
    for line in spec_text[start + len(_BEGIN) : end].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[0] in ("Task", "") or set(cells[0]) <= {"-"}:
            continue
        function, file = _FUNCTION_RE.search(cells[1]), _FILE_RE.search(cells[1])
        assert function and file, f"C.9 task row's 'Created by' names no `Class.function()` or no `file.py`: {line}"
        rows[(file.group(1), function.group(1), function.group(2))] = cells[0]
    assert rows, "C.9's task table between the markers is empty"
    return rows


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None


def _starters(classes: dict[str, ast.ClassDef], name: str) -> set[str]:
    # The methods a class's (or a base's) starter lists return, as `self.<method>` references.
    found: set[str] = set()
    todo = [name]
    while todo:
        node = classes.get(todo.pop())
        if node is None:
            continue
        todo.extend(b.id for b in node.bases if isinstance(b, ast.Name))
        for fn in node.body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name in _STARTER_LISTS:
                found.update(n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self")
    return found


def task_sites(src: Path) -> list[tuple[Site, int]]:
    sites: list[tuple[Site, int]] = []
    for path in sorted(src.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        for top in tree.body:
            owners = [(top.name, fn) for fn in top.body] if isinstance(top, ast.ClassDef) else [("", top)]
            for cls, fn in owners:
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call) and _call_name(node) in _TASK_CALLS:
                        name = fn.name if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) else "<module>"
                        sites.append(((path.name, cls, name), node.lineno))
    return sites


def inventory_findings(src: Path, spec_text: str) -> list[str]:
    classes = {}
    for path in sorted(src.glob("*.py")):
        classes.update({n.name: n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.ClassDef)})
    rows = table_rows(spec_text)
    findings: list[str] = []
    used: set[Site] = set()
    for (file, cls, fn), line in task_sites(src):
        if cls and fn in _starters(classes, cls):
            continue
        if (file, cls, fn) in rows:
            used.add((file, cls, fn))
            continue
        findings.append(f"{file}:{line} {cls}.{fn}(): a task created outside every starter, and no row of C.9's task table names it")
    findings += [f"C.9 task table: row '{task}' names {cls}.{fn}() in {file}, which creates no task (stale row)" for (file, cls, fn), task in rows.items() if (file, cls, fn) not in used]
    return findings


def _spec() -> str:
    return SPEC.read_text(encoding="utf-8")


@pytest.fixture
def src_copy(tmp_path: Path) -> Path:
    return Path(shutil.copytree(SRC, tmp_path / "src"))


def _edit(src: Path, name: str, old: str, new: str) -> None:
    path = src / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{name}: the anchor is not unique: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_every_task_site_is_a_starter_or_a_tabled_row() -> None:
    assert inventory_findings(SRC, _spec()) == []


def test_the_table_and_the_starters_both_carry_sites() -> None:
    # Neither half is vacuous: every row matches a site, and most sites are starters.
    sites = task_sites(SRC)
    assert set(table_rows(_spec())) <= {site for site, _ in sites}
    assert len(sites) > len(table_rows(_spec())) + 10, sites


def test_an_untabled_task_fails_naming_its_site(src_copy: Path) -> None:
    _edit(src_copy, "asy_neopixel_driver.py", "    def toggle(self) -> None:\n", "    def toggle(self) -> None:\n        asyncio.create_task(self._signal_loop())\n")
    findings = inventory_findings(src_copy, _spec())
    assert len(findings) == 1 and findings[0].startswith("asy_neopixel_driver.py:") and "NeopixelDriver.toggle(): a task created outside every starter" in findings[0], findings


def test_a_starter_dropped_from_its_list_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_neopixel_driver.py", "return [self.start_asy_overlay, self.start_asy_signal]", "return [self.start_asy_overlay]")
    findings = inventory_findings(src_copy, _spec())
    assert len(findings) == 1 and "NeopixelDriver.start_asy_signal(): a task created outside every starter" in findings[0], findings


def test_a_stale_row_fails() -> None:
    spec = _spec().replace(_END, "| Gone | `WifiService.gone()` (`asy_wifi_service.py`) | - | - | - |\n" + _END)
    assert inventory_findings(SRC, spec) == ["C.9 task table: row 'Gone' names WifiService.gone() in asy_wifi_service.py, which creates no task (stale row)"]


def test_a_row_naming_no_function_fails_to_parse() -> None:
    spec = _spec().replace(_END, "| Vague | `WifiService` somewhere (`asy_wifi_service.py`) | - | - | - |\n" + _END)
    with pytest.raises(AssertionError, match=re.escape("names no `Class.function()`")):
        table_rows(spec)
