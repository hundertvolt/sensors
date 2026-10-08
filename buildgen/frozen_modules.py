"""Dependency-driven frozen-module selection (SPECIFICATION.md Part L.2): the
transitive `import`/`from...import` closure, AST-scanned, seeded from the generated device module's
own imports. Computes *which* modules; `scripts/build_firmware.py` stages them."""

import ast
from pathlib import Path

from buildgen.errors import BuildError
from buildgen.source_ast import parse_source


def _is_type_checking_test(test: ast.expr) -> bool:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _collect_imports(node: ast.AST, out: "set[str]") -> None:
    if isinstance(node, ast.Import):
        out.update(alias.name.split(".")[0] for alias in node.names)
        return
    if isinstance(node, ast.ImportFrom):
        if node.module and node.level == 0:  # level>0 (relative) doesn't occur in this flat layout
            out.add(node.module.split(".")[0])
        return
    if isinstance(node, ast.If) and _is_type_checking_test(node.test):
        # The body never executes on-device, so it is no frozen-module dependency; its else: does.
        for stmt in node.orelse:
            _collect_imports(stmt, out)
        return
    for child in ast.iter_child_nodes(node):
        _collect_imports(child, out)


def _local_imports_of(module: str, roots: "tuple[Path, ...]", device: str = "<src>") -> "set[str]":
    for root in roots:
        path = root / f"{module}.py"
        if path.is_file():
            try:
                tree = parse_source(path.read_text(encoding="utf-8"), str(path))
            except SyntaxError as e:
                raise BuildError(device, f"{path} has a syntax error: {e}", rule="source.syntax-error", fix="fix the file so Python can parse it", instance=module) from e
            names: set[str] = set()
            _collect_imports(tree, names)
            return _with_a_file(names, roots)
    return set()


def _with_a_file(names: "set[str]", roots: "tuple[Path, ...]") -> "set[str]":
    return {n for n in names if any((root / f"{n}.py").is_file() for root in roots)}


def compute_frozen_modules(module_source: str, src_dir: Path, ext_dir: Path, *, device: str = "<src>") -> "frozenset[str]":
    # The seed is what the generated module imports that has a file in either root (every declared
    # driver and the mandatory services; built-ins and the build-time frozen_html drop out).
    roots = (src_dir, ext_dir)
    seed: set[str] = set()
    _collect_imports(ast.parse(module_source), seed)

    closure: set[str] = set()
    frontier = _with_a_file(seed, roots)
    while frontier:
        module = frontier.pop()
        if module in closure:
            continue
        closure.add(module)
        frontier |= _local_imports_of(module, roots, device) - closure

    return frozenset(closure)
