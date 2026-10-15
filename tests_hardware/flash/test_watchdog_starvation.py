"""Flash-tier automated tests: the real RP2040 hardware watchdog resets the board when starved, and SystemService's
reboot falls back to starving it when its timer cannot arm - mock and twin coverage can never prove the peripheral
fires. The banners and the absent action discriminate here; the fallback's reset code is proven at L4."""

import time
from typing import TYPE_CHECKING

import pytest
from harness import DEVICE_SCRIPTS_DIR, parse_facts, wait_until

if TYPE_CHECKING:
    from collections.abc import Iterator

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_10_watchdog_hang_backstop",)

_ARMED_BANNER = "WDT armed, starving now"  # printed by device_scripts/watchdog_starvation_reset.py
_STARVE_BANNER = "STARVE flag set, feeding only through feed_watchdog() now"  # device_scripts/reboot_fallback_starves_the_watchdog.py
# @tunable l3.watchdog_starvation_script_timeout_s = 15.0
_SCRIPT_TIMEOUT_S = 15.0
# @tunable l3.watchdog_starvation_reset_elapsed_max_s = 10.0
_RESET_ELAPSED_MAX_S = 10.0
# @tunable l3.watchdog_starvation_device_present_timeout_s = 15.0
_DEVICE_PRESENT_TIMEOUT_S = 15.0
# @tunable l3.watchdog_starvation_device_present_poll_s = 0.3
_DEVICE_PRESENT_POLL_S = 0.3
# @tunable l3.watchdog_starvation_fallback_script_timeout_s = 20.0
_FALLBACK_SCRIPT_TIMEOUT_S = 20.0
# @tunable l3.watchdog_starvation_fallback_elapsed_max_s = 12.0
_FALLBACK_ELAPSED_MAX_S = 12.0


@pytest.fixture(scope="module")
def closing_reset(board: "Board") -> "Iterator[None]":
    # Both tests end on a board just back from a watchdog reset; one hard reset and a passive presence wait close the
    # module, so the tier never ends on a board a raw-REPL attach parked without its watchdog.
    yield
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_DEVICE_PRESENT_TIMEOUT_S, poll_interval_s=_DEVICE_PRESENT_POLL_S, description="USB device node reappears after the closing hard_reset()")


def test_watchdog_starvation_triggers_a_real_hardware_reset(board: "Board", closing_reset: None) -> None:
    del closing_reset
    start = time.monotonic()
    # The run ends in the reset, so the output printed before it is the outcome; a script that kept running would
    # time out instead and fail here.
    output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "watchdog_starvation_reset.py", timeout_s=_SCRIPT_TIMEOUT_S)
    elapsed = time.monotonic() - start
    facts = parse_facts(output, allow_missing_done=True)
    assert elapsed < _RESET_ELAPSED_MAX_S, f"took {elapsed:.1f}s to observe the connection drop with the watchdog armed for {facts.get('armed_ms')} ms - something else timed out:\n{output}"
    # The banner separates a real reset from a connect failure that drops the run just as fast.
    assert _ARMED_BANNER in output, f"the connection dropped within the bound but without {_ARMED_BANNER!r} - the script never started:\n{output}"
    # Passive: is_device_present() opens the port without entering the REPL, so main.py boots undisturbed.
    wait_until(board.is_device_present, timeout_s=_DEVICE_PRESENT_TIMEOUT_S, poll_interval_s=_DEVICE_PRESENT_POLL_S, description="USB device node reappears after a real watchdog-triggered reset")


def test_reboot_falls_back_to_starving_the_watchdog_when_its_timer_cannot_arm(board: "Board", closing_reset: None) -> None:
    # SystemService._reboot()'s fallback on silicon: with the alarm pool exhausted the reset timer cannot arm, so the
    # supervisor's own feed_watchdog() must stop feeding and the watchdog resets the board.
    del closing_reset
    wait_until(board.is_device_present, timeout_s=_DEVICE_PRESENT_TIMEOUT_S, poll_interval_s=_DEVICE_PRESENT_POLL_S, description="board present before the fallback run")
    start = time.monotonic()
    output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reboot_fallback_starves_the_watchdog.py", timeout_s=_FALLBACK_SCRIPT_TIMEOUT_S)
    elapsed = time.monotonic() - start
    facts = parse_facts(output, allow_missing_done=True)
    assert "failure" not in facts, f"the fallback's premise failed before any starvation: {facts['failure']}\n{output}"
    assert elapsed < _FALLBACK_ELAPSED_MAX_S, f"took {elapsed:.1f}s to observe the connection drop with the watchdog armed for {facts.get('armed_ms')} ms - something else timed out:\n{output}"
    assert _STARVE_BANNER in output, f"the connection dropped without {_STARVE_BANNER!r} - the fallback flag was never reached (pool {facts.get('pool_timers')} timers):\n{output}"
    assert "action_fired=True" not in output, f"the reboot action fired although its timer could not be armed:\n{output}"
    wait_until(board.is_device_present, timeout_s=_DEVICE_PRESENT_TIMEOUT_S, poll_interval_s=_DEVICE_PRESENT_POLL_S, description="USB device node reappears after the fallback's watchdog reset")
