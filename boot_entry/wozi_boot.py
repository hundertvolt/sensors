"""Real firmware entry point for the wozi prototype - deliberately separate from
src/sensortask_wozi.py (see that module's own docstring for why). src/sensortask_wozi.py stays independently testable (import it, call
build_system()/main() directly, always returns); this file is the one place that actually blocks
forever, matching how a real deployed unit boots today (modules/_boot.py's own `import
sensortask.py` triggers exactly this shape) - kept untouched per CLAUDE.md's hard rule, not edited
or replaced by this file. How this file itself gets frozen/wired into a real build is Step 5's
"full Unix-port integration"/assembly job, not Step 1's.
"""

import asyncio
import gc

from sensortask_wozi import main

# gc.threshold(32768) - proactive collection (MicroPython's own default on this hardware is -1,
# collection only ever reactive) - project owner's decision (BACKLOG.md, 2026-09-05) after real
# sub-second-resolution frequency/mem_free-floor measurements at 16384/32768/65536 under both idle
# and hammer load, on top of (not instead of) the /status JSON-streaming fix (already independently
# confirmed to eliminate the real-hardware MemoryError reproduction with no threshold change at
# all) - defense in depth against any other, still-undiscovered large-allocation site. Set here, at
# module level, as early as possible - before `main()`/`build_system()` allocate anything - to match
# exactly how this value was measured on the dev bench (see BACKLOG.md for the full comparison
# table); WoZi is never physically flashed (CLAUDE.md's hard rule) but shares the same underlying
# mechanisms, so the same value applies here for consistency.
gc.threshold(32768)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
