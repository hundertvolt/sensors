# Scratch, run under tests/_coverage_runner.py: does every_api_write leave dev unable to build under settrace?
import gc
import sys
import asyncio
import micropython
from _sensortask_scenarios import register_for_device, build
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device = "dev"
import _sensortask_scenarios as _ss
_real_boot = _ss._boot
_n = [0]


_fresh = {}


async def _traced_boot(*a, **k):
    _n[0] += 1
    m = __import__("sensortask_" + a[0])
    if not _fresh:
        _fresh["names"] = set(dir(m))
    if len(sys.argv) > 5 and sys.argv[5] == "release":
        for name in dir(m):
            if name not in _fresh["names"]:
                setattr(m, name, None)
    report("before boot %d" % _n[0])
    return await _real_boot(*a, **k)


_ss._boot = _traced_boot
tests = register_for_device(device)


def first(sub):
    return [n for n in tests if sub in n][0]


def report(label):
    gc.collect()
    print("==", label)
    micropython.mem_info()


tests[first(sys.argv[4] if len(sys.argv) > 4 else "debug_level_survives_a_simulated_reboot")]()
report("after a warm-up build")
tests[first(sys.argv[3] if len(sys.argv) > 3 else "every_api_write")]()
report("after the scenario")
try:
    build(device)
    print("BUILD OK")
except MemoryError as e:
    print("BUILD FAILED", type(e).__name__)
asyncio.get_event_loop().set_exception_handler(None)
report("after dropping the loop handler")
try:
    build(device)
    print("BUILD2 OK")
except MemoryError as e:
    print("BUILD2 FAILED", type(e).__name__)
