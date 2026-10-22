"""Runs every hardware instrument in the twin at each GC stage and writes the twin record (twin_record.json in
tests_hardware): the flash tier under `pytest --twin`, each device script no flash test runs through TwinBoard, the
bench tier as needing the bridge. test_twin_record.py keeps it current."""

# Usage: .venv/bin/python scripts/record_twin_instrument_runs.py [--reasons FILE]
# FILE is JSON {"tests_hardware/<path>": "<why it cannot run in the twin>"}. Never builds the Unix port: exit 1 without it.

import argparse
import ast
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests_hardware"))
import twin_board  # noqa: E402 - tests_hardware/ is on sys.path from the line above
from harness import HardwareNotAvailableError, HardwareTestFailureError  # noqa: E402 - tests_hardware/ is on sys.path from the line above

if TYPE_CHECKING:
    from collections.abc import Generator

TESTS_HARDWARE = REPO_ROOT / "tests_hardware"
DEVICE_SCRIPTS = TESTS_HARDWARE / "device_scripts"
RECORD = TESTS_HARDWARE / "twin_record.json"
RUNNER_FILES = (REPO_ROOT / "digital_twin" / "run_device_script.py", TESTS_HARDWARE / "twin_board.py")
BENCH_REASON = "needs the bench bridge (network, WLAN role-reversal)"
_INCLUDE = "# @include _shared/"
# @tunable l3.record_twin_flash_run_timeout_s = 3600.0
_FLASH_RUN_TIMEOUT_S = 3600.0  # the whole flash tier under --twin, one pytest process
# MicroPython's own reactive default, the stage the whole design must hold at, then the firmware boot entry's value.
GC_THRESHOLDS = (-1, 32768)
_STAGE_OPTION = "--record-gc-threshold"  # this module as the flash run's pytest plugin: the stage its twin board runs at
_STAGED = pytest.StashKey[int]()  # the twin boards the plugin staged in one flash run


def _flash_outcomes(stage: int) -> "dict[str, dict[str, list[str]]]":
    # Each flash module's test functions with their failures at `stage` (empty: every case passed), from one `pytest
    # --twin` run's JUnit report with this module as its plugin; a case skipped under --twin is a failure to record.
    with tempfile.TemporaryDirectory(prefix="twin_record_") as tmp:
        report = Path(tmp) / "flash.xml"
        # The wear gates' deselecting flags: the twin's flash and SCD30 NVM are files, and a deselected test is no record.
        argv = ["uv", "run", "--no-sync", "pytest", "tests_hardware/flash", "--twin", "--allow-persistence-write", "--allow-scd30-extra-write", "-p", "no:cacheprovider", "-p", "scripts.record_twin_instrument_runs", _STAGE_OPTION, str(stage), "-q", f"--junitxml={report}"]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, (str(REPO_ROOT), os.environ.get("PYTHONPATH")))))  # the plugin's import
        proc = subprocess.run(argv, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=_FLASH_RUN_TIMEOUT_S, check=False)
        if not report.is_file():
            raise SystemExit(f"record_twin_instrument_runs: pytest --twin wrote no report (exit {proc.returncode}):\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}")
        if " deselected" in proc.stdout:  # a deselected test never reaches the report, so its scripts would read as run
            raise SystemExit(f"record_twin_instrument_runs: pytest --twin deselected tests - every instrument must run:\n{proc.stdout[-2000:]}")
        if staged_line(stage) not in proc.stdout:  # a board left at the default would record the -1 stage twice
            raise SystemExit(f"record_twin_instrument_runs: the flash run's twin board never took gc.threshold({stage}):\n{proc.stdout[-2000:]}")
        outcomes: dict[str, dict[str, list[str]]] = {}
        for case in ET.parse(report).getroot().iter("testcase"):  # pytest's own report, written just above
            module = "tests_hardware/flash/" + case.get("classname", "").rsplit(".", 1)[-1] + ".py"
            problems = outcomes.setdefault(module, {}).setdefault(case.get("name", "").split("[", 1)[0], [])
            for kind in ("failure", "error", "skipped"):
                problems += [f"{case.get('name')}: {kind}: {(node.get('message') or '').splitlines()[0] if node.get('message') else kind}" for node in case.iter(kind)]
    return outcomes


def _includes(path: Path, seen: "set[Path] | None" = None) -> "list[Path]":
    # The _shared/ files `path` includes, nested includes too, each once.
    seen = set() if seen is None else seen
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(_INCLUDE):
            include = DEVICE_SCRIPTS / "_shared" / line[len(_INCLUDE) :].strip()
            if include not in seen and include.is_file():
                seen.add(include)
                _includes(include, seen)
    return sorted(seen)


def _problems(path: Path, flash: "dict[str, dict[str, list[str]]]", run_by: "dict[str, list[tuple[str, str]]]") -> "list[str]":
    # One instrument's failures at one stage: a flash module's own, a device script those of the flash tests running it.
    key = path.relative_to(REPO_ROOT).as_posix()
    if path.parent.name == "flash":
        return [problem for problems in flash[key].values() for problem in problems] if key in flash else ["no test of it ran under --twin"]
    return [f"run by {module}: {problem}" for module, test in run_by[key] for problem in flash.get(module, {}).get(test, [f"{test}: no case of it ran under --twin"])]


def _reached(name: str, top: "dict[str, ast.AST]") -> "set[str]":
    # The device scripts module-level `name` names (a "<name>.py" string constant naming a file in device_scripts/),
    # through the module-level constants, helpers and fixtures it uses too, each followed once.
    scripts: set[str] = set()
    seen: set[str] = set()
    todo = [name]
    while todo:
        current = todo.pop()
        if current in seen:
            continue
        seen.add(current)
        for node in ast.walk(top[current]):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(".py") and (DEVICE_SCRIPTS / node.value).is_file():
                scripts.add(node.value)
            elif isinstance(node, ast.Name) and node.id in top:
                todo.append(node.id)
            elif isinstance(node, ast.arg) and node.arg in top:
                todo.append(node.arg)
    return scripts


def _scripts_run_by_flash() -> "dict[str, list[tuple[str, str]]]":
    # Each device script a flash test runs, with every (module, test) reaching it: a test's failure is charged to the
    # scripts it runs, never to its siblings'.
    run_by: dict[str, list[tuple[str, str]]] = {}
    for module in sorted((TESTS_HARDWARE / "flash").glob("*.py")):
        top: dict[str, ast.AST] = {}
        for node in ast.parse(module.read_text(encoding="utf-8")).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                top[node.name] = node
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                top.update((target.id, node) for target in (node.targets if isinstance(node, ast.Assign) else [node.target]) if isinstance(target, ast.Name))
        for name in sorted(name for name in top if name.startswith("test_")):
            for script in sorted(_reached(name, top)):
                run_by.setdefault(f"tests_hardware/device_scripts/{script}", []).append((module.relative_to(REPO_ROOT).as_posix(), name))
    return run_by


def api_sha256(path: Path) -> str:
    # sha256 over the src/ modules the file imports, its includes' imports too (by ast), in name order.
    names: set[str] = set()
    for source in [path, *(_includes(path) if path.parent == DEVICE_SCRIPTS else [])]:
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.add(node.module.split(".")[0])
    return files_sha256(*(REPO_ROOT / "src" / f"{name}.py" for name in sorted(names) if (REPO_ROOT / "src" / f"{name}.py").is_file()))


def entry_hashes(path: Path) -> "dict[str, str]":
    # The three hashes an entry pins: the file itself (a device script with its includes), the runner, the src/ API.
    own = [path, *_includes(path)] if path.parent == DEVICE_SCRIPTS else [path]
    return {"sha256": files_sha256(*own), "runner_sha256": files_sha256(*RUNNER_FILES), "api_sha256": api_sha256(path)}


def files_sha256(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def instruments() -> "list[Path]":
    # Every instrument the record covers: the device scripts (never the _shared/ includes), the flash and bench tests.
    return sorted([*DEVICE_SCRIPTS.glob("*.py"), *(TESTS_HARDWARE / "flash").glob("test_*.py"), *(TESTS_HARDWARE / "bench").glob("test_*.py")])


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Record every hardware instrument's twin run in the twin record.")
    parser.add_argument("--reasons", type=Path, help="JSON {path: reason} naming why an instrument cannot run in the twin")
    args = parser.parse_args(argv)
    binary = twin_board.unix_port_binary()
    if not binary.is_file():
        print(f"record_twin_instrument_runs: MicroPython Unix port not built at {binary} - run scripts/test.sh once", file=sys.stderr)
        return 1
    reasons: dict[str, str] = json.loads(args.reasons.read_text(encoding="utf-8")) if args.reasons else {}
    flash = {stage: _flash_outcomes(stage) for stage in GC_THRESHOLDS}
    run_by = _scripts_run_by_flash()
    date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record: dict[str, dict[str, object]] = {}
    unexplained: list[str] = []
    for path in instruments():
        key = path.relative_to(REPO_ROOT).as_posix()
        stages: dict[int, list[str]] = {}
        for stage in GC_THRESHOLDS:
            if path.parent.name == "bench":
                stages[stage] = [BENCH_REASON]
            elif path.parent.name == "flash" or key in run_by:
                stages[stage] = _problems(path, flash[stage], run_by)
            else:
                try:
                    twin_board.TwinBoard(gc_threshold=stage).run_isolated(path)
                    stages[stage] = []
                except (HardwareTestFailureError, HardwareNotAvailableError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                    stages[stage] = [f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}"]
        problems = [f"gc.threshold({stage}): {problem}" for stage, found in stages.items() for problem in found]
        reason = BENCH_REASON if path.parent.name == "bench" else reasons.get(key, "")
        # A failure with no reason given (--reasons) fails the run.
        if problems and not reason:
            unexplained.append(f"{key}: {'; '.join(problems)}")
        outcomes = {str(stage): "exception" if found else "pass" for stage, found in stages.items()}
        record[key] = {**entry_hashes(path), "result": "exception" if problems else "pass", "reason": reason if problems else "", "stages": outcomes, "date": date}
    if unexplained:
        print("record_twin_instrument_runs: these failed in the twin with no reason given (--reasons):\n" + "\n".join(unexplained), file=sys.stderr)
        return 1
    tmp = RECORD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(RECORD)
    print(f"record_twin_instrument_runs: {len(record)} instruments recorded in {RECORD.relative_to(REPO_ROOT)}")
    return 0


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(_STAGE_OPTION, type=int, default=None, help="the GC stage the twin board runs every script at (the twin record's flash run)")


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef: "pytest.FixtureDef[object]", request: pytest.FixtureRequest) -> "Generator[None, object, object]":
    # Every twin board a fixture yields runs at the recorder's stage, as if made with it; staged_line() reports the count.
    del fixturedef
    value = yield
    stage = request.config.getoption(_STAGE_OPTION)
    if stage is not None and isinstance(value, twin_board.TwinBoard):
        value.gc_threshold = stage
        request.config.stash[_STAGED] = request.config.stash.get(_STAGED, 0) + 1
    return value


def pytest_terminal_summary(terminalreporter: "pytest.TerminalReporter", exitstatus: int, config: pytest.Config) -> None:
    del exitstatus
    stage = config.getoption(_STAGE_OPTION)
    if stage is not None and config.stash.get(_STAGED, 0):
        terminalreporter.write_line(staged_line(stage))


def staged_line(stage: int) -> str:
    # The flash run's own word that its twin board took `stage`; its absence refuses the run.
    return f"record_twin_instrument_runs: the twin board ran at gc.threshold({stage})"


if __name__ == "__main__":
    raise SystemExit(main())
