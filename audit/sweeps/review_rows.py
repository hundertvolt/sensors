"""Renders audit/b3/review.md from redflags.py's records and review_verdicts.json: one row per test, its counts on top.
`python3 -I audit/sweeps/review_rows.py [--check]`; --check fails on a stale verdict or a row left without one, writing
nothing (agent, 2026-10-26)."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVIEW = ROOT / "audit/b3/review.md"
VERDICTS = HERE / "review_verdicts.json"
ORDER = ["blank", "weak", "open", "lead", "CRr2", "fixed", "justified", "biting"]
TERMINAL = {"fixed", "justified", "biting"}
SUITE_ROWS = [
    ("scripts/_digital_twin_ci_suite.py:790", "_restore_is_all_or_nothing", "removed", "dead suite code: no run called it (Run 5b asserts Run 5's exact ring; the cut-write case is tests/test_digital_twin_fram_crash_points.py's), its one caller its reader tests_scripts/test_digital_twin_ci_suite_errcount.py; removed with the four tests that exercised only it (git grep, getattr strings and the run table: nothing else reached it). _non_empty_slots and _counter stay: Run 5b, Run 5c's loss sweep and other runs call them"),
]


def load_redflags() -> "object":
    spec = importlib.util.spec_from_file_location("redflags", HERE / "redflags.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row_verdict(record: "dict[str, object]", verdicts: "dict[str, dict[str, list[str]]]") -> "tuple[str, list[tuple[str, str, str]]]":
    if record["level"] == "device script":  # its facts row: CRr2 until a ds_facts verdict names how the host reads them
        given = verdicts.get(str(record["key"]), {}).get("ds_facts")
        return (given[0], [("ds_facts", *given)]) if given else ("CRr2", [])
    per = [(f[0], *verdicts.get(str(record["key"]), {}).get(f[0], ["open", "no verdict yet"])) for f in record["flags"]]  # type: ignore[index]
    per += [(flag, *v) for flag, v in verdicts.get(str(record["key"]), {}).items() if flag.startswith("was:")]  # a fixed row's former flag
    if not per:
        return "biting", []
    return min((v for _f, v, _r in per), key=ORDER.index), per


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render(records: "list[dict[str, object]]", verdicts: "dict[str, dict[str, list[str]]]", flags: "dict[str, str]", cannot_see: "list[str]") -> str:
    header = REVIEW.read_text(encoding="utf-8").split("\n## ", 1)[0].split("\n| file:line |", 1)[0].rstrip()
    rows, by_level, by_verdict, by_flag, flag_verdict = [], Counter(), Counter(), Counter(), Counter()
    flagged_level = Counter()
    for r in records:
        verdict, per = row_verdict(r, verdicts)
        by_level[r["level"]] += 1
        by_verdict[verdict] += 1
        if r["flags"]:
            flagged_level[r["level"]] += 1
        for flag, v, _reason in per:
            by_flag[flag] += 1
            flag_verdict[(flag, v)] += 1
        flag_text = "; ".join(f"{f}" for f, _v, _r in per) or "—"
        fix = "; ".join(f"{f}: {v}: {reason}" for f, v, reason in per) or ("device-script facts (CRr2)" if verdict == "CRr2" else "biting as is")
        rows.append(f"| {r['file']}:{r['line']} | {cell(str(r['test']))} | {r['level']} | {verdict} | {flag_text} | {cell(fix)} |")
    out = [header, "", "## Counts", "", f"Rendered by `audit/sweeps/review_rows.py` from `redflags.py`'s scan and `review_verdicts.json`: {len(records)} rows, {sum(flagged_level.values())} flagged. A flag is a candidate; the verdict is the reviewer's.", ""]
    out += ["| level | rows | flagged |", "|---|---|---|"] + [f"| {lv} | {n} | {flagged_level[lv]} |" for lv, n in sorted(by_level.items())]
    out += ["", "| verdict (per row) | rows |", "|---|---|"] + [f"| {v} | {by_verdict[v]} |" for v in ORDER if by_verdict[v]]
    out += ["", "| red flag | rows | verdicts |", "|---|---|---|"] + [f"| {f} | {by_flag[f]} | {', '.join(f'{v} {flag_verdict[(f, v)]}' for v in ORDER if flag_verdict[(f, v)])} |" for f in flags if by_flag[f]]
    out += ["", "Detectors with no row at this base: " + (", ".join(f for f in flags if not by_flag[f]) or "none") + ".", "", "### Red flags (redflags.py's detectors)", ""]
    out += [f"- `{f}`: {d}" for f, d in flags.items()]
    out += ["", "## Normal-situation scan (A.U35.37)", "", "Every `ns_*` row, and every row whose reason classes it (a) a normal situation tolerating a code, (b) a provoked fault expecting its code, (c) a hardware test tolerating a code. No (a) at this base. The seed texts of the three sites U11 fixed (\"legitimately logs\", \"two benign warnings\", \"may legitimately appear\") occur nowhere in the test tiers or the twin suite (`git grep`); SGP40's first boot logs nothing (`tests/test_asy_sgp40_driver.py` `test_read_sgp_without_compensation_data_yet_logs_nothing`).", ""]
    for r in records:
        _v, per = row_verdict(r, verdicts)
        hits = [(f, v, reason) for f, v, reason in per if f.startswith("ns_") or reason[:4] in ("(a) ", "(b) ", "(c) ")]
        out += [f"- {r['file']}:{r['line']} `{r['test']}`: " + "; ".join(f"{f} → {v}: {reason}" for f, v, reason in hits) for _ in [0] if hits]
    out += ["", "## Suite code rows", "", "| site | name | verdict | reason |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | {cell(d)} |" for a, b, c, d in SUITE_ROWS]
    out += ["", "## What the scan cannot see", ""] + [f"- {c}" for c in cannot_see]
    out += ["", "## Rows", "", "| file:line | test | level | verdict (biting / weak / blank) | red flag | fix, or \"biting as is\" |", "|---|---|---|---|---|---|"] + rows
    return "\n".join(out) + "\n"


def problems(records: "list[dict[str, object]]", verdicts: "dict[str, dict[str, list[str]]]") -> "list[str]":
    have = {str(r["key"]): {f[0] for f in r["flags"]} for r in records}  # type: ignore[index]
    out = [f"stale verdict: {key} {flag}" for key, per in verdicts.items() for flag in per if flag not in have.get(key, set()) and not (flag.startswith("was:") and key in have) and not (flag == "ds_facts" and key.startswith("tests_hardware/device_scripts/"))]
    out += [f"no verdict: {r['key']} {f[0]}" for r in records for f in r["flags"] if f[0] not in verdicts.get(str(r["key"]), {})]  # type: ignore[index]
    return out


def main(argv: "list[str]") -> int:
    rf = load_redflags()
    records = rf.scan()  # type: ignore[attr-defined]
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
    bad = problems(records, verdicts)
    if bad:
        print("\n".join(bad))
        return 1
    if "--check" not in argv:
        REVIEW.write_text(render(records, verdicts, rf.FLAGS, rf.CANNOT_SEE), encoding="utf-8")  # type: ignore[attr-defined]
    counts = Counter(row_verdict(r, verdicts)[0] for r in records)
    print(f"{len(records)} rows: " + ", ".join(f"{v} {counts[v]}" for v in ORDER if counts[v]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
