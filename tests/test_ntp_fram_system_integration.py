"""Integration tests across the real four-object chain: asy_wifi_service.py (asy_conn_time) ->
asy_ntp_client.py (asy_ntp_client) -> {asy_fram_manager.py's timestamped FRAM chunk,
system_service.py's SystemService} - exactly matching improved-quality/sensortask-wozi.py's real
wiring (`ntp.ntp_issynced` passed as both SGP40_Reader's own fram_ntp_callback and SystemService's
asy_ntp_callback: `SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, debug=debug)`).

tests/test_ntp_wifi_dns_integration.py already proves the wifi/ntp/dns seam with real objects
instead of lambda stand-ins; this file extends the same approach to the two *downstream* consumers
of ntp.ntp_issynced that this repo's four-branch-merge bidirectional review flagged: several
asy_fram_manager.py/system_service.py comments still attributed this callback to the legacy,
unpromoted async_connect.py, when sensortask-wozi.py's actual wiring supplies it from the
newly-promoted, audited asy_ntp_client.py instead (fixed in that same review pass - see git log).
Every individual module already has thorough lambda-based unit tests of its own (including the
"callback raises" guard: tests/test_asy_fram_manager.py's test_ntp_callback_raising_degrades_..., and
tests/test_system_service.py's test_ntp_boot_signature_callback_exception_returns_none_and_logs_once);
what those can't observe is whether the *real*, currently-wired chain - a real asy_conn_time driving
a real asy_ntp_client through an actual UDP NTP round trip - produces the value/timing behavior
asy_fram_manager.py's and system_service.py's own contracts assume, including the no-deadlock
assumption that reading a shared asy_ntp_client's sync state from a concurrent FRAM/SystemService
consumer never contends with the wifi_mode_lock a real sync attempt holds.
"""

import asyncio
import os
import select
import socket
import struct
import time

import network
from _fram_chip_fake import FakeMB85RS64V

import asy_ntp_client as ntpmod
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_ntp_client import asy_ntp_client
from asy_spi_driver import SPI
from asy_wifi_service import asy_conn_time
from crc_checks import CRC32
from system_service import SystemService

# Same one-process-per-test-file swap as every other asy_fram_* test file.
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


def _wlan(conn: asy_conn_time) -> "Any":
    # Narrows to Any once, here, matching test_asy_wifi_service.py's/test_ntp_wifi_dns_integration.py's
    # own identical helper - see their comments for why (tests/network.py's fake vs. the real stub).
    return conn.wlan


# ---------------------------------------------------------------------------
# Shared fixtures - conn/ntp construction mirrors test_ntp_wifi_dns_integration.py's own helpers
# (kept file-local rather than imported: no test file in this suite imports another, see
# tests/README.md's per-file self-containment convention); the FRAM side mirrors
# tests/test_fram_integration.py's make_manager().
# ---------------------------------------------------------------------------

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
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/ntpfram_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    _remove_any(path + "/config_WIFI.cfg")
    _remove_any(path + "/config_NTP.cfg")
    return path + "/"


def make_conn() -> asy_conn_time:
    return asy_conn_time(led_pin=None, cfg_path=_tmp_cfg_dir())


def make_ntp(conn: asy_conn_time, ntp_host: str, ntp_fetch_timeout_ms: int = 5000) -> asy_ntp_client:
    # Exactly sensortask-wozi.py's own wiring: conn.get_wifi_mode_lock()/network_available/
    # get_dns_server_ip passed straight through as ntp's own constructor arguments - the real bound
    # methods, not a lambda standing in for them.
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(f'{{"NTP_Host": "{ntp_host}", "NTP_Offset_S": 0, "NTP_Interv_H": 12, "GMTOffset": 0, "DSTOffset": 0}}')
    return asy_ntp_client(
        conn.get_wifi_mode_lock(),
        conn.network_available,
        conn.get_dns_server_ip,
        cfg_path=cfg_path,
        ntp_fetch_timeout_ms=ntp_fetch_timeout_ms,
    )


def connect_wlan(conn: asy_conn_time, dns_server: str = "192.0.2.53") -> None:
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


def make_fram_manager(max_size: int = 0x2000) -> "tuple[AsyFramManager, FakeMB85RS64V]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


# ---------------------------------------------------------------------------
# Real UDP NTP round trip - same machinery as test_ntp_wifi_dns_integration.py's own
# FakeNtpServer/_RedirectNtpNetworking, kept file-local per this suite's per-file convention.
# ---------------------------------------------------------------------------

_next_port = 56000


def make_addr() -> "tuple[str, int]":
    global _next_port
    _next_port += 1
    return socket.getaddrinfo("127.0.0.1", _next_port)[0][-1]  # type: ignore[return-value]


def make_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


class _RedirectNtpNetworking:
    # Same Unix-port-only workaround as test_asy_ntp_client.py's/test_ntp_wifi_dns_integration.py's
    # own class of the same name: redirects _NTP_UDP_PORT away from the real privileged port 123,
    # and pre-resolves AsyUDPSocket's addr since this build's raw connect() rejects a plain
    # (host, port) tuple.
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


async def sync_real_ntp_chain(conn: asy_conn_time, ntp: asy_ntp_client) -> None:
    # Drives one full, real, successful sync attempt (real WLAN state -> real DNS-skip via literal
    # IP -> real UDP round trip against a fake server) so a test can then observe ntp.ntp_issynced()
    # genuinely returning True through downstream consumers, not a hand-set flag.
    connect_wlan(conn)
    server = FakeNtpServer()
    reply = make_ntp_reply(int(time.time()))
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
            await _cancel(task)
    finally:
        server.close()
    assert await ntp.ntp_issynced() is True  # sanity: the helper itself actually synced


# ---------------------------------------------------------------------------
# FRAM timestamped-chunk propagation: ntp.ntp_issynced (real, chain-derived) flowing into
# AsyFramChunkTimestampedBuffer's write_into()/read_into(), exactly the seam
# asy_sgp40_driver.py's SGP40_Reader relies on (fram_ntp_callback=ntp.ntp_issynced in
# sensortask-wozi.py) but without needing a full fake I2C sensor to prove it.
# ---------------------------------------------------------------------------


def test_fram_write_into_gets_a_real_valid_timestamp_once_the_real_ntp_chain_is_synced() -> None:
    conn = make_conn()
    ntp = make_ntp(conn, "127.0.0.1")
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32())
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, bool]:
        await sync_real_ntp_chain(conn, ntp)
        return await chunk.write(b"12345678", require_ntp=True)

    ntp_synced, utc, write_ok = run(scenario())
    assert ntp_synced is True
    assert write_ok is True
    assert utc is not None and abs(utc - int(time.time())) < 5  # a real, current UTC timestamp


def test_fram_write_into_require_ntp_refuses_when_the_real_ntp_chain_has_never_synced() -> None:
    # Exactly asy_sgp40_driver.py's own _run_backup() "no write due to no timesync yet" real path
    # (require_ntp=True, ntp_synced=False -> no write, no error) - driven by a real never-connected
    # asy_conn_time/asy_ntp_client pair instead of a lambda that always returns False.
    conn = make_conn()  # never connected: network_available() genuinely returns False
    ntp = make_ntp(conn, "127.0.0.1")
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32())
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, bool]:
        return await chunk.write(b"12345678", require_ntp=True)

    ntp_synced, utc, write_ok = run(scenario())
    assert (ntp_synced, utc, write_ok) == (False, None, False)


def test_fram_read_into_age_is_computed_from_the_real_ntp_chains_synced_clock() -> None:
    conn = make_conn()
    ntp = make_ntp(conn, "127.0.0.1")
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32())
    assert chunk is not None

    async def scenario() -> tuple[int | None, int | None, bytearray | None]:
        await sync_real_ntp_chain(conn, ntp)
        await chunk.write(b"deadbeef")
        return await chunk.read()

    ts, age, data = run(scenario())
    assert data == bytearray(b"deadbeef")
    assert ts is not None
    assert age is not None and age >= 0  # age.is computed via a second real ntp.ntp_issynced() call


def test_calling_real_ntp_issynced_from_fram_write_into_does_not_block_on_a_concurrent_real_sync() -> None:
    # Proves the "no cross-lock contention" assumption asy_fram_manager.py's docstring/comments now
    # rely on: ntp.ntp_issynced() only touches SensorReader's own private _datalock (base_classes.py),
    # never conn's/ntp's shared wifi_mode_lock - so a FRAM backup cycle calling it while a real NTP
    # sync attempt is genuinely in flight (and holding wifi_mode_lock, per
    # tests/test_ntp_wifi_dns_integration.py's own test_ntp_sync_holding_the_lock_blocks_a_concurrent_real_wifi_mode_switch)
    # must complete promptly rather than hang.
    conn = make_conn()
    connect_wlan(conn)
    unreachable_addr = make_addr()  # nobody listens here
    ntp = make_ntp(conn, unreachable_addr[0], ntp_fetch_timeout_ms=2000)  # long enough to observe the lock held
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32())
    assert chunk is not None

    async def scenario() -> bool:
        task = asyncio.create_task(ntp.asy_ntp_time())
        ntp.ntp_sync_trigger_event.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert conn.wifi_mode_lock.locked() is True  # ntp genuinely holds conn's own shared lock right now
        try:
            _ntp_synced, _utc, write_ok = await asyncio.wait_for(chunk.write(b"12345678"), 0.2)
        except asyncio.TimeoutError:
            await _cancel(task)
            return False  # would mean ntp_issynced() got stuck behind the shared lock - a real bug
        await _cancel(task)
        return write_ok

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# SystemService propagation: ntp.ntp_issynced (real, chain-derived) flowing into
# SystemService._ntp_boot_signature()/status_counter(), exactly sensortask-wozi.py's own
# `SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, debug=debug)` wiring.
# ---------------------------------------------------------------------------


def test_system_service_boot_signature_resolves_via_the_real_ntp_chain_once_synced() -> None:
    conn = make_conn()
    ntp = make_ntp(conn, "127.0.0.1")
    svc = SystemService(ntp.ntp_issynced)

    async def scenario() -> int | None:
        await sync_real_ntp_chain(conn, ntp)
        task = asyncio.create_task(svc.status_counter())
        await _tick(svc.uptime_event, 1)
        await _cancel(task)
        return await svc.get_boot_signature()

    boot_signature = run(scenario())
    assert boot_signature is not None
    assert abs(boot_signature - int(time.time())) < 5  # a real NTP-derived timestamp, not a random fallback


def test_system_service_boot_signature_falls_back_to_random_once_the_real_chain_never_syncs() -> None:
    conn = make_conn()  # never connected
    ntp = make_ntp(conn, "127.0.0.1")
    svc = SystemService(ntp.ntp_issynced)

    async def scenario() -> int | None:
        task = asyncio.create_task(svc.status_counter())
        await _tick(svc.uptime_event, 121)  # past _NTP_WAIT_TIME (120s, one tick per uptime second)
        await _cancel(task)
        assert await ntp.ntp_issynced() is False  # sanity: the real chain genuinely never synced
        return await svc.get_boot_signature()

    boot_signature = run(scenario())
    assert boot_signature is not None  # random fallback resolved despite the real chain staying unsynced


def test_system_service_and_a_fram_backup_chunk_share_one_real_ntp_client_independently() -> None:
    # Matches sensortask-wozi.py's real topology: one asy_ntp_client instance (ntp), one bound
    # ntp.ntp_issynced method, handed to two independent real consumers at once (SystemService and a
    # FRAM timestamped chunk, standing in for SGP40_Reader's own ts_storage) - proves neither
    # consumer's own call to the shared callback corrupts or blocks the other's.
    conn = make_conn()
    ntp = make_ntp(conn, "127.0.0.1")
    svc = SystemService(ntp.ntp_issynced)
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32())
    assert chunk is not None

    async def scenario() -> tuple[int | None, bool]:
        await sync_real_ntp_chain(conn, ntp)
        task = asyncio.create_task(svc.status_counter())
        await _tick(svc.uptime_event, 1)
        await _cancel(task)
        boot_signature = await svc.get_boot_signature()
        _ntp_synced, _utc, write_ok = await chunk.write(b"12345678", require_ntp=True)
        return boot_signature, write_ok

    boot_signature, write_ok = run(scenario())
    assert boot_signature is not None
    assert write_ok is True


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
