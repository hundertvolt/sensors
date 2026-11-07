# Scratch: which tasks does a scenario leave behind, and what stays allocated? leak.py <device> <name substring>
import gc
import sys
import asyncio
import micropython
from _sensortask_scenarios import register_for_device

args = sys.argv[1:]
device, wanted = args[0], args[1]
made = []
real_create = asyncio.create_task


def create_task(coro):
    t = real_create(coro)
    made.append((t, repr(coro)))
    return t


asyncio.create_task = create_task
import asyncio.core
asyncio.core.create_task = create_task
tests = register_for_device(device)
name = [n for n in tests if wanted in n][0]
gc.collect()
print("before free", gc.mem_free())
micropython.mem_info()
tests[name]()
gc.collect()
print("after free", gc.mem_free())
micropython.mem_info()
alive = [(t, r) for t, r in made if not t.done()]
print("tasks made", len(made), "not done", len(alive))
for t, r in alive:
    print("  ALIVE", r)
import machine
armed = [t for t in machine.Timer.all_timers if t.callback is not None]
print("timers", len(machine.Timer.all_timers), "armed", len(armed))
machine.Timer.all_timers.clear()
gc.collect()
print("after clearing all_timers")
micropython.mem_info()
