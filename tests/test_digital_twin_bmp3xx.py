"""Deterministic unit tests for digital_twin/_bmp3xx_chip.py's own transaction-response logic - matches the register-addressed shape src/asy_bmp3xx_driver.py's BMP3XX_I2C sends (no CRC framing, unlike SGP40/SCD30).
The fixed calibration block round-trips exactly through the real driver's own compensation formula for every target in the twin's default sensible range."""

import errno
import struct
import sys
import time

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _bmp3xx_chip import BMP3XXChip
from _twin_common import Walk
from _twin_random import FixedRandom

# @tunable l2.bmp3xx_probe_hang_s = 0.05
_PROBE_HANG_S = 0.05


def _decode_temp_pressure(_chip: "BMP3XXChip | None", cal_raw: bytes) -> "tuple[float, float, float, tuple[float, ...]]":
    coeff = struct.unpack("<HHbhhbbHHbbhbb", cal_raw)
    t1 = coeff[0] / 2**-8.0
    t2 = coeff[1] / 2**30.0
    t3 = coeff[2] / 2**48.0
    p1 = (coeff[3] - 2**14.0) / 2**20.0
    p2 = (coeff[4] - 2**14.0) / 2**29.0
    p3 = coeff[5] / 2**32.0
    p4 = coeff[6] / 2**37.0
    p5 = coeff[7] / 2**-3.0
    p6 = coeff[8] / 2**6.0
    p7 = coeff[9] / 2**8.0
    p8 = coeff[10] / 2**15.0
    p9 = coeff[11] / 2**48.0
    p10 = coeff[12] / 2**48.0
    p11 = coeff[13] / 2**65.0
    return t1, t2, t3, (p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11)


def _forward(cal_raw: bytes, adc_p: int, adc_t: int) -> "tuple[float, float]":
    t1, t2, t3, p = _decode_temp_pressure(None, cal_raw)
    p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 = p
    pd1 = adc_t - t1
    pd2 = pd1 * t2
    temperature = pd2 + pd1 * pd1 * t3
    pd1 = p6 * temperature
    pd2 = p7 * temperature**2.0
    pd3 = p8 * temperature**3.0
    po1 = p5 + pd1 + pd2 + pd3
    pd1 = p2 * temperature
    pd2 = p3 * temperature**2.0
    pd3 = p4 * temperature**3.0
    po2 = adc_p * (p1 + pd1 + pd2 + pd3)
    pd1 = adc_p**2.0
    pd2 = p9 + p10 * temperature
    pd3 = pd1 * pd2
    pd4 = pd3 + p11 * adc_p**3.0
    pressure = po1 + po2 + pd4
    return pressure / 100, temperature


def _read(chip: BMP3XXChip, reg: int, nbytes: int) -> bytes:
    return chip.handle_readfrom_mem(reg, nbytes)


def _write(chip: BMP3XXChip, reg: int, data: "list[int]") -> None:
    chip.handle_writeto_mem(reg, bytes(data))


def test_chip_id_register_reports_a_recognized_id() -> None:
    chip = BMP3XXChip()
    reply = _read(chip, 0x00, 1)
    assert reply[0] in (0x50, 0x60)  # BMP384/BMP388 vs BMP390 (asy_bmp3xx_driver.py's own check)


def test_status_starts_command_ready() -> None:
    chip = BMP3XXChip()
    reply = _read(chip, 0x03, 1)
    assert reply[0] & 0x10  # STATUS_CMD_RDY


def test_calibration_block_is_not_degenerate() -> None:
    chip = BMP3XXChip()
    raw = _read(chip, 0x31, 21)
    assert len(raw) == 21
    assert not (raw == bytes([raw[0]]) * len(raw) and raw[0] in (0x00, 0xFF))


def test_forced_mode_trigger_sets_data_ready_and_a_readable_burst() -> None:
    # First 2 values: the uniform draw at construction. Last 2: the step delta the forced-mode
    # trigger below draws - zeroed so the final decoded value stays exactly at the constructed one.
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[22.0, 1000.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])  # CONTROL = forced mode, press+temp enabled
    status = _read(chip, 0x03, 1)[0]
    assert status & 0x60 == 0x60  # STATUS_DATA_READY (both drdy_press|drdy_temp)
    burst = _read(chip, 0x04, 6)
    assert len(burst) == 6


def test_forced_mode_reading_decodes_to_the_requested_target_via_the_real_formula() -> None:
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[21.0, 987.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])
    burst = _read(chip, 0x04, 6)
    cal_raw = _read(chip, 0x31, 21)
    adc_p = burst[2] << 16 | burst[1] << 8 | burst[0]
    adc_t = burst[5] << 16 | burst[4] << 8 | burst[3]
    pressure_hpa, temperature = _forward(cal_raw, adc_p, adc_t)
    # Tolerance accounts for rounding the Newton-solved raw ADC value to the nearest integer count
    # (real hardware only ever reports integer ADC counts) - well above the ~1e-4 worst-case
    # quantization error this introduces, but still tight enough to prove the inversion is real.
    assert abs(temperature - 21.0) < 1e-3
    assert abs(pressure_hpa - 987.0) < 1e-3


def test_construction_draws_an_initial_value_within_range_without_a_forced_mode_trigger() -> None:
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[23.5, 1013.25]))
    assert chip._temp_c == 23.5
    assert chip._pressure_hpa == 1013.25


def test_forced_mode_trigger_steps_from_the_previous_value_rather_than_a_fresh_draw() -> None:
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[20.0, 1000.0, 0.5, -2.0]))
    assert chip._temp_c == 20.0 and chip._pressure_hpa == 1000.0  # construction draw
    _write(chip, 0x1B, [0x13])
    assert chip._temp_c == 20.5  # 20.0 + 0.5
    assert chip._pressure_hpa == 998.0  # 1000.0 + -2.0


def test_forced_mode_trigger_step_is_clamped_to_the_configured_max() -> None:
    chip = BMP3XXChip(
        pressure=Walk(950.0, 1050.0, 5.0),
        random_source=FixedRandom(uniform_values=[20.0, 1048.0, 0.0, 5.0]),
    )
    _write(chip, 0x1B, [0x13])
    assert chip._pressure_hpa == 1050.0  # 1048.0 + 5.0 would be 1053.0 - clamped to the pressure walk's hi


def test_forced_mode_trigger_step_is_clamped_to_the_configured_min() -> None:
    chip = BMP3XXChip(
        temp=Walk(15.0, 30.0, 1.0),
        random_source=FixedRandom(uniform_values=[15.4, 1000.0, -1.0, 0.0]),
    )
    _write(chip, 0x1B, [0x13])
    assert chip._temp_c == 15.0  # 15.4 + -1.0 would be 14.4 - clamped to the temp walk's lo


def test_step_bounds_are_configurable_via_the_constructor() -> None:
    random = FixedRandom(uniform_values=[20.0, 1000.0, 0.1, 0.5])
    chip = BMP3XXChip(temp=Walk(15.0, 30.0, 0.1), pressure=Walk(950.0, 1050.0, 0.5), random_source=random)
    _write(chip, 0x1B, [0x13])
    assert random.calls[2:] == [(-0.1, 0.1), (-0.5, 0.5)], random.calls  # the step draws take the walks' own steps


def test_default_range_stays_inside_the_drivers_own_operating_range_check() -> None:
    # asy_bmp3xx_driver.py's own _read() rejects anything outside 300-1250 hPa / -40-85 degC
    # (datasheet sec 1, Table 2) - the twin's defaults must be a sensible sub-range of that.
    chip = BMP3XXChip()
    assert chip._min_pressure_hpa >= 300.0 and chip._max_pressure_hpa <= 1250.0
    assert chip._min_temp_c >= -40.0 and chip._max_temp_c <= 85.0


def test_a_fresh_reading_is_drawn_on_every_forced_mode_trigger() -> None:
    # Construction draw: 20.0/1000.0. The first trigger's step delta is zeroed, so it stays there; the
    # second's sits at this chip's default temp/pressure walk step boundary - proving each trigger
    # draws its own fresh step, not the same value twice, while staying within the walk's bound.
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[20.0, 1000.0, 0.0, 0.0, 1.0, 5.0]))
    cal_raw = _read(chip, 0x31, 21)
    _write(chip, 0x1B, [0x13])
    burst1 = _read(chip, 0x04, 6)
    _write(chip, 0x1B, [0x13])
    burst2 = _read(chip, 0x04, 6)
    assert burst1 != burst2
    adc_p1 = burst1[2] << 16 | burst1[1] << 8 | burst1[0]
    adc_t1 = burst1[5] << 16 | burst1[4] << 8 | burst1[3]
    p1, t1 = _forward(cal_raw, adc_p1, adc_t1)
    assert abs(t1 - 20.0) < 1e-3 and abs(p1 - 1000.0) < 1e-3
    adc_p2 = burst2[2] << 16 | burst2[1] << 8 | burst2[0]
    adc_t2 = burst2[5] << 16 | burst2[4] << 8 | burst2[3]
    p2, t2 = _forward(cal_raw, adc_p2, adc_t2)
    assert abs(t2 - 21.0) < 1e-3 and abs(p2 - 1005.0) < 1e-3  # stepped by the (1.0, 5.0) delta


def test_osr_and_config_registers_store_whatever_byte_they_are_given() -> None:
    # Bit-field read-modify-write logic lives in asy_i2c_driver.py's own get_bits()/set_bits() -
    # already tested there. This twin only needs to persist/return the raw byte faithfully.
    chip = BMP3XXChip()
    assert _read(chip, 0x1C, 1) == b"\x02"  # OSR's default (DS001 register map)
    assert _read(chip, 0x1F, 1) == b"\x00"  # CONFIG's default (DS001 register map)
    _write(chip, 0x1C, [0b00010101])
    assert _read(chip, 0x1C, 1) == b"\x15"
    _write(chip, 0x1F, [0b00000110])
    assert _read(chip, 0x1F, 1) == b"\x06"


def test_soft_reset_command_restores_command_ready_status() -> None:
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[20.0, 1000.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])
    assert _read(chip, 0x03, 1)[0] & 0x60  # data ready, not command-ready-only
    _write(chip, 0x1C, [0x0D])
    _write(chip, 0x1F, [0x06])
    _write(chip, 0x7E, [0xB6])  # CMD register, soft reset opcode
    assert _read(chip, 0x03, 1) == b"\x10"  # back to command-ready only
    assert _read(chip, 0x1C, 1) == b"\x02"  # "overwritten with their default state" (DS001 4.3.22)
    assert _read(chip, 0x1F, 1) == b"\x00"


def test_err_register_reports_no_error() -> None:
    chip = BMP3XXChip()
    assert _read(chip, 0x02, 1) == b"\x00"


def test_event_reports_por_detected_after_power_up_and_a_soft_reset_and_clears_on_read() -> None:
    # DS001 4.3.7: por_detected is 1 after a power-up or a soft reset, cleared by reading EVENT (0x10).
    chip = BMP3XXChip()
    assert _read(chip, 0x10, 1) == b"\x01"  # constructed = just powered up
    assert _read(chip, 0x10, 1) == b"\x00"
    _write(chip, 0x7E, [0xB6])
    assert _read(chip, 0x10, 1) == b"\x01"
    assert _read(chip, 0x10, 1) == b"\x00"


def test_an_8_byte_read_at_err_reg_returns_err_status_and_the_data_bytes() -> None:
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[20.0, 1000.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])
    block = _read(chip, 0x02, 8)
    assert block[0] == 0x00
    assert block[1] == _read(chip, 0x03, 1)[0]
    assert block[2:] == _read(chip, 0x04, 6)  # ERR_REG, STATUS and the data are one contiguous file
    assert _read(chip, 0x03, 7) == block[1:]


def test_the_fatal_err_knob_sets_err_reg_bit_0() -> None:
    chip = BMP3XXChip()
    chip.fatal_err = True
    assert _read(chip, 0x02, 1) == b"\x01"
    assert _read(chip, 0x02, 8)[0] == 0x01
    chip.fatal_err = False
    assert _read(chip, 0x02, 1) == b"\x00"


def test_unknown_register_returns_zero_bytes_without_raising() -> None:
    chip = BMP3XXChip()
    assert _read(chip, 0x50, 2) == bytes(2)  # not a register this chip fake models
    _write(chip, 0x50, [0xFF])  # real hardware would just silently accept/ignore it too


def test_handle_writeto_accepts_the_zero_byte_bus_probe_without_raising() -> None:
    # Regression test from baseline verification: I2CDevice.setup()/_probe_for_device() always does a plain,
    # empty chip.writeto(address, b"") before any register access.
    #
    # This chip fake used to have no handle_writeto() at all, only handle_writeto_mem() matching its real
    # register-addressed protocol, so the twin's I2C.writeto() dispatch raised AttributeError on every real
    # boot, repeatedly failing the BMP3XX reader task.
    chip = BMP3XXChip()
    image = (_read(chip, 0x1C, 1), _read(chip, 0x1F, 1), _read(chip, 0x03, 1))
    chip.handle_writeto(b"")  # must not raise
    assert (_read(chip, 0x1C, 1), _read(chip, 0x1F, 1), _read(chip, 0x03, 1)) == image
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "probe NAK")
    try:
        chip.handle_writeto(b"")
        raise AssertionError("expected the queued probe fault")
    except OSError:
        pass
    assert chip.fault.pending("writeto") == 0


def test_a_queued_writeto_hang_delays_the_probe() -> None:
    chip = BMP3XXChip()
    chip.fault.inject_hang("writeto", _PROBE_HANG_S)
    start = time.ticks_ms()
    chip.handle_writeto(b"")
    assert time.ticks_diff(time.ticks_ms(), start) >= int(_PROBE_HANG_S * 1000)


def test_fault_injection_on_writeto() -> None:
    chip = BMP3XXChip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "no ACK")
    try:
        chip.handle_writeto(b"")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    chip.handle_writeto(b"")  # one-shot fault - back to normal


def test_fault_injection_on_readfrom_mem_and_writeto_mem() -> None:
    chip = BMP3XXChip()
    chip.fault.inject_fault("readfrom_mem", OSError, errno.EIO, "no ACK")
    try:
        _read(chip, 0x00, 1)
        raise AssertionError("expected OSError")
    except OSError:
        pass
    assert _read(chip, 0x00, 1)[0] in (0x50, 0x60)
    chip.fault.inject_fault("writeto_mem", OSError, errno.ETIMEDOUT, "timeout")
    try:
        _write(chip, 0x1B, [0x13])
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_a_read_fault_keyed_to_the_data_register_spares_the_calibration_read() -> None:
    chip = BMP3XXChip()
    chip.fault.inject_fault("readfrom_mem", OSError, errno.EIO, "data read", match=0x04)
    assert len(_read(chip, 0x31, 21)) == 21
    assert chip.fault.pending("readfrom_mem") == 1
    try:
        _read(chip, 0x04, 6)
        raise AssertionError("expected the keyed fault on the data read")
    except OSError as e:
        assert e.errno == errno.EIO
    assert chip.fault.pending("readfrom_mem") == 0


def test_two_raises_of_one_queued_fault_are_distinct_fresh_exceptions() -> None:
    chip = BMP3XXChip()
    chip.fault.inject_fault("readfrom_mem", OSError, errno.EIO, "planted", times=2)
    raised = []
    for _ in range(2):
        try:
            _read(chip, 0x00, 1)
        except OSError as e:
            raised.append(e)
    assert len(raised) == 2
    assert raised[0] is not raised[1]


def test_power_cycle_restores_the_power_up_registers_and_keeps_the_walk() -> None:
    chip = BMP3XXChip(random_source=FixedRandom(uniform_values=[20.0, 1000.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])
    _write(chip, 0x1C, [0x15])
    _write(chip, 0x1F, [0x06])
    assert _read(chip, 0x10, 1) == b"\x01"  # the construction's power-up, now read and cleared
    walked = (chip._temp_c, chip._pressure_hpa)
    chip.power_cycle()
    fresh = BMP3XXChip()
    assert _read(chip, 0x03, 1) == b"\x10"  # command-ready, no data ready
    assert _read(chip, 0x04, 6) == bytes(6)
    assert _read(chip, 0x10, 1) == b"\x01"
    assert _read(chip, 0x1C, 1) == _read(fresh, 0x1C, 1)
    assert _read(chip, 0x1F, 1) == _read(fresh, 0x1F, 1)
    assert (chip._temp_c, chip._pressure_hpa) == walked


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
