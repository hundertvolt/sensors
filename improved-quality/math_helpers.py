import math


def wet_bulb_temperature(temperature: float | None, humidity: float | None) -> float | None:
    # Stull's empirical wet-bulb approximation; valid only within the range checked below.
    if (temperature is None) or (humidity is None):
        return None
    tw = None
    if (-20.0 <= temperature <= 50.0) and (0.5 <= humidity <= 99.0):
        tw = (
            temperature * math.atan(0.151977 * math.pow(humidity + 8.313659, 0.5))
            + math.atan(temperature + humidity)
            - math.atan(humidity - 1.676331)
            + 0.00391838 * math.pow(humidity, 3.0 / 2.0) * math.atan(0.023101 * humidity)
            - 4.686035
        )
    return tw


def dew_point(temperature: float | None, humidity: float | None) -> float | None:
    # Magnus-Tetens dew-point approximation; coeff1/toffs pick the ice- vs water-phase constants.
    if (temperature is None) or (humidity is None):
        return None
    dp = None
    if (-40.0 <= temperature <= 50.0) and (0.1 <= humidity <= 100.0):
        loghum = math.log(humidity * 0.01)
        if temperature >= 0:
            toffs = 243.04
            coeff1 = 17.625
        else:
            toffs = 272.62
            coeff1 = 22.46
        coeff2 = 1.0 / (toffs + temperature)
        dp = (
            toffs
            * ((coeff1 * temperature) * coeff2 + loghum)
            / ((coeff1 * toffs) * coeff2 - loghum)
        )
    return dp


def altitude_baro(p0: float | None, dh: float | None, tmean: float | None) -> float | None:
    # Barometric formula: pressure at height offset dh from the p0 reference (callers pass a
    # negative dh to reduce a station reading to sea-level-equivalent pressure), not an altitude.
    if (p0 is None) or (dh is None) or (tmean is None):
        return None
    return p0 * math.exp(-dh * ((0.0289644 * 9.80665) / (8.31446261815324 * (tmean + 273.15))))
    # g = 9.80665; M = 0.0289644; T0 = 273.15; R = 8.31446261815324


def abs_humidity(temperature: float | None, humidity: float | None) -> float | None:
    # Magnus-type saturation-vapor-pressure formula; a/b pick the ice- vs water-phase constants.
    if (temperature is None) or (humidity is None):
        return None
    ah = None
    if (-30.0 <= temperature <= 40.0) and (0.0 <= humidity <= 100.0):
        if temperature >= 0.0:
            a = 7.5
            b = 237.4
        else:
            a = 7.6
            b = 240.7
        ah = (
            13.23454
            * humidity
            / (temperature + 273.15)
            * math.pow(10.0, (a * temperature) / (b + temperature))
        )
    return ah


def rel_humidity(temperature: float | None, abs_hum: float | None) -> float | None:
    # Inverse of abs_humidity's Magnus-type formula; result is clamped to the valid 0-100% range.
    if (temperature is None) or (abs_hum is None):
        return None
    rh = None
    if -30.0 <= temperature <= 40.0:
        if temperature >= 0.0:
            a = 7.5
            b = 237.4
        else:
            a = 7.6
            b = 240.7
        rh = (
            abs_hum
            * (temperature + 273.15)
            / (13.23454 * math.pow(10.0, (a * temperature) / (b + temperature)))
        )
        if rh > 100.0:
            rh = 100.0
        if rh < 0.0:
            rh = 0.0
    return rh
