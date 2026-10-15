"""Bench-tier automated tests (the owner's suggested angle, 2026-09-03): heavy API load through the full HTTP stack
against every bus at once - the bench counterpart of flash/test_bus_concurrency.py (SPECIFICATION.md C.8)."""

import threading
import time
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
from error_log_helpers import ErrcountEntry, assert_module_error_log_empty, assert_no_task_ended, code, errcount_entry, get_errcount, reset_all_error_logs, save_errcount
from harness import Board, configured_max_connections, crash_lines, fram_backed_logger_names, observe_during, recover_by_reset, save_fram_raw, wait_until

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bench_control import BenchBridge
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("bus_hazard_concurrency",)

# _GET_WORKERS + 1 concurrent clients (the SGP40 reset thread too), two slots under the build's own
# max_connections: at it, real wireless timing overlaps into an undesired reject-when-full. Derived,
# so a raised ceiling really means more concurrent bus-facing API load.
_GET_WORKERS = max(2, configured_max_connections() - 3)
# @tunable l4.bus_concurrency_under_api_load_get_iterations = 8
_GET_ITERATIONS_PER_WORKER = 8
# @tunable l4.bus_concurrency_under_api_load_put_reset_count = 2
_PUT_RESET_COUNT = 2
# Ceiling refusals fetch() retried, by "METHOD path": a connection reset under a config write shares
# their signature, so the two config-write arms note these and a gated run tells the two apart.
_ceiling_retries: dict[str, int] = {}
_ceiling_retries_lock = threading.Lock()

# The readers' answered floors, of the 24 reads dev's TOML sends per arm (3 readers x 8): every read where nothing
# faults, half under a light network fault, a quarter while the link flaps or the board reboots under the load.
# @tunable l4.bus_concurrency_under_api_load_plain_min_answered = 24
_PLAIN_MIN_ANSWERED = 24
# @tunable l4.bus_concurrency_under_api_load_degraded_min_answered = 12
_DEGRADED_MIN_ANSWERED = 12
# @tunable l4.bus_concurrency_under_api_load_ntp_min_answered = 12
_NTP_MIN_ANSWERED = 12
# @tunable l4.bus_concurrency_under_api_load_flap_min_answered = 6
_FLAP_MIN_ANSWERED = 6
# @tunable l4.bus_concurrency_under_api_load_write_min_answered = 24
_WRITE_MIN_ANSWERED = 24
# @tunable l4.bus_concurrency_under_api_load_command_min_answered = 6
_COMMAND_MIN_ANSWERED = 6

# @tunable l4.bus_concurrency_under_api_load_fetch_timeout_s = 15.0
_FETCH_TIMEOUT_S = 15.0
# @tunable l4.bus_concurrency_under_api_load_ceiling_retry_backoff_s = 0.25
_CEILING_RETRY_BACKOFF_S = 0.25
# @tunable l4.bus_concurrency_under_api_load_ceiling_retry_attempts = 3
_CEILING_RETRY_ATTEMPTS = 3
# @tunable l4.bus_concurrency_under_api_load_join_timeout_s = 120.0
_JOIN_TIMEOUT_S = 120.0
# @tunable l4.bus_concurrency_under_api_load_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.bus_concurrency_under_api_load_recovery_timeout_s = 30.0
_RECOVERY_TIMEOUT_S = 30.0
# @tunable l4.bus_concurrency_under_api_load_recovery_poll_s = 2.0
_RECOVERY_POLL_S = 2.0
# @tunable l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s = 20.0
_DEGRADED_FETCH_TIMEOUT_S = 20.0
# @tunable l4.bus_concurrency_under_api_load_degraded_join_timeout_s = 180.0
_DEGRADED_JOIN_TIMEOUT_S = 180.0
# @tunable l4.bus_concurrency_under_api_load_ntp_resync_timeout_s = 20.0
_NTP_RESYNC_TIMEOUT_S = 20.0
# @tunable l4.bus_concurrency_under_api_load_ntp_resync_poll_s = 1.0
_NTP_RESYNC_POLL_S = 1.0
# @tunable l4.network_resilience_flap_step_s = 3.0
_FLAP_STEP_S = 3.0
# @tunable l4.network_resilience_flap_cycles = 3
_FLAP_CYCLES = 3
# @tunable l4.bus_concurrency_under_api_load_flap_recovery_timeout_s = 150.0
_FLAP_RECOVERY_TIMEOUT_S = 150.0
# @tunable l4.bus_concurrency_under_api_load_reboot_ready_timeout_s = 60.0
_REBOOT_READY_TIMEOUT_S = 60.0
# @tunable l4.bus_concurrency_under_api_load_ntp_block_margin_s = 10.0
_NTP_BLOCK_MARGIN_S = 10.0
# @tunable l4.bus_concurrency_under_api_load_command_after_answered = 3
_COMMAND_AFTER_ANSWERED = 3
_NTP = "asy_ntp_client.py"
_SYSTEM = "asy_system_service.py"
# The read paths' new codes, named so a load arm that provokes one says which (catalog names, checked at run time).
_LOAD_CODES = (("W", "BMP_CHIP_RESET"), ("E", "READ_RANGE"), ("W", "ISL_DIVERGED"))


def test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes(board: Board, dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    load = _load.Load()
    resets = threading.Thread(target=_sgp40_resets, args=(dut_ip, load, _FETCH_TIMEOUT_S, ""), name="sgp40-resets")
    with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_FETCH_TIMEOUT_S, join_s=_JOIN_TIMEOUT_S, fetch=fetch, others=(resets,)) as alive:
        pass  # the readers and the resets run their bounded course
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s - possible real deadlock under concurrent load"
    _assert_load(load, _PLAIN_MIN_ANSWERED, "under concurrent API load", transport_failures_allowed=False)

    # A WiFi reconnect blip after a heavy load surfaces as a transient GET /status failure that heals in seconds
    # (SPECIFICATION.md F.2): the recovery wait comes before the log checks.
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_RECOVERY_POLL_S, description="webserver serving normally again after the concurrent bus-load test")
    _assert_bus_logs_empty(dut_ip)
    findings = _load.measurement_findings(_load.get_object(dut_ip, "/measurements", _PROBE_TIMEOUT_S))
    assert not findings, f"implausible measurements after the load: {findings}"
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Compound fault: the bus contention above with light network degradation also active, since a
# deployed unit meets imperfect WiFi and client traffic together, not as separate incidents. The
# everyday-congestion range from test_network_resilience.py, not the severe one.
# ---------------------------------------------------------------------------


def test_concurrent_get_sensors_under_real_multi_client_load_survives_light_network_degradation(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    context = " under degraded network"
    load = _load.Load(context)
    bench.inject_network_degradation(loss_pct=2, delay_ms=30, jitter_ms=20)
    try:
        resets = threading.Thread(target=_sgp40_resets, args=(dut_ip, load, _DEGRADED_FETCH_TIMEOUT_S, context), name="sgp40-resets")
        # The join bound is over the plain arm's: retried requests under loss take longer.
        with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_DEGRADED_FETCH_TIMEOUT_S, join_s=_DEGRADED_JOIN_TIMEOUT_S, fetch=fetch, others=(resets,)) as alive:
            pass
    finally:
        bench.clear_network_degradation()
    assert not alive, f"{alive} never finished within {_DEGRADED_JOIN_TIMEOUT_S:g}s under degraded network - possible real deadlock, not just slow requests"
    _assert_load(load, _DEGRADED_MIN_ANSWERED, context, transport_failures_allowed=True)

    # Full recovery once the degradation clears, as test_network_resilience.py proves without the bus load.
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_RECOVERY_POLL_S, description="webserver serving normally again after concurrent bus load + degraded network")
    _assert_bus_logs_empty(dut_ip)
    assert_no_task_ended(dut_ip, "bus load under a network fault")
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Recombination test (owner's request): bus contention concurrent with a real NTP outage - a
# guaranteed UDP-port block - so neither NTP's retry timer nor the bus load disrupts the other on one event loop.
# ---------------------------------------------------------------------------


def test_concurrent_get_sensors_under_real_multi_client_load_survives_an_ntp_transient_outage_and_retry(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # A synced client attempts nothing for NTPInterval hours and an unchanged NTPHost PUT fires no post function
    # (src/asy_api_response.py), so the reset under the block makes the boot's first sync fail; the client's own
    # unsynced retry timer then runs inside the block, which lasts one retry period plus a margin.
    networking = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S)
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTPHost": networking.get("NTPHost")}, timeout_s=_PROBE_TIMEOUT_S)
    word = _load.as_object(res.json().get("result"), "result").get("NTPHost")
    assert res.status_code == 200 and word == "Unchanged", f"an NTPHost PUT of its current value answered {word!r}: something was written ({res.body!r})"
    reset_all_error_logs(dut_ip, request.node.name)
    context = " during the NTP outage"
    load = _load.Load(context)
    block_s = _ntp_retry_period_s() + _NTP_BLOCK_MARGIN_S
    bench.block_udp_ports([123])
    try:
        _load.reset_and_wait(board, bench, dut_ip, timeout_s=_REBOOT_READY_TIMEOUT_S)
        blocked_until = time.monotonic() + block_s
        resets = threading.Thread(target=_sgp40_resets, args=(dut_ip, load, _DEGRADED_FETCH_TIMEOUT_S, context), name="sgp40-resets")
        with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_DEGRADED_FETCH_TIMEOUT_S, join_s=_DEGRADED_JOIN_TIMEOUT_S, fetch=fetch, others=(resets,)) as alive:
            wait_until(lambda: _load._ntp_error_log_contains(dut_ip, code("E", "NTP_NO_REPLY")), timeout_s=block_s, poll_interval_s=_NTP_RESYNC_POLL_S, description="an NTP attempt meeting the block (NTP_NO_REPLY)")
            time.sleep(max(blocked_until - time.monotonic(), 0.0))
    finally:
        bench.unblock_udp_ports([123])
    assert not alive, f"{alive} never finished within {_DEGRADED_JOIN_TIMEOUT_S:g}s during the NTP outage - possible real deadlock, not just slow requests"
    _assert_load(load, _NTP_MIN_ANSWERED, context, transport_failures_allowed=True)

    # The client's own retry timer resyncs once the block lifts: no reset after the one that started the window.
    started = time.monotonic()
    wait_until(lambda: _load.ntp_synced(dut_ip), timeout_s=_NTP_RESYNC_TIMEOUT_S + block_s, poll_interval_s=_NTP_RESYNC_POLL_S, description="NTP resynced by its own retry timer after the block, under bus load")
    result_note(f"NTP resynced {time.monotonic() - started:.1f}s after the block lifted")
    _assert_bus_logs_empty(dut_ip)
    assert_no_task_ended(dut_ip, "bus load under a network fault")
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Recombination test (owner's request): bus contention with repeated WiFi flapping (3x
# ap_down()/ap_up()). Unlike the two compound tests above this really drops and re-raises the STA
# link, so wifi_mode_lock and the DNS/hotspot teardown are exercised, not just a degraded link.
# ---------------------------------------------------------------------------


def test_concurrent_get_sensors_under_real_multi_client_load_survives_repeated_real_wifi_flapping(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    context = " during WiFi flapping"
    load = _load.Load(context)
    resets = threading.Thread(target=_sgp40_resets, args=(dut_ip, load, _DEGRADED_FETCH_TIMEOUT_S, context), name="sgp40-resets")
    flaps = threading.Thread(target=_flap, args=(bench,), name="flap")
    try:
        with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_DEGRADED_FETCH_TIMEOUT_S, join_s=_DEGRADED_JOIN_TIMEOUT_S, fetch=fetch, others=(resets, flaps)) as alive:
            pass
    finally:
        bench.ap_up()  # a flap cut short by a failure must not leave the bench AP down
    assert not alive, f"{alive} never finished within {_DEGRADED_JOIN_TIMEOUT_S:g}s during real WiFi flapping - possible real deadlock, not just slow requests"
    _assert_load(load, _FLAP_MIN_ANSWERED, context, transport_failures_allowed=True)

    noted = _load.Noted(result_note)
    recover_by_reset(
        board,
        bench,
        ready=lambda: _load.serving(dut_ip),
        first_wait_s=_FLAP_RECOVERY_TIMEOUT_S,
        retry_wait_s=_REBOOT_READY_TIMEOUT_S,
        skipped="error-log-empty checks for SCD30, BMP3XX, SGP40, ISL29125, FRAM",
        note=noted,
        description="WiFi flapping under bus load",
    )
    if not noted.recovered:
        _assert_bus_logs_empty(dut_ip)
    assert_no_task_ended(dut_ip, "bus load + real WiFi flapping")  # on both paths - FRAM keeps SYSTEM
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Flash-tier parity, per Part C.8's standing rule: every flash-tier bus hazard gets a bench-tier
# counterpart through the real HTTP/REST stack. This one answers test_bus_concurrency.py's
# test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads.
# ---------------------------------------------------------------------------

# @tunable l4.bus_concurrency_under_api_load_isl29125_write_cycles = 4
_ISL29125_WRITE_CYCLES = 4  # modest relative to flash tier's 8 - each cycle here is a real HTTP round trip, not a bare I2C write


@pytest.mark.persistence_write
def test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load(board: Board, dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    sensors = _load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S)
    original_resolution = _load.as_object(sensors.get("ISL29125"), "GET /sensors ISL29125").get("Resolution")
    resolutions = _load.allowed_ints("asy_isl29125_driver.py", "Resolution")
    assert len(resolutions) == 2, f"ISL29125 Resolution no longer has exactly two settings: {resolutions!r}"
    load = _load.Load()

    def isl29125_write_worker() -> None:
        # Alternates both settings so HTTP and scheduling jitter land each write at a different point against the
        # readers; it starts away from the board's value, since an equal PUT answers "Unchanged" and reaches no chip.
        first = 1 if original_resolution == resolutions[0] else 0
        for i in range(_ISL29125_WRITE_CYCLES):
            value = resolutions[(first + i) % 2]
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"Resolution": value}}, timeout_s=_FETCH_TIMEOUT_S)
                word = _load.as_object(_load.as_object(res.json().get("result"), "result").get("ISL29125"), "result.ISL29125").get("Resolution")
            except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as e:
                load.failure(f"isl29125 write {i}: {type(e).__name__}: {e}")
                continue
            if word != "Valid":
                load.failure(f"isl29125 write {i}: Resolution={value} answered {word!r}")

    writer = threading.Thread(target=isl29125_write_worker, name="isl29125-writer")
    try:
        with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_FETCH_TIMEOUT_S, join_s=_JOIN_TIMEOUT_S, fetch=fetch, others=(writer,)) as alive:
            pass
    finally:
        restore = fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"Resolution": original_resolution}}, timeout_s=_PROBE_TIMEOUT_S)
        word = _load.as_object(_load.as_object(restore.json().get("result"), "result").get("ISL29125"), "result.ISL29125").get("Resolution")
        assert word in ("Valid", "Unchanged"), f"failed to restore ISL29125 Resolution={original_resolution!r}: {restore.status_code} {restore.body!r}"
        _report_ceiling_retries(result_note, "isl29125 config-write arm")
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s - possible real deadlock under concurrent load"
    _assert_load(load, _WRITE_MIN_ANSWERED, "under the ISL29125 config writes", transport_failures_allowed=False)
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_RECOVERY_POLL_S, description="webserver serving normally again after the ISL29125-write-vs-siblings load test")
    _assert_bus_logs_empty(dut_ip, ("CFGMGR_ISL29125",))
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Real-hardware counterpart to tests_hardware/flash/test_bus_concurrency.py::
# test_bmp3xx_same_device_read_write_concurrency, driven through the real HTTP/REST stack (flash-tier
# bus-hazard coverage is always a subset of bench-tier coverage - SPECIFICATION.md Part C.8/E.6.6).
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
def test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load(board: Board, dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    sensors = _load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S)
    original_press_overs = _load.as_object(sensors.get("BMP3XX"), "GET /sensors BMP3XX").get("PresOvers")
    settings = _load.allowed_ints("asy_bmp3xx_driver.py", "PresOvers")
    assert len(settings) >= 2, f"BMP3XX PresOvers no longer offers two settings: {settings!r}"
    load = _load.Load()

    def bmp3xx_write_worker() -> None:
        # The ISL29125 writer's varied offsets against this sensor's own reads, a same-device hazard; it starts away
        # from the board's value, since a board at defaults holds the first setting and its write would be a no-op.
        first = 1 if original_press_overs == settings[0] else 0
        for i in range(_ISL29125_WRITE_CYCLES):
            value = settings[(first + i) % 2]
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": {"PresOvers": value}}, timeout_s=_FETCH_TIMEOUT_S)
                word = _load.as_object(_load.as_object(res.json().get("result"), "result").get("BMP3XX"), "result.BMP3XX").get("PresOvers")
            except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as e:
                load.failure(f"bmp3xx write {i}: {type(e).__name__}: {e}")
                continue
            if word != "Valid":
                load.failure(f"bmp3xx write {i}: PresOvers={value} answered {word!r}")

    writer = threading.Thread(target=bmp3xx_write_worker, name="bmp3xx-writer")
    try:
        with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_FETCH_TIMEOUT_S, join_s=_JOIN_TIMEOUT_S, fetch=fetch, others=(writer,)) as alive:
            pass
    finally:
        restore = fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": {"PresOvers": original_press_overs}}, timeout_s=_PROBE_TIMEOUT_S)
        word = _load.as_object(_load.as_object(restore.json().get("result"), "result").get("BMP3XX"), "result.BMP3XX").get("PresOvers")
        assert word in ("Valid", "Unchanged"), f"failed to restore BMP3XX PresOvers={original_press_overs!r}: {restore.status_code} {restore.body!r}"
        _report_ceiling_retries(result_note, "bmp3xx config-write arm")
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s - possible real deadlock under concurrent load"
    _assert_load(load, _WRITE_MIN_ANSWERED, "under the BMP3XX config writes", transport_failures_allowed=False)
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_RECOVERY_POLL_S, description="webserver serving normally again after the BMP3xx same-device load test")
    _assert_bus_logs_empty(dut_ip, ("CFGMGR_BMP3XX",))
    reset_all_error_logs(dut_ip, request.node.name)


# PUT /sensors reaches SCD30's NVM through its chip store: two owned writes and the restore, gated
# (tests_hardware/README.md budget table). The counterpart of flash/test_bus_concurrency.py's SCD30 write arm.

# @tunable l4.bus_concurrency_under_api_load_scd30_write_cycles = 2
_SCD30_WRITE_CYCLES = 2
# @tunable l4.bus_concurrency_under_api_load_scd30_offset_step_k = 0.5
_SCD30_OFFSET_STEP_K = 0.5


@pytest.mark.persistence_write
@pytest.mark.scd30_extra_write
def test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load(board: Board, dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    original = _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get("SCD30"), "GET /sensors SCD30").get("TempOffset")
    assert isinstance(original, (int, float)) and not isinstance(original, bool), f"SCD30 TempOffset read back {original!r}: the chip store answered no value"
    values = _offset_values(float(original))
    assert len(values) == _SCD30_WRITE_CYCLES, f"no {_SCD30_WRITE_CYCLES} in-range offsets around {original!r}: {values}"
    load = _load.Load()

    def scd30_write_worker() -> None:
        for i, value in enumerate(values):
            try:
                res = fetch(dut_ip, 80, "PUT", "/sensors", {"SCD30": {"TempOffset": value}}, timeout_s=_FETCH_TIMEOUT_S)
                word = _load.as_object(_load.as_object(res.json().get("result"), "result").get("SCD30"), "result.SCD30").get("TempOffset")
            except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as e:
                load.failure(f"scd30 write {i}: {type(e).__name__}: {e}")
                continue
            if word != "Valid":
                load.failure(f"scd30 write {i}: TempOffset={value} answered {word!r}")

    writer = threading.Thread(target=scd30_write_worker, name="scd30-writer")
    try:
        with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_FETCH_TIMEOUT_S, join_s=_JOIN_TIMEOUT_S, fetch=fetch, others=(writer,)) as alive:
            pass
    finally:
        restore = fetch(dut_ip, 80, "PUT", "/sensors", {"SCD30": {"TempOffset": original}}, timeout_s=_PROBE_TIMEOUT_S)
        word = _load.as_object(_load.as_object(restore.json().get("result"), "result").get("SCD30"), "result.SCD30").get("TempOffset")
        assert word in ("Valid", "Unchanged"), f"failed to restore SCD30 TempOffset={original!r}: {restore.status_code} {restore.body!r}"
        _report_ceiling_retries(result_note, "scd30 config-write arm")
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s - possible real deadlock under concurrent load"
    _assert_load(load, _WRITE_MIN_ANSWERED, "under the SCD30 config writes", transport_failures_allowed=False)
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_RECOVERY_POLL_S, description="webserver serving normally again after the SCD30-write-vs-siblings load test")
    for module in _load.bus_sharer_loggers("scd30"):
        assert_module_error_log_empty(dut_ip, module)
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# The system commands under the hammer (owner, 2026-09-30): an FRAM erase and a reboot issued while the readers
# run, each answered, each resetting through its own sequence, never the watchdog. Neither writes flash.
# ---------------------------------------------------------------------------


def test_fram_erase_under_api_load(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # The FRAM evidence first (CLAUDE.md's FRAM rule): the erase clears every FRAM-backed log for good. The raw dump
    # stops main.py, so the board is reset to serving before the load starts.
    save_errcount(dut_ip, request.node.name)
    save_fram_raw(board, request.node.name)
    _load.reset_and_wait(board, bench, dut_ip, timeout_s=_REBOOT_READY_TIMEOUT_S)
    noted = _load.Noted(result_note)
    _command_under_load(board, bench, dut_ip, "erasefram", noted)
    if not noted.recovered:
        assert _reset_reason(dut_ip) == _load.src_number(_SYSTEM, "_RR_FRAM_ERASED"), f"the erase's reset reads ResetReason {_reset_reason(dut_ip)!r}, not the erase's own code (a watchdog reset reads 2)"
    counts = get_errcount(dut_ip)
    kept = {name: errcount_entry(counts, name) for name in fram_backed_logger_names() if [h for h in errcount_entry(counts, name)["history"] if h.get("type") != "N"]}
    assert not kept, f"FRAM-backed logs still hold entries after the erase: {kept}"


def test_reboot_under_api_load(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    before = get_errcount(dut_ip)
    save_errcount(dut_ip, request.node.name)
    noted = _load.Noted(result_note)
    _command_under_load(board, bench, dut_ip, "reboot", noted)
    if not noted.recovered:
        assert _reset_reason(dut_ip) == _load.src_number(_SYSTEM, "_RR_REBOOT"), f"the reboot reads ResetReason {_reset_reason(dut_ip)!r}, not the commanded reboot's own code (a watchdog reset reads 2)"
    lost = _supersets(before, get_errcount(dut_ip))
    assert not lost, f"a commanded reboot under load lost FRAM-backed history: {lost}"


# SGP40's general-call hazard has no bench-tier counterpart either, and that is Part C.8's
# structural exception 2: the broadcast fires only from _reset() at setup. ResetVOC, which the
# workers above use and which looks like a trigger, reaches a software-only reset instead.


def _assert_bus_logs_empty(dut_ip: str, extra: "tuple[str, ...]" = ()) -> None:
    # Every logger a bus load reaches (each I2C/SPI instance's, from the bench TOML) empty; the read paths' new codes are
    # named so a failure says which of them a load provoked.
    named = {code(kind, name): name for kind, name in _LOAD_CODES}
    for module in (*_load.bus_loggers(), *extra):
        entry = errcount_entry(get_errcount(dut_ip), module)
        seen = sorted({named[num] for h in entry["history"] if isinstance(num := h.get("num"), int) and num in named})
        assert entry["counter"] == 0, f"{module!r} logged under bus load (of the read paths' load codes: {seen or 'none'}): {entry!r}"


def _assert_load(load: _load.Load, floor: int, context: str, *, transport_failures_allowed: bool) -> None:
    # No torn read ever; the readers' answered floor; transport failures only where the arm's fault makes them.
    assert not load.findings, f"{len(load.findings)} torn or corrupted read(s) {context}: {'; '.join(load.findings[:10])}"
    if not transport_failures_allowed:
        assert not load.failures, f"{len(load.failures)} failed request(s) {context}: {'; '.join(load.failures[:10])}"
    assert len(load.answered) >= floor, f"only {len(load.answered)} reads answered {context}, below the floor {floor} - the arm loaded too little to prove anything ({len(load.failures)} failed: {load.failures[:5]})"


@pytest.fixture(autouse=True)
def _ceiling_retries_noted(result_note: "_load.Note") -> "Iterator[None]":
    # Every test's retried refusals reach the run record, not a print capture drops on a pass.
    yield from _noted_ceiling_retries(result_note)


def _command_under_load(board: Board, bench: "BenchBridge", dut_ip: str, command: str, noted: "_load.Noted") -> "tuple[_load.Load, list[str]]":
    # The readers start, the command goes out once a few reads have been answered, and the board is waited for
    # passively; one recovery reset at most, reported. Returns the readers' record and the log over the window.
    load = _load.Load(f" around {command}")

    def action() -> None:
        wait_until(lambda: len(load.answered) >= _COMMAND_AFTER_ANSWERED, timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_NTP_RESYNC_POLL_S, description=f"the readers answered before {command}")
        res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": command}, timeout_s=_PROBE_TIMEOUT_S)
        word = _load.as_object(res.json().get("result"), "result").get("SystemCmd")
        assert res.status_code == 200 and word == "Valid", f"{command} under the API load answered {res.status_code} {res.body!r}"
        bench.kick_all_stations()  # the reset is a real machine.reset(): no stale AP-side station entry may outlive it
        recover_by_reset(board, bench, ready=lambda: _load.serving(dut_ip), first_wait_s=_REBOOT_READY_TIMEOUT_S, retry_wait_s=_REBOOT_READY_TIMEOUT_S, skipped=f"the passive wait after {command} and its ResetReason check", note=noted, description=f"{command} under the API load")

    with _load.readers(_GET_WORKERS, dut_ip, load, iterations=_GET_ITERATIONS_PER_WORKER, timeout_s=_DEGRADED_FETCH_TIMEOUT_S, join_s=_DEGRADED_JOIN_TIMEOUT_S, fetch=fetch) as alive:
        _result, lines = observe_during(board, action)
    assert not alive, f"{alive} never finished within {_DEGRADED_JOIN_TIMEOUT_S:g}s around {command}"
    assert not crash_lines(lines), f"a crash over the {command} window: {crash_lines(lines)}"
    _assert_load(load, _COMMAND_MIN_ANSWERED, f"around {command}", transport_failures_allowed=True)
    return load, lines


def _flap(bench: "BenchBridge") -> None:
    # 3x(3 s down/3 s up), short against the 60 s established-retry cadence: the DUT is still mid-wait between toggles.
    for _cycle in range(_FLAP_CYCLES):
        bench.ap_down()
        time.sleep(_FLAP_STEP_S)
        bench.ap_up()
        time.sleep(_FLAP_STEP_S)


def _noted_ceiling_retries(note: "_load.Note") -> "Iterator[None]":
    _take_ceiling_retries()
    yield
    counts = _take_ceiling_retries()
    if counts:
        note(f"CEILING_RETRIES rest of the test: {counts}")


def _ntp_retry_period_s() -> float:
    # The unsynced client's first retry step: its default interval, rounded up to the check tick it is counted on.
    return max(_load.src_number(_NTP, "_DEFAULT_RETRY_S"), _load.src_number(_NTP, "_NTP_CHECK_INTERV"))


def _offset_values(original: float) -> "list[float]":
    # Two values differing from the board's TempOffset by the step, each inside _VAL_TEMP_OFFSET's range.
    _kind, _default, low, high, _special = _load.field_schema("asy_scd30_driver.py", "TempOffset")
    assert isinstance(low, float) and isinstance(high, float), f"SCD30 TempOffset's schema bounds are {low!r}..{high!r}"
    candidates = [original + _SCD30_OFFSET_STEP_K, original - _SCD30_OFFSET_STEP_K, original + 2 * _SCD30_OFFSET_STEP_K]
    return [round(value, 2) for value in candidates if low <= value <= high][:_SCD30_WRITE_CYCLES]


def _report_ceiling_retries(note: "_load.Note", arm: str) -> None:
    note(f"CEILING_RETRIES {arm}: {_take_ceiling_retries() or 'none'}")


def _reset_reason(dut_ip: str) -> object:
    return _load.as_object(_load.get_object(dut_ip, "/status").get("system"), "GET /status system").get("ResetReason")


def _sgp40_resets(dut_ip: str, load: _load.Load, timeout_s: float, context: str) -> None:
    # The SGP40 reset trigger beside the readers: a dispatch-only PUT, so it persists nothing.
    for i in range(_PUT_RESET_COUNT):
        try:
            res = fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"ResetVOC": True}}, timeout_s=timeout_s)
            word = _load.as_object(_load.as_object(res.json().get("result"), "result").get("SGP40"), "result.SGP40").get("ResetVOC")
        except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as e:
            load.failure(f"sgp40 reset {i}{context}: {type(e).__name__}: {e}")
            continue
        if word != "Valid":
            load.finding(f"sgp40 reset {i}{context}: ResetVOC answered {word!r}")


def _supersets(before: "dict[str, ErrcountEntry]", after: "dict[str, ErrcountEntry]") -> "list[str]":
    # Each FRAM-backed history the reboot lost: its counter fell, or an entry the full ring had room to keep is gone.
    lost = []
    for name in fram_backed_logger_names():
        old, new = errcount_entry(before, name), errcount_entry(after, name)
        old_used = [h for h in old["history"] if h.get("type") != "N"]
        new_used = [h for h in new["history"] if h.get("type") != "N"]
        missing = [h for h in old_used if h not in new_used]
        if new["counter"] < old["counter"] or (missing and len(new_used) < len(new["history"])):
            lost.append(f"{name}: {old!r} -> {new!r}")
    return lost


def _take_ceiling_retries() -> dict[str, int]:
    with _ceiling_retries_lock:
        counts = dict(_ceiling_retries)
        _ceiling_retries.clear()
    return counts


def fetch(host: str, port: int, method: str, path: str, json_body: "JSONObject | None" = None, timeout_s: float = _FETCH_TIMEOUT_S) -> http_client.HttpResponse:
    # A ceiling refusal under concurrent load is the stack's reject-when-full, not a fault: retried at most
    # _CEILING_RETRY_ATTEMPTS times per call. Remove if the arms ever run below the ceiling. Name and positional
    # signature stay http_client.fetch's, so the wear guard reads each PUT body here as at fetch() itself.
    for attempt in range(_CEILING_RETRY_ATTEMPTS):
        try:
            return http_client.fetch(host, port, method, path, json_body, timeout_s=timeout_s)
        except http_client.CeilingRefusedError:
            if attempt == _CEILING_RETRY_ATTEMPTS - 1:
                raise
            with _ceiling_retries_lock:
                _ceiling_retries[f"{method} {path}"] = _ceiling_retries.get(f"{method} {path}", 0) + 1
            time.sleep(_CEILING_RETRY_BACKOFF_S)
    raise AssertionError("unreachable")
