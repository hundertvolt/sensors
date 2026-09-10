"""Isolated-driver device script, phase 1/3 for the boot-import-mechanism check. Raises SYSTEM
DebugLevel to 3 (_LOG_ONCE) so the next hard_reset()'s boot-chatter lines actually emit - backs up
the real prior value first (never a hardcoded restore target) so its restore-phase sibling can put it back exactly."""

import asyncio

import config_manager as cm

_SYS_SCHEMA: "cm.ConfigSchema" = (("DebugLevel", "int", 0, 0, 5, None),)
_SYS_PATH = "config_SYSTEM.cfg"
_BACKUP_SCHEMA: "cm.ConfigSchema" = (("PrevLevel", "int", 0, 0, 5, None),)
_BACKUP_PATH = "config_HWTEST_DEBUGLEVEL_BACKUP.cfg"
_VERBOSE_LEVEL = 3  # print_log.py's _LOG_ONCE - the level pr.one() itself is gated on


async def _main() -> None:
    sys_mgr = cm.ConfigManager(_SYS_PATH, _SYS_SCHEMA, "SYSTEM")
    await sys_mgr.setup()
    current = await sys_mgr.get_dict(["DebugLevel"])
    if current is None or "DebugLevel" not in current:
        print("RESULT: FAIL could not read the current DebugLevel before changing it")
        return
    previous_level = current["DebugLevel"]
    if not isinstance(previous_level, int):  # get_dict() returns the config-value union; the schema says int
        print(f"RESULT: FAIL DebugLevel read back as {previous_level!r}, not an int")
        return

    backup_mgr = cm.ConfigManager(_BACKUP_PATH, _BACKUP_SCHEMA, "HWTEST")
    await backup_mgr.setup()
    backup_ok, _validity = await backup_mgr.write_config({"PrevLevel": previous_level}, _BACKUP_SCHEMA)
    if not backup_ok:
        print(f"RESULT: FAIL could not back up the current DebugLevel={previous_level} before changing it")
        return

    if previous_level >= _VERBOSE_LEVEL:
        print(f"RESULT: PASS DebugLevel already {previous_level} (>= {_VERBOSE_LEVEL}) - nothing to raise")
        return

    ok, validity = await sys_mgr.write_config({"DebugLevel": _VERBOSE_LEVEL}, _SYS_SCHEMA)
    if ok and validity.get("DebugLevel") in ("Valid", "Unchanged"):
        print(f"RESULT: PASS DebugLevel raised from {previous_level} to {_VERBOSE_LEVEL}")
    else:
        print(f"RESULT: FAIL write_config() reported {validity} for DebugLevel={_VERBOSE_LEVEL}")


asyncio.run(_main())
