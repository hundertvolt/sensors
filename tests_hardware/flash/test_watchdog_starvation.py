"""Flash-tier automated test: confirms the real RP2040 hardware watchdog genuinely resets the board
when starved - prior coverage was mock/twin-level only, which can never prove the peripheral fires.
Safe under run_isolated(): WDT(timeout=...) always re-arms fresh, so the short device-script timeout governs."""

from __future__ import annotations

import time
from pathlib import Path

from harness import Board, HardwareTestFailureError, wait_until

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"


def test_watchdog_starvation_triggers_a_real_hardware_reset(board: Board) -> None:
    start = time.monotonic()
    try:
        board.run_isolated(DEVICE_SCRIPTS / "watchdog_starvation_reset.py", timeout_s=15.0)
        raise AssertionError("run_isolated() returned normally - the watchdog never fired (the device script should never return)")
    except HardwareTestFailureError:
        pass  # expected: the connection dies mid-script when the watchdog resets the board

    elapsed = time.monotonic() - start
    assert elapsed < 10.0, (
        f"took {elapsed:.1f}s to observe the connection drop - the device script's own watchdog "
        "is armed for 1.5s, so something else likely timed out instead of a real watchdog reset"
    )

    # Checked via is_device_present()/is_reachable() rather than tail_log() content, since log
    # output is gated behind DebugLevel (0 by default) and this must hold regardless of that config.
    wait_until(board.is_device_present, timeout_s=15.0, poll_interval_s=0.3, description="USB device node reappears after a real watchdog-triggered reset")
    wait_until(board.is_reachable, timeout_s=15.0, poll_interval_s=0.5, description="mpremote can talk to the board again after the reset")
