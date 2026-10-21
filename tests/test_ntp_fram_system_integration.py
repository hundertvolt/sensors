"""Integration across the real chain WifiService -> NTPClient -> {a timestamped FRAM chunk, SystemService}, wired as the
generated build_system() wires them (buildgen/codegen.py); proves the chain's value/timing behaviour and the no-deadlock
assumption around wifi_mode_lock."""

import asyncio
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP shim's directory (digital_twin/README.md)

import network
from _async_harness import cancel, run
from _error_codes import code
from _fake_time import DrivenTime, tick
from _fram_builders import make_fram_manager
from _ntp_frames import FakeNtpServer, make_ntp_reply
from _port_bands import PortAllocator
from _recording_print import record_prints
from _src_const import src_const, src_int
from _task_names import task_name
from _tmp_scratch import TmpScratch
from _udp_port_redirect import redirect_udp_port
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

import asy_base_classes
import asy_ntp_client as ntpmod
from asy_base_classes import ValueRef
from asy_bmp3xx_driver import BMP3XX_Reader
from asy_crc_checks import CRC32
from asy_dns_client import DNS_FAILED
from asy_i2c_driver import I2C
from asy_ntp_client import NTPClient, NtpTiming
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_system_service import SystemService
from asy_wifi_service import WifiConfig, WifiService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    from _protocols import WLANLike
    from machine import I2C as FakeI2C

    class _FakeWLAN(WLANLike, Protocol):
        # The fake's test-only names this file sets: mypy resolves `network` to the board stub, which has none of
        # them (tests/network.py is outside the main pass, B.15).
        _connected: bool
        _status: int
        _ifconfig: tuple[str, str, str, str]

# Once, before any UDPSocket connects: this Unix build's socket takes no plain (host, port) tuple (SPECIFICATION.md F.7).
patch_asy_udp_socket_for_unix_port()

# Read from source: const() folds them out of the module (tests/_src_const.py).
_NTP_UDP_PORT = src_const("src/asy_ntp_client.py", "_NTP_UDP_PORT")
_LOG_ALL: int = src_int("src/asy_print_log.py", "_LOG_ALL")

# @tunable ntp.fetch_timeout_ms = 5000
_FETCH_TIMEOUT_MS = 5000
# @tunable l1.asy_ntp_client_serve_wait_s = 5
_SERVE_WAIT_S = 5
# @tunable l1.asy_ntp_client_state_poll_ms = 20
_STATE_POLL_MS = 20
# @tunable l1.asy_ntp_client_synced_poll_tries = 50
_SYNCED_POLL_TRIES = 50
# @tunable l1.ntp_fram_system_integration_utc_tolerance_s = 5
_UTC_TOLERANCE_S = 5
# @tunable l1.ntp_fram_system_integration_supervisor_scan_wait_s = 2.5
_SCAN_WAIT_S = 2.5
# @tunable l1.ntp_fram_system_integration_start_poll_s = 0.01
_START_POLL_S = 0.01
# @tunable l1.ntp_fram_system_integration_start_poll_tries = 200
_START_POLL_TRIES = 200
# @tunable l1.asy_ntp_client_fake_server_poll_ms = 10
_FAKE_SERVER_POLL_MS = 10
# @tunable l1.asy_ntp_client_fake_server_poll_tries = 1000
_FAKE_SERVER_POLL_TRIES = 1000


def _wlan(conn: WifiService) -> "_FakeWLAN":
    return conn._wlan  # type: ignore[return-value]  # the fake, which mypy sees as the board stub's WLAN


# ---------------------------------------------------------------------------
# Fixtures: the conn/ntp construction of test_ntp_wifi_dns_integration.py, the shared FRAM builder.
# ---------------------------------------------------------------------------

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("ntpfram")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def _make_conn() -> WifiService:
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), cfg_path=_tmp_cfg_dir())
    run(conn.setup())
    return conn


def _make_ntp(
    conn: WifiService, ntp_host: str, ntp_fetch_timeout_ms: int = _FETCH_TIMEOUT_MS,
) -> NTPClient:
    # The generated build_system() wiring (buildgen/codegen.py): the three providers passed positionally, the real
    # bound methods, not a lambda standing in for them.
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write(f'{{"NTPHost": "{ntp_host}", "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 0, "DSTOffset": 0, "DNSFallback": ""}}')
    ntp = NTPClient(
        conn.get_wifi_mode_lock(),
        conn.network_available_locked,
        conn.get_dns_server_ip,
        NtpTiming(500, 1, ntp_fetch_timeout_ms, 10, 600),
        cfg_path=cfg_path,
    )
    run(ntp.setup())
    return ntp


async def _connect_wlan(conn: WifiService, dns_server: str = "192.0.2.53") -> None:
    # The fake radio connected with a DHCP lease, then one 1 Hz snapshot step under wifi_mode_lock: every
    # getter reads the snapshot, so the DHCP server reaches NTP only through it.
    wlan = _wlan(conn)
    wlan._connected = True
    wlan._status = network.STAT_GOT_IP
    wlan._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", dns_server)
    async with conn.get_wifi_mode_lock():
        await conn._update_wifi_snapshot(connected=True)


def connect_wlan(conn: WifiService) -> None:
    run(_connect_wlan(conn))


# ---------------------------------------------------------------------------
# Real UDP NTP round trip: the shared tests/_ntp_frames.py FakeNtpServer, port 123 pointed at it by
# tests/_udp_port_redirect.py.
# ---------------------------------------------------------------------------

# This file's own band of tests/_port_bands.py: files run concurrently, and a UDP collision is a silent timeout.
_PORTS = PortAllocator("test_ntp_fram_system_integration")


def _make_port() -> int:
    return _PORTS.next()


def _make_ntp_server() -> FakeNtpServer:
    return FakeNtpServer(_make_port(), poll_ms=_FAKE_SERVER_POLL_MS, poll_tries=_FAKE_SERVER_POLL_TRIES)


async def sync_real_ntp_chain(conn: WifiService, ntp: NTPClient) -> None:
    # Drives one full, real, successful sync attempt (real WLAN state -> real DNS-skip via literal
    # IP -> real UDP round trip against a fake server) so a test can then observe ntp.ntp_issynced()
    # genuinely returning True through downstream consumers, not a hand-set flag.
    await _connect_wlan(conn)
    server = _make_ntp_server()
    reply = make_ntp_reply(int(time.time()))
    try:
        with redirect_udp_port(ntpmod, _NTP_UDP_PORT, server.port):
            task = asyncio.create_task(ntp._sync_loop())
            server_task = asyncio.create_task(server.serve_once(reply))
            ntp._ntp_sync_trigger_event.set()
            await asyncio.wait_for(server_task, _SERVE_WAIT_S)
            for _ in range(_SYNCED_POLL_TRIES):
                if await ntp.ntp_issynced():
                    break
                await asyncio.sleep_ms(_STATE_POLL_MS)
            await cancel(task)
    finally:
        server.close()
    assert await ntp.ntp_issynced() is True  # sanity: the helper itself actually synced


# ---------------------------------------------------------------------------
# FRAM timestamped-chunk propagation: ntp.ntp_issynced, real and chain-derived, flowing into
# FRAMChunkTimestampedBuffer's write_into()/read_into() - exactly the seam SGP40_Reader relies on via
# SgpBackup.ntp_synced, but without needing a full fake I2C sensor to prove it.
# ---------------------------------------------------------------------------


def test_fram_write_into_gets_a_real_valid_timestamp_once_the_real_ntp_chain_is_synced() -> None:
    conn = _make_conn()
    ntp = _make_ntp(conn, "127.0.0.1")
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, int | None]:
        await sync_real_ntp_chain(conn, ntp)
        return await chunk.write(b"12345678", require_ntp=True)

    write_ok, ntp_synced, utc = run(scenario())
    assert ntp_synced is True
    assert write_ok is True
    assert utc is not None and abs(utc - int(time.time())) < _UTC_TOLERANCE_S  # a real, current UTC timestamp


def test_fram_write_into_require_ntp_refuses_when_the_real_ntp_chain_has_never_synced() -> None:
    # Exactly asy_sgp40_driver.py's own _run_backup() "no write due to no timesync yet" real path
    # (require_ntp=True, ntp_synced=False -> no write, no error) - driven by a real never-connected
    # WifiService/NTPClient pair instead of a lambda that always returns False.
    conn = _make_conn()  # never connected: network_available_locked() genuinely returns False
    ntp = _make_ntp(conn, "127.0.0.1")
    ntp.pr.set_level(_LOG_ALL)  # the skip is a console line at DebugLevel 5 only: recorded, it proves the loop woke
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, int | None]:
        task = asyncio.create_task(ntp._sync_loop())
        await tick(ntp._ntp_sync_trigger_event, 1)  # the loop wakes and skips: no network
        await cancel(task)
        return await chunk.write(b"12345678", require_ntp=True)

    with record_prints(ntp.pr) as printed:
        assert run(scenario()) == (False, False, None)
    assert ("NTP", "Network not available, skipping sync attempt.") in printed.lines, printed.lines


def test_fram_read_into_age_is_computed_from_the_real_ntp_chains_synced_clock() -> None:
    conn = _make_conn()
    ntp = _make_ntp(conn, "127.0.0.1")
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk is not None

    async def scenario() -> tuple[int | None, int | None, bytearray | None]:
        await sync_real_ntp_chain(conn, ntp)
        await chunk.write(b"deadbeef")
        return await chunk.read()

    ts, age, data = run(scenario())
    assert data == bytearray(b"deadbeef")
    assert ts is not None
    assert age is not None and age >= 0  # age.is computed via a second real ntp.ntp_issynced() call


# @tunable l1.fram_lock_fetch_timeout_ms = 2000
_LOCK_HOLD_FETCH_TIMEOUT_MS = 2000
# @tunable l1.fram_write_prompt_s = 1.0
_WRITE_PROMPT_S = 1.0


def test_calling_real_ntp_issynced_from_fram_write_into_does_not_block_on_a_concurrent_real_sync() -> None:
    # Proves the "no cross-lock contention" assumption asy_fram_manager.py's comments rely on:
    # ntp_issynced() only touches SensorReader's private _data_lock, never conn's or ntp's shared
    # wifi_mode_lock.
    #
    # So a FRAM backup cycle calling it while a real NTP sync attempt is genuinely in flight, and holding
    # wifi_mode_lock, must complete promptly rather than hang.
    conn = _make_conn()
    connect_wlan(conn)
    server = _make_ntp_server()  # bound, never answering: the fetch waits out its timeout inside the lock
    ntp = _make_ntp(conn, "127.0.0.1", ntp_fetch_timeout_ms=_LOCK_HOLD_FETCH_TIMEOUT_MS)  # long enough to observe the lock held
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk is not None

    async def scenario() -> bool:
        with redirect_udp_port(ntpmod, _NTP_UDP_PORT, server.port):
            task = asyncio.create_task(ntp._sync_loop())
            ntp._ntp_sync_trigger_event.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert conn.wifi_mode_lock.locked() is True  # ntp genuinely holds conn's own shared lock right now
            try:
                # A fraction of _LOCK_HOLD_FETCH_TIMEOUT_MS: checks the write completes promptly, not stuck behind the lock.
                write_ok, *_ = await asyncio.wait_for(chunk.write(b"12345678"), _WRITE_PROMPT_S)
            except asyncio.TimeoutError:
                await cancel(task)
                return False  # would mean ntp_issynced() got stuck behind the shared lock - a real bug
            assert conn.wifi_mode_lock.locked() is True  # the write finished inside the hold, not after it
            await cancel(task)
        return write_ok

    try:
        assert run(scenario()) is True
    finally:
        server.close()


# ---------------------------------------------------------------------------
# SystemService propagation: ntp.ntp_issynced (real, chain-derived) flowing into
# SystemService._ntp_boot_signature()/_status_loop(), as the generated build_system() wires it
# (buildgen/codegen.py): `SystemService(ntp.ntp_issynced, ...)`.
# ---------------------------------------------------------------------------


def test_system_service_boot_signature_resolves_via_the_real_ntp_chain_once_synced() -> None:
    conn = _make_conn()
    ntp = _make_ntp(conn, "127.0.0.1")
    with DrivenTime(asy_base_classes) as clock:
        svc = SystemService(ntp.ntp_issynced)

        async def scenario() -> int | float | None:
            await sync_real_ntp_chain(conn, ntp)
            task = asyncio.create_task(svc._status_loop())
            await tick(svc._uptime_event, 1, clock)
            await cancel(task)
            return await svc.get_boot_signature()

        boot_signature = run(scenario())
    assert boot_signature is not None
    assert abs(boot_signature - int(time.time())) < _UTC_TOLERANCE_S  # a real NTP-derived timestamp, not a random fallback


def test_system_service_boot_signature_falls_back_to_random_once_the_real_chain_never_syncs() -> None:
    conn = _make_conn()  # never connected
    ntp = _make_ntp(conn, "127.0.0.1")
    with DrivenTime(asy_base_classes) as clock:
        svc = SystemService(ntp.ntp_issynced)

        async def scenario() -> int | float | None:
            task = asyncio.create_task(svc._status_loop())
            await tick(svc._uptime_event, 121, clock)  # 121 driven seconds: past _NTP_WAIT_TIME (120 s)
            await cancel(task)
            assert await ntp.ntp_issynced() is False  # sanity: the real chain genuinely never synced
            return await svc.get_boot_signature()

        boot_signature = run(scenario())
    assert boot_signature is not None  # random fallback resolved despite the real chain staying unsynced


def test_system_service_and_a_fram_backup_chunk_share_one_real_ntp_client_independently() -> None:
    # Matches the real device topology: one NTPClient instance, one bound ntp_issynced method, handed to
    # two independent real consumers at once - SystemService and a FRAM timestamped chunk standing in for
    # SGP40_Reader's _ts_storage - proving neither consumer's call corrupts or blocks the other's.
    conn = _make_conn()
    ntp = _make_ntp(conn, "127.0.0.1")
    manager, _chip = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk is not None
    with DrivenTime(asy_base_classes) as clock:
        svc = SystemService(ntp.ntp_issynced)

        async def scenario() -> tuple[int | float | None, bool]:
            await sync_real_ntp_chain(conn, ntp)
            task = asyncio.create_task(svc._status_loop())
            await tick(svc._uptime_event, 1, clock)
            await cancel(task)
            boot_signature = await svc.get_boot_signature()
            write_ok, _ntp_synced, _utc = await chunk.write(b"12345678", require_ntp=True)
            return boot_signature, write_ok

        boot_signature, write_ok = run(scenario())
    assert boot_signature is not None
    assert write_ok is True


# ---------------------------------------------------------------------------
# Task-supervision seam: an unreachable NTP server is routine, handled inside the task (Part C.7.2), so
# the real supervisor (supervise_tasks()) must see a live task and spend none of its reboot budget on it -
# each restart costs 100 of 300 there, which is how an outage used to reboot the device.
# ---------------------------------------------------------------------------


def test_system_service_never_restarts_a_real_ntp_task_whose_server_stays_unreachable() -> None:
    conn = _make_conn()
    connect_wlan(conn)  # network_available_locked() is genuinely True - failures come from resolution, not this
    ntp = _make_ntp(conn, "127.0.0.1")
    svc = SystemService(ntp.ntp_issynced)
    starts: list[asyncio.Task[None]] = []

    def spy_starter() -> "asyncio.Task[None]":
        # Wraps the real starter (not a synthetic one) so this test can observe how many times the
        # real supervisor actually (re)started the real task, without reaching into its task list.
        t = ntp.start_asy_sync()
        starts.append(t)
        return t

    original_resolver = ntpmod.resolve_ipv4

    async def always_fails(*_args: object, **_kwargs: object) -> "tuple[str | None, int]":
        return None, DNS_FAILED  # every real resolution attempt fails instantly - no real network wait needed

    ntpmod.resolve_ipv4 = always_fails
    try:

        async def scenario() -> int:
            await svc.start_tasks([spy_starter], task_names=[task_name(ntp, ntp.start_asy_sync)])
            assert len(starts) == 1
            svc_task = asyncio.create_task(svc.supervise_tasks())
            await asyncio.sleep(0)  # one yield: the supervisor's first pass (a limit, not an interleaving claim)
            for _ in range(20):  # four times the old five-failure give-up streak
                ntp._ntp_sync_trigger_event.set()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
            await asyncio.sleep(_SCAN_WAIT_S)  # real wall-clock wait for the supervisor's next 2 s pass
            assert not starts[0].done()  # the real _sync_loop() task is still the one running
            await cancel(svc_task)
            return len(starts)

        call_count = run(scenario())
    finally:
        ntpmod.resolve_ipv4 = original_resolver
    assert call_count == 1  # the initial real start only - no restart
    assert run(svc.get_error_counter())["SYSTEM"]["ErrCount"] == 0  # no restart warning, no budget spent
    assert run(ntp.get_error_counter())["NTP"]["ErrCount"] == 20  # every failure still counted


# ---------------------------------------------------------------------------
# Torn-write self-heal with a real, chain-derived timestamp: applying tests/test_fram_integration.py's
# fault-injection pattern (simulate power loss mid-write, then a fresh reboot) to a timestamped chunk whose
# ntp_sync_callback is a real NTPClient.ntp_issynced, not the always-True stub the other FRAM tests use.
# ---------------------------------------------------------------------------

_STATUS_BUSY: int = src_int("src/asy_fram_manager.py", "_STATUS_BUSY")


def test_fram_timestamped_chunk_torn_write_self_heals_with_a_real_ntp_derived_timestamp() -> None:
    conn = _make_conn()
    ntp = _make_ntp(conn, "127.0.0.1")
    manager1, chip = make_fram_manager()
    run(manager1.setup())
    chunk1 = manager1.get_timestamped_chunk(8, ntp.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk1 is not None

    async def before_reboot() -> None:
        await sync_real_ntp_chain(conn, ntp)
        write_ok, ntp_synced, _utc = await chunk1.write(b"deadbeef")
        assert ntp_synced is True
        assert write_ok is True

    run(before_reboot())
    # Simulate power loss mid-write: block 0's status bytes are left BUSY, mirroring
    # tests/test_fram_integration.py's own torn-write fault injection exactly.
    addr0, _addr1 = chunk1._block_addr
    status_addr = addr0 + chunk1.size + chunk1.crc.length()
    chip.memory[status_addr] = _STATUS_BUSY
    chip.memory[status_addr + 1] = _STATUS_BUSY

    # Fresh reboot: new manager/chunk objects (same underlying chip), a fresh never-synced
    # NTPClient this time - proving the self-heal doesn't depend on NTP state at read time.
    manager2, _ = make_fram_manager(chip=chip)
    run(manager2.setup())
    conn2 = _make_conn()
    ntp2 = _make_ntp(conn2, "127.0.0.1")
    chunk2 = manager2.get_timestamped_chunk(8, ntp2.ntp_issynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk2 is not None

    ts, _age, data = run(chunk2.read())
    assert data == bytearray(b"deadbeef")  # recovered from block 1 despite block 0's torn-write marker
    assert ts is not None  # the real timestamp written before the simulated reboot survived intact


# ---------------------------------------------------------------------------
# SystemService supervising a real sensor Reader task, not just the ntp one above.
# get_task_starters()/start_asy_read() are proven individually in the BMP3xx suite, by tests a coverage
# audit found had never been called at all before.
#
# But nothing proves the same starter still works once wired through the real, generic
# start_tasks()/supervise_tasks() every device actually uses - the seam the NTP-task test above proves for
# NTPClient, generalized here to a sensor driver.
# ---------------------------------------------------------------------------

_BMP_ADDR = 0x77


async def _one_supervisor_pass(svc: SystemService, starts: "list[asyncio.Task[None]]") -> int:
    # The supervisor's first pass restarts the dead task at once; its next pass is 2 s away, so the count is read
    # before that one can restart the task a second time, with the same bounded real-time poll as the start.
    svc_task = asyncio.create_task(svc.supervise_tasks())
    for _ in range(_START_POLL_TRIES):
        if len(starts) > 1:
            break
        await asyncio.sleep(_START_POLL_S)
    await cancel(svc_task)
    return len(starts)


def _make_bmp_reader(cfg_path: str, max_module_error: int = 1) -> BMP3XX_Reader:
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = BMP3XX_Reader(i2c, address=_BMP_ADDR, max_module_error=max_module_error, cfg_path=cfg_path)
    run(reader.cfgmgr.setup())
    return reader


async def _never_synced() -> bool:
    return False


def test_system_service_restarts_a_real_sensor_reader_task_that_genuinely_gives_up() -> None:
    reader = _make_bmp_reader(_tmp_cfg_dir(), max_module_error=1)  # gives up on the 2nd consecutive real failure
    fake_i2c: FakeI2C = reader._bmp._i2c_bmp3xx.i2c_device.i2c._i2c  # type: ignore[assignment]
    fake_i2c.nak_addresses.add(_BMP_ADDR)  # every real bus op fails - setup() itself never succeeds
    svc = SystemService(_never_synced)
    starts: list[asyncio.Task[None]] = []

    def spy_starter() -> "asyncio.Task[None]":
        # Wraps the real starter (not a synthetic one), same technique as
        # test_system_service_never_restarts_a_real_ntp_task_whose_server_stays_unreachable above.
        t = reader.start_asy_read()
        starts.append(t)
        return t

    async def scenario() -> int:
        await svc.start_tasks([spy_starter], task_names=[task_name(reader, reader.start_asy_read)])
        for _ in range(_START_POLL_TRIES):  # bounded wait for the real _read_loop()'s own init failure -> return False -
            # a real sleep, not sleep(0): asy_i2c_driver.py's _probe_for_device() awaits two real
            # 0.1s sleeps regardless of outcome, and sleep(0) never advances wall-clock time on this
            # Unix-port event loop, so it can never observe those real sleeps completing.
            if starts and starts[0].done():
                break
            await asyncio.sleep(_START_POLL_S)
        assert starts[0].done()  # the real _read_loop() genuinely returned on its own (init failed)
        return await _one_supervisor_pass(svc, starts)

    call_count = run(scenario())
    assert call_count == 2  # the initial real start, plus one genuine restart by the real supervisor
    counter = run(svc.get_error_counter())
    assert counter["SYSTEM"]["ErrCount"] == 1
    assert counter["SYSTEM"]["ErrNum"][-1] == code("E", "TASK_RETURNED")  # the task's end is persisted; the restart line is console-only


_SCD30_ADDR: int = src_int("src/asy_scd30_driver.py", "_SCD30_ADDR")
_SGP40_ADDR: int = src_int("src/asy_sgp40_driver.py", "_SGP40_ADDR")


def _make_scd30_reader(cfg_path: str, max_module_error: int = 1) -> SCD30_Reader:
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    return SCD30_Reader(i2c, irq_pin=5, max_module_error=max_module_error, cfg_path=cfg_path)


def _make_sgp40_reader(cfg_path: str, max_module_error: int = 1) -> SGP40_Reader:
    i2c = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    # A real SCD30_Reader behind the temperature/humidity value references (SPECIFICATION.md Parts C.14 and L.6.3) -
    # never read() or setup(), so its get_data() just returns its unmeasured-sentinel namedtuple with every
    # field None, matching what the old _no_comp_data() returned directly.
    scd_reader = _make_scd30_reader(cfg_path)
    reader = SGP40_Reader(
        i2c,
        ValueRef(scd_reader, "Temp"),
        ValueRef(scd_reader, "Hum"),
        max_module_error=max_module_error,
        cfg_path=cfg_path,
    )
    run(reader.cfgmgr.setup())
    return reader


def test_system_service_restarts_a_real_scd30_reader_task_that_genuinely_gives_up() -> None:
    # Same technique as the BMP3xx case above, for the SCD30 reader: the task-completeness audit that motivated
    # the BMP3xx test flagged SCD30 and SGP40 as the two Readers never driven through a real SystemService.
    #
    # test_asy_scd30_driver.py uses the identical NAK-the-address setup at the module level, just without a
    # real supervisor watching it.
    reader = _make_scd30_reader(_tmp_cfg_dir(), max_module_error=1)
    fake_i2c: FakeI2C = reader._scd._i2c_scd30.i2c_device.i2c._i2c  # type: ignore[assignment]
    fake_i2c.nak_addresses.add(_SCD30_ADDR)  # every real bus op fails - init itself never succeeds
    svc = SystemService(_never_synced)
    starts: list[asyncio.Task[None]] = []

    def spy_starter() -> "asyncio.Task[None]":
        t = reader.start_asy_read()
        starts.append(t)
        return t

    async def scenario() -> int:
        await svc.start_tasks([spy_starter], task_names=[task_name(reader, reader.start_asy_read)])
        for _ in range(_START_POLL_TRIES):  # bounded wait for the real _read_loop()'s own init failure -> return False -
            # a real sleep, not sleep(0): see the BMP3xx test above for why.
            if starts and starts[0].done():
                break
            await asyncio.sleep(_START_POLL_S)
        assert starts[0].done()  # the real _read_loop() genuinely returned on its own (init failed)
        return await _one_supervisor_pass(svc, starts)

    call_count = run(scenario())
    assert call_count == 2  # the initial real start, plus one genuine restart by the real supervisor
    counter = run(svc.get_error_counter())
    assert counter["SYSTEM"]["ErrCount"] == 1
    assert counter["SYSTEM"]["ErrNum"][-1] == code("E", "TASK_RETURNED")  # the task's end is persisted; the restart line is console-only


def test_system_service_restarts_a_real_sgp40_reader_task_that_genuinely_gives_up() -> None:
    reader = _make_sgp40_reader(_tmp_cfg_dir(), max_module_error=1)
    fake_i2c: FakeI2C = reader._sgp._i2c_sgp40.i2c_device.i2c._i2c  # type: ignore[assignment]
    fake_i2c.nak_addresses.add(_SGP40_ADDR)  # every real bus op fails - init itself never succeeds
    svc = SystemService(_never_synced)
    starts: list[asyncio.Task[None]] = []

    def spy_starter() -> "asyncio.Task[None]":
        t = reader.start_asy_read()
        starts.append(t)
        return t

    async def scenario() -> int:
        await svc.start_tasks([spy_starter], task_names=[task_name(reader, reader.start_asy_read)])
        for _ in range(_START_POLL_TRIES):  # bounded wait for the real _read_loop()'s own init failure -> return False -
            # a real sleep, not sleep(0): see the BMP3xx test above for why.
            if starts and starts[0].done():
                break
            await asyncio.sleep(_START_POLL_S)
        assert starts[0].done()  # the real _read_loop() genuinely returned on its own (init failed)
        return await _one_supervisor_pass(svc, starts)

    call_count = run(scenario())
    assert call_count == 2  # the initial real start, plus one genuine restart by the real supervisor
    counter = run(svc.get_error_counter())
    assert counter["SYSTEM"]["ErrCount"] == 1
    assert counter["SYSTEM"]["ErrNum"][-1] == code("E", "TASK_RETURNED")  # the task's end is persisted; the restart line is console-only


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
