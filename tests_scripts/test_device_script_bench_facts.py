"""Device scripts take every board fact from BENCH (tests_hardware/bench_facts.py, rendered by the harness): no pin, bus
or address literal, no device module but the one rendered import, no key build() does not return; the type stub
matches build(), and README's "Bench facts" table dates and sources every filled row."""

import ast
import re
import sys
from functools import cache
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, bench_device

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import bench_facts
import harness

_SCRIPTS = Path(__file__).resolve().parents[1] / "tests_hardware" / "device_scripts"
_README = Path(__file__).resolve().parents[1] / "tests_hardware" / "README.md"
_HARDWARE_CALLS = frozenset({"I2C", "SPI", "UART", "Pin", "NeopixelDriver", "NeoPixel"})
_PIN_OR_BUS = re.compile(r"(pin|^id$|^port_id$|^bus$|^scl$|^sda$|^sck$|^mosi$|^miso$|^tx$|^rx$|^cs$)")
_REGISTER_NAME = re.compile(r"(^_?REG|_REG)")
_DRIVER_ADDRESS = re.compile(r"^_\w*ADDR\w* = const\((0x[0-9A-Fa-f]+)\)", re.MULTILINE)
_LIMITED_ADDRESS = re.compile(r"^# @limits address in \{([^}]*)\}", re.MULTILINE)
_EXTRAS_MARKER = "# Per-run extras"


def _scripts(scripts_dir: Path = _SCRIPTS) -> "list[Path]":
    return sorted(scripts_dir.glob("*.py"))


def _call_name(call: ast.Call) -> str:
    return call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")


def _int_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)


@cache
def _driver_addresses(src: Path = _SCRIPTS.parents[1] / "src") -> "frozenset[int]":
    # Every I2C device address a src/ driver binds (a 7-bit _..._ADDR const or its @limits address set).
    texts = [path.read_text(encoding="utf-8") for path in src.glob("asy_*_driver.py")]
    values = {int(m.group(1), 16) for text in texts for m in _DRIVER_ADDRESS.finditer(text)}
    values |= {int(v, 0) for text in texts for m in _LIMITED_ADDRESS.finditer(text) for v in m.group(1).split(",")}
    return frozenset(v for v in values if v < 0x80)


def _literal_findings(path: Path) -> "list[str]":
    # Pin/bus literals in a hardware constructor, a sensortask_ or dynamic import, a copied address or register constant.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) in _HARDWARE_CALLS:
            literal_args = [a for a in node.args if _int_literal(a)] + [kw.value for kw in node.keywords if kw.arg and _PIN_OR_BUS.search(kw.arg) and _int_literal(kw.value)]
            found += [f"{path.name}:{node.lineno} {_call_name(node)}() takes a pin or bus literal" for _ in literal_args[:1]]
        elif isinstance(node, ast.Call) and _call_name(node) == "__import__":
            found.append(f"{path.name}:{node.lineno} __import__()")
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names = [node.module or ""] if isinstance(node, ast.ImportFrom) else [alias.name for alias in node.names]
            found += [f"{path.name}:{node.lineno} imports {name}" for name in names if name.startswith(("sensortask_", "importlib"))]
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and _int_literal(node.value):
            # A conformance probe keeps its register map (datasheet values); its address still comes from BENCH.
            copied = node.value.value in _driver_addresses()
            for target in [t for t in node.targets if isinstance(t, ast.Name)]:
                if ("ADDR" in target.id and copied) or (_REGISTER_NAME.search(target.id) and not path.name.endswith("_conformance_probe.py")):
                    found.append(f"{path.name}:{node.lineno} binds {target.id} to a literal")
    return found


def test_no_script_carries_a_board_literal_or_another_device_module() -> None:
    found = [line for path in _scripts() for line in _literal_findings(path)]
    assert not found, "board facts belong in BENCH, the device module in the one rendered import:\n  " + "\n  ".join(found)


def _device_imports(path: Path) -> "list[str]":
    return [line for line in path.read_text(encoding="utf-8").splitlines() if re.match(r"\s*(import|from)\s+_bench_device\b", line)]


def test_the_device_module_comes_only_through_the_rendered_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    users = {path: lines for path in _scripts() if (lines := _device_imports(path))}
    malformed = {path.name: lines for path, lines in users.items() if len(lines) != 1 or not lines[0].startswith(harness._DEVICE_IMPORT)}
    assert not malformed, f"a script imports the device module other than through the one marked line: {malformed}"
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path)
    module = bench_facts.build(bench_device())["device_module"]
    for path in users:
        rendered = harness.render_device_script(path).read_text(encoding="utf-8")
        assert f"import {module} as device  # rendered: " in rendered and "_bench_device" not in rendered, path.name


def test_the_device_stub_declares_every_attribute_a_script_reads() -> None:
    stub = ast.parse((_SCRIPTS / "_bench_device.pyi").read_text(encoding="utf-8"))
    declared = {n.target.id for n in stub.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    declared |= {n.name for n in stub.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
    used = {f"{path.name}: device.{n.attr}" for path in _scripts() for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "device" and n.attr not in declared}
    assert not used, f"_bench_device.pyi does not declare: {sorted(used)}"


def _stub_keys() -> "tuple[set[str], set[str]]":
    # BenchFacts' keys in bench_facts.pyi: (those build() returns, the per-run extras declared after the marker comment).
    lines = (_SCRIPTS / "bench_facts.pyi").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("class BenchFacts("))
    marker = next(i for i, line in enumerate(lines) if i > start and line.strip().startswith(_EXTRAS_MARKER))
    key = re.compile(r"^    (\w+): ")
    built = {m.group(1) for line in lines[start:marker] if (m := key.match(line))}
    extras = {m.group(1) for line in lines[marker:] if (m := key.match(line))}
    return built, extras


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_stub_keys_are_build_keys_plus_the_declared_extras(device: str) -> None:
    built, extras = _stub_keys()
    assert set(bench_facts.build(device)) == built, f"bench_facts.pyi and build({device!r}) disagree"
    assert not built & extras, f"an extra shadows a fact: {sorted(built & extras)}"


def _bench_keys(path: Path) -> "set[str]":
    # Every BENCH["key"] and BENCH.get("key") a script reads.
    keys: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "BENCH" and isinstance(node.slice, ast.Constant):
            keys.add(str(node.slice.value))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and isinstance(node.func.value, ast.Name) and node.func.value.id == "BENCH" and node.args and isinstance(node.args[0], ast.Constant):
            keys.add(str(node.args[0].value))
    return keys


def test_every_bench_key_a_script_reads_is_a_fact_or_a_declared_extra() -> None:
    assert any(_bench_keys(path) for path in _scripts()), "no script reads a BENCH key - the scan reads nothing"
    _, extras = _stub_keys()
    facts = set(bench_facts.build(bench_device()))
    unknown = {path.name: sorted(keys - facts - extras) for path in _scripts() if (keys := _bench_keys(path)) - facts - extras}
    assert not unknown, f"BENCH keys neither build() nor a declared extra provides: {unknown}"


def _bench_facts_rows(readme: str) -> "list[list[str]] | None":
    # The "### Bench facts" table's body rows as cells, or None when the section is missing.
    section = re.search(r"^### Bench facts\n(.*?)(?=^#{1,3} |\Z)", readme, re.MULTILINE | re.DOTALL)
    if section is None:
        return None
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in section.group(1).splitlines() if line.strip().startswith("|")]
    return [row for row in rows[1:] if not all(set(cell) <= set("-: ") for cell in row)]


def _undated_rows(rows: "list[list[str]]") -> "list[str]":
    # fact | value | source | date: a filled row (a value that is not "to be read ...") names its source and a date.
    return [row[0] for row in rows if len(row) >= 4 and not row[1].lower().startswith("to be read") and (not row[2] or not re.search(r"\d{4}-\d{2}-\d{2}", row[3]))]


def test_the_bench_facts_table_dates_and_sources_every_filled_row() -> None:
    rows = _bench_facts_rows(_README.read_text(encoding="utf-8"))
    assert rows is not None, 'tests_hardware/README.md has no "### Bench facts" table'
    assert rows, "the Bench facts table has no rows"
    assert not _undated_rows(rows), f"filled rows without a source or a date: {_undated_rows(rows)}"


def test_the_bench_facts_checks_bite(tmp_path: Path) -> None:
    script = tmp_path / "bite.py"
    script.write_text("import sensortask_fixture\nSCD30_ADDR = 0x61\ni2c = I2C(0, scl_pin=5, sda_pin=4)\nx = BENCH['no_such_fact']\n", encoding="utf-8")
    assert [line.split(" ", 1)[1] for line in _literal_findings(script)] == ["imports sensortask_fixture", "binds SCD30_ADDR to a literal", "I2C() takes a pin or bus literal"]
    assert _bench_keys(script) == {"no_such_fact"}
    table = "### Bench facts\n\n| fact | value | source | date |\n|---|---|---|---|\n| FRAM part | MB85RS2MTA | fram_raw_dump.py | |\n| BME688 | to be read in R0 | | |\n"
    rows = _bench_facts_rows(table)
    assert rows is not None and _undated_rows(rows) == ["FRAM part"]
