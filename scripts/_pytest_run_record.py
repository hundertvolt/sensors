"""Pytest plugin writing one JSON run record (--run-record=PATH): every test's outcome, skip reason,
markers and user_properties, collection skips/errors, deselections with their cause, the options,
the effective -m and session notes; scripts/_summary_block.py reads it (SPECIFICATION.md E.10)."""

# Load with `PYTHONPATH=scripts pytest -p _pytest_run_record --run-record=PATH`. Record keys: tests,
# collection, deselected, options, markexpr, collect_only, session_notes, exitstatus (pytest's exit).

import json
import os
from pathlib import Path

import pytest

JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]

_NOTES = pytest.StashKey[list[JSONValue]]()


def _json_safe(value: object) -> JSONValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return str(value)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-record", default=None, metavar="PATH", help="write this session's JSON run record to PATH")


def pytest_configure(config: pytest.Config) -> None:
    config.stash.setdefault(_NOTES, [])
    config.pluginmanager.register(_Recorder(config), "_pytest_run_record_recorder")


def add_session_note(config: pytest.Config, text: str, *, recovery: bool = False, source: str = "") -> None:
    """Records a session-level note (a recovery when `recovery`), written under session_notes."""
    note: JSONValue = {"text": text, "recovery": recovery, "source": source}
    config.stash.setdefault(_NOTES, []).append(note)


def _reason(report: pytest.TestReport | pytest.CollectReport) -> str:
    wasxfail = getattr(report, "wasxfail", None)
    if wasxfail is not None:
        return f"xfail: {wasxfail}"
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:  # noqa: PLR2004 - a skip's (path, lineno, message)
        return str(longrepr[2]).removeprefix("Skipped: ")
    crash = getattr(longrepr, "reprcrash", None)
    text = str(getattr(crash, "message", "") or report.longreprtext).strip()
    return text.splitlines()[0] if text else ""


def _markers(item: pytest.Item) -> list[JSONValue]:
    return [str(name) for name in sorted({mark.name for mark in item.iter_markers()})]


class _Recorder:
    """The session's record; an entry whose outcome stays null reads as "no verdict" downstream."""

    def __init__(self, config: pytest.Config) -> None:
        self.config = config
        self.tests: dict[str, dict[str, JSONValue]] = {}
        self.collection: list[JSONValue] = []
        self.deselected: list[JSONValue] = []

    def _entry(self, nodeid: str) -> dict[str, JSONValue]:
        return self.tests.setdefault(nodeid, {"nodeid": nodeid, "outcome": None, "when": None, "reason": "", "markers": [], "user_properties": []})

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            self._entry(item.nodeid)["markers"] = _markers(item)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        entry = self._entry(report.nodeid)
        entry["user_properties"] = [[str(k), _json_safe(v)] for k, v in report.user_properties]
        outcome: str
        if report.when == "call":
            outcome = report.outcome
        elif report.failed:
            # A setup/teardown failure is an error and outranks a call that passed; never a call failure.
            if entry["outcome"] in ("failed", "error"):
                return
            outcome = "error"
        elif report.skipped:
            outcome = "skipped"
        else:
            return
        entry.update(outcome=outcome, when=report.when, reason="" if outcome == "passed" else _reason(report))

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.skipped or report.failed:
            self.collection.append({"nodeid": report.nodeid, "outcome": "skipped" if report.skipped else "error", "reason": _reason(report)})

    def pytest_deselected(self, items: list[pytest.Item]) -> None:
        for item in items:
            by = next((str(value) for key, value in item.user_properties if key == "deselected_by"), "runner selection")
            self.deselected.append({"nodeid": item.nodeid, "by": by, "markers": _markers(item)})

    def _notes(self) -> list[JSONValue]:
        notes: list[JSONValue] = self.config.stash.setdefault(_NOTES, [])
        return notes.copy()

    def pytest_sessionfinish(self, exitstatus: int) -> None:
        target = self.config.getoption("run_record")
        if not target:
            return
        record: dict[str, JSONValue] = {
            "tests": list(self.tests.values()),
            "collection": self.collection,
            "deselected": self.deselected,
            "options": _json_safe(vars(self.config.option)),
            "markexpr": str(self.config.option.markexpr or ""),
            "collect_only": bool(self.config.option.collectonly),
            "session_notes": self._notes(),
            "exitstatus": int(exitstatus),
        }
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(record, indent=1) + "\n")
        os.replace(tmp, path)
