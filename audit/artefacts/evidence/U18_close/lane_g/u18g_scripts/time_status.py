import sys, time
sys.path.insert(0, "tests")
import _sensortask_scenarios as s
from _tmp_scratch import TmpScratch
s._scratch = TmpScratch("u18g_time_status")
for device in ("wozi", "dev"):
    module = s.build(device)
    best = None
    worst = 0
    for _ in range(5):
        t0 = time.ticks_ms()
        res = s._dispatch(module, "GET", "/status")
        s.status_body(res)
        dt = time.ticks_diff(time.ticks_ms(), t0)
        best = dt if best is None else min(best, dt)
        worst = max(worst, dt)
    print(device, "GET /status ms best", best, "worst", worst)
