"""Named soak-test duration tiers for --soak-tier and every @pytest.mark.long_soak test. Standalone
module, not inline in conftest.py, because a subdirectory's own conftest.py (e.g. flash/) shadows a
bare `from conftest import ...` - confirmed directly via a real ImportError on first collection."""

# @tunable l4.soak_duration_short_s = 60.0
# @tunable l4.soak_duration_mid_s = 600.0
# @tunable l4.soak_duration_long_h = 6
SOAK_TIER_SECONDS = {"short": 60.0, "mid": 600.0, "long": 6 * 3600.0}
