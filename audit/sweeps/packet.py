"""Auditor packet for one execution unit: plan 4.4's "Auditor context" verbatim, the unit's register blocks,
its files (owner_of.py) and the A-C merged changes landing in it (work order, via step_packet.py).
Usage: packet.py <unit|AREA> [--out FILE] [--claude-md]  (temporary; deleted with the audit)"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import owner_of
import step_packet
from resolve_refs import spec_sections

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit"
PLAN = ROOT / "PROJECT_AUDIT_PLAN.md"
SPEC = ROOT / "SPECIFICATION.md"
AREAS = "XCUT CORE ALGO BUS SENS STOR UART NET REST LED GEN TOOL SCR CI WEB TEST TWIN HW SEC MEM PERF PLAT PAR DOC LIC ENV".split()
ID_RE = re.compile(r"\b(" + "|".join(AREAS) + r")\.([TS]\d\d)\b")
B2_FROM = 15  # plan 4.4: committed artefacts join the packet "from the B2 subsystems group on" (U15-U22)


def unit_areas(plan):
    """Unit -> area codes, parsed from 4.1's unit table (U0 'B0 ENV', U9 'B2 pilot: LED', 'U10-U14 | ...: XCUT, ...')."""
    sec = re.search(r"(?ms)^\*\*Units\*\*.*?\n\n(.*?)\n\n", plan).group(1)
    out = {}
    for cell in re.findall(r"\| (U\d+(?:-U\d+)?) \| ([^|]+)", sec):
        nums = [int(x) for x in re.findall(r"\d+", cell[0])]
        units = [f"U{n}" for n in range(nums[0], nums[-1] + 1)]
        codes = [c for c in re.findall(r"\b[A-Z]{2,4}\b", cell[1]) if c in AREAS]
        if len(codes) == len(units):
            out.update({u: [c] for u, c in zip(units, codes)})
    return out


def plan_slice(plan, start_re, stop_re):
    m = re.search(start_re, plan, re.M)
    if not m:
        return ""
    end = re.compile(stop_re, re.M).search(plan, m.end())
    return plan[m.start():end.start() if end else len(plan)].rstrip()


def area_section(plan, area):
    if area == "ENV":
        return ""  # ENV's section is 4.6, already inside sections 0-4
    return plan_slice(plan, rf"^### 5\.\d+ {area} — ", r"^### |^## ")


def item_text(plan, iid):
    """The defining bullet of a topic/seed ID with its indented continuation lines."""
    lines = plan.split("\n")
    for i, ln in enumerate(lines):
        if re.match(r"^\s*- (?:\[[ x~]\] )?\*\*" + re.escape(iid) + r"\*\*", ln):
            out = [ln]
            for nxt in lines[i + 1:]:
                if not nxt.strip() or not nxt.startswith(" ") or re.match(r"^\s*- ", nxt):
                    break
                out.append(nxt)
            return "\n".join(out)
    return None


def spec_parts(refs_text):
    """SPEC Part IDs named on a References line: 'Parts A.4, C.7-C.9, G', 'I.4(f.1)', 'E (all)'; never 'Appendix B'."""
    t = re.sub(r"`[^`]*`|\"[^\"]*\"", " ", refs_text)
    out = []
    for m in re.finditer(r"(?<![\w.])([A-M])((?:\.\d+)*)(?:\s*-\s*\1((?:\.\d+)+))?(?![\w])", t):
        head, tail, upto = m.group(1), m.group(2), m.group(3)
        before, after = t[:m.start()], t[m.end():]
        if not tail and not (re.search(r"Parts? $", before) or (before.endswith(", ") and re.match(r"\s*(?:[,;.]|\(all\))", after))):
            continue
        if re.search(r"Appendix $", before):
            continue
        if upto:
            lo, hi = tail.split("."), upto.split(".")
            out += [head + ".".join(lo[:-1] + [str(n)]) for n in range(int(lo[-1]), int(hi[-1]) + 1)]
        else:
            out.append(head + tail)
    return list(dict.fromkeys(out))


def register_blocks(unit):
    idx = (AUDIT / "pass2" / "INDEX.md").read_text()
    sec = idx.split("## By execution unit", 1)[1].split("\n## ", 1)[0]
    m = re.search(rf"^- \*\*{re.escape(unit)}\*\* \(\d+\): (.*)$", sec, re.M)
    ids = [x.strip() for x in m.group(1).split(",")] if m else []
    out = []
    for rid in ids:
        src = AUDIT / "pass2" / (rid.split("/")[0] + ".md")
        b = re.search(rf"(?ms)^### {re.escape(rid)} .*?(?=^### |^## |\Z)", src.read_text()) if src.exists() else None
        out.append(b.group(0).rstrip() if b else f"### {rid} (block not found in {src.name})")
    return ids, out


def landing_changes(unit_rec, steps):
    """The unit's merged changes in work-order order, with step_packet.py's site-file reading of each."""
    changes, _actions = step_packet.load()
    out = []
    for n, group in enumerate(unit_rec["order"], 1):
        if len(group) > 1:
            out.append(f"- Step {n}: co-landing group (one commit)")
        for c in group:
            lead = "  - " if len(group) > 1 else f"- Step {n}: "
            out.append(f"{lead}**{c}** — {steps[c]['title']} · sites: {', '.join(step_packet.site_files(changes.get(c, '')))}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("unit", help="execution unit (U0, U0R, U15, C, ...) or an area code (its B2 unit)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--claude-md", action="store_true", help="inline CLAUDE.md instead of relying on auto-load")
    a = ap.parse_args()
    plan = PLAN.read_text()
    wo = json.loads((AUDIT / "order" / "work_order.json").read_text())
    by_unit = unit_areas(plan)
    unit = a.unit
    if unit in AREAS:
        unit = min((u for u, c in by_unit.items() if c == [unit]), key=lambda u: int(u[1:]), default=unit)
    units = {u["unit"]: u for u in wo["units"]}
    if unit not in units:
        raise SystemExit(f"unknown unit {a.unit!r}; units: {' '.join(units)}")
    areas = by_unit.get(unit, [])
    out = [f"# Auditor packet — {unit}" + (f" ({', '.join(areas)})" if areas else " (no owning area: a B0/B1/B3-B5/C/D unit)"), ""]

    out += ["## PACKET 1: CLAUDE.md", ""]
    out += [(ROOT / "CLAUDE.md").read_text().rstrip()] if a.claude_md else ["Auto-loaded in every session at the repo root (plan 4.4); not repeated. `--claude-md` inlines it."]

    out += ["", "## PACKET 2: Plan sections 0-4 and 5.0 (verbatim; 3 is the answered owner record)", ""]
    out.append(plan[:plan.index("\n## 5. ")].rstrip())
    out += ["", plan_slice(plan, r"^### 5\.0 ", r"^### 5\.1 ").rstrip("-\n ")]

    cited, refs = [], ""
    for area in areas:
        sec = area_section(plan, area)
        out += ["", f"## PACKET 3: Area section: {area}", "", sec or "(ENV: section 4.6, above.)"]
        scan = sec or plan_slice(plan, r"^### 4\.6 ", r"^### |^## ")
        cited += [m.group(0) for m in ID_RE.finditer(scan) if m.group(1) != area]
        r = re.search(r"(?ms)^\*\*References\*\*:(.*?)(?=\n\n|\n[A-Z][a-z]+:\n)", sec)
        refs += (r.group(1) + "\n") if r else ""
    cited = list(dict.fromkeys(cited))
    out += ["", "## PACKET 4: Cited topics and seeds of other areas (context only)", ""]
    for iid in cited:
        t = item_text(plan, iid)
        out.append(f"Context only, owned by {iid.split('.')[0]}:\n{t}" if t else f"{iid}: definition not found in the plan")
    out += [] if cited else ["(none)"]

    out += ["", "## PACKET 5: Harvested notes of the area", ""]
    for area in areas:
        hp = AUDIT / "harvest" / f"{area}.md"
        out.append(hp.read_text().rstrip() if hp.exists() else f"({area}: no `audit/harvest/{area}.md`)")
    out += [] if areas else ["(no owning area)"]

    out += ["", "## PACKET 6: Do-not-reopen index", ""]
    dnr = AUDIT / "do_not_reopen.md"
    out.append(dnr.read_text().rstrip() if dnr.exists() else "(`audit/do_not_reopen.md` missing)")

    parts = spec_parts(refs)
    out += ["", f"## PACKET 7: SPECIFICATION Parts on the References line: {', '.join(parts) or 'none'}", ""]
    spec = SPEC.read_text()
    secs = spec_sections(spec)
    spans = sorted(secs[p][1:] for p in parts if p in secs)
    merged = []
    for s, e in spans:  # a Part already inside a wider one is not printed twice
        if merged and s < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    out += [spec[s:e].rstrip() for s, e in merged]
    out += [f"(Part {p}: no such heading in SPECIFICATION.md)" for p in parts if p not in secs]

    out += ["", "## PACKET 8: Committed audit artefacts this unit depends on", ""]
    n = int(unit[1:]) if re.fullmatch(r"U\d+", unit) else None
    if n is not None and n >= B2_FROM:
        earlier = ["ENV"] + [c for u, cs in by_unit.items() if int(u[1:]) < n for c in cs]
        tracked = subprocess.run(["git", "ls-files", "audit/artefacts"], capture_output=True, text=True, check=False, cwd=ROOT).stdout.split()
        deps = [p for p in tracked if p.split("/")[2] in earlier]
        for p in deps:
            body = (ROOT / p).read_text(errors="replace").rstrip() if p.endswith((".md", ".txt", ".json", ".csv")) else "(binary or non-text; read the file)"
            out += [f"### {p}", "", body, ""]
        out += [] if deps else ["(none committed yet)"]
    else:
        out.append("(not part of this unit's context: plan 4.4 adds artefacts from the B2 subsystems group, U15, on)")

    ids, blocks = register_blocks(unit)
    out += ["", f"## PACKET 9: Register blocks (`audit/pass2/INDEX.md` by execution unit): {len(ids)}", ""]
    out += blocks or ["(none listed for this unit)"]

    out += ["", "## PACKET 10: Files", ""]
    if areas:
        tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=False, cwd=ROOT).stdout.split("\n")
        for area in areas:
            own = [p for p in tracked if p and owner_of.classify(p) == [area]]
            out.append(f"Owned by {area} (`owner_of.py`): " + (", ".join(own) or "cross-cutting, no owned files"))
    unit_rec = units[unit]
    out.append(f"Touched by the merged changes landing here (work order): {', '.join(unit_rec.get('files', [])) or 'none'}")

    steps = {s["change"]: s for s in wo["steps"] if s["unit"] == unit}
    out += ["", f"## PACKET 11: A-C merged changes landing in {unit} (work order; full texts: `step_packet.py {unit}`): {len(steps)}", ""]
    out += landing_changes(unit_rec, steps)

    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text)
        print(f"{unit}: {len(text)} chars, {len(cited)} cited items, {len(parts)} SPEC Parts, {len(ids)} register blocks, {len(steps)} merged changes -> {a.out}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
