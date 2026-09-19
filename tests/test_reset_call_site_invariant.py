"""Regression test: every reset goes through SystemService._reboot(), and WDT() is constructed
exactly once per sensortask_<device>.py entry point - a new call site elsewhere would reintroduce
a not-paused-first reset race or a circumventable watchdog."""

import os

_SRC_DIR = "src"  # scripts/test.sh always invokes tests from the repo root, like tests/_tmp_scratch.py's own "tests/_tmp" convention


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
    # "must be hardcoded so no error ever can circumvent it when it is set active" - the owner's comment on
    # the sanctioned WDT() construction sites, each device's own sensortask_<device>.py entry point.
    #
    # The dev-bench baseline work extended this from a single hardcoded site to one per device, the same no-
    # injection-point contract. A WDT() construction anywhere else in src/, in a shared driver or service
    # module, would be a real deployed-firmware-breaking regression, not a style nit.
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
