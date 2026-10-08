"""Integration tests across the real three-file chain: WifiService -> NTPClient -> asy_dns_client.py's resolve_ipv4(). Every other test file replaces peers with a lambda/recorder; this file wires real instances (matching sensortask-wozi.py) to prove the *linked* behavior - calling order, error handling, value propagation - a lambda-based unit test can't observe.
Found and fixed a real bug this way: NTPClient used to call get_dns_server_ip() after acquiring the shared wifi_mode_lock, so its own locked() gate always saw True and always returned None. Fixed via _safe_get_dns_server(), called before acquiring the lock."""
# No real port-53 or port-123 exchange (both need root): a literal-IP NTPHost skips DNS, and an
# empty DNSFallback with a 0.0.0.0 DHCP server leaves no candidate to ask.

import asyncio
import select
import socket
import struct
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP shim's directory (digital_twin/README.md)

import network
from _error_codes import code
from _tmp_scratch import TmpScratch
from _udp_port_redirect import redirect_udp_port
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

import asy_base_classes
import asy_dns_client
import asy_ntp_client as ntpmod
from asy_ntp_client import NTPClient, NtpTiming
from asy_wifi_service import WIFI, WifiConfig, WifiService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Literal, TypeVar

    from typing_extensions import Self

    from asy_print_log import ErrorLog, PrintLogHistory

    T = TypeVar("T")

# Once, before any UDPSocket connects: this Unix build's socket takes no plain (host, port) tuple (SPECIFICATION.md F.7).
patch_asy_udp_socket_for_unix_port()

# The two well-known ports the product dials; asy_ntp_client.py's and asy_dns_client.py's const()s are not
# importable once folded, so these mirror them (keep in sync).
_NTP_PORT = 123
_DNS_PORT = 53
# Mirrors asy_wifi_service.py's _PHASE_STA_ESTABLISHED, likewise (keep in sync).
_PHASE_STA_ESTABLISHED = 1

# @tunable l1.ntp_wifi_dns_integration_lock_blocked_wait_s = 0.05
_LOCK_BLOCKED_WAIT_S = 0.05
# @tunable l1.asy_ntp_client_serve_wait_s = 5
_SERVE_WAIT_S = 5
# @tunable l1.asy_ntp_client_state_poll_ms = 20
_STATE_POLL_MS = 20
# @tunable l1.asy_ntp_client_synced_poll_tries = 50
_SYNCED_POLL_TRIES = 50
# @tunable l1.asy_ntp_client_no_reply_fetch_timeout_ms = 100
_FETCH_TIMEOUT_NO_REPLY_MS = 100
# @tunable l1.ntp_wifi_dns_integration_past_fetch_timeout_ms = 150
_PAST_FETCH_TIMEOUT_MS = 150
# @tunable l1.ntp_wifi_dns_integration_failure_cycles = 8
_FAILURE_CYCLES = 8
_SETTLE_YIELDS = 200  # a bound in scheduling steps for one hand-over between the NTP and WiFi tasks


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _wlan(conn: WifiService) -> "Any":  # Any is the point here, not an omission - see below
    # _wlan(conn) is typed against the real network.WLAN stub (pyproject.toml's tests/network.py exclude),
    # but at runtime MICROPYPATH constructs tests/network.py's fake, exposing test-only attributes the real
    # stub has no reason to declare. Narrows to Any once here, matching test_asy_wifi_service.py's helper.
    return conn._wlan


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("integ")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def make_conn(cfg_path: "str | None" = None) -> WifiService:
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), cfg_path=cfg_path)
    run(conn.setup())
    return conn


def make_ntp(
    conn: WifiService,
    ntp_host: str,
    cfg_path: "str | None" = None,
    ntp_fetch_timeout_ms: int = 5000,  # the generated wiring's fetch timeout
) -> NTPClient:
    # Exactly sensortask-wozi.py's own wiring: conn.get_wifi_mode_lock()/network_available_locked/
    # get_dns_server_ip passed straight through as ntp's own constructor arguments - the real
    # bound methods, not a lambda standing in for them.
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        # One single f-string, not a plain-string-literal-adjacent-to-an-f-string concatenation -
        # same MicroPython gotcha test_asy_ntp_client.py's own _client_with_offsets() documents.
        f.write(f'{{"NTPHost": "{ntp_host}", "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 0, "DSTOffset": 0, "DNSFallback": ""}}')
    timing = NtpTiming(500, 1, ntp_fetch_timeout_ms, 10, 600)
    ntp = NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip, timing, cfg_path=cfg_path)
    run(ntp.setup())
    return ntp


def _link_up(conn: WifiService, dns_server: str = "192.0.2.53") -> None:
    # The fake network.WLAN in a connected STA state with a DHCP lease, bypassing the real _connect_loop().
    wlan = _wlan(conn)
    wlan._connected = True
    wlan._status = network.STAT_GOT_IP
    wlan._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", dns_server)


async def _snapshot_step(conn: WifiService) -> None:
    # One 1 Hz networking snapshot, taken under wifi_mode_lock as the real uptime loop takes it.
    async with conn.get_wifi_mode_lock():
        await conn._update_wifi_snapshot(connected=True)


def connect_wlan(conn: WifiService, dns_server: str = "192.0.2.53") -> None:
    # The link up, then one snapshot step: every getter reads the snapshot, so the DHCP server reaches NTP only through it.
    _link_up(conn, dns_server)
    run(_snapshot_step(conn))


async def _tick(flag: "asyncio.ThreadSafeFlag", times: int = 1) -> None:
    for _ in range(times):
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _last_err(counter: "ErrorLog", field: 'Literal["ErrNum", "ErrType"]') -> "int | str | None":
    # Same helper as tests/test_asy_ntp_client.py's own _last_err() - duplicated, not imported,
    # matching this file's existing convention of small per-file test helpers.
    value = counter["NTP"][field]  # ErrNum/ErrType are list-shaped once _error_check() has run once
    assert isinstance(value, list)
    return value[-1] if value else None


# ---------------------------------------------------------------------------
# Value propagation: conn.get_dns_server_ip()'s real, WLAN-derived value, published by the 1 Hz snapshot,
# reaching resolve_ipv4()'s dns_servers argument - the exact seam the lock-collision bug lived in.
# ---------------------------------------------------------------------------


class _RecordingResolver:
    def __init__(self, return_value: "str | None") -> None:
        self.calls: list[tuple[str, tuple[str, ...], int, int]] = []
        self.return_value = return_value

    async def __call__(self, host: str, dns_servers: "tuple[str, ...]" = (), timeout_ms: int = 0, tries: int = 0, *, pr: "PrintLogHistory") -> "str | None":
        self.calls.append((host, dns_servers, timeout_ms, tries))
        return self.return_value


def test_dns_server_ip_flows_from_a_connected_real_wifi_service_into_resolve_ipv4() -> None:
    conn = make_conn()
    connect_wlan(conn, dns_server="203.0.113.9")
    ntp = make_ntp(conn, "pool.ntp.org")
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # a module-attribute swap, as test_asy_ntp_client.py makes it; restored below
    try:

        async def scenario() -> None:
            task = asyncio.create_task(ntp._sync_loop())
            await _tick(ntp._ntp_sync_trigger_event, 1)
            await _cancel(task)

        run(scenario())
    finally:
        ntpmod.resolve_ipv4 = original
    # The real conn-derived DNS server IP - not None, not a stand-in lambda's value - reached the
    # resolver call. This is the exact value that used to always arrive as None before the fix.
    assert recorder.calls == [("pool.ntp.org", ("203.0.113.9",), 500, 1)]


def test_dns_server_ip_unset_sentinel_flows_through_a_real_never_configured_wifi_service() -> None:
    # A fresh device that has never gotten a DHCP lease: WLAN.ifconfig()'s documented default is all
    # "0.0.0.0" fields, and this proves that value, not filtered by get_dns_server_ip() itself, reaches
    # resolve_ipv4() as-is. resolve_ipv4()'s own "0.0.0.0" skip is covered at its own unit level.
    conn = make_conn()
    connect_wlan(conn, dns_server="0.0.0.0")
    ntp = make_ntp(conn, "pool.ntp.org")
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder
    try:

        async def scenario() -> None:
            task = asyncio.create_task(ntp._sync_loop())
            await _tick(ntp._ntp_sync_trigger_event, 1)
            await _cancel(task)

        run(scenario())
    finally:
        ntpmod.resolve_ipv4 = original
    assert recorder.calls == [("pool.ntp.org", ("0.0.0.0",), 500, 1)]


def test_get_dns_server_ip_real_wlan_exception_is_treated_as_none_not_propagated() -> None:
    # A snapshot step whose ifconfig() read raises publishes no DHCP server (print-only, never persisted or
    # raised); _safe_get_dns_server() then answers a clean None and resolution goes on without a hint.
    conn = make_conn()
    connect_wlan(conn)
    _wlan(conn).raise_on["ifconfig"] = OSError("simulated WLAN hardware fault")
    run(_snapshot_step(conn))
    ntp = make_ntp(conn, "127.0.0.1")  # literal IP - resolve_ipv4() never touches the network
    dns_server = run(ntp._safe_get_dns_server())
    assert dns_server is None
    result = run(ntp._resolve_ntp_server("127.0.0.1", dns_server, ""))
    assert result == ("127.0.0.1", _NTP_PORT)  # resolution still proceeds despite the WLAN fault


# ---------------------------------------------------------------------------
# Calling/locking: the two real objects genuinely share one wifi_mode_lock instance - proves the
# mutual-exclusion coordination the shared lock exists for actually holds across both files, not
# just within one file's own isolated tests.
# ---------------------------------------------------------------------------


def test_wifi_mode_lock_is_the_same_instance_on_both_real_objects() -> None:
    conn = make_conn()
    ntp = make_ntp(conn, "pool.ntp.org")
    assert ntp.wifi_mode_lock is conn.get_wifi_mode_lock()


def test_ntp_sync_holding_the_lock_blocks_a_concurrent_real_wifi_mode_switch() -> None:
    conn = make_conn()
    connect_wlan(conn)
    server = FakeNtpServer()  # bound, never answering: _fetch_ntp_reply() waits out its 5 s fetch timeout in the lock
    ntp = make_ntp(conn, "127.0.0.1")

    async def scenario() -> bool:
        with redirect_udp_port(ntpmod, _NTP_PORT, server.port):
            task = asyncio.create_task(ntp._sync_loop())
            ntp._ntp_sync_trigger_event.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert conn.wifi_mode_lock.locked() is True  # ntp is genuinely holding conn's own lock
            assert conn.get_dns_server_ip() == "192.0.2.53"  # the snapshot from before the hold, never None for the lock
            blocked = False
            try:
                await asyncio.wait_for(conn._select_wifi_mode(network.AP_IF), _LOCK_BLOCKED_WAIT_S)
            except asyncio.TimeoutError:
                blocked = True  # conn's own mode switch is genuinely stuck waiting on the shared lock
            await _cancel(task)
        return blocked

    try:
        assert run(scenario()) is True
    finally:
        server.close()


# ---------------------------------------------------------------------------
# The NTP attempt's hold of wifi_mode_lock, seen from every waiter (SPECIFICATION.md C.8's hold table):
# the getters serve the snapshot, the uptime keeps counting, and the WiFi loop resumes once it ends.
# ---------------------------------------------------------------------------

_TICKS_PERIOD = 1 << 30  # rp2's ticks_ms() wrap: py/mpconfig.h's MICROPY_PY_TIME_TICKS_PERIOD on a 32-bit small int


class _DrivenTime:
    # Stands in for asy_base_classes' `time` so TickSeconds (the WiFi uptime) reads driven ticks; every
    # other name reaches the real module. Installed before the service is built, restored on exit.
    def __init__(self) -> None:
        self.now = 0
        self._saved: object = None

    def __enter__(self) -> "Self":
        self._saved = asy_base_classes.time
        asy_base_classes.time = self  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        asy_base_classes.time = self._saved  # type: ignore[assignment]

    def __getattr__(self, name: str) -> object:
        return getattr(time, name)

    def advance_s(self, seconds: int) -> None:
        self.now = self.ticks_add(self.now, seconds * 1000)

    def ticks_add(self, a: int, b: int) -> int:
        return (a + b) & (_TICKS_PERIOD - 1)

    def ticks_diff(self, a: int, b: int) -> int:
        return ((a - b + _TICKS_PERIOD // 2) & (_TICKS_PERIOD - 1)) - _TICKS_PERIOD // 2

    def ticks_ms(self) -> int:
        return self.now


class _FastAsyncSleep:
    # The WiFi loop's refresh, settle and poll sleeps (seconds each) become one yield for the block, so its
    # iterations run as scheduling steps. asyncio.sleep is process-wide, so it is restored however the block exits.
    def __enter__(self) -> "Self":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # a module-attribute swap for the block, not a caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


class _GatedResolver:
    # Stands in for resolve_ipv4(): parks the NTP attempt, and so its hold of wifi_mode_lock, until release().
    def __init__(self) -> None:
        self.entered = False
        self.servers: tuple[str, ...] | None = None
        self._gate = asyncio.Event()

    async def __call__(self, host: str, dns_servers: "tuple[str, ...]" = (), timeout_ms: int = 0, tries: int = 0, *, pr: "PrintLogHistory") -> "str | None":
        self.entered = True
        self.servers = dns_servers
        await self._gate.wait()
        return None  # no answer: the attempt ends as a resolution failure, one NTP_DNS entry

    def release(self) -> None:
        self._gate.set()


async def _until(predicate: "Callable[[], bool]") -> bool:
    # A bound in yields, not milliseconds: every step waited for here is a hand-over between tasks.
    for _ in range(_SETTLE_YIELDS):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


async def _settle() -> None:
    # The whole _until() bound, spent: long enough for any task that could run to have run.
    for _ in range(_SETTLE_YIELDS):
        await asyncio.sleep(0)


async def _ntp_holding_the_lock(ntp: NTPClient, resolver: _GatedResolver) -> "asyncio.Task[None]":
    # Starts the real sync task and returns once its attempt sits in the resolver, inside wifi_mode_lock.
    task = asyncio.create_task(ntp._sync_loop())
    ntp._ntp_sync_trigger_event.set()
    assert await _until(lambda: resolver.entered)
    assert ntp.wifi_mode_lock.locked() is True
    return task


def test_a_held_lock_serves_the_snapshot_and_uptime_keeps_counting() -> None:
    with _DrivenTime() as clock:
        conn = make_conn()
        connect_wlan(conn)
        ntp = make_ntp(conn, "pool.ntp.org")  # a host name: the attempt waits in the resolver, inside the lock
        resolver = _GatedResolver()

        async def scenario() -> "tuple[WIFI, WIFI, int, int, str | None, tuple[str, ...] | None]":
            uptime_task = asyncio.create_task(conn._uptime_loop())
            await asyncio.sleep(0)  # the loop starts its uptime at the driven clock's zero
            clock.advance_s(1)
            await _tick(conn._time_counter_trigger_event)  # one 1 Hz step before the hold
            before = await conn.get_data()
            uptime_before = await conn.get_wifi_uptime()
            sync_task = await _ntp_holding_the_lock(ntp, resolver)
            for _ in range(3):  # three seconds pass while the NTP attempt holds the lock
                clock.advance_s(1)
                await _tick(conn._time_counter_trigger_event)
            assert conn.wifi_mode_lock.locked() is True  # still held: the uptime loop's own step waits on it
            held = await asyncio.wait_for(conn.get_data(), _LOCK_BLOCKED_WAIT_S)  # served at once, never waiting
            uptime_held = await conn.get_wifi_uptime()
            dns_held = conn.get_dns_server_ip()
            resolver.release()
            assert await _until(lambda: not conn.wifi_mode_lock.locked())
            await _cancel(sync_task)
            await _cancel(uptime_task)
            return before, held, uptime_before, uptime_held, dns_held, resolver.servers

        saved = ntpmod.resolve_ipv4
        ntpmod.resolve_ipv4 = resolver  # a module-attribute swap, restored below
        try:
            before, held, uptime_before, uptime_held, dns_held, servers = run(scenario())
        finally:
            ntpmod.resolve_ipv4 = saved
    assert uptime_before == 1  # one measured second before the hold
    assert held == before  # the pre-attempt snapshot, no field emptied by the hold
    assert (held.Connected, held.IP, held.Subnet, held.Gateway, held.DNS) == (True, "10.0.0.5", "255.255.255.0", "10.0.0.1", "192.0.2.53")
    assert dns_held == "192.0.2.53"
    assert servers == ("192.0.2.53",)  # the DHCP server alone: the stored DNSFallback is empty
    assert uptime_held == uptime_before + 3  # measured ticks: the hold costs the uptime nothing


def _sta_conn() -> WifiService:
    # An SSID stored and a fake radio that joins on connect(): the real _connect_loop() reaches a steady link.
    conn = make_conn()
    assert run(conn._set_dict_cfg({"SSID": "HomeNet", "PW": "supersecret"}, conn.get_cfg_schema())) == {"SSID": "Valid", "PW": "Valid"}
    wlan = _wlan(conn)

    def joins(ssid: "str | None" = None, password: "str | None" = None) -> None:
        wlan.connect_calls.append((ssid, password))
        _link_up(conn)

    wlan.connect = joins
    return conn


def _counted_sta_steps(conn: WifiService) -> "list[int]":
    # Counts the WiFi loop's completed STA steps (each one wifi_mode_lock hold) through the real method.
    steps = [0]
    real = conn._run_sta_mode

    async def counted() -> None:
        await real()
        steps[0] += 1

    conn._run_sta_mode = counted  # type: ignore[method-assign]  # wraps, never replaces, the real step
    return steps


def test_the_wifi_loop_resumes_after_the_lock_without_a_fault() -> None:
    conn = _sta_conn()
    steps = _counted_sta_steps(conn)
    ntp = make_ntp(conn, "pool.ntp.org")
    resolver = _GatedResolver()

    async def scenario() -> "tuple[int, int, bool, bool]":
        wifi_task = asyncio.create_task(conn._connect_loop())
        assert await _until(lambda: conn._conn_phase == _PHASE_STA_ESTABLISHED and steps[0] >= 2)
        sync_task = await _ntp_holding_the_lock(ntp, resolver)
        held_steps = steps[0]
        await _settle()  # with the lock held throughout
        blocked_steps = steps[0] - held_steps
        resolver.release()
        resumed = await _until(lambda: steps[0] > held_steps)
        hw_op_failed = conn._hw_op_failed
        await _cancel(sync_task)
        alive = not wifi_task.done()
        await _cancel(wifi_task)
        return blocked_steps, steps[0] - held_steps, resumed and alive, hw_op_failed

    saved = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = resolver  # a module-attribute swap, restored below
    try:
        with _FastAsyncSleep():
            blocked_steps, resumed_steps, resumed, hw_op_failed = run(scenario())
    finally:
        ntpmod.resolve_ipv4 = saved
    assert blocked_steps == 0  # the loop waited on the lock for the whole hold
    assert resumed is True and resumed_steps >= 1  # and ran on once it ended
    assert hw_op_failed is False
    assert run(conn.get_error_counter())["WIFI"]["ErrCount"] == 0  # the wait is no fault: nothing logged


def test_a_reconnect_asked_during_the_hold_runs_in_the_next_wifi_iteration() -> None:
    conn = _sta_conn()
    steps = _counted_sta_steps(conn)
    ntp = make_ntp(conn, "pool.ntp.org")
    resolver = _GatedResolver()

    async def scenario() -> "tuple[bool, bool, bool, bool, bool]":
        wifi_task = asyncio.create_task(conn._connect_loop())
        assert await _until(lambda: conn._conn_phase == _PHASE_STA_ESTABLISHED and steps[0] >= 2)
        sync_task = await _ntp_holding_the_lock(ntp, resolver)
        conn.reconnect_wifi()  # a PUT's post hook: it only flags the reconnect, it never waits on the lock
        flagged = conn._reconn_wifi
        await _settle()  # with the lock held throughout
        early = _wlan(conn).disconnect_called
        resolver.release()
        acted = await _until(lambda: _wlan(conn).disconnect_called and not conn._reconn_wifi)
        relinked = await _until(lambda: conn._conn_phase == _PHASE_STA_ESTABLISHED)
        await _cancel(sync_task)
        alive = not wifi_task.done()
        await _cancel(wifi_task)
        return flagged, early, acted, relinked, alive

    saved = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = resolver  # a module-attribute swap, restored below
    try:
        with _FastAsyncSleep():
            flagged, early, acted, relinked, alive = run(scenario())
    finally:
        ntpmod.resolve_ipv4 = saved
    assert flagged is True
    assert early is False  # nothing touched the radio while the NTP attempt held it
    assert acted is True and relinked is True and alive is True  # the next iteration reconnected
    assert run(conn.get_error_counter())["WIFI"]["ErrCount"] == 0


def test_no_socket_is_built_without_a_dns_candidate() -> None:
    # The "no test reaches a public resolver" property at L1: an empty DNSFallback, a 0.0.0.0 DHCP server and
    # a host name leave nothing to ask. A loopback DHCP server then builds exactly one, proving the count is live.
    conn = make_conn()
    connect_wlan(conn, dns_server="0.0.0.0")
    ntp = make_ntp(conn, "pool.ntp.org")

    async def attempt(errors_before: int) -> int:
        task = asyncio.create_task(ntp._sync_loop())
        ntp._ntp_sync_trigger_event.set()
        for _ in range(_SYNCED_POLL_TRIES):  # until the attempt has logged its resolution failure
            if (await ntp.get_error_counter())["NTP"]["ErrCount"] > errors_before:
                break
            await asyncio.sleep_ms(_STATE_POLL_MS)
        await _cancel(task)
        return (await ntp.get_error_counter())["NTP"]["ErrCount"]

    with redirect_udp_port(asy_dns_client, _DNS_PORT, make_port()) as dns_sockets:  # an unbound loopback port
        errors = run(attempt(0))
        none_built = dns_sockets.constructed
        connect_wlan(conn, dns_server="127.0.0.1")
        errors_after_control = run(attempt(errors))
    assert none_built == 0
    assert errors == 1
    assert dns_sockets.constructed == 1
    assert errors_after_control == 2
    assert _last_err(run(ntp.get_error_counter()), "ErrNum") == code("E", "NTP_DNS")


# ---------------------------------------------------------------------------
# Full real chain, end to end: real conn + real ntp, a real UDP round trip, no monkeypatched
# resolver - the closest thing to production wiring this test suite can reach without root.
# ---------------------------------------------------------------------------

# Below the OS ephemeral range (32768-60999) so a concurrently-running ephemeral socket can
# never be assigned this port - see scripts/test.sh's own TEST_PARALLELISM comment.
_next_port = 25000


def make_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


class FakeNtpServer:
    def __init__(self) -> None:
        self.port = make_port()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket.getaddrinfo("127.0.0.1", self.port)[0][-1])  # a raw socket: this build's bind() takes the sockaddr
        self.sock.setblocking(False)
        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLIN)

    def close(self) -> None:
        self.sock.close()

    async def serve_once(self, reply: bytes) -> None:
        for _ in range(1000):
            ready = any(event & select.POLLIN for _fd, event in self.poller.ipoll(0))
            if ready:
                try:
                    _data, from_addr = self.sock.recvfrom(1024)
                except OSError:
                    await asyncio.sleep_ms(10)
                    continue
                self.sock.sendto(reply, from_addr)
                return
            await asyncio.sleep_ms(10)


_NTP_EPOCH_DELTA = 2208988800


def make_ntp_reply(unix_seconds: int) -> bytes:
    ntp_seconds = (unix_seconds + _NTP_EPOCH_DELTA) & 0xFFFFFFFF
    header = b"\x1c\x01" + bytes(38)  # LI=0/VN=3/Mode=4(server), Stratum=1(genuinely synchronized)
    transmit = struct.pack("!I", ntp_seconds) + bytes(4)
    packet = header + transmit
    assert len(packet) == 48
    return packet


def test_full_chain_reaches_synced_state_via_a_real_wifi_service_and_a_literal_ip_ntp_host() -> None:
    conn = make_conn()
    connect_wlan(conn)
    server = FakeNtpServer()
    ntp = make_ntp(conn, "127.0.0.1")
    reply = make_ntp_reply(int(time.time()))

    async def scenario() -> "tuple[bool, int | None]":
        try:
            with redirect_udp_port(ntpmod, _NTP_PORT, server.port):
                task = asyncio.create_task(ntp._sync_loop())
                server_task = asyncio.create_task(server.serve_once(reply))
                ntp._ntp_sync_trigger_event.set()
                await asyncio.wait_for(server_task, _SERVE_WAIT_S)
                for _ in range(_SYNCED_POLL_TRIES):
                    if await ntp.ntp_issynced():
                        break
                    await asyncio.sleep_ms(_STATE_POLL_MS)
                synced = await ntp.ntp_issynced()
                last_sync = await ntp.get_last_ntp_sync()
                await _cancel(task)
                return synced, last_sync
        finally:
            server.close()

    synced, last_sync = run(scenario())
    assert synced is True
    assert last_sync == 0


def test_full_chain_degrades_cleanly_when_wifi_reports_connected_but_the_ntp_server_never_answers() -> None:
    # The real-hardware finding this proves at the mock tier (BACKLOG.md open question 6, closed
    # 2026-09-04): the CYW43 firmware and lwIP stack can report a link as fully connected while it is dead -
    # a real arping probe got zero responses from a DUT `iw station dump` called associated.
    #
    # connect_wlan(conn) below puts the real WifiService's WLAN into exactly that "looks connected" state,
    # so conn.network_available_locked(), driven through the real object rather than a lambda stand-in, genuinely
    # reports True throughout.
    #
    # The FakeNtpServer is bound and reachable, a real socket on a real port, but its serve_once() is never
    # called, so a real send genuinely goes unanswered - the same observable shape a dead-but-reported-alive
    # link produces. The code only ever sees "sent, then nothing back within the timeout" either way.
    conn = make_conn()
    connect_wlan(conn)
    server = FakeNtpServer()
    ntp = make_ntp(conn, "127.0.0.1", ntp_fetch_timeout_ms=_FETCH_TIMEOUT_NO_REPLY_MS)

    async def scenario() -> "tuple[bool, bool, int, int, ErrorLog]":
        try:
            with redirect_udp_port(ntpmod, _NTP_PORT, server.port):
                task = asyncio.create_task(ntp._sync_loop())
                # Far past the old five-failure give-up, each cycle bounded by the 100ms fetch timeout.
                for _ in range(_FAILURE_CYCLES):
                    ntp._ntp_sync_trigger_event.set()
                    await asyncio.sleep_ms(_PAST_FETCH_TIMEOUT_MS)
                still_running = not task.done()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return still_running, await ntp.ntp_issynced(), ntp._retry_wait_s, ntp._retry_max_s, await ntp.get_error_counter()
        finally:
            server.close()

    still_running, synced, wait_s, max_s, counter = run(scenario())
    # Never synced, but the task handles it (Part C.7.2): still running, backed off to its cap, and the
    # silent timeout persisted once for the run (C.7.1's repeat rule) while counted every time.
    assert still_running is True
    assert synced is False
    assert wait_s == max_s
    assert counter["NTP"]["ErrCount"] == 8
    assert counter["NTP"]["ErrNum"] == [0] * 9 + [code("E", "NTP_NO_REPLY")]


def test_full_chain_stays_unsynced_when_the_real_wifi_service_reports_network_unavailable() -> None:
    # conn never connected (default fake WLAN state: disconnected, STAT_IDLE) - conn.network_available_locked()
    # genuinely returns False, driven through the real object rather than a lambda stand-in like
    # tests/test_asy_ntp_client.py's own test_run_sync_attempt_network_unavailable_skips_everything_downstream.
    conn = make_conn()
    ntp = make_ntp(conn, "127.0.0.1")

    async def scenario() -> bool:
        task = asyncio.create_task(ntp._sync_loop())
        await _tick(ntp._ntp_sync_trigger_event, 1)
        synced = await ntp.ntp_issynced()
        await _cancel(task)
        return synced

    assert run(scenario()) is False


def test_dns_resolution_with_no_candidate_persists_the_dns_error() -> None:
    # Every candidate is unset - "0.0.0.0" from the snapshot and the stored empty DNSFallback - so
    # resolve_ipv4()'s ipv4_to_int() guard asks no server, through the real chain, not a synthetic resolver.
    conn = make_conn()
    connect_wlan(conn, dns_server="0.0.0.0")
    ntp = make_ntp(conn, "bogus.invalid")

    async def scenario() -> None:
        task = asyncio.create_task(ntp._sync_loop())
        await _tick(ntp._ntp_sync_trigger_event, 1)
        await _cancel(task)

    run(scenario())
    assert run(ntp.ntp_issynced()) is False
    counter = run(ntp.get_error_counter())
    err_num, err_type = counter["NTP"]["ErrNum"], counter["NTP"]["ErrType"]
    assert isinstance(err_num, list) and isinstance(err_type, list)
    assert err_num[-1] == code("E", "NTP_DNS")  # the last entry now: no streak counter logs after it any more
    assert err_type[-1] == "E"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
