# Probe: runs only the dev i2c1 recovery scenario, timing every SCL wait of the clear and every
# occupant read, without changing the code under test (wrappers call the originals).
import sys
import os
import time
# the runner's own dir (tests/) is sys.path[0], ahead of MICROPYPATH: a shadowing catalog must go first explicitly
_cd = os.getenv("CATALOG_DIR")
if _cd:
    sys.path.insert(0, _cd)
import asyncio
import json
import asy_i2c_driver as drv
import _bus_hazard_catalog as cat
from machine import Pin

ARGS = sys.argv[3:] if len(sys.argv) > 3 else []
REPEATS = int(ARGS[0]) if ARGS else 5
STALL_K = int(ARGS[1]) if len(ARGS) > 1 else -1  # inject: block the interpreter after the k-th poll sleep of the clear
STALL_MS = int(ARGS[2]) if len(ARGS) > 2 else 0
STALL_OFFSET = int(ARGS[3]) if len(ARGS) > 3 else -1

ev = []
T0 = [time.ticks_us()]
def now():
    return time.ticks_diff(time.ticks_us(), T0[0])

cur_offset = [-1]
wait_idx = [0]
orig_released = drv._scl_released
async def timed_released(scl, timeout_us):
    i = wait_idx[0]; wait_idx[0] += 1
    s = now()
    r = await orig_released(scl, timeout_us)
    ev.append(("wait", cur_offset[0], i, r, now() - s))
    return r
drv._scl_released = timed_released

# stall injection: patch the driver's asyncio namespace sleep_ms (only the clear's SCL polls use it)
class _A:
    pass
shim = _A()
for k in dir(asyncio):
    if not k.startswith("__"):
        setattr(shim, k, getattr(asyncio, k))
poll_n = [0]
async def sleep_ms(ms):
    await asyncio.sleep_ms(ms)
    poll_n[0] += 1
    ev.append(("poll", cur_offset[0], poll_n[0], now()))
    if STALL_MS and poll_n[0] == STALL_K and (STALL_OFFSET < 0 or cur_offset[0] == STALL_OFFSET):
        time.sleep_ms(STALL_MS)
        ev.append(("STALL", cur_offset[0], STALL_MS, now()))
shim.sleep_ms = sleep_ms
drv.asyncio = shim

plan = json.load(open("build/generated_src/sensortask_dev_wiring_plan.json"))
att = plan["buses"]["i2c1"]

class LoggingLock(asyncio.Lock):
    # records when each task asks for / gets the bus lock (probe only)
    async def acquire(self):
        t = asyncio.current_task()
        ev.append(("lock_req", cur_offset[0], id(t) % 100000, now()))
        await super().acquire()
        ev.append(("lock_got", cur_offset[0], id(t) % 100000, now()))

def build_fresh():
    i2c = cat.make_i2c(1)
    if "-L" in ARGS:
        i2c.bus_lock = LoggingLock()
    occ = cat.build_bus_occupants(i2c, att)
    for o in occ:
        orig = o.adapter.read_once
        if not getattr(orig, "_wrapped", False):
            pass
    return cat.fake(i2c), occ

# wrap read_once per adapter (once)
for name, ad in cat.I2C_HAZARD_CATALOG.items():
    orig = ad.read_once
    def mk(orig, name):
        async def w(inst):
            s = now()
            ev.append(("rd_start", cur_offset[0], name, s))
            await orig(inst)
            ev.append(("rd_end", cur_offset[0], name, now()))
        return w
    ad.read_once = mk(orig, name)

orig_run = cat._run_recovery_vs_siblings_at_offset
async def run_at(fake_bus, occupants, iterations, offset):
    cur_offset[0] = offset; wait_idx[0] = 0; poll_n[0] = 0
    ev.append(("offset_start", offset, now()))
    await orig_run(fake_bus, occupants, iterations, offset)
cat._run_recovery_vs_siblings_at_offset = run_at

fails = 0
for rep in range(REPEATS):
    ev.clear(); T0[0] = time.ticks_us()
    try:
        asyncio.run(cat.scenario_bus_recovery_does_not_disturb_concurrent_siblings(build_fresh))
        res = "PASS"
    except AssertionError as e:
        res = "FAIL " + str(e); fails += 1
    waits = [e for e in ev if e[0] == "wait"]
    print("rep", rep, res)
    for off in range(6):
        w = [(e[2], e[3], e[4]) for e in waits if e[1] == off]
        lead = [x for x in w if x[0] == 0]
        print("  offset", off, "waits(us):", [x[2] for x in w], "held" if any(not x[1] for x in w) else "")
    if res != "PASS" or "-v" in ARGS:
        for e in ev:
            print("   ", e)
print("catalog", cat.__file__)
print("fails", fails, "/", REPEATS)
