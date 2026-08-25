"""Construction/wiring tests for sensortask_wozi.py's build_system() - see SPECIFICATION.md Part A.7 for the full construction-order/FRAM-chunk-order/setup-batch/dependency-graph reference this file verifies against.
Also covers the webserver's own real wiring (a real Microdot() app + WebserverService, every module's registrations) - deep per-route behavior stays tests/test_asy_webserver_service.py's job; this file only checks the real driver objects were registered correctly."""

import asyncio
import json
import os
import sys

# Same convention as tests/test_asy_webserver_service.py's own module docstring: scripts/test.sh's
# MICROPYPATH deliberately excludes ext/, and sensortask_wozi.py now transitively imports microdot
# (via asy_webserver_service.py) - extending sys.path here reaches the real, vendored
# ext/microdot.py without touching MICROPYPATH/pyproject.toml/scripts/test.sh.
sys.path.insert(0, "ext")

import machine  # noqa: E402
from _fram_chip_fake import FakeMB85RS64V  # noqa: E402
from microdot import Request  # type: ignore[import-not-found]  # noqa: E402

import asy_spi_driver  # noqa: E402
import sensortask_wozi  # noqa: E402
from print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore  # noqa: E402

# Same one-process-per-test-file swap as every other asy_fram_*-touching test file (see their own
# comments) - sensortask_wozi.build_system() constructs a real SPI-backed AsyFramManager.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Per-test config-file isolation - same pattern as test_ntp_fram_system_integration.py's own
# _tmp_cfg_dir(): build_system() constructs five real ConfigManager-backed modules (conn, ntp,
# sgp_reader, bmp_reader, notify_service), each of which writes/reads a real config_<NAME>.cfg file
# at its cfg_path - repeated calls across test_* functions in this one process must not collide on
# the same files, and must not touch the real repo-root config files either.
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # _next_dir always restarts at 0 per process, so a second scripts/test.sh run on the same
    # machine reuses the exact same directory names an earlier run already left behind - and
    # "already exists from a stale previous run" (the comment below used to say) turns out not to
    # be harmless: the earlier run's real, persisted config_*.cfg files are still sitting there, so
    # a write that should be a genuine value change instead compares against yesterday's
    # already-matching value and gets misreported "Unchanged" instead of "Valid" (confirmed by
    # direct reproduction - deleting tests/_tmp/wozi_* took this file from 23/29 to 29/29 passing;
    # re-running it again, now dirty from that clean run, reproduced the exact same 6 failures every
    # time). This exact _tmp_cfg_dir() shape is copy-pasted across every test_*.py file with its own
    # _TMP_DIR/_next_dir pair - same fix applied uniformly to each. Sweeping at import time, rather than only guarding
    # against the empty-directory case os.mkdir()'s own try/except already handled, is what actually
    # restores the "must not collide"/fresh-directory guarantee this helper's own docstring promises.
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


_sweep_stale_tmp_dirs("wozi_")


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/wozi_" + str(_next_dir)
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
    stale_dir = _TMP_DIR + "/wozi_stale_test_marker"
    try:
        os.mkdir(stale_dir)
    except OSError:
        pass
    with open(stale_dir + "/config_LEFTOVER.cfg", "w") as f:
        f.write('{"NTP_Host": "time.example.org"}')  # shaped like a real persisted config write

    _sweep_stale_tmp_dirs("wozi_stale_test_marker")

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
    keep_dir = _TMP_DIR + "/not_wozi_prefixed_marker"
    try:
        os.mkdir(keep_dir)
    except OSError:
        pass

    _sweep_stale_tmp_dirs("wozi_")  # this file's own real prefix - must not touch an unrelated name

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
    _sweep_stale_tmp_dirs("wozi_")


# ---------------------------------------------------------------------------
# Construction: every legacy-named module is reachable, bare globals (no wrapper container).
# ---------------------------------------------------------------------------


def test_build_system_constructs_every_legacy_named_module() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    # Bare module-level attributes - Step 2 (and this test) reaches every long-lived object the
    # same way the legacy reference file's own module-level names would be reached.
    for name in (
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
    ):
        assert hasattr(sensortask_wozi, name), f"sensortask_wozi.{name} was not constructed"
        assert getattr(sensortask_wozi, name) is not None


def test_build_system_wires_the_wifi_led_callback_after_both_exist() -> None:
    # conn.set_ext_led(pixel) - the one cross-wiring step that must run after both objects exist.
    # Confirmed indirectly: AsyConnTime's own ext_led slot is set.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.conn is not None
    assert sensortask_wozi.conn.ext_led is sensortask_wozi.pixel


def test_build_system_is_independently_callable_and_returns() -> None:
    # The whole point of the two-file split: importing this
    # test file and calling build_system() must never block. If this test hangs, that's the
    # regression to report - not something to work around here.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))


def test_build_system_web_host_and_port_default_to_production_values() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.webserver is not None
    assert sensortask_wozi.webserver._host == "0.0.0.0"
    assert sensortask_wozi.webserver._port == 80


def test_build_system_web_host_and_port_are_overridable() -> None:
    # Step 5's own real need: a non-root Unix-port integration run can't bind the production
    # 0.0.0.0:80 default (EACCES) - build_system() must let a caller override both, mirroring its
    # existing cfg_path/debug override pattern (refined plan,
    # decision 3).
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    assert sensortask_wozi.webserver is not None
    assert sensortask_wozi.webserver._host == "127.0.0.1"
    assert sensortask_wozi.webserver._port == 8080


def test_main_forwards_web_host_and_port_to_build_system() -> None:
    # main() itself (not just build_system()) must accept and forward the override - Step 5's own
    # real entry point calls sensortask_wozi.main(), never build_system() directly. Fakes
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
        run(sensortask_wozi.main(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        AsyNtpClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]
    assert sensortask_wozi.webserver is not None
    assert sensortask_wozi.webserver._host == "127.0.0.1"
    assert sensortask_wozi.webserver._port == 8080


# ---------------------------------------------------------------------------
# FRAM chunk order - five chunks, exact relative sequence.
# ---------------------------------------------------------------------------


def test_fram_chunk_allocation_order_matches_the_documented_five_chunk_sequence() -> None:
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
        run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        AsyFramManager.get_chunk = real_get_chunk  # type: ignore[method-assign]
        AsyFramManager.get_timestamped_chunk = real_get_timestamped_chunk  # type: ignore[method-assign]

    # SystemService(chunk) -> SGP40 own log(chunk) -> SGP40 VOC backup(timestamped) ->
    # NeopixelDriver(chunk) -> NotificationCoordinator(chunk), in that order, unconditionally.
    assert calls == ["chunk", "chunk", "timestamped", "chunk", "chunk"]


def test_fram_chunks_are_all_successfully_allocated_not_out_of_memory() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    # Every FRAM-chunk-owning module's own PrintLogHistoryStore/AsyFramTimestampedChunk degrades to
    # in-memory-only on allocation failure rather than raising (base_classes.py's own contract) -
    # assert the happy path actually got real FRAM-backed chunks, not a silently-degraded one.
    assert sensortask_wozi.sysfunct is not None
    assert sensortask_wozi.sgp_reader is not None
    assert sensortask_wozi.pixel is not None
    assert sensortask_wozi.notify_service is not None
    assert isinstance(sensortask_wozi.sysfunct.pr, PrintLogHistoryStore)
    assert sensortask_wozi.sysfunct.pr.fram is not None
    assert isinstance(sensortask_wozi.sgp_reader.pr, PrintLogHistoryStore)
    assert sensortask_wozi.sgp_reader.pr.fram is not None
    assert sensortask_wozi.sgp_reader.ts_storage is not None
    assert isinstance(sensortask_wozi.pixel.pr, PrintLogHistoryStore)
    assert sensortask_wozi.pixel.pr.fram is not None
    assert isinstance(sensortask_wozi.notify_service.pr, PrintLogHistoryStore)
    assert sensortask_wozi.notify_service.pr.fram is not None


class _DeadFramChip(FakeMB85RS64V):
    # Same technique as test_fram_integration.py's own
    # test_sensorreader_runs_in_degraded_mode_when_fram_setup_never_succeeded: a real device-ID
    # mismatch (not just fram=None) - the chip responds, just never comes up as an MB85RS64V.
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
        run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        asy_spi_driver._SPI = real_spi_class  # type: ignore[misc]

    # build_system() completed fully - didn't raise, didn't skip constructing anything - despite
    # the underlying FRAM chip never coming up.
    assert sensortask_wozi.fram is not None
    assert sensortask_wozi.fram.fram is not None
    assert sensortask_wozi.fram.fram.initialized is False  # the dead chip, confirmed never ready
    assert sensortask_wozi.sysfunct is not None
    assert sensortask_wozi.sgp_reader is not None
    assert sensortask_wozi.pixel is not None
    assert sensortask_wozi.notify_service is not None

    # Every FRAM-chunk-owning module's own logger still allocated a chunk (pure bookkeeping,
    # SPECIFICATION.md C.13 - doesn't require setup() to have succeeded) but stays functional in
    # degraded mode rather than raising - matches test_fram_integration.py's own established
    # "reader.pr.fram is not None, just permanently hardware-unusable" pattern.
    assert isinstance(sensortask_wozi.sysfunct.pr, PrintLogHistoryStore)
    run(sensortask_wozi.sysfunct.pr.err_s("boom", errno=1))  # never raises despite the dead chip
    assert run(sensortask_wozi.sysfunct.get_error_counter())["SYSTEM"]["ErrCount"] == 1  # still counted in memory

    # SGP40 specifically: VOC backup/restore chunk allocated but unusable - skips backups, starts
    # from scratch every time, but the reader itself keeps running (asy_sgp40_driver.py's own
    # _check_storage() contract, not re-tested here at that depth).
    assert isinstance(sensortask_wozi.sgp_reader.pr, PrintLogHistoryStore)
    assert sensortask_wozi.sgp_reader.ts_storage is not None
    assert run(sensortask_wozi.sgp_reader.get_error_counter())["SGP40"]["ErrCount"] == 0

    # The rest of the system is unaffected - task/timer starter collection still works end to end.
    starters = sensortask_wozi._collect_task_starters()
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
        run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
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
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.notify_service is not None
    assert sensortask_wozi.notify_service.cfgmgr.valid is True


# ---------------------------------------------------------------------------
# Debug level - persisted on sysfunct, pushed live to every logger's own set_level() through a
# registry collected once at boot (owner requirement: general, system-wide, not per-module - but
# no shared mutable value anywhere; see SPECIFICATION.md Part A.7's "Debug-level registry"
# section and _collect_level_setters() for the full logger list).
# ---------------------------------------------------------------------------


def _all_loggers() -> "list[Any]":
    w = sensortask_wozi
    assert w.conn is not None and w.ntp is not None and w.fram is not None and w.sysfunct is not None
    assert w.sgp_reader is not None and w.bmp_reader is not None and w.scd_reader is not None
    assert w.pixel is not None and w.notify_service is not None and w.webserver is not None
    return [
        w.conn.pr,
        w.conn.cfgmgr.pr,
        w.conn.dns_server.pr,
        w.ntp.pr,
        w.ntp.cfgmgr.pr,
        w.fram.pr,
        w.sysfunct.pr,
        w.sysfunct.cfgmgr.pr,
        w.sgp_reader.pr,
        w.sgp_reader.cfgmgr.pr,
        w.bmp_reader.pr,
        w.bmp_reader.cfgmgr.pr,
        w.scd_reader.pr,
        w.pixel.pr,
        w.notify_service.pr,
        w.notify_service.cfgmgr.pr,
        w.webserver.pr,
    ]


def test_collect_level_setters_returns_one_entry_per_logger_in_the_object_graph() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    setters = sensortask_wozi._collect_level_setters()
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
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), debug=PrintLog.level_warn()))
    assert sensortask_wozi.sysfunct is not None
    # First boot - no persisted value yet, so sysfunct.setup() writes and resolves the schema
    # default (0), then pushes it out through the registry - overriding the debug= seed every
    # individual module's own logger was constructed with. Matches test_system_service.py's own
    # test_setup_resolves_cfgmgr_and_leaves_debug_level_at_the_default_on_first_boot.
    assert sensortask_wozi.sysfunct.get_debug_level() == 0
    for pr in _all_loggers():
        assert pr.get_level() == 0, f"{pr.name!r} still shows the debug= seed, not the resolved default"


def test_sysfunct_set_debug_level_updates_every_logger_in_the_object_graph() -> None:
    # End-to-end: once Step 2 wires a REST route to sysfunct.set_debug_level(), this is the whole
    # observable effect a real request would have - every logger's own set_level() called directly,
    # no shared mutable value anywhere.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.sysfunct is not None
    ok = run(sensortask_wozi.sysfunct.set_debug_level(PrintLog.level_err()))
    assert ok is True
    for pr in _all_loggers():
        assert pr.get_level() == PrintLog.level_err(), f"{pr.name!r} did not observe set_debug_level()"


def test_debug_level_survives_a_simulated_reboot_through_build_system() -> None:
    cfg_path = _tmp_cfg_dir()
    run(sensortask_wozi.build_system(cfg_path=cfg_path))
    assert sensortask_wozi.sysfunct is not None
    run(sensortask_wozi.sysfunct.set_debug_level(PrintLog.level_once()))

    run(sensortask_wozi.build_system(cfg_path=cfg_path))  # simulated reboot - same cfg_path, fresh objects
    assert sensortask_wozi.sysfunct is not None
    assert sensortask_wozi.sysfunct.get_debug_level() == PrintLog.level_once()
    for pr in _all_loggers():
        assert pr.get_level() == PrintLog.level_once(), f"{pr.name!r} did not get the persisted level on reboot"


# ---------------------------------------------------------------------------
# Task/timer starter collection - shape and membership only, never drives the infinite supervisor
# loop (start_and_check_tasks()) or a starter's own coroutine body. That boundary is Step 5's job.
# ---------------------------------------------------------------------------


def test_collect_task_starters_includes_every_constructed_module() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    starters = sensortask_wozi._collect_task_starters()
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
        sensortask_wozi.scd_reader,
        sensortask_wozi.bmp_reader,
        sensortask_wozi.sgp_reader,
        sensortask_wozi.pixel,
        sensortask_wozi.notify_service,
        sensortask_wozi.sysfunct,
        sensortask_wozi.conn,
        sensortask_wozi.ntp,
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
    # three would otherwise silently never run. Found missing entirely - Step 7 second-pass audit.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    starters = sensortask_wozi._collect_timer_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    for owner in (
        sensortask_wozi.scd_reader,
        sensortask_wozi.bmp_reader,
        sensortask_wozi.sgp_reader,
        sensortask_wozi.pixel,
        sensortask_wozi.notify_service,
        sensortask_wozi.sysfunct,
        sensortask_wozi.conn,
        sensortask_wozi.ntp,
        sensortask_wozi.webserver,
    ):
        assert owner is not None
        for expected in owner.get_timer_starters():
            assert expected in starters, f"no timer starter bound to {owner!r}"


def test_collect_task_starters_never_touches_start_and_check_tasks() -> None:
    # Collection is pure list-building from already-constructed objects - calling it must not
    # start, await, or block on anything. If it did, this test itself would hang.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    sensortask_wozi._collect_task_starters()
    sensortask_wozi._collect_timer_starters()


# ---------------------------------------------------------------------------
# main()'s own composition - build_system() -> start_timers() -> ntp_force_sync() ->
# start_and_check_tasks(), in that order. start_timers()'s real Timer-sequencing mechanism and
# start_and_check_tasks()'s real supervisor loop are each already thoroughly covered by
# test_system_service.py directly - this test fakes both out (they'd otherwise need real
# wall-clock-firing Timers, which tests/machine.py's fake only fires via manual .trigger(), or
# block forever) to verify main() itself wires the pieces together in the right order, matching
# the reference file's own main() shape, without re-proving either subsystem's own internals here.
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
        run(sensortask_wozi.main(cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        AsyNtpClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]

    assert calls == ["start_timers", "force_sync", "start_and_check_tasks"]
    # build_system() itself already ran (construction succeeded) - main() reaches the task-starting
    # phase with every module in place, not just up to build_system().
    assert sensortask_wozi.sysfunct is not None


# ---------------------------------------------------------------------------
# Webserver wiring (closed in a later session) - build_system() now
# also constructs a real Microdot() app + WebserverService, registering every real driver's
# SettingsGroup/status_source/system_cmd/notification_led/maintenance_sensor/error_source. These
# tests check the *real* registrations landed correctly (right module, right fields, right hooks) -
# not the generic dispatch/aggregation logic itself, which tests/test_asy_webserver_service.py's own
# uniform-fake suite already covers in full depth (its own endpoint-design decision).
# ---------------------------------------------------------------------------


def _dispatch(method: str, path: str, json_body: "dict[str, Any] | None" = None) -> "Any":
    assert sensortask_wozi.webserver is not None
    app = sensortask_wozi.webserver._app
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    req = Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)
    return run(app.dispatch_request(req))


def test_webserver_pr_is_ram_only_not_fram_backed() -> None:
    # Deliberate decision (see build_system()'s own comment): a warning on every per-call/outer-cap
    # reclaim could churn far faster than any sensor's rare-hardware-fault log - keeping it RAM-only
    # also preserves the five-chunk FRAM allocation order (see SPECIFICATION.md Part A.7) unchanged, not a
    # sixth chunk.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.webserver is not None
    assert isinstance(sensortask_wozi.webserver.pr, PrintLogHistory)
    assert not isinstance(sensortask_wozi.webserver.pr, PrintLogHistoryStore)


def test_webserver_measurements_and_sensors_get_include_every_real_sensor() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("GET", "/measurements")
    assert res.status_code == 200
    measurements = json.loads(res.body)
    assert set(measurements.keys()) == {"SCD30", "BMP3XX", "SGP40"}
    # Regression coverage for a real bug found via a real user report against the real assembled
    # system: every real driver's own get_dict_data()/get_dict_cfg() already returns a
    # {name: {...}} self-wrapped shape, and _get_measurements()/_get_sensors() used to index that
    # by name again, producing {"SCD30": {"SCD30": {...}}} for every sensor - see
    # src/asy_webserver_service.py's own comments there for the full account. Only checking
    # top-level keys (as this test used to) doesn't catch that.
    for name, fields in measurements.items():
        assert name not in fields, f"{name}'s own value is still self-wrapped: {fields!r}"
        assert fields, f"{name} returned no fields at all"

    res = _dispatch("GET", "/sensors")
    sensors = json.loads(res.body)
    assert set(sensors.keys()) == {"SCD30", "BMP3XX", "SGP40"}
    for name, fields in sensors.items():
        assert name not in fields, f"{name}'s own value is still self-wrapped: {fields!r}"
        assert fields, f"{name} returned no fields at all"


def test_webserver_sensors_put_round_trips_a_real_field_through_the_real_driver() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/sensors", {"SGP40": {"BackupPeriod": 5}})
    body = json.loads(res.body)
    assert body["result"] == {"SGP40": {"BackupPeriod": "Valid"}}
    assert sensortask_wozi.sgp_reader is not None
    assert run(sensortask_wozi.sgp_reader.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}


def test_webserver_sensors_put_round_trips_a_real_scd30_field_through_the_real_driver() -> None:
    # Regression test from baseline verification: SCD30_Reader
    # is the only sensors=-registered module that's a plain SensorReader rather than a
    # SensorReaderConfig subclass (no local cfgmgr - these params live on the sensor itself, see
    # asy_scd30_driver.py's own _VAL_* comment), so it never inherited get_cfg_schema() the way
    # every other registered sensor does. _put_sensors() calls module.get_cfg_schema() uniformly
    # for every sensor named in the PUT body - without SCD30_Reader's own now-added method, this
    # crashed with a real 500 (AttributeError). The existing SGP40 round-trip test just above
    # never exercised this because SGP40 is a SensorReaderConfig subclass; this is the SCD30
    # counterpart, added because nothing in this file (or tests/test_setter_microdot_integration.py,
    # which routes SCD30 through a separate hand-rolled endpoint instead of the real /sensors PUT
    # route) ever put the real WebserverService._put_sensors() route and SCD30 together before.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/sensors", {"SCD30": {"MeasInt": 4}})
    body = json.loads(res.body)
    assert body["result"] == {"SCD30": {"MeasInt": "Valid"}}


def test_webserver_networking_put_ssid_group_reconnects_but_led_group_alone_does_not() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.conn is not None
    res = _dispatch("PUT", "/networking", {"LedWifiOn": False})
    assert json.loads(res.body)["result"] == {"LedWifiOn": "Valid"}
    assert sensortask_wozi.conn.reconn_wifi is False  # LedWifiOn alone must never reconnect

    res = _dispatch("PUT", "/networking", {"Hostname": "TestHost"})
    assert json.loads(res.body)["result"] == {"Hostname": "Valid"}
    assert sensortask_wozi.conn.reconn_wifi is True  # setNetwork's own field group did change


def test_webserver_networking_put_ntp_fields_forces_a_resync() -> None:
    # Same observable-effect precedent as tests/test_setter_microdot_integration.py's own
    # ntp_force_sync() coverage: a failing-sync streak in progress, cleared to 0 by the post_asy_fct.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.ntp is not None
    sensortask_wozi.ntp.ntp_retries = 3
    res = _dispatch("PUT", "/networking", {"NTP_Host": "time.example.org"})
    assert json.loads(res.body)["result"] == {"NTP_Host": "Valid"}
    assert sensortask_wozi.ntp.ntp_retries == 0  # post_asy_fct fired


def test_webserver_system_put_debug_level_propagates_to_every_logger() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.sysfunct is not None and sensortask_wozi.conn is not None
    res = _dispatch("PUT", "/system", {"DebugLevel": PrintLog.level_err()})
    assert json.loads(res.body)["result"]["DebugLevel"] == "Valid"
    assert sensortask_wozi.sysfunct.get_debug_level() == PrintLog.level_err()
    assert sensortask_wozi.conn.pr.get_level() == PrintLog.level_err()  # pushed via the registry


def test_webserver_system_put_gmt_dst_offset_applies_without_a_reconnect() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.ntp is not None and sensortask_wozi.conn is not None
    res = _dispatch("PUT", "/system", {"GMTOffset": 7200})
    assert json.loads(res.body)["result"] == {"GMTOffset": "Valid"}
    assert run(sensortask_wozi.ntp.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 7200}
    assert sensortask_wozi.conn.reconn_wifi is False  # unrelated to the networking settings groups


def test_webserver_system_put_reboot_cmd_arms_the_real_reset_timer() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.sysfunct is not None
    before = machine.reset_count
    res = _dispatch("PUT", "/system", {"SystemCmd": "reboot"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Valid"
    sensortask_wozi.sysfunct.reset_timer.trigger()  # fake Timer - fires the armed callback synchronously
    assert machine.reset_count == before + 1


def test_webserver_system_put_invalid_cmd_is_rejected_without_side_effects() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    before = machine.reset_count
    res = _dispatch("PUT", "/system", {"SystemCmd": "bogus"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Invalid"
    assert machine.reset_count == before


def test_webserver_notification_put_light_cmd_led_dispatches_to_the_real_pixel_driver() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_light_cmd_led_accepts_integral_float_rgb_and_int_t_coerced() -> None:
    # config_manager.py's coerce_numeric() policy applied to lightCmdLED too (SPECIFICATION.md
    # Part A.8): an integral float r/g/b coerces to int, a plain int t coerces to float - both
    # directions a real client could plausibly send.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10.0, "g": 20.0, "b": 30.0, "t": 1}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_light_cmd_led_rejects_fractional_rgb() -> None:
    # Regression test for the behavior this callback used to have (raw int()/float() truncating
    # casts, commits 53b5147/b5502c8): a fractional r/g/b is now rejected outright, not silently
    # truncated (12.5 no longer becomes a silent 12).
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10.5, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_non_numeric_field() -> None:
    # Another behavior change from the old raw int()/float() casts: those would silently parse a
    # numeric-looking string ("10") via Python's lenient int()/float() constructors - coerce_numeric()
    # never parses strings, only coerces between the two numeric types, so this is now rejected too.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": "10", "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_non_numeric_t() -> None:
    # t goes through cm.coerce_numeric(payload["t"], float) - a distinct code path from r/g/b's own
    # int coercion (already tested above for r specifically) - confirms the same non-numeric
    # rejection holds for t's own float-typed branch, not just the int-typed ones.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": "soon"}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_missing_field() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30}})  # t missing
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_out_of_range_rgb() -> None:
    # Regression test for WEBSITE_PLAN.md §8's "lightCmdLED legacy-vs-src/ divergence" gap: legacy's
    # own led_cmd() (modules/sensortask-wozi.py) validates and rejects out-of-range r/g/b (0-255) via
    # update_valid_json(...) - the promoted src/ callback used to silently clamp instead
    # (asy_neopixel_driver.py's _clamp_byte()). Rejected exactly like a missing/non-numeric field.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 256, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_negative_rgb() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": -1, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_rejects_out_of_range_t() -> None:
    # Legacy's own t bound is 0.5-60.0 (modules/sensortask-wozi.py) - the promoted src/ callback used
    # to floor a too-small t to 0.1 (asy_neopixel_driver.py's neopixel_signal()) and never bounded a
    # too-large one at all.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 0.1}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 100.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


def test_webserver_notification_put_light_cmd_led_accepts_lower_boundary_rgb_and_t() -> None:
    # Deliberately one dispatch per test (not both boundaries in one test function): _dispatch()
    # drives each call through its own fresh asyncio.run(), so NeopixelDriver's background
    # neopixel_signal() consumer task never actually runs here - a second real request_signal()
    # call in the same test would find start_signal_event already set from the first call and
    # never cleared, hanging forever in request_signal()'s own `while ...: await asyncio.sleep(0)`
    # loop. Matches every other lightCmdLED test in this file's own single-dispatch convention.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 0, "g": 255, "b": 0, "t": 0.5}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_light_cmd_led_accepts_upper_boundary_rgb_and_t() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    res = _dispatch("PUT", "/notification", {"lightCmdLED": {"r": 255, "g": 0, "b": 255, "t": 60.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


def test_webserver_notification_put_pause_time_dispatches_to_the_real_coordinator() -> None:
    # Regression test: the legacy `pauseAutoLED` override-countdown command (pixel.set_override_led()
    # in modules/sensortask-wozi.py) had no equivalent wiring at all in the promoted REST layer until
    # this fix - _notification_pause_callback()/notification_pause= closes that gap.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.notify_service is not None
    assert run(sensortask_wozi.notify_service.get_override_led()) == 0
    res = _dispatch("PUT", "/notification", {"PauseTime": 60})
    assert json.loads(res.body)["result"]["PauseTime"] == "Valid"
    assert run(sensortask_wozi.notify_service.get_override_led()) == 60


def test_webserver_notification_put_flat_field_round_trips_through_the_real_coordinator() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.notify_service is not None
    res = _dispatch("PUT", "/notification", {"WarnCO2": 1800})
    assert json.loads(res.body)["result"] == {"WarnCO2": "Valid"}
    assert run(sensortask_wozi.notify_service.cfgmgr.get_dict(["WarnCO2"])) == {"WarnCO2": 1800}


def test_webserver_status_get_reflects_the_real_object_graph() -> None:
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
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
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.conn is not None
    run(sensortask_wozi.conn.pr.err_s("simulated", errno=99))
    assert (run(sensortask_wozi.conn.get_error_counter()))["WIFI"]["ErrCount"] == 1
    res = _dispatch("PUT", "/status", {"ResetErrors": True})
    assert json.loads(res.body)["res"] == "OK"
    assert (run(sensortask_wozi.conn.get_error_counter()))["WIFI"]["ErrCount"] == 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
