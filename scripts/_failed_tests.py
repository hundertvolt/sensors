#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The failed and errored tests of a pytest run record (scripts/_pytest_run_record.py), as the -k expression that
reruns exactly them or as their node ids, so a rerun's selection is never typed by hand. CPython 3.11+, stdlib only."""

# Usage: _failed_tests.py RECORD [--nodeids]; RECORD is a run_record.json (a hardware runner's lands in its
# build/archive/<runner>/<UTC>/). Prints nothing and exits 0 when none failed, 1 when some did, 2 on a bad record.

import json
import sys
from pathlib import Path


def failed(record: dict[str, object]) -> list[str]:
    # Node ids of every test that failed or errored, setup and collection errors included, in record order.
    lists = [record.get(key) for key in ("tests", "collection")]
    entries = [e for found in lists if isinstance(found, list) for e in found]
    ids = [e["nodeid"] for e in entries if isinstance(e, dict) and e.get("outcome") in ("failed", "error") and isinstance(e.get("nodeid"), str)]
    return list(dict.fromkeys(ids))


def keyword(ids: list[str]) -> str:
    # One -k term per test function: the node id's last part, its parameters dropped, since -k cannot spell brackets.
    names = dict.fromkeys(nodeid.rsplit("::", 1)[-1].split("[", 1)[0] for nodeid in ids)
    return " or ".join(names)


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        sys.stdout.write("usage: _failed_tests.py RECORD [--nodeids]\n")
        return 0
    args = [a for a in argv if a != "--nodeids"]
    if len(args) != 1:
        sys.stderr.write("usage: _failed_tests.py RECORD [--nodeids]\n")
        return 2
    try:
        record = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"_failed_tests.py: {exc}\n")
        return 2
    if not isinstance(record, dict):
        sys.stderr.write("_failed_tests.py: the record is not a JSON object\n")
        return 2
    ids = failed(record)
    if ids:
        sys.stdout.write(("\n".join(ids) if "--nodeids" in argv else f"-k '{keyword(ids)}'") + "\n")
    return 1 if ids else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
