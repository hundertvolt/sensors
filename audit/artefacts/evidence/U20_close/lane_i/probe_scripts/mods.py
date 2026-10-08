# Scratch: modules first imported by a scenario after a warm-up build. mods.py <device> <name substring>
import gc
import sys
from _sensortask_scenarios import register_for_device
import asyncio
import asyncio.core
import machine
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device, wanted = sys.argv[1], sys.argv[2]
tests = register_for_device(device)
m = __import__("sensortask_" + device)
fresh = set(dir(m))
tests[[n for n in tests if "debug_level_survives_a_simulated_reboot" in n][0]]()
before = set(sys.modules)
gc.collect()
a = gc.mem_alloc()
if wanted != "none":
    tests[[n for n in tests if wanted in n][0]]()
gc.collect()
print("new modules", sorted(set(sys.modules) - before), "retained", gc.mem_alloc() - a)

q = asyncio.core._io_queue
print("cur_task", asyncio.core.cur_task, "exc_context", {k: type(v).__name__ for k, v in asyncio.core._exc_context.items()})
print("io map", len(q.map), [(k, [type(x).__name__ for x in v]) for k, v in q.map.items()])
print("task queue peek", asyncio.core._task_queue.peek())


def step(label, fn):
    fn()
    gc.collect()
    print("after", label, gc.mem_alloc() - a)


step("io map", lambda: q.map.clear())
step("timers", lambda: machine.Timer.all_timers.clear())
step("pins", lambda: machine.Pin.reset_registry())
step("uart live", lambda: machine.UART._live.clear())


def drop():
    gone = [name for name in dir(m) if name not in fresh]
    print("dropping", len(gone), "fresh had sysfunct:", "sysfunct" in fresh)
    for name in gone:
        delattr(m, name)
    print("left sysfunct:", getattr(m, "sysfunct", "absent"))


step("module graph globals", drop)

step("cur_task", lambda: setattr(asyncio.core, "cur_task", None))
step("exc_context", lambda: asyncio.core._exc_context.update({"future": None, "exception": None, "message": None}))


def junk(n):
    a = b = c = d = e = f = g = h = 0
    if n:
        return junk(n - 1) + a + b + c + d + e + f + g + h
    return 0


step("stack scrub", lambda: junk(60))
