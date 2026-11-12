"""Isolated-driver device script, phase 2/2 (see reboot_persist_write.py): after a genuine machine.reset(), a fresh
ConfigManager.setup() reads the test-only file back - the real write_config() -> littlefs -> read path across a real
reboot - and reports what it found; the host compares. The file is removed on every path."""

import asyncio
import errno
import os

import asy_config_manager as cm

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm

_SCHEMA: "cm.ConfigSchema" = (("Marker", "int", 0, 0, 999999999, None),)
_PATH = "config_HWTEST_REBOOT.cfg"
_EXPECTED_MARKER_VALUE = 424242


async def _main() -> None:
    wdt = arm()
    try:
        mgr = cm.ConfigManager(_PATH, _SCHEMA, "HWTEST")
        await mgr.setup()
        wdt.feed()
        fact("valid", mgr.valid)
        result = await mgr.get_dict(["Marker"])
        fact("marker", None if result is None else result.get("Marker"))
        fact("expected", _EXPECTED_MARKER_VALUE)
    finally:
        try:
            os.remove(_PATH)
        except OSError as e:
            if e.errno != errno.ENOENT:
                fact("remove_errno", e.errno)
        done()


asyncio.run(_main())
