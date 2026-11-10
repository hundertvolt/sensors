"""Locks in src/ are taken in order: inside one function a lock is taken only while holding locks of a higher level,
and two locks without a level are never nested. Every `async with`/`.acquire()` names a lock the check can place."""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
# The only nesting src/ does: a device session's lock before its bus's (asy_base_classes.py Lockable). Every other
# lock (an attribute named *_lock) has no level and is never nested with another inside one function.
LEVELS = {"session_lock": 2, "bus_lock": 1}
# A device session by its attribute name (`self._i2c_<chip>`, or a public form a class keeps), a bus device, its class.
_SESSION_ATTR_RE = re.compile(r"^_?(?:i2c|spi)_\w+$")
_BUS_DEVICE_ATTRS = frozenset({"i2c_device", "spi_device"})
_BUS_DEVICE_CLASSES = frozenset({"I2CDevice", "SPIDevice"})


Assignment = ast.Assign | ast.AnnAssign | ast.AugAssign


def _targets(stmt: Assignment) -> list[ast.expr]:
    return stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]


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

    def is_lockable(self, name: str) -> bool:
        return "Lockable" in self.mro(name)

    def annotation_class(self, annotation: ast.expr | None) -> str | None:
        if annotation is None:
            return None
        text = annotation.value if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str) else ast.unparse(annotation)
        found = [word for word in re.findall(r"\w+", text) if word in self.classes]
        return found[0] if len(found) == 1 else None

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

    def value_class(self, value: ast.expr, params: dict[str, ast.expr | None], depth: int = 0) -> str | None:
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in self.classes:
            return value.func.id
        if isinstance(value, ast.Name) and value.id in params:
            return self.annotation_class(params[value.id])
        if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id in params and depth < 4:
            owner = self.annotation_class(params[value.value.id])
            return None if owner is None else self.attr_class(owner, value.attr, depth + 1)
        return None


class _Resolver:
    # Names the lock an acquisition takes: an attribute named *_lock, a bus device's bus lock, a device session's lock.
    def __init__(self, index: SourceIndex) -> None:
        self.index = index

    def receiver_class(self, expr: ast.expr, cls: str | None, local: dict[str, ast.expr]) -> str | None:
        if isinstance(expr, ast.Name) and expr.id in local:
            return self.receiver_class(local[expr.id], cls, {})
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == "self" and cls is not None:
            return self.index.attr_class(cls, expr.attr)
        return None

    def resolve(self, expr: ast.expr, cls: str | None, local: dict[str, ast.expr]) -> str | None:
        if isinstance(expr, ast.Attribute):
            if expr.attr.endswith("_lock"):
                return expr.attr
            if expr.attr in _BUS_DEVICE_ATTRS:
                return "bus_lock"
            if _SESSION_ATTR_RE.match(expr.attr):
                return "session_lock"
        found = self.receiver_class(expr, cls, local)
        if found in _BUS_DEVICE_CLASSES:
            return "bus_lock"
        if found is not None and self.index.is_lockable(found):
            return "session_lock"
        return None


def _nesting_problem(outer: str, inner: str) -> str | None:
    if outer not in LEVELS or inner not in LEVELS:
        return f"nested with {outer}, and a lock without a level is never nested inside one function"
    if LEVELS[inner] >= LEVELS[outer]:
        return f"level {LEVELS[inner]} taken while holding level {LEVELS[outer]} ({outer}): a higher level comes first"
    return None


def function_findings(file: str, cls: str | None, fn: ast.FunctionDef | ast.AsyncFunctionDef, resolver: _Resolver) -> list[str]:
    findings: list[str] = []
    local: dict[str, ast.expr] = {}
    acquired: list[tuple[str, str]] = []
    where = f"{file} {cls + '.' if cls else ''}{fn.name}()"

    def take(expr: ast.expr, line: int, holding: list[str]) -> str | None:
        lock = resolver.resolve(expr, cls, local)
        if lock is None:
            findings.append(f"{where}:{line}: `{ast.unparse(expr)}` names no lock the order check can place")
            return None
        findings.extend(f"{where}:{line}: {lock} {problem}" for outer in holding if (problem := _nesting_problem(outer, lock)))
        return lock

    def visit(node: ast.AST, held: list[str]) -> None:
        if node is not fn and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            return
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            local[node.targets[0].id] = node.value
        if isinstance(node, ast.AsyncWith):
            inner = list(held)
            for item in node.items:
                visit(item.context_expr, inner)
                taken = take(item.context_expr, node.lineno, inner + [r for _, r in acquired])
                if taken is not None:
                    inner.append(taken)
            for stmt in node.body:
                visit(stmt, inner)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("acquire", "release") and not node.args:
            lock = node.func.value
            if node.func.attr == "acquire":
                taken = take(lock, node.lineno, held + [r for _, r in acquired])
                if taken is not None:
                    acquired.append((ast.unparse(lock), taken))
            else:
                acquired[:] = [(text, taken) for text, taken in acquired if text != ast.unparse(lock)]
            return
        for child in ast.iter_child_nodes(node):
            visit(child, held)

    visit(fn, [])
    return findings


def order_findings(src: Path) -> list[str]:
    index = SourceIndex(src)
    resolver = _Resolver(index)
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


def test_every_lock_is_taken_in_order() -> None:
    assert order_findings(SRC) == []


def test_the_nested_session_and_bus_sites_are_seen() -> None:
    # The resolver reaches the one nesting src/ does: a site it dropped would pass the order rule unseen.
    index = SourceIndex(SRC)
    resolver = _Resolver(index)
    seen = {lock for tree in index.trees.values() for cls in tree.body if isinstance(cls, ast.ClassDef)
            for fn in cls.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(fn) if isinstance(node, ast.AsyncWith)
            for item in node.items if (lock := resolver.resolve(item.context_expr, cls.name, {})) is not None}
    assert set(LEVELS) <= seen, seen
