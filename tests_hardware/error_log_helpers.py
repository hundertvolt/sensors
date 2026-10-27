"""Shared /status errcount helpers: save the logs, then clear them; confirm a provoked fault left its catalog entry.
Shape: GET /status -> {"errcount": {"<Logger>": {"counter": int, "history": [...]}}} (SPECIFICATION.md A.8, H.6).
Every oracle fails closed: a logger missing from errcount is a renamed or unwired one, never an empty log."""

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import evidence
import http_client

# The one catalog lookup every tier shares, re-exported for the bench modules. The repo root is
# appended, so tests/ resolves as this repository's namespace package and no tests/ fake shadows a host module.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from tests._error_codes import code, name

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from harness import Board
    from http_client import JSONObject

__all__ = [
    "ErrcountEntry",
    "assert_module_error_log_clean",
    "assert_module_error_log_contains",
    "assert_module_error_log_empty",
    "assert_module_logged_one_code",
    "assert_no_module_logged_a_new_error",
    "assert_no_new_task_raised",
    "assert_no_task_ended",
    "assert_no_unprovoked_entry",
    "clears_made",
    "code",
    "errcount_entry",
    "gained_entries",
    "get_errcount",
    "new_logged_entries",
    "new_task_raised",
    "provoked_entries",
    "read_live_system_log",
    "reads_before_clears",
    "reset_all_error_logs",
    "save_errcount",
]


class ErrcountEntry(TypedDict):
    counter: int
    history: "list[JSONObject]"


# Above the server's 15.0 s outer_cap_s, never below: a legitimate concurrent reset stays under the
# cap and WiFi latency is absorbed here. Timings: SPECIFICATION.md C.7.
# @tunable l4.reset_errors_timeout_s = 30.0
_RESET_ERRORS_TIMEOUT_S = 30.0
# @tunable l4.error_log_helpers_errcount_timeout_s = 10.0
_ERRCOUNT_TIMEOUT_S = 10.0
# A task-level raise: a supervised task's, or the supervisor's own, which ends in a watchdog reset.
_RAISED = (code("E", "TASK_RAISED"), code("E", "SUPERVISOR_RAISED"))
# The flash tier has no network client: the live firmware's own SYSTEM logger read through exec_live(), which keeps its
# modules, from its RAM copy only (no FRAM access). The read ends main.py, so a caller reads outside its observed window.
_READ_SYSTEM_LOG = (
    "import asyncio, json, sys\n"
    "m = [v for k, v in sys.modules.items() if k.startswith('sensortask_') and getattr(v, 'sysfunct', None) is not None]\n"
    "print('SYSLOG', json.dumps(asyncio.run(m[0].sysfunct.get_error_counter())['SYSTEM'] if m else None))\n"
)
# The parsed GET /status reset_all_error_logs() takes before each ResetErrors it makes this session, in order: what
# each clear erased, which the bench log check reads as the end of a segment (CLAUDE.md: read before any ResetErrors).
_CLEARS: "list[dict[str, ErrcountEntry]]" = []


def _slots(entry: ErrcountEntry) -> "list[tuple[str, int]]":
    # A history's (type, num) slots, oldest first, "N" for an unused one.
    return [(str(h.get("type")), int(str(h.get("num", 0)))) for h in entry["history"]]


def _status(dut_ip: str) -> "tuple[bytes, JSONObject]":
    # GET /status, strict: a 200 whose body is one JSON object, returned verbatim beside its parse.
    res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_ERRCOUNT_TIMEOUT_S)
    assert res.status_code == 200, f"GET /status failed: {res.status_code} {res.body!r}"
    return res.body, res.json()


def _errcount(status: "JSONObject") -> "dict[str, ErrcountEntry]":
    counts = status.get("errcount")
    assert isinstance(counts, dict), f"GET /status carries no errcount object: {status!r}"
    return {name: errcount_entry(counts, name) for name in counts}


def _saved_status(dut_ip: str, reason: str) -> "tuple[Path, JSONObject]":
    # The verbatim GET /status body - errcount, the reset reason and every other field - in the run's evidence.
    body, status = _status(dut_ip)
    return evidence.save_text(f"errcount-{reason}.json", body.decode("utf-8", "replace")), status


def get_errcount(dut_ip: str) -> "dict[str, ErrcountEntry]":
    _body, status = _status(dut_ip)
    return _errcount(status)


def assert_module_error_log_clean(dut_ip: str, module_name: str, allowed_warnings: "tuple[int, ...]" = (), allowed_errors: "tuple[int, ...]" = ()) -> None:
    # Nothing in the log's history beyond the named entries; for a test whose documented outcome includes those
    # codes (a provoked torn write).
    entry = errcount_entry(get_errcount(dut_ip), module_name)
    unexpected = [h for h in entry["history"] if (h.get("type") == "E" and h.get("num") not in allowed_errors) or (h.get("type") == "W" and h.get("num") not in allowed_warnings)]
    assert not unexpected, f"{module_name!r} logged {unexpected!r} - only warnings {allowed_warnings!r} and errors {allowed_errors!r} are expected here; full entry: {entry!r}"


def assert_module_error_log_contains(dut_ip: str, module_name: str, num: int, kind: str) -> None:
    # Kind is "E" (err_s()) or "W" (wrn_s()).
    history = errcount_entry(get_errcount(dut_ip), module_name)["history"]
    assert any(h.get("num") == num and h.get("type") == kind for h in history), f"{module_name!r} error log does not contain the expected {kind}{num}: history={history!r}"


def assert_module_error_log_empty(dut_ip: str, module_name: str) -> None:
    entry = errcount_entry(get_errcount(dut_ip), module_name)
    assert entry["counter"] == 0, f"{module_name!r} error log was not empty as expected (counter={entry['counter']}): {entry!r}"


def assert_module_logged_one_code(dut_ip: str, module_name: str, kind: str, num: int, events: "int | None") -> None:
    # A provoked fault's exact record: one used slot holding kind+num and nothing else, counted `events` times; None
    # where the count is the attempts a fault window met, a repeat spending no new slot (SPECIFICATION.md C.7.1).
    entry = errcount_entry(get_errcount(dut_ip), module_name)
    used = [(h.get("type"), h.get("num")) for h in entry["history"] if h.get("type") != "N"]
    counted = entry["counter"] == events if events is not None else entry["counter"] >= 1
    assert used == [(kind, num)] and counted, f"{module_name!r} should hold exactly {kind}{num}, counted {events if events is not None else 'at least once'}: {entry!r}"


def assert_no_module_logged_a_new_error(dut_ip: str, before: "dict[str, ErrcountEntry]", context: str) -> None:
    # Every logger's counter, not one named module's: a full-ceiling burst starves the heap for the whole graph, so an
    # allocation failure it provokes can surface anywhere. A logger present on one side only is a /status shape change.
    after = get_errcount(dut_ip)
    appeared, vanished = sorted(set(after) - set(before)), sorted(set(before) - set(after))
    assert not appeared and not vanished, f"{context}: /status errcount changed shape during the burst - appeared {appeared!r}, vanished {vanished!r}; full log: {after!r}"
    grew = {name: (errcount_entry(before, name)["counter"], errcount_entry(after, name)["counter"]) for name in after if errcount_entry(after, name)["counter"] > errcount_entry(before, name)["counter"]}
    assert not grew, f"{context}: these modules logged new errors during the burst (before, after): {grew!r}; full log: {after!r}"


def assert_no_new_task_raised(before: "dict[str, ErrcountEntry]", after: "dict[str, ErrcountEntry]", context: str) -> None:
    # The console gates' second half: at DebugLevel 0 the firmware's unretrieved-exception report prints nothing, so a
    # task (or the supervisor) that died of an exhausted heap shows only here (SPECIFICATION.md Part I.4(e)).
    found = new_task_raised(before, after)
    assert found == 0, f"{context}: SYSTEM logged {found} new TASK_RAISED or SUPERVISOR_RAISED entr(y/ies) - a supervised task or the supervisor ended raising; before {before.get('SYSTEM')!r}, after {after.get('SYSTEM')!r}"


def assert_no_task_ended(dut_ip: str, context: str) -> None:
    # The supervisor's record since the test's opening ResetErrors: a task that ended (TASK_RAISED, TASK_CANCELLED,
    # TASK_RETURNED) or a budget reboot lands in SYSTEM, which FRAM keeps across a hard_reset(); a routine fault is
    # handled in place (SPECIFICATION.md C.7.2).
    entry = errcount_entry(get_errcount(dut_ip), "SYSTEM")
    assert entry["counter"] == 0, f"{context}: a task ended and was restarted (or the budget rebooted the board) - SYSTEM log: {entry!r}"


def assert_no_unprovoked_entry(before: "dict[str, ErrcountEntry]", after: "dict[str, ErrcountEntry]", test: str, *, pre_clear: "Sequence[dict[str, ErrcountEntry]]" = (), expected: "frozenset[tuple[str, str, int]]" = frozenset()) -> None:
    # The bench log check's verdict (C.7: a normal operation logs neither E nor W): over each segment from a test's first
    # read through the reads its own clears took first to its last, no logger gained one beyond its provokes_log set.
    bounds = [before, *pre_clear, after]
    gained = [entry for i in range(len(bounds) - 1) for entry in new_logged_entries(bounds[i], bounds[i + 1], cleared=i > 0)]
    found = [f"{module} {kind}{num} {name(kind, num) or '(no live catalog row)'}" for module, kind, num in dict.fromkeys(gained) if (module, kind, num) not in expected]
    assert not found, f"{test} logged {'; '.join(found)} - a test whose entries are its purpose names each in provokes_log(\"<why>\", (logger, kind, catalog name), ...)"


def clears_made() -> int:
    return len(_CLEARS)


def errcount_entry(counts: "Mapping[str, object]", name: str) -> ErrcountEntry:
    # One logger's entry, never a default: a missing name or a malformed entry fails naming what is there.
    entry: object = counts.get(name)
    if entry is None:
        raise AssertionError(f"{name!r} is not in /status errcount ({sorted(counts)}): a renamed or unwired logger, or a changed /status shape")
    assert isinstance(entry, dict), f"{name!r}'s errcount entry is {entry!r}, not an object"
    counter, history = entry.get("counter"), entry.get("history")
    shape = f"{name!r}'s errcount entry {entry!r} lacks an int counter or a history list - a changed /status shape"
    assert isinstance(counter, int) and not isinstance(counter, bool) and isinstance(history, list) and all(isinstance(h, dict) for h in history), shape
    return ErrcountEntry(counter=counter, history=history)


def gained_entries(before: ErrcountEntry, after: ErrcountEntry) -> "list[tuple[str, int]] | None":
    # The (type, num) slots a fixed-length history gained between two reads: each new code shifts it one slot (a repeat
    # of the newest spends none), so the gain is the smallest shift within the counter's growth that lines the reads
    # up; None where none does, a clear or a reboot in between.
    old, new = _slots(before), _slots(after)
    for shift in range(min(after["counter"] - before["counter"], len(new)) + 1):
        if new[: len(new) - shift] == old[shift:]:
            return new[len(new) - shift :]
    return None


def new_logged_entries(before: "dict[str, ErrcountEntry]", after: "dict[str, ErrcountEntry]", *, cleared: bool) -> "list[tuple[str, str, int]]":
    # (logger, type, num) of each E or W entry every logger gained between two reads. After a clear (`cleared`, or a
    # history the later read does not continue) all of a log is newer; a counter that grew with no slot gained is a
    # repeat of the newest. A logger on one side only is a /status shape change.
    appeared, vanished = sorted(set(after) - set(before)), sorted(set(before) - set(after))
    assert not appeared and not vanished, f"/status errcount changed shape between the reads: appeared {appeared!r}, vanished {vanished!r}"
    found: list[tuple[str, str, int]] = []
    for module in sorted(after):
        old, new = before[module], after[module]
        gained = None if cleared else gained_entries(old, new)
        if gained is None:
            gained = _slots(new)
        elif not gained and new["counter"] > old["counter"]:
            gained = _slots(new)[-1:]
        found += [(module, kind, num) for kind, num in gained if kind in ("E", "W")]
    return found


def new_task_raised(before: "dict[str, ErrcountEntry]", after: "dict[str, ErrcountEntry]") -> int:
    # SYSTEM TASK_RAISED/SUPERVISOR_RAISED entries between two errcount reads, an empty `before` (a log cleared first)
    # counting all as new. Counted over the newest entries the counter grew by, so a repeat into the newest slot still
    # counts; reaching past a collapsed repeat into an older entry can only fail a run.
    old = errcount_entry(before, "SYSTEM") if before else ErrcountEntry(counter=0, history=[])
    new = errcount_entry(after, "SYSTEM")
    used = [h for h in new["history"] if h.get("type") != "N"]
    grew = new["counter"] - old["counter"]
    if grew < 0:  # cleared in between: everything in the log is newer than the first read
        grew = len(used)
    window = used[len(used) - min(grew, len(used)) :]
    return sum(1 for h in window if h.get("type") == "E" and h.get("num") in _RAISED)


def provoked_entries(args: "tuple[object, ...]", kwargs: "Mapping[str, object]") -> "tuple[str, frozenset[tuple[str, str, int]]]":
    # provokes_log("<why>", (logger, kind, catalog name), ...): its reason and the (logger, kind, num) set it admits; a
    # ValueError for a reason alone, a keyword, a malformed entry or a name with no live catalog row of that kind.
    reason = args[0] if args else None
    if kwargs or not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"provokes_log takes its reason first, then each entry as (logger, kind, catalog name): {args!r} {dict(kwargs)!r}")
    if len(args) < 2:
        raise ValueError(f"provokes_log names a reason but no entry ({reason!r}): add each one the test may leave as (logger, kind, catalog name)")
    entries: set[tuple[str, str, int]] = set()
    for entry in args[1:]:
        if not (isinstance(entry, tuple) and len(entry) == 3 and all(isinstance(part, str) and part for part in entry) and entry[1] in ("E", "W")):
            raise ValueError(f'provokes_log entry {entry!r} is not (logger, "E" or "W", catalog name)')
        try:
            entries.add((entry[0], entry[1], code(entry[1], entry[2])))
        except KeyError:
            raise ValueError(f"provokes_log entry {entry!r}: the catalog has no live {entry[1]} row named {entry[2]!r}") from None
    return reason, frozenset(entries)


def read_live_system_log(board: "Board") -> "dict[str, ErrcountEntry]":
    # SYSTEM's log in /status's errcount shape, read off the running firmware over the REPL (see _READ_SYSTEM_LOG).
    output = board.exec_live(_READ_SYSTEM_LOG)
    line = next((ln for ln in output.splitlines() if ln.startswith("SYSLOG ")), None)
    assert line is not None, f"the board printed no SYSLOG line:\n{output}"
    entry = json.loads(line[len("SYSLOG ") :])
    assert isinstance(entry, dict), f"no running sensortask_* module with a SystemService on the board:\n{output}"
    history: list[JSONObject] = [{"num": n, "type": t} for n, t in zip(entry["ErrNum"], entry["ErrType"], strict=True)]
    return {"SYSTEM": ErrcountEntry(counter=entry["ErrCount"], history=history)}


def reads_before_clears(since: int) -> "list[dict[str, ErrcountEntry]]":
    # The reads the clears after the first `since` of this session took before their PUT, oldest first.
    return _CLEARS[since:]


def reset_all_error_logs(dut_ip: str, reason: str) -> None:
    # Save, then clear: ResetErrors wipes every registered logger, FRAM-backed history included, and nothing brings it
    # back - so the verbatim /status goes to the run's evidence first, its parse to the bench log check (CLAUDE.md).
    erased = _errcount(_saved_status(dut_ip, reason)[1])
    res = http_client.fetch(dut_ip, 80, "PUT", "/status", {"ResetErrors": True}, timeout_s=_RESET_ERRORS_TIMEOUT_S)
    answer = res.json() if res.status_code == 200 else {}
    result = answer.get("result")
    # "Failed": a store's cleared state was not written, or a pending reboot refused it - nothing is clear (A.8).
    assert answer.get("res") == "OK" and isinstance(result, dict) and result.get("ResetErrors") == "Valid", f"PUT /status ResetErrors did not clear the logs: {res.status_code} {res.body!r}"
    _CLEARS.append(erased)


def save_errcount(dut_ip: str, reason: str) -> Path:
    return _saved_status(dut_ip, reason)[0]
