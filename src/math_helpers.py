"""Derived physical quantities from raw sensor readings: meteorological (wet-bulb temperature, dew
point, barometric correction, humidity conversions), colorimetric (RGB->HSB, RGB->XYZ->xy, McCamy CCT), plus the project's one first-order EMA (SPECIFICATION.md Part G.2).
Every function returns None - never raises - for a None, out-of-domain, or NaN input (see each function's own comment for its range/source).
"""

import math

from micropython import const

# Per-function input-domain bounds, named here rather than inline at each comparison; each
# function's own comment carries the source/rationale for its range. const() + a leading
# underscore keeps them compile-time-inlined, so naming them costs no RAM on-device.
_WB_T_MIN = const(-20.0)
_WB_T_MAX = const(50.0)
_WB_RH_MIN = const(5.0)
_WB_RH_MAX = const(99.0)
_DP_T_MIN = const(-40.0)
_DP_T_MAX = const(50.0)
_DP_RH_MIN = const(0.1)
_DP_RH_MAX = const(100.0)
_BARO_P_MIN = const(300.0)
_BARO_P_MAX = const(1250.0)
_BARO_DH_MIN = const(-9000.0)
_BARO_DH_MAX = const(9000.0)
_BARO_T_MIN = const(-40.0)
_BARO_T_MAX = const(85.0)
_MAGNUS_T_MIN = const(-30.0)
_MAGNUS_T_MAX = const(40.0)
_MAGNUS_RH_MAX = const(100.0)
_MAGNUS_AH_MAX = const(100.0)
# Colour-chain domains. The RGB triples these take are already normalised 0-1 by the driver's own
# scaling chain (SPECIFICATION.md Part M.1.3), so anything outside means that chain is
# broken, not that the light was unusual - hence a reject rather than a clamp.
_COLOUR_IN_MIN = const(0.0)
_COLOUR_IN_MAX = const(1.0)
# 1e-12 rather than 0.0: a denormal X+Y+Z would otherwise divide out to a ~1e300 chromaticity.
# The upper bound is what rejects +-inf (and, through the sum, a NaN in any single component).
_CHROMA_SUM_MIN = const(1e-12)
_CHROMA_SUM_MAX = const(1e9)
_CCT_EPICENTRE_EPS = const(1e-9)  # McCamy's n diverges at y = 0.1858 - a plausible chromaticity
_CCT_MIN = const(2000.0)  # McCamy (1992) fits the Planckian locus over roughly 2000-12500 K;
_CCT_MAX = const(12500.0)  # outside it the cubic still returns a number, with nothing marking it meaningless


def wet_bulb_temperature(temperature: float | None, humidity: float | None) -> float | None:
    # Stull (2011) empirical wet-bulb approximation. Valid domain per the paper: -20-50 degC,
    # 5-99% RH (errors grow sharply outside it, especially at low RH + low temperature together).
    if temperature is None or humidity is None:
        return None
    if not (_WB_T_MIN <= temperature <= _WB_T_MAX and _WB_RH_MIN <= humidity <= _WB_RH_MAX):
        return None
    try:
        return (
            temperature * math.atan(0.151977 * math.sqrt(humidity + 8.313659))
            + math.atan(temperature + humidity)
            - math.atan(humidity - 1.676331)
            + 0.00391838 * humidity * math.sqrt(humidity) * math.atan(0.023101 * humidity)
            - 4.686035
        )
    except (ValueError, ArithmeticError):
        return None


def dew_point(temperature: float | None, humidity: float | None) -> float | None:
    # Magnus-Tetens approximation: water branch (temperature >= 0) uses Alduchov & Eskridge's
    # (1996) refit (17.625/243.04), ice branch uses Sonntag (1990) (22.46/272.62) - independently
    # fit curves, ~1 degC apart at the switch (see test_dew_point_branch_boundary_roughly_continuous).
    if temperature is None or humidity is None:
        return None
    if not (_DP_T_MIN <= temperature <= _DP_T_MAX and _DP_RH_MIN <= humidity <= _DP_RH_MAX):
        return None
    if temperature >= 0:
        toffs = 243.04
        coeff1 = 17.625
    else:
        toffs = 272.62
        coeff1 = 22.46
    try:
        loghum = math.log(humidity * 0.01)
        coeff2 = 1.0 / (toffs + temperature)
        return toffs * ((coeff1 * temperature) * coeff2 + loghum) / ((coeff1 * toffs) * coeff2 - loghum)
    except (ValueError, ArithmeticError):
        return None


def altitude_baro(p0: float | None, dh: float | None, tmean: float | None) -> float | None:
    # Barometric formula: pressure at height offset dh from the p0 reference (callers pass a
    # negative dh to reduce a station reading to sea-level-equivalent pressure, not an altitude).
    # p0/tmean range matches the BMP388/390 datasheet (its only caller).
    if p0 is None or dh is None or tmean is None:
        return None
    if not (_BARO_P_MIN <= p0 <= _BARO_P_MAX and _BARO_DH_MIN <= dh <= _BARO_DH_MAX and _BARO_T_MIN <= tmean <= _BARO_T_MAX):
        return None
    try:
        # Inlined below: g 9.80665 m/s2, M 0.0289644 kg/mol, T0 273.15 K, R 8.31446261815324 J/(mol K)
        return p0 * math.exp(-dh * ((0.0289644 * 9.80665) / (8.31446261815324 * (tmean + 273.15))))
    except (ValueError, ArithmeticError):
        return None


def abs_humidity(temperature: float | None, humidity: float | None) -> float | None:
    # Magnus-type saturation-vapor-pressure formula; a/b pick the ice- vs water-phase constants.
    if temperature is None or humidity is None:
        return None
    if not (_MAGNUS_T_MIN <= temperature <= _MAGNUS_T_MAX and 0.0 <= humidity <= _MAGNUS_RH_MAX):
        return None
    if temperature >= 0.0:
        a = 7.5
        b = 237.4
    else:
        a = 7.6
        b = 240.7
    try:
        return 13.23454 * humidity / (temperature + 273.15) * math.pow(10.0, (a * temperature) / (b + temperature))
    except (ValueError, ArithmeticError):
        return None


def rel_humidity(temperature: float | None, abs_hum: float | None) -> float | None:
    # Inverse of abs_humidity's Magnus-type formula; result is clamped to the valid 0-100% range.
    # abs_hum is upper-bounded generously above abs_humidity's own max output (~51 g/m3 at the
    # top of its domain, 40 degC/100% RH) purely to reject negative/nonsensical input.
    if temperature is None or abs_hum is None:
        return None
    if not (_MAGNUS_T_MIN <= temperature <= _MAGNUS_T_MAX and 0.0 <= abs_hum <= _MAGNUS_AH_MAX):
        return None
    if temperature >= 0.0:
        a = 7.5
        b = 237.4
    else:
        a = 7.6
        b = 240.7
    try:
        rh = abs_hum * (temperature + 273.15) / (13.23454 * math.pow(10.0, (a * temperature) / (b + temperature)))
    except (ValueError, ArithmeticError):
        return None
    return max(0.0, min(100.0, rh))


def rgb_to_hsb(red: float | None, green: float | None, blue: float | None) -> "tuple[float, float, float] | None":
    # Standard HSV/HSB hexcone over a normalised 0-1 triple: hue in [0, 360), S and B in [0, 1].
    # Returns a tuple, unlike the rest of this file, because all three derive from one max/min and
    # separate entry points could disagree. The range gate also catches NaN, which compares false.
    if red is None or green is None or blue is None:
        return None
    if not (_COLOUR_IN_MIN <= red <= _COLOUR_IN_MAX and _COLOUR_IN_MIN <= green <= _COLOUR_IN_MAX and _COLOUR_IN_MIN <= blue <= _COLOUR_IN_MAX):
        return None
    bri = max(red, green, blue)
    chroma = bri - min(red, green, blue)
    if chroma == 0.0:  # grey is a valid colour with no hue - None here would be a read failure
        return 0.0, 0.0, bri
    if bri == red:
        hue = 60.0 * (((green - blue) / chroma) % 6.0)
    elif bri == green:
        hue = 60.0 * ((blue - red) / chroma + 2.0)
    else:
        hue = 60.0 * ((red - green) / chroma + 4.0)
    hue %= 360.0  # wrapped exactly once, here, so no branch above has to get it right
    return hue, chroma / bri, bri


def rgb_to_xyz(red: float | None, green: float | None, blue: float | None) -> "tuple[float, float, float] | None":
    # sRGB/Rec.709 D65 primaries, pinned as literals: a second published rounding differs in the
    # 6th decimal, so these must not be "corrected" (Part M.1.3). No gamma decode - this sensor is
    # linear in irradiance. A documented PLACEHOLDER: p13 Eq. 1 says the coefficients are per-setup.
    if red is None or green is None or blue is None:
        return None
    if not (_COLOUR_IN_MIN <= red <= _COLOUR_IN_MAX and _COLOUR_IN_MIN <= green <= _COLOUR_IN_MAX and _COLOUR_IN_MIN <= blue <= _COLOUR_IN_MAX):
        return None
    x_val = 0.4124564 * red + 0.3575761 * green + 0.1804375 * blue
    y_val = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z_val = 0.0193339 * red + 0.1191920 * green + 0.9503041 * blue
    return x_val, y_val, z_val


def chromaticity_xy(x_val: float | None, y_val: float | None, z_val: float | None) -> "tuple[float, float] | None":
    # CIE 1931 chromaticity, the step that makes CCT range- and resolution-invariant: any common
    # scale factor cancels. The single windowed sum test rejects darkness, a negative sum, +-inf and
    # NaN at once. The low-light POLICY floor is a device fact and lives in the driver, in counts.
    if x_val is None or y_val is None or z_val is None:
        return None
    total = x_val + y_val + z_val
    if not (_CHROMA_SUM_MIN <= total <= _CHROMA_SUM_MAX):
        return None
    return x_val / total, y_val / total


def cct_mccamy(chroma_x: float | None, chroma_y: float | None) -> float | None:
    # McCamy (1992) cubic CCT from CIE 1931 chromaticity. The circulated sign-flipped form -
    # n = (x - 0.3320)/(y - 0.1858) with -449/+3525/-6823.3 - is algebraically the same function.
    # Out-of-span results are REJECTED, not clamped: a clamped 12500 would look like a real one.
    if chroma_x is None or chroma_y is None:
        return None
    if not (_COLOUR_IN_MIN <= chroma_x <= _COLOUR_IN_MAX and _COLOUR_IN_MIN <= chroma_y <= _COLOUR_IN_MAX):
        return None
    denominator = 0.1858 - chroma_y
    if abs(denominator) < _CCT_EPICENTRE_EPS:  # the epicentre is a real division by zero here
        return None
    n_val = (chroma_x - 0.3320) / denominator
    cct = 449.0 * n_val**3 + 3525.0 * n_val**2 + 6823.3 * n_val + 5520.33
    if not (_CCT_MIN <= cct <= _CCT_MAX):
        return None
    return cct


def ema_step(previous: float | None, sample: float | None, coefficient: float | None) -> float | None:
    # The project's single first-order EMA (Part G.2), promoted from the legacy SHTC3/MPRLS
    # readers. A coefficient outside (0, 1] means "filter off", the convention FiltCoeff = -1.0
    # relies on. isfinite(), not a range gate: one NaN would poison the caller's state for good.
    if sample is None or not math.isfinite(sample):
        return None
    if coefficient is None or not (0.0 < coefficient <= 1.0):  # a NaN coefficient lands here too
        return sample
    if previous is None or not math.isfinite(previous):  # unseeded, or an already-poisoned state
        return sample
    return previous + coefficient * (sample - previous)
