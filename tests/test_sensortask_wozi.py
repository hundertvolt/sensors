"""Construction/wiring tests for sensortask_wozi.py's build_system() - Step 1's async-safe rewrite
of improved-quality/sensortask-wozi.py's flat, module-level construction sequence (see
FINAL_WIRING_PLAN.md's Step 1 section and WIRING_CONTRACT.md for the full rationale). Verifies, in
one place, everything the "Criteria for this step to finish" checklist asks for:

- Every module the reference file constructs is reachable as a plain module-level attribute of
  sensortask_wozi (conn, ntp, i2c0, i2c1, spi0, fram, sysfunct, sgp_reader, bmp_reader, scd_reader,
  pixel, notify_service) - bare globals, not a wrapper container (owner-confirmed, see
  FINAL_WIRING_PLAN.md's refined-plan Q3).
- The real FRAM chunk order (five chunks, not four - WIRING_CONTRACT.md item 8's correction):
  SystemService -> SGP40_Reader's own log -> SGP40_Reader's VOC backup -> NeopixelDriver ->
  NotificationCoordinator.
- The grouped await x.setup() batch (fram -> sgp_reader -> bmp_reader -> notify_service), and the
  one real ordering constraint that makes grouping correct rather than just tidy:
  notify_service.setup() only runs after notify_service.finalize() (asy_notification_service.py's
  own documented contract).
- get_task_starters()/get_timer_starters() collection reaching every constructed module, without
  ever driving start_and_check_tasks()'s intentionally-infinite supervisor loop - that boundary
  (boot-to-steady-state) belongs to Step 5, not Step 1 (FINAL_WIRING_PLAN.md's own scoping).
- build_system() is independently callable and returns - no top-level blocking call anywhere in
  this module (the two-file split from FINAL_WIRING_PLAN.md's refined plan: the real
  blocking-import production entry point lives in boot_entry/wozi_boot.py instead). If this file
  hangs the test process, that alone is a real Step 1 regression.

Deliberately not covered here: Microdot/routes (excluded from Step 1 entirely, owner-confirmed -
see FINAL_WIRING_PLAN.md's refined plan Q2), real sensor I2C/SPI transactions (tests/machine.py's
raw bus fakes only - the digital twin is Step 3's job and Step 1 has no dependency on it).
"""

import asyncio
import os

from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
import sensortask_wozi
from print_log import PrintLog, PrintLogHistoryStore

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
    # conn.set_ext_led(pixel) - the one cross-wiring step that must run after both objects exist
    # (WIRING_CONTRACT.md item 13). Confirmed indirectly: AsyConnTime's own ext_led slot is set.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    assert sensortask_wozi.conn is not None
    assert sensortask_wozi.conn.ext_led is sensortask_wozi.pixel


def test_build_system_is_independently_callable_and_returns() -> None:
    # The whole point of the two-file split (FINAL_WIRING_PLAN.md's refined plan): importing this
    # test file and calling build_system() must never block. If this test hangs, that's the
    # regression to report - not something to work around here.
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))


# ---------------------------------------------------------------------------
# FRAM chunk order - five chunks, exact relative sequence (WIRING_CONTRACT.md item 8's correction).
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


def test_setup_batch_runs_sysfunct_then_fram_then_sgp_then_bmp_then_notify_in_order() -> None:
    calls: list[str] = []
    from asy_bmp3xx_driver import BMP3xx_Reader
    from asy_fram_manager import AsyFramManager
    from asy_notification_service import NotificationCoordinator
    from asy_sgp40_driver import SGP40_Reader
    from system_service import SystemService

    real_sysfunct_setup = SystemService.setup
    real_fram_setup = AsyFramManager.setup
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
    SGP40_Reader.setup = _tracking_sgp_setup  # type: ignore[method-assign]
    BMP3xx_Reader.setup = _tracking_bmp_setup  # type: ignore[method-assign]
    NotificationCoordinator.setup = _tracking_notify_setup  # type: ignore[method-assign]
    NotificationCoordinator.finalize = _tracking_notify_finalize  # type: ignore[method-assign]
    try:
        run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.setup = real_sysfunct_setup  # type: ignore[method-assign]
        AsyFramManager.setup = real_fram_setup  # type: ignore[method-assign]
        SGP40_Reader.setup = real_sgp_setup  # type: ignore[method-assign]
        BMP3xx_Reader.setup = real_bmp_setup  # type: ignore[method-assign]
        NotificationCoordinator.setup = real_notify_setup  # type: ignore[method-assign]
        NotificationCoordinator.finalize = real_notify_finalize  # type: ignore[method-assign]

    # notify_finalize runs during synchronous construction, before any setup() call; sysfunct is
    # first *within* the async setup() batch - resolves the real persisted debug level as early as
    # possible (this module's own docstring).
    assert calls == ["notify_finalize", "sysfunct", "fram", "sgp", "bmp", "notify_setup"]


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
# no shared mutable value anywhere; see sensortask_wozi.py's own module docstring and
# _collect_level_setters() for the full logger list).
# ---------------------------------------------------------------------------


def _all_loggers() -> "list[Any]":
    w = sensortask_wozi
    assert w.conn is not None and w.ntp is not None and w.fram is not None and w.sysfunct is not None
    assert w.sgp_reader is not None and w.bmp_reader is not None and w.scd_reader is not None
    assert w.pixel is not None and w.notify_service is not None
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
    # No Microdot/webserver task in Step 1 (owner-confirmed - FINAL_WIRING_PLAN.md's refined plan
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
    run(sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir()))
    starters = sensortask_wozi._collect_timer_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    for owner in (
        sensortask_wozi.scd_reader,
        sensortask_wozi.bmp_reader,
        sensortask_wozi.sgp_reader,
        sensortask_wozi.sysfunct,
        sensortask_wozi.conn,
        sensortask_wozi.ntp,
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
