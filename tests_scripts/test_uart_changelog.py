"""Ties UART_C_PORT_CHANGELOG.md to the protocol module: its constants table, its closed status set and its row order.
Deleted with the changelog at the post-audit C reconciliation."""

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "UART_C_PORT_CHANGELOG.md"
MODULE = REPO_ROOT / "src" / "asy_uart_comm.py"

_CONSTANTS_HEADING = "## Constants the check reads"
_CLASS_HEADINGS = {"A": "## Class A", "B": "## Class B"}
_CONSTANT_COLUMNS = ("Name", "Value", "Class", "Last entry")
_STATUSES = ("proposed", "applied-python", "recorded", "reconciled")
_LOG_CODE_PREFIXES = ("_ERR_", "_WRN_")  # the error catalog's numbers, not the protocol's
_BASELINE = "baseline"
_FIX = "add a changelog entry naming the constant, then set its row's Value and Last entry"
_ROW_KEY = re.compile(r"^([AB])(\d+)$")


def module_constants(source: str) -> dict[str, int | str]:
    # Every module-level `NAME = const(...)` except the log codes; an argument that is no literal keeps its source
    # text, so it fails the comparison instead of dropping out of it.
    found: dict[str, int | str] = {}
    for node in ast.parse(source).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "const" and len(call.args) == 1):
            continue
        name = node.targets[0].id
        try:
            value = ast.literal_eval(call.args[0])
        except ValueError:
            value = ast.unparse(call.args[0])
        if name.startswith(_LOG_CODE_PREFIXES) or isinstance(value, bool):
            continue
        if isinstance(value, int) or (isinstance(value, str) and not isinstance(call.args[0], ast.Constant)):
            found[name] = value
    return found


def _cells(line: str) -> list[str]:
    # A table row's cells; a pipe inside a code span stays in its cell.
    cells, current, in_code = [], "", False
    for ch in line.strip().strip("|"):
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(current.strip())
            current = ""
        else:
            current += ch
    return [*cells, current.strip()]


def tables(text: str) -> dict[str, list[dict[str, str]]]:
    # The first table under each "## " heading, as one dict per row keyed by the header cells.
    found: dict[str, list[dict[str, str]]] = {}
    heading, header = "", None
    for line in text.splitlines():
        if line.startswith("## "):
            heading, header = line.strip(), None
        elif not line.startswith("|"):
            if header is not None:
                heading = ""  # the table ended: a later one under the same heading is not read
            header = None
        elif not heading:
            continue
        elif header is None:
            header = _cells(line)
            found[heading] = []
        elif not set(line) <= set("|-: "):
            found[heading].append(dict(zip(header, _cells(line), strict=False)))
    return found


def _table(found: dict[str, list[dict[str, str]]], prefix: str) -> list[dict[str, str]] | None:
    return next((rows for heading, rows in found.items() if heading.startswith(prefix)), None)


def _name(cell: str) -> str:
    return cell.strip("`")


def _structure_findings(found: dict[str, list[dict[str, str]]]) -> list[str]:
    # A renamed heading or a dropped column must fail, never leave the checks below nothing to read.
    out = []
    constants = _table(found, _CONSTANTS_HEADING)
    if not constants or any(column not in constants[0] for column in _CONSTANT_COLUMNS):
        out.append(f"no '{_CONSTANTS_HEADING}' table with columns {', '.join(_CONSTANT_COLUMNS)}")
    for cls, heading in _CLASS_HEADINGS.items():
        rows = _table(found, heading)
        if not rows or "#" not in rows[0] or "Status" not in rows[0] or "Change" not in rows[0]:
            out.append(f"no '{heading}' table with columns #, Change and Status (class {cls})")
    return out


def constant_findings(module_source: str, found: dict[str, list[dict[str, str]]]) -> list[str]:
    # (a) the module's constants and the table's rows are the same (name, value) set.
    out = []
    module = module_constants(module_source)
    table: dict[str, int | str] = {}
    for row in _table(found, _CONSTANTS_HEADING) or []:
        name, cell = _name(row.get("Name", "")), row.get("Value", "")
        if name in table:
            out.append(f"{name}: listed twice in the constants table")
            continue
        try:
            table[name] = int(cell, 0)
        except ValueError:
            table[name] = cell
    for name in sorted(module.keys() | table.keys()):
        mine, listed = module.get(name, "none"), table.get(name, "none")
        if mine != listed:
            out.append(f"{name}: module value {mine}, table value {listed} - {_FIX}")
    return out


def last_entry_findings(found: dict[str, list[dict[str, str]]]) -> list[str]:
    # (b) a Last entry is the baseline or an existing row whose Change names the constant in backticks; (c) its class.
    out = []
    changes = {row.get("#", ""): row.get("Change", "") for heading in _CLASS_HEADINGS.values() for row in _table(found, heading) or []}
    for row in _table(found, _CONSTANTS_HEADING) or []:
        name, entry, cls = _name(row.get("Name", "")), row.get("Last entry", ""), row.get("Class", "")
        if cls not in _CLASS_HEADINGS:
            out.append(f"{name}: Class {cls!r} is neither A nor B")
        if entry == _BASELINE:
            continue
        if entry not in changes:
            out.append(f"{name}: Last entry {entry!r} is neither {_BASELINE} nor an existing row")
        elif f"`{name}`" not in changes[entry]:
            out.append(f"{name}: Last entry {entry}'s Change does not name `{name}`")
    return out


def row_findings(found: dict[str, list[dict[str, str]]]) -> list[str]:
    # (d) every Status is one of the closed set; (e) each class's rows ascend by number.
    out = []
    for cls, heading in _CLASS_HEADINGS.items():
        previous = 0
        for row in _table(found, heading) or []:
            key, status = row.get("#", ""), row.get("Status", "")
            if status not in _STATUSES:
                out.append(f"{key}: Status {status!r} is not one of {', '.join(_STATUSES)}")
            match = _ROW_KEY.match(key)
            if match is None or match.group(1) != cls:
                out.append(f"{key!r}: not a Class {cls} row number")
                continue
            number = int(match.group(2))
            if number <= previous:
                out.append(f"{key} follows {cls}{previous}: Class {cls} rows run in ascending number order")
            previous = number
    return out


def findings(module: Path, changelog: Path) -> list[str]:
    found = tables(changelog.read_text(encoding="utf-8"))
    return [
        *_structure_findings(found),
        *constant_findings(module.read_text(encoding="utf-8"), found),
        *last_entry_findings(found),
        *row_findings(found),
    ]


def test_the_changelog_agrees_with_the_module() -> None:
    found = findings(MODULE, CHANGELOG)
    assert not found, "UART_C_PORT_CHANGELOG.md and src/asy_uart_comm.py disagree:\n" + "\n".join(f"  {line}" for line in found)


def test_the_module_has_constants_beyond_the_log_codes() -> None:
    # Guards the parser: an empty read would let (a) pass on any table.
    constants = module_constants(MODULE.read_text(encoding="utf-8"))
    assert constants["_RESYNC_NUM"] == 3
    assert not [name for name in constants if name.startswith(_LOG_CODE_PREFIXES)]


@pytest.fixture
def copies(tmp_path: Path) -> tuple[Path, Path]:
    module, changelog = tmp_path / "asy_uart_comm.py", tmp_path / "UART_C_PORT_CHANGELOG.md"
    module.write_text(MODULE.read_text(encoding="utf-8"), encoding="utf-8")
    changelog.write_text(CHANGELOG.read_text(encoding="utf-8"), encoding="utf-8")
    assert findings(module, changelog) == []
    return module, changelog


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def _row(path: Path, key: str) -> str:
    return next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith(f"| {key} |"))


def test_a_changed_module_constant_fails(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(module, "_RESYNC_NUM = const(3)", "_RESYNC_NUM = const(4)")
    assert findings(module, changelog) == [f"_RESYNC_NUM: module value 4, table value 3 - {_FIX}"]


def test_a_constant_without_a_row_and_a_row_without_a_constant_fail(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(module, "_RESYNC_NUM = const(3)", "_RESYNC_NUM = const(3)\n_NEW_BOUND = const(7)")
    _replace(module, "_GATE_STEP_MS = const(20)", "_GATE_STEP_MS = 20")
    assert findings(module, changelog) == [
        f"_GATE_STEP_MS: module value none, table value 20 - {_FIX}",
        f"_NEW_BOUND: module value 7, table value none - {_FIX}",
    ]


def test_an_unknown_status_fails(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    row = _row(changelog, "A9")
    _replace(changelog, row, row.replace("| proposed |", "| proposed, owner-decided |"))
    assert findings(module, changelog) == [f"A9: Status 'proposed, owner-decided' is not one of {', '.join(_STATUSES)}"]


def test_a_swapped_row_pair_fails(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    seven, eight = _row(changelog, "A7"), _row(changelog, "A8")
    _replace(changelog, f"{seven}\n{eight}\n", f"{eight}\n{seven}\n")
    assert findings(module, changelog) == ["A7 follows A8: Class A rows run in ascending number order"]


def test_a_last_entry_whose_change_does_not_name_the_constant_fails(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(changelog, "| `_DEFAULT_CHUNK_BYTES` | 256 | B | B64 |", "| `_DEFAULT_CHUNK_BYTES` | 256 | B | B63 |")
    assert findings(module, changelog) == ["_DEFAULT_CHUNK_BYTES: Last entry B63's Change does not name `_DEFAULT_CHUNK_BYTES`"]


def test_a_last_entry_naming_no_row_and_a_bad_class_fail(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(changelog, "| `_GATE_STEP_MS` | 20 | B | baseline |", "| `_GATE_STEP_MS` | 20 | C | B999 |")
    assert findings(module, changelog) == [
        "_GATE_STEP_MS: Class 'C' is neither A nor B",
        "_GATE_STEP_MS: Last entry 'B999' is neither baseline nor an existing row",
    ]


def test_a_renamed_heading_fails_rather_than_passing_empty(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(changelog, _CONSTANTS_HEADING + "\n", "## Constants\n")
    found = findings(module, changelog)
    assert found[0] == f"no '{_CONSTANTS_HEADING}' table with columns {', '.join(_CONSTANT_COLUMNS)}"
    assert f"_RESYNC_NUM: module value 3, table value none - {_FIX}" in found


def test_a_constant_the_parser_cannot_evaluate_fails_rather_than_dropping_out(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(module, "_RESYNC_NUM = const(3)", "_RESYNC_NUM = const(_RESYNC_DEN + 1)")
    assert findings(module, changelog) == [f"_RESYNC_NUM: module value _RESYNC_DEN + 1, table value 3 - {_FIX}"]


def test_a_duplicated_table_row_fails(copies: tuple[Path, Path]) -> None:
    module, changelog = copies
    _replace(changelog, "| `_GATE_STEP_MS` | 20 | B | baseline |\n", "| `_GATE_STEP_MS` | 20 | B | baseline |\n| `_GATE_STEP_MS` | 30 | B | baseline |\n")
    assert findings(module, changelog) == ["_GATE_STEP_MS: listed twice in the constants table"]
