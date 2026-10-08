import sys
import time
modname = sys.argv[1] if len(sys.argv) > 1 else "test_asy_webserver_service"
mod = __import__(modname)
rows = []
t0 = time.ticks_ms()
for name, value in mod.__dict__.items():
    if not name.startswith("test_") or not callable(value):
        continue
    s = time.ticks_ms()
    try:
        value()
        ok = "PASS"
    except Exception as e:
        ok = "FAIL"
    rows.append((time.ticks_diff(time.ticks_ms(), s), name, ok))
total = time.ticks_diff(time.ticks_ms(), t0)
rows.sort(reverse=True)
for r in rows[:12]:
    print(r)
print("order of first 5:", [n for n in mod.__dict__ if n.startswith("test_")][:5])
print("TOTAL", total, len(rows))
