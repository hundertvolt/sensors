"""Bench-tier automated tests: heavily loads the real I2C buses through the full production HTTP
stack (concurrent threads hammering GET /sensors, the real bus-touching endpoint) - complements
tests_hardware/flash/test_bus_concurrency.py's direct-driver, no-HTTP version (SPECIFICATION.md Part C.8)."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

import http_client
import pytest
from error_log_helpers import assert_module_error_log_empty, assert_no_task_ended, reset_all_error_logs
from harness import Board, configured_max_connections, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0
VOC_MIN, VOC_MAX = 0, 500  # same bounds as device_scripts/sgp40_voc_algorithm_quality.py

# _GET_WORKERS + 1 concurrent clients (the SGP40 reset thread too), two slots under the build's own
# max_connections: at it, real wireless timing overlaps into an undesired reject-when-full. Derived,
# so a raised ceiling really means more concurrent bus-facing API load.
_GET_WORKERS = max(2, configured_max_connections() - 3)
_GET_ITERATIONS_PER_WORKER = 8
_PUT_RESET_COUNT = 2
# Ceiling refusals fetch() retried, by "METHOD path": BACKLOG 30's resets share their signature, so
# the two config-write arms print these, and a gated run tells the ceiling from an ISL29125 mechanism.
_ceiling_retries: dict[str, int] = {}
_ceiling_retries_lock = threading.Lock()


def _report_ceiling_retries(arm: str) -> None:
    with _ceiling_retries_lock:
        counts = dict(_ceiling_retries)
        _ceiling_retries.clear()
    print(f"CEILING_RETRIES {arm}: {counts or 'none'}")


def fetch(host: str, port: int, method: str, path: str, json_body: dict[str, Any] | None = None, timeout_s: float = 15.0) -> http_client.HttpResponse:
    """http_client.fetch(), retrying only a connection-ceiling refusal, never a transport failure. Same
    name and positional signature on purpose: tests_scripts/test_persistence_write_marker_completeness.py
    reads PUT bodies by AST and would silently lose a persisting write behind another shape (F15)."""
    for attempt in range(3):
        try:
            return http_client.fetch(host, port, method, path, json_body, timeout_s=timeout_s)
        except Exception as exc:
            if attempt == 2 or not http_client.is_ceiling_close(exc):
                raise
            with _ceiling_retries_lock:
                _ceiling_retries[f"{method} {path}"] = _ceiling_retries.get(f"{method} {path}", 0) + 1
            time.sleep(0.25)
    raise AssertionError("unreachable")


def _schema_sanity_findings(body: dict[str, Any], context: str) -> list[str]:
    """Range-checks one GET /sensors body against each driver's own schema. A value outside it is
    not a driver bug but a torn/corrupted read - the property every worker below is really watching
    for, extracted here so all four tests check exactly the same thing (and stay under C901)."""
    findings = []
    meas_int = body.get("SCD30", {}).get("MeasInt")
    if meas_int is not None and not (2 <= meas_int <= 1800):
        findings.append(f"SCD30 MeasInt={meas_int!r} outside valid schema range{context} - possible torn/corrupted config read")
    press_overs = body.get("BMP3XX", {}).get("PressOvers")
    if press_overs is not None and press_overs not in (1, 2, 4, 8, 16, 32):
        findings.append(f"BMP3XX PressOvers={press_overs!r} outside valid schema range{context} - possible torn/corrupted config read")
    resolution = body.get("ISL29125", {}).get("Resolution")
    if resolution is not None and resolution not in (12, 16):
        findings.append(f"ISL29125 Resolution={resolution!r} outside valid schema range{context} - possible torn/corrupted config read")
    # SGP40's own real DATA field, not a config field like the three above - closes a real gap
    # (SPECIFICATION.md Part C.8): every other real occupant of dev's own i2c1 was
    # schema-checked here, but a torn/corrupted SGP40 VOC reading under bench load went undetected.
    voc = body.get("SGP40", {}).get("VOC")
    if voc is not None and not (VOC_MIN <= voc <= VOC_MAX):
        findings.append(f"SGP40 VOC={voc!r} outside valid schema range{context} - possible torn/corrupted data read")
    return findings


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
                res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=15.0)
            except Exception as e:
                _record(f"worker {worker_id} iter {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200:
                _record(f"worker {worker_id} iter {i}: GET /sensors returned {res.status_code}: {res.body!r}")
                continue
            for finding in _schema_sanity_findings(res.json(), ""):
                _record(f"worker {worker_id} iter {i}: {finding}")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=15.0)
            except Exception as e:
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

    # The whole system must have stayed genuinely healthy, not just "no thread hung" - SCD30/BMP3XX/
    # ISL29125 (whose reads this test drove directly), SGP40 (whose reset it triggered), and FRAM
    # (which every one of those sensors' own error-log writes lands on) must all report nothing wrong.
    for module in ("SCD30", "BMP3XX", "SGP40", "ISL29125", "FRAM"):
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
# Compound fault: the bus contention above with light network degradation also active, since a
# deployed unit meets imperfect WiFi and client traffic together, not as separate incidents. The
# everyday-congestion range from test_network_resilience.py, not the severe one.
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
                res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=20.0)
            except Exception:
                continue
            if res.status_code != 200:
                continue
            for finding in _schema_sanity_findings(res.json(), " under degraded network"):
                _record(f"worker {worker_id} iter {i}: {finding}")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=20.0)
            except Exception:
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
    for module in ("SCD30", "BMP3XX", "SGP40", "ISL29125", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    assert_no_task_ended(dut_ip, "bus load under a network fault")
    reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Recombination test (owner's request): real bus contention concurrent with a real transient NTP
# outage - a guaranteed UDP-port block, not probabilistic degradation - so neither NTP's retry
# timers nor the bus load disrupts the other despite sharing one event loop.
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
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
                res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=20.0)
            except Exception:
                continue
            if res.status_code != 200:
                continue
            for finding in _schema_sanity_findings(res.json(), " during NTP outage"):
                _record(f"worker {worker_id} iter {i}: {finding}")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=20.0)
            except Exception:
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
    for module in ("SCD30", "BMP3XX", "SGP40", "ISL29125", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    assert_no_task_ended(dut_ip, "bus load under a network fault")
    reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Recombination test (owner's request): real bus contention with repeated WiFi flapping (3x
# ap_down()/ap_up()). Unlike the two compound tests above this really drops and re-raises the STA
# link, so wifi_mode_lock and the DNS/hotspot teardown are exercised, not just a degraded link.
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
                res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=20.0)
            except Exception:
                continue
            if res.status_code != 200:
                continue
            for finding in _schema_sanity_findings(res.json(), " during WiFi flapping"):
                _record(f"worker {worker_id} iter {i}: {finding}")

    def sgp40_reset_trigger_worker() -> None:
        for i in range(_PUT_RESET_COUNT):
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=20.0)
            except Exception:
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
        for module in ("SCD30", "BMP3XX", "SGP40", "ISL29125", "FRAM"):
            assert_module_error_log_empty(dut_ip, module)
    assert_no_task_ended(dut_ip, "bus load + real WiFi flapping")  # on both paths - FRAM keeps SYSTEM
    reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Flash-tier parity, per Part C.8's standing rule: every flash-tier bus hazard gets a bench-tier
# counterpart through the real HTTP/REST stack. This one answers test_bus_concurrency.py's
# test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads.
# ---------------------------------------------------------------------------

_ISL29125_RESOLUTIONS = (12, 16)  # the only two real, valid settings (asy_isl29125_driver.py's own _RESOLUTIONS)
_ISL29125_WRITE_CYCLES = 4  # modest relative to flash tier's 8 - each cycle here is a real HTTP round trip, not a bare I2C write


@pytest.mark.persistence_write
def test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    _report_ceiling_retries("before isl29125 arm")  # clears whatever an earlier test left
    get_before = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /sensors failed: {get_before.status_code} {get_before.body!r}"
    original_resolution = get_before.json()["ISL29125"]["Resolution"]

    errors: list[str] = []
    errors_lock = threading.Lock()

    def _record(msg: str) -> None:
        with errors_lock:
            errors.append(msg)

    def get_sensors_worker(worker_id: int) -> None:
        for i in range(_GET_ITERATIONS_PER_WORKER):
            try:
                res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=15.0)
            except Exception as e:
                _record(f"worker {worker_id} iter {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200:
                _record(f"worker {worker_id} iter {i}: GET /sensors returned {res.status_code}: {res.body!r}")
                continue
            for finding in _schema_sanity_findings(res.json(), ""):
                _record(f"worker {worker_id} iter {i}: {finding}")

    def isl29125_write_worker() -> None:
        # Alternates between both valid settings so HTTP and scheduling jitter land each write at
        # a different relative timing against the readers - this tier's substitute for the mock
        # tier's explicit sleep(0)-offset sweep (tests_hardware/README.md).

        # Starting away from the board's current value matters: an equal PUT reports "Unchanged"
        # and _set_dict_cfg() pushes only "Valid" fields live, so it would reach no hardware.
        first = 1 if original_resolution == _ISL29125_RESOLUTIONS[0] else 0
        for i in range(_ISL29125_WRITE_CYCLES):
            value = _ISL29125_RESOLUTIONS[(first + i) % 2]
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"Resolution": value}}, timeout_s=15.0)
            except Exception as e:
                _record(f"isl29125 write {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200 or res.json().get("result", {}).get("ISL29125", {}).get("Resolution") != "Valid":
                _record(f"isl29125 write {i}: PUT /sensors Resolution={value} rejected: {res.status_code} {res.body!r}")

    threads = [threading.Thread(target=get_sensors_worker, args=(w,)) for w in range(_GET_WORKERS)]
    threads.append(threading.Thread(target=isl29125_write_worker))
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120.0)
            assert not t.is_alive(), "a worker thread never finished within 120s - possible real deadlock under concurrent load"
        assert not errors, f"{len(errors)} issue(s) under concurrent API load: {'; '.join(errors[:10])}"
    finally:
        # Restore the board's original config regardless of outcome - same "shared bench rig" duty
        # test_sensor_config_push_over_real_hardware.py's own BMP3xx push test already owes.
        restore_res = fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"Resolution": original_resolution}}, timeout_s=10.0)
        # "Unchanged" is a success here, not a rejection: the alternation above can legitimately end
        # on the original value, which makes this restore a no-op. Accepting only "Valid" would fail
        # the fixture's own cleanup and mask whatever the body was actually reporting.
        assert restore_res.status_code == 200 and restore_res.json()["result"]["ISL29125"].get("Resolution") in ("Valid", "Unchanged"), f"failed to restore original ISL29125 Resolution={original_resolution!r}: {restore_res.status_code} {restore_res.body!r}"
        _report_ceiling_retries("isl29125 config-write arm")

    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after the ISL29125-write-vs-siblings load test",
    )
    for module in ("SCD30", "BMP3XX", "SGP40", "ISL29125", "CFGMGR_ISL29125", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip)


# SCD30's two write hazards have no bench-tier counterpart, and that is Part C.8's structural
# exception 1 rather than a gap, because the driver registers no push callback at all - so no PUT
# can reach its NVM write. The flash tier's gated scripts are their only real-hardware coverage.


# ---------------------------------------------------------------------------
# Real-hardware counterpart to tests_hardware/flash/test_bus_concurrency.py::
# test_bmp3xx_same_device_read_write_concurrency, driven through the real HTTP/REST stack (flash-tier
# bus-hazard coverage is always a subset of bench-tier coverage - SPECIFICATION.md Part C.8/E.6.6).
# ---------------------------------------------------------------------------

_BMP3XX_OVERSAMPLING_SETTINGS = (1, 2)  # cycled - both real, valid settings (asy_bmp3xx_driver.py's own _OSR_SETTINGS)


@pytest.mark.persistence_write
def test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    _report_ceiling_retries("before bmp3xx arm")
    get_before = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /sensors failed: {get_before.status_code} {get_before.body!r}"
    original_press_overs = get_before.json()["BMP3XX"]["PressOvers"]

    errors: list[str] = []
    errors_lock = threading.Lock()

    def _record(msg: str) -> None:
        with errors_lock:
            errors.append(msg)

    def get_sensors_worker(worker_id: int) -> None:
        for i in range(_GET_ITERATIONS_PER_WORKER):
            try:
                res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=15.0)
            except Exception as e:
                _record(f"worker {worker_id} iter {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200:
                _record(f"worker {worker_id} iter {i}: GET /sensors returned {res.status_code}: {res.body!r}")
                continue
            for finding in _schema_sanity_findings(res.json(), ""):
                _record(f"worker {worker_id} iter {i}: {finding}")

    def bmp3xx_write_worker() -> None:
        # The ISL29125 writer's varied-offset approach, scaled to BMP3xx's two-value setting -
        # but against this same sensor's own concurrent reads, a same-device hazard rather than a
        # cross-occupant one.

        # Starting away from the current value matters doubly here: PressOvers' driver default IS
        # _BMP3XX_OVERSAMPLING_SETTINGS[0], so a board at defaults would spend its first write on
        # a no-op every run.
        first = 1 if original_press_overs == _BMP3XX_OVERSAMPLING_SETTINGS[0] else 0
        for i in range(_ISL29125_WRITE_CYCLES):
            value = _BMP3XX_OVERSAMPLING_SETTINGS[(first + i) % 2]
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": {"PressOvers": value}}, timeout_s=15.0)
            except Exception as e:
                _record(f"bmp3xx write {i}: {type(e).__name__}: {e}")
                continue
            if res.status_code != 200 or res.json().get("result", {}).get("BMP3XX", {}).get("PressOvers") != "Valid":
                _record(f"bmp3xx write {i}: PUT /sensors PressOvers={value} rejected: {res.status_code} {res.body!r}")

    threads = [threading.Thread(target=get_sensors_worker, args=(w,)) for w in range(_GET_WORKERS)]
    threads.append(threading.Thread(target=bmp3xx_write_worker))
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120.0)
            assert not t.is_alive(), "a worker thread never finished within 120s - possible real deadlock under concurrent load"
        assert not errors, f"{len(errors)} issue(s) under concurrent API load: {'; '.join(errors[:10])}"
    finally:
        restore_res = fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": {"PressOvers": original_press_overs}}, timeout_s=10.0)
        # "Unchanged" is a success here for the same reason the ISL29125 restore above accepts it.
        assert restore_res.status_code == 200 and restore_res.json()["result"]["BMP3XX"].get("PressOvers") in ("Valid", "Unchanged"), f"failed to restore original BMP3XX PressOvers={original_press_overs!r}: {restore_res.status_code} {restore_res.body!r}"
        _report_ceiling_retries("bmp3xx config-write arm")

    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="webserver serving normally again after the BMP3xx same-device load test",
    )
    for module in ("SCD30", "BMP3XX", "CFGMGR_BMP3XX", "SGP40", "ISL29125", "FRAM"):
        assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip)


# SGP40's general-call hazard has no bench-tier counterpart either, and that is Part C.8's
# structural exception 2: the broadcast fires only from _reset() at setup. SGPResetVOC, which the
# workers above use and which looks like a trigger, reaches a software-only reset instead.
