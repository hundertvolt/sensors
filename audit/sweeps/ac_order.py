"""A-C2: parse every merged change, resolve dependencies to merged changes, check unit order and cycles."""
import glob, json, re, collections, sys

HEAD = re.compile(r"^### (M\.[A-Z_]+\.\d+)\b\s*(.*)$")
SLOT = re.compile(r"^- \*\*(From|Site|Change|Resolved|Unit|Depends|Blast carried by|Blast|Kind)\*\*:\s?(.*)$")
UNIT = re.compile(r"\b(U\d+(?:C2|C)?|B0|C)\b")
MREF = re.compile(r"M\.([A-Z_]+)\.(\d+)((?:/\.\d+)*)")
AREF = re.compile(r"A\.[A-Za-z0-9]+\.[A-Za-z0-9]+")


def unit_key(u):
    if u == "B0":
        return (-1, 0)
    if u == "C":
        return (99, 0)
    m = re.match(r"U(\d+)(C2|C)?$", u)
    return (int(m.group(1)), {"": 0, "C": 1, "C2": 2}[m.group(2) or ""])


def parse():
    ch = {}
    for f in sorted(glob.glob("audit/consolidation/M_*.md")):
        cur = slot = None
        for line in open(f):
            h = HEAD.match(line)
            if h:
                cur = h.group(1)
                ch[cur] = {"title": h.group(2), "file": f, "slots": collections.defaultdict(str)}
                slot = None
                continue
            if line.startswith("## "):
                cur = slot = None
                continue
            if not cur:
                continue
            s = SLOT.match(line)
            if s:
                slot = s.group(1)
                ch[cur]["slots"][slot] += s.group(2)
            elif slot and line.startswith("  "):
                ch[cur]["slots"][slot] += " " + line.strip()
            elif not line.strip():
                pass
            else:
                slot = None
    return ch


def mrefs(text):
    out = set()
    for m in MREF.finditer(text):
        cl, n, more = m.group(1), m.group(2), m.group(3)
        out.add(f"M.{cl}.{int(n):03d}")
        for k in re.findall(r"\.(\d+)", more):
            out.add(f"M.{cl}.{int(k):03d}")
    return out


def main():
    ch = parse()
    a2m = collections.defaultdict(set)
    for k, c in ch.items():
        for a in AREF.findall(c["slots"]["From"]):
            a2m[a].add(k)
    report = {"changes": len(ch), "no_unit": [], "unknown_m": [], "unknown_a": [], "back_edges": [], "cycles": []}
    units, deps = {}, {}
    for k, c in ch.items():
        us = UNIT.findall(c["slots"]["Unit"])
        if not us:
            report["no_unit"].append(k)
            continue
        units[k] = sorted(set(us), key=unit_key)
    for k, c in ch.items():
        d = c["slots"]["Depends"]
        ms = {m for m in mrefs(d) if m != k}
        for m in list(ms):
            if m not in ch:
                report["unknown_m"].append((k, m))
                ms.discard(m)
        for a in AREF.findall(d):
            if a in a2m:
                ms |= a2m[a] - {k}
            else:
                report["unknown_a"].append((k, a))
        deps[k] = ms
    for k, ds in deps.items():
        if k not in units:
            continue
        first = units[k][0]
        for d in ds:
            if d in units and unit_key(units[d][0]) > unit_key(units[k][-1]):
                report["back_edges"].append((k, units[k], d, units[d]))
    # cycle check (Tarjan SCC)
    idx, low, on, st, sccs, i = {}, {}, set(), [], [], [0]
    sys.setrecursionlimit(100000)

    def strong(v):
        idx[v] = low[v] = i[0]; i[0] += 1; st.append(v); on.add(v)
        for w in deps.get(v, ()):
            if w not in idx:
                strong(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop(); on.discard(w); comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(sorted(comp))
    for v in ch:
        if v not in idx:
            strong(v)
    report["cycles"] = sccs
    json.dump({"units": units, "deps": {k: sorted(v) for k, v in deps.items()}}, open("audit/order/graph.json", "w"), indent=0)
    json.dump(report, open("audit/order/check.json", "w"), indent=1)
    print({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()})
    per_unit = collections.Counter(u for us in units.values() for u in us)
    print(sorted(per_unit.items(), key=lambda x: unit_key(x[0])))


if __name__ == "__main__":
    main()
