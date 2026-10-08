"""FRAM chunks and loggers are built once per boot, never re-entered by a task restart (SPECIFICATION.md
A.4): in src/ only constructors build them, and in every generated device only build_system()'s own
top-level statements construct an instance. Every chunk names its owner, and the owners' seeds differ."""

import ast
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from collections.abc import Callable

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CHUNK_CALLS = frozenset({"get_chunk", "get_timestamped_chunk"})
_BUILDERS = _CHUNK_CALLS | {"make_logger", "PrintLogHistoryStore", "ConfigManager"}
# make_logger() is the one factory: its body builds the store its callers' constructors ask for.
_ALLOWED_EXTRA_SITES = frozenset({("asy_print_log.py", "make_logger")})
_SEED_WIDTHS = (1, 2)  # _owner_seed() folds into min(crc.length(), 2) bytes: CRC8, then CRC16/CRC32
_VOC_SUFFIX = "_VOC"  # the SGP40 backup chunk's owner: its logger's name plus this suffix


class _StandInCrc:
    def __init__(self, width: int) -> None:
        self._width = width

    def length(self) -> int:
        return self._width


def _all_owners() -> "list[str]":
    return sorted({owner for device in DEVICE_NAMES for owner in _generated(device)[1]})


def _builder_sites(tree: ast.Module) -> "list[tuple[str, int, str]]":
    # (builder, line, nearest enclosing function); explicit descent so each call is attributed once.
    sites: list[tuple[str, int, str]] = []

    def visit(node: ast.AST, owner: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name)
                continue
            if isinstance(child, ast.Call) and _called_name(child) in _BUILDERS:
                sites.append((str(_called_name(child)), child.lineno, owner))
            visit(child, owner)

    visit(tree, "<module>")
    return sites


def _called_name(call: ast.Call) -> "str | None":
    if isinstance(call.func, ast.Name):
        return call.func.id
    return call.func.attr if isinstance(call.func, ast.Attribute) else None


def _construction_problems(device: str, source: str) -> "list[str]":
    tree = ast.parse(source)
    instances = _instance_globals(tree)
    classes = set(instances.values())
    problems = []
    for func in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        direct = set(func.body) if func.name == "build_system" else set()
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in instances for t in node.targets) and node not in direct:
                problems.append(f"{device}:{node.lineno}: {ast.unparse(node.targets[0])} assigned in {func.name}(), not as a top-level statement of build_system()")
            if isinstance(node, ast.Call) and ast.unparse(node.func) in classes and func.name != "build_system":
                problems.append(f"{device}:{node.lineno}: {ast.unparse(node.func)}() constructed in {func.name}()")
    built = {t.id for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "build_system" for s in n.body if isinstance(s, ast.Assign) for t in s.targets if isinstance(t, ast.Name)}
    missing = sorted(set(instances) - built)
    if missing:
        problems.append(f"{device}: {missing} never constructed by a top-level statement of build_system()")
    return problems


def _constructor_problems(name: str, source: str) -> "list[str]":
    return [
        f"src/{name}:{line}: {builder}() called in {owner}(), not in a constructor"
        for builder, line, owner in _builder_sites(ast.parse(source))
        if owner != "__init__" and (name, owner) not in _ALLOWED_EXTRA_SITES
    ]


@cache
def _generated(device: str) -> "tuple[str, tuple[str, ...]]":
    # The module source and its chunk owners: each resolved logger name, its config store, the VOC backup.
    result = generate_device(_REPO_ROOT / "devices" / f"{device}.toml", _REPO_ROOT / "src", _REPO_ROOT / "ext")
    owners = {"WIFI", "CFGMGR_WIFI", "DNSSRV", "NTP", "CFGMGR_NTP", "SYSTEM", "CFGMGR_SYSTEM", "WEBSERVER"}
    for spec in result.model.instances.values():
        assert spec.resolved_name is not None, spec.label
        owners |= {spec.resolved_name, "CFGMGR_" + spec.resolved_name}
        if spec.driver == "sgp40":
            owners.add(spec.resolved_name + _VOC_SUFFIX)
    return result.module_source, tuple(sorted(owners))


def _instance_globals(tree: ast.Module) -> "dict[str, str]":
    # Module globals declared `name: Class | None = None`, mapped to the class build_system() puts there.
    out = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out[node.target.id] = ast.unparse(node.annotation).split(" | ")[0]
    return out


def _owner_problems(name: str, source: str) -> "list[str]":
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _CHUNK_CALLS]
    return [f"src/{name}:{c.lineno}: {_called_name(c)}() passes no owner=" for c in calls if not any(kw.arg == "owner" for kw in c.keywords)]


@cache
def _owner_seed_fn() -> "Callable[[str, _StandInCrc], object]":
    # _owner_seed() run as written, under CPython: its source read from the manager, never imported.
    tree = ast.parse((_REPO_ROOT / "src" / "asy_fram_manager.py").read_text())
    (func,) = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_owner_seed"]
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=[func], type_ignores=[]), "asy_fram_manager.py", "exec"), {"CRCBase": object}, namespace)  # noqa: S102
    fn = namespace["_owner_seed"]
    assert callable(fn)
    return fn


def _seed(owner: str, width: int) -> int:
    seed = _owner_seed_fn()(owner, _StandInCrc(width))
    assert isinstance(seed, int)
    return seed


def _seed_problems(owners: "list[str]") -> "list[str]":
    problems = []
    for width in _SEED_WIDTHS:
        all_ones = (1 << (8 * width)) - 1
        by_seed: dict[int, str] = {}
        for owner in sorted(set(owners)):
            seed = _seed(owner, width)
            if seed in (0, all_ones):
                problems.append(f"{width}-byte seed of {owner!r} is {seed:#x}: zero data or the unseeded default would validate")
            elif seed in by_seed:
                problems.append(f"{width}-byte seeds collide: {by_seed[seed]!r} and {owner!r} both {seed:#x}")
            else:
                by_seed[seed] = owner
    return problems


def _src() -> "list[tuple[str, str]]":
    return [(p.name, p.read_text()) for p in sorted((_REPO_ROOT / "src").glob("*.py"))]


def test_src_builds_chunks_and_loggers_only_in_constructors() -> None:
    sources = _src()
    found = {(name, builder) for name, text in sources for builder, _line, _owner in _builder_sites(ast.parse(text))}
    assert {b for _n, b in found} == set(_BUILDERS), f"a builder has no site left in src/, so the scan has gone blind for it: {sorted(found)}"
    problems = [p for name, text in sources for p in _constructor_problems(name, text)]
    assert not problems, "\n".join(problems)


def test_every_chunk_call_in_src_names_its_owner() -> None:
    problems = [p for name, text in _src() for p in _owner_problems(name, text)]
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_generated_devices_construct_every_instance_once_at_the_top_of_build_system(device: str) -> None:
    source, _owners = _generated(device)
    problems = _construction_problems(device, source)
    assert not problems, "\n".join(problems)


def test_every_owner_across_the_devices_has_its_own_seed_at_every_width() -> None:
    owners = _all_owners()
    assert any(o.endswith(_VOC_SUFFIX) for o in owners), "no SGP40 backup owner derived: the owner list has gone blind"
    problems = _seed_problems(owners)
    assert not problems, "\n".join(problems)


# --- bites --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "class C:\n    def setup(self):\n        self.c = fram.get_chunk(8, crc=CRC8(), owner='X')\n",
        "def build():\n    return make_logger(log, 'X')\n",
        "class C:\n    def __init__(self):\n        def later():\n            return ConfigManager(p, s, 'X')\n        self.f = later\n",
        "STORE = PrintLogHistoryStore(fram, 8, 0, name='X')\n",
    ],
)
def test_the_constructor_check_bites(body: str) -> None:
    assert _constructor_problems("asy_x.py", body)


def test_the_constructor_check_passes_a_constructor_site() -> None:
    assert not _constructor_problems("asy_x.py", "class C:\n    def __init__(self):\n        self.c = fram.get_chunk(8, crc=CRC8(), owner='X')\n")


def test_the_owner_check_bites() -> None:
    assert _owner_problems("asy_x.py", "x = fram.get_timestamped_chunk(8, synced, crc=CRC32())\n")
    assert not _owner_problems("asy_x.py", "x = fram.get_timestamped_chunk(8, synced, crc=CRC32(), owner='X_VOC')\n")


@pytest.mark.parametrize(
    "body",
    [
        "async def build_system():\n    if flag:\n        fram = FRAMManager(spi0, 5)\n",
        "async def build_system():\n    fram = FRAMManager(spi0, 5)\n\ndef _restart():\n    return FRAMManager(spi0, 5)\n",
        "async def build_system():\n    for _ in range(2):\n        fram = FRAMManager(spi0, 5)\n",
        "async def build_system():\n    pass\n",
    ],
)
def test_the_generated_construction_check_bites(body: str) -> None:
    assert _construction_problems("x", "fram: FRAMManager | None = None\n" + body)


def test_the_seed_check_bites_on_a_planted_collision() -> None:
    owners = _all_owners()
    target = owners[0]
    planted = next(f"PLANT{i}" for i in range(1 << 16) if _seed(f"PLANT{i}", 1) == _seed(target, 1))
    problems = _seed_problems([*owners, planted])
    assert any(target in p and planted in p for p in problems), problems
