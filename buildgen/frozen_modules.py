"""Dependency-driven frozen-module selection (BUILD_CHAIN_PLAN.md's "Core design decisions"): the
transitive `import`/`from...import` closure, AST-scanned, seeded from the device's declared drivers
plus a fixed core set. Computes *which* modules; feeding them to freeze() is Session 6's job."""

import ast
from pathlib import Path

from buildgen.model import DeviceModel

# Always-included core (every device needs all of these regardless of which optional drivers it
# declares - mandatory infra plus the modules build_system() itself always imports directly, not
# necessarily transitively reachable from any one driver).
CORE_MODULES = frozenset(
    {
        "config_manager",
        "base_classes",
        "print_log",
        "api_response",
        "asy_i2c_driver",
        "asy_spi_driver",
        "asy_webserver_service",
        "asy_wifi_service",
        "asy_ntp_client",
        "asy_dns_client",
        "captive_dns",
        "system_service",
        "crc_checks",
    }
)


def _is_type_checking_test(test: ast.expr) -> bool:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _collect_imports(node: ast.AST, out: set) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and _is_type_checking_test(child.test):
            continue  # never executes on-device - not a real frozen-module dependency
        if isinstance(child, ast.Import):
            for alias in child.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(child, ast.ImportFrom):
            if child.module and child.level == 0:  # level>0 (relative) doesn't occur in this flat layout
                out.add(child.module.split(".")[0])
        else:
            _collect_imports(child, out)


def _local_imports_of(module: str, roots: "tuple[Path, ...]") -> set:
    for root in roots:
        path = root / f"{module}.py"
        if path.is_file():
            tree = ast.parse(path.read_text(), filename=str(path))
            names: set = set()
            _collect_imports(tree, names)
            return {n for n in names if any((root2 / f"{n}.py").is_file() for root2 in roots)}
    return set()


def compute_frozen_modules(model: DeviceModel, src_dir: Path, ext_dir: "Path | None" = None) -> "frozenset[str]":
    roots = (src_dir,) if ext_dir is None else (src_dir, ext_dir)
    seed = set(CORE_MODULES) | {spec.driver_info.module for spec in model.instances.values() if spec.driver_info is not None}

    closure: set = set()
    frontier = set(seed)
    while frontier:
        module = frontier.pop()
        if module in closure:
            continue
        closure.add(module)
        frontier |= _local_imports_of(module, roots) - closure

    return frozenset(closure)
