"""The WiFi radio re-init rung on silicon, with the bench AP up: the device script connects the WiFi service, runs its
_recover_device() rung and connects again; the host judges its facts (the link back, an address, within the budget)
and puts the board back to serving. No config write."""

from typing import TYPE_CHECKING

import _load
from harness import DEVICE_SCRIPTS_DIR, parse_facts, restore_board_to_serving

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("wifi_modes",)

# @tunable l4.wifi_radio_reinit_script_timeout_s = 120.0
_SCRIPT_TIMEOUT_S = 120.0
_WIFI = "asy_wifi_service.py"


def test_the_radio_reinit_rung_restores_the_link(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> None:
    try:
        output = board.run_isolated(DEVICE_SCRIPTS_DIR / "wifi_radio_reinit_recovery.py", timeout_s=_SCRIPT_TIMEOUT_S)
    finally:
        restore_board_to_serving(board, bench, dut_ip)
    facts = parse_facts(output)
    assert facts.get("config_read") is True, f"the board holds no readable config_WIFI.cfg to connect with: {facts}"
    assert facts.get("connected_before") is True, f"the WiFi service never connected before the rung, so the rung proves nothing: {facts}"
    elapsed, budget = facts.get("elapsed_ms"), facts.get("budget_ms")
    result_note(f"radio re-init rung: link back in {elapsed} ms (rung returned {facts.get('recover_returned')!r})")
    assert facts.get("reconnected") is True and facts.get("ip"), f"the link did not come back after the radio re-init: {facts}"
    # The rung's own mode switch (its three settles, src/asy_wifi_service.py _switch_wlan_mode()) plus one connect budget.
    switch_ms = 1000 * sum(_load.src_number(_WIFI, name) for name in ("_WLAN_DOWN_SETTLE_S", "_WLAN_DEINIT_SETTLE_S", "_WLAN_MODE_SETTLE_S"))
    assert isinstance(elapsed, int) and isinstance(budget, int) and elapsed <= switch_ms + budget, f"the re-init and reconnect took {elapsed} ms, past the rung's {switch_ms:g} ms mode switch plus one {budget} ms connect budget: {facts}"
