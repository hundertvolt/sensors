"""Mock-tier proof for buildgen's WiFi/NTP/webserver FRAM-wiring session: AsyConnTime/AsyNtpClient/WebserverService
all get a real FRAM-backed PrintLogHistoryStore logger when directly constructed with fram=
(surviving a simulated reboot through the real chunk) and stay plain RAM-only PrintLogHistory
without it - class-level capability, exercised here independent of whether buildgen actually wires
it for a given consumer (it does for conn/ntp; WebserverService's own module comment explains why
buildgen deliberately never passes fram= to it, despite this class-level support). Also proves
AsyConnTime forwards the real AsyFramManager into its own DNSServer rather than None."""

import asyncio
import os
import sys

sys.path.insert(0, "ext")  # real, vendored ext/microdot.py - see test_asy_webserver_service.py's
# own comment for why (scripts/test.sh's MICROPYPATH deliberately excludes ext/).

from _fram_chip_fake import FakeMB85RS64V
from microdot import Microdot  # type: ignore[import-not-found]

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_ntp_client import AsyNtpClient
from asy_spi_driver import SPI
from asy_webserver_service import WebserverService
from asy_wifi_service import AsyConnTime
from print_log import PrintLogHistory, PrintLogHistoryStore

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


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Per-test config-file isolation - same _tmp_cfg_dir()/_sweep_stale_tmp_dirs() shape every other
# test file uses (see tests/test_sensortask.py's own comment for the full root-cause story).
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return
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


_sweep_stale_tmp_dirs("framwiring_")


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/framwiring_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def make_fram_manager(max_size: int = 0x2000) -> "tuple[AsyFramManager, FakeMB85RS64V]":
    # Same shape as test_ntp_fram_system_integration.py's own make_fram_manager().
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


def make_conn(fram: "AsyFramManager | None" = None) -> AsyConnTime:
    conn = AsyConnTime(led_pin=None, cfg_path=_tmp_cfg_dir(), fram=fram)
    run(conn.cfgmgr.setup())
    return conn


def make_ntp(conn: AsyConnTime, fram: "AsyFramManager | None" = None) -> AsyNtpClient:
    ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip, cfg_path=_tmp_cfg_dir(), fram=fram)
    run(ntp.cfgmgr.setup())
    return ntp


def make_webserver(fram: "AsyFramManager | None" = None) -> WebserverService:
    return WebserverService(Microdot(), fram=fram)


# ---------------------------------------------------------------------------
# FRAM-present path: the logger genuinely becomes a real, chunk-backed PrintLogHistoryStore.
# ---------------------------------------------------------------------------


def test_conn_logger_is_fram_backed_when_fram_is_wired() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    conn = make_conn(fram=manager)
    assert isinstance(conn.pr, PrintLogHistoryStore)


def test_ntp_logger_is_fram_backed_when_fram_is_wired() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    conn = make_conn()
    ntp = make_ntp(conn, fram=manager)
    assert isinstance(ntp.pr, PrintLogHistoryStore)


def test_webserver_logger_is_fram_backed_when_fram_is_wired() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    webserver = make_webserver(fram=manager)
    assert isinstance(webserver.pr, PrintLogHistoryStore)


def test_conn_forwards_the_real_fram_manager_into_its_own_dns_server() -> None:
    # asy_wifi_service.py's own AsyConnTime.__init__ forwards fram= straight through to the
    # DNSServer it owns internally - this proves it actually receives the real manager (a real,
    # allocated chunk), not a silently-dropped None.
    manager, _chip = make_fram_manager()
    run(manager.setup())
    conn = make_conn(fram=manager)
    assert isinstance(conn.dns_server.pr, PrintLogHistoryStore)
    assert conn.dns_server.pr.fram is not None


# ---------------------------------------------------------------------------
# FRAM-absent path: today's behavior, unchanged - a plain in-memory logger, regression-proofed so a
# future change can't silently make fram= mandatory or default it to something FRAM-backed.
# ---------------------------------------------------------------------------


def test_conn_logger_stays_ram_only_without_fram() -> None:
    conn = make_conn()
    assert type(conn.pr) is PrintLogHistory
    assert type(conn.dns_server.pr) is PrintLogHistory


def test_ntp_logger_stays_ram_only_without_fram() -> None:
    conn = make_conn()
    ntp = make_ntp(conn)
    assert type(ntp.pr) is PrintLogHistory


def test_webserver_logger_stays_ram_only_without_fram() -> None:
    webserver = make_webserver()
    assert type(webserver.pr) is PrintLogHistory


# ---------------------------------------------------------------------------
# Persistence across a simulated reboot: a fresh AsyFramManager over the SAME underlying chip is
# the digital-twin/mock-tier analogue of a real device losing power and cold-booting with the same
# physical FRAM chip still attached - same technique as
# tests/test_ntp_fram_system_integration.py's own test_fram_timestamped_chunk_torn_write_self_heals...
# and tests/test_digital_twin_sensortask_integration.py's own SGP40 VOC-backup reboot test.
# ---------------------------------------------------------------------------


def test_conn_wifi_error_log_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    manager1, chip = make_fram_manager()
    run(manager1.setup())
    conn1 = make_conn(fram=manager1)
    run(conn1.pr.setup())
    run(conn1.pr.err_s("boot failed", errno=7))
    assert run(conn1.pr.get_log())["WIFI"]["ErrCount"] == 1

    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip  # reuse the same underlying chip bytes
    run(manager2.setup())
    conn2 = make_conn(fram=manager2)  # a genuinely fresh object - the persisted FRAM bytes, not
    # Python state, are what carries the error across the "reboot" (conn2 is not conn1).
    run(conn2.pr.setup())
    log = run(conn2.pr.get_log())
    assert log["WIFI"]["ErrCount"] == 1
    assert log["WIFI"]["ErrNum"][-1] == 7


def test_ntp_error_log_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    manager1, chip = make_fram_manager()
    run(manager1.setup())
    conn1 = make_conn(fram=manager1)
    ntp1 = make_ntp(conn1, fram=manager1)
    run(ntp1.pr.setup())
    run(ntp1.pr.err_s("sync failed", errno=3))
    assert run(ntp1.pr.get_log())["NTP"]["ErrCount"] == 1

    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    conn2 = make_conn(fram=manager2)  # same construction sequence as boot 1 - conn before ntp -
    ntp2 = make_ntp(conn2, fram=manager2)  # so ntp's own chunk lands at the identical FRAM address.
    assert ntp2 is not ntp1
    run(ntp2.pr.setup())
    log = run(ntp2.pr.get_log())
    assert log["NTP"]["ErrCount"] == 1
    assert log["NTP"]["ErrNum"][-1] == 3


def test_webserver_error_log_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    manager1, chip = make_fram_manager()
    run(manager1.setup())
    webserver1 = make_webserver(fram=manager1)
    run(webserver1.pr.setup())
    run(webserver1.pr.err_s("unexpected error", errno=1))
    assert run(webserver1.pr.get_log())["WEBSERVER"]["ErrCount"] == 1

    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    webserver2 = make_webserver(fram=manager2)
    assert webserver2 is not webserver1
    run(webserver2.pr.setup())
    log = run(webserver2.pr.get_log())
    assert log["WEBSERVER"]["ErrCount"] == 1
    assert log["WEBSERVER"]["ErrNum"][-1] == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
