import sys
import time

module = __import__(sys.argv[1])
for name in sys.argv[2:]:
    t0 = time.ticks_ms()
    try:
        getattr(module, name)()
        print("PASS", name, time.ticks_diff(time.ticks_ms(), t0) / 1000)
    except BaseException as e:  # noqa: BLE001 - a probe driver reports every outcome
        print("FAIL", name, time.ticks_diff(time.ticks_ms(), t0) / 1000, repr(e))
        sys.print_exception(e)
sys.exit(0)
