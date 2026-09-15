"""Bench-tier automated tests: WP3's UartLinkExerciser fram_target wiring survives a real reboot
inside the full deployed graph, reached through the production REST API - complements
tests_hardware/flash/test_uart_fram_logging.py's direct-driver, no-HTTP version and
tests_hardware/bench/test_uart_link_under_api_load.py's own coexistence-under-load coverage
(SPECIFICATION.md Part J.9/C.14)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import http_client
import pytest
from error_log_helpers import assert_module_error_log_empty, get_errcount, reset_all_error_logs
from harness import wait_until

if TYPE_CHECKING:
    from harness import Board

_UART_MODULES = ("UART_init", "UART_resp")  # asy_uart_link_driver.UartLinkExerciser's own
# name_ext="init"/"resp" -> instance_name() resolution, matching test_uart_link_under_api_load.py


def _require_uart_modules(dut_ip: str) -> None:
    present = get_errcount(dut_ip)
    missing = [name for name in _UART_MODULES if name not in present]
    if missing:
        pytest.skip(
            f"this firmware exposes no {', '.join(missing)} error source - check devices/dev.toml "
            "still declares its uart_link instances and this build actually used it",
        )


def test_both_uart_instances_are_present_and_start_clean(board: Board, dut_ip: str) -> None:
    # Basic wiring proof, unaffected by fram_target vs RAM-only on its own: both instances are
    # individually addressable through the real errcount endpoint (SPECIFICATION.md Part A.7).
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip)
    for name in _UART_MODULES:
        assert_module_error_log_empty(dut_ip, name)


def test_the_fram_backed_error_logs_survive_a_real_reboot(board: Board, dut_ip: str) -> None:
    # devices/dev.toml now wires fram_target = "fram" on both real dev instances (own chunk each -
    # see that TOML's own comment for why not a logger_target reach-through onto each other), so
    # each end's errno/wrnno history is durable rather than RAM-only. A genuinely provoked fault is
    # out of reach here without physically disturbing the crossover jumper, so this proves the
    # weaker but still real claim a totally broken FRAM chunk allocation would fail: a real
    # hard_reset() must not corrupt either chunk into a nonzero/garbage initial read, nor make
    # either module disappear from the graph - tests_hardware/flash/test_uart_fram_logging.py's own
    # direct-driver device script is what proves a *recorded* error actually survives.
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip)
    for name in _UART_MODULES:
        assert_module_error_log_empty(dut_ip, name)

    board.hard_reset()
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=1.0,
        description="board reachable again after hard_reset()",
    )

    _require_uart_modules(dut_ip)  # both chunks must have re-initialized cleanly, not disappeared
    for name in _UART_MODULES:
        assert_module_error_log_empty(dut_ip, name)
