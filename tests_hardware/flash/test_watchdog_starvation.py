"""Flash-tier automated test: confirms the real RP2040 hardware watchdog genuinely resets the
board when starved. Closes a real gap found this session - the only prior real-hardware
confirmation of this was manual (tests_hardware/manual/manual_bus_electrical.py, human-observed);
automated coverage existed only at the mock/twin unit level (tests/test_system_service.py's
_force_watchdog_starve bookkeeping tests), which can never prove the actual peripheral fires.

Uses run_isolated() + watchdog_starvation_reset.py (which arms a short-window WDT and never feeds
it) rather than a bespoke raw exec() dance - safe because machine.WDT(timeout=...)'s constructor
unconditionally re-arms with a fresh window regardless of any prior state (confirmed against
ports/rp2/machine_wdt.c this session), so the device script's own short timeout governs, not
run_isolated()'s own longer 8000ms re-arm."""

from __future__ import annotations

import time
from pathlib import Path

from harness import Board, HardwareTestFailure, wait_until

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"


def test_watchdog_starvation_triggers_a_real_hardware_reset(board: Board) -> None:
    start = time.monotonic()
    try:
        board.run_isolated(DEVICE_SCRIPTS / "watchdog_starvation_reset.py", timeout_s=15.0)
        raise AssertionError("run_isolated() returned normally - the watchdog never fired (the device script should never return)")
    except HardwareTestFailure:
        pass  # expected: the connection dies mid-script when the watchdog resets the board

    elapsed = time.monotonic() - start
    assert elapsed < 10.0, (
        f"took {elapsed:.1f}s to observe the connection drop - the device script's own watchdog "
        "is armed for 1.5s, so something else likely timed out instead of a real watchdog reset"
    )

    # A real watchdog reset is a genuine hardware reset (RP2040 restarts from its own reset
    # vector), producing the same real USB re-enumeration cycle a hard_reset() does (confirmed via
    # dmesg correlation earlier this session) - checked here via is_device_present()/is_reachable()
    # rather than tail_log() content, since log output is gated behind config_SYSTEM.cfg's
    # DebugLevel (0 by default - see print_log.py) and this test must hold regardless of that
    # runtime config, not just on a bench that happens to have logging turned up.
    wait_until(board.is_device_present, timeout_s=15.0, poll_interval_s=0.3, description="USB device node reappears after a real watchdog-triggered reset")
    wait_until(board.is_reachable, timeout_s=15.0, poll_interval_s=0.5, description="mpremote can talk to the board again after the reset")
