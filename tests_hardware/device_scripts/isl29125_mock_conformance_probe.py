"""Register-level ISL29125 conformance probe, run identically on the bench chip and on the twin's fake: raw machine.I2C
only, KEY=VALUE lines and DONE=1 for flash/test_chip_conformance.py to diff (conformance.py), light-dependent keys
only in an independent form."""
import asyncio
import time

from machine import I2C, Pin

# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _mpy_shed.time_mp import _TicksMs
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# The register map (datasheet FN8424 p.9 Table 1, bits p.10-12), independent of the driver's own copy.
REG_ID, REG_C1, REG_C2, REG_C3, REG_THR, REG_STATUS, REG_DATA = 0x00, 0x01, 0x02, 0x03, 0x04, 0x08, 0x09
CFG1_RNG, CFG1_BITS = 0x08, 0x10
STATUS_CONVENF = 0x02  # "set to logic high when the conversion have been completed" (p.12)
_RP2_I2C_TIMEOUT_US = 50000  # machine.I2C's own default (ports/rp2/machine_i2c.c:38, v1.29.0)
# Measured delays, not polls: the probe characterises the chip's own write-settle and conversion timing for the twin
# comparison, so a register read inside these windows would become part of what is measured.
# @tunable l3.isl29125_mock_conformance_probe_write_settle_ms = 50
_WRITE_SETTLE_MS = 50
# Two 16-bit RGB cycles (3 x tINT, tINT 101 ms, p.3) with margin.
# @tunable l3.isl29125_mock_conformance_probe_conversion_settle_ms = 700
_CONVERSION_SETTLE_MS = 700
# Three 16-bit RGB cycles: a range or mode change has taken effect with one cycle to spare.
# @tunable l3.isl29125_mock_conformance_probe_reconfigure_settle_ms = 1000
_RECONFIGURE_SETTLE_MS = 1000
# Many 12-bit cycles (tINT / 16 each) after a resolution change.
# @tunable l3.isl29125_mock_conformance_probe_short_settle_ms = 500
_SHORT_SETTLE_MS = 500
# One 16-bit RGB cycle plus margin: the conversion a CONFIG1 write restarted has completed.
# @tunable l3.isl29125_mock_conformance_probe_one_cycle_ms = 400
_ONE_CYCLE_MS = 400
# @tunable l3.isl29125_mock_conformance_probe_int_release_ms = 20
_INT_RELEASE_MS = 20
# @tunable l3.isl29125_mock_conformance_probe_hold_window_ms = 700
_HOLD_WINDOW_MS = 700
# @tunable l3.isl29125_mock_conformance_probe_int_poll_tries = 40
_INT_POLL_TRIES = 40
# @tunable l3.isl29125_mock_conformance_probe_int_poll_ms = 50
_INT_POLL_MS = 50
# @tunable l3.isl29125_mock_conformance_probe_int_fast_ms = 400
_INT_FAST_MS = 400
# @tunable l3.isl29125_mock_conformance_probe_prst_poll_tries = 60
_PRST_POLL_TRIES = 60
# @tunable l3.isl29125_mock_conformance_probe_prst_poll_ms = 25
_PRST_POLL_MS = 25
# The 12-bit conversion cycle: CONVENF rises timed by a status-poll series (each read clears the flag, p.12).
# @tunable l3.isl29125_mock_conformance_probe_cycle_samples = 9
_CYCLE_SAMPLES = 9
# @tunable l3.isl29125_mock_conformance_probe_cycle_window_ms = 1500
_CYCLE_WINDOW_MS = 1500
# @tunable l3.isl29125_mock_conformance_probe_cycle_poll_ms = 1
_CYCLE_POLL_MS = 1


async def _section_a_identity(p: "Probe") -> None:

    # --- A. identity and reset -------------------------------------------------
    emit("A01_device_id", hx(p.rd(REG_ID, 1)))
    # Auto-increment is only observable against a neighbour that is NOT zero: p6's own burst-read
    # text says the pointer advances, so 2 bytes from 0x00 must read 7d then CONFIG1's real value.
    p.wr(REG_C1, [0x25])
    emit("A02_id_burst_2_c1_is_25", hx(p.rd(REG_ID, 2)))
    p.wr(REG_C1, [0x00])

    p.wr(REG_C1, [0x3F, 0xBF, 0x1F])  # dirty every writable bit before resetting
    await p.settle(_WRITE_SETTLE_MS)
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
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])
    await p.settle(_CONVERSION_SETTLE_MS)
    green_low = p.rd(REG_DATA, 1)[0]
    emit("B05_green_low_byte_now", f"{green_low:02x}")
    emit("B05_status_burst_2", hx(p.rd(REG_STATUS, 2)))
    emit("B06_status_burst_2_second_byte_is_data", "yes" if p.rd(REG_STATUS, 2)[1] != 0 or green_low == 0 else "no")
    p.reset()


class Probe:
    def __init__(self, i2c: I2C, address: int, mode_rgb: int, wdt: "machine.WDT") -> None:
        self.i2c, self.address, self.mode_rgb, self.wdt = i2c, address, mode_rgb, wdt

    def counts(self) -> "tuple[int, int, int]":
        raw = self.rd(REG_DATA, 6)
        g = raw[0] | (raw[1] << 8)
        r = raw[2] | (raw[3] << 8)
        b = raw[4] | (raw[5] << 8)
        return g, r, b

    def rd(self, reg: int, n: int) -> bytes:
        return bytes(self.i2c.readfrom_mem(self.address, reg, n))

    def reset(self) -> None:
        self.wr(REG_ID, [0x46])

    async def settle(self, ms: int) -> None:
        # Real time on both sides (the twin's Timer is a real asyncio task); fed, so no wait outruns the watchdog.
        await fed_sleep_ms(self.wdt, ms)

    def wr(self, reg: int, data: "list[int]") -> None:
        self.i2c.writeto_mem(self.address, reg, bytes(data))


async def main() -> None:
    chip = BENCH["instances"]["isl29125"]
    bus = BENCH["bus"][chip["bus"]]
    i2c = I2C(bus["id"], scl=Pin(bus["scl_pin"]), sda=Pin(bus["sda_pin"]), freq=bus["frequency"], timeout=bus.get("timeout", _RP2_I2C_TIMEOUT_US))
    p = Probe(i2c, BENCH["addresses"]["isl29125"], BENCH["isl29125"]["mode_rgb"], arm())
    await _section_a_identity(p)
    await _section_b_status(p)
    await _section_c_reserved(p)
    await _section_d_config(p)
    await _section_e_conversion(p)
    await _section_f_powerdown(p)
    await _section_g_restart(p)
    await _section_h_interrupt(p, chip["irq_pin"])
    await _section_j_conversion_cycle(p)
    await _section_i_teardown(p)


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
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])
    await p.settle(_CONVERSION_SETTLE_MS)
    emit("C09_read_8_from_0x0d_rollover", hx(p.rd(0x0D, 8)))
    p.reset()


async def _section_d_config(p: "Probe") -> None:
    # --- D. config write/readback and auto-increment ----------------------------
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x09])  # CONFIG1-3 in one auto-incrementing burst
    emit("D01_config_burst_readback", hx(p.rd(REG_C1, 3)))
    p.wr(REG_C2, [0x15])  # single-byte write into the middle register only
    emit("D02_config_after_single_c2_write", hx(p.rd(REG_C1, 3)))
    emit("D03_config_partial_read_from_c2", hx(p.rd(REG_C2, 2)))
    p.wr(REG_THR, [0x34, 0x12, 0xCD, 0xAB])
    emit("D04_threshold_roundtrip", hx(p.rd(REG_THR, 4)))
    p.wr(REG_THR, [0x00, 0x00, 0xFF, 0xFF])


async def _section_e_conversion(p: "Probe") -> None:
    # --- E. conversion, data registers, resolution ------------------------------
    p.wr(REG_C1, [p.mode_rgb | CFG1_RNG, 0x28, 0x00])  # RGB, 10000lx, 16 bit, no interrupt
    await p.settle(_RECONFIGURE_SETTLE_MS)
    g16, r16, b16 = p.counts()
    emit("E01_counts_16bit_hi_range", f"{g16},{r16},{b16}")
    emit("E02_data_partial_read_from_0x0b", hx(p.rd(0x0B, 4)))
    emit("E03_data_burst_8_past_end", hx(p.rd(REG_DATA, 8)))

    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])  # 375 lx range, 16 bit
    await p.settle(_RECONFIGURE_SETTLE_MS)
    g_lo, r_lo, b_lo = p.counts()
    emit("E04_counts_16bit_lo_range", f"{g_lo},{r_lo},{b_lo}")

    p.wr(REG_C1, [p.mode_rgb | CFG1_BITS, 0x28, 0x00])  # 375 lx range, 12 bit
    await p.settle(_SHORT_SETTLE_MS)
    g12, r12, b12 = p.counts()
    emit("E05_counts_12bit_lo_range", f"{g12},{r12},{b12}")
    emit("E06_12bit_within_4095", "yes" if max(g12, r12, b12) <= 4095 else "no")


async def _section_f_powerdown(p: "Probe") -> None:
    # --- F. power-down and standby hold the data registers -----------------------
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])
    await p.settle(_RECONFIGURE_SETTLE_MS)
    held = p.counts()
    p.wr(REG_C1, [0x00, 0x28, 0x00])  # power-down
    await p.settle(_HOLD_WINDOW_MS)
    after_pd = p.counts()
    emit("F01_powerdown_holds_data", "yes" if after_pd == held else f"no ({held} -> {after_pd})")
    p.wr(REG_C1, [0x04, 0x28, 0x00])  # standby
    await p.settle(_HOLD_WINDOW_MS)
    emit("F02_standby_holds_data", "yes" if p.counts() == after_pd else "no")


async def _section_g_restart(p: "Probe") -> None:
    # --- G. CONFIG1 write restarts the conversion --------------------------------
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])
    await p.settle(_CONVERSION_SETTLE_MS)
    before = p.counts()
    p.wr(REG_C1, [p.mode_rgb | CFG1_RNG, 0x28, 0x00])  # a real CONFIG1 write (range change)
    immediately = p.counts()
    await p.settle(_ONE_CYCLE_MS)
    after_cycle = p.counts()
    emit("G01_config1_restart_stale_window", "yes" if immediately == before else f"no ({before} -> {immediately})")
    emit("G02_config1_restart_new_after_cycle", "yes" if after_cycle != immediately else "no")


async def _section_h_interrupt(p: "Probe", int_pin: int) -> None:
    # --- H. interrupt line ---------------------------------------------------------
    pin = Pin(int_pin, mode=Pin.IN, pull=Pin.PULL_UP)
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])
    p.wr(REG_THR, [0x00, 0x00, 0xFF, 0xFF])
    p.rd(REG_STATUS, 1)  # destructive: clear anything standing
    await p.settle(_CONVERSION_SETTLE_MS)
    emit("H01_int_idle_level", pin.value())
    p.wr(REG_C3, [0x01])  # INTSEL = green, PRST = 1
    p.wr(REG_THR, [0x00, 0x00, 0x01, 0x00])  # high threshold = 1 count: any light trips it
    fired_ms = -1
    start = time.ticks_ms()
    for _ in range(_INT_POLL_TRIES):
        if pin.value() == 0:
            fired_ms = time.ticks_diff(time.ticks_ms(), start)
            break
        await p.settle(_INT_POLL_MS)
    emit("H02_int_asserted_low", "yes" if fired_ms >= 0 else "no")
    emit("H03_int_assert_ms_bucket", "n/a" if fired_ms < 0 else (f"fast<{_INT_FAST_MS}" if fired_ms < _INT_FAST_MS else f"slow>={_INT_FAST_MS}"))
    status_at_int = p.rd(REG_STATUS, 1)[0]
    emit("H04_status_rgbthf_set_when_int", "yes" if status_at_int & 0x01 else "no")
    await p.settle(_INT_RELEASE_MS)
    emit("H05_int_released_by_status_read", pin.value())
    emit("H06_status_rgbthf_cleared_by_read", "yes" if not (p.rd(REG_STATUS, 1)[0] & 0x01) else "no")

    # PRST unit: 4 cycles at 16 bit is ~1212ms if it counts RGB cycles, ~404ms if channels.
    p.wr(REG_C3, [0x00])
    p.wr(REG_C1, [p.mode_rgb, 0x28, 0x00])
    p.rd(REG_STATUS, 1)
    await p.settle(_CONVERSION_SETTLE_MS)
    p.wr(REG_C3, [0x01 | (2 << 2)])  # INTSEL = green, PRST = 4
    p.wr(REG_THR, [0x00, 0x00, 0x01, 0x00])
    p.rd(REG_STATUS, 1)
    start = time.ticks_ms()
    prst_ms = -1
    for _ in range(_PRST_POLL_TRIES):
        if pin.value() == 0:
            prst_ms = time.ticks_diff(time.ticks_ms(), start)
            break
        await p.settle(_PRST_POLL_MS)
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


async def _section_j_conversion_cycle(p: "Probe") -> None:
    # --- J. the 12-bit conversion cycle: CONVENF rises timed by a status-poll series --------
    p.wr(REG_C1, [p.mode_rgb | CFG1_BITS, 0x28, 0x00])  # RGB, 375 lx, 12 bit
    await p.settle(_SHORT_SETTLE_MS)
    p.rd(REG_STATUS, 1)  # destructive: the series starts from a cleared flag
    stamps: list[_TicksMs] = []
    start = time.ticks_ms()
    while len(stamps) < _CYCLE_SAMPLES and time.ticks_diff(time.ticks_ms(), start) < _CYCLE_WINDOW_MS:
        if p.rd(REG_STATUS, 1)[0] & STATUS_CONVENF:
            stamps.append(time.ticks_ms())
        await asyncio.sleep_ms(_CYCLE_POLL_MS)
    emit("J01_cycle_12bit_ms_series", ",".join(str(time.ticks_diff(stamps[i], stamps[i - 1])) for i in range(1, len(stamps))))
    emit("J02_cycle_12bit_series_complete", "yes" if len(stamps) == _CYCLE_SAMPLES else "no")
    p.reset()


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


def hx(data: "bytes | bytearray") -> str:
    return "".join(f"{b:02x}" for b in bytes(data))


asyncio.run(main())
