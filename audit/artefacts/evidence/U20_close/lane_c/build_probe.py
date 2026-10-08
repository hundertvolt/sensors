import sys
sys.path.append("ext")
import asyncio
import gc
from machine import WDT

DEVICE = sys.argv[1] if len(sys.argv) > 1 else "dev"
m = __import__("sensortask_" + DEVICE)


async def run():
    wdt = WDT(timeout=8000)
    await m.build_system(watchdog=wdt, cfg_path="/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u20c/cfg_" + DEVICE + "_")
    assert m.sysfunct._watchdog is wdt
    stores = m._collect_config_stores()
    setups = m._collect_setups()
    print(DEVICE, "built; reset_reason", m.sysfunct.get_reset_reason(), "stores", sorted(s.module_name for s in stores), "setups", len(setups))
    print("cmd unknown ->", await m._system_cmd_callback("nope"))


asyncio.run(run())
