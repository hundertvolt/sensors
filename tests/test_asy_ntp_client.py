import asyncio
import os
import select
import socket
import struct
import time

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch
from machine import RTC, Timer

import asy_base_classes
import asy_ntp_client as ntpmod
import asy_spi_driver
from asy_fram_manager import FRAMManager
from asy_ntp_client import NTPClient, NtpTiming
from asy_print_log import DEFAULT_LOG, LogConfig, PrintLogHistoryStore

# Same one-process-per-test-file swap as test_asy_base_classes.py/test_asy_fram_driver.py/
# test_asy_fram_manager.py - only exercised by the FRAM-backed log test below, isolated to this
# file's own process.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Literal, NoReturn, TypeVar

    from typing_extensions import Self

    from asy_ntp_client import GMTimeStruct
    from asy_print_log import ErrorLog

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _last_err(counter: "ErrorLog", field: 'Literal["ErrNum", "ErrType"]') -> "int | str":
    value = counter["NTP"][field]  # ErrNum/ErrType are list-shaped once _error_check() has run once
    assert isinstance(value, list)
    return value[-1]


# Mirrors asy_ntp_client.py's own _VAL_NTP_HOST/_VAL_NTP_OFFSET/_VAL_NTP_INTERVAL/_VAL_GMT_OFFSET/_VAL_DST_OFFSET schema tuples -
# not importable once const()-folded (same reasoning as test_asy_wifi_service.py's own
# duplicated _PHASE_* constants), so mirrored here instead.
_VAL_NTP_HOST = (("NTPHost", "str", "pool.ntp.org", 3, 253, None),)
_VAL_NTP_OFFSET = (("NTPOffset", "int", 0, -43200, 43200, None),)
_VAL_NTP_INTERVAL = (("NTPInterval", "int", 12, 1, 24, None),)
_VAL_GMT_OFFSET = (("GMTOffset", "int", 3600, -43200, 43200, None),)
_VAL_DST_OFFSET = (("DSTOffset", "int", 3600, -43200, 43200, None),)


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("ntp")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


# The generated module's NtpTiming values: the resolver's DNS bounds and codegen's fetch timeout,
# then the client's own backoff defaults (_DEFAULT_RETRY_S/_DEFAULT_RETRY_MAX_S) - mirrored, not imported.
_DNS_TIMEOUT_MS = 500
_DNS_TRIES = 1
# @tunable ntp.fetch_timeout_ms = 5000
_FETCH_TIMEOUT_MS = 5000
_RETRY_S = 10
_RETRY_MAX_S = 600

# The client's own compiled-away schedule constants (asy_ntp_client.py) - mirrored, not imported.
# @tunable ntp.check_interval_s = 10
_CHECK_INTERVAL_S = 10
# @tunable ntp.retry_interval_s = 15
_RETRY_INTERVAL_S = 15
# @tunable ntp.sync_retries = 3
_SYNC_RETRIES = 3
# @tunable ntp.async_intervals = 3
_ASYNC_INTERVALS = 3

# @tunable l1.asy_ntp_client_event_wait_s = 0.2
_EVENT_WAIT_S = 0.2
# @tunable l1.asy_ntp_client_fake_server_poll_ms = 10
_FAKE_SERVER_POLL_MS = 10
# @tunable l1.asy_ntp_client_fired_probe_s = 0.05
_FIRED_PROBE_S = 0.05
# @tunable l1.asy_ntp_client_state_poll_ms = 20
_STATE_POLL_MS = 20
# @tunable l1.asy_ntp_client_no_answer_wait_s = 1
_NO_ANSWER_WAIT_S = 1
# @tunable l1.asy_ntp_client_reply_process_s = 0.2
_REPLY_PROCESS_S = 0.2
# @tunable l1.asy_ntp_client_no_reply_fetch_timeout_ms = 100
_NO_REPLY_FETCH_TIMEOUT_MS = 100
# @tunable l1.asy_ntp_client_past_fetch_timeout_ms = 200
_PAST_FETCH_TIMEOUT_MS = 200
# @tunable l1.asy_ntp_client_responder_poll_tries = 500
_RESPONDER_POLL_TRIES = 500
# @tunable l1.asy_ntp_client_fake_server_poll_tries = 1000
_FAKE_SERVER_POLL_TRIES = 1000
# @tunable l1.asy_ntp_client_synced_poll_tries = 50
_SYNCED_POLL_TRIES = 50
# @tunable l1.asy_ntp_client_state_poll_tries = 200
_STATE_POLL_TRIES = 200
# @tunable l1.asy_ntp_client_retry_armed_poll_tries = 300
_RETRY_ARMED_POLL_TRIES = 300


def _timing(
    dns_timeout_ms: int = _DNS_TIMEOUT_MS,
    dns_tries: int = _DNS_TRIES,
    fetch_timeout_ms: int = _FETCH_TIMEOUT_MS,
    retry_s: int = _RETRY_S,
    retry_max_s: int = _RETRY_MAX_S,
) -> NtpTiming:
    return NtpTiming(dns_timeout_ms, dns_tries, fetch_timeout_ms, retry_s, retry_max_s)


def make_client(
    wifi_mode_lock: "asyncio.Lock | None" = None,
    network_available_locked: "Callable[[], bool] | None" = None,
    get_dns_server: "Callable[[], str | None] | None" = None,
    timing: "NtpTiming | None" = None,
    log: LogConfig = DEFAULT_LOG,
    cfg_path: "str | None" = None,
) -> NTPClient:
    if wifi_mode_lock is None:
        wifi_mode_lock = asyncio.Lock()
    if network_available_locked is None:
        network_available_locked = lambda: True  # noqa: E731
    if get_dns_server is None:
        get_dns_server = lambda: None  # noqa: E731
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    client = NTPClient(
        wifi_mode_lock,
        network_available_locked,
        get_dns_server,
        _timing() if timing is None else timing,
        cfg_path=cfg_path,
        log=log,
    )
    run(client.setup())  # the boot batch's setup(): the logger, then the config manager
    return client


def make_client_with_json(json_text: str) -> NTPClient:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(json_text)
    return make_client(cfg_path=cfg_path)


def make_invalid_cfg_client() -> NTPClient:
    # A directory where ConfigManager expects a plain file - its os.stat() 0x4000 (MP_S_IFDIR)
    # check rejects it and leaves self.valid False, the same "config manager itself is invalid"
    # state the old empty-schema route reproduced before this driver's schema became non-empty.
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_NTP.cfg")
    return make_client(cfg_path=cfg_path)


class _RaiseOnArm:
    # Same technique as test_asy_system_service.py's _RaiseOnArm - toggles tests/machine.py's shared
    # Timer.raise_on_arm for the `with` block, simulating rp2 alarm-pool exhaustion. `exc` picks
    # which arm of `except (OSError, MemoryError)` runs; neither covers the other (Part F).
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "Self":
        Timer.raise_on_arm_exc = self._exc
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        Timer.raise_on_arm = False
        Timer.raise_on_arm_exc = OSError


# Below the OS ephemeral range (32768-60999) so a concurrently-running ephemeral socket can
# never be assigned this port - see scripts/test.sh's own TEST_PARALLELISM comment.
_next_port = 23000


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
# __init__ - NTPClient now extends asy_base_classes.py's SensorReaderConfig: it owns its own
# config_NTP.cfg file/schema internally (no externally-injected ConfigManager, no separate
# get_default_cfg()/_DEFAULT_CONFIG merge step anymore - see SPECIFICATION.md/BACKLOG.md).
# ---------------------------------------------------------------------------


def test_init_never_synced_before_first_task_run() -> None:
    client = make_client()
    assert run(client.ntp_issynced()) is False
    assert run(client.get_last_ntp_sync()) is None


def test_init_creates_its_own_config_file_with_schema_defaults() -> None:
    cfg_path = _tmp_cfg_dir()
    client = make_client(cfg_path=cfg_path)
    assert client.cfgmgr.valid is True
    values = run(client.cfgmgr.get_dict(["NTPHost", "NTPOffset", "NTPInterval", "GMTOffset", "DSTOffset"]))
    assert values == {
        "NTPHost": "pool.ntp.org",
        "NTPOffset": 0,
        "NTPInterval": 12,
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
    client = make_client(log=LogConfig(None, 10, 3))
    assert client.pr.level == 3


def test_get_task_starters_returns_all_three_ntp_tasks() -> None:
    client = make_client()
    assert client.get_task_starters() == [
        client.start_asy_sync,
        client.start_asy_refresh,
        client.start_asy_sync_age,
    ]


def test_get_timer_starters_returns_both_ntp_timers() -> None:
    client = make_client()
    assert client.get_timer_starters() == [client.start_check_timer, client.start_sync_age_timer]


def test_start_asy_ntp_refresh_returns_a_real_task() -> None:
    client = make_client()

    async def scenario() -> bool:
        task = client.start_asy_refresh()
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
        task = client.start_asy_sync_age()
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
    # Proves the constructor forwards its log config to SensorReaderConfig/SensorReader rather than
    # dropping it, using the same real FRAMManager plus simulated chip test_asy_base_classes.py uses.
    bus = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = FRAMManager(bus, 1, max_size=0x2000)
    client = make_client(log=LogConfig(manager, 10, None))
    assert isinstance(client.pr, PrintLogHistoryStore)


# ---------------------------------------------------------------------------
# get_dict_cfg / get_data / get_dict_data / get_error_counter - the base-class getter quartet
# (SPECIFICATION.md Part C.4.2).
# ---------------------------------------------------------------------------


def test_get_dict_cfg_returns_schema_defaults_wrapped_in_ntp_key() -> None:
    client = make_client()
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTPHost": "pool.ntp.org",
            "NTPOffset": 0,
            "NTPInterval": 12,
            "GMTOffset": 3600,
            "DSTOffset": 3600,
        },
    }


def test_get_dict_cfg_reflects_a_customized_on_disk_config() -> None:
    client = make_client_with_json(_VALID_JSON)
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTPHost": "time.example.org",
            "NTPOffset": 5,
            "NTPInterval": 6,
            "GMTOffset": 7200,
            "DSTOffset": 3600,
        },
    }


def test_get_dict_cfg_returns_all_none_values_when_config_manager_is_invalid() -> None:
    client = make_invalid_cfg_client()
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTPHost": None,
            "NTPOffset": None,
            "NTPInterval": None,
            "GMTOffset": None,
            "DSTOffset": None,
        },
    }


def test_get_data_and_get_dict_data_reflect_the_initial_never_synced_state() -> None:
    asy_base_classes.set_utc_valid(valid=False)  # another test's sync may have set the process-wide flag
    client = make_client()
    data = run(client.get_data())
    assert data.Synced is False
    assert data.LastSyncAge is None
    assert data.TS is None  # no timestamp before the first sync of the boot
    dict_data = run(client.get_dict_data())
    assert dict_data == {"NTP": {"Synced": False, "LastSyncAge": None, "TS": None}}


def test_get_data_reflects_a_successful_sync() -> None:
    client = make_client()
    try:
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        data = run(client.get_data())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert data.Synced is True
    assert data.LastSyncAge == 0
    assert data.TS is not None  # the sync itself marked the clock valid before stamping


def test_a_successful_sync_marks_the_utc_clock_valid() -> None:
    client = make_client()
    try:
        asy_base_classes.set_utc_valid(valid=False)
        assert asy_base_classes.utc_now() is None
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        assert isinstance(asy_base_classes.utc_now(), int)
    finally:
        asy_base_classes.set_utc_valid(valid=False)


def test_get_dict_data_reflects_a_successful_sync() -> None:
    client = make_client()
    try:
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        dict_data = run(client.get_dict_data())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert dict_data["NTP"]["TS"] is not None
    assert dict_data["NTP"]["Synced"] is True
    assert dict_data["NTP"]["LastSyncAge"] == 0


def test_get_error_counter_starts_empty_and_records_a_real_error() -> None:
    client = make_client()
    counter = run(client.get_error_counter())
    assert counter["NTP"]["ErrCount"] == 0
    run(client.pr.err_s("boom", errno=1))
    counter = run(client.get_error_counter())
    assert counter["NTP"]["ErrCount"] == 1


def test_get_error_counter_counts_a_warning_too() -> None:
    # Full-dict equality (not indexing into the union-typed ErrNum/ErrType values) - same style
    # test_asy_print_log.py's own get_log() tests use; history_length defaults to 10 (make_client()
    # doesn't override it), so 9 untouched "N"/0 slots precede the one real warning.
    client = make_client()
    run(client.pr.wrn_s("careful", wrnno=1))
    counter = run(client.get_error_counter())
    assert counter == {"NTP": {"ErrCount": 1, "ErrNum": [0] * 9 + [1], "ErrType": ["N"] * 9 + ["W"]}}


def test_get_error_counter_records_multiple_entries_in_order() -> None:
    client = make_client()
    run(client.pr.err_s("first error", errno=1))
    run(client.pr.wrn_s("first warning", wrnno=2))
    counter = run(client.get_error_counter())
    assert counter == {"NTP": {"ErrCount": 2, "ErrNum": [0] * 8 + [1, 2], "ErrType": ["N"] * 8 + ["E", "W"]}}


# The state helpers _set_synced()/_set_last_sync_age(): each does an unlocked get-then-set with no
# await between (see asy_ntp_client.py's comment on _set_synced()).
# ---------------------------------------------------------------------------


def test_set_synced_to_true_preserves_last_sync_age_and_ts() -> None:
    client = make_client()
    run(client._set_last_sync_age(value=42))
    before = run(client.get_data())
    run(client._set_synced(value=True))
    after = run(client.get_data())
    assert after.Synced is True
    assert after.LastSyncAge == 42
    assert after.TS == before.TS  # _set_synced() never touches TS


def test_set_synced_to_false_preserves_last_sync_age() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    run(client._set_last_sync_age(value=7))
    run(client._set_synced(value=False))
    data = run(client.get_data())
    assert data.Synced is False
    assert data.LastSyncAge == 7


def test_set_last_sync_age_preserves_synced_flag_when_true() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    run(client._set_last_sync_age(value=99))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge == 99


def test_set_last_sync_age_to_none_preserves_synced_flag() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    run(client._set_last_sync_age(value=None))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge is None


def test_the_sync_age_publish_keeps_the_synced_flag() -> None:
    client = make_client()

    async def scenario() -> "tuple[bool, int | None]":
        await client._set_synced(value=True)
        task = asyncio.create_task(client._sync_age_loop())
        await _tick(client._time_counter_trigger_event)
        data = await client.get_data()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return data.Synced, data.LastSyncAge

    synced, age = run(scenario())
    assert synced is True
    assert age is not None


# ---------------------------------------------------------------------------
# Timer start/stop - normal arm, and real rp2 alarm-pool exhaustion (OSError(ENOMEM))
# ---------------------------------------------------------------------------


def test_start_ntp_timer_arms_periodic_with_the_documented_period() -> None:
    client = make_client()
    client.start_check_timer()
    assert client._ntp_timer.mode == Timer.PERIODIC
    assert client._ntp_timer.period == _CHECK_INTERVAL_S * 1000


def test_start_ntp_timer_fires_the_trigger_event() -> None:
    client = make_client()
    client.start_check_timer()

    async def scenario() -> bool:
        client._ntp_timer.trigger()
        try:
            await asyncio.wait_for(client._ntp_timer_trigger_event.wait(), _EVENT_WAIT_S)
        except asyncio.TimeoutError:
            return False
        else:
            return True

    assert run(scenario())


def test_start_ntp_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    print("(expected) simulating alarm-pool exhaustion - the following 'Could not start NTP timer' is intentional")
    with _RaiseOnArm():
        client.start_check_timer()  # must not raise despite the timer failing to arm
    assert client._ntp_timer.period == -1  # never actually armed


def test_start_ntp_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_check_timer()'s own
    # `except (OSError, MemoryError)`: a real alarm allocation can fail with MemoryError instead,
    # which is not an OSError subclass - same graceful degradation must hold either way.
    client = make_client()
    print("(expected) simulating an allocation failure - the following 'Could not start NTP timer' is intentional")
    with _RaiseOnArm(MemoryError):
        client.start_check_timer()  # must not raise despite the timer failing to arm
    assert client._ntp_timer.period == -1  # never actually armed


def test_stop_ntp_timer_deinits() -> None:
    client = make_client()
    client.start_check_timer()
    client.stop_check_timer()
    assert client._ntp_timer.deinit_called is True


def test_start_counter_timer_arms_periodic_1s() -> None:
    client = make_client()
    client.start_sync_age_timer()
    assert client._counter_timer.mode == Timer.PERIODIC
    assert client._counter_timer.period == 1000


def test_start_counter_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    with _RaiseOnArm():
        client.start_sync_age_timer()
    assert client._counter_timer.period == -1


def test_start_counter_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_sync_age_timer()'s own
    # `except (OSError, MemoryError)`.
    client = make_client()
    with _RaiseOnArm(MemoryError):
        client.start_sync_age_timer()
    assert client._counter_timer.period == -1


def test_stop_counter_timer_deinits() -> None:
    client = make_client()
    client.start_sync_age_timer()
    client.stop_sync_age_timer()
    assert client._counter_timer.deinit_called is True


# ---------------------------------------------------------------------------
# ntp_issynced / ntp_force_sync / get_last_ntp_sync
# ---------------------------------------------------------------------------


def test_ntp_force_sync_resets_last_sync_retries_and_fires_the_sync_trigger() -> None:
    client = make_client()

    async def scenario() -> bool:
        await client._set_last_sync_age(value=5)
        client._ntp_retries = 2
        await client.ntp_force_sync()
        assert await client.get_last_ntp_sync() is None
        assert client._ntp_retries == 0
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _EVENT_WAIT_S)
        except asyncio.TimeoutError:
            return False
        else:
            return True

    assert run(scenario())


def test_ntp_force_sync_deinits_a_pending_retry_timer() -> None:
    client = make_client()
    client._ntp_retry_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)
    run(client.ntp_force_sync())
    assert client._ntp_retry_timer.deinit_called is True


# ---------------------------------------------------------------------------
# Configuration: every valid field, plus single/multiple invalid recombinations from a real
# on-disk config_NTP.cfg, through the real ConfigManager this client owns - proving this module's
# handling of per-field defaulting, not re-testing ConfigManager (test_asy_config_manager.py does).
# ---------------------------------------------------------------------------

_VALID_JSON = (
    '{"NTPHost": "time.example.org", "NTPOffset": 5, "NTPInterval": 6, '
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
    # NTPHost too short (min length 3) - falls back to its own default; NTPOffset stays real.
    json_text = '{"NTPHost": "ab", "NTPOffset": 5, "NTPInterval": 6, "GMTOffset": 7200, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]  # defaulted
    assert ntp_offs == [5]  # untouched


def test_get_ntp_config_multiple_invalid_fields_each_fall_back_independently() -> None:
    # NTPHost wrong type, NTPOffset out of range (both invalid at once) - each defaults on its own.
    json_text = '{"NTPHost": 12345, "NTPOffset": 999999, "NTPInterval": 6, "GMTOffset": 7200, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    ntp_host, ntp_offs = ntp_cfg
    assert ntp_host == ["pool.ntp.org"]
    assert ntp_offs == [0]


def test_get_ntp_config_all_fields_invalid_falls_back_to_every_default() -> None:
    json_text = '{"NTPHost": null, "NTPOffset": "bad", "NTPInterval": -5, "GMTOffset": "x", "DSTOffset": null}'
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
# _safe_get_dns_server - reads the get_dns_server callback (WifiService.get_dns_server_ip) and
# wraps its errors; called by _sync_loop() BEFORE acquiring wifi_mode_lock, since from inside
# the locked section it always saw the shared Lock as held and always got None back.
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


def test_safe_get_dns_server_callback_raising_persists_a_callback_error() -> None:
    def raiser() -> "str | None":
        raise RuntimeError("get_wlan_ifconfig() exploded")

    client = make_client(get_dns_server=raiser)
    run(client._safe_get_dns_server())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "CALLBACK")
    assert _last_err(counter, "ErrType") == "E"


# ---------------------------------------------------------------------------
# _resolve_ntp_server - delegates to asy_dns_client.py's resolve_ipv4(), so this file's old
# long_block_lock is gone: resolve_ipv4() never blocks the event loop the way getaddrinfo() did.
# dns_server is a plain parameter, since _safe_get_dns_server() must run before the lock above.
# ---------------------------------------------------------------------------


def test_resolve_ntp_server_literal_ip_returns_immediately() -> None:
    # asy_dns_client.py's own resolve_ipv4() short-circuits a literal IPv4 address without any
    # network I/O at all - proven at that layer already (tests/test_asy_dns_client.py); this just
    # confirms the (ip, 123) tuple shape _resolve_ntp_server() wraps its result in.
    client = make_client()
    result = run(client._resolve_ntp_server("127.0.0.1", None))
    assert result == ("127.0.0.1", 123)


class _RecordingResolver:
    # Stands in for asy_dns_client.resolve_ipv4() - proves _resolve_ntp_server()'s orchestration
    # (tuple building, error handling, timeout_ms/tries forwarding) independent of resolve_ipv4()'s
    # own network behavior, which tests/test_asy_dns_client.py covers exhaustively.
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
        client = make_client(timing=_timing(dns_timeout_ms=1234, dns_tries=3))
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
        run(client._resolve_ntp_server("bogus.invalid", None))
    finally:
        ntpmod.resolve_ipv4 = original
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "NTP_DNS")
    assert _last_err(counter, "ErrType") == "E"


# No real-network end-to-end test through _resolve_ntp_server() itself: resolve_ipv4()'s `port`
# has no override here, and binding a fake DNS peer to port 53 needs root and is
# environment-dependent, unlike every other loopback test in this suite.

# The seam is already fully characterized above (_RecordingResolver pins the exact arguments and
# return-value handling) and resolve_ipv4()'s real UDP behavior is covered by
# tests/test_asy_dns_client.py - together proving what a port-53 test would, without the fragility.


# ---------------------------------------------------------------------------
# _fetch_ntp_reply
# ---------------------------------------------------------------------------


def test_fetch_ntp_reply_invalid_addr_returns_none() -> None:
    client = make_client()
    result = run(client._fetch_ntp_reply((12345, 80)))  # type: ignore[arg-type]  # host not a str
    assert result is None


# Recorder shared by every _RecordingUDPSocket instance below - module-level rather than a class
# attribute so the shared mutable state is explicit at the point it lives.
_recording_udp_calls: "list[int]" = []


class _RecordingUDPSocket:
    # Stands in for asy_udp_socket.UDPSocket - records the timeout_ms _fetch_ntp_reply() passes
    # to write_and_recvfrom(), proving ntp_fetch_timeout_ms is this instance's configured value
    # reaching the real call, not a hardcoded module constant.
    def __init__(self, addr: "tuple[str, int]", mode: str = "client", conn_tries: int = 1) -> None:
        pass

    # Only timeout_ms is read; the rest keep UDPSocket's own parameter order/positions.
    async def write_and_recvfrom(
        self, _msg: "bytes | bytearray", _buf: int, timeout_ms: int = -1, _tries: int = 1,
    ) -> "tuple[bytes | None, tuple[str, int] | None]":
        _recording_udp_calls.append(timeout_ms)
        return None, None

    async def disconnect(self) -> None:
        pass


def test_fetch_ntp_reply_forwards_the_constructors_own_fetch_timeout() -> None:
    client = make_client(timing=_timing(fetch_timeout_ms=9999))
    original = ntpmod.UDPSocket
    _recording_udp_calls.clear()
    ntpmod.UDPSocket = _RecordingUDPSocket  # type: ignore[assignment, misc]
    try:
        run(client._fetch_ntp_reply(("127.0.0.1", 123)))
    finally:
        ntpmod.UDPSocket = original  # type: ignore[misc]
    assert _recording_udp_calls == [9999]


def test_fetch_ntp_reply_ipv6_shaped_four_tuple_addr_returns_none() -> None:
    # getaddrinfo() is called with no address-family hint, so a resolver preferring IPv6 hands
    # back a 4-tuple, not the 2-tuple this file assumes. UDPSocket.__init__ rejects that with
    # TypeError, which _fetch_ntp_reply catches, so the pipeline degrades to "no reply".
    client = make_client()
    result = run(client._fetch_ntp_reply(("2001:db8::1", 123, 0, 0)))  # type: ignore[arg-type]
    assert result is None


def test_fetch_ntp_reply_no_server_listening_times_out_to_none() -> None:
    client = make_client()
    addr = make_addr()
    result = run(client._fetch_ntp_reply(addr))
    assert result is None
    assert _last_err(run(client.get_error_counter()), "ErrNum") == code("E", "NTP_NO_REPLY")  # a silent timeout used to persist nothing


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
        for _ in range(_RESPONDER_POLL_TRIES):
            # ipoll(0) returns an always-truthy iterator on this port (confirmed directly) - must
            # iterate and check the actual event flags, exactly like asy_udp_socket.py's own
            # ready() does, not just truth-test the returned object itself.
            ready = any(event & select.POLLIN for _fd, event in poller.ipoll(0))
            if ready:
                try:
                    _data, from_addr = server.recvfrom(1024)
                except OSError:  # spurious wakeup/transient EAGAIN - keep polling instead of raising
                    await asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)
                    continue
                server.sendto(reply, from_addr)
                break
            await asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)
        server.close()

    async def scenario() -> "bytes | None":
        responder_task = asyncio.create_task(responder())
        await asyncio.sleep(0)  # let the responder bind()+register() before the client sends -
        # UDPSocket's own _connect()/ready() can complete synchronously for a fresh, uncontended
        # client socket (UDP connect()/POLLOUT are both immediately satisfiable), so without this
        # yield the request could race ahead of the responder's own bind() (confirmed directly).
        msg = await client._fetch_ntp_reply(addr)
        await responder_task
        return msg

    assert run(scenario()) == reply


# ---------------------------------------------------------------------------
# _parse_ntp_reply - NTP packet format per RFC 5905: 48-byte header, Transmit Timestamp at byte
# offset 40 (only the integer seconds half is read), 2208988800s being the 1900->1970 epoch delta.

# Byte 0's Leap Indicator and byte 1's Stratum are checked before the timestamp is trusted at all
# (LI=3 "unsynchronized" and Stratum=0 Kiss-o'-Death are rejected), so every helper below sets
# Stratum=1 by default. _parse_ntp_reply() is async, hence the run() around every call.
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
    # A non-zero Stratum whenever the length reaches index 1, so these truncation-length tests are
    # rejected for being too short to reach the Transmit Timestamp, not incidentally for looking
    # like a Kiss-o'-Death reply - keeping this isolated from the separate LI/Stratum check.
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
    def gmtime(self, *_a: int) -> "NoReturn":
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


def _make_raw_ntp_reply(raw_s: int) -> bytes:
    # Same LI=0/Stratum=1 header as make_ntp_reply() above - a genuinely-synchronized-looking
    # server, so these era/plausibility-window tests aren't incidentally rejected by the separate
    # LI/Stratum check instead of exercising the era logic they're meant to test.
    header = b"\x1c\x01" + bytes(38)
    transmit = struct.pack("!I", raw_s & 0xFFFFFFFF) + bytes(4)
    msg = header + transmit
    assert len(msg) == 48
    return msg


def test_parse_ntp_reply_era_rollover_wrapped_reply_reconstructs_the_real_future_date() -> None:
    # NTP's 32-bit "seconds since 1900" field wraps in 2036, distinct from the ~2037 Unix time_t
    # OverflowError above, so a post-2036 server sends a small wrapped value. _parse_ntp_reply()
    # reinterprets a below-floor reading as the next NTP era (RFC 5905 7.3) and rechecks it.
    client = make_client()
    target_unix = 2185978496  # 2039-04-09ish - past the ~2036 wrap, well within the plausible ceiling
    raw = (target_unix + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(target_unix))


def test_parse_ntp_reply_rejects_a_timestamp_implausible_in_every_era() -> None:
    # A raw value implausible both read directly (era 0: ~1995, below the floor) and after the
    # one-shot era reinterpretation (era 1: ~2131, past the ceiling) - genuinely corrupt data, not
    # an ordinary rollover reply. This used to produce a bogus-but-accepted "successful sync".
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
    # RFC 5905's Leap Indicator = 3 ("clock unsynchronized") is an alarm condition: the server is
    # explicitly saying it is not a trustworthy time source, even though its Transmit Timestamp
    # here is a plausible current date that would pass every other check.
    client = make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=3, stratum=1, unix_seconds=int(time.time()))
    assert run(client._parse_ntp_reply(msg, 0)) is None


def test_parse_ntp_reply_rejects_stratum_zero_kiss_of_death() -> None:
    # RFC 5905/4330: Stratum 0 means "unspecified or invalid", used for Kiss-o'-Death packets -
    # never a genuine time source whatever its Transmit Timestamp holds. A real KoD reply's
    # all-zero timestamp would otherwise land inside the plausibility window after era-reinterp.
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
    assert client._ntp_retry_timer.period == -1  # never armed - _refresh_loop() retries instead


def test_handle_sync_failure_while_synced_arms_a_retry_and_increments_the_counter() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    run(client._handle_ntp_sync_failure())
    assert client._ntp_retries == 1
    assert client._ntp_retry_timer.mode == Timer.ONE_SHOT
    assert client._ntp_retry_timer.period == _RETRY_INTERVAL_S * 1000


def test_handle_sync_failure_retry_timer_fires_the_sync_trigger() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    run(client._handle_ntp_sync_failure())

    async def scenario() -> bool:
        client._ntp_retry_timer.trigger()
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _EVENT_WAIT_S)
        except asyncio.TimeoutError:
            return False
        else:
            return True

    assert run(scenario())


def test_handle_sync_failure_gives_up_after_max_retries() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    client._ntp_retries = _SYNC_RETRIES
    run(client._handle_ntp_sync_failure())
    assert client._ntp_retries == 0
    assert client._ntp_retry_timer.period == -1  # never (re)armed - past the retry budget


def test_handle_sync_failure_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    with _RaiseOnArm():
        run(client._handle_ntp_sync_failure())  # must not raise despite the timer failing to arm
    assert client._ntp_retries == 0  # given up this cycle rather than left stuck


def test_handle_sync_failure_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of _handle_ntp_sync_failure()'s own
    # `except (OSError, MemoryError)` - the retry cycle is given up the same way either way, and the
    # same TIMER error is persisted (this site logs via the async err_s(), unlike the two starters above).
    client = make_client()
    run(client._set_synced(value=True))
    with _RaiseOnArm(MemoryError):
        run(client._handle_ntp_sync_failure())  # must not raise despite the timer failing to arm
    assert client._ntp_retries == 0  # given up this cycle rather than left stuck
    assert _last_err(run(client.get_error_counter()), "ErrNum") == code("E", "TIMER")


def _slots(client: NTPClient) -> "tuple[int, list[int]]":
    # (ErrCount, the ring's used slots oldest first) - "N" marks an unused one.
    entry = run(client.get_error_counter())["NTP"]
    nums, types = entry["ErrNum"], entry["ErrType"]
    assert isinstance(nums, list) and isinstance(types, list)
    return int(entry["ErrCount"]), [nums[i] for i in range(len(nums)) if types[i] != "N"]


def test_repeated_retry_arm_failures_count_each_and_keep_one_slot() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    with _RaiseOnArm():
        run(client._handle_ntp_sync_failure())
        run(client._handle_ntp_sync_failure())
    assert _slots(client) == (2, [code("E", "TIMER")])


def test_repeated_retry_exhaustion_counts_each_and_keep_one_slot() -> None:
    client = make_client()
    run(client._set_synced(value=True))
    for _ in range(2):
        client._ntp_retries = _SYNC_RETRIES
        run(client._handle_ntp_sync_failure())
    assert _slots(client) == (2, [code("E", "NTP_RETRIES")])


def test_handle_sync_success_resets_retries_marks_synced_and_records_the_sync_time() -> None:
    client = make_client()
    client._ntp_retries = 2
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert client._ntp_retries == 0
    assert run(client.ntp_issynced()) is True
    assert run(client.get_last_ntp_sync()) == 0


def test_handle_sync_success_deinits_a_pending_retry_timer() -> None:
    client = make_client()
    client._ntp_retry_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert client._ntp_retry_timer.deinit_called is True


# ---------------------------------------------------------------------------
# _refresh_loop
# ---------------------------------------------------------------------------


async def _tick(flag: "asyncio.ThreadSafeFlag", times: int = 1) -> None:
    for _ in range(times):
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # let one full loop iteration's awaits settle


class _DrivenTime:
    # A ticks source the test advances, installed as asy_base_classes' `time` for the block: the sync
    # age counts measured ticks (SPECIFICATION.md G.2), so it follows advance(), never the wake-ups.
    def __init__(self) -> None:
        self.now_ms = 0

    def __enter__(self) -> "Self":
        self._real = asy_base_classes.time
        asy_base_classes.time = self  # type: ignore[assignment]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *exc_info: object) -> None:
        asy_base_classes.time = self._real

    def advance(self, ms: int) -> None:
        self.now_ms += ms

    def ticks_ms(self) -> int:
        return self.now_ms

    def ticks_diff(self, new: int, old: int) -> int:
        return new - old

    def gmtime(self) -> "tuple[int, ...]":
        return self._real.gmtime()

    def mktime(self, t: "tuple[int, ...]") -> int:
        return self._real.mktime(t)


def test_ntp_time_hours_counter_missing_config_falls_back_to_12h_default_without_raising() -> None:
    client = make_invalid_cfg_client()

    async def scenario() -> None:
        task = asyncio.create_task(client._refresh_loop())
        await _tick(client._ntp_timer_trigger_event, 1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run(scenario())  # must not raise despite the missing config


def test_ntp_time_hours_counter_triggers_sync_immediately_when_not_yet_synced() -> None:
    client = make_client()

    async def scenario() -> bool:
        task = asyncio.create_task(client._refresh_loop())
        await _tick(client._ntp_timer_trigger_event, 1)
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _EVENT_WAIT_S)
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


def test_ntp_time_hours_counter_waits_out_the_current_backoff_step_while_unsynced() -> None:
    # _retry_wait_s=40 at the 10s tick: the 4th tick triggers, not the 3rd; the count then restarts.
    client = make_client()
    client._retry_wait_s = 40

    async def fired() -> bool:
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _FIRED_PROBE_S)
        except asyncio.TimeoutError:
            return False
        return True

    async def scenario() -> "list[bool]":
        task = asyncio.create_task(client._refresh_loop())
        results = []
        for ticks in (3, 1, 3, 1):
            await _tick(client._ntp_timer_trigger_event, ticks)
            results.append(await fired())
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return results

    assert run(scenario()) == [False, True, False, True]


def test_ntp_time_hours_counter_does_not_retrigger_while_synced_and_under_interval() -> None:
    json_text = '{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(value=True)
        task = asyncio.create_task(client._refresh_loop())
        await _tick(client._ntp_timer_trigger_event, 1)  # one tick, well under 1h / 10s-per-tick
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _EVENT_WAIT_S)
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
    # NTPInterval=1 -> 3600s / _NTP_CHECK_INTERV(10s) = 360 ticks to reach the interval.
    json_text = '{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(value=True)
        task = asyncio.create_task(client._refresh_loop())
        await _tick(client._ntp_timer_trigger_event, 360)
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _EVENT_WAIT_S)
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
    # set _ntp_sec_count directly at that boundary to isolate this specific transition.
    json_text = '{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(value=True)
        task = asyncio.create_task(client._refresh_loop())
        await asyncio.sleep(0)  # let the task run past its own `self._ntp_sec_count = 0` reset first
        client._ntp_sec_count = _ASYNC_INTERVALS * 1 * 60 * 60  # x NTPInterval (1) x 3600 s
        await _tick(client._ntp_timer_trigger_event, 1)
        synced = await client.ntp_issynced()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return synced

    assert run(scenario()) is False


def test_ntp_time_hours_counter_never_naturally_reaches_the_async_interval_multiple_under_constant_config() -> None:
    # Complements the test above that isolates the 3x transition by poking _ntp_sec_count. Under
    # natural ticking the loop's own reset-to-0 at 1x fires every cycle before sec_count nears 3x,
    # so the "distrust a stale sync" net never engages - inherited byte for byte from legacy.
    json_text = '{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    client = make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(value=True)
        task = asyncio.create_task(client._refresh_loop())
        # 3 full 1h/360-tick cycles - well past where the 3x(=3h) threshold would sit if sec_count
        # were ever allowed to accumulate past a single 1x cycle.
        await _tick(client._ntp_timer_trigger_event, 3 * 360)
        still_synced = await client.ntp_issynced()
        sec_count_bounded = client._ntp_sec_count < (1 * 60 * 60)  # always reset well under 1x
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return still_synced and sec_count_bounded

    assert run(scenario())


# ---------------------------------------------------------------------------
# cettime() - CET/CEST DST boundary math, verified through the real time.mktime()/time.gmtime()
# rather than hand-computing the "last Sunday of March/October" formula, which is copied verbatim
# from deployed production code. This only proves branch selection and exception safety.
#
# Real finding, flagged rather than silently fixed: this project's pinned Unix-port interpreter's
# time.gmtime() returns a 9-element tuple (trailing isdst=0), not the 8-element shape MicroPython
# documents for embedded ports including rp2 - the ambiguity typings' _TimeTuple anticipates.
#
# cettime()'s `if len(cet) == 8` check is correct for the real rp2 target but would return None
# under this interpreter, so every test below normalizes gmtime()'s result to 8 elements through
# a monkeypatched `time` shim.
# ---------------------------------------------------------------------------


def test_this_interpreters_gmtime_returns_nine_elements_not_eight() -> None:
    assert len(time.gmtime()) == 9


class _FixedNowTime:
    # Same monkeypatch technique as test_asy_system_service.py's _OverflowingTime/_RaisingGmtime -
    # replaces this module's own `time` name, not the read-only builtin. gmtime()/mktime()
    # delegate to the real module; only time() is overridden and gmtime() truncated to 8 elements.
    def __init__(self, fixed_now: int, raise_exc: "Exception | None" = None) -> None:
        self._fixed_now = fixed_now
        self._raise_exc = raise_exc

    def gmtime(self, *a: int) -> "tuple[int, ...]":
        if self._raise_exc is not None:
            raise self._raise_exc
        return tuple(time.gmtime(*a))[:8]

    def mktime(self, t: "tuple[int, ...]") -> int:
        if self._raise_exc is not None:
            raise self._raise_exc
        return time.mktime(t)

    def time(self) -> int:
        return self._fixed_now


def _mid_month_now(month: int) -> int:
    year = time.gmtime()[0]
    return time.mktime((year, month, 15, 12, 0, 0, 0, 0, 0))


def _client_with_offsets(gmt_offset: int, dst_offset: int) -> NTPClient:
    # Deliberately one single f-string, not a plain literal adjacent to an f-string: confirmed
    # directly that MicroPython mishandles the latter when the plain part contains a literal brace
    # (this JSON's opening "{"), raising a spurious KeyError on the plain part's own content.
    json_text = (
        f'{{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 12, '
        f'"GMTOffset": {gmt_offset}, "DSTOffset": {dst_offset}}}'
    )
    return make_client_with_json(json_text)


def test_cettime_returns_none_when_not_synced() -> None:
    client = make_client()
    assert run(client.cettime()) is None


def test_cettime_returns_none_when_config_missing() -> None:
    client = make_invalid_cfg_client()
    run(client._set_synced(value=True))
    assert run(client.cettime()) is None


def _run_cettime_with_fixed_now(client: NTPClient, fixed_now: int, raise_exc: "Exception | None" = None) -> "GMTimeStruct | None":
    original_time = ntpmod.time
    ntpmod.time = _FixedNowTime(fixed_now, raise_exc)  # type: ignore[assignment]
    try:
        return run(client.cettime())
    finally:
        ntpmod.time = original_time


def test_cettime_before_march_boundary_applies_gmt_offset_only() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(value=True))
    fixed_now = _mid_month_now(1)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600))[:8]


def test_cettime_between_march_and_october_applies_gmt_plus_dst_offset() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(value=True))
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600 + 3600))[:8]


def test_cettime_after_october_boundary_applies_gmt_offset_only() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(value=True))
    fixed_now = _mid_month_now(12)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600))[:8]


def test_cettime_zero_offsets_are_accepted_not_rejected() -> None:
    client = _client_with_offsets(0, 0)
    run(client._set_synced(value=True))
    fixed_now = _mid_month_now(1)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now))[:8]


def test_cettime_negative_offsets_are_accepted_not_rejected() -> None:
    client = _client_with_offsets(-3600, -3600)
    run(client._set_synced(value=True))
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now - 3600 - 3600))[:8]


def test_cettime_mktime_or_gmtime_failure_returns_none_not_raise() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(value=True))
    result = _run_cettime_with_fixed_now(
        client, _mid_month_now(1), raise_exc=OverflowError("past rp2's ~2037 range"),
    )
    assert result is None


class _ShortGmtimeTime:
    # Real rp2 time.gmtime() always returns exactly 8 elements - cettime()'s own `len(cet) == 8`
    # check can't actually fail through any real gmtime() call, so this fakes a malformed result
    # directly, the same technique _FixedNowTime above uses for its own fixed-now/raising variants.
    def __init__(self, fixed_now: int) -> None:
        self._fixed_now = fixed_now

    def gmtime(self, *a: int) -> "tuple[int, ...]":
        return tuple(time.gmtime(*a))[:7]  # one short of the real 8-element shape

    def mktime(self, t: "tuple[int, ...]") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return self._fixed_now


def test_cettime_returns_none_when_gmtime_result_has_the_wrong_length() -> None:
    client = _client_with_offsets(3600, 3600)
    run(client._set_synced(value=True))
    original_time = ntpmod.time
    ntpmod.time = _ShortGmtimeTime(_mid_month_now(1))  # type: ignore[assignment]
    try:
        result = run(client.cettime())
    finally:
        ntpmod.time = original_time
    assert result is None


# ---------------------------------------------------------------------------
# _sync_age_loop() - the synced-clock second counter
# ---------------------------------------------------------------------------


def test_sync_age_follows_measured_time_while_synced() -> None:
    with _DrivenTime() as clock:
        client = make_client()

        async def scenario() -> "int | None":
            await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
            task = asyncio.create_task(client._sync_age_loop())
            await asyncio.sleep(0)
            for _ in range(3):
                clock.advance(1000)
                await _tick(client._time_counter_trigger_event)
            value = await client.get_last_ntp_sync()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return value

        try:
            assert run(scenario()) == 3
        finally:
            asy_base_classes.set_utc_valid(valid=False)


def test_a_late_wake_advances_the_age_by_the_measured_seconds() -> None:
    # One wake-up 2.5 s after the sync: the age is the 2 whole seconds that passed, not one per
    # wake-up, so a dropped or late soft-Timer callback costs latency only (SPECIFICATION.md C.9).
    with _DrivenTime() as clock:
        client = make_client()

        async def scenario() -> "int | None":
            await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
            task = asyncio.create_task(client._sync_age_loop())
            await asyncio.sleep(0)
            clock.advance(2500)
            await _tick(client._time_counter_trigger_event)
            value = await client.get_last_ntp_sync()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return value

        try:
            assert run(scenario()) == 2
        finally:
            asy_base_classes.set_utc_valid(valid=False)


def test_time_counter_resets_to_none_while_not_synced() -> None:
    client = make_client()

    async def scenario() -> "int | None":
        task = asyncio.create_task(client._sync_age_loop())
        await _tick(client._time_counter_trigger_event, 2)
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
    client = make_client(network_available_locked=lambda: False)
    reached = [False]

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        reached[0] = True
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert reached[0] is False


def test_run_sync_attempt_network_available_raising_is_treated_as_unavailable() -> None:
    def raiser() -> bool:
        raise RuntimeError("wlan.status() exploded")

    client = make_client(network_available_locked=raiser)
    reached = [False]

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        reached[0] = True
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))  # must not raise
    assert reached[0] is False


def test_run_sync_attempt_network_available_raising_persists_a_callback_error() -> None:
    def raiser() -> bool:
        raise RuntimeError("wlan.status() exploded")

    client = make_client(network_available_locked=raiser)
    run(client._run_ntp_sync_attempt(None))
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "CALLBACK")
    assert _last_err(counter, "ErrType") == "E"


def test_run_sync_attempt_missing_config_marks_not_synced_and_returns() -> None:
    client = make_client()
    run(client._set_synced(value=True))

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert run(client.ntp_issynced()) is False


def test_run_sync_attempt_resolve_failure_calls_handle_failure() -> None:
    client = make_client()
    handled = [False]

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "str | None") -> "tuple[str, int] | None":
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
    # the actual value only ever comes from _sync_loop()'s _safe_get_dns_server() call, read
    # before wifi_mode_lock is acquired (see that method's own comment/BACKLOG.md).
    client = make_client()
    received: list[Any] = []

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, dns_server: "str | None") -> "tuple[str, int] | None":
        received.append(dns_server)
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    run(client._run_ntp_sync_attempt("203.0.113.53"))
    assert received == ["203.0.113.53"]


def test_run_sync_attempt_fetch_failure_calls_handle_failure() -> None:
    client = make_client()
    handled = [False]

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "str | None") -> "tuple[str, int] | None":
        return ("1.2.3.4", 123)

    async def fake_fetch(_addr: "tuple[str, int]") -> "bytes | None":
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

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "str | None") -> "tuple[str, int] | None":
        return ("1.2.3.4", 123)

    async def fake_fetch(_addr: "tuple[str, int]") -> "bytes | None":
        return b"garbage"

    async def fake_parse(_msg: bytes, _off: int) -> "tuple[int, ...] | None":
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

    async def fake_get_cfg() -> "tuple[list[str], list[int]] | None":
        return (["pool.ntp.org"], [0])

    async def fake_resolve(_host: str, _dns_server: "str | None") -> "tuple[str, int] | None":
        return ("1.2.3.4", 123)

    async def fake_fetch(_addr: "tuple[str, int]") -> "bytes | None":
        return b"x" * 48

    async def fake_parse(_msg: bytes, _off: int) -> "tuple[int, ...] | None":
        return parsed_tm

    async def fake_handle_success(tm: "tuple[int, ...]") -> None:
        handled_with.append(tm)

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    client._fetch_ntp_reply = fake_fetch  # type: ignore[assignment, method-assign]
    client._parse_ntp_reply = fake_parse  # type: ignore[assignment, method-assign]
    client._handle_ntp_sync_success = fake_handle_success  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert handled_with == [parsed_tm]


# ---------------------------------------------------------------------------
# _sync_loop() - the task-supervisor entry point: proves the trigger -> lock -> attempt ->
# lock-release cycle works, and that the lock is released by `async with` even if the attempt raises.
# ---------------------------------------------------------------------------


def test_asy_ntp_time_runs_one_attempt_per_trigger_and_releases_the_wifi_lock() -> None:
    client = make_client()
    attempts = [0]

    async def fake_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        attempts[0] += 1
        return None, True

    client._run_ntp_sync_attempt = fake_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> int:
        task = asyncio.create_task(client._sync_loop())
        client._ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not client.wifi_mode_lock.locked()
        client._ntp_sync_trigger_event.set()
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

    async def raising_attempt(_dns_server: "str | None") -> "NoReturn":
        raise RuntimeError("simulated bug downstream")

    client._run_ntp_sync_attempt = raising_attempt  # type: ignore[assignment, method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(client._sync_loop())
        client._ntp_sync_trigger_event.set()
        # the uncaught RuntimeError kills this task - matches every other supervised task in this
        # codebase, which relies on the outer task-supervisor to notice and restart it, not a
        # catch-all here; retrieved explicitly so asyncio doesn't warn about it going unretrieved.
        try:
            await asyncio.wait_for(task, _EVENT_WAIT_S)
            raised = False
        except RuntimeError:
            raised = True
        return raised and not client.wifi_mode_lock.locked()

    assert run(scenario())


def test_setup_initialises_the_logger_before_any_task() -> None:
    # The boot batch's setup() readies the logger; the sync task never sets it up itself (SPECIFICATION.md A.7).
    client = NTPClient(asyncio.Lock(), lambda: True, lambda: None, _timing(), cfg_path=_tmp_cfg_dir())
    before = client.pr.initialized
    run(client.setup())
    assert (before, client.pr.initialized) == (False, True)
    unset = NTPClient(asyncio.Lock(), lambda: True, lambda: None, _timing(), cfg_path=_tmp_cfg_dir())

    async def scenario() -> bool:
        task = asyncio.create_task(unset._sync_loop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        initialized = unset.pr.initialized
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return initialized

    assert run(scenario()) is False


async def _drive_attempts(client: NTPClient, cycles: int) -> bool:
    # Fires `cycles` sync triggers through the real _sync_loop() loop; True = task still running.
    task = asyncio.create_task(client._sync_loop())
    for _ in range(cycles):
        client._ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
    still_running = not task.done()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    return still_running


def test_asy_ntp_time_never_gives_up_on_a_persistently_failing_server() -> None:
    # An unreachable server is routine for this task (Part C.7.2): a restart re-initialises nothing,
    # and each one costs the supervisor's reboot budget. So far past any old streak, still running.
    client = make_client()

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        return None, True  # network was available, but the attempt itself still failed

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 50)) is True
    assert client._err_cnt_internal == 0  # no streak is kept at all
    assert run(client.get_error_counter())["NTP"]["ErrCount"] == 0  # no give-up entry, nor any other


def test_asy_ntp_time_failed_unsynced_attempts_double_the_retry_interval_up_to_its_cap() -> None:
    client = make_client(timing=_timing(retry_s=10, retry_max_s=70))
    seen: list[int] = []

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        seen.append(client._retry_wait_s)
        return None, True

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 6)) is True
    assert seen == [10, 20, 40, 70, 70, 70]


def test_asy_ntp_time_network_unavailable_cycles_leave_the_retry_interval_alone() -> None:
    # A skipped attempt says nothing about the server, so the next one must come promptly.
    client = make_client(timing=_timing(retry_s=10, retry_max_s=600))

    async def unavailable_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        return None, False

    client._run_ntp_sync_attempt = unavailable_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 10)) is True
    assert client._retry_wait_s == 10


def test_asy_ntp_time_failures_while_synced_leave_the_unsynced_retry_interval_alone() -> None:
    # A synced device's failed resync is _handle_ntp_sync_failure()'s retry loop's business; the
    # backoff starts only once the sync has actually gone stale.
    client = make_client(timing=_timing(retry_s=10, retry_max_s=600))

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        await client._set_synced(value=True)
        return None, True

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 5)) is True
    assert client._retry_wait_s == 10


def test_a_successful_sync_resets_the_backoff() -> None:
    client = make_client(timing=_timing(retry_s=10, retry_max_s=600))
    client._retry_wait_s, client._unsynced_wait_s = 320, 30
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert (client._retry_wait_s, client._unsynced_wait_s) == (10, 0)


def test_ntp_force_sync_resets_the_backoff() -> None:
    # An operator's resync (a PUT of NTPHost) must run now, not after a ten-minute backoff step.
    client = make_client(timing=_timing(retry_s=10, retry_max_s=600))
    client._retry_wait_s, client._unsynced_wait_s = 600, 50
    run(client.ntp_force_sync())
    assert (client._retry_wait_s, client._unsynced_wait_s) == (10, 0)


def test_constructor_clamps_the_backoff_pair_to_the_check_tick_and_to_each_other() -> None:
    client = make_client(timing=_timing(retry_s=3, retry_max_s=5))
    assert (client._retry_s, client._retry_max_s, client._retry_wait_s) == (10, 10, 10)
    client = make_client(timing=_timing(retry_s=40, retry_max_s=20))
    assert (client._retry_s, client._retry_max_s) == (40, 40)


def test_asy_ntp_time_alternating_failure_codes_spend_a_slot_each_and_count_every_one() -> None:
    # The central newest-entry rule (C.7.1) collapses only a repeat of the newest code: alternation spends a slot each.
    client = make_client()
    codes = [code("E", "NTP_DNS"), code("E", "NTP_NO_REPLY")] * 2 + [code("E", "NTP_DNS")]
    expected = list(codes)

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        await client.pr.err_s("failed", errno=codes.pop(0))
        return None, True

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 5)) is True
    assert _slots(client) == (5, expected)


def test_a_recurring_code_after_a_success_keeps_one_slot() -> None:
    client = make_client()
    no_reply, unsync = code("E", "NTP_NO_REPLY"), code("W", "NTP_UNSYNC_REPLY")

    async def scenario() -> None:
        await client.pr.err_s("no reply", errno=no_reply)
        await client.pr.err_s("no reply", errno=no_reply)
        await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
        await client.pr.err_s("no reply", errno=no_reply)
        await client.pr.wrn_s("kiss of death", wrnno=unsync)
        await client.pr.wrn_s("kiss of death", wrnno=unsync)

    run(scenario())
    log = run(client.get_error_counter())["NTP"]
    assert log["ErrCount"] == 5
    assert log["ErrNum"][-2:] == [no_reply, unsync]
    assert log["ErrType"][-2:] == ["E", "W"]


def test_asy_ntp_time_keeps_running_across_alternating_failure_and_success() -> None:
    client = make_client()
    toggle = [True]

    async def alternating_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        if toggle[0]:
            toggle[0] = False
            return None, True  # failure
        toggle[0] = True
        return (2026, 1, 1, 0, 0, 0, 0, 0), True  # success

    client._run_ntp_sync_attempt = alternating_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 20)) is True


# ===========================================================================
# Integration tests: the real network path, driving the whole _sync_loop() task through
# cfgmgr -> _resolve_ntp_server -> UDPSocket -> real UDP loopback -> a staged real NTP server,
# proving how a genuine fault or success propagates up through the public getters.
# ===========================================================================


class _RedirectNtpNetworking:
    # Two Unix-port-only workarounds, needed only when driving the FULL _sync_loop() task end to
    # end. They must NOT be applied where a test calls _fetch_ntp_reply() with an already-resolved
    # addr, since indexing into an already-opaque object would itself break.
    #
    # (1) _resolve_ntp_server() always returns the real NTP port 123, and binding a test server
    #     there needs root/CAP_NET_BIND_SERVICE, which CI runners lack (bind() raises EACCES).
    #     Redirected to a real, already-bound ephemeral port instead.
    #
    # (2) _resolve_ntp_server() returns a plain (str, int) tuple - correct for real rp2 hardware -
    #     which this Unix-port build's connect() rejects (micropython/micropython#6924), so
    #     UDPSocket is wrapped to pre-resolve it, like test_asy_dns_client.py's own wrapper.
    def __init__(self, port: int) -> None:
        self._port = port

    def __enter__(self) -> "Self":
        self._original_port = ntpmod._NTP_UDP_PORT
        self._original_socket_cls = ntpmod.UDPSocket
        ntpmod._NTP_UDP_PORT = self._port
        real_cls = self._original_socket_cls

        class _Resolving:
            def __init__(self, addr: "tuple[str, int]", mode: str = "client", conn_tries: int = 1) -> None:
                resolved = socket.getaddrinfo(addr[0], addr[1])[0][-1]
                self._real = real_cls(resolved, mode=mode, conn_tries=conn_tries)  # type: ignore[arg-type]

            def __getattr__(self, name: str) -> object:
                return getattr(self._real, name)

        ntpmod.UDPSocket = _Resolving  # type: ignore[assignment, misc]
        return self

    def __exit__(self, *exc_info: object) -> None:
        ntpmod._NTP_UDP_PORT = self._original_port
        ntpmod.UDPSocket = self._original_socket_cls  # type: ignore[misc]


class FakeNtpServer:
    # A genuine independent UDP endpoint (a real socket.socket(), not an UDPSocket), staged to
    # answer with a controlled reply or drop the request - the same "real peer, not a mock"
    # approach as test_asy_udp_socket.py's AdversarialPeer, on a free ephemeral port.
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
        for _ in range(_FAKE_SERVER_POLL_TRIES):
            ready = any(event & select.POLLIN for _fd, event in self.poller.ipoll(0))
            if ready:
                try:
                    _data, from_addr = self.sock.recvfrom(1024)
                except OSError:  # spurious wakeup/transient EAGAIN - keep polling instead of raising
                    await asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)
                    continue
                if reply is not None:
                    self.sock.sendto(reply, from_addr)
                return
            await asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)

    def close(self) -> None:
        self.sock.close()


def make_integration_client() -> NTPClient:
    json_text = '{"NTPHost": "127.0.0.1", "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 0, "DSTOffset": 0}'
    return make_client_with_json(json_text)


def test_integration_full_task_reaches_synced_state_on_a_real_successful_reply() -> None:
    client = make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "tuple[bool, int | None]":
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                task = asyncio.create_task(client._sync_loop())
                server_task = asyncio.create_task(server.serve_once(reply))
                client._ntp_sync_trigger_event.set()
                await asyncio.wait_for(server_task, 5)
                for _ in range(_SYNCED_POLL_TRIES):
                    if await client.ntp_issynced():
                        break
                    await asyncio.sleep_ms(_STATE_POLL_MS)
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
        task = asyncio.create_task(client._sync_loop())
        client._ntp_sync_trigger_event.set()
        await asyncio.sleep(_NO_ANSWER_WAIT_S)  # comfortably longer than the fetch timeout would need to fail once
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
                task = asyncio.create_task(client._sync_loop())
                server_task = asyncio.create_task(server.serve_once(garbage_reply))
                client._ntp_sync_trigger_event.set()
                await asyncio.wait_for(server_task, 5)
                await asyncio.sleep(_REPLY_PROCESS_S)
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
    # A real network fault propagated up and recovered from, but only meaningful once already
    # synced: _handle_ntp_sync_failure()'s one-shot retry timer is armed only when ntp_synced is
    # already True, a fresh client relying on the periodic retrigger covered above.

    # So this takes one real successful sync, forces a second attempt that gets dropped, and proves
    # the resulting retry timer genuinely reaches a real listening server on a later attempt.
    client = make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def _wait_synced(*, target: bool) -> None:
        for _ in range(_STATE_POLL_TRIES):
            if await client.ntp_issynced() == target:
                return
            await asyncio.sleep_ms(_STATE_POLL_MS)

    async def scenario() -> bool:
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                task = asyncio.create_task(client._sync_loop())
                client._ntp_sync_trigger_event.set()
                first_reply_task = asyncio.create_task(server.serve_once(reply))
                await asyncio.wait_for(first_reply_task, 5)
                await _wait_synced(target=True)
                assert await client.ntp_issynced() is True  # confirmed synced once via a real round trip

                await client.ntp_force_sync()  # trigger a second attempt
                await server.serve_once(None)  # drop it entirely
                for _ in range(_RETRY_ARMED_POLL_TRIES):  # wait for the real fetch timeout to elapse and arm a retry
                    if client._ntp_retry_timer.callback is not None:
                        break
                    await asyncio.sleep_ms(_STATE_POLL_MS)
                assert client._ntp_retry_timer.callback is not None  # retry genuinely armed this time

                client._ntp_retry_timer.trigger()  # fire the scheduled retry immediately, not after 15s
                second_reply_task = asyncio.create_task(server.serve_once(reply))
                await asyncio.wait_for(second_reply_task, 5)
                await _wait_synced(target=True)
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
    # get_cfg_schema() is the base-class-owned access path (see asy_base_classes.py) to the private schema.
    client = make_client()
    assert client.get_cfg_schema() == client._cfg_schema
    assert client.get_cfg_schema() == (_VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET)


def test_set_dict_cfg_works_out_of_the_box_with_zero_driver_changes() -> None:
    # Every NTP field is persist-only, and no asy_ntp_client.py source change was needed to gain
    # setter support: asy_base_classes.py's generic _set_dict_cfg() already covers the "persist,
    # nothing to push" case for free. This is exactly the abstraction the design meant to prove.
    client = make_client()
    results = run(client._set_dict_cfg({"NTPHost": "time.example.org", "NTPInterval": 6}, client.get_cfg_schema()))
    assert results == {"NTPHost": "Valid", "NTPInterval": "Valid"}
    stored = run(client.cfgmgr.get_dict(["NTPHost", "NTPInterval"]))
    assert stored == {"NTPHost": "time.example.org", "NTPInterval": 6}


def test_set_dict_cfg_invalid_field_reported_individually_others_still_apply() -> None:
    client = make_client()
    results = run(client._set_dict_cfg({"NTPInterval": 999, "GMTOffset": 7200}, client.get_cfg_schema()))
    assert results == {"NTPInterval": "Invalid", "GMTOffset": "Valid"}
    stored = run(client.cfgmgr.get_dict(["NTPInterval", "GMTOffset"]))
    assert stored == {"NTPInterval": 12, "GMTOffset": 7200}  # Interv_H untouched default, GMTOffset applied


def test_no_push_callbacks_are_registered_for_any_ntp_field() -> None:
    # Confirms the persist-only design explicitly, not just implicitly via the absence of a push:
    # every NTP field goes straight to cfgmgr with nothing live to update.
    client = make_client()
    assert client._push_callbacks == {}


def test_cfg_schema_matches_what_cfgmgr_was_built_with() -> None:
    # Regression check for the integration bug where a shared REST helper needed each module's own
    # schema to validate a write correctly - get_cfg_schema() gives an outside caller that schema,
    # without reaching into a private const.
    client = make_client()
    assert client.get_cfg_schema() == (_VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET)


def test_write_config_via_public_cfg_schema_round_trips_a_real_value() -> None:
    # Proves get_cfg_schema()'s schema is actually usable for a real write, not just structurally equal - the exact
    # call shape api_helpers.py's cmd_post_check() now makes.
    client = make_client()

    async def scenario() -> "tuple[bool, dict[str, int | float | str | bool | None] | None]":
        written, _ = await client.cfgmgr.write_config({"NTPHost": "time.example.org"})
        data = await client.cfgmgr.get_dict(["NTPHost"])
        return written, data

    written, data = run(scenario())
    assert written
    assert data == {"NTPHost": "time.example.org"}


# ---------------------------------------------------------------------------
# Part C.7.2: never give up, back off while unsynced, one ring slot per repeated code
# (the central newest-entry rule)
# ---------------------------------------------------------------------------


def test_backoff_defaults_are_ten_seconds_doubling_to_ten_minutes() -> None:
    client = NTPClient(asyncio.Lock(), lambda: True, lambda: None, NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _FETCH_TIMEOUT_MS, _RETRY_S, _RETRY_MAX_S), cfg_path=_tmp_cfg_dir())
    assert (client._retry_s, client._retry_max_s, client._retry_wait_s, client._unsynced_wait_s) == (_RETRY_S, _RETRY_MAX_S, _RETRY_S, 0)


def _twice_one_slot(client: NTPClient, make_call: "Callable[[], Coroutine[Any, Any, object]]") -> "tuple[int, list[int], list[str]]":
    # Runs one failure site twice; returns (ErrCount, the non-empty ring slots, their types).
    async def scenario() -> "ErrorLog":
        await make_call()
        await make_call()
        return await client.get_error_counter()

    entry = run(scenario())["NTP"]
    nums, types = entry["ErrNum"], entry["ErrType"]
    assert isinstance(nums, list) and isinstance(types, list)
    kept = [(n, t) for n, t in zip(nums, types) if t != "N"]  # noqa: B905 - MicroPython zip() rejects strict=
    return int(entry["ErrCount"]), [n for n, _ in kept], [t for _, t in kept]


def test_missing_config_failure_logs_in_both_layers_one_slot_each() -> None:
    client = make_invalid_cfg_client()  # the store logs its own CFG_PATH_IS_DIR at construction
    before = run(client.cfgmgr.get_error_counter())["CFGMGR_NTP"]["ErrCount"]
    assert _twice_one_slot(client, lambda: client._run_ntp_sync_attempt(None)) == (2, [code("E", "CFG_READ")], ["E"])
    store = run(client.cfgmgr.get_error_counter())["CFGMGR_NTP"]
    assert store["ErrCount"] - before == 4  # each attempt reads the store twice (host, then offset)
    kept = [store["ErrNum"][i] for i in range(len(store["ErrNum"])) if store["ErrType"][i] != "N"]
    assert kept[-1] == code("E", "CFG_NOT_VALID") and kept.count(code("E", "CFG_NOT_VALID")) == 1, kept


def test_dns_failure_is_counted_twice_but_persisted_once() -> None:
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = _RecordingResolver(None)  # type: ignore[assignment]
    try:
        client = make_client()
        assert _twice_one_slot(client, lambda: client._resolve_ntp_server("bogus.invalid", None)) == (2, [code("E", "NTP_DNS")], ["E"])
    finally:
        ntpmod.resolve_ipv4 = original


def test_invalid_server_address_is_counted_twice_but_persisted_once() -> None:
    client = make_client()
    assert _twice_one_slot(client, lambda: client._fetch_ntp_reply((12345, 80))) == (2, [code("E", "BAD_ARG")], ["E"])  # type: ignore[arg-type]


def test_no_reply_is_counted_twice_but_persisted_once() -> None:
    client = make_client(timing=_timing(fetch_timeout_ms=_NO_REPLY_FETCH_TIMEOUT_MS))
    addr = make_addr()
    assert _twice_one_slot(client, lambda: client._fetch_ntp_reply(addr)) == (2, [code("E", "NTP_NO_REPLY")], ["E"])


def test_implausible_time_is_counted_twice_but_persisted_once() -> None:
    client = make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=1, unix_seconds=1000)  # past 2100 in every era
    assert _twice_one_slot(client, lambda: client._parse_ntp_reply(msg, 0)) == (2, [code("E", "NTP_IMPLAUSIBLE")], ["E"])


def test_malformed_reply_is_counted_twice_but_persisted_once() -> None:
    client = make_client()
    assert _twice_one_slot(client, lambda: client._parse_ntp_reply(b"x", 0)) == (2, [code("E", "NTP_MALFORMED")], ["E"])


def test_kiss_of_death_warning_is_counted_twice_but_persisted_once() -> None:
    client = make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=0, unix_seconds=int(time.time()))
    assert _twice_one_slot(client, lambda: client._parse_ntp_reply(msg, 0)) == (2, [code("W", "NTP_UNSYNC_REPLY")], ["W"])


def test_an_error_and_a_warning_with_the_same_number_are_different_codes() -> None:
    # errno n and wrnno n mean different things; one must never suppress the other's slot.
    client = make_client()
    n = code("W", "NTP_UNSYNC_REPLY")

    async def scenario() -> "list[str]":
        await client.pr.err_s("an error numbered n", errno=n)
        await client.pr.wrn_s("a warning numbered n", wrnno=n)
        types = (await client.get_error_counter())["NTP"]["ErrType"]
        assert isinstance(types, list)
        return types[-2:]

    assert run(scenario()) == ["E", "W"]


def test_distinct_codes_each_keep_a_slot() -> None:
    # A changed verdict mid-outage is evidence, so no code may shadow another (C.7.1).
    client = make_client()
    errors = [code("E", name) for name in ("NTP_DNS", "NTP_IMPLAUSIBLE", "NTP_MALFORMED", "NTP_RETRIES", "NTP_NO_REPLY")]
    warning = code("W", "NTP_UNSYNC_REPLY")

    async def scenario() -> None:
        for errno in errors:
            await client.pr.err_s("failed", errno=errno)
        await client.pr.wrn_s("rejected", wrnno=warning)

    run(scenario())
    assert _slots(client) == (6, errors + [warning])


def test_backoff_restarts_from_the_first_interval_after_a_recovery() -> None:
    client = make_client(timing=_timing(retry_s=10, retry_max_s=600))
    outcomes = [None, None, (2026, 1, 1, 0, 0, 0, 0, 0), None, None]
    seen: list[int] = []

    async def scripted_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        seen.append(client._retry_wait_s)
        tm = outcomes.pop(0)
        if tm is None:
            return None, True
        await client._handle_ntp_sync_success(tm)
        await client._set_synced(value=False)  # the sync goes stale again, back onto the unsynced cadence
        return tm, True

    client._run_ntp_sync_attempt = scripted_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 5)) is True
    assert seen == [10, 20, 40, 10, 20]


def test_ntp_time_hours_counter_does_not_bank_synced_ticks_toward_the_unsynced_wait() -> None:
    # Ticks while synced belong to the resync interval; once the sync goes stale the first retry
    # waits a full backoff step rather than firing on credit saved up while synced.
    client = make_client()
    client._retry_wait_s = 30

    async def fired() -> bool:
        try:
            await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _FIRED_PROBE_S)
        except asyncio.TimeoutError:
            return False
        return True

    async def scenario() -> "list[bool]":
        await client._set_synced(value=True)
        task = asyncio.create_task(client._refresh_loop())
        await _tick(client._ntp_timer_trigger_event, 5)
        results = [await fired()]
        await client._set_synced(value=False)
        await _tick(client._ntp_timer_trigger_event, 2)
        results.append(await fired())
        await _tick(client._ntp_timer_trigger_event, 1)
        results.append(await fired())
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return results

    assert run(scenario()) == [False, False, True]


def test_integration_self_heals_after_an_outage_through_the_real_task_and_socket() -> None:
    # Three real requests go unanswered, then the server answers: the same task (never restarted)
    # syncs, the backoff drops back to its first step, and the outage left exactly one ring slot.
    client = make_integration_client()
    client._ntp_fetch_timeout_ms = _NO_REPLY_FETCH_TIMEOUT_MS
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "tuple[bool, bool, int, ErrorLog]":
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                task = asyncio.create_task(client._sync_loop())
                for answer in (None, None, None, reply):
                    served = asyncio.create_task(server.serve_once(answer))
                    client._ntp_sync_trigger_event.set()
                    await asyncio.wait_for(served, 5)
                    await asyncio.sleep_ms(_PAST_FETCH_TIMEOUT_MS)  # past the 100ms fetch timeout either way
                still_running = not task.done()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return still_running, await client.ntp_issynced(), client._retry_wait_s, await client.get_error_counter()
        finally:
            server.close()

    still_running, synced, wait_s, log = run(scenario())
    assert still_running is True
    assert synced is True
    assert wait_s == client._retry_s
    assert log["NTP"]["ErrCount"] == 3
    assert log["NTP"]["ErrNum"] == [0] * 9 + [code("E", "NTP_NO_REPLY")]


def test_integration_a_successful_exchange_persists_nothing() -> None:
    client = make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "ErrorLog":
        server = FakeNtpServer()
        try:
            with server.redirect_resolution():
                served = asyncio.create_task(server.serve_once(reply))
                assert await client._fetch_ntp_reply(("127.0.0.1", ntpmod._NTP_UDP_PORT)) is not None  # the redirected port
                await asyncio.wait_for(served, 5)
                return await client.get_error_counter()
        finally:
            server.close()

    assert run(scenario())["NTP"]["ErrCount"] == 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
