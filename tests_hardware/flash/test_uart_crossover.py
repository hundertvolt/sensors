"""Flash-tier automated tests: the UART message protocol across the dev bench's permanent
UART0<->UART1 crossover jumper - real timing, real peripheral behaviour and real poll latency,
the three things no fake reproduces (requirement H3 / SPECIFICATION.md Part J.7)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)

# Both scripts import asy_uart_comm, which a dev firmware built today does contain (sensortask_dev
# imports it, and build_firmware.py freezes all of src/). The guard below is therefore not an
# expected skip - it only names the cause if some future firmware lacks it (BACKLOG.md).
_MISSING_MODULE_RE = re.compile(r"ImportError: no module named 'asy_uart_comm'")


def _run_or_skip(board: Board, script: str, timeout_s: float) -> str:
    try:
        return board.run_isolated(DEVICE_SCRIPTS / script, timeout_s=timeout_s)
    except Exception as e:  # HardwareTestFailureError carries the device-side traceback in its text
        if _MISSING_MODULE_RE.search(str(e)):
            pytest.skip(
                "this firmware does not contain asy_uart_comm - a dev build normally pulls it in "
                "behind sensortask_dev, so check how this firmware was built (BACKLOG.md)",
            )
        raise


def _assert_pass(output: str, what: str) -> None:
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{what} failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_get_and_set_and_a_multi_chunk_train_cross_the_jumper(board: Board) -> None:
    # One Python instance as initiator and one as responder interoperating perfectly is a required,
    # tested property of this protocol, not an incidental one - and the jumper is where it is
    # physically true rather than modelled.
    output = _run_or_skip(board, "uart_crossover_exchange.py", timeout_s=120.0)
    _assert_pass(output, "UART crossover GET/SET/multi-chunk exchange")


def test_one_sided_silence_recovers_and_a_parameter_mismatch_fails_loudly(board: Board) -> None:
    # The two failure classes that matter on real hardware: the one the design recovers from, and
    # the one it deliberately cannot - which must therefore be diagnosed rather than absorbed.
    output = _run_or_skip(board, "uart_crossover_recovery.py", timeout_s=180.0)
    _assert_pass(output, "UART crossover recovery and mismatch detection")
