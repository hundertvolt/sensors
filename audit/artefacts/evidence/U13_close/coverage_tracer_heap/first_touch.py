import gc
import sys
import math_helpers
math_helpers.dew_point(20.0, 50.0)
_ = 0  # every global the span binds exists before it, so the module dict cannot grow inside it
gc.collect()
before = gc.mem_alloc()
for _ in range(3):
    math_helpers.abs_humidity(20.0, 50.0)
    math_helpers.cct_mccamy(0.31, 0.32)
    math_helpers.chromaticity_xy(1.0, 2.0, 3.0)
    math_helpers.ema_step(1.0, 2.0, 0.5)
    math_helpers.pressure_at_height(1013.0, 100.0, 15.0)
    math_helpers.rel_humidity(20.0, 8.0)
    math_helpers.rgb_to_hsb(10.0, 20.0, 30.0)
    math_helpers.rgb_to_xyz(10.0, 20.0, 30.0)
    math_helpers.wet_bulb_temperature(20.0, 50.0)
gc.collect()
print("GREW", gc.mem_alloc() - before)
sys.exit(0)
