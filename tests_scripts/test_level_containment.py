"""Level containment, checked rather than stated (SPECIFICATION.md E.6.1, E.6.6): every twin scenario
has an adapted L3/L4 counterpart (COVERS_TWIN_SCENARIOS) or an E.6.6 exception row, bench contains
flash, and no row outlives its gap. Reads source by AST and the SPEC table as text; imports nothing."""

import ast
import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

_TWIN_PREFIX = "test_digital_twin_"
_CI_SUITE = "scripts/_digital_twin_ci_suite.py"
_FLASH_HAZARDS = "tests_hardware/flash/test_bus_concurrency.py"
_BENCH_HAZARDS = "tests_hardware/bench/test_bus_concurrency_under_api_load.py"
_BENCH_RUNNER = "scripts/run_bench_hardware_suite.sh"
_COUNTERPART_RE = re.compile(r"#\s*Bench counterpart:\s*(?:bench/test_bus_concurrency_under_api_load\.py::(\w+)|none, E\.6\.6 row `([\w-]+)`)")


def _families(repo_root: Path) -> "dict[str, set[str]]":
    # stem -> the devices it was collapsed from (empty for a scenario that is not per device).
    found: dict[str, set[str]] = {}
    for path in sorted((repo_root / "tests").glob(f"{_TWIN_PREFIX}*.py")):
        stem = path.stem[len(_TWIN_PREFIX) :]
        device = next((d for d in DEVICE_NAMES if stem.endswith(f"_{d}")), None)
        if device is None:
            found.setdefault(stem, set())
        else:
            found.setdefault(stem[: -len(device) - 1], set()).add(device)
    return found


def _ci_suite_ids(repo_root: Path) -> "set[str]":
    # Every function run_suite() calls, read from its body: one scenario each.
    tree = ast.parse((repo_root / _CI_SUITE).read_text())
    run_suite = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_suite")
    ids = {f"ci_suite.{node.func.id}" for node in ast.walk(run_suite) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id.startswith("_run_")}
    assert len(ids) >= 10, f"run_suite() calls only {sorted(ids)} - the scan has stopped seeing its runs"
    return ids


def _twin_ids(repo_root: Path) -> "set[str]":
    return set(_families(repo_root)) | _ci_suite_ids(repo_root)


def _level_modules(repo_root: Path) -> "list[Path]":
    return sorted((repo_root / "tests_hardware" / "flash").glob("test_*.py")) + sorted((repo_root / "tests_hardware" / "bench").glob("test_*.py"))


def _declared(path: Path) -> "tuple[str, ...] | None":
    for node in ast.parse(path.read_text()).body:
        target: ast.expr
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == "COVERS_TWIN_SCENARIOS":
            assert isinstance(value, ast.Tuple) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts), f"{path.name}: COVERS_TWIN_SCENARIOS must be a tuple of string literals"
            return tuple(e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str))
    return None


def _covered(repo_root: Path) -> "dict[str, list[str]]":
    # scenario id -> the L3/L4 modules naming it.
    covered: dict[str, list[str]] = {}
    for path in _level_modules(repo_root):
        for scenario in _declared(path) or ():
            covered.setdefault(scenario, []).append(str(path.relative_to(repo_root)))
    return covered


def _exception_rows(repo_root: Path) -> "list[dict[str, str]]":
    # E.6.6's table, cells keyed by header; the section ends at the next heading.
    text = (repo_root / "SPECIFICATION.md").read_text()
    start = re.search(r"^### E\.6\.6 .*$", text, re.MULTILINE)
    assert start is not None, "SPECIFICATION.md has no E.6.6 section"
    section = text[start.end() :]
    end = re.search(r"^#{1,3} ", section, re.MULTILINE)
    lines = [ln.strip() for ln in section[: end.start() if end else None].splitlines() if ln.strip().startswith("|")]
    assert len(lines) >= 2, "E.6.6 holds no exception table"
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    assert {"ID", "Scenario/behaviour", "Reason"} <= set(header), f"E.6.6's table header is {header}"
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def _row_id(row: "dict[str, str]") -> str:
    return row.get("ID", "").strip("`")


def _named_scenarios(row: "dict[str, str]", twin_ids: "set[str]") -> "set[str]":
    # A row names a scenario by a code span holding its ID or its test file's stem.
    spans = set(re.findall(r"`([^`]+)`", row.get("Scenario/behaviour", "")))
    return {s.removeprefix(_TWIN_PREFIX) for s in spans if s.removeprefix(_TWIN_PREFIX) in twin_ids or s.startswith((_TWIN_PREFIX, "ci_suite."))}


def test_every_level_module_declares_the_twin_scenarios_it_covers(repo_root: Path) -> None:
    missing = [str(p.relative_to(repo_root)) for p in _level_modules(repo_root) if _declared(p) is None]
    assert not missing, f"L3/L4 modules without COVERS_TWIN_SCENARIOS: {missing}"


def test_every_twin_scenario_is_covered_or_an_exception_row_with_a_reason(repo_root: Path) -> None:
    twin_ids = _twin_ids(repo_root)
    covered = _covered(repo_root)
    excepted = {s for row in _exception_rows(repo_root) if row.get("Reason", "").strip() for s in _named_scenarios(row, twin_ids)}
    uncovered = sorted(twin_ids - set(covered) - excepted)
    assert not uncovered, f"twin scenarios with neither an L3/L4 counterpart nor an E.6.6 row with a reason: {uncovered}"


def test_every_scenario_named_anywhere_exists(repo_root: Path) -> None:
    twin_ids = _twin_ids(repo_root)
    unknown = {s: modules for s, modules in _covered(repo_root).items() if s not in twin_ids}
    assert not unknown, f"COVERS_TWIN_SCENARIOS names scenarios that do not exist: {unknown}"
    stale_rows = {_row_id(row): sorted(gone) for row in _exception_rows(repo_root) if (gone := _named_scenarios(row, twin_ids) - twin_ids)}
    assert not stale_rows, f"E.6.6 rows name scenarios that do not exist: {stale_rows}"


def test_no_exception_row_names_a_covered_scenario(repo_root: Path) -> None:
    twin_ids = _twin_ids(repo_root)
    covered = _covered(repo_root)
    stale = {_row_id(row): sorted(both) for row in _exception_rows(repo_root) if (both := _named_scenarios(row, twin_ids) & set(covered))}
    assert not stale, f"E.6.6 rows for scenarios an L3/L4 module now covers: {stale}"


def test_every_per_device_family_spans_the_device_set(repo_root: Path) -> None:
    families = {name: devices for name, devices in _families(repo_root).items() if devices}
    assert families, "no per-device twin family found - the collapse has stopped seeing them"
    short = {name: sorted(set(DEVICE_NAMES) - devices) for name, devices in families.items() if devices != set(DEVICE_NAMES)}
    assert not short, f"per-device twin families missing devices of devices/*.toml: {short}"


def test_the_bench_runner_runs_the_flash_level_too(repo_root: Path) -> None:
    text = (repo_root / _BENCH_RUNNER).read_text()
    assert "tests_hardware/flash" in text, f"{_BENCH_RUNNER} no longer runs tests_hardware/flash - bench must contain flash"


def _flash_hazard_tests(repo_root: Path) -> "dict[str, list[str]]":
    # test name -> the comment lines directly above its decorators and def.
    lines = (repo_root / _FLASH_HAZARDS).read_text().splitlines()
    found: dict[str, list[str]] = {}
    for node in ast.parse("\n".join(lines)).body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)]) - 1
            block: list[str] = []
            while first > 0 and lines[first - 1].lstrip().startswith("#"):
                first -= 1
                block.insert(0, lines[first])
            found[node.name] = block
    return found


@pytest.mark.parametrize("test_name", sorted(_flash_hazard_tests(Path(__file__).resolve().parent.parent)))
def test_every_flash_bus_hazard_test_names_its_bench_counterpart_or_a_row(repo_root: Path, test_name: str) -> None:
    bench = {n.name for n in ast.parse((repo_root / _BENCH_HAZARDS).read_text()).body if isinstance(n, ast.FunctionDef)}
    rows = {_row_id(row) for row in _exception_rows(repo_root)}
    named = [m.groups() for line in _flash_hazard_tests(repo_root)[test_name] if (m := _COUNTERPART_RE.search(line))]
    assert len(named) == 1, f"{test_name} must carry exactly one '# Bench counterpart:' line above it, found {named}"
    counterpart, row = named[0]
    if counterpart is not None:
        assert counterpart in bench, f"{test_name} names {counterpart}, which {_BENCH_HAZARDS} does not define"
    else:
        assert row in rows, f"{test_name} names E.6.6 row {row!r}, which the table does not hold"
