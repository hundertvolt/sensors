"""Shared scenario library: build_system() construction/wiring for every real device, plus real
webserver wiring (deep per-route behavior stays tests/test_asy_webserver_service.py's job).
Not a test file - register_for_device() is the export; SPECIFICATION.md Part E.2.1 has the split."""

import asyncio
import json
import sys

# Same convention as tests/test_asy_webserver_service.py: scripts/test.sh's MICROPYPATH excludes
# ext/, and every generated sensortask_<device> transitively imports microdot - extending sys.path
# reaches the real vendored ext/microdot.py without a build-environment scope change.
sys.path.insert(0, "ext")

import machine
from _fram_chip_fake import FakeMB85RS64V
from _shared_rest_roundtrip import (
    assert_named_modules_constructed,
    assert_sensor_payload_not_self_wrapped,
    drain_json_response_body,
)
from _tmp_scratch import TmpScratch
from microdot import Request, Response  # type: ignore[import-not-found]

import asy_spi_driver
from print_log import PrintLog, PrintLogHistoryStore

# Mirrors asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_HOTSPOT values - same
# not-importable-once-const()-folded reasoning as tests/test_asy_wifi_service.py's own copy; keep in
# sync with asy_wifi_service.py's own definitions if those ever change.
_PHASE_STA_SEEKING = 0
_PHASE_HOTSPOT = 2

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from asy_fram_manager import AsyFramChunk, AsyFramTimestampedChunk
    from base_classes import SensorReaderConfig
    from crc_checks import CRC_Base

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def status_body(res: "Response") -> bytes:
    # GET /status streams a list of already-json.dumps()-encoded fragments (see
    # asy_webserver_service.py's _build_status_pieces()); draining it the way a real client would
    # keeps every json.loads(...) assertion on a /status response working unchanged.
    return drain_json_response_body(res.body)


# Every real device (devices/*.toml) - buildgen generates each one's own module + wiring plan into
# build/generated_src/ before scripts/test.sh ever runs this file (scripts/_generate_sensortask_modules.py).
_DEVICES = ("wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi")


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # dev's real FRAM is a 256KB MB85RS2MTA (SPECIFICATION.md Part C.3.1), not the 8KB MB85RS64V
    # the base fake defaults to. A subclass, since build_system() offers no post-construction hook.
    # Only the RDID changes - that is what asy_fram_manager.py's setup() keys its chip check off.
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])


# Same "keyed by the real chip's own max_size" table digital_twin/machine.py's _FRAM_RDID_BY_MAX_SIZE
# uses, for the identical reason - derived from each device's own real FRAM. A third real size needs
# one new entry here, the same narrow addition twin_wiring.py's own table would need.
_FRAM_FAKE_BY_MAX_SIZE: "dict[int, type[FakeMB85RS64V]]" = {
    0x2000: FakeMB85RS64V,
    0x40000: _FakeMB85RS2MTA,
}


def _wiring_plan(device: str) -> "dict[str, Any]":
    with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
        plan: dict[str, Any] = json.load(f)
    return plan


def _fram_fake_class(device: str) -> "type[FakeMB85RS64V]":
    plan = _wiring_plan(device)
    (spi_attachment,) = plan["spi"].values()  # every real device has exactly one FRAM/SPI instance
    return _FRAM_FAKE_BY_MAX_SIZE[spi_attachment["max_size"]]


def fram_fake_class(device: str) -> "type[FakeMB85RS64V]":
    """Public alias of _fram_fake_class for tests/_boot_contiguity_probe.py, which boots the same
    devices from its own script entry point - exported rather than copied so the RDID table above
    stays the one place the tests tier maps a device to its real chip."""
    return _fram_fake_class(device)


# ---------------------------------------------------------------------------
# Per-test config-file isolation via tests/_tmp_scratch.py: build_system() constructs several real
# ConfigManager-backed modules, each writing a real config_<NAME>.cfg at its cfg_path - repeated
# calls in this process must not collide, nor touch the real repo-root config files.

# Keyed per-device (register_for_device() sets this up), not one shared "sensortask" key: each
# device's batch is its own OS process, potentially concurrent, so two devices must never resolve
# TmpScratch's tests/_tmp/<key>/ path to the same directory - one wipe could race the other.
# ---------------------------------------------------------------------------

_scratch: "TmpScratch | None" = None


def _tmp_cfg_dir() -> str:
    assert _scratch is not None, "register_for_device() must run before any scenario calls _tmp_cfg_dir()"
    return _scratch.dir()


# ---------------------------------------------------------------------------
# _boot()/reflective helpers - the mechanism every parametrized scenario below shares.
# ---------------------------------------------------------------------------

_OPTIONAL_INSTANCE_NAMES = ("scd30", "sgp40", "bmp3xx", "isl29125", "neopixel", "notification")


async def _boot(device: str, cfg_path: "str | None" = None, **kwargs: "Any") -> "Any":
    # Per-call, not module-level: different devices need different FRAM fakes (max_size/RDID), and
    # several devices' own modules get booted in this one process across this file's full run.
    asy_spi_driver._SPI = _fram_fake_class(device)  # type: ignore[misc]
    module = __import__(f"sensortask_{device}")
    await module.build_system(cfg_path=cfg_path if cfg_path is not None else _tmp_cfg_dir(), **kwargs)
    return module


def build(device: str, cfg_path: "str | None" = None, **kwargs: "Any") -> "Any":
    return run(_boot(device, cfg_path, **kwargs))


def _device_of(module: "Any") -> str:
    name: str = module.__name__
    assert name.startswith("sensortask_")
    return name[len("sensortask_") :]


def _present_optional_instances(module: "Any") -> "tuple[str, ...]":
    # Reflective, but the oracle is the wiring plan buildgen wrote from devices/<device>.toml,
    # never the built module's attributes: reading the module back cannot tell "device has no
    # bmp3xx" from "buildgen silently dropped a declared driver". fram is excluded, always present.
    plan_instances = set(_wiring_plan(_device_of(module))["instances"])
    return tuple(name for name in _OPTIONAL_INSTANCE_NAMES if name in plan_instances)


def _has(module: "Any", name: str) -> bool:
    present = name in _present_optional_instances(module)
    device = _device_of(module)
    if present:
        assert getattr(module, name, None) is not None, f"{name} is in devices/{device}.toml's own instances but build_system() never constructed it"
    else:
        # The reverse direction matters too: a wiring plan that silently UNDER-reports (omits a
        # driver build_system() genuinely constructs) must not let this check quietly agree with
        # it and stop testing a real, live object.
        assert getattr(module, name, None) is None, f"{name} is NOT in devices/{device}.toml's own instances, but build_system() constructed it anyway"
    return present


def _has_uart_link(module: "Any") -> bool:
    # uart_link doesn't fit _has()'s one-driver-one-attribute shape: a device that has it always
    # has exactly two instances (uart_link_init/uart_link_resp - buildgen/twin_wiring.py's own
    # instance_label() naming), never a single "module.uart_link". Only "dev" has it today.
    present = "uart_link" in set(_wiring_plan(_device_of(module))["instances"])
    init = getattr(module, "uart_link_init", None)
    resp = getattr(module, "uart_link_resp", None)
    if present:
        assert init is not None and resp is not None, "uart_link is in devices/<device>.toml's own instances but build_system() never constructed both instances"
    else:
        assert init is None and resp is None, "uart_link is NOT in devices/<device>.toml's own instances, but build_system() constructed it anyway"
    return present


def _all_loggers(module: "Any") -> "list[Any]":
    assert module.conn is not None and module.ntp is not None and module.fram is not None and module.sysfunct is not None
    assert module.neopixel is not None and module.notification is not None and module.webserver is not None
    loggers = [
        module.conn.pr,
        module.conn.cfgmgr.pr,
        module.conn.dns_server.pr,
        module.ntp.pr,
        module.ntp.cfgmgr.pr,
        module.fram.pr,
        module.sysfunct.pr,
        module.sysfunct.cfgmgr.pr,
    ]
    # scd30 before sgp40 before bmp3xx matches buildgen's topological construction order (sgp40
    # depends on scd30 as its temperature/humidity source), the same relative order every device's
    # TOML lists (Part L.3). setters[i] is paired with loggers[i] elsewhere, so this is load-bearing.
    if _has(module, "scd30"):
        loggers.append(module.scd30.pr)
    if _has(module, "sgp40"):
        loggers += [module.sgp40.pr, module.sgp40.cfgmgr.pr]
    if _has(module, "bmp3xx"):
        loggers += [module.bmp3xx.pr, module.bmp3xx.cfgmgr.pr]
    if _has(module, "isl29125"):
        loggers += [module.isl29125.pr, module.isl29125.cfgmgr.pr]
    loggers += [module.neopixel.pr, module.notification.pr, module.notification.cfgmgr.pr]
    if _has_uart_link(module):
        # No cfgmgr - UART_Comm has no config schema (its parameters are an out-of-band wire
        # contract, never runtime-writable, SPECIFICATION.md Part J.6), one entry per instance.
        loggers += [module.uart_link_init.pr, module.uart_link_resp.pr]
    loggers.append(module.webserver.pr)
    return loggers


def _expected_fram_chunk_calls(module: "Any") -> "list[str]":
    # The full expected chunk order is SPECIFICATION.md Part A.7's "Real FRAM chunk order" -
    # implicit-FRAM-wiring (conn/ntp/webserver and conn's DNSServer) and a cfgmgr chunk right after
    # each SensorReaderConfig-based module's own pr chunk are the two rules that shape it.

    # Built from the module's own reflected instance set, not a hardcoded per-device literal: every
    # device's TOML lists its instances in this same relative order (Part L.3), so the fixed shape
    # below stays correct for all 6.
    calls = ["chunk", "chunk", "chunk"]  # AsyConnTime, its own CFGMGR_WIFI, its own DNSServer
    calls += ["chunk", "chunk"]  # AsyNtpClient, its own CFGMGR_NTP
    calls += ["chunk", "chunk"]  # SystemService, its own CFGMGR_SYSTEM
    if _has(module, "scd30"):
        calls.append("chunk")  # SCD30_Reader - no cfgmgr
    if _has(module, "sgp40"):
        calls += ["chunk", "chunk", "timestamped"]  # SGP40, its own CFGMGR_SGP40, VOC backup
    if _has(module, "bmp3xx"):
        calls += ["chunk", "chunk"]  # BMP3xx_Reader, its own CFGMGR_BMP3XX
    if _has(module, "isl29125"):
        calls += ["chunk", "chunk"]  # ISL29125_Reader, its own CFGMGR_ISL29125
    calls.append("chunk")  # NeopixelDriver - always present, no cfgmgr
    calls += ["chunk", "chunk"]  # NotificationCoordinator, its own CFGMGR_NOTIFY - always present
    if _has_uart_link(module):
        calls += ["chunk", "chunk"]  # UartLinkExerciser x2 (init, resp) - no cfgmgr, WP3
    calls.append("chunk")  # WebserverService - no cfgmgr
    return calls


def _sensor_reader_owners(module: "Any") -> "list[Any]":
    # Every SensorReader/SensorReaderConfig instance real construction wires a task/timer starter
    # for - reflective over the same optional-instance set _present_optional_instances() derives,
    # plus the mandatory infra modules every real device always has.
    owners = [getattr(module, name) for name in ("scd30", "bmp3xx", "sgp40", "neopixel", "notification") if _has(module, name)]
    owners += [module.sysfunct, module.conn, module.ntp]
    return owners


def _dispatch(module: "Any", method: str, path: str, json_body: "dict[str, Any] | None" = None) -> "Response":
    assert module.webserver is not None
    app = module.webserver._app
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    req = Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)
    return run(app.dispatch_request(req))


# ---------------------------------------------------------------------------
# Scenario bodies - one per distinct construction/wiring/webserver-registration concern, each
# parametrized by `device` and registered per real device below, mirroring
# tests/_webserver_concurrency_scenarios.py's dynamic-registration convention (Part E.1).
# ---------------------------------------------------------------------------

_SCENARIOS: "list[tuple[str, Callable[[str], None]]]" = []


def _register(name: str) -> "Callable[[Callable[[str], None]], Callable[[str], None]]":
    def deco(fn: "Callable[[str], None]") -> "Callable[[str], None]":
        _SCENARIOS.append((name, fn))
        return fn

    return deco


@_register("build_system_constructs_every_real_module")
def _scenario_build_system_constructs_every_real_module(device: str) -> None:
    module = build(device)
    # Bare module-level attributes - reaches every long-lived object the way the legacy reference
    # file's own module-level names would. Shared shape with tests/_shared_rest_roundtrip.py.
    # Mandatory infra plus this device's reflected optional set, never a hardcoded 3-sensor literal.
    mandatory = ("conn", "ntp", "i2c0", "i2c1", "spi0", "fram", "sysfunct", "neopixel", "notification", "watchdog")
    assert_named_modules_constructed(module, mandatory + _present_optional_instances(module))


@_register("scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it")
def _scenario_scd30_clock_stretch(device: str) -> None:
    # SCD30 documents up to 150ms of clock stretching once per day (datasheets/scd30/...
    # _Interface_Description.pdf p.2) and rp2's I2C timeout default is 50ms, so whichever bus SCD30
    # sits on must override it. Looked up through scd30 itself, not assumed to be i2c0.
    module = build(device)
    if not _has(module, "scd30"):
        return  # every real device has scd30 today, but this stays correct if a future one doesn't
    scd_bus = module.scd30.scd.i2c_scd30.i2c_device.i2c
    assert scd_bus._i2c is not None
    assert scd_bus._i2c.freq == 50000
    assert scd_bus._i2c.timeout >= 150000

    # Whichever bus that isn't (SGP40's, and BMP3xx's where present) has no such requirement and
    # keeps the port default.
    assert module.i2c0 is not None and module.i2c1 is not None
    other_bus = module.i2c1 if scd_bus is module.i2c0 else module.i2c0
    assert other_bus._i2c is not None
    assert other_bus._i2c.timeout == 50000


@_register("build_system_wires_the_wifi_led_callback_after_both_exist")
def _scenario_wifi_led_wiring(device: str) -> None:
    # conn.set_ext_led(neopixel) - the one cross-wiring step that must run after both objects exist.
    # Confirmed indirectly: AsyConnTime's own ext_led slot is set.
    module = build(device)
    assert module.conn is not None
    assert module.conn.ext_led is module.neopixel


@_register("build_system_is_independently_callable_and_returns")
def _scenario_build_system_independently_callable(device: str) -> None:
    # The whole point of the generated-module split: importing this test file and calling
    # build_system() must never block. If this test hangs, that's the regression to report - not
    # something to work around here.
    build(device)


@_register("build_system_web_host_and_port_default_to_production_values")
def _scenario_web_host_port_defaults(device: str) -> None:
    module = build(device)
    assert module.webserver is not None
    assert module.webserver._host == "0.0.0.0"
    assert module.webserver._port == 80


@_register("build_system_web_host_and_port_are_overridable")
def _scenario_web_host_port_overridable(device: str) -> None:
    # A non-root Unix-port integration run can't bind the production 0.0.0.0:80 default (EACCES) -
    # build_system() must let a caller override both, mirroring its existing cfg_path/debug
    # override pattern.
    module = build(device, web_host="127.0.0.1", web_port=8080)
    assert module.webserver is not None
    assert module.webserver._host == "127.0.0.1"
    assert module.webserver._port == 8080


@_register("main_forwards_web_host_and_port_to_build_system")
def _scenario_main_forwards_web_host_port(device: str) -> None:
    # main() itself, not just build_system(), must accept and forward the override - the real entry
    # point calls <module>.main(). Fakes the three steps for the same reason the main-call-order
    # scenario below does: the real Timer-sequencing chain never completes under machine.py's fake.
    from asy_ntp_client import AsyNtpClient
    from system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = AsyNtpClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    async def _fake_start_timers(self: "SystemService", timers: "list[Callable[[], None]]") -> None:
        pass

    async def _fake_force_sync(self: "AsyNtpClient") -> None:
        pass

    async def _fake_start_and_check(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        pass  # never loops - this test only cares that build_system() received the override

    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    AsyNtpClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.start_and_check_tasks = _fake_start_and_check  # type: ignore[method-assign]
    try:
        asy_spi_driver._SPI = _fram_fake_class(device)  # type: ignore[misc]
        module = __import__(f"sensortask_{device}")
        run(module.main(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        AsyNtpClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]
    assert module.webserver is not None
    assert module.webserver._host == "127.0.0.1"
    assert module.webserver._port == 8080


# ---------------------------------------------------------------------------
# FRAM chunk order - exact relative sequence (six or seven chunks, depending on bmp3xx presence).
# ---------------------------------------------------------------------------


@_register("fram_chunk_allocation_order_matches_the_documented_sequence")
def _scenario_fram_chunk_order(device: str) -> None:
    calls: list[str] = []
    from asy_fram_manager import AsyFramManager

    real_get_chunk = AsyFramManager.get_chunk
    real_get_timestamped_chunk = AsyFramManager.get_timestamped_chunk

    # Both wrappers restate AsyFramManager's own signature verbatim rather than forwarding
    # *args/**kwargs - same call for every caller, and it keeps the parameter types real.
    def _tracking_get_chunk(
        self: "AsyFramManager", size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8,
    ) -> "AsyFramChunk | None":
        calls.append("chunk")
        return real_get_chunk(self, size, crc, verify, check_length)

    def _tracking_get_timestamped_chunk(
        self: "AsyFramManager",
        size: int,
        ntp_sync_callback: "Callable[[], Coroutine[Any, Any, bool]]",
        crc: "CRC_Base | None" = None,
        verify: int = 0,
        check_length: int = 8,
    ) -> "AsyFramTimestampedChunk | None":
        calls.append("timestamped")
        return real_get_timestamped_chunk(self, size, ntp_sync_callback, crc, verify, check_length)

    AsyFramManager.get_chunk = _tracking_get_chunk  # type: ignore[method-assign]
    AsyFramManager.get_timestamped_chunk = _tracking_get_timestamped_chunk  # type: ignore[method-assign]
    try:
        module = build(device)
    finally:
        AsyFramManager.get_chunk = real_get_chunk  # type: ignore[method-assign]
        AsyFramManager.get_timestamped_chunk = real_get_timestamped_chunk  # type: ignore[method-assign]

    assert calls == _expected_fram_chunk_calls(module)


@_register("fram_chunks_are_all_successfully_allocated_not_out_of_memory")
def _scenario_fram_chunks_allocated(device: str) -> None:
    module = build(device)
    # Every FRAM-chunk-owning module degrades to in-memory-only on allocation failure rather than
    # raising (base_classes.py's contract) - assert the happy path got real chunks, not a degraded
    # one. This is also the per-device "does everything fit" capacity check.

    # The real enforcement is exactly this - no chunk-holding module ended up with a None chunk -
    # not `allocated_size <= size`, which get_chunk() makes true by construction. The negative case
    # is test_base_classes.py's test_sensorreaderconfig_fram_allocation_failure_and_missing_....
    assert module.conn is not None and module.ntp is not None
    assert module.sysfunct is not None and module.neopixel is not None and module.notification is not None
    assert isinstance(module.conn.pr, PrintLogHistoryStore)
    assert module.conn.pr.fram is not None
    assert isinstance(module.conn.cfgmgr.pr, PrintLogHistoryStore)
    assert module.conn.cfgmgr.pr.fram is not None
    assert isinstance(module.conn.dns_server.pr, PrintLogHistoryStore)
    assert module.conn.dns_server.pr.fram is not None
    assert isinstance(module.ntp.pr, PrintLogHistoryStore)
    assert module.ntp.pr.fram is not None
    assert isinstance(module.ntp.cfgmgr.pr, PrintLogHistoryStore)
    assert module.ntp.cfgmgr.pr.fram is not None
    assert isinstance(module.sysfunct.pr, PrintLogHistoryStore)
    assert module.sysfunct.pr.fram is not None
    assert isinstance(module.sysfunct.cfgmgr.pr, PrintLogHistoryStore)
    assert module.sysfunct.cfgmgr.pr.fram is not None
    assert isinstance(module.neopixel.pr, PrintLogHistoryStore)
    assert module.neopixel.pr.fram is not None
    assert isinstance(module.notification.pr, PrintLogHistoryStore)
    assert module.notification.pr.fram is not None
    assert isinstance(module.notification.cfgmgr.pr, PrintLogHistoryStore)
    assert module.notification.cfgmgr.pr.fram is not None
    assert isinstance(module.webserver.pr, PrintLogHistoryStore)
    assert module.webserver.pr.fram is not None
    if _has(module, "scd30"):
        assert isinstance(module.scd30.pr, PrintLogHistoryStore)
        assert module.scd30.pr.fram is not None
    if _has(module, "sgp40"):
        assert isinstance(module.sgp40.pr, PrintLogHistoryStore)
        assert module.sgp40.pr.fram is not None
        assert module.sgp40.ts_storage is not None
        assert isinstance(module.sgp40.cfgmgr.pr, PrintLogHistoryStore)
        assert module.sgp40.cfgmgr.pr.fram is not None
    if _has(module, "bmp3xx"):
        assert isinstance(module.bmp3xx.pr, PrintLogHistoryStore)
        assert module.bmp3xx.pr.fram is not None
        assert isinstance(module.bmp3xx.cfgmgr.pr, PrintLogHistoryStore)
        assert module.bmp3xx.cfgmgr.pr.fram is not None
    if _has(module, "isl29125"):
        assert isinstance(module.isl29125.pr, PrintLogHistoryStore)
        assert module.isl29125.pr.fram is not None
        assert isinstance(module.isl29125.cfgmgr.pr, PrintLogHistoryStore)
        assert module.isl29125.cfgmgr.pr.fram is not None
    if _has_uart_link(module):
        # WP3 - own chunk each, no cfgmgr (UART_Comm has no on-flash config schema).
        assert isinstance(module.uart_link_init.pr, PrintLogHistoryStore)
        assert module.uart_link_init.pr.fram is not None
        assert isinstance(module.uart_link_resp.pr, PrintLogHistoryStore)
        assert module.uart_link_resp.pr.fram is not None


@_register("the_fram_manager_is_the_only_error_source_whose_own_log_is_not_fram_backed")
def _scenario_only_the_fram_manager_logs_in_memory(device: str) -> None:
    module = build(device)
    # scripts/_digital_twin_ci_suite.py's Run 5c sweeps the whole errcount table and exempts its
    # _IN_MEMORY_ONLY_ERROR_SOURCES. Pinned from the real object graph: AsyFramManager is the only
    # source allowed to be in-memory, since the store cannot persist its own failures through itself.
    in_memory = sorted(logger.name for logger in _all_loggers(module) if not isinstance(logger, PrintLogHistoryStore))
    assert in_memory == ["FRAM"], f"{device}: only the FRAM manager's own log may be in-memory-only, found {in_memory}"


class _DeadFramChip(FakeMB85RS64V):
    # Same technique as test_fram_integration.py's
    # test_sensorreader_runs_in_degraded_mode_when_fram_setup_never_succeeded: a real device-ID
    # mismatch, not just fram=None - the chip responds, it just never comes up as the expected one.
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])


@_register("build_system_never_insists_on_fram_hardware_being_available")
def _scenario_fram_never_required(device: str) -> None:
    # Owner requirement: no module may insist on FRAM availability - every FRAM-backed error log
    # must keep working in plain RAM, and SGP40 must keep running without backup/restore. Exercises
    # the whole construction chain with a dead chip, not one driver in isolation.
    asy_spi_driver._SPI = _DeadFramChip  # type: ignore[misc]
    module = __import__(f"sensortask_{device}")
    run(module.build_system(cfg_path=_tmp_cfg_dir()))

    # build_system() completed fully - didn't raise, didn't skip constructing anything - despite
    # the underlying FRAM chip never coming up.
    assert module.fram is not None
    assert module.fram.fram is not None
    assert module.fram.fram.initialized is False  # the dead chip, confirmed never ready
    assert module.sysfunct is not None and module.neopixel is not None and module.notification is not None

    # Every FRAM-chunk-owning logger still allocated a chunk (pure bookkeeping, SPECIFICATION.md
    # Part C.13 - doesn't need setup() to have succeeded) but stays functional in degraded mode,
    # matching test_fram_integration.py's "not None, just permanently hardware-unusable" pattern.
    assert isinstance(module.sysfunct.pr, PrintLogHistoryStore)
    run(module.sysfunct.pr.err_s("boom", errno=1))  # never raises despite the dead chip
    assert run(module.sysfunct.get_error_counter())["SYSTEM"]["ErrCount"] == 1  # still counted in memory

    # SGP40 (present on every real device): VOC backup/restore chunk allocated but unusable - skips
    # backups, starts from scratch every time, but the reader itself keeps running
    # (asy_sgp40_driver.py's own _check_storage() contract, not re-tested here at that depth).
    if _has(module, "sgp40"):
        assert isinstance(module.sgp40.pr, PrintLogHistoryStore)
        assert module.sgp40.ts_storage is not None
        assert run(module.sgp40.get_error_counter())["SGP40"]["ErrCount"] == 0

    # bmp3xx/scd30: same degraded-mode contract as sysfunct above - a FRAM-backed logger stays
    # functional in plain memory when the chip never comes up. Only asserted for whichever of the
    # two this device actually has.
    if _has(module, "bmp3xx"):
        assert isinstance(module.bmp3xx.pr, PrintLogHistoryStore)
        run(module.bmp3xx.pr.err_s("boom", errno=1))
        assert run(module.bmp3xx.get_error_counter())["BMP3XX"]["ErrCount"] == 1
    if _has(module, "scd30"):
        assert isinstance(module.scd30.pr, PrintLogHistoryStore)
        run(module.scd30.pr.err_s("boom", errno=1))
        assert run(module.scd30.get_error_counter())["SCD30"]["ErrCount"] == 1

    # The rest of the system is unaffected - task/timer starter collection still works end to end.
    starters = module._collect_task_starters()
    assert len(starters) > 0


# ---------------------------------------------------------------------------
# setup() batch: grouped, fixed order, notification.setup() only after finalize().
# ---------------------------------------------------------------------------


@_register("setup_batch_runs_sysfunct_then_fram_then_conn_then_ntp_then_sgp_then_bmp_then_notify_in_order")
def _scenario_setup_batch_order(device: str) -> None:
    calls: list[str] = []
    from asy_fram_manager import AsyFramManager
    from asy_notification_service import NotificationCoordinator
    from asy_ntp_client import AsyNtpClient
    from asy_sgp40_driver import SGP40_Reader
    from asy_wifi_service import AsyConnTime
    from system_service import SystemService

    real_sysfunct_setup = SystemService.setup
    real_fram_setup = AsyFramManager.setup
    real_conn_setup = AsyConnTime.setup
    real_ntp_setup = AsyNtpClient.setup
    real_sgp_setup = SGP40_Reader.setup
    real_notify_setup = NotificationCoordinator.setup
    real_notify_finalize = NotificationCoordinator.finalize

    # bmp3xx is only ever present on some devices - patched conditionally below, once the module's
    # own reflected shape is known, rather than unconditionally importing/patching a class the
    # generated module for this device may never construct at all.
    real_bmp_setup = None
    if device in _bmp3xx_devices():
        from asy_bmp3xx_driver import BMP3xx_Reader

        real_bmp_setup = BMP3xx_Reader.setup

    async def _tracking_sysfunct_setup(self: "SystemService") -> None:
        calls.append("sysfunct")
        return await real_sysfunct_setup(self)

    async def _tracking_fram_setup(self: "AsyFramManager") -> bool:
        calls.append("fram")
        return await real_fram_setup(self)

    # conn/ntp/sgp/bmp all inherit setup() from SensorReaderConfig, so that - not the concrete
    # subclass - is the type of the class attribute each override is assigned to below.
    async def _tracking_conn_setup(self: "SensorReaderConfig") -> None:
        calls.append("conn")
        return await real_conn_setup(self)

    async def _tracking_ntp_setup(self: "SensorReaderConfig") -> None:
        calls.append("ntp")
        return await real_ntp_setup(self)

    async def _tracking_sgp_setup(self: "SensorReaderConfig") -> None:
        calls.append("sgp")
        return await real_sgp_setup(self)

    async def _tracking_bmp_setup(self: "SensorReaderConfig") -> None:
        calls.append("bmp")
        assert real_bmp_setup is not None
        return await real_bmp_setup(self)

    def _tracking_notify_finalize(self: "NotificationCoordinator") -> None:
        calls.append("notify_finalize")
        return real_notify_finalize(self)

    async def _tracking_notify_setup(self: "NotificationCoordinator") -> None:
        calls.append("notify_setup")
        return await real_notify_setup(self)

    SystemService.setup = _tracking_sysfunct_setup  # type: ignore[method-assign]
    AsyFramManager.setup = _tracking_fram_setup  # type: ignore[method-assign]
    AsyConnTime.setup = _tracking_conn_setup  # type: ignore[method-assign]
    AsyNtpClient.setup = _tracking_ntp_setup  # type: ignore[method-assign]
    SGP40_Reader.setup = _tracking_sgp_setup  # type: ignore[method-assign]
    NotificationCoordinator.setup = _tracking_notify_setup  # type: ignore[method-assign]
    NotificationCoordinator.finalize = _tracking_notify_finalize  # type: ignore[method-assign]
    if real_bmp_setup is not None:
        from asy_bmp3xx_driver import BMP3xx_Reader

        BMP3xx_Reader.setup = _tracking_bmp_setup  # type: ignore[method-assign]
    try:
        module = build(device)
    finally:
        SystemService.setup = real_sysfunct_setup  # type: ignore[method-assign]
        AsyFramManager.setup = real_fram_setup  # type: ignore[method-assign]
        AsyConnTime.setup = real_conn_setup  # type: ignore[method-assign]
        AsyNtpClient.setup = real_ntp_setup  # type: ignore[method-assign]
        SGP40_Reader.setup = real_sgp_setup  # type: ignore[method-assign]
        NotificationCoordinator.setup = real_notify_setup  # type: ignore[method-assign]
        NotificationCoordinator.finalize = real_notify_finalize  # type: ignore[method-assign]
        if real_bmp_setup is not None:
            from asy_bmp3xx_driver import BMP3xx_Reader

            BMP3xx_Reader.setup = real_bmp_setup  # type: ignore[method-assign]

    # notify_finalize runs during synchronous construction; fram is first within the async setup()
    # batch, because sysfunct's FRAM-backed cfgmgr.pr.setup() needs AsyFramManager initialized or it
    # degrades instantly. conn/ntp are built earlier but placed after those two, conn before ntp.
    expected = ["notify_finalize", "fram", "sysfunct", "conn", "ntp", "sgp"]
    if _has(module, "bmp3xx"):
        expected.append("bmp")
    expected.append("notify_setup")
    assert calls == expected


@_register("boot_feeds_the_watchdog_exactly_once_per_setup_call")
def _scenario_boot_feeds_the_watchdog(device: str) -> None:
    # WP6 (SPECIFICATION.md Part D.9/G.2): the generated boot sequence must actually execute a feed
    # after every setup() call, not just emit one in source (tests_scripts/test_buildgen_generate.py
    # proves the codegen shape). The expected count comes from the generated source, not by hand.
    with open(f"build/generated_src/sensortask_{device}.py") as f:
        source_lines = f.readlines()
    expected_feeds = sum(1 for line in source_lines if line.strip().startswith("await ") and line.strip().endswith(".setup()"))
    assert expected_feeds > 0
    module = build(device)
    assert module.sysfunct is not None and module.watchdog is not None
    assert module.sysfunct.watchdog is module.watchdog
    assert module.watchdog.feed_count == expected_feeds


def _bmp3xx_devices() -> "frozenset[str]":
    # Which of _DEVICES declare a bmp3xx, from each device's buildgen-computed wiring plan rather
    # than a hardcoded literal - used only where a scenario must know this BEFORE construction;
    # every other scenario derives it afterwards by reflecting on the built module.
    return frozenset(d for d in _DEVICES if "bmp3xx" in _wiring_plan_driver_names(d))


def _wiring_plan_driver_names(device: str) -> "frozenset[str]":
    plan = _wiring_plan(device)
    names = {a["driver"] for attachments in plan["buses"].values() for a in attachments}
    names |= {a["driver"] for a in plan["spi"].values()}
    return frozenset(names)


@_register("notify_service_cfgmgr_exists_once_build_system_completes")
def _scenario_notify_cfgmgr_exists(device: str) -> None:
    # self.cfgmgr only comes into existence via finalize()'s delayed super().__init__() -
    # asy_notification_service.py's own contract. If build_system() ever called notification's
    # setup() before finalize(), this would be the observable symptom (AttributeError instead).
    module = build(device)
    assert module.notification is not None
    assert module.notification.cfgmgr.valid is True


# ---------------------------------------------------------------------------
# Debug level - persisted on sysfunct, pushed live to every logger's own set_level() through a
# registry collected once at boot (owner requirement: system-wide, but no shared mutable value).
# See SPECIFICATION.md Part A.7's "Debug-level registry" and _collect_level_setters().
# ---------------------------------------------------------------------------


@_register("collect_level_setters_returns_one_entry_per_logger_in_the_object_graph")
def _scenario_collect_level_setters(device: str) -> None:
    module = build(device)
    setters = module._collect_level_setters()
    loggers = _all_loggers(module)
    assert len(setters) == len(loggers)
    # Each collected setter really is that logger's own bound set_level, confirmed by behavior
    # rather than identity (bound-method identity isn't guaranteed). Index-based, not zip() - that
    # avoids a silent length-mismatch footgun on top of the explicit length assert above.
    for i in range(len(loggers)):
        loggers[i].set_level(PrintLog.level_off())
        setters[i](PrintLog.level_info())
        assert loggers[i].get_level() == PrintLog.level_info()


@_register("debug_seed_value_is_the_starting_level_before_setup_resolves_the_persisted_one")
def _scenario_debug_seed_value(device: str) -> None:
    module = build(device, debug=PrintLog.level_warn())
    assert module.sysfunct is not None
    # First boot - no persisted value yet, so sysfunct.setup() writes and resolves the schema
    # default (0), then pushes it through the registry, overriding the debug= seed each logger was
    # constructed with. Matches test_system_service.py's own first-boot test.
    assert module.sysfunct.get_debug_level() == 0
    for pr in _all_loggers(module):
        assert pr.get_level() == 0, f"{pr.name!r} still shows the debug= seed, not the resolved default"


@_register("sysfunct_set_debug_level_updates_every_logger_in_the_object_graph")
def _scenario_set_debug_level_updates_every_logger(device: str) -> None:
    # End-to-end: once a REST route wires to sysfunct.set_debug_level(), this is the whole
    # observable effect a real request would have - every logger's own set_level() called directly,
    # no shared mutable value anywhere.
    module = build(device)
    assert module.sysfunct is not None
    ok = run(module.sysfunct.set_debug_level(PrintLog.level_err()))
    assert ok is True
    for pr in _all_loggers(module):
        assert pr.get_level() == PrintLog.level_err(), f"{pr.name!r} did not observe set_debug_level()"


@_register("debug_level_survives_a_simulated_reboot_through_build_system")
def _scenario_debug_level_survives_reboot(device: str) -> None:
    cfg_path = _tmp_cfg_dir()
    module = build(device, cfg_path=cfg_path)
    assert module.sysfunct is not None
    run(module.sysfunct.set_debug_level(PrintLog.level_once()))

    module = build(device, cfg_path=cfg_path)  # simulated reboot - same cfg_path, fresh objects
    assert module.sysfunct is not None
    assert module.sysfunct.get_debug_level() == PrintLog.level_once()
    for pr in _all_loggers(module):
        assert pr.get_level() == PrintLog.level_once(), f"{pr.name!r} did not get the persisted level on reboot"


# ---------------------------------------------------------------------------
# Task/timer starter collection - shape and membership only, never drives the infinite supervisor
# loop (start_and_check_tasks()) or a starter's own coroutine body. That boundary stays out of this
# file's own scope.
# ---------------------------------------------------------------------------


@_register("collect_task_starters_includes_every_constructed_module")
def _scenario_collect_task_starters(device: str) -> None:
    module = build(device)
    starters = module._collect_task_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    # No Microdot/webserver task - webserver's own task lives outside this collection entirely.
    assert not any("webserver" in getattr(s, "__name__", "").lower() for s in starters)
    # MicroPython bound methods don't expose __self__ (confirmed against the real Unix-port
    # interpreter - that is a CPython-only assumption), but they compare equal when bound to the
    # same (instance, function) pair, so membership via == still proves real ownership.
    for owner in _sensor_reader_owners(module):
        for expected in owner.get_task_starters():
            assert expected in starters, f"no task starter bound to {owner!r}"


@_register("collect_timer_starters_includes_every_constructed_module")
def _scenario_collect_timer_starters(device: str) -> None:
    # Every constructed module is checked, not just those currently contributing a timer:
    # neopixel/notification/webserver all return [] today, but this proves _collect_timer_starters()
    # actually calls each of them rather than picking modules by name.
    module = build(device)
    starters = module._collect_timer_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    for owner in _sensor_reader_owners(module) + [module.webserver]:
        assert owner is not None
        for expected in owner.get_timer_starters():
            assert expected in starters, f"no timer starter bound to {owner!r}"


@_register("collect_task_starters_never_touches_start_and_check_tasks")
def _scenario_collect_starters_never_blocks(device: str) -> None:
    # Collection is pure list-building from already-constructed objects - calling it must not
    # start, await, or block on anything. If it did, this test itself would hang.
    module = build(device)
    module._collect_task_starters()
    module._collect_timer_starters()


# ---------------------------------------------------------------------------
# main()'s own composition - build_system() -> start_timers() -> ntp_force_sync() ->
# start_and_check_tasks(), in that order. Both middle steps are faked out (their real mechanisms
# need wall-clock Timers, or block forever); test_system_service.py covers them directly.
# ---------------------------------------------------------------------------


@_register("main_calls_start_timers_then_force_sync_then_start_and_check_tasks_in_order")
def _scenario_main_call_order(device: str) -> None:
    calls: list[str] = []
    from asy_ntp_client import AsyNtpClient
    from system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = AsyNtpClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    # self/timers/task_starters keep their names (and stay unused): these are assigned onto the
    # real class attributes below, so mypy checks their parameter NAMES against the real methods'
    # (an underscore prefix is a hard [assignment] error, not covered by the method-assign ignore).
    async def _fake_start_timers(self: "SystemService", timers: "list[Callable[[], None]]") -> None:
        calls.append("start_timers")

    async def _fake_force_sync(self: "AsyNtpClient") -> None:
        calls.append("force_sync")

    async def _fake_start_and_check(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        calls.append("start_and_check_tasks")
        # Deliberately never loops - the real implementation runs forever; this proves main()
        # reaches this call, not that the supervisor loop itself behaves (test_system_service.py's
        # own job).

    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    AsyNtpClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.start_and_check_tasks = _fake_start_and_check  # type: ignore[method-assign]
    try:
        asy_spi_driver._SPI = _fram_fake_class(device)  # type: ignore[misc]
        module = __import__(f"sensortask_{device}")
        run(module.main(cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        AsyNtpClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]

    assert calls == ["start_timers", "force_sync", "start_and_check_tasks"]
    # build_system() itself already ran (construction succeeded) - main() reaches the task-starting
    # phase with every module in place, not just up to build_system().
    assert module.sysfunct is not None


# ---------------------------------------------------------------------------
# Webserver wiring - build_system() also constructs a real Microdot() app + WebserverService,
# registering every driver's SettingsGroup/status_source/system_cmd/notification_led/
# maintenance_sensor/error_source. These check the real registrations landed correctly.

# Not the generic dispatch/aggregation logic (tests/test_asy_webserver_service.py's uniform-fake
# suite covers that in full depth), and not concurrent-connection behavior
# (tests/_webserver_concurrency_scenarios.py, also parametrized across all 6 devices).
# ---------------------------------------------------------------------------


@_register("webserver_pr_is_fram_backed_when_device_wires_fram")
def _scenario_webserver_pr_fram_backed(device: str) -> None:
    # WP1/CLAUDE.md's implicit-FRAM-wiring rule (SPECIFICATION.md Part A.7): every device's TOML
    # declares [device.wiring].fram_target, so webserver's self.pr is FRAM-backed on all 6, like
    # conn/ntp/sysfunct. No device-level fram_target is covered at the codegen level instead.
    module = build(device)
    assert module.webserver is not None
    assert isinstance(module.webserver.pr, PrintLogHistoryStore)
    assert module.webserver.pr.fram is not None


@_register("webserver_measurements_and_sensors_get_include_every_real_sensor")
def _scenario_webserver_measurements_and_sensors_get(device: str) -> None:
    # Shared shape with the twin's equivalent check (tests/_shared_rest_roundtrip.py). The expected
    # sensor-name set is derived reflectively from this device's present optional instances
    # (neopixel/notification aren't sensors=-registered), never a hardcoded 3-sensor literal.
    module = build(device)
    expected = {name.upper() for name in _present_optional_instances(module) if name in ("scd30", "sgp40", "bmp3xx", "isl29125")}
    res = _dispatch(module, "GET", "/measurements")
    assert res.status_code == 200
    measurements = json.loads(status_body(res))
    assert_sensor_payload_not_self_wrapped(measurements, expected)

    res = _dispatch(module, "GET", "/sensors")
    sensors = json.loads(status_body(res))
    assert_sensor_payload_not_self_wrapped(sensors, expected)


@_register("webserver_sensors_put_round_trips_a_real_field_through_the_real_driver")
def _scenario_sensors_put_sgp40(device: str) -> None:
    module = build(device)
    if not _has(module, "sgp40"):
        return  # every real device has sgp40 today, but this stays correct if a future one doesn't
    res = _dispatch(module, "PUT", "/sensors", {"SGP40": {"BackupPeriod": 5}})
    body = json.loads(res.body)
    assert body["result"] == {"SGP40": {"BackupPeriod": "Valid"}}
    assert run(module.sgp40.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}


@_register("webserver_sensors_put_round_trips_a_real_scd30_field_through_the_real_driver")
def _scenario_sensors_put_scd30(device: str) -> None:
    # SCD30_Reader is the only sensors=-registered module that is a plain SensorReader rather than
    # a SensorReaderConfig subclass (its params live on the sensor), so it never inherited
    # get_cfg_schema() - which _put_sensors() calls uniformly, crashing with a real 500 before.
    module = build(device)
    res = _dispatch(module, "PUT", "/sensors", {"SCD30": {"MeasInt": 4}})
    body = json.loads(res.body)
    assert body["result"] == {"SCD30": {"MeasInt": "Valid"}}


@_register("webserver_networking_put_ssid_group_reconnects_but_led_group_alone_does_not")
def _scenario_networking_put_ssid_group(device: str) -> None:
    module = build(device)
    assert module.conn is not None
    res = _dispatch(module, "PUT", "/networking", {"LedWifiOn": False})
    assert json.loads(res.body)["result"] == {"LedWifiOn": "Valid"}
    assert module.conn.reconn_wifi is False  # LedWifiOn alone must never reconnect

    res = _dispatch(module, "PUT", "/networking", {"Hostname": "TestHost"})
    assert json.loads(res.body)["result"] == {"Hostname": "Valid"}
    assert module.conn.reconn_wifi is True  # setNetwork's own field group did change


@_register("webserver_networking_put_ntp_fields_forces_a_resync")
def _scenario_networking_put_ntp(device: str) -> None:
    # Same observable-effect precedent as tests/test_setter_microdot_integration.py's own
    # ntp_force_sync() coverage: a failing-sync streak in progress, cleared to 0 by the post_asy_fct.
    module = build(device)
    assert module.ntp is not None
    module.ntp.ntp_retries = 3
    res = _dispatch(module, "PUT", "/networking", {"NTP_Host": "time.example.org"})
    assert json.loads(res.body)["result"] == {"NTP_Host": "Valid"}
    assert module.ntp.ntp_retries == 0  # post_asy_fct fired


@_register("webserver_system_put_debug_level_propagates_to_every_logger")
def _scenario_system_put_debug_level(device: str) -> None:
    module = build(device)
    assert module.sysfunct is not None and module.conn is not None
    res = _dispatch(module, "PUT", "/system", {"DebugLevel": PrintLog.level_err()})
    assert json.loads(res.body)["result"]["DebugLevel"] == "Valid"
    assert module.sysfunct.get_debug_level() == PrintLog.level_err()
    assert module.conn.pr.get_level() == PrintLog.level_err()  # pushed via the registry


@_register("webserver_system_put_gmt_dst_offset_applies_without_a_reconnect")
def _scenario_system_put_gmt_offset(device: str) -> None:
    module = build(device)
    assert module.ntp is not None and module.conn is not None
    res = _dispatch(module, "PUT", "/system", {"GMTOffset": 7200})
    assert json.loads(res.body)["result"] == {"GMTOffset": "Valid"}
    assert run(module.ntp.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 7200}
    assert module.conn.reconn_wifi is False  # unrelated to the networking settings groups


@_register("webserver_system_put_reboot_cmd_arms_the_real_reset_timer")
def _scenario_system_put_reboot(device: str) -> None:
    module = build(device)
    assert module.sysfunct is not None
    before = machine.reset_count
    res = _dispatch(module, "PUT", "/system", {"SystemCmd": "reboot"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Valid"
    module.sysfunct.reset_timer.trigger()  # fake Timer - fires the armed callback synchronously
    assert machine.reset_count == before + 1


@_register("webserver_system_put_reboot_flushes_a_still_pending_config_write_first")
def _scenario_system_put_reboot_flushes_pending_write(device: str) -> None:
    # A commanded reboot must not drop a still-staged write (the generated _flush_pending_configs(),
    # config_manager.py's flush_pending()) - unlike the accepted power-loss residual risk (Part F.2),
    # this path can wait the flush out. One PUT with a settings change plus SystemCmd=reboot.
    module = build(device)
    assert module.sysfunct is not None
    res = _dispatch(module, "PUT", "/system", {"DebugLevel": PrintLog.level_err(), "SystemCmd": "reboot"})
    result = json.loads(res.body)["result"]
    assert result["DebugLevel"] == "Valid"
    assert result["SystemCmd"] == "Valid"
    assert module.sysfunct.cfgmgr._pending_flush is None  # the exact thing being proven: already flushed, not merely scheduled


@_register("webserver_system_put_invalid_cmd_is_rejected_without_side_effects")
def _scenario_system_put_invalid_cmd(device: str) -> None:
    module = build(device)
    before = machine.reset_count
    res = _dispatch(module, "PUT", "/system", {"SystemCmd": "bogus"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Invalid"
    assert machine.reset_count == before


@_register("webserver_notification_put_light_cmd_led_dispatches_to_the_real_pixel_driver")
def _scenario_notification_put_light_cmd_led(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


@_register("webserver_notification_put_light_cmd_led_accepts_integral_float_rgb_and_int_t_coerced")
def _scenario_notification_light_cmd_led_integral_float(device: str) -> None:
    # config_manager.py's coerce_numeric() policy applied to lightCmdLED too (SPECIFICATION.md
    # Part A.8): an integral float r/g/b coerces to int, a plain int t coerces to float - both
    # directions a real client could plausibly send.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10.0, "g": 20.0, "b": 30.0, "t": 1}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


@_register("webserver_notification_put_light_cmd_led_rejects_fractional_rgb")
def _scenario_notification_light_cmd_led_rejects_fractional(device: str) -> None:
    # Regression test for the behavior this callback used to have (raw int()/float() truncating
    # casts): a fractional r/g/b is now rejected outright, not silently truncated (12.5 no longer
    # becomes a silent 12).
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10.5, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_non_numeric_field")
def _scenario_notification_light_cmd_led_rejects_non_numeric_field(device: str) -> None:
    # Another behavior change from the old raw int()/float() casts: those would parse a
    # numeric-looking string ("10") via Python's lenient constructors, while coerce_numeric() only
    # coerces between the two numeric types, so this is now rejected too.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": "10", "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_non_numeric_t")
def _scenario_notification_light_cmd_led_rejects_non_numeric_t(device: str) -> None:
    # t goes through cm.coerce_numeric(payload["t"], float) - a distinct code path from r/g/b's own
    # int coercion (already tested above for r specifically) - confirms the same non-numeric
    # rejection holds for t's own float-typed branch, not just the int-typed ones.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": "soon"}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_missing_field")
def _scenario_notification_light_cmd_led_rejects_missing_field(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30}})  # t missing
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_out_of_range_rgb")
def _scenario_notification_light_cmd_led_rejects_out_of_range_rgb(device: str) -> None:
    # Regression test for a real legacy-vs-src/ divergence (SPECIFICATION.md Part H.6's
    # dispatch-only field rules): legacy's led_cmd() rejects out-of-range r/g/b (0-255) where the
    # promoted callback used to silently clamp. Rejected exactly like a missing/non-numeric field.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 256, "g": 20, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_negative_rgb")
def _scenario_notification_light_cmd_led_rejects_negative_rgb(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": -1, "b": 30, "t": 1.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_out_of_range_t")
def _scenario_notification_light_cmd_led_rejects_out_of_range_t(device: str) -> None:
    # Legacy's own t bound is 0.5-60.0 - the promoted src/ callback used to floor a too-small t to
    # 0.1 and never bounded a too-large one at all.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 0.1}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 10, "g": 20, "b": 30, "t": 100.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_accepts_lower_boundary_rgb_and_t")
def _scenario_notification_light_cmd_led_lower_boundary(device: str) -> None:
    # Deliberately one dispatch per test: _dispatch() drives each call through its own fresh
    # asyncio.run(), so NeopixelDriver's consumer task never runs here - a second request_signal()
    # would find start_signal_event already set and never cleared, hanging in its own wait loop.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 0, "g": 255, "b": 0, "t": 0.5}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


@_register("webserver_notification_put_light_cmd_led_accepts_upper_boundary_rgb_and_t")
def _scenario_notification_light_cmd_led_upper_boundary(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"lightCmdLED": {"r": 255, "g": 0, "b": 255, "t": 60.0}})
    assert json.loads(res.body)["result"]["lightCmdLED"] == "Valid"


@_register("webserver_notification_put_pause_time_dispatches_to_the_real_coordinator")
def _scenario_notification_put_pause_time(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"PauseTime": 30})
    assert json.loads(res.body)["result"]["PauseTime"] == "Valid"


@_register("webserver_notification_put_flat_field_round_trips_through_the_real_coordinator")
def _scenario_notification_put_flat_field(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"WarnCO2": 1800})
    assert json.loads(res.body)["result"]["WarnCO2"] == "Valid"
    assert module.notification is not None
    assert run(module.notification.cfgmgr.get_dict(["WarnCO2"])) == {"WarnCO2": 1800}


@_register("webserver_status_get_reflects_the_real_object_graph")
def _scenario_status_get(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "GET", "/status")
    body = json.loads(status_body(res))
    assert set(body.keys()) == {"networking", "system", "notification", "sensors", "errcount"}
    # SGP40 and UARTLINK are the only maintenance-status sources any real device has today (VOC
    # backup/restore timestamps; UART transfer/failure counts) - reflective, not hardcoded, since a
    # future device with neither would otherwise go stale silently here.
    expected_sensors = set()
    if _has(module, "sgp40"):
        expected_sensors.add("SGP40")
    if _has_uart_link(module):
        expected_sensors.add("UARTLINK")
    assert set(body["sensors"].keys()) == expected_sensors
    if _has(module, "sgp40"):
        assert "BackupTS" in body["sensors"]["SGP40"] and "RestoreTS" in body["sensors"]["SGP40"]
    if _has_uart_link(module):
        assert "Transfers" in body["sensors"]["UARTLINK"] and "Failures" in body["sensors"]["UARTLINK"]
    assert "SysUptime" in body["system"] and "LocalTime" in body["system"] and "UtcTime" in body["system"]
    assert "WifiUptime" in body["networking"] and "NtpSynced" in body["networking"]
    assert "Triggered" in body["notification"] and "PauseTime" in body["notification"]
    # One entry per real module + per real ConfigManager + this service's own "WEBSERVER" entry,
    # from _all_loggers()'s reflected shape. By NAME, not count: the website's errcount rows are
    # keyed by name (Part H.6), so a published key nothing matches renders nothing at all.
    assert {logger.name for logger in _all_loggers(module)} == set(body["errcount"].keys())
    assert len(body["errcount"]) == len(_all_loggers(module)), "two loggers sharing a name would collapse into one row"


@_register("webserver_system_get_reports_the_real_build_info")
def _scenario_system_get_build_info(device: str) -> None:
    # SPECIFICATION.md Part L.7: every generated device embeds FIRMWARE_VERSION/WEBSITE_VERSION
    # plus a build timestamp under GET /system's "build" sub-entry, beside the flat Debug/GMT/DST
    # fields - the only proof of that flat shape. Build-info values are checked for shape only.
    module = build(device)
    res = _dispatch(module, "GET", "/system")
    body = json.loads(status_body(res))
    build_info = body.pop("build")
    assert set(body.keys()) == {"DebugLevel", "GMTOffset", "DSTOffset"}
    assert isinstance(build_info["firmwareVersion"], str) and build_info["firmwareVersion"]
    assert isinstance(build_info["websiteVersion"], str) and build_info["websiteVersion"]
    assert isinstance(build_info["buildDate"], str) and build_info["buildDate"]


@_register("webserver_status_put_reset_errors_clears_a_real_modules_history")
def _scenario_status_put_reset_errors(device: str) -> None:
    module = build(device)
    assert module.conn is not None
    run(module.conn.pr.err_s("simulated", errno=99))
    assert (run(module.conn.get_error_counter()))["WIFI"]["ErrCount"] == 1
    res = _dispatch(module, "PUT", "/status", {"ResetErrors": True})
    assert json.loads(res.body)["res"] == "OK"
    assert (run(module.conn.get_error_counter()))["WIFI"]["ErrCount"] == 0


@_register("webserver_status_put_reset_errors_is_not_undone_by_a_fram_loggers_later_setup")
def _scenario_status_reset_errors_not_undone(device: str) -> None:
    # SPECIFICATION.md Part C.7's boot window, reproduced exactly: every FRAM-backed logger runs
    # pr.setup() from inside its own task while the webserver already answers, so a ResetErrors PUT
    # can land on a stale chunk. build_system() starts no tasks, making that state deterministic.
    module = build(device)
    sgp = module.sgp40
    assert sgp is not None
    run(sgp.pr.setup())
    run(sgp.pr.err_s("simulated", errno=99))
    sgp.pr.initialized = False  # what the boot window looks like: bytes on the chip, RAM side not yet set up

    res = _dispatch(module, "PUT", "/status", {"ResetErrors": True})
    assert json.loads(res.body)["res"] == "OK"
    run(sgp.pr.setup())  # ... and only now does _init_sgp() get there

    log = run(sgp.get_error_counter())
    assert log["SGP40"]["ErrCount"] == 0
    assert 99 not in log["SGP40"]["ErrNum"], "setup() restored the pre-reset history over a reset that returned OK"


# ---------------------------------------------------------------------------
# Captive-portal hotspot-mode redirect wiring (SPECIFICATION.md Part A.5/A.7) - confirms
# `is_hotspot_active=conn.is_hotspot_active` reaches the real wired conn through the real
# construction graph. No WiFi task runs: conn._conn_phase is set directly, this file's test seam.
# ---------------------------------------------------------------------------


@_register("is_hotspot_active_wiring_redirects_when_conn_is_in_hotspot_phase")
def _scenario_hotspot_redirects(device: str) -> None:
    module = build(device)
    assert module.conn is not None
    module.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch(module, "GET", "/generate_204")
    assert res.status_code == 302
    assert res.headers["Location"] == "/"


@_register("is_hotspot_active_wiring_default_sta_phase_still_404s")
def _scenario_hotspot_default_sta_404(device: str) -> None:
    # Error-path/good-outcome baseline: AsyConnTime.__init__ starts in _PHASE_STA_SEEKING - the real
    # wiring must not accidentally redirect before hotspot mode is ever reached.
    module = build(device)
    assert module.conn is not None
    assert module.conn._conn_phase == _PHASE_STA_SEEKING
    res = _dispatch(module, "GET", "/generate_204")
    assert res.status_code == 404


@_register("is_hotspot_active_wiring_dynamic_phase_switch_is_reflected_live")
def _scenario_hotspot_dynamic_switch(device: str) -> None:
    # Dynamic-mode-switch coverage through the real construction graph: flips the real conn's phase
    # back and forth on the same built system and confirms each dispatch reflects the phase at call
    # time, not whatever it was when WebserverService(...) was constructed.
    module = build(device)
    assert module.conn is not None
    conn = module.conn

    assert _dispatch(module, "GET", "/generate_204").status_code == 404

    conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch(module, "GET", "/generate_204")
    assert res.status_code == 302
    assert res.headers["Location"] == "/"

    conn._conn_phase = _PHASE_STA_SEEKING
    assert _dispatch(module, "GET", "/generate_204").status_code == 404


@_register("is_hotspot_active_wiring_real_static_root_and_api_route_unaffected_in_hotspot_mode")
def _scenario_hotspot_real_routes_unaffected(device: str) -> None:
    # Upstream/downstream error handling: real content must keep flowing through cleanly - the
    # redirect fallback must never shadow an actual file hit or a real API route, hotspot mode or not.
    module = build(device)
    assert module.conn is not None
    module.conn._conn_phase = _PHASE_HOTSPOT

    res = _dispatch(module, "GET", "/")
    assert res.status_code == 200  # real (stub) index.html, not a redirect loop

    res = _dispatch(module, "GET", "/measurements")
    assert res.status_code == 200
    expected = {name.upper() for name in _present_optional_instances(module) if name in ("scd30", "sgp40", "bmp3xx", "isl29125")}
    assert_sensor_payload_not_self_wrapped(json.loads(status_body(res)), expected)


@_register("is_hotspot_active_wiring_directory_traversal_still_404s_in_hotspot_mode")
def _scenario_hotspot_directory_traversal_404s(device: str) -> None:
    # All-paths coverage through the real wiring: the ".." guard clause in _serve_static() runs
    # before is_hotspot_active() is ever consulted (see asy_webserver_service.py's own source order).
    module = build(device)
    assert module.conn is not None
    module.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch(module, "GET", "/foo/../../index.html")
    assert res.status_code == 404


@_register("is_hotspot_active_wiring_put_to_unmatched_path_still_405_in_hotspot_mode")
def _scenario_hotspot_put_unmatched_405(device: str) -> None:
    # All-paths coverage: a non-GET request to an unmatched path resolves to 405 inside Microdot's
    # own routing before _serve_static() is ever reached - real hotspot state must not change that.
    module = build(device)
    assert module.conn is not None
    module.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch(module, "PUT", "/generate_204", {})
    assert res.status_code == 405


# ---------------------------------------------------------------------------
# Registration: one test_<scenario> per scenario, for whichever single device the caller names -
# microtest.py discovers every callable in globals() named test_*, the only parametrization
# mechanism available here (no real pytest on MicroPython - SPECIFICATION.md Part E.1).
#
# fn is bound as a default-argument value rather than read from the loop variable, or every
# generated test would share the same last-iteration fn.
#
# One device per call: each tests/test_sensortask_<device>.py calls this once, for its own device,
# so the scenarios run as one independent Unix-port process per device instead of one process
# building all 6 object graphs for every scenario (this module's docstring has the rationale).
# ---------------------------------------------------------------------------


def register_for_device(device: str) -> "dict[str, Callable[[], None]]":
    global _scratch
    assert device in _DEVICES, f"{device!r} is not one of this module's own real devices {_DEVICES!r}"
    _scratch = TmpScratch(f"sensortask_{device}")

    tests: dict[str, Callable[[], None]] = {}
    for scenario_name, scenario_fn in _SCENARIOS:

        def _make_test(fn: "Callable[[str], None]" = scenario_fn) -> "Callable[[], None]":
            def test() -> None:
                fn(device)

            return test

        tests[f"test_{scenario_name}"] = _make_test()
    return tests
