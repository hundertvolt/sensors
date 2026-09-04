"""Isolated-driver device script, phase 3/3 for the boot-import-mechanism check - see
system_debug_level_raise_for_boot_log_check.py's own docstring for the full design. Restores the
real, persisted SYSTEM DebugLevel back to 0 (this project's production-quiet default) after that
script raised it and the intervening hard_reset()'s boot log was captured. Run from a `finally`
block in the driving test so a failed assertion never leaves the board's real config non-default."""

import asyncio

import config_manager as cm

_SCHEMA: "cm.ConfigSchema" = (("DebugLevel", "int", 0, 0, 5, None),)
_PATH = "config_SYSTEM.cfg"
_PRODUCTION_LEVEL = 0  # print_log.py's _LOG_OFF


async def _main() -> None:
    mgr = cm.ConfigManager(_PATH, _SCHEMA, "SYSTEM")
    await mgr.setup()
    ok, validity = await mgr.write_config({"DebugLevel": _PRODUCTION_LEVEL}, _SCHEMA)
    if ok and validity.get("DebugLevel") in ("Valid", "Unchanged"):
        print(f"RESULT: PASS DebugLevel restored to {_PRODUCTION_LEVEL}")
    else:
        print(f"RESULT: FAIL write_config() reported {validity} for DebugLevel={_PRODUCTION_LEVEL}")


asyncio.run(_main())
