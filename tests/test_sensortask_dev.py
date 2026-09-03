"""Construction/wiring tests for sensortask_dev.py's build_system() - full parity with
tests/test_sensortask_wozi.py's own coverage (DEV_HARDWARE_BASELINE_PLAN.md decision 6), adapted to
the dev bench's own pins/FRAM size. See SPECIFICATION.md Part A.7 for the general
construction-order/FRAM-chunk-order/setup-batch/dependency-graph reference this file verifies
against - sensortask_dev.py mirrors sensortask_wozi.py's own shape exactly, just wired differently.
Also covers the webserver's own real wiring (a real Microdot() app + WebserverService, every module's
registrations) - deep per-route behavior stays tests/test_asy_webserver_service.py's job; this file
only checks the real driver objects were registered correctly."""

import asyncio
import json
import os
import sys

# Same convention as tests/test_asy_webserver_service.py's own module docstring: scripts/test.sh's
# MICROPYPATH deliberately excludes ext/, and sensortask_dev now transitively imports microdot
# (via asy_webserver_service.py) - extending sys.path here reaches the real, vendored
# ext/microdot.py without touching MICROPYPATH/pyproject.toml/scripts/test.sh.
sys.path.insert(0, "ext")

import machine  # noqa: E402
from _fram_chip_fake import FakeMB85RS64V  # noqa: E402
from _shared_rest_roundtrip import assert_named_modules_constructed, assert_sensor_payload_not_self_wrapped  # noqa: E402
from microdot import Request  # type: ignore[import-not-found]  # noqa: E402

import asy_spi_driver  # noqa: E402
import sensortask_dev  # noqa: E402
from print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # The dev bench's real FRAM chip (dev_legacy/README.md's wiring table) is a 256KB MB85RS2MTA,
    # not wozi's 8KB MB85RS64V - FakeMB85RS64V's own default rdid_response models the 8KB chip's
    # real ID (product ID bytes 0x03, 0x02), which would mismatch this variant's own
    # max_size=0x40000 -> expected product ID 0x4803 lookup (asy_fram_driver.py's
    # _KNOWN_PRODUCT_IDS) and push every FRAM-backed module into degraded (uninitialized) mode by
    # default. Real hardware finding (SPECIFICATION.md Part C.3.1): MB85RS2MTA reports product ID
    # bytes 0x48, 0x03. tests/test_asy_fram_driver.py's own make_fram() reuses the same base fake
    # and overrides rdid_response by hand after construction for its max_size=0x40000 cases - not
    # possible here, since sensortask_dev.build_system() constructs the chip internally with no
    # post-construction hook before its own setup() batch runs, hence this small subclass instead.
    def __init__(self, *args: "Any", **kwargs: "Any") -> None:
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


# ---------------------------------------------------------------------------
# Per-test config-file isolation - same pattern as test_sensortask_wozi.py's own _tmp_cfg_dir():
# build_system() constructs five real ConfigManager-backed modules (conn, ntp, sgp_reader,
# bmp_reader, notify_service), each of which writes/reads a real config_<NAME>.cfg file at its
# cfg_path - repeated calls across test_* functions in this one process must not collide on the
# same files, and must not touch the real repo-root config files either.
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
# _sweep_stale_tmp_dirs() itself - regression coverage for the actual bug (a later
# scripts/test.sh run silently reusing an earlier run's persisted config files), not just a
# re-assertion of the pre-existing "config write applies" expectation the FAIL output already
# covered indirectly. See _sweep_stale_tmp_dirs()'s own comment above for the full root-cause story.
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
    # SCD30 documents up to 150ms of clock stretching once per day for internal calibration
    # (datasheets/scd30/..._Interface_Description.pdf p.2) - rp2's own I2C timeout default is
    # 50ms (DEFAULT_I2C_TIMEOUT, ports/rp2/machine_i2c.c), so whichever bus SCD30 sits on must
    # override it or that expected stretch surfaces as a spurious OSError roughly once a day.
    # Looked up through scd_reader itself (not assumed to be any particular bus) - dev wires SCD30
    # to i2c1 (wozi: i2c0) - this test stays correct either way.
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
    # main() itself (not just build_system()) must accept and forward the override - the real
    # entry point calls sensortask_dev.main(), never build_system() directly. Fakes
    # start_timers()/ntp_force_sync()/start_and_check_tasks() the same way
    # test_main_calls_start_timers_then_force_sync_then_start_and_check_tasks_in_order() already
    # does, and for the same reason (see that test's own comment): start_timers()'s real
    # Timer-sequencing chain never completes under tests/machine.py's fake, which only fires
    # Timer callbacks via manual .trigger() - awaiting it for real here would hang.
    from asy_ntp_client import AsyNtpClient
    from system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = AsyNtpClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    async def _fake_start_timers(self: "Any", timers: "Any") -> None:
        pass

    async def _fake_force_sync(self: "Any") -> None:
        pass

    async def _fake_start_and_check(self: "Any", task_starters: "Any") -> None:
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
# FRAM chunk order - seven chunks, exact relative sequence. Doesn't need to match wozi's own
# sequence (DEV_HARDWARE_BASELINE_PLAN.md decision 3) - only needs to stay stable across rebuilds
# of this same file, which sensortask_dev.py achieves by mirroring wozi's own construction order.
# ---------------------------------------------------------------------------


def test_fram_chunk_allocation_order_matches_the_documented_seven_chunk_sequence() -> None:
    calls: list[str] = []
    from asy_fram_manager import AsyFramManager

    real_get_chunk = AsyFramManager.get_chunk
    real_get_timestamped_chunk = AsyFramManager.get_timestamped_chunk

    def _tracking_get_chunk(self: "AsyFramManager", *args: "Any", **kwargs: "Any") -> "Any":
        calls.append("chunk")
        return real_get_chunk(self, *args, **kwargs)

    def _tracking_get_timestamped_chunk(self: "AsyFramManager", *args: "Any", **kwargs: "Any") -> "Any":
        calls.append("timestamped")
        return real_get_timestamped_chunk(self, *args, **kwargs)

    AsyFramManager.get_chunk = _tracking_get_chunk  # type: ignore[method-assign]
    AsyFramManager.get_timestamped_chunk = _tracking_get_timestamped_chunk  # type: ignore[method-assign]
    try:
        run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        AsyFramManager.get_chunk = real_get_chunk  # type: ignore[method-assign]
        AsyFramManager.get_timestamped_chunk = real_get_timestamped_chunk  # type: ignore[method-assign]

    # SystemService(chunk) -> SGP40 own log(chunk) -> SGP40 VOC backup(timestamped) ->
    # BMP3xx_Reader(chunk) -> SCD30_Reader(chunk) -> NeopixelDriver(chunk) ->
    # NotificationCoordinator(chunk), in that order, unconditionally - same order as
    # sensortask_wozi.py's own build_system() (mirrored deliberately, see that module's own
    # comment - not a hard requirement, just the simplest choice for an identical sensor set).
    assert calls == ["chunk", "chunk", "timestamped", "chunk", "chunk", "chunk", "chunk"]


def test_fram_chunks_are_all_successfully_allocated_not_out_of_memory() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    # Every FRAM-chunk-owning module's own PrintLogHistoryStore/AsyFramTimestampedChunk degrades to
    # in-memory-only on allocation failure rather than raising (base_classes.py's own contract) -
    # assert the happy path actually got real FRAM-backed chunks, not a silently-degraded one.
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
    def __init__(self, *args: "Any", **kwargs: "Any") -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])


def test_build_system_never_insists_on_fram_hardware_being_available() -> None:
    # Owner requirement: no module may insist on FRAM availability - every currently FRAM-backed
    # error log must keep working in plain RAM, and SGP40 specifically must keep running (skipping
    # backup/restore entirely) without FRAM. Exercises the *whole* construction chain with a dead
    # chip, not just one driver in isolation (asy_sgp40_driver.py's/print_log.py's own test suites
    # already cover each class's own degraded-mode contract at the unit level in more depth).
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

    # Every FRAM-chunk-owning module's own logger still allocated a chunk (pure bookkeeping,
    # SPECIFICATION.md C.13 - doesn't require setup() to have succeeded) but stays functional in
    # degraded mode rather than raising - matches test_fram_integration.py's own established
    # "reader.pr.fram is not None, just permanently hardware-unusable" pattern.
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

    async def _tracking_sysfunct_setup(self: "Any") -> "Any":
        calls.append("sysfunct")
        return await real_sysfunct_setup(self)

    async def _tracking_fram_setup(self: "Any") -> "Any":
        calls.append("fram")
        return await real_fram_setup(self)

    async def _tracking_conn_setup(self: "Any") -> "Any":
        calls.append("conn")
        return await real_conn_setup(self)

    async def _tracking_ntp_setup(self: "Any") -> "Any":
        calls.append("ntp")
        return await real_ntp_setup(self)

    async def _tracking_sgp_setup(self: "Any") -> "Any":
        calls.append("sgp")
        return await real_sgp_setup(self)

    async def _tracking_bmp_setup(self: "Any") -> "Any":
        calls.append("bmp")
        return await real_bmp_setup(self)

    async def _tracking_notify_setup(self: "Any") -> "Any":
        calls.append("notify_setup")
        return await real_notify_setup(self)

    def _tracking_notify_finalize(self: "Any") -> "Any":
        calls.append("notify_finalize")
        return real_notify_finalize(self)

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

    # notify_finalize runs during synchronous construction, before any setup() call; sysfunct is
    # first *within* the async setup() batch - resolves the real persisted debug level as early as
    # possible (this module's own docstring). conn/ntp were both built before fram/sysfunct but are
    # placed after them here too, matching sysfunct's/fram's own already-fixed positions; conn before
    # ntp mirrors their own real construction order.
    assert calls == ["notify_finalize", "sysfunct", "fram", "conn", "ntp", "sgp", "bmp", "notify_setup"]


def test_notify_service_cfgmgr_exists_once_build_system_completes() -> None:
    # self.cfgmgr only comes into existence via finalize()'s delayed super().__init__() -
    # asy_notification_service.py's own contract. If build_system() ever called notify_service's
    # setup() before finalize(), this would be the observable symptom (AttributeError instead).
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.notify_service is not None
    assert sensortask_dev.notify_service.cfgmgr.valid is True


# ---------------------------------------------------------------------------
# Debug level - persisted on sysfunct, pushed live to every logger's own set_level() through a
# registry collected once at boot (owner requirement: general, system-wide, not per-module - but
# no shared mutable value anywhere; see SPECIFICATION.md Part A.7's "Debug-level registry"
# section and _collect_level_setters() for the full logger list).
# ---------------------------------------------------------------------------


def _all_loggers() -> "list[Any]":
    d = sensortask_dev
    assert d.conn is not None and d.ntp is not None and d.fram is not None and d.sysfunct is not None
    assert d.sgp_reader is not None and d.bmp_reader is not None and d.scd_reader is not None
    assert d.pixel is not None and d.notify_service is not None and d.webserver is not None
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
        d.webserver.pr,
    ]


def test_collect_level_setters_returns_one_entry_per_logger_in_the_object_graph() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    setters = sensortask_dev._collect_level_setters()
    loggers = _all_loggers()
    assert len(setters) == len(loggers)
    # Each collected setter really is that logger's own bound set_level - confirmed by behavior
    # (bound-method identity isn't guaranteed, matching this file's own established convention for
    # checking bound methods elsewhere): calling it must change that exact logger's own level.
    # Index-based, not zip() - avoids a silent length-mismatch footgun on top of the explicit
    # length assert above.
    for i in range(len(loggers)):
        loggers[i].set_level(PrintLog.level_off())
        setters[i](PrintLog.level_info())
        assert loggers[i].get_level() == PrintLog.level_info()


def test_debug_seed_value_is_the_starting_level_before_setup_resolves_the_persisted_one() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), debug=PrintLog.level_warn()))
    assert sensortask_dev.sysfunct is not None
    # First boot - no persisted value yet, so sysfunct.setup() writes and resolves the schema
    # default (0), then pushes it out through the registry - overriding the debug= seed every
    # individual module's own logger was constructed with. Matches test_system_service.py's own
    # test_setup_resolves_cfgmgr_and_leaves_debug_level_at_the_default_on_first_boot.
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
    # No Microdot/webserver task in Step 1 (owner-confirmed - refined plan
    # Q2, Step 2's job entirely).
    assert not any("webserver" in getattr(s, "__name__", "").lower() for s in starters)
    # Each real module's own get_task_starters() output is present. MicroPython bound methods
    # don't expose __self__ (confirmed directly against the real Unix-port interpreter - a
    # CPython-only introspection assumption), but they do compare equal when bound to the same
    # (instance, function) pair, so membership via == still proves each owner actually contributed
    # its own starters to the combined list, not just that the total count happens to match.
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
    # Every constructed module is checked here, not just the ones that currently contribute a real
    # timer (matches test_collect_task_starters_includes_every_constructed_module's own uniform
    # ownership check) - pixel/notify_service/webserver all currently return [] from their own
    # get_timer_starters(), but this test still proves _collect_timer_starters() actually calls
    # each of them (rather than picking modules by name), since a future Timer added to any of the
    # three would otherwise silently never run.
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
# start_and_check_tasks(), in that order. start_timers()'s real Timer-sequencing mechanism and
# start_and_check_tasks()'s real supervisor loop are each already thoroughly covered by
# test_system_service.py directly - this test fakes both out (they'd otherwise need real
# wall-clock-firing Timers, which tests/machine.py's fake only fires via manual .trigger(), or
# block forever) to verify main() itself wires the pieces together in the right order, matching
# sensortask_wozi.py's own main() shape, without re-proving either subsystem's own internals here.
# ---------------------------------------------------------------------------


def test_main_calls_start_timers_then_force_sync_then_start_and_check_tasks_in_order() -> None:
    calls: list[str] = []
    from asy_ntp_client import AsyNtpClient
    from system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = AsyNtpClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    async def _fake_start_timers(self: "Any", timers: "Any") -> None:
        calls.append("start_timers")

    async def _fake_force_sync(self: "Any") -> None:
        calls.append("force_sync")

    async def _fake_start_and_check(self: "Any", task_starters: "Any") -> None:
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
# Webserver wiring - build_system() also constructs a real Microdot() app + WebserverService,
# registering every real driver's SettingsGroup/status_source/system_cmd/notification_led/
# maintenance_sensor/error_source. These tests check the *real* registrations landed correctly
# (right module, right fields, right hooks) - not the generic dispatch/aggregation logic itself,
# which tests/test_asy_webserver_service.py's own uniform-fake suite already covers in full depth
# (its own endpoint-design decision).
# ---------------------------------------------------------------------------


def _dispatch(method: str, path: str, json_body: "dict[str, Any] | None" = None) -> "Any":
    assert sensortask_dev.webserver is not None
    app = sensortask_dev.webserver._app
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    req = Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)
    return run(app.dispatch_request(req))


def test_webserver_pr_is_ram_only_not_fram_backed() -> None:
    # Deliberate decision (see build_system()'s own comment): a warning on every per-call/outer-cap
    # reclaim could churn far faster than any sensor's rare-hardware-fault log - keeping it RAM-only
    # also preserves the seven-chunk FRAM allocation order (see SPECIFICATION.md Part A.7) unchanged.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_dev.webserver is not None
    assert isinstance(sensortask_dev.webserver.pr, PrintLogHistory)
    assert not isinstance(sensortask_dev.webserver.pr, PrintLogHistoryStore)


def test_webserver_measurements_and_sensors_get_include_every_real_sensor() -> None:
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("GET", "/measurements")
    assert res.status_code == 200
    measurements = json.loads(res.body)
    assert_sensor_payload_not_self_wrapped(measurements, {"SCD30", "BMP3XX", "SGP40"})

    res = _dispatch("GET", "/sensors")
    sensors = json.loads(res.body)
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
    body = json.loads(res.body)
    assert set(body.keys()) == {"networking", "system", "notification", "sensors", "errcount"}
    assert set(body["sensors"].keys()) == {"SGP40"}  # only sensor with real maintenance data
    assert "BackupTS" in body["sensors"]["SGP40"] and "RestoreTS" in body["sensors"]["SGP40"]
    assert "SysUptime" in body["system"] and "LocalTime" in body["system"] and "UtcTime" in body["system"]
    assert "WifiUptime" in body["networking"] and "NtpSynced" in body["networking"]
    assert "Triggered" in body["notification"] and "PauseTime" in body["notification"]
    # One entry per real module + per real ConfigManager + this service's own "WEBSERVER" entry -
    # same 16-owner enumeration _collect_level_setters()/_collect_error_sources() both share, plus one.
    assert len(body["errcount"]) == 17


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
# `is_hotspot_active=conn.is_hotspot_active` (build_system()'s own real WebserverService(...) call)
# actually reaches the real, wired conn instance, through the real construction graph - not a fake
# callback like tests/test_asy_webserver_service.py's own Section G.2 coverage. No real WiFi task is
# started here (deliberately - see test_digital_twin_real_website_integration.py's own note for the
# same reasoning): conn._conn_phase is set directly, the same test-seam convention this file's own
# test_webserver_networking_put_ssid_group_reconnects_but_led_group_alone_does_not() and others
# already use for a real driver's internal state.
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
    assert_sensor_payload_not_self_wrapped(json.loads(res.body), {"SCD30", "BMP3XX", "SGP40"})


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
