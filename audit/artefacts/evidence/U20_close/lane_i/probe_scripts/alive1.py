# Scratch: is one named object of the last build alive after the module drops its build? alive1.py <device> <name>
import gc
import sys
from _sensortask_scenarios import register_for_device
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device, target = sys.argv[1], sys.argv[2]
tests = register_for_device(device)
m = __import__("sensortask_" + device)
fresh = set(dir(m))
tests[[n for n in tests if "build_system_constructs_every_real_module" in n][0]]()
getattr(m, target)._probe_blob = bytearray(1000000)
gc.collect()
a = gc.mem_alloc()
for n in dir(m):
    if n not in fresh:
        setattr(m, n, None)
gc.collect()
print(target, "freed by the drop", a - gc.mem_alloc())
import machine
import rp2
print("armed timers", [(t.period, t.mode) for t in machine.Timer.all_timers if t.callback is not None])
machine.Timer.all_timers.clear()
gc.collect()
print(target, "freed after clearing timers", a - gc.mem_alloc())
rp2.DMA.reset_registry()
gc.collect()
print(target, "freed after DMA reset", a - gc.mem_alloc())
machine.UART._live.clear()
gc.collect()
print(target, "freed after UART live", a - gc.mem_alloc())
import asyncio
import asyncio.core as core
core._io_queue = core.IOQueue()
gc.collect()
print(target, "freed after fresh IOQueue", a - gc.mem_alloc())
core._task_queue = core.TaskQueue()
gc.collect()
print(target, "freed after fresh TaskQueue", a - gc.mem_alloc())
core.cur_task = None
core._exc_context["future"] = None
gc.collect()
print(target, "freed after cur_task/context", a - gc.mem_alloc())
