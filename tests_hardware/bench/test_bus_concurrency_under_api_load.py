"""Bench-tier automated test: heavily loads the real I2C buses *through the full production HTTP
stack* (concurrent host-side threads hammering the real REST API), the project owner's own suggested
bench-tier angle on SPECIFICATION.md Part C.8's locking model - complementing
tests_hardware/flash/test_bus_concurrency.py's direct-driver-level tests (no webserver/HTTP in the
loop there) with the same hazard proven under genuine multi-client, full-stack concurrent load.

GET /sensors (not /measurements) is the real bus-touching endpoint here: SCD30_Reader.get_dict_cfg()/
BMP3xx_Reader.get_dict_cfg() both wire a live callback (_read_sensor_dict()) that issues a real
get_config_snapshot() bus read on every single call (asy_scd30_driver.py/asy_bmp3xx_driver.py's own
torn-read-closing comments) - unlike GET /measurements, which only ever returns whatever the
background read_loop() task last cached (SensorReader._get_meas_data(), pure in-RAM, no bus I/O at
all) and so cannot exercise this at all. Concurrent GET /sensors calls from multiple real HTTP
clients therefore drive real concurrent SCD30 (i2c1)/BMP3xx (i2c0) bus reads through the exact same
device-session/bus-lock machinery the flash tier tests directly, but arriving from independent
Microdot connection-task coroutines instead of this test's own hand-written asyncio.gather().

Real-hardware write-budget constraints (same as the flash tier - see
tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py's own docstring): this test issues
zero PUT requests that persist to the RP2040's flash-backed ConfigManager, and zero additional SCD30
NVM writes. The one PUT used here (SGP40's `SGPResetVOC`) is explicitly documented as command-only,
never persisted (asy_sgp40_driver.py's own `_VAL_RESET` comment, confirmed directly by
bench/test_sensor_config_push_over_real_hardware.py's own test for it) - triggering SGP40's real
general-call reset broadcast (SPECIFICATION.md Part C.8's "Known structural gap" finding) to land
concurrently with the GET-driven SCD30/BMP3xx bus reads above, the full-stack counterpart of
tests_hardware/flash/device_scripts/sgp40_general_call_reset_hazard.py's direct-driver version."""

from __future__ import annotations

import threading

import http_client
from bench_control import BenchBridge
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import Board, wait_until

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0

# REAL FINDING, fixed: the total concurrent worker count is _GET_WORKERS + 1 (the SGP40 reset
# thread runs alongside, not instead of, the GET workers) - the original _GET_WORKERS=3 made that
# 4, exactly *at* the real max_connections=4 ceiling (asy_webserver_service.py) with zero margin,
# not "safely under" it as this comment claimed. Confirmed directly on real hardware: a first real
# run failed with a genuine ConnectionResetError on the SGP40 reset thread's very first request -
# the same real accept-loop-lag/reject-when-full behavior
# test_connections_at_and_above_the_real_socket_limit_degrade_cleanly already proves is correct,
# just with no headroom here to absorb even a brief overlap between two workers' own real HTTP
# request/response cycles over a genuine wireless link. 2 (+1 SGP40 thread = 3 total) leaves real
# margin; this test's own job is bus contention under load, not re-proving the connection-accept
# limit (see test_end_to_end_timing.py's own connections-at-the-limit test for that boundary
# itself).
_GET_WORKERS = 2
_GET_ITERATIONS_PER_WORKER = 8
_PUT_RESET_COUNT = 2


def test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)

    errors: list[str] = []
    errors_lock = threading.Lock()

    def _record(msg: str) -> None:
        with errors_lock:
            errors.append(msg)

    def get_sensors_worker(worker_id: int) -> None:
        for i in range(_GET_ITERATIONS_PER_WORKER):
            try:
                res = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=15.0)
            except Exception as e:  # noqa: BLE001 - a real connection-level failure under load is itself worth surfacing
                _record(f"worker {worker_id} iter {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200:
                _record(f"worker {worker_id} iter {i}: GET /sensors returned {res.status_code}: {res.body!r}")
                continue
            body = res.json()
            scd30 = body.get("SCD30", {})
            bmp = body.get("BMP3XX", {})
            meas_int = scd30.get("MeasInt")
            if meas_int is not None and not (2 <= meas_int <= 1800):
                _record(f"worker {worker_id} iter {i}: SCD30 MeasInt={meas_int!r} outside valid schema range - possible torn/corrupted config read")
            press_overs = bmp.get("PressOvers")
            if press_overs is not None and press_overs not in (1, 2, 4, 8, 16, 32):
                _record(f"worker {worker_id} iter {i}: BMP3XX PressOvers={press_overs!r} outside valid schema range - possible torn/corrupted config read")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=15.0)
            except Exception as e:  # noqa: BLE001 - see get_sensors_worker's own comment
                _record(f"sgp40 reset {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200 or res.json().get("result", {}).get("SGP40", {}).get("SGPResetVOC") != "Valid":
                _record(f"sgp40 reset {i}: PUT /sensors SGPResetVOC rejected: {res.status_code} {res.body!r}")

    threads = [threading.Thread(target=get_sensors_worker, args=(w,)) for w in range(_GET_WORKERS)]
    threads.append(threading.Thread(target=sgp40_reset_trigger_worker))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120.0)
        assert not t.is_alive(), "a worker thread never finished within 120s - possible real deadlock under concurrent load"

    assert not errors, f"{len(errors)} issue(s) under concurrent API load: {'; '.join(errors[:10])}"

    # REAL FINDING, fixed: a real WiFi reconnect blip (this bench's own already-documented,
    # unresolved flakiness - BACKLOG.md open question 6, not a bus-hazard-specific issue) can land
    # right after this heavy concurrent load finishes, surfacing as a transient GET /status 500 on
    # the very next call - confirmed directly, on real hardware: a real run hit exactly this, then
    # self-healed within seconds (a follow-up GET /status came back 200, WifiUptime reset to a low
    # value confirming a recent reconnect). Give the server a real chance to settle before the
    # error-log checks below, the same pattern already used elsewhere in this tier for a heavy-load
    # settle (e.g. test_connections_at_and_above_the_real_socket_limit_degrade_cleanly's own final
    # check).
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after the concurrent bus-load test",
    )

    # The whole system must have stayed genuinely healthy through this, not just "no thread hung" -
    # per the standing error-log policy (tests_hardware/README.md), a clean pass leaves nothing
    # behind for either SCD30 or BMP3XX (whose config-snapshot reads this test drove directly) or
    # SGP40 (whose real general-call reset this test triggered concurrently with those reads).
    # FRAM has no dedicated REST-triggered synchronous write path to drive directly the way
    # GET /sensors does for SCD30/BMP3xx above (its own writes happen on each sensor's periodic
    # error-log/VOC-backup cycle, not on-demand) - but every one of those sensors' own error-log
    # writes above this same heavy concurrent load already lands on FRAM, so confirming FRAM itself
    # reported nothing wrong is real, meaningful coverage of it staying healthy under this load too.
    for module in ("SCD30", "BMP3XX", "SGP40", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)

    # Final sanity: the real system is still serving plausible measurements after the load, not
    # left in some degraded state.
    res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=10.0)
    assert res.status_code == 200, f"GET /measurements after the load test failed: {res.status_code} {res.body!r}"
    body = res.json()
    co2 = body.get("SCD30", {}).get("CO2")
    pressure = body.get("BMP3XX", {}).get("Pres")
    if co2 is not None:
        assert CO2_MIN_PPM <= co2 <= CO2_MAX_PPM, f"post-load CO2={co2!r} outside plausible bounds"
    if pressure is not None:
        assert PRESSURE_MIN_HPA <= pressure <= PRESSURE_MAX_HPA, f"post-load Pres={pressure!r} outside plausible bounds"

    reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Compound fault: the same real bus contention above, but with a real, sustained network
# degradation also active - the "everything realistic happens at once" axis identified via a
# bird's-eye gap review (2026-09-04): every other test in this file proves bus-hazard concurrency
# under a clean network, and every degradation test in test_network_resilience.py proves recovery
# under a clean, single-client load - nothing combines the two, even though a real deployed unit
# experiences imperfect WiFi and concurrent client traffic simultaneously as a matter of course, not
# as two separate incidents. Uses test_network_resilience.py's own researched "everyday congestion"
# range (loss_pct=2, delay_ms=30, jitter_ms=20 - test_real_operations_unaffected_by_light_realistic_
# wifi_congestion's own parameters), not the severe/sustained range: the property under test here is
# bus-lock correctness surviving realistic background network noise stacked on top of concurrent
# load, not a second, redundant proof that severe degradation alone is survivable (already proven
# above without bus contention in the mix).
# ---------------------------------------------------------------------------


def test_concurrent_get_sensors_under_real_multi_client_load_survives_light_network_degradation(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)

    corruption: list[str] = []
    corruption_lock = threading.Lock()

    def _record(msg: str) -> None:
        with corruption_lock:
            corruption.append(msg)

    def get_sensors_worker(worker_id: int) -> None:
        for i in range(_GET_ITERATIONS_PER_WORKER):
            try:
                res = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=20.0)
            except Exception:  # noqa: BLE001 - an individual request failing under real, injected network
                # degradation is expected here, not itself a finding (test_network_resilience.py's own
                # "a bounded retry loop eventually gets through" philosophy) - only genuine data
                # corruption below is what this test actually exists to catch.
                continue
            if res.status_code != 200:
                continue
            body = res.json()
            scd30 = body.get("SCD30", {})
            bmp = body.get("BMP3XX", {})
            meas_int = scd30.get("MeasInt")
            if meas_int is not None and not (2 <= meas_int <= 1800):
                _record(f"worker {worker_id} iter {i}: SCD30 MeasInt={meas_int!r} outside valid schema range under degraded network - possible torn/corrupted config read")
            press_overs = bmp.get("PressOvers")
            if press_overs is not None and press_overs not in (1, 2, 4, 8, 16, 32):
                _record(f"worker {worker_id} iter {i}: BMP3XX PressOvers={press_overs!r} outside valid schema range under degraded network - possible torn/corrupted config read")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=20.0)
            except Exception:  # noqa: BLE001 - same "expected under degradation" reasoning as above
                continue
            if res.status_code == 200:
                result = res.json().get("result", {}).get("SGP40", {}).get("SGPResetVOC")
                if result not in ("Valid", None):  # None = this specific PUT's own body didn't even parse right under the noise - a connection-level symptom already covered by the bare except above, not a bus-corruption finding
                    _record(f"sgp40 reset {i}: unexpected non-Valid result under degraded network: {result!r}")

    bench.inject_network_degradation(loss_pct=2, delay_ms=30, jitter_ms=20)
    try:
        threads = [threading.Thread(target=get_sensors_worker, args=(w,)) for w in range(_GET_WORKERS)]
        threads.append(threading.Thread(target=sgp40_reset_trigger_worker))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=180.0)  # generous over the plain-load test's 120s - real, individually-retried requests under injected loss/latency legitimately take longer
            assert not t.is_alive(), "a worker thread never finished within 180s under degraded network - possible real deadlock, not just slow requests"
    finally:
        bench.clear_network_degradation()

    assert not corruption, f"{len(corruption)} real data-corruption finding(s) under concurrent bus load + degraded network: {'; '.join(corruption[:10])}"

    # Full recovery once the degradation clears - same "not left in some lingering half-degraded
    # state" property test_real_operations_survive_and_recover_under_sustained_packet_loss_and_latency
    # already proves for the no-bus-load case.
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after concurrent bus load + degraded network",
    )
    for module in ("SCD30", "BMP3XX", "SGP40", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip)
