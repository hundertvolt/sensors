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

from sensortask_dev import main

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
