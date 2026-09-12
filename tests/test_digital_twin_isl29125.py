"""Deterministic unit tests for digital_twin/_isl29125_chip.py's own transaction-response logic - matches the register-addressed shape src/asy_isl29125_driver.py's ISL29125_I2C sends.
Real-time INT-pin scheduling is exercised only through the synchronous set_illumination()/_produce_new_reading() hooks here; the real-time-firing check lives in test_digital_twin_machine.py."""

import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _isl29125_chip import Isl29125Chip

_ADDR_ID = 0x00
_ADDR_CONFIG1 = 0x01
_ADDR_CONFIG2 = 0x02
_ADDR_CONFIG3 = 0x03
_ADDR_THRESH = 0x04
_ADDR_STATUS = 0x08
_ADDR_DATA = 0x09

_MODE_RGB = 0x05
_RNG_HIGH = 0x08
_BITS_12 = 0x10
_INTSEL_GREEN = 0x01

_STATUS_RGBTHF = 0x01
_STATUS_BOUTF = 0x04


class _FixedRandom:
    # Every value walk in this file is driven explicitly through set_illumination(), so the only
    # uniform() call that ever happens is the one in __init__ - scripted to one fixed value so
    # nothing in these tests depends on the host's own RNG.
    def __init__(self, value: float = 100.0) -> None:
        self._value = value

    def uniform(self, a: float, b: float) -> float:
        return self._value


class _RecordingPin:
    # Stand-in for machine.py's Pin - only simulate_edge() is ever called on an INT pin.
    def __init__(self) -> None:
        self.edges: list[int] = []
        self.value = 1  # idle high: the line is open-drain with an external pull-up

    def simulate_edge(self, new_value: object) -> None:
        level = 1 if new_value else 0
        if level == self.value:
            return
        self.value = level
        self.edges.append(level)


def make_chip(**kwargs: object) -> Isl29125Chip:
    kwargs.setdefault("random_source", _FixedRandom())
    kwargs.setdefault("auto_refresh", False)
    return Isl29125Chip(**kwargs)  # type: ignore[arg-type]


def configure(chip: Isl29125Chip, config1: int, config2: int = 0x00, config3: int = 0x00) -> None:
    # One 3-byte burst from 0x01, exactly the shape the driver's own _write_shadow() sends.
    chip.handle_writeto_mem(_ADDR_CONFIG1, bytes([config1, config2, config3]))


def read_counts(chip: Isl29125Chip) -> "tuple[int, int, int]":
    raw = chip.handle_readfrom_mem(_ADDR_DATA, 6)
    green = raw[0] | (raw[1] << 8)
    red = raw[2] | (raw[3] << 8)
    blue = raw[4] | (raw[5] << 8)
    return green, red, blue


# ---------------------------------------------------------------------------
# power-on state and identity
# ---------------------------------------------------------------------------


def test_device_id_reads_the_datasheet_value() -> None:
    chip = make_chip()
    assert chip.handle_readfrom_mem(_ADDR_ID, 1) == bytes([0x7D])


def test_power_on_config_is_all_zero() -> None:
    chip = make_chip()
    assert chip.handle_readfrom_mem(_ADDR_CONFIG1, 3) == bytes([0x00, 0x00, 0x00])


def test_brownout_flag_is_high_at_power_on() -> None:
    # Table 18 p12: BOUTF defaults HIGH, so a freshly constructed chip really is in the
    # post-brownout state - a twin test expecting readings before the driver configures it is
    # asserting the wrong thing.
    chip = make_chip()
    assert chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_BOUTF


def test_thresholds_default_to_the_documented_values() -> None:
    # Table 14 p12: low threshold 0x0000, high threshold 0xFFFF.
    chip = make_chip()
    assert chip.handle_readfrom_mem(_ADDR_THRESH, 4) == bytes([0x00, 0x00, 0xFF, 0xFF])


def test_no_conversion_happens_in_the_power_down_mode() -> None:
    chip = make_chip()
    chip.set_illumination(200.0)
    assert read_counts(chip) == (0, 0, 0)


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_command_restores_every_default() -> None:
    chip = make_chip()
    configure(chip, _MODE_RGB | _RNG_HIGH, 0x28, 0x09)
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x34, 0x12, 0xCD, 0xAB]))
    chip.handle_writeto_mem(_ADDR_STATUS, bytes([0x00]))  # clear BOUTF
    chip.handle_writeto_mem(_ADDR_ID, bytes([0x46]))
    assert chip.handle_readfrom_mem(_ADDR_CONFIG1, 3) == bytes([0x00, 0x00, 0x00])
    assert chip.handle_readfrom_mem(_ADDR_THRESH, 4) == bytes([0x00, 0x00, 0xFF, 0xFF])
    # BOUTF comes back HIGH: Table 15 documents 0x04 as this register's own default, so a reset
    # restores it exactly like a power-up does. The driver's own reset verify has to tolerate it.
    assert chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_BOUTF


def test_a_non_reset_write_to_the_id_register_is_ignored() -> None:
    chip = make_chip()
    configure(chip, _MODE_RGB)
    chip.handle_writeto_mem(_ADDR_ID, bytes([0x12]))
    assert chip.handle_readfrom_mem(_ADDR_CONFIG1, 1) == bytes([_MODE_RGB])


# ---------------------------------------------------------------------------
# config writes
# ---------------------------------------------------------------------------


def test_a_three_byte_burst_from_0x01_writes_all_three_config_registers() -> None:
    chip = make_chip()
    configure(chip, 0x15, 0x28, 0x09)
    assert chip.handle_readfrom_mem(_ADDR_CONFIG1, 3) == bytes([0x15, 0x28, 0x09])


def test_a_two_byte_burst_from_0x02_leaves_config1_untouched() -> None:
    # The driver writes from 0x02 for an IR-compensation-only change precisely so the conversion
    # is not restarted - this asserts the fake honours the auto-incrementing address pointer.
    chip = make_chip()
    configure(chip, 0x15, 0x28, 0x09)
    chip.handle_writeto_mem(_ADDR_CONFIG2, bytes([0x3F, 0x05]))
    assert chip.handle_readfrom_mem(_ADDR_CONFIG1, 3) == bytes([0x15, 0x3F, 0x05])


def test_threshold_burst_is_little_endian_low_pair_then_high_pair() -> None:
    chip = make_chip()
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x34, 0x12, 0xCD, 0xAB]))
    assert chip.handle_readfrom_mem(_ADDR_THRESH, 4) == bytes([0x34, 0x12, 0xCD, 0xAB])


def test_writing_the_status_register_clears_the_brownout_flag() -> None:
    chip = make_chip()
    chip.handle_writeto_mem(_ADDR_STATUS, bytes([0x00]))
    assert not chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_BOUTF


# ---------------------------------------------------------------------------
# the conversion model
# ---------------------------------------------------------------------------


def test_counts_scale_linearly_with_illumination_on_the_low_range() -> None:
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB)  # RNG = 0 -> 375 lux full scale
    chip.set_illumination(187.5)
    green, red, blue = read_counts(chip)
    assert abs(green - 32768) <= 1
    assert green == red == blue  # a neutral tint weights all three the same


def test_the_high_range_uses_the_per_instance_ratio_not_the_nominal_one() -> None:
    # This is the whole point of the non-nominal ratio: the same light read on the high range
    # does NOT come back at lux/10000 of full scale, so the driver has a real error to learn.
    chip = make_chip(dark_counts=0, gain_ratio=25.9)
    configure(chip, _MODE_RGB | _RNG_HIGH)
    chip.set_illumination(1000.0)
    green, _red, _blue = read_counts(chip)
    nominal = int(1000.0 / 10000.0 * 65535)
    actual = int(1000.0 / (375.0 * 25.9) * 65535)
    assert abs(green - actual) <= 1
    assert abs(green - nominal) > 100  # measurably off nominal, in the direction the ratio says


def test_the_low_range_carries_the_dark_count_and_the_high_range_does_not() -> None:
    # DDark is specified at range 0 (p3), and that is the only place an additive offset is
    # material - 1 count is 0.006 lux there and 0.15 lux on the high range.
    chip = make_chip(dark_counts=1)
    configure(chip, _MODE_RGB)
    chip.set_illumination(0.0)
    assert read_counts(chip) == (1, 1, 1)
    configure(chip, _MODE_RGB | _RNG_HIGH)
    chip.set_illumination(0.0)
    assert read_counts(chip) == (0, 0, 0)


def test_twelve_bit_mode_truncates_to_the_twelve_bit_full_scale() -> None:
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB | _BITS_12)
    chip.set_illumination(187.5)
    green, _red, _blue = read_counts(chip)
    assert abs(green - 2048) <= 1  # half of 4095, not half of 65535


def test_clipping_reads_the_resolutions_own_maximum_not_65535() -> None:
    # Load-bearing: the driver tests saturation against (1 << bits) - 1 on the RAW counts, so a
    # fake that saturated at 65535 regardless of BITS would make the 12-bit half of that vacuous.
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB)
    chip.set_illumination(10000.0)  # far past the 375 lux range
    assert read_counts(chip) == (65535, 65535, 65535)
    configure(chip, _MODE_RGB | _BITS_12)
    chip.set_illumination(10000.0)
    assert read_counts(chip) == (4095, 4095, 4095)


def test_a_tint_can_clip_one_channel_while_green_stays_mid_scale() -> None:
    # The scene the auto-range peak rule exists for, and the one a scalar-lux fake cannot make.
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB)
    chip.set_illumination(200.0, tint=(3.0, 0.4, 0.3))
    green, red, blue = read_counts(chip)
    assert red == 65535
    assert green < 30000
    assert blue < green


def test_data_registers_are_green_red_blue_in_that_order() -> None:
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB)
    chip.set_illumination(100.0, tint=(0.5, 1.0, 0.25))
    green, red, blue = read_counts(chip)
    assert green > red > blue  # the tint's own ordering, read back through the register layout


def test_a_config1_write_leaves_the_previous_cycles_data_in_place() -> None:
    # Table 7 p10: with SYNC = 0 the ADC restarts on an I2C write to 0x01. The registers are
    # double buffered, so what is readable until the next cycle completes is the PREVIOUS
    # sample - taken on the old gain. That stale window is what the driver's settle wait exists
    # to discard, so the fake has to present it rather than smooth it away.
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB)
    chip.set_illumination(187.5)
    before = read_counts(chip)
    chip.handle_writeto_mem(_ADDR_CONFIG1, bytes([_MODE_RGB | _RNG_HIGH]))
    assert read_counts(chip) == before


# ---------------------------------------------------------------------------
# the status register and the INT line
# ---------------------------------------------------------------------------


def test_reading_the_status_register_clears_the_interrupt_flag_and_releases_the_pin() -> None:
    pin = _RecordingPin()
    chip = make_chip(int_pin=pin, dark_counts=0)
    configure(chip, _MODE_RGB, 0x00, _INTSEL_GREEN)
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x00, 0x00, 0x00, 0x10]))  # high threshold 4096
    chip.set_illumination(187.5)  # ~32768 counts, well above it
    assert pin.edges == [0]  # active-low assert
    assert chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_RGBTHF
    # The read is destructive - the flag is gone and the line is back high.
    assert not chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_RGBTHF
    assert pin.edges == [0, 1]


def test_no_interrupt_is_raised_when_intsel_is_disarmed() -> None:
    pin = _RecordingPin()
    chip = make_chip(int_pin=pin, dark_counts=0)
    configure(chip, _MODE_RGB, 0x00, 0x00)  # INTSEL = 00, "No Interrupt"
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x00, 0x00, 0x00, 0x10]))
    chip.set_illumination(187.5)
    assert pin.edges == []
    assert not chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_RGBTHF


def test_persistence_delays_the_interrupt_by_the_configured_cycle_count() -> None:
    # PRST = 10 -> 4 integration cycles (Table 12 p11), one per RGB cycle since INTSEL selects a
    # single channel that converts once per cycle.
    pin = _RecordingPin()
    chip = make_chip(int_pin=pin, dark_counts=0)
    configure(chip, _MODE_RGB, 0x00, _INTSEL_GREEN | 0x08)  # PRST[1:0] = 10
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x00, 0x00, 0x00, 0x10]))
    for _ in range(3):
        chip.set_illumination(187.5)
        assert pin.edges == []
    chip.set_illumination(187.5)
    assert pin.edges == [0]


def test_persistence_restarts_when_the_reading_comes_back_inside_the_window() -> None:
    pin = _RecordingPin()
    chip = make_chip(int_pin=pin, dark_counts=0)
    configure(chip, _MODE_RGB, 0x00, _INTSEL_GREEN | 0x08)  # 4 cycles
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x00, 0x00, 0x00, 0x10]))
    for _ in range(3):
        chip.set_illumination(187.5)
    chip.set_illumination(10.0)  # back inside the window - the counter restarts from zero
    for _ in range(3):
        chip.set_illumination(187.5)
        assert pin.edges == []


def test_the_int_stuck_high_fault_suppresses_the_edge_while_data_keeps_moving() -> None:
    # Requirement 17's failure mode, and the only thing in this package that can produce it: the
    # bus keeps working, the flag still sets, and the line simply never moves.
    pin = _RecordingPin()
    chip = make_chip(int_pin=pin, dark_counts=0)
    chip.configure_fault("isl29125:int_stuck_high")
    configure(chip, _MODE_RGB, 0x00, _INTSEL_GREEN)
    chip.handle_writeto_mem(_ADDR_THRESH, bytes([0x00, 0x00, 0x00, 0x10]))
    chip.set_illumination(187.5)
    assert pin.edges == []
    assert chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] & _STATUS_RGBTHF
    assert read_counts(chip) != (0, 0, 0)  # conversions never stopped


def test_configure_fault_rejects_an_unknown_mode() -> None:
    chip = make_chip()
    try:
        chip.configure_fault("isl29125:nonsense")
    except ValueError:
        return
    raise AssertionError("an unknown fault mode must be rejected, not silently ignored")


def test_the_conversion_flag_field_rotates_across_the_three_channels() -> None:
    chip = make_chip(dark_counts=0)
    configure(chip, _MODE_RGB)
    seen = set()
    for _ in range(6):
        chip.set_illumination(100.0)
        seen.add((chip.handle_readfrom_mem(_ADDR_STATUS, 1)[0] >> 4) & 0x03)
    assert seen == {1, 2, 3}


# ---------------------------------------------------------------------------
# fault injection through the shared primitive
# ---------------------------------------------------------------------------


def test_injected_bus_faults_surface_on_the_matching_operation_only() -> None:
    chip = make_chip()
    chip.fault.inject_fault("readfrom_mem", OSError(5, "injected"))
    try:
        chip.handle_readfrom_mem(_ADDR_ID, 1)
    except OSError:
        pass
    else:
        raise AssertionError("the injected read fault did not surface")
    chip.handle_writeto_mem(_ADDR_CONFIG1, bytes([0x05]))  # a write is unaffected
    assert chip.handle_readfrom_mem(_ADDR_CONFIG1, 1) == bytes([0x05])


def test_cycle_time_follows_the_configured_resolution() -> None:
    chip = make_chip()
    configure(chip, _MODE_RGB)
    assert chip.cycle_ms() == 303  # 3 x tINT, tINT = 101ms at 16 bits (p3)
    configure(chip, _MODE_RGB | _BITS_12)
    assert chip.cycle_ms() == 19  # 3 x ~6.3ms, derived from p6's n-bit-counter model


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
