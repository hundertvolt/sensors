"""A-C3 Part R: trace every register requirement to the merged changes (or phase-C steps) that deliver it."""
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
AUD = ROOT / "audit"
REG_FILES = [f"G{n}" for n in range(1, 11)] + ["LEAD", "REF"]
SKIP = {"AC_NOTES.md", "REGISTER_FIXES_wave1.md", "REGISTER_FIXES_wave2.md", "REGISTER_FIXES_wave3.md"}
RID = re.compile(r"\b(G\d+|LEAD|REF)/R(\d+)")
AID = re.compile(r"A\.([A-Za-z0-9]+)\.([A-Za-z]*)(\d+)((?:\s?/\s?\.?\d+)*)(?:\s?[-–]\s?(?:A\.\1\.\2|\.)?(\d+))?")
MID = re.compile(r"M\.([A-Z_]+)\.(\d+)((?:\s?/\s?\.\d+)*)(?:\s?[-–]\s?(?:M\.\1)?\.(\d+))?")
C_RE = re.compile(r"\bin C\b(?!\.\d)|hardware in C\b|\bC —|phase[- ]C\b|\bC \(")
DROP_WORDS = re.compile(r"\b(dropped|withdrawn|obsolete|superseded|not merged|void)\b", re.I)


def norm_rid(g, n):
    return f"{g}/R{int(n):02d}"


def expand_aids(text, known=None):
    out = []
    for m in AID.finditer(text):
        grp, pre, num, more, rng = m.groups()
        w = len(num)
        nums = [int(num)] + [int(x) for x in re.findall(r"(\d+)", more or "")]
        if rng and int(rng) > int(num) and int(rng) - int(num) < 200:
            nums += list(range(int(num) + 1, int(rng) + 1))
        for k in nums:
            aid = f"A.{grp}.{pre}{k:0{w}d}"
            if known is not None and aid not in known:
                alt = [a for a in (f"A.{grp}.{pre}{k:02d}", f"A.{grp}.{pre}{k:03d}", f"A.{grp}.{pre}{k}") if a in known]
                aid = alt[0] if alt else aid
            out.append(aid)
    return out


def expand_mids(text):
    out = []
    for m in MID.finditer(text):
        cl, num, more, rng = m.groups()
        nums = [int(num)] + [int(x) for x in re.findall(r"(\d+)", more or "")]
        if rng and int(rng) > int(num) and int(rng) - int(num) < 100:
            nums += list(range(int(num) + 1, int(rng) + 1))
        out += [f"M.{cl}.{k:03d}" for k in nums]
    return out


def register():
    out = {}
    for name in REG_FILES:
        txt = (AUD / "pass2" / f"{name}.md").read_text()
        for m in re.finditer(r"(?ms)^### ((?:G\d+|LEAD|REF)/R\d+) (.*?)\n(.*?)(?=^### |^## |\Z)", txt):
            f = dict(re.findall(r"(?m)^- \*\*(\w[\w ]*)\*\*: (.*)$", m.group(3)))
            rid = m.group(1)
            out[rid] = {"id": rid, "title": m.group(2).strip(), "file": name, **{k.lower().replace(" ", "_"): v for k, v in f.items()}}
    return out


def state_units(state):
    state = re.sub(r"A\.[A-Za-z0-9]+\.[A-Za-z0-9]+|V\.[A-Za-z0-9]+\.[A-Za-z0-9]+", "", state)
    units = set(re.findall(r"\b(U\d+(?:C2|C|a|b)?|B0)\b", state))
    for a, b in re.findall(r"\bU(\d+) ?[-–] ?U?(\d+)\b", state):
        units |= {f"U{k}" for k in range(int(a), int(b) + 1)}
    units = {u[:-1] if u.endswith(("a", "b")) and u.startswith("U36") else u for u in units}
    if C_RE.search(state):
        units.add("C")
    return units


def parse_actions():
    acts = {}
    HEAD = re.compile(r"^### (A\.[A-Za-z0-9]+\.[A-Za-z0-9]+)\b(.*)$")
    SLOT = re.compile(r"^- \*\*(Why|Site|Change|Blast|Depends|Kind|Unit)\*\*:\s?(.*)$")
    for p in sorted((AUD / "actions").glob("*.md")):
        if p.name in SKIP:
            continue
        cur = slot = None
        for line in p.read_text().splitlines():
            m = HEAD.match(line)
            if m:
                cur = {"id": m.group(1), "title": m.group(2).strip(), "file": p.stem, "slots": collections.defaultdict(str), "body": ""}
                acts[cur["id"]] = cur
                slot = None
                continue
            if cur is None:
                continue
            if line.startswith(("## ", "### ")):
                cur = None
                continue
            cur["body"] += line + "\n"
            s = SLOT.match(line)
            if s:
                slot = s.group(1)
                cur["slots"][slot] += s.group(2)
            elif slot and line.startswith(("  ", "\t")):
                cur["slots"][slot] += " " + line.strip()
    return acts


def parse_ledgers(known):
    rows = []
    for p in sorted((AUD / "actions").glob("*.md")):
        if p.name in SKIP:
            continue
        lines = p.read_text().splitlines()
        in_led = False
        hdr = None
        for i, line in enumerate(lines):
            if line.startswith("## "):
                in_led = line.startswith("## Ledger") or line.startswith("## Hardware-duty")
                hdr = None
                continue
            if not in_led or not line.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if hdr is None:
                hdr = [c.lower() for c in cells]
                continue
            if set(cells[0]) <= set("-: "):
                continue
            if "register block" not in hdr[0]:
                continue
            rids, last = [], None
            for m in re.finditer(r"(?:(G\d+|LEAD|REF)/)?R(\d+)", cells[0]):
                g = m.group(1) or last
                if g:
                    rids.append(norm_rid(g, m.group(2)))
                    last = g
            res = cells[-1]
            unit_cell = cells[1] if "unit" in hdr[1] and len(cells) == 4 else ""
            clause = cells[-2] if len(cells) >= 3 else ""
            rows.append({"file": p.stem, "line": i + 1, "rids": rids, "unit_cell": unit_cell, "clause": clause, "result": res,
                         "aids": expand_aids(res, known)})
    return rows


def parse_m():
    HEAD = re.compile(r"^### (M\.[A-Z_]+\.\d+)\b\s*(.*)$")
    SLOT = re.compile(r"^- \*\*(From|Site|Change|Resolved|Unit|Depends|Blast carried by|Blast|Kind)\*\*:\s?(.*)$")
    ch, ledgers = {}, []
    for f in sorted((AUD / "consolidation").glob("M_*.md")):
        cur = slot = None
        section = ""
        for ln, line in enumerate(f.read_text().splitlines(), 1):
            h = HEAD.match(line)
            if h:
                cur = h.group(1)
                ch[cur] = {"id": cur, "title": h.group(2), "file": f.stem, "line": ln, "section": section, "slots": collections.defaultdict(str)}
                slot = None
                continue
            if line.startswith("## "):
                cur = slot = None
                section = line[3:].strip()
                continue
            if section.startswith("Ledger") and line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and cells[0].startswith(("A.", "`A.")):
                    ledgers.append({"file": f.stem, "line": ln, "cells": cells})
                continue
            if not cur:
                continue
            s = SLOT.match(line)
            if s:
                slot = s.group(1)
                ch[cur]["slots"][slot] += s.group(2)
            elif slot and line.startswith("  "):
                ch[cur]["slots"][slot] += " " + line.strip()
            elif line.strip():
                slot = None
    return ch, ledgers


UNIT_TOK = re.compile(r"\b(U\d+(?:C2|C)?|B0)\b|\b(phase C|C)\b")


def m_units(unit_text):
    us = set()
    for m in UNIT_TOK.finditer(unit_text):
        us.add(m.group(1) or "C")
    return us


def from_carries(from_text, known):
    """A-IDs carried by a From slot, and those it names only to drop."""
    carried, dropped = set(), set()
    for seg in re.split(r";|\. (?=[A-Z])", from_text):
        ids = expand_aids(seg, known)
        if not ids:
            continue
        if DROP_WORDS.search(seg):
            # first ID before the drop word is dropped; IDs after "dropped" in the same segment too
            pos = DROP_WORDS.search(seg).start()
            before = expand_aids(seg[:pos], known)
            if before:
                dropped.add(before[-1])
                carried |= set(ids) - {before[-1]}
            else:
                dropped |= set(ids)
            continue
        carried |= set(ids)
    return carried, dropped


def main():
    reg = register()
    acts = parse_actions()
    known = set(acts)
    rows = parse_ledgers(known)
    ch, mled = parse_m()
    a2m, a2m_drop = collections.defaultdict(set), collections.defaultdict(set)
    for k, c in ch.items():
        car, drp = from_carries(c["slots"]["From"], known)
        for a in car:
            a2m[a].add(k)
        for a in drp:
            a2m_drop[a].add(k)
    led_disp = collections.defaultdict(list)
    for r in mled:
        rest = " | ".join(r["cells"][1:])
        for a in expand_aids(r["cells"][0], known):
            led_disp[a].append(f"{r['file']}: " + rest)
            if not re.match(r"\s*(dropped|withdrawn|no |read|blast-only|holds|not )", rest, re.I) or re.search(r"merged into|^M\.", rest):
                for m in expand_mids(rest):
                    if m in ch:
                        a2m[a].add(m)
    why_cite = collections.defaultdict(set)
    any_cite = collections.defaultdict(set)
    for a in acts.values():
        for m in RID.finditer(a["slots"]["Why"]):
            why_cite[norm_rid(*m.groups())].add(a["id"])
        for m in RID.finditer(a["body"]):
            any_cite[norm_rid(*m.groups())].add(a["id"])
    m_cite = collections.defaultdict(set)
    for k, c in ch.items():
        txt = " ".join(c["slots"].values())
        for m in RID.finditer(txt):
            m_cite[norm_rid(*m.groups())].add(k)
    led_by_rid = collections.defaultdict(list)
    for r in rows:
        for rid in r["rids"]:
            led_by_rid[rid].append(r)
    out = {}
    for rid, r in reg.items():
        state = r.get("state", "")
        su = state_units(state)
        lrows = led_by_rid.get(rid, [])
        aids = set()
        for lr in lrows:
            aids |= set(lr["aids"])
        aids_why = why_cite.get(rid, set())
        allaids = aids | aids_why
        tr = {}
        for a in sorted(allaids):
            tr[a] = {"exists": a in acts, "file": acts[a]["file"] if a in acts else None,
                     "m": sorted(a2m.get(a, ())), "m_drop": sorted(a2m_drop.get(a, ())),
                     "units": sorted({u for m in a2m.get(a, ()) for u in m_units(ch[m]["slots"]["Unit"])}),
                     "ledger": led_disp.get(a, [])[:6]}
        out[rid] = {"title": r["title"], "file": r["file"], "state": state, "home": r.get("home", ""), "lead": r.get("lead", ""),
                    "state_units": sorted(su), "ledger_rows": [{k: v for k, v in lr.items() if k != "rids"} for lr in lrows],
                    "why_aids": sorted(aids_why), "any_aids": sorted(any_cite.get(rid, set()) - allaids), "m_cite": sorted(m_cite.get(rid, ())),
                    "trace": tr}
    dest = pathlib.Path(sys.argv[1])  # an output path outside the repo (e.g. a scratch directory)
    dest.write_text(json.dumps(out, indent=1))
    mdest = dest.with_name("ac3_m_changes.json")
    mdest.write_text(json.dumps({k: {"title": c["title"], "file": c["file"], "line": c["line"], "unit": c["slots"]["Unit"], "site": c["slots"]["Site"][:400],
                                     "from": c["slots"]["From"], "kind": c["slots"]["Kind"]} for k, c in ch.items()}, indent=1))
    print("requirements", len(reg), "actions", len(acts), "ledger rows", len(rows), "M changes", len(ch))


if __name__ == "__main__":
    main()
