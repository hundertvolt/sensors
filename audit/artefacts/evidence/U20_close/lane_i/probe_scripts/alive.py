# Scratch: which objects of the last build stay alive once the module drops them? alive.py <device>
import gc
import sys
from _sensortask_scenarios import register_for_device
sys.path.append("digital_twin")
import unix_port_unretrieved_report
sys.path.pop()
unix_port_unretrieved_report.install()

device = sys.argv[1]
tests = register_for_device(device)
m = __import__("sensortask_" + device)
fresh = set(dir(m))
tests[[n for n in tests if "build_system_constructs_every_real_module" in n][0]]()
names = [n for n in dir(m) if n not in fresh]
sizes = {}
for i, n in enumerate(names):
    obj = getattr(m, n)
    try:
        obj._probe_blob = bytearray(100000 + 1000 * i)
        sizes[n] = 100000 + 1000 * i
    except Exception as e:
        print("cannot tag", n, type(obj).__name__, e)
gc.collect()
print('alloc before drop', gc.mem_alloc())
for n in names:
    delattr(m, n)
del obj
gc.collect()
a = gc.mem_alloc()
print("alloc with tags", a)
import rp2
import machine
rp2.DMA.reset_registry()
gc.collect()
print("after rp2.DMA reset", gc.mem_alloc() - a)
machine._DMA_CHANNELS.clear()
gc.collect()
print("after machine DMA clear", gc.mem_alloc() - a)
machine.UART._live.clear()
gc.collect()
print("after UART live clear", gc.mem_alloc() - a)
