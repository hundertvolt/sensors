"""Integration tests across the real three-file chain: AsyConnTime -> AsyNtpClient -> asy_dns_client.py's resolve_ipv4(). Every other test file replaces peers with a lambda/recorder; this file wires real instances (matching sensortask-wozi.py) to prove the *linked* behavior - calling order, error handling, value propagation - a lambda-based unit test can't observe.
Found and fixed a real bug this way: AsyNtpClient used to call get_dns_server_ip() after acquiring the shared wifi_mode_lock, so its own locked() gate always saw True and always returned None. Fixed via _safe_get_dns_server(), called before acquiring the lock."""
# No real port-53/port-123-privileged end-to-end test is attempted (needs root, not CI-portable).
# Tests needing a real UDP round trip use a literal-IP NTP_Host (sidesteps DNS/port 53 entirely) or
# malformed DNS-server entries (skipped instantly by resolve_ipv4()'s own guard, no network wait
# needed). Real UDP behavior of resolve_ipv4()/AsyUDPSocket is already covered by
# tests/test_asy_dns_client.py and tests/test_asy_ntp_client.py.

import asyncio
import os
import select
import socket
import struct
import time

import network

import asy_ntp_client as ntpmod
from asy_ntp_client import AsyNtpClient
from asy_wifi_service import AsyConnTime

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


def _wlan(conn: AsyConnTime) -> "Any":
    # _wlan(conn) is typed against the real network.WLAN stub (see pyproject.toml's own
    # tests/network.py exclude comment); at runtime MICROPYPATH ordering constructs
    # tests/network.py's fake instead, which exposes test-only attributes (raise_on, _status,
    # _ifconfig, _connected, ...) the real stub has no reason to declare. Narrows to Any once,
    # here, matching test_asy_wifi_service.py's own identical helper.
    return conn.wlan


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # Sweeps pre-existing <prefix>* scratch dirs left behind by an earlier scripts/test.sh run on
    # this machine - _next_dir always restarts at 0 per process, so without this a later run
    # silently reuses an earlier run's real, persisted config_*.cfg files instead of a genuinely
    # fresh directory. See tests/test_sensortask_wozi.py's own _sweep_stale_tmp_dirs() for the full
    # root-cause writeup (this exact _tmp_cfg_dir() shape is copy-pasted across every test file with
    # its own _TMP_DIR/_next_dir pair - same fix applied uniformly to each).
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


_sweep_stale_tmp_dirs("integ_")


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass  # already gone, or genuinely not removable - not this helper's problem


def _tmp_cfg_dir() -> str:
    # One fresh directory per call, shared by both services below - AsyConnTime names its own
    # file "config_WIFI.cfg" and AsyNtpClient names its own "config_NTP.cfg" (both from
    # base_classes.py's SensorReaderConfig), so the two never collide even sharing one directory.
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/integ_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    _remove_any(path + "/config_WIFI.cfg")
    _remove_any(path + "/config_NTP.cfg")
    return path + "/"


def make_conn(cfg_path: "str | None" = None) -> AsyConnTime:
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    conn = AsyConnTime(led_pin=None, cfg_path=cfg_path)
    run(conn.cfgmgr.setup())
    return conn


def make_ntp(conn: AsyConnTime, ntp_host: str, cfg_path: "str | None" = None) -> AsyNtpClient:
    # Exactly sensortask-wozi.py's own wiring: conn.get_wifi_mode_lock()/network_available/
    # get_dns_server_ip passed straight through as ntp's own constructor arguments - the real
    # bound methods, not a lambda standing in for them.
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        # One single f-string, not a plain-string-literal-adjacent-to-an-f-string concatenation -
        # same MicroPython gotcha test_asy_ntp_client.py's own _client_with_offsets() documents.
        f.write(f'{{"NTP_Host": "{ntp_host}", "NTP_Offset_S": 0, "NTP_Interv_H": 12, "GMTOffset": 0, "DSTOffset": 0}}')
    ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip, cfg_path=cfg_path)
    run(ntp.cfgmgr.setup())
    return ntp


def connect_wlan(conn: AsyConnTime, dns_server: str = "192.0.2.53") -> None:
    # Puts the real fake network.WLAN into a normal, connected STA state - the same shape
    # network_available()/get_dns_server_ip() expect in production (see asy_wifi_service.py's own
    # _conn_phase/_wlan_status_or_none()). Bypasses the real wlan_connect() state machine (out of
    # scope here - test_asy_wifi_service.py already covers that machine in isolation) to focus
    # purely on the two accessor methods this file's integration actually depends on.
    _wlan(conn)._connected = True
    _wlan(conn)._status = network.STAT_GOT_IP
    _wlan(conn)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", dns_server)


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


# ---------------------------------------------------------------------------
# Value propagation: conn.get_dns_server_ip()'s real, WLAN-derived value reaching
# resolve_ipv4()'s dns_servers argument - the exact seam the lock-collision bug lived in.
# ---------------------------------------------------------------------------


class _RecordingResolver:
    def __init__(self, return_value: "str | None") -> None:
        self.calls: list[tuple[str, tuple[str, ...], int, int]] = []
        self.return_value = return_value

    async def __call__(self, host: str, dns_servers: "tuple[str, ...]" = (), timeout_ms: int = 0, tries: int = 0) -> "str | None":
        self.calls.append((host, dns_servers, timeout_ms, tries))
        return self.return_value


def test_dns_server_ip_flows_from_a_connected_real_wifi_service_into_resolve_ipv4() -> None:
    conn = make_conn()
    connect_wlan(conn, dns_server="203.0.113.9")
    ntp = make_ntp(conn, "pool.ntp.org")
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]  # deliberate monkeypatch, same as test_asy_ntp_client.py's own
    try:

        async def scenario() -> None:
            task = asyncio.create_task(ntp.asy_ntp_time())
            await _tick(ntp.ntp_sync_trigger_event, 1)
            await _cancel(task)

        run(scenario())
    finally:
        ntpmod.resolve_ipv4 = original
    # The real conn-derived DNS server IP - not None, not a stand-in lambda's value - reached the
    # resolver call. This is the exact value that used to always arrive as None before the fix.
    assert recorder.calls == [("pool.ntp.org", ("203.0.113.9",), 500, 1)]


def test_dns_server_ip_unset_sentinel_flows_through_a_real_never_configured_wifi_service() -> None:
    # A fresh device that has never gotten a DHCP lease: WLAN.ifconfig()'s real documented default
    # is all "0.0.0.0" fields (see asy_wifi_service.py's own fake network.WLAN default) - proves
    # this real value (not filtered by get_dns_server_ip() itself) reaches resolve_ipv4() as-is;
    # resolve_ipv4()'s own "0.0.0.0" skip is already covered at that file's own unit level
    # (tests/test_asy_dns_client.py), this just proves the value actually gets there unmodified.
    conn = make_conn()
    connect_wlan(conn, dns_server="0.0.0.0")
    ntp = make_ntp(conn, "pool.ntp.org")
    recorder = _RecordingResolver("9.9.9.9")
    original = ntpmod.resolve_ipv4
    ntpmod.resolve_ipv4 = recorder  # type: ignore[assignment]
    try:

        async def scenario() -> None:
            task = asyncio.create_task(ntp.asy_ntp_time())
            await _tick(ntp.ntp_sync_trigger_event, 1)
            await _cancel(task)

        run(scenario())
    finally:
        ntpmod.resolve_ipv4 = original
    assert recorder.calls == [("pool.ntp.org", ("0.0.0.0",), 500, 1)]


def test_get_dns_server_ip_real_wlan_exception_is_treated_as_none_not_propagated() -> None:
    # conn.get_wlan_ifconfig() degrades a real wlan.ifconfig() exception to None - an
    # observation-tier query, so it degrades via self.pr.err() (debug-level only, never persisted
    # to get_error_counter(); see asy_wifi_service.py's own module docstring and
    # test_get_dns_server_ip_returns_none_on_exception in test_asy_wifi_service.py) rather than
    # raising or logging a real error. Proves that degradation, driven through the real object,
    # still reaches _safe_get_dns_server() as a clean None rather than an exception - resolution
    # proceeds with no server hint instead of the WLAN fault surfacing as a crash.
    conn = make_conn()
    connect_wlan(conn)
    _wlan(conn).raise_on["ifconfig"] = OSError("simulated WLAN hardware fault")
    ntp = make_ntp(conn, "127.0.0.1")  # literal IP - resolve_ipv4() never touches the network
    run(ntp.pr.setup())
    dns_server = run(ntp._safe_get_dns_server())
    assert dns_server is None
    result = run(ntp._resolve_ntp_server("127.0.0.1", dns_server))
    assert result == ("127.0.0.1", 123)  # resolution still proceeds despite the WLAN fault


# ---------------------------------------------------------------------------
# Calling/locking: the two real objects genuinely share one wifi_mode_lock instance - proves the
# mutual-exclusion coordination the shared lock exists for actually holds across both files, not
# just within one file's own isolated tests.
# ---------------------------------------------------------------------------


def test_wifi_mode_lock_is_the_same_instance_on_both_real_objects() -> None:
    conn = make_conn()
    ntp = make_ntp(conn, "pool.ntp.org")
    assert ntp.wifi_mode_lock is conn.wifi_mode_lock


def test_ntp_sync_holding_the_lock_blocks_a_concurrent_real_wifi_mode_switch() -> None:
    conn = make_conn()
    connect_wlan(conn)
    unreachable_addr = make_addr()  # nobody listens here - _fetch_ntp_reply() blocks for its own
    # _NTP_CONN_TIMEOUT (5s), giving this test a window to observe the lock genuinely held.
    ntp = make_ntp(conn, unreachable_addr[0])

    async def scenario() -> bool:
        task = asyncio.create_task(ntp.asy_ntp_time())
        ntp.ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert conn.wifi_mode_lock.locked() is True  # ntp is genuinely holding conn's own lock
        assert conn.get_dns_server_ip() is None  # conn's own accessor correctly degrades right now
        blocked = False
        try:
            await asyncio.wait_for(conn._select_wifi_mode(network.AP_IF), 0.05)
        except asyncio.TimeoutError:
            blocked = True  # conn's own mode switch is genuinely stuck waiting on the shared lock
        await _cancel(task)
        return blocked

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# Full real chain, end to end: real conn + real ntp, a real UDP round trip, no monkeypatched
# resolver - the closest thing to production wiring this test suite can reach without root.
# ---------------------------------------------------------------------------

_next_port = 55000


def make_addr() -> "tuple[str, int]":
    global _next_port
    _next_port += 1
    return socket.getaddrinfo("127.0.0.1", _next_port)[0][-1]  # type: ignore[return-value]


def make_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


class _RedirectNtpNetworking:
    # Same combined Unix-port-only workaround as test_asy_ntp_client.py's own class of the same
    # name: redirects _NTP_UDP_PORT away from the real privileged port 123, and pre-resolves
    # AsyUDPSocket's addr since this build's raw connect() rejects a plain (host, port) tuple.
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

    def close(self) -> None:
        self.sock.close()


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
            with server.redirect_resolution():
                task = asyncio.create_task(ntp.asy_ntp_time())
                server_task = asyncio.create_task(server.serve_once(reply))
                ntp.ntp_sync_trigger_event.set()
                await asyncio.wait_for(server_task, 5)
                for _ in range(50):
                    if await ntp.ntp_issynced():
                        break
                    await asyncio.sleep_ms(20)
                synced = await ntp.ntp_issynced()
                last_sync = await ntp.get_last_ntp_sync()
                await _cancel(task)
                return synced, last_sync
        finally:
            server.close()

    synced, last_sync = run(scenario())
    assert synced is True
    assert last_sync == 0


def test_full_chain_stays_unsynced_when_the_real_wifi_service_reports_network_unavailable() -> None:
    # conn never connected (default fake WLAN state: disconnected, STAT_IDLE) - conn.network_available()
    # genuinely returns False, driven through the real object rather than a lambda stand-in like
    # tests/test_asy_ntp_client.py's own test_run_sync_attempt_network_unavailable_skips_everything_downstream.
    conn = make_conn()
    ntp = make_ntp(conn, "127.0.0.1")

    async def scenario() -> bool:
        task = asyncio.create_task(ntp.asy_ntp_time())
        await _tick(ntp.ntp_sync_trigger_event, 1)
        synced = await ntp.ntp_issynced()
        await _cancel(task)
        return synced

    assert run(scenario()) is False


def test_dns_resolution_totally_unreachable_through_the_real_chain_persists_errno_12() -> None:
    # Every candidate server is malformed/unset ("0.0.0.0" from conn's own real ifconfig plus a
    # monkeypatched malformed fallback list) - resolve_ipv4()'s own _is_ipv4_literal() guard skips
    # each one instantly (no network wait needed), reaching its own "no valid server anywhere"
    # None return through the real three-file chain rather than a synthetic _RecordingResolver.
    import asy_dns_client

    conn = make_conn()
    connect_wlan(conn, dns_server="0.0.0.0")
    ntp = make_ntp(conn, "bogus.invalid")
    original_fallback = asy_dns_client._FALLBACK_DNS_SERVERS
    asy_dns_client._FALLBACK_DNS_SERVERS = ("not-an-ip",)
    try:
        run(ntp.pr.setup())

        async def scenario() -> None:
            task = asyncio.create_task(ntp.asy_ntp_time())
            await _tick(ntp.ntp_sync_trigger_event, 1)
            await _cancel(task)

        run(scenario())
    finally:
        asy_dns_client._FALLBACK_DNS_SERVERS = original_fallback
    assert run(ntp.ntp_issynced()) is False
    counter = run(ntp.get_error_counter())
    # index -1, not -2, is base_classes.py's own _error_check() streak-counter log (errno=1, "Error
    # counter increased to") - it always logs once more right after a failed attempt, on top of this
    # file's own errno=12 "No valid NTP server" - see that method's own comment in base_classes.py.
    err_num, err_type = counter["NTP"]["ErrNum"], counter["NTP"]["ErrType"]
    assert isinstance(err_num, list) and isinstance(err_type, list)
    assert err_num[-2] == 12
    assert err_type[-2] == "E"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
