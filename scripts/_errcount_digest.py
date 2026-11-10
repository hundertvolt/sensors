#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""GET /status's errcount table in one short line per source that logged anything; given two saved answers, only the
sources that changed between them. Reads files, never the board. CPython 3.11+, stdlib only."""

# Usage: _errcount_digest.py STATUS.json [LATER.json]; each file holds a saved GET /status body or its bare errcount
# table. Exit 0 when the table (or the change) is empty, 1 when something is listed, 2 when a file is unusable.

import json
import sys
from pathlib import Path

# The repo root is appended, so the harness's own reader of the table resolves.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts._twin_process import JSONObject, JSONValue, errcount_table


def _logged(entry: JSONObject) -> tuple[int, str]:
    # The counter and the kept non-"N" history entries, oldest first ("W22,E81"); a repeat is counted, not kept again.
    history = entry.get("history")
    kept = [f"{h.get('type')}{h.get('num')}" for h in (history if isinstance(history, list) else []) if isinstance(h, dict) and h.get("type") != "N"]
    counter = entry.get("counter")
    return (counter if isinstance(counter, int) else -1), ",".join(kept) or "-"


def _table(path: Path) -> dict[str, JSONObject]:
    body: JSONValue = json.loads(path.read_text(encoding="utf-8"))
    return errcount_table(200, body if isinstance(body, dict) and "errcount" in body else {"errcount": body})


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        sys.stdout.write("usage: _errcount_digest.py STATUS.json [LATER.json]\n")
        return 0
    if len(argv) not in (1, 2):
        sys.stderr.write("usage: _errcount_digest.py STATUS.json [LATER.json]\n")
        return 2
    tables: list[dict[str, JSONObject]] = []
    for arg in argv:
        try:
            tables.append(_table(Path(arg)))
        except (OSError, ValueError, RuntimeError) as exc:
            sys.stderr.write(f"_errcount_digest.py: {arg}: {exc}\n")
            return 2
    lines: list[str] = []
    if len(tables) == 1:
        for name, entry in sorted(tables[0].items()):
            counter, kept = _logged(entry)
            if counter or kept != "-":
                lines.append(f"{name} counter={counter} history={kept}")
        sys.stdout.write("\n".join(lines) + "\n" if lines else f"all {len(tables[0])} sources clean\n")
        return 1 if lines else 0
    before, after = tables
    for name in sorted(set(before) | set(after)):
        was, now = _logged(before.get(name, {})), _logged(after.get(name, {}))
        if was != now:
            cleared = " (cleared in between)" if 0 <= now[0] < was[0] else ""
            lines.append(f"{name} counter {was[0]}->{now[0]} history {was[1]} -> {now[1]}{cleared}")
    unchanged = len(set(before) | set(after)) - len(lines)
    sys.stdout.write("\n".join([*lines, f"{unchanged} source(s) unchanged"]) + "\n")
    return 1 if lines else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
