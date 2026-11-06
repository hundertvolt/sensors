"""Flash-tier automated tests: the supervisor's restart of a real dead task, and the running graph on a real board
under an emptied alarm pool, a stepped RTC and a fault that stops every feed - not mock/twin bookkeeping. A scratch
graph writes the production FRAM chunks, so each of those tests saves the raw FRAM first; the verdict is here."""

import json
import time
from typing import TYPE_CHECKING

import pytest
from error_log_helpers import code
from harness import DEVICE_SCRIPTS_DIR, SRC_DIR, HardwareTestFailureError, parse_facts, save_fram_raw, wait_for_boot, wait_until

from buildgen.validate import _WDT_TIMEOUT_MS, module_int_const

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("sensortask_integration", "clock_jump", "timer_pool", "scenarios.watchdog_fault_main_exit", "scenarios.watchdog_fault_supervisor_raise")

_SCRIPT_TIMEOUT_S = 15.0
_SCAN_SCRIPT_TIMEOUT_S = 60.0  # the script's own 20 s watch, its FRAM setup and the chunk clears
_SCAN_ENTRIES = 5  # four task ends and the reboot's entry (Part N system.scan_budget)
_GRAPH_SCRIPT_TIMEOUT_S = 120.0
_TASK_RETURNED = code("E", "TASK_RETURNED")
_TIMER = code("E", "TIMER")
_SGP_BACKUP_AGE = code("W", "SGP_BACKUP_AGE")
_RR_WATCHDOG = module_int_const(SRC_DIR, "asy_system_service.py", "_RR_WATCHDOG")
_TIMER_BIT, _FORCED_BIT = 0x1, 0x2  # the watchdog's REASON bits 0-1, TIMER and FORCE (pico-sdk watchdog.h)
_BOOT_TIMEOUT_S = 60.0
_DST_START = 1774746000  # source: tests_hardware/device_scripts/clock_step_under_the_running_graph.py _DST_START
_STEPS_S = (-3600, 86400)  # source: tests_hardware/device_scripts/clock_step_under_the_running_graph.py _STEPS_S
_STEP_SLACK_S = 30  # the script's sample waits between the two steps' stamps, at most its own 20 s bound and the read
_PRESENT_TIMEOUT_S = 30.0
# The production boot's reset reason and the REASON bits, read through exec_live() once its boot is done.
_READ_AFTER_BOOT = (
    "import json, sys\nfrom machine import mem32\n"
    "m = [v for k, v in sys.modules.items() if k.startswith('sensortask_') and getattr(v, 'sysfunct', None) is not None]\n"
    "print('AFTER ' + json.dumps({'reason': m[0].sysfunct.get_reset_reason(), 'bits': mem32[0x40058008] & 3} if m else None))\n"
)
# Each fault's scratch directory, left behind by the reset that ends its run.
_REMOVE_SCRATCH = "import os\nif 'hwtest-scratch' in os.listdir():\n    for n in os.listdir('hwtest-scratch/'):\n        os.remove('hwtest-scratch/' + n)\n    os.rmdir('hwtest-scratch/')\n"


def test_the_supervisor_restarts_a_real_dead_task(board: "Board") -> None:
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / "system_service_restarts_a_real_dead_task.py", timeout_s=_SCRIPT_TIMEOUT_S, mode="restart")
    facts = parse_facts(output)
    calls, system = facts.get("starter_calls"), facts.get("system")
    assert isinstance(calls, int) and calls >= 2, f"the dying task's starter ran {calls} time(s) - expected the first start and a real restart: {facts}"
    assert isinstance(system, dict), f"no SYSTEM log fact: {facts}"
    # Each restart follows exactly one logged end: the supervisor logs the dead task, then starts it anew.
    assert system.get("ErrCount") == calls - 1, f"{calls} starter calls but {system.get('ErrCount')} logged task ends: {facts}"
    logged = [(t, n) for t, n in zip(system.get("ErrType", []), system.get("ErrNum", []), strict=True) if t != "N"]
    assert logged and all(entry == ("E", _TASK_RETURNED) for entry in logged), f"the SYSTEM log holds other than TASK_RETURNED entries: {system}"
    # At DebugLevel 0 a dying task prints nothing: asyncio's default handler text or a traceback is a leak past the log.
    leaked = [line for line in output.splitlines() if "Task exception wasn't retrieved" in line or "Traceback" in line]
    assert not leaked, "a task's end reached the console at DebugLevel 0:\n" + "\n".join(leaked)


def test_one_supervisor_pass_with_every_task_ended_stays_inside_the_watchdog(board: "Board", result_note: "Callable[[str], None]") -> None:
    # Part N's system.scan_budget on silicon: the sleep and the escalating pass between two feeds, then the reset's
    # countdown after the last one, each under the watchdog; the script writes SYSTEM's FRAM chunk, so the dump comes first.
    save_fram_raw(board, "supervisor-scan-timing")
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "supervisor_scan_timing.py", timeout_s=_SCAN_SCRIPT_TIMEOUT_S))
    scan_ms, reset_ms = facts.get("scan_feed_to_feed_ms"), facts.get("feed_to_reset_ms")
    result_note(f"the sleep and one escalating pass {scan_ms} ms between feeds, the reset {reset_ms} ms after the last feed")
    system = facts.get("system")
    assert isinstance(system, dict) and system.get("ErrCount", 0) >= _SCAN_ENTRIES, f"the pass logged fewer than {_SCAN_ENTRIES} SYSTEM entries: {facts}"
    assert isinstance(scan_ms, int) and scan_ms < _WDT_TIMEOUT_MS, f"the supervisor sleep and its escalating pass took {scan_ms} ms between feeds, not under {_WDT_TIMEOUT_MS}: {facts}"
    assert isinstance(reset_ms, int) and reset_ms < _WDT_TIMEOUT_MS, f"the reset came {reset_ms} ms after the last feed, not under {_WDT_TIMEOUT_MS}: {facts}"
    assert facts.get("cleared_last") is True, f"the SYSTEM chunk the script wrote was not cleared: {facts}"


def test_the_running_graph_handles_every_failed_arm_of_an_emptied_alarm_pool_in_place(board: "Board") -> None:
    # The whole graph's tasks and timers started with no alarm free: every starter runs, the stagger's failed arm is
    # logged and slept instead, the uptime still rises, mempause answers, the WiFi tick re-arms once the pool frees, and
    # no task ends and no reset arms.
    save_fram_raw(board, "timer-pool-empty-beside-the-graph")
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "timer_pool_empty_beside_the_graph.py", timeout_s=_GRAPH_SCRIPT_TIMEOUT_S))
    assert "failure" not in facts and "leftover_errno" not in facts, f"the scratch graph failed before its verdict: {facts}"
    assert isinstance(facts.get("pool_free"), int) and facts.get("timers_started") is True, f"the timers never started over the empty pool: {facts}"
    assert facts.get("uptime_rose") is True, f"the uptime stood still while its tick was unarmed: {facts}"
    assert facts.get("mempause") is True and facts.get("paused") in (True, None), f"mempause with the pool empty did not pause: {facts}"
    assert facts.get("wifi_tick_armed_empty") in (False, None) and facts.get("wifi_tick_rearmed", True) is True, f"the WiFi tick armed from an empty pool or never re-armed: {facts}"
    system, gained = facts.get("system"), facts.get("system_gained")
    assert isinstance(system, dict) and isinstance(gained, int) and gained >= 1, f"SYSTEM logged no failed arm: {facts}"
    newest = [num for kind, num in zip(system["ErrType"], system["ErrNum"], strict=True) if kind == "E"][-gained:]
    assert _TIMER in newest, f"the stagger's failed arm is not among SYSTEM's {gained} newest entries {newest}: {facts}"
    assert facts.get("tasks_alive") is True and facts.get("reset_armed") is False, f"a task ended or a reset armed over the empty pool: {facts}"


@pytest.mark.parametrize("mode", ["main_exit", "supervisor_raise"])
def test_a_fault_inside_the_running_graph_stops_every_feed_and_the_watchdog_resets(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]", mode: str) -> None:
    # After the supervisor's first feed, main() ends under the live loop or the dead-task report raises: no feed after
    # it, the loop runs on, and the watchdog resets the board - the next boot reads 2 with the TIMER bit alone. The twin
    # never resets, so there its runner's starved-watchdog exit is the outcome and the after-boot half is silicon's.
    script = DEVICE_SCRIPTS_DIR / "watchdog_fault_in_the_running_graph.py"
    twin = request.config.getoption("--twin")
    save_fram_raw(board, f"watchdog-fault-{mode}")
    try:
        if twin:
            with pytest.raises(HardwareTestFailureError, match="starved the watchdog") as starved:
                board.run_isolated_expect_reset(script, timeout_s=_GRAPH_SCRIPT_TIMEOUT_S, mode=mode)
            output = str(starved.value)
        else:
            output = board.run_isolated_expect_reset(script, timeout_s=_GRAPH_SCRIPT_TIMEOUT_S, mode=mode)
        facts = parse_facts(output, allow_missing_done=True)
        assert "failure" not in facts and "leftover_errno" not in facts, f"{mode}: the fault was never reached: {facts}"
        assert twin or "no_reset_after_ms" not in facts, f"{mode}: the board outlived its unfed loop: {facts}"
        fed, rounds = facts.get("fed_at_fault"), [value for key, value in facts.items() if key.startswith("round_") and isinstance(value, dict)]
        assert isinstance(fed, int) and rounds and all(r["feeds"] == fed for r in rounds), f"{mode}: a feed after the fault, or no round of the live loop: fed {fed}, rounds {rounds}"
        ended = {key: rounds[-1][key] for key in ("main", "supervisor")}
        assert ended == {"main": mode == "main_exit", "supervisor": True}, f"{mode}: by the last round the fault had not ended the supervisor, alone or with main(): {ended}"
        result_note(f"{mode}: fed {fed} times, then {len(rounds)} unfed rounds of the live loop")
        if twin:
            return
        wait_until(board.is_device_present, timeout_s=_PRESENT_TIMEOUT_S, description=f"board back on USB after the {mode} watchdog reset")
        wait_for_boot(board, _BOOT_TIMEOUT_S)
        line = next((ln for ln in board.exec_live(_READ_AFTER_BOOT).splitlines() if ln.startswith("AFTER ")), None)
        after = json.loads(line[len("AFTER ") :]) if line else None
        assert isinstance(after, dict), f"{mode}: no running sensortask_* module after the boot"
        result_note(f"{mode}: the next boot read ResetReason {after['reason']}, REASON bits {after['bits']}")
        assert after["reason"] == _RR_WATCHDOG, f"{mode}: the next boot read ResetReason {after['reason']}, not {_RR_WATCHDOG}"
        assert after["bits"] & _TIMER_BIT and not after["bits"] & _FORCED_BIT, f"{mode}: a starvation reset must set the timer bit, never the forced one: {after['bits']}"
    finally:
        board.exec(_REMOVE_SCRATCH)
        board.hard_reset()
        wait_until(board.is_device_present, timeout_s=_PRESENT_TIMEOUT_S, description="board back on USB after the closing hard reset")


def test_a_stepped_clock_under_the_running_graph_moves_every_wall_clock_consumer_with_it(board: "Board") -> None:
    # The graph running with its clock set as a sync leaves it, then the RTC stepped: each BMP3XX sample carries the
    # stepped clock, an SGP40 backup dated after a step back is refused under a max age and kept under none, cettime()
    # crosses the March switch both ways, and a year's steps leave Synced set and LastSyncAge on the ticks.
    save_fram_raw(board, "clock-step-under-the-graph")
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "clock_step_under_the_running_graph.py", timeout_s=_GRAPH_SCRIPT_TIMEOUT_S))
    assert "failure" not in facts and "leftover_errno" not in facts, f"the scratch graph failed before its verdict: {facts}"
    stamps = facts.get("stamps")
    assert isinstance(stamps, list) and len(stamps) == len(_STEPS_S), f"no stamp per step: {facts}"
    assert all(isinstance(clock, int) and isinstance(ts, int) and abs(ts - clock) <= 1 for clock, ts in stamps), f"a sample not stamped from the clock it was read under: {stamps}"
    moved = stamps[1][0] - stamps[0][0]
    assert _STEPS_S[1] <= moved <= _STEPS_S[1] + _STEP_SLACK_S, f"the clock moved {moved} s between the steps, not the {_STEPS_S[1]} s step: {stamps}"
    backup = facts.get("backup")
    assert isinstance(backup, dict) and isinstance(backup["stamp"], int), f"no SGP40 backup was written: {facts}"
    refused, kept = backup["restores"]
    assert (refused["restored"], refused["newest"]) == (False, [["W", _SGP_BACKUP_AGE]]), f"a backup dated after the step back was not refused under BackupMaxAge {refused['max_age']}: {refused}"
    assert (kept["restored"], kept["from"]) == (True, backup["stamp"]), f"BackupMaxAge 0 did not restore the backup of {backup['stamp']}: {kept}"
    offsets, local = facts.get("offsets"), facts.get("local")
    assert isinstance(offsets, dict) and isinstance(local, list), f"no offsets or local times: {facts}"
    gmt, dst = int(offsets["GMTOffset"]), int(offsets["DSTOffset"])
    expected = [[at, list(time.gmtime(at + gmt + (dst if at >= _DST_START else 0))[:5])] for at, _cet in local]
    assert [[at, cet[:5] if cet else cet] for at, cet in local] == expected, f"cettime() across the March switch read {local}, not {expected}"
    sync = facts.get("sync")
    assert isinstance(sync, dict) and sync["synced"] is True, f"a clock step cleared Synced: {sync}"
    assert isinstance(sync["age"], int) and abs(sync["age"] - sync["ticks_s"]) <= 1, f"LastSyncAge {sync['age']} after {sync['ticks_s']} s of ticks: {sync}"
