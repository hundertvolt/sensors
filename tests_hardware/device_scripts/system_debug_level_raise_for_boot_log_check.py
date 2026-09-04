"""Isolated-driver device script, phase 1/3 for the boot-import-mechanism check
(tests_hardware/flash/test_reboot_persistence.py::test_boot_import_mechanism_actually_boots_the_real_system).

REAL FINDING this exists to work around: at this board's own current, deliberately production-quiet
DebugLevel=0, every pr.one()-level boot-chatter line (ConfigManager's "JSON Data in config file...
found", the per-module CFGMGR_/FRAM announcements the test looks for) is unconditionally suppressed
(print_log.py: `def one(self, ...): if self.level >= _LOG_ONCE: ...`, _LOG_ONCE=3) - confirmed
directly against real source, not assumed. Raises the real, persisted SYSTEM DebugLevel to 3
(_LOG_ONCE) so the very next real hard_reset()'s boot sequence actually emits the lines this test
checks for. The companion script `system_debug_level_restore_after_boot_log_check.py` sets it back
to 0 afterward - this script alone leaves the board in a non-default state on purpose, for exactly
one intervening hard_reset()'s duration.

Writes to the real config_SYSTEM.cfg (system_service.py's own production config file), not a
dedicated test-only file like reboot_persist_write.py's Marker - deliberately, since DebugLevel's
real effect on real boot-time logging is exactly what's under test here. The schema tuple below is
hand-copied verbatim from system_service.py's own `_VAL_DEBUG_LEVEL` (a `micropython.const()`-
wrapped tuple, not importable across modules in a frozen build - see SPECIFICATION.md Part F.1)."""

import asyncio

import config_manager as cm

_SCHEMA: "cm.ConfigSchema" = (("DebugLevel", "int", 0, 0, 5, None),)
_PATH = "config_SYSTEM.cfg"
_VERBOSE_LEVEL = 3  # print_log.py's _LOG_ONCE - the level pr.one() itself is gated on


async def _main() -> None:
    mgr = cm.ConfigManager(_PATH, _SCHEMA, "SYSTEM")
    await mgr.setup()
    ok, validity = await mgr.write_config({"DebugLevel": _VERBOSE_LEVEL}, _SCHEMA)
    if ok and validity.get("DebugLevel") in ("Valid", "Unchanged"):
        print(f"RESULT: PASS DebugLevel raised to {_VERBOSE_LEVEL}")
    else:
        print(f"RESULT: FAIL write_config() reported {validity} for DebugLevel={_VERBOSE_LEVEL}")


asyncio.run(_main())
