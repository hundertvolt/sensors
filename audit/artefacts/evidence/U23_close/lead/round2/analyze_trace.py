# analyze_trace.py <trace.jsonl>: the E3 split - where each live put-matrix command's time goes.
import json, sys, collections
ev = [json.loads(l) for l in open(sys.argv[1])]
reqs = {}
for e in ev:
    if e["ev"] == "req": reqs[e["id"]] = {"m": e["m"], "u": e["u"], "t0": e["t"], "t1": None}
    elif e["ev"] in ("fin", "fail") and e.get("id") in reqs: reqs[e["id"]]["t1"] = e["t"]
tot = collections.Counter(); cnt = collections.Counter()
def add(k, v): tot[k] += v; cnt[k] += 1
cmds = []
cur = None
for e in ev:
    if e["ev"] == "cmd0": cur = {"c": e["c"], "t0": e["t"], "marks": []}
    elif e["ev"] == "cmd1" and cur: cur["t1"] = e["t"]; cmds.append(cur); cur = None
    elif cur and e["ev"] not in ("req", "fin", "fail"): cur["marks"].append((e["ev"], e["t"]))
first = ev[0]["t"]; last = ev[-1]["t"]
for c in cmds:
    add(f"cmd {c['c']}", c["t1"] - c["t0"])
    pts = [("start", c["t0"])] + c["marks"] + [("end", c["t1"])]
    for (a, ta), (b, tb) in zip(pts, pts[1:]):
        add(f"  {c['c']}: {a}->{b}", tb - ta)
    # page requests inside the Apply window
    m = dict(c["marks"])
    if "ap_click0" in m and "ap_done" in m:
        inwin = sorted((r for r in reqs.values() if m["ap_click0"] <= r["t0"] <= m["ap_done"] and r["t1"]), key=lambda r: r["t0"])
        put_seen = False
        for r in inwin:
            if r["m"] == "PUT": add("  apply: PUT", r["t1"] - r["t0"]); put_seen = True
            elif not put_seen: add(f"  apply: GET before PUT ({'status' if r['u']=='/status' else 'section'})", r["t1"] - r["t0"])
            else: add(f"  apply: GET after PUT ({'status' if r['u']=='/status' else 'section'})", r["t1"] - r["t0"])
    if "nav_clicked" in m and "card" in m:
        inwin = [r for r in reqs.values() if m["nav_clicked"] - 50 <= r["t0"] <= m["card"] and r["t1"] and r["m"] == "GET"]
        for r in inwin: add(f"  {c['c']}: nav GET {r['u'] if r['u']=='/status' else 'section'}", r["t1"] - r["t0"])
print(f"trace span {(last-first)/1000:.1f} s, commands {len(cmds)}")
for k in sorted(tot, key=lambda k: (k.startswith('  '), k)):
    print(f"{k:70s} n={cnt[k]:4d} total={tot[k]/1000:8.1f} s mean={tot[k]/cnt[k]:7.1f} ms")
