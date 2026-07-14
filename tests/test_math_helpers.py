import math_helpers as mh


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# wet_bulb_temperature
# ---------------------------------------------------------------------------


def test_wet_bulb_none_temperature() -> None:
    assert mh.wet_bulb_temperature(None, 50.0) is None


def test_wet_bulb_none_humidity() -> None:
    assert mh.wet_bulb_temperature(20.0, None) is None


def test_wet_bulb_none_both() -> None:
    assert mh.wet_bulb_temperature(None, None) is None


def test_wet_bulb_valid_typical() -> None:
    result = mh.wet_bulb_temperature(25.0, 50.0)
    assert result is not None
    assert 15.0 < result < 20.0


def test_wet_bulb_temperature_below_range() -> None:
    assert mh.wet_bulb_temperature(-20.1, 50.0) is None


def test_wet_bulb_temperature_above_range() -> None:
    assert mh.wet_bulb_temperature(50.1, 50.0) is None


def test_wet_bulb_humidity_below_range() -> None:
    # 0.5% used to be the (incorrect) lower bound; Stull's paper only validates 5-99% RH.
    assert mh.wet_bulb_temperature(20.0, 0.5) is None
    assert mh.wet_bulb_temperature(20.0, 4.9) is None


def test_wet_bulb_humidity_above_range() -> None:
    assert mh.wet_bulb_temperature(20.0, 99.1) is None


def test_wet_bulb_boundary_values_accepted() -> None:
    assert mh.wet_bulb_temperature(-20.0, 5.0) is not None
    assert mh.wet_bulb_temperature(50.0, 99.0) is not None


def test_wet_bulb_no_exception_on_extreme_inputs() -> None:
    assert mh.wet_bulb_temperature(-1000.0, 50.0) is None
    assert mh.wet_bulb_temperature(1000.0, 50.0) is None
    assert mh.wet_bulb_temperature(20.0, -1000.0) is None
    assert mh.wet_bulb_temperature(20.0, 1000.0) is None


# ---------------------------------------------------------------------------
# dew_point
# ---------------------------------------------------------------------------


def test_dew_point_none_inputs() -> None:
    assert mh.dew_point(None, 50.0) is None
    assert mh.dew_point(20.0, None) is None
    assert mh.dew_point(None, None) is None


def test_dew_point_valid_water_branch() -> None:
    result = mh.dew_point(25.0, 50.0)
    assert result is not None
    assert 12.0 < result < 15.0


def test_dew_point_valid_ice_branch() -> None:
    result = mh.dew_point(-10.0, 80.0)
    assert result is not None
    assert result < -10.0


def test_dew_point_branch_boundary_roughly_continuous() -> None:
    # The water-phase and ice-phase coefficient sets are two independently-fit approximations
    # stitched together at temperature == 0, not a single continuous formula: measured, they
    # disagree by about 1.03 degC right at the boundary (50% RH) - a real property of this
    # formula, not a bug introduced here. This is a regression guard against that gap growing
    # much larger (e.g. from an accidental coefficient/branch-condition change), not an assertion
    # that the two branches are continuous.
    just_above = mh.dew_point(0.0, 50.0)
    just_below = mh.dew_point(-0.001, 50.0)
    assert just_above is not None
    assert just_below is not None
    assert approx(just_above, just_below, tol=1.5)


def test_dew_point_out_of_range_temperature() -> None:
    assert mh.dew_point(-40.1, 50.0) is None
    assert mh.dew_point(50.1, 50.0) is None


def test_dew_point_out_of_range_humidity() -> None:
    assert mh.dew_point(20.0, 0.05) is None
    assert mh.dew_point(20.0, 100.1) is None


def test_dew_point_boundary_values_accepted() -> None:
    assert mh.dew_point(-40.0, 0.1) is not None
    assert mh.dew_point(50.0, 100.0) is not None


def test_dew_point_never_exceeds_air_temperature() -> None:
    result = mh.dew_point(30.0, 40.0)
    assert result is not None
    assert result <= 30.0


# ---------------------------------------------------------------------------
# altitude_baro
# ---------------------------------------------------------------------------


def test_altitude_baro_none_inputs() -> None:
    assert mh.altitude_baro(None, 0.0, 20.0) is None
    assert mh.altitude_baro(1013.0, None, 20.0) is None
    assert mh.altitude_baro(1013.0, 0.0, None) is None


def test_altitude_baro_zero_offset_is_identity() -> None:
    result = mh.altitude_baro(1000.0, 0.0, 20.0)
    assert result is not None
    assert approx(result, 1000.0, tol=1e-6)


def test_altitude_baro_negative_dh_increases_pressure() -> None:
    # Negative dh = reducing a station reading up to sea level, so pressure should increase.
    result = mh.altitude_baro(950.0, -500.0, 15.0)
    assert result is not None
    assert result > 950.0


def test_altitude_baro_positive_dh_decreases_pressure() -> None:
    result = mh.altitude_baro(1013.25, 1000.0, 15.0)
    assert result is not None
    assert result < 1013.25


def test_altitude_baro_out_of_range_pressure() -> None:
    assert mh.altitude_baro(299.9, 0.0, 20.0) is None
    assert mh.altitude_baro(1250.1, 0.0, 20.0) is None


def test_altitude_baro_out_of_range_temperature() -> None:
    assert mh.altitude_baro(1000.0, 0.0, -40.1) is None
    assert mh.altitude_baro(1000.0, 0.0, 85.1) is None


def test_altitude_baro_out_of_range_dh() -> None:
    assert mh.altitude_baro(1000.0, -9000.1, 20.0) is None
    assert mh.altitude_baro(1000.0, 9000.1, 20.0) is None


def test_altitude_baro_boundary_values_accepted() -> None:
    assert mh.altitude_baro(300.0, -9000.0, -40.0) is not None
    assert mh.altitude_baro(1250.0, 9000.0, 85.0) is not None


def test_altitude_baro_no_exception_near_absolute_zero() -> None:
    # tmean = -273.15 would zero the formula's denominator; the -40..85 degC range check must
    # reject it before the division ever runs.
    assert mh.altitude_baro(1000.0, 100.0, -273.15) is None


# ---------------------------------------------------------------------------
# abs_humidity / rel_humidity
# ---------------------------------------------------------------------------


def test_abs_humidity_none_inputs() -> None:
    assert mh.abs_humidity(None, 50.0) is None
    assert mh.abs_humidity(20.0, None) is None


def test_abs_humidity_valid() -> None:
    result = mh.abs_humidity(20.0, 50.0)
    assert result is not None
    assert 8.0 < result < 9.5


def test_abs_humidity_zero_humidity_is_zero() -> None:
    result = mh.abs_humidity(20.0, 0.0)
    assert result is not None
    assert approx(result, 0.0, tol=1e-9)


def test_abs_humidity_out_of_range_temperature() -> None:
    assert mh.abs_humidity(-30.1, 50.0) is None
    assert mh.abs_humidity(40.1, 50.0) is None


def test_abs_humidity_out_of_range_humidity() -> None:
    assert mh.abs_humidity(20.0, -0.1) is None
    assert mh.abs_humidity(20.0, 100.1) is None


def test_abs_humidity_boundary_values_accepted() -> None:
    assert mh.abs_humidity(-30.0, 0.0) is not None
    assert mh.abs_humidity(40.0, 100.0) is not None


def test_rel_humidity_none_inputs() -> None:
    assert mh.rel_humidity(None, 5.0) is None
    assert mh.rel_humidity(20.0, None) is None


def test_rel_humidity_round_trip() -> None:
    ah = mh.abs_humidity(20.0, 50.0)
    assert ah is not None
    rh = mh.rel_humidity(20.0, ah)
    assert rh is not None
    assert approx(rh, 50.0, tol=0.01)


def test_rel_humidity_clamped_high() -> None:
    # An abs_hum far above what 100% RH would produce at this temperature must clamp to 100, not
    # return an out-of-range percentage.
    result = mh.rel_humidity(20.0, 20.0)
    assert result is not None
    assert approx(result, 100.0, tol=1e-6)


def test_rel_humidity_zero_is_zero() -> None:
    result = mh.rel_humidity(20.0, 0.0)
    assert result is not None
    assert approx(result, 0.0, tol=1e-9)


def test_rel_humidity_out_of_range_temperature() -> None:
    assert mh.rel_humidity(-30.1, 5.0) is None
    assert mh.rel_humidity(40.1, 5.0) is None


def test_rel_humidity_out_of_range_abs_hum() -> None:
    assert mh.rel_humidity(20.0, -0.1) is None
    assert mh.rel_humidity(20.0, 100.1) is None


def test_rel_humidity_boundary_values_accepted() -> None:
    assert mh.rel_humidity(-30.0, 0.0) is not None
    assert mh.rel_humidity(40.0, 100.0) is not None


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
