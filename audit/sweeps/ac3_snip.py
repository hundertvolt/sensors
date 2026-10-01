"""A-C3 Part S helper: print an action's text around a file's basename, and its ledger rows."""
import re, sys, json
sys.path.insert(0, "audit/sweeps")
import ac3_site_trace as t

acts = {a["id"]: a for a in t.parse_actions()}
d = json.load(open("audit/sweeps/ac3_site_trace.json"))
rows = {(r["action"], r["file"]): r for r in d["rows"]}
for arg in sys.argv[1:]:
    aid, f = arg.split("=", 1)
    a = acts[aid]
    txt = " ".join(f"[{k}] {v}" for k, v in a["slots"].items())
    base = f.rstrip("/").rsplit("/", 1)[-1].replace("*", "")
    print(f"#### {aid} :: {f}")
    for m in list(re.finditer(re.escape(base), txt))[:3]:
        print("   ..." + txt[max(0, m.start() - 260): m.end() + 200] + "...")
    r = rows.get((aid, f))
    if r:
        print("   ledger:", " || ".join(x[:160] for x in r["ledger"][:6]))
