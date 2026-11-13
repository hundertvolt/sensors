"""Entry point of the manual mode: run this file, never runner.py directly - that makes a second `runner` module
instance with its own empty registry, so every test would silently not run (tests_hardware/README.md)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner  # first: it puts tests_hardware/ and scripts/ on the path the test modules import from

# isort: split
import manual_bus_electrical
import manual_persistence
import manual_sensor_accuracy
import manual_toolchain
import manual_wifi

if __name__ == "__main__":
    raise SystemExit(runner.main())
