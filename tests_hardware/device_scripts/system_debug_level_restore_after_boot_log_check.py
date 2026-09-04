"""Isolated-driver device script, phase 3/3 for the boot-import-mechanism check - see
system_debug_level_raise_for_boot_log_check.py's own docstring for the full design, including the
real finding (a hardcoded "restore to 0" here used to clobber a board legitimately left at a higher
DebugLevel for the rest of a real test session). Restores the real, persisted SYSTEM DebugLevel to
whatever it actually was before that script ran - read back from the dedicated backup file it
wrote, never a hardcoded assumption. Run from a `finally` block in the driving test so a failed
assertion never leaves the board's real config changed."""

import asyncio

import config_manager as cm

_SYS_SCHEMA: "cm.ConfigSchema" = (("DebugLevel", "int", 0, 0, 5, None),)
_SYS_PATH = "config_SYSTEM.cfg"
_BACKUP_SCHEMA: "cm.ConfigSchema" = (("PrevLevel", "int", 0, 0, 5, None),)
_BACKUP_PATH = "config_HWTEST_DEBUGLEVEL_BACKUP.cfg"


async def _main() -> None:
    backup_mgr = cm.ConfigManager(_BACKUP_PATH, _BACKUP_SCHEMA, "HWTEST")
    await backup_mgr.setup()
    if not backup_mgr.valid:
        print(f"RESULT: FAIL {_BACKUP_PATH} did not load as valid - cannot recover the original DebugLevel")
        return
    backup = await backup_mgr.get_dict(["PrevLevel"])
    if backup is None or "PrevLevel" not in backup:
        print("RESULT: FAIL could not read the backed-up DebugLevel")
        return
    previous_level = backup["PrevLevel"]

    sys_mgr = cm.ConfigManager(_SYS_PATH, _SYS_SCHEMA, "SYSTEM")
    await sys_mgr.setup()
    ok, validity = await sys_mgr.write_config({"DebugLevel": previous_level}, _SYS_SCHEMA)
    if ok and validity.get("DebugLevel") in ("Valid", "Unchanged"):
        print(f"RESULT: PASS DebugLevel restored to {previous_level}")
    else:
        print(f"RESULT: FAIL write_config() reported {validity} restoring DebugLevel={previous_level}")


asyncio.run(_main())
