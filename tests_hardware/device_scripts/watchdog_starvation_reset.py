"""Isolated-driver device script: deliberately starves the RP2040 hardware watchdog to confirm the
real peripheral resets the board, not just mock/twin bookkeeping. Arms a short 1500ms window and
never feeds it; never returns - the reset kills the connection mid-command, observed host-side."""

import machine

# @tunable l3.starvation_wdt_ms = 1500
_WATCHDOG_TIMEOUT_MS = 1500

machine.WDT(timeout=_WATCHDOG_TIMEOUT_MS)
print("WDT armed, starving now")
while True:
    pass
