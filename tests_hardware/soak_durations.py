"""Named soak durations for --soak-duration and every soak_duration test; its own module because a
subdirectory's conftest.py shadows a bare `from conftest import ...`."""

# @tunable l4.soak_duration_short_s = 60.0
# @tunable l4.soak_duration_mid_s = 600.0
# @tunable l4.soak_duration_long_h = 6
SOAK_DURATION_SECONDS = {"short": 60.0, "mid": 600.0, "long": 6 * 3600.0}
