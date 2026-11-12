import machine
r0, r1 = machine.mem_backup(0), machine.mem_backup(1)
print("SUM resets after reset_cause", machine.reset_cause(), "wd_reason", hex(machine.mem32[0x40058008] & 3), "chip_reset", hex(machine.mem32[0x40064008] & 0x110100),
      "region0", [hex(x) for x in r0], "region1", [hex(x) for x in r1])
