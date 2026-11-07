# Scratch: which global path still reaches the last build's graph? holder.py <device> <name substring>
import gc
import sys
from _sensortask_scenarios import register_for_device
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device, wanted = sys.argv[1], sys.argv[2]
tests = register_for_device(device)
m = __import__("sensortask_" + device)
tests[[n for n in tests if wanted in n][0]]()
targets = {id(getattr(m, n)): n for n in ("sysfunct", "fram", "conn", "webserver") if getattr(m, n, None) is not None}
print("targets", targets)
seen = set()
found = []


def walk(obj, path, depth):
    if len(found) > 12 or depth > 7:
        return
    oid = id(obj)
    if oid in targets:
        found.append(path + " -> " + targets[oid])
        return
    if oid in seen:
        return
    seen.add(oid)
    t = type(obj)
    if t in (int, str, bytes, bool, float, type(None), bytearray):
        return
    if t is dict:
        for k, v in obj.items():
            walk(v, path + "[" + repr(k)[:30] + "]", depth + 1)
        return
    if t in (list, tuple, set):
        for i, v in enumerate(obj):
            walk(v, path + "[" + str(i) + "]", depth + 1)
        return
    d = getattr(obj, "__dict__", None)
    if type(d) is dict:
        for k, v in d.items():
            walk(v, path + "." + str(k), depth + 1)


for name, mod in list(sys.modules.items()):
    if mod is m:
        continue
    walk(mod, name, 0)
for p in found:
    print("HOLDER", p)
print("done", len(seen))
