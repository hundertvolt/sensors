# Scratch: retained growth per repeated scenario run. growth.py <device> <name substring> <runs>
import gc
import sys
import machine
from _sensortask_scenarios import register_for_device
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device, wanted, runs = sys.argv[1], sys.argv[2], int(sys.argv[3])
tests = register_for_device(device)
fn = tests[[n for n in tests if wanted in n][0]]
fn()
gc.collect()
a = gc.mem_alloc()
import asyncio.core
stop = len(sys.argv) > 4 and sys.argv[4] == "stop"
for i in range(runs):
    fn()
    print("queue peek", asyncio.core._task_queue.peek(), "armed", sum(1 for t in machine.Timer.all_timers if t.callback is not None))
    if stop:
        for t in machine.Timer.all_timers:
            t.deinit()
        machine.Timer.all_timers.clear()
    gc.collect()
    print("run", i + 1, "growth", gc.mem_alloc() - a, "timers", len(machine.Timer.all_timers), "pins", len(machine.Pin._value_logs), len(machine.Pin._external))
