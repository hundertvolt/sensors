"""Isolated-driver device script, flash-tier: deliberately starves the RP2040 hardware watchdog to
confirm the real peripheral actually resets the board, not just the mock/twin unit-test bookkeeping
(tests/test_system_service.py's _force_watchdog_starve tests, which never touch real hardware).
Closes a real gap this session found: previously the only real-hardware confirmation of this was
manual (tests_hardware/manual/manual_bus_electrical.py, human-observed).

Arms a short 1500ms window and then genuinely never feeds it - `machine.WDT(timeout=...)`'s own
constructor unconditionally re-arms regardless of any prior state (confirmed against
ports/rp2/machine_wdt.c, and against run_isolated()'s own chained `machine.WDT(timeout=8000)`
re-arm - see harness.py's own docstring), so this 1500ms window is what actually governs when the
reset fires, not the 8000ms one run_isolated() sets up first. Never expected to return: the
watchdog fires a real hardware reset before any further output is possible, killing the connection
mid-command - the calling test observes that from the host side (a real USB disconnect/reconnect,
mpremote's connection dying with a real OSError), not from anything this script itself reports.

Run via `mpremote run <this>`."""

import machine

WATCHDOG_TIMEOUT_MS = 1500

machine.WDT(timeout=WATCHDOG_TIMEOUT_MS)
print("WDT armed, starving now")
while True:
    pass
