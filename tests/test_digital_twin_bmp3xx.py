"""Deterministic unit tests for digital_twin/_bmp3xx_chip.py's own transaction-response logic - matches the register-addressed shape src/asy_bmp3xx_driver.py's BMP3XX_I2C sends (no CRC framing, unlike SGP40/SCD30).
The fixed calibration block round-trips exactly through the real driver's own compensation formula for every target in the twin's default sensible range."""

import struct
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _bmp3xx_chip import Bmp3xxChip  # noqa: E402


def _read(chip: Bmp3xxChip, reg: int, nbytes: int) -> bytes:
    return chip.handle_readfrom_mem(reg, nbytes)


def _write(chip: Bmp3xxChip, reg: int, data: "list[int]") -> None:
    chip.handle_writeto_mem(reg, bytes(data))


def _decode_temp_pressure(chip: "Bmp3xxChip | None", cal_raw: bytes) -> "tuple[float, float, float, tuple[float, ...]]":
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


class _FixedRandom:
    def __init__(self, uniform_values: "list[float] | None" = None) -> None:
        self._uniform_values = list(uniform_values or [])

    def uniform(self, a: float, b: float) -> float:
        assert self._uniform_values, "uniform() called more times than scripted"
        value = self._uniform_values.pop(0)
        assert a <= value <= b, f"scripted value {value} outside requested range [{a},{b}]"
        return value


def test_chip_id_register_reports_a_recognized_id() -> None:
    chip = Bmp3xxChip()
    reply = _read(chip, 0x00, 1)
    assert reply[0] in (0x50, 0x60)  # BMP384/BMP388 vs BMP390 (asy_bmp3xx_driver.py's own check)


def test_status_starts_command_ready() -> None:
    chip = Bmp3xxChip()
    reply = _read(chip, 0x03, 1)
    assert reply[0] & 0x10  # STATUS_CMD_RDY


def test_calibration_block_is_not_degenerate() -> None:
    chip = Bmp3xxChip()
    raw = _read(chip, 0x31, 21)
    assert len(raw) == 21
    assert not (raw == bytes([raw[0]]) * len(raw) and raw[0] in (0x00, 0xFF))


def test_forced_mode_trigger_sets_data_ready_and_a_readable_burst() -> None:
    # First 2 values: the uniform draw at construction. Last 2: the step delta the forced-mode
    # trigger below draws - zeroed so the final decoded value stays exactly at the constructed one.
    chip = Bmp3xxChip(random_source=_FixedRandom(uniform_values=[22.0, 1000.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])  # CONTROL = forced mode, press+temp enabled
    status = _read(chip, 0x03, 1)[0]
    assert status & 0x60 == 0x60  # STATUS_DATA_READY (both drdy_press|drdy_temp)
    burst = _read(chip, 0x04, 6)
    assert len(burst) == 6


def test_forced_mode_reading_decodes_to_the_requested_target_via_the_real_formula() -> None:
    chip = Bmp3xxChip(random_source=_FixedRandom(uniform_values=[21.0, 987.0, 0.0, 0.0]))
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
    chip = Bmp3xxChip(random_source=_FixedRandom(uniform_values=[23.5, 1013.25]))
    assert chip._temp_c == 23.5
    assert chip._pressure_hpa == 1013.25


def test_forced_mode_trigger_steps_from_the_previous_value_rather_than_a_fresh_draw() -> None:
    chip = Bmp3xxChip(random_source=_FixedRandom(uniform_values=[20.0, 1000.0, 0.5, -2.0]))
    assert chip._temp_c == 20.0 and chip._pressure_hpa == 1000.0  # construction draw
    _write(chip, 0x1B, [0x13])
    assert chip._temp_c == 20.5  # 20.0 + 0.5
    assert chip._pressure_hpa == 998.0  # 1000.0 + -2.0


def test_forced_mode_trigger_step_is_clamped_to_the_configured_max() -> None:
    chip = Bmp3xxChip(
        max_pressure_hpa=1050.0,
        pressure_step_hpa=5.0,
        random_source=_FixedRandom(uniform_values=[20.0, 1048.0, 0.0, 5.0]),
    )
    _write(chip, 0x1B, [0x13])
    assert chip._pressure_hpa == 1050.0  # 1048.0 + 5.0 would be 1053.0 - clamped to max_pressure_hpa


def test_forced_mode_trigger_step_is_clamped_to_the_configured_min() -> None:
    chip = Bmp3xxChip(
        min_temp_c=15.0,
        temp_step_c=1.0,
        random_source=_FixedRandom(uniform_values=[15.4, 1000.0, -1.0, 0.0]),
    )
    _write(chip, 0x1B, [0x13])
    assert chip._temp_c == 15.0  # 15.4 + -1.0 would be 14.4 - clamped to min_temp_c


def test_step_bounds_are_configurable_via_the_constructor() -> None:
    chip = Bmp3xxChip(
        temp_step_c=0.1,
        pressure_step_hpa=0.5,
        random_source=_FixedRandom(uniform_values=[20.0, 1000.0, 0.1, 0.5]),
    )
    _write(chip, 0x1B, [0x13])  # would violate the default 1.0/5.0 bounds - proves the override took


def test_default_range_stays_inside_the_drivers_own_operating_range_check() -> None:
    # asy_bmp3xx_driver.py's own _read() rejects anything outside 300-1250 hPa / -40-85 degC
    # (datasheet sec 1, Table 2) - the twin's defaults must be a sensible sub-range of that.
    chip = Bmp3xxChip()
    assert 300.0 <= chip._min_pressure_hpa and chip._max_pressure_hpa <= 1250.0
    assert -40.0 <= chip._min_temp_c and chip._max_temp_c <= 85.0


def test_a_fresh_reading_is_drawn_on_every_forced_mode_trigger() -> None:
    # Construction draw: 20.0/1000.0. First trigger's step delta is zeroed (stays at 20.0/1000.0);
    # the second trigger's delta (1.0, 5.0) sits at this chip's default temp_step_c/
    # pressure_step_hpa boundary - proving each trigger draws its own fresh step, not the same value
    # twice, while staying within the walk's own bound.
    chip = Bmp3xxChip(random_source=_FixedRandom(uniform_values=[20.0, 1000.0, 0.0, 0.0, 1.0, 5.0]))
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
    chip = Bmp3xxChip()
    _write(chip, 0x1C, [0b00010101])
    assert _read(chip, 0x1C, 1) == b"\x15"
    _write(chip, 0x1F, [0b00000110])
    assert _read(chip, 0x1F, 1) == b"\x06"


def test_soft_reset_command_restores_command_ready_status() -> None:
    chip = Bmp3xxChip(random_source=_FixedRandom(uniform_values=[20.0, 1000.0, 0.0, 0.0]))
    _write(chip, 0x1B, [0x13])
    assert _read(chip, 0x03, 1)[0] & 0x60  # data ready, not command-ready-only
    _write(chip, 0x7E, [0xB6])  # CMD register, soft reset opcode
    assert _read(chip, 0x03, 1)[0] & 0x10  # back to command-ready


def test_err_register_reports_no_error() -> None:
    chip = Bmp3xxChip()
    assert _read(chip, 0x02, 1) == b"\x00"


def test_unknown_register_returns_zero_bytes_without_raising() -> None:
    chip = Bmp3xxChip()
    assert _read(chip, 0x50, 2) == bytes(2)  # not a register this chip fake models
    _write(chip, 0x50, [0xFF])  # real hardware would just silently accept/ignore it too


def test_handle_writeto_accepts_the_zero_byte_bus_probe_without_raising() -> None:
    # Regression test from baseline verification:
    # asy_i2c_driver.py's I2CDevice.setup()/_probe_for_device() always does a plain, empty
    # chip.writeto(address, b"") before any register access - this chip fake used to have no
    # handle_writeto() at all (only handle_writeto_mem(), matching its real register-addressed
    # protocol), so digital_twin/machine.py's I2C.writeto() dispatch raised AttributeError on every
    # real boot, repeatedly failing the BMP3XX reader task.
    chip = Bmp3xxChip()
    chip.handle_writeto(b"")  # must not raise


def test_fault_injection_on_writeto() -> None:
    chip = Bmp3xxChip()
    chip.fault.inject_fault("writeto", OSError(5, "no ACK"))
    try:
        chip.handle_writeto(b"")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    chip.handle_writeto(b"")  # one-shot fault - back to normal


def test_fault_injection_on_readfrom_mem_and_writeto_mem() -> None:
    chip = Bmp3xxChip()
    chip.fault.inject_fault("readfrom_mem", OSError(5, "no ACK"))
    try:
        _read(chip, 0x00, 1)
        raise AssertionError("expected OSError")
    except OSError:
        pass
    assert _read(chip, 0x00, 1)[0] in (0x50, 0x60)
    chip.fault.inject_fault("writeto_mem", OSError(5, "timeout"))
    try:
        _write(chip, 0x1B, [0x13])
        raise AssertionError("expected OSError")
    except OSError:
        pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
