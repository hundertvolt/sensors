"""SPECIFICATION.md Part L.3's device-TOML key table equals what the build accepts: every (table, key,
required) row against validate.py's and buildspec.py's tables and each driver's own wiring tags, both
ways, so a key added, dropped or made required anywhere fails here until the other side follows."""

import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

import buildgen.validate as validate_mod
from buildgen.buildspec import OPTIONAL_TOML_FIELDS, REQUIRED_TOML_FIELDS
from buildgen.driver_registry import SINGLETON_SERVICE_DRIVERS, resolve_driver
from buildgen.signals import WARN_SIGNALS
from buildgen.value_wiring import parse_value_wiring
from buildgen.wiring import parse_wiring

_BEGIN, _END = "<!-- toml-schema-table -->", "<!-- /toml-schema-table -->"
_HEADER = ("Table", "Key", "Required", "Type / range", "Consumer")
# Required beyond each bus kind's wire pins, as validate.py's _check_i2c_bus()/_check_uart_bus() refuse their absence.
_BUS_REQUIRED_EXTRA = {"i2c": frozenset({"frequency"}), "spi": frozenset(), "uart": frozenset({"baudrate"})}
_BUS_TABLES = {"i2c": "[bus.i2cN]", "spi": "[bus.spiN]", "uart": "[bus.uartN]"}

_Row = tuple[str, str, bool]


def _spec_rows(spec_text: str) -> "set[_Row]":
    # The marked table's (table, key, required) rows: backticks dropped, Required read as yes/no.
    assert _BEGIN in spec_text and _END in spec_text, f"SPECIFICATION.md carries no {_BEGIN} ... {_END} block in Part L.3"
    block = spec_text.split(_BEGIN, 1)[1].split(_END, 1)[0]
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    cells = [[cell.strip().replace("`", "") for cell in line.strip("|").split("|")] for line in lines]
    assert cells and tuple(cells[0]) == _HEADER, f"the table's header is {cells[:1]}, expected {_HEADER}"
    rows: set[_Row] = set()
    for row in cells[2:]:  # past the header and its |---| rule
        assert len(row) == len(_HEADER) and row[2] in ("yes", "no"), f"malformed row {row}"
        rows.add((row[0], row[1], row[2] == "yes"))
    return rows


def _build_rows(src_dir: Path) -> "set[_Row]":
    # The same rows read from the build: the validator's own tables, buildspec's, and every driver's tags.
    rows: set[_Row] = {("[device]", key, key in validate_mod._REQUIRED_DEVICE_FIELDS) for key in validate_mod._ALLOWED_DEVICE_FIELDS - {"wiring"}}
    for key, consumers in validate_mod._DEVICE_WIRING_CONSUMERS.items():
        tags = [wf for f, label in consumers for wf in parse_wiring(src_dir / f, "schema", label) if wf.toml_field == key]
        rows.add(("[device.wiring]", key, any(wf.required for wf in tags)))
    for kind, table in _BUS_TABLES.items():
        required = frozenset(validate_mod._BUS_WIRE_FIELDS[kind]) | _BUS_REQUIRED_EXTRA[kind]
        rows |= {(table, key, key in required) for key in validate_mod._BUS_ALLOWED_FIELDS[kind]}
    for driver in REQUIRED_TOML_FIELDS:
        table = f"[[instance]] {driver}"
        rows |= {(table, "driver", True), (table, "name_ext", driver not in SINGLETON_SERVICE_DRIVERS)}
        rows |= {(table, key, True) for key in REQUIRED_TOML_FIELDS[driver]} | {(table, key, False) for key in OPTIONAL_TOML_FIELDS[driver]}
        path = resolve_driver(driver, src_dir, "schema").source_path
        wiring = f"[instance.wiring] {driver}"
        rows |= {(wiring, wf.toml_field, wf.required) for wf in parse_wiring(path, "schema", driver)}
        rows |= {(wiring, vwf.toml_field, vwf.required) for vwf in parse_value_wiring(path, "schema", driver)}
        if driver == "notification":
            rows |= {(wiring, key, False) for key in WARN_SIGNALS}
    return rows


@pytest.fixture(scope="module")
def spec_text(repo_root: Path) -> str:
    return (repo_root / "SPECIFICATION.md").read_text()


def test_the_l3_key_table_equals_the_builds_tables(spec_text: str, repo_root: Path) -> None:
    documented, built = _spec_rows(spec_text), _build_rows(repo_root / "src")
    missing, extra = sorted(built - documented), sorted(documented - built)
    assert not missing and not extra, f"SPECIFICATION.md L.3's key table lacks {missing} and states {extra} the build does not take"


def test_the_l3_key_table_names_no_device(spec_text: str) -> None:
    # The schema is the same for every device: the table carries no device name, the devices carry their values.
    rows = _spec_rows(spec_text)
    named = sorted(row for row in rows for device in DEVICE_NAMES if re.search(rf"\b{device}\b", " ".join(map(str, row)), re.IGNORECASE))
    assert not named, f"the key table names a device: {named}"


def test_the_build_side_is_never_empty(repo_root: Path) -> None:
    # Guard: a table read that went empty would make the comparison above vacuous.
    tables = {table for table, _key, _required in _build_rows(repo_root / "src")}
    assert {"[device]", "[device.wiring]", "[bus.i2cN]", "[bus.spiN]", "[bus.uartN]"} <= tables
    assert {f"[[instance]] {driver}" for driver in REQUIRED_TOML_FIELDS} <= tables
