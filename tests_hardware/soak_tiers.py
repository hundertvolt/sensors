"""Named soak-test duration tiers for --soak-tier and every @pytest.mark.long_soak test. Standalone
module, not inline in conftest.py, because a subdirectory's own conftest.py (e.g. flash/) shadows a
bare `from conftest import ...` - confirmed directly via a real ImportError on first collection."""

from __future__ import annotations

SOAK_TIER_SECONDS = {"short": 60.0, "mid": 600.0, "long": 6 * 3600.0}
