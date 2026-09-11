"""Construction/wiring tests for sensortask_dev.py's build_system() - full parity with
tests/test_sensortask_wozi.py's own coverage, adapted to the dev bench's pins/FRAM size (see
SPECIFICATION.md Part A.7 for the shared construction-order/FRAM-chunk/setup-batch reference)."""

import asyncio
import json
import os
import sys

# scripts/test.sh's MICROPYPATH excludes ext/; sensortask_dev transitively imports microdot, so
# this reaches the real vendored ext/microdot.py without touching MICROPYPATH.
sys.path.insert(0, "ext")

import machine
from _fram_chip_fake import FakeMB85RS64V
from _shared_rest_roundtrip import (
    assert_named_modules_constructed,
    assert_sensor_payload_not_self_wrapped,
    drain_json_response_body,
)
from microdot import Request, Response  # type: ignore[import-not-found]

import asy_spi_driver
import sensortask_dev
from print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from asy_fram_manager import AsyFramChunk, AsyFramTimestampedChunk
    from base_classes import SensorReaderConfig
    from crc_checks import CRC_Base

    T = TypeVar("T")


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # dev's real FRAM chip is a 256KB MB85RS2MTA (product ID 0x48 0x03, SPECIFICATION.md Part
    # C.3.1), not wozi's 8KB MB85RS64V the base fake models by default. A subclass, not a
    # post-construction override, since build_system() constructs the chip with no such hook.
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])


# Same one-process-per-test-file swap as every other asy_fram_*-touching test file (see their own
# comments) - sensortask_dev.build_system() constructs a real SPI-backed AsyFramManager.
asy_spi_driver._SPI = _FakeMB85RS2MTA  # type: ignore[misc]

# Mirrors asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_HOTSPOT values - same
# not-importable-once-const()-folded reasoning as tests/test_asy_wifi_service.py's own copy; keep in
# sync with asy_wifi_service.py's own definitions if those ever change.
_PHASE_STA_SEEKING = 0
_PHASE_HOTSPOT = 2


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def status_body(res: "Response") -> bytes:
    # GET /status streams from a list of already-json.dumps()-encoded fragments; drain it back
    # into one body so existing json.loads(...) assertions keep working unchanged.
    return drain_json_response_body(res.body)


# ---------------------------------------------------------------------------
# Per-test config-file isolation, same pattern as test_sensortask_wozi.py's own _tmp_cfg_dir(): the
# five real ConfigManager-backed modules build_system() constructs must not collide across test_*
# functions in this one process, nor touch the real repo-root config files.
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # See test_sensortask_wozi.py's own identical helper for the full root-cause story (a later
    # scripts/test.sh run silently reusing an earlier run's persisted config files) - this is the
    # same fix, applied to this file's own "dev_" prefix.
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return  # tests/_tmp itself doesn't exist yet - nothing to clean
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("dev_")


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/dev_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    return path + "/"


# ---------------------------------------------------------------------------
# _sweep_stale_tmp_dirs() itself - regression coverage for the stale-persisted-config-reuse bug
# its own comment above describes.
# ---------------------------------------------------------------------------


def test_sweep_stale_tmp_dirs_removes_a_pre_existing_matching_directory_and_its_contents() -> None:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    stale_dir = _TMP_DIR + "/dev_stale_test_marker"
    try:
        os.mkdir(stale_dir)
    except OSError:
        pass
    with open(stale_dir + "/config_LEFTOVER.cfg", "w") as f:
        f.write('{"NTP_Host": "time.example.org"}')  # shaped like a real persisted config write

    _sweep_stale_tmp_dirs("dev_stale_test_marker")

    try:
        os.stat(stale_dir)
        raise AssertionError("expected the stale directory to have been removed")
    except OSError:
        pass  # gone, as expected


def test_sweep_stale_tmp_dirs_leaves_non_matching_entries_alone() -> None:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    keep_dir = _TMP_DIR + "/not_dev_prefixed_marker"
    try:
        os.mkdir(keep_dir)
    except OSError:
        pass

    _sweep_stale_tmp_dirs("dev_")  # this file's own real prefix - must not touch an unrelated name

    os.stat(keep_dir)  # still there - raises OSError (failing this test) if it got swept
    os.rmdir(keep_dir)  # this test's own responsibility to clean up, not _sweep_stale_tmp_dirs()'s


def test_sweep_stale_tmp_dirs_tolerates_a_missing_tmp_dir_entirely() -> None:
    # Nothing to assert beyond "doesn't raise" - the real-world case this guards is the very first
    # scripts/test.sh run ever, before tests/_tmp exists at all.
    try:
        os.listdir(_TMP_DIR)  # raises immediately (before any iteration) if _TMP_DIR is missing
    except OSError:
        pass  # confirms this environment's own tests/_tmp is absent for this particular check
    else:
        return  # tests/_tmp already exists (other tests created it) - nothing new to prove here
    _sweep_stale_tmp_dirs("dev_")


# ---------------------------------------------------------------------------
# Construction: every legacy-named module is reachable, bare globals (no wrapper container).
# ---------------------------------------------------------------------------


def test_build_system_constructs_every_legacy_named_module() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    # Bare module-level attributes - same shape as sensortask_wozi.py's own equivalent test.
    assert_named_modules_constructed(
        sensortask_dev,
        (
            "conn",
            "ntp",
            "i2c0",
            "i2c1",
            "spi0",
            "fram",
            "sysfunct",
            "sgp_reader",
            "bmp_reader",
            "scd_reader",
            "pixel",
            "notify_service",
            "watchdog",
        ),
    )


def test_scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it() -> None:
    # SCD30 documents up to 150ms clock stretching once a day (datasheet p.2); rp2's I2C timeout
    # default is 50ms, so SCD30's bus must override it or that stretch surfaces as a spurious
    # OSError. Looked up via scd_reader itself so this stays correct regardless of which bus.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.scd_reader is not None
    scd_bus = sensortask_dev.scd_reader.scd.i2c_scd30.i2c_device.i2c
    assert scd_bus._i2c is not None
    assert scd_bus._i2c.freq == 50000
    assert scd_bus._i2c.timeout >= 150000

    # Whichever bus that isn't (BMP3xx's, alone on this variant) has no such requirement and keeps
    # the port default.
    assert sensortask_dev.i2c0 is not None and sensortask_dev.i2c1 is not None
    other_bus = sensortask_dev.i2c1 if scd_bus is sensortask_dev.i2c0 else sensortask_dev.i2c0
    assert other_bus._i2c is not None
    assert other_bus._i2c.timeout == 50000


def test_build_system_wires_the_wifi_led_callback_after_both_exist() -> None:
    # conn.set_ext_led(pixel) - the one cross-wiring step that must run after both objects exist.
    # Confirmed indirectly: AsyConnTime's own ext_led slot is set.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    assert sensortask_dev.conn.ext_led is sensortask_dev.pixel


def test_build_system_is_independently_callable_and_returns() -> None:
    # The whole point of the two-file split: importing this
    # test file and calling build_system() must never block. If this test hangs, that's the
    # regression to report - not something to work around here.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))


def test_build_system_web_host_and_port_default_to_production_values() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.webserver is not None
    assert sensortask_dev.webserver._host == "0.0.0.0"
    assert sensortask_dev.webserver._port == 80


def test_build_system_web_host_and_port_are_overridable() -> None:
    # A non-root Unix-port integration run can't bind the production 0.0.0.0:80 default (EACCES) -
    # build_system() must let a caller override both, mirroring sensortask_wozi.py's own existing
    # cfg_path/debug override pattern.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    assert sensortask_dev.webserver is not None
    assert sensortask_dev.webserver._host == "127.0.0.1"
    assert sensortask_dev.webserver._port == 8080


def test_main_forwards_web_host_and_port_to_build_system() -> None:
    # main() (the real entry point) must forward the override too, not just build_system(). Fakes
    # start_timers()/ntp_force_sync()/start_and_check_tasks() since start_timers()'s real
    # Timer-sequencing chain never completes under tests/machine.py's manual-.trigger()-only fake.
    from asy_ntp_client import AsyNtpClient
    from system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = AsyNtpClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    async def _fake_start_timers(self: "SystemService", timers: "list[Callable[[], None]]") -> None:
        pass

    async def _fake_force_sync(self: "AsyNtpClient") -> None:
        pass

    async def _fake_start_and_check(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        pass  # never loops - this test only cares that build_system() received the override

    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    AsyNtpClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.start_and_check_tasks = _fake_start_and_check  # type: ignore[method-assign]
    try:
        run(sensortask_dev.main(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        AsyNtpClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]
    assert sensortask_dev.webserver is not None
    assert sensortask_dev.webserver._host == "127.0.0.1"
    assert sensortask_dev.webserver._port == 8080


# ---------------------------------------------------------------------------
# FRAM chunk order - seven chunks, exact relative sequence, stable across rebuilds by mirroring
# wozi's own construction order.
# ---------------------------------------------------------------------------


def test_fram_chunk_allocation_order_matches_the_documented_seven_chunk_sequence() -> None:
    calls: list[str] = []
    from asy_fram_manager import AsyFramManager

    real_get_chunk = AsyFramManager.get_chunk
    real_get_timestamped_chunk = AsyFramManager.get_timestamped_chunk

    def _tracking_get_chunk(
        self: "AsyFramManager", size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8,
    ) -> "AsyFramChunk | None":  # signature mirrors the real method it replaces - mypy checks it on assignment
        calls.append("chunk")
        return real_get_chunk(self, size, crc, verify, check_length)

    def _tracking_get_timestamped_chunk(
        self: "AsyFramManager", size: int, ntp_sync_callback: "Callable[[], Coroutine[Any, Any, bool]]",
        crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8,
    ) -> "AsyFramTimestampedChunk | None":
        calls.append("timestamped")
        return real_get_timestamped_chunk(self, size, ntp_sync_callback, crc, verify, check_length)

    AsyFramManager.get_chunk = _tracking_get_chunk  # type: ignore[method-assign]
    AsyFramManager.get_timestamped_chunk = _tracking_get_timestamped_chunk  # type: ignore[method-assign]
    try:
        run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        AsyFramManager.get_chunk = real_get_chunk  # type: ignore[method-assign]
        AsyFramManager.get_timestamped_chunk = real_get_timestamped_chunk  # type: ignore[method-assign]

    # SystemService -> SGP40 log -> SGP40 VOC backup(timestamped) -> BMP3xx -> SCD30 -> Neopixel ->
    # NotificationCoordinator, matching sensortask_wozi.py's own build_system() order.
    assert calls == ["chunk", "chunk", "timestamped", "chunk", "chunk", "chunk", "chunk"]


def test_fram_chunks_are_all_successfully_allocated_not_out_of_memory() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    # Each chunk-owning module degrades to in-memory-only on allocation failure rather than
    # raising; assert the happy path actually got real FRAM-backed chunks, not a silent degrade.
    assert sensortask_dev.sysfunct is not None
    assert sensortask_dev.sgp_reader is not None
    assert sensortask_dev.bmp_reader is not None
    assert sensortask_dev.scd_reader is not None
    assert sensortask_dev.pixel is not None
    assert sensortask_dev.notify_service is not None
    assert isinstance(sensortask_dev.sysfunct.pr, PrintLogHistoryStore)
    assert sensortask_dev.sysfunct.pr.fram is not None
    assert isinstance(sensortask_dev.sgp_reader.pr, PrintLogHistoryStore)
    assert sensortask_dev.sgp_reader.pr.fram is not None
    assert sensortask_dev.sgp_reader.ts_storage is not None
    assert isinstance(sensortask_dev.bmp_reader.pr, PrintLogHistoryStore)
    assert sensortask_dev.bmp_reader.pr.fram is not None
    assert isinstance(sensortask_dev.scd_reader.pr, PrintLogHistoryStore)
    assert sensortask_dev.scd_reader.pr.fram is not None
    assert isinstance(sensortask_dev.pixel.pr, PrintLogHistoryStore)
    assert sensortask_dev.pixel.pr.fram is not None
    assert isinstance(sensortask_dev.notify_service.pr, PrintLogHistoryStore)
    assert sensortask_dev.notify_service.pr.fram is not None


class _DeadFramChip(_FakeMB85RS2MTA):
    # Same technique as test_sensortask_wozi.py's own _DeadFramChip: a real device-ID mismatch
    # (not just fram=None) - the chip responds, just never comes up as an MB85RS2MTA.
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])


def test_build_system_never_insists_on_fram_hardware_being_available() -> None:
    # No module may insist on FRAM: every FRAM-backed error log keeps working in plain RAM, and
    # SGP40 keeps running (skipping backup/restore) - exercised through the whole construction
    # chain with a dead chip, not just per-driver in isolation.
    real_spi_class = asy_spi_driver._SPI
    asy_spi_driver._SPI = _DeadFramChip  # type: ignore[misc]
    try:
        run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        asy_spi_driver._SPI = real_spi_class  # type: ignore[misc]

    # build_system() completed fully - didn't raise, didn't skip constructing anything - despite
    # the underlying FRAM chip never coming up.
    assert sensortask_dev.fram is not None
    assert sensortask_dev.fram.fram is not None
    assert sensortask_dev.fram.fram.initialized is False  # the dead chip, confirmed never ready
    assert sensortask_dev.sysfunct is not None
    assert sensortask_dev.sgp_reader is not None
    assert sensortask_dev.bmp_reader is not None
    assert sensortask_dev.scd_reader is not None
    assert sensortask_dev.pixel is not None
    assert sensortask_dev.notify_service is not None

    # Each logger still allocated a chunk (pure bookkeeping, SPECIFICATION.md C.13) but stays
    # functional in degraded mode rather than raising.
    assert isinstance(sensortask_dev.sysfunct.pr, PrintLogHistoryStore)
    run(sensortask_dev.sysfunct.pr.err_s("boom", errno=1))  # never raises despite the dead chip
    assert run(sensortask_dev.sysfunct.get_error_counter())["SYSTEM"]["ErrCount"] == 1  # still counted in memory

    # SGP40 specifically: VOC backup/restore chunk allocated but unusable - skips backups, starts
    # from scratch every time, but the reader itself keeps running (asy_sgp40_driver.py's own
    # _check_storage() contract, not re-tested here at that depth).
    assert isinstance(sensortask_dev.sgp_reader.pr, PrintLogHistoryStore)
    assert sensortask_dev.sgp_reader.ts_storage is not None
    assert run(sensortask_dev.sgp_reader.get_error_counter())["SGP40"]["ErrCount"] == 0

    # BMP3xx/SCD30: same degraded-mode contract as sysfunct above - a FRAM-backed logger stays
    # functional in plain memory when the chip never comes up.
    assert isinstance(sensortask_dev.bmp_reader.pr, PrintLogHistoryStore)
    run(sensortask_dev.bmp_reader.pr.err_s("boom", errno=1))
    assert run(sensortask_dev.bmp_reader.get_error_counter())["BMP3XX"]["ErrCount"] == 1
    assert isinstance(sensortask_dev.scd_reader.pr, PrintLogHistoryStore)
    run(sensortask_dev.scd_reader.pr.err_s("boom", errno=1))
    assert run(sensortask_dev.scd_reader.get_error_counter())["SCD30"]["ErrCount"] == 1

    # The rest of the system is unaffected - task/timer starter collection still works end to end.
    starters = sensortask_dev._collect_task_starters()
    assert len(starters) > 0


# ---------------------------------------------------------------------------
# setup() batch: grouped, fixed order, notify_service.setup() only after finalize().
# ---------------------------------------------------------------------------


def test_setup_batch_runs_sysfunct_then_fram_then_conn_then_ntp_then_sgp_then_bmp_then_notify_in_order() -> None:
    calls: list[str] = []
    from asy_bmp3xx_driver import BMP3xx_Reader
    from asy_fram_manager import AsyFramManager
    from asy_notification_service import NotificationCoordinator
    from asy_ntp_client import AsyNtpClient
    from asy_sgp40_driver import SGP40_Reader
    from asy_wifi_service import AsyConnTime
    from system_service import SystemService

    real_sysfunct_setup = SystemService.setup
    real_fram_setup = AsyFramManager.setup
    real_conn_setup = AsyConnTime.setup
    real_ntp_setup = AsyNtpClient.setup
    real_sgp_setup = SGP40_Reader.setup
    real_bmp_setup = BMP3xx_Reader.setup
    real_notify_setup = NotificationCoordinator.setup
    real_notify_finalize = NotificationCoordinator.finalize

    # Every self: below names the class that *declares* the replaced method, not the one it is
    # installed on - that is the signature mypy checks each assignment against.
    async def _tracking_sysfunct_setup(self: "SystemService") -> None:
        calls.append("sysfunct")
        await real_sysfunct_setup(self)

    async def _tracking_fram_setup(self: "AsyFramManager") -> bool:
        calls.append("fram")
        return await real_fram_setup(self)

    async def _tracking_conn_setup(self: "SensorReaderConfig") -> None:
        calls.append("conn")
        await real_conn_setup(self)

    async def _tracking_ntp_setup(self: "SensorReaderConfig") -> None:
        calls.append("ntp")
        await real_ntp_setup(self)

    async def _tracking_sgp_setup(self: "SensorReaderConfig") -> None:
        calls.append("sgp")
        await real_sgp_setup(self)

    async def _tracking_bmp_setup(self: "SensorReaderConfig") -> None:
        calls.append("bmp")
        await real_bmp_setup(self)

    async def _tracking_notify_setup(self: "NotificationCoordinator") -> None:
        calls.append("notify_setup")
        await real_notify_setup(self)

    def _tracking_notify_finalize(self: "NotificationCoordinator") -> None:
        calls.append("notify_finalize")
        real_notify_finalize(self)

    SystemService.setup = _tracking_sysfunct_setup  # type: ignore[method-assign]
    AsyFramManager.setup = _tracking_fram_setup  # type: ignore[method-assign]
    AsyConnTime.setup = _tracking_conn_setup  # type: ignore[method-assign]
    AsyNtpClient.setup = _tracking_ntp_setup  # type: ignore[method-assign]
    SGP40_Reader.setup = _tracking_sgp_setup  # type: ignore[method-assign]
    BMP3xx_Reader.setup = _tracking_bmp_setup  # type: ignore[method-assign]
    NotificationCoordinator.setup = _tracking_notify_setup  # type: ignore[method-assign]
    NotificationCoordinator.finalize = _tracking_notify_finalize  # type: ignore[method-assign]
    try:
        run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.setup = real_sysfunct_setup  # type: ignore[method-assign]
        AsyFramManager.setup = real_fram_setup  # type: ignore[method-assign]
        AsyConnTime.setup = real_conn_setup  # type: ignore[method-assign]
        AsyNtpClient.setup = real_ntp_setup  # type: ignore[method-assign]
        SGP40_Reader.setup = real_sgp_setup  # type: ignore[method-assign]
        BMP3xx_Reader.setup = real_bmp_setup  # type: ignore[method-assign]
        NotificationCoordinator.setup = real_notify_setup  # type: ignore[method-assign]
        NotificationCoordinator.finalize = real_notify_finalize  # type: ignore[method-assign]

    # notify_finalize runs during sync construction, before any setup() call; sysfunct is first
    # within the async setup() batch to resolve the persisted debug level as early as possible.
    assert calls == ["notify_finalize", "sysfunct", "fram", "conn", "ntp", "sgp", "bmp", "notify_setup"]


def test_notify_service_cfgmgr_exists_once_build_system_completes() -> None:
    # self.cfgmgr only comes into existence via finalize()'s delayed super().__init__() -
    # asy_notification_service.py's own contract. If build_system() ever called notify_service's
    # setup() before finalize(), this would be the observable symptom (AttributeError instead).
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.notify_service is not None
    assert sensortask_dev.notify_service.cfgmgr.valid is True


# ---------------------------------------------------------------------------
# Debug level - persisted on sysfunct, pushed live to every logger via a registry collected once
# at boot (SPECIFICATION.md Part A.7's "Debug-level registry" section).
# ---------------------------------------------------------------------------


def _all_loggers() -> "list[Any]":
    d = sensortask_dev
    assert d.conn is not None and d.ntp is not None and d.fram is not None and d.sysfunct is not None
    assert d.sgp_reader is not None and d.bmp_reader is not None and d.scd_reader is not None
    assert d.pixel is not None and d.notify_service is not None and d.webserver is not None
    assert d.uart_initiator is not None and d.uart_responder is not None
    return [
        d.conn.pr,
        d.conn.cfgmgr.pr,
        d.conn.dns_server.pr,
        d.ntp.pr,
        d.ntp.cfgmgr.pr,
        d.fram.pr,
        d.sysfunct.pr,
        d.sysfunct.cfgmgr.pr,
        d.sgp_reader.pr,
        d.sgp_reader.cfgmgr.pr,
        d.bmp_reader.pr,
        d.bmp_reader.cfgmgr.pr,
        d.scd_reader.pr,
        d.pixel.pr,
        d.notify_service.pr,
        d.notify_service.cfgmgr.pr,
        d.uart_initiator.pr,  # the two ends of the bench rig's permanent UART crossover jumper,
        d.uart_responder.pr,  # each with its own name so their histories never merge
        d.webserver.pr,
    ]


def test_collect_level_setters_returns_one_entry_per_logger_in_the_object_graph() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    setters = sensortask_dev._collect_level_setters()
    loggers = _all_loggers()
    assert len(setters) == len(loggers)
    # Each collected setter really is that logger's own bound set_level, confirmed by behavior
    # (bound-method identity isn't guaranteed): calling it must change that exact logger's level.
    for i in range(len(loggers)):
        loggers[i].set_level(PrintLog.level_off())
        setters[i](PrintLog.level_info())
        assert loggers[i].get_level() == PrintLog.level_info()


def test_debug_seed_value_is_the_starting_level_before_setup_resolves_the_persisted_one() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), debug=PrintLog.level_warn()))
    assert sensortask_dev.sysfunct is not None
    # First boot - no persisted value yet, so sysfunct.setup() resolves the schema default (0) and
    # pushes it out, overriding the debug= seed every logger was constructed with.
    assert sensortask_dev.sysfunct.get_debug_level() == 0
    for pr in _all_loggers():
        assert pr.get_level() == 0, f"{pr.name!r} still shows the debug= seed, not the resolved default"


def test_sysfunct_set_debug_level_updates_every_logger_in_the_object_graph() -> None:
    # End-to-end: once a REST route is wired to sysfunct.set_debug_level(), this is the whole
    # observable effect a real request would have - every logger's own set_level() called directly,
    # no shared mutable value anywhere.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.sysfunct is not None
    ok = run(sensortask_dev.sysfunct.set_debug_level(PrintLog.level_err()))
    assert ok is True
    for pr in _all_loggers():
        assert pr.get_level() == PrintLog.level_err(), f"{pr.name!r} did not observe set_debug_level()"


def test_debug_level_survives_a_simulated_reboot_through_build_system() -> None:
    cfg_path = _tmp_cfg_dir()
    run(sensortask_dev.build_system(cfg_path=cfg_path))
    assert sensortask_dev.sysfunct is not None
    run(sensortask_dev.sysfunct.set_debug_level(PrintLog.level_once()))

    run(sensortask_dev.build_system(cfg_path=cfg_path))  # simulated reboot - same cfg_path, fresh objects
    assert sensortask_dev.sysfunct is not None
    assert sensortask_dev.sysfunct.get_debug_level() == PrintLog.level_once()
    for pr in _all_loggers():
        assert pr.get_level() == PrintLog.level_once(), f"{pr.name!r} did not get the persisted level on reboot"


# ---------------------------------------------------------------------------
# Task/timer starter collection - shape and membership only, never drives the infinite supervisor
# loop (start_and_check_tasks()) or a starter's own coroutine body. That boundary is Step 5's job.
# ---------------------------------------------------------------------------


def test_collect_task_starters_includes_every_constructed_module() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    starters = sensortask_dev._collect_task_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    assert not any("webserver" in getattr(s, "__name__", "").lower() for s in starters)
    # MicroPython bound methods don't expose __self__, but they compare equal when bound to the
    # same (instance, function) pair, so membership via == still proves each owner contributed.
    for owner in (
        sensortask_dev.scd_reader,
        sensortask_dev.bmp_reader,
        sensortask_dev.sgp_reader,
        sensortask_dev.pixel,
        sensortask_dev.notify_service,
        sensortask_dev.sysfunct,
        sensortask_dev.conn,
        sensortask_dev.ntp,
    ):
        assert owner is not None
        for expected in owner.get_task_starters():
            assert expected in starters, f"no task starter bound to {owner!r}"


def test_collect_timer_starters_includes_every_constructed_module() -> None:
    # Every constructed module is checked, not just ones with a real timer today - proves
    # _collect_timer_starters() calls each module rather than picking by name, so a future Timer
    # added to pixel/notify_service/webserver (all currently []) won't silently never run.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    starters = sensortask_dev._collect_timer_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    for owner in (
        sensortask_dev.scd_reader,
        sensortask_dev.bmp_reader,
        sensortask_dev.sgp_reader,
        sensortask_dev.pixel,
        sensortask_dev.notify_service,
        sensortask_dev.sysfunct,
        sensortask_dev.conn,
        sensortask_dev.ntp,
        sensortask_dev.webserver,
    ):
        assert owner is not None
        for expected in owner.get_timer_starters():
            assert expected in starters, f"no timer starter bound to {owner!r}"


def test_collect_task_starters_never_touches_start_and_check_tasks() -> None:
    # Collection is pure list-building from already-constructed objects - calling it must not
    # start, await, or block on anything. If it did, this test itself would hang.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    sensortask_dev._collect_task_starters()
    sensortask_dev._collect_timer_starters()


# ---------------------------------------------------------------------------
# main()'s own composition - build_system() -> start_timers() -> ntp_force_sync() ->
# start_and_check_tasks(), in order. Fakes the latter two (test_system_service.py already covers
# their internals directly) since real Timer-firing/an infinite supervisor loop would hang here.
# ---------------------------------------------------------------------------


def test_main_calls_start_timers_then_force_sync_then_start_and_check_tasks_in_order() -> None:
    calls: list[str] = []
    from asy_ntp_client import AsyNtpClient
    from system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = AsyNtpClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    async def _fake_start_timers(self: "SystemService", timers: "list[Callable[[], None]]") -> None:
        calls.append("start_timers")

    async def _fake_force_sync(self: "AsyNtpClient") -> None:
        calls.append("force_sync")

    async def _fake_start_and_check(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        calls.append("start_and_check_tasks")
        # Deliberately never loops - the real implementation runs forever; this proves main()
        # reaches this call, not that the supervisor loop itself behaves (test_system_service.py's
        # own job).

    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    AsyNtpClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.start_and_check_tasks = _fake_start_and_check  # type: ignore[method-assign]
    try:
        run(sensortask_dev.main(cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        AsyNtpClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]

    assert calls == ["start_timers", "force_sync", "start_and_check_tasks"]
    # build_system() itself already ran (construction succeeded) - main() reaches the task-starting
    # phase with every module in place, not just up to build_system().
    assert sensortask_dev.sysfunct is not None


# ---------------------------------------------------------------------------
# Webserver wiring - checks build_system()'s real driver registrations landed correctly (right
# module/fields/hooks); generic dispatch/aggregation logic is test_asy_webserver_service.py's job.
# ---------------------------------------------------------------------------


def _dispatch(method: str, path: str, json_body: "dict[str, Any] | None" = None) -> "Response":
    assert sensortask_dev.webserver is not None
    app = sensortask_dev.webserver._app
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    req = Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)
    return run(app.dispatch_request(req))


def test_webserver_pr_is_ram_only_not_fram_backed() -> None:
    # Deliberate: a per-call/outer-cap reclaim warning could churn far faster than a sensor's rare
    # hardware-fault log, and RAM-only preserves the seven-chunk FRAM order (Part A.7) unchanged.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.webserver is not None
    assert isinstance(sensortask_dev.webserver.pr, PrintLogHistory)
    assert not isinstance(sensortask_dev.webserver.pr, PrintLogHistoryStore)


def test_webserver_measurements_and_sensors_get_include_every_real_sensor() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("GET", "/measurements")
    assert res.status_code == 200
    measurements = json.loads(status_body(res))
    assert_sensor_payload_not_self_wrapped(measurements, {"SCD30", "BMP3XX", "SGP40"})

    res = _dispatch("GET", "/sensors")
    sensors = json.loads(status_body(res))
    assert_sensor_payload_not_self_wrapped(sensors, {"SCD30", "BMP3XX", "SGP40"})


def test_webserver_sensors_put_round_trips_a_real_field_through_the_real_driver() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/sensors", {"SGP40": {"BackupPeriod": 5}})
    body = json.loads(res.body)
    assert body["result"] == {"SGP40": {"BackupPeriod": "Valid"}}
    assert sensortask_dev.sgp_reader is not None
    assert run(sensortask_dev.sgp_reader.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}


def test_webserver_sensors_put_round_trips_a_real_scd30_field_through_the_real_driver() -> None:
    # SCD30_Reader is the only sensors=-registered module that's a plain SensorReader rather than a
    # SensorReaderConfig subclass (no local cfgmgr - these params live on the sensor itself) - see
    # test_sensortask_wozi.py's own identical test for the full regression story.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/sensors", {"SCD30": {"MeasInt": 4}})
    body = json.loads(res.body)
    assert body["result"] == {"SCD30": {"MeasInt": "Valid"}}


def test_webserver_networking_put_ssid_group_reconnects_but_led_group_alone_does_not() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    res = _dispatch("PUT", "/networking", {"LedWifiOn": False})
    assert json.loads(res.body)["result"] == {"LedWifiOn": "Valid"}
    assert sensortask_dev.conn.reconn_wifi is False  # LedWifiOn alone must never reconnect

    res = _dispatch("PUT", "/networking", {"Hostname": "TestHost"})
    assert json.loads(res.body)["result"] == {"Hostname": "Valid"}
    assert sensortask_dev.conn.reconn_wifi is True  # setNetwork's own field group did change


def test_webserver_networking_put_ntp_fields_forces_a_resync() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.ntp is not None
    sensortask_dev.ntp.ntp_retries = 3
    res = _dispatch("PUT", "/networking", {"NTP_Host": "time.example.org"})
    assert json.loads(res.body)["result"] == {"NTP_Host": "Valid"}
    assert sensortask_dev.ntp.ntp_retries == 0  # post_asy_fct fired


def test_webserver_system_put_debug_level_propagates_to_every_logger() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.sysfunct is not None and sensortask_dev.conn is not None
    res = _dispatch("PUT", "/system", {"DebugLevel": PrintLog.level_err()})
    assert json.loads(res.body)["result"]["DebugLevel"] == "Valid"
    assert sensortask_dev.sysfunct.get_debug_level() == PrintLog.level_err()
    assert sensortask_dev.conn.pr.get_level() == PrintLog.level_err()  # pushed via the registry


def test_webserver_system_put_gmt_dst_offset_applies_without_a_reconnect() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.ntp is not None and sensortask_dev.conn is not None
    res = _dispatch("PUT", "/system", {"GMTOffset": 7200})
    assert json.loads(res.body)["result"] == {"GMTOffset": "Valid"}
    assert run(sensortask_dev.ntp.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 7200}
    assert sensortask_dev.conn.reconn_wifi is False  # unrelated to the networking settings groups


def test_webserver_system_put_reboot_cmd_arms_the_real_reset_timer() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.sysfunct is not None
    before = machine.reset_count
    res = _dispatch("PUT", "/system", {"SystemCmd": "reboot"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Valid"
    sensortask_dev.sysfunct.reset_timer.trigger()  # fake Timer - fires the armed callback synchronously
    assert machine.reset_count == before + 1


def test_webserver_system_put_invalid_cmd_is_rejected_without_side_effects() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    before = machine.reset_count
    res = _dispatch("PUT", "/system", {"SystemCmd": "bogus"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Invalid"
    assert machine.reset_count == before


def test_webserver_notification_put_light_cmd_led_dispatches_to_the_real_pixel_driver() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_light_cmd_led_accepts_integral_float_rgb_and_int_t_coerced() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10.0, "g": 20.0, "b": 30.0, "t": 1}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_light_cmd_led_rejects_fractional_rgb() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10.5, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_non_numeric_field() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": "10", "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_non_numeric_t() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": "soon"}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_missing_field() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30}})  # t missing
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_out_of_range_rgb() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 256, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_negative_rgb() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": -1, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_out_of_range_t() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 0.1}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 100.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_accepts_lower_boundary_rgb_and_t() -> None:
    # Deliberately one dispatch per test (not both boundaries in one test function) - see
    # test_sensortask_wozi.py's own identical test for the full reasoning (NeopixelDriver's own
    # request_signal() start_signal_event guard).
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 0, "g": 255, "b": 0, "t": 0.5}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_light_cmd_led_accepts_upper_boundary_rgb_and_t() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 255, "g": 0, "b": 255, "t": 60.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_pause_time_dispatches_to_the_real_coordinator() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.notify_service is not None
    assert run(sensortask_dev.notify_service.get_override_led()) == 0
    res = _dispatch("PUT", "/notification", {"PauseTime": 60})
    assert json.loads(res.body)["result"]["PauseTime"] == "Valid"
    assert run(sensortask_dev.notify_service.get_override_led()) == 60


def test_webserver_notification_put_flat_field_round_trips_through_the_real_coordinator() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.notify_service is not None
    res = _dispatch("PUT", "/notification", {"WarnCO2": 1800})
    assert json.loads(res.body)["result"] == {"WarnCO2": "Valid"}
    assert run(sensortask_dev.notify_service.cfgmgr.get_dict(["WarnCO2"])) == {"WarnCO2": 1800}


def test_webserver_status_get_reflects_the_real_object_graph() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("GET", "/status")
    body = json.loads(status_body(res))
    assert set(body.keys()) == {"networking", "system", "notification", "sensors", "errcount"}
    assert set(body["sensors"].keys()) == {"SGP40"}  # only sensor with real maintenance data
    assert "BackupTS" in body["sensors"]["SGP40"] and "RestoreTS" in body["sensors"]["SGP40"]
    assert "SysUptime" in body["system"] and "LocalTime" in body["system"] and "UtcTime" in body["system"]
    assert "WifiUptime" in body["networking"] and "NtpSynced" in body["networking"]
    assert "Triggered" in body["notification"] and "PauseTime" in body["notification"]
    # One entry per real module + per real ConfigManager + this service's own "WEBSERVER" entry -
    # same 18-owner enumeration _collect_level_setters()/_collect_error_sources() both share, plus
    # one. 18 rather than 16 since the bench rig's two UART crossover ends each register their own.
    assert len(body["errcount"]) == 19
    assert "UART_INIT" in body["errcount"]
    assert "UART_RESP" in body["errcount"]


def test_webserver_status_put_reset_errors_clears_a_real_modules_history() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    run(sensortask_dev.conn.pr.err_s("simulated", errno=99))
    assert (run(sensortask_dev.conn.get_error_counter()))["WIFI"]["ErrCount"] == 1
    res = _dispatch("PUT", "/status", {"ResetErrors": True})
    assert json.loads(res.body)["res"] == "OK"
    assert (run(sensortask_dev.conn.get_error_counter()))["WIFI"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# Captive-portal hotspot-mode redirect wiring (SPECIFICATION.md Part A.5/A.7) - confirms
# build_system()'s real `is_hotspot_active=conn.is_hotspot_active` reaches the real conn instance,
# not a fake callback. No real WiFi task runs; conn._conn_phase is set directly instead.
# ---------------------------------------------------------------------------


def test_is_hotspot_active_wiring_redirects_when_conn_is_in_hotspot_phase() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    sensortask_dev.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch("GET", "/generate_204")
    assert res.status_code == 302
    assert res.headers["Location"] == "/"


def test_is_hotspot_active_wiring_default_sta_phase_still_404s() -> None:
    # Error-path/good-outcome baseline: AsyConnTime.__init__ starts in _PHASE_STA_SEEKING - the real
    # wiring must not accidentally redirect before hotspot mode is ever reached.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    assert sensortask_dev.conn._conn_phase == _PHASE_STA_SEEKING
    res = _dispatch("GET", "/generate_204")
    assert res.status_code == 404


def test_is_hotspot_active_wiring_dynamic_phase_switch_is_reflected_live() -> None:
    # Dynamic-mode-switch coverage through the real construction graph: flips the real conn's phase
    # back and forth on the same built system and confirms each dispatch reflects the phase at call
    # time, not whatever it was when WebserverService(...) was constructed.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    conn = sensortask_dev.conn

    assert _dispatch("GET", "/generate_204").status_code == 404

    conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch("GET", "/generate_204")
    assert res.status_code == 302
    assert res.headers["Location"] == "/"

    conn._conn_phase = _PHASE_STA_SEEKING
    assert _dispatch("GET", "/generate_204").status_code == 404


def test_is_hotspot_active_wiring_real_static_root_and_api_route_unaffected_in_hotspot_mode() -> None:
    # Upstream/downstream error handling: real content must keep flowing through cleanly - the
    # redirect fallback must never shadow an actual file hit or a real API route, hotspot mode or not.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    sensortask_dev.conn._conn_phase = _PHASE_HOTSPOT

    res = _dispatch("GET", "/")
    assert res.status_code == 200  # real (stub) index.html, not a redirect loop

    res = _dispatch("GET", "/measurements")
    assert res.status_code == 200
    assert_sensor_payload_not_self_wrapped(json.loads(status_body(res)), {"SCD30", "BMP3XX", "SGP40"})


def test_is_hotspot_active_wiring_directory_traversal_still_404s_in_hotspot_mode() -> None:
    # All-paths coverage through the real wiring: the ".." guard clause in _serve_static() runs
    # before is_hotspot_active() is ever consulted (see asy_webserver_service.py's own source order).
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    sensortask_dev.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch("GET", "/foo/../../index.html")
    assert res.status_code == 404


def test_is_hotspot_active_wiring_put_to_unmatched_path_still_405_in_hotspot_mode() -> None:
    # All-paths coverage: a non-GET request to an unmatched path resolves to 405 inside Microdot's
    # own routing before _serve_static() is ever reached - real hotspot state must not change that.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.conn is not None
    sensortask_dev.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch("PUT", "/generate_204", {})
    assert res.status_code == 405


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
