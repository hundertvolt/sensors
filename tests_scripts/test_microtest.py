"""tests/microtest.py's contract, which scripts/test.sh's summary reads (run under the real Unix port, as tests/ is),
and the conventions of tests/ it relies on, read by AST: the canonical trailer, asyncio.run() only in the harness,
json.loads() only where no response body is read, private doubles and builders, unique scratch keys."""

import ast
import functools
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

REPO_ROOT = Path(__file__).resolve().parent.parent
_TESTS = REPO_ROOT / "tests"
_TRAILER = 'if __name__ == "__main__":\n    import microtest\n\n    microtest.run(globals())\n'
_HARNESS = "_async_harness.py"
# Reads of JSON that is no response body, each file's count of json.loads() calls; a response body is read with
# tests/_strict_json.py's strict_loads(), the oracle itself being the one file outside this list.
_JSON_LOADS_ALLOWED: "dict[str, tuple[int, str]]" = {
    "test_asy_base_classes.py": (1, "the round trip of the unavailable marker through the interpreter's own json"),
    "test_asy_config_manager.py": (2, "config files and a decoder stand-in, not a response"),
    "test_asy_system_service.py": (3, "config files the service wrote"),
    "test_strict_json.py": (2, "compares the recogniser with the interpreter's own json.loads()"),
}


def _asyncio_run_sites(directory: Path) -> "dict[str, list[int]]":
    sites = {}
    for name, tree in _parsed(directory, "*.py"):
        modules = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names if alias.name == "asyncio"}
        functions = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == "asyncio" for alias in node.names if alias.name == "run"}
        lines = _calls(tree, modules, "run", functions)
        if lines:
            sites[name] = lines
    return sites


# A test stuck in a busy child task its main task awaits: the interrupt lands in the child, and the harness's reap must
# not then wait on the main task forever. The second stays parked past the drain after it: the after-each check.
_HUNG_IN_A_RUN = (
    "import asyncio\nfrom _async_harness import run\n\n\ndef test_a_pass():\n    pass\n\n\ndef test_b_hangs():\n"
    "    async def spins():\n        open({marker!r}, 'w').close()\n        while True:\n            pass\n\n"
    "    async def main():\n        await asyncio.create_task(spins())\n\n    run(main())\n\n\ndef test_c_later():\n    pass\n"
)
_HUNG_IN_THE_DRAIN = (
    "import asyncio\n\n\nasync def _stubborn():\n    open({marker!r}, 'w').close()\n    while True:\n        try:\n"
    "            await asyncio.sleep(3600)\n        except asyncio.CancelledError:\n            pass\n\n\n"
    "def test_a_pass():\n    pass\n\n\ndef test_b_hangs():\n    async def main():\n        asyncio.create_task(_stubborn())\n"
    "        await asyncio.sleep(0)\n\n    asyncio.run(main())\n\n\ndef test_c_later():\n    pass\n"
)


def _interrupted(micropython_bin: Path, tmp_path: Path, source: str) -> "tuple[int | None, list[str]]":
    # Runs `source` as a test file, sends SIGINT once its test has written the marker, and returns its exit code (None
    # when it did not end within ten seconds of the interrupt, and was killed) and its output lines.
    marker = tmp_path / "hung"
    test_file = tmp_path / "test_case.py"
    test_file.write_text(source.format(marker=str(marker)) + '\n\nif __name__ == "__main__":\n    import microtest\n\n    microtest.run(globals())\n', encoding="utf-8")
    env = {**os.environ, "MICROPYPATH": f"{REPO_ROOT / 'tests'}:.frozen"}
    with subprocess.Popen([str(micropython_bin), str(test_file)], cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
        deadline = time.monotonic() + 30
        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        proc.send_signal(signal.SIGINT)
        try:
            out, _ = proc.communicate(timeout=10)
            code: int | None = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            code = None
    return code, out.splitlines()


def test_a_skip_a_pass_and_a_failure_are_each_reported_and_counted(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(
        micropython_bin,
        tmp_path,
        "import microtest\n\n\ndef test_a_pass():\n    pass\n\n\ndef test_b_fail():\n    assert False, 'boom'\n\n\ndef test_c_skip():\n    raise microtest.Skip('needs a board')\n",
    )
    lines = done.stdout.splitlines()
    assert "PASS test_a_pass" in lines
    assert "FAIL test_b_fail:" in lines
    assert "SKIP test_c_skip: needs a board" in lines
    assert lines[-1] == "1/3 passed, 1 failed, 1 skipped", done.stdout
    assert done.returncode == 1


def test_a_skip_alone_is_not_a_failure(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(micropython_bin, tmp_path, "import microtest\n\n\ndef test_a_pass():\n    pass\n\n\ndef test_c_skip():\n    raise microtest.Skip('not here')\n")
    assert done.stdout.splitlines()[-1] == "1/2 passed, 0 failed, 1 skipped", done.stdout
    assert done.returncode == 0


def test_a_file_with_no_test_function_fails(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(micropython_bin, tmp_path, "def helper():\n    pass\n")
    assert done.stdout.splitlines()[-1] == "0/0 passed, 0 failed, 0 skipped - no test_* function collected", done.stdout
    assert done.returncode == 1


def test_the_pc_report_is_installed_first_and_prints_a_detached_task_dying_of_memory(micropython_bin: Path, tmp_path: Path) -> None:
    # The memory gate greps this output: a task that died of an exhausted heap, unawaited, must reach it with the
    # interpreter's own wording, whatever the firmware's DebugLevel (SPECIFICATION.md Part I.4(e)).
    done = _run(
        micropython_bin,
        tmp_path,
        "import asyncio\nimport micropython\nimport sys\n\n\n"
        "async def _dies():\n    micropython.heap_lock()\n    try:\n        bytearray(16)\n    finally:\n        micropython.heap_unlock()\n\n\n"
        "def test_a_detached_death():\n"
        "    assert asyncio.get_event_loop().get_exception_handler() is sys.modules['unix_port_unretrieved_report'].report_unretrieved\n\n"
        "    async def scenario():\n        task = asyncio.create_task(_dies())\n        for _ in range(4):\n            await asyncio.sleep(0)\n        assert task.done()\n\n"
        "    asyncio.run(scenario())\n",
    )
    lines = done.stdout.splitlines()
    assert "UNRETRIEVED TASK EXCEPTION: Task exception wasn't retrieved" in lines, done.stdout
    assert "MemoryError: memory allocation failed, heap is locked" in lines, done.stdout
    assert lines[-1] == "1/1 passed, 0 failed, 0 skipped", done.stdout
    assert done.returncode == 0


def test_an_async_test_fails_instead_of_passing_unrun(micropython_bin: Path, tmp_path: Path) -> None:
    # A coroutine function called synchronously only builds its coroutine: its body never runs, so it must not pass.
    done = _run(micropython_bin, tmp_path, "async def test_x():\n    assert False\n\n\ndef test_y():\n    return 1\n")
    lines = done.stdout.splitlines()
    assert "FAIL test_x: returned a value - an async def test_* or a stray return; microtest runs synchronous functions only" in lines, done.stdout
    assert "FAIL test_y: returned a value - an async def test_* or a stray return; microtest runs synchronous functions only" in lines, done.stdout
    assert lines[-1] == "0/2 passed, 2 failed, 0 skipped", done.stdout
    assert done.returncode == 1


def test_an_exit_inside_a_test_aborts_the_file_and_the_later_tests_are_not_run(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(micropython_bin, tmp_path, "import sys\n\n\ndef test_a():\n    pass\n\n\ndef test_b():\n    sys.exit(0)\n\n\ndef test_c():\n    print('test_c ran')\n")
    lines = done.stdout.splitlines()
    assert "PASS test_a" in lines, done.stdout
    assert "ABORT test_b:" in lines, done.stdout
    assert "test_c ran" not in lines, done.stdout
    assert lines[-1] == "1/3 passed, 1 failed, 0 skipped - aborted at test_b, later tests not run", done.stdout
    assert done.returncode == 1


def test_a_simulated_reset_escaping_a_test_fails_only_that_test(micropython_bin: Path, tmp_path: Path) -> None:
    # The loaded machine module names the reset class; microtest itself imports no fake.
    (tmp_path / "machine.py").write_text("class SimulatedRebootError(BaseException):\n    pass\n", encoding="utf-8")
    done = _run(micropython_bin, tmp_path, "import machine\n\n\ndef test_a():\n    raise machine.SimulatedRebootError\n\n\ndef test_b():\n    pass\n")
    lines = done.stdout.splitlines()
    assert "FAIL test_a: reset reached without a catch" in lines, done.stdout
    assert "PASS test_b" in lines, done.stdout
    assert lines[-1] == "1/2 passed, 1 failed, 0 skipped", done.stdout
    assert done.returncode == 1


@pytest.mark.parametrize("source", [_HUNG_IN_A_RUN, _HUNG_IN_THE_DRAIN], ids=["in_a_run", "in_the_drain"])
def test_an_interrupt_aborts_the_hung_test_by_name_and_ends_the_file(micropython_bin: Path, tmp_path: Path, source: str) -> None:
    # scripts/test.sh's per-file timeout interrupts first: the file must end, naming the test and where it hung.
    code, lines = _interrupted(micropython_bin, tmp_path, source)
    assert code == 1, lines
    assert "PASS test_a_pass" in lines, lines
    assert lines.index("ABORT test_b_hangs:") < lines.index("Traceback (most recent call last):"), lines
    assert any(line.startswith("KeyboardInterrupt") for line in lines), lines
    assert lines[-1] == "1/3 passed, 1 failed, 0 skipped - aborted at test_b_hangs, later tests not run", lines


def test_an_interrupted_run_names_the_line_it_hung_on(micropython_bin: Path, tmp_path: Path) -> None:
    _, lines = _interrupted(micropython_bin, tmp_path, _HUNG_IN_A_RUN)
    assert any(line.startswith('  File "') and line.endswith(", in spins") for line in lines), lines


def test_the_tests_run_in_name_order_not_the_namespaces_hash_order(micropython_bin: Path, tmp_path: Path) -> None:
    names = [f"test_{letter}" for letter in "abcdefghijklmnopqrstuvwxyz"]
    done = _run(micropython_bin, tmp_path, "".join(f"def {name}():\n    pass\n\n\n" for name in reversed(names)))
    ran = [line.removeprefix("PASS ") for line in done.stdout.splitlines() if line.startswith("PASS ")]
    assert ran == names, done.stdout
    assert done.returncode == 0


# ---------------------------------------------------------------------------
# The conventions of tests/, read by AST
# ---------------------------------------------------------------------------


def _calls(tree: ast.Module, module_names: "set[str]", attribute: str, function_names: "set[str]") -> "list[int]":
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            on_module = isinstance(func, ast.Attribute) and func.attr == attribute and isinstance(func.value, ast.Name) and func.value.id in module_names
            if on_module or (isinstance(func, ast.Name) and func.id in function_names):
                lines.append(node.lineno)
    return lines


def _duplicate_scratch_keys(directory: Path) -> "list[str]":
    owners: dict[str, list[str]] = {}
    for name, line, key in _scratch_keys(directory):
        owners.setdefault(key, []).append(f"{name}:{line}")
    return [f"{key}: {sites}" for key, sites in sorted(owners.items()) if len(sites) > 1]


def _json_loads_sites(directory: Path) -> "dict[str, list[int]]":
    sites = {}
    for name, tree in _parsed(directory, "*.py"):
        modules, functions = _json_module_names(tree)
        lines = _calls(tree, modules, "loads", functions)
        if lines:
            sites[name] = lines
    return sites


def _json_module_names(tree: ast.Module) -> "tuple[set[str], set[str]]":
    # The names `json` is imported under, and the names its loads() is imported under, anywhere in the file.
    modules: set[str] = set()
    functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == "json")
        elif isinstance(node, ast.ImportFrom) and node.module == "json":
            functions.update(alias.asname or alias.name for alias in node.names if alias.name == "loads")
    return modules, functions


@functools.cache
def _parse(source: str, filename: str) -> ast.Module:
    # Once per distinct text: five scans read the same 120 files, and a planted file is rewritten between two scans.
    return ast.parse(source, filename)


def _parsed(directory: Path, pattern: str) -> "list[tuple[str, ast.Module]]":
    return [(path.name, _parse(path.read_text(encoding="utf-8"), str(path))) for path in sorted(directory.glob(pattern))]


def _public_double_problems(directory: Path) -> "list[str]":
    # A test file's own doubles and builders are private; a shared one lives in a tests/_*.py module.
    problems = []
    for name, tree in _parsed(directory, "test_*.py"):
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.startswith("Fake"):
                problems.append(f"{name}:{node.lineno}: class {node.name} - a file-local double is _Fake...")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("make_"):
                problems.append(f"{name}:{node.lineno}: def {node.name} - a file-local builder is _make_...")
    return problems


def _run(micropython_bin: Path, tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    test_file = tmp_path / "test_case.py"
    test_file.write_text(source + '\n\nif __name__ == "__main__":\n    import microtest\n\n    microtest.run(globals())\n', encoding="utf-8")
    env = {**os.environ, "MICROPYPATH": f"{REPO_ROOT / 'tests'}:.frozen"}
    return subprocess.run([str(micropython_bin), str(test_file)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60)


def _scratch_keys(directory: Path) -> "list[tuple[str, int, str]]":
    # (file, line, key) of every TmpScratch(<literal or f-string>) outside a test function, where TmpScratch's own tests
    # re-take a key on purpose (refused at run time); an f-string's prefix is taken with each derived device's name.
    keys = []
    for name, tree in _parsed(directory, "*.py"):
        outside = [top for top in tree.body if not (isinstance(top, ast.FunctionDef) and top.name.startswith("test_"))]
        for node in (node for top in outside for node in ast.walk(top)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "TmpScratch" and node.args):
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.append((name, node.lineno, arg.value))
            elif isinstance(arg, ast.JoinedStr) and arg.values and isinstance(arg.values[0], ast.Constant):
                keys += [(name, node.lineno, str(arg.values[0].value) + device) for device in DEVICE_NAMES]
    return keys


def _trailer_problems(directory: Path) -> "list[str]":
    # Each test file ends with the canonical trailer and binds test_* only to synchronous functions.
    trailer = ast.dump(ast.parse(_TRAILER).body[0])
    problems = []
    for name, tree in _parsed(directory, "test_*.py"):
        if not tree.body or ast.dump(tree.body[-1]) != trailer:
            problems.append(f"{name}: does not end with the canonical microtest trailer")
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
                problems.append(f"{name}:{node.lineno}: async def {node.name} - microtest runs synchronous functions only")
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
            bound = [t.id for t in targets if isinstance(t, ast.Name) and t.id.startswith("test_")]
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                bound += [alias.asname or alias.name for alias in node.names if (alias.asname or alias.name).startswith("test_")]
            value = getattr(node, "value", None)
            registered = isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "register_for_device"
            problems += [f"{name}:{node.lineno}: {target} is bound to something other than a function" for target in bound if not registered]
    return problems


def test_every_test_file_ends_with_the_canonical_trailer_and_binds_only_functions() -> None:
    assert len(list(_TESTS.glob("test_*.py"))) >= 80  # the floor: a glob matching nothing would pass vacuously
    assert _trailer_problems(_TESTS) == []


def test_asyncio_run_is_called_only_in_the_harness() -> None:
    sites = _asyncio_run_sites(_TESTS)
    assert sites.pop(_HARNESS, []), "the harness's own asyncio.run() call was not found - the scan reads nothing"
    assert sites == {}


def test_json_loads_reads_no_response_body() -> None:
    sites = _json_loads_sites(_TESTS)
    assert sites.pop("_strict_json.py", []), "the oracle's own json.loads() was not found - the scan reads nothing"
    counts = {name: len(lines) for name, lines in sites.items()}
    assert counts == {name: count for name, (count, _reason) in _JSON_LOADS_ALLOWED.items()}, sites


def test_test_files_keep_their_doubles_and_builders_private() -> None:
    assert _public_double_problems(_TESTS) == []


def test_every_scratch_key_is_taken_once_across_the_test_tree() -> None:
    assert len(_scratch_keys(_TESTS)) >= 10
    assert _duplicate_scratch_keys(_TESTS) == []


_PLANTED = {
    "trailer": ("test_planted.py", "def test_a():\n    pass\n", _trailer_problems),
    "async": ("test_planted.py", "async def test_a():\n    pass\n\n\n" + _TRAILER, _trailer_problems),
    "bound": ("test_planted.py", "test_a = print\n\n\n" + _TRAILER, _trailer_problems),
    "asyncio_run": ("_planted.py", "import asyncio as aio\n\n\ndef go(c):\n    return aio.run(c)\n", lambda d: [str(_asyncio_run_sites(d))] if _asyncio_run_sites(d) else []),
    "json_loads": ("_planted.py", "from json import loads\n\n\ndef body(b):\n    return loads(b)\n", lambda d: [str(_json_loads_sites(d))] if _json_loads_sites(d) else []),
    "fake_class": ("test_planted.py", "class FakeRadio:\n    pass\n\n\n" + _TRAILER, _public_double_problems),
    "builder": ("test_planted.py", "def make_radio():\n    pass\n\n\n" + _TRAILER, _public_double_problems),
    "scratch_key": ("_planted.py", 'a = TmpScratch("dup")\nb = TmpScratch(f"d{x}")\nc = TmpScratch("dup")\n', _duplicate_scratch_keys),
}


@pytest.mark.parametrize("case", sorted(_PLANTED))
def test_a_planted_violation_is_found_and_its_clean_form_is_not(tmp_path: Path, case: str) -> None:
    filename, source, scan = _PLANTED[case]
    (tmp_path / filename).write_text(source, encoding="utf-8")
    assert scan(tmp_path), f"the planted {case} violation passed the scan"
    (tmp_path / filename).write_text("def test_a():\n    pass\n\n\n" + _TRAILER, encoding="utf-8")
    assert scan(tmp_path) == []
