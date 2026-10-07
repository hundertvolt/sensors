import gc
import sys
import math_helpers


def span_a() -> None:
    for _ in range(3):
        math_helpers.abs_humidity(20.0, 50.0)
        math_helpers.cct_mccamy(0.31, 0.32)
        math_helpers.chromaticity_xy(1.0, 2.0, 3.0)
        math_helpers.ema_step(1.0, 2.0, 0.5)


def span_b() -> None:
    for _ in range(3):
        math_helpers.pressure_at_height(1013.0, 100.0, 15.0)
        math_helpers.rel_humidity(20.0, 8.0)
        math_helpers.rgb_to_hsb(10.0, 20.0, 30.0)
        math_helpers.rgb_to_xyz(10.0, 20.0, 30.0)
        math_helpers.wet_bulb_temperature(20.0, 50.0)


def measured(span: object) -> int:
    gc.collect()
    before = gc.mem_alloc()
    span()  # type: ignore[operator]
    gc.collect()
    return gc.mem_alloc() - before


math_helpers.dew_point(20.0, 50.0)
print("GREW", measured(span_a), measured(span_b), measured(span_a), measured(span_b))
sys.exit(0)
