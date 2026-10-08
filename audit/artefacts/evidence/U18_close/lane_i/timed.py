# Runs one test file's test_* functions with per-test wall times (scratch tool, never committed).
import sys, time
import _tmp_scratch
f = sys.argv[1]
ns = {"__name__": "timed", "__file__": f}
exec(compile(open(f).read(), f, "exec"), ns)
fails = 0
for name, fn in list(ns.items()):
    if name.startswith("test_") and callable(fn):
        t0 = time.ticks_ms()
        try:
            fn()
            r = "PASS"
        except Exception as e:
            r = "FAIL"
            fails += 1
            sys.print_exception(e)
        print(r, time.ticks_diff(time.ticks_ms(), t0), "ms", name)
_tmp_scratch.teardown_all()
sys.exit(1 if fails else 0)
