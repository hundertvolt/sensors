"""Raw FRAM access in a device script stays off the production layout: every raw set_values/get_values call is
addressed from the script's declared _SCRATCH_REGIONS (or _EVIDENCE_REGIONS, a production read), scratch regions of
different scripts are disjoint, and each lies between the bench build's allocated FRAM and the part's end."""

import ast
import operator
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import bench_device

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import bench_facts

if TYPE_CHECKING:
    from collections.abc import Callable

_SCRIPTS = Path(__file__).resolve().parents[1] / "tests_hardware" / "device_scripts"
_RAW_CALLS = frozenset({"set_values", "get_values", "set_values_sync", "get_values_sync"})
_REGIONS = ("_SCRATCH_REGIONS", "_EVIDENCE_REGIONS")
# The twin boot test_digital_twin_boot_contiguity.py measures with: scripts/test.sh's own path and heap size.
_MICROPYPATH = "build/generated_src:src:tests:frozen_modules:.frozen"
# @tunable l1.unix_heapsize = 16M
_HEAPSIZE = "16M"
# @tunable l0.fram_regions_boot_timeout_s = 120
_BOOT_TIMEOUT_S = 120
_ALLOCATION_PROBE = """
import sys
sys.path.insert(0, "ext")
import asy_spi_driver
from _async_harness import run
from _generated_module import boot_generated, fram_fake_class

asy_spi_driver._SPI = fram_fake_class(sys.argv[1])  # the FRAM fake in place before the module binds its drivers
import {module} as device_module


async def _main(device, cfg_path):
    module, _ = await boot_generated(device_module, device, cfg_path=cfg_path, web_host="127.0.0.1", web_port=0)
    print("FRAM_ALLOCATED=%d" % module.fram._allocated_size)
    return 0


sys.exit(run(_main(sys.argv[1], sys.argv[2])))
"""


def _call_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")


def _bindings(tree: ast.Module) -> "dict[str, list[ast.expr]]":
    # Every name's bound values anywhere in the script: assignments and for-loop targets (bound from their iterable).
    found: dict[str, list[ast.expr]] = {}
    for node in ast.walk(tree):
        pairs = [(t, node.value) for t in node.targets] if isinstance(node, ast.Assign) else [(node.target, node.value)] if isinstance(node, ast.AnnAssign | ast.AugAssign) and node.value is not None else [(node.target, node.iter)] if isinstance(node, ast.For) else []
        for target, value in pairs:
            for name in [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]:
                found.setdefault(name, []).append(value)
    return found


def _derives_from(node: ast.expr, bindings: "dict[str, list[ast.expr]]", wanted: "tuple[str, ...]") -> bool:
    # Whether `node` reads one of `wanted`, directly or through any chain of bindings.
    seen: set[str] = set()
    pending = [node]
    while pending:
        current = pending.pop()
        for name in [n.id for n in ast.walk(current) if isinstance(n, ast.Name)]:
            if name in wanted:
                return True
            if name not in seen:
                seen.add(name)
                pending += bindings.get(name, [])
    return False


def _address(call: ast.Call) -> "ast.expr | None":
    return call.args[1] if len(call.args) > 1 else next((kw.value for kw in call.keywords if kw.arg == "addr_start"), None)


def undeclared_raw_calls(source: str) -> "list[int]":
    # Lines of raw calls addressed neither from a declared region nor through a get_chunk() result's block address.
    tree = ast.parse(source)
    bindings = _bindings(tree)
    chunked = "._block_addr" in source and "get_chunk(" in source
    found: list[int] = []
    scopes: list[ast.AST] = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)] or [tree]
    for fn in scopes:
        chunk_scoped = chunked and "block_addr" in ast.unparse(fn)
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call) and _call_name(n) in _RAW_CALLS]:
            address = _address(call)
            if address is None or not (_derives_from(address, bindings, _REGIONS) or chunk_scoped):
                found.append(call.lineno)
    return sorted(set(found))


_ARITHMETIC: "dict[type[ast.operator], Callable[[int, int], int]]" = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv}


def _evaluate(node: ast.expr, facts: "dict[str, object]") -> object:
    # A region literal: numbers, tuples, + - * // and BENCH["key"]; anything else is no declaration this check reads.
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Tuple | ast.List):
        return tuple(_evaluate(e, facts) for e in node.elts)
    if isinstance(node, ast.BinOp) and type(node.op) in _ARITHMETIC:
        left, right = _evaluate(node.left, facts), _evaluate(node.right, facts)
        if isinstance(left, int) and isinstance(right, int):
            return _ARITHMETIC[type(node.op)](left, right)
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "BENCH" and isinstance(node.slice, ast.Constant):
        return facts[str(node.slice.value)]
    raise ValueError(f"not a region literal: {ast.unparse(node)}")


def _regions(source: str, facts: "dict[str, object]") -> "dict[str, list[tuple[int, int]]]":
    # The declared region tuples, evaluated with the script's BENCH facts where they read one.
    regions: dict[str, list[tuple[int, int]]] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in _REGIONS:
            value = _evaluate(node.value, facts)
            pairs = [region for region in value if isinstance(region, tuple) and len(region) == 2 and all(isinstance(v, int) for v in region)] if isinstance(value, tuple) else []
            assert isinstance(value, tuple) and len(pairs) == len(value), f"{node.targets[0].id} is no tuple of (start, length): {value!r}"
            regions[node.targets[0].id] = [(int(start), int(length)) for start, length in pairs]
    return regions


def test_every_raw_fram_call_is_addressed_from_a_declared_region() -> None:
    raw = [p for p in _SCRIPTS.glob("*.py") if any(_call_name(n) in _RAW_CALLS for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))))]
    assert raw, "no script issues a raw FRAM call - the scan reads nothing"
    found = {path.name: lines for path in sorted(_SCRIPTS.glob("*.py")) if (lines := undeclared_raw_calls(path.read_text(encoding="utf-8")))}
    assert not found, f"raw FRAM calls whose address no _SCRATCH_REGIONS/_EVIDENCE_REGIONS declares (script: lines): {found}"


@pytest.fixture(scope="module")
def allocated_size(repo_root: Path, micropython_bin: Path, tmp_path_factory: pytest.TempPathFactory) -> int:
    # The bench build's FRAM allocation, read by booting its generated module under the Unix-port twin.
    work = tmp_path_factory.mktemp("fram_regions")
    probe = work / "fram_allocation_probe.py"
    probe.write_text(_ALLOCATION_PROBE.format(module=f"sensortask_{bench_device()}"), encoding="utf-8")
    ran = subprocess.run(
        [str(micropython_bin), "-X", f"heapsize={_HEAPSIZE}", str(probe), bench_device(), f"{work}/"],
        cwd=repo_root,
        env=dict(os.environ, MICROPYPATH=_MICROPYPATH, TZ="UTC"),
        capture_output=True,
        text=True,
        timeout=_BOOT_TIMEOUT_S,
        check=False,
    )
    match = re.search(r"^FRAM_ALLOCATED=(\d+)$", ran.stdout, re.MULTILINE)
    assert ran.returncode == 0 and match is not None, f"the twin boot of {bench_device()} reported no FRAM allocation (exit {ran.returncode}):\n{ran.stdout}\n{ran.stderr}"
    return int(match.group(1))


def _pair_stem(name: str) -> str:
    # A seed/verify script pair's shared name: fram_reset_race_during_write for its _seed_and_race and _verify_recovery.
    for marker in ("_seed", "_verify"):
        if marker in name:
            return name.split(marker, 1)[0]
    return name


def test_every_scratch_region_lies_above_the_allocation_and_regions_never_overlap(allocated_size: int) -> None:
    facts: dict[str, object] = dict(bench_facts.build(bench_device()))
    part_size = facts["fram_max_size"]
    assert isinstance(part_size, int), "the bench device wires no FRAM"
    declared = [(path.name, start, length) for path in sorted(_SCRIPTS.glob("*.py")) for start, length in _regions(path.read_text(encoding="utf-8"), facts).get("_SCRATCH_REGIONS", [])]
    assert declared, "no script declares _SCRATCH_REGIONS - the bounds below would hold vacuously"
    outside = [(name, hex(start), length) for name, start, length in declared if not (allocated_size <= start and start + length <= part_size)]
    assert not outside, f"scratch regions outside [{allocated_size}, {part_size}) - the bench build's allocated FRAM to the part's end: {outside}"
    # A seed script and its verify script share one region, the verify reading what the seed left: the same name
    # before "_seed"/"_verify" and the identical (start, length) is one pair's region, any other overlap a clash.
    overlaps = [(a[0], b[0]) for i, a in enumerate(declared) for b in declared[i + 1 :] if a[0] != b[0] and a[1] < b[1] + b[2] and b[1] < a[1] + a[2] and not (_pair_stem(a[0]) == _pair_stem(b[0]) and a[1:] == b[1:])]
    assert not overlaps, f"scratch regions of different scripts overlap: {overlaps}"


def test_the_session_saves_evidence_before_any_script_runs(repo_root: Path) -> None:
    # An _EVIDENCE_REGIONS script reads production FRAM: the autouse session fixture has saved it first.
    tree = ast.parse((repo_root / "tests_hardware" / "conftest.py").read_text(encoding="utf-8"))
    fixture = next((fn for fn in tree.body if isinstance(fn, ast.FunctionDef) and fn.name == "fram_evidence_saved"), None)
    assert fixture is not None, "tests_hardware/conftest.py no longer defines fram_evidence_saved"
    keywords = {kw.arg: kw.value.value for d in fixture.decorator_list if isinstance(d, ast.Call) for kw in d.keywords if isinstance(kw.value, ast.Constant)}
    assert keywords.get("scope") == "session" and keywords.get("autouse") is True, keywords


_BITES = {
    "_SCRATCH_REGIONS = ((0x3FF00, 0x100),)\n_A = _SCRATCH_REGIONS[0][0]\n\n\ndef f(chip, buf):\n    chip.set_values_sync(buf, _A + 8)\n": [],
    "def f(chip, buf):\n    chip.set_values_sync(buf, 0x100)\n": [2],
    "async def f(fram, buf):\n    for addr in range(0, 64, 8):\n        await fram.get_values(buf, addr_start=addr)\n": [3],
    "chunk = fram.get_chunk(8, crc=c, owner='x')\n\n\nasync def f(dev, block_addr):\n    await dev.set_values(b'\\x01', block_addr[0] + 9)\n\nf(d, chunk._block_addr)\n": [],
}


@pytest.mark.parametrize(("source", "lines"), list(_BITES.items()), ids=["from-region", "literal", "loop-literal", "chunk-scoped"])
def test_the_region_check_bites(source: str, lines: "list[int]") -> None:
    assert undeclared_raw_calls(source) == lines


def test_the_overlap_and_bounds_reading_bites() -> None:
    regions = _regions("_SCRATCH_REGIONS = ((BENCH['fram_max_size'] - 0x100, 0x100),)\n", {"fram_max_size": 0x40000})
    assert regions == {"_SCRATCH_REGIONS": [(0x3FF00, 0x100)]}
