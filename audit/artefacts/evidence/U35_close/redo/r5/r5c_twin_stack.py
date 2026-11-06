import sys
sys.path.insert(0, "tests_hardware")
sys.path.insert(0, ".")
from harness import DEVICE_SCRIPTS_DIR
from twin_board import TwinBoard

for mode in ("reboot", "entry_held"):
    b = TwinBoard(default_timeout_s=120)
    try:
        out = b.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reset_code_stack_exhausted.py", mode=mode)
    except Exception as e:
        out = str(e)
    print("=====", mode)
    print("\n".join(l for l in out.splitlines() if l.startswith(("FACT", "digital_twin", "DONE", "twin run", "Traceback")) or "Error" in l)[:3000])
