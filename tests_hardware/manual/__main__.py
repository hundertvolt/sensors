"""Real entry point for the manual-test runner - run this file, never runner.py directly. Running
runner.py directly creates a second `runner` module instance with its own empty `_REGISTRY`,
silently no-op'ing every registered test (see tests_hardware/README.md for the full account)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner

if __name__ == "__main__":
    sys.exit(runner.main())
