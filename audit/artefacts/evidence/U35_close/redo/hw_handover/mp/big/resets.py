# One reset kind per run: markers into both mem_backup regions, then the reset; resets_read.py reads them after.
import machine, time
KIND = "reset"
r0, r1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(len(r0)): r0[i] = 0xA0 + i
for i in range(len(r1)): r1[i] = 0xB0 + i
print("SUM resets armed", KIND); time.sleep_ms(100)
if KIND == "reset": machine.reset()
elif KIND == "soft": machine.soft_reset()
elif KIND == "wdt":
    machine.WDT(timeout=1000)
    while True: pass
