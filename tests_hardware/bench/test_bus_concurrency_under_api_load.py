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
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import Board

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0

# Held safely under the real max_connections=4 ceiling (asy_webserver_service.py) - see
# test_end_to_end_timing.py's own connections-at-the-limit test for that boundary itself; this
# test's own job is bus contention under load, not re-proving the connection-accept limit.
_GET_WORKERS = 3
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

    # The whole system must have stayed genuinely healthy through this, not just "no thread hung" -
    # per the standing error-log policy (tests_hardware/README.md), a clean pass leaves nothing
    # behind for either SCD30 or BMP3XX (whose config-snapshot reads this test drove directly) or
    # SGP40 (whose real general-call reset this test triggered concurrently with those reads).
    for module in ("SCD30", "BMP3XX", "SGP40"):
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
