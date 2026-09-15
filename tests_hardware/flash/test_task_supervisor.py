"""Flash-tier automated test: SystemService.start_and_check_tasks()'s own restart-a-dead-task
mechanism against a real board, not just mock/twin bookkeeping - the recovery rung CLAUDE.md's own
memory-safety-discipline rule leans on between a caught local degrade and the hardware watchdog."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def test_start_and_check_tasks_restarts_a_real_dead_task(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "system_service_restarts_a_real_dead_task.py", timeout_s=15.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"task-supervisor restart check failed: {match.group(2).strip()}\nfull output:\n{output}"
