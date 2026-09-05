"""Real firmware entry point for the dev-bench variant - deliberately separate from
src/sensortask_dev.py (see that module's own docstring for why). src/sensortask_dev.py stays independently testable (import it, call
build_system()/main() directly, always returns); this file is the one place that actually blocks
forever, matching how a real deployed unit boots today (modules/_boot.py's own `import
sensortask.py` triggers exactly this shape) - kept untouched per CLAUDE.md's hard rule, not edited
or replaced by this file. How this file itself gets frozen/wired into a real build is
scripts/build_firmware.py's own per-device staging job (see that script's own device->boot-module
mechanism).
"""

import asyncio
import gc

from sensortask_dev import main

# gc.threshold(32768) - proactive collection (MicroPython's own default on this hardware is -1,
# collection only ever reactive) - project owner's decision (BACKLOG.md, 2026-09-05) after real
# sub-second-resolution frequency/mem_free-floor measurements at 16384/32768/65536 under both idle
# and hammer load, on top of (not instead of) the /status JSON-streaming fix (already independently
# confirmed to eliminate the real-hardware MemoryError reproduction with no threshold change at
# all) - defense in depth against any other, still-undiscovered large-allocation site. Set here, at
# module level, as early as possible - before `main()`/`build_system()` allocate anything - to match
# exactly how this value was measured (see BACKLOG.md for the full comparison table and the real
# hammer-load re-run this value was validated against).
gc.threshold(32768)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
