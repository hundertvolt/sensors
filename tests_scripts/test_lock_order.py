"""SPECIFICATION.md C.8's lock table is complete and obeyed: every lock attribute in src/ is a row and every
row a lock, every `async with`/`.acquire()` resolves to a row, and inside one function a lock is taken only
while holding locks of a higher level - never under a leaf or with a row that has no level."""

import ast
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
SPEC = REPO_ROOT / "SPECIFICATION.md"
_BEGIN, _END = "<!-- locks:begin -->", "<!-- locks:end -->"
_NAME_RE = re.compile(r"`(\w+)\.(\w+)`")
# A device session by its attribute name (C.8: `self._i2c_<chip>`, or a public form a class keeps) and a
# session's bus device, which C.8's Lockable row names as the bus lock itself.
_SESSION_ATTR_RE = re.compile(r"^_?(?:i2c|spi)_\w+$")
_BUS_DEVICE_ATTRS = frozenset({"i2c_device", "spi_device"})
_BUS_DEVICE_CLASSES = frozenset({"I2CDevice", "SPIDevice"})
_BUS_ROW = ("I2C", "bus_lock")
_SESSION_ROW = ("Lockable", "session_lock")


Assignment = ast.Assign | ast.AnnAssign | ast.AugAssign


def _targets(stmt: Assignment) -> list[ast.expr]:
    return stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]


@dataclass(frozen=True)
class Row:
    names: tuple[tuple[str, str], ...]
    level: int | None  # None: "leaf" or no level
    leaf: bool

    def label(self) -> str:
        return ", ".join(f"{cls}.{attr}" for cls, attr in self.names)


def table_rows(spec_text: str) -> list[Row]:
    start, end = spec_text.index(_BEGIN), spec_text.index(_END)
    rows: list[Row] = []
    for line in spec_text[start + len(_BEGIN) : end].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("Lock", "") or set(cells[0]) <= {"-"}:
            continue
        names = tuple(_NAME_RE.findall(cells[0]))
        assert names, f"C.8 lock row names no `Class.attribute`: {line}"
        level = cells[1]
        assert level.isdigit() or level in ("leaf", "\u2014"), f"C.8 lock row level is not a number, 'leaf' or a dash: {line}"
        rows.append(Row(names, int(level) if level.isdigit() else None, level == "leaf"))
    assert rows, "C.8's lock table between the markers is empty"
    return rows


class SourceIndex:
    # Every class in src/ by name, its bases, and the class each `self.<attr>` is assigned from: a constructor
    # call, an annotated parameter, or an attribute of an annotated parameter. Enough to type a lock receiver.

    def __init__(self, src: Path) -> None:
        self.trees: dict[str, ast.Module] = {}
        self.classes: dict[str, ast.ClassDef] = {}
        self.class_file: dict[str, str] = {}
        for path in sorted(src.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
            self.trees[path.name] = tree
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    assert node.name not in self.classes, f"class {node.name} defined twice in src/"
                    self.classes[node.name] = node
                    self.class_file[node.name] = path.name

    def bases(self, name: str) -> list[str]:
        node = self.classes.get(name)
        return [] if node is None else [b.id for b in node.bases if isinstance(b, ast.Name)]

    def mro(self, name: str) -> list[str]:
        out, todo = [], [name]
        while todo:
            current = todo.pop(0)
            if current not in out:
                out.append(current)
                todo.extend(self.bases(current))
        return out

    def is_lockable(self, name: str) -> bool:
        return "Lockable" in self.mro(name)

    def annotation_class(self, annotation: ast.expr | None) -> str | None:
        if annotation is None:
            return None
        text = annotation.value if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str) else ast.unparse(annotation)
        found = [word for word in re.findall(r"\w+", text) if word in self.classes]
        return found[0] if len(found) == 1 else None

    def value_class(self, value: ast.expr, params: dict[str, ast.expr | None], depth: int = 0) -> str | None:
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in self.classes:
            return value.func.id
        if isinstance(value, ast.Name) and value.id in params:
            return self.annotation_class(params[value.id])
        if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id in params and depth < 4:
            owner = self.annotation_class(params[value.value.id])
            return None if owner is None else self.attr_class(owner, value.attr, depth + 1)
        return None

    def attr_class(self, cls: str, attr: str, depth: int = 0) -> str | None:
        for name in self.mro(cls):
            node = self.classes.get(name)
            if node is None:
                continue
            for fn in (n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
                params = {a.arg: a.annotation for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)}
                for stmt in (s for s in ast.walk(fn) if isinstance(s, (ast.Assign, ast.AnnAssign))):
                    for target in _targets(stmt):
                        if isinstance(target, ast.Attribute) and target.attr == attr and isinstance(target.value, ast.Name) and target.value.id == "self":
                            if isinstance(stmt, ast.AnnAssign) and (found := self.annotation_class(stmt.annotation)):
                                return found
                            if stmt.value is not None and (found := self.value_class(stmt.value, params, depth)):
                                return found
        return None


def _is_lock_creation(value: ast.expr | None) -> bool:
    return value is not None and any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "Lock" and isinstance(n.func.value, ast.Name) and n.func.value.id == "asyncio"
        for n in ast.walk(value)
    )


def _self_attr_assignments(node: ast.ClassDef) -> list[tuple[str, ast.expr | None, int]]:
    out: list[tuple[str, ast.expr | None, int]] = []
    for stmt in (s for s in ast.walk(node) if isinstance(s, (ast.Assign, ast.AnnAssign))):
        out.extend(
            (target.attr, stmt.value, stmt.lineno)
            for target in _targets(stmt)
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self"
        )
    return out


def attribute_findings(index: SourceIndex, rows: list[Row]) -> list[str]:
    # A created lock is its class's (or a base's) row; any other `*_lock` attribute names a tabled lock; a
    # lock created anywhere but a self attribute has no row; a row names a lock its class really assigns.
    by_name = {name: row for row in rows for name in row.names}
    tabled_attrs = {attr for row in rows for _, attr in row.names}
    findings: list[str] = []
    assigned: set[tuple[str, str]] = set()
    held_in_attr: set[int] = set()
    for cls, node in index.classes.items():
        for attr, value, line in _self_attr_assignments(node):
            assigned.add((cls, attr))
            site = f"{index.class_file[cls]}:{line} {cls}.{attr}"
            if _is_lock_creation(value):
                held_in_attr.update(id(n) for n in ast.walk(value) if isinstance(n, ast.Call))  # type: ignore[arg-type]
                if not any((base, attr) in by_name for base in index.mro(cls)):
                    findings.append(f"{site}: an asyncio.Lock() with no row in C.8's lock table")
            elif attr.endswith("_lock") and attr not in tabled_attrs:
                findings.append(f"{site}: a lock attribute with no row in C.8's lock table")
    findings.extend(
        f"{file}:{node.lineno}: an asyncio.Lock() not held in a self attribute, so no C.8 row can name it"
        for file, tree in index.trees.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_lock_creation(node) and isinstance(node.func, ast.Attribute) and node.func.attr == "Lock" and id(node) not in held_in_attr
    )
    for row in rows:
        for cls, attr in row.names:
            if (cls, attr) not in assigned:
                findings.append(f"C.8 lock table: {cls}.{attr} is assigned nowhere in src/ (stale row)")
    return findings


class _Resolver:
    def __init__(self, index: SourceIndex, rows: list[Row]) -> None:
        self.index = index
        self.by_attr: dict[str, Row] = {}
        self.by_name = {name: row for row in rows for name in row.names}
        for row in rows:
            for _, attr in row.names:
                assert self.by_attr.get(attr, row) is row, f"C.8 lock table: attribute {attr} names two rows"
                self.by_attr[attr] = row

    def receiver_class(self, expr: ast.expr, cls: str | None, local: dict[str, ast.expr]) -> str | None:
        if isinstance(expr, ast.Name) and expr.id in local:
            return self.receiver_class(local[expr.id], cls, {})
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == "self" and cls is not None:
            return self.index.attr_class(cls, expr.attr)
        return None

    def resolve(self, expr: ast.expr, cls: str | None, local: dict[str, ast.expr]) -> Row | None:
        if isinstance(expr, ast.Attribute):
            if expr.attr in self.by_attr:
                return self.by_attr[expr.attr]
            if expr.attr in _BUS_DEVICE_ATTRS:
                return self.by_name[_BUS_ROW]
            if _SESSION_ATTR_RE.match(expr.attr):
                return self.by_name[_SESSION_ROW]
        found = self.receiver_class(expr, cls, local)
        if found in _BUS_DEVICE_CLASSES:
            return self.by_name[_BUS_ROW]
        if found is not None and self.index.is_lockable(found):
            return self.by_name[_SESSION_ROW]
        return None


def _nesting_problem(outer: Row, inner: Row) -> str | None:
    if outer.leaf:
        return f"taken inside the leaf lock {outer.label()}"
    if outer.level is None or inner.level is None:
        return f"nested with {outer.label()}, and a row without a level is never nested inside one function"
    if inner.level >= outer.level:
        return f"level {inner.level} taken while holding level {outer.level} ({outer.label()}): a higher level comes first"
    return None


def function_findings(file: str, cls: str | None, fn: ast.FunctionDef | ast.AsyncFunctionDef, resolver: _Resolver) -> list[str]:
    findings: list[str] = []
    local: dict[str, ast.expr] = {}
    acquired: list[tuple[str, Row]] = []
    where = f"{file} {cls + '.' if cls else ''}{fn.name}()"

    def take(expr: ast.expr, line: int, holding: list[Row]) -> Row | None:
        row = resolver.resolve(expr, cls, local)
        if row is None:
            findings.append(f"{where}:{line}: `{ast.unparse(expr)}` resolves to no row of C.8's lock table")
            return None
        findings.extend(f"{where}:{line}: {row.label()} {problem}" for outer in holding if (problem := _nesting_problem(outer, row)))
        return row

    def visit(node: ast.AST, held: list[Row]) -> None:
        if node is not fn and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            return
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            local[node.targets[0].id] = node.value
        if isinstance(node, ast.AsyncWith):
            inner = list(held)
            for item in node.items:
                visit(item.context_expr, inner)
                row = take(item.context_expr, node.lineno, inner + [r for _, r in acquired])
                if row is not None:
                    inner.append(row)
            for stmt in node.body:
                visit(stmt, inner)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("acquire", "release") and not node.args:
            lock = node.func.value
            if node.func.attr == "acquire":
                row = take(lock, node.lineno, held + [r for _, r in acquired])
                if row is not None:
                    acquired.append((ast.unparse(lock), row))
            else:
                acquired[:] = [(text, row) for text, row in acquired if text != ast.unparse(lock)]
            return
        for child in ast.iter_child_nodes(node):
            visit(child, held)

    visit(fn, [])
    return findings


def order_findings(index: SourceIndex, rows: list[Row]) -> list[str]:
    resolver = _Resolver(index, rows)
    findings: list[str] = []
    for file, tree in index.trees.items():
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings += function_findings(file, None, node, resolver)
            elif isinstance(node, ast.ClassDef):
                for fn in node.body:
                    if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        findings += function_findings(file, node.name, fn, resolver)
    return findings


def all_findings(src: Path, spec_text: str) -> list[str]:
    index, rows = SourceIndex(src), table_rows(spec_text)
    return attribute_findings(index, rows) + order_findings(index, rows)


def _spec() -> str:
    return SPEC.read_text(encoding="utf-8")


@pytest.fixture
def src_copy(tmp_path: Path) -> Path:
    return Path(shutil.copytree(SRC, tmp_path / "src"))


def _append(src: Path, name: str, text: str) -> None:
    path = src / name
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_every_lock_is_tabled_and_taken_in_order() -> None:
    assert all_findings(SRC, _spec()) == []


def test_every_acquisition_in_src_resolves_to_a_row() -> None:
    # The resolver reaches every site the table covers: a site it dropped would pass the order rule unseen.
    index, rows = SourceIndex(SRC), table_rows(_spec())
    resolver = _Resolver(index, rows)
    seen = {row.label() for file, tree in index.trees.items() for cls in tree.body if isinstance(cls, ast.ClassDef)
            for fn in cls.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(fn) if isinstance(node, ast.AsyncWith)
            for item in node.items if (row := resolver.resolve(item.context_expr, cls.name, {})) is not None}
    assert {"_FRAMBaseChunk._op_lock", "Lockable.session_lock", "I2C.bus_lock, SPI.bus_lock", "FRAM_SPI._bus_lock"} <= seen, seen


def test_a_lower_level_taken_before_a_higher_one_fails(src_copy: Path) -> None:
    _append(src_copy, "asy_bmp3xx_driver.py", "\n\nasync def _planted(dev):\n    async with dev.i2c_device as i2c, dev._i2c_bmp3xx as s:\n        pass\n")
    findings = all_findings(src_copy, _spec())
    assert len(findings) == 1 and "asy_bmp3xx_driver.py _planted():" in findings[0], findings
    assert "Lockable.session_lock level 2 taken while holding level 1" in findings[0], findings


def test_an_untabled_lock_attribute_fails(src_copy: Path) -> None:
    path = src_copy / "asy_neopixel_driver.py"
    text = path.read_text(encoding="utf-8")
    anchor = "        self._overlay_lock = asyncio.Lock()"
    assert anchor in text
    path.write_text(text.replace(anchor, "        self._extra_lock = asyncio.Lock()\n" + anchor), encoding="utf-8")
    findings = all_findings(src_copy, _spec())
    assert len(findings) == 1 and "NeopixelDriver._extra_lock: an asyncio.Lock() with no row" in findings[0], findings


def test_an_acquisition_inside_a_leaf_lock_fails(src_copy: Path) -> None:
    _append(src_copy, "asy_base_classes.py", "\n\nasync def _planted(r):\n    async with r._data_lock:\n        async with r._overlay_lock:\n            pass\n")
    findings = all_findings(src_copy, _spec())
    assert len(findings) == 1 and "_planted():" in findings[0] and "taken inside the leaf lock SensorReader._data_lock" in findings[0], findings


def test_an_unlevelled_row_nested_with_another_fails(src_copy: Path) -> None:
    _append(src_copy, "asy_wifi_service.py", "\n\nasync def _planted(w, s):\n    async with w.wifi_mode_lock:\n        async with s._connect_lock:\n            pass\n")
    findings = all_findings(src_copy, _spec())
    assert len(findings) == 1 and "UDPSocket._connect_lock nested with WifiService.wifi_mode_lock" in findings[0], findings


def test_an_acquire_call_holds_until_its_release(src_copy: Path) -> None:
    planted = "\n\nasync def _planted(f):\n    await f._bus_lock.acquire()\n    f._bus_lock.release()\n    await f.session_lock.acquire()\n    async with f._bus_lock:\n        await f._op_lock.acquire()\n"
    _append(src_copy, "asy_fram_driver.py", planted)
    findings = all_findings(src_copy, _spec())
    # The released bus lock is not held at the session acquire; both locks held at the _op_lock acquire are.
    assert sorted(f.split(": ", 1)[1] for f in findings) == [
        "_FRAMBaseChunk._op_lock level 3 taken while holding level 1 (FRAM_SPI._bus_lock): a higher level comes first",
        "_FRAMBaseChunk._op_lock level 3 taken while holding level 2 (Lockable.session_lock): a higher level comes first",
    ], findings


def test_an_acquisition_the_table_cannot_name_fails(src_copy: Path) -> None:
    _append(src_copy, "asy_udp_socket.py", "\n\nasync def _planted(x):\n    async with x.mystery:\n        pass\n")
    findings = all_findings(src_copy, _spec())
    assert findings == [findings[0]] and "`x.mystery` resolves to no row" in findings[0], findings


def test_a_lock_outside_a_self_attribute_fails(src_copy: Path) -> None:
    _append(src_copy, "asy_udp_socket.py", "\n\n_SHARED = asyncio.Lock()\n")
    findings = all_findings(src_copy, _spec())
    assert len(findings) == 1 and "asy_udp_socket.py:" in findings[0] and "not held in a self attribute" in findings[0], findings


def test_a_stale_row_fails() -> None:
    spec = _spec().replace(_END, "| `UDPSocket._gone_lock` | \u2014 | nothing | nothing |\n" + _END)
    findings = all_findings(SRC, spec)
    assert findings == ["C.8 lock table: UDPSocket._gone_lock is assigned nowhere in src/ (stale row)"], findings
