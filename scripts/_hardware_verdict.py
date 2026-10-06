#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Judges a hardware pytest run from its run record (scripts/_pytest_run_record.py) and prints the
summary block (SPECIFICATION.md E.10): every skip, deselection, recovery and note is read from the
record by nodeid and marker, never grepped from output a caller's -q or a collection skip can hide."""

# Usage: _hardware_verdict.py --run-record PATH --pytest-exit N --runner NAME --levels TEXT
# [--not-clean-reason TEXT]. Exits pytest's own code when nonzero, 1 for a failed verdict, 4 for a
# passing run that is NOT CLEAN, 2 for a usage error, else 0.

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/, for the shared summary block

from _summary_block import Summary, from_run_record  # type: ignore[import-not-found]

# Skip-gating marker -> the option (argparse dest) that runs it: its skip is expected only while
# that option is unset. The wear gates deselect instead and reach the verdict as deselections.
GATE_OPTIONS = {
    "flash_cycle": "allow_flash_cycle",
    "long_soak": "soak_tier",
    "multi_day_rollover": "allow_multi_day_rollover_wait",
    "neopixel_sweep": "allow_neopixel_sweep",
}

PERMANENT_SKIPS = (
    # A real rogue-NTP spoof needs an off-subnet host the bench lacks (owner, 2026-09-26; attempted on the bench first).
    "tests_hardware/bench/test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored",
)

_NOT_COVERED = "not covered by this run"


def _flag(dest: str) -> str:
    return "--" + dest.replace("_", "-")


def _load(path: Path) -> "dict[str, object]":
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def _entries(record: "dict[str, object]", key: str) -> "list[dict[str, object]]":
    value = record.get(key)
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def _judge_skip(nodeid: str, reason: str, markers: "list[str]", options: "dict[str, object]") -> "tuple[str, str]":
    # (kind, detail) for one skipped test: an expected skip stays a skip, anything else fails.
    if nodeid in PERMANENT_SKIPS:
        return "skipped", reason
    for marker in markers:
        dest = GATE_OPTIONS.get(marker)
        if dest is not None:
            if options.get(dest):
                return "failed", f"skipped although {_flag(dest)} was given: {reason}"
            return "skipped", f"{reason} (gate {_flag(dest)} not given)"
    return "failed", f"unexpected skip: {reason}"


@dataclass
class _Verdict(Summary):  # type: ignore[misc]  # Summary is Any to mypy: scripts/ is not on host_typecheck.ini's mypy_path
    # pytest's own nonzero exit is propagated unchanged, so its Result names it rather than reading
    # pytest's 2 (interrupted) or 4 (its usage error) as this block's usage-error or NOT CLEAN code.
    pytest_exit: int = 0

    def result(self, exit_code: int) -> str:
        return f"FAIL (pytest exited {self.pytest_exit})" if self.pytest_exit else super().result(exit_code)


def judge(record_path: Path, pytest_exit: int, runner: str, levels: str, not_clean_reason: "str | None") -> int:
    record = _load(record_path)
    summary = _Verdict(runner=runner, levels=levels, pytest_exit=pytest_exit)
    if record.get("collect_only") and pytest_exit == 0:
        return _not_a_run(summary, record)
    base = from_run_record(record_path)
    raw_options = record.get("options")
    options: dict[str, object] = raw_options if isinstance(raw_options, dict) else {}
    markers: dict[str, list[str]] = {}
    for entry in _entries(record, "tests"):
        raw_markers = entry.get("markers")
        markers[str(entry.get("nodeid"))] = [str(m) for m in raw_markers] if isinstance(raw_markers, list) else []
    for kind in ("passed", "failed", "retried", "recovered", "vacuous"):
        for name, detail in getattr(base, kind):
            summary.add(kind, name, detail)
    for name, text in base.notes:
        summary.note(name, text)
    for name, reason in base.skipped:
        kind, detail = _judge_skip(name, reason, markers.get(name, []), options)
        summary.add(kind, name, detail)
    wear_flags = []
    for name, by in base.deselected:
        if by == "runner selection":
            summary.add("deselected", name, f"runner selection (-m), {_NOT_COVERED}")
        else:
            summary.add("deselected", name, f"wear gate {by}, {_NOT_COVERED}")
            wear_flags.append(by)
    if pytest_exit != 0 and not summary.failed:  # a failing pytest with no failed item still names one
        summary.add("failed", "pytest session", f"pytest exited {pytest_exit}")
    if not any(entry.get("outcome") == "passed" for entry in _entries(record, "tests")):  # a session note is no test
        summary.add("failed", "run", "no test passed - real hardware is expected to be attached and reachable for the whole run")

    if wear_flags:
        flags = " ".join(dict.fromkeys(wear_flags))
        print(f"Not covered: {len(wear_flags)} test(s) deselected by a wear gate; {flags} would select them.")

    if pytest_exit != 0:
        exit_code = pytest_exit
    elif summary.failed or summary.vacuous:
        exit_code = 1
    elif not_clean_reason:
        summary.not_clean_reason = not_clean_reason
        exit_code = 4
    else:
        exit_code = 0
    summary.print(exit_code)
    return exit_code


class _CollectionOnly(Summary):  # type: ignore[misc]
    def result(self, exit_code: int) -> str:  # noqa: ARG002 - the same verdict whatever the code
        return "NOT A RUN (collection only)"


def _not_a_run(summary: Summary, record: "dict[str, object]") -> int:
    # A collection pass ran nothing: its deselections are listed, nothing is judged.
    block = _CollectionOnly(runner=summary.runner, levels=summary.levels)
    for entry in _entries(record, "deselected"):
        block.add("deselected", str(entry.get("nodeid")), str(entry.get("by") or "runner selection"))
    block.print(0)
    return 0


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-record", type=Path, required=True, metavar="PATH", help="the run record scripts/_pytest_run_record.py wrote")
    parser.add_argument("--pytest-exit", type=int, required=True, metavar="N", help="pytest's own exit code")
    parser.add_argument("--runner", required=True, help="the runner named in the summary block")
    parser.add_argument("--levels", required=True, help="the Levels: line of the summary block")
    parser.add_argument("--not-clean-reason", default=None, metavar="TEXT", help="report a passing run as NOT CLEAN (exit 4) for this reason")
    args = parser.parse_args(argv)  # a usage error exits 2 (argparse)
    return judge(args.run_record, args.pytest_exit, args.runner, args.levels, args.not_clean_reason)


if __name__ == "__main__":
    raise SystemExit(main())
