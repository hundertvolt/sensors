"""Isolated-driver device script, phase 1/2: writes a real ConfigManager-backed value to a dedicated
test-only config file, then the host triggers a genuine machine.reset() and reboot_persist_read.py
confirms it survived. Must flush before returning - write_config() only stages (see _main)."""

import asyncio

import config_manager as cm

_SCHEMA: "cm.ConfigSchema" = (("Marker", "int", 0, 0, 999999999, None),)
_PATH = "config_HWTEST_REBOOT.cfg"
_MARKER_VALUE = 424242


async def _main() -> None:
    mgr = cm.ConfigManager(_PATH, _SCHEMA, "HWTEST")
    await mgr.setup()
    ok, _validity = await mgr.write_config({"Marker": _MARKER_VALUE}, _SCHEMA)
    if not ok:
        print(f"RESULT: FAIL write_config() reported failure for Marker={_MARKER_VALUE}")
        return
    # write_config() stages and spawns the flash write as its own task (Part F.2); nothing here
    # awaits anything afterwards, so asyncio.run() would tear the loop down with the flush still
    # queued and the value would never reach flash at all.
    await mgr.flush_pending()
    print(f"RESULT: PASS wrote and flushed Marker={_MARKER_VALUE} to {_PATH}")


asyncio.run(_main())
