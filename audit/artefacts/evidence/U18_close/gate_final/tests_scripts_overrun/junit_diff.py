# junit_diff.py <old.xml> <new.xml>: per-file and per-test time deltas.
import sys, collections, xml.etree.ElementTree as ET
def load(p):
    out = {}
    for tc in ET.parse(p).getroot().iter("testcase"):
        out[tc.get("classname", "") + "::" + tc.get("name", "")] = float(tc.get("time", 0))
    return out
a, b = load(sys.argv[1]), load(sys.argv[2])
fa, fb = collections.Counter(), collections.Counter()
for k, v in a.items(): fa[k.split("::")[0]] += v
for k, v in b.items(): fb[k.split("::")[0]] += v
print("total old %.1f (%d tests) new %.1f (%d tests)" % (sum(a.values()), len(a), sum(b.values()), len(b)))
print("-- files by delta")
for f in sorted(set(fa) | set(fb), key=lambda f: fb[f] - fa[f], reverse=True)[:20]:
    print("%8.1f %8.1f %+8.1f %s" % (fa[f], fb[f], fb[f] - fa[f], f))
print("-- tests by delta")
for k in sorted(set(a) | set(b), key=lambda k: b.get(k, 0) - a.get(k, 0), reverse=True)[:30]:
    print("%8.1f %8.1f %+8.1f %s" % (a.get(k, 0), b.get(k, 0), b.get(k, 0) - a.get(k, 0), k[:160]))
