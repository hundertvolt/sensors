"""Every class with an async setup() answers each public call before setup() and after a setup() forced to
fail exactly as its contract says - a sentinel, False, "Failed" per key, or its documented raise - never an
AttributeError; setup() itself answers a bool (SPECIFICATION.md Part C.13)."""

import asyncio
import os
import sys
from collections import namedtuple

# The webserver's row needs the real vendored ext/microdot.py, which scripts/test.sh's MICROPYPATH leaves out.
sys.path.insert(0, "ext")

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch
from microdot import Microdot

import asy_config_manager as cm
import asy_spi_driver
from asy_base_classes import SensorReader, SensorReaderConfig
from asy_fram_driver import FRAM_SPI
from asy_fram_manager import FRAMManager
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService
from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore
from asy_spi_driver import SPI, SPIDevice
from asy_system_service import SystemService
from asy_uart_comm import ROLE_INITIATOR, UARTComm
from asy_uart_driver import UART
from asy_uart_link_driver import UARTLinkDriver
from asy_webserver_service import RouteSources, ServingLimits, WebserverService
from asy_wifi_service import WifiConfig, WifiService

asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    from asy_print_log import ErrorLog

    T = TypeVar("T")
    Check = Callable[[object], bool]
    Calls = dict[str, tuple[tuple[object, ...], Check]]

_scratch = TmpScratch("readiness_gates")
Meas = namedtuple("Meas", ["Temp", "TS"])
_VAL_COUNT: "cm.ConfigSchema" = (("Count", "int", 5, 0, 10, None),)


def run(coro: "Coroutine[object, object, T]") -> "T":
    return asyncio.run(coro)


async def _ntp_synced() -> bool:
    return False


def _fram(*, writable: bool) -> "FRAMManager":
    # A real manager over the chip fake; writable=False drops every WREN, so no chunk write lands.
    manager = FRAMManager(SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4), 1, max_size=0x2000)
    run(manager.setup())
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    chip.drop_wren = not writable
    return manager


def _blocked_dir(name: str) -> str:
    # A config path whose file is a directory: the store's setup() fails, never overwriting it.
    path = _scratch.dir()
    os.mkdir(path + "config_" + name + ".cfg")
    return path


def _answers(obj: object, calls: "Calls") -> "list[str]":
    # Calls each public method; returns the ones whose answer is not the documented one.
    wrong: list[str] = []
    for name, (args, ok) in calls.items():
        result = getattr(obj, name)(*args)
        if hasattr(result, "send"):  # a coroutine: an async method
            result = run(result)
        if not ok(result):
            wrong.append(f"{name} -> {result!r}")
    return wrong


def _is_log_of(name: str) -> "Check":
    return lambda log: type(log) is dict and list(log) == [name]


def _reader_calls(obj: SensorReader) -> "Calls":
    return {
        "get_error_sources": ((), lambda r: isinstance(r, list) and obj in r),
        "get_loggers": ((), lambda r: isinstance(r, list) and obj.pr in r),
        "get_error_counter": ((), _is_log_of(obj.name)),
        "get_trigger_starters": ((), lambda r: r == []),
    }


def test_sensor_reader_answers_before_and_after_a_setup_whose_logger_cannot_reach_its_store() -> None:
    reader = SensorReader(Meas(None, None), "GATE", max_module_error=3, log=LogConfig(_fram(writable=False), 4, None))
    assert _answers(reader, _reader_calls(reader)) == []
    assert run(reader.setup()) is True  # the reader is ready; its logger runs in RAM
    assert reader.pr.initialized is False
    assert _answers(reader, _reader_calls(reader)) == []


def test_sensor_reader_config_answers_before_and_after_a_failed_setup() -> None:
    reader = SensorReaderConfig(Meas(None, None), "GATECFG", _VAL_COUNT, max_module_error=3, cfg_path=_blocked_dir("GATECFG"))
    calls = _reader_calls(reader)
    calls["get_cfg_schema"] = ((), lambda r: r == _VAL_COUNT)
    assert _answers(reader, calls) == []
    assert run(reader.setup()) is False
    assert _answers(reader, calls) == []
    assert run(reader._set_dict_cfg({"Count": 3}, _VAL_COUNT)) == {"Count": "Failed"}


def test_system_service_answers_before_and_after_a_failed_setup() -> None:
    svc = SystemService(_ntp_synced, cfg_path=_blocked_dir("SYSTEM"))
    calls: Calls = {
        "get_uptime": ((), lambda r: r == 0),
        "get_boot_signature": ((), lambda r: r is None),
        "get_error_sources": ((), lambda r: r == [svc, svc.cfgmgr]),
        "get_loggers": ((), lambda r: r == [svc.pr, svc.cfgmgr.pr]),
        "get_error_counter": ((), _is_log_of(svc.name)),
        "get_cfg_schema": ((), lambda r: r == svc.get_cfg_schema() and isinstance(r, tuple) and r[0][0] == "DebugLevel"),
        "get_dict_cfg": ((), lambda r: r == {"SYSTEM": {"DebugLevel": None}}),
        "get_debug_level": ((), lambda r: r == 0),
        "set_debug_level": ((3,), lambda r: r is False),
        "feed_watchdog": ((), lambda r: r is None),
        "pause_permanent_storage": ((10,), lambda r: r is None),  # no storage wired: a no-op
    }
    assert _answers(svc, calls) == []
    assert run(svc.setup()) is False
    assert svc.pr.initialized is True
    assert _answers(svc, calls) == []


def test_config_manager_is_gated_on_valid_before_and_after_a_failed_setup() -> None:
    path = _blocked_dir("GATEMGR")
    mgr = cm.ConfigManager(path + "config_GATEMGR.cfg", _VAL_COUNT, "GATEMGR")
    calls: Calls = {
        "get_dict": ((["Count"],), lambda r: r is None),
        "get_int_values": ((_VAL_COUNT,), lambda r: r is None),
        "write_config": (({"Count": 3}, _VAL_COUNT), lambda r: r == (False, {})),
        "get_error_counter": ((), _is_log_of(mgr.name)),
        "flush_pending": ((), lambda r: r is None),
    }
    assert _answers(mgr, calls) == []
    assert run(mgr.setup()) is False
    assert mgr.valid is False
    assert _answers(mgr, calls) == []


def test_history_stores_answer_before_and_after_a_failed_setup() -> None:
    for history in (PrintLogHistory(4, None, name="GATELOG"), PrintLogHistoryStore(_fram(writable=False), 4, None, name="GATELOG")):
        calls: Calls = {
            "get_log": ((), _is_log_of(history.name)),
            "get_level": ((), lambda r: r == 0),
        }
        assert _answers(history, calls) == []
        expected = type(history) is PrintLogHistory  # only the RAM history can always set up
        assert run(history.setup()) is expected
        assert history.initialized is expected
        assert _answers(history, calls) == []
        run(history.err_s("still counted", errno=1))
        assert history._err_count == 1


_WRONG_CHIP_ID = bytes([0x05, 0x7F, 0x03, 0x02])  # a manufacturer ID no supported FRAM reports


def _spi() -> SPI:
    return SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def _is(value: object) -> "Check":
    return lambda r: r is value


def _raised(coro_or_call: "Callable[[], object]") -> str:
    try:
        result = coro_or_call()
        if hasattr(result, "send"):
            run(result)  # type: ignore[arg-type]
    except (OSError, RuntimeError) as e:
        return f"{type(e).__name__}: {e}"
    return ""


async def _enter(device: SPIDevice) -> None:
    async with device:
        pass


async def _signal(_r: int, _g: int, _b: int, _t: float) -> bool:
    return True


async def _no_local_time() -> None:
    return None


def _last_error(log: "ErrorLog", name: str) -> int:
    return log[name]["ErrNum"][-1]


def test_spi_device_refuses_a_session_before_setup_whose_own_setup_cannot_fail() -> None:
    device = SPIDevice(_spi(), 1)
    refusal = "RuntimeError: SPIDevice not set up - call setup() first"  # the async with structural raise (C.13)
    assert (device.initialized, _raised(device.session_begin), _raised(lambda: _enter(device))) == (False, refusal, refusal)
    assert run(device.setup()) is True
    assert device.initialized is True
    assert _raised(lambda: _enter(device)) == ""


def test_fram_driver_answers_its_sentinels_before_and_after_a_setup_that_finds_no_chip() -> None:
    fram = FRAM_SPI(_spi(), 1, logger=PrintLogHistory(name="GATEFRAM"))
    calls: Calls = {
        "get_size": ((), lambda r: r == 0x2000),
        "get_values": ((bytearray(4),), _is(False)),
        "set_values": ((b"ab", 0), _is(False)),
        "get_values_sync": ((bytearray(4),), lambda r: type(r) is int and r != 0),  # a refusal status, never OK
        "set_values_sync": ((b"ab", 0), lambda r: type(r) is int and r != 0),
        "get_write_protected": ((), _is(False)),
        "verify_present": ((), _is(False)),
    }
    assert _answers(fram, calls) == []
    assert run(fram.set_write_protected(value=True)) is False
    chip = fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    chip.rdid_response = _WRONG_CHIP_ID
    # The protocol layer's documented raise; FRAMManager.setup() catches it (next test).
    assert _raised(fram.setup) == "OSError: FRAM SPI device not found"
    assert fram.initialized is False
    assert _answers(fram, calls) == []
    assert _last_error(run(fram.pr.get_log()), "GATEFRAM") == code("E", "NOT_INIT")  # each refusal logged


def test_fram_manager_answers_before_and_after_a_setup_that_finds_no_chip() -> None:
    manager = FRAMManager(_spi(), 1, max_size=0x2000)
    calls: Calls = {
        "get_pause": ((), _is(False)),
        "get_chunk": ((8,), lambda r: r is not None),  # pure bookkeeping, safe before setup() (C.13)
        "get_error_sources": ((), lambda r: r == [manager]),
        "get_loggers": ((), lambda r: r == [manager.pr]),
        "get_error_counter": ((), _is_log_of(manager.name)),
    }
    assert _answers(manager, calls) == []
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    chip.rdid_response = _WRONG_CHIP_ID
    assert run(manager.setup()) is False
    assert manager.fram.initialized is False
    assert _last_error(run(manager.get_error_counter()), manager.name) == code("E", "INIT")
    assert _answers(manager, calls) == []


def test_neopixel_driver_answers_before_and_after_a_setup_whose_logger_cannot_reach_its_store() -> None:
    driver = NeopixelDriver(18, log=LogConfig(_fram(writable=False), 4, None))
    calls: Calls = {
        "get_error_counter": ((), _is_log_of(driver.name)),
        "get_error_sources": ((), lambda r: r == [driver]),
        "get_loggers": ((), lambda r: r == [driver.pr]),
        "get_timer_starters": ((), lambda r: r == []),
        "on": ((), _is(None)),
        "off": ((), _is(None)),
        "toggle": ((), _is(None)),
    }
    assert _answers(driver, calls) == []
    assert run(driver.setup()) is True  # ready: a logger that cannot reach its store has logged it and runs in RAM
    assert driver.pr.initialized is False
    assert _answers(driver, calls) == []


def test_notification_service_answers_before_and_after_a_failed_setup() -> None:
    svc = NotificationService(_signal, _no_local_time, (), cfg_path=_blocked_dir("NOTIFY"), log=LogConfig(None, 4, None))
    calls = _reader_calls(svc)
    calls.update({
        "get_data": ((), lambda r: isinstance(r, tuple) and tuple(r) == (False, None)),
        "get_dict_data": ((), lambda r: r == {"NOTIFY": {"Triggered": False, "TS": None}}),
        "get_dict_cfg": ((), lambda r: isinstance(r, dict) and list(r) == ["NOTIFY"] and set(r["NOTIFY"].values()) == {None}),
        "get_override_led": ((), lambda r: r == 0),
        "get_timer_starters": ((), lambda r: r == []),
    })
    assert _answers(svc, calls) == []
    assert run(svc.setup()) is False
    assert _answers(svc, calls) == []
    assert run(svc._set_dict_cfg({"AutoOn": True}, svc.get_cfg_schema())) == {"AutoOn": "Failed"}
    run(svc.set_override_led(5))  # the pause runs on ticks, with no store involved
    assert run(svc.get_override_led()) == 5


def test_wifi_service_answers_before_and_after_a_failed_setup() -> None:
    svc = WifiService(WifiConfig("GATE", "12345678", 5, 5), cfg_path=_blocked_dir("WIFI"), log=LogConfig(None, 4, None))
    calls = _reader_calls(svc)
    calls.update({
        "get_data": ((), lambda r: isinstance(r, tuple) and tuple(r) == (None, None, None, None)),
        "get_dict_data": ((), lambda r: r == {"WIFI": {"Mode": None, "Connected": None, "IP": None, "TS": None}}),
        "get_dict_cfg": ((), lambda r: isinstance(r, dict) and list(r) == ["WIFI"] and r["WIFI"]["SSID"] is None),
        "get_wifi_uptime": ((), lambda r: r == 0),
        "is_hotspot_active": ((), _is(False)),
        "wlan_isconnected": ((), _is(False)),
        "network_available_locked": ((), _is(False)),
        "get_dns_server_ip": ((), lambda r: r is None or type(r) is str),
        "get_wlan_rssi": ((), lambda r: r is None or type(r) is int),
        "get_wlan_ifconfig": ((), lambda r: r is None or (type(r) is tuple and len(r) == 4)),
    })
    assert _answers(svc, calls) == []
    assert run(svc.setup()) is False
    assert svc._dns_server.pr.initialized is True  # the captive DNS logger is set up all the same
    assert _answers(svc, calls) == []
    assert run(svc._set_dict_cfg({"SSID": "net"}, svc.get_cfg_schema())) == {"SSID": "Failed"}


def test_webserver_service_answers_before_and_after_a_setup_whose_logger_cannot_reach_its_store() -> None:
    routes = RouteSources((), None, None, None, None, None, None, (), ())
    serving = ServingLimits(2048, 256, 3, None, 0.2, 0.5, "0.0.0.0", 80)
    svc = WebserverService(Microdot(), routes, serving, None, LogConfig(_fram(writable=False), 4, None))  # type: ignore[arg-type]
    calls: Calls = {
        "get_error_counter": ((), _is_log_of(svc.pr.name)),
        "get_error_sources": ((), lambda r: r == [svc]),
        "get_loggers": ((), lambda r: r == [svc.pr]),
        "get_timer_starters": ((), lambda r: r == []),
    }
    assert _answers(svc, calls) == []
    assert run(svc.setup()) is True  # it serves with its logger in RAM
    assert svc.pr.initialized is False
    assert _answers(svc, calls) == []


def test_uart_link_driver_with_no_bus_answers_false_and_persists_the_refusal() -> None:
    driver = UARTLinkDriver(None, ROLE_INITIATOR, name_ext="gate")
    calls: Calls = {
        "get_error_counter": ((), _is_log_of(driver.name)),
        "get_error_sources": ((), lambda r: r == [driver._comm]),
        "get_loggers": ((), lambda r: r == [driver.pr]),
        "get_link_status": ((), lambda r: r == {"Transfers": 0, "Failures": 0}),
        "get_timer_starters": ((), lambda r: r == []),
    }
    assert driver.initialized is False
    assert _answers(driver, calls) == []
    assert run(driver.setup()) is False
    assert driver.initialized is False
    assert _last_error(run(driver.get_error_counter()), driver.name) == code("E", "UART_NO_BUS")
    assert _answers(driver, calls) == []


def test_uart_comm_refused_at_construction_answers_its_sentinels_and_persists_the_refusal() -> None:
    comm = UARTComm(UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=2), ROLE_INITIATOR, payload_size=0, name="GATEUART")
    calls: Calls = {
        "uart_get": ((1,), _is(None)),
        "uart_set": ((1, b"x"), _is(False)),
        "get_task_starters": ((), lambda r: r == []),
        "get_timer_starters": ((), lambda r: r == []),
        "get_error_counter": ((), _is_log_of("GATEUART")),
    }
    assert comm.initialized is False
    assert _answers(comm, calls) == []
    assert run(comm.setup()) is False
    assert comm.initialized is False
    assert _last_error(run(comm.get_error_counter()), "GATEUART") == code("E", "UART_PAYLOAD_SIZE")
    assert _answers(comm, calls) == []


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
