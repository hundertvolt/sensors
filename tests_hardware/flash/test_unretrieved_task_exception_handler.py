"""Flash-tier automated test: SYSTEM's unretrieved-task-exception report on real silicon - allocation-free with the
heap locked at DebugLevel 0 and 1 through the real USB console path, and a thousand detached task deaths leaving the
collected heap where it was. The twin and unit tiers cannot confirm the console path; this is where it is confirmed."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ()

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


# @tunable l3.unretrieved_task_exception_handler_script_timeout_s = 30.0
_SCRIPT_TIMEOUT_S = 30.0


def _assert_pass(output: str, what: str) -> None:
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{what} failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_the_unretrieved_exception_report_is_allocation_free_and_retains_nothing_on_real_hardware(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "unretrieved_task_exception_handler.py", timeout_s=_SCRIPT_TIMEOUT_S)
    # Printed on pass too: run_isolated() captures the board's stdout, and these are the measured figures.
    for line in (ln for ln in output.splitlines() if ln.startswith(("REPORT ", "HEAP ", "HAMMER "))):
        print(line)
    _assert_pass(output, "unretrieved-exception report check")
