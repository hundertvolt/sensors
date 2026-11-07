"""A-C3 Part S: repo-wide sweep of every merged change's "Blast carried by" pointers (G1-G4 did it per group)."""
import json, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, "audit/sweeps")
import ac3_site_trace as t

CLUSTERS = {"DOCS", "DOC", "GEN", "HW_BENCH", "HW_DEV", "PROC", "SCR", "SPEC", "SRC_CORE", "SRC_NET", "SRC_SENS",
            "TEST_HELP", "TEST_UNIT", "TOOL", "TSC", "TWIN", "WEB", "TST", "CFG"}
ALIAS = {"DOC": "DOCS", "CFG": "TOOL"}


def split_items(s):
    out, depth, tick, cur = [], 0, False, ""
    for ch in s:
        if ch == "`":
            tick = not tick
        elif not tick and ch in "([":
            depth += 1
        elif not tick and ch in ")]":
            depth = max(0, depth - 1)
        if ch == ";" and depth == 0 and not tick:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def main():
    changes, ledgers = t.parse_m()
    ids = {c["id"] for c in changes}
    from_any = defaultdict(set)      # A-ID -> clusters whose change From names it
    text_by_cluster = {}
    for p in sorted(t.CONS.glob("M_*.md")):
        txt = p.read_text()
        text_by_cluster[p.stem[2:]] = txt.split("\n## Ledger", 1)[0]
    for c in changes:
        for a in t.ids_in(c["slots"].get("From", "")):
            from_any[a].add(c["cluster"])
    led = defaultdict(list)
    for r in ledgers:
        for a in r["ids"]:
            led[a].append(f'{r["cluster"]}: {r["text"]}')
    all_actions = {a["id"] for a in t.parse_actions()}
    rows, stats = [], Counter()
    for c in changes:
        for item in split_items(c["slots"].get("Blast carried by", "")):
            if not item or item in ("—", "-"):
                continue
            mids = set(re.findall(r"\bM\.[A-Z_]+\.\d{3}\b", item))
            aids = set(t.ids_in(item))
            labels = {ALIAS.get(x, x) for x in re.findall(r"\b([A-Z][A-Z_]+)\b", item) if x in CLUSTERS}
            res = []
            for m in sorted(mids):
                res.append((m, "ok" if m in ids else "MISSING-MID"))
            for a in sorted(aids):
                if a not in all_actions:
                    res.append((a, "UNKNOWN-AID")); continue
                if from_any[a]:
                    tgt = {l for l in labels if l not in ("TST",)}
                    if tgt and not (tgt & from_any[a]) and not any(a in text_by_cluster.get(l, "") for l in tgt):
                        res.append((a, "carried-elsewhere:" + ",".join(sorted(from_any[a]))))
                    else:
                        res.append((a, "ok"))
                elif any(a in text_by_cluster[k] for k in text_by_cluster):
                    res.append((a, "body-only"))
                elif led[a]:
                    res.append((a, "ledger-only"))
                else:
                    res.append((a, "UNCARRIED"))
            kind = "mid" if mids else "aid" if aids else "noid"
            stats[kind] += 1
            for _, s in res:
                stats[s.split(":")[0]] += 1
            rows.append({"src": c["id"], "item": item, "kind": kind, "labels": sorted(labels), "res": res})
    json.dump(rows, open("audit/sweeps/ac3_blast_sweep.json", "w"), indent=1)
    print("items", len(rows), dict(stats))


if __name__ == "__main__":
    main()
