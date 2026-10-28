"""Bench-tier automated tests: real REST-triggered reboot sequencing, concurrent-client-burst
stress, cold-boot-to-first-response latency, and hard resets during natural FRAM backup activity -
all need a reachable network, unavailable on flash tier."""

import threading
import time
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
from error_log_helpers import assert_module_error_log_clean, assert_module_error_log_empty, assert_no_task_ended, code, reset_all_error_logs
from harness import Board, configured_max_connections, kick_then_reset, recover_by_reset, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("webserver_concurrency", "sensortask_integration", "poll_prewarm")

# ---------------------------------------------------------------------------
# A commanded reboot over REST runs the controlled shutdown and resets through the armed timer, never the watchdog, on
# real timing.
# ---------------------------------------------------------------------------


# @tunable l4.end_to_end_timing_reboot_phase_timeout_s = 30.0
_REBOOT_PHASE_TIMEOUT_S = 30.0
# @tunable l4.end_to_end_timing_down_poll_s = 0.5
_DOWN_POLL_S = 0.5
# @tunable l4.end_to_end_timing_reboot_loss_margin_s = 1.5
_REBOOT_LOSS_MARGIN_S = 1.5
# @tunable l4.end_to_end_timing_poll_s = 1.0
_POLL_S = 1.0
# @tunable l4.end_to_end_timing_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.end_to_end_timing_join_timeout_s = 15.0
_JOIN_TIMEOUT_S = 15.0
# @tunable l4.end_to_end_timing_recovery_sanity_timeout_s = 120.0
_RECOVERY_SANITY_TIMEOUT_S = 120.0
# @tunable l4.end_to_end_timing_reset_spacing_s = 25.0
_RESET_SPACING_S = 25.0
# @tunable l4.end_to_end_timing_reset_cycles = 3
_RESET_CYCLES = 3
# @tunable l4.end_to_end_timing_reset_recovery_timeout_s = 60.0
_RESET_RECOVERY_TIMEOUT_S = 60.0
# @tunable l4.end_to_end_timing_backup_advance_timeout_s = 90.0
_BACKUP_ADVANCE_TIMEOUT_S = 90.0
# @tunable l4.end_to_end_timing_backup_poll_s = 5.0
_BACKUP_POLL_S = 5.0
# @tunable l4.end_to_end_timing_restore_recovery_timeout_s = 20.0
_RESTORE_RECOVERY_TIMEOUT_S = 20.0
_SYSTEM = "asy_system_service.py"


def test_real_reboot_sequencing_via_rest_completes_cleanly(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> None:
    # Passive waits only (is_reachable() would stop the fresh main.py): the webserver serves within
    # l4.dut_serving_after_sta_s of STA connect, the generated main() starting it before the first NTP sync.
    task_check_s = _load.src_number(_SYSTEM, "_TASK_CHECK_TIME")
    reset_delay_s = _load.src_number(_SYSTEM, "_RESET_DELAY")
    watchdog_ms = _load.buildgen_number("validate.py", "_WDT_TIMEOUT_MS")
    # The upper bound must exclude a watchdog reset, which records the same reset code.
    assert watchdog_ms - (reset_delay_s + task_check_s) * 1000 > _REBOOT_LOSS_MARGIN_S * 1000, f"the {_REBOOT_LOSS_MARGIN_S}s margin reaches the {watchdog_ms} ms watchdog"
    res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": "reboot"}, timeout_s=_PROBE_TIMEOUT_S)
    replied = time.monotonic()
    assert _load.as_object(res.json().get("result"), "result").get("SystemCmd") == "Valid", f"reboot command was rejected: {res.status_code} {res.body!r}"
    bench.kick_all_stations()  # a genuine machine.reset() follows: no stale AP-side station entry may outlive it
    wait_until(lambda: not board.is_device_present(), timeout_s=_REBOOT_PHASE_TIMEOUT_S, poll_interval_s=_DOWN_POLL_S, description="board to go unreachable (real reboot firing)")
    lost_s = time.monotonic() - replied
    result_note(f"reply to USB loss {lost_s:.2f}s: the armed reset {reset_delay_s:g}s after a shutdown bounded by one {task_check_s:g}s task check")
    assert reset_delay_s <= lost_s <= task_check_s + reset_delay_s + _REBOOT_LOSS_MARGIN_S, f"the reboot reset {lost_s:.2f}s after its reply, outside {reset_delay_s:g}..{task_check_s + reset_delay_s + _REBOOT_LOSS_MARGIN_S:g}s"
    noted = _load.Noted(result_note)
    recover_by_reset(board, bench, ready=lambda: board.is_device_present() and _load.serving(dut_ip), first_wait_s=_REBOOT_PHASE_TIMEOUT_S, retry_wait_s=_REBOOT_PHASE_TIMEOUT_S, skipped="the passive post-reboot wait", note=noted, description="REST reboot")
    if not noted.recovered:  # a recovery reset records its own reason
        reason = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system").get("ResetReason")
        assert reason == _load.src_number(_SYSTEM, "_RR_REBOOT"), f"the REST reboot reads ResetReason {reason!r}, not the reboot's own code (a watchdog reset reads 2)"
    assert_no_task_ended(dut_ip, "a REST reboot")


# ---------------------------------------------------------------------------
# Real concurrent-client-burst stress test - standing robustness validation of the burst scenario
# itself (the segfault this originally chased is confirmed compiled out of real rp2 firmware).
# ---------------------------------------------------------------------------


@pytest.mark.provokes_log(
    "twice the ceiling at once: each connection refused above it logs HTTP_REFUSED",
    ("WEBSERVER", "W", "HTTP_REFUSED"),
    ("WEBSERVER", "W", "HTTP_PEER_RESET"),
)
def test_real_concurrent_client_burst_does_not_crash_the_webserver(dut_ip: str, board: Board) -> None:
    # Twice the build's own ceiling, concurrently, against its reject-when-full policy - so some
    # subset legitimately gets a silent close rather than a crash. The property under test is that
    # the server survives and keeps serving at least the ceiling's own worth of requests.
    _max_connections = configured_max_connections()  # derived from the build, never a restated literal
    n_clients = _max_connections * 2
    results: list[int | str] = [0] * n_clients

    def _client(i: int) -> None:
        try:
            res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=_PROBE_TIMEOUT_S)
            results[i] = res.status_code
        except (OSError, http_client.HTTP_ERROR) as exc:
            results[i] = repr(exc)

    threads: list[threading.Thread] = []
    try:
        for i in range(n_clients):
            thread = threading.Thread(target=_client, args=(i,), name=f"burst-{i}")
            threads.append(thread)
            thread.start()
    finally:
        alive = _load.join(threads, _JOIN_TIMEOUT_S)
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s"

    successes = [r for r in results if r == 200]
    assert len(successes) >= _max_connections, f"only {len(successes)}/{n_clients} concurrent requests succeeded (expected at least the {_max_connections}-connection admission ceiling to be served): {results}"
    # A crash surfacing after the burst rather than during it slips through the per-request results above.
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_PROBE_TIMEOUT_S).status_code == 200, "webserver unresponsive after the concurrent burst"


# ---------------------------------------------------------------------------
# Cold-boot-to-first-response latency: real WiFi-connect + NTP + sensor-init latency, reported.
# Reported with a sanity ceiling, never asserted against a tight bound: boot latency is not a metric (CLAUDE.md), only
# the watchdog feed margins are (SPECIFICATION.md Part F.3).
# ---------------------------------------------------------------------------


def test_cold_boot_to_first_http_response_latency_is_sane(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> None:
    kick_then_reset(board, bench)  # the stale AP-side station entry kicked first, then the one cold reset
    start = time.monotonic()
    # A sanity ceiling only - see the banner above.
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_SANITY_TIMEOUT_S, poll_interval_s=_POLL_S, description="first successful HTTP response after a cold boot")
    result_note(f"cold-boot-to-first-response latency: {time.monotonic() - start:.1f}s")  # reported, never asserted (boot latency is evidence, not a target)


# ---------------------------------------------------------------------------
# Recombination test (owner, 2026-09-04): a real hard_reset() landing at an uncontrolled
# point in FRAM's natural background write activity - SGP40's periodic VOC backup - must leave
# the subsystem healthy. The flash tier's reset race can only land as a write session begins.
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
@pytest.mark.provokes_log(
    "the resets tear some SPI writes: the status byte and block-invalid entries this test's own allow-list names",
    ("FRAM", "W", "FRAM_BLOCK_INVALID"),
    ("FRAM", "E", "FRAM_STATUS_BYTE"),
)
def test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    sgp40 = _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get("SGP40"), "GET /sensors SGP40")
    original_backup_period = sgp40.get("BackupPeriod")
    assert isinstance(original_backup_period, int), f"could not read the current real BackupPeriod before changing it: {original_backup_period!r}"

    # BackupPeriod=1 (minute) is the schema's fastest active cadence (0 disables it entirely) -
    # restored to its original value in the finally block below.
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"BackupPeriod": 1}}, timeout_s=_PROBE_TIMEOUT_S)
    word = _load.as_object(_load.as_object(put_res.json().get("result"), "result").get("SGP40"), "result.SGP40").get("BackupPeriod")
    assert put_res.status_code == 200 and word in ("Valid", "Unchanged"), f"failed to set BackupPeriod=1: {put_res.status_code} {put_res.body!r}"

    try:
        for n in range(1, _RESET_CYCLES + 1):
            time.sleep(_RESET_SPACING_S)  # spread across the 60s backup cadence: each reset lands at another point of it
            kick_then_reset(board, bench)  # the fault itself: a reset the host cannot synchronise to the SPI write
            recover_by_reset(board, bench, ready=lambda: _load.serving(dut_ip), first_wait_s=_RESET_RECOVERY_TIMEOUT_S, retry_wait_s=_RESET_RECOVERY_TIMEOUT_S, skipped="the passive reconnect after this reset", note=result_note, description=f"reset {n} during a natural backup")

        # Full health check, not just "reachable" - the FRAM subsystem specifically must still work.
        assert_module_error_log_empty(dut_ip, "SGP40")
        # Three hard resets inside real SPI writes are meant to tear some: only a status byte left neither idle nor
        # uninitialised and the block-invalid repair warning are allowed, and a fresh backup must still complete below
        # (owner, 2026-09-13, on the torn-write trace: "Settled as acceptable degradation rather than a robustness gap").
        assert_module_error_log_clean(dut_ip, "FRAM", allowed_warnings=(code("W", "FRAM_BLOCK_INVALID"),), allowed_errors=(code("E", "FRAM_STATUS_BYTE"),))

        # One more real backup completing cleanly after all three resets proves the FRAM subsystem
        # itself is still genuinely functional, not merely "board reachable".
        backup_ts_before = _backup_ts(dut_ip)
        wait_until(lambda: _backup_ts(dut_ip) not in (None, backup_ts_before), timeout_s=_BACKUP_ADVANCE_TIMEOUT_S, poll_interval_s=_BACKUP_POLL_S, description="a fresh real SGP40 VOC backup completing after the reset sequence")
        assert_no_task_ended(dut_ip, "hard resets during natural FRAM backup activity")
    finally:
        recover_by_reset(board, bench, ready=lambda: _load.serving(dut_ip), first_wait_s=_RESTORE_RECOVERY_TIMEOUT_S, retry_wait_s=_RESET_RECOVERY_TIMEOUT_S, skipped="the passive reconnect before the BackupPeriod restore", note=result_note, description="reachability for the BackupPeriod restore")
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"BackupPeriod": original_backup_period}}, timeout_s=_PROBE_TIMEOUT_S)
        word = _load.as_object(_load.as_object(restore_res.json().get("result"), "result").get("SGP40"), "result.SGP40").get("BackupPeriod")
        assert word in ("Valid", "Unchanged"), f"failed to restore BackupPeriod to {original_backup_period}: {restore_res.status_code} {restore_res.body!r}"
        reset_all_error_logs(dut_ip, request.node.name)


def _backup_ts(dut_ip: str) -> object:
    # GET /status's SGP40 BackupTS, None while the board does not answer.
    try:
        sensors = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("sensors"), "GET /status sensors")
        return _load.as_object(sensors.get("SGP40"), "GET /status sensors.SGP40").get("BackupTS")
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError):
        return None
