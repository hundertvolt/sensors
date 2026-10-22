"""Recomputes SPECIFICATION.md Part F.3's code-derived timing rows from src/, buildgen/codegen.py, the UART span device
script and the device TOMLs, never importing src/: a wrong Value or missing term, an unmarked or stale crossing, an
unknown Part N ID, an I2C timeout past its bound, differing reply slacks, a lost row or table fail; each bites below."""

import ast
import math
import re
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml
from test_tunables_register import parse_register

from buildgen.model import load_device
from buildgen.source_ast import parse_source
from buildgen.validate import _WDT_TIMEOUT_MS, _bus_kind, module_float_const, module_int_const, smallest_hard_consumer

_BEGIN, _END = "<!-- timing-budget:begin -->", "<!-- timing-budget:end -->"
_FIGURE = r"(\d[\d,]*(?:\.\d+)?)\s*(µs|us|ms|s)\b"
_FIGURE_RE, _LEADING_RE = re.compile(_FIGURE), re.compile(r"^" + _FIGURE)
_TO_US = {"µs": 1, "us": 1, "ms": 1000, "s": 1_000_000}
_CONSUMER_RE = re.compile(r"`(con\.[a-z_]+)`(\s*\(crossed)?")
_ID_RE = re.compile(r"`([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)`")
_SRC_FILES = (
    "asy_system_service.py", "asy_uart_comm.py", "asy_uart_driver.py", "asy_scd30_driver.py", "asy_i2c_driver.py", "asy_neopixel_driver.py",
    "asy_spi_driver.py", "asy_webserver_service.py", "asy_wifi_service.py",
)
# What the running device takes from outside src/: the generated module's DNS timeout, and the UART span script's frame.
_CODEGEN_DIR = Path(__file__).resolve().parent.parent / "buildgen"
_SPAN_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "tests_hardware" / "device_scripts"

def _bitten(spec_text: str, old: str, new: str) -> str:
    table = spec_text[spec_text.index(_BEGIN) : spec_text.index(_END)]
    assert table.count(old) == 1, f"the bite's anchor {old!r} must occur once in F.3's tables"
    return spec_text.replace(table, table.replace(old, new))


def _calls_in(path: Path, function: str, callee: str, arg: "str | None" = None) -> int:
    # How many calls of `callee` the named function makes (with `arg` as its first argument, if given), by AST.
    tree = parse_source(path.read_text(encoding="utf-8"), str(path))
    count = 0
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef | ast.FunctionDef) and n.name == function):
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == callee):
            if arg is None or (call.args and isinstance(call.args[0], ast.Name) and call.args[0].id == arg):
                count += 1
    return count


def _cells(line: str) -> "list[str]":
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _device_terms(src: Path) -> "tuple[int, set[int], set[int]]":
    # The largest I2C timeout of any device (unstated: the rp2 default), as buildgen's bus.i2c-timeout-consumer rule reads
    # it; every uart_link's reply slack from buildgen's one source, smallest_hard_consumer(), given that link alone; every UART baud.
    default_us = module_int_const(src, "asy_i2c_driver.py", "_DEFAULT_TIMEOUT_US")
    timeouts, slacks, bauds = [default_us], set(), set()
    for device in DEVICE_NAMES:
        buses = tomllib.loads(device_toml(device).read_text(encoding="utf-8")).get("bus", {})
        timeouts += [table.get("timeout", default_us) for name, table in buses.items() if _bus_kind(name, device) == "i2c"]
        bauds |= {table["baudrate"] for name, table in buses.items() if _bus_kind(name, device) == "uart"}
        model = load_device(device_toml(device))
        slacks |= {smallest_hard_consumer(replace(model, instances={key: spec}), src).ms for key, spec in model.instances.items() if spec.driver == "uart_link"}
    return max(timeouts), slacks, bauds


def _figures_us(cell: str) -> "list[int]":
    return [_us(number, unit) for number, unit in _FIGURE_RE.findall(cell)]


def _leading_us(cell: str) -> "int | None":
    # A cell that opens with a figure states its value; any other cell (owed, a rule in words) is not compared.
    match = _LEADING_RE.match(cell)
    return _us(*match.groups()) if match else None


def _us(number: str, unit: str) -> int:
    return round(float(number.replace(",", "")) * _TO_US[unit])


def check_table(spec_text: str, src: Path) -> "list[str]":
    consumers, rows, problems = parse_tables(spec_text)
    if problems:
        return problems
    table = {**consumers, **rows}
    value_of = {name: cells.get("tolerance", cells.get("value and derivation", "")) for name, cells in table.items()}
    timeout_us, slacks, bauds = _device_terms(src)
    if len(slacks) > 1:
        problems.append(f"the uart_link reply slacks differ across devices ({sorted(slacks)} ms): `con.uart_reply` needs one row per value")
    if len(bauds) > 1:
        problems.append(f"the UART bauds differ across buses ({sorted(bauds)}): `stall.uart_call` needs one row per value")
    for name, figures in expected_rows(src).items():
        if name not in table:
            problems.append(f"F.3 has no `{name}` row, which the code derives")
            continue
        cell = value_of[name]
        if _leading_us(cell) != figures[0]:
            problems.append(f"F.3 `{name}`: its value opens {cell[:40]!r}, the code gives {figures[0]} µs")
        problems += [f"F.3 `{name}`: {f} µs is a term of its derivation and missing from {cell[:40]!r}" for f in figures[1:] if f not in _figures_us(cell)]
    ends = math.ceil((module_int_const(src, "asy_system_service.py", "_TASK_FAIL_MAX") + 1) / module_int_const(src, "asy_system_service.py", "_TASK_FAIL_INCREMENT"))
    if f"{ends} task ends" not in value_of.get("feed.supervisor", ""):
        problems.append(f"F.3 `feed.supervisor`: the escalating pass makes {ends} task ends, its value does not say so")
    register = {row.id: row for row in parse_register(spec_text)[0]}
    bound = _leading_us(register["i2c.timeout_max_us"].cells.get("value", "")) if "i2c.timeout_max_us" in register else None
    if bound is None or timeout_us > bound:
        problems.append(f"the largest I2C timeout, {timeout_us} µs, is above Part N `i2c.timeout_max_us` ({bound} µs)")
    for name, cells in rows.items():
        value = _leading_us(value_of[name])
        if value is not None and name.startswith("feed.") and value >= _WDT_TIMEOUT_MS * 1000:
            problems.append(f"F.3 `{name}`: {value} µs between two feeds is not below the {_WDT_TIMEOUT_MS} ms watchdog")
        for consumer, crossed in _CONSUMER_RE.findall(cells.get("consumers", "")):
            tolerance = _leading_us(value_of[consumer]) if consumer in consumers else None
            if consumer not in consumers:
                problems.append(f"F.3 `{name}` names consumer `{consumer}`, which the consumer table lacks")
            elif value is not None and tolerance is not None and (value > tolerance) != bool(crossed):
                state = "a stale crossing: it fits" if crossed else "past it, and not marked crossed"
                problems.append(f"F.3 `{name}` ({value} µs) against `{consumer}` ({tolerance} µs): {state}")
        problems += [f"F.3 `{name}` cites `{pid}`, which is not a Part N row" for pid in _ID_RE.findall(cells.get("part n", "")) if pid not in register]
    return problems


def expected_rows(src: Path) -> "dict[str, list[int]]":
    # Each code-derived row's figures in µs, the Value cell's leading one first; the rest must appear in the cell.
    system = "asy_system_service.py"
    task_check_s, reset_s, entry_ms = (module_int_const(src, system, n) for n in ("_TASK_CHECK_TIME", "_RESET_DELAY", "_ESCALATION_ENTRY_WAIT_MS"))
    gc_ms = module_int_const(src, "asy_uart_comm.py", "_GC_PAUSE_WORST_MS")
    cmd_ms = module_int_const(src, "asy_scd30_driver.py", "_CMD_RESPONSE_WAIT_MS")
    probe_ms = module_int_const(src, "asy_i2c_driver.py", "_PROBE_SETTLE_MS")
    reads = _calls_in(src / "asy_scd30_driver.py", "get_config_snapshot", "_read_dev_register")
    settles = _calls_in(src / "asy_i2c_driver.py", "_probe_for_device", "sleep_ms", "_PROBE_SETTLE_MS")
    timeout_us, slacks, bauds = _device_terms(src)
    wifi = "asy_wifi_service.py"
    disconnect_ms = module_int_const(src, wifi, "_STA_DISCONNECT_WAIT_ITERS") * module_int_const(src, wifi, "_STA_DISCONNECT_POLL_MS")
    connect_ms = module_int_const(src, wifi, "_STA_CONNECT_POLL_ITERS") * module_int_const(src, wifi, "_STA_CONNECT_POLL_MS")
    switch_s = sum(module_int_const(src, wifi, f"_WLAN_{n}_SETTLE_S") for n in ("DOWN", "DEINIT", "MODE"))
    clear_us, cs_us = module_int_const(src, "asy_i2c_driver.py", "_CLEAR_HALF_PERIOD_US"), module_int_const(src, "asy_spi_driver.py", "_CS_SETTLE_US")
    per_call_s, outer_s = (module_float_const(src, "asy_webserver_service.py", n) for n in ("_DEFAULT_PER_CALL_TIMEOUT_S", "_DEFAULT_OUTER_CAP_S"))
    rows = {
        "con.watchdog": [(_WDT_TIMEOUT_MS - task_check_s * 1000) * 1000],
        "con.led_frame": [1000 // module_int_const(src, "asy_neopixel_driver.py", "_NEOPIXEL_FREQ_HZ") * 1000],
        "con.routine_stall": [gc_ms * 1000],
        "stall.gc": [gc_ms * 1000],
        "stall.i2c_transfer": [2 * timeout_us, timeout_us, module_int_const(src, "asy_i2c_driver.py", "_DEFAULT_TIMEOUT_US")],
        "hold.scd30_command": [cmd_ms * 1000],
        "hold.scd30_snapshot": [reads * cmd_ms * 1000, cmd_ms * 1000],
        "hold.i2c_probe": [settles * probe_ms * 1000, probe_ms * 1000],
        "feed.supervisor": [task_check_s * 1_000_000, entry_ms * 1000],
        "feed.reset_path": [reset_s * 1_000_000],
        "con.dns_query": [module_int_const(_CODEGEN_DIR, "codegen.py", "_DNS_TIMEOUT_MS") * 1000],
        "con.http_call": [round(per_call_s * 1_000_000), round(outer_s * 1_000_000)],
        "stall.sync_wait": [max(clear_us, cs_us), clear_us, cs_us],
        "hold.wifi_lock": [max(disconnect_ms, connect_ms, switch_s * 1000) * 1000, connect_ms * 1000, switch_s * 1_000_000],
        "stall.flash_program": [module_int_const(src, "asy_uart_comm.py", "_FLASH_HOLD_MAX_MS") * 1000],
    }
    rows.update({"con.uart_reply": [min(slacks) * 1000]} if len(slacks) == 1 else {})
    if len(bauds) == 1:  # a third of one frame's wire time, as the span script bounds one UART driver call
        wire_us = module_int_const(_SPAN_SCRIPT_DIR, "uart_driver_read_never_blocks_the_loop.py", "FRAME") * 10 * 1_000_000 // min(bauds)
        rows["stall.uart_call"] = [wire_us // module_int_const(_SPAN_SCRIPT_DIR, "uart_driver_read_never_blocks_the_loop.py", "_SPAN_FRACTION"), wire_us]
    return rows


def parse_tables(spec_text: str) -> "tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], list[str]]":
    # The consumer table (first column "Consumer") and the budget table (first column "Row"), keyed by each row's
    # first backticked name; a duplicate or an unnamed row is a problem.
    if spec_text.count(_BEGIN) != 1 or spec_text.count(_END) != 1 or spec_text.index(_BEGIN) > spec_text.index(_END):
        return {}, {}, [f"SPECIFICATION.md must hold Part F.3's timing tables exactly once between {_BEGIN} and {_END}"]
    tables: dict[str, dict[str, dict[str, str]]] = {"consumer": {}, "row": {}}
    problems: list[str] = []
    header: list[str] | None = None
    for raw in spec_text[spec_text.index(_BEGIN) : spec_text.index(_END)].splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells) or header[0] not in tables:
            continue
        name = re.match(r"`([^`]+)`", cells[0])
        if name is None or name.group(1) in tables[header[0]]:
            problems.append(f"F.3 {header[0]} row {cells[0]!r} is unnamed or named twice")
            continue
        tables[header[0]][name.group(1)] = dict(zip(header, cells, strict=False))
    if not tables["consumer"] or not tables["row"]:
        problems.append("F.3 needs both its consumer table and its budget table between the markers")
    return tables["consumer"], tables["row"], problems


@pytest.fixture(scope="module")
def spec_text(repo_root: Path) -> str:
    return (repo_root / "SPECIFICATION.md").read_text(encoding="utf-8")


def test_the_code_derived_rows_match_the_code(spec_text: str, repo_root: Path) -> None:
    problems = check_table(spec_text, repo_root / "src")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("| 50 ms per session", "| 60 ms per session", "the code gives 50000 µs"),
        ("`con.led_frame` (crossed: a stutter)", "`con.led_frame`", "past it, and not marked crossed"),
        ("`con.uart_reply` (its floor holds it)", "`con.uart_reply` (crossed: its floor holds it)", "a stale crossing"),
        ("`scd30.cmd_response_wait_ms` |", "`scd30.cmd_wait_ms` |", "`scd30.cmd_wait_ms`, which is not a Part N row"),
        ("| `hold.i2c_probe` |", "| `hold.i2c_probe_settle` |", "no `hold.i2c_probe` row"),
        ("`con.led_frame` (crossed: a stutter)", "`con.led_frames` (crossed: a stutter)", "which the consumer table lacks"),
        ("4 task ends", "5 task ends", "makes 4 task ends"),
        ("50,000 µs (`_DEFAULT_TIMEOUT_US`", "the rp2 default (`_DEFAULT_TIMEOUT_US`", "50000 µs is a term of its derivation"),
        ("| `hold.scd30_snapshot` |", "| `hold.scd30_command` |", "is unnamed or named twice"),
        ("| `rate.trigger_spacing` |", "| rate.trigger_spacing |", "is unnamed or named twice"),
        ("| Consumer | Tolerance |", "| Item | Tolerance |", "needs both its consumer table and its budget table"),
        ("| 500 ms per server", "| 900 ms per server", "`con.dns_query`: its value opens"),
        ("| 5 s per stream call", "| 7 s per stream call", "`con.http_call`: its value opens"),
        ("| 1,533 µs:", "| 9,533 µs:", "`stall.uart_call`: its value opens"),
        ("| 5 µs per wait", "| 50 µs per wait", "`stall.sync_wait`: its value opens"),
        ("| 10 s, the longest hold", "| 20 s, the longest hold", "`hold.wifi_lock`: its value opens"),
        ("| 2129 ms", "| 400 ms", "`stall.flash_program`: its value opens"),
    ],
)
def test_each_failure_class_bites(spec_text: str, repo_root: Path, old: str, new: str, expected: str) -> None:
    problems = check_table(_bitten(spec_text, old, new), repo_root / "src")
    assert any(expected in p for p in problems), problems


def test_an_i2c_timeout_above_its_register_bound_bites(spec_text: str, repo_root: Path) -> None:
    # Part N's bound, not F.3's table, moves: a copy of the register row, never an edit of Part N.
    row = next(line for line in spec_text.splitlines() if line.startswith("| `i2c.timeout_max_us` | "))
    problems = check_table(spec_text.replace(row, row.replace("| 200000 µs |", "| 100000 µs |", 1)), repo_root / "src")
    assert any("is above Part N `i2c.timeout_max_us` (100000 µs)" in p for p in problems), problems


def test_reply_slacks_that_differ_across_devices_bite(spec_text: str, repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    timeout_us, slacks, bauds = _device_terms(repo_root / "src")
    monkeypatch.setattr(sys.modules[__name__], "_device_terms", lambda _src: (timeout_us, {*slacks, max(slacks) + 5}, bauds))
    assert any("the uart_link reply slacks differ across devices" in p for p in check_table(spec_text, repo_root / "src"))


def test_uart_bauds_that_differ_across_buses_bite(spec_text: str, repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    timeout_us, slacks, bauds = _device_terms(repo_root / "src")
    monkeypatch.setattr(sys.modules[__name__], "_device_terms", lambda _src: (timeout_us, slacks, {*bauds, max(bauds) // 2}))
    assert any("the UART bauds differ across buses" in p for p in check_table(spec_text, repo_root / "src"))


def test_lost_markers_bite(spec_text: str, repo_root: Path) -> None:
    assert any("exactly once between" in p for p in check_table(spec_text.replace(_END, ""), repo_root / "src"))


def test_a_reset_delay_past_the_watchdog_bites(spec_text: str, repo_root: Path, tmp_path: Path) -> None:
    # The code side moves, and the table with it: the relation, not the copy, has to fail.
    for name in _SRC_FILES:
        shutil.copy(repo_root / "src" / name, tmp_path / name)
    system = tmp_path / "asy_system_service.py"
    system.write_text(system.read_text(encoding="utf-8").replace("_RESET_DELAY = const(4)", "_RESET_DELAY = const(9)"), encoding="utf-8")
    problems = check_table(_bitten(spec_text, "| 4000 ms countdown", "| 9000 ms countdown"), tmp_path)
    assert any("`feed.reset_path`: 9000000 µs between two feeds is not below" in p for p in problems), problems
