# Scratch (not repo): per-test wall time.
import sys
import time
test_file = sys.argv[1]
with open(test_file) as f:
    source = f.read()
ns = {"__name__": "not_main", "__file__": test_file}
exec(compile(source, test_file, "exec"), ns)
rows = []
for name, value in list(ns.items()):
    if name.startswith("test_") and callable(value):
        t = time.ticks_ms()
        try:
            value()
        except Exception as e:
            print("FAIL", name, repr(e))
        rows.append((time.ticks_diff(time.ticks_ms(), t), name))
rows.sort()
for ms, name in rows[-25:]:
    print(ms, name)
print("total", sum(r[0] for r in rows))
