"""Device scripts report facts and the host test gives the verdict: no script prints a RESULT line, every host
function that runs a script parses its facts, harness.parse_facts() holds its contract, and every loop in an async
def of a device script awaits on each path that loops back, so a failing round never starves the loop."""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import harness

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
_SCRIPTS = _TESTS_HARDWARE / "device_scripts"
_RUN = "run_isolated"
_RUN_EXPECT_RESET = "run_isolated_expect_reset"


def _device_sources(scripts_dir: Path) -> "list[Path]":
    # Every script and every include: an include's loop runs on the board like the script's own.
    return sorted([*scripts_dir.glob("*.py"), *(scripts_dir / "_shared").glob("*.py")])


def _host_modules(root: Path) -> "list[Path]":
    return sorted(p for p in root.rglob("*.py") if "device_scripts" not in p.parts)


def _call_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")


def _result_prints(path: Path) -> "list[int]":
    # print("RESULT: ...") in any spelling: a plain string, an f-string, or a concatenation starting with it.
    lines: list[int] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if _call_name(node) == "print" and isinstance(node, ast.Call) and node.args:
            first = node.args[0]
            while isinstance(first, ast.BinOp):
                first = first.left
            text = first.values[0] if isinstance(first, ast.JoinedStr) and first.values else first
            if isinstance(text, ast.Constant) and isinstance(text.value, str) and text.value.startswith("RESULT"):
                lines.append(node.lineno)
    return lines


def test_no_device_script_prints_a_verdict() -> None:
    assert len(_device_sources(_SCRIPTS)) > 1, "no device script found - the scan reads nothing"
    found = {path.relative_to(_SCRIPTS).as_posix(): lines for path in _device_sources(_SCRIPTS) if (lines := _result_prints(path))}
    assert not found, f"a device script prints RESULT; it reports facts and the host test decides: {found}"


def _parses(call: ast.Call, path: Path) -> bool:
    # parse_facts(), or the chip conformance probes' own KEY=VALUE reader: conformance.parse() (bare inside its module).
    if _call_name(call) == "parse_facts":
        return True
    func = call.func
    named = isinstance(func, ast.Attribute) and func.attr == "parse" and isinstance(func.value, ast.Name) and func.value.id == "conformance"
    return named or (path.name == "conformance.py" and isinstance(func, ast.Name) and func.id == "parse")


def _unparsed_runs(path: Path) -> "list[str]":
    # Functions that run a script without parsing its facts in the same function; a reset runner allows a missing DONE.
    offenders: list[str] = []
    for fn in [n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
        runs = {_call_name(c) for c in calls} & {_RUN, _RUN_EXPECT_RESET}
        parses = [c for c in calls if _parses(c, path)]
        if not runs or fn.name in {_RUN, _RUN_EXPECT_RESET}:
            continue
        lenient = any(kw.arg == "allow_missing_done" and isinstance(kw.value, ast.Constant) and kw.value.value is True for c in parses for kw in c.keywords)
        if not parses:
            offenders.append(f"{fn.name} runs a script and parses no facts")
        elif _RUN_EXPECT_RESET in runs and not lenient:
            offenders.append(f"{fn.name} runs a resetting script without parse_facts(..., allow_missing_done=True)")
    return offenders


def test_every_host_function_that_runs_a_script_parses_its_facts() -> None:
    runs = [p for p in _host_modules(_TESTS_HARDWARE) if f".{_RUN}(" in p.read_text(encoding="utf-8")]
    assert runs, "no host module runs a device script - the scan reads nothing"
    found = {path.relative_to(_TESTS_HARDWARE).as_posix(): offenders for path in _host_modules(_TESTS_HARDWARE) if (offenders := _unparsed_runs(path))}
    assert not found, f"a script's output must reach harness.parse_facts(): {found}"


def test_parse_facts_reads_facts_and_requires_done() -> None:
    assert harness.parse_facts('FACT a=1\nFACT b={"x": [1, 2]}\nnoise\nDONE\n') == {"a": 1, "b": {"x": [1, 2]}}
    with pytest.raises(harness.HardwareTestFailureError, match="no DONE line") as missing:
        harness.parse_facts("FACT a=1\n")
    assert "FACT a=1" in str(missing.value), "the failure quotes the output"
    assert harness.parse_facts("FACT a=1\n", allow_missing_done=True) == {"a": 1}
    with pytest.raises(harness.HardwareTestFailureError, match="FACT width"):
        harness.parse_facts("FACT width=nan\nDONE\n")


def _awaits(node: ast.AST) -> bool:
    # An await in this node's own code, not in a nested function or lambda it defines.
    pending = [node]
    while pending:
        current = pending.pop()
        if isinstance(current, ast.Await | ast.AsyncFor | ast.AsyncWith):
            return True
        pending += [c for c in ast.iter_child_nodes(current) if not isinstance(c, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda)]
    return False


def _join(*states: "bool | None") -> "bool | None":
    # A merge point: None where no path arrives, else whether every arriving path awaited.
    reached = [s for s in states if s is not None]
    return all(reached) if reached else None


def _flow(stmts: "list[ast.stmt]", awaited: "bool | None") -> "tuple[bool | None, list[int]]":
    # (state where the block falls through, lines of a `continue` reached without an await).
    bad: list[int] = []
    state = awaited
    for stmt in stmts:
        if state is None:
            break
        if isinstance(stmt, ast.Continue):
            return None, [*bad, *([] if state else [stmt.lineno])]
        if isinstance(stmt, ast.Break | ast.Return | ast.Raise):
            return None, bad
        if isinstance(stmt, ast.If):
            start = state or _awaits(stmt.test)
            (body, b1), (orelse, b2) = _flow(stmt.body, start), _flow(stmt.orelse, start)
            bad += b1 + b2
            state = _join(body, orelse)
        elif isinstance(stmt, ast.Try):
            body, b1 = _flow(stmt.body + stmt.orelse, state)
            handled = [_flow(h.body, state) for h in stmt.handlers]
            bad += b1 + [line for _, b in handled for line in b]
            state = _join(body, *(s for s, _ in handled))
            if stmt.finalbody and state is not None:
                state, b3 = _flow(stmt.finalbody, state)
                bad += b3
        elif isinstance(stmt, ast.With | ast.AsyncWith):
            state, b1 = _flow(stmt.body, state or isinstance(stmt, ast.AsyncWith) or any(_awaits(i.context_expr) for i in stmt.items))
            bad += b1
        elif isinstance(stmt, ast.For | ast.While):
            # A nested loop is taken to run once (it is checked on its own): its header or body awaits, or its exits do.
            header = _awaits(stmt.iter if isinstance(stmt, ast.For) else stmt.test)
            inner, _ = _flow(stmt.body, state or header)
            state = state or header or bool(inner)
        else:
            state = state or _awaits(stmt)
    return state, bad


def _starving_loops(source: str) -> "list[int]":
    # Lines of each loop in an async def (outside any nested sync def) with a path looping back unawaited: every while,
    # and every for that awaits somewhere; a for that never awaits is bounded synchronous work (agent, 2026-10-14).
    found: list[int] = []
    for fn in [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.AsyncFunctionDef)]:
        pending: list[ast.AST] = list(fn.body)
        while pending:
            node = pending.pop()
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue
            if isinstance(node, ast.While) or (isinstance(node, ast.For) and any(_awaits(stmt) for stmt in node.body)):
                end, bad = _flow(node.body, _awaits(node.test) if isinstance(node, ast.While) else False)
                if bad or end is False:
                    found.append(node.lineno)
            pending += ast.iter_child_nodes(node)
    return sorted(found)


def test_every_loop_in_an_async_def_awaits_on_every_path_back() -> None:
    assert any(isinstance(n, ast.While) for p in _device_sources(_SCRIPTS) for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))), "no while loop in any script - the scan reads nothing"
    found = {path.relative_to(_SCRIPTS).as_posix(): lines for path in _device_sources(_SCRIPTS) if (lines := _starving_loops(path.read_text(encoding="utf-8")))}
    assert not found, f"loops in an async def that can loop back without an await (script: loop lines): {found}"


_LOOP_BITES = {
    "async def f():\n    while True:\n        if ok():\n            await asyncio.sleep(0)\n": True,
    "async def f():\n    for i in range(3):\n        try:\n            await read()\n        except OSError:\n            continue\n": True,
    "async def f():\n    while True:\n        if not ok():\n            break\n        await asyncio.sleep(0)\n": False,
    "async def f():\n    for i in range(3):\n        try:\n            x = await read()\n        except OSError:\n            errors += 1\n        await asyncio.sleep(0)\n": False,
    "async def f():\n    async with lock:\n        for i in range(3):\n            read_sync(i)\n": False,
    "async def f():\n    while not stop:\n        read_sync()\n": True,
    "def f():\n    while True:\n        spin()\n": False,
}


@pytest.mark.parametrize(("source", "starves"), list(_LOOP_BITES.items()), ids=["if-only", "continue-unawaited", "break-then-await", "await-after-try", "bounded-sync-for", "sync-while", "sync-def"])
def test_the_loop_check_bites(source: str, *, starves: bool) -> None:
    assert bool(_starving_loops(source)) is starves


def test_the_print_and_parse_checks_bite(tmp_path: Path) -> None:
    script = tmp_path / "script.py"
    script.write_text('print(f"RESULT: PASS {x}")\nprint("RESULT: " + y)\nprint("FACT a=1")\n', encoding="utf-8")
    assert _result_prints(script) == [1, 2]
    host = tmp_path / "test_host.py"
    host.write_text(
        "def test_a(board):\n    out = board.run_isolated(S)\n    assert 'ok' in out\n\n\n"
        "def test_b(board):\n    harness.parse_facts(board.run_isolated_expect_reset(S))\n\n\n"
        "def test_c(board):\n    harness.parse_facts(board.run_isolated_expect_reset(S), allow_missing_done=True)\n\n\n"
        "def test_d(board):\n    conformance.parse(board.run_isolated(S))\n\n\n"
        "def test_e(board):\n    other.parse(board.run_isolated(S))\n",
        encoding="utf-8",
    )
    assert [o.split(" ", 1)[0] for o in _unparsed_runs(host)] == ["test_a", "test_b", "test_e"]
