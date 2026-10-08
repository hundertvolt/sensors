"""Flash-tier automated test: SystemService.start_tasks()/supervise_tasks()'s own restart-a-dead-task
mechanism against a real board, not just mock/twin bookkeeping - the recovery rung CLAUDE.md's own
memory-safety-discipline rule leans on between a caught local degrade and the hardware watchdog."""

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_5_recovery_after_bounded_fault",)

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


# @tunable l3.task_supervisor_script_timeout_s = 15.0
_SCRIPT_TIMEOUT_S = 15.0


def test_the_supervisor_restarts_a_real_dead_task(board: "Board") -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "system_service_restarts_a_real_dead_task.py", timeout_s=_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"task-supervisor restart check failed: {match.group(2).strip()}\nfull output:\n{output}"
