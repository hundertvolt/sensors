"""Isolated-driver device script, phase 1/2: writes one ConfigManager-backed value to a test-only config file and
flushes it; the host then triggers a genuine machine.reset() and reboot_persist_read.py reports what survived. A
leftover file from an aborted run goes first, so setup() writes the defaults and the marker is the one owned write."""

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
_MARKER_VALUE = 424242


async def _main() -> None:
    wdt = arm()
    try:
        os.remove(_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_remove_errno", e.errno)
            done()
            return
    mgr = cm.ConfigManager(_PATH, _SCHEMA, "HWTEST")
    await mgr.setup()  # the file is absent: the defaults are written once, a prerequisite of the owned write
    wdt.feed()
    ok, validity = await mgr.write_config({"Marker": _MARKER_VALUE})
    fact("written", {"ok": ok, "validity": validity})
    await mgr.flush_pending()  # write_config() stages; the flush is its own task, so it is awaited here
    fact("flushed", not mgr.unpersisted)
    fact("expected", _MARKER_VALUE)
    done()


asyncio.run(_main())
