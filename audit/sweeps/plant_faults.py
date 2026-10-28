"""Renders audit/b3/faults.md from plant_set.PLANTS, the run records (JSON lines) and plant_notes.json.

Usage: plant_faults.py OUT.md RESULTS.jsonl [MORE.jsonl ...]; a later record of one id replaces an earlier one.
"""

import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from plant_set import PLANTS  # noqa: E402

NAME_RES = (re.compile(r"^(?:FAIL|ABORT) (test_\w+)"), re.compile(r"FAILED \S+::(\S+)"), re.compile(r"^\s*(?:×|✗|FAIL)\s+(?:\S+ > )*(.+?)(?: \d+ms)?$"))


def _names(rec: dict) -> list[str]:
    out = []
    for run in rec["runs"]:
        if run["rc"] == 0 and not run.get("gate_red"):
            continue
        if run.get("gate_red") and run["rc"] == 0:
            out.append("scripts/test.sh `_flag_memory_errors` (" + Path(run["file"]).name + ")")
            continue
        if run["file"] == "twin gate":
            out.append("`_check_no_memory_error_in_log()` on the twin's log")
            continue
        if run["timed_out"]:
            out.append(f"{Path(run['file']).name}: the {run_stage(run)} file timeout only")
            continue
        found = [m.group(1) for line in run["fails"] for rx in NAME_RES for m in [rx.search(line)] if m]
        out.extend(f"{Path(run['file']).name}::{n}" for n in found[:2]) if found else out.append(f"{Path(run['file']).name} (rc {run['rc']})")
    return sorted(set(out))


def run_stage(run: dict) -> str:
    return {"-1": "-1", "32768": "32768"}.get(run["stage"], run["stage"])


def _stages(rec: dict) -> str:
    red = sorted({run_stage(r) for r in rec["runs"] if r["rc"] != 0 or r.get("gate_red")})
    return "red at " + ", ".join(red) if red else "green"


def _decisions(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(isinstance(n, (ast.If, ast.IfExp, ast.While, ast.ExceptHandler, ast.Await, ast.Compare)) for n in ast.walk(tree))


def main() -> None:
    out, results = Path(sys.argv[1]), sys.argv[2:]
    recs: dict[str, dict] = {}
    for res in results:
        for line in Path(res).read_text().splitlines():
            rec = json.loads(line)
            recs[rec["id"]] = rec
    notes = json.loads((HERE / "plant_notes.json").read_text())
    head, rows, counts = notes["header"], [], {"planted": 0, "biting": 0, "fixed": 0, "equivalent": 0, "open": 0, "not planted": 0}
    for p in PLANTS:
        if p["id"].startswith("base.") or p["id"].endswith("-control"):
            continue
        rec = recs.get(p["id"])
        site = rec["sites"][0] if rec and rec["sites"] else p["edits"][0]["file"]
        note = notes["plants"].get(p["id"], {})
        verdict = note.get("verdict", "biting" if rec and rec["red"] else "open")
        counts["planted"] += 1
        counts[verdict] += 1
        fault = note.get("fault") or f"{p['id']}: {p['edits'][0].get('sub', ['', ''])[1] or 'planted'!s}"
        catching = "; ".join(_names(rec)) if rec else "not run"
        action = note.get("action", "biting") if verdict != "biting" or "action" in note else f"biting ({_stages(rec)})" if rec else "not run"
        why = f" [{p['why']}]" if p.get("why") else ""
        rows.append(f"| {p['row']} | {note.get('fault', fault)}{why} | `{site[:140]}` | {catching} | {action} |")
    for row in notes["rows"]:
        counts["not planted" if row.get("not_planted") else row.get("verdict", "not planted")] += 1
        rows.append(f"| {row['module']} | {row['fault']} | {row['site']} | {row['catching']} | {row['action']} |")
    planted_modules = {e["file"] for p in PLANTS for e in p["edits"]}
    for path in sorted((REPO / "src").glob("*.py")):
        rel = f"src/{path.name}"
        n = _decisions(path)
        k = sum(1 for p in PLANTS if not p["id"].startswith("base.") and any(e["file"] == rel for e in p["edits"]))
        counts["not planted"] += 1
        rows.append(f"| {rel} | its other {n - k if rel in planted_modules else n} decision sites (if, ternary, while, except, await, compare) | `{rel}` | the module's direct tests (`tests/test_{path.stem}.py`) | not planted: straightforward logic (method line) |")
    body = head.replace("{COUNTS}", ", ".join(f"{v} {k}" for k, v in counts.items()))
    out.write_text(body + "\n".join(rows) + "\n", encoding="utf-8")
    print(counts)


if __name__ == "__main__":
    main()
