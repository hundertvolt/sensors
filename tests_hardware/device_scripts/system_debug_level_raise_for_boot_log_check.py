"""Isolated-driver device script, phase 1/3 for the boot-import-mechanism check
(tests_hardware/flash/test_reboot_persistence.py::test_boot_import_mechanism_actually_boots_the_real_system).

REAL FINDING this exists to work around: at a low SYSTEM DebugLevel (e.g. this project's own
production-quiet default, 0), every pr.one()-level boot-chatter line (ConfigManager's "JSON Data in
config file... found", the per-module CFGMGR_/FRAM announcements the test looks for) is
unconditionally suppressed (print_log.py: `def one(self, ...): if self.level >= _LOG_ONCE: ...`,
_LOG_ONCE=3) - confirmed directly against real source, not assumed. Raises the real, persisted
SYSTEM DebugLevel to 3 (_LOG_ONCE) so the very next real hard_reset()'s boot sequence actually
emits the lines this test checks for.

SECOND REAL FINDING, fixed: an earlier version of this pair hardcoded "restore to 0" on the way
back out, which silently undid whatever DebugLevel the board was actually meant to be running at
for the rest of a real test session - tests_hardware/README.md's own "Known assumptions" entry on
this documents the whole bench tier needs DebugLevel>=5 to function at all, so a board legitimately
left at 5 for testing would get clobbered back to 0 by this test alone, breaking every bench test
that runs after it. Fixed: this script backs up whatever the *real, current* DebugLevel actually is
(not an assumption) to a dedicated test-only config file before changing anything, so the companion
script `system_debug_level_restore_after_boot_log_check.py` can restore the exact original value
afterward, not a hardcoded guess. If the current level is already >= 3, nothing is changed at all
(the backup is still written, so restore is always a correct no-op/no-change in that case too).

Writes to the real config_SYSTEM.cfg (system_service.py's own production config file) only when a
change is actually needed - the backup itself uses a dedicated test-only file
(config_HWTEST_DEBUGLEVEL_BACKUP.cfg), the same "never collide with a real driver's own file"
convention reboot_persist_write.py already established in this same directory. The SYSTEM schema
tuple below is hand-copied verbatim from system_service.py's own `_VAL_DEBUG_LEVEL` (a
`micropython.const()`-wrapped tuple, not importable across modules in a frozen build - see
SPECIFICATION.md Part F.1)."""

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
