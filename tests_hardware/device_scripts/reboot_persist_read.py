"""Isolated-driver device script, phase 2/2 for flash-tier candidate C.13 - see
reboot_persist_write.py's own docstring for the full design. Run after a genuine machine.reset()
(not soft_reset) following that script. Constructs a fresh ConfigManager against the exact same
config_HWTEST_REBOOT.cfg/schema and confirms the marker value written before the reboot is still
there - the real write_config() -> real littlefs -> a fresh ConfigManager.setup() read path,
exercised across a genuine reboot, not just a raw file peek."""

import asyncio

import config_manager as cm

_SCHEMA: "cm.ConfigSchema" = (("Marker", "int", 0, 0, 999999999, None),)
_PATH = "config_HWTEST_REBOOT.cfg"
_EXPECTED_MARKER_VALUE = 424242


async def _main() -> None:
    mgr = cm.ConfigManager(_PATH, _SCHEMA, "HWTEST")
    await mgr.setup()
    if not mgr.valid:
        print(f"RESULT: FAIL {_PATH} did not load as valid after reboot - config_manager.setup() rejected it")
        return
    result = await mgr.get_dict(["Marker"])
    if result is None:
        print("RESULT: FAIL get_dict(['Marker']) returned None after reboot")
    elif result.get("Marker") != _EXPECTED_MARKER_VALUE:
        print(f"RESULT: FAIL Marker={result.get('Marker')!r} after reboot, expected {_EXPECTED_MARKER_VALUE}")
    else:
        print(f"RESULT: PASS Marker={result['Marker']} survived a genuine machine.reset()")


asyncio.run(_main())
