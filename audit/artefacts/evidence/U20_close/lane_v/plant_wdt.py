import sys
from pathlib import Path
root = Path(sys.argv[1]); sys.path[:0] = [str(root), str(root / "tests_scripts")]
import pytest
sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", str(root / "tests_scripts/test_buildgen_validate.py"), "-k", "watchdog_the_budget", "-p", "plant_wdt_plugin"]))
