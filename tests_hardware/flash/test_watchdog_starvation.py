"""Flash-tier automated test: confirms the real RP2040 hardware watchdog genuinely resets the board
when starved - prior coverage was mock/twin-level only, which can never prove the peripheral fires.
Safe under run_isolated(): WDT(timeout=...) always re-arms fresh, so the short device-script timeout governs."""

from __future__ import annotations

import time
from pathlib import Path

from harness import Board, HardwareTestFailureError, wait_until

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
_ARMED_BANNER = "WDT armed, starving now"  # printed by device_scripts/watchdog_starvation_reset.py


def test_watchdog_starvation_triggers_a_real_hardware_reset(board: Board) -> None:
    start = time.monotonic()
    failure = ""
    try:
        # allow_recovery=False: the connection dying is the expected outcome, so the harness's
        # transient-disconnect retry must not run - its 10s grace window put this measurement at
        # a reproducible ~13.2s against the 10.0s bound, measuring the retry, not the watchdog.
        board.run_isolated(DEVICE_SCRIPTS / "watchdog_starvation_reset.py", timeout_s=15.0, allow_recovery=False)
        raise AssertionError("run_isolated() returned normally - the watchdog never fired (the device script should never return)")
    except HardwareTestFailureError as exc:
        failure = str(exc)  # expected: the connection dies mid-script. `exc` is unbound after this block

    elapsed = time.monotonic() - start
    assert elapsed < 10.0, (
        f"took {elapsed:.1f}s to observe the connection drop - the device script's own watchdog "
        "is armed for 1.5s, so something else likely timed out instead of a real watchdog reset"
    )
    # After the timing bound, not before: a TimeoutExpired reports no stdout at all, and the
    # bound already names that 15s hang correctly. The banner is what separates a real reset from
    # the transient connect failure allow_recovery=False lets through just as fast.
    assert _ARMED_BANNER in failure, f"the connection dropped within the bound but without {_ARMED_BANNER!r} ever arriving - the device script never started, so this was a connect failure, not a watchdog reset:\n{failure}"

    # Checked via is_device_present()/is_reachable() rather than tail_log() content, since log
    # output is gated behind DebugLevel (0 by default) and this must hold regardless of that config.
    wait_until(board.is_device_present, timeout_s=15.0, poll_interval_s=0.3, description="USB device node reappears after a real watchdog-triggered reset")
    wait_until(board.is_reachable, timeout_s=15.0, poll_interval_s=0.5, description="mpremote can talk to the board again after the reset")
