"""Named soak-test duration tiers, shared by tests_hardware/conftest.py's own --soak-tier option
and every @pytest.mark.long_soak test that needs the resulting duration. A standalone module
(not defined inline in conftest.py) specifically because a bare `import conftest`/`from conftest
import ...` from a test file living in a subdirectory that has its own conftest.py (e.g.
tests_hardware/flash/, which has its own SCD30 NVM-write-budget fixture file) resolves to THAT
local conftest.py instead of this package's - confirmed directly, not assumed (a real
ImportError: cannot import name 'SOAK_TIER_SECONDS' from 'conftest' on the first collection
attempt). harness.py/bench_control.py already establish this exact "flat module in tests_hardware/
itself, no naming collision" pattern - this follows it.

"short"/"mid" exist to actually exercise a soak test's own mechanism/assertions quickly (CI-time,
not a real leak-trend proof); "long" is the real multi-hour production duration the mechanism was
designed to catch a slow trend over. See scripts/run_bench_soak_tests.sh, the only intended way to
select one - soak tests always need their own deliberate, dedicated invocation, never bundled into
a general suite run (tests_hardware/conftest.py's own pytest_addoption() docstring)."""

from __future__ import annotations

SOAK_TIER_SECONDS = {"short": 60.0, "mid": 600.0, "long": 6 * 3600.0}
