"""Check allover pass 2: every pass-1 candidate, cluster, plan topic/seed, provenance decision and OR row is placed."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT.parent / "PROJECT_AUDIT_PLAN.md"


def ids(pattern, text):
    return set(re.findall(pattern, text))


def expand_ranges(text):
    """Expand 'G3.001-G3.004', 'G3.001-004', 'HR010-HR012' and 'XCUT.T01-T03' ranges into single IDs."""
    out = set()
    for pre, a, b in re.findall(r"\b(G(?:10|[1-9])\.)(\d{3})\s*[-–]\s*(?:G(?:10|[1-9])\.)?(\d{3})\b", text):
        out |= {f"{pre}{n:03d}" for n in range(int(a), int(b) + 1)}
    for a, b in re.findall(r"\bHR(\d{3})\s*[-–]\s*(?:HR)?(\d{3})\b", text):
        out |= {f"HR{n:03d}" for n in range(int(a), int(b) + 1)}
    for area, k, a, b in re.findall(r"\b([A-Z]{2,5})\.([TS])(\d{2})\s*[-–]\s*(?:[A-Z]{2,5}\.)?[TS]?(\d{2})\b", text):
        out |= {f"{area}.{k}{n:02d}" for n in range(int(a), int(b) + 1)}
    return out


def main():
    files = sorted((ROOT / "pass2").glob("G*.md")) + [ROOT / "pass2" / "LEAD.md"] + ([ROOT / "pass2" / "REF.md"] if (ROOT / "pass2" / "REF.md").exists() else [])
    text = "\n".join(p.read_text() for p in files)
    got = ids(r"\b(G(?:10|[1-9])\.\d{3}|HR\d{3}|[A-Z]{2,5}\.[TS]\d{2}|A2-\d{2}|[ABCDEVL]\d{2}|OR\d+)\b", text) | expand_ranges(text)
    hreq = "\n".join(p.read_text() for p in (ROOT / "hreq").glob("G*.md"))
    merge = (ROOT / "hreq" / "MERGE.md").read_text()
    clusters = {m.group(1): re.findall(r"G(?:10|[1-9])\.\d{3}", m.group(2))
                for m in re.finditer(r"^### (HR\d{3}) .+?\n.*?^- \*\*Members\*\*: (.+?)$", merge, re.M | re.S)}
    cand = set(re.findall(r"(?m)^### (G(?:10|[1-9])\.\d{3})\b", hreq))
    covered = {c for c in cand if c in got} | {m for hr, mem in clusters.items() if hr in got for m in mem}
    plan = PLAN.read_text()
    topics = set(re.findall(r"\*\*([A-Z]{2,5}\.[TS]\d{2})\*\*", plan))
    prov = set(re.findall(r"(?m)^\| (A2-\d{2}|[ABCDEVL]\d{2}) \|", (ROOT / "DECISION_PROVENANCE.md").read_text()))
    ors = {f"OR{n}" for n in range(1, 120)}
    rows = [
        ("candidates (direct or via cluster)", cand, covered),
        ("clusters", set(clusters), got),
        ("plan topics and seeds", topics, got),
        ("provenance decisions", prov, got),
        ("OR rows", ors, got),
    ]
    bad = 0
    for name, want, have in rows:
        miss = sorted(want - have)
        bad += bool(miss)
        print(f"{name}: {len(want)} expected, {len(want) - len(miss)} placed, {len(miss)} missing" + (": " + ", ".join(miss[:40]) if miss else ""))
    reqs = re.findall(r"(?m)^### ((?:G(?:10|[1-9])|LEAD|REF)/R\d+)\b", text)
    dup = sorted({r for r in reqs if reqs.count(r) > 1})
    print(f"requirements: {len(reqs)} in {len(files)} files" + (f", duplicate IDs: {dup}" if dup else ""))
    return 1 if bad or dup else 0



def check_refined() -> None:
    """Every refined-harvest finding (audit/refined/FINDINGS.md) has one ledger line in audit/refined/I*.md."""
    import re as _re
    f = ROOT / "refined" / "FINDINGS.md"
    if not f.exists():
        return
    ids = set(_re.findall(r"\*\*(RF\d{3})\*\*", f.read_text()))
    led = "\n".join(p.read_text() for p in sorted((ROOT / "refined").glob("I*.md")))
    got = set(_re.findall(r"(?m)^\|?\s*-?\s*\**(RF\d{3})\b", led))
    print(f"RF ids: {len(ids)} expected, {len(ids & got)} in ledgers, missing {sorted(ids - got)[:20]}")


if __name__ == "__main__":
    check_refined()
    sys.exit(main())

