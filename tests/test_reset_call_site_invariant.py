"""Regression test for CLAUDE.md's/BACKLOG.md's reset invariant: every deliberate reset goes through SystemService._reboot() (pauses FRAM first, then waits) and WDT() is constructed exactly once, hardcoded, in each device's own sensortask_<device>.py entry-point file (e.g. sensortask_wozi.py, sensortask_dev.py) -
a new call site anywhere else would reintroduce a not-paused-first reset race or a circumventable watchdog."""

import os

_SRC_DIR = "src"  # scripts/test.sh always invokes tests from the repo root, like every other test file's own _TMP_DIR = "tests/_tmp" convention


def _src_files() -> "list[str]":
    return sorted(f for f in os.listdir(_SRC_DIR) if f.endswith(".py"))


def test_reset_and_bootloader_calls_confined_to_system_service() -> None:
    # machine.reset()/machine.bootloader() are imported in system_service.py as system_reset/
    # system_bootloader and called only from _reboot()'s own action callbacks - any other call site
    # would bypass storage_pause()/the _RESET_DELAY wait this invariant relies on.
    offenders = []
    for filename in _src_files():
        if filename == "system_service.py":
            continue
        with open(_SRC_DIR + "/" + filename) as f:
            source = f.read()
        if any(needle in source for needle in ("system_reset(", "system_bootloader(", "machine.reset(", "machine.bootloader(")):
            offenders.append(filename)
    assert offenders == []


def test_wdt_constructed_only_in_sensortask_entry_point_files() -> None:
    # "must be hardcoded so no error ever can circumvent it when it is set active" - own comment
    # on the sanctioned WDT() construction sites: each device's own sensortask_<device>.py
    # entry-point file (sensortask_wozi.py, sensortask_dev.py, ... - DEV_HARDWARE_BASELINE_PLAN.md
    # decision 5 extended this from a single hardcoded site to "one per device", same hardcoded-
    # no-injection-point contract, just once per device instead of once repo-wide). A WDT()
    # construction anywhere else in src/ (a shared driver/service module) would be a real,
    # deployed-firmware-breaking regression, not a style nit.
    offenders = []
    for filename in _src_files():
        if filename.startswith("sensortask_") and filename.endswith(".py"):
            continue
        with open(_SRC_DIR + "/" + filename) as f:
            source = f.read()
        if "WDT(" in source:
            offenders.append(filename)
    assert offenders == []


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
