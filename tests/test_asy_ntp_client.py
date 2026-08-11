import asyncio
import os
import select
import socket
import struct
import time

from _fram_chip_fake import FakeMB85RS64V
from machine import RTC, Timer

import asy_ntp_client as ntpmod
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_ntp_client import AsyNtpClient
from print_log import PrintLogHistoryStore

# Same one-process-per-test-file swap as test_base_classes.py/test_asy_fram_driver.py/
# test_asy_fram_manager.py - only exercised by the fram= wiring test below, isolated to this
# file's own process.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _last_err(counter: "dict[str, dict[str, int | list[int] | list[str]]]", field: str) -> "int | str":
    value = counter["NTP"][field]  # ErrNum/ErrType are list-shaped once _error_check() has run once
    assert isinstance(value, list)
    return value[-1]


# Mirrors asy_ntp_client.py's own _VAL_NH/_VAL_NOS/_VAL_NIH/_VAL_GMT/_VAL_DST schema tuples -
# not importable once const()-folded (same reasoning as test_asy_wifi_service.py's own
# duplicated _PHASE_* constants), so mirrored here instead.
_VAL_NH = (("NTP_Host", "str", "pool.ntp.org", 3, 1024, None),)
_VAL_NOS = (("NTP_Offset_S", "int", 0, -43200, 43200, None),)
_VAL_NIH = (("NTP_Interv_H", "int", 12, 1, 24, None),)
_VAL_GMT = (("GMTOffset", "int", 3600, -43200, 43200, None),)
_VAL_DST = (("DSTOffset", "int", 3600, -43200, 43200, None),)


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass  # already gone, or genuinely not removable - not this helper's problem


def _tmp_cfg_dir() -> str:
    # A fresh, unique directory per call - AsyNtpClient now names its own config file
    # unconditionally ("config_NTP.cfg", from base_classes.py's SensorReaderConfig), so tests can
    # no longer isolate each other via distinct filenames the way the old externally-injected
    # ConfigManager tests did; a fresh directory does the same job.
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/ntp_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    _remove_any(path + "/config_NTP.cfg")  # clear any stale leftover (file or directory) from a previous run
    return path + "/"


def make_client(
    wifi_mode_lock: "asyncio.Lock | None" = None,
    network_available: "Callable[[], bool] | None" = None,
    get_dns_server: "Callable[[], str | None] | None" = None,
    max_i2c_err: int = 5,
    dns_timeout_ms: int = 500,
    dns_tries: int = 1,
    ntp_fetch_timeout_ms: int = 5000,
    debug: "int | None" = None,
    cfg_path: "str | None" = None,
    fram: "AsyFramManager | None" = None,
) -> AsyNtpClient:
    if wifi_mode_lock is None:
        wifi_mode_lock = asyncio.Lock()
    if network_available is None:
        network_available = lambda: True  # noqa: E731
    if get_dns_server is None:
        get_dns_server = lambda: None  # noqa: E731
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    client = AsyNtpClient(
        wifi_mode_lock,
        network_available,
        get_dns_server,
        max_i2c_err=max_i2c_err,
        dns_timeout_ms=dns_timeout_ms,
        dns_tries=dns_tries,
        ntp_fetch_timeout_ms=ntp_fetch_timeout_ms,
        debug=debug,
        cfg_path=cfg_path,
        fram=fram,
    )
    run(client.cfgmgr.setup())
    return client


def make_client_with_json(json_text: str) -> AsyNtpClient:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(json_text)
    return make_client(cfg_path=cfg_path)


def make_invalid_cfg_client() -> AsyNtpClient:
    # A directory where ConfigManager expects a plain file - its own os.stat() 0x4000 (MP_S_IFDIR)
    # check rejects this and leaves self.valid False; the same "config manager itself is invalid"
    # state the old empty-schema make_broken_cfgmgr() reproduced a different way (this driver's own
    # schema is fixed and non-empty now, so that route no longer applies here).
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_NTP.cfg")
    return make_client(cfg_path=cfg_path)


class _RaiseOnArm:
    # Same technique as test_system_service.py's own _RaiseOnArm - toggles tests/machine.py's
    # Timer.raise_on_arm (a shared class attribute, not per-instance) for the duration of the
    # `with` block, simulating real rp2 alarm-pool exhaustion (OSError(ENOMEM) from Timer.init()).
    # `exc` picks which arm of every call site's own `except (OSError, MemoryError)` is exercised -
    # MemoryError is not an OSError subclass (see CLAUDE.md/SPECIFICATION.md Part F), so neither arm
    # covers the other. Timer.raise_on_arm_exc is a shared class attribute too, reset back to its
    # OSError default on exit alongside raise_on_arm.
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "_RaiseOnArm":
        Timer.raise_on_arm_exc = self._exc
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: "Any") -> None:
        Timer.raise_on_arm = False
        Timer.raise_on_arm_exc = OSError


_next_port = 53000


def make_addr() -> "tuple[str, int]":
    global _next_port
    _next_port += 1
    # Same Unix-port-only workaround as test_asy_udp_socket.py's make_addr(): a plain (host, port)
    # tuple is rejected by bind()/connect()/sendto() on this port's "standard" build.
    return socket.getaddrinfo("127.0.0.1", _next_port)[0][-1]  # type: ignore[return-value]


def make_port() -> int:
    # A raw port int, sharing make_addr()'s own counter - needed wherever a test has to redirect
    # _NTP_UDP_PORT (see FakeNtpServer below), since make_addr()'s own return value is opaque/
    # non-indexable on this Unix port (the same reason it's never indexed into elsewhere in this file).
    global _next_port
    _next_port += 1
    return _next_port


# ---------------------------------------------------------------------------
# __init__ - AsyNtpClient now extends base_classes.py's SensorReaderConfig: it owns its own
# config_NTP.cfg file/schema internally (no externally-injected ConfigManager, no separate
# get_default_cfg()/_DEFAULT_CONFIG merge step anymore - see DRIVER_SPEC.md/BACKLOG.md).
# ---------------------------------------------------------------------------


def test_init_never_synced_before_first_task_run() -> None:
    client = make_client()
    assert run(client.ntp_issynced()) is False
    assert run(client.get_last_ntp_sync()) is None


def test_init_creates_its_own_config_file_with_schema_defaults() -> None:
    cfg_path = _tmp_cfg_dir()
    client = make_client(cfg_path=cfg_path)
    assert client.cfgmgr.valid is True
    values = run(client.cfgmgr.get_dict(["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"]))
    assert values == {
        "NTP_Host": "pool.ntp.org",
        "NTP_Offset_S": 0,
        "NTP_Interv_H": 12,
        "GMTOffset": 3600,
        "DSTOffset": 3600,
    }


def test_config_persists_across_a_fresh_client_instance_pointed_at_the_same_path() -> None:
    # Proves config_NTP.cfg is genuinely read from disk at __init__, not just written once and
    # cached in-process - a second, independent client pointed at the same cfg_path must see the
    # same persisted values, not fall back to schema defaults.
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(_VALID_JSON)
    first = make_client(cfg_path=cfg_path)
    second = make_client(cfg_path=cfg_path)
    first_cfg = run(first._get_ntp_config())
    second_cfg = run(second._get_ntp_config())
    assert first_cfg is not None
    assert second_cfg is not None
    first_host, _first_offs = first_cfg
    second_host, _second_offs = second_cfg
    assert first_host == ["time.example.org"]
    assert second_host == ["time.example.org"]


def test_two_clients_with_different_cfg_paths_have_independent_configs() -> None:
    first = make_client_with_json(_VALID_JSON)
    second = make_client()  # fresh directory, defaults only
    first_cfg = run(first._get_ntp_config())
    second_cfg = run(second._get_ntp_config())
    assert first_cfg is not None
    assert second_cfg is not None
    first_host, _first_offs = first_cfg
    second_host, _second_offs = second_cfg
    assert first_host == ["time.example.org"]
    assert second_host == ["pool.ntp.org"]


def test_debug_level_propagates_to_the_inherited_pr_logger() -> None:
    print("(expected) debug=3 makes the fresh ConfigManager below log its normal first-use config-file creation")
    client = make_client(debug=3)
    assert client.pr.get_level() == 3


def test_get_task_starters_returns_all_three_ntp_tasks() -> None:
    client = make_client()
    assert client.get_task_starters() == [
        client.start_asy_ntp_client,
        client.start_asy_ntp_refresh,
        client.start_asy_sync_age_counter,
    ]


def test_get_timer_starters_returns_both_ntp_timers() -> None:
    client = make_client()
    assert client.get_timer_starters() == [client.start_ntp_timer, client.start_counter_timer]


def test_start_asy_ntp_refresh_returns_a_real_task() -> None:
    client = make_client()

    async def scenario() -> bool:
        task = client.start_asy_ntp_refresh()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_start_asy_sync_age_counter_returns_a_real_task() -> None:
    client = make_client()

    async def scenario() -> bool:
        task = client.start_asy_sync_age_counter()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_fram_given_uses_fram_backed_logging() -> None:
    # AsyNtpClient didn't accept a fram= parameter at all before this migration - proves the
    # constructor actually forwards it to SensorReaderConfig/SensorReader rather than silently
    # dropping it (the same real, promoted AsyFramManager + simulated chip test_base_classes.py
    # uses for the equivalent base-class-level check, exercised here as an integration check of
    # this driver's own constructor wiring).
    bus = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=0x2000)
    client = make_client(fram=manager)
    assert isinstance(client.pr, PrintLogHistoryStore)


# ---------------------------------------------------------------------------
# get_dict_cfg / get_data / get_dict_data / get_error_counter - the base-class getter quartet
# (DRIVER_SPEC.md section 4.2). Setters are explicitly out of scope (see BACKLOG.md).
# ---------------------------------------------------------------------------


def test_get_dict_cfg_returns_schema_defaults_wrapped_in_ntp_key() -> None:
    client = make_client()
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTP_Host": "pool.ntp.org",
            "NTP_Offset_S": 0,
            "NTP_Interv_H": 12,
            "GMTOffset": 3600,
            "DSTOffset": 3600,
        }
    }


def test_get_dict_cfg_reflects_a_customized_on_disk_config() -> None:
    client = make_client_with_json(_VALID_JSON)
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTP_Host": "time.example.org",
            "NTP_Offset_S": 5,
            "NTP_Interv_H": 6,
            "GMTOffset": 7200,
            "DSTOffset": 3600,
        }
    }


def test_get_dict_cfg_returns_all_none_values_when_config_manager_is_invalid() -> None:
    client = make_invalid_cfg_client()
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTP_Host": None,
            "NTP_Offset_S": None,
            "NTP_Interv_H": None,
            "GMTOffset": None,
            "DSTOffset": None,
        }
    }


def test_get_data_and_get_dict_data_reflect_the_initial_never_synced_state() -> None:
    client = make_client()
    data = run(client.get_data())
    assert data.Synced is False
    assert data.LastSyncAge is None
    dict_data = run(client.get_dict_data())
    assert dict_data == {"NTP": {"Synced": False, "LastSyncAge": None, "TS": data.TS}}


def test_get_data_reflects_a_successful_sync() -> None:
    client = make_client()
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge == 0


def test_get_dict_data_reflects_a_successful_sync() -> None:
    client = make_client()
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    dict_data = run(client.get_dict_data())
    assert dict_data["NTP"]["Synced"] is True
    assert dict_data["NTP"]["LastSyncAge"] == 0


def test_get_error_counter_starts_empty_and_records_a_real_error() -> None:
    client = make_client()
    run(client.pr.setup())
    counter = run(client.get_error_counter())
    assert counter["NTP"]["ErrCount"] == 0
    run(client.pr.err_s("boom", errno=1))
    counter = run(client.get_error_counter())
    assert counter["NTP"]["ErrCount"] == 1


def test_get_error_counter_counts_a_warning_too() -> None:
    # Full-dict equality (not indexing into the union-typed ErrNum/ErrType values) - same style
    # test_print_log.py's own get_log() tests use; history_length defaults to 10 (make_client()
    # doesn't override it), so 9 untouched "N"/0 slots precede the one real warning.
    client = make_client()
    run(client.pr.setup())
    run(client.pr.wrn_s("careful", wrnno=1))
    counter = run(client.get_error_counter())
    assert counter == {"NTP": {"ErrCount": 1, "ErrNum": [0] * 9 + [1], "ErrType": ["N"] * 9 + ["W"]}}


def test_get_error_counter_records_multiple_entries_in_order() -> None:
    client = make_client()
    run(client.pr.setup())
    run(client.pr.err_s("first error", errno=1))
    run(client.pr.wrn_s("first warning", wrnno=2))
    counter = run(client.get_error_counter())
    assert counter == {"NTP": {"ErrCount": 2, "ErrNum": [0] * 8 + [1, 2], "ErrType": ["N"] * 8 + ["E", "W"]}}


# ---------------------------------------------------------------------------
# _now() / _set_synced() / _set_last_sync_age() / _increment_last_sync_age() - the internal
# state-mutation helpers that replaced last_ntp_sync's/ntp_synced's old independent LockedCounter/
# LockedFlag objects. These are exercised incidentally as test setup throughout this file, but the
# field-preservation/None-handling/clamping contract they're actually responsible for needs its own
# direct coverage - this is exactly the concurrency-safety claim BACKLOG.md's fifth-pass entry
# makes (each helper does an unlocked get-then-set pair, safe only because nothing in between
# awaits - see asy_ntp_client.py's own comment on _set_synced()).
# ---------------------------------------------------------------------------


def test_now_returns_a_real_unix_timestamp() -> None:
    client = make_client()
    result = client._now()
    assert result is not None
    assert result >= 1735689600  # sane lower bound - _NTP_MIN_PLAUSIBLE_UNIX_TIME, compiled away


class _RaisingTimeForNow:
    def __init__(self, exc: "Exception") -> None:
        self._exc = exc

    def gmtime(self, *_a: "Any") -> "Any":
        raise self._exc

    def mktime(self, *_a: "Any") -> "Any":
        raise self._exc


def test_now_returns_none_on_overflow_error() -> None:
    client = make_client()
    original_time = ntpmod.time
    ntpmod.time = _RaisingTimeForNow(OverflowError("past rp2's ~2037 32-bit epoch range"))  # type: ignore[assignment]
    try:
        result = client._now()
    finally:
        ntpmod.time = original_time
    assert result is None


def test_now_returns_none_on_os_error() -> None:
    client = make_client()
    original_time = ntpmod.time
    ntpmod.time = _RaisingTimeForNow(OSError("simulated RTC read failure"))  # type: ignore[assignment]
    try:
        result = client._now()
    finally:
        ntpmod.time = original_time
    assert result is None


def test_set_synced_to_true_preserves_last_sync_age_and_ts() -> None:
    client = make_client()
    run(client._set_last_sync_age(42))
    before = run(client.get_data())
    run(client._set_synced(True))
    after = run(client.get_data())
    assert after.Synced is True
    assert after.LastSyncAge == 42
    assert after.TS == before.TS  # _set_synced() never touches TS


def test_set_synced_to_false_preserves_last_sync_age() -> None:
    client = make_client()
    run(client._set_synced(True))
    run(client._set_last_sync_age(7))
    run(client._set_synced(False))
    data = run(client.get_data())
    assert data.Synced is False
    assert data.LastSyncAge == 7


def test_set_last_sync_age_preserves_synced_flag_when_true() -> None:
    client = make_client()
    run(client._set_synced(True))
    run(client._set_last_sync_age(99))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge == 99


def test_set_last_sync_age_to_none_preserves_synced_flag() -> None:
    client = make_client()
    run(client._set_synced(True))
    run(client._set_last_sync_age(None))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge is None


def test_increment_last_sync_age_from_none_yields_one() -> None:
    # None counts as 0, then +1 - matches base_classes.py's LockedCounter.increment() this
    # replaces (see BACKLOG.md's fifth-pass entry: an earlier draft got this wrong, returning 0).
    client = make_client()
    result = run(client._increment_last_sync_age())
    assert result == 1
    assert run(client.get_data()).LastSyncAge == 1


def test_increment_last_sync_age_from_a_real_value_adds_one() -> None:
    client = make_client()
    run(client._set_last_sync_age(10))
    result = run(client._increment_last_sync_age())
    assert result == 11


def test_increment_last_sync_age_clamps_at_uint32_max() -> None:
    client = make_client()
    run(client._set_last_sync_age(0xFFFFFFFF))
    result = run(client._increment_last_sync_age())
    assert result == 0xFFFFFFFF  # clamped, not wrapped/overflowed


def test_increment_last_sync_age_preserves_synced_flag() -> None:
    client = make_client()
    run(client._set_synced(True))
    run(client._increment_last_sync_age())
    data = run(client.get_data())
    assert data.Synced is True


# ---------------------------------------------------------------------------
# Timer start/stop - normal arm, and real rp2 alarm-pool exhaustion (OSError(ENOMEM))
# ---------------------------------------------------------------------------


def test_start_ntp_timer_arms_periodic_with_the_documented_period() -> None:
    client = make_client()
    client.start_ntp_timer()
    assert client.ntp_timer.mode == Timer.PERIODIC
    assert client.ntp_timer.period == 10 * 1000  # _NTP_CHECK_INTERV: const(), compiled away, hardcoded


def test_start_ntp_timer_fires_the_trigger_event() -> None:
    client = make_client()
    client.start_ntp_timer()

    async def scenario() -> bool:
        client.ntp_timer.trigger()
        try:
            await asyncio.wait_for(client.ntp_timer_trigger_event.wait(), 0.2)
            return True
        except asyncio.TimeoutError:
            return False

    assert run(scenario())


def test_start_ntp_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client(debug=1)
    print("(expected) simulating alarm-pool exhaustion - the following 'Could not start NTP timer' is intentional")
    with _RaiseOnArm():
        client.start_ntp_timer()  # must not raise despite the timer failing to arm
    assert client.ntp_timer.period == -1  # never actually armed


def test_start_ntp_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_ntp_timer()'s own
    # `except (OSError, MemoryError)`: a real alarm allocation can fail with MemoryError instead,
    # which is not an OSError subclass - same graceful degradation must hold either way.
    client = make_client(debug=1)
    print("(expected) simulating an allocation failure - the following 'Could not start NTP timer' is intentional")
    with _RaiseOnArm(MemoryError):
        client.start_ntp_timer()  # must not raise despite the timer failing to arm
    assert client.ntp_timer.period == -1  # never actually armed


def test_stop_ntp_timer_deinits() -> None:
    client = make_client()
    client.start_ntp_timer()
    client.stop_ntp_timer()
    assert client.ntp_timer.deinit_called is True


def test_start_counter_timer_arms_periodic_1s() -> None:
    client = make_client()
    client.start_counter_timer()
    assert client.counter_timer.mode == Timer.PERIODIC
    assert client.counter_timer.period == 1000


def test_start_counter_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    with _RaiseOnArm():
        client.start_counter_timer()
    assert client.counter_timer.period == -1


def test_start_counter_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_counter_timer()'s own
    # `except (OSError, MemoryError)`.
    client = make_client()
    with _RaiseOnArm(MemoryError):
        client.start_counter_timer()
    assert client.counter_timer.period == -1


def test_stop_counter_timer_deinits() -> None:
    client = make_client()
    client.start_counter_timer()
    client.stop_counter_timer()
    assert client.counter_timer.deinit_called is True


# ---------------------------------------------------------------------------
# ntp_issynced / ntp_force_sync / get_last_ntp_sync
# ---------------------------------------------------------------------------


def test_ntp_force_sync_resets_last_sync_retries_and_fires_the_sync_trigger() -> None:
    client = make_client()

    async def scenario() -> bool:
        await client._set_last_sync_age(5)
        client.ntp_retries = 2
        await client.ntp_force_sync()
        assert await client.get_last_ntp_sync() is None
        assert client.ntp_retries == 0
        try:
            await asyncio.wait_for(client.ntp_sync_trigger_event.wait(), 0.2)
            return True
        except asyncio.TimeoutError:
            return False

    assert run(scenario())


def test_ntp_force_sync_deinits_a_pending_retry_timer() -> None:
    client = make_client()
    client.ntp_retry_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda b: None)
    run(client.ntp_force_sync())
    assert client.ntp_retry_timer.deinit_called is True


# ---------------------------------------------------------------------------
# Configuration: every valid field, and single/multiple invalid recombinations coming from a real
# on-disk config_NTP.cfg file, exercised through the real ConfigManager AsyNtpClient now owns
# internally (not mocked) - proving asy_ntp_client.py's own handling of ConfigManager's per-field
# defaulting, not re-testing ConfigManager's own contract (already covered by test_config_manager.py).
# ---------------------------------------------------------------------------

_VALID_JSON = (
    '{"NTP_Host": "time.example.org", "NTP_Offset_S": 5, "NTP_Interv_H": 6, '
    '"GMTOffset": 7200, "DSTOffset": 3600}'
)


def test_get_ntp_config_returns_real_values_from_a_fully_valid_file() -> None:
    client = make_client_with_json(_VALID_JSON)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["time.example.org"]
    assert ntp_offs == [5]


def test_get_ntp_config_single_invalid_field_falls_back_to_default_for_that_field_only() -> None:
    # NTP_Host too short (min length 3) - falls back to its own default; NTP_Offset_S stays real.
    json_text = '{"NTP_Host": "ab", "NTP_Offset_S": 5, "NTP_Interv_H": 6, "GMTOffset": 7200, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]  # defaulted
    assert ntp_offs == [5]  # untouched


def test_get_ntp_config_multiple_invalid_fields_each_fall_back_independently() -> None:
    # NTP_Host wrong type, NTP_Offset_S out of range (both invalid at once) - each defaults on its own.
    json_text = '{"NTP_Host": 12345, "NTP_Offset_S": 999999, "NTP_Interv_H": 6, "GMTOffset": 7200, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]
    assert ntp_offs == [0]


def test_get_ntp_config_all_fields_invalid_falls_back_to_every_default() -> None:
    json_text = '{"NTP_Host": null, "NTP_Offset_S": "bad", "NTP_Interv_H": -5, "GMTOffset": "x", "DSTOffset": null}'
    client = make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]
    assert ntp_offs == [0]


def test_get_ntp_config_missing_file_uses_every_default() -> None:
    client = make_client()  # fresh directory - no config_NTP.cfg written, so every default applies
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]
    assert ntp_offs == [0]


def test_get_ntp_config_non_dict_json_uses_every_default() -> None:
    client = make_client_with_json("[1, 2, 3]")
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]
    assert ntp_offs == [0]


def test_get_ntp_config_malformed_json_syntax_uses_every_default() -> None:
    client = make_client_with_json("{not json at all")
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]
    assert ntp_offs == [0]


def test_get_ntp_config_returns_none_when_config_manager_itself_is_invalid() -> None:
    client = make_invalid_cfg_client()
    assert client.cfgmgr.valid is False
    assert run(client._get_ntp_config()) is None


# ---------------------------------------------------------------------------
# _safe_get_dns_server - reads the get_dns_server callback (AsyConnTime.get_dns_server_ip) and
# wraps its errors; called by asy_ntp_time() *before* acquiring wifi_mode_lock (see that method's
# own comment and BACKLOG.md for the real bug this split fixes: calling the callback from inside the
# locked section always saw the shared Lock as held and always got None back, regardless of the
# real WLAN state).
# ---------------------------------------------------------------------------


def test_safe_get_dns_server_returns_the_callbacks_value() -> None:
    client = make_client(get_dns_server=lambda: "192.0.2.53")
    assert run(client._safe_get_dns_server()) == "192.0.2.53"


def test_safe_get_dns_server_passes_through_none() -> None:
    client = make_client(get_dns_server=lambda: None)
    assert run(client._safe_get_dns_server()) is None


def test_safe_get_dns_server_callback_raising_returns_none() -> None:
    def raiser() -> "str | None":
        raise RuntimeError("get_wlan_ifconfig() exploded")

    client = make_client(get_dns_server=raiser)
    assert run(client._safe_get_dns_server()) is None


def test_safe_get_dns_server_callback_raising_persists_a_warning() -> None:
    def raiser() -> "str | None":
        raise RuntimeError("get_wlan_ifconfig() exploded")

    client = make_client(get_dns_server=raiser)
    run(client.pr.setup())
    run(client._safe_get_dns_server())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == 3
    assert _last_err(counter, "ErrType") == "W"


# ---------------------------------------------------------------------------
# _resolve_ntp_server - now delegates to asy_dns_client.py's resolve_ipv4() (see that file's own
# module docstring and BACKLOG.md); this file's own long_block_lock is gone entirely since
# resolve_ipv4() never blocks the event loop the way socket.getaddrinfo() used to. Takes dns_server
# as a plain parameter (not a callback it invokes itself) since _safe_get_dns_server() above must be
# called before wifi_mode_lock is acquired, one level up in asy_ntp_time() - see that method's own
# comment.
# ---------------------------------------------------------------------------


def test_resolve_ntp_server_literal_ip_returns_immediately() -> None:
    # asy_dns_client.py's own resolve_ipv4() short-circuits a literal IPv4 address without any
    # network I/O at all - proven at that layer already (tests/test_asy_dns_client.py); this just
    # confirms the (ip, 123) tuple shape _resolve_ntp_server() wraps its result in.
    client = make_client()
    result = run(client._resolve_ntp_server("127.0.0.1", None))
    assert result == ("127.0.0.1", 123)


class _RecordingResolver:
    # Stands in for asy_dns_client.resolve_ipv4() itself - proves _resolve_ntp_server()'s own
    # orchestration (tuple building, error handling, timeout_ms/tries forwarding) independent of
    # resolve_ipv4()'s own real network behavior, which tests/test_asy_dns_client.py already
    # covers exhaustively.
    def __init__(self, return_value: "str | None") -> None:
        self.calls: list[tuple[str, tuple[str, ...], int, int]] = []
        self.return_value = return_value

    async def __call__(self, host: str, dns_servers: "tuple[str, ...]" = (), timeout_ms: int = 0, tries: int = 0) -> "str | None":
        self.calls.append((host, dns_servers, timeout_ms, tries))
        return self.return_value


def test_resolve_ntp_server_passes_the_given_dns_server_through() -> None:
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]  # deliberate monkeypatch
    try:
        client = make_client()
        result = run(client._resolve_ntp_server("pool.ntp.org", "192.0.2.53"))
    finally:
        ntpmod.resolve_ipv4 = original
    assert result == ("9.9.9.9", 123)
    assert recorder.calls == [("pool.ntp.org", ("192.0.2.53",), 500, 1)]


def test_resolve_ntp_server_none_dns_server_passes_an_empty_servers_tuple() -> None:
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]
    try:
        client = make_client()
        run(client._resolve_ntp_server("pool.ntp.org", None))
    finally:
        ntpmod.resolve_ipv4 = original
    assert recorder.calls == [("pool.ntp.org", (), 500, 1)]


def test_resolve_ntp_server_forwards_the_constructors_own_dns_timeout_and_tries() -> None:
    # Proves dns_timeout_ms/dns_tries are this instance's own configured values (see
    # asy_ntp_client.py's own constructor comment) reaching resolve_ipv4() unchanged - not
    # asy_dns_client.py's own standalone defaults, and not hardcoded here either.
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]
    try:
        client = make_client(dns_timeout_ms=1234, dns_tries=3)
        run(client._resolve_ntp_server("pool.ntp.org", None))
    finally:
        ntpmod.resolve_ipv4 = original
    assert recorder.calls == [("pool.ntp.org", (), 1234, 3)]


def test_resolve_ntp_server_dns_failure_returns_none() -> None:
    recorder = _RecordingResolver(None)
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]
    try:
        client = make_client()
        result = run(client._resolve_ntp_server("bogus.invalid", None))
    finally:
        ntpmod.resolve_ipv4 = original
    assert result is None


def test_resolve_ntp_server_dns_failure_persists_an_error() -> None:
    recorder = _RecordingResolver(None)
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]
    try:
        client = make_client()
        run(client.pr.setup())
        run(client._resolve_ntp_server("bogus.invalid", None))
    finally:
        ntpmod.resolve_ipv4 = original
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == 12
    assert _last_err(counter, "ErrType") == "E"


# No real-network end-to-end test through _resolve_ntp_server() itself: resolve_ipv4()'s `port`
# parameter has no override here (real hardware always queries port 53, and _resolve_ntp_server()
# doesn't expose a test-only knob for it) - binding a fake DNS peer to port 53 would need root and
# would be genuinely environment-dependent (unlike every other loopback test in this suite, which
# uses an arbitrary unprivileged port). The seam between the two files is already fully
# characterized above (_RecordingResolver proves the exact arguments/return-value handling), and
# resolve_ipv4()'s own real UDP behavior is exhaustively covered by tests/test_asy_dns_client.py -
# together these prove the same thing a port-53 integration test would, without that fragility.


# ---------------------------------------------------------------------------
# _fetch_ntp_reply
# ---------------------------------------------------------------------------


def test_fetch_ntp_reply_invalid_addr_returns_none() -> None:
    client = make_client()
    result = run(client._fetch_ntp_reply((12345, 80)))  # type: ignore[arg-type]  # host not a str
    assert result is None


class _RecordingUDPSocket:
    # Stands in for asy_udp_socket.AsyUDPSocket - records the timeout_ms _fetch_ntp_reply() passes
    # to write_and_recvfrom(), proving ntp_fetch_timeout_ms is this instance's own configured value
    # (see asy_ntp_client.py's own constructor comment) reaching the real call, not a hardcoded
    # module constant.
    calls: "list[int]" = []

    def __init__(self, addr: "Any", mode: str = "client", conn_tries: int = 1) -> None:
        pass

    async def write_and_recvfrom(
        self, msg: "bytes | bytearray", buf: int, timeout_ms: int = -1, tries: int = 1
    ) -> "tuple[bytes | None, tuple[str, int] | None]":
        _RecordingUDPSocket.calls.append(timeout_ms)
        return None, None

    async def disconnect(self) -> None:
        pass


def test_fetch_ntp_reply_forwards_the_constructors_own_fetch_timeout() -> None:
    client = make_client(ntp_fetch_timeout_ms=9999)
    original = ntpmod.AsyUDPSocket
    _RecordingUDPSocket.calls = []
    ntpmod.AsyUDPSocket = _RecordingUDPSocket  # type: ignore[assignment, misc]
    try:
        run(client._fetch_ntp_reply(("127.0.0.1", 123)))
    finally:
        ntpmod.AsyUDPSocket = original  # type: ignore[misc]
    assert _RecordingUDPSocket.calls == [9999]


def test_fetch_ntp_reply_ipv6_shaped_four_tuple_addr_returns_none() -> None:
    # getaddrinfo() is called with no address-family hint, so a resolver that prefers/returns IPv6
    # would hand back a 4-tuple (host, port, flowinfo, scopeid), not the (host, port) 2-tuple this
    # file assumes throughout. AsyUDPSocket.__init__ already rejects any non-2-tuple with TypeError
    # (see its own module docstring), which _fetch_ntp_reply already catches - proving the whole
    # pipeline degrades to "no reply" instead of crashing on an unexpected address family, even
    # though this file never restricts getaddrinfo() to AF_INET (see BACKLOG.md's third-pass note).
    client = make_client()
    result = run(client._fetch_ntp_reply(("2001:db8::1", 123, 0, 0)))  # type: ignore[arg-type]
    assert result is None


def test_fetch_ntp_reply_no_server_listening_times_out_to_none() -> None:
    client = make_client()
    addr = make_addr()
    result = run(client._fetch_ntp_reply(addr))
    assert result is None


def test_fetch_ntp_reply_real_round_trip_returns_the_exact_reply_bytes() -> None:
    client = make_client()
    addr = make_addr()
    reply = b"\x1c" + bytearray(47)

    async def responder() -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(addr)
        server.setblocking(False)
        poller = select.poll()
        poller.register(server, select.POLLIN)
        for _ in range(500):
            # ipoll(0) returns an always-truthy iterator on this port (confirmed directly) - must
            # iterate and check the actual event flags, exactly like asy_udp_socket.py's own
            # ready() does, not just truth-test the returned object itself.
            ready = any(event & select.POLLIN for _fd, event in poller.ipoll(0))
            if ready:
                try:
                    _data, from_addr = server.recvfrom(1024)
                except OSError:  # spurious wakeup/transient EAGAIN - keep polling instead of raising
                    await asyncio.sleep_ms(10)
                    continue
                server.sendto(reply, from_addr)
                break
            await asyncio.sleep_ms(10)
        server.close()

    async def scenario() -> "bytes | None":
        responder_task = asyncio.create_task(responder())
        await asyncio.sleep(0)  # let the responder bind()+register() before the client sends -
        # AsyUDPSocket's own _connect()/ready() can complete synchronously for a fresh, uncontended
        # client socket (UDP connect()/POLLOUT are both immediately satisfiable), so without this
        # yield the request could race ahead of the responder's own bind() (confirmed directly).
        msg = await client._fetch_ntp_reply(addr)
        await responder_task
        return msg

    assert run(scenario()) == reply


# ---------------------------------------------------------------------------
# _parse_ntp_reply - NTP packet format verified against RFC 5905 during an earlier session: 48-byte
# header, Transmit Timestamp at byte offset 40 (8 bytes: 4-byte integer seconds + 4-byte fraction,
# only the integer half is read here), 2208988800s is the documented 1900->1970 epoch delta - see
# BACKLOG.md. Also checks byte 0's Leap Indicator and byte 1's Stratum before trusting the
# timestamp at all (rejects LI=3 "unsynchronized" and Stratum=0 "invalid"/Kiss-o'-Death) - every
# helper below sets Stratum=1 by default so the era/plausibility-window tests aren't incidentally
# rejected by this separate check. _parse_ntp_reply() is now async (it persists errors/warnings via
# self.pr.err_s()/wrn_s(), which require awaiting) - every call below is wrapped in run().
# ---------------------------------------------------------------------------

_NTP_EPOCH_DELTA = 2208988800


def make_ntp_reply(unix_seconds: int) -> bytes:
    ntp_seconds = (unix_seconds + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    # LI=0/VN=3/Mode=4(server) + Stratum=1(primary reference, i.e. genuinely synchronized - stratum
    # 0 would now be rejected as a Kiss-o'-Death packet, see asy_ntp_client.py's own
    # _NTP_STRATUM_INVALID) + zeroed Poll..Receive Timestamp - content-agnostic beyond that.
    header = b"\x1c\x01" + bytes(38)
    transmit = struct.pack("!I", ntp_seconds) + bytes(4)  # seconds + zeroed fraction
    packet = header + transmit
    assert len(packet) == 48
    return packet


def test_parse_ntp_reply_valid_packet_returns_gmtime_and_sets_the_rtc() -> None:
    client = make_client()
    now = int(time.time())
    msg = make_ntp_reply(now)
    tm = run(client._parse_ntp_reply(msg, 0))
    assert tm is not None
    assert tm[0] >= 2024  # sanity bound: a real current-ish year, not the 2000 fake-RTC default
    rtc_datetime = RTC().datetime()
    assert rtc_datetime is not None  # only None-shaped when called as a setter with dt=None
    assert tuple(rtc_datetime) == (tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0)


def test_parse_ntp_reply_applies_the_ntp_offset_s_correction() -> None:
    client = make_client()
    now = int(time.time())
    msg = make_ntp_reply(now)
    tm_no_offset = run(client._parse_ntp_reply(msg, 0))
    tm_with_offset = run(client._parse_ntp_reply(msg, 3600))
    assert tm_no_offset is not None and tm_with_offset is not None
    assert time.mktime(tm_with_offset) - time.mktime(tm_no_offset) == 3600


def _truncated(length: int) -> bytes:
    # A non-zero Stratum (index 1) whenever the length reaches it, so these truncation-length tests
    # are rejected (if at all) for being too short to reach the Transmit Timestamp, not incidentally
    # for looking like a Kiss-o'-Death reply (stratum 0) - keeps this isolated from the separate
    # LI/Stratum check.
    buf = bytearray(length)
    if length > 1:
        buf[1] = 1
    return bytes(buf)


def test_parse_ntp_reply_truncated_packet_returns_none() -> None:
    client = make_client()
    for length in (0, 10, 39, 43):  # all short of the 44 bytes struct.unpack("!I", msg[40:44]) needs
        assert run(client._parse_ntp_reply(_truncated(length), 0)) is None


def test_parse_ntp_reply_zero_length_and_exact_boundary_lengths() -> None:
    client = make_client()
    assert run(client._parse_ntp_reply(b"", 0)) is None
    assert run(client._parse_ntp_reply(_truncated(44), 0)) is not None  # exactly enough bytes - accepted


def test_parse_ntp_reply_arbitrary_binary_content_never_raises() -> None:
    client = make_client()
    garbage = bytes(range(48))  # a full 48 bytes, but not a real NTP reply at all
    run(client._parse_ntp_reply(garbage, 0))  # must not raise - result (None or a valid tm) not asserted


class _OverflowingTime:
    def gmtime(self, *_a: "Any") -> "Any":
        raise OverflowError("past rp2's ~2037 32-bit epoch range")

    def time(self) -> int:
        return int(time.time())


def test_parse_ntp_reply_gmtime_overflow_returns_none_not_raise() -> None:
    client = make_client()
    msg = make_ntp_reply(int(time.time()))
    original_time = ntpmod.time
    ntpmod.time = _OverflowingTime()  # type: ignore[assignment]  # deliberate monkeypatch
    try:
        result = run(client._parse_ntp_reply(msg, 0))
    finally:
        ntpmod.time = original_time
    assert result is None


def test_parse_ntp_reply_rtc_set_failure_returns_none_not_raise() -> None:
    client = make_client()
    msg = make_ntp_reply(int(time.time()))
    RTC.raise_exc = ValueError("simulated RTC set failure")
    try:
        result = run(client._parse_ntp_reply(msg, 0))
    finally:
        RTC.raise_exc = None
    assert result is None


def _make_raw_ntp_reply(raw_seconds: int) -> bytes:
    # Same LI=0/Stratum=1 header as make_ntp_reply() above - a genuinely-synchronized-looking
    # server, so these era/plausibility-window tests aren't incidentally rejected by the separate
    # LI/Stratum check instead of exercising the era logic they're meant to test.
    header = b"\x1c\x01" + bytes(38)
    transmit = struct.pack("!I", raw_seconds & 0xFFFFFFFF) + bytes(4)
    msg = header + transmit
    assert len(msg) == 48
    return msg


def test_parse_ntp_reply_era_rollover_wrapped_reply_reconstructs_the_real_future_date() -> None:
    # NTP's 32-bit "seconds since 1900" field wraps in 2036 (era rollover) - distinct from the
    # ~2037 Unix time_t OverflowError already covered above. A real post-2036 server sends a small
    # raw value (wrapped back near 0, not the huge continuously-counting value it "really" means).
    # _parse_ntp_reply() now reinterprets a below-floor reading as the next NTP era (RFC 5905 7.3)
    # and rechecks against the same plausibility window - this proves the round trip actually lands
    # back on the real intended date, not just "doesn't crash" (see BACKLOG.md).
    client = make_client()
    target_unix = 2185978496  # 2039-04-09ish - past the ~2036 wrap, well within the plausible ceiling
    raw = (target_unix + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(target_unix))


def test_parse_ntp_reply_rejects_a_timestamp_implausible_in_every_era() -> None:
    # A raw value that looks implausible both read directly (era 0: ~1995, below the floor) and
    # after the one-shot era reinterpretation (era 1: ~2131, past the ceiling) - genuinely
    # rejectable corrupt/garbage data, not just an ordinary era-rollover reply. Fixes the real bug
    # found while writing this test's predecessor: previously this silently produced a bogus-but-
    # accepted "successful sync" (see BACKLOG.md's third-pass entry) instead of failing closed.
    client = make_client()
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(3000000000), 0))
    assert result is None


def test_parse_ntp_reply_accepts_exactly_at_the_floor_boundary() -> None:
    client = make_client()
    floor = 1735689600  # 2025-01-01T00:00:00Z - _NTP_MIN_PLAUSIBLE_UNIX_TIME, compiled away, hardcoded
    raw = (floor + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(floor))


def test_parse_ntp_reply_accepts_exactly_at_the_ceiling_boundary() -> None:
    client = make_client()
    ceiling = 4102444800  # 2100-01-01T00:00:00Z - _NTP_MAX_PLAUSIBLE_UNIX_TIME, compiled away, hardcoded
    raw = (ceiling + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(ceiling))


def test_parse_ntp_reply_rejects_just_past_the_ceiling_boundary() -> None:
    client = make_client()
    ceiling = 4102444800
    raw = (ceiling + 1 + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is None


def _reply_with_li_and_stratum(leap_indicator: int, stratum: int, unix_seconds: int) -> bytes:
    ntp_seconds = (unix_seconds + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    first_byte = (leap_indicator << 6) | 0b011100  # VN=3, Mode=4(server) in the low 6 bits
    header = bytes([first_byte, stratum]) + bytes(38)
    transmit = struct.pack("!I", ntp_seconds) + bytes(4)
    msg = header + transmit
    assert len(msg) == 48
    return msg


def test_parse_ntp_reply_rejects_leap_indicator_unsynchronized() -> None:
    # RFC 5905's Leap Indicator = 3 ("unknown (clock unsynchronized)") is an alarm condition - the
    # server is explicitly saying it isn't a trustworthy time source yet, even though its Transmit
    # Timestamp here is a perfectly plausible current date that would otherwise pass every other
    # check (see BACKLOG.md).
    client = make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=3, stratum=1, unix_seconds=int(time.time()))
    assert run(client._parse_ntp_reply(msg, 0)) is None


def test_parse_ntp_reply_rejects_stratum_zero_kiss_of_death() -> None:
    # RFC 5905/4330: Stratum 0 = "unspecified or invalid", used for Kiss-o'-Death (KoD) packets -
    # never a genuine time source, regardless of its Transmit Timestamp's contents (see
    # BACKLOG.md's worked example: a real KoD reply's all-zero Transmit Timestamp would otherwise
    # land exactly inside the plausibility window after era-reinterpretation).
    client = make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=0, unix_seconds=int(time.time()))
    assert run(client._parse_ntp_reply(msg, 0)) is None


def test_parse_ntp_reply_accepts_a_normal_synchronized_reply_li_zero_stratum_one() -> None:
    # Companion to the two rejection tests above - proves the new LI/Stratum check doesn't reject
    # everything, only the two specific alarm/KoD conditions.
    client = make_client()
    now = int(time.time())
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=1, unix_seconds=now)
    result = run(client._parse_ntp_reply(msg, 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(now))


# ---------------------------------------------------------------------------
# _handle_ntp_sync_failure / _handle_ntp_sync_success - retry counting + timer arm/degrade
# ---------------------------------------------------------------------------


def test_handle_sync_failure_while_never_synced_does_not_arm_a_retry() -> None:
    client = make_client()  # never synced yet
    run(client._handle_ntp_sync_failure())
    assert client.ntp_retry_timer.period == -1  # never armed - ntp_time_hours_counter() retries instead


def test_handle_sync_failure_while_synced_arms_a_retry_and_increments_the_counter() -> None:
    client = make_client()
    run(client._set_synced(True))
    run(client._handle_ntp_sync_failure())
    assert client.ntp_retries == 1
    assert client.ntp_retry_timer.mode == Timer.ONE_SHOT
    assert client.ntp_retry_timer.period == 15 * 1000  # _NTP_RETRY_INTERV: const(), compiled away


def test_handle_sync_failure_retry_timer_fires_the_sync_trigger() -> None:
    client = make_client()
    run(client._set_synced(True))
    run(client._handle_ntp_sync_failure())

    async def scenario() -> bool:
        client.ntp_retry_timer.trigger()
        try:
            await asyncio.wait_for(client.ntp_sync_trigger_event.wait(), 0.2)
            return True
        except asyncio.TimeoutError:
            return False

    assert run(scenario())


def test_handle_sync_failure_gives_up_after_max_retries() -> None:
    client = make_client()
    run(client._set_synced(True))
    client.ntp_retries = 3  # _NTP_SYNC_RETRIES: const(), compiled away
    run(client._handle_ntp_sync_failure())
    assert client.ntp_retries == 0
    assert client.ntp_retry_timer.period == -1  # never (re)armed - past the retry budget


def test_handle_sync_failure_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    run(client._set_synced(True))
    with _RaiseOnArm():
        run(client._handle_ntp_sync_failure())  # must not raise despite the timer failing to arm
    assert client.ntp_retries == 0  # given up this cycle rather than left stuck


def test_handle_sync_failure_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of _handle_ntp_sync_failure()'s own
    # `except (OSError, MemoryError)` - the retry cycle is given up the same way either way, and the
    # same errno=16 is persisted (this site logs via the async err_s(), unlike the two starters above).
    client = make_client()
    run(client.pr.setup())
    run(client._set_synced(True))
    with _RaiseOnArm(MemoryError):
        run(client._handle_ntp_sync_failure())  # must not raise despite the timer failing to arm
    assert client.ntp_retries == 0  # given up this cycle rather than left stuck
    assert _last_err(run(client.get_error_counter()), "ErrNum") == 16


def test_handle_sync_success_resets_retries_marks_synced_and_records_the_sync_time() -> None:
    client = make_client()
    client.ntp_retries = 2
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert client.ntp_retries == 0
    assert run(client.ntp_issynced()) is True
    assert run(client.get_last_ntp_sync()) == 0


def test_handle_sync_success_deinits_a_pending_retry_timer() -> None:
    client = make_client()
    client.ntp_retry_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda b: None)
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert client.ntp_retry_timer.deinit_called is True


# ---------------------------------------------------------------------------
# ntp_time_hours_counter
# ---------------------------------------------------------------------------


async def _tick(flag: "asyncio.ThreadSafeFlag", times: int = 1) -> None:
    for _ in range(times):
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # let one full loop iteration's awaits settle


def test_ntp_time_hours_counter_missing_config_falls_back_to_12h_default_without_raising() -> None:
    client = make_invalid_cfg_client()

    async def scenario() -> None:
        task = asyncio.create_task(client.ntp_time_hours_counter())
        await _tick(client.ntp_timer_trigger_event, 1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run(scenario())  # must not raise despite the missing config


def test_ntp_time_hours_counter_triggers_sync_immediately_when_not_yet_synced() -> None:
    client = make_client()

    async def scenario() -> bool:
        task = asyncio.create_task(client.ntp_time_hours_counter())
        await _tick(client.ntp_timer_trigger_event, 1)
        try:
            await asyncio.wait_for(client.ntp_sync_trigger_event.wait(), 0.2)
            fired = True
        except asyncio.TimeoutError:
            fired = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return fired

    assert run(scenario())


def test_ntp_time_hours_counter_does_not_retrigger_while_synced_and_under_interval() -> None:
    json_text = '{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(True)
        task = asyncio.create_task(client.ntp_time_hours_counter())
        await _tick(client.ntp_timer_trigger_event, 1)  # one tick, well under 1h / 10s-per-tick
        try:
            await asyncio.wait_for(client.ntp_sync_trigger_event.wait(), 0.2)
            fired = True
        except asyncio.TimeoutError:
            fired = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return fired

    assert run(scenario()) is False


def test_ntp_time_hours_counter_retriggers_once_interval_elapses() -> None:
    # NTP_Interv_H=1 -> 3600s / _NTP_CHECK_INTERV(10s) = 360 ticks to reach the interval.
    json_text = '{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(True)
        task = asyncio.create_task(client.ntp_time_hours_counter())
        await _tick(client.ntp_timer_trigger_event, 360)
        try:
            await asyncio.wait_for(client.ntp_sync_trigger_event.wait(), 0.2)
            fired = True
        except asyncio.TimeoutError:
            fired = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return fired

    assert run(scenario())


def test_ntp_time_hours_counter_marks_out_of_sync_past_the_async_interval_multiple() -> None:
    # _NTP_ASYNC_INTERV(3) x interval(1h) = 10800s without a successful resync flips ntp_synced
    # back to False even though the retrigger condition normally resets sec_count to 0 first -
    # set ntp_sec_count directly at that boundary to isolate this specific transition.
    json_text = '{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(True)
        task = asyncio.create_task(client.ntp_time_hours_counter())
        await asyncio.sleep(0)  # let the task run past its own `self.ntp_sec_count = 0` reset first
        client.ntp_sec_count = 3 * 1 * 60 * 60  # _NTP_ASYNC_INTERV(3) * 1h * 3600 - const(), compiled away
        await _tick(client.ntp_timer_trigger_event, 1)
        synced = await client.ntp_issynced()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return synced

    assert run(scenario()) is False


def test_ntp_time_hours_counter_never_naturally_reaches_the_async_interval_multiple_under_constant_config() -> None:
    # Complements test_ntp_time_hours_counter_marks_out_of_sync_past_the_async_interval_multiple
    # above (which isolates the 3x transition by directly poking ntp_sec_count). Under natural
    # ticking with a constant NTP_Interv_H, the loop's own reset-to-0-once-sec_count-hits-1x-
    # interval logic fires every single cycle before sec_count can ever approach the 3x threshold -
    # so the "distrust a stale sync after 3x the interval" safety net never actually engages here,
    # even across several full cycles of continuous (simulated) sync silence. See BACKLOG.md's
    # third-pass findings: inherited from python/CommonDrivers/async_connect.py byte-for-byte,
    # flagged rather than changed.
    json_text = '{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(True)
        task = asyncio.create_task(client.ntp_time_hours_counter())
        # 3 full 1h/360-tick cycles - well past where the 3x(=3h) threshold would sit if sec_count
        # were ever allowed to accumulate past a single 1x cycle.
        await _tick(client.ntp_timer_trigger_event, 3 * 360)
        still_synced = await client.ntp_issynced()
        sec_count_bounded = client.ntp_sec_count < (1 * 60 * 60)  # always reset well under 1x
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return still_synced and sec_count_bounded

    assert run(scenario())


# ---------------------------------------------------------------------------
# cettime() - CET/CEST DST boundary math; verified through the real time.mktime()/time.gmtime()
# rather than hand-computing the "last Sunday of March/October" formula independently (already
# confirmed copied verbatim from deployed production code - see BACKLOG.md) - this only needs to
# prove branch selection + exception-safety, not re-derive the formula itself.
#
# Real finding, flagged (not silently fixed) in an earlier session's report: this project's pinned
# MicroPython Unix-port test interpreter's time.gmtime() returns a 9-element tuple (trailing
# isdst=0), not the 8-element shape MicroPython's own docs document for embedded ports including
# rp2, the real deployment target (confirmed directly below) - matches the cross-port ambiguity
# typings/_mpy_shed/time_mp.pyi's _TimeTuple union already anticipates. cettime()'s own
# `if len(cet) == 8` check is correct for the real rp2 target, but would return None under this
# interpreter if not accounted for - so every test below normalizes gmtime()'s result to 8
# elements via a monkeypatched `time` shim, to test the real rp2-target contract despite running
# on a host whose own gmtime() shape differs.
# ---------------------------------------------------------------------------


def test_this_interpreters_gmtime_returns_nine_elements_not_eight() -> None:
    assert len(time.gmtime()) == 9


class _FixedNowTime:
    # Same monkeypatch technique as test_system_service.py's _OverflowingTime/_RaisingGmtime -
    # replaces AsyNtpClient's own module-level `time` name (a plain, mutable module global),
    # not the real (read-only builtin) module. gmtime()/mktime() delegate to the real module so
    # the DST-boundary formula is genuinely exercised; only time() is overridden (deterministic
    # branch selection instead of depending on the real calendar date) and gmtime()'s result is
    # truncated to 8 elements (see module comment above - the real rp2 target's actual shape).
    def __init__(self, fixed_now: int, raise_exc: "Exception | None" = None) -> None:
        self._fixed_now = fixed_now
        self._raise_exc = raise_exc

    def gmtime(self, *a: "Any") -> "Any":
        if self._raise_exc is not None:
            raise self._raise_exc
        return tuple(time.gmtime(*a))[:8]

    def mktime(self, t: "Any") -> int:
        if self._raise_exc is not None:
            raise self._raise_exc
        return time.mktime(t)

    def time(self) -> int:
        return self._fixed_now


def _mid_month_now(month: int) -> int:
    year = time.gmtime()[0]
    return time.mktime((year, month, 15, 12, 0, 0, 0, 0, 0))


def _client_with_offsets(gmt_offset: int, dst_offset: int) -> AsyNtpClient:
    # Deliberately one single f-string, not a plain-string-literal-adjacent-to-an-f-string
    # concatenation: confirmed directly that MicroPython mishandles the latter when the plain
    # part contains a literal brace (this JSON's opening "{") - it raises a spurious
    # KeyError on the plain part's own content instead of producing the intended string.
    json_text = (
        f'{{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 12, '
        f'"GMTOffset": {gmt_offset}, "DSTOffset": {dst_offset}}}'
    )
    return make_client_with_json(json_text)


def test_cettime_returns_none_when_not_synced() -> None:
    client = make_client()
    assert run(client.cettime()) is None


def test_cettime_returns_none_when_config_missing() -> None:
    client = make_invalid_cfg_client()
    run(client._set_synced(True))
    assert run(client.cettime()) is None


def _run_cettime_with_fixed_now(client: AsyNtpClient, fixed_now: int, raise_exc: "Exception | None" = None) -> "Any":
    original_time = ntpmod.time
    ntpmod.time = _FixedNowTime(fixed_now, raise_exc)  # type: ignore[assignment]
    try:
        return run(client.cettime())
    finally:
        ntpmod.time = original_time


def test_cettime_before_march_boundary_applies_gmt_offset_only() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(True))
    fixed_now = _mid_month_now(1)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600))[:8]


def test_cettime_between_march_and_october_applies_gmt_plus_dst_offset() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(True))
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600 + 3600))[:8]


def test_cettime_after_october_boundary_applies_gmt_offset_only() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(True))
    fixed_now = _mid_month_now(12)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600))[:8]


def test_cettime_zero_offsets_are_accepted_not_rejected() -> None:
    client = _client_with_offsets(0, 0)
    run(client._set_synced(True))
    fixed_now = _mid_month_now(1)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now))[:8]


def test_cettime_negative_offsets_are_accepted_not_rejected() -> None:
    client = _client_with_offsets(-3600, -3600)
    run(client._set_synced(True))
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now - 3600 - 3600))[:8]


def test_cettime_mktime_or_gmtime_failure_returns_none_not_raise() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(True))
    result = _run_cettime_with_fixed_now(
        client, _mid_month_now(1), raise_exc=OverflowError("past rp2's ~2037 range")
    )
    assert result is None


class _ShortGmtimeTime:
    # Real rp2 time.gmtime() always returns exactly 8 elements - cettime()'s own `len(cet) == 8`
    # check can't actually fail through any real gmtime() call, so this fakes a malformed result
    # directly, the same technique _FixedNowTime above uses for its own fixed-now/raising variants.
    def __init__(self, fixed_now: int) -> None:
        self._fixed_now = fixed_now

    def gmtime(self, *a: "Any") -> "Any":
        return tuple(time.gmtime(*a))[:7]  # one short of the real 8-element shape

    def mktime(self, t: "Any") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return self._fixed_now


def test_cettime_returns_none_when_gmtime_result_has_the_wrong_length() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(True))
    original_time = ntpmod.time
    ntpmod.time = _ShortGmtimeTime(_mid_month_now(1))  # type: ignore[assignment]
    try:
        result = run(client.cettime())
    finally:
        ntpmod.time = original_time
    assert result is None


# ---------------------------------------------------------------------------
# time_counter()
# ---------------------------------------------------------------------------


def test_time_counter_increments_while_synced() -> None:
    client = make_client()

    async def scenario() -> "int | None":
        await client._set_synced(True)
        task = asyncio.create_task(client.time_counter())
        await _tick(client.time_counter_trigger_event, 3)
        value = await client.get_last_ntp_sync()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return value

    assert run(scenario()) == 3


def test_time_counter_resets_to_none_while_not_synced() -> None:
    client = make_client()

    async def scenario() -> "int | None":
        task = asyncio.create_task(client.time_counter())
        await _tick(client.time_counter_trigger_event, 2)
        value = await client.get_last_ntp_sync()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return value

    assert run(scenario()) is None


# ---------------------------------------------------------------------------
# _run_ntp_sync_attempt - every branch, isolated from the real network stack by monkeypatching the
# next layer down (real end-to-end network behavior is covered separately further below).
# ---------------------------------------------------------------------------


def test_run_sync_attempt_network_unavailable_skips_everything_downstream() -> None:
    client = make_client(network_available=lambda: False)
    reached = [False]

    async def fake_get_cfg() -> "Any":
        reached[0] = True
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert reached[0] is False


def test_run_sync_attempt_network_available_raising_is_treated_as_unavailable() -> None:
    def raiser() -> bool:
        raise RuntimeError("wlan.status() exploded")

    client = make_client(network_available=raiser)
    reached = [False]

    async def fake_get_cfg() -> "Any":
        reached[0] = True
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))  # must not raise
    assert reached[0] is False


def test_run_sync_attempt_network_available_raising_persists_a_warning() -> None:
    def raiser() -> bool:
        raise RuntimeError("wlan.status() exploded")

    client = make_client(network_available=raiser)
    run(client.pr.setup())
    run(client._run_ntp_sync_attempt(None))
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == 1
    assert _last_err(counter, "ErrType") == "W"


def test_run_sync_attempt_missing_config_marks_not_synced_and_returns() -> None:
    client = make_client()
    run(client._set_synced(True))

    async def fake_get_cfg() -> "Any":
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert run(client.ntp_issynced()) is False


def test_run_sync_attempt_resolve_failure_calls_handle_failure() -> None:
    client = make_client()
    handled = [False]

    async def fake_get_cfg() -> "Any":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "Any") -> "Any":
        return None

    async def fake_handle_failure() -> None:
        handled[0] = True

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    client._handle_ntp_sync_failure = fake_handle_failure  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert handled[0] is True


def test_run_sync_attempt_passes_the_given_dns_server_to_resolve_ntp_server() -> None:
    # Proves _run_ntp_sync_attempt() forwards its own dns_server parameter through unchanged -
    # the actual value only ever comes from asy_ntp_time()'s _safe_get_dns_server() call, read
    # before wifi_mode_lock is acquired (see that method's own comment/BACKLOG.md).
    client = make_client()
    received: list[Any] = []

    async def fake_get_cfg() -> "Any":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, dns_server: "Any") -> "Any":
        received.append(dns_server)
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    run(client._run_ntp_sync_attempt("203.0.113.53"))
    assert received == ["203.0.113.53"]


def test_run_sync_attempt_fetch_failure_calls_handle_failure() -> None:
    client = make_client()
    handled = [False]

    async def fake_get_cfg() -> "Any":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "Any") -> "Any":
        return ("1.2.3.4", 123)

    async def fake_fetch(_addr: "Any") -> "Any":
        return None

    async def fake_handle_failure() -> None:
        handled[0] = True

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    client._fetch_ntp_reply = fake_fetch  # type: ignore[assignment, method-assign]
    client._handle_ntp_sync_failure = fake_handle_failure  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert handled[0] is True


def test_run_sync_attempt_parse_failure_calls_handle_failure() -> None:
    client = make_client()
    handled = [False]

    async def fake_get_cfg() -> "Any":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "Any") -> "Any":
        return ("1.2.3.4", 123)

    async def fake_fetch(_addr: "Any") -> "Any":
        return b"garbage"

    async def fake_parse(_msg: "Any", _off: "Any") -> "Any":
        return None

    async def fake_handle_failure() -> None:
        handled[0] = True

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    client._fetch_ntp_reply = fake_fetch  # type: ignore[assignment, method-assign]
    client._parse_ntp_reply = fake_parse  # type: ignore[assignment, method-assign]
    client._handle_ntp_sync_failure = fake_handle_failure  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert handled[0] is True


def test_run_sync_attempt_success_calls_handle_success_with_the_parsed_time() -> None:
    client = make_client()
    handled_with: list[Any] = []
    parsed_tm = (2026, 1, 1, 0, 0, 0, 0, 0)

    async def fake_get_cfg() -> "Any":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "Any") -> "Any":
        return ("1.2.3.4", 123)

    async def fake_fetch(_addr: "Any") -> "Any":
        return b"x" * 48

    async def fake_parse(_msg: "Any", _off: "Any") -> "Any":
        return parsed_tm

    async def fake_handle_success(tm: "Any") -> None:
        handled_with.append(tm)

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    client._fetch_ntp_reply = fake_fetch  # type: ignore[assignment, method-assign]
    client._parse_ntp_reply = fake_parse  # type: ignore[assignment, method-assign]
    client._handle_ntp_sync_success = fake_handle_success  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert handled_with == [parsed_tm]


# ---------------------------------------------------------------------------
# asy_ntp_time() - the task-supervisor entry point: proves the trigger -> lock -> attempt ->
# lock-release cycle actually works, and that the lock is released even if the attempt itself
# raises (shouldn't happen after an earlier session's own exception audit, but the surrounding
# try/finally must not depend on that to stay correct).
# ---------------------------------------------------------------------------


def test_asy_ntp_time_runs_one_attempt_per_trigger_and_releases_the_wifi_lock() -> None:
    client = make_client()
    attempts = [0]

    async def fake_attempt(_dns_server: "Any") -> "Any":
        attempts[0] += 1
        return None, True

    client._run_ntp_sync_attempt = fake_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> int:
        task = asyncio.create_task(client.asy_ntp_time())
        client.ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not client.wifi_mode_lock.locked()
        client.ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return attempts[0]

    assert run(scenario()) == 2


def test_asy_ntp_time_releases_the_wifi_lock_even_if_the_attempt_raises() -> None:
    client = make_client()

    async def raising_attempt(_dns_server: "Any") -> "Any":
        raise RuntimeError("simulated bug downstream")

    client._run_ntp_sync_attempt = raising_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(client.asy_ntp_time())
        client.ntp_sync_trigger_event.set()
        # the uncaught RuntimeError kills this task - matches every other supervised task in this
        # codebase, which relies on the outer task-supervisor to notice and restart it, not a
        # catch-all here; retrieved explicitly so asyncio doesn't warn about it going unretrieved.
        try:
            await asyncio.wait_for(task, 0.2)
            raised = False
        except RuntimeError:
            raised = True
        return raised and not client.wifi_mode_lock.locked()

    assert run(scenario())


def test_asy_ntp_time_swallows_an_already_released_wifi_lock() -> None:
    # Regression-shaped defensive guard: if the lock were somehow already released by the time
    # asy_ntp_time()'s own finally block runs, wifi_mode_lock.release() raises RuntimeError - caught
    # and swallowed rather than crashing the task. Forced here by having the (monkeypatched)
    # attempt itself release the lock as a side effect, simulating that "already released" state.
    client = make_client()

    async def attempt_releases_lock_itself(_dns_server: "Any") -> "Any":
        client.wifi_mode_lock.release()
        return None, True

    client._run_ntp_sync_attempt = attempt_releases_lock_itself  # type: ignore[assignment, method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(client.asy_ntp_time())
        client.ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        still_running = not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return still_running

    assert run(scenario()) is True  # must not have crashed on the redundant release


def test_asy_ntp_time_calls_pr_setup_before_entering_its_loop() -> None:
    client = make_client()
    assert client.pr.initialized is False

    async def scenario() -> bool:
        task = asyncio.create_task(client.asy_ntp_time())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        initialized = client.pr.initialized
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return initialized

    assert run(scenario()) is True


def test_asy_ntp_time_resets_err_cnt_internal_at_the_start_of_every_run() -> None:
    client = make_client()
    client._err_cnt_internal = 99

    async def scenario() -> int:
        task = asyncio.create_task(client.asy_ntp_time())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        streak = client._err_cnt_internal
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return streak

    assert run(scenario()) == 0


def test_asy_ntp_time_gives_up_after_repeated_sync_failures_and_persists_errno_20() -> None:
    # Independent, coarser safety net on top of _handle_ntp_sync_failure()'s own short-term
    # ntp_retries/_NTP_SYNC_RETRIES retry loop - see asy_ntp_time()'s own comment. A real attempt
    # that completes (network was up) but never yields a parsed time counts toward this streak.
    client = make_client(max_i2c_err=2)

    async def failing_attempt(_dns_server: "Any") -> "Any":
        return None, True  # network was available, but the attempt itself still failed

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> "Any":
        task = asyncio.create_task(client.asy_ntp_time())
        for _ in range(3):  # one trigger per would-be failure cycle - max_i2c_err=2 gives up on the 3rd
            client.ntp_sync_trigger_event.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        await asyncio.wait_for(task, 2.0)  # must actually complete, not loop forever
        return await client.get_error_counter()

    counter = run(scenario())
    assert _last_err(counter, "ErrNum") == 20
    assert _last_err(counter, "ErrType") == "E"


def test_asy_ntp_time_network_unavailable_cycles_never_count_toward_giving_up() -> None:
    # condition=network_ok excludes "network wasn't up yet" from the give-up streak, the same way
    # SGP40 excludes a missing-compensation read via condition=compensated - proven here by running
    # well past max_i2c_err trigger cycles, all reporting network unavailable, without giving up.
    client = make_client(max_i2c_err=2)

    async def unavailable_attempt(_dns_server: "Any") -> "Any":
        return None, False  # network not available - condition=False, must not count as a real failure

    client._run_ntp_sync_attempt = unavailable_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(client.asy_ntp_time())
        for _ in range(10):
            client.ntp_sync_trigger_event.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        still_running = not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return still_running

    assert run(scenario()) is True


def test_asy_ntp_time_recovers_the_streak_on_alternating_failure_and_success() -> None:
    # A success resets tm to non-None, decrementing _err_cnt_internal (base_classes.py's own
    # _error_check() contract) - failures that never land two-in-a-row must never trip
    # max_i2c_err=2, however many trigger cycles run in total.
    client = make_client(max_i2c_err=2)
    toggle = [True]

    async def alternating_attempt(_dns_server: "Any") -> "Any":
        if toggle[0]:
            toggle[0] = False
            return None, True  # failure
        toggle[0] = True
        return (2026, 1, 1, 0, 0, 0, 0, 0), True  # success

    client._run_ntp_sync_attempt = alternating_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(client.asy_ntp_time())
        for _ in range(20):
            client.ntp_sync_trigger_event.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        still_running = not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return still_running

    assert run(scenario()) is True


# ===========================================================================
# Integration tests: real (not mocked) network path, driving the whole asy_ntp_time() task
# through cfgmgr -> _resolve_ntp_server -> AsyUDPSocket -> real UDP loopback -> a staged real NTP
# server - proving how a genuine network fault (or success) propagates all the way up through
# ntp_issynced()/get_last_ntp_sync()/cettime(), not just the unit under test in isolation.
# ===========================================================================


class _RedirectNtpNetworking:
    # Combines two Unix-port-only test workarounds needed only when driving the FULL asy_ntp_time()
    # task end-to-end (not when calling _fetch_ntp_reply() etc. directly with an already-resolved
    # addr, which every other test in this file already does - this must NOT be applied there, or
    # indexing into an already-opaque object would itself break, confirmed directly):
    # (1) _resolve_ntp_server() always returns _NTP_UDP_PORT (123, the real NTP port) alongside
    #     whatever IP resolve_ipv4() resolved - binding a test server on the real port 123 needs
    #     root/CAP_NET_BIND_SERVICE, which CI runners don't have (confirmed directly: bind() raises
    #     EACCES there, even though it worked in a root dev sandbox). Redirected here to a real,
    #     already-bound ephemeral port instead (see _NTP_UDP_PORT's own comment on why it's
    #     deliberately not const()-wrapped, unlike every sibling constant in that file).
    # (2) _resolve_ntp_server() now returns a plain (str, int) tuple - the correct, typed shape real
    #     rp2 hardware's socket.connect() accepts directly (see asy_dns_client.py's own resolve_ipv4()
    #     contract) - but this Unix-port "standard" build's connect() rejects that same plain tuple
    #     (test_asy_udp_socket.py's own make_addr() comment, micropython/micropython#6924). Wraps
    #     asy_ntp_client.py's own AsyUDPSocket import to pre-resolve it transparently, exactly like
    #     tests/test_asy_dns_client.py's own _ResolvingAsyUDPSocket wrapper.
    def __init__(self, port: int) -> None:
        self._port = port

    def __enter__(self) -> "_RedirectNtpNetworking":
        self._original_port = ntpmod._NTP_UDP_PORT
        self._original_socket_cls = ntpmod.AsyUDPSocket
        ntpmod._NTP_UDP_PORT = self._port
        real_cls = self._original_socket_cls

        class _Resolving:
            def __init__(self, addr: "Any", mode: str = "client", conn_tries: int = 1) -> None:
                resolved = socket.getaddrinfo(addr[0], addr[1])[0][-1]
                self._real = real_cls(resolved, mode=mode, conn_tries=conn_tries)  # type: ignore[arg-type]

            def __getattr__(self, name: str) -> "Any":
                return getattr(self._real, name)

        ntpmod.AsyUDPSocket = _Resolving  # type: ignore[assignment, misc]
        return self

    def __exit__(self, *exc_info: "Any") -> None:
        ntpmod._NTP_UDP_PORT = self._original_port
        ntpmod.AsyUDPSocket = self._original_socket_cls  # type: ignore[misc]


class FakeNtpServer:
    # A genuine independent UDP endpoint (real socket.socket(), not an AsyUDPSocket) - staged to
    # answer with a controlled reply or drop the request entirely, the same "real peer, not a
    # mock" approach as test_asy_udp_socket.py's AdversarialPeer. Binds to a real, free ephemeral
    # port (see _RedirectNtpNetworking above for why not real port 123).
    def __init__(self) -> None:
        self.port = make_port()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket.getaddrinfo("127.0.0.1", self.port)[0][-1])
        self.sock.setblocking(False)
        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLIN)

    def redirect_resolution(self) -> _RedirectNtpNetworking:
        return _RedirectNtpNetworking(self.port)

    async def serve_once(self, reply: "bytes | None") -> None:
        # Answers exactly one request with `reply` (None = drop it silently, never answer).
        # ipoll(0) returns an always-truthy iterator on this port (confirmed directly) - must
        # iterate and check the actual event flags, exactly like asy_udp_socket.py's own ready().
        for _ in range(1000):
            ready = any(event & select.POLLIN for _fd, event in self.poller.ipoll(0))
            if ready:
                try:
                    _data, from_addr = self.sock.recvfrom(1024)
                except OSError:  # spurious wakeup/transient EAGAIN - keep polling instead of raising
                    await asyncio.sleep_ms(10)
                    continue
                if reply is not None:
                    self.sock.sendto(reply, from_addr)
                return
            await asyncio.sleep_ms(10)

    def close(self) -> None:
        self.sock.close()


def make_integration_client() -> AsyNtpClient:
    json_text = '{"NTP_Host": "127.0.0.1", "NTP_Offset_S": 0, "NTP_Interv_H": 12, "GMTOffset": 0, "DSTOffset": 0}'
    return make_client_with_json(json_text)


def test_integration_full_task_reaches_synced_state_on_a_real_successful_reply() -> None:
    client = make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "tuple[bool, int | None]":
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                task = asyncio.create_task(client.asy_ntp_time())
                server_task = asyncio.create_task(server.serve_once(reply))
                client.ntp_sync_trigger_event.set()
                await asyncio.wait_for(server_task, 5)
                for _ in range(50):
                    if await client.ntp_issynced():
                        break
                    await asyncio.sleep_ms(20)
                synced = await client.ntp_issynced()
                last_sync = await client.get_last_ntp_sync()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return synced, last_sync
        finally:
            server.close()

    synced, last_sync = run(scenario())
    assert synced is True
    assert last_sync == 0


def test_integration_full_task_stays_not_synced_when_nobody_answers() -> None:
    client = make_integration_client()

    async def scenario() -> bool:
        task = asyncio.create_task(client.asy_ntp_time())
        client.ntp_sync_trigger_event.set()
        await asyncio.sleep(1)  # comfortably longer than _NTP_CONN_TIMEOUT would need to fail once
        synced = await client.ntp_issynced()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return synced

    assert run(scenario()) is False


def test_integration_full_task_stays_not_synced_on_a_malformed_reply() -> None:
    client = make_integration_client()
    garbage_reply = b"not-a-real-ntp-packet-at-all-way-too-short"

    async def scenario() -> bool:
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                task = asyncio.create_task(client.asy_ntp_time())
                server_task = asyncio.create_task(server.serve_once(garbage_reply))
                client.ntp_sync_trigger_event.set()
                await asyncio.wait_for(server_task, 5)
                await asyncio.sleep(0.2)
                synced = await client.ntp_issynced()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return synced
        finally:
            server.close()

    assert run(scenario()) is False


def test_integration_recovers_on_retry_after_one_dropped_request() -> None:
    # A real network fault propagated up and then recovered from - but only meaningful once
    # already synced once: _handle_ntp_sync_failure()'s one-shot retry timer is only armed when
    # ntp_synced is already True (its own comment: a fresh/never-synced client instead relies on
    # ntp_time_hours_counter()'s own periodic retrigger, covered separately above). So this first
    # gets one real successful sync, forces a second attempt that gets dropped (simulating a lost
    # UDP packet / transient unreachable server), and proves the resulting retry timer genuinely
    # reaches a real listening server on a later attempt, not just in isolation.
    client = make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def _wait_synced(target: bool) -> None:
        for _ in range(200):
            if await client.ntp_issynced() == target:
                return
            await asyncio.sleep_ms(20)

    async def scenario() -> bool:
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                task = asyncio.create_task(client.asy_ntp_time())
                client.ntp_sync_trigger_event.set()
                first_reply_task = asyncio.create_task(server.serve_once(reply))
                await asyncio.wait_for(first_reply_task, 5)
                await _wait_synced(True)
                assert await client.ntp_issynced() is True  # confirmed synced once via a real round trip

                await client.ntp_force_sync()  # trigger a second attempt
                await server.serve_once(None)  # drop it entirely
                for _ in range(300):  # wait for the real _NTP_CONN_TIMEOUT to elapse and arm a retry
                    if client.ntp_retry_timer.callback is not None:
                        break
                    await asyncio.sleep_ms(20)
                assert client.ntp_retry_timer.callback is not None  # retry genuinely armed this time

                client.ntp_retry_timer.trigger()  # fire the scheduled retry immediately, not after 15s
                second_reply_task = asyncio.create_task(server.serve_once(reply))
                await asyncio.wait_for(second_reply_task, 5)
                await _wait_synced(True)
                synced = await client.ntp_issynced()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return synced
        finally:
            server.close()

    assert run(scenario())


def test_get_cfg_schema_matches_the_public_attribute() -> None:
    # get_cfg_schema() is the new, base-class-owned access path (see base_classes.py) - cfg_schema
    # itself stays a public attribute too, for the legacy REST layer's own direct reads.
    client = make_client()
    assert client.get_cfg_schema() == client.cfg_schema
    assert client.get_cfg_schema() == (_VAL_NH + _VAL_NOS + _VAL_NIH + _VAL_GMT + _VAL_DST)


def test_set_dict_cfg_works_out_of_the_box_with_zero_driver_changes() -> None:
    # Every NTP field is persist-only (this file's own module docstring: "Config setters are out
    # of scope... only the getter quartet is implemented" predates this generalization pass) - no
    # asy_ntp_client.py source change was needed to gain setter support at all, since
    # base_classes.py's generic _set_dict_cfg() already covers the "persist, nothing to push"
    # case for free. This is exactly the abstraction the design was meant to prove out.
    client = make_client()
    results = run(client._set_dict_cfg({"NTP_Host": "time.example.org", "NTP_Interv_H": 6}, client.get_cfg_schema()))
    assert results == {"NTP_Host": "Valid", "NTP_Interv_H": "Valid"}
    stored = run(client.cfgmgr.get_dict(["NTP_Host", "NTP_Interv_H"]))
    assert stored == {"NTP_Host": "time.example.org", "NTP_Interv_H": 6}


def test_set_dict_cfg_invalid_field_reported_individually_others_still_apply() -> None:
    client = make_client()
    results = run(client._set_dict_cfg({"NTP_Interv_H": 999, "GMTOffset": 7200}, client.get_cfg_schema()))
    assert results == {"NTP_Interv_H": "Invalid", "GMTOffset": "Valid"}
    stored = run(client.cfgmgr.get_dict(["NTP_Interv_H", "GMTOffset"]))
    assert stored == {"NTP_Interv_H": 12, "GMTOffset": 7200}  # Interv_H untouched default, GMTOffset applied


def test_no_push_callbacks_are_registered_for_any_ntp_field() -> None:
    # Confirms the persist-only design explicitly, not just implicitly via the absence of a push:
    # every NTP field goes straight to cfgmgr with nothing live to update.
    client = make_client()
    assert client._push_callbacks == {}


def test_cfg_schema_matches_what_cfgmgr_was_built_with() -> None:
    # Regression check for the sensortask-wozi.py integration bug where a shared REST helper
    # (api_helpers.py's cmd_post_check()) needed each module's own schema to call the promoted
    # config_manager.ConfigManager.write_config(data, cfg_vals) correctly - cfg_schema is the public
    # attribute that lets a caller outside this module get that schema without reaching into a
    # private, underscore-prefixed module-level const.
    client = make_client()
    assert client.cfg_schema == (_VAL_NH + _VAL_NOS + _VAL_NIH + _VAL_GMT + _VAL_DST)


def test_write_config_via_public_cfg_schema_round_trips_a_real_value() -> None:
    # Proves cfg_schema is actually usable for a real write, not just structurally equal - the exact
    # call shape api_helpers.py's cmd_post_check() now makes.
    client = make_client()

    async def scenario() -> "tuple[bool, dict[str, int | float | str | bool | None] | None]":
        written, _ = await client.cfgmgr.write_config({"NTP_Host": "time.example.org"}, client.cfg_schema)
        data = await client.cfgmgr.get_dict(["NTP_Host"])
        return written, data

    written, data = run(scenario())
    assert written
    assert data == {"NTP_Host": "time.example.org"}


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
