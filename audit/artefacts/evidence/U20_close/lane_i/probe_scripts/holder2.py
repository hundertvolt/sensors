# Scratch: after the module drops its build, which global path still reaches any object of it? holder2.py <device>
import gc
import sys
from _sensortask_scenarios import register_for_device
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device = sys.argv[1]
tests = register_for_device(device)
m = __import__("sensortask_" + device)
fresh = set(dir(m))
tests[[n for n in tests if "build_system_constructs_every_real_module" in n][0]]()
targets = {}
for n in dir(m):
    if n in fresh:
        continue
    obj = getattr(m, n)
    targets[id(obj)] = n
    d = getattr(obj, "__dict__", None)
    if type(d) is dict:
        for k, v in d.items():
            if type(v) not in (int, str, bool, float, type(None), bytes, tuple):
                targets.setdefault(id(v), n + "." + k)
for n in dir(m):
    if n not in fresh:
        delattr(m, n)
obj = d = v = None
print("targets", len(targets))
seen = set()
found = []


def walk(o, path, depth):
    if len(found) > 20 or depth > 9:
        return
    oid = id(o)
    if oid in targets:
        found.append(path + " -> " + targets[oid])
        return
    if oid in seen:
        return
    seen.add(oid)
    t = type(o)
    if t in (int, str, bytes, bool, float, type(None), bytearray, memoryview):
        return
    if t is dict:
        for k, val in o.items():
            walk(val, path + "[" + repr(k)[:40] + "]", depth + 1)
        return
    if t in (list, tuple, set):
        for i, val in enumerate(o):
            walk(val, path + "[" + str(i) + "]", depth + 1)
        return
    dd = getattr(o, "__dict__", None)
    if type(dd) is dict:
        for k, val in dd.items():
            walk(val, path + "." + str(k), depth + 1)


walk(sys.modules, "sys.modules", 0)
for p in found:
    print("HOLDER", p)
print("seen", len(seen))
