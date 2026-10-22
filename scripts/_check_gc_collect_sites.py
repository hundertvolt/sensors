#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The gc policy check (SPECIFICATION.md I.4(e)/(f.1)): every gc.collect(), gc.threshold(<value>), gc.disable() and
gc.enable() reached via a name bound to gc or one of them, in src/, tests/, digital_twin/, tests_hardware/ and generated
modules, outside the one allowance table is reported with its enclosing function; nothing unreadable passes."""

# Usage: python3 scripts/_check_gc_collect_sites.py [--root DIR]
# Exit 0 when clean, 1 naming each site outside the table (or a row with no site), 2 when a file or a device cannot be
# read or a scope holds nothing to read.

import argparse
import ast
import bisect
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from buildgen.errors import BuildError  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.generate import generate_device  # noqa: E402 - the repo-root insert above makes it importable

if TYPE_CHECKING:
    from collections.abc import Iterator

SCOPES = ("src", "tests", "digital_twin", "tests_hardware")
POLICY = ("collect", "threshold", "disable", "enable")  # threshold only as a set: the zero-argument call reads it
# Why a site may call gc (SPECIFICATION.md I.4(e)/(f.1)): every row names one.
CATEGORIES = ("placement reset", "baseline", "boot mirror", "before a timed window", "twin exception", "measured collection pause", "stage")
_DS = "tests_hardware/device_scripts/"
# The whole allowance, (module, enclosing function, call) -> its category and reason; a baseline's reading follows it.
ALLOWED = {
    ("src/asy_system_service.py", "SystemService.run_setups", "collect"): "placement reset: between the units of the one-time setup list",
    ("src/asy_system_service.py", "SystemService.start_tasks", "collect"): "placement reset: between the units of the one-time task-start list",
    ("tests/_boot_contiguity_probe.py", "_dump", "collect"): "baseline: the heap map that follows",
    ("tests/_boot_contiguity_probe.py", "_ProbeGc.collect", "collect"): "boot mirror: the placement reset on the probe's live arm",
    ("tests/_threshold_runner.py", "_run", "threshold"): "stage: the process's GC stage for the file it runs",
    ("tests/microtest.py", "_reset_process_state", "threshold"): "stage: the run's own stage restored after each test",
    ("tests/test_asy_base_classes.py", "test_piecebuffer_retains_nothing_after_construction", "collect"): "baseline: the retention readings",
    ("tests/test_asy_fram_allocation_budget.py", "_priced", "collect"): "baseline: the setup's priced window",
    ("tests/test_asy_system_service.py", "_call_cost", "collect"): "baseline: an empty call's allocation",
    ("tests/test_asy_system_service.py", "_settled_alloc", "collect"): "baseline: the settled allocation",
    ("tests/test_asy_system_service.py", "test_the_reports_outputs_allocate_nothing", "collect"): "baseline: the report's allocation",
    ("tests/test_asy_uart_comm.py", "test_a_declared_size_over_max_transfer_bytes_is_refused_before_any_allocation.measured", "collect"): "baseline: the refusals' retention",
    ("tests/test_asy_uart_comm.py", "test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat", "collect"): "baseline: the trains' retention",
    ("tests/test_asy_uart_driver.py", "test_a_read_retains_nothing.grown", "collect"): "baseline: the reads' retention",
    ("tests/test_asy_webserver_service.py", "test_f9_soak_100_plus_start_wedge_reclaim_cycles_hold_counter_and_memory_flat.free_after", "collect"): "baseline: the soak's free heap, and each 3-cycle period's end so every collect finds the same heap",
    ("tests/test_async_harness.py", "_growth_over_awaited_tasks.scenario", "collect"): "baseline: the awaited tasks' growth",
    ("tests/test_digital_twin_sensortask_integration.py", "_heap_floor", "collect"): "baseline: the supervised deaths' heap floor",
    ("tests/test_digital_twin_uart_link.py", "_hammer_with_the_graph_running", "collect"): "baseline: the hammer's retention rate",
    ("tests/test_digital_twin_uart_link.py", "test_many_back_to_back_transfers_do_not_degrade_or_leak", "collect"): "baseline: the transfers' retention rate",
    ("tests/test_digital_twin_unix_port_unretrieved_report.py", "_call_cost", "collect"): "baseline: an empty call's allocation",
    ("tests/test_digital_twin_unix_port_unretrieved_report.py", "_settled_alloc", "collect"): "baseline: the settled allocation",
    ("tests/test_digital_twin_unix_port_unretrieved_report.py", "test_the_reports_outputs_allocate_nothing", "collect"): "baseline: the report's allocation",
    ("tests/test_uart_comm_hazard.py", "_hammer_clean.hammer", "collect"): "baseline: the clean hammer's retention",
    ("tests/test_uart_comm_hazard.py", "_hammer_faulted.hammer", "collect"): "baseline: each faulted window's retention",
    ("tests/test_uart_comm_hazard.py", "_measure_retention", "collect"): "baseline: the retention and its ambient control",
    ("digital_twin/run_device_script.py", "main", "threshold"): "stage: the script runner's --gc-threshold",
    ("digital_twin/run_generic_integration.py", "<module>", "threshold"): "stage: the twin runner's --gc-threshold",
    ("digital_twin/run_generic_integration.py", "_mem_sampler", "collect"): "twin exception: Run 11's memory sampler (owner, 2026-09-26)",
    ("digital_twin/run_generic_integration.py", "_print_shutdown_line", "collect"): "baseline: the shutdown line's largest free block",
    (f"{_DS}_shared/heap_probe.py", "_report", "collect"): "baseline: the HEAP line's figures",
    (f"{_DS}_shared/heap_probe.py", "dump_map", "collect"): "baseline: the heap map that follows",
    (f"{_DS}_shared/heap_probe.py", "largest_block", "collect"): "baseline: the largest-block probe",
    (f"{_DS}allocation_need_per_source.py", "_build_sieve", "collect"): "baseline: the sieve the probes are placed in",
    (f"{_DS}allocation_need_per_source.py", "_measure", "collect"): "baseline: each probe's churn",
    (f"{_DS}allocation_need_per_source.py", "_release_sieve", "collect"): "baseline: the next rung's sieve",
    (f"{_DS}heap_layout_after_full_boot_sequence.py", "_ProbeGc.collect", "collect"): "boot mirror: the placement reset on the live arm",
    (f"{_DS}loop_stretch_timing.py", "_main", "collect"): "measured collection pause: the pause SPECIFICATION.md F.3 bounds",
    (f"{_DS}serving_at_default_gc.py", "_observe", "collect"): "baseline: the heap map that follows",
    (f"{_DS}uart_dma_ring_interrupts_off.py", "_sweep", "collect"): "baseline: the ring's heap cost",
    (f"{_DS}uart_dma_ring_interrupts_off.py", "_window", "collect"): "before a timed window: the interrupts-off record",
    (f"{_DS}uart_driver_read_never_blocks_the_loop.py", "_trial", "collect"): "before a timed window: the driver's read span",
    (f"{_DS}uart_driver_read_never_blocks_the_loop.py", "main", "collect"): "before a timed window: the idle gap",
    (f"{_DS}uart_idle_poll_rate.py", "_count_rounds", "collect"): "before a timed window: the counted poll rounds",
    (f"{_DS}uart_link_under_concurrent_system_load.py", "_heap_floor", "collect"): "baseline: the link's heap floor",
    (f"{_DS}unretrieved_task_exception_handler.py", "_at_threshold", "collect"): "baseline: the free heap after the hammer",
    (f"{_DS}unretrieved_task_exception_handler.py", "_locked_reports", "collect"): "baseline: each report's allocation",
    (f"{_DS}unretrieved_task_exception_handler.py", "_settled_alloc", "collect"): "baseline: the settled allocation",
}
_RULE = "is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))"
_GENERATED = "build/generated_src"
_INPUT_DIRS = (("devices", ".toml"), ("buildgen", ".py"), ("src", ".py"), ("ext", ".py"))  # the generator's input globs


@dataclass(frozen=True)
class Generated:
    rel: str
    text: str
    boot_entry: bool


@dataclass
class ScanResult:
    findings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    generated: int = 0
    fresh: bool = False  # the generated modules were read from a current build/generated_src/


def _bound_names(tree: ast.Module) -> "tuple[set[str], dict[str, str]]":
    # (names bound to the gc module, names bound to one of its policy functions -> that function): import forms, aliases,
    # a star import and plain assignments, each a statement, so the statements alone are walked.
    modules: set[str] = set()
    functions: dict[str, str] = {}
    assigned: list[ast.Assign] = []
    for node in _statements(tree.body):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == "gc")
        elif isinstance(node, ast.ImportFrom) and node.module == "gc":
            for alias in node.names:
                if alias.name == "*":
                    functions.update((name, name) for name in POLICY)
                elif alias.name in POLICY:
                    functions[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr in POLICY and isinstance(node.value.value, ast.Name):
            assigned.append(node)
    for node in assigned:
        if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and node.value.value.id in modules:
            functions.update((target.id, node.value.attr) for target in node.targets if isinstance(target, ast.Name))
    return modules, functions


def _check_generated(sources: "list[Generated]", result: ScanResult) -> None:
    # A generated module calls no gc policy function; a boot entry calls exactly one, gc.threshold(<int literal>) at module
    # level, the value the firmware runs at (SPECIFICATION.md I.4(f)).
    for source in sources:
        tree = _parsed(source.text, source.rel, result)
        result.generated += 1
        if tree is None:
            continue
        modules, _functions = _bound_names(tree)
        sets = [stmt for stmt in tree.body if _literal_threshold(stmt, modules)] if source.boot_entry else []
        for line, owner, name in policy_calls(tree, source.text):
            if sets and line == sets[0].lineno and owner == "<module>":
                continue
            result.findings.append(f"{source.rel}:{line}: {_shown(name)} in {owner} {_RULE}")
        if source.boot_entry and not sets:
            result.findings.append(f"{source.rel}: the boot entry sets no gc.threshold(<int literal>) at module level - SPECIFICATION.md I.4(f)")


def _check_source(text: str, rel: str, result: ScanResult, allowed: "dict[tuple[str, str, str], str]", seen: "set[tuple[str, str, str]]") -> None:
    tree = _parsed(text, rel, result)
    if tree is None or "gc" not in text:  # a file naming no gc binds no name to it: parsed, nothing to walk
        return
    stages = _stage_sets(tree) if rel.startswith(_DS) and "/" not in rel[len(_DS) :] else set()
    for line, owner, name in policy_calls(tree, text):
        if (rel, owner, name) in allowed:
            seen.add((rel, owner, name))
        elif not (name == "threshold" and line in stages):
            result.findings.append(f"{rel}:{line}: {_shown(name)} in {owner} {_RULE}")


def _int_literal(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and type(node.value) is int


def _lines(text: str) -> "list[str]":
    # The lines as ast numbers them: \r\n, \r and \n end one, never the other breaks str.splitlines() knows.
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _literal_threshold(stmt: ast.stmt, modules: "set[str]") -> bool:
    # A module-level `gc.threshold(<int>)` statement through a name bound to gc.
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return False
    call = stmt.value
    func = call.func
    named = isinstance(func, ast.Attribute) and func.attr == "threshold" and isinstance(func.value, ast.Name) and func.value.id in modules
    literal = len(call.args) == 1 and not call.keywords and isinstance(call.args[0], ast.Constant) and type(call.args[0].value) is int
    return named and literal


def _named(call: ast.Call, modules: "set[str]", functions: "dict[str, str]") -> "str | None":
    # The policy function a call reaches through a name bound to gc or to one of them, whatever its arguments.
    func = call.func
    if isinstance(func, ast.Name):
        return functions.get(func.id)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in modules and func.attr in POLICY:
        return func.attr
    return None


def _parsed(text: str, rel: str, result: ScanResult) -> "ast.Module | None":
    try:
        return ast.parse(text, rel)
    except SyntaxError as e:
        result.errors.append(f"{rel}:{e.lineno}: cannot parse ({e.msg}) - the gc check could not look")
        return None


def _read(path: Path, rel: str, result: ScanResult) -> "str | None":
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        result.errors.append(f"{rel}: cannot read ({e}) - the gc check could not look")
        return None


def _shown(name: str) -> str:
    return "gc.threshold(...)" if name == "threshold" else f"gc.{name}()"


def _stage_sets(tree: ast.Module) -> "set[int]":
    # A device script's own stage set (tests_scripts/test_device_script_gc_threshold.py pins its report), in the tree's
    # two forms: gc.threshold(<int literal>) at module level before the first definition, or a set whose next statement
    # reads the value back. Its lines; any other set is a finding.
    modules, functions = _bound_names(tree)

    def sets(stmt: ast.stmt) -> bool:
        return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and _named(stmt.value, modules, functions) == "threshold"

    def reads(stmt: ast.stmt) -> bool:
        return any(isinstance(n, ast.Call) and not (n.args or n.keywords) and _named(n, modules, functions) == "threshold" for n in ast.walk(stmt))

    lines: set[int] = set()
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        if sets(stmt) and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and len(stmt.value.args) == 1 and not stmt.value.keywords and _int_literal(stmt.value.args[0]):
            lines.add(stmt.lineno)
    for node in ast.walk(tree):
        for block in (getattr(node, name, None) for name in ("body", "orelse", "finalbody")):
            if isinstance(block, list):
                lines.update(stmt.lineno for stmt, after in pairwise(block) if sets(stmt) and reads(after))
    return lines


def _statements(body: "list[ast.stmt]") -> "Iterator[ast.stmt]":
    # Every statement, nested ones included: the bodies of compound statements, their except handlers and match cases.
    for stmt in body:
        yield stmt
        for name in ("body", "orelse", "finalbody", "handlers", "cases"):
            for item in getattr(stmt, name, ()):
                yield from _statements([item] if isinstance(item, ast.stmt) else item.body)


def fresh_tree(root: Path) -> "list[Generated] | None":
    # The generator's own output while its stamp still holds (scripts/_generate_sensortask_modules.py): every input it
    # read has its recorded sha256, no file joined its input directories, every device's three files are there. Else
    # None, and the caller generates: a stale tree is never read.
    try:
        stamp = json.loads((root / _GENERATED / ".inputs_stamp.json").read_text(encoding="utf-8"))
        recorded, outputs = dict(stamp["inputs"]), set(stamp["outputs"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    current = {path.relative_to(root).as_posix() for folder, suffix in _INPUT_DIRS for path in (root / folder).glob(f"*{suffix}") if not (folder == "devices" and path.stem.startswith("zz_test_"))}
    if not current <= recorded.keys() or any(not (root / rel).is_file() or hashlib.sha256((root / rel).read_bytes()).hexdigest() != digest for rel, digest in recorded.items()):
        return None
    sources: list[Generated] = []
    for device in sorted(Path(rel).stem for rel in current if rel.startswith("devices/")):
        for name, boot_entry in ((f"sensortask_{device}.py", False), (f"sensortask_{device}_main.py", True), (f"sensortask_{device}_main_noautostart.py", True)):
            path = root / _GENERATED / name
            if name not in outputs or not path.is_file():
                return None
            sources.append(Generated(f"{_GENERATED}/{name}", path.read_text(encoding="utf-8"), boot_entry=boot_entry))
    return sources or None


def generate_all(root: Path) -> "tuple[list[Generated], list[str]]":
    # Every derived device's module and both boot entries, as the generator would write them, built once; a zz_test_
    # TOML is a test fixture, never a device.
    sources: list[Generated] = []
    errors: list[str] = []
    tomls = sorted(toml for toml in (root / "devices").glob("*.toml") if not toml.stem.startswith("zz_test_"))
    for toml in tomls:
        try:
            device = generate_device(toml, root / "src", root / "ext")
        except BuildError as e:
            errors.append(f"{toml.relative_to(root).as_posix()}: cannot generate ({e}) - the gc check could not look")
            continue
        stem = f"{_GENERATED}/sensortask_{toml.stem}"
        sources += [Generated(f"{stem}.py", device.module_source, boot_entry=False), Generated(f"{stem}_main.py", device.boot_entry_source, boot_entry=True), Generated(f"{stem}_main_noautostart.py", device.boot_entry_noautostart_source, boot_entry=True)]
    if not tomls:
        errors.append("devices/: no device to generate - the gc check could not look at a generated module")
    return sources, errors


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="the tree to check (default: this repository)")
    args = parser.parse_args(argv)
    result = scan_tree(args.root)
    for line in [*result.errors, *result.findings]:
        print(line, file=sys.stderr)
    origin = f"{_GENERATED}/, its stamp current" if result.fresh else "generated in memory"
    print(f"gc policy sites: {len(ALLOWED)} allowed, {len(result.findings)} outside the table; scopes checked: {', '.join(f'{scope}/' for scope in SCOPES)}; generated modules checked: {result.generated} ({origin})")
    if result.errors:
        return 2
    return 1 if result.findings else 0


def policy_calls(tree: ast.Module, text: str) -> "list[tuple[int, str, str]]":
    # (line, qualified enclosing function or "<module>", policy function) of every policy call, by explicit descent so each
    # call is attributed to its nearest function; a gc.threshold() with no argument is a read and is left out. A statement
    # whose lines name no bound name holds no such call and is passed over.
    modules, functions = _bound_names(tree)
    if not modules and not functions:
        return []
    named = re.compile(r"\b(?:" + "|".join(re.escape(name) for name in sorted({*modules, *functions})) + r")\b")
    marked = [number for number, line in enumerate(_lines(text), 1) if named.search(line)]
    calls: list[tuple[int, str, str]] = []

    def called(call: ast.Call) -> "str | None":
        name = _named(call, modules, functions)
        return None if name == "threshold" and not (call.args or call.keywords) else name

    def touched(stmt: ast.stmt) -> bool:
        first = min([stmt.lineno, *(d.lineno for d in getattr(stmt, "decorator_list", ()))])
        at = bisect.bisect_left(marked, first)
        return at < len(marked) and marked[at] <= (stmt.end_lineno or stmt.lineno)

    def visit(node: ast.AST, owner: "tuple[str, ...]") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt) and not touched(child):
                continue
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, (*owner, child.name))
                continue
            if isinstance(child, ast.Call):
                name = called(child)
                if name is not None:
                    calls.append((child.lineno, ".".join(owner) or "<module>", name))
            visit(child, owner)

    visit(tree, ())
    return calls


def scan_tree(root: Path, generated: "list[Generated] | None" = None, allowed: "dict[tuple[str, str, str], str] | None" = None) -> ScanResult:
    # `generated` and `allowed` default to this tree's own generation and the table above.
    table = ALLOWED if allowed is None else allowed
    result = ScanResult()
    seen: set[tuple[str, str, str]] = set()
    for scope in SCOPES:
        sources = sorted((root / scope).rglob("*.py"))
        if not sources:
            result.errors.append(f"{scope}/: no Python file to scan - the gc check could not look")
        for path in sources:
            rel = path.relative_to(root).as_posix()
            text = _read(path, rel, result)
            if text is not None:
                _check_source(text, rel, result, table, seen)
    for path in sorted((root / "buildgen").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(_lines(_read(path, rel, result) or ""), 1):
            if "gc.collect(" in line:
                result.findings.append(f"{rel}:{number}: gc.collect( in buildgen/'s text - the generated modules carry none (SPECIFICATION.md I.4(f.1))")
    if generated is None:
        generated = fresh_tree(root)
        result.fresh = generated is not None
    if generated is None:
        generated, errors = generate_all(root)
        result.errors += errors
    _check_generated(generated, result)
    for rel, owner, name in sorted(table):
        if not (root / rel).is_file():
            result.findings.append(f"{rel}: the allowed site {owner} names a file that is gone - remove its row")
        elif (rel, owner, name) not in seen:
            result.findings.append(f"{rel}: the allowed site {owner} holds no {_shown(name)} call - restore it or remove its row")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
