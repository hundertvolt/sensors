# B8 carry-ins from earlier units (lead, 2026-11-03)

- The generated boot entry prints at DebugLevel 0: `sys.print_exception(ended)` after the loop ends (B1 hand-back), and
  the no-autostart entry's manual start line at import (B1 falsification). Judge both against "level 0 prints nothing,
  ever" (owner, 2026-11-02 20:53).
- The boot entry's `report_if_fatal(ended)` (B1 action list: out of B1).
- If the owner chooses it in clarification (d2): the stored DebugLevel read before construction.
