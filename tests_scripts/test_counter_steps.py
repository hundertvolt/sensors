"""Counters stay allocation-free (SPECIFICATION.md G.2): over src/, every device's generated modules and the twin, no
min(x + n, cap) step and no cap or max_val above COUNTER_CAP (2**30 - 1, the largest small int)."""

import ast
import re

import pytest
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT

from buildgen.generate import generate_device

_SMALL_INT_MAX = 0x3FFFFFFF
_CAP_NAME = re.compile(r".*_CAP|.*max_val.*|.*MAX.*")

# (path, constant) -> why a value above COUNTER_CAP is no counter bound.
_LARGE_CONSTANTS: dict[tuple[str, str], str] = {
    ("src/asy_ntp_client.py", "_NTP_MAX_PLAUSIBLE_UNIX_TIME"): "a UTC plausibility bound, compared, never stepped",
    ("src/voc_algorithm.py", "_FIX16_MAXIMUM"): "the Sensirion port's C int32 fix16 limit, not a counter",
}
def _int_constants(tree: ast.Module) -> dict[str, int]:
    # Module-level names bound to an int literal or const(<int literal>).
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value.args[0] if isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "const" and node.value.args else node.value
            if isinstance(value, ast.Constant) and type(value.value) is int:
                found[node.targets[0].id] = value.value
    return found


def large_caps(path: str, tree: ast.Module) -> list[tuple[str, str, int, int]]:
    # (2) every integer above COUNTER_CAP bound to a cap-shaped name or passed as max_val=: (path, name, line, value).
    found = []
    for node in ast.walk(tree):
        pairs: list[tuple[str, ast.expr | None]] = []
        if isinstance(node, ast.Assign):
            pairs = [(ast.unparse(t).rsplit(".", 1)[-1], node.value) for t in node.targets]
        elif isinstance(node, ast.AnnAssign):
            pairs = [(ast.unparse(node.target).rsplit(".", 1)[-1], node.value)]
        elif isinstance(node, ast.keyword) and node.arg is not None:
            pairs = [(node.arg, node.value)] if node.arg == "max_val" else []
        elif isinstance(node, ast.arguments):
            named = [*node.posonlyargs, *node.args]
            pairs = [(a.arg, d) for a, d in zip(named[len(named) - len(node.defaults) :], node.defaults, strict=True)]
            pairs += [(a.arg, d) for a, d in zip(node.kwonlyargs, node.kw_defaults, strict=True)]
        for name, value in pairs:
            literal = value.args[0] if isinstance(value, ast.Call) and ast.unparse(value.func) == "const" and value.args else value
            if isinstance(literal, ast.Constant) and type(literal.value) is int and literal.value > _SMALL_INT_MAX and _CAP_NAME.fullmatch(name):
                found.append((path, name, literal.lineno, literal.value))
    return found


def min_steps(path: str, tree: ast.Module) -> list[str]:
    # (1) min(<expr> + <n>, <cap>) and min(max(<x> + ...)) build the stepped value before the cap applies.
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "min" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Call) and ast.unparse(first.func) == "max" and first.args:
                first = first.args[0]
            if isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
                found.append(f"{path}:{node.lineno}: {ast.unparse(node)}")
    return found


@pytest.fixture(scope="module")
def modules(tmp_path_factory: pytest.TempPathFactory) -> list[tuple[str, ast.Module]]:
    out = tmp_path_factory.mktemp("generated_src")
    found = [(f"{d}/{p.name}", ast.parse(p.read_text(encoding="utf-8"))) for d in ("src", "digital_twin", "fakes") for p in sorted((REPO_ROOT / d).glob("*.py"))]
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src", REPO_ROOT / "ext")
        for name, source in ((f"sensortask_{device}", generated.module_source), (f"sensortask_{device}_main", generated.boot_entry_source), (f"sensortask_{device}_main_noautostart", generated.boot_entry_noautostart_source)):
            (out / f"{name}.py").write_text(source, encoding="utf-8")
            found.append((f"build/generated_src/{name}.py", ast.parse((out / f"{name}.py").read_text(encoding="utf-8"))))
    return found


def test_no_min_step(modules: list[tuple[str, ast.Module]]) -> None:
    found = [line for path, tree in modules for line in min_steps(path, tree)]
    assert not found, "check the bound before stepping, never min() after it:\n" + "\n".join(found)


def test_no_cap_above_the_small_int_range(modules: list[tuple[str, ast.Module]]) -> None:
    found = [f"{p}:{line}: {name} = {value:#x}" for path, tree in modules for p, name, line, value in large_caps(path, tree) if (p, name) not in _LARGE_CONSTANTS]
    assert not found, "a cap above COUNTER_CAP lets a counter leave the small-int range:\n" + "\n".join(found)


def test_every_large_constant_entry_is_still_above_the_range(modules: list[tuple[str, ast.Module]]) -> None:
    present = {(p, name) for path, tree in modules for p, name, _, _ in large_caps(path, tree)}
    assert set(_LARGE_CONSTANTS) <= present, f"no longer above COUNTER_CAP - delete the entry: {sorted(set(_LARGE_CONSTANTS) - present)}"


def test_the_twin_scans_and_keeps_its_own_copy_of_the_counter_cap(modules: list[tuple[str, ast.Module]]) -> None:
    # The twin imports nothing from src/ (fakes/_twin_common.py), so its cap is a copy pinned equal here.
    trees = dict(modules)
    assert any(path.startswith("digital_twin/") for path in trees), "the twin dropped out of the scan"
    assert _int_constants(trees["fakes/_twin_common.py"])["COUNTER_CAP"] == _int_constants(trees["src/asy_base_classes.py"])["COUNTER_CAP"] == _SMALL_INT_MAX
