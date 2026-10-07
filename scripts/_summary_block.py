#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Python emitter of the runner summary block (SPECIFICATION.md E.10), byte-identical to
scripts/_summary_block.sh, plus the reader of a scripts/_pytest_run_record.py run record."""

# Usage: _summary_block.py --from-run-record PATH (--counts-only | --list KIND)
# --counts-only prints "P F S D" (passed failed skipped deselected) for scripts/test.sh's L0 line;
# --list prints one "name<TAB>detail" line per item of that kind (or per note, for "notes"). A usage error exits 2.

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("passed", "failed", "skipped", "deselected", "retried", "recovered", "vacuous")
_TITLES = (("failed", "Failed"), ("skipped", "Skipped"), ("deselected", "Deselected"), ("retried", "Passed only on retry"), ("recovered", "Recovery passes"), ("vacuous", "Checked nothing"))
_NO_RECORD = "no verdict (run record missing or unreadable)"
# pytest's own exit codes for a session that did not run to a verdict (pytest.ExitCode).
_ABORTED_EXITS = {2: "interrupted", 3: "internal error", 4: "usage error"}
_NO_TESTS_COLLECTED = 5
_PASSING_EXITS = (0, 3, 4)  # E.10: pass, pass with the coverage render failed, NOT CLEAN


@dataclass(frozen=True)
class Counts:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    deselected: int = 0
    retried: int = 0
    recovered: int = 0
    vacuous: int = 0

    def line(self, unit: str) -> str:
        return f"Counts ({unit}): passed {self.passed} · failed {self.failed} · skipped {self.skipped} · deselected {self.deselected} · retried {self.retried} · recovered {self.recovered} · vacuous {self.vacuous}"


@dataclass
class Summary:
    runner: str
    unit: str = "tests"
    passed: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    deselected: list[tuple[str, str]] = field(default_factory=list)
    retried: list[tuple[str, str]] = field(default_factory=list)
    recovered: list[tuple[str, str]] = field(default_factory=list)
    vacuous: list[tuple[str, str]] = field(default_factory=list)
    levels: str | None = None
    gc_stage: str | None = None
    extra_counts: list[tuple[str, Counts]] = field(default_factory=list)
    not_clean_reason: str | None = None
    notes: list[tuple[str, str]] = field(default_factory=list)

    def add(self, kind: str, name: str, detail: str = "") -> None:
        # Files one item; an empty kind is a missing verdict and files it failed (E.10).
        if not kind:
            kind, detail = "failed", "no verdict"
        if kind not in KINDS:
            raise ValueError(f"unknown summary kind {kind!r} (one of: {' '.join(KINDS)})")
        self._items(kind).append((name, detail))

    def note(self, name: str, text: str = "") -> None:
        # Lists one note under Notes:; a note is never counted and never changes the result.
        self.notes.append((name, text))

    def _items(self, kind: str) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = getattr(self, kind)
        return items

    def counts(self) -> Counts:
        return Counts(*(len(self._items(kind)) for kind in KINDS))

    def exit_code(self, given: int) -> int:
        # The code the block prints and the caller exits with: a failed or vacuous item raises a passing
        # code (0, 3, 4) to 1; a failure code (1, 2, any other) is kept.
        counts = self.counts()
        if (counts.failed or counts.vacuous) and given in _PASSING_EXITS:
            return 1
        return given

    def result(self, exit_code: int) -> str:
        counts = self.counts()
        if exit_code == 2:  # noqa: PLR2004 - E.10's usage-error code
            return "USAGE ERROR"
        if counts.failed or counts.vacuous:
            return "FAIL"
        if exit_code == 0:
            return "PASS"
        if exit_code == 3:  # noqa: PLR2004 - E.10's coverage-render-only code
            return "PASS (coverage report not rendered)"
        if exit_code == 4:  # noqa: PLR2004 - E.10's NOT CLEAN code
            return f"NOT CLEAN ({self.not_clean_reason})" if self.not_clean_reason else "NOT CLEAN"
        return "FAIL"

    def render(self, exit_code: int) -> str:
        exit_code = self.exit_code(exit_code)
        lines = [f"== Summary: {self.runner} ==", f"Commit: {_commit()}"]
        if self.levels is not None:
            lines.append(f"Levels: {self.levels}")
        if self.gc_stage is not None:
            lines.append(f"GC stage: {self.gc_stage}")
        lines.append(self.counts().line(self.unit))
        lines.extend(counts.line(unit) for unit, counts in self.extra_counts)
        for kind, title in _TITLES:
            items = self._items(kind)
            lines.append(f"{title}:" if items else f"{title}: none")
            lines.extend(_item_line(kind, name, detail) for name, detail in items)
            if kind == "recovered":
                lines.append("Notes:" if self.notes else "Notes: none")
                lines.extend(_item_line("note", name, text) for name, text in self.notes)
        lines.extend((f"Result: {self.result(exit_code)}", f"Exit code: {exit_code}"))
        return "\n".join(lines) + "\n"

    def print(self, exit_code: int) -> int:
        # Prints the block and returns the code it printed; the caller exits with that code.
        sys.stdout.write(self.render(exit_code))
        sys.stdout.flush()
        return self.exit_code(exit_code)


def _item_line(kind: str, name: str, detail: str) -> str:
    if not detail:
        return f"  - {name}"
    if kind == "deselected":
        return f"  - {name}: by {detail}"
    if kind == "retried":
        return f"  - {name} (attempt {detail})"
    return f"  - {name}: {detail}"


def _git(*args: str) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run([git, *args], capture_output=True, text=True, check=False)  # noqa: S603 - fixed git subcommands
    except OSError:
        return None
    return done.stdout if done.returncode == 0 else None


def _commit() -> str:
    sha = (_git("rev-parse", "--short", "HEAD") or "").strip()
    if not sha:
        return "unknown"
    # A status git cannot report reads as dirty: an unknown tree is never presented as the commit.
    porcelain = _git("status", "--porcelain")
    return f"{sha} (uncommitted changes)" if porcelain is None or porcelain.strip() else sha


def _props(props: object) -> list[tuple[str, str]]:
    # Every user_properties (key, value) pair, the value as text.
    pairs = props if isinstance(props, list) else []
    return [(str(p[0]), str(p[1])) for p in pairs if isinstance(p, list) and len(p) == 2]  # noqa: PLR2004 - a (key, value) pair


def _add_test(summary: Summary, entry: dict[str, object]) -> None:
    nodeid = str(entry.get("nodeid") or "<unnamed test>")
    outcome = entry.get("outcome")
    reason = str(entry.get("reason") or "")
    props = _props(entry.get("user_properties"))
    recoveries = [text for key, text in props if key == "recovery"]
    if outcome == "passed":
        if recoveries:
            summary.add("recovered", nodeid, "; ".join(recoveries))
        else:
            summary.add("passed", nodeid)
    elif outcome == "skipped":
        summary.add("skipped", nodeid, reason)
    elif outcome in ("failed", "error"):
        summary.add("failed", nodeid, f"{outcome} in {entry.get('when') or '?'}" + (f": {reason}" if reason else ""))
    else:
        summary.add("", nodeid)
    # Every result note is listed; a recovery note of a test that did not pass becomes one too.
    for key, text in props:
        if key == "result_note" or (key == "recovery" and outcome != "passed"):
            summary.note(nodeid, f"recovery: {text}" if key == "recovery" else text)


def from_run_record(path: Path) -> Summary:
    # The pytest run record as a Summary (unit tests); a missing or unreadable record is one failed item.
    summary = Summary("pytest")
    try:
        record = json.loads(path.read_text())
        if not isinstance(record, dict):
            raise TypeError("not a JSON object")
    except (OSError, TypeError, ValueError):
        summary.add("failed", str(path), _NO_RECORD)
        return summary
    for entry in record.get("tests") or []:
        _add_test(summary, entry if isinstance(entry, dict) else {})
    for entry in record.get("collection") or []:
        item = entry if isinstance(entry, dict) else {}
        nodeid, reason = str(item.get("nodeid") or "<collection>"), str(item.get("reason") or "")
        if item.get("outcome") == "skipped":
            summary.add("skipped", nodeid, reason)
        else:
            summary.add("failed", nodeid, "collection error" + (f": {reason}" if reason else ""))
    for entry in record.get("deselected") or []:
        item = entry if isinstance(entry, dict) else {}
        summary.add("deselected", str(item.get("nodeid") or "<deselected>"), str(item.get("by") or "runner selection"))
    for note in record.get("session_notes") or []:
        if not isinstance(note, dict):
            continue
        source, text = str(note.get("source") or ""), str(note.get("text") or "")
        if note.get("recovery"):
            summary.add("recovered", source or "session", text)
        else:
            summary.note(f"session ({source})" if source else "session", text)
    _add_session_status(summary, record.get("exitstatus"))
    return summary


def _add_session_status(summary: Summary, exitstatus: object) -> None:
    # A session that ended without a verdict, or failed with no failed test recorded, is never clean.
    if not isinstance(exitstatus, int) or isinstance(exitstatus, bool):
        summary.add("failed", "pytest session", "no exit status recorded")
    elif exitstatus in _ABORTED_EXITS:
        summary.add("failed", "pytest session", f"exit status {exitstatus} ({_ABORTED_EXITS[exitstatus]})")
    elif exitstatus == _NO_TESTS_COLLECTED:
        summary.add("vacuous", "pytest session: no tests collected")
    elif exitstatus != 0 and not summary.failed:
        summary.add("failed", "pytest session", f"exit status {exitstatus} with no failed test recorded")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-run-record", type=Path, required=True, metavar="PATH", help="a run record written by scripts/_pytest_run_record.py")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--counts-only", action="store_true", help='print "P F S D": passed, failed, skipped, deselected')
    mode.add_argument("--list", choices=(*KINDS, "notes"), metavar="KIND", help=f"print name<TAB>detail per item of KIND ({', '.join(KINDS)}) or per note (notes)")
    args = parser.parse_args(argv)  # a usage error exits 2 (argparse)
    summary = from_run_record(args.from_run_record)
    if args.counts_only:
        counts = summary.counts()
        print(f"{counts.passed} {counts.failed} {counts.skipped} {counts.deselected}")
    else:
        for name, detail in getattr(summary, args.list):
            print(f"{name}\t{detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
