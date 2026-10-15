"""Isolated-driver device script: deliberately starves the RP2040 hardware watchdog to confirm the real peripheral resets
the board, not just mock/twin bookkeeping. Arms a short window and never feeds it; never returns - the reset ends the
run, and the host reads the armed window and the banner printed before it."""

import machine

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import fact

# @tunable l3.starvation_wdt_ms = 1500
_WATCHDOG_TIMEOUT_MS = 1500

machine.WDT(timeout=_WATCHDOG_TIMEOUT_MS)
fact("armed_ms", _WATCHDOG_TIMEOUT_MS)
print("WDT armed, starving now")
while True:
    pass
