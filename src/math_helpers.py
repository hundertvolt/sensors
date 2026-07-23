"""Derived meteorological quantities from raw sensor readings (wet-bulb temperature, dew point,
barometric pressure correction, absolute/relative humidity conversions).

Shared contract for every function here: returns None - never raises - if an input is None, is
outside the formula's validated domain (see each function's own comment for its range and
source), or if the computation fails for any other reason (e.g. a NaN slipping through a sensor
read). Assumes callers pass the annotated types (float | None) - MicroPython doesn't enforce this
at runtime, but mypy does at every call site, so this module doesn't duplicate that check itself.
This is deliberate for unattended, long-running operation: a transient bad reading from a sensor
must degrade to "no value this cycle," not take down the calling task.
"""

import math


def wet_bulb_temperature(temperature: float | None, humidity: float | None) -> float | None:
    # Stull (2011) empirical wet-bulb approximation. Valid domain per the paper: -20-50 degC,
    # 5-99% RH (errors grow sharply outside it, especially at low RH + low temperature together).
    if temperature is None or humidity is None:
        return None
    if not (-20.0 <= temperature <= 50.0 and 5.0 <= humidity <= 99.0):
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
    # Magnus-Tetens dew-point approximation (Sonntag 1990); coeff1/toffs pick the ice- vs
    # water-phase constants. The two branches are independently-fit curves, not one continuous
    # formula - they disagree by ~1 degC right at the temperature==0 switch; not a bug, see BACKLOG.md.
    if temperature is None or humidity is None:
        return None
    if not (-40.0 <= temperature <= 50.0 and 0.1 <= humidity <= 100.0):
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
    # p0/tmean range matches the BMP388/390 datasheet (its only caller); see BACKLOG.md.
    if p0 is None or dh is None or tmean is None:
        return None
    if not (300.0 <= p0 <= 1250.0 and -9000.0 <= dh <= 9000.0 and -40.0 <= tmean <= 85.0):
        return None
    try:
        return p0 * math.exp(-dh * ((0.0289644 * 9.80665) / (8.31446261815324 * (tmean + 273.15))))
    except (ValueError, ArithmeticError):
        return None
    # g = 9.80665; M = 0.0289644; T0 = 273.15; R = 8.31446261815324


def abs_humidity(temperature: float | None, humidity: float | None) -> float | None:
    # Magnus-type saturation-vapor-pressure formula; a/b pick the ice- vs water-phase constants.
    if temperature is None or humidity is None:
        return None
    if not (-30.0 <= temperature <= 40.0 and 0.0 <= humidity <= 100.0):
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
    if not (-30.0 <= temperature <= 40.0 and 0.0 <= abs_hum <= 100.0):
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
