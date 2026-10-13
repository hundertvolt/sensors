import sys
import time

import test_digital_twin_sensortask_integration as t

for name in sys.argv[1:]:
    t0 = time.ticks_ms()
    try:
        getattr(t, name)()
        print("PASS", name, time.ticks_diff(time.ticks_ms(), t0) / 1000)
    except BaseException as e:  # noqa: BLE001 - a probe driver reports every outcome
        print("FAIL", name, time.ticks_diff(time.ticks_ms(), t0) / 1000, repr(e))
        sys.print_exception(e)
sys.exit(0)
