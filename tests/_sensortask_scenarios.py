"""Shared scenario library: build_system() construction/wiring for every real device, plus real
webserver wiring (deep per-route behavior stays tests/test_asy_webserver_service.py's job).
Not a test file - register_for_device() is the export; SPECIFICATION.md Part E.2.1 has the split."""

import asyncio
import json
import os
import struct
import sys
import time

# Same convention as tests/test_asy_webserver_service.py: scripts/test.sh's MICROPYPATH excludes
# ext/, and every generated sensortask_<device> transitively imports microdot - extending sys.path
# reaches the real vendored ext/microdot.py without a build-environment scope change.
sys.path.insert(0, "ext")

import machine
import network
import rp2
from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _shared_rest_roundtrip import (
    assert_named_modules_constructed,
    assert_sensor_payload_not_self_wrapped,
    drain_json_response_body,
)
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen
from microdot import Request, Response

import asy_config_manager
import asy_spi_driver
import asy_system_service
import asy_wifi_service
from asy_base_classes import SensorReader, SensorReaderConfig
from asy_crc_checks import CRC8
from asy_fram_manager import FRAMManager, _owner_seed
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService
from asy_ntp_client import NTP
from asy_print_log import PrintLogHistory, PrintLogHistoryStore
from asy_system_service import SystemService
from asy_uart_link_driver import UARTLinkDriver
from asy_webserver_service import WebserverService

# Mirrors asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_HOTSPOT values - same
# not-importable-once-const()-folded reasoning as tests/test_asy_wifi_service.py's own copy; keep in
# sync with asy_wifi_service.py's own definitions if those ever change.
_PHASE_STA_SEEKING = 0
_PHASE_HOTSPOT = 2

# Every pair of read triggers stays at least this far apart (SPECIFICATION.md Part C.9.1); estimated,
# measurement owed: the worst-case read duration per driver on the bench, in a hardware session.
# @tunable stagger.min_read_separation_ms = 100
_MIN_READ_SEPARATION_MS = 100

# A refused LED command answers at once; the bound also ends a regression that waits instead of
# letting it hang the file.
# @tunable l1.sensortask_led_refusal_ms = 100
_LED_REFUSAL_MS = 100

# A status read never waits on wifi_mode_lock; the bound only ends a regression that does, instead of
# letting it hang the file (one GET /status here takes 0.1-0.3 s).
# @tunable l1.sensortask_locked_status_ms = 5000
_LOCKED_STATUS_MS = 5000

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


def status_body(res: "Response") -> bytes:
    # GET /status streams a list of already-json.dumps()-encoded fragments (see
    # asy_webserver_service.py's _build_status_pieces()); draining it the way a real client would
    # keeps every json.loads(...) assertion on a /status response working unchanged.
    return drain_json_response_body(res.body)


# Every real device (devices/*.toml) - buildgen generates each one's own module + wiring plan into
# build/generated_src/ before scripts/test.sh ever runs this file (scripts/_generate_sensortask_modules.py).
_DEVICES = ("wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi")


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # dev's real FRAM: a 256KB MB85RS2MTA with its own RDID (DS501-00032 p.10), not the base fake's 8KB
    # MB85RS64V. A subclass, since build_system() offers no post-construction hook.
    SIZE = 0x40000
    RDID = bytes([0x04, 0x7F, 0x48, 0x03])


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


def fram_fake_class(device: str) -> "type[FakeMB85RS64V]":
    # Public because tests/_boot_contiguity_probe.py boots the same devices from its own script
    # entry point: shared rather than copied, so the RDID table above stays the one place the
    # tests tier maps a device to its real chip.
    plan = _wiring_plan(device)
    (spi_attachment,) = plan["spi"].values()  # every real device has exactly one FRAM/SPI instance
    return _FRAM_FAKE_BY_MAX_SIZE[spi_attachment["max_size"]]


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


async def _boot(device: str, cfg_path: "str | None" = None, chip: "type[FakeMB85RS64V] | None" = None, **kwargs: "Any") -> "Any":
    # Per-call, not module-level: different devices need different FRAM fakes (max_size/RDID), and
    # several devices' own modules get booted in this one process across this file's full run.
    asy_spi_driver._SPI = fram_fake_class(device) if chip is None else chip  # type: ignore[misc]
    rp2.DMA.reset_registry()  # each build is a boot: the soft reset before it frees every DMA channel
    module = __import__(f"sensortask_{device}")
    await module.build_system(cfg_path=cfg_path if cfg_path is not None else _tmp_cfg_dir(), **kwargs)
    return module


def build(device: str, cfg_path: "str | None" = None, chip: "type[FakeMB85RS64V] | None" = None, **kwargs: "Any") -> "Any":
    return run(_boot(device, cfg_path, chip, **kwargs))


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
        module.conn._dns_server.pr,
        module.ntp.pr,
        module.ntp.cfgmgr.pr,
        module.fram.pr,
        module.neopixel.pr,
        module.sysfunct.pr,
        module.sysfunct.cfgmgr.pr,
    ]
    # The collector's order: conn and ntp first, then buildgen's construction order, where the
    # NeoPixel precedes conn (passed as its ext_led) and scd30 precedes sgp40 (its compensation
    # source). setters[i] is paired with loggers[i] elsewhere, so this is load-bearing.
    if _has(module, "scd30"):
        loggers += [module.scd30.pr, module.scd30.cfgmgr.pr]
    if _has(module, "sgp40"):
        loggers += [module.sgp40.pr, module.sgp40.cfgmgr.pr]
    if _has(module, "bmp3xx"):
        loggers += [module.bmp3xx.pr, module.bmp3xx.cfgmgr.pr]
    if _has(module, "isl29125"):
        loggers += [module.isl29125.pr, module.isl29125.cfgmgr.pr]
    loggers += [module.notification.pr, module.notification.cfgmgr.pr]
    if _has_uart_link(module):
        # No cfgmgr - UARTComm has no config schema (its parameters are an out-of-band wire
        # contract, never runtime-writable, SPECIFICATION.md Part J.6), one entry per instance.
        loggers += [module.uart_link_init.pr, module.uart_link_resp.pr]
    loggers.append(module.webserver.pr)
    return loggers


def _ram_only_config_logs(module: "Any") -> "list[str]":
    # The config loggers a reader's class keeps off FRAM (_CFG_LOG_FRAM False): read from the class, never named.
    owners = [getattr(module, name) for name in _present_optional_instances(module)]
    return sorted(owner.cfgmgr.pr.name for owner in owners if getattr(owner, "cfgmgr", None) is not None and not getattr(type(owner), "_CFG_LOG_FRAM", True))


_READER_OWNERS = (("scd30", "SCD30"), ("sgp40", "SGP40"), ("bmp3xx", "BMP3XX"), ("isl29125", "ISL29125"))
_STATUS_BYTES_PER_BLOCK = 2  # mirrors asy_fram_manager.py's _NUM_STATUS_BYTES (const(), not importable); keep in sync


def _expected_fram_chunk_owners(module: "Any") -> "list[str]":
    # SPECIFICATION.md Part A.7's "Real FRAM chunk order": construction order, the NeoPixel first (conn's
    # ext_led), each module's own log then its FRAM-backed config log, conn's captive DNS after conn's two.
    owners = ["NEOPIXEL", "WIFI", "CFGMGR_WIFI", "DNSSRV", "NTP", "CFGMGR_NTP", "SYSTEM", "CFGMGR_SYSTEM"]
    for attr, name in _READER_OWNERS:
        if _has(module, attr):
            reader = getattr(module, attr)
            owners.append(name)
            if getattr(type(reader), "_CFG_LOG_FRAM", True):  # derived from the class, never named
                owners.append("CFGMGR_" + name)
            if attr == "sgp40":
                owners.append(reader.name + "_VOC")  # the VOC backup's owner, read from the built reader
    owners += ["NOTIFY", "CFGMGR_NOTIFY"]
    if _has_uart_link(module):
        owners += ["UART_init", "UART_resp"]  # no config store: the link's parameters are a wire contract
    owners.append("WEBSERVER")
    return owners


def _fram_stores(module: "Any") -> "list[Any]":
    return [logger for logger in _all_loggers(module) if isinstance(logger, PrintLogHistoryStore) and logger.fram is not None]


def _fram_chunks(module: "Any") -> "list[tuple[str, Any]]":
    # Every chunk the built graph holds, with the owner name it was allocated under, in address order.
    chunks = [(logger.name, logger.fram) for logger in _fram_stores(module)]
    if _has(module, "sgp40") and module.sgp40._ts_storage is not None:
        chunks.append((module.sgp40.name + "_VOC", module.sgp40._ts_storage))
    return sorted(chunks, key=lambda owned: owned[1]._block_addr[0])


def _fram_chip(module: "Any") -> "Any":
    return module.fram.fram._spidev.spi._spi


def _sensor_reader_owners(module: "Any") -> "list[Any]":
    # Every SensorReader/SensorReaderConfig instance real construction wires a task/timer starter
    # for - reflective over the same optional-instance set _present_optional_instances() derives,
    # plus the mandatory infra modules every real device always has.
    owners = [getattr(module, name) for name in ("scd30", "bmp3xx", "sgp40", "neopixel", "notification") if _has(module, name)]
    owners += [module.sysfunct, module.conn, module.ntp]
    return owners


def _dispatch(module: "Any", method: str, path: str, json_body: "dict[str, Any] | None" = None, timeout_ms: "int | None" = None) -> "Response":
    assert module.webserver is not None
    app = module.webserver._app
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    req = Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body)
    coro = app.dispatch_request(req)
    if timeout_ms is not None:  # a request that must answer at once fails with TimeoutError, never hangs
        coro = asyncio.wait_for_ms(coro, timeout_ms)
    return run(coro)  # type: ignore[no-any-return]  # the upstream stub leaves dispatch_request() unannotated - removal trigger: SPECIFICATION.md B.15


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


@_register("every_build_starts_with_every_dma_channel_free")
def _scenario_every_build_starts_with_every_dma_channel_free(device: str) -> None:
    # Each UART link claims two of the twelve DMA channels in its setup; without the per-build reset a
    # process rebuilding a linked graph runs out on its third build. Four builds, each after every channel was taken.
    for _ in range(4):
        stale = []
        while True:
            try:
                stale.append(rp2.DMA())
            except OSError:
                break
        assert stale, f"{device}: no DMA channel was free to plant before this build"
        build(device)
        assert all(channel.channel == 0xFF for channel in stale), f"{device}: a DMA channel held before the build was still claimed after it"


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
    scd_bus = module.scd30._scd._i2c_scd30.i2c_device.i2c
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
    # The NeoPixel is constructed before conn and passed as its ext_led at construction. Confirmed
    # indirectly: WifiService's own ext_led slot is set.
    module = build(device)
    assert module.conn is not None
    assert module.conn._ext_led is module.neopixel


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
    from asy_ntp_client import NTPClient
    from asy_system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = NTPClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    async def _fake_start_timers(self: "SystemService", triggers: "list[Callable[[], None]]", timers: "list[Callable[[], None]]") -> None:
        pass

    async def _fake_force_sync(self: "NTPClient") -> None:
        pass

    async def _fake_start_and_check(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        pass  # never loops - this test only cares that build_system() received the override

    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    NTPClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.start_and_check_tasks = _fake_start_and_check  # type: ignore[method-assign]
    try:
        asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
        module = __import__(f"sensortask_{device}")
        run(module.main(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        NTPClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]
    assert module.webserver is not None
    assert module.webserver._host == "127.0.0.1"
    assert module.webserver._port == 8080


# ---------------------------------------------------------------------------
# FRAM chunk layout: one build's on-chip layout, fixed within that build and free to change in the
# next (owner, 2026-09-26); each chunk's CRC is seeded by its owner, so another build's bytes read blank.
# ---------------------------------------------------------------------------


def _layout(module: "Any") -> "list[tuple[str, int, int]]":
    return [(owner, chunk._block_addr[0], chunk.size) for owner, chunk in _fram_chunks(module)]


@_register("fram_chunk_layout_is_contiguous_deterministic_and_in_owner_order")
def _scenario_fram_chunk_layout(device: str) -> None:
    module = build(device)
    chunks = _fram_chunks(module)
    owners = [owner for owner, _chunk in chunks]
    assert owners == _expected_fram_chunk_owners(module), owners
    assert len(set(owners)) == len(owners), f"two chunks share an owner name, so they share a CRC seed: {owners}"
    end = 0
    for owner, chunk in chunks:
        assert chunk._block_addr[0] == end, (owner, chunk._block_addr, end)  # bump allocation: no gap, no overlap
        assert chunk._crc_seed == _owner_seed(owner, chunk.crc), f"{owner}'s chunk is not seeded by its own name"
        end += 2 * (chunk.size + chunk.crc.length() + _STATUS_BYTES_PER_BLOCK)
    assert end == module.fram._allocated_size
    first = _layout(module)
    assert _layout(build(device)) == first  # a second build of the same image lays out identically


def _chip_holding(base: "type[FakeMB85RS64V]", image: bytes) -> "type[FakeMB85RS64V]":
    # The device's own part, powered up holding `image`: what the next boot finds on the chip.
    class _Holding(base):  # type: ignore[valid-type,misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self.memory[:] = image

    return _Holding


def _log_one_entry_everywhere(module: "Any", text: str) -> None:
    for logger in _fram_stores(module):
        run(logger.err_s(text, errno=code("E", "INIT")))


def _error_count(logger: "Any") -> int:
    count: int = run(logger.get_log())[logger.name]["ErrCount"]
    return count


def _assert_every_chunk_starts_empty_and_accepts_writes(device: str, image: bytes) -> None:
    # A boot on an image this build did not write: no owner restores anything, every store is set up on a
    # re-initialised chunk, and a reboot on the same filesystem then restores what that boot wrote.
    base = fram_fake_class(device)
    cfg_path = _tmp_cfg_dir()
    module = build(device, cfg_path, chip=_chip_holding(base, image))
    stores = _fram_stores(module)
    for logger in stores:
        assert logger.initialized is True, f"{logger.name} stayed RAM-only on a foreign image"
        assert _error_count(logger) == 0, f"{logger.name} restored a history it never wrote"
    if _has(module, "sgp40"):
        backup = module.sgp40._ts_storage
        valid, _ts, _age = run(backup.read_into(backup.get_buffer()))
        assert valid is False, "the VOC backup read a foreign image as a backup"
    fram_log = run(module.fram.get_error_counter())["FRAM"]
    content = {("E", code("E", n)) for n in ("FRAM_STATUS_BYTE", "FRAM_STATUS_DISAGREE", "FRAM_DATA_CRC", "FRAM_COPIES_DIFFER")}
    content.add(("W", code("W", "FRAM_BLOCK_INVALID")))
    found = {(kind, fram_log["ErrNum"][i]) for i, kind in enumerate(fram_log["ErrType"]) if kind != "N"}
    assert found <= content, f"a foreign image raised a fault, not a content state: {found - content}"
    # No flood: each of a chunk's two blocks is read once, and its CRC check and its block check each keep one entry.
    assert fram_log["ErrCount"] <= 2 * 2 * len(_fram_chunks(module)), fram_log
    _log_one_entry_everywhere(module, "written after the foreign image")
    rewritten = bytes(_fram_chip(module).memory)
    module = build(device, cfg_path, chip=_chip_holding(base, rewritten))
    for logger in _fram_stores(module):
        log = run(logger.get_log())[logger.name]
        assert log["ErrCount"] == 1 and code("E", "INIT") in log["ErrNum"], (logger.name, log)


def _image_with_every_chunk_written(device: str) -> "tuple[bytes, int]":
    # One entry in every store and one VOC backup: every chunk holds a valid dual copy. Also returns the
    # first chunk's full size, the shift a layout with one more leading chunk of that size would have.
    module = build(device)
    _log_one_entry_everywhere(module, "written by the previous build")
    if _has(module, "sgp40"):
        backup = module.sgp40._ts_storage
        data = backup.get_buffer().get_data_buf()
        assert data is not None
        written, _synced, _utc = run(backup.write(bytes(len(data))))
        assert written is True
    _owner, first = _fram_chunks(module)[0]
    return bytes(_fram_chip(module).memory), 2 * (first.size + first.crc.length() + _STATUS_BYTES_PER_BLOCK)


@_register("first_boot_after_a_reflash_reinitialises_every_chunk_without_flood")
def _scenario_first_boot_after_a_reflash(device: str) -> None:
    # Another build's bytes over this build's addresses read as invalid and are re-initialised, with no
    # crash and no error flood (owner, 2026-09-26). Rotating the image by 3 bytes misaligns every chunk.
    image, _shift = _image_with_every_chunk_written(device)
    _assert_every_chunk_starts_empty_and_accepts_writes(device, image[3:] + image[:3])


@_register("a_layout_shifted_by_one_chunk_restores_no_neighbours_history")
def _scenario_layout_shifted_by_one_chunk(device: str) -> None:
    # An image from a build with one more leading chunk: each equal-size chunk now holds its neighbour's
    # valid dual copy, and only the owner seed tells them apart, so every owner must read it as blank.
    image, shift = _image_with_every_chunk_written(device)
    _assert_every_chunk_starts_empty_and_accepts_writes(device, bytes(shift) + image[: len(image) - shift])


@_register("fram_chunks_are_all_successfully_allocated_not_out_of_memory")
def _scenario_fram_chunks_allocated(device: str) -> None:
    module = build(device)
    # Every FRAM-chunk-owning module degrades to in-memory-only on allocation failure rather than
    # raising (asy_base_classes.py's contract) - assert the happy path got real chunks, not a degraded
    # one. This is also the per-device "does everything fit" capacity check.

    # The real enforcement is exactly this - no chunk-holding module ended up with a None chunk -
    # not `_allocated_size <= size`, which get_chunk() makes true by construction. The negative case
    # is test_asy_base_classes.py's test_sensorreaderconfig_fram_allocation_failure_and_missing_....
    assert module.conn is not None and module.ntp is not None
    assert module.sysfunct is not None and module.neopixel is not None and module.notification is not None
    assert isinstance(module.conn.pr, PrintLogHistoryStore)
    assert module.conn.pr.fram is not None
    assert isinstance(module.conn.cfgmgr.pr, PrintLogHistoryStore)
    assert module.conn.cfgmgr.pr.fram is not None
    assert isinstance(module.conn._dns_server.pr, PrintLogHistoryStore)
    assert module.conn._dns_server.pr.fram is not None
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
        assert not isinstance(module.scd30.cfgmgr.pr, PrintLogHistoryStore)  # its class keeps the config log off FRAM
    if _has(module, "sgp40"):
        assert isinstance(module.sgp40.pr, PrintLogHistoryStore)
        assert module.sgp40.pr.fram is not None
        assert module.sgp40._ts_storage is not None
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
        # WP3 - own chunk each, no cfgmgr (UARTComm has no on-flash config schema).
        assert isinstance(module.uart_link_init.pr, PrintLogHistoryStore)
        assert module.uart_link_init.pr.fram is not None
        assert isinstance(module.uart_link_resp.pr, PrintLogHistoryStore)
        assert module.uart_link_resp.pr.fram is not None


@_register("the_fram_manager_is_the_only_error_source_whose_own_log_is_not_fram_backed")
def _scenario_only_the_fram_manager_logs_in_memory(device: str) -> None:
    module = build(device)
    # scripts/_digital_twin_ci_suite.py's Run 5c sweeps the whole errcount table and exempts its
    # _IN_MEMORY_ONLY_ERROR_SOURCES. Pinned from the real object graph: FRAMManager (the store cannot persist its
    # own failures through itself) and the config logs a reader's class keeps off FRAM are the in-memory ones.
    in_memory = sorted(logger.name for logger in _all_loggers(module) if not isinstance(logger, PrintLogHistoryStore))
    expected = sorted(["FRAM"] + _ram_only_config_logs(module))
    assert in_memory == expected, f"{device}: only the FRAM manager's own log and the RAM-only config logs may be in-memory-only, found {in_memory}"


class _DeadFramChip(FakeMB85RS64V):
    # Same technique as test_fram_integration.py's
    # test_sensorreader_runs_in_degraded_mode_when_fram_setup_never_succeeded: a real device-ID
    # mismatch, not just fram=None - the chip responds, it just never comes up as the expected one.
    RDID = bytes([0xFF, 0xFF, 0xFF, 0xFF])


def _ram_only_entries(logger: "Any") -> int:
    log = run(logger.get_log())[logger.name]
    return sum(1 for i, kind in enumerate(log["ErrType"]) if kind == "E" and log["ErrNum"][i] == code("E", "LOG_RAM_ONLY"))


async def _supervise_until_the_reboot_is_armed(sysfunct: "Any", starters: "list[Any]") -> None:
    sup = asyncio.create_task(sysfunct.start_and_check_tasks(starters))
    for _ in range(5000):
        if sysfunct._reset_armed or sup.done():
            break
        await asyncio.sleep(0)
    sup.cancel()
    await asyncio.sleep(0)


@_register("a_declared_dead_fram_chip_escalates_to_a_reboot")
def _scenario_dead_fram_chip_escalates(device: str) -> None:
    # A declared chip that never comes up escalates like every other declared chip (owner, 2026-09-29: 'the
    # same as all other chips'); until the reboot every module keeps logging in RAM (owner, 2026-08-11).
    module = build(device, chip=_DeadFramChip)
    assert module.fram is not None and module.sysfunct is not None
    assert module.neopixel is not None and module.notification is not None
    rdids = _fram_chip(module).rdid_count
    assert rdids == 3, rdids  # identification retried before setup gives up
    assert module.fram.initialized is False
    assert module.fram.fram.initialized is False

    # Every chunk is still allocated (bookkeeping, SPECIFICATION.md Part C.13) but unreadable: each store
    # runs RAM-only for this boot and says so once in its own history, then keeps counting in memory.
    stores = _fram_stores(module)
    assert stores
    for logger in stores:
        assert logger.initialized is False, logger.name
        assert _ram_only_entries(logger) == 1, logger.name
        assert _error_count(logger) == 1, logger.name
    run(module.sysfunct.pr.err_s("boom", errno=code("E", "INIT")))  # never raises despite the dead chip
    assert run(module.sysfunct.get_error_counter())["SYSTEM"]["ErrCount"] == 2
    if _has(module, "sgp40"):  # its backup chunk is allocated but unusable; the reader itself keeps running
        assert module.sgp40._ts_storage is not None

    # The manager's one supervised task ends at once, so the supervisor's restart budget arms the reboot.
    (watch,) = module.fram.get_task_starters()
    assert watch in module._collect_task_starters()
    asy_system_service.asyncio = _AsyncioWaits()  # type: ignore[assignment]
    try:
        run(_supervise_until_the_reboot_is_armed(module.sysfunct, [watch]))
    finally:
        asy_system_service.asyncio = asyncio
    assert module.sysfunct._reset_armed is True
    assert machine.mem_backup(0)[1] == _system_const("_RR_TASK_BUDGET")
    assert module.sysfunct._reset_timer.callback is not None
    run(_cancel_reset_task(module.sysfunct))


# ---------------------------------------------------------------------------
# setup() batch: grouped, fixed order, notification.setup() last.
# ---------------------------------------------------------------------------


@_register("setup_batch_runs_every_unit_in_the_generated_order")
def _scenario_setup_batch_order(device: str) -> None:
    # Every class defining its own setup() is wrapped to record which object ran it; the recorded
    # objects, named by their module globals, must equal the generated batch's `await X.setup()` order.
    ran: list[object] = []

    def recording(real: "Callable[[Any], Coroutine[Any, Any, bool]]") -> "Callable[[Any], Coroutine[Any, Any, bool]]":
        async def setup(self: "Any") -> bool:
            ran.append(self)
            return await real(self)

        return setup

    candidates: tuple[Any, ...] = (SensorReader, SensorReaderConfig, SystemService, FRAMManager, NotificationService, UARTLinkDriver, WebserverService, NeopixelDriver)
    owners = [cls for cls in candidates if getattr(cls, "setup", None) is not None and all(getattr(base, "setup", None) is not cls.setup for base in cls.__bases__)]
    originals = [(cls, cls.setup) for cls in owners]
    for cls, real in originals:
        cls.setup = recording(real)
    try:
        module = build(device)
    finally:
        for cls, real in originals:
            cls.setup = real

    # super().setup() inside a recorded setup records the same object again, back to back: one unit.
    units = [obj for n, obj in enumerate(ran) if n == 0 or obj is not ran[n - 1]]
    by_id = {id(getattr(module, name)): name for name in dir(module) if not name.startswith("_")}
    with open(module.__file__) as f:  # the module actually loaded, wherever MICROPYPATH found it
        expected = [line.strip()[len("await ") : -len(".setup()")] for line in f if line.strip().startswith("await ") and line.strip().endswith(".setup()")]
    assert [by_id.get(id(obj), repr(obj)) for obj in units] == expected
    # fram first (sysfunct's FRAM-backed store logs to it), every sensor reader set up, the webserver last.
    fram_vars = [name for name in expected if name.startswith("fram")]
    assert expected[: len(fram_vars)] == fram_vars
    readers = [name for name in dir(module) if not name.startswith("_") and isinstance(getattr(module, name), SensorReader)]
    assert readers
    for name in readers:
        assert name in expected, f"{name} is not set up in the batch"
    assert expected[-1] == "webserver"


@_register("boot_feeds_the_watchdog_exactly_once_per_setup_call")
def _scenario_boot_feeds_the_watchdog(device: str) -> None:
    # WP6 (SPECIFICATION.md Part D.9/G.2): the generated boot sequence must actually execute a feed
    # after every setup() call, not just emit one in source (tests_scripts/test_buildgen_generate.py
    # proves the codegen shape). The expected count comes from the generated source, not by hand.
    module = build(device)
    with open(module.__file__) as f:  # the module actually loaded, wherever MICROPYPATH found it
        source_lines = f.readlines()
    expected_feeds = sum(1 for line in source_lines if line.strip().startswith("await ") and line.strip().endswith(".setup()"))
    assert expected_feeds > 0
    assert module.sysfunct is not None and module.watchdog is not None
    assert module.sysfunct._watchdog is module.watchdog
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
    # The coordinator takes its signals at construction and builds its combined schema there, so its
    # cfgmgr exists, and is valid once the setup() batch has run, with no post-construction step.
    module = build(device)
    assert module.notification is not None
    assert module.notification.cfgmgr.valid is True


@_register("every_measurement_starts_none_on_every_sensor")
def _scenario_measurements_start_none(device: str) -> None:
    # Right after the boot setup and before any task runs, every registered sensor answers its whole map with
    # None: "not yet measured" is the one starting value. No value is a tuple or list; a dict is only a
    # documented nested group (ISL29125's RGB/HSB, SPECIFICATION.md Part M.1), itself all None.
    module = build(device)
    sensors = list(module.webserver._sensors.values())
    assert sensors
    for sensor in sensors:
        data = run(sensor.get_dict_data())
        assert len(data) == 1, data
        for name, fields in data.items():
            leaves = [v for value in fields.values() for v in (value.values() if isinstance(value, dict) else [value])]
            assert fields and all(leaf is None for leaf in leaves), (name, fields)


@_register("a_fresh_filesystem_boot_writes_each_config_file_once")
def _scenario_fresh_filesystem_writes_once(device: str) -> None:
    # A first boot over an empty config dir writes each store's file once, with its defaults; a store whose schema
    # stores nothing writes none; a second boot over the same dir writes nothing; a rebuild writes only what is missing.
    cfg_path = _tmp_cfg_dir()
    first, second = _DirWrites(cfg_path), _DirWrites(cfg_path)
    with first:
        module = build(device, cfg_path=cfg_path)
    owners = [obj for obj in _module_objects(module).values() if getattr(obj, "cfgmgr", None) is not None]
    storing = [obj.cfgmgr for obj in owners if any(asy_config_manager.check_cfg_get_default(field)[0] for field in obj.get_cfg_schema())]
    assert sorted(first.paths) == sorted(cfg_path + "config_" + store.name[len("CFGMGR_") :] + ".cfg" for store in storing), first.paths
    with second:
        build(device, cfg_path=cfg_path)
    assert second.paths == []
    # A config reset cut by a power loss after k removals: the rebuild writes each removed file once, with its
    # defaults, and no other.
    removed = sorted(first.paths)[::2]
    for path in removed:
        os.remove(path)
    third = _DirWrites(cfg_path)
    with third:
        build(device, cfg_path=cfg_path)
    assert sorted(third.paths) == removed


class _DirWrites(WriteCountingOpen):
    # Counts only the opens for writing inside one config dir: an earlier scenario's still-pending flush task may
    # run during this boot's event loop, into its own dir.
    def __init__(self, cfg_path: str) -> None:
        super().__init__(asy_config_manager)
        self.cfg_path = cfg_path
        self.paths: list[str] = []

    def __call__(self, path: str, mode: str = "r") -> object:
        if "w" in mode and path.startswith(self.cfg_path):
            self.paths.append(path)
        return super().__call__(path, mode)


# ---------------------------------------------------------------------------
# Debug level - persisted on sysfunct, pushed live to every logger's own set_level() through a
# registry collected once at boot (owner, 2026-08-11: system-wide, no shared mutable value).
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
        loggers[i].set_level(0)
        setters[i](4)
        assert loggers[i].level == 4


def _system_debug_level(module: "Any") -> object:
    return json.loads(status_body(_dispatch(module, "GET", "/system")))["DebugLevel"]


@_register("debug_seed_value_is_the_starting_level_before_setup_resolves_the_persisted_one")
def _scenario_debug_seed_value(device: str) -> None:
    module = build(device, debug=2)
    # First boot - no persisted value yet, so sysfunct.setup() writes and resolves the schema default (0),
    # then pushes it through the registry, overriding the debug= seed each logger was constructed with.
    assert _system_debug_level(module) == 0
    for pr in _all_loggers(module):
        assert pr.level == 0, f"{pr.name!r} still shows the debug= seed, not the resolved default"


@_register("system_put_debug_level_updates_every_logger_in_the_object_graph")
def _scenario_set_debug_level_updates_every_logger(device: str) -> None:
    # The whole observable effect of the /system setting: every logger's own set_level() called, no shared
    # mutable value anywhere.
    module = build(device)
    res = _dispatch(module, "PUT", "/system", {"DebugLevel": 1})
    assert json.loads(res.body)["result"]["DebugLevel"] == "Valid"
    for pr in _all_loggers(module):
        assert pr.level == 1, f"{pr.name!r} did not observe the DebugLevel PUT"


@_register("debug_level_survives_a_simulated_reboot_through_build_system")
def _scenario_debug_level_survives_reboot(device: str) -> None:
    cfg_path = _tmp_cfg_dir()
    module = build(device, cfg_path=cfg_path)
    assert json.loads(_dispatch(module, "PUT", "/system", {"DebugLevel": 1}).body)["result"]["DebugLevel"] == "Valid"
    run(module.sysfunct.cfgmgr.flush_pending())

    module = build(device, cfg_path=cfg_path)  # simulated reboot - same cfg_path, fresh objects
    assert _system_debug_level(module) == 1
    for pr in _all_loggers(module):
        assert pr.level == 1, f"{pr.name!r} did not get the persisted level on reboot"


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
    # The webserver's serving task is supervised like every other: its own starter is collected; so is the
    # FRAM manager's chip watch, on every device that declares a chip.
    assert module.webserver is not None and module.fram is not None
    assert module.webserver.get_task_starters() != []
    assert len(module.fram.get_task_starters()) == 1
    # MicroPython bound methods don't expose __self__ (confirmed against the real Unix-port
    # interpreter - that is a CPython-only assumption), but they compare equal when bound to the
    # same (instance, function) pair, so membership via == still proves real ownership.
    for owner in _sensor_reader_owners(module) + [module.fram, module.webserver]:
        for expected in owner.get_task_starters():
            assert expected in starters, f"no task starter bound to {owner!r}"


@_register("collect_timer_starters_includes_every_constructed_module")
def _scenario_collect_timer_starters(device: str) -> None:
    # Every constructed module is checked, not just those currently contributing a timer:
    # neopixel/notification/webserver/fram all return [] today, but this proves _collect_timer_starters()
    # actually calls each of them rather than picking modules by name.
    module = build(device)
    starters = module._collect_timer_starters()
    assert len(starters) > 0
    assert all(callable(s) for s in starters)
    for owner in _sensor_reader_owners(module) + [module.fram, module.webserver]:
        assert owner is not None
        for expected in owner.get_timer_starters():
            assert expected in starters, f"no timer starter bound to {owner!r}"


@_register("neopixel_empty_timer_list_reaches_the_generated_collector")
def _scenario_neopixel_empty_timer_list_reaches_the_collector(device: str) -> None:
    # The driver's kept-empty timer list is a seam (SPECIFICATION.md C.9 shape): the generated
    # collector must call it and take its [] without error, not skip the module by name.
    module = build(device)
    assert _has(module, "neopixel")
    pixel = module.neopixel
    assert pixel.get_timer_starters() == []
    calls: list[int] = []
    real = pixel.get_timer_starters

    def recording() -> "list[Callable[[], None]]":
        calls.append(1)
        result: list[Callable[[], None]] = real()
        return result

    pixel.get_timer_starters = recording  # an instance attribute shadows the method for this call only
    try:
        starters = module._collect_timer_starters()
    finally:
        del pixel.get_timer_starters
    assert calls == [1], f"_collect_timer_starters() called the NeoPixel's get_timer_starters() {len(calls)} times"
    assert all(callable(s) for s in starters)


async def _cancel_reset_task(sysfunct: "Any") -> None:
    sysfunct._reset_task.cancel()
    await asyncio.sleep(0)


def _system_const(name: str) -> int:
    # A const() of asy_system_service.py, read from its source (const() folds the name away on import).
    with open("src/asy_system_service.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(")[1].split(")")[0])
    raise AssertionError(name + " not found in src/asy_system_service.py")


async def _reset_task_done(sysfunct: "Any") -> None:
    # Yields until the reset task a fired reset timer woke has run the reset action.
    for _ in range(50):
        if sysfunct._reset_task is not None and sysfunct._reset_task.done():
            return
        await asyncio.sleep(0)
    raise AssertionError("the reset task never ran")


class _StaggerClock:
    # Stands in for asy_system_service.time: a millisecond clock the scenario advances by each armed
    # stagger wait's own period before firing it, so the real start_timers() runs on exact fake time.
    def __init__(self) -> None:
        self.now = 0

    def ticks_ms(self) -> int:
        return self.now

    def ticks_add(self, ticks: int, delta: int) -> int:
        return ticks + delta

    def ticks_diff(self, new: int, old: int) -> int:
        return new - old


class _AsyncioWaits:
    # Stands in for asy_system_service's asyncio: every other name reaches the real module; the service's
    # own sleeps are recorded in milliseconds and yield once instead of waiting.
    def __init__(self, on_wait: "Callable[[int], None] | None" = None) -> None:
        self.waits_ms: list[int] = []
        self._on_wait = on_wait  # called with the wait count as each wait is recorded, before it yields

    def __getattr__(self, name: str) -> "Any":
        return getattr(asyncio, name)

    async def sleep(self, seconds: float) -> None:
        await self.sleep_ms(round(seconds * 1000))

    async def sleep_ms(self, ms: int) -> None:
        self.waits_ms.append(ms)
        if self._on_wait is not None:
            self._on_wait(len(self.waits_ms))
        await asyncio.sleep(0)


async def _fire_stagger_waits(sysfunct: "Any", task: "asyncio.Task[None]", clock: _StaggerClock) -> "list[int]":
    # Fires each armed stagger one-shot after advancing the fake clock by its period; returns the periods.
    periods: list[int] = []
    for _ in range(100):
        if task.done():
            break
        await asyncio.sleep(0)
        timer = sysfunct._sequencer_timer
        if timer.callback is not None:
            periods.append(timer.period)
            clock.now += timer.period
            machine.Timer.clock_ms = clock.now  # the Timer fake's clock follows: each arm records its time
            timer.trigger()
    assert task.done(), "start_timers() did not finish: a stagger wait was never armed or fired"
    await task
    return periods


def _module_objects(module: "Any") -> "dict[str, Any]":
    # Every module global build_system() constructed that joins the fan-in collectors.
    found = {name: getattr(module, name) for name in dir(module) if not name.startswith("_")}
    return {name: obj for name, obj in found.items() if not isinstance(obj, type) and hasattr(obj, "get_loggers")}


@_register("read_triggers_follow_the_stagger_on_the_real_sequencer")
def _scenario_read_trigger_stagger(device: str) -> None:
    # The real start_timers() over the real _collect_trigger_starters() on a fake clock: trigger k runs at
    # k * slot exactly, bus-sharing readers sit furthest apart, and every pair of reads stays at least
    # _MIN_READ_SEPARATION_MS apart for every combination of whole-second periods up to 3600 s.
    module = build(device)
    sysfunct = module.sysfunct
    triggers = module._collect_trigger_starters()
    readers = [(attachment["driver"] + ("_" + attachment["name_ext"] if attachment["name_ext"] else ""), bus) for bus, attachments in _wiring_plan(device)["buses"].items() for attachment in attachments]
    for var, _bus in readers:
        for starter in getattr(module, var).get_trigger_starters():
            assert starter in triggers, f"{var}'s read trigger is not collected"
    bus_of = [next(bus for var, bus in readers if starter in getattr(module, var).get_trigger_starters()) for starter in triggers]
    clock = _StaggerClock()
    ran_at: list[int] = []

    def recorded(starter: "Callable[[], None]") -> "Callable[[], None]":
        def start() -> None:
            ran_at.append(clock.now)
            starter()

        return start

    async def drive() -> None:
        task = asyncio.create_task(sysfunct.start_timers([recorded(s) for s in triggers], module._collect_timer_starters()))
        await _fire_stagger_waits(sysfunct, task, clock)

    asy_system_service.time = clock  # type: ignore[assignment]
    machine.Timer.clock_ms = 0
    try:
        run(drive())
    finally:
        asy_system_service.time = time
        machine.Timer.clock_ms = 0
    slot = _system_const("_TIMER_BASE_PERIOD") // (len(triggers) + 1)
    assert ran_at == [k * slot for k in range(len(triggers))]
    # The sequencer's own arms, read off the Timer fake's clock: trigger k's one-shot armed when trigger k - 1 ran.
    assert sysfunct._sequencer_timer.arms == [((k - 1) * slot, slot, machine.Timer.ONE_SHOT) for k in range(1, len(triggers))]
    n = len(triggers)
    base = _system_const("_TIMER_BASE_PERIOD")

    def closest_same_bus_pair(buses: "list[str]") -> int:
        # The smallest circular distance, within the one-second plan, between two triggers on one bus.
        gaps = [base]
        for i in range(n):
            for j in range(i + 1, n):
                if buses[i] == buses[j]:
                    d = (j - i) * slot % base
                    gaps.append(min(d, base - d))
        return min(gaps)

    def placements(rest: "list[str]") -> "list[list[str]]":
        # Every distinct order of the bus labels (no starred display: MicroPython lacks it).
        if not rest:
            return [[]]
        found: list[list[str]] = []
        for bus in sorted(set(rest)):
            i = rest.index(bus)
            for tail in placements(rest[:i] + rest[i + 1 :]):
                tail.insert(0, bus)
                found.append(tail)
        return found

    best = max(closest_same_bus_pair(p) for p in placements(list(bus_of)))
    assert closest_same_bus_pair(bus_of) == best, f"bus order {bus_of} does not keep same-bus readers furthest apart"
    for i in range(n):
        for j in range(i + 1, n):
            for gcd in range(1, 3601):
                period = 1000 * gcd
                d = (ran_at[j] - ran_at[i]) % period
                assert min(d, period - d) >= _MIN_READ_SEPARATION_MS, (i, j, gcd)


@_register("the_unfed_boot_stretch_after_the_last_setup_feed_stays_within_two_seconds")
def _scenario_unfed_boot_stretch(device: str) -> None:
    # From the batch's last feed to the supervisor's first: the trigger plan's one-shot waits (under one
    # second) and the task-start spread (N sleeps of 1/N s) are the only waits; any other fails here.
    module = build(device, web_host="127.0.0.1", web_port=0)
    sysfunct = module.sysfunct
    clock = _StaggerClock()
    waits = _AsyncioWaits()
    started: list[Any] = []
    first_feed: list[int] = []

    def tracking(starter: "Callable[[], Any]") -> "Callable[[], Any]":
        def start() -> "Any":
            task = starter()
            started.append(task)
            return task

        return start

    def feed() -> None:
        if not first_feed:
            first_feed.append(len(waits.waits_ms))

    task_starters = module._collect_task_starters()

    async def boot_tail() -> "list[int]":
        timers = asyncio.create_task(sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters()))
        periods = await _fire_stagger_waits(sysfunct, timers, clock)
        await module.ntp.ntp_force_sync()
        sup = asyncio.create_task(sysfunct.start_and_check_tasks([tracking(s) for s in task_starters]))
        for _ in range(5000):
            if first_feed:
                break
            await asyncio.sleep(0)
        sup.cancel()
        for task in started:
            if task is not None:
                task.cancel()
        for _ in range(5):
            await asyncio.sleep(0)
        return periods

    sysfunct.feed_watchdog = feed
    asy_system_service.time = clock  # type: ignore[assignment]
    asy_system_service.asyncio = waits  # type: ignore[assignment]
    try:
        periods = run(boot_tail())
    finally:
        asy_system_service.time = time
        asy_system_service.asyncio = asyncio
        del sysfunct.feed_watchdog
    assert first_feed, "the supervisor never reached its first feed"
    n = len(task_starters)
    assert waits.waits_ms[: first_feed[0]] == [1000 // n] * n  # the task-start spread, no other wait
    assert sum(periods) < 1000  # the read-trigger plan spans less than one second
    assert sum(periods) + sum(waits.waits_ms[: first_feed[0]]) <= 2000


@_register("one_supervisor_pass_over_dead_tasks_persists_at_most_one_entry_per_end")
def _scenario_supervisor_scan_budget(device: str) -> None:
    # Every supervised task already dead at the first pass: the pass persists at most one entry per task
    # end plus the escalation's, counted on the FRAM chip, and makes at most one _TASK_CHECK_TIME sleep.
    module = build(device, web_host="127.0.0.1", web_port=0)
    sysfunct = module.sysfunct
    k = len(module._collect_task_starters())
    chip = module.fram.fram._spidev.spi._spi
    before = chip.write_transactions
    run(sysfunct.pr.err_s("probe: one entry's chip cost", errno=_system_const("_ERR_TASK_RETURNED")))
    entry_cost = chip.write_transactions - before
    assert entry_cost > 0, "SYSTEM's logger is not FRAM-backed"

    async def ends() -> None:
        return

    def dead_starter() -> "asyncio.Task[None]":
        return asyncio.create_task(ends())

    marks: dict[str, int] = {}

    def on_wait(count: int) -> None:
        # The k-th wait is the start loop's last; the next one is the first pass's sleep, its end.
        if count == k:
            marks["start"], marks["entries"], marks["feeds"] = chip.write_transactions, sysfunct.pr._err_count, module.watchdog.feed_count
        elif count == k + 1:
            marks["end"], marks["entries_end"], marks["feeds_end"] = chip.write_transactions, sysfunct.pr._err_count, module.watchdog.feed_count

    waits = _AsyncioWaits(on_wait)

    async def one_pass() -> None:
        sup = asyncio.create_task(sysfunct.start_and_check_tasks([dead_starter] * k))
        for _ in range(5000):
            if sup.done() or "end" in marks:
                break
            await asyncio.sleep(0)
        if not sup.done():
            sup.cancel()
        await asyncio.sleep(0)

    asy_system_service.asyncio = waits  # type: ignore[assignment]
    try:
        run(one_pass())
    finally:
        asy_system_service.asyncio = asyncio
    if sysfunct._reset_task is not None:
        run(_cancel_reset_task(sysfunct))
    entries = marks["entries_end"] - marks["entries"]
    increment, budget = _system_const("_TASK_FAIL_INCREMENT"), _system_const("_TASK_FAIL_MAX")
    escalated = k * increment > budget
    ends_logged = min(k, -(-(budget + 1) // increment))  # the scan stops at the first end past the budget
    assert entries == ends_logged + (1 if escalated else 0), (entries, k)
    assert marks["end"] - marks["start"] <= entries * entry_cost, (marks, entries, entry_cost)
    assert marks["feeds_end"] - marks["feeds"] == 1  # one feed per pass: the pass end's, or the escalation's when starved
    pass_waits = waits.waits_ms[k:]
    if escalated:
        assert sysfunct._reset_timer.callback is not None  # the reboot is armed inside the pass
        assert sysfunct._force_watchdog_starve is True
    assert pass_waits[0] == _system_const("_TASK_CHECK_TIME") * 1000, waits.waits_ms  # the pass ends in one sleep, escalated or not


@_register("every_module_and_logger_reaches_the_fan_in_collectors_exactly_once")
def _scenario_fan_in_inventory(device: str) -> None:
    # Every constructed module's error sources and loggers are collected; every logger reachable one level
    # into a module (its own, its store's, a sub-object's) is collected exactly once; and every collected
    # source answers as an error source: a str name, its own /status entry, a reset.
    module = build(device)
    objects = _module_objects(module)
    sources = module._collect_error_sources()
    setters = module._collect_level_setters()
    names: list[str] = []
    for source in sources:
        assert type(source.name) is str
        assert list(run(source.get_error_counter())) == [source.name]
        assert callable(source.reset_error_counter)
        names.append(source.name)
    assert len(set(names)) == len(names), f"duplicate /status names: {names}"
    reachable: list[Any] = []
    for name, obj in objects.items():
        if obj is not module.webserver:  # its own /status entry is written by the route itself
            for source in obj.get_error_sources():
                assert any(source is s for s in sources), f"{name}'s error source {source.name} is not collected"
        for candidate in [obj] + [getattr(obj, attr, None) for attr in dir(obj) if not attr.startswith("__")]:
            logger = getattr(candidate, "pr", None)
            if isinstance(logger, PrintLogHistory) and not any(logger is r for r in reachable):
                reachable.append(logger)
    for logger in reachable:
        count = sum(1 for setter in setters if setter == logger.set_level)
        assert count == 1, f"{logger.name} reaches the level registry {count} times"


@_register("every_logger_is_set_up_by_the_batch_before_any_task_starts")
def _scenario_loggers_set_up_by_the_batch(device: str) -> None:
    module = build(device)
    for name, obj in _module_objects(module).items():
        for logger in obj.get_loggers():
            assert logger.initialized is True, f"{name}'s logger {logger.name} was not set up by the boot batch"


_GET_ROUTES = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status")


def _float_config_keys(obj: "Any") -> "list[str]":
    if not hasattr(obj, "get_cfg_schema") or not hasattr(obj, "cfgmgr"):
        return []
    return [field[0] for field in obj.get_cfg_schema() if field[1] == "float"]


def _leaves(parsed: "Any") -> "list[Any]":
    if isinstance(parsed, dict):
        return [leaf for v in parsed.values() for leaf in _leaves(v)]
    if isinstance(parsed, list):
        return [leaf for v in parsed for leaf in _leaves(v)]
    return [parsed]


@_register("no_get_route_serialises_a_non_finite_float")
def _scenario_no_non_finite_float_on_the_wire(device: str) -> None:
    # Every measurement field and every float config value set to NaN, +inf and -inf in turn: every GET
    # body stays strict JSON (json.dumps() would write bare nan/inf) and the injected fields read null.
    module = build(device, web_host="127.0.0.1", web_port=0)
    objects = _module_objects(module)
    readers = [obj for obj in objects.values() if hasattr(obj, "_set_meas_data")]
    assert readers
    for value in (float("nan"), float("inf"), float("-inf")):
        injected: list[tuple[Any, str]] = []
        for obj in readers:
            fields = obj._datastruct
            run(obj._set_meas_data(type(fields)(*([value] * len(fields)))))
        for obj in objects.values():
            for key in _float_config_keys(obj):
                obj.cfgmgr._cache[key] = value
                injected.append((obj, key))
        seen: list[Any] = []
        for route in _GET_ROUTES:
            res = _dispatch(module, "GET", route)
            assert res.status_code == 200, (route, res.status_code)
            body = drain_json_response_body(res.body)  # strict RFC 8259: a bare nan or inf fails here
            parsed = json.loads(body)
            if route == "/measurements":
                for obj in readers:
                    if obj.name in parsed:
                        assert _leaves(parsed[obj.name]) == [None] * len(_leaves(parsed[obj.name])), (obj.name, parsed[obj.name])
            elif route == "/sensors":
                seen += [parsed[obj.name][key] for obj, key in injected if key in parsed.get(obj.name, {})]
            elif route != "/status":  # the flat settings routes: one module's keys each
                seen += [parsed[key] for obj, key in injected if obj.name not in module.webserver._sensors and key in parsed]
        assert seen == [None] * len(seen), seen  # every injected config value served reads null
        assert seen or not injected


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
# need wall-clock Timers, or block forever); test_asy_system_service.py covers them directly.
# ---------------------------------------------------------------------------


@_register("main_calls_start_timers_then_force_sync_then_start_and_check_tasks_in_order")
def _scenario_main_call_order(device: str) -> None:
    calls: list[str] = []
    passed: list[tuple[list[Callable[[], None]], list[Callable[[], None]]]] = []
    from asy_ntp_client import NTPClient
    from asy_system_service import SystemService

    real_start_timers = SystemService.start_timers
    real_force_sync = NTPClient.ntp_force_sync
    real_start_and_check = SystemService.start_and_check_tasks

    # self/timers/task_starters keep their names (and stay unused): these are assigned onto the
    # real class attributes below, so mypy checks their parameter NAMES against the real methods'
    # (an underscore prefix is a hard [assignment] error, not covered by the method-assign ignore).
    async def _fake_start_timers(self: "SystemService", triggers: "list[Callable[[], None]]", timers: "list[Callable[[], None]]") -> None:
        calls.append("start_timers")
        passed.append((triggers, timers))

    async def _fake_force_sync(self: "NTPClient") -> None:
        calls.append("force_sync")

    async def _fake_start_and_check(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        calls.append("start_and_check_tasks")
        # Deliberately never loops - the real implementation runs forever; this proves main()
        # reaches this call, not that the supervisor loop itself behaves (test_asy_system_service.py's
        # own job).

    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    NTPClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.start_and_check_tasks = _fake_start_and_check  # type: ignore[method-assign]
    try:
        asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
        module = __import__(f"sensortask_{device}")
        run(module.main(cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        NTPClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.start_and_check_tasks = real_start_and_check  # type: ignore[method-assign]

    assert calls == ["start_timers", "force_sync", "start_and_check_tasks"]
    # the read triggers first, staggered; the unstaggered timer starters second
    assert passed == [(module._collect_trigger_starters(), module._collect_timer_starters())]
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


def _queue_scd30_snapshot(fake_i2c: "Any", interval: int) -> None:
    # The six register replies of one SCD30 config snapshot (word + CRC-8 each), queued for its address
    # only: TempOffset 0, MeasInterval `interval`, AmbPres 0, Altitude 0, ForceCalRef 400, SelfCal 0.
    for value in (0, interval, 0, 0, 400, 0):
        payload = struct.pack(">H", value)
        crc = run(CRC8().add(bytearray(payload)))
        assert crc is not None
        fake_i2c.read_queue_by_address.setdefault(0x61, []).append(payload + bytes([crc[-1]]))


@_register("webserver_sensors_put_round_trips_a_real_scd30_field_through_the_real_driver")
def _scenario_sensors_put_scd30(device: str) -> None:
    # SCD30's chip is its config store: the PUT compares against a chip snapshot, writes the
    # interval command, and the next GET reads the chip again (each snapshot answered by the fake bus).
    module = build(device)
    fake_i2c = module.scd30._scd._i2c_scd30.i2c_device.i2c._i2c
    _queue_scd30_snapshot(fake_i2c, 2)
    res = _dispatch(module, "PUT", "/sensors", {"SCD30": {"MeasInterval": 4}})
    body = json.loads(res.body)
    assert body["result"] == {"SCD30": {"MeasInterval": "Valid"}}
    assert ("writeto", 0x61, bytes([0x46, 0x00, 0x00, 0x04, 0x45]), True) in list(fake_i2c.log)
    _queue_scd30_snapshot(fake_i2c, 4)
    res = _dispatch(module, "GET", "/sensors")
    assert json.loads(status_body(res))["SCD30"]["MeasInterval"] == 4


@_register("webserver_networking_put_ssid_group_reconnects_but_led_group_alone_does_not")
def _scenario_networking_put_ssid_group(device: str) -> None:
    module = build(device)
    assert module.conn is not None
    res = _dispatch(module, "PUT", "/networking", {"LEDWifiOn": False})
    assert json.loads(res.body)["result"] == {"LEDWifiOn": "Valid"}
    assert module.conn._reconn_wifi is False  # LEDWifiOn alone must never reconnect

    res = _dispatch(module, "PUT", "/networking", {"Hostname": "TestHost"})
    assert json.loads(res.body)["result"] == {"Hostname": "Valid"}
    assert module.conn._reconn_wifi is True  # setNetwork's own field group did change


@_register("webserver_networking_put_ntp_fields_forces_a_resync")
def _scenario_networking_put_ntp(device: str) -> None:
    # Same observable-effect precedent as tests/test_setter_microdot_integration.py's own
    # ntp_force_sync() coverage: a failing-sync streak in progress, cleared to 0 by the post_asy_fct.
    module = build(device)
    assert module.ntp is not None
    module.ntp._ntp_retries = 3
    res = _dispatch(module, "PUT", "/networking", {"NTPHost": "time.example.org"})
    assert json.loads(res.body)["result"] == {"NTPHost": "Valid"}
    assert module.ntp._ntp_retries == 0  # post_asy_fct fired


@_register("webserver_networking_put_ntp_fields_clears_synced_until_the_next_sync")
def _scenario_networking_put_ntp_clears_synced(device: str) -> None:
    # (owner, 2026-09-29: "an NTP settings change clears `Synced`, as legacy"): nothing runs on a sync
    # taken under the old settings; the generated post_asy_fct is ntp_force_sync().
    module = build(device)
    assert module.ntp is not None
    run(module.ntp._set_meas_data(NTP(Synced=True, LastSyncAge=0, TS=1767225600)))
    assert json.loads(status_body(_dispatch(module, "GET", "/status")))["networking"]["NTPSynced"] is True
    res = _dispatch(module, "PUT", "/networking", {"NTPHost": "time.example.org"})
    assert json.loads(res.body)["result"] == {"NTPHost": "Valid"}
    assert json.loads(status_body(_dispatch(module, "GET", "/status")))["networking"]["NTPSynced"] is False


@_register("webserver_networking_put_dns_fallback_stores_a_list_and_refuses_a_malformed_one")
def _scenario_networking_put_dns_fallback(device: str) -> None:
    # DNSFallback is its own settings group: empty means none, and a list the resolver could not use is refused.
    module = build(device)
    assert module.ntp is not None
    res = _dispatch(module, "PUT", "/networking", {"DNSFallback": ""})
    assert json.loads(res.body)["result"] == {"DNSFallback": "Valid"}
    assert json.loads(status_body(_dispatch(module, "GET", "/networking")))["DNSFallback"] == ""
    res = _dispatch(module, "PUT", "/networking", {"DNSFallback": "8.8.8.8,"})
    assert json.loads(res.body)["result"] == {"DNSFallback": "Invalid"}
    assert run(module.ntp.cfgmgr.get_dict(["DNSFallback"])) == {"DNSFallback": ""}


async def _start_hotspot_once(conn: "Any") -> None:
    # The mode switch's settle sleeps collapse to a yield; the captive DNS task it starts is cancelled
    # before it runs, so no later scenario meets a port-53 listener.
    asy_wifi_service.asyncio = _AsyncioWaits()  # type: ignore[assignment]
    try:
        await conn._start_hotspot()
    finally:
        asy_wifi_service.asyncio = asyncio
    task = conn._dns_server_task
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@_register("webserver_networking_put_hotspot_pw_configures_the_next_hotspot_and_reads_back_masked")
def _scenario_networking_put_hotspot_pw(device: str) -> None:
    module = build(device)
    conn = module.conn
    assert conn is not None
    res = _dispatch(module, "PUT", "/networking", {"HotspotPW": "newpass123"})
    assert json.loads(res.body)["result"] == {"HotspotPW": "Valid"}
    assert conn._reconn_wifi is True  # the identity group's reconnect
    assert json.loads(status_body(_dispatch(module, "GET", "/networking")))["HotspotPW"] == "********"
    run(_start_hotspot_once(conn))
    assert [c["password"] for c in conn._wlan.config_calls if "password" in c] == ["newpass123"]


@_register("webserver_networking_put_of_the_mask_string_stores_it_as_the_password")
def _scenario_networking_put_mask_string(device: str) -> None:
    # No value is excluded on PUT (owner, 2026-09-29: "I don't want to restrict it in any way"): the mask
    # string is a valid 8-character password, stored verbatim, and GET still answers the mask.
    module = build(device)
    assert module.conn is not None
    for field in ("PW", "HotspotPW"):
        res = _dispatch(module, "PUT", "/networking", {field: "********"})
        assert json.loads(res.body)["result"] == {field: "Valid"}, field
        assert run(module.conn.cfgmgr.get_dict([field])) == {field: "********"}
        assert json.loads(status_body(_dispatch(module, "GET", "/networking")))[field] == "********"


@_register("webserver_system_put_debug_level_propagates_to_every_logger")
def _scenario_system_put_debug_level(device: str) -> None:
    module = build(device)
    assert module.sysfunct is not None and module.conn is not None
    res = _dispatch(module, "PUT", "/system", {"DebugLevel": 1})
    assert json.loads(res.body)["result"]["DebugLevel"] == "Valid"
    assert _system_debug_level(module) == 1
    assert module.conn.pr.level == 1  # pushed via the registry


@_register("webserver_system_put_gmt_dst_offset_applies_without_a_reconnect")
def _scenario_system_put_gmt_offset(device: str) -> None:
    module = build(device)
    assert module.ntp is not None and module.conn is not None
    res = _dispatch(module, "PUT", "/system", {"GMTOffset": 7200})
    assert json.loads(res.body)["result"] == {"GMTOffset": "Valid"}
    assert run(module.ntp.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 7200}
    assert module.conn._reconn_wifi is False  # unrelated to the networking settings groups


@_register("webserver_system_put_reboot_cmd_arms_the_real_reset_timer")
def _scenario_system_put_reboot(device: str) -> None:
    module = build(device)
    assert module.sysfunct is not None
    before = machine.reset_count
    res = _dispatch(module, "PUT", "/system", {"SystemCmd": "reboot"})
    assert json.loads(res.body)["result"]["SystemCmd"] == "Valid"
    assert machine.reset_count == before  # armed, not yet fired
    module.sysfunct._reset_timer.trigger()  # fake Timer - its callback only wakes the reset task
    run(_reset_task_done(module.sysfunct))  # the woken task runs the reset
    assert machine.reset_count == before + 1
    assert machine.reset_cause() == machine.WDT_RESET


@_register("webserver_system_put_reboot_flushes_a_still_pending_config_write_first")
def _scenario_system_put_reboot_flushes_pending_write(device: str) -> None:
    # A commanded reboot must not drop a still-staged write (the generated _flush_pending_configs(),
    # asy_config_manager.py's flush_pending()) - unlike the accepted power-loss residual risk (owner, 2026-09-26; Part F.2),
    # this path can wait the flush out. One PUT with a settings change plus SystemCmd=reboot.
    module = build(device)
    assert module.sysfunct is not None
    res = _dispatch(module, "PUT", "/system", {"DebugLevel": 1, "SystemCmd": "reboot"})
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
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Valid"


@_register("webserver_notification_put_light_cmd_led_accepts_integral_float_rgb_and_int_t_coerced")
def _scenario_notification_light_cmd_led_integral_float(device: str) -> None:
    # asy_config_manager.py's checked_int()/checked_float() policy applied to LightCmdLED too (SPECIFICATION.md
    # Part A.8): an integral float R/G/B coerces to int, a plain int T coerces to float - both
    # directions a real client could plausibly send.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10.0, "G": 20.0, "B": 30.0, "T": 1}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Valid"


@_register("webserver_notification_put_light_cmd_led_rejects_fractional_rgb")
def _scenario_notification_light_cmd_led_rejects_fractional(device: str) -> None:
    # Regression test for the behavior this callback used to have (raw int()/float() truncating
    # casts): a fractional R/G/B is now rejected outright, not silently truncated (12.5 no longer
    # becomes a silent 12).
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10.5, "G": 20, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_non_numeric_field")
def _scenario_notification_light_cmd_led_rejects_non_numeric_field(device: str) -> None:
    # Another behavior change from the old raw int()/float() casts: those would parse a
    # numeric-looking string ("10") via Python's lenient constructors, while the checked_*() validators only
    # coerces between the two numeric types, so this is now rejected too.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": "10", "G": 20, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_non_numeric_t")
def _scenario_notification_light_cmd_led_rejects_non_numeric_t(device: str) -> None:
    # T goes through cm.coerce_numeric(payload["T"], float) - a distinct code path from R/G/B's own
    # int coercion (already tested above for R specifically) - confirms the same non-numeric
    # rejection holds for T's own float-typed branch, not just the int-typed ones.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": "soon"}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_missing_field")
def _scenario_notification_light_cmd_led_rejects_missing_field(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30}})  # T missing
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_out_of_range_rgb")
def _scenario_notification_light_cmd_led_rejects_out_of_range_rgb(device: str) -> None:
    # Regression test for a real legacy-vs-src/ divergence (SPECIFICATION.md Part H.6's
    # dispatch-only field rules): legacy's led_cmd() rejects out-of-range r/g/b (0-255) where the
    # promoted callback used to silently clamp. Rejected exactly like a missing/non-numeric field.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 256, "G": 20, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_negative_rgb")
def _scenario_notification_light_cmd_led_rejects_negative_rgb(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": -1, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_rejects_out_of_range_t")
def _scenario_notification_light_cmd_led_rejects_out_of_range_t(device: str) -> None:
    # Legacy's own t bound is 0.5-60.0 - the promoted src/ callback used to floor a too-small t to
    # 0.1 and never bounded a too-large one at all.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": 0.1}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": 100.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Failed"


@_register("webserver_notification_put_light_cmd_led_accepts_lower_boundary_rgb_and_t")
def _scenario_notification_light_cmd_led_lower_boundary(device: str) -> None:
    # Deliberately one dispatch per test: _dispatch() drives each call through its own fresh
    # asyncio.run(), so NeopixelDriver's consumer task never runs here - a second command would find
    # the first still queued and be refused.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 0, "G": 255, "B": 0, "T": 0.5}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Valid"


@_register("webserver_notification_put_light_cmd_led_accepts_upper_boundary_rgb_and_t")
def _scenario_notification_light_cmd_led_upper_boundary(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 255, "G": 0, "B": 255, "T": 60.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Valid"


@_register("webserver_notification_light_cmd_led_refuses_a_second_flash_at_once")
def _scenario_notification_light_cmd_led_refuses_while_busy(device: str) -> None:
    # Each dispatch is its own asyncio.run(), so the pixel's signal task never runs in between: the
    # first flash stays queued and the second is refused at once, never queued (owner, 2026-09-29).
    module = build(device)
    flash = {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": 1.0}}
    first = _dispatch(module, "PUT", "/notification", flash)
    assert json.loads(first.body)["result"]["LightCmdLED"] == "Valid"
    t0 = time.ticks_ms()
    second = _dispatch(module, "PUT", "/notification", flash, timeout_ms=_LED_REFUSAL_MS)
    elapsed_ms = time.ticks_diff(time.ticks_ms(), t0)
    assert json.loads(second.body)["result"]["LightCmdLED"] == "Failed"
    assert elapsed_ms < _LED_REFUSAL_MS, f"the refusal took {elapsed_ms} ms; a busy LED is refused at once, not waited out"


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
    assert "SysUptime" in body["system"] and "LocalTime" in body["system"] and "UTCTime" in body["system"]
    assert "WifiUptime" in body["networking"] and "NTPSynced" in body["networking"]
    assert "Triggered" in body["notification"] and "PauseTime" in body["notification"]
    # One entry per real module + per real ConfigManager + this service's own "WEBSERVER" entry,
    # from _all_loggers()'s reflected shape. By NAME, not count: the website's errcount rows are
    # keyed by name (Part H.6), so a published key nothing matches renders nothing at all.
    assert {logger.name for logger in _all_loggers(module)} == set(body["errcount"].keys())
    assert len(body["errcount"]) == len(_all_loggers(module)), "two loggers sharing a name would collapse into one row"


@_register("webserver_status_answers_the_networking_snapshot_while_wifi_mode_lock_is_held")
def _scenario_status_snapshot_under_the_held_lock(device: str) -> None:
    # One snapshot per response, read without the radio: a held wifi_mode_lock never blanks or delays
    # it, and the address is published once, as IPv4.
    module = build(device)
    conn = module.conn
    assert conn is not None
    conn._wlan._ifconfig = ("192.168.1.42", "255.255.255.0", "192.168.1.1", "192.168.1.53")
    conn._wlan._rssi = -61
    run(conn._update_wifi_snapshot(connected=True))
    run(conn.wifi_mode_lock.acquire())
    try:
        res = _dispatch(module, "GET", "/status", timeout_ms=_LOCKED_STATUS_MS)
    finally:
        conn.wifi_mode_lock.release()
    networking = json.loads(status_body(res))["networking"]
    assert "IP" not in networking
    got = {key: networking[key] for key in ("Mode", "Connected", "IPv4", "Subnet", "Gateway", "DNS", "RSSI")}
    assert got == {"Mode": "STA", "Connected": True, "IPv4": "192.168.1.42", "Subnet": "255.255.255.0", "Gateway": "192.168.1.1", "DNS": "192.168.1.53", "RSSI": -61}


@_register("webserver_status_in_ap_mode_reports_no_rssi_and_never_queries_it")
def _scenario_status_ap_mode_rssi(device: str) -> None:
    # An AP interface has no RSSI (cyw43 raises outside STA): the snapshot leaves it null and never asks.
    module = build(device)
    conn = module.conn
    assert conn is not None
    conn._conn_phase = _PHASE_HOTSPOT
    conn._ap_selected = True
    conn._wlan = network.WLAN(network.AP_IF)
    conn._wlan._ifconfig = ("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1")
    queries: list[object] = []
    real_status = conn._wlan.status

    def status(param: "str | None" = None) -> "Any":
        queries.append(param)
        return real_status(param)

    conn._wlan.status = status
    run(conn._update_wifi_snapshot(connected=True))
    networking = json.loads(status_body(_dispatch(module, "GET", "/status")))["networking"]
    assert (networking["Mode"], networking["Connected"], networking["IPv4"], networking["RSSI"]) == ("AP", True, "192.168.4.1", None)
    assert "rssi" not in queries, queries


@_register("webserver_status_publishes_utc_time_only_after_the_first_ntp_sync")
def _scenario_status_utc_time_waits_for_ntp_sync(device: str) -> None:
    # rp2's RTC starts at its reset epoch (ports/rp2/main.c), a plausible-looking wrong date, so
    # UTCTime is gated on ntp_issynced() exactly as LocalTime is.
    module = build(device)
    system = json.loads(status_body(_dispatch(module, "GET", "/status")))["system"]
    assert system["UTCTime"] is None and system["LocalTime"] is None

    async def synced() -> bool:
        return True

    module.ntp.ntp_issynced = synced
    utc = json.loads(status_body(_dispatch(module, "GET", "/status")))["system"]["UTCTime"]
    assert isinstance(utc, dict), utc
    assert set(utc.keys()) == {"Year", "Month", "MDay", "Hour", "Minute", "Second", "Weekday", "Yearday"}


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
    assert isinstance(build_info["FirmwareVersion"], str) and build_info["FirmwareVersion"]
    assert isinstance(build_info["WebsiteVersion"], str) and build_info["WebsiteVersion"]
    assert isinstance(build_info["BuildDate"], str) and build_info["BuildDate"]


@_register("webserver_status_put_reset_errors_clears_a_real_modules_history")
def _scenario_status_put_reset_errors(device: str) -> None:
    module = build(device)
    assert module.conn is not None
    run(module.conn.pr.err_s("simulated", errno=99))
    assert (run(module.conn.get_error_counter()))["WIFI"]["ErrCount"] == 1
    res = _dispatch(module, "PUT", "/status", {"ResetErrors": True})
    assert json.loads(res.body)["res"] == "OK"
    assert json.loads(res.body)["result"]["ResetErrors"] == "Valid"
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
    assert json.loads(res.body)["result"]["ResetErrors"] == "Valid"
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
    # Error-path/good-outcome baseline: WifiService.__init__ starts in _PHASE_STA_SEEKING - the real
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
