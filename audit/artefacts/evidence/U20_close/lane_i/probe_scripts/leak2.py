# Scratch: which global holds what a scenario leaves allocated? leak2.py <device> <name substring>
import gc
import sys
import asyncio
import machine
import network
from _sensortask_scenarios import register_for_device

device, wanted = sys.argv[1], sys.argv[2]
tests = register_for_device(device)
name = [n for n in tests if wanted in n][0]
warm = [n for n in tests if "build_system_constructs_every_real_module" in n][0]
tests[warm]()
gc.collect()
base = gc.mem_alloc()
print("base after a warm-up build", base)
tests[name]()
gc.collect()
print("retained", gc.mem_alloc() - base)
module = sys.modules["sensortask_" + device]


def step(label, fn):
    fn()
    gc.collect()
    print("after", label, gc.mem_alloc() - base)


step("loop exception handler", lambda: asyncio.get_event_loop().set_exception_handler(None))
step("DMA channels", lambda: machine._DMA_CHANNELS.clear())
step("UART live", lambda: machine.UART._live.clear())
step("Pin registry", lambda: machine.Pin.reset_registry())
step("I2C registry", lambda: machine.I2C.reset_registry())
step("timers", lambda: machine.Timer.all_timers.clear())
print("network attrs", [a for a in dir(network) if not a.startswith("__")])
for cls_name in ("WLAN",):
    cls = getattr(network, cls_name, None)
    if cls is not None:
        print("WLAN attrs", [a for a in dir(cls) if a.startswith("_") and not a.startswith("__")])
def drop_globals():
    for n in dir(module):
        if not n.startswith("__"):
            try:
                setattr(module, n, None)
            except Exception:
                pass
step("module globals", drop_globals)
