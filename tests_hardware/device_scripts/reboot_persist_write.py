"""Isolated-driver device script, phase 1/2, for flash-tier candidate C.13: writes a real
ConfigManager-backed value to a dedicated test-only config file (never a real driver's own file -
config_HWTEST_REBOOT.cfg collides with nothing in src/), then the host triggers a genuine
machine.reset() (see harness.Board.reset_via_machine_reset() - a real reboot, not
machine.soft_reset()) and reboot_persist_read.py (run after the board comes back) confirms the
written value survived on real littlefs. Deliberately a dedicated schema/file rather than reusing
any real driver's own config file or reaching into the live system's already-running object graph -
see this file's own module docstring in the test file that drives it
(tests_hardware/flash/test_reboot_persistence.py) for why. Run via `mpremote run <this>` with
soft_reset_after=False (the host must NOT soft-reset here - that would defeat the point immediately,
before the real hard reset even happens)."""

import asyncio

import config_manager as cm

_SCHEMA: "cm.ConfigSchema" = (("Marker", "int", 0, 0, 999999999, None),)
_PATH = "config_HWTEST_REBOOT.cfg"
_MARKER_VALUE = 424242


async def _main() -> None:
    mgr = cm.ConfigManager(_PATH, _SCHEMA, "HWTEST")
    await mgr.setup()
    ok, _validity = await mgr.write_config({"Marker": _MARKER_VALUE}, _SCHEMA)
    if ok:
        print(f"RESULT: PASS wrote Marker={_MARKER_VALUE} to {_PATH}")
    else:
        print(f"RESULT: FAIL write_config() reported failure for Marker={_MARKER_VALUE}")


asyncio.run(_main())
