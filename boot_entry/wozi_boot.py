"""Real firmware entry point for the wozi prototype - deliberately separate from
src/sensortask_wozi.py (see that module's own docstring for why). src/sensortask_wozi.py stays independently testable (import it, call
build_system()/main() directly, always returns); this file is the one place that actually blocks
forever, matching how a real deployed unit boots today (modules/_boot.py's own `import
sensortask.py` triggers exactly this shape) - kept untouched per CLAUDE.md's hard rule, not edited
or replaced by this file. How this file itself gets frozen/wired into a real build is Step 5's
"full Unix-port integration"/assembly job, not Step 1's.
"""

import asyncio

from sensortask_wozi import main

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
