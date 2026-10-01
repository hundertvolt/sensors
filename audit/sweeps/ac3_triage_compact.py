"""Compact per-action view of untraced pairs: Site text, carriers, and per file who names it (Site) or mentions it (carrier body)."""
import json, sys
from collections import defaultdict
sys.path.insert(0, "audit/sweeps")
import ac3_site_trace as t

states = set(sys.argv[1].split(","))
d = json.load(open("audit/sweeps/ac3_site_trace.json"))
acts = {a["id"]: a for a in t.parse_actions()}
changes, _ = t.parse_m()
ch = {c["id"]: c for c in changes}
by = defaultdict(list)
for r in d["rows"]:
    if r["state"] in states:
        by[r["action"]].append(r)
for aid, rs in sorted(by.items()):
    print(f"##### {aid} ({acts[aid]['file']}) carriers: " + " ".join(rs[0]["from_changes"]))
    print("  SITE:", acts[aid]["slots"].get("Site", "")[:700])
    for r in rs[:12]:
        base = r["file"].rsplit("/", 1)[-1]
        body = [cid for cid in r["from_changes"] if base and base in " ".join(ch[cid]["slots"].values())]
        print(f"    {r['file']} [{r['how']}{'' if r['exists'] else ',new'}] site-by={r['site_carriers'][:6]} body={body[:6]} SITEBODY={r['site_body']}")
    if len(rs) > 12:
        print(f"    ... {len(rs) - 12} more files")
    for l in rs[0]["ledger"][:8]:
        print("  L:", l[:220])
