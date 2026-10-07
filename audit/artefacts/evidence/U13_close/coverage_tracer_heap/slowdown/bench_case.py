import time
import sys
import math_helpers
t = time.ticks_ms()
for i in range(20000):
    math_helpers.dew_point(20.0, 50.0)
print("BENCH ms", time.ticks_diff(time.ticks_ms(), t))
sys.exit(0)
