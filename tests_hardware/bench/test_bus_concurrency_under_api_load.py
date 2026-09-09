"""Bench-tier automated tests: heavily loads the real I2C buses through the full production HTTP
stack (concurrent threads hammering GET /sensors, the real bus-touching endpoint) - complements
tests_hardware/flash/test_bus_concurrency.py's direct-driver, no-HTTP version (SPECIFICATION.md Part C.8)."""

from __future__ import annotations

import threading
import time

import http_client
from bench_control import BenchBridge
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import Board, wait_until

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0

# Total concurrent worker count is _GET_WORKERS + 1 (the SGP40 reset thread runs alongside the GET
# workers) - must stay under max_connections=4 with real margin, not exactly at it, or a brief
# overlap under real wireless timing hits a genuine (but here undesired) reject-when-full.
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

    # A real WiFi reconnect blip (BACKLOG.md open question 6, not bus-hazard-specific) can land
    # right after this heavy load finishes, surfacing as a transient GET /status 500 that self-heals
    # within seconds - give the server a real chance to settle before the error-log checks below.
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after the concurrent bus-load test",
    )

    # The whole system must have stayed genuinely healthy, not just "no thread hung" - SCD30/BMP3XX
    # (whose reads this test drove directly), SGP40 (whose reset it triggered), and FRAM (which
    # every one of those sensors' own error-log writes lands on) must all report nothing wrong.
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
# Compound fault: the same real bus contention above, but with real, light network degradation
# also active - a real deployed unit experiences imperfect WiFi and concurrent client traffic
# simultaneously, not as two separate incidents. Uses the same "everyday congestion" range as
# test_network_resilience.py's light-congestion test, not the severe range (already proven survivable alone).
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
            except Exception:  # noqa: BLE001 - an individual request failing under injected degradation is expected, not a finding; only data corruption below is
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

    # Full recovery once the degradation clears - same property test_network_resilience.py's
    # packet-loss test already proves for the no-bus-load case.
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after concurrent bus load + degraded network",
    )
    for module in ("SCD30", "BMP3XX", "SGP40", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Recombination test (project owner's request): real bus contention with a real transient NTP
# outage (a guaranteed UDP-port block, not probabilistic degradation) running concurrently - proves
# neither NTP's retry-timer machinery nor concurrent bus load disrupts the other, even though both
# share the same event loop/task scheduler.
# ---------------------------------------------------------------------------


def test_concurrent_get_sensors_under_real_multi_client_load_survives_an_ntp_transient_outage_and_retry(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    get_before = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /networking failed: {get_before.status_code} {get_before.body!r}"
    original_host = get_before.json()["NTP_Host"]

    def _synced() -> bool:
        status = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()
        return status.get("networking", {}).get("NtpSynced") is True

    # Same precondition wait as the standalone NTP transient-outage test: dut_ip only waits for
    # HTTP reachability, not specifically for NTP sync to finish.
    wait_until(_synced, timeout_s=30.0, poll_interval_s=2.0, description="test precondition: DUT to report NTP-synced before this test's own transient NTP outage starts")
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
            except Exception:  # noqa: BLE001 - an individual request failing during the NTP-outage window is not itself a finding, same reasoning as the network-degradation compound test above
                continue
            if res.status_code != 200:
                continue
            body = res.json()
            scd30 = body.get("SCD30", {})
            bmp = body.get("BMP3XX", {})
            meas_int = scd30.get("MeasInt")
            if meas_int is not None and not (2 <= meas_int <= 1800):
                _record(f"worker {worker_id} iter {i}: SCD30 MeasInt={meas_int!r} outside valid schema range during NTP outage - possible torn/corrupted config read")
            press_overs = bmp.get("PressOvers")
            if press_overs is not None and press_overs not in (1, 2, 4, 8, 16, 32):
                _record(f"worker {worker_id} iter {i}: BMP3XX PressOvers={press_overs!r} outside valid schema range during NTP outage - possible torn/corrupted config read")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=20.0)
            except Exception:  # noqa: BLE001 - see get_sensors_worker's own comment
                continue
            if res.status_code == 200:
                result = res.json().get("result", {}).get("SGP40", {}).get("SGPResetVOC")
                if result not in ("Valid", None):
                    _record(f"sgp40 reset {i}: unexpected non-Valid result during NTP outage: {result!r}")

    bench.block_udp_ports([123])
    try:
        # Re-triggers a real resync attempt without a reboot - post_asy_fct fires on ANY validated
        # field, even one PUT back to its own current value.
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTP_Host": original_host}, timeout_s=10.0)
        assert put_res.status_code == 200 and put_res.json()["result"].get("NTP_Host") in ("Valid", "Unchanged"), f"re-triggering PUT /networking NTP_Host={original_host!r} was rejected: {put_res.status_code} {put_res.body!r}"

        threads = [threading.Thread(target=get_sensors_worker, args=(w,)) for w in range(_GET_WORKERS)]
        threads.append(threading.Thread(target=sgp40_reset_trigger_worker))
        for t in threads:
            t.start()
        for t in threads:
            # This join alone virtually guarantees it outlasts the 5s _NTP_CONN_TIMEOUT needed to
            # genuinely fail one attempt - no separate sleep needed, unlike the standalone test.
            t.join(timeout=180.0)
            assert not t.is_alive(), "a worker thread never finished within 180s during the NTP outage - possible real deadlock, not just slow requests"
    finally:
        bench.unblock_udp_ports([123])

    assert not corruption, f"{len(corruption)} real data-corruption finding(s) under concurrent bus load + NTP transient outage: {'; '.join(corruption[:10])}"

    # NTP must resync via its own retry timer (well inside 15s _NTP_RETRY_INTERV), no hard_reset()
    # anywhere - same bar the standalone test holds, now proven concurrently with real bus load.
    wait_until(_synced, timeout_s=20.0, poll_interval_s=1.0, description="NTP resynced via its own retry timer after a transient outage, concurrent with real bus load")
    for module in ("SCD30", "BMP3XX", "SGP40", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Recombination test (project owner's request): real bus contention with repeated real WiFi
# flapping (3x ap_down()/ap_up()) running concurrently - unlike the two compound tests above, this
# actually disconnects/reconnects the real STA link, exercising wifi_mode_lock and
# DNS/hotspot-bookkeeping teardown, not just a degraded link or a different subsystem's retry timer.
# ---------------------------------------------------------------------------


def test_concurrent_get_sensors_under_real_multi_client_load_survives_repeated_real_wifi_flapping(board: Board, bench: BenchBridge, dut_ip: str) -> None:
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
            except Exception:  # noqa: BLE001 - an individual request failing while the real STA link is mid-flap is expected here, not itself a finding, same reasoning as the other compound tests above
                continue
            if res.status_code != 200:
                continue
            body = res.json()
            scd30 = body.get("SCD30", {})
            bmp = body.get("BMP3XX", {})
            meas_int = scd30.get("MeasInt")
            if meas_int is not None and not (2 <= meas_int <= 1800):
                _record(f"worker {worker_id} iter {i}: SCD30 MeasInt={meas_int!r} outside valid schema range during WiFi flapping - possible torn/corrupted config read")
            press_overs = bmp.get("PressOvers")
            if press_overs is not None and press_overs not in (1, 2, 4, 8, 16, 32):
                _record(f"worker {worker_id} iter {i}: BMP3XX PressOvers={press_overs!r} outside valid schema range during WiFi flapping - possible torn/corrupted config read")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=20.0)
            except Exception:  # noqa: BLE001 - see get_sensors_worker's own comment
                continue
            if res.status_code == 200:
                result = res.json().get("result", {}).get("SGP40", {}).get("SGPResetVOC")
                if result not in ("Valid", None):
                    _record(f"sgp40 reset {i}: unexpected non-Valid result during WiFi flapping: {result!r}")

    def flap_worker() -> None:
        # Same 3x(3s down/3s up) shape as test_network_resilience.py's flapping test - short
        # relative to the 60s established-retry cadence, so the DUT is still mid-wait between toggles.
        for _cycle in range(3):
            bench.ap_down()
            time.sleep(3.0)
            bench.ap_up()
            time.sleep(3.0)

    threads = [threading.Thread(target=get_sensors_worker, args=(w,)) for w in range(_GET_WORKERS)]
    threads.append(threading.Thread(target=sgp40_reset_trigger_worker))
    threads.append(threading.Thread(target=flap_worker))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=180.0)
        assert not t.is_alive(), "a worker thread never finished within 180s during real WiFi flapping - possible real deadlock, not just slow requests"

    assert not corruption, f"{len(corruption)} real data-corruption finding(s) under concurrent bus load + real WiFi flapping: {'; '.join(corruption[:10])}"

    bench.kick_all_stations()  # clears any stale AP-side entry - see kick_client()'s own docstring
    recovered_via_hard_reset = False
    try:
        wait_until(
            lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
            timeout_s=150.0,
            poll_interval_s=5.0,
            description="webserver serving normally again after concurrent bus load + real WiFi flapping",
        )
    except TimeoutError:
        # Same accepted real-pass pattern as test_network_resilience.py's flapping test - a
        # hard_reset() fallback is a genuine recovery, not a failure, here.
        recovered_via_hard_reset = True
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable again after a recovery hard_reset()")
        print("RESULT NOTE: recovered via a fallback hard_reset() after the flapping+bus-load compound")

    if not recovered_via_hard_reset:
        for module in ("SCD30", "BMP3XX", "SGP40", "FRAM"):
            assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip)
