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


def test_wet_bulb_nan_and_inf_return_none() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.wet_bulb_temperature(nan, 50.0) is None
    assert mh.wet_bulb_temperature(20.0, nan) is None
    assert mh.wet_bulb_temperature(inf, 50.0) is None
    assert mh.wet_bulb_temperature(-inf, 50.0) is None
    assert mh.wet_bulb_temperature(20.0, inf) is None


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
    # The water-phase and ice-phase coefficient sets are two independently-fit approximations stitched
    # together at temperature == 0, not a single continuous formula: measured, they disagree by about 1.03
    # degC right at the boundary at 50% RH - a real property of the formula, not a bug introduced here.
    #
    # A regression guard against that gap growing much larger, from an accidental coefficient or branch-
    # condition change, not an assertion that the two branches are continuous.
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


def test_dew_point_nan_and_inf_return_none() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.dew_point(nan, 50.0) is None
    assert mh.dew_point(20.0, nan) is None
    assert mh.dew_point(inf, 50.0) is None
    assert mh.dew_point(20.0, -inf) is None


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


def test_altitude_baro_nan_and_inf_return_none() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.altitude_baro(nan, 0.0, 20.0) is None
    assert mh.altitude_baro(1000.0, nan, 20.0) is None
    assert mh.altitude_baro(1000.0, 0.0, nan) is None
    assert mh.altitude_baro(-inf, 0.0, 20.0) is None
    assert mh.altitude_baro(1000.0, inf, 20.0) is None


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


def test_abs_humidity_nan_and_inf_return_none() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.abs_humidity(nan, 50.0) is None
    assert mh.abs_humidity(20.0, nan) is None
    assert mh.abs_humidity(inf, 50.0) is None
    assert mh.abs_humidity(20.0, inf) is None


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


def test_rel_humidity_nan_and_inf_return_none() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.rel_humidity(nan, 5.0) is None
    assert mh.rel_humidity(20.0, nan) is None
    assert mh.rel_humidity(inf, 5.0) is None
    assert mh.rel_humidity(20.0, inf) is None


# ---------------------------------------------------------------------------
# rgb_to_hsb
# ---------------------------------------------------------------------------


def test_rgb_to_hsb_none_inputs() -> None:
    assert mh.rgb_to_hsb(None, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, None, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 0.5, None) is None


def test_rgb_to_hsb_out_of_range_rejected() -> None:
    assert mh.rgb_to_hsb(-0.001, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(1.001, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, -0.001, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 0.5, 1.001) is None


def test_rgb_to_hsb_nan_and_inf_rejected() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.rgb_to_hsb(nan, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, nan, 0.5) is None
    assert mh.rgb_to_hsb(inf, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 0.5, -inf) is None


def test_rgb_to_hsb_boundary_values_accepted() -> None:
    assert mh.rgb_to_hsb(0.0, 0.0, 0.0) is not None
    assert mh.rgb_to_hsb(1.0, 1.0, 1.0) is not None


def test_rgb_to_hsb_grey_has_zero_hue_and_saturation() -> None:
    # chroma == 0: a real, valid colour (no hue), not a read failure - None would be wrong here.
    result = mh.rgb_to_hsb(0.4, 0.4, 0.4)
    assert result is not None
    hue, sat, bri = result
    assert approx(hue, 0.0)
    assert approx(sat, 0.0)
    assert approx(bri, 0.4)


def test_rgb_to_hsb_black_is_grey_too() -> None:
    result = mh.rgb_to_hsb(0.0, 0.0, 0.0)
    assert result is not None
    hue, sat, bri = result
    assert approx(hue, 0.0)
    assert approx(sat, 0.0)
    assert approx(bri, 0.0)


def test_rgb_to_hsb_red_max_branch() -> None:
    # RGB(255, 128, 0) - orange, hue ~30 degrees.
    result = mh.rgb_to_hsb(1.0, 0.5, 0.0)
    assert result is not None
    hue, sat, bri = result
    assert approx(hue, 30.0, tol=0.1)
    assert approx(sat, 1.0)
    assert approx(bri, 1.0)


def test_rgb_to_hsb_green_max_branch() -> None:
    # RGB(0, 255, 128) - spring green, hue ~150 degrees.
    result = mh.rgb_to_hsb(0.0, 1.0, 0.5)
    assert result is not None
    hue, _sat, _bri = result
    assert approx(hue, 150.0, tol=0.1)


def test_rgb_to_hsb_blue_max_branch() -> None:
    # RGB(128, 0, 255) - violet, hue ~270 degrees.
    result = mh.rgb_to_hsb(0.5, 0.0, 1.0)
    assert result is not None
    hue, _sat, _bri = result
    assert approx(hue, 270.0, tol=0.1)


def test_rgb_to_hsb_hue_wraps_into_0_360() -> None:
    # Red-max branch with green < blue drives the raw formula negative before the final wrap.
    result = mh.rgb_to_hsb(1.0, 0.0, 0.5)
    assert result is not None
    hue, _sat, _bri = result
    assert 0.0 <= hue < 360.0
    assert approx(hue, 330.0, tol=0.1)


# ---------------------------------------------------------------------------
# rgb_to_xyz
# ---------------------------------------------------------------------------


def test_rgb_to_xyz_none_inputs() -> None:
    assert mh.rgb_to_xyz(None, 0.5, 0.5) is None
    assert mh.rgb_to_xyz(0.5, None, 0.5) is None
    assert mh.rgb_to_xyz(0.5, 0.5, None) is None


def test_rgb_to_xyz_out_of_range_rejected() -> None:
    assert mh.rgb_to_xyz(-0.001, 0.5, 0.5) is None
    assert mh.rgb_to_xyz(0.5, 1.001, 0.5) is None


def test_rgb_to_xyz_nan_and_inf_rejected() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.rgb_to_xyz(nan, 0.5, 0.5) is None
    assert mh.rgb_to_xyz(0.5, 0.5, inf) is None


def test_rgb_to_xyz_black_is_zero() -> None:
    result = mh.rgb_to_xyz(0.0, 0.0, 0.0)
    assert result is not None
    x_val, y_val, z_val = result
    assert approx(x_val, 0.0)
    assert approx(y_val, 0.0)
    assert approx(z_val, 0.0)


def test_rgb_to_xyz_pure_red_matches_the_sRGB_matrix_column() -> None:
    result = mh.rgb_to_xyz(1.0, 0.0, 0.0)
    assert result is not None
    x_val, y_val, z_val = result
    assert approx(x_val, 0.4124564)
    assert approx(y_val, 0.2126729)
    assert approx(z_val, 0.0193339)


def test_rgb_to_xyz_coefficients_are_the_pinned_literals() -> None:
    # Exact equality, not approx(): two published roundings of this matrix differ in the 6th decimal
    # (Part C.11.2) and both would pass a 1e-6 tolerance. The constants are const()-folded and not
    # readable as attributes, so reading them back through a pure primary is the only way to pin.
    assert mh.rgb_to_xyz(1.0, 0.0, 0.0) == (0.4124564, 0.2126729, 0.0193339)
    assert mh.rgb_to_xyz(0.0, 1.0, 0.0) == (0.3575761, 0.7151522, 0.1191920)
    assert mh.rgb_to_xyz(0.0, 0.0, 1.0) == (0.1804375, 0.0721750, 0.9503041)


def test_rgb_to_xyz_white_matches_the_d65_white_point() -> None:
    # A known, independently-published check value: sRGB white (1,1,1) -> the D65 reference white
    # point (~0.95047, 1.0, 1.08883) - real evidence the three coefficient rows weren't transposed
    # or mistyped, not just "it returns a tuple".
    result = mh.rgb_to_xyz(1.0, 1.0, 1.0)
    assert result is not None
    x_val, y_val, z_val = result
    assert approx(x_val, 0.95047, tol=1e-4)
    assert approx(y_val, 1.0, tol=1e-4)
    assert approx(z_val, 1.08883, tol=1e-4)


# ---------------------------------------------------------------------------
# chromaticity_xy
# ---------------------------------------------------------------------------


def test_chromaticity_xy_none_inputs() -> None:
    assert mh.chromaticity_xy(None, 0.5, 0.5) is None
    assert mh.chromaticity_xy(0.5, None, 0.5) is None
    assert mh.chromaticity_xy(0.5, 0.5, None) is None


def test_chromaticity_xy_darkness_rejected() -> None:
    # A near-zero (or exactly zero) sum is darkness, not a valid chromaticity to divide out.
    assert mh.chromaticity_xy(0.0, 0.0, 0.0) is None
    assert mh.chromaticity_xy(1e-15, 1e-15, 1e-15) is None


def test_chromaticity_xy_negative_sum_rejected() -> None:
    assert mh.chromaticity_xy(-1.0, -1.0, -1.0) is None


def test_chromaticity_xy_absurdly_large_sum_rejected() -> None:
    assert mh.chromaticity_xy(2e9, 0.0, 0.0) is None


def test_chromaticity_xy_nan_and_inf_rejected() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.chromaticity_xy(nan, 0.5, 0.5) is None
    assert mh.chromaticity_xy(inf, 0.5, 0.5) is None


def test_chromaticity_xy_d65_white_point() -> None:
    # Feeding rgb_to_xyz(1,1,1)'s own output back through should land on D65's published
    # chromaticity (~0.3127, ~0.3290) - a real round-trip check, not an isolated formula check.
    xyz = mh.rgb_to_xyz(1.0, 1.0, 1.0)
    assert xyz is not None
    result = mh.chromaticity_xy(*xyz)
    assert result is not None
    chroma_x, chroma_y = result
    assert approx(chroma_x, 0.3127, tol=1e-3)
    assert approx(chroma_y, 0.3290, tol=1e-3)


def test_chromaticity_xy_boundary_sum_accepted() -> None:
    assert mh.chromaticity_xy(1e-12, 0.0, 0.0) is not None
    assert mh.chromaticity_xy(1e9, 0.0, 0.0) is not None


# ---------------------------------------------------------------------------
# cct_mccamy
# ---------------------------------------------------------------------------


def test_cct_mccamy_none_inputs() -> None:
    assert mh.cct_mccamy(None, 0.33) is None
    assert mh.cct_mccamy(0.31, None) is None


def test_cct_mccamy_out_of_domain_chromaticity_rejected() -> None:
    assert mh.cct_mccamy(-0.001, 0.33) is None
    assert mh.cct_mccamy(0.31, 1.001) is None


def test_cct_mccamy_nan_and_inf_rejected() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.cct_mccamy(nan, 0.33) is None
    assert mh.cct_mccamy(0.31, inf) is None


def test_cct_mccamy_epicentre_is_rejected_not_a_zero_division_crash() -> None:
    # y = 0.1858 makes the denominator exactly zero - this is the one case in the whole colour
    # chain that would otherwise raise, so it gets its own dedicated, "biting" test.
    assert mh.cct_mccamy(0.3, 0.1858) is None


def test_cct_mccamy_d65_chromaticity_is_close_to_6500k() -> None:
    # D65's own defining chromaticity should round-trip back to approximately 6500K - real
    # evidence the coefficients/sign convention are right, not just "returns a float".
    result = mh.cct_mccamy(0.3127, 0.3290)
    assert result is not None
    assert 6300.0 < result < 6700.0


def test_cct_mccamy_out_of_span_result_is_rejected_not_clamped() -> None:
    # A valid (in-domain) chromaticity whose formula result still lands outside the McCamy
    # validity span (2000-12500K) must return None, never a clamped 2000.0/12500.0 that would
    # look like a real measurement.
    assert mh.cct_mccamy(0.0, 0.5) is None


def test_cct_mccamy_boundary_domain_values_accepted_or_rejected_on_their_own_merits() -> None:
    # 0.0/1.0 are in-domain chromaticities; whether the *result* is in-span is a separate question
    # already covered above - this only asserts the domain gate itself doesn't reject them outright.
    assert mh.cct_mccamy(0.0, 0.0) is not None


# ---------------------------------------------------------------------------
# ema_step
# ---------------------------------------------------------------------------


def test_ema_step_none_sample_returns_none() -> None:
    assert mh.ema_step(10.0, None, 0.5) is None


def test_ema_step_nan_or_inf_sample_returns_none() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.ema_step(10.0, nan, 0.5) is None
    assert mh.ema_step(10.0, inf, 0.5) is None


def test_ema_step_none_coefficient_bypasses_the_filter() -> None:
    # No coefficient at all - treated the same as "off", the sample passes through unfiltered.
    assert mh.ema_step(10.0, 20.0, None) == 20.0


def test_ema_step_filt_coeff_off_sentinel_bypasses_the_filter() -> None:
    # -1.0 is FiltCoeff's own documented "filter off" convention throughout src/.
    assert mh.ema_step(10.0, 20.0, -1.0) == 20.0


def test_ema_step_zero_coefficient_bypasses_the_filter() -> None:
    # 0.0 is excluded by the strict "> 0.0" lower bound too - would otherwise mean "never update".
    assert mh.ema_step(10.0, 20.0, 0.0) == 20.0


def test_ema_step_coefficient_above_one_bypasses_the_filter() -> None:
    assert mh.ema_step(10.0, 20.0, 1.5) == 20.0


def test_ema_step_nan_coefficient_bypasses_the_filter() -> None:
    nan = float("nan")
    assert mh.ema_step(10.0, 20.0, nan) == 20.0


def test_ema_step_unseeded_previous_returns_the_sample() -> None:
    # First-ever sample: nothing to blend with yet.
    assert mh.ema_step(None, 20.0, 0.5) == 20.0


def test_ema_step_poisoned_previous_recovers_to_the_sample() -> None:
    # A NaN/inf previous state (e.g. from an earlier unfiltered pass-through of a bad reading)
    # must not poison every future value forever - the next good sample resets it clean.
    nan = float("nan")
    inf = float("inf")
    assert mh.ema_step(nan, 20.0, 0.5) == 20.0
    assert mh.ema_step(inf, 20.0, 0.5) == 20.0


def test_ema_step_normal_blend_is_the_documented_formula() -> None:
    result = mh.ema_step(10.0, 20.0, 0.5)
    assert result is not None
    assert approx(result, 15.0)


def test_ema_step_coefficient_one_is_full_replacement() -> None:
    # The upper bound (1.0) is inclusive and valid - not a bypass - and collapses to the sample.
    result = mh.ema_step(10.0, 20.0, 1.0)
    assert result is not None
    assert approx(result, 20.0)


def test_ema_step_converges_toward_a_held_constant_sample() -> None:
    # Resilience/"biting" check: repeated stepping with a fixed coefficient must monotonically
    # close the gap to a constant sample, and actually reach it within a bounded number of steps -
    # not just return *some* number each time.
    value: float | None = 0.0
    previous_gap = 100.0
    for _ in range(60):
        assert value is not None
        gap = abs(100.0 - value)
        assert gap <= previous_gap
        previous_gap = gap
        value = mh.ema_step(value, 100.0, 0.2)
    assert value is not None
    assert approx(value, 100.0, tol=1e-3)  # gap shrinks by (1-0.2) per step: 100*0.8**60 ~ 1.5e-4


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
