"""Bench-tier automated test, Part 1 category D subset (tmp_hardware_test_candidates.md item 16,
moved here from flash - see tests_hardware/flash/test_memory_stress.py's own module docstring for
why: this candidate's own description needs "real firmware under HTTP soak traffic", which needs a
reachable network client, unavailable on flash tier).

Design note - why this doesn't sample gc.mem_free() directly the way the digital twin's own
recovery-peak-trend soak does (digital_twin/run_wozi_integration.py): doing that here would need
repeated harness.Board.exec() calls interleaved with the HTTP soak traffic, but exec() always
interrupts the live system first (see run_isolated()'s own docstring) - a KeyboardInterrupt into a
running asyncio.run() call does not resume on its own once the raw-REPL session ends, so repeated
sampling this way would permanently kill the live system partway through its own soak. Real HTTP
soak traffic is generated over WiFi only (http_client, never touching the serial console), in
parallel with a purely passive tail_log() watch for the two disqualifying symptoms genuinely
observable without disturbing anything: a MemoryError traceback, or an unexpected mid-soak reboot."""

from __future__ import annotations

import threading

import http_client
import pytest
from error_log_helpers import get_errcount, reset_all_error_logs
from harness import Board
from soak_tiers import SOAK_TIER_SECONDS

# The six modules SPECIFICATION.md Part A.7's seven-chunk FRAM layout backs (WIFI/NTP/every
# CFGMGR_* logger are RAM-only, don't survive a reboot - see error_log_helpers.py's own docstring).
# CLAUDE.md's own standing rule (added 2026-09-08, after the single real WDT_RESET's own evidence
# was lost to routine ResetErrors cleanup before anyone thought to check): read these before
# clearing state on any unexpected error.
_FRAM_BACKED_MODULES = ("SYSTEM", "SGP40", "BMP3XX", "SCD30", "NEOPIXEL", "NOTIFY")

# Bounded, automated form of the max-speed "hammer load" methodology used ad-hoc across several
# real-hardware investigations (BACKLOG.md's memory-safety-audit hand-off notes and the
# /status-streaming fix): 4 GET threads at true max speed (no throttle - unlike the modest,
# @pytest.mark.long_soak-gated 0.2s-interval test below, this deliberately reproduces the request
# density that originally found real MemoryErrors within 45s) plus 1 thread PUTting
# SGP40.SGPResetVOC every 3s, matching the original investigation's own client mix exactly. Not
# soak-tier gated - 120s comfortably fits the same "reproduces within 10 minutes" budget every
# other dedicated real-hardware test in this session used, and needs no --soak-tier flag to run.
_HAMMER_DURATION_S = 120.0
_HAMMER_PATHS = ("/measurements", "/sensors")
_HAMMER_THREAD_COUNT = 4


def _run_max_speed_hammer_load(board: Board, dut_ip: str, duration_s: float) -> tuple[list[str], int, list[str]]:
    stop = threading.Event()
    request_errors: list[str] = []
    success_count = 0
    lock = threading.Lock()

    def _get_hammer(thread_index: int) -> None:
        nonlocal success_count
        i = thread_index
        while not stop.is_set():
            path = _HAMMER_PATHS[i % len(_HAMMER_PATHS)]
            i += 1
            try:
                res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=5.0)
                with lock:
                    if res.status_code == 200:
                        success_count += 1
                    else:
                        request_errors.append(f"GET {path} -> {res.status_code}")
            except OSError as exc:
                # REAL FINDING (this helper's own first run): at 4 GET threads + 1 PUT thread (5
                # concurrent) against asy_webserver_service.py's max_connections=4 (BACKLOG.md's
                # own open question 7), ConnectionResetError is the server's *intended*
                # reject-when-full behavior under deliberately oversubscribed max-speed load, not
                # a fault - confirmed real (740/~3000 requests) in that run, with zero
                # MemoryErrors/reboots. Not asserted against by either caller below; only genuine
                # 200s count as proof the server stayed alive and responsive throughout.
                with lock:
                    request_errors.append(f"GET {path} -> {exc!r}")

    def _reset_voc_periodically() -> None:
        nonlocal success_count
        while not stop.wait(3.0):
            try:
                res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=5.0)
                with lock:
                    if res.status_code == 200:
                        success_count += 1
                    else:
                        request_errors.append(f"PUT /sensors SGPResetVOC -> {res.status_code}")
            except OSError as exc:
                with lock:
                    request_errors.append(f"PUT /sensors SGPResetVOC -> {exc!r}")

    threads = [threading.Thread(target=_get_hammer, args=(i,), daemon=True) for i in range(_HAMMER_THREAD_COUNT)]
    threads.append(threading.Thread(target=_reset_voc_periodically, daemon=True))
    for t in threads:
        t.start()
    try:
        lines = board.tail_log(duration_s=duration_s)
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=10.0)
    return lines, success_count, request_errors


def _assert_no_crash_or_reboot(lines: list[str]) -> None:
    joined = "\n".join(lines)
    # "config is ready"/"FRAM SPI FRAM Driver Setup complete" are config_manager.py's/
    # asy_fram_driver.py's own genuinely one-time-per-setup() completion lines, confirmed real
    # reboot signals (see the soak test below for the false-positive history of a naive
    # "CFGMGR_" substring check).
    crash_markers = [ln for ln in lines if "MemoryError" in ln or "Traceback" in ln]
    reboot_markers = [ln for ln in lines if "config is ready" in ln or "FRAM SPI FRAM Driver Setup complete" in ln]
    assert not crash_markers, "observed a crash/MemoryError during max-speed hammer load:\n" + "\n".join(crash_markers)
    assert not reboot_markers, "observed an unexpected mid-hammer reboot (real memory exhaustion -> WDT reset?):\n" + "\n".join(reboot_markers) + f"\nfull log:\n{joined}"


def test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    lines, success_count, request_errors = _run_max_speed_hammer_load(board, dut_ip, _HAMMER_DURATION_S)
    _assert_no_crash_or_reboot(lines)
    # A real success requires the webserver to have actually accepted, processed, and responded to
    # the request with valid JSON while under load - proof the server stayed alive and responsive
    # throughout, not just that no crash marker appeared in the log (which a fully-wedged-but-
    # not-crashed server would also satisfy). max_connections=4 rejections are expected and not
    # counted against this - see _run_max_speed_hammer_load()'s own reject-when-full comment.
    assert success_count > 100, f"too few successful requests got through during the hammer load ({success_count} ok, {len(request_errors)} rejected/errored) - server may have wedged"
    reset_all_error_logs(dut_ip)


@pytest.mark.long_soak
def test_real_hardware_survives_extended_max_speed_hammer_load_with_fram_diagnostics_preserved(board: Board, dut_ip: str, request: pytest.FixtureRequest) -> None:
    """Long-duration (--soak-tier mid = 600s, matching the original ad-hoc investigation's own
    hammer-load duration that preceded the one real WDT_RESET this project has ever observed -
    BACKLOG.md's now-closed WDT-reset entry) form of the bounded test above, for tracing a
    recurrence if one ever happens. Two things this adds beyond the bounded test: (1) the real
    duration the original reset actually followed, not just a 120s bounded sample; (2) explicit
    FRAM-backed errcount capture in the assertion message itself, so a real recurrence leaves
    traceable evidence in this test's own failure output - CLAUDE.md's own standing rule (a FRAM-
    backed module's error history is the one piece of diagnostic evidence a reboot doesn't erase,
    and is irreversibly lost the moment anything calls ResetErrors afterward, which is exactly what
    happened to the original occurrence's own evidence)."""
    tier = request.config.getoption("--soak-tier")
    if tier is None:
        pytest.skip("real extended max-speed hammer load - run via scripts/run_bench_soak_tests.sh --tier mid (600s, matching the original WDT-reset investigation's own duration)")
    duration_s = SOAK_TIER_SECONDS[tier]
    reset_all_error_logs(dut_ip)
    lines, success_count, request_errors = _run_max_speed_hammer_load(board, dut_ip, duration_s)
    errcount_after = get_errcount(dut_ip)
    fram_errcount_after = {mod: errcount_after[mod] for mod in _FRAM_BACKED_MODULES if errcount_after.get(mod, {}).get("counter", 0) > 0}
    try:
        _assert_no_crash_or_reboot(lines)
        assert not fram_errcount_after, f"a FRAM-backed module logged a real error during the hammer load - real diagnostic evidence, captured before any cleanup: {fram_errcount_after!r}"
        assert success_count > 100, f"too few successful requests got through during the hammer load ({success_count} ok, {len(request_errors)} rejected/errored) - server may have wedged"
    finally:
        # Deliberately only cleared AFTER the assertions above have already captured/reported
        # whatever FRAM-backed history existed - never clear before a failure had the chance to
        # surface it, per this file's own new standing rule.
        reset_all_error_logs(dut_ip)


@pytest.mark.long_soak
def test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic(board: Board, dut_ip: str, request: pytest.FixtureRequest) -> None:
    tier = request.config.getoption("--soak-tier")
    if tier is None:
        pytest.skip("real HTTP soak, one of three named duration tiers - run via scripts/run_bench_soak_tests.sh --tier {short,mid,long}")
    duration_s = SOAK_TIER_SECONDS[tier]
    stop = threading.Event()
    request_errors: list[str] = []

    def _hammer() -> None:
        paths = ("/measurements", "/sensors", "/status", "/networking")
        i = 0
        while not stop.is_set():
            path = paths[i % len(paths)]
            i += 1
            try:
                res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=5.0)
                if res.status_code != 200:
                    request_errors.append(f"GET {path} -> {res.status_code}")
            except OSError as exc:  # a real transient network hiccup during a long soak is expected sometimes
                request_errors.append(f"GET {path} -> {exc!r}")
            stop.wait(0.2)  # a modest, sustained request rate - not a flood (that's item 17's job)

    hammer_thread = threading.Thread(target=_hammer, daemon=True)
    hammer_thread.start()
    try:
        lines = board.tail_log(duration_s=duration_s)
    finally:
        stop.set()
        hammer_thread.join(timeout=10.0)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "MemoryError" in ln or "Traceback" in ln]
    # REAL FINDING, fixed (2026-09-04): "CFGMGR_" is NOT a one-time boot marker - it's the module-
    # tag prefix ConfigManager's PrintLogHistory logger stamps on EVERY log line from that logger,
    # including ordinary, routine per-cycle reads (e.g. SGP40's own periodic backup-period check
    # logs "CFGMGR_SGP40 config_SGP40.cfg - Reading config data into list." once per read cycle,
    # confirmed directly against a real soak run's own log - this fired constantly, not once).
    # This made the old check a near-guaranteed false positive on any real soak run long enough to
    # see one ordinary config read, and false negative on a real reboot that had no such read yet.
    # config_manager.py's own three genuinely one-time-per-setup() messages all end "- config is
    # ready." / "found." after a fresh load - "config is ready" (config_manager.py's own two
    # setup-completion lines) is the correct, confirmed-real one-time signal; "SPI FRAM Driver
    # Setup complete" (asy_fram_driver.py, tagged "FRAM" by its own logger) was already correct.
    reboot_markers = [ln for ln in lines if "config is ready" in ln or "FRAM SPI FRAM Driver Setup complete" in ln]
    assert not crash_markers, "observed a crash/MemoryError during the HTTP soak:\n" + "\n".join(crash_markers)
    assert not reboot_markers, "observed an unexpected mid-soak reboot (real memory exhaustion -> WDT reset?):\n" + "\n".join(reboot_markers) + f"\nfull log:\n{joined}"
    assert len(request_errors) < 5, f"too many failed/non-200 requests during the soak ({len(request_errors)}): {request_errors[:10]}"
