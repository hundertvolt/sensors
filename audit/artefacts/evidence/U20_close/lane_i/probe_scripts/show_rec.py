import sys, asyncio
import _sensortask_scenarios as sc
sc.register_for_device("wozi")
from _boot_recorder import BootRecorder
import asy_system_service
m = sc.build("wozi")
r = BootRecorder(m)
asy_system_service.asyncio = sc._AsyncioWaits()
try:
    sc.run(sc._main_until_supervised(m, "wozi", r))
finally:
    asy_system_service.asyncio = asyncio
    r.restore()
print("ENTRIES", r.entries())
print("EXPECT", sc._expected_boot_entries(sc._expected_facts("wozi")["boot_sequence"]))
