"""Dump the untraced (action, file) pairs of ac3_site_trace.json with the action's Site and its carriers' Sites, for reading by hand."""
import json, sys
from collections import defaultdict
sys.path.insert(0, "audit/sweeps")
import ac3_site_trace as t

states = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else {"merged-elsewhere"}
d = json.load(open("audit/sweeps/ac3_site_trace.json"))
acts = {a["id"]: a for a in t.parse_actions()}
changes, _ = t.parse_m()
ch = {c["id"]: c for c in changes}
by = defaultdict(list)
for r in d["rows"]:
    if r["state"] in states:
        by[r["action"]].append(r)
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
for aid, rs in sorted(by.items()):
    if only and aid not in only:
        continue
    print(f"##### {aid} ({acts[aid]['file']})  files: " + ", ".join(f"{r['file']}[{r['how']}]" for r in rs)[:1500])
    print("  SITE:", acts[aid]["slots"].get("Site", "")[:900])
    for r in rs:
        base = r["file"].rsplit("/", 1)[-1]
        body = [cid for cid in r["from_changes"] if base and base in " ".join(ch[cid]["slots"].values())]
        print(f"    FILE {r['file']}: named-in-Site-by={r['site_carriers'][:8]} carrier-body-mentions={body[:8]}")
    for cid in rs[0]["from_changes"]:
        c = ch[cid]
        print(f"  {cid} [{c['cluster']}] sec={c['sec_files'][:2]} SITE: {c['slots'].get('Site', '')[:300]}")
    for l in rs[0]["ledger"][:6]:
        print("  LEDGER", l[:250])
    print()
