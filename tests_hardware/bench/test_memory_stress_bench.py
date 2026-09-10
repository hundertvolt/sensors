"""Bench-tier automated tests: real firmware memory behavior under HTTP soak traffic (needs a
reachable network, unavailable on flash tier) - generates load over WiFi while passively
tail_log()-watching for a MemoryError or an unexpected mid-soak reboot."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import http_client
import pytest
from error_log_helpers import get_errcount, reset_all_error_logs
from soak_tiers import SOAK_TIER_SECONDS

if TYPE_CHECKING:
    from harness import Board

# The six FRAM-backed modules (SPECIFICATION.md Part A.7) - WIFI/NTP/every CFGMGR_* logger are
# RAM-only. CLAUDE.md's standing rule: read these before clearing state on any unexpected error.
_FRAM_BACKED_MODULES = ("SYSTEM", "SGP40", "BMP3XX", "SCD30", "NEOPIXEL", "NOTIFY")

# 4 GET threads at true max speed (unlike the modest, soak-gated test below) plus 1 thread
# PUTting SGP40.SGPResetVOC every 3s - reproduces the request density that originally found real
# MemoryErrors within 45s. Not soak-tier gated - 120s needs no --soak-tier flag to run.
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
                # At 5 concurrent threads against max_connections=4, ConnectionResetError is the
                # server's intended reject-when-full behavior, not a fault - not asserted against
                # below; only genuine 200s count as proof the server stayed alive (BACKLOG.md open question 7).
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
    # "config is ready"/"FRAM SPI FRAM Driver Setup complete" are the genuinely one-time-per-
    # setup() completion lines, confirmed real reboot signals (see tests_hardware/README.md for
    # why a naive "CFGMGR_" substring check was a false-positive-prone predecessor to this).
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
    """Long-duration form (--soak-tier mid = 600s, matching the one real WDT_RESET this project
    has observed) of the bounded test above - captures FRAM-backed errcount in the assertion
    message before any cleanup clears it (CLAUDE.md's standing rule)."""
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
    # "config is ready"/"FRAM SPI FRAM Driver Setup complete" are the genuinely one-time-per-setup()
    # completion lines - "CFGMGR_" alone is NOT a reboot marker, since it's stamped on every
    # routine per-cycle config read too (see tests_hardware/README.md for the false-positive history).
    reboot_markers = [ln for ln in lines if "config is ready" in ln or "FRAM SPI FRAM Driver Setup complete" in ln]
    assert not crash_markers, "observed a crash/MemoryError during the HTTP soak:\n" + "\n".join(crash_markers)
    assert not reboot_markers, "observed an unexpected mid-soak reboot (real memory exhaustion -> WDT reset?):\n" + "\n".join(reboot_markers) + f"\nfull log:\n{joined}"
    assert len(request_errors) < 5, f"too many failed/non-200 requests during the soak ({len(request_errors)}): {request_errors[:10]}"
