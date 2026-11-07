import sys
import time
sys.path.insert(0, "tests")
mod = __import__(sys.argv[1])
for name in sorted(dir(mod)):
    if name.startswith("test_"):
        t0 = time.ticks_ms()
        try:
            getattr(mod, name)()
            ok = "ok"
        except Exception as e:
            ok = "FAIL " + repr(e)
        print(time.ticks_diff(time.ticks_ms(), t0), name, ok)
