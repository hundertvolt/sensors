"""Flash-tier automated tests: WP3's UartLinkExerciser fram_target/logger_target wiring against
the real MB85RS2MTA chip - a structurally different mechanism from test_uart_crossover.py's own
jumper-based coverage, which never wires either option (SPECIFICATION.md Part J.9/C.14)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def _run_and_assert_pass(board: Board, script_name: str, timeout_s: float, label: str) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / script_name, timeout_s=timeout_s)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{label} failed: {match.group(2).strip()}\nfull output:\n{output}"


# ---------------------------------------------------------------------------
# Own-chunk path (fram_target): UartLinkExerciser forwards fram= into UART_Comm's own
# already-correct construction (Part J.9), which is what this test actually proves - the wiring,
# not UART_Comm's own FRAM support (already covered by test_fram_storage.py's
# fram_error_log_roundtrip.py, one layer below this wrapper).
# ---------------------------------------------------------------------------


def test_uart_link_exerciser_fram_backed_error_log_persists_across_a_simulated_reboot(board: Board) -> None:
    # One real FRAM write group (project-owner-mandated write-budget discipline, SPECIFICATION.md
    # Part C.8) - a single err_s() call, then a simulated reboot in the same process (a fresh
    # AsyFramManager against the same chip), matching every other module's own reboot-persistence
    # device script (e.g. fram_error_log_roundtrip.py). No real UART peripheral is exercised at all
    # (uart=None) - only the FRAM-backed logger this wrapper forwards through.
    _run_and_assert_pass(board, "uart_fram_error_log_roundtrip.py", timeout_s=30.0, label="UartLinkExerciser FRAM error log roundtrip")
