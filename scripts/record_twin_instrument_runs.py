"""Runs every hardware instrument in the twin and writes the twin record (twin_record.json in tests_hardware): the
flash tier under `pytest --twin`, each device script no flash test runs through TwinBoard, the bench tier as needing
the bridge. A failure with no reason given (--reasons) fails the run; tests_scripts/test_twin_record.py keeps it current."""

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

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests_hardware"))
import twin_board  # noqa: E402  (tests_hardware/ is on the path from the line above)
from harness import HardwareNotAvailableError, HardwareTestFailureError  # noqa: E402

TESTS_HARDWARE = REPO_ROOT / "tests_hardware"
DEVICE_SCRIPTS = TESTS_HARDWARE / "device_scripts"
RECORD = TESTS_HARDWARE / "twin_record.json"
RUNNER_FILES = (REPO_ROOT / "digital_twin" / "run_device_script.py", TESTS_HARDWARE / "twin_board.py")
BENCH_REASON = "needs the bench bridge (network, WLAN role-reversal)"
_INCLUDE = "# @include _shared/"
# @tunable l3.record_twin_flash_run_timeout_s = 3600.0
_FLASH_RUN_TIMEOUT_S = 3600.0  # the whole flash tier under --twin, one pytest process
_GC_THRESHOLD = -1  # every run at MicroPython's own reactive default, the stage the whole design must hold at


def _flash_outcomes() -> "dict[str, list[str]]":
    # Each flash module's failures (empty: every test in it passed) from one `pytest --twin` run's JUnit report; a test
    # skipped under --twin counts as a failure to record, never as a pass.
    with tempfile.TemporaryDirectory(prefix="twin_record_") as tmp:
        report = Path(tmp) / "flash.xml"
        # The wear gates' deselecting flags: the twin's flash and SCD30 NVM are files, and a deselected test is no record.
        argv = ["uv", "run", "--no-sync", "pytest", "tests_hardware/flash", "--twin", "--allow-persistence-write", "--allow-scd30-extra-write", "-p", "no:cacheprovider", "-q", f"--junitxml={report}"]
        proc = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True, timeout=_FLASH_RUN_TIMEOUT_S, check=False)  # noqa: S603 - a fixed argv, no shell
        if not report.is_file():
            raise SystemExit(f"record_twin_instrument_runs: pytest --twin wrote no report (exit {proc.returncode}):\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}")
        if " deselected" in proc.stdout:  # a deselected test never reaches the report, so its scripts would read as run
            raise SystemExit(f"record_twin_instrument_runs: pytest --twin deselected tests - every instrument must run:\n{proc.stdout[-2000:]}")
        outcomes: dict[str, list[str]] = {}
        for case in ET.parse(report).getroot().iter("testcase"):  # noqa: S314 - pytest's own report, written just above
            module = "tests_hardware/flash/" + case.get("classname", "").rsplit(".", 1)[-1] + ".py"
            problems = outcomes.setdefault(module, [])
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


def _scripts_run_by_flash() -> "dict[str, str]":
    # Each device script a flash module names (a "<name>.py" string constant naming a file in device_scripts/), with the
    # first module naming it: its run is that module's.
    run_by: dict[str, str] = {}
    for module in sorted((TESTS_HARDWARE / "flash").glob("*.py")):
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(".py") and (DEVICE_SCRIPTS / node.value).is_file():
                run_by.setdefault(f"tests_hardware/device_scripts/{node.value}", module.relative_to(REPO_ROOT).as_posix())
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
    flash = _flash_outcomes()
    run_by = _scripts_run_by_flash()
    date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record: dict[str, dict[str, object]] = {}
    unexplained: list[str] = []
    for path in instruments():
        key = path.relative_to(REPO_ROOT).as_posix()
        if path.parent.name == "bench":
            problems = [BENCH_REASON]
        elif path.parent.name == "flash":
            problems = flash.get(key, ["no test of it ran under --twin"])
        elif key in run_by:
            problems = [f"run by {run_by[key]}: {problem}" for problem in flash.get(run_by[key], ["no test of it ran under --twin"])]
        else:
            try:
                twin_board.TwinBoard(gc_threshold=_GC_THRESHOLD).run_isolated(path)
                problems = []
            except (HardwareTestFailureError, HardwareNotAvailableError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                problems = [f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}"]
        reason = BENCH_REASON if path.parent.name == "bench" else reasons.get(key, "")
        if problems and not reason:
            unexplained.append(f"{key}: {'; '.join(problems)}")
        record[key] = {**entry_hashes(path), "result": "exception" if problems else "pass", "reason": reason if problems else "", "gc_threshold": _GC_THRESHOLD, "date": date}
    if unexplained:
        print("record_twin_instrument_runs: these failed in the twin with no reason given (--reasons):\n" + "\n".join(unexplained), file=sys.stderr)
        return 1
    tmp = RECORD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, RECORD)
    print(f"record_twin_instrument_runs: {len(record)} instruments recorded in {RECORD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
