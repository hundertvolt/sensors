"""Isolated-driver device script, phase 1/2: writes a real ConfigManager-backed value to a dedicated
test-only config file, then the host triggers a genuine machine.reset() and reboot_persist_read.py
confirms it survived. Run with soft_reset_after=False - that would defeat the point beforehand."""

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
