"""Bare-image reset probe: MODE "read" prints this boot's reset flags and whether both mem_backup() regions kept the
pattern the last arm wrote; MODE "arm_<kind>" writes the pattern and resets the chip that way. Registers per pico-sdk:
WATCHDOG REASON 0x40058008 (bit 0 timer, bit 1 force), CHIP_RESET 0x40064008 (bit 8 POR, 16 RUN, 20 PSM restart)."""

import time

import machine

MODE = "read"
KINDS = ("none", "machine_reset", "soft_reset", "wdt_1000", "wdt_4000", "wdt_8388", "bootloader", "power", "run_pin")
PAT = 0x5A5A0000
CHECK = PAT | 0xFFFF


def read() -> None:
    r0, r1 = machine.mem_backup(0), machine.mem_backup(1)
    reason = machine.mem32[0x40058008] & 3
    chip = machine.mem32[0x40064008] & 0x110100
    k0 = all(r0[i] == PAT | i for i in range(4))
    k1 = r1[2] == CHECK and (r1[0] >> 16) == 0x5A5A
    idx = r1[0] & 0xFF
    kind = KINDS[idx] if k1 and idx < len(KINDS) else "?"
    elapsed = r1[1] if k1 else -1
    print("SUM reset armed=%s cause=%d reason=0x%x chip=0x%06x r0_kept=%d r1_kept=%d elapsed_ms=%d" % (kind, machine.reset_cause(), reason, chip, k0, k1, elapsed))
    for i in range(4):
        r0[i] = 0
    for i in range(3):
        r1[i] = 0


def arm(kind: str) -> None:
    r0, r1 = machine.mem_backup(0), machine.mem_backup(1)
    for i in range(4):
        r0[i] = PAT | i
    r1[0], r1[1], r1[2] = PAT | KINDS.index(kind), 0, CHECK
    print("ARMED", kind)
    time.sleep_ms(200)
    if kind == "machine_reset":
        machine.reset()
    elif kind == "soft_reset":
        machine.soft_reset()
    elif kind == "bootloader":
        machine.bootloader()
    elif kind.startswith("wdt_"):
        if kind == "wdt_8388":
            try:
                machine.WDT(timeout=8389)
                print("SUM wdt_cap 8389 accepted")
            except ValueError as e:
                print("SUM wdt_cap 8389 refused:", e)
        t0 = time.ticks_ms()
        machine.WDT(timeout=int(kind[4:]))
        while True:  # stamps the elapsed time every ms until the watchdog resets the chip
            r1[1] = time.ticks_diff(time.ticks_ms(), t0)
            time.sleep_ms(1)
    else:  # "power" or "run_pin": the owner cuts the power or pulls RUN low now
        print("SUM waiting for", kind)
        while True:
            time.sleep_ms(100)


if MODE == "read":
    read()
else:
    arm(MODE[4:])
print("DONE=1")
