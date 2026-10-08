"""Shared scenario library: build_system() construction/wiring for every real device, plus real
webserver wiring (deep per-route behavior stays tests/test_asy_webserver_service.py's job).
Not a test file - register_for_device() is the export; SPECIFICATION.md Part E.2.1 has the split."""

import asyncio
import json
import os
import sys
import time

# Same convention as tests/test_asy_webserver_service.py: scripts/test.sh's MICROPYPATH excludes
# ext/, and every generated sensortask_<device> transitively imports microdot - extending sys.path
# reaches the real vendored ext/microdot.py without a build-environment scope change.
sys.path.insert(0, "ext")

import machine
import network
import rp2
from _boot_recorder import BootRecorder
from _bus_hazard_catalog import scd_data_frame, scd_register_frame
from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _generated_module import boot_entry_watchdog, boot_generated, write_offline_ntp_config
from _shared_rest_roundtrip import (
    assert_named_modules_constructed,
    assert_sensor_payload_not_self_wrapped,
    drain_json_response_body,
)
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen, scd30_nvm_writes
from microdot import Request, Response

import asy_config_manager
import asy_scd30_driver
import asy_spi_driver
import asy_system_service
import asy_webserver_service
import asy_wifi_service
from asy_base_classes import SensorReader
from asy_fram_manager import _owner_seed
from asy_ntp_client import NTP
from asy_print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_system_service import SystemService

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
    from collections.abc import Callable, Coroutine, Iterable
    from typing import Any, TypeVar

    from asy_base_classes import SetupFct

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


_BLANK = bytes(4096)


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # dev's real FRAM: a 256KB MB85RS2MTA with its own RDID (DS501-00032 p.10), not the base fake's 8KB
    # MB85RS64V. A subclass, since build_system() offers no post-construction hook.
    SIZE = 0x40000
    RDID = bytes([0x04, 0x7F, 0x48, 0x03])
    # One array for every build of the process, blank at each construction: a fresh 256 KB array needs one free
    # run that long, which a long scenario's survivors left nowhere on the settrace binary (12 MemoryErrors).
    _array: "bytearray | None" = None
    _holder: "_FakeMB85RS2MTA | None" = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.SIZE = 0  # shadows the class value while the base constructor runs, so it allocates no array
        super().__init__(*args, **kwargs)
        del self.SIZE
        cls = _FakeMB85RS2MTA
        if cls._array is None:
            cls._array = bytearray(self.SIZE)
        for start in range(0, self.SIZE, len(_BLANK)):
            cls._array[start : start + len(_BLANK)] = _BLANK
        if cls._holder is not None:
            cls._holder.memory = None  # type: ignore[assignment]  # an earlier build's chip fails loudly, never writes this one
        cls._holder = self
        self.size = self.SIZE
        self.memory = cls._array
        self._addr_width = 3  # the 3-byte address of a part above 64 KB (DS501-00032 p.9)


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


def _expected_facts(device: str) -> "dict[str, Any]":
    # What buildgen alone derives for the device (its boot sequence, its FRAM-wired modules), written beside the module.
    with open(f"build/generated_src/sensortask_{device}_expected.json") as f:
        facts: dict[str, Any] = json.load(f)
    return facts


def fram_fake_class(device: str) -> "type[FakeMB85RS64V]":
    # Public because tests/_boot_contiguity_probe.py boots the same devices from its own script
    # entry point: shared rather than copied, so the RDID table above stays the one place the
    # tests tier maps a device to its real chip.
    plan = _wiring_plan(device)
    (spi_attachment,) = plan["spi"].values()  # every real device has exactly one FRAM/SPI instance
    return _FRAM_FAKE_BY_MAX_SIZE[spi_attachment["max_size"]]


def _src_const(path: str, name: str) -> str:
    # A shipped const()'s literal, read from its source: a const() is not a module attribute on MicroPython.
    with open(path) as f:
        for line in f:
            if line.startswith(name + " = const("):
                literal: str = line.split("const(", 1)[1].split(")", 1)[0]
                return literal
    raise AssertionError(name + " not found in " + path)


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


def _reset_peripherals() -> None:
    # Each build is a boot: rp2's soft reset frees every DMA channel and stops every timer (ports/rp2/main.c
    # v1.29.0, rp2_dma_deinit(), soft_timer_deinit()). A timer left armed kept its run's whole graph alive.
    rp2.DMA.reset_registry()
    for timer in machine.Timer.all_timers:
        timer.deinit()
    machine.Timer.all_timers.clear()


async def _boot(device: str, cfg_path: "str | None" = None, chip: "type[FakeMB85RS64V] | None" = None, **kwargs: "Any") -> "tuple[Any, Any]":
    # Per-call, not module-level: different devices need different FRAM fakes (max_size/RDID), and
    # several devices' own modules get booted in this one process across this file's full run.
    asy_spi_driver._SPI = fram_fake_class(device) if chip is None else chip  # type: ignore[misc]
    _reset_peripherals()
    module = __import__(f"sensortask_{device}")
    return await boot_generated(module, device, cfg_path=cfg_path if cfg_path is not None else _tmp_cfg_dir(), **kwargs)


def build(device: str, cfg_path: "str | None" = None, chip: "type[FakeMB85RS64V] | None" = None, **kwargs: "Any") -> "Any":
    # The module, constructed and set up; called only at synchronous scenario scope. The WDT its boot armed
    # comes with run(_boot(...)), for the scenarios that read it.
    module, _watchdog = run(_boot(device, cfg_path, chip, **kwargs))
    return module


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


class _NoopHolder:  # Request.sock's stand-in: a static route hands its opened file to the writer's hold()
    def hold(self, closable: object) -> None:
        pass


async def _dispatch_async(module: "Any", method: str, path: str, json_body: "dict[str, Any] | None" = None) -> "Response":
    # The request a real client's would be, dispatched in-process: for a scenario already inside its one coroutine.
    app = module.webserver._app
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    sock = (_NoopHolder(), _NoopHolder())
    req = Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=body, sock=sock)  # type: ignore[arg-type]  # the stub types sock as asyncio's stream pair; the product reads only _Holder.hold() off it
    return await app.dispatch_request(req)  # type: ignore[no-any-return]  # the upstream stub leaves dispatch_request() unannotated - removal trigger: SPECIFICATION.md B.15


def _dispatch(module: "Any", method: str, path: str, json_body: "dict[str, Any] | None" = None, timeout_ms: "int | None" = None) -> "Response":
    coro = _dispatch_async(module, method, path, json_body)
    if timeout_ms is not None:  # a request that must answer at once fails with TimeoutError, never hangs
        return run(asyncio.wait_for_ms(coro, timeout_ms))
    return run(coro)


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
    mandatory = ("conn", "ntp", "i2c0", "i2c1", "spi0", "fram", "sysfunct", "neopixel", "notification")
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
    # point calls <module>.main(). Fakes every step after the setup list, as the main-call-order
    # scenario below does: the real ones start every task and then supervise them for good.
    from asy_ntp_client import NTPClient
    from asy_system_service import SystemService

    real_start_tasks = SystemService.start_tasks
    real_start_timers = SystemService.start_timers
    real_force_sync = NTPClient.ntp_force_sync
    real_supervise = SystemService.supervise_tasks

    async def _fake_start_tasks(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        pass

    async def _fake_start_timers(self: "SystemService", triggers: "list[Callable[[], None]]", timers: "list[Callable[[], None]]") -> None:
        pass

    async def _fake_force_sync(self: "NTPClient") -> None:
        pass

    async def _fake_supervise(self: "SystemService") -> None:
        pass  # returns at once: this test only checks that build_system() received the override

    SystemService.start_tasks = _fake_start_tasks  # type: ignore[method-assign]
    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    NTPClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.supervise_tasks = _fake_supervise  # type: ignore[method-assign]
    try:
        asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
        module = __import__(f"sensortask_{device}")
        run(module.main(watchdog=boot_entry_watchdog(module, device), cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=8080))
    finally:
        SystemService.start_tasks = real_start_tasks  # type: ignore[method-assign]
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        NTPClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.supervise_tasks = real_supervise  # type: ignore[method-assign]
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
    # re-initialised chunk, and a reboot on the same filesystem then restores what that boot wrote. No task
    # starts, so neither boot needs the offline NTP file, whose repair would log in CFGMGR_NTP.
    base = fram_fake_class(device)
    cfg_path = _tmp_cfg_dir()
    module = build(device, cfg_path, chip=_chip_holding(base, image), offline_ntp=False)
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
    module = build(device, cfg_path, chip=_chip_holding(base, rewritten), offline_ntp=False)
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
    # The per-device "does everything fit" check: get_chunk() answers None when a chunk does not fit, so a None
    # chunk is the failure - `_allocated_size <= size` holds by construction. The FRAM-wired modules are the
    # build's own list; the negative case is test_asy_base_classes.py's FRAM allocation-failure test.
    module = build(device)
    wired = _expected_facts(device)["fram_wired"]
    objects = _module_objects(module)
    assert sorted(name for name in wired if name in objects) == sorted(wired), (wired, sorted(objects))
    for name, obj in objects.items():
        # A config log its class keeps off FRAM stays RAM-only on a FRAM-wired module (read from the class).
        ram_config = getattr(obj, "cfgmgr", None) if not getattr(type(obj), "_CFG_LOG_FRAM", True) else None
        for logger in obj.get_loggers():
            chunk = getattr(logger, "fram", None)
            if name in wired and (ram_config is None or logger is not ram_config.pr):
                assert chunk is not None, f"{name}'s logger {logger.name} holds no FRAM chunk"
            else:
                assert chunk is None, f"{name}'s logger {logger.name} holds a FRAM chunk the build does not wire"
    for obj in objects.values():
        if isinstance(obj, SGP40_Reader):  # the one data-chunk owner: its VOC backup
            assert obj._ts_storage is not None, f"{obj.name}'s VOC backup holds no FRAM chunk"


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


async def _stop_supervising(sysfunct: "Any", sup: "asyncio.Task[None]") -> None:
    # supervise_tasks() runs the loop as its own task: both are cancelled, so no pass outlives the scenario.
    sup.cancel()
    if sysfunct._supervisor_task is not None:
        sysfunct._supervisor_task.cancel()
    await asyncio.sleep(0)


async def _supervise_until_the_reboot_is_armed(sysfunct: "Any", starters: "list[Any]") -> None:
    await sysfunct.start_tasks(starters)
    sup = asyncio.create_task(sysfunct.supervise_tasks())
    for _ in range(5000):
        if sysfunct._reset_armed or sup.done():
            break
        await asyncio.sleep(0)
    await _stop_supervising(sysfunct, sup)


@_register("a_declared_dead_fram_chip_escalates_to_a_reboot")
def _scenario_dead_fram_chip_escalates(device: str) -> None:
    # A declared chip that never comes up escalates like every other declared chip (owner, 2026-09-29: 'the
    # same as all other chips'); until the reboot every module keeps logging in RAM (owner, 2026-08-11). No NTP
    # task starts here, so the boot keeps a fresh config dir: the offline file's repair would log in CFGMGR_NTP.
    module = build(device, chip=_DeadFramChip, offline_ntp=False)
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
# setup() batch: the generated _collect_setups() list, run by SystemService.run_setups() in its fixed order.
# ---------------------------------------------------------------------------


def _setup_owner_names(module: "Any") -> "list[str]":
    # The module global owning each entry of _collect_setups(), in list order: a bound method equals its
    # own object's (MicroPython exposes no __self__).
    names = [name for name in dir(module) if not name.startswith("_") and hasattr(getattr(module, name), "setup")]
    return [next((name for name in names if getattr(module, name).setup == setup), repr(setup)) for setup in module._collect_setups()]


@_register("setup_batch_runs_every_unit_in_the_collected_order")
def _scenario_setup_batch_order(device: str) -> None:
    # The boot's setup units, recorded from outside as run_setups() runs them and named by their module globals:
    # exactly the generated _collect_setups() list, in its order, each unit once.
    recorder = BootRecorder(build(device))  # the recorder names its classes from a built module
    try:
        module = build(device)
    finally:
        recorder.restore()
    expected = _setup_owner_names(module)
    assert [name for kind, name in recorder.entries() if kind == "setup"] == expected, recorder.entries()
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
    # SPECIFICATION.md Part D.9/G.2: the boot must actually feed the WDT it was handed after every setup()
    # it runs. The expected count is the generated setup list's own length, not a number by hand.
    module, wdt = run(_boot(device))
    expected_feeds = len(module._collect_setups())
    assert expected_feeds > 0
    assert module.sysfunct is not None
    assert module.sysfunct._watchdog is wdt
    assert wdt.feed_count == expected_feeds


def _expected_boot_entries(sequence: "dict[str, list[str]]") -> "list[tuple[str, str]]":
    # The recorder's view of the build's boot sequence: a step's inner entries between its call and its return,
    # the webserver built last after the model's own nodes; the last step, the supervisor, never returns.
    entries: list[tuple[str, str]] = []
    for step in sequence["phases"]:
        if step.startswith("BOOT_"):
            entries.append(("phase", step))
            continue
        entries.append(("call", step))
        if step == "build_system":
            entries += [("construct", name) for name in sequence["construction"] + ["webserver"]]
        elif step == "run_setups":
            for name in sequence["setups"]:
                entries += [("setup", name), ("feed", "")]
        if step != sequence["phases"][-1]:
            entries.append(("return", step))
    return entries


async def _main_until_supervised(module: "Any", device: str, recorder: "BootRecorder") -> None:
    # The real main(), as the boot entry runs it, until the recorder stops it entering supervise_tasks(); each
    # stagger wait is fired, the Timer fake never firing one itself. The tasks main() started are stopped after.
    asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
    _reset_peripherals()
    cfg_path = _tmp_cfg_dir()
    write_offline_ntp_config(cfg_path)
    main = asyncio.create_task(module.main(watchdog=boot_entry_watchdog(module, device), cfg_path=cfg_path, web_host="127.0.0.1", web_port=0))
    try:
        for _ in range(100000):
            if main.done():
                break
            await asyncio.sleep(0)
            timer = module.sysfunct._sequencer_timer
            if timer.callback is not None:
                timer.trigger()
        assert main.done(), "main() never reached supervise_tasks()"
        await main
    except Exception as e:
        if not recorder.stopped_by(e):
            raise
    else:
        raise AssertionError("main() returned")
    finally:
        main.cancel()
        for task in module.sysfunct._tasks:
            if task is not None:
                task.cancel()
        await asyncio.sleep(0)


@_register("boot_sequence_matches_the_generated_expectation")
def _scenario_boot_sequence(device: str) -> None:
    # main() up to the supervisor: every construction, each setup unit once with one feed after it, then each step
    # main() awaits, each returned before the next began - exactly the boot sequence the build derived for the device.
    module = build(device)  # the recorder names its classes from a built module
    recorder = BootRecorder(module)
    asy_system_service.asyncio = _AsyncioWaits()  # type: ignore[assignment]
    try:
        run(_main_until_supervised(module, device, recorder))
    finally:
        asy_system_service.asyncio = asyncio
        recorder.restore()
    assert recorder.entries() == _expected_boot_entries(_expected_facts(device)["boot_sequence"]), recorder.entries()


@_register("every_logger_the_boot_constructs_reaches_status_errcount_exactly_once")
def _scenario_no_dropped_logger(device: str) -> None:
    # Every logger the boot constructs, recorded from PrintLog's own constructor (each logger class derives from it,
    # and the FRAM manager builds its own directly), is one GET /status errcount entry by name: none dropped, none shadowed.
    made: list[Any] = []
    real_init = PrintLog.__init__

    def recording(self: "PrintLog", level: "int | None" = None, name: str = "") -> None:
        real_init(self, level, name)
        made.append(self)

    PrintLog.__init__ = recording  # type: ignore[method-assign]
    try:
        module = build(device)
    finally:
        PrintLog.__init__ = real_init  # type: ignore[method-assign]
    names = [logger.name for logger in made]
    assert len(set(names)) == len(names), f"two loggers share a name, so one of them has no errcount entry: {sorted(names)}"
    errcount = json.loads(status_body(_dispatch(module, "GET", "/status")))["errcount"]
    assert sorted(errcount) == sorted(names), (sorted(errcount), sorted(names))


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
# loop (supervise_tasks()) or a starter's own coroutine body. That boundary stays out of this
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
    # From the batch's last feed to the supervisor's first, in main()'s order: the task-start spread (N sleeps
    # of 1/N s) and the trigger plan's one-shot waits (under one second) are the only waits; any other fails here.
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
        await sysfunct.start_tasks([tracking(s) for s in task_starters])
        timers = asyncio.create_task(sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters()))
        periods = await _fire_stagger_waits(sysfunct, timers, clock)
        await module.ntp.ntp_force_sync()
        sup = asyncio.create_task(sysfunct.supervise_tasks())
        for _ in range(5000):
            if first_feed:
                break
            await asyncio.sleep(0)
        await _stop_supervising(sysfunct, sup)
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
    module, wdt = run(_boot(device, web_host="127.0.0.1", web_port=0))
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
            marks["start"], marks["entries"], marks["feeds"] = chip.write_transactions, sysfunct.pr._err_count, wdt.feed_count
        elif count == k + 1:
            marks["end"], marks["entries_end"], marks["feeds_end"] = chip.write_transactions, sysfunct.pr._err_count, wdt.feed_count

    waits = _AsyncioWaits(on_wait)

    async def boot_lists() -> None:
        await sysfunct.start_tasks([dead_starter] * k)
        await sysfunct.supervise_tasks()

    async def one_pass() -> None:
        sup = asyncio.create_task(boot_lists())
        for _ in range(5000):
            if sup.done() or "end" in marks:
                break
            await asyncio.sleep(0)
        await _stop_supervising(sysfunct, sup)

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
    # The float fields the module's own store holds: a chip-stored one (SCD30's TempOffset) is read from the chip.
    if not hasattr(obj, "get_cfg_schema") or not hasattr(obj, "cfgmgr"):
        return []
    return [field[0] for field in obj.get_cfg_schema() if field[1] == "float" and field[0] in obj.cfgmgr._cache]


def _leaves(parsed: "Any") -> "list[Any]":
    if isinstance(parsed, dict):
        return [leaf for v in parsed.values() for leaf in _leaves(v)]
    if isinstance(parsed, list):
        return [leaf for v in parsed for leaf in _leaves(v)]
    return [parsed]


@_register("no_get_route_serialises_a_non_finite_float")
def _scenario_no_non_finite_float_on_the_wire(device: str) -> None:
    # Every measurement field and every float config value a store holds set to NaN, +inf and -inf in turn: every GET
    # body stays strict JSON (json.dumps() would write bare nan/inf), and every injected field is served and reads null.
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
        seen: dict[tuple[str, str], Any] = {}
        for route in _GET_ROUTES:
            if route == "/sensors" and _has(module, "scd30"):  # its snapshot answered, so SCD30's map is served, not the marker
                _queue_scd30_snapshot(module.scd30._scd._i2c_scd30.i2c_device.i2c._i2c, 2)
            res = _dispatch(module, "GET", route)
            assert res.status_code == 200, (route, res.status_code)
            body = drain_json_response_body(res.body)  # strict RFC 8259: a bare nan or inf fails here
            parsed = json.loads(body)
            if route == "/measurements":
                for obj in readers:
                    if obj.name in module.webserver._sensors:  # every sensor answers here; the other readers feed /status
                        assert _leaves(parsed[obj.name]) == [None] * len(_leaves(parsed[obj.name])), (obj.name, parsed[obj.name])
            elif route == "/sensors":
                seen.update({(obj.name, key): parsed[obj.name][key] for obj, key in injected if key in parsed.get(obj.name, {})})
            elif route != "/status":  # the flat settings routes: one module's keys each
                seen.update({(obj.name, key): parsed[key] for obj, key in injected if obj.name not in module.webserver._sensors and key in parsed})
        assert sorted(seen) == sorted((obj.name, key) for obj, key in injected), (sorted(seen), injected)  # every injected value served
        assert list(seen.values()) == [None] * len(seen), seen  # and read null


# A device's whole serving demand stays within the heap free after boot (SPECIFICATION.md I.6: about 105,000 B) less
# the 32,768 B contiguity reserve; estimated (agent, 2026-10-08) - measurement owed: post-boot free heap on dev, phase C.
# @tunable web.serving_demand_budget_b = 72232
_SERVING_DEMAND_BUDGET_B = 72232
_POINTER_BYTES = 4  # one piece-list slot on the RP2040


@_register("webserver_every_get_route_fits_the_serving_demand_budget_and_sends_its_pieces_uncopied")
def _scenario_serving_demand(device: str) -> None:
    # Per admitted connection: the head and body caps, the largest GET body held once as its encoded pieces, the piece
    # list and one in-flight chunk; the body is the writer's own pieces (identity), so an encode-copy fails here.
    module = build(device)
    webserver = module.webserver
    ssid = "K\u00fcche-W\u00e4sche"  # non-ASCII: a body's byte count differs from its character count
    assert json.loads(_dispatch(module, "PUT", "/networking", {"SSID": ssid}).body)["result"] == {"SSID": "Valid"}
    if _has(module, "scd30"):  # its config snapshot answered, so /sensors carries SCD30's whole map
        _queue_scd30_snapshot(module.scd30._scd._i2c_scd30.i2c_device.i2c._i2c, 2)
    filled: list[list[bytes]] = []
    real_writer = asy_webserver_service._PieceWriter

    class _RecordingPieceWriter(asy_webserver_service._PieceWriter):
        def __init__(self, pieces: "list[bytes]", max_bytes: int) -> None:
            filled.append(pieces)
            super().__init__(pieces, max_bytes)

    sizes: dict[str, tuple[int, int]] = {}
    asy_webserver_service._PieceWriter = _RecordingPieceWriter  # type: ignore[misc]
    try:
        for route in _GET_ROUTES:
            filled.clear()
            res = _dispatch(module, "GET", route)
            assert res.status_code == 200 and len(filled) == 1, (route, res.status_code, len(filled))
            pieces = filled[0]
            body: Iterable[bytes] = res.body  # type: ignore[assignment]  # the stub types Response.body as bytes (microdot.pyi:162), yet a streamed route's is an iterator over its pieces - removal trigger: SPECIFICATION.md B.15
            sent = list(body)
            assert len(sent) == len(pieces) and all(sent[i] is pieces[i] for i in range(len(pieces))), route
            sizes[route] = (sum(len(piece) for piece in pieces), len(pieces))
            assert int(res.headers["Content-Length"]) == sizes[route][0], route
            if route == "/networking":
                assert json.loads(drain_json_response_body(iter(sent)))["SSID"] == ssid
    finally:
        asy_webserver_service._PieceWriter = real_writer  # type: ignore[misc]
    head = int(_src_const("src/asy_webserver_service.py", "_MAX_HEAD_BYTES"))
    body_cap = Request.max_content_length  # this device's ServingLimits, set by the build above
    largest_body = max(size for size, _ in sizes.values())
    most_pieces = max(count for _, count in sizes.values())
    demand = webserver._max_connections * (head + body_cap + largest_body + _POINTER_BYTES * most_pieces + webserver._chunk_bytes)
    print(f"SERVING_DEMAND {device} connections={webserver._max_connections} head={head} body_cap={body_cap} largest_body={largest_body} most_pieces={most_pieces} chunk={webserver._chunk_bytes} demand={demand} budget={_SERVING_DEMAND_BUDGET_B} routes={sizes}")
    assert demand <= _SERVING_DEMAND_BUDGET_B, (demand, sizes)


@_register("collect_task_starters_never_touches_start_tasks")
def _scenario_collect_starters_never_blocks(device: str) -> None:
    # Collection is pure list-building from already-constructed objects - calling it must not
    # start, await, or block on anything. If it did, this test itself would hang.
    module = build(device)
    module._collect_task_starters()
    module._collect_timer_starters()


# ---------------------------------------------------------------------------
# main()'s own composition - build_system() -> run_setups() -> start_tasks() -> start_timers() ->
# ntp_force_sync() -> supervise_tasks(), in that order. Every step after construction is faked (the
# real ones start tasks, wait on Timers or supervise for good); test_asy_system_service.py covers them.
# ---------------------------------------------------------------------------


@_register("main_runs_setups_then_tasks_then_timers_then_force_sync_then_supervises_in_order")
def _scenario_main_call_order(device: str) -> None:
    calls: list[str] = []
    passed: list[object] = []
    from asy_ntp_client import NTPClient
    from asy_system_service import SystemService

    real_run_setups = SystemService.run_setups
    real_start_tasks = SystemService.start_tasks
    real_start_timers = SystemService.start_timers
    real_force_sync = NTPClient.ntp_force_sync
    real_supervise = SystemService.supervise_tasks

    # self/setups/task_starters/triggers/timers keep their names (and self stays unused): these are assigned onto
    # the real class attributes below, so mypy checks their parameter NAMES against the real methods'
    # (an underscore prefix is a hard [assignment] error, not covered by the method-assign ignore).
    async def _fake_run_setups(self: "SystemService", setups: "list[SetupFct]") -> None:
        calls.append("run_setups")
        passed.append(setups)

    async def _fake_start_tasks(self: "SystemService", task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        calls.append("start_tasks")
        passed.append(task_starters)

    async def _fake_start_timers(self: "SystemService", triggers: "list[Callable[[], None]]", timers: "list[Callable[[], None]]") -> None:
        calls.append("start_timers")
        passed.append((triggers, timers))

    async def _fake_force_sync(self: "NTPClient") -> None:
        calls.append("force_sync")

    async def _fake_supervise(self: "SystemService") -> None:
        calls.append("supervise_tasks")
        # Returns at once where the real one supervises for good: this proves main() reaches it, not
        # that the supervisor loop itself behaves (test_asy_system_service.py's own job).

    SystemService.run_setups = _fake_run_setups  # type: ignore[method-assign]
    SystemService.start_tasks = _fake_start_tasks  # type: ignore[method-assign]
    SystemService.start_timers = _fake_start_timers  # type: ignore[method-assign]
    NTPClient.ntp_force_sync = _fake_force_sync  # type: ignore[method-assign]
    SystemService.supervise_tasks = _fake_supervise  # type: ignore[method-assign]
    try:
        asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
        module = __import__(f"sensortask_{device}")
        run(module.main(watchdog=boot_entry_watchdog(module, device), cfg_path=_tmp_cfg_dir()))
    finally:
        SystemService.run_setups = real_run_setups  # type: ignore[method-assign]
        SystemService.start_tasks = real_start_tasks  # type: ignore[method-assign]
        SystemService.start_timers = real_start_timers  # type: ignore[method-assign]
        NTPClient.ntp_force_sync = real_force_sync  # type: ignore[method-assign]
        SystemService.supervise_tasks = real_supervise  # type: ignore[method-assign]

    assert calls == ["run_setups", "start_tasks", "start_timers", "force_sync", "supervise_tasks"], calls
    # The collected lists, each handed over whole: the setups in their fixed order, then the task starters, then the
    # read triggers (staggered) beside the unstaggered timer starters.
    expected = [module._collect_setups(), module._collect_task_starters(), (module._collect_trigger_starters(), module._collect_timer_starters())]
    assert passed == expected, passed
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

    if _has(module, "scd30"):  # its config snapshot answered, so SCD30's map is read rather than marked unavailable
        _queue_scd30_snapshot(module.scd30._scd._i2c_scd30.i2c_device.i2c._i2c, 2)
    res = _dispatch(module, "GET", "/sensors")
    sensors = json.loads(status_body(res))
    assert_sensor_payload_not_self_wrapped(sensors, expected)
    assert all("error" not in fields for fields in sensors.values()), sensors  # the marker is no sensor's config


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
    fake_i2c.read_queue_by_address.setdefault(0x61, []).extend(scd_register_frame(value) for value in (0, interval, 0, 0, 400, 0))


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


def _config_snapshot_chips(module: "Any") -> "list[tuple[Any, Any]]":
    # (reader, I2CDevice) for every sensor whose config GET reads a chip snapshot, found by shape, never by name.
    chips = []
    for reader in module.webserver._sensors.values():
        for protocol in reader.__dict__.values():
            if hasattr(protocol, "get_config_snapshot"):
                chips += [(reader, session.i2c_device) for session in protocol.__dict__.values() if hasattr(session, "i2c_device")]
    return chips


@_register("webserver_sensors_get_sends_the_unavailable_marker_for_a_failed_chip_config_read")
def _scenario_sensors_get_marks_a_failed_chip_read(device: str) -> None:
    # A chip that stops acknowledging under its config snapshot: GET /sensors sends exactly the marker for that module,
    # never nulls a reader would take for unset values, keeps its one persisted entry, and leaves every other map as it was.
    module = build(device)
    chips = _config_snapshot_chips(module)
    expected = [name for attr, name in _READER_OWNERS if attr != "sgp40" and _has(module, attr)]  # SGP40's config is its file alone
    assert sorted(reader.name for reader, _ in chips) == sorted(expected)

    def get_sensors(faulted: "Any") -> "dict[str, Any]":
        if _has(module, "scd30") and faulted is not module.scd30:  # its six replies, as the PUT scenario above queues them
            _queue_scd30_snapshot(module.scd30._scd._i2c_scd30.i2c_device.i2c._i2c, 2)
        sensors: dict[str, Any] = json.loads(status_body(_dispatch(module, "GET", "/sensors")))
        return sensors

    before = get_sensors(None)
    assert all("error" not in fields for fields in before.values()), before
    for reader, i2c_device in chips:
        count = run(reader.get_error_counter())[reader.name]["ErrCount"]
        bus = i2c_device.i2c._i2c
        bus.nak_addresses.add(i2c_device.device_address)
        try:
            sensors = get_sensors(reader)
        finally:
            bus.nak_addresses.discard(i2c_device.device_address)
        assert sensors[reader.name] == {"error": "unavailable"}, (reader.name, sensors[reader.name])
        assert {k: v for k, v in sensors.items() if k != reader.name} == {k: v for k, v in before.items() if k != reader.name}
        log = run(reader.get_error_counter())[reader.name]
        assert log["ErrCount"] == count + 1, (reader.name, log)
        assert (log["ErrType"][-1], log["ErrNum"][-1]) == ("E", code("E", "CHIP_GET")), (reader.name, log)


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


@_register("webserver_networking_put_answers_an_unknown_key_invalid")
def _scenario_networking_put_unknown_key(device: str) -> None:
    # A key no settings group of the endpoint lists is answered in the OK envelope, never dropped unanswered.
    module = build(device)
    body = json.loads(_dispatch(module, "PUT", "/networking", {"NoSuchKey": 1}).body)
    assert (body["res"], body["result"]) == ("OK", {"NoSuchKey": "Invalid"})


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
    # Booted on the schema default, which the offline NTP file would already have emptied; no task starts.
    module = build(device, offline_ntp=False)
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


class _StepGate:
    # Holds the controlled shutdown at a named step until the scenario opens it: a gate, never a sleep.
    def __init__(self) -> None:
        self.arrived = asyncio.Event()
        self.release = asyncio.Event()
        self.step = ""
        self.passed: list[str] = []

    async def hold(self, step: str) -> None:
        self.step = step
        self.passed.append(step)
        self.arrived.set()
        await self.release.wait()
        self.release.clear()

    def open(self) -> None:
        self.arrived.clear()
        self.release.set()


class _SupervisorAtGate(_AsyncioWaits):
    # asy_system_service's asyncio in a command scenario: the start spread yields at once and the supervisor's pass
    # sleep holds at the gate, so a command sent then finds its first step (S1) waiting on the supervisor.
    def __init__(self, gate: "_StepGate") -> None:
        super().__init__()
        self._gate = gate

    async def sleep(self, seconds: float) -> None:
        await self._gate.hold("S1")


def _hold_each_step(module: "Any", gate: "_StepGate") -> None:
    # Gates in front of each later step of the sequence: S2 the stores' flush, S3 storage quiesced, S4 the tasks
    # stopped (right after S3), S5 the file deletions or the chip erase, S6 the reset armed.
    sysfunct, fram = module.sysfunct, module.fram
    flush, quiesce, erase, reboot = sysfunct._flush_config_stores, fram.quiesce, fram.erase_chip, sysfunct._reboot

    async def flush_held(*, close: bool = False, step_done: "Any" = None) -> bool:
        if step_done is not None:  # the sequence's own flush; the reset's last one passes no step_done
            await gate.hold("S2")
        ok: bool = await flush(close=close, step_done=step_done)
        return ok

    async def quiesce_held(step_done: "Any") -> None:
        await gate.hold("S3")
        await quiesce(step_done)
        await gate.hold("S4")

    async def erase_held(step_done: "Any") -> bool:
        await gate.hold("S5")
        ok: bool = await erase(step_done)
        return ok

    async def reboot_held(code: int, message: str, action: "Any", *, fed: bool = False) -> None:
        await gate.hold("S6")
        await reboot(code, message, action, fed=fed)

    stores = sysfunct._config_stores
    delete = stores[0].delete_file

    async def first_delete_held() -> bool:
        await gate.hold("S5")
        ok: bool = await delete()
        return ok

    sysfunct._flush_config_stores = flush_held
    fram.quiesce = quiesce_held
    fram.erase_chip = erase_held
    sysfunct._reboot = reboot_held
    stores[0].delete_file = first_delete_held


async def _until(done: "Callable[[], bool]", what: str) -> None:
    # Yields until done() holds; the bound ends a regression that never gets there instead of hanging the file.
    for _ in range(100000):
        if done():
            return
        await asyncio.sleep(0)
    raise AssertionError(what)


async def _boot_supervised(device: str, gate: "_StepGate", **kwargs: "Any") -> "tuple[Any, asyncio.Task[None]]":
    # main()'s state after its last step: every task started and the supervisor running, its first pass ended at the
    # gate, so a command sent now finds its first step waiting on the supervisor (in this file's one coroutine).
    module, _watchdog = await _boot(device, web_host="127.0.0.1", web_port=0, **kwargs)
    await module.sysfunct.start_tasks(module._collect_task_starters())
    sup = asyncio.create_task(module.sysfunct.supervise_tasks())
    await _until(gate.arrived.is_set, "the supervisor never ended its first pass")
    return module, sup


async def _command_to_reset(module: "Any", sup: "asyncio.Task[None]", gate: "_StepGate", body: "dict[str, Any]", at_step: "Any" = None) -> "dict[str, Any]":
    # The command over REST, every held step let through (at_step(step) run first at each), then the armed reset
    # fired and the supervisor's task ended: the run stops where a real unit restarts. Returns the PUT's results.
    sysfunct = module.sysfunct
    fired = machine.reset_count + machine.bootloader_count
    result: dict[str, Any] = json.loads((await _dispatch_async(module, "PUT", "/system", body)).body)["result"]
    assert result["SystemCmd"] == "Valid", result
    task = sysfunct._shutdown_task
    while True:
        await _until(lambda: gate.arrived.is_set() or task.done(), f"{body}: the sequence stopped between its steps")
        if not gate.arrived.is_set():
            break
        if at_step is not None:
            await at_step(gate.step)
        gate.open()
    await task
    assert sysfunct._reset_armed and machine.reset_count + machine.bootloader_count == fired, "the sequence ended unarmed or reset early"
    sysfunct._reset_timer.trigger()  # the fake Timer fires only on request; its callback wakes the reset task
    await _until(sysfunct._reset_task.done, "the armed reset never ran")
    sup.cancel()
    try:
        await sup
    except asyncio.CancelledError:
        pass
    return result


def _run_gated(gate: "_StepGate", coro: "Coroutine[Any, Any, T]") -> "T":
    asy_system_service.asyncio = _SupervisorAtGate(gate)  # type: ignore[assignment]
    try:
        return run(coro)
    finally:
        asy_system_service.asyncio = asyncio


@_register("webserver_system_put_reboot_cmd_arms_the_real_reset_timer")
def _scenario_system_put_reboot(device: str) -> None:
    # "Valid", then the controlled shutdown arms the reset with region 0's reboot code; the fired timer resets the unit
    # once and the reset cause reads WDT. One coroutine from the boot to the reset: never a nested asyncio.run().
    gate = _StepGate()
    before = machine.reset_count

    async def scenario() -> None:
        module, sup = await _boot_supervised(device, gate)
        await _command_to_reset(module, sup, gate, {"SystemCmd": "reboot"})

    _run_gated(gate, scenario())
    assert machine.mem_backup(0)[1] == _system_const("_RR_REBOOT")
    assert machine.reset_count == before + 1
    assert machine.reset_cause() == machine.WDT_RESET


@_register("webserver_system_put_reboot_flushes_a_still_pending_config_write_first")
def _scenario_system_put_reboot_flushes_pending_write(device: str) -> None:
    # A commanded reboot must not drop a still-staged write: unlike the accepted power-loss residual risk (owner,
    # 2026-09-26; Part F.2) this path waits the flush out, in the sequence's own flush step. A write after it is refused.
    gate = _StepGate()

    async def scenario() -> "tuple[list[object], dict[str, Any]]":
        module, sup = await _boot_supervised(device, gate)
        _hold_each_step(module, gate)
        wifi = module.conn.cfgmgr
        wifi.commit = lambda: None  # its flush waits on a commit no one sends: still staged when the command comes
        staged = json.loads((await _dispatch_async(module, "PUT", "/networking", {"LEDWifiOn": False})).body)["result"]
        del wifi.commit
        seen: list[object] = []

        async def at_step(step: str) -> None:
            if step in ("S2", "S3"):  # just before and just after the sequence's own flush step
                for store, key in ((wifi, "LEDWifiOn"), (module.sysfunct.cfgmgr, "DebugLevel")):
                    with open(store._config_file) as f:
                        seen.append((step, store._pending_flush is None, json.load(f)[key]))

        result = await _command_to_reset(module, sup, gate, {"DebugLevel": 1, "SystemCmd": "reboot"}, at_step)
        assert result == {"DebugLevel": "Valid", "SystemCmd": "Valid"} and staged == {"LEDWifiOn": "Valid"}, (staged, result)
        late = json.loads((await _dispatch_async(module, "PUT", "/networking", {"LEDWifiOn": True})).body)["result"]
        return seen, late

    seen, late = _run_gated(gate, scenario())
    assert seen[:1] == [("S2", False, True)], seen  # the networking write still staged, the file on its old value
    assert seen[2:] == [("S3", True, False), ("S3", True, 1)], seen  # on flash, not merely scheduled, after S2
    assert late == {"LEDWifiOn": "Failed"}, late


def _scd30_readers(module: "Any") -> "list[Any]":
    return [obj for obj in _module_objects(module).values() if isinstance(obj, SCD30_Reader)]


def _scd30_bus(reader: "Any") -> "Any":
    return reader._scd._i2c_scd30.i2c_device.i2c._i2c


def _scd30_put_bodies(reader: "Any") -> "list[dict[str, Any]]":
    # One body per key a PUT may carry, each a value its field accepts: the schema's keys, and ContMeas's stop.
    bodies = []
    for name, kind, default, low, _high, _special in reader.get_cfg_schema():
        value = True if kind == "bool" else (low if low is not None else default)
        bodies.append({reader.name: {name: value}})
    bodies.append({reader.name: {"ContMeas": False}})
    return bodies


async def _every_write_refused(module: "Any", word: str, accepted: "Any") -> "list[object]":
    # Every write the API offers, sent while the sequence waits at a gate: the answers that are not "Failed" (the same
    # command again: "Valid", nothing new started). ResetErrors writes FRAM, not a store: refused once S3 paused FRAM.
    wrong: list[object] = []
    paused = module.fram.get_pause()

    async def put(path: str, body: "dict[str, Any]") -> "dict[str, Any]":
        answer: dict[str, Any] = json.loads((await _dispatch_async(module, "PUT", path, body)).body)["result"]
        return answer

    for reader in _scd30_readers(module):
        queue = _scd30_bus(reader).read_queue_by_address.setdefault(reader._scd._i2c_scd30.i2c_device.device_address, [])
        before = list(queue)
        for body in _scd30_put_bodies(reader):
            # A chip snapshot waits on the bus, so a PUT the closed store let through would read it and write the chip.
            _queue_scd30_snapshot(_scd30_bus(reader), 2)
            waiting = list(queue)
            answer = await put("/sensors", body)
            if answer != {reader.name: dict.fromkeys(body[reader.name], "Failed")} or queue != waiting:
                wrong.append(("/sensors", body, answer, len(waiting) - len(queue)))
            queue[:] = before
    for path, body in (("/networking", {"LEDWifiOn": True}), ("/status", {"ResetErrors": True}), ("/system", {"SystemCmd": "bootloader" if word == "reboot" else "reboot"})):
        answer = await put(path, body)
        if answer != dict.fromkeys(body, "Valid" if path == "/status" and not paused else "Failed"):
            wrong.append((path, body, answer))
    again = await put("/system", {"SystemCmd": word})
    if again != {"SystemCmd": "Valid"} or module.sysfunct._shutdown_task is not accepted:
        wrong.append(("/system", word, again))
    return wrong


class _StaticI2C:
    # rp2's machine.I2C(id) is one object per bus (machine_i2c.c): kept so for one scenario, a controller a recovery
    # rebuilds keeps the log and replies a count reads; every bus is fresh per build again afterwards.
    def __init__(self, device: str) -> None:
        self.ids = [int(name[len("i2c") :]) for name in _wiring_plan(device)["buses"] if name.startswith("i2c")]

    def __enter__(self) -> "_StaticI2C":
        for bus_id in self.ids:
            machine.I2C.reset_id(bus_id)
        return self

    def __exit__(self, *_exc: object) -> None:
        machine.I2C.reset_registry()


def _scd30_commands(reader: "Any", word: int) -> int:
    # The frames of one command word the reader's bus carried to its address, with or without an argument.
    address = reader._scd._i2c_scd30.i2c_device.device_address
    return sum(1 for entry in _scd30_bus(reader).log if entry[0] == "writeto" and entry[1] == address and len(entry[2]) >= 2 and (entry[2][0] << 8 | entry[2][1]) == word)


async def _scd30_cycles(module: "Any") -> "list[tuple[int, int, int]]":
    # Every SCD30's own cycle, driven to its end: the init, its 500 ms ticks past the FRC idle limit, ready and
    # not-ready reads, then reads on an empty bus failing up the recovery ladder until the read task gives up.
    # Returns per reader the idle ticks counted, the measurement reads and the soft resets the bus carried.
    sysfunct = module.sysfunct
    covered: list[tuple[int, int, int]] = []
    for reader in _scd30_readers(module):
        queue = _scd30_bus(reader).read_queue_by_address.setdefault(reader._scd._i2c_scd30.i2c_device.device_address, [])
        queue.extend(scd_register_frame(word) for word in (0x0342, 0, 2))  # the firmware version, offset 0, interval 2 s
        for _ in range(3):
            queue.extend((scd_register_frame(1), scd_data_frame(600.0, 21.5, 40.0)))
        queue.append(scd_register_frame(0))  # data-ready clear: a not-ready read
    await sysfunct.start_tasks(module._collect_task_starters())
    timers = asyncio.create_task(sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters()))

    def stagger_done() -> bool:
        if sysfunct._sequencer_timer.callback is not None:
            sysfunct._sequencer_timer.trigger()
        return timers.done()

    await _until(stagger_done, "start_timers() never finished")
    for reader in _scd30_readers(module):
        for _ in range(4 * reader._frc_interval_s + 2):  # the ticks to the FRC idle limit and past it
            reader._start_trigger_timer.trigger()

            def tick_taken(reader: "Any" = reader) -> bool:
                return not reader._base_trigger_event.state

            await _until(tick_taken, "a tick was never taken")
        idle_ticks = reader._frc_idle_ticks
        read = sysfunct._tasks[sysfunct._task_starters.index(reader.start_asy_read)]
        for _ in range(20):  # each edge one read cycle; the empty bus ends the task within the error budget
            if read.done():
                break
            reader._irq_pin.trigger_irq()
            for _ in range(200):
                await asyncio.sleep(0)
        assert read.done(), f"{reader.name}'s read task outlived its error budget"
        covered.append((idle_ticks, _scd30_commands(reader, 0x0300), _scd30_commands(reader, 0xD304)))
    for task in sysfunct._tasks:
        if task is not None:
            task.cancel()
    await asyncio.sleep(0)
    return covered


@_register("only_the_api_writes_the_scd30")
def _scenario_only_the_api_writes_the_scd30(device: str) -> None:
    # From the boot setup on, the SCD30's own cycle writes nothing to the chip's NVM, its recovery included; a
    # PUT /sensors is the one writer, its one interval frame the only new count.
    async def scenario() -> "tuple[list[dict[int, int]], list[dict[int, int]], list[object]]":
        module, _watchdog = await _boot(device, web_host="127.0.0.1", web_port=0)
        readers = _scd30_readers(module)
        assert readers, f"{device} declares no SCD30"
        after_setup = [scd30_nvm_writes(_scd30_bus(reader)) for reader in readers]
        for idle_ticks, reads, resets in await _scd30_cycles(module):
            # The whole cycle ran: the idle limit reached, the three ready reads, the init's soft reset and the ladder's.
            assert idle_ticks >= 8 and reads >= 3 and resets >= 2, (idle_ticks, reads, resets)
        window = [scd30_nvm_writes(_scd30_bus(reader)) for reader in readers]
        answers: list[object] = []
        for reader in readers:
            _queue_scd30_snapshot(_scd30_bus(reader), 2)
            answers.append(json.loads((await _dispatch_async(module, "PUT", "/sensors", {reader.name: {"MeasInterval": 4}})).body)["result"])
        return after_setup, window, answers + [scd30_nvm_writes(_scd30_bus(reader)) for reader in readers]

    asy_system_service.asyncio = _AsyncioWaits()  # type: ignore[assignment]
    asy_scd30_driver.asyncio = _AsyncioWaits()  # type: ignore[assignment]
    try:
        with _StaticI2C(device):
            after_setup, window, after_put = run(scenario())
    finally:
        asy_system_service.asyncio = asyncio
        asy_scd30_driver.asyncio = asyncio
    assert window == after_setup, (after_setup, window)
    count = len(after_setup)
    assert after_put[:count] == [{"SCD30": {"MeasInterval": "Valid"}}] * count, after_put
    expected = [dict(writes) for writes in window]
    for writes in expected:
        writes[0x4600] = writes.get(0x4600, 0) + 1  # the interval command's one frame
    assert after_put[count:] == expected, (window, after_put)


@_register("every_api_write_is_refused_from_a_system_commands_acceptance_to_its_reset")
def _scenario_writes_refused_during_the_shutdown(device: str) -> None:
    # Each of the four words, its sequence held at every step by a gate: each SCD30 key, a networking setting,
    # ResetErrors and another command answer "Failed", the same command "Valid" with nothing new started, and no
    # SCD30 NVM write happens from the acceptance to the reset (owner, 2026-10-02: no SCD30 write while it runs).
    for word, steps in (("reboot", "S1 S2 S3 S4 S6"), ("bootloader", "S1 S2 S3 S4 S6"), ("resetconfig", "S1 S2 S3 S4 S5 S6"), ("erasefram", "S1 S2 S3 S4 S5 S6")):
        gate = _StepGate()

        async def scenario(word: str = word, gate: "_StepGate" = gate) -> "tuple[list[object], list[dict[int, int]], list[dict[int, int]]]":
            module, sup = await _boot_supervised(device, gate)
            _hold_each_step(module, gate)
            nvm: list[list[dict[int, int]]] = []
            wrong: list[object] = []

            async def at_step(step: str) -> None:
                if not nvm:  # the first step runs right after the acceptance
                    nvm.append([scd30_nvm_writes(_scd30_bus(reader)) for reader in _scd30_readers(module)])
                if module.fram.get_pause() != (step >= "S4"):  # FRAM pauses inside S3's quiesce, before the tasks stop
                    wrong.append((step, "FRAM paused" if module.fram.get_pause() else "FRAM not paused"))
                wrong.extend((step, w) for w in await _every_write_refused(module, word, module.sysfunct._shutdown_task))

            await _command_to_reset(module, sup, gate, {"SystemCmd": word}, at_step)
            return wrong, nvm[0], [scd30_nvm_writes(_scd30_bus(reader)) for reader in _scd30_readers(module)]

        with _StaticI2C(device):
            wrong, accepted, reset = _run_gated(gate, scenario())
        assert gate.passed == steps.split(), (word, gate.passed)
        assert wrong == [], (word, wrong)
        assert reset == accepted, (word, accepted, reset)


@_register("resetconfig_over_a_damaged_config_file_boots_next_on_every_default")
def _scenario_resetconfig_over_a_damaged_file(device: str) -> None:
    # NTP's file corrupted before the boot: the boot repairs it and still lists NTP in ConfigFaults; "Reset to
    # defaults" deletes every file, and the next boot over the same directory writes each once, its defaults alone.
    cfg_path = _tmp_cfg_dir()
    ntp_name = json.loads(_src_const("src/asy_ntp_client.py", "_NAME"))
    with open(asy_config_manager.config_filename(cfg_path, ntp_name), "w") as f:
        f.write("{not json")
    gate = _StepGate()

    async def scenario() -> "list[str]":
        module, sup = await _boot_supervised(device, gate, cfg_path=cfg_path)
        faults: list[str] = json.loads(drain_json_response_body((await _dispatch_async(module, "GET", "/status")).body))["system"]["ConfigFaults"]
        await _command_to_reset(module, sup, gate, {"SystemCmd": "resetconfig"})
        return faults

    assert _run_gated(gate, scenario()) == [ntp_name]
    assert machine.mem_backup(0)[1] == _system_const("_RR_CONFIG_RESET")
    assert [name for name in os.listdir(cfg_path) if name.startswith("config_")] == [], os.listdir(cfg_path)
    module = build(device, cfg_path=cfg_path, offline_ntp=False)  # no task runs: the defaults alone, NTP's included
    stores = _storing_stores(module)
    assert sorted(os.listdir(cfg_path)) == sorted(asy_config_manager.config_filename("", store.module_name) for store in stores)
    for store in stores:
        with open(store._config_file) as f:
            assert json.load(f) == _store_defaults(store), store.module_name
    assert json.loads(status_body(_dispatch(module, "GET", "/status")))["system"]["ConfigFaults"] == []


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
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


@_register("webserver_notification_put_light_cmd_led_rejects_non_numeric_field")
def _scenario_notification_light_cmd_led_rejects_non_numeric_field(device: str) -> None:
    # Another behavior change from the old raw int()/float() casts: those would parse a
    # numeric-looking string ("10") via Python's lenient constructors, while the checked_*() validators only
    # coerces between the two numeric types, so this is now rejected too.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": "10", "G": 20, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


@_register("webserver_notification_put_light_cmd_led_rejects_non_numeric_t")
def _scenario_notification_light_cmd_led_rejects_non_numeric_t(device: str) -> None:
    # T goes through cm.coerce_numeric(payload["T"], float) - a distinct code path from R/G/B's own
    # int coercion (already tested above for R specifically) - confirms the same non-numeric
    # rejection holds for T's own float-typed branch, not just the int-typed ones.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": "soon"}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


@_register("webserver_notification_put_light_cmd_led_rejects_missing_field")
def _scenario_notification_light_cmd_led_rejects_missing_field(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30}})  # T missing
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


@_register("webserver_notification_put_light_cmd_led_rejects_out_of_range_rgb")
def _scenario_notification_light_cmd_led_rejects_out_of_range_rgb(device: str) -> None:
    # Regression test for a real legacy-vs-src/ divergence (SPECIFICATION.md Part H.6's
    # dispatch-only field rules): legacy's led_cmd() rejects out-of-range r/g/b (0-255) where the
    # promoted callback used to silently clamp. Rejected exactly like a missing/non-numeric field.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 256, "G": 20, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


@_register("webserver_notification_put_light_cmd_led_rejects_negative_rgb")
def _scenario_notification_light_cmd_led_rejects_negative_rgb(device: str) -> None:
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": -1, "B": 30, "T": 1.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


@_register("webserver_notification_put_light_cmd_led_rejects_out_of_range_t")
def _scenario_notification_light_cmd_led_rejects_out_of_range_t(device: str) -> None:
    # Legacy's own t bound is 0.5-60.0 - the promoted src/ callback used to floor a too-small t to
    # 0.1 and never bounded a too-large one at all.
    module = build(device)
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": 0.1}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"
    res = _dispatch(module, "PUT", "/notification", {"LightCmdLED": {"R": 10, "G": 20, "B": 30, "T": 100.0}})
    assert json.loads(res.body)["result"]["LightCmdLED"] == "Invalid"


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
    system = body["system"]
    for key in ("ResetReason", "ResetBits", "MemFree"):  # this boot's decoded reason, the chip's raw flags, the free heap
        assert type(system[key]) is int, (key, system[key])
    assert system["ConfigFaults"] == [] and system["ConfigUnpersisted"] == [], system  # a clean boot
    assert "WifiUptime" in body["networking"] and "NTPSynced" in body["networking"] and "WifiTS" in body["networking"]
    assert body["networking"]["HTTPDropped"] == 0  # a clean boot has dropped no connection
    assert "Triggered" in body["notification"] and "PauseTime" in body["notification"]
    # One entry per real module + per real ConfigManager + this service's own "WEBSERVER" entry,
    # from _all_loggers()'s reflected shape. By NAME, not count: the website's errcount rows are
    # keyed by name (Part H.6), so a published key nothing matches renders nothing at all.
    assert {logger.name for logger in _all_loggers(module)} == set(body["errcount"].keys())
    assert len(body["errcount"]) == len(_all_loggers(module)), "two loggers sharing a name would collapse into one row"


def _storing_stores(module: "Any") -> "list[Any]":
    # Every config store the build collected whose schema keeps a value in its file, in the collected order.
    return [store for store in module.sysfunct._config_stores if any(asy_config_manager.check_cfg_get_default(field)[0] for field in store._cfg_vals)]


def _store_defaults(store: "Any") -> "dict[str, Any]":
    fields = asy_config_manager.schema_dict(store._cfg_vals).items()
    return {name: asy_config_manager.check_cfg_get_default(field)[1] for name, field in fields if asy_config_manager.check_cfg_get_default(field)[0]}


def _out_of_field(store: "Any") -> "dict[str, Any] | None":
    # The store's defaults with one bounded number set past its maximum, or None when no field has a maximum.
    for name, field in asy_config_manager.schema_dict(store._cfg_vals).items():
        if field[1] in ("int", "float") and field[4] is not None and name in _store_defaults(store):
            return dict(_store_defaults(store), **{name: field[4] + 1})
    return None


class _ReadFails(WriteCountingOpen):
    # asy_config_manager's open for one boot: reading the one planted file fails as a flash read error would.
    def __init__(self, path: str) -> None:
        super().__init__(asy_config_manager)
        self.path = path

    def __call__(self, path: str, mode: str = "r") -> object:
        if "w" not in mode and path == self.path:
            raise OSError(5, "EIO")
        return super().__call__(path, mode)


@_register("webserver_status_lists_exactly_the_modules_whose_config_file_was_unreadable_or_damaged")
def _scenario_status_config_faults(device: str) -> None:
    # Planted before a boot: one file unreadable, one unparseable, one not an object, one with a value its field
    # refuses - each listed in ConfigFaults even after the boot repaired it; one file lacking a key and one holding
    # an unknown key are repaired and not listed. A missing or unknown key is schema drift, not damage.
    stores = _storing_stores(build(device))
    assert len(stores) >= 6, [store.module_name for store in stores]  # one store per planted case
    bounded = next(store for store in stores if _out_of_field(store) is not None)
    others = [store for store in stores if store is not bounded]
    unreadable, unparseable, not_object, lacking, unknown = others[:5]
    cfg_path = _tmp_cfg_dir()
    planted = {
        unreadable: "{}",
        unparseable: "{not json",
        not_object: "[1, 2]",
        bounded: json.dumps(_out_of_field(bounded)),
        lacking: json.dumps(dict(list(_store_defaults(lacking).items())[1:])),
        unknown: json.dumps(dict(_store_defaults(unknown), NoSuchKey=1)),
    }
    for store, text in planted.items():
        with open(asy_config_manager.config_filename(cfg_path, store.module_name), "w") as f:
            f.write(text)
    unreadable_path = asy_config_manager.config_filename(cfg_path, unreadable.module_name)
    with _ReadFails(unreadable_path):
        module = build(device, cfg_path=cfg_path)
    faulted = [unreadable, unparseable, not_object, bounded]
    system = json.loads(status_body(_dispatch(module, "GET", "/status")))["system"]
    assert system["ConfigFaults"] == [store.module_name for store in stores if store in faulted], system["ConfigFaults"]
    assert system["ConfigUnpersisted"] == [], system["ConfigUnpersisted"]
    with open(unreadable_path) as f:
        assert f.read() == "{}", "the unreadable file was overwritten"
    for store in (unparseable, not_object, bounded, lacking, unknown):  # every readable damaged or drifted file repaired
        with open(asy_config_manager.config_filename(cfg_path, store.module_name)) as f:
            assert json.load(f) == _store_defaults(store), store.module_name


@_register("webserver_status_lists_a_module_whose_config_write_failed_until_its_next_good_write")
def _scenario_status_config_unpersisted(device: str) -> None:
    # Every file write of a fresh boot refused: each storing module runs on values the flash lacks and is listed in
    # ConfigUnpersisted (not ConfigFaults: no file was damaged); a module's next good write takes it off the list.
    cfg_path = _tmp_cfg_dir()
    with WriteCountingOpen(asy_config_manager, fail_writes=True):
        module = build(device, cfg_path=cfg_path)
    names = [store.module_name for store in _storing_stores(module)]
    system = json.loads(status_body(_dispatch(module, "GET", "/status")))["system"]
    assert (system["ConfigUnpersisted"], system["ConfigFaults"]) == (names, []), system
    assert json.loads(_dispatch(module, "PUT", "/system", {"DebugLevel": 1}).body)["result"]["DebugLevel"] == "Valid"
    run(module.sysfunct.cfgmgr.flush_pending())
    system = json.loads(status_body(_dispatch(module, "GET", "/status")))["system"]
    assert system["ConfigUnpersisted"] == [name for name in names if name != module.sysfunct.cfgmgr.module_name], system


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
    assert networking["WifiTS"] == run(conn.get_data()).TS  # the time of the snapshot these fields came from


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


@_register("webserver_system_get_sends_the_unavailable_marker_for_an_unreadable_system_store")
def _scenario_system_get_unreadable_store(device: str) -> None:
    # SYSTEM's config file is a directory, so its store cannot be read: each of its fields on GET /system carries the
    # marker in place of a value, never a null or a missing key, while the other modules' fields keep theirs.
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_SYSTEM.cfg")
    module = build(device, cfg_path=cfg_path)
    body = json.loads(status_body(_dispatch(module, "GET", "/system")))
    groups = module.webserver._settings["system"]
    system_fields = [field for group in groups if group.module is module.sysfunct for field in group.fields]
    others = [(group.module, field) for group in groups if group.module is not module.sysfunct for field in group.fields]
    assert system_fields and others
    assert [body[field] for field in system_fields] == [{"error": "unavailable"}] * len(system_fields), body
    for other, field in others:
        assert body[field] == run(other.get_dict_cfg())[other.name][field], (field, body[field])


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


class _RefusedStream:
    # A connection the ceiling refuses: _serve() closes it and never reads or writes it.
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


@_register("webserver_status_counts_a_refused_connection_in_http_dropped_until_reset_errors")
def _scenario_http_dropped_counts_a_refusal(device: str) -> None:
    # One connection past the device's own ceiling: refused, traced once, counted in /status's HTTPDropped, and
    # ResetErrors clears the window with the logs.
    module = build(device)
    webserver = module.webserver
    stream = _RefusedStream()

    async def refuse_one() -> None:
        for _ in range(webserver._max_connections):  # every slot held, as by open connections
            await webserver._open_conns.increment()
        await webserver._serve(stream, stream)
        for _ in range(webserver._max_connections):
            await webserver._open_conns.decrement()

    run(refuse_one())
    assert stream.closed
    log = run(webserver.get_error_counter())["WEBSERVER"]
    assert log["ErrCount"] == 1, log
    assert (log["ErrType"][-1], log["ErrNum"][-1]) == ("W", code("W", "HTTP_REFUSED")), log
    assert json.loads(status_body(_dispatch(module, "GET", "/status")))["networking"]["HTTPDropped"] == 1
    assert json.loads(_dispatch(module, "PUT", "/status", {"ResetErrors": True}).body)["result"] == {"ResetErrors": "Valid"}
    assert json.loads(status_body(_dispatch(module, "GET", "/status")))["networking"]["HTTPDropped"] == 0


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
    # All-paths coverage through the real wiring: the ".." guard clause in _StaticRoutes.serve() runs
    # before is_hotspot_active() is ever consulted (see asy_webserver_service.py's own source order).
    module = build(device)
    assert module.conn is not None
    module.conn._conn_phase = _PHASE_HOTSPOT
    res = _dispatch(module, "GET", "/foo/../../index.html")
    assert res.status_code == 404


@_register("is_hotspot_active_wiring_put_to_unmatched_path_still_405_in_hotspot_mode")
def _scenario_hotspot_put_unmatched_405(device: str) -> None:
    # All-paths coverage: a non-GET request to an unmatched path resolves to 405 inside Microdot's
    # own routing before _StaticRoutes.serve() is ever reached - real hotspot state must not change that.
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
