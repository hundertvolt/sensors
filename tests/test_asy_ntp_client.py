"""NTPClient: request and reply handling, plausibility, retries and their timer, the DNS fallback, the sync flag and age,
and the logged failures, against fake servers."""

import asyncio
import errno
import json
import os
import select
import socket
import struct
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

from _async_harness import cancel, cancel_all, run
from _cancel_sweep import assert_unlocked, cancel_at_each_await
from _error_codes import code
from _fake_time import DrivenTime, tick
from _fake_timer_arm import RaiseOnArm
from _fram_builders import make_fram_manager
from _ntp_frames import FakeNtpServer, make_ntp_reply
from _ntp_responder import NtpResponder
from _port_bands import PortAllocator
from _src_const import NTP_EPOCH_DELTA, src_int
from _src_schema import src_schema
from _ticks30 import Ticks30Time
from _tmp_scratch import TmpScratch
from _udp_port_redirect import redirect_udp_port
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from machine import RTC, Timer

import asy_base_classes
import asy_ntp_client as ntpmod
import asy_udp_socket
from asy_dns_client import DNS_FAILED, DNS_NOT_SENT, DNS_NXDOMAIN, DNS_RESOLVED
from asy_ntp_client import NTPClient, NtpTiming
from asy_print_log import DEFAULT_LOG, LogConfig, PrintLogHistoryStore

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Literal, NoReturn

    import asy_config_manager as cm
    from asy_ntp_client import GMTimeStruct
    from asy_print_log import ErrorLog

    _Seen = tuple[bool, int | None, int, tuple[int, ...] | None]  # Synced, LastSyncAge, the backoff step, the RTC reading


# The client's schema, read from source by the typed readers (tests/_src_const.py), in the constructor's order.
_VAL_NTP_HOST: "cm.ConfigSchema" = src_schema("src/asy_ntp_client.py", "_VAL_NTP_HOST")
_VAL_NTP_OFFSET: "cm.ConfigSchema" = src_schema("src/asy_ntp_client.py", "_VAL_NTP_OFFSET")
_VAL_NTP_INTERVAL: "cm.ConfigSchema" = src_schema("src/asy_ntp_client.py", "_VAL_NTP_INTERVAL")
_VAL_GMT_OFFSET: "cm.ConfigSchema" = src_schema("src/asy_ntp_client.py", "_VAL_GMT_OFFSET")
_VAL_DST_OFFSET: "cm.ConfigSchema" = src_schema("src/asy_ntp_client.py", "_VAL_DST_OFFSET")
_VAL_DNS_FALLBACK: "cm.ConfigSchema" = src_schema("src/asy_ntp_client.py", "_VAL_DNS_FALLBACK")
_SCHEMA = _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET + _VAL_DNS_FALLBACK


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("ntp")


# The generated module's NtpTiming values: the resolver's DNS bounds and the client's own backoff defaults, read from
# source; codegen's fetch timeout has no src/ constant (buildgen/codegen.py writes it), so its copy keeps the tag.
_DNS_TIMEOUT_MS: int = src_int("src/asy_dns_client.py", "_DNS_TIMEOUT_MS")
_DNS_TRIES: int = src_int("src/asy_dns_client.py", "_DNS_TRIES")
# @tunable ntp.fetch_timeout_ms = 5000
_FETCH_TIMEOUT_MS = 5000
_RETRY_S: int = src_int("src/asy_ntp_client.py", "_DEFAULT_RETRY_S")
_RETRY_MAX_S: int = src_int("src/asy_ntp_client.py", "_DEFAULT_RETRY_MAX_S")

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
# @tunable l1.asy_ntp_client_responder_poll_ms = 1
_RESPONDER_POLL_MS = 1  # the real sleep between those looks, in the receive-error responder
# @tunable l1.asy_ntp_client_fake_server_poll_tries = 1000
_FAKE_SERVER_POLL_TRIES = 1000
# @tunable l1.asy_ntp_client_synced_poll_tries = 50
_SYNCED_POLL_TRIES = 50
# @tunable l1.asy_ntp_client_state_poll_tries = 200
_STATE_POLL_TRIES = 200
# @tunable l1.asy_ntp_client_retry_armed_poll_tries = 300
_RETRY_ARMED_POLL_TRIES = 300
_FETCH_CANCEL_ROUNDS = 12  # the rounds after a fetch's deadline passes a cancel is tried at: the failure's whole handling
_END_ROUNDS = 20  # scheduler rounds a cancelled sync task gets to end in


_PORTS = PortAllocator("test_asy_ntp_client")  # this file's band (tests/_port_bands.py)
# A literal NTPHost, so an attempt resolves without a DNS query.
_INTEGRATION_CFG = '{"NTPHost": "127.0.0.1", "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 0, "DSTOffset": 0, "DNSFallback": ""}'


def _against_responder(client: NTPClient, responder: NtpResponder, modes: "list[str]") -> "list[_Seen]":
    # One forced attempt per mode through the real _sync_loop(), the responder serving beside it in that mode; a silent
    # attempt waits the short fetch timeout, a served one returns on its reply.
    finished = _counted(client)
    RTC().datetime(_RTC_UNSET)

    async def scenario() -> "list[_Seen]":
        seen: list[_Seen] = []
        with redirect_udp_port(ntpmod, 123, responder.port):
            tasks = [asyncio.create_task(responder.serve()), asyncio.create_task(client._sync_loop())]
            try:
                for mode in modes:
                    responder.mode = mode
                    client._ntp_fetch_timeout_ms = _NO_REPLY_FETCH_TIMEOUT_MS if mode == "silent" else _FETCH_TIMEOUT_MS
                    client._ntp_sync_trigger_event.set()
                    await _attempt_ended(finished)
                    data = await client.get_data()
                    seen.append((data.Synced, data.LastSyncAge, client._retry_wait_s, RTC().datetime()))
            finally:
                await cancel_all(tasks)
        return seen

    try:
        return run(scenario())
    finally:
        responder.close()
        asy_base_classes.set_utc_valid(valid=False)


async def _attempt_ended(finished: asyncio.Event) -> None:
    # An attempt ends within its two fetch timeouts, the write's and the read's.
    await asyncio.wait_for_ms(finished.wait(), 2 * _FETCH_TIMEOUT_MS)
    finished.clear()


def _client_with_offsets(gmt_offset: int, dst_offset: int) -> NTPClient:
    # Deliberately one single f-string, not a plain literal adjacent to an f-string: confirmed
    # directly that MicroPython mishandles the latter when the plain part contains a literal brace
    # (this JSON's opening "{"), raising a spurious KeyError on the plain part's own content.
    json_text = (
        f'{{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 12, '
        f'"GMTOffset": {gmt_offset}, "DSTOffset": {dst_offset}}}'
    )
    return _make_client_with_json(json_text)


def _counted(client: NTPClient) -> asyncio.Event:
    # The real attempt, signalling its end; _sync_loop() applies its backoff before it next yields, so a waiter the
    # signal wakes sees that too.
    finished = asyncio.Event()
    attempt = client._run_ntp_sync_attempt

    async def counted(dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        try:
            return await attempt(dns_server)
        finally:
            finished.set()

    client._run_ntp_sync_attempt = counted  # type: ignore[method-assign]
    return finished


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


async def _drive_refresh(client: NTPClient, clock: Ticks30Time, ticks: int, on_tick: "Callable[[int], Coroutine[object, object, None]] | None" = None) -> "list[tuple[int, bool]]":
    # One check tick per 10 s of measured time; returns each change of Synced as (seconds since the start, Synced).
    changes: list[tuple[int, bool]] = []
    for n in range(1, ticks + 1):
        clock.advance(_CHECK_INTERVAL_S * 1000)
        await tick(client._ntp_timer_trigger_event)
        if on_tick is not None:
            await on_tick(n * _CHECK_INTERVAL_S)
        synced = await client.ntp_issynced()
        if not changes or changes[-1][1] != synced:
            changes.append((n * _CHECK_INTERVAL_S, synced))
    return changes


def _fails_twice(mode: str) -> "tuple[list[_Seen], tuple[int, list[int]]]":
    # Two attempts against a failing responder: what each left, and the log's (ErrCount, used slots).
    client = _responder_client()
    return _against_responder(client, NtpResponder(_PORTS.next()), [mode, mode]), _slots(client)


def _fetch_with(client: NTPClient, script: "_SocketScript") -> "bytes | None":
    original = ntpmod.UDPSocket
    ntpmod.UDPSocket = script.make  # type: ignore[assignment, misc]
    try:
        return run(client._fetch_ntp_reply(("192.0.2.123", 123)))
    finally:
        ntpmod.UDPSocket = original  # type: ignore[misc]


def _hourly_client() -> NTPClient:
    return _make_client_with_json('{"NTPHost": "pool.ntp.org", "NTPInterval": 1, "DNSFallback": ""}')


def _last_err(counter: "ErrorLog", field: 'Literal["ErrNum", "ErrType"]') -> "int | str":
    value = counter["NTP"][field]  # ErrNum/ErrType are list-shaped once _error_check() has run once
    assert isinstance(value, list)
    return value[-1]


def _last_sunday_0100_utc(year: int, month: int) -> int:
    # The switch instant from the C library's own calendar (TZ=UTC), not from cettime()'s formula.
    weekday = time.gmtime(time.mktime((year, month, 31, 1, 0, 0, 0, 0, 0)))[6]  # 0 = Monday
    return time.mktime((year, month, 31 - (weekday + 1) % 7, 1, 0, 0, 0, 0, 0))


def _make_addr() -> "tuple[str, int]":
    # A plain tuple for UDPSocket (the shim resolves it on this build).
    return ("127.0.0.1", _PORTS.next())


def _make_client(
    wifi_mode_lock: "asyncio.Lock | None" = None,
    network_available_locked: "Callable[[], bool] | None" = None,
    get_dns_server: "Callable[[], str | None] | None" = None,
    timing: "NtpTiming | None" = None,
    log: LogConfig = DEFAULT_LOG,
    cfg_path: "str | None" = None,
    dns_fallback: "str | None" = "",
) -> NTPClient:
    def network_ok() -> bool:
        return True

    def no_dns_server() -> "str | None":
        return None

    if wifi_mode_lock is None:
        wifi_mode_lock = asyncio.Lock()
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    client = NTPClient(
        wifi_mode_lock,
        network_ok if network_available_locked is None else network_available_locked,
        no_dns_server if get_dns_server is None else get_dns_server,
        _timing() if timing is None else timing,
        cfg_path=cfg_path,
        log=log,
    )

    async def build() -> None:
        await client.setup()  # the boot batch's setup(): the logger, then the config manager
        if dns_fallback is not None:
            # No L1 client asks a public resolver: the fallback list is empty unless a test sets it.
            await client.cfgmgr.write_config({"DNSFallback": dns_fallback})
            await client.cfgmgr.flush_pending()

    run(build())
    return client


def _make_client_with_json(json_text: str) -> NTPClient:
    # The file's own content stands: a DNSFallback it omits reads as the schema default.
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(json_text)
    return _make_client(cfg_path=cfg_path, dns_fallback=None)


def _make_integration_client() -> NTPClient:
    return _make_client_with_json(_INTEGRATION_CFG)


def _make_invalid_cfg_client() -> NTPClient:
    # A directory where ConfigManager expects a plain file - its os.stat() 0x4000 (MP_S_IFDIR)
    # check rejects it and leaves self.valid False, the same "config manager itself is invalid"
    # state the old empty-schema route reproduced before this driver's schema became non-empty.
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_NTP.cfg")
    return _make_client(cfg_path=cfg_path, dns_fallback=None)


def _make_ntp_server() -> FakeNtpServer:
    # The shared loopback server (tests/_ntp_frames.py) on a fresh port; the product sends to port 123, which needs
    # root, so each test runs inside redirect_udp_port(ntpmod, 123, server.port).
    return FakeNtpServer(_PORTS.next(), poll_ms=_FAKE_SERVER_POLL_MS, poll_tries=_FAKE_SERVER_POLL_TRIES)


def _make_raw_ntp_reply(raw_s: int) -> bytes:
    # Same LI=0/Stratum=1 header as make_ntp_reply() above - a genuinely-synchronized-looking
    # server, so these era/plausibility-window tests aren't incidentally rejected by the separate
    # LI/Stratum check instead of exercising the era logic they're meant to test.
    header = b"\x1c\x01" + bytes(38)
    transmit = struct.pack("!I", raw_s & 0xFFFFFFFF) + bytes(4)
    msg = header + transmit
    assert len(msg) == 48
    return msg


def _mid_month_now(month: int) -> int:
    year = time.gmtime()[0]
    return time.mktime((year, month, 15, 12, 0, 0, 0, 0, 0))


async def _no_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
    return None, False


def _put(client: NTPClient, data: "dict[str, object]") -> "dict[str, str]":
    return run(client._set_dict_cfg(data, client.get_cfg_schema()))  # type: ignore[arg-type]


def _raw_sockaddr(addr: "tuple[str, int]") -> "tuple[str, int] | tuple[str, int, int, int]":
    # A plain socket.socket on this Unix build takes only the resolved form (SPECIFICATION.md F.7 row 1).
    return socket.getaddrinfo(addr[0], addr[1])[0][-1]


def _reply_with_li_and_stratum(leap_indicator: int, stratum: int, unix_seconds: int) -> bytes:
    ntp_seconds = (unix_seconds + NTP_EPOCH_DELTA) & 0xFFFFFFFF
    first_byte = (leap_indicator << 6) | 0b011100  # VN=3, Mode=4(server) in the low 6 bits
    header = bytes([first_byte, stratum]) + bytes(38)
    transmit = struct.pack("!I", ntp_seconds) + bytes(4)
    msg = header + transmit
    assert len(msg) == 48
    return msg


def _resolve_with(recorder: "_RecordingResolver", client: NTPClient, host: str, dns: "str | None", fallback: str) -> "tuple[str, int] | None":
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder
    try:
        return run(client._resolve_ntp_server(host, dns, fallback))
    finally:
        ntpmod.resolve_ipv4 = original


async def _respond_once(addr: "tuple[str, int]", reply: bytes, ready: asyncio.Event) -> None:
    # A real independent UDP endpoint answering one request with `reply`; `ready` is set once it listens.
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(_raw_sockaddr(addr))
    server.setblocking(False)
    poller = select.poll()
    poller.register(server, select.POLLIN)
    ready.set()
    for _ in range(_RESPONDER_POLL_TRIES):
        # ipoll(0) returns an always-truthy iterator: test the event flags (SPECIFICATION.md F.7 row 13).
        if any(event & select.POLLIN for _fd, event in poller.ipoll(0)):
            try:
                _data, from_addr = server.recvfrom(1024)
            except OSError:  # spurious wakeup/transient EAGAIN - keep polling instead of raising
                await asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)
                continue
            server.sendto(reply, from_addr)
            break
        await asyncio.sleep_ms(_FAKE_SERVER_POLL_MS)
    server.close()


def _responder_client(interval_h: int = 12) -> NTPClient:
    # The file's builder on the responder's address: an IPv4 literal (no lookup) and no fallback resolver.
    return _make_client_with_json(json.dumps({"NTPHost": "127.0.0.1", "NTPInterval": interval_h, "DNSFallback": ""}))


def _rtc_reading(unix_s: int) -> "tuple[int, ...]":
    # What RTC().datetime() reads after a set to unix_s: the getter's recomputed weekday, subseconds 0.
    tm = time.gmtime(unix_s)
    return (tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0)


def _run_cettime_with_fixed_now(client: NTPClient, fixed_now: int) -> "GMTimeStruct | None":
    original_time = ntpmod.time
    ntpmod.time = _FixedNowTime(fixed_now)  # type: ignore[assignment]
    try:
        with _ClockSet():
            return run(client.cettime())
    finally:
        ntpmod.time = original_time


async def _run_sync_task_briefly(client: NTPClient) -> "tuple[bool, ErrorLog]":
    # Starts _sync_loop(), wakes it once, and reports whether it ended by itself, with the client's log.
    task = asyncio.create_task(client._sync_loop())
    for _ in range(3):
        await asyncio.sleep(0)
    client._ntp_sync_trigger_event.set()
    for _ in range(3):
        await asyncio.sleep(0)
    ended = task.done()
    if ended:
        await task  # a clean return; a raise fails the test here
    else:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return ended, await client.get_error_counter()


def _serve_through(exc: OSError, times: int) -> "tuple[bytes | None, BaseException | None]":
    # One query to a FakeNtpServer whose receive raises `exc` `times` times: what the querier got and what serve_once() raised.
    server = FakeNtpServer(_PORTS.next(), poll_ms=_RESPONDER_POLL_MS, poll_tries=_RESPONDER_POLL_TRIES)
    server.sock = _RaisingRecvSocket(server.sock, exc, times)  # type: ignore[assignment]  # the stand-in socket
    querier = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    querier.setblocking(False)
    querier.sendto(b"query", _raw_sockaddr(("127.0.0.1", server.port)))
    try:
        run(server.serve_once(b"reply"))
        raised = None
    except OSError as e:
        raised = e
    finally:
        server.close()
    try:
        answer: bytes | None = querier.recv(64)
    except OSError:  # nothing came back
        answer = None
    querier.close()
    return answer, raised


def _slots(client: NTPClient) -> "tuple[int, list[int]]":
    # (ErrCount, the ring's used slots oldest first) - "N" marks an unused one.
    entry = run(client.get_error_counter())["NTP"]
    nums, types = entry["ErrNum"], entry["ErrType"]
    assert isinstance(nums, list) and isinstance(types, list)
    return int(entry["ErrCount"]), [nums[i] for i in range(len(nums)) if types[i] != "N"]


def _synced_due_at(phase_ms: int, latency_ms: int, cycles: int) -> "list[int]":
    # A synced hourly client, each resync succeeding: its check timer fires on its own phase, `phase_ms` off the loop's
    # start, and each await of a tick's handling takes `latency_ms`. Only the ticks around each boundary arrive (the
    # cadence reads elapsed time, so the rest change nothing): the measured seconds of each fire that triggered a resync.
    with _SteppedClock() as clock:
        client = _hourly_client()
        issynced = client.ntp_issynced

        async def slow_issynced() -> bool:
            clock.advance(latency_ms)
            return await issynced()

        client.ntp_issynced = slow_issynced  # type: ignore[method-assign]

        async def scenario() -> "list[int]":
            await client._handle_ntp_sync_success(_TM)
            task = asyncio.create_task(client._refresh_loop())
            await asyncio.sleep(0)  # the loop starts its cadence at 0 ms
            period = 3600 // _CHECK_INTERVAL_S
            due_at: list[int] = []
            for cycle in range(1, cycles + 1):
                for n in range(cycle * period - 2, cycle * period + 3):
                    fire_ms = phase_ms + n * _CHECK_INTERVAL_S * 1000
                    clock.advance(fire_ms - clock.now)  # the timer's phase, whatever the last tick's handling took
                    await tick(client._ntp_timer_trigger_event)
                    if client._ntp_sync_trigger_event.state:
                        client._ntp_sync_trigger_event.clear()
                        due_at.append(fire_ms // 1000)
                        await client._handle_ntp_sync_success(_TM)
            await cancel(task)
            return due_at

        try:
            return run(scenario())
        finally:
            asy_base_classes.set_utc_valid(valid=False)


def _timing(
    dns_timeout_ms: int = _DNS_TIMEOUT_MS,
    dns_tries: int = _DNS_TRIES,
    fetch_timeout_ms: int = _FETCH_TIMEOUT_MS,
    retry_s: int = _RETRY_S,
    retry_max_s: int = _RETRY_MAX_S,
) -> NtpTiming:
    return NtpTiming(dns_timeout_ms, dns_tries, fetch_timeout_ms, retry_s, retry_max_s)


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def _truncated(length: int) -> bytes:
    # A non-zero Stratum whenever the length reaches index 1, so these truncation-length tests are
    # rejected for being too short to reach the Transmit Timestamp, not incidentally for looking
    # like a Kiss-o'-Death reply - keeping this isolated from the separate LI/Stratum check.
    buf = bytearray(length)
    if length > 1:
        buf[1] = 1
    return bytes(buf)


def _twice_one_slot(client: NTPClient, make_call: "Callable[[], Coroutine[object, object, object]]") -> "tuple[int, list[int], list[str]]":
    # Runs one failure site twice; returns (ErrCount, the non-empty ring slots, their types).
    async def scenario() -> "ErrorLog":
        await make_call()
        await make_call()
        return await client.get_error_counter()

    entry = run(scenario())["NTP"]
    nums, types = entry["ErrNum"], entry["ErrType"]
    assert isinstance(nums, list) and isinstance(types, list)
    kept = [(n, t) for n, t in zip(nums, types) if t != "N"]
    return int(entry["ErrCount"]), [n for n, _ in kept], [t for _, t in kept]


# ---------------------------------------------------------------------------
# Construction: the client owns its config_NTP.cfg and schema (SensorReaderConfig).
# ---------------------------------------------------------------------------


def test_init_never_synced_before_first_task_run() -> None:
    client = _make_client()
    assert run(client.ntp_issynced()) is False
    assert run(client.get_last_ntp_sync()) is None


def test_init_creates_its_own_config_file_with_schema_defaults() -> None:
    cfg_path = _tmp_cfg_dir()
    client = _make_client(cfg_path=cfg_path)
    assert client.cfgmgr.valid is True
    values = run(client.cfgmgr.get_dict(["NTPHost", "NTPOffset", "NTPInterval", "GMTOffset", "DSTOffset", "DNSFallback"]))
    assert values == {
        "NTPHost": "pool.ntp.org",
        "NTPOffset": 0,
        "NTPInterval": 12,
        "GMTOffset": 3600,
        "DSTOffset": 3600,
        "DNSFallback": "",  # the builder's: no public resolver
    }


def test_config_persists_across_a_fresh_client_instance_pointed_at_the_same_path() -> None:
    # Proves config_NTP.cfg is genuinely read from disk at __init__, not just written once and
    # cached in-process - a second, independent client pointed at the same cfg_path must see the
    # same persisted values, not fall back to schema defaults.
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(_VALID_JSON)
    first = _make_client(cfg_path=cfg_path)
    second = _make_client(cfg_path=cfg_path)
    first_cfg = run(first._get_ntp_config())
    second_cfg = run(second._get_ntp_config())
    assert first_cfg is not None
    assert second_cfg is not None
    first_host, _first_fallback, _first_offs = first_cfg
    second_host, _second_fallback, _second_offs = second_cfg
    assert first_host == "time.example.org"
    assert second_host == "time.example.org"


def test_two_clients_with_different_cfg_paths_have_independent_configs() -> None:
    first = _make_client_with_json(_VALID_JSON)
    second = _make_client()  # fresh directory, defaults only
    first_cfg = run(first._get_ntp_config())
    second_cfg = run(second._get_ntp_config())
    assert first_cfg is not None
    assert second_cfg is not None
    first_host, _first_fallback, _first_offs = first_cfg
    second_host, _second_fallback, _second_offs = second_cfg
    assert first_host == "time.example.org"
    assert second_host == "pool.ntp.org"


def test_debug_level_propagates_to_the_inherited_pr_logger() -> None:
    print("(expected) debug=3 makes the fresh ConfigManager below log its normal first-use config-file creation")
    client = _make_client(log=LogConfig(None, 10, 3))
    assert client.pr.level == 3


def test_get_task_starters_returns_all_three_ntp_tasks() -> None:
    client = _make_client()
    assert client.get_task_starters() == [
        client.start_asy_sync,
        client.start_asy_refresh,
        client.start_asy_sync_age,
    ]


def test_get_timer_starters_returns_both_ntp_timers() -> None:
    client = _make_client()
    assert client.get_timer_starters() == [client.start_check_timer, client.start_sync_age_timer]


def test_start_asy_ntp_refresh_returns_a_real_task() -> None:
    client = _make_client()

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
    client = _make_client()

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


def test_fram_given_logs_into_the_fram_chunk() -> None:
    # The constructor forwards its log config: an entry the client logs lands in its FRAM chunk, where the same
    # client built anew over a fresh manager on that chip (a reboot) reads it back.
    manager, chip = make_fram_manager()
    assert run(manager.setup()) is True  # the boot batch sets the manager up before any chunk is written
    client = _make_client(log=LogConfig(manager, 10, None))
    assert isinstance(client.pr, PrintLogHistoryStore)
    run(client.pr.err_s("probe", errno=code("E", "CALLBACK")))
    rebooted, _ = make_fram_manager(chip=chip)
    assert run(rebooted.setup()) is True
    reread = _make_client(log=LogConfig(rebooted, 10, None))
    entry = run(reread.pr.get_log())["NTP"]
    assert entry["ErrCount"] == 1
    assert _last_err({"NTP": entry}, "ErrNum") == code("E", "CALLBACK")


# ---------------------------------------------------------------------------
# get_dict_cfg / get_data / get_dict_data / get_error_counter - the base-class getter quartet
# (SPECIFICATION.md Part C.4.2).
# ---------------------------------------------------------------------------


def test_get_dict_cfg_returns_schema_defaults_wrapped_in_ntp_key() -> None:
    client = _make_client()
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTPHost": "pool.ntp.org",
            "NTPOffset": 0,
            "NTPInterval": 12,
            "GMTOffset": 3600,
            "DSTOffset": 3600,
            "DNSFallback": "",
        },
    }


def test_get_dict_cfg_reflects_a_customized_on_disk_config() -> None:
    client = _make_client_with_json(_VALID_JSON)
    result = run(client.get_dict_cfg())
    assert result == {
        "NTP": {
            "NTPHost": "time.example.org",
            "NTPOffset": 5,
            "NTPInterval": 6,
            "GMTOffset": 7200,
            "DSTOffset": 3600,
            "DNSFallback": "8.8.8.8,1.1.1.1",  # the file omits it: the schema default shows
        },
    }


def test_get_dict_cfg_is_the_unavailable_marker_when_config_manager_is_invalid() -> None:
    client = _make_invalid_cfg_client()
    result = run(client.get_dict_cfg())
    assert result == {"NTP": {"error": "unavailable"}}


def test_get_data_and_get_dict_data_reflect_the_initial_never_synced_state() -> None:
    asy_base_classes.set_utc_valid(valid=False)  # another test's sync may have set the process-wide flag
    client = _make_client()
    data = run(client.get_data())
    assert data.Synced is False
    assert data.LastSyncAge is None
    assert data.TS is None  # no timestamp before the first sync of the boot
    dict_data = run(client.get_dict_data())
    assert dict_data == {"NTP": {"Synced": False, "LastSyncAge": None, "TS": None}}


def test_get_data_reflects_a_successful_sync() -> None:
    client = _make_client()
    try:
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        data = run(client.get_data())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert data.Synced is True
    assert data.LastSyncAge == 0
    assert data.TS is not None  # the sync itself marked the clock valid before stamping


def test_a_successful_sync_marks_the_utc_clock_valid() -> None:
    client = _make_client()
    try:
        asy_base_classes.set_utc_valid(valid=False)
        assert asy_base_classes.utc_now() is None
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        assert isinstance(asy_base_classes.utc_now(), int)
    finally:
        asy_base_classes.set_utc_valid(valid=False)


def test_get_dict_data_reflects_a_successful_sync() -> None:
    client = _make_client()
    try:
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        dict_data = run(client.get_dict_data())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert dict_data["NTP"]["TS"] is not None
    assert dict_data["NTP"]["Synced"] is True
    assert dict_data["NTP"]["LastSyncAge"] == 0


def test_get_error_counter_starts_empty_and_records_a_real_error() -> None:
    client = _make_client()
    counter = run(client.get_error_counter())
    assert counter["NTP"]["ErrCount"] == 0
    run(client.pr.err_s("boom", errno=1))
    counter = run(client.get_error_counter())
    assert counter["NTP"]["ErrCount"] == 1


def test_get_error_counter_counts_a_warning_too() -> None:
    # Full-dict equality (not indexing into the union-typed ErrNum/ErrType values) - same style
    # test_asy_print_log.py's own get_log() tests use; history_length defaults to 10 (_make_client()
    # doesn't override it), so 9 untouched "N"/0 slots precede the one real warning.
    client = _make_client()
    run(client.pr.wrn_s("careful", wrnno=1))
    counter = run(client.get_error_counter())
    assert counter == {"NTP": {"ErrCount": 1, "ErrNum": [0] * 9 + [1], "ErrType": ["N"] * 9 + ["W"]}}


def test_get_error_counter_records_multiple_entries_in_order() -> None:
    client = _make_client()
    run(client.pr.err_s("first error", errno=1))
    run(client.pr.wrn_s("first warning", wrnno=2))
    counter = run(client.get_error_counter())
    assert counter == {"NTP": {"ErrCount": 2, "ErrNum": [0] * 8 + [1, 2], "ErrType": ["N"] * 8 + ["E", "W"]}}


# The state helpers _set_synced()/_set_last_sync_age(): each does an unlocked get-then-set with no
# await between (see asy_ntp_client.py's comment on _set_synced()).
# ---------------------------------------------------------------------------


def test_set_synced_to_true_preserves_last_sync_age_and_ts() -> None:
    client = _make_client()
    run(client._set_last_sync_age(value=42))
    before = run(client.get_data())
    run(client._set_synced(value=True))
    after = run(client.get_data())
    assert after.Synced is True
    assert after.LastSyncAge == 42
    assert after.TS == before.TS  # _set_synced() never touches TS


def test_set_synced_to_false_preserves_last_sync_age() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    run(client._set_last_sync_age(value=7))
    run(client._set_synced(value=False))
    data = run(client.get_data())
    assert data.Synced is False
    assert data.LastSyncAge == 7


def test_set_last_sync_age_preserves_synced_flag_when_true() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    run(client._set_last_sync_age(value=99))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge == 99


def test_set_last_sync_age_to_none_preserves_synced_flag() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    run(client._set_last_sync_age(value=None))
    data = run(client.get_data())
    assert data.Synced is True
    assert data.LastSyncAge is None


def test_the_sync_age_publish_keeps_the_synced_flag() -> None:
    client = _make_client()

    async def scenario() -> "tuple[bool, int | None]":
        await client._set_synced(value=True)
        task = asyncio.create_task(client._sync_age_loop())
        await tick(client._time_counter_trigger_event)
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
    client = _make_client()
    assert client._check_armed is None  # not attempted yet
    client.start_check_timer()
    assert client._ntp_timer.mode == Timer.PERIODIC
    assert client._ntp_timer.period == _CHECK_INTERVAL_S * 1000
    assert client._check_armed is True


def test_start_ntp_timer_fires_the_trigger_event() -> None:
    client = _make_client()
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
    client = _make_client()
    print("(expected) simulating alarm-pool exhaustion - the following 'Could not start NTP timer' is intentional")
    with RaiseOnArm():
        client.start_check_timer()  # must not raise despite the timer failing to arm
    assert client._ntp_timer.period == -1  # never actually armed
    assert client._check_armed is False  # recorded for the sync task's retry


def test_start_ntp_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_check_timer()'s own
    # `except (OSError, MemoryError)`: a real alarm allocation can fail with MemoryError instead,
    # which is not an OSError subclass - same graceful degradation must hold either way.
    client = _make_client()
    print("(expected) simulating an allocation failure - the following 'Could not start NTP timer' is intentional")
    with RaiseOnArm(MemoryError):
        client.start_check_timer()  # must not raise despite the timer failing to arm
    assert client._ntp_timer.period == -1  # never actually armed
    assert client._check_armed is False


def test_stop_ntp_timer_deinits() -> None:
    client = _make_client()
    client.start_check_timer()
    client.stop_check_timer()
    assert client._ntp_timer.deinit_called is True


def test_start_counter_timer_arms_periodic_1s() -> None:
    client = _make_client()
    assert client._tick_armed is None
    client.start_sync_age_timer()
    assert client._counter_timer.mode == Timer.PERIODIC
    assert client._counter_timer.period == 1000
    assert client._tick_armed is True


def test_start_counter_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = _make_client()
    with RaiseOnArm():
        client.start_sync_age_timer()
    assert client._counter_timer.period == -1
    assert client._tick_armed is False


def test_start_counter_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_sync_age_timer()'s own
    # `except (OSError, MemoryError)`.
    client = _make_client()
    with RaiseOnArm(MemoryError):
        client.start_sync_age_timer()
    assert client._counter_timer.period == -1
    assert client._tick_armed is False


def test_stop_counter_timer_deinits() -> None:
    client = _make_client()
    client.start_sync_age_timer()
    client.stop_sync_age_timer()
    assert client._counter_timer.deinit_called is True


def test_an_arm_failing_twice_ends_the_sync_task_with_one_timer_entry() -> None:
    # A dead check timer leaves no next sync trigger but a PUT: the task's retry fails too, so it ends for the supervisor.
    client = _make_client()
    client._run_ntp_sync_attempt = _no_attempt  # type: ignore[assignment, method-assign]
    with RaiseOnArm():
        client.start_check_timer()
        ended, log = run(_run_sync_task_briefly(client))
    assert ended is True
    assert client._check_armed is False
    assert log["NTP"]["ErrCount"] == 1  # the starter's own failure is a console line; the task's retry persists
    assert (log["NTP"]["ErrNum"][-1], log["NTP"]["ErrType"][-1]) == (code("E", "TIMER"), "E")


def test_a_sync_age_arm_failing_twice_ends_the_sync_task_with_one_timer_entry() -> None:
    client = _make_client()
    client._run_ntp_sync_attempt = _no_attempt  # type: ignore[assignment, method-assign]
    with RaiseOnArm(MemoryError):
        client.start_sync_age_timer()
        ended, log = run(_run_sync_task_briefly(client))
    assert ended is True
    assert client._tick_armed is False
    assert log["NTP"]["ErrCount"] == 1
    assert log["NTP"]["ErrNum"][-1] == code("E", "TIMER")


def test_a_restarted_sync_task_rearms_the_check_timer() -> None:
    client = _make_client()
    client._run_ntp_sync_attempt = _no_attempt  # type: ignore[assignment, method-assign]
    with RaiseOnArm():
        client.start_check_timer()
    assert client._check_armed is False
    ended, log = run(_run_sync_task_briefly(client))  # the arm now succeeds
    assert ended is False
    assert (client._ntp_timer.period, client._ntp_timer.mode, client._check_armed) == (_CHECK_INTERVAL_S * 1000, Timer.PERIODIC, True)
    assert client._tick_armed is None  # never attempted: nothing to retry
    assert log["NTP"]["ErrCount"] == 0


def test_a_restarted_sync_task_rearms_the_sync_age_timer() -> None:
    client = _make_client()
    client._run_ntp_sync_attempt = _no_attempt  # type: ignore[assignment, method-assign]
    with RaiseOnArm():
        client.start_sync_age_timer()
    ended, _log = run(_run_sync_task_briefly(client))
    assert ended is False
    assert (client._counter_timer.period, client._counter_timer.mode, client._tick_armed) == (1000, Timer.PERIODIC, True)


# ---------------------------------------------------------------------------
# ntp_issynced / ntp_force_sync / get_last_ntp_sync
# ---------------------------------------------------------------------------


def test_ntp_force_sync_resets_last_sync_retries_and_fires_the_sync_trigger() -> None:
    client = _make_client()

    async def scenario() -> bool:
        await client._set_synced(value=True)
        await client._set_last_sync_age(value=5)
        client._ntp_retries = 2
        await client.ntp_force_sync()
        assert not await client.ntp_issynced()  # a settings change clears Synced, as legacy did
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
    client = _make_client()
    client._ntp_retry_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)
    run(client.ntp_force_sync())
    assert client._ntp_retry_timer.deinit_called is True


def test_a_forced_resync_reports_unsynced_until_the_next_success() -> None:
    # Synced and LastSyncAge clear together, in one publish; the clock-set gate keeps local time answering.
    client = _make_client()

    async def scenario() -> "list[tuple[bool, int | None, bool]]":
        seen = []
        await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
        before = await client.get_data()
        seen.append((await client.ntp_issynced(), await client.get_last_ntp_sync(), await client.cettime() is not None))
        await client.ntp_force_sync()
        after = await client.get_data()
        assert after.TS == before.TS  # the stamp of the last publish stands
        seen.append((await client.ntp_issynced(), await client.get_last_ntp_sync(), await client.cettime() is not None))
        await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
        seen.append((await client.ntp_issynced(), await client.get_last_ntp_sync(), await client.cettime() is not None))
        return seen

    original_time = ntpmod.time
    ntpmod.time = _FixedNowTime(_mid_month_now(7))  # type: ignore[assignment]  # rp2's 8-field gmtime()
    try:
        assert run(scenario()) == [(True, 0, True), (False, None, True), (True, 0, True)]
    finally:
        ntpmod.time = original_time
        asy_base_classes.set_utc_valid(valid=False)


def test_the_clock_turns_valid_at_a_successful_sync() -> None:
    # ntp_clock_valid() is the gate UTCTime and the VOC backups read: unset until a sync this boot.
    client = _make_client()

    async def scenario() -> "list[bool]":
        seen = [await client.ntp_clock_valid()]
        await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
        seen.append(await client.ntp_clock_valid())
        return seen

    try:
        assert run(scenario()) == [False, True]
    finally:
        asy_base_classes.set_utc_valid(valid=False)


def test_a_settings_change_unsets_the_clock_until_the_next_sync() -> None:
    # ntp_force_sync() clears it together with Synced; the next success sets both again.
    client = _make_client()

    async def state() -> "tuple[bool, bool]":
        return await client.ntp_issynced(), await client.ntp_clock_valid()

    async def scenario() -> "list[tuple[bool, bool]]":
        await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
        seen = [await state()]
        await client.ntp_force_sync()
        seen.append(await state())
        await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
        seen.append(await state())
        return seen

    try:
        assert run(scenario()) == [(True, True), (False, False), (True, True)]
    finally:
        asy_base_classes.set_utc_valid(valid=False)


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
    client = _make_client_with_json(_VALID_JSON)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "time.example.org"
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 5


def test_get_ntp_config_returns_the_stored_fallback_list() -> None:
    client = _make_client_with_json('{"NTPHost": "time.example.org", "DNSFallback": "192.0.2.1,192.0.2.2"}')
    assert run(client._get_ntp_config()) == ("time.example.org", "192.0.2.1,192.0.2.2", 0)


def test_a_stored_host_that_is_not_a_host_name_uses_its_default() -> None:
    # A file written by hand or by an older firmware: within the schema's length, outside the hostName shape.
    client = _make_client_with_json('{"NTPHost": "-bad-.example", "DNSFallback": ""}')
    assert run(client._get_ntp_config()) == ("pool.ntp.org", "", 0)
    assert _slots(client) == (1, [code("W", "STORED_DEFAULT")])
    assert run(client.get_error_counter())["NTP"]["ErrType"][-1] == "W"


def test_a_stored_fallback_that_is_not_an_ipv4_list_uses_its_default() -> None:
    # Only a file written outside the PUT path can hold one; four servers would also break the lock-hold bound (C.8).
    for stored in ("8.8.8.8,x", "1.1.1.1,1.0.0.1,9.9.9.9,8.8.8.8"):
        client = _make_client_with_json('{"NTPHost": "time.example.org", "DNSFallback": "' + stored + '"}')
        assert run(client._get_ntp_config()) == ("time.example.org", "8.8.8.8,1.1.1.1", 0), stored
        assert _slots(client) == (1, [code("W", "STORED_DEFAULT")])


def test_get_ntp_config_single_invalid_field_falls_back_to_default_for_that_field_only() -> None:
    # NTPHost too short (min length 3) - falls back to its own default; NTPOffset stays real.
    json_text = '{"NTPHost": "ab", "NTPOffset": 5, "NTPInterval": 6, "GMTOffset": 7200, "DSTOffset": 3600}'
    client = _make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "pool.ntp.org"  # defaulted
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 5  # untouched


def test_get_ntp_config_multiple_invalid_fields_each_fall_back_independently() -> None:
    # NTPHost wrong type, NTPOffset out of range (both invalid at once) - each defaults on its own.
    json_text = '{"NTPHost": 12345, "NTPOffset": 999999, "NTPInterval": 6, "GMTOffset": 7200, "DSTOffset": 3600}'
    client = _make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "pool.ntp.org"
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 0


def test_get_ntp_config_all_fields_invalid_falls_back_to_every_default() -> None:
    json_text = '{"NTPHost": null, "NTPOffset": "bad", "NTPInterval": -5, "GMTOffset": "x", "DSTOffset": null}'
    client = _make_client_with_json(json_text)
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "pool.ntp.org"
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 0


def test_get_ntp_config_missing_file_uses_every_default() -> None:
    client = _make_client(dns_fallback=None)  # fresh directory - no config_NTP.cfg written, so every default applies
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "pool.ntp.org"
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 0


def test_get_ntp_config_non_dict_json_uses_every_default() -> None:
    client = _make_client_with_json("[1, 2, 3]")
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "pool.ntp.org"
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 0


def test_get_ntp_config_malformed_json_syntax_uses_every_default() -> None:
    client = _make_client_with_json("{not json at all")
    ntp_cfg = run(client._get_ntp_config())
    assert ntp_cfg is not None
    host, fallback, offset = ntp_cfg
    assert host == "pool.ntp.org"
    assert fallback == "8.8.8.8,1.1.1.1"  # the file omits it
    assert offset == 0


def test_get_ntp_config_returns_none_when_config_manager_itself_is_invalid() -> None:
    client = _make_invalid_cfg_client()
    assert client.cfgmgr.valid is False
    assert run(client._get_ntp_config()) is None


# ---------------------------------------------------------------------------
# _safe_get_dns_server - reads the get_dns_server callback (WifiService.get_dns_server_ip, its last
# snapshot's DHCP server) and wraps its errors; _sync_loop() calls it before taking wifi_mode_lock.
# ---------------------------------------------------------------------------


def test_safe_get_dns_server_returns_the_callbacks_value() -> None:
    client = _make_client(get_dns_server=lambda: "192.0.2.53")
    assert run(client._safe_get_dns_server()) == "192.0.2.53"


def test_safe_get_dns_server_passes_through_none() -> None:
    client = _make_client(get_dns_server=lambda: None)
    assert run(client._safe_get_dns_server()) is None


def test_safe_get_dns_server_callback_raising_returns_none() -> None:
    def raiser() -> "str | None":
        raise RuntimeError("get_dns_server_ip() exploded")

    client = _make_client(get_dns_server=raiser)
    assert run(client._safe_get_dns_server()) is None


def test_safe_get_dns_server_callback_raising_persists_a_callback_error() -> None:
    def raiser() -> "str | None":
        raise RuntimeError("get_dns_server_ip() exploded")

    client = _make_client(get_dns_server=raiser)
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
    client = _make_client()
    result = run(client._resolve_ntp_server("127.0.0.1", None, ""))
    assert result == ("127.0.0.1", 123)


class _RecordingResolver:
    # Stands in for asy_dns_client.resolve_ipv4() - proves _resolve_ntp_server()'s orchestration
    # (server order, tuple building, error handling, timeout_ms/tries/pr forwarding) independent of
    # resolve_ipv4()'s own network behavior, which tests/test_asy_dns_client.py covers exhaustively.
    def __init__(self, return_value: "str | None", cause: int = DNS_FAILED) -> None:
        self.calls: list[tuple[str, tuple[str, ...], int, int]] = []
        self.loggers: list[object] = []
        self.return_value = return_value
        self.cause = DNS_RESOLVED if return_value is not None else cause

    async def __call__(
        self, host: str, dns_servers: "tuple[str, ...]" = (), timeout_ms: int = 0, tries: int = 0, *, pr: object = None,
    ) -> "tuple[str | None, int]":
        self.calls.append((host, dns_servers, timeout_ms, tries))
        self.loggers.append(pr)
        return self.return_value, self.cause


def test_resolve_ntp_server_passes_the_given_dns_server_through() -> None:
    recorder = _RecordingResolver("9.9.9.9")
    client = _make_client()
    result = _resolve_with(recorder, client, "pool.ntp.org", "192.0.2.53", "8.8.8.8,1.1.1.1")
    assert result == ("9.9.9.9", 123)
    assert recorder.calls == [("pool.ntp.org", ("192.0.2.53", "8.8.8.8", "1.1.1.1"), 500, 1)]
    assert recorder.loggers == [client.pr]  # the resolver logs through this client's history


def test_resolve_ntp_server_none_dns_server_asks_only_the_fallback_list() -> None:
    recorder = _RecordingResolver("9.9.9.9")
    _resolve_with(recorder, _make_client(), "pool.ntp.org", None, "8.8.8.8,1.1.1.1")
    assert recorder.calls == [("pool.ntp.org", ("8.8.8.8", "1.1.1.1"), 500, 1)]


def test_resolve_ntp_server_asks_dhcp_first_then_the_fallback_list_in_order() -> None:
    recorder = _RecordingResolver("9.9.9.9")
    _resolve_with(recorder, _make_client(), "pool.ntp.org", "192.0.2.53", "198.51.100.7,192.0.2.1,203.0.113.9")
    assert recorder.calls == [("pool.ntp.org", ("192.0.2.53", "198.51.100.7", "192.0.2.1", "203.0.113.9"), 500, 1)]


def test_an_empty_fallback_asks_only_the_dhcp_server() -> None:
    recorder = _RecordingResolver("9.9.9.9")
    _resolve_with(recorder, _make_client(), "pool.ntp.org", "192.0.2.53", "")
    assert recorder.calls == [("pool.ntp.org", ("192.0.2.53",), 500, 1)]


def test_no_dhcp_server_and_an_empty_fallback_ask_nobody() -> None:
    recorder = _RecordingResolver(None)
    assert _resolve_with(recorder, _make_client(), "pool.ntp.org", None, "") is None
    assert recorder.calls == [("pool.ntp.org", (), 500, 1)]


def test_resolve_ntp_server_forwards_the_constructors_own_dns_timeout_and_tries() -> None:
    # Proves dns_timeout_ms/dns_tries are this instance's own configured values (see
    # asy_ntp_client.py's own constructor comment) reaching resolve_ipv4() unchanged - not
    # asy_dns_client.py's own standalone defaults, and not hardcoded here either.
    recorder = _RecordingResolver("9.9.9.9")
    _resolve_with(recorder, _make_client(timing=_timing(dns_timeout_ms=1234, dns_tries=3)), "pool.ntp.org", None, "")
    assert recorder.calls == [("pool.ntp.org", (), 1234, 3)]


def test_resolve_ntp_server_dns_failure_returns_none() -> None:
    assert _resolve_with(_RecordingResolver(None), _make_client(), "bogus.invalid", None, "") is None


def test_resolve_ntp_server_dns_failure_persists_an_error() -> None:
    client = _make_client()
    _resolve_with(_RecordingResolver(None), client, "bogus.invalid", None, "")
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "NTP_DNS")
    assert _last_err(counter, "ErrType") == "E"


def test_the_resolvers_cause_picks_the_persisted_code() -> None:
    # A query that never left the device and a name the server says does not exist each keep their own code; every
    # other failure keeps the generic one. One entry per failed resolution.
    for cause, name in ((DNS_NOT_SENT, "NTP_DNS_NOT_SENT"), (DNS_NXDOMAIN, "NTP_DNS_NXDOMAIN"), (DNS_FAILED, "NTP_DNS")):
        client = _make_client()
        assert _resolve_with(_RecordingResolver(None, cause), client, "bogus.invalid", "192.0.2.53", "") is None
        counter = run(client.get_error_counter())
        assert counter["NTP"]["ErrCount"] == 1, name
        assert _last_err(counter, "ErrNum") == code("E", name), name


# No real-network end-to-end test through _resolve_ntp_server() itself: resolve_ipv4()'s `port`
# has no override here, and binding a fake DNS peer to port 53 needs root and is
# environment-dependent, unlike every other loopback test in this suite.

# The seam is already fully characterized above (_RecordingResolver pins the exact arguments and
# return-value handling) and resolve_ipv4()'s real UDP behavior is covered by
# tests/test_asy_dns_client.py - together proving what a port-53 test would, without the fragility.


# ---------------------------------------------------------------------------
# _fetch_ntp_reply - its own write() and recvfrom() of one 48-byte NTP packet, the socket torn down
# in a finally whatever happens
# ---------------------------------------------------------------------------


class _FakeUDPSocket:
    # Stands in for asy_udp_socket.UDPSocket: records each call and answers as the script says, a
    # None-shaped sentinel for silence exactly as the real socket returns one.
    def __init__(self, script: "_SocketScript", addr: "tuple[str, int]", mode: str) -> None:
        self.script, self.addr, self.mode = script, addr, mode
        self.calls: list[tuple[str, int, int]] = []
        self.disconnected = False

    async def disconnect(self) -> bool:
        self.disconnected = True
        return self.script.teardown_ok

    async def recvfrom(self, buf: int, timeout_ms: int = -1) -> "tuple[bytes | None, tuple[str, int] | None]":
        self.calls.append(("recvfrom", buf, timeout_ms))
        if self.script.park is not None:
            self.script.parked.set()
            await self.script.park.wait()
        if self.script.gate_ms:
            await _SOCKET_CLOCK.asyncio.sleep_ms(self.script.gate_ms)
        return self.script.reply, (None if self.script.reply is None else self.addr)

    async def write(self, msg: "bytes | bytearray", timeout_ms: int = -1) -> "int | None":
        self.calls.append(("write", len(msg), timeout_ms))
        self.script.requests.append(msg)  # the object itself: the test checks which one was sent
        if self.script.gate_ms:
            await _SOCKET_CLOCK.asyncio.sleep_ms(self.script.gate_ms)
        return self.script.sent


class _Clocked:
    # A module stand-in for the fake socket's waits: a DrivenTime with sleeps replaces its `time` and `asyncio`.
    def __init__(self) -> None:
        self.time = time
        self.asyncio = asyncio


_SOCKET_CLOCK = _Clocked()  # the real modules, but inside a cancel sweep's block


class _SocketScript:
    # What every _FakeUDPSocket it makes answers; its make() replaces asy_ntp_client.UDPSocket. `gate_ms`: each send and
    # receive first waits that long on _SOCKET_CLOCK.
    def __init__(self, *, sent: "int | None" = 48, reply: "bytes | None" = None, teardown_ok: bool = True, park: bool = False, gate_ms: int = 0) -> None:
        self.sent, self.reply, self.teardown_ok = sent, reply, teardown_ok
        self.gate_ms = gate_ms
        self.park = asyncio.Event() if park else None
        self.parked = asyncio.Event()
        self.sockets: list[_FakeUDPSocket] = []
        self.requests: list[bytes | bytearray] = []

    def make(self, addr: "tuple[str, int]", mode: str = "client") -> _FakeUDPSocket:
        sock = _FakeUDPSocket(self, addr, mode)
        self.sockets.append(sock)
        return sock


def test_fetch_ntp_reply_forwards_the_constructors_own_fetch_timeout() -> None:
    client = _make_client(timing=_timing(fetch_timeout_ms=9999))
    script = _SocketScript()
    assert _fetch_with(client, script) is None
    (sock,) = script.sockets
    assert (sock.addr, sock.mode) == (("192.0.2.123", 123), "client")
    assert sock.calls == [("write", 48, 9999), ("recvfrom", 48, 9999)]  # one 48-byte request, a 48-byte receive
    assert script.requests == [b"\x1b" + bytes(47)]  # LI 0, VN 3, mode 3 (client)
    assert sock.disconnected is True


def test_every_fetch_sends_the_one_request_built_at_import() -> None:
    # The exchange allocates no request: each attempt sends the module's one prebuilt 48-byte packet.
    client = _make_client()
    script = _SocketScript()
    _fetch_with(client, script)
    _fetch_with(client, script)
    first, second = script.requests
    assert first is second
    assert first is ntpmod._NTP_REQUEST
    assert first == b"\x1b" + bytes(47)


def test_a_never_connected_socket_logs_not_sent_and_returns_before_the_fetch_timeout() -> None:
    # A request that never left is a local failure, not the server's silence: no wait for a reply.
    client = _make_client()
    script = _SocketScript(sent=None)
    assert _fetch_with(client, script) is None
    (sock,) = script.sockets
    assert sock.calls == [("write", 48, _FETCH_TIMEOUT_MS)]  # no recvfrom() at all
    assert sock.disconnected is True
    assert _slots(client) == (1, [code("E", "NTP_NOT_SENT")])


def test_a_failed_teardown_leaves_one_socket_teardown_warning() -> None:
    client = _make_client()
    reply = make_ntp_reply(int(time.time()))
    assert _fetch_with(client, _SocketScript(reply=reply, teardown_ok=False)) == reply
    assert _slots(client) == (1, [code("W", "SOCKET_TEARDOWN")])
    log = run(client.get_error_counter())["NTP"]
    assert log["ErrType"][-1] == "W"


def test_a_clean_exchange_logs_nothing() -> None:
    client = _make_client()
    reply = make_ntp_reply(int(time.time()))
    assert _fetch_with(client, _SocketScript(reply=reply)) == reply
    assert _slots(client) == (0, [])


def test_a_cancelled_fetch_still_disconnects() -> None:
    client = _make_client()
    script = _SocketScript(park=True)
    original = ntpmod.UDPSocket
    ntpmod.UDPSocket = script.make  # type: ignore[assignment, misc]

    async def scenario() -> bool:
        task = asyncio.create_task(client._fetch_ntp_reply(("192.0.2.123", 123)))
        try:
            await asyncio.wait_for(script.parked.wait(), _EVENT_WAIT_S)  # waiting in recvfrom()
        except asyncio.TimeoutError:
            pass  # never reached recvfrom(): awaiting the task below surfaces why
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True
        return False

    try:
        assert run(scenario()) is True  # the cancel is re-raised
    finally:
        ntpmod.UDPSocket = original  # type: ignore[misc]
    (sock,) = script.sockets
    assert sock.disconnected is True


def test_fetch_ntp_reply_no_server_listening_times_out_to_none() -> None:
    client = _make_client()
    addr = _make_addr()
    result = run(client._fetch_ntp_reply(addr))
    assert result is None
    assert _last_err(run(client.get_error_counter()), "ErrNum") == code("E", "NTP_NO_REPLY")  # a silent timeout used to persist nothing


def test_fetch_ntp_reply_real_round_trip_returns_the_exact_reply_bytes() -> None:
    client = _make_client()
    addr = _make_addr()
    reply = b"\x1c" + bytearray(47)

    async def scenario() -> "bytes | None":
        ready = asyncio.Event()
        responder_task = asyncio.create_task(_respond_once(addr, reply, ready))
        await ready.wait()  # listening before the client sends
        msg = await client._fetch_ntp_reply(addr)
        await responder_task
        return msg

    assert run(scenario()) == reply


def test_a_long_reply_is_read_as_its_48_byte_header() -> None:
    # A reply with extension fields or a MAC after its 48-byte header is cut to the header and parsed as before.
    client = _make_integration_client()
    header = make_ntp_reply(int(time.time()))
    port = _PORTS.next()

    async def scenario() -> "tuple[bool, bool]":
        ready = asyncio.Event()
        responder_task = asyncio.create_task(_respond_once(("127.0.0.1", port), header + bytes(range(42)), ready))
        await ready.wait()
        with redirect_udp_port(ntpmod, 123, port):
            tm, _network_ok = await client._run_ntp_sync_attempt(None)
        await responder_task
        return tm is not None, await client.ntp_issynced()

    try:
        assert run(scenario()) == (True, True)
    finally:
        asy_base_classes.set_utc_valid(valid=False)


# ---------------------------------------------------------------------------
# _parse_ntp_reply - NTP packet format per RFC 5905: 48-byte header, Transmit Timestamp at byte
# offset 40 (only the integer seconds half is read), 2208988800s being the 1900->1970 epoch delta.

# Byte 0's Leap Indicator and byte 1's Stratum are checked before the timestamp is trusted at all
# (LI=3 "unsynchronized" and Stratum=0 Kiss-o'-Death are rejected), so each reply builder at the top of the file
# sets Stratum=1 by default. _parse_ntp_reply() is async, hence the run() around every call.
# ---------------------------------------------------------------------------

def test_parse_ntp_reply_valid_packet_returns_gmtime_and_sets_the_rtc() -> None:
    client = _make_client()
    now = int(time.time())
    msg = make_ntp_reply(now)
    tm = run(client._parse_ntp_reply(msg, 0))
    assert tm is not None
    assert tm[0] >= 2024  # sanity bound: a real current-ish year, not the 2000 fake-RTC default
    rtc_datetime = RTC().datetime()
    assert rtc_datetime is not None  # only None-shaped when called as a setter with dt=None
    # rp2's getter recomputes the weekday (Monday 0, gmtime's own) and ignores the tm[6] + 1 the client writes
    # (ports/rp2/machine_rtc.c:85-96, v1.29.0).
    assert tuple(rtc_datetime) == (tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0)


def test_parse_ntp_reply_applies_the_ntp_offset_s_correction() -> None:
    client = _make_client()
    now = int(time.time())
    msg = make_ntp_reply(now)
    tm_no_offset = run(client._parse_ntp_reply(msg, 0))
    tm_with_offset = run(client._parse_ntp_reply(msg, 3600))
    assert tm_no_offset is not None and tm_with_offset is not None
    assert time.mktime(tm_with_offset) - time.mktime(tm_no_offset) == 3600


def test_parse_ntp_reply_truncated_packet_returns_none() -> None:
    client = _make_client()
    for length in (0, 10, 39, 43):  # all short of the 48-byte NTP header (RFC 5905 7.3)
        assert run(client._parse_ntp_reply(_truncated(length), 0)) is None
    assert _slots(client) == (4, [code("E", "NTP_MALFORMED")])


def test_parse_ntp_reply_zero_length_and_exact_boundary_lengths() -> None:
    # A reply that reaches the Transmit Timestamp but not the header's end is still short of the 48-byte header.
    client = _make_client()
    for length in (0, 44, 47):
        assert run(client._parse_ntp_reply(_truncated(length), 0)) is None, length
    assert _slots(client) == (3, [code("E", "NTP_MALFORMED")])
    assert run(client._parse_ntp_reply(make_ntp_reply(int(time.time())), 0)) is not None  # 48 bytes: read


def test_a_zero_transmit_timestamp_is_rejected() -> None:
    # RFC 5905 6: a zero timestamp is unset; the era step would otherwise carry it to 2036-02-07, inside the window.
    client = _make_client()
    msg = b"\x1c\x02" + bytes(46)  # 48 bytes, LI 0, stratum 2, bytes 40-43 zero
    RTC().datetime((2001, 2, 3, 4, 5, 6, 7, 0))
    before = RTC().datetime()
    assert run(client._parse_ntp_reply(msg, 0)) is None
    assert RTC().datetime() == before  # the RTC was not set
    assert _slots(client) == (1, [code("E", "NTP_MALFORMED")])


def test_parse_ntp_reply_decodes_arbitrary_bytes_as_their_transmit_timestamp() -> None:
    client = _make_client()
    garbage = bytes(range(48))  # a full 48 bytes, LI 0 and stratum 1, but not a real NTP reply at all
    # Bytes 40-43 = 0x28292A2B = 673786411 s since 1900, below the floor, so next era: Unix 2759764907.
    result = run(client._parse_ntp_reply(garbage, 0))
    assert result is not None
    assert tuple(result)[:8] == (2057, 6, 14, 17, 21, 47, 3, 165)  # a Thursday, day 165


# The plausibility window, read from source (tests/_src_const.py).
_FLOOR: int = src_int("src/asy_ntp_client.py", "_NTP_MIN_PLAUSIBLE_UNIX_TIME")
_CEILING: int = src_int("src/asy_ntp_client.py", "_NTP_MAX_PLAUSIBLE_UNIX_TIME")


def test_the_plausibility_ceiling_fits_the_device_clock() -> None:
    # The window's ceiling is below 2**32, so gmtime() of any reply time it lets through cannot overflow rp2's clock (Part F.1).
    assert _CEILING < 2**32


class _AllocFailingTime:
    def gmtime(self, *_a: int) -> "NoReturn":
        raise MemoryError("injected for the parse path")


def test_an_allocation_failure_while_parsing_returns_none() -> None:
    client = _make_client()
    msg = make_ntp_reply(int(time.time()))
    original_time = ntpmod.time
    ntpmod.time = _AllocFailingTime()  # type: ignore[assignment]  # deliberate monkeypatch
    try:
        result = run(client._parse_ntp_reply(msg, 0))
    finally:
        ntpmod.time = original_time
    assert result is None
    assert _slots(client) == (1, [code("E", "ALLOC")])


def test_parse_ntp_reply_rtc_set_failure_returns_none_not_raise() -> None:
    client = _make_client()
    msg = make_ntp_reply(int(time.time()))
    RTC.raise_exc = OSError("simulated RTC set failure")
    try:
        result = run(client._parse_ntp_reply(msg, 0))
    finally:
        RTC.raise_exc = None
    assert result is None


def test_parse_ntp_reply_era_rollover_wrapped_reply_reconstructs_the_real_future_date() -> None:
    # NTP's 32-bit seconds-since-1900 field wraps in 2036, unrelated to the device clock, which runs
    # to 2106 (Part F.1); a post-2036 server sends a small wrapped value. _parse_ntp_reply()
    # reinterprets a below-floor reading as the next NTP era (RFC 5905 7.3) and rechecks it.
    client = _make_client()
    target_unix = 2185978496  # 2039-04-09ish - past the ~2036 wrap, well within the plausible ceiling
    raw = (target_unix + NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(target_unix))


def test_parse_ntp_reply_rejects_a_timestamp_implausible_in_every_era() -> None:
    # A raw value implausible both read directly (era 0: ~1995, below the floor) and after the
    # one-shot era reinterpretation (era 1: ~2131, past the ceiling) - genuinely corrupt data, not
    # an ordinary rollover reply. This used to produce a bogus-but-accepted "successful sync".
    client = _make_client()
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(3000000000), 0))
    assert result is None


def test_parse_ntp_reply_accepts_exactly_at_the_floor_boundary() -> None:
    client = _make_client()
    raw = (_FLOOR + NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(_FLOOR))


def test_parse_ntp_reply_accepts_exactly_at_the_ceiling_boundary() -> None:
    client = _make_client()
    raw = (_CEILING + NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(_CEILING))


def test_parse_ntp_reply_rejects_just_past_the_ceiling_boundary() -> None:
    client = _make_client()
    raw = (_CEILING + 1 + NTP_EPOCH_DELTA) & 0xFFFFFFFF
    result = run(client._parse_ntp_reply(_make_raw_ntp_reply(raw), 0))
    assert result is None


def test_parse_ntp_reply_rejects_leap_indicator_unsynchronized() -> None:
    # RFC 5905's Leap Indicator = 3 ("clock unsynchronized") is an alarm condition: the server is
    # explicitly saying it is not a trustworthy time source, even though its Transmit Timestamp
    # here is a plausible current date that would pass every other check.
    client = _make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=3, stratum=1, unix_seconds=int(time.time()))
    assert run(client._parse_ntp_reply(msg, 0)) is None


def test_parse_ntp_reply_rejects_stratum_zero_kiss_of_death() -> None:
    # RFC 5905/4330: Stratum 0 means "unspecified or invalid", used for Kiss-o'-Death packets -
    # never a genuine time source whatever its Transmit Timestamp holds. A real KoD reply's
    # all-zero timestamp would otherwise land inside the plausibility window after era-reinterp.
    client = _make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=0, unix_seconds=int(time.time()))
    assert run(client._parse_ntp_reply(msg, 0)) is None


def test_parse_ntp_reply_accepts_a_normal_synchronized_reply_li_zero_stratum_one() -> None:
    # Companion to the two rejection tests above - proves the new LI/Stratum check doesn't reject
    # everything, only the two specific alarm/KoD conditions.
    client = _make_client()
    now = int(time.time())
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=1, unix_seconds=now)
    result = run(client._parse_ntp_reply(msg, 0))
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(now))


# ---------------------------------------------------------------------------
# _handle_ntp_sync_failure / _handle_ntp_sync_success - retry counting + timer arm/degrade
# ---------------------------------------------------------------------------


def test_handle_sync_failure_while_never_synced_does_not_arm_a_retry() -> None:
    client = _make_client()  # never synced yet
    run(client._handle_ntp_sync_failure())
    assert client._ntp_retry_timer.period == -1  # never armed - _refresh_loop() retries instead


def test_handle_sync_failure_while_synced_arms_a_retry_and_increments_the_counter() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    run(client._handle_ntp_sync_failure())
    assert client._ntp_retries == 1
    assert client._ntp_retry_timer.mode == Timer.ONE_SHOT
    assert client._ntp_retry_timer.period == _RETRY_INTERVAL_S * 1000


def test_handle_sync_failure_retry_timer_fires_the_sync_trigger() -> None:
    client = _make_client()
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
    client = _make_client()
    run(client._set_synced(value=True))
    client._ntp_retries = _SYNC_RETRIES
    run(client._handle_ntp_sync_failure())
    assert client._ntp_retries == 0
    assert client._ntp_retry_timer.period == -1  # never (re)armed - past the retry budget


def test_handle_sync_failure_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    with RaiseOnArm():
        run(client._handle_ntp_sync_failure())  # must not raise despite the timer failing to arm
    assert client._ntp_retries == 0  # given up this cycle rather than left stuck


def test_handle_sync_failure_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of _handle_ntp_sync_failure()'s own
    # `except (OSError, MemoryError)` - the retry cycle is given up the same way either way, and the
    # same TIMER error is persisted (this site logs via the async err_s(), unlike the two starters above).
    client = _make_client()
    run(client._set_synced(value=True))
    with RaiseOnArm(MemoryError):
        run(client._handle_ntp_sync_failure())  # must not raise despite the timer failing to arm
    assert client._ntp_retries == 0  # given up this cycle rather than left stuck
    assert _last_err(run(client.get_error_counter()), "ErrNum") == code("E", "TIMER")


def test_repeated_retry_arm_failures_count_each_and_keep_one_slot() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    with RaiseOnArm():
        run(client._handle_ntp_sync_failure())
        run(client._handle_ntp_sync_failure())
    assert _slots(client) == (2, [code("E", "TIMER")])


def test_repeated_retry_exhaustion_counts_each_and_keep_one_slot() -> None:
    client = _make_client()
    run(client._set_synced(value=True))
    for _ in range(2):
        client._ntp_retries = _SYNC_RETRIES
        run(client._handle_ntp_sync_failure())
    assert _slots(client) == (2, [code("E", "NTP_RETRIES")])


def test_handle_sync_success_resets_retries_marks_synced_and_records_the_sync_time() -> None:
    client = _make_client()
    client._ntp_retries = 2
    try:
        run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
        data = run(client.get_data())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert client._ntp_retries == 0
    assert data.Synced is True
    assert data.LastSyncAge == 0
    assert data.TS is not None  # the success set the clock-set state before stamping


def test_handle_sync_success_deinits_a_pending_retry_timer() -> None:
    client = _make_client()
    client._ntp_retry_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert client._ntp_retry_timer.deinit_called is True


# ---------------------------------------------------------------------------
# _refresh_loop
# ---------------------------------------------------------------------------


class _SteppedClock(DrivenTime):
    # asy_base_classes' `time` for the block: the sync age counts measured ticks (SPECIFICATION.md G.2), so it follows
    # advance(), never the wake-ups; plus a wall clock the test can step (an RTC set, an offset change), as utc_now() reads it.
    def __init__(self) -> None:
        super().__init__(asy_base_classes)
        self.wall: int | None = None

    def __enter__(self) -> "_SteppedClock":
        super().__enter__()
        return self

    def gmtime(self, *a: int) -> "tuple[int, ...]":
        return time.gmtime(*a) if a or self.wall is None else time.gmtime(self.wall)

    def time(self) -> int:
        return int(time.time()) if self.wall is None else self.wall


def test_ntp_time_hours_counter_missing_config_falls_back_to_12h_default_without_raising() -> None:
    # Synced, with no config to read: the tick at 12 h of measured time is due, the one 10 s before it is not.
    with _SteppedClock() as clock:
        client = _make_invalid_cfg_client()

        async def fired() -> bool:
            try:
                await asyncio.wait_for(client._ntp_sync_trigger_event.wait(), _EVENT_WAIT_S)
            except asyncio.TimeoutError:
                return False
            return True

        async def scenario() -> "tuple[bool, bool]":
            await client._set_synced(value=True)
            task = asyncio.create_task(client._refresh_loop())
            await asyncio.sleep(0)  # the loop starts its cadence before the first tick's time passes
            await tick(client._ntp_timer_trigger_event, 1, clock, (12 * 3600 - _CHECK_INTERVAL_S) * 1000)
            early = await fired()
            await tick(client._ntp_timer_trigger_event, 1, clock, _CHECK_INTERVAL_S * 1000)
            due = await fired()
            await cancel(task)
            return early, due

        assert run(scenario()) == (False, True)
    assert _slots(client) == (2, [code("E", "CFG_READ")])  # each tick's missing-config entry, one slot for the repeat


def test_ntp_time_hours_counter_triggers_sync_immediately_when_not_yet_synced() -> None:
    client = _make_client()

    async def scenario() -> bool:
        task = asyncio.create_task(client._refresh_loop())
        await tick(client._ntp_timer_trigger_event, 1)
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
    client = _make_client()
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
            await tick(client._ntp_timer_trigger_event, ticks)
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
    client = _make_client_with_json(json_text)

    async def scenario() -> bool:
        await client._set_synced(value=True)
        task = asyncio.create_task(client._refresh_loop())
        await tick(client._ntp_timer_trigger_event, 1)  # one tick, well under 1h / 10s-per-tick
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
    # NTPInterval=1 -> 3600s of measured time, 360 check ticks of _NTP_CHECK_INTERV (10s), to reach the interval.
    json_text = '{"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 1, "GMTOffset": 3600, "DSTOffset": 3600}'
    with _SteppedClock() as clock:
        client = _make_client_with_json(json_text)

        async def scenario() -> bool:
            await client._set_synced(value=True)
            task = asyncio.create_task(client._refresh_loop())
            await asyncio.sleep(0)  # the loop starts its cadence before the first tick's time passes
            await tick(client._ntp_timer_trigger_event, 360, clock, _CHECK_INTERVAL_S * 1000)
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


_TM = (2026, 1, 1, 0, 0, 0, 0, 0)  # a parsed reply's time, for the success path
_STALE_AFTER_S = _ASYNC_INTERVALS * 3600  # NTPInterval 1 h


def test_refresh_marks_the_sync_stale_three_intervals_after_the_last_success() -> None:
    # Staleness clears only Synced: UTCTime and the VOC backups keep the clock this boot's sync set.
    with _SteppedClock() as clock:
        client = _hourly_client()

        async def scenario() -> "tuple[list[tuple[int, bool]], bool]":
            await client._handle_ntp_sync_success(_TM)
            task = asyncio.create_task(client._refresh_loop())
            seen = await _drive_refresh(client, clock, _STALE_AFTER_S // _CHECK_INTERVAL_S + 1)
            await cancel(task)
            return seen, await client.ntp_clock_valid()

        try:
            changes, valid = run(scenario())
        finally:
            asy_base_classes.set_utc_valid(valid=False)
    assert changes == [(_CHECK_INTERVAL_S, True), (_STALE_AFTER_S, False)]  # synced until the age reaches 3 h, not before
    assert valid is True  # the clock stays valid through the stale sync


def test_ntp_goes_stale_when_every_due_resync_fails() -> None:
    # The due resync fires every hour and fails each time: only a success restarts the age, so the
    # sync goes stale three intervals after the last one, never postponed by a failed resync.
    recorder = _RecordingResolver(None)
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder
    with _SteppedClock() as clock:
        client = _hourly_client()

        async def scenario() -> "list[tuple[int, bool]]":
            sync_task = asyncio.create_task(client._sync_loop())
            await asyncio.sleep(0)  # past the task's own unsynced start
            await client._handle_ntp_sync_success(_TM)
            task = asyncio.create_task(client._refresh_loop())
            seen = await _drive_refresh(client, clock, _STALE_AFTER_S // _CHECK_INTERVAL_S + 1)
            await cancel(task)
            await cancel(sync_task)
            return seen

        try:
            changes = run(scenario())
        finally:
            ntpmod.resolve_ipv4 = original
            asy_base_classes.set_utc_valid(valid=False)
    assert changes == [(_CHECK_INTERVAL_S, True), (_STALE_AFTER_S, False)]
    assert len(recorder.calls) >= 2  # the 1 h and 2 h resyncs ran, and failed
    assert _slots(client)[1][0] == code("E", "NTP_DNS")


def test_a_successful_resync_restarts_the_age() -> None:
    with _SteppedClock() as clock:
        client = _hourly_client()

        async def resync_at_150_min(t: int) -> None:
            if t == 150 * 60:
                await client._handle_ntp_sync_success(_TM)

        async def scenario() -> "list[tuple[int, bool]]":
            await client._handle_ntp_sync_success(_TM)
            task = asyncio.create_task(client._refresh_loop())
            seen = await _drive_refresh(client, clock, 4 * 3600 // _CHECK_INTERVAL_S, resync_at_150_min)
            await cancel(task)
            return seen

        try:
            changes = run(scenario())
            age = client._sync_age.read()  # on the stepped clock: past the block, ticks_ms() is the host's uptime
        finally:
            asy_base_classes.set_utc_valid(valid=False)
    assert changes == [(_CHECK_INTERVAL_S, True)]  # 4 h after the first success, 1.5 h after the second
    assert age == 90 * 60


def test_the_due_counter_never_exceeds_one_interval() -> None:
    # Every due resync succeeds, so the sync never goes stale. Each period ends in the state it began in, so
    # three identical periods prove the bound for any uptime - no need to brute-force days of ticks.
    with _SteppedClock() as clock:
        client = _hourly_client()

        async def succeeding_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
            await client._handle_ntp_sync_success(_TM)
            return _TM, True

        client._run_ntp_sync_attempt = succeeding_attempt  # type: ignore[assignment, method-assign]
        period = 3600 // _CHECK_INTERVAL_S
        counts: list[int] = []

        async def record(_t: int) -> None:
            counts.append(client._ntp_sec_count)

        async def scenario() -> "list[tuple[int, bool]]":
            sync_task = asyncio.create_task(client._sync_loop())
            await asyncio.sleep(0)
            await client._handle_ntp_sync_success(_TM)
            task = asyncio.create_task(client._refresh_loop())
            await asyncio.sleep(0)  # the loop starts its cadence before the first tick's time passes
            changes = await _drive_refresh(client, clock, 3 * period, record)
            await cancel(task)
            await cancel(sync_task)
            return changes

        try:
            changes = run(scenario())
        finally:
            asy_base_classes.set_utc_valid(valid=False)
    assert changes == [(_CHECK_INTERVAL_S, True)]
    assert counts[:period] == counts[period : 2 * period] == counts[2 * period :]
    assert max(counts) < 3600 and counts[period - 1] == 0  # reset at the due tick itself


# ---------------------------------------------------------------------------
# cettime() - this Unix port's gmtime() returns 9 elements (trailing isdst) where rp2 returns 8, so a
# shim truncates it for cettime()'s length check (SPECIFICATION.md F.7 row 4).
# ---------------------------------------------------------------------------


def test_this_interpreters_gmtime_returns_nine_elements_not_eight() -> None:
    assert len(time.gmtime()) == 9


class _FixedNowTime:
    # Replaces this module's own `time` name, not the read-only builtin: the clock reads `now` (a test may
    # step it), gmtime() is truncated to rp2's 8 elements, mktime() is the real one.
    def __init__(self, fixed_now: int) -> None:
        self.now = fixed_now

    def gmtime(self, *a: int) -> "tuple[int, ...]":
        return tuple(time.gmtime(a[0] if a else self.now))[:8]

    def mktime(self, t: "tuple[int, ...]") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return self.now


class _ClockSet:
    # utc_now() answers for the block - the one-way clock-set state a successful sync sets - and is reset after.
    def __enter__(self) -> None:
        asy_base_classes.set_utc_valid()

    def __exit__(self, *exc_info: object) -> None:
        asy_base_classes.set_utc_valid(valid=False)


def test_cettime_returns_none_before_the_clock_was_set() -> None:
    client = _make_client()
    run(client._set_synced(value=True))  # Synced alone does not open the gate: the clock-set state does
    asy_base_classes.set_utc_valid(valid=False)
    assert asy_base_classes.utc_now() is None
    original_time = ntpmod.time
    ntpmod.time = _FixedNowTime(_mid_month_now(7))  # type: ignore[assignment]
    try:
        assert run(client.cettime()) is None
    finally:
        ntpmod.time = original_time


def test_cettime_answers_after_synced_goes_stale() -> None:
    # The RTC keeps good time after a sync goes stale, so local-time consumers keep running.
    client = _client_with_offsets(3600, 3600)
    assert run(client.ntp_issynced()) is False
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600 + 3600))[:8]


def test_cettime_returns_none_when_config_missing() -> None:
    client = _make_invalid_cfg_client()
    assert _run_cettime_with_fixed_now(client, _mid_month_now(7)) is None


def test_cettime_before_march_boundary_applies_gmt_offset_only() -> None:
    client = _client_with_offsets(3600, 3600)
    fixed_now = _mid_month_now(1)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600))[:8]


def test_cettime_between_march_and_october_applies_gmt_plus_dst_offset() -> None:
    client = _client_with_offsets(3600, 3600)
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600 + 3600))[:8]


def test_cettime_after_october_boundary_applies_gmt_offset_only() -> None:
    client = _client_with_offsets(3600, 3600)
    fixed_now = _mid_month_now(12)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now + 3600))[:8]


def test_cettime_zero_offsets_are_accepted_not_rejected() -> None:
    client = _client_with_offsets(0, 0)
    fixed_now = _mid_month_now(1)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now))[:8]


def test_cettime_negative_offsets_are_accepted_not_rejected() -> None:
    client = _client_with_offsets(-3600, -3600)
    fixed_now = _mid_month_now(7)
    result = _run_cettime_with_fixed_now(client, fixed_now)
    assert result is not None
    assert tuple(result) == tuple(time.gmtime(fixed_now - 3600 - 3600))[:8]


def test_cettime_switches_on_the_last_sundays_of_march_and_october() -> None:
    # Every year of the plausibility window. On rp2, 5 * year / 4 is exact in single precision to 2106 (two fractional bits).
    client = _client_with_offsets(3600, 3600)
    original_time = ntpmod.time
    fake = _FixedNowTime(0)
    ntpmod.time = fake  # type: ignore[assignment]
    try:
        with _ClockSet():
            for year in range(2025, 2100):
                for month, before, after in ((3, 3600, 7200), (10, 7200, 3600)):
                    switch = _last_sunday_0100_utc(year, month)
                    for now, offset in ((switch - 1, before), (switch, after)):
                        fake.now = now
                        result = run(client.cettime())
                        assert result is not None and tuple(result) == tuple(time.gmtime(now + offset))[:8], (year, month, now)
    finally:
        ntpmod.time = original_time


def test_cettime_follows_a_backward_rtc_step_across_the_march_switch() -> None:
    # cettime() reads the clock on every call, so a step (an RTC set) is followed at once, either way.
    client = _client_with_offsets(3600, 3600)
    switch = _last_sunday_0100_utc(time.gmtime()[0], 3)
    original_time = ntpmod.time
    fake = _FixedNowTime(switch + 3600)
    ntpmod.time = fake  # type: ignore[assignment]
    try:
        with _ClockSet():
            after = run(client.cettime())
            fake.now = switch - 3600  # the RTC stepped back two hours, across the switch
            before = run(client.cettime())
    finally:
        ntpmod.time = original_time
    assert after is not None and tuple(after) == tuple(time.gmtime(switch + 3600 + 7200))[:8]
    assert before is not None and tuple(before) == tuple(time.gmtime(switch - 3600 + 3600))[:8]


class _ShortGmtimeTime:
    # Real rp2 time.gmtime() always returns exactly 8 elements - cettime()'s own `len(cet) == 8`
    # check can't actually fail through any real gmtime() call, so this fakes a malformed result
    # directly, the same technique _FixedNowTime above uses for its own fixed-now variant.
    def __init__(self, fixed_now: int) -> None:
        self._fixed_now = fixed_now

    def gmtime(self, *a: int) -> "tuple[int, ...]":
        return tuple(time.gmtime(a[0] if a else self._fixed_now))[:7]  # one short of the real 8-element shape

    def mktime(self, t: "tuple[int, ...]") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return self._fixed_now


def test_cettime_returns_none_when_gmtime_result_has_the_wrong_length() -> None:
    client = _client_with_offsets(3600, 3600)
    original_time = ntpmod.time
    ntpmod.time = _ShortGmtimeTime(_mid_month_now(1))  # type: ignore[assignment]
    try:
        with _ClockSet():
            result = run(client.cettime())
    finally:
        ntpmod.time = original_time
    assert result is None


# ---------------------------------------------------------------------------
# _sync_age_loop() - the synced-clock second counter
# ---------------------------------------------------------------------------


def test_sync_age_follows_measured_time_while_synced() -> None:
    with _SteppedClock() as clock:
        client = _make_client()

        async def scenario() -> "int | None":
            await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
            task = asyncio.create_task(client._sync_age_loop())
            await asyncio.sleep(0)
            for _ in range(3):
                clock.advance(1000)
                await tick(client._time_counter_trigger_event)
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
    with _SteppedClock() as clock:
        client = _make_client()

        async def scenario() -> "int | None":
            await client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0))
            task = asyncio.create_task(client._sync_age_loop())
            await asyncio.sleep(0)
            clock.advance(2500)
            await tick(client._time_counter_trigger_event)
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


def test_sync_state_follows_measured_ticks_not_rtc_steps() -> None:
    # An RTC stepped a year forward, then two back, moves neither Synced nor LastSyncAge: both count measured ticks.
    with _SteppedClock() as clock:
        client = _hourly_client()

        async def scenario() -> "list[tuple[bool, int | None]]":
            await client._handle_ntp_sync_success(_TM)
            tasks = [asyncio.create_task(client._sync_age_loop()), asyncio.create_task(client._refresh_loop())]
            await asyncio.sleep(0)
            seen = []
            for step_s in (365 * 86400, -2 * 365 * 86400):
                clock.wall = int(time.time()) + step_s
                clock.advance(_CHECK_INTERVAL_S * 1000)
                await tick(client._time_counter_trigger_event)
                await tick(client._ntp_timer_trigger_event)
                seen.append((await client.ntp_issynced(), await client.get_last_ntp_sync()))
            for task in tasks:
                await cancel(task)
            return seen

        try:
            assert run(scenario()) == [(True, 10), (True, 20)]
        finally:
            asy_base_classes.set_utc_valid(valid=False)


def test_the_first_sync_from_the_boot_default_restarts_the_age() -> None:
    # The board boots with its RTC at 2021-01-01 (ports/rp2/main.c:141-145, v1.29.0); the first sync jumps it years on.
    reply_time = time.mktime((2026, 6, 1, 12, 0, 0, 0, 0, 0))
    with _SteppedClock() as clock:
        client = _make_client()
        clock.wall = time.mktime((2021, 1, 1, 0, 0, 0, 0, 0, 0))
        RTC().datetime((2021, 1, 1, 5, 0, 0, 0, 0))

        async def scenario() -> "tuple[tuple[int, ...], tuple[int, ...], int | None, int | None, int | None]":
            clock.advance(3600 * 1000)  # an hour of uptime before the first sync
            tm = await client._parse_ntp_reply(make_ntp_reply(reply_time), 0)
            assert tm is not None
            rtc = RTC().datetime()
            assert rtc is not None
            clock.wall = reply_time  # what the RTC now reads
            await client._handle_ntp_sync_success(tm)
            first = await client.get_last_ntp_sync()
            task = asyncio.create_task(client._sync_age_loop())
            await asyncio.sleep(0)
            clock.advance(_CHECK_INTERVAL_S * 1000)
            await tick(client._time_counter_trigger_event)
            later = await client.get_last_ntp_sync()
            await cancel(task)
            return rtc, tuple(tm), first, later, (await client.get_data()).TS

        try:
            rtc, tm, first, later, stamp = run(scenario())
        finally:
            asy_base_classes.set_utc_valid(valid=False)
    assert rtc == (tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0)  # the getter's recomputed weekday
    assert (first, later, stamp) == (0, _CHECK_INTERVAL_S, reply_time)  # the age counts from the sync, not from boot


def test_an_offset_put_then_a_sync_shifts_the_rtc_and_cycles_synced() -> None:
    client = _make_client_with_json('{"NTPHost": "127.0.0.1", "DNSFallback": ""}')
    reply_time = int(time.time())

    async def fetch(_addr: "tuple[str, int]") -> "bytes | None":
        return make_ntp_reply(reply_time)

    client._fetch_ntp_reply = fetch  # type: ignore[assignment, method-assign]

    async def scenario() -> "tuple[bool, tuple[int, ...] | None, bool, tuple[int, ...]]":
        await client._handle_ntp_sync_success(_TM)
        assert await client._set_dict_cfg({"NTPOffset": 3600}, client.get_cfg_schema()) == {"NTPOffset": "Valid"}
        await client.ntp_force_sync()  # the networking group's post-PUT hook (buildgen/codegen.py)
        cleared = await client.ntp_issynced()
        tm, _network_ok = await client._run_ntp_sync_attempt(None)
        rtc = RTC().datetime()
        assert rtc is not None
        return cleared, tm, await client.ntp_issynced(), rtc

    try:
        cleared, tm, synced, rtc = run(scenario())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    shifted = tuple(time.gmtime(reply_time + 3600))
    assert (cleared, synced) == (False, True)
    assert tm is not None and tuple(tm)[:8] == shifted[:8]
    assert rtc == (shifted[0], shifted[1], shifted[2], shifted[6], shifted[3], shifted[4], shifted[5], 0)  # the getter's recomputed weekday


def test_time_counter_resets_to_none_while_not_synced() -> None:
    client = _make_client()

    async def scenario() -> "int | None":
        task = asyncio.create_task(client._sync_age_loop())
        await tick(client._time_counter_trigger_event, 2)
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
    client = _make_client(network_available_locked=lambda: False)
    reached = [False]

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        reached[0] = True
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert reached[0] is False


def test_run_sync_attempt_network_available_raising_is_treated_as_unavailable() -> None:
    def raiser() -> bool:
        raise RuntimeError("wlan.status() exploded")

    client = _make_client(network_available_locked=raiser)
    reached = [False]

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        reached[0] = True
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))  # must not raise
    assert reached[0] is False


def test_run_sync_attempt_network_available_raising_persists_a_callback_error() -> None:
    def raiser() -> bool:
        raise RuntimeError("wlan.status() exploded")

    client = _make_client(network_available_locked=raiser)
    run(client._run_ntp_sync_attempt(None))
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "CALLBACK")
    assert _last_err(counter, "ErrType") == "E"


def test_run_sync_attempt_missing_config_marks_not_synced_and_returns() -> None:
    client = _make_client()
    run(client._set_synced(value=True))

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert run(client.ntp_issynced()) is False


def test_run_sync_attempt_resolve_failure_calls_handle_failure() -> None:
    client = _make_client()
    handled = [False]

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        return ("pool.ntp.org", "", 0)

    async def fake_resolve(_host: str, _dns_server: "str | None", _fallback: str) -> "tuple[str, int] | None":
        return None

    async def fake_handle_failure() -> None:
        handled[0] = True

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    client._handle_ntp_sync_failure = fake_handle_failure  # type: ignore[method-assign]
    run(client._run_ntp_sync_attempt(None))
    assert handled[0] is True


def test_run_sync_attempt_passes_the_given_dns_server_to_resolve_ntp_server() -> None:
    # Proves the attempt forwards its own dns_server unchanged: the value comes from _sync_loop()'s
    # _safe_get_dns_server() call, read before wifi_mode_lock is taken (see that method's own comment).
    client = _make_client()
    received: list[str | None] = []

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        return ("pool.ntp.org", "", 0)

    async def fake_resolve(_host: str, dns_server: "str | None", _fallback: str) -> "tuple[str, int] | None":
        received.append(dns_server)
        return None

    client._get_ntp_config = fake_get_cfg  # type: ignore[method-assign]
    client._resolve_ntp_server = fake_resolve  # type: ignore[assignment, method-assign]
    run(client._run_ntp_sync_attempt("203.0.113.53"))
    assert received == ["203.0.113.53"]


def test_run_sync_attempt_fetch_failure_calls_handle_failure() -> None:
    client = _make_client()
    handled = [False]

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        return ("pool.ntp.org", "", 0)

    async def fake_resolve(_host: str, _dns_server: "str | None", _fallback: str) -> "tuple[str, int] | None":
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
    client = _make_client()
    handled = [False]

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        return ("pool.ntp.org", "", 0)

    async def fake_resolve(_host: str, _dns_server: "str | None", _fallback: str) -> "tuple[str, int] | None":
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
    client = _make_client()
    handled_with: list[tuple[int, ...]] = []
    parsed_tm = (2026, 1, 1, 0, 0, 0, 0, 0)

    async def fake_get_cfg() -> "tuple[str, str, int] | None":
        return ("pool.ntp.org", "", 0)

    async def fake_resolve(_host: str, _dns_server: "str | None", _fallback: str) -> "tuple[str, int] | None":
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
    client = _make_client()
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
    client = _make_client()

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


class _SweptSync:
    # One sweep count's fixture: a fresh client over the shared config, its trigger set, and the fake sockets it opens.
    def __init__(self, client: NTPClient, script: _SocketScript) -> None:
        self.client = client
        self.script = script


def test_the_sync_task_survives_a_cancel_at_every_await() -> None:
    # The real _sync_loop() and attempt over the fake socket, its send and receive each a driven 5 ms wait; cancelled at
    # each 1 ms turn, through the sync and into the next trigger wait, every lock is free and every socket torn down.
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(_INTEGRATION_CFG)  # written once: each count's client only reads it
    reply = make_ntp_reply(int(time.time()))
    built: list[_SweptSync] = []
    phases: list[tuple[int, bool]] = []

    async def build() -> _SweptSync:
        client = NTPClient(asyncio.Lock(), lambda: True, lambda: None, _timing(), cfg_path=cfg_path)
        await client.setup()
        client._ntp_sync_trigger_event.set()
        built.append(_SweptSync(client, _SocketScript(reply=reply, gate_ms=5)))
        return built[-1]

    async def start(swept: _SweptSync) -> None:
        await swept.client._sync_loop()

    def invariants(swept: _SweptSync) -> None:
        client = swept.client
        assert_unlocked(wifi_mode_lock=client.wifi_mode_lock, data_lock=client._data_lock, config_lock=client.cfgmgr._config_lock)
        left = [sock for sock in swept.script.sockets if not sock.disconnected]
        assert not left, f"{len(left)} socket(s) left open"
        data = client._datastruct
        assert isinstance(data, ntpmod.NTP)
        phase = (sum(len(sock.calls) for sock in swept.script.sockets), data.Synced)
        if not phases or phases[-1] != phase:
            phases.append(phase)

    def make(addr: "tuple[str, int]", mode: str = "client") -> _FakeUDPSocket:
        return built[-1].script.make(addr, mode)

    original = ntpmod.UDPSocket
    ntpmod.UDPSocket = make  # type: ignore[assignment, misc]
    try:
        with DrivenTime(_SOCKET_CLOCK, sleeps=True) as clock:
            counts = cancel_at_each_await(build, start, invariants, max_steps=16, turn=lambda: clock.elapse(1), endless=True)
            assert clock.wakes() == [], clock.wakes()
    finally:
        ntpmod.UDPSocket = original  # type: ignore[misc]
        asy_base_classes.set_utc_valid(valid=False)  # the sync this sweep completes sets the process-wide flag
    assert counts == len(built) == 16
    assert phases == [(0, False), (1, False), (2, False), (2, True)], phases  # before the socket, in each wait, after the sync


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


def test_asy_ntp_time_never_gives_up_on_a_persistently_failing_server() -> None:
    # An unreachable server is routine for this task (Part C.7.2): a restart re-initialises nothing,
    # and each one costs the supervisor's reboot budget. So far past any old streak, still running.
    client = _make_client()

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        return None, True  # network was available, but the attempt itself still failed

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 50)) is True
    assert client._err_cnt_internal == 0  # no streak is kept at all
    assert run(client.get_error_counter())["NTP"]["ErrCount"] == 0  # no give-up entry, nor any other


def test_asy_ntp_time_failed_unsynced_attempts_double_the_retry_interval_up_to_its_cap() -> None:
    client = _make_client(timing=_timing(retry_s=10, retry_max_s=70))
    seen: list[int] = []

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        seen.append(client._retry_wait_s)
        return None, True

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 6)) is True
    assert seen == [10, 20, 40, 70, 70, 70]


def test_asy_ntp_time_network_unavailable_cycles_leave_the_retry_interval_alone() -> None:
    # A skipped attempt says nothing about the server, so the next one must come promptly.
    client = _make_client(timing=_timing(retry_s=10, retry_max_s=600))

    async def unavailable_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        return None, False

    client._run_ntp_sync_attempt = unavailable_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 10)) is True
    assert client._retry_wait_s == 10


def test_asy_ntp_time_failures_while_synced_leave_the_unsynced_retry_interval_alone() -> None:
    # A synced device's failed resync is _handle_ntp_sync_failure()'s retry loop's business; the
    # backoff starts only once the sync has actually gone stale.
    client = _make_client(timing=_timing(retry_s=10, retry_max_s=600))

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        await client._set_synced(value=True)
        return None, True

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 5)) is True
    assert client._retry_wait_s == 10


def test_a_successful_sync_resets_the_backoff() -> None:
    client = _make_client(timing=_timing(retry_s=10, retry_max_s=600))
    client._retry_wait_s, client._unsynced_wait_s = 320, 30
    run(client._handle_ntp_sync_success((2026, 1, 1, 0, 0, 0, 0, 0)))
    assert (client._retry_wait_s, client._unsynced_wait_s) == (10, 0)


def test_ntp_force_sync_resets_the_backoff() -> None:
    # An operator's resync (a PUT of NTPHost) must run now, not after a ten-minute backoff step.
    client = _make_client(timing=_timing(retry_s=10, retry_max_s=600))
    client._retry_wait_s, client._unsynced_wait_s = 600, 50
    run(client.ntp_force_sync())
    assert (client._retry_wait_s, client._unsynced_wait_s) == (10, 0)


def test_constructor_clamps_the_backoff_pair_to_the_check_tick_and_to_each_other() -> None:
    client = _make_client(timing=_timing(retry_s=3, retry_max_s=5))
    assert (client._retry_s, client._retry_max_s, client._retry_wait_s) == (10, 10, 10)
    client = _make_client(timing=_timing(retry_s=40, retry_max_s=20))
    assert (client._retry_s, client._retry_max_s) == (40, 40)


def test_asy_ntp_time_alternating_failure_codes_spend_a_slot_each_and_count_every_one() -> None:
    # The central newest-entry rule (C.7.1) collapses only a repeat of the newest code: alternation spends a slot each.
    client = _make_client()
    codes = [code("E", "NTP_DNS"), code("E", "NTP_NO_REPLY")] * 2 + [code("E", "NTP_DNS")]
    expected = list(codes)

    async def failing_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        await client.pr.err_s("failed", errno=codes.pop(0))
        return None, True

    client._run_ntp_sync_attempt = failing_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 5)) is True
    assert _slots(client) == (5, expected)


def test_a_recurring_code_after_a_success_keeps_one_slot() -> None:
    client = _make_client()
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
    client = _make_client()
    toggle = [True]

    async def alternating_attempt(_dns_server: "str | None") -> "tuple[tuple[int, ...] | None, bool]":
        if toggle[0]:
            toggle[0] = False
            return None, True  # failure
        toggle[0] = True
        return (2026, 1, 1, 0, 0, 0, 0, 0), True  # success

    client._run_ntp_sync_attempt = alternating_attempt  # type: ignore[assignment, method-assign]
    assert run(_drive_attempts(client, 20)) is True


# ---------------------------------------------------------------------------
# Integration tests: the real network path, driving the whole _sync_loop() task through
# cfgmgr -> _resolve_ntp_server -> UDPSocket -> real UDP loopback -> a staged real NTP server,
# proving how a genuine fault or success propagates up through the public getters.
# ---------------------------------------------------------------------------


class _RaisingRecvSocket:
    # Stands in for a FakeNtpServer's own socket: recvfrom() raises `exc` the first `times` calls, then the real one reads.
    def __init__(self, sock: "socket.socket", exc: OSError, times: int) -> None:
        self._sock = sock
        self._exc = exc
        self._times = times

    def close(self) -> None:
        self._sock.close()

    def recvfrom(self, size: int) -> "tuple[bytes, object]":
        if self._times:
            self._times -= 1
            raise self._exc
        return self._sock.recvfrom(size)

    def sendto(self, data: bytes, addr: object) -> int:
        return self._sock.sendto(data, addr)  # type: ignore[arg-type]  # the address recvfrom() answered


def test_the_fake_ntp_server_waits_out_an_eagain_receive() -> None:
    # A wake-up with nothing to read is the one receive failure the server absorbs: it polls on and answers.
    assert _serve_through(OSError(errno.EAGAIN), 1) == (b"reply", None)


def test_the_fake_ntp_server_raises_any_other_receive_failure() -> None:
    # Any other receive failure is the test rig failing, not a wake-up: it reaches the test instead of a silent give-up.
    answer, raised = _serve_through(OSError(errno.ECONNRESET), _RESPONDER_POLL_TRIES)
    assert answer is None
    assert isinstance(raised, OSError) and raised.errno == errno.ECONNRESET, raised


def test_integration_full_task_reaches_synced_state_on_a_real_successful_reply() -> None:
    client = _make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "tuple[bool, int | None]":
        server = _make_ntp_server()
        try:
            with redirect_udp_port(ntpmod, 123, server.port):
                task = asyncio.create_task(client._sync_loop())
                client._ntp_sync_trigger_event.set()
                assert await server.serve_once(reply) is True
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
    client = _make_integration_client()

    async def scenario() -> bool:
        # A port of this file's band that nothing binds: a twin booted beside this run holds the real port 123.
        with redirect_udp_port(ntpmod, 123, _PORTS.next()):
            task = asyncio.create_task(client._sync_loop())
            client._ntp_sync_trigger_event.set()
            await asyncio.sleep(_NO_ANSWER_WAIT_S)  # longer than one failed attempt against a closed loopback port
            synced = await client.ntp_issynced()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return synced

    assert run(scenario()) is False


def test_integration_full_task_stays_not_synced_on_a_malformed_reply() -> None:
    client = _make_integration_client()
    garbage_reply = b"not-a-real-ntp-packet-at-all-way-too-short"

    async def scenario() -> bool:
        server = _make_ntp_server()
        try:
            with redirect_udp_port(ntpmod, 123, server.port):
                task = asyncio.create_task(client._sync_loop())
                client._ntp_sync_trigger_event.set()
                assert await server.serve_once(garbage_reply) is True
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

    # So this takes one real successful sync, starts a due resync (a forced one would clear Synced) that gets
    # dropped, and proves the resulting retry timer genuinely reaches a real listening server on a later attempt.
    client = _make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def _wait_synced(*, target: bool) -> None:
        for _ in range(_STATE_POLL_TRIES):
            if await client.ntp_issynced() == target:
                return
            await asyncio.sleep_ms(_STATE_POLL_MS)

    async def scenario() -> bool:
        server = _make_ntp_server()
        try:
            with redirect_udp_port(ntpmod, 123, server.port):
                task = asyncio.create_task(client._sync_loop())
                client._ntp_sync_trigger_event.set()
                assert await server.serve_once(reply) is True
                await _wait_synced(target=True)
                assert await client.ntp_issynced() is True  # confirmed synced once via a real round trip

                client._ntp_sync_trigger_event.set()  # the due resync's trigger: Synced stays set
                assert await server.serve_once(None) is True  # taken and dropped entirely
                for _ in range(_RETRY_ARMED_POLL_TRIES):  # wait for the real fetch timeout to elapse and arm a retry
                    if client._ntp_retry_timer.callback is not None:
                        break
                    await asyncio.sleep_ms(_STATE_POLL_MS)
                assert client._ntp_retry_timer.callback is not None  # retry genuinely armed this time

                client._ntp_retry_timer.trigger()  # fire the scheduled retry immediately, not after 15s
                assert await server.serve_once(reply) is True
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


def test_get_cfg_schema_is_the_schema_in_source() -> None:
    # The client's schema, in the constructor's order, as the source declares it (read above).
    assert _make_client().get_cfg_schema() == _SCHEMA


def test_set_dict_cfg_persists_plain_fields_through_the_base_path() -> None:
    # Fields other than NTPHost and DNSFallback persist through SensorReaderConfig's generic path; nothing is pushed live.
    client = _make_client()
    results = run(client._set_dict_cfg({"NTPHost": "time.example.org", "NTPInterval": 6}, client.get_cfg_schema()))
    assert results == {"NTPHost": "Valid", "NTPInterval": "Valid"}
    stored = run(client.cfgmgr.get_dict(["NTPHost", "NTPInterval"]))
    assert stored == {"NTPHost": "time.example.org", "NTPInterval": 6}


def test_set_dict_cfg_invalid_field_reported_individually_others_still_apply() -> None:
    client = _make_client()
    results = run(client._set_dict_cfg({"NTPInterval": 999, "GMTOffset": 7200}, client.get_cfg_schema()))
    assert results == {"NTPInterval": "Invalid", "GMTOffset": "Valid"}
    stored = run(client.cfgmgr.get_dict(["NTPInterval", "GMTOffset"]))
    assert stored == {"NTPInterval": 12, "GMTOffset": 7200}  # Interv_H untouched default, GMTOffset applied


def test_a_put_of_a_malformed_dns_fallback_is_invalid_and_stores_nothing() -> None:
    client = _make_client()
    bad = ("8.8.8.8,", "8.8.8.8 ,1.1.1.1", "1.2.3.4,5.6.7.8,9.9.9.9,1.1.1.1", "x", "256.1.1.1", 7)
    for value in bad:
        assert _put(client, {"DNSFallback": value}) == {"DNSFallback": "Invalid"}, value
    assert run(client.cfgmgr.get_dict(["DNSFallback"])) == {"DNSFallback": ""}  # the builder's value stands
    assert _slots(client) == (len(bad), [code("E", "BAD_ARG")])  # one entry each, in this client's own log


def test_a_refused_field_leaves_the_rest_of_the_put_to_apply() -> None:
    client = _make_client()
    assert _put(client, {"DNSFallback": "x", "NTPHost": "-a.b", "NTPInterval": 6}) == {"DNSFallback": "Invalid", "NTPHost": "Invalid", "NTPInterval": "Valid"}
    assert run(client.cfgmgr.get_dict(["DNSFallback", "NTPHost", "NTPInterval"])) == {"DNSFallback": "", "NTPHost": "pool.ntp.org", "NTPInterval": 6}


def test_a_put_of_an_ntp_host_that_is_not_a_host_name_is_invalid() -> None:
    client = _make_client()
    bad = ("-a.b", "a" * 64 + ".org", "a..b", "a b", "pool.ntp.org.", 12345)
    for value in bad:
        assert _put(client, {"NTPHost": value}) == {"NTPHost": "Invalid"}, value
    assert run(client.cfgmgr.get_dict(["NTPHost"])) == {"NTPHost": "pool.ntp.org"}
    assert _slots(client) == (len(bad), [code("E", "BAD_ARG")])


def test_a_put_of_a_valid_host_or_ipv4_list_is_valid() -> None:
    client = _make_client()
    for host in ("192.168.1.1", "pool.ntp.org", "a-b.example", "ntp1"):  # each differs from the one before
        assert _put(client, {"NTPHost": host}) == {"NTPHost": "Valid"}, host
        assert run(client.cfgmgr.get_dict(["NTPHost"])) == {"NTPHost": host}
    for servers in ("8.8.8.8", "8.8.8.8,1.1.1.1", "1.1.1.1,8.8.4.4,9.9.9.9", ""):
        assert _put(client, {"DNSFallback": servers}) == {"DNSFallback": "Valid"}, servers
        assert run(client.cfgmgr.get_dict(["DNSFallback"])) == {"DNSFallback": servers}
    assert _slots(client) == (0, [])


# The corpus keys this file judges and the field each goes through; with the other judge files' they name every key
# of tests/_radio_shape_cases.json (tests_scripts/test_radio_shape_corpus.py).
_JUDGED_SHAPES = (("hostName", "NTPHost"), ("ipv4List", "DNSFallback"))


def test_the_shape_corpus_judges_ntp_host_and_dns_fallback() -> None:
    # One corpus, three judges: this product check, buildgen's and the mock's (SPECIFICATION.md G.2).
    with open("tests/_radio_shape_cases.json") as f:
        cases = json.load(f)
    for shape, field in _JUDGED_SHAPES:
        assert cases[shape]["accept"] and cases[shape]["reject"], shape
        for value in cases[shape]["accept"]:
            client = _make_client()
            assert _put(client, {field: value})[field] in ("Valid", "Unchanged"), (field, value)  # a default is unchanged
            assert run(client.cfgmgr.get_dict([field])) == {field: value}
        for value in cases[shape]["reject"]:
            assert _put(_make_client(), {field: value}) == {field: "Invalid"}, (field, value)


def test_no_push_callbacks_are_registered_for_any_ntp_field() -> None:
    # Confirms the persist-only design explicitly, not just implicitly via the absence of a push:
    # every NTP field goes straight to cfgmgr with nothing live to update.
    client = _make_client()
    assert client._push_callbacks == {}


def test_write_config_round_trips_a_real_value() -> None:
    # A real write through the store the REST PUT path reaches (asy_api_response.py's handle_set_cmd()), read back.
    client = _make_client()

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


def test_missing_config_failure_logs_in_both_layers_one_slot_each() -> None:
    client = _make_invalid_cfg_client()  # the store logs its own CFG_PATH_IS_DIR at construction
    before = run(client.cfgmgr.get_error_counter())["CFGMGR_NTP"]["ErrCount"]
    assert _twice_one_slot(client, lambda: client._run_ntp_sync_attempt(None)) == (2, [code("E", "CFG_READ")], ["E"])
    store = run(client.cfgmgr.get_error_counter())["CFGMGR_NTP"]
    assert store["ErrCount"] - before == 1  # four failed reads (two per attempt: host, then offset), one run: one entry
    kept = [store["ErrNum"][i] for i in range(len(store["ErrNum"])) if store["ErrType"][i] != "N"]
    assert kept[-1] == code("E", "CFG_NOT_VALID") and kept.count(code("E", "CFG_NOT_VALID")) == 1, kept


def test_dns_failure_is_counted_twice_but_persisted_once() -> None:
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = _RecordingResolver(None)
    try:
        client = _make_client()
        assert _twice_one_slot(client, lambda: client._resolve_ntp_server("bogus.invalid", None, "")) == (2, [code("E", "NTP_DNS")], ["E"])
    finally:
        ntpmod.resolve_ipv4 = original


def test_no_reply_is_counted_twice_but_persisted_once() -> None:
    client = _make_client(timing=_timing(fetch_timeout_ms=_NO_REPLY_FETCH_TIMEOUT_MS))
    addr = _make_addr()
    assert _twice_one_slot(client, lambda: client._fetch_ntp_reply(addr)) == (2, [code("E", "NTP_NO_REPLY")], ["E"])


def test_implausible_time_is_counted_twice_but_persisted_once() -> None:
    client = _make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=1, unix_seconds=1000)  # past 2100 in every era
    assert _twice_one_slot(client, lambda: client._parse_ntp_reply(msg, 0)) == (2, [code("E", "NTP_IMPLAUSIBLE")], ["E"])


def test_malformed_reply_is_counted_twice_but_persisted_once() -> None:
    client = _make_client()
    assert _twice_one_slot(client, lambda: client._parse_ntp_reply(b"x", 0)) == (2, [code("E", "NTP_MALFORMED")], ["E"])


def test_kiss_of_death_warning_is_counted_twice_but_persisted_once() -> None:
    client = _make_client()
    msg = _reply_with_li_and_stratum(leap_indicator=0, stratum=0, unix_seconds=int(time.time()))
    assert _twice_one_slot(client, lambda: client._parse_ntp_reply(msg, 0)) == (2, [code("W", "NTP_UNSYNC_REPLY")], ["W"])


def test_an_error_and_a_warning_with_the_same_number_are_different_codes() -> None:
    # errno n and wrnno n mean different things; one must never suppress the other's slot.
    client = _make_client()
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
    client = _make_client()
    errors = [code("E", name) for name in ("NTP_DNS", "NTP_IMPLAUSIBLE", "NTP_MALFORMED", "NTP_RETRIES", "NTP_NO_REPLY", "NTP_NOT_SENT")]
    warning = code("W", "NTP_UNSYNC_REPLY")

    async def scenario() -> None:
        for num in errors:
            await client.pr.err_s("failed", errno=num)
        await client.pr.wrn_s("rejected", wrnno=warning)

    run(scenario())
    assert _slots(client) == (7, errors + [warning])


def test_backoff_restarts_from_the_first_interval_after_a_recovery() -> None:
    client = _make_client(timing=_timing(retry_s=10, retry_max_s=600))
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
    client = _make_client()
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
        await tick(client._ntp_timer_trigger_event, 5)
        results = [await fired()]
        await client._set_synced(value=False)
        await tick(client._ntp_timer_trigger_event, 2)
        results.append(await fired())
        await tick(client._ntp_timer_trigger_event, 1)
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
    client = _make_integration_client()
    client._ntp_fetch_timeout_ms = _NO_REPLY_FETCH_TIMEOUT_MS
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "tuple[bool, bool, int, ErrorLog]":
        server = _make_ntp_server()
        try:
            with redirect_udp_port(ntpmod, 123, server.port):
                task = asyncio.create_task(client._sync_loop())
                for answer in (None, None, None, reply):
                    client._ntp_sync_trigger_event.set()
                    assert await server.serve_once(answer) is True
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
    client = _make_integration_client()
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "ErrorLog":
        server = _make_ntp_server()
        try:
            with redirect_udp_port(ntpmod, 123, server.port):
                served = asyncio.create_task(server.serve_once(reply))
                # 123 is a const() in the product, not a module attribute; the redirect maps it.
                assert await client._fetch_ntp_reply(("127.0.0.1", 123)) is not None
                assert await served is True
                return await client.get_error_counter()
        finally:
            server.close()

    assert run(scenario())["NTP"]["ErrCount"] == 0



# ---- The client against the twin's local NTP responder (digital_twin/unixport/_ntp_responder.py): a real UDP round
# trip on loopback per attempt ----

_RTC_UNSET = (2001, 2, 3, 5, 4, 5, 6, 0)  # a Saturday in the getter's own form (Monday 0): a time no sync writes


# What a failed unsynced attempt leaves: not synced, no age, the RTC unset, the backoff doubled per attempt (C.7.2).
_FAILED_TWICE = [(False, None, min(2 * _RETRY_S, _RETRY_MAX_S), _RTC_UNSET), (False, None, min(4 * _RETRY_S, _RETRY_MAX_S), _RTC_UNSET)]


def test_a_sync_against_the_responder_sets_the_rtc_and_synced() -> None:
    before = int(time.time())
    seen = _against_responder(_responder_client(), NtpResponder(_PORTS.next()), ["silent", "serve"])
    after = int(time.time())
    assert seen[0][:2] == (False, None) and seen[0][3] == _RTC_UNSET  # no reply, no sync
    assert seen[1][:2] == (True, 0)
    assert seen[1][3] in [_rtc_reading(t) for t in range(before, after + 1)], seen[1][3]


def test_the_servers_offset_moves_the_set_time() -> None:
    responder = NtpResponder(_PORTS.next())
    responder.offset_s = 3600
    before = int(time.time())
    seen = _against_responder(_responder_client(), responder, ["serve"])
    after = int(time.time())
    assert seen[0][3] in [_rtc_reading(t + 3600) for t in range(before, after + 1)], seen[0][3]


def test_a_cancel_in_any_round_after_a_silent_fetch_times_out_ends_the_sync_task() -> None:
    # The shutdown cancels the sync task and awaits it. ready()'s wait_for_ms() took a cancel landing after its timeout for
    # the timeout: the fetch read as no reply and the loop went back to its trigger wait (SPECIFICATION.md F.2).
    client = _responder_client()
    client._ntp_fetch_timeout_ms = _NO_REPLY_FETCH_TIMEOUT_MS
    responder = NtpResponder(_PORTS.next())  # bound and never served: no request is answered

    async def scenario(clock: DrivenTime, rounds: int) -> bool:
        task = asyncio.create_task(client._sync_loop())
        await clock.elapse(0)  # parked on its trigger
        client._ntp_sync_trigger_event.set()
        await clock.elapse(_NO_REPLY_FETCH_TIMEOUT_MS - 1)  # the request sent, its reply awaited
        clock.advance(1)  # the fetch's deadline passes; what it wakes runs from the next round
        for _ in range(rounds):
            await asyncio.sleep_ms(0)
        task.cancel()
        for _ in range(_END_ROUNDS):
            if task.done():
                break
            await asyncio.sleep_ms(0)
        done = task.done()
        if not done:  # back on its trigger: ended there, so the failure below names the round
            await clock.elapse(0)
            await cancel(task)
        return done

    ended: list[bool] = []
    try:
        for k in range(_FETCH_CANCEL_ROUNDS):
            with DrivenTime(asy_udp_socket, sleeps=True) as clock, redirect_udp_port(ntpmod, 123, responder.port):
                ended.append(run(scenario(clock, k)))
    finally:
        responder.close()
    assert all(ended), f"a cancel in these rounds after the fetch timed out did not end the task: {[k for k, done in enumerate(ended) if not done]}"


def test_a_silent_responder_fails_each_attempt_with_no_reply() -> None:
    assert _fails_twice("silent") == (_FAILED_TWICE, (2, [code("E", "NTP_NO_REPLY")]))


def test_an_unsynchronised_reply_fails_each_attempt_with_its_warning() -> None:
    assert _fails_twice("unsync") == (_FAILED_TWICE, (2, [code("W", "NTP_UNSYNC_REPLY")]))


def test_a_short_reply_fails_each_attempt_as_malformed() -> None:
    assert _fails_twice("short") == (_FAILED_TWICE, (2, [code("E", "NTP_MALFORMED")]))


def test_an_implausible_reply_fails_each_attempt_as_implausible() -> None:
    assert _fails_twice("implausible") == (_FAILED_TWICE, (2, [code("E", "NTP_IMPLAUSIBLE")]))


def test_a_failed_resync_never_resets_the_staleness_count() -> None:
    # Synced from the responder, then a failed resync at 1 h and 2 h with it silent: stale three intervals after the
    # success all the same (the owner-reviewed rule in _refresh_loop()); the due cadence's own case is further up.
    responder = NtpResponder(_PORTS.next())
    with _SteppedClock() as clock:
        client = _responder_client(interval_h=1)
        finished = _counted(client)

        async def scenario() -> "list[tuple[int, bool]]":
            seen: list[tuple[int, bool]] = []
            with redirect_udp_port(ntpmod, 123, responder.port):
                tasks = [asyncio.create_task(responder.serve()), asyncio.create_task(client._sync_loop()), asyncio.create_task(client._refresh_loop())]
                try:
                    client._ntp_sync_trigger_event.set()
                    await _attempt_ended(finished)
                    responder.mode, client._ntp_fetch_timeout_ms = "silent", _NO_REPLY_FETCH_TIMEOUT_MS
                    elapsed_s = 0
                    for age_s in (3600, 7200, _STALE_AFTER_S - _CHECK_INTERVAL_S, _STALE_AFTER_S):
                        clock.advance((age_s - elapsed_s) * 1000)
                        elapsed_s = age_s
                        if age_s % 3600 == 0 and age_s < _STALE_AFTER_S:
                            client._ntp_sync_trigger_event.set()
                            await _attempt_ended(finished)
                        await tick(client._ntp_timer_trigger_event)
                        seen.append((age_s, await client.ntp_issynced()))
                finally:
                    await cancel_all(tasks)
            return seen

        try:
            seen = run(scenario())
        finally:
            responder.close()
            asy_base_classes.set_utc_valid(valid=False)
    assert seen == [(3600, True), (7200, True), (_STALE_AFTER_S - _CHECK_INTERVAL_S, True), (_STALE_AFTER_S, False)]
    assert responder.requests >= 3  # the sync, then the two failed resyncs
    assert _slots(client)[1] == [code("E", "NTP_NO_REPLY")]


def test_a_responder_back_mid_backoff_syncs_at_the_next_attempt() -> None:
    seen = _against_responder(_responder_client(), NtpResponder(_PORTS.next()), ["silent", "silent", "serve"])
    assert [s[:3] for s in seen] == [s[:3] for s in _FAILED_TWICE] + [(True, 0, _RETRY_S)]



def test_a_dropped_check_tick_does_not_delay_the_due_resync() -> None:
    # The resync cadence reads elapsed time, as the stale rule does: with one check tick dropped (a soft-Timer
    # callback can be, SPECIFICATION.md F.1), the resync is still due at one NTPInterval of measured time.
    with _SteppedClock() as clock:
        client = _hourly_client()

        async def scenario() -> "int | None":
            await client._handle_ntp_sync_success(_TM)
            task = asyncio.create_task(client._refresh_loop())
            await asyncio.sleep(0)  # the loop starts its cadence before the first tick's time passes
            due_at = None
            for n in range(1, 3600 // _CHECK_INTERVAL_S + 2):
                clock.advance(_CHECK_INTERVAL_S * 1000)
                if n == 100:
                    continue  # this tick's callback is dropped: its time passes, no tick arrives
                await tick(client._ntp_timer_trigger_event)
                if client._ntp_sync_trigger_event.state:
                    due_at = n * _CHECK_INTERVAL_S
                    break
            await cancel(task)
            return due_at

        try:
            due_at = run(scenario())
        finally:
            asy_base_classes.set_utc_valid(valid=False)
    assert due_at == 3600, due_at


def test_the_boundary_tick_triggers_the_resync_though_the_cadence_restarted_after_a_fire() -> None:
    # The due tick restarts the cadence after its own awaits, a few ms past its fire, and later fires keep the timer's
    # phase: each boundary tick reads just under one NTPInterval and still triggers, cycle after cycle.
    due_at = _synced_due_at(0, 2, 3)
    assert due_at == [3600, 7200, 10800], due_at


def test_the_resync_goes_to_the_check_tick_nearest_its_boundary() -> None:
    # A cadence started off the timer's phase (a restarted loop): the tick 4 s before the boundary triggers, and the
    # one 6 s before it does not.
    early = _synced_due_at(-4000, 0, 2)
    assert early == [3596, 7196], early
    late = _synced_due_at(4000, 0, 1)
    assert late == [3604], late


def _unsynced_due_at(step_ms: int, dropped: int) -> "int | None":
    # A never-synced client on a 40 s backoff step, one check tick per `step_ms` of measured time with tick `dropped`'s
    # callback lost (a soft-Timer callback can be, SPECIFICATION.md F.1): the measured seconds its retry triggered at.
    with _SteppedClock() as clock:
        client = _make_client()
        client._retry_wait_s = 40

        async def scenario() -> "int | None":
            task = asyncio.create_task(client._refresh_loop())
            await asyncio.sleep(0)  # the loop starts before the first tick's time passes
            due_at = None
            for n in range(1, 7):
                clock.advance(step_ms)
                if n == dropped:
                    continue  # its time passes, no tick arrives
                await tick(client._ntp_timer_trigger_event)
                if client._ntp_sync_trigger_event.state:
                    due_at = n * _CHECK_INTERVAL_S
                    break
            await cancel(task)
            return due_at

        return run(scenario())


def test_a_dropped_check_tick_does_not_delay_the_unsynced_retry() -> None:
    # The tick after a dropped one counts both intervals, so the retry still triggers at 40 s of measured time.
    due_at = _unsynced_due_at(_CHECK_INTERVAL_S * 1000, dropped=2)
    assert due_at == 40, due_at


def test_a_dropped_tick_between_early_wakes_still_counts() -> None:
    # Each wake lands a little before a whole interval since the last (a loop's own latency varies): the gap rounds to
    # the nearest interval, so the 19.998 s across the dropped tick still counts two.
    due_at = _unsynced_due_at(_CHECK_INTERVAL_S * 1000 - 1, dropped=2)
    assert due_at == 40, due_at


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
