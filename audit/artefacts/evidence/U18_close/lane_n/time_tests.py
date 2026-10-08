import sys
import time

mod = __import__(sys.argv[1])
rows = []
for name in sorted(k for k in mod.__dict__ if k.startswith("test_")):
    t0 = time.ticks_ms()
    try:
        mod.__dict__[name]()
        ok = "ok"
    except Exception as e:  # scratch timing only
        ok = "FAIL " + repr(e)
    rows.append((time.ticks_diff(time.ticks_ms(), t0), name, ok))
rows.sort()
for r in rows[-12:]:
    print(r)
