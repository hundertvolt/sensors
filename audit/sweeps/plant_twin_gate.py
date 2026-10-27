"""The twin gate's plant arm: one dev twin booted from the planted copy (cwd), its log read by the suite's own check.

Args: MICROPYTHON_BIN GC_THRESHOLD LOG_OUT. Exit 1 when _check_no_memory_error_in_log() fails the run, 0 when it passes.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")
import _digital_twin_ci_suite as ci  # noqa: E402
import _twin_process as tp  # noqa: E402

mp, stage, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
state = Path(f".twin_state_{stage}")
state.mkdir()
launch = tp.TwinLaunch(mp, "sensortask_dev", Path("build/generated_src/sensortask_dev_wiring_plan.json"), "dev", "127.0.0.1", 8080, stage)
run = tp.spawn(launch, state_dir=state, log_path=out)
deadline = time.monotonic() + 120
status = 0
while time.monotonic() < deadline and run.proc.poll() is None:
    try:
        status, _ = tp.http("GET", "127.0.0.1", 8080, "/status", timeout_s=2.0)
    except OSError:
        status = 0
    if status == 200:
        break
    time.sleep(1)
print(f"GET /status: {status}")
ec = tp.shutdown(run, "plant")
print(f"twin exit {ec}")
ci._check_no_memory_error_in_log(out, "plant run")
print(f"suite failures: {ci._FAILURES}")
sys.exit(1 if ci._FAILURES else 0)
