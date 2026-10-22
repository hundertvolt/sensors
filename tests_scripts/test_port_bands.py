"""tests/_port_bands.py, the one table of test port bands (SPECIFICATION.md E.1): its rows are disjoint and below the
OS ephemeral range, an allocator never leaves its band, and a per-device band splits over the generated devices, so a
seventh device shrinks each block rather than running into a neighbour's band."""

import ast
import json
import re
import sys
import types
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPO = Path(__file__).resolve().parent.parent
_EPHEMERAL_FIRST = 32768  # Linux's default net.ipv4.ip_local_port_range starts here


@pytest.fixture
def port_bands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> "Iterator[types.ModuleType]":
    # tests/_port_bands.py under CPython over a fixture generated tree; its _twin_devices import resolves to the copy
    # registered first, and both leave sys.modules again.
    try:
        devices = load_script_module(_REPO / "tests" / "_twin_devices.py", "_twin_devices")
        monkeypatch.setattr(devices, "_TREE", str(tmp_path))
        yield load_script_module(_REPO / "tests" / "_port_bands.py", "_port_bands")
    finally:
        for name in ("_port_bands", "_twin_devices"):
            sys.modules.pop(name, None)


def _plant_devices(tree: Path, devices: "list[str]") -> None:
    for device in devices:
        (tree / f"sensortask_{device}_wiring_plan.json").write_text(json.dumps({"device": device, "instances": []}), encoding="utf-8")


def test_every_row_is_a_valid_range_below_the_ephemeral_range(port_bands: types.ModuleType) -> None:
    bad = {owner: row for owner, row in port_bands.BANDS.items() if not (1024 <= row[0] <= row[1] < _EPHEMERAL_FIRST and row[2] in ("tcp", "udp"))}
    assert bad == {}


def test_no_two_rows_of_one_protocol_overlap(port_bands: types.ModuleType) -> None:
    rows = sorted((protocol, first, last, owner) for owner, (first, last, protocol) in port_bands.BANDS.items())
    overlaps = [(a[3], b[3]) for a, b in pairwise(rows) if a[0] == b[0] and b[1] <= a[2]]
    assert overlaps == []


def test_every_per_device_owner_has_a_row(port_bands: types.ModuleType) -> None:
    assert port_bands.PER_DEVICE_OWNERS
    assert [owner for owner in port_bands.PER_DEVICE_OWNERS if owner not in port_bands.BANDS] == []


def test_every_row_names_an_owner_that_still_exists(port_bands: types.ModuleType) -> None:
    # A retired owner's row holds its band for nothing and hides that the file is gone: each owner is a module of the
    # tree, or the name a PortAllocator() call passes.
    modules = {p.stem for d in ("src", "tests", "digital_twin", "scripts", "tests_js") for p in (_REPO / d).iterdir() if p.suffix in {".py", ".js", ".mjs"}}
    callers = {m for d in ("tests", "scripts", "digital_twin") for p in (_REPO / d).glob("*.py") for m in re.findall(r'PortAllocator\("(\w+)"', p.read_text(encoding="utf-8"))}
    assert sorted(set(port_bands.BANDS) - modules - callers) == []


def test_an_allocator_hands_out_its_band_in_order_then_fails_naming_it(port_bands: types.ModuleType) -> None:
    owner = next(o for o, (first, last, _) in port_bands.BANDS.items() if last - first >= 2)
    first, last, _ = port_bands.BANDS[owner]
    ports = port_bands.PortAllocator(owner)
    assert [ports.next() for _ in range(last - first + 1)] == list(range(first, last + 1))
    with pytest.raises(AssertionError, match=rf"^{owner} ran past its port band {first}-{last}$"):
        ports.next()


def test_an_owner_without_a_row_is_refused(port_bands: types.ModuleType) -> None:
    with pytest.raises(KeyError, match="test_nobody"):
        port_bands.PortAllocator("test_nobody")


def test_a_taken_port_names_its_band(port_bands: types.ModuleType) -> None:
    owner = port_bands.PER_DEVICE_OWNERS[0]
    error = port_bands.PortAllocator(owner).taken(19999)
    assert isinstance(error, OSError)
    assert str(error.args[-1]) == f"port 19999 (band {owner}) is taken"


@pytest.mark.parametrize("extra", [0, 1])
def test_each_device_gets_a_disjoint_block_inside_the_band(port_bands: types.ModuleType, tmp_path: Path, extra: int) -> None:
    # The real devices, and one more: a further TOML shrinks each block instead of overflowing the band.
    devices = sorted([*DEVICE_NAMES, *(f"fixture-device-{i}" for i in range(extra))])
    _plant_devices(tmp_path, devices)
    for owner in port_bands.PER_DEVICE_OWNERS:
        first, last, _ = port_bands.BANDS[owner]
        blocks = [port_bands.band_for_device(owner, device) for device in devices]
        assert all(first <= lo <= hi <= last for lo, hi in blocks), (owner, blocks)
        assert all(a[1] < b[0] for a, b in pairwise(blocks)), (owner, blocks)
        ports = port_bands.PortAllocator(owner, devices[-1])
        assert ports.next() == blocks[-1][0]


def test_a_per_device_band_refuses_an_unknown_device_and_a_shared_owner(port_bands: types.ModuleType, tmp_path: Path) -> None:
    _plant_devices(tmp_path, ["fixture-device"])
    owner = port_bands.PER_DEVICE_OWNERS[0]
    with pytest.raises(AssertionError, match=r"'fixture-device-x' is not a generated device \['fixture-device'\]"):
        port_bands.band_for_device(owner, "fixture-device-x")
    shared = next(o for o in port_bands.BANDS if o not in port_bands.PER_DEVICE_OWNERS)
    with pytest.raises(AssertionError, match=rf"{shared} has no per-device band"):
        port_bands.band_for_device(shared, "fixture-device")


_PORT_CALLS = ("start_server", "fetch", "bind", "connect", "open_connection")  # getaddrinfo() resolves, never binds


def _literal_ports(tree: ast.Module) -> "list[int]":
    # Every port a file states as a literal: a port-named assignment, a port keyword, or a socket call's argument.
    found: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and "port" in t.id.lower() for t in node.targets):
            found.append(node.value)
        if isinstance(node, ast.keyword) and node.arg and "port" in node.arg.lower():
            found.append(node.value)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in _PORT_CALLS:
            found += node.args
    return [n.value for n in found if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool) and 1024 <= n.value <= 65535]


def _named_owners(text: str) -> "list[str]":
    return re.findall(r"(?:PortAllocator|band_for_device)\(\s*\"([^\"]+)\"", text)


def test_every_test_file_that_binds_a_port_draws_it_from_its_band(port_bands: types.ModuleType) -> None:
    # Each binding module either allocates through a named row, or states only ports inside the row named after it.
    problems = []
    for path in sorted((_REPO / "tests").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        literals = _literal_ports(ast.parse(text))
        owners = _named_owners(text)
        if not (literals or owners or "_next_port" in text):
            continue
        unknown = [owner for owner in owners if owner not in port_bands.BANDS]
        row = port_bands.BANDS.get(path.stem)
        outside = [port for port in literals if row is None or not row[0] <= port <= row[1]]
        if unknown or (not owners and (outside or not literals)) or (owners and outside):
            problems.append(f"tests/{path.name}: rows {unknown or owners}, literal ports {literals} (its own row {row})")
    assert problems == []


@pytest.mark.parametrize(
    ("path", "pattern", "owner"),
    [
        ("tests_js/_live_twin_command.js", r"^const PORT = (\d+);$", "_live_twin_command"),
        ("tests_js/_live_matrix_command.js", r"^const PORT = (\d+);$", "_live_matrix_command"),
        ("scripts/cross_browser_smoke.mjs", r"^const (?:PROXY_)?PORT = (\d+);$", "cross_browser_smoke"),
        ("scripts/_digital_twin_ci_suite.py", r"^PORT = (\d+)\b", "_digital_twin_ci_suite"),
        ("digital_twin/unix_port_poll_prewarm.py", r"^_PORT_SCAN_BASE = (\d+)$", "unix_port_poll_prewarm"),
    ],
)
def test_each_fixed_row_holds_the_constant_its_owner_binds(port_bands: types.ModuleType, path: str, pattern: str, owner: str) -> None:
    # A port bound outside this table's allocators keeps its own constant; the row covers it, so no allocator can take it.
    ports = [int(p) for p in re.findall(pattern, (_REPO / path).read_text(encoding="utf-8"), re.MULTILINE)]
    first, last, _ = port_bands.BANDS[owner]
    assert ports and all(first <= port <= last for port in ports), (ports, (first, last))


def test_the_prewarm_scan_window_fits_its_row(port_bands: types.ModuleType) -> None:
    text = (_REPO / "digital_twin" / "unix_port_poll_prewarm.py").read_text(encoding="utf-8")
    base, window = (int(re.search(rf"^{name} = (\d+)$", text, re.MULTILINE).group(1)) for name in ("_PORT_SCAN_BASE", "_PORT_SCAN_WINDOW"))  # type: ignore[union-attr]
    assert (base, base + window - 1) == port_bands.BANDS["unix_port_poll_prewarm"][:2]
