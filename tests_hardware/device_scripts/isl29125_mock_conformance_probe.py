"""Register-level ISL29125 conformance probe, run IDENTICALLY against the real chip and against
digital_twin/_isl29125_chip.py - it talks only raw machine.I2C, the one layer both implement, and
emits KEY=VALUE lines that tests_hardware/isl29125_conformance.py diffs. See that module for which
keys are protocol (must match exactly) and which are illumination-dependent."""
import asyncio
import time

import machine
from machine import I2C, Pin

_WDT = None
try:
    _WDT = machine.WDT(timeout=8000)  # real hardware: mpremote's own arming call already started one
except (AttributeError, ValueError, OSError):
    _WDT = None  # the twin's machine.py has no real watchdog to feed

ADDR = 0x44
INT_PIN = 6

REG_ID, REG_C1, REG_C2, REG_C3, REG_THR, REG_STATUS, REG_DATA = 0x00, 0x01, 0x02, 0x03, 0x04, 0x08, 0x09
MODE_RGB = 0x05
CFG1_RNG, CFG1_BITS = 0x08, 0x10


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


def hx(data: "bytes | bytearray") -> str:
    return "".join(f"{b:02x}" for b in bytes(data))


class Probe:
    def __init__(self, i2c: "I2C") -> None:
        self.i2c = i2c

    def rd(self, reg: int, n: int) -> bytes:
        return bytes(self.i2c.readfrom_mem(ADDR, reg, n))

    def wr(self, reg: int, data: "list[int]") -> None:
        self.i2c.writeto_mem(ADDR, reg, bytes(data))

    def counts(self) -> "tuple[int, int, int]":
        raw = self.rd(REG_DATA, 6)
        g = raw[0] | (raw[1] << 8)
        r = raw[2] | (raw[3] << 8)
        b = raw[4] | (raw[5] << 8)
        return g, r, b

    def reset(self) -> None:
        self.wr(REG_ID, [0x46])


async def settle(ms: int) -> None:
    # Real time on both sides: the twin's Timer is a real asyncio task, so one modelled
    # conversion cycle costs the same wall-clock as a real one. Feeds the watchdog on the way
    # through - every wait in this probe goes through here, so nothing can outrun the 8s ceiling.
    if _WDT is not None:
        _WDT.feed()
    await asyncio.sleep_ms(ms)


async def main() -> None:
    i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000, timeout=200000)
    p = Probe(i2c)
    await _section_a_identity(p)
    await _section_b_status(p)
    await _section_c_reserved(p)
    await _section_d_config(p)
    await _section_e_conversion(p)
    await _section_f_powerdown(p)
    await _section_g_restart(p)
    await _section_h_interrupt(p)
    await _section_i_teardown(p)


async def _section_a_identity(p: "Probe") -> None:

    # --- A. identity and reset -------------------------------------------------
    emit("A01_device_id", hx(p.rd(REG_ID, 1)))
    # Auto-increment is only observable against a neighbour that is NOT zero: p6's own burst-read
    # text says the pointer advances, so 2 bytes from 0x00 must read 7d then CONFIG1's real value.
    p.wr(REG_C1, [0x25])
    emit("A02_id_burst_2_c1_is_25", hx(p.rd(REG_ID, 2)))
    p.wr(REG_C1, [0x00])

    p.wr(REG_C1, [0x3F, 0xBF, 0x1F])  # dirty every writable bit before resetting
    await settle(50)
    emit("A03_config_before_reset", hx(p.rd(REG_C1, 3)))
    p.reset()
    emit("A04_config_after_reset", hx(p.rd(REG_C1, 3)))
    emit("A05_thresholds_after_reset", hx(p.rd(REG_THR, 4)))


async def _section_b_status(p: "Probe") -> None:
    # --- B. status register ----------------------------------------------------
    emit("B01_status_first_read", hx(p.rd(REG_STATUS, 1)))
    emit("B02_status_second_read", hx(p.rd(REG_STATUS, 1)))
    p.wr(REG_STATUS, [0x00])  # p12: BOUTF is cleared by an I2C write, despite Table 15's "RO"
    emit("B03_status_after_write_00", hx(p.rd(REG_STATUS, 1)))
    emit("B04_status_reserved_bits_set", "yes" if p.rd(REG_STATUS, 1)[0] & 0xC8 else "no")
    # Same question at 0x08, where the neighbour is the green data low byte. Needs a conversion
    # actually running, or the neighbour is zero and the probe proves nothing.
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])
    await settle(700)
    green_low = p.rd(REG_DATA, 1)[0]
    emit("B05_green_low_byte_now", f"{green_low:02x}")
    emit("B05_status_burst_2", hx(p.rd(REG_STATUS, 2)))
    emit("B06_status_burst_2_second_byte_is_data", "yes" if p.rd(REG_STATUS, 2)[1] != 0 or green_low == 0 else "no")
    p.reset()


async def _section_c_reserved(p: "Probe") -> None:
    # --- C. reserved / undefined bits and registers ----------------------------
    p.wr(REG_C1, [0xFF])
    emit("C01_config1_ff_readback", hx(p.rd(REG_C1, 1)))
    p.wr(REG_C2, [0xFF])
    emit("C02_config2_ff_readback", hx(p.rd(REG_C2, 1)))
    p.wr(REG_C3, [0xFF])
    emit("C03_config3_ff_readback", hx(p.rd(REG_C3, 1)))
    p.reset()
    emit("C04_config_after_reset_2", hx(p.rd(REG_C1, 3)))
    emit("C05_read_reg_0f", hx(p.rd(0x0F, 1)))
    emit("C06_read_reg_10", hx(p.rd(0x10, 1)))
    try:
        p.wr(0x0F, [0x5A])
        emit("C07_write_reg_0f", "accepted")
    except OSError as exc:
        emit("C07_write_reg_0f", f"OSError:{exc.args[0]}")
    emit("C08_read_reg_0f_after_write", hx(p.rd(0x0F, 1)))
    # p6's burst text: "when the counter reaches the end of the register address list, it rolls
    # over and goes back to the first Register Address" - so a long read from 0x0D should wrap
    # round to the device ID (0x7d) rather than running into zero padding.
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])
    await settle(700)
    emit("C09_read_8_from_0x0d_rollover", hx(p.rd(0x0D, 8)))
    p.reset()


async def _section_d_config(p: "Probe") -> None:
    # --- D. config write/readback and auto-increment ----------------------------
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x09])  # CONFIG1-3 in one auto-incrementing burst
    emit("D01_config_burst_readback", hx(p.rd(REG_C1, 3)))
    p.wr(REG_C2, [0x15])  # single-byte write into the middle register only
    emit("D02_config_after_single_c2_write", hx(p.rd(REG_C1, 3)))
    emit("D03_config_partial_read_from_c2", hx(p.rd(REG_C2, 2)))
    p.wr(REG_THR, [0x34, 0x12, 0xCD, 0xAB])
    emit("D04_threshold_roundtrip", hx(p.rd(REG_THR, 4)))
    p.wr(REG_THR, [0x00, 0x00, 0xFF, 0xFF])


async def _section_e_conversion(p: "Probe") -> None:
    # --- E. conversion, data registers, resolution ------------------------------
    p.wr(REG_C1, [MODE_RGB | CFG1_RNG, 0x28, 0x00])  # RGB, 10000lx, 16 bit, no interrupt
    await settle(1000)
    g16, r16, b16 = p.counts()
    emit("E01_counts_16bit_hi_range", f"{g16},{r16},{b16}")
    emit("E02_data_partial_read_from_0x0b", hx(p.rd(0x0B, 4)))
    emit("E03_data_burst_8_past_end", hx(p.rd(REG_DATA, 8)))

    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])  # 375 lx range, 16 bit
    await settle(1000)
    g_lo, r_lo, b_lo = p.counts()
    emit("E04_counts_16bit_lo_range", f"{g_lo},{r_lo},{b_lo}")

    p.wr(REG_C1, [MODE_RGB | CFG1_BITS, 0x28, 0x00])  # 375 lx range, 12 bit
    await settle(500)
    g12, r12, b12 = p.counts()
    emit("E05_counts_12bit_lo_range", f"{g12},{r12},{b12}")
    emit("E06_12bit_within_4095", "yes" if max(g12, r12, b12) <= 4095 else "no")


async def _section_f_powerdown(p: "Probe") -> None:
    # --- F. power-down and standby hold the data registers -----------------------
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])
    await settle(1000)
    held = p.counts()
    p.wr(REG_C1, [0x00, 0x28, 0x00])  # power-down
    await settle(700)
    after_pd = p.counts()
    emit("F01_powerdown_holds_data", "yes" if after_pd == held else f"no ({held} -> {after_pd})")
    p.wr(REG_C1, [0x04, 0x28, 0x00])  # standby
    await settle(700)
    emit("F02_standby_holds_data", "yes" if p.counts() == after_pd else "no")


async def _section_g_restart(p: "Probe") -> None:
    # --- G. CONFIG1 write restarts the conversion --------------------------------
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])
    await settle(700)
    before = p.counts()
    p.wr(REG_C1, [MODE_RGB | CFG1_RNG, 0x28, 0x00])  # a real CONFIG1 write (range change)
    immediately = p.counts()
    await settle(400)
    after_cycle = p.counts()
    emit("G01_config1_restart_stale_window", "yes" if immediately == before else f"no ({before} -> {immediately})")
    emit("G02_config1_restart_new_after_cycle", "yes" if after_cycle != immediately else "no")


async def _section_h_interrupt(p: "Probe") -> None:
    # --- H. interrupt line ---------------------------------------------------------
    pin = Pin(INT_PIN, mode=Pin.IN, pull=Pin.PULL_UP)
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])
    p.wr(REG_THR, [0x00, 0x00, 0xFF, 0xFF])
    p.rd(REG_STATUS, 1)  # destructive: clear anything standing
    await settle(700)
    emit("H01_int_idle_level", pin.value())
    p.wr(REG_C3, [0x01])  # INTSEL = green, PRST = 1
    p.wr(REG_THR, [0x00, 0x00, 0x01, 0x00])  # high threshold = 1 count: any light trips it
    fired_ms = -1
    start = time.ticks_ms()
    for _ in range(40):
        if pin.value() == 0:
            fired_ms = time.ticks_diff(time.ticks_ms(), start)
            break
        await settle(50)
    emit("H02_int_asserted_low", "yes" if fired_ms >= 0 else "no")
    emit("H03_int_assert_ms_bucket", "n/a" if fired_ms < 0 else ("fast<400" if fired_ms < 400 else "slow>=400"))
    status_at_int = p.rd(REG_STATUS, 1)[0]
    emit("H04_status_rgbthf_set_when_int", "yes" if status_at_int & 0x01 else "no")
    await settle(20)
    emit("H05_int_released_by_status_read", pin.value())
    emit("H06_status_rgbthf_cleared_by_read", "yes" if not (p.rd(REG_STATUS, 1)[0] & 0x01) else "no")

    # PRST unit: 4 cycles at 16 bit is ~1212ms if it counts RGB cycles, ~404ms if channels.
    p.wr(REG_C3, [0x00])
    p.wr(REG_C1, [MODE_RGB, 0x28, 0x00])
    p.rd(REG_STATUS, 1)
    await settle(700)
    p.wr(REG_C3, [0x01 | (2 << 2)])  # INTSEL = green, PRST = 4
    p.wr(REG_THR, [0x00, 0x00, 0x01, 0x00])
    p.rd(REG_STATUS, 1)
    start = time.ticks_ms()
    prst_ms = -1
    for _ in range(60):
        if pin.value() == 0:
            prst_ms = time.ticks_diff(time.ticks_ms(), start)
            break
        await settle(25)
    emit("H07_prst4_ms", prst_ms)
    emit("H08_prst4_unit", "inconclusive" if prst_ms < 0 else ("rgb_cycles" if abs(prst_ms - 1212) < abs(prst_ms - 404) else "channel_integrations"))
    p.rd(REG_STATUS, 1)


async def _section_i_teardown(p: "Probe") -> None:
    # --- I. disarm and leave the part in a sane state -------------------------------
    p.wr(REG_C3, [0x00])
    p.wr(REG_THR, [0x00, 0x00, 0xFF, 0xFF])
    p.rd(REG_STATUS, 1)
    p.reset()
    emit("I01_final_config", hx(p.rd(REG_C1, 3)))
    emit("DONE", "1")


asyncio.run(main())
