"""Generated build_system() construction and wiring scenarios for the device named by TEST_DEVICE - one job per
generated device, dispatched by scripts/test.sh (SPECIFICATION.md E.2.1)."""

import os

PER_DEVICE = True
device = os.getenv("TEST_DEVICE")
if not device:
    raise RuntimeError("run through scripts/test.sh, or set TEST_DEVICE to one of devices/*.toml")

from _sensortask_scenarios import register_for_device  # noqa: E402 - after the device guard, so a refusal has no side effect

globals().update(register_for_device(device))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
