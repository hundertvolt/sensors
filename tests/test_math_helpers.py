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
# rgb_to_hsb - M1 (ISL29125 colour chain, see ISL29125_FUNCTION_SPEC.md section 4.1)
# ---------------------------------------------------------------------------


def test_rgb_to_hsb_covers_all_six_hue_sectors() -> None:
    # One pure colour per 60-degree sector of the HSV hexcone, so a mis-ordered branch in the
    # which-channel-is-max dispatch cannot pass: each sector is reached by a different branch.
    cases = (
        (1.0, 0.0, 0.0, 0.0),  # red
        (1.0, 1.0, 0.0, 60.0),  # yellow
        (0.0, 1.0, 0.0, 120.0),  # green
        (0.0, 1.0, 1.0, 180.0),  # cyan
        (0.0, 0.0, 1.0, 240.0),  # blue
        (1.0, 0.0, 1.0, 300.0),  # magenta
    )
    for red, green, blue, expected_hue in cases:
        result = mh.rgb_to_hsb(red, green, blue)
        assert result is not None
        hue, sat, bri = result
        assert approx(hue, expected_hue), (red, green, blue, hue)
        assert approx(sat, 1.0)
        assert approx(bri, 1.0)


def test_rgb_to_hsb_returns_zero_hue_for_grey() -> None:
    # Grey has no hue, but it is a perfectly valid colour - returning None here would make the
    # driver report a read failure for a white wall (see the function's own failure-mode list).
    for level in (0.0, 0.25, 1.0):
        result = mh.rgb_to_hsb(level, level, level)
        assert result is not None
        hue, sat, bri = result
        assert hue == 0.0
        assert sat == 0.0
        assert approx(bri, level)


def test_rgb_to_hsb_hue_is_always_inside_the_circle() -> None:
    # The wrap happens exactly once, at the end - a value of exactly 360.0 would be a defect.
    for step in range(101):
        frac = step * 0.01
        result = mh.rgb_to_hsb(1.0, frac, 0.0)
        assert result is not None
        assert 0.0 <= result[0] < 360.0


def test_rgb_to_hsb_hue_rotates_monotonically_with_the_input() -> None:
    # Sweeping green up against a fixed full red walks hue from 0 to 60 without ever going back.
    previous = -1.0
    for step in range(51):
        result = mh.rgb_to_hsb(1.0, step * 0.02, 0.0)
        assert result is not None
        assert result[0] >= previous
        previous = result[0]
    assert approx(previous, 60.0)


def test_rgb_to_hsb_none_in_each_argument() -> None:
    assert mh.rgb_to_hsb(None, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, None, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 0.5, None) is None


def test_rgb_to_hsb_rejects_out_of_range_and_nan() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.rgb_to_hsb(-0.001, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 1.001, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 0.5, 2.0) is None
    # NaN compares false against everything, so the range gate is what catches it - and it has to
    # run before the max/min, which would otherwise silently pick the wrong branch.
    assert mh.rgb_to_hsb(nan, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(0.5, nan, 0.5) is None
    assert mh.rgb_to_hsb(0.5, 0.5, nan) is None
    assert mh.rgb_to_hsb(inf, 0.5, 0.5) is None
    assert mh.rgb_to_hsb(-inf, 0.5, 0.5) is None


def test_rgb_to_hsb_boundary_values_accepted() -> None:
    assert mh.rgb_to_hsb(0.0, 0.0, 0.0) is not None
    assert mh.rgb_to_hsb(1.0, 1.0, 1.0) is not None


# ---------------------------------------------------------------------------
# rgb_to_xyz - M2
# ---------------------------------------------------------------------------


def test_rgb_to_xyz_reproduces_the_matrix_columns_for_pure_primaries() -> None:
    # A pure primary at 1.0 selects exactly one matrix column, so these three calls read the
    # whole 3x3 back out - the shape check that catches a transposed or mis-indexed multiply.
    red = mh.rgb_to_xyz(1.0, 0.0, 0.0)
    green = mh.rgb_to_xyz(0.0, 1.0, 0.0)
    blue = mh.rgb_to_xyz(0.0, 0.0, 1.0)
    assert red is not None and green is not None and blue is not None
    assert approx(red[0], 0.4124564) and approx(red[1], 0.2126729) and approx(red[2], 0.0193339)
    assert approx(green[0], 0.3575761) and approx(green[1], 0.7151522) and approx(green[2], 0.1191920)
    assert approx(blue[0], 0.1804375) and approx(blue[1], 0.0721750) and approx(blue[2], 0.9503041)


def test_rgb_to_xyz_coefficients_are_the_pinned_literals() -> None:
    # Exact equality, not approx(): two published roundings of this same matrix differ in the
    # 6th decimal (the CSS WG corrected its own once, see ISL29125_FUNCTION_SPEC.md section 5.3),
    # and both would pass a 1e-6 tolerance. The driver's constants are const()-folded and so are
    # not readable as module attributes - reading them back through a pure primary is the only
    # way to pin them, and it pins the wiring at the same time.
    assert mh.rgb_to_xyz(1.0, 0.0, 0.0) == (0.4124564, 0.2126729, 0.0193339)
    assert mh.rgb_to_xyz(0.0, 1.0, 0.0) == (0.3575761, 0.7151522, 0.1191920)
    assert mh.rgb_to_xyz(0.0, 0.0, 1.0) == (0.1804375, 0.0721750, 0.9503041)


def test_rgb_to_xyz_is_all_zero_for_black() -> None:
    result = mh.rgb_to_xyz(0.0, 0.0, 0.0)
    assert result == (0.0, 0.0, 0.0)


def test_rgb_to_xyz_applies_no_gamma_decode() -> None:
    # The sensor output is linear in irradiance, so the sRGB transfer function must NOT be
    # applied - half input must give exactly half output, which a gamma decode would not.
    full = mh.rgb_to_xyz(1.0, 1.0, 1.0)
    half = mh.rgb_to_xyz(0.5, 0.5, 0.5)
    assert full is not None and half is not None
    # No strict= (ruff B905): MicroPython's zip() rejects it, and both tuples are length 3
    for a, b in zip(full, half):  # noqa: B905
        assert approx(a * 0.5, b)


def test_rgb_to_xyz_none_in_each_argument() -> None:
    assert mh.rgb_to_xyz(None, 0.5, 0.5) is None
    assert mh.rgb_to_xyz(0.5, None, 0.5) is None
    assert mh.rgb_to_xyz(0.5, 0.5, None) is None


def test_rgb_to_xyz_rejects_out_of_range_and_nan() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.rgb_to_xyz(-0.001, 0.5, 0.5) is None
    assert mh.rgb_to_xyz(0.5, 1.001, 0.5) is None
    assert mh.rgb_to_xyz(nan, 0.5, 0.5) is None
    assert mh.rgb_to_xyz(0.5, inf, 0.5) is None
    assert mh.rgb_to_xyz(0.5, 0.5, -inf) is None


# ---------------------------------------------------------------------------
# chromaticity_xy - M3
# ---------------------------------------------------------------------------


def test_chromaticity_xy_returns_none_at_zero_sum() -> None:
    assert mh.chromaticity_xy(0.0, 0.0, 0.0) is None


def test_chromaticity_xy_refuses_just_below_the_sum_floor_and_accepts_just_above() -> None:
    # Mirrors the driver's own _CHROMA_SUM_MIN (const()-folded, so not readable from here) - the
    # floor is 1e-12 rather than 0.0 so a denormal can never produce a 1e300 chromaticity.
    floor = 1e-12
    assert mh.chromaticity_xy(floor * 0.3, floor * 0.3, floor * 0.3) is None
    assert mh.chromaticity_xy(floor, floor, floor) is not None


def test_chromaticity_xy_matches_d65_for_a_known_vector() -> None:
    # An external check, not a self-consistent one: the sRGB matrix's own white point is D65, so
    # an equal-energy RGB triple has to land on D65's published (0.3127, 0.3290).
    xyz = mh.rgb_to_xyz(1.0, 1.0, 1.0)
    assert xyz is not None
    result = mh.chromaticity_xy(xyz[0], xyz[1], xyz[2])
    assert result is not None
    assert approx(result[0], 0.3127, 5e-4)
    assert approx(result[1], 0.3290, 5e-4)


def test_chromaticity_xy_rejects_a_negative_sum() -> None:
    assert mh.chromaticity_xy(-1.0, -1.0, -1.0) is None


def test_chromaticity_xy_none_in_each_argument() -> None:
    assert mh.chromaticity_xy(None, 1.0, 1.0) is None
    assert mh.chromaticity_xy(1.0, None, 1.0) is None
    assert mh.chromaticity_xy(1.0, 1.0, None) is None


def test_chromaticity_xy_rejects_nan_and_inf() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.chromaticity_xy(nan, 1.0, 1.0) is None
    assert mh.chromaticity_xy(1.0, inf, 1.0) is None
    assert mh.chromaticity_xy(1.0, 1.0, -inf) is None


# ---------------------------------------------------------------------------
# cct_mccamy - M4
# ---------------------------------------------------------------------------


def test_cct_mccamy_matches_two_published_illuminants() -> None:
    # External checks: CIE Illuminant A is 2856 K at (0.4476, 0.4074), D65 is 6504 K at
    # (0.3127, 0.3290) - McCamy's own cubic is fitted to reproduce both to within a few kelvin.
    a_result = mh.cct_mccamy(0.4476, 0.4074)
    d65_result = mh.cct_mccamy(0.3127, 0.3290)
    assert a_result is not None and d65_result is not None
    assert abs(a_result - 2856.0) < 5.0
    assert abs(d65_result - 6504.0) < 10.0


def test_cct_mccamy_agrees_with_the_sign_flipped_published_form() -> None:
    # Two forms of the same formula are in circulation and differ only in the denominator's sign
    # (which flips n, and therefore the sign of every odd-power term). They are algebraically
    # identical; this pins that, so nobody "corrects" one into the other believing it a fix.
    for chroma_x, chroma_y in ((0.3127, 0.3290), (0.4476, 0.4074), (0.35, 0.30), (0.35, 0.36)):
        mine = mh.cct_mccamy(chroma_x, chroma_y)
        n = (chroma_x - 0.3320) / (chroma_y - 0.1858)
        theirs = -449.0 * n**3 + 3525.0 * n**2 - 6823.3 * n + 5520.33
        assert mine is not None
        assert approx(mine, theirs, 1e-6)


def test_cct_mccamy_returns_none_at_the_epicentre() -> None:
    # y == 0.1858 is a real division by zero, not a theoretical one - it is a plausible
    # chromaticity, so this is a guard, not defensive decoration.
    assert mh.cct_mccamy(0.3320, 0.1858) is None
    assert mh.cct_mccamy(0.45, 0.1858) is None


def test_cct_mccamy_is_finite_either_side_of_the_epicentre() -> None:
    # Just outside the epsilon the formula is enormous, so the span rejection below is what
    # actually makes these None - either way, no raise and no inf.
    assert mh.cct_mccamy(0.45, 0.1858 + 1e-4) is None
    assert mh.cct_mccamy(0.45, 0.1858 - 1e-4) is None


def test_cct_mccamy_rejects_outside_the_valid_span() -> None:
    # Rejected, not clamped: a clamped 12500 would be indistinguishable from a real 12500.
    low = mh.cct_mccamy(0.60, 0.35)  # deep red - below McCamy's usable span
    high = mh.cct_mccamy(0.20, 0.20)  # far blue - above it
    assert low is None
    assert high is None


def test_cct_mccamy_none_in_each_argument() -> None:
    assert mh.cct_mccamy(None, 0.33) is None
    assert mh.cct_mccamy(0.33, None) is None


def test_cct_mccamy_rejects_out_of_range_and_nan() -> None:
    nan = float("nan")
    inf = float("inf")
    assert mh.cct_mccamy(-0.1, 0.33) is None
    assert mh.cct_mccamy(1.1, 0.33) is None
    assert mh.cct_mccamy(0.33, nan) is None
    assert mh.cct_mccamy(inf, 0.33) is None


# ---------------------------------------------------------------------------
# ema_step - M5 (SPECIFICATION.md Part G.2 shared primitive)
# ---------------------------------------------------------------------------


def test_ema_step_is_a_passthrough_when_disabled() -> None:
    # <= 0 means "filter off" - the legacy SHTC3/MPRLS convention FiltCoeff = -1.0 relies on.
    assert mh.ema_step(10.0, 20.0, 0.0) == 20.0
    assert mh.ema_step(10.0, 20.0, -1.0) == 20.0


def test_ema_step_treats_a_coefficient_above_one_as_off() -> None:
    # Defence in depth: the schema already bounds FiltCoeff to [-1.0, 1.0], but a coefficient
    # above 1 makes the filter overshoot and ring, so it is refused rather than applied.
    assert mh.ema_step(10.0, 20.0, 1.5) == 20.0
    assert mh.ema_step(10.0, 20.0, None) == 20.0


def test_ema_step_seeds_from_none() -> None:
    assert mh.ema_step(None, 7.5, 0.1) == 7.5


def test_ema_step_returns_none_for_a_none_sample() -> None:
    # Nothing to filter, and the caller must not advance its stored state from it.
    assert mh.ema_step(10.0, None, 0.1) is None
    assert mh.ema_step(None, None, 0.1) is None


def test_ema_step_never_stores_a_nan() -> None:
    # The nastiest failure mode this function has: one NaN sample would otherwise poison
    # `previous` for the lifetime of the task, making every later output NaN.
    nan = float("nan")
    assert mh.ema_step(10.0, nan, 0.1) is None
    # A previous that is somehow already NaN reseeds from the sample rather than staying poisoned.
    reseeded = mh.ema_step(nan, 5.0, 0.1)
    assert reseeded == 5.0


def test_ema_step_applies_the_first_order_formula() -> None:
    assert approx(mh.ema_step(10.0, 20.0, 0.25), 12.5)  # type: ignore[arg-type]
    assert approx(mh.ema_step(0.0, 1.0, 1.0), 1.0)  # type: ignore[arg-type]


def test_ema_step_converges_to_a_constant_input() -> None:
    value: float | None = 0.0
    for _ in range(200):
        value = mh.ema_step(value, 26.67, 0.1)
    assert value is not None
    assert approx(value, 26.67, 1e-6)


def test_ema_step_rejects_an_infinite_sample() -> None:
    inf = float("inf")
    assert mh.ema_step(10.0, inf, 0.1) is None
    assert mh.ema_step(10.0, -inf, 0.1) is None



if __name__ == "__main__":
    import microtest

    microtest.run(globals())
