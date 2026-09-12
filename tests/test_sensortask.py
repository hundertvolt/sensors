"""Construction/wiring tests for every real device's buildgen-generated sensortask_<device>.py
build_system() - SPECIFICATION.md Part A.7 has the full reference. Also covers real webserver
wiring; deep per-route behavior stays tests/test_asy_webserver_service.py's job."""

import asyncio
import json
import os
import sys

# Same convention as tests/test_asy_webserver_service.py's own module docstring: scripts/test.sh's
# MICROPYPATH deliberately excludes ext/, and every generated sensortask_<device> module now
# transitively imports microdot (via asy_webserver_service.py) - extending sys.path here reaches
# the real, vendored ext/microdot.py without touching MICROPYPATH/pyproject.toml/scripts/test.sh.
sys.path.insert(0, "ext")

import machine
from _fram_chip_fake import FakeMB85RS64V
from _shared_rest_roundtrip import (
    assert_named_modules_constructed,
    assert_sensor_payload_not_self_wrapped,
    drain_json_response_body,
)
from microdot import Request, Response  # type: ignore[import-not-found]

import asy_spi_driver
from print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore

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
    # GET /status streams from a plain list of already-json.dumps()-encoded fragments now (see
    # asy_webserver_service.py's _get_status()/_build_status_pieces()) - drains it the way a real
    # client naturally would, so every existing json.loads(...) assertion on a GET /status response
    # keeps working unchanged.
    return drain_json_response_body(res.body)


# Every real device (devices/*.toml) - buildgen generates each one's own module + wiring plan into
# build/generated_src/ before scripts/test.sh ever runs this file (scripts/_generate_sensortask_modules.py).
_DEVICES = ("wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi")


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # dev's real FRAM chip is a 256KB MB85RS2MTA (product ID 0x04 0x7F 0x48 0x03, SPECIFICATION.md
    # Part C.3.1), not the 8KB MB85RS64V every other real device uses (the base fake's own default
    # RDID). A subclass, not a post-construction override, since build_system() constructs the chip
    # with no such hook. Only the RDID changes, not the fake's own memory buffer size - nothing in
    # this file's own construction/wiring scope ever writes chunks anywhere near a real chip's
    # capacity ceiling, on either size; the RDID is what asy_fram_manager.py's own setup() actually
    # keys "did I find the chip I expect" off.
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])


# Same "keyed by the real chip's own max_size" table digital_twin/machine.py's own
# _FRAM_RDID_BY_MAX_SIZE uses for the identical reason - derived from each device's own real FRAM
# instance (devices/*.toml's [[instance]] driver="fram" max_size=...), read here from the wiring
# plan buildgen already computed, not a hardcoded wozi/dev special case. A future device with a
# third real FRAM size needs one new entry here, the same narrow addition twin_wiring.py's own table
# would need.
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


# ---------------------------------------------------------------------------
# Per-test config-file isolation - same pattern as test_ntp_fram_system_integration.py's own
# _tmp_cfg_dir(): build_system() constructs several real ConfigManager-backed modules (conn, ntp,
# sgp40, [bmp3xx], notification), each of which writes/reads a real config_<NAME>.cfg file at its
# cfg_path - repeated calls across test_* functions in this one process must not collide on the
# same files, and must not touch the real repo-root config files either. One shared "sensortask_"
# prefix, not one per device, now that this file collapses what used to be two separate files
# (BUILD_CHAIN_PLAN.md's Session 6.2) - _next_dir's own per-process counter already keeps every
# call's own directory unique regardless of which device that call happens to be for.
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # _next_dir always restarts at 0 per process, so a second scripts/test.sh run on the same
    # machine reuses the exact same directory names an earlier run already left behind - and
    # "already exists from a stale previous run" (the comment below used to say) turns out not to
    # be harmless: the earlier run's real, persisted config_*.cfg files are still sitting there, so
    # a write that should be a genuine value change instead compares against yesterday's
    # already-matching value and gets misreported "Unchanged" instead of "Valid" (confirmed by
    # direct reproduction against this file's own former two halves). This exact _tmp_cfg_dir()
    # shape is copy-pasted across every test_*.py file with its own _TMP_DIR/_next_dir pair - same
    # fix applied uniformly to each. Sweeping at import time, rather than only guarding against the
    # empty-directory case os.mkdir()'s own try/except already handled, is what actually restores
    # the "must not collide"/fresh-directory guarantee this helper's own docstring promises.
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


_sweep_stale_tmp_dirs("sensortask_")


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/sensortask_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    return path + "/"


# ---------------------------------------------------------------------------
# _sweep_stale_tmp_dirs() itself - regression coverage for the actual bug (a later scripts/test.sh
# run silently reusing an earlier run's persisted config files), not just a re-assertion of the
# pre-existing "config write applies" expectation. Device-independent (no build_system() call at
# all), so these run once, not parametrized.
# ---------------------------------------------------------------------------


def test_sweep_stale_tmp_dirs_removes_a_pre_existing_matching_directory_and_its_contents() -> None:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    stale_dir = _TMP_DIR + "/sensortask_stale_test_marker"
    try:
        os.mkdir(stale_dir)
    except OSError:
        pass
    with open(stale_dir + "/config_LEFTOVER.cfg", "w") as f:
        f.write('{"NTP_Host": "time.example.org"}')  # shaped like a real persisted config write

    _sweep_stale_tmp_dirs("sensortask_stale_test_marker")

    try:
        os.stat(stale_dir)
        raise AssertionError("expected the stale directory to have been removed")
    except OSError:
        pass  # gone, as expected


def test_sweep_stale_tmp_dirs_leaves_non_matching_entries_alone() -> None:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    keep_dir = _TMP_DIR + "/not_sensortask_prefixed_marker"
    try:
        os.mkdir(keep_dir)
    except OSError:
        pass

    _sweep_stale_tmp_dirs("sensortask_")  # this file's own real prefix - must not touch an unrelated name

    os.stat(keep_dir)  # still there - raises OSError (failing this test) if it got swept
    os.rmdir(keep_dir)  # this test's own responsibility to clean up, not _sweep_stale_tmp_dirs()'s


def test_sweep_stale_tmp_dirs_tolerates_a_missing_tmp_dir_entirely() -> None:
    # Nothing to assert beyond "doesn't raise" - the real-world case this guards is the very first
    # scripts/test.sh run ever, before tests/_tmp exists at all.
    try:
        os.listdir(_TMP_DIR)  # raises immediately (before any iteration) if _TMP_DIR is missing
    except OSError:
        pass  # confirms this environment's own tests/_tmp is absent for this particular check
    else:
        return  # tests/_tmp already exists (other tests created it) - nothing new to prove here
    _sweep_stale_tmp_dirs("sensortask_")


# ---------------------------------------------------------------------------
# _boot()/reflective helpers - the mechanism every parametrized scenario below shares.
# ---------------------------------------------------------------------------

_OPTIONAL_INSTANCE_NAMES = ("scd30", "sgp40", "bmp3xx", "neopixel", "notification")


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
    # Reflective, not a hardcoded per-device table - but the oracle is the wiring plan buildgen
    # wrote BEFORE this module was even generated (scripts/_generate_sensortask_modules.py's own
    # "instances" list, straight from devices/<device>.toml), never the built module's own
    # attributes: reading the module back (getattr(module, name, None) is not None) can't
    # distinguish "device genuinely has no bmp3xx" from "buildgen silently dropped a declared
    # driver" - a real construction bug would read back as though the driver was never wired at
    # all, and every check below would agree with it. fram is deliberately excluded here - every
    # real device has one unconditionally, and it's never part of the sensor-facing sets below.
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
        # it and stop testing a real, live object - confirmed by direct review this was the one
        # blind spot the "declared present -> constructed" check above didn't cover.
        assert getattr(module, name, None) is None, f"{name} is NOT in devices/{device}.toml's own instances, but build_system() constructed it anyway"
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
    # scd30 before sgp40 before bmp3xx: matches buildgen's own construction/collection order
    # (topological - sgp40 depends on scd30 as its temperature/humidity source, so scd30 is built
    # and collected first) - every real device's own devices/*.toml lists its instances in this
    # same relative order (BUILD_CHAIN_PLAN.md's Session 2), so this fixed shape (rather than a
    # generic reflective walk of buildgen's own construction order) stays correct for all 6. This
    # test pairs setters[i] with loggers[i] by index elsewhere in this file, so this order is
    # load-bearing.
    if _has(module, "scd30"):
        loggers.append(module.scd30.pr)
    if _has(module, "sgp40"):
        loggers += [module.sgp40.pr, module.sgp40.cfgmgr.pr]
    if _has(module, "bmp3xx"):
        loggers += [module.bmp3xx.pr, module.bmp3xx.cfgmgr.pr]
    loggers += [module.neopixel.pr, module.notification.pr, module.notification.cfgmgr.pr, module.webserver.pr]
    return loggers


def _expected_fram_chunk_calls(module: "Any") -> "list[str]":
    # SystemService(chunk) -> SCD30_Reader(chunk) -> SGP40 own log(chunk) -> SGP40 VOC backup
    # (timestamped) -> [BMP3xx_Reader(chunk), only if present] -> NeopixelDriver(chunk) ->
    # NotificationCoordinator(chunk), in that order, unconditionally. SCD30 constructs before SGP40
    # (ordering-hazard #1, SPECIFICATION.md Part A.7/C.14 - SGP40 holds a direct reference to scd30
    # as its temperature_source/humidity_source, so the producer must exist first). Derived from the
    # module's own reflected instance set (_present_optional_instances()), not a hardcoded
    # per-device literal - every real device's own devices/*.toml lists its instances in this same
    # relative order (BUILD_CHAIN_PLAN.md's Session 2), so this fixed shape stays correct for all 6.
    calls = ["chunk"]  # SystemService
    if _has(module, "scd30"):
        calls.append("chunk")
    if _has(module, "sgp40"):
        calls += ["chunk", "timestamped"]
    if _has(module, "bmp3xx"):
        calls.append("chunk")
    calls += ["chunk", "chunk"]  # NeopixelDriver, NotificationCoordinator - always present
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
# parametrized by `device` and registered once per real device below via _register()/globals(),
# mirroring tests/test_digital_twin_webserver_concurrency.py's own dynamic-registration convention
# (the only parametrization mechanism available without a real pytest - SPECIFICATION.md Part E.1).
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
    # Bare module-level attributes - reaches every long-lived object the same way the legacy
    # reference file's own module-level names would be reached. Shared shape with the twin's own
    # equivalent test (tests/_shared_rest_roundtrip.py). Mandatory infra + this device's own
    # reflected optional-instance set - never a hardcoded 3-sensor literal.
    mandatory = ("conn", "ntp", "i2c0", "i2c1", "spi0", "fram", "sysfunct", "neopixel", "notification", "watchdog")
    assert_named_modules_constructed(module, mandatory + _present_optional_instances(module))


@_register("scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it")
def _scenario_scd30_clock_stretch(device: str) -> None:
    # SCD30 documents up to 150ms of clock stretching once per day for internal calibration
    # (datasheets/scd30/..._Interface_Description.pdf p.2) - rp2's own I2C timeout default is
    # 50ms (DEFAULT_I2C_TIMEOUT, ports/rp2/machine_i2c.c), so whichever bus SCD30 sits on must
    # override it or that expected stretch surfaces as a spurious OSError roughly once a day.
    # Looked up through scd30 itself (not assumed to be i2c0) - every real device wires it to i2c0
    # today, but this test stays correct as-is if a future variant wired it elsewhere.
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
    # main() itself (not just build_system()) must accept and forward the override - the real entry
    # point calls <module>.main(), never build_system() directly. Fakes
    # start_timers()/ntp_force_sync()/start_and_check_tasks() the same way this file's own
    # main-call-order scenario (below) already does, and for the same reason (see that scenario's
    # own comment): start_timers()'s real Timer-sequencing chain never completes under
    # tests/machine.py's fake, which only fires Timer callbacks via manual .trigger() - awaiting it
    # for real here would hang.
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
    # Every FRAM-chunk-owning module's own PrintLogHistoryStore/AsyFramTimestampedChunk degrades to
    # in-memory-only on allocation failure rather than raising (base_classes.py's own contract) -
    # assert the happy path actually got real FRAM-backed chunks, not a silently-degraded one.
    assert module.sysfunct is not None and module.neopixel is not None and module.notification is not None
    assert isinstance(module.sysfunct.pr, PrintLogHistoryStore)
    assert module.sysfunct.pr.fram is not None
    assert isinstance(module.neopixel.pr, PrintLogHistoryStore)
    assert module.neopixel.pr.fram is not None
    assert isinstance(module.notification.pr, PrintLogHistoryStore)
    assert module.notification.pr.fram is not None
    if _has(module, "scd30"):
        assert isinstance(module.scd30.pr, PrintLogHistoryStore)
        assert module.scd30.pr.fram is not None
    if _has(module, "sgp40"):
        assert isinstance(module.sgp40.pr, PrintLogHistoryStore)
        assert module.sgp40.pr.fram is not None
        assert module.sgp40.ts_storage is not None
    if _has(module, "bmp3xx"):
        assert isinstance(module.bmp3xx.pr, PrintLogHistoryStore)
        assert module.bmp3xx.pr.fram is not None


class _DeadFramChip(FakeMB85RS64V):
    # Same technique as test_fram_integration.py's own
    # test_sensorreader_runs_in_degraded_mode_when_fram_setup_never_succeeded: a real device-ID
    # mismatch (not just fram=None) - the chip responds, just never comes up as an MB85RS64V. Not
    # device-specific: any RDID mismatch degrades the same way regardless of which real chip's
    # RDID the healthy case would have used.
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])


@_register("build_system_never_insists_on_fram_hardware_being_available")
def _scenario_fram_never_required(device: str) -> None:
    # Owner requirement: no module may insist on FRAM availability - every currently FRAM-backed
    # error log must keep working in plain RAM, and SGP40 specifically must keep running (skipping
    # backup/restore entirely) without FRAM. Exercises the *whole* construction chain with a dead
    # chip, not just one driver in isolation (asy_sgp40_driver.py's/print_log.py's own test suites
    # already cover each class's own degraded-mode contract at the unit level in more depth).
    asy_spi_driver._SPI = _DeadFramChip  # type: ignore[misc]
    module = __import__(f"sensortask_{device}")
    run(module.build_system(cfg_path=_tmp_cfg_dir()))

    # build_system() completed fully - didn't raise, didn't skip constructing anything - despite
    # the underlying FRAM chip never coming up.
    assert module.fram is not None
    assert module.fram.fram is not None
    assert module.fram.fram.initialized is False  # the dead chip, confirmed never ready
    assert module.sysfunct is not None and module.neopixel is not None and module.notification is not None

    # Every FRAM-chunk-owning module's own logger still allocated a chunk (pure bookkeeping,
    # SPECIFICATION.md C.13 - doesn't require setup() to have succeeded) but stays functional in
    # degraded mode rather than raising - matches test_fram_integration.py's own established
    # "reader.pr.fram is not None, just permanently hardware-unusable" pattern.
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

    # notify_finalize runs during synchronous construction, before any setup() call; sysfunct is
    # first *within* the async setup() batch - resolves the real persisted debug level as early as
    # possible (this module's own docstring). conn/ntp were both built before fram/sysfunct but are
    # placed after them here too, matching sysfunct's/fram's own already-fixed positions; conn before
    # ntp mirrors their own real construction order. bmp only appears for a device that has one.
    expected = ["notify_finalize", "sysfunct", "fram", "conn", "ntp", "sgp"]
    if _has(module, "bmp3xx"):
        expected.append("bmp")
    expected.append("notify_setup")
    assert calls == expected


def _bmp3xx_devices() -> "frozenset[str]":
    # Which of _DEVICES actually declare a bmp3xx instance, derived from each device's own wiring
    # plan (buildgen-computed from devices/*.toml) rather than a hardcoded "wozi/dev" literal -
    # used only where a scenario needs to know this BEFORE construction (to decide whether to
    # import/patch BMP3xx_Reader at all); every other scenario derives it AFTER construction, by
    # reflecting on the built module itself.
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
# registry collected once at boot (owner requirement: general, system-wide, not per-module - but
# no shared mutable value anywhere; see SPECIFICATION.md Part A.7's "Debug-level registry"
# section and _collect_level_setters() for the full logger list).
# ---------------------------------------------------------------------------


@_register("collect_level_setters_returns_one_entry_per_logger_in_the_object_graph")
def _scenario_collect_level_setters(device: str) -> None:
    module = build(device)
    setters = module._collect_level_setters()
    loggers = _all_loggers(module)
    assert len(setters) == len(loggers)
    # Each collected setter really is that logger's own bound set_level - confirmed by behavior
    # (bound-method identity isn't guaranteed, matching this file's own established convention for
    # checking bound methods elsewhere): calling it must change that exact logger's own level.
    # Index-based, not zip() - avoids a silent length-mismatch footgun on top of the explicit
    # length assert above.
    for i in range(len(loggers)):
        loggers[i].set_level(PrintLog.level_off())
        setters[i](PrintLog.level_info())
        assert loggers[i].get_level() == PrintLog.level_info()


@_register("debug_seed_value_is_the_starting_level_before_setup_resolves_the_persisted_one")
def _scenario_debug_seed_value(device: str) -> None:
    module = build(device, debug=PrintLog.level_warn())
    assert module.sysfunct is not None
    # First boot - no persisted value yet, so sysfunct.setup() writes and resolves the schema
    # default (0), then pushes it out through the registry - overriding the debug= seed every
    # individual module's own logger was constructed with. Matches test_system_service.py's own
    # test_setup_resolves_cfgmgr_and_leaves_debug_level_at_the_default_on_first_boot.
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
    # Each real module's own get_task_starters() output is present. MicroPython bound methods
    # don't expose __self__ (confirmed directly against the real Unix-port interpreter - a
    # CPython-only introspection assumption), but they do compare equal when bound to the same
    # (instance, function) pair, so membership via == still proves each owner actually contributed
    # its own starters to the combined list, not just that the total count happens to match.
    for owner in _sensor_reader_owners(module):
        for expected in owner.get_task_starters():
            assert expected in starters, f"no task starter bound to {owner!r}"


@_register("collect_timer_starters_includes_every_constructed_module")
def _scenario_collect_timer_starters(device: str) -> None:
    # Every constructed module is checked here, not just the ones that currently contribute a real
    # timer (matches _scenario_collect_task_starters's own uniform ownership check) - neopixel/
    # notification/webserver all currently return [] from their own get_timer_starters(), but this
    # test still proves _collect_timer_starters() actually calls each of them (rather than picking
    # modules by name), since a future Timer added to any of the three would otherwise silently
    # never run.
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
# start_and_check_tasks(), in that order. start_timers()'s real Timer-sequencing mechanism and
# start_and_check_tasks()'s real supervisor loop are each already thoroughly covered by
# test_system_service.py directly - this test fakes both out (they'd otherwise need real
# wall-clock-firing Timers, which tests/machine.py's fake only fires via manual .trigger(), or
# block forever) to verify main() itself wires the pieces together in the right order, without
# re-proving either subsystem's own internals here.
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
# registering every real driver's SettingsGroup/status_source/system_cmd/notification_led/
# maintenance_sensor/error_source. These tests check the *real* registrations landed correctly
# (right module, right fields, right hooks) - not the generic dispatch/aggregation logic itself,
# which tests/test_asy_webserver_service.py's own uniform-fake suite already covers in full depth
# (its own endpoint-design decision), and not real concurrent-connection behavior, which
# tests/test_digital_twin_webserver_concurrency.py already covers, also parametrized across all 6
# devices.
# ---------------------------------------------------------------------------


@_register("webserver_pr_is_ram_only_not_fram_backed")
def _scenario_webserver_pr_ram_only(device: str) -> None:
    # Deliberate decision (see build_system()'s own comment): a warning on every per-call/outer-cap
    # reclaim could churn far faster than any sensor's rare-hardware-fault log - keeping it RAM-only
    # also preserves the FRAM allocation order (see SPECIFICATION.md Part A.7) unchanged.
    module = build(device)
    assert module.webserver is not None
    assert isinstance(module.webserver.pr, PrintLogHistory)
    assert not isinstance(module.webserver.pr, PrintLogHistoryStore)


@_register("webserver_measurements_and_sensors_get_include_every_real_sensor")
def _scenario_webserver_measurements_and_sensors_get(device: str) -> None:
    # Shared shape with the twin's own equivalent check (tests/_shared_rest_roundtrip.py). Expected
    # sensor-name set is derived reflectively from this device's own present optional instances
    # (scd30/sgp40/bmp3xx only - neopixel/notification aren't sensors=-registered), never a
    # hardcoded wozi/dev 3-sensor literal.
    module = build(device)
    expected = {name.upper() for name in _present_optional_instances(module) if name in ("scd30", "sgp40", "bmp3xx")}
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
    # Regression test from baseline verification: SCD30_Reader is the only sensors=-registered
    # module that's a plain SensorReader rather than a SensorReaderConfig subclass (no local
    # cfgmgr - these params live on the sensor itself, see asy_scd30_driver.py's own _VAL_*
    # comment), so it never inherited get_cfg_schema() the way every other registered sensor does.
    # _put_sensors() calls module.get_cfg_schema() uniformly for every sensor named in the PUT
    # body - without SCD30_Reader's own now-added method, this crashed with a real 500
    # (AttributeError).
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
    # Another behavior change from the old raw int()/float() casts: those would silently parse a
    # numeric-looking string ("10") via Python's lenient int()/float() constructors -
    # coerce_numeric() never parses strings, only coerces between the two numeric types, so this
    # is now rejected too.
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
    # dispatch-only field rules): legacy's own led_cmd() validates and rejects out-of-range r/g/b
    # (0-255) - the promoted src/ callback used to silently clamp instead. Rejected exactly like a
    # missing/non-numeric field.
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
    # Deliberately one dispatch per test (not both boundaries in one test function): _dispatch()
    # drives each call through its own fresh asyncio.run(), so NeopixelDriver's background
    # neopixel_signal() consumer task never actually runs here - a second real request_signal()
    # call in the same test would find start_signal_event already set from the first call and
    # never cleared, hanging forever in request_signal()'s own `while ...: await asyncio.sleep(0)`
    # loop. Matches every other lightCmdLED scenario in this file's own single-dispatch convention.
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
    # SGP40 is the only sensor with real maintenance data (VOC backup/restore timestamps) -
    # reflective, not hardcoded, since a future device without sgp40 (buildgen/codegen.py's own
    # "if sgp40 in have") would otherwise go stale silently here.
    assert set(body["sensors"].keys()) == ({"SGP40"} if _has(module, "sgp40") else set())
    assert "BackupTS" in body["sensors"]["SGP40"] and "RestoreTS" in body["sensors"]["SGP40"]
    assert "SysUptime" in body["system"] and "LocalTime" in body["system"] and "UtcTime" in body["system"]
    assert "WifiUptime" in body["networking"] and "NtpSynced" in body["networking"]
    assert "Triggered" in body["notification"] and "PauseTime" in body["notification"]
    # One entry per real module + per real ConfigManager + this service's own "WEBSERVER" entry -
    # derived from _all_loggers()'s own reflected shape, never a hardcoded wozi/dev-specific count.
    assert len(body["errcount"]) == len(_all_loggers(module))


@_register("webserver_system_get_reports_the_real_build_info")
def _scenario_system_get_build_info(device: str) -> None:
    # BUILD_CHAIN_PLAN.md Session 7: every generated device embeds buildgen.version.FIRMWARE_VERSION/
    # WEBSITE_VERSION plus a real build timestamp and reports them live under GET /system's "build"
    # sub-entry. Can't cross-check the exact values against buildgen itself from inside the
    # MicroPython interpreter (host-CPython-only tooling), so this proves presence/shape only.
    module = build(device)
    res = _dispatch(module, "GET", "/system")
    body = json.loads(status_body(res))
    build_info = body["build"]
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
    # SPECIFICATION.md Part C.7's boot window, reproduced exactly. Every FRAM-backed logger runs its
    # own pr.setup() from inside its task - SGP40's lives in read_loop()'s _init_sgp() - while the
    # webserver's own task answers as soon as start_server() returns. So a ResetErrors PUT can land
    # while the chunk still holds the previous boot's history and the RAM-side logger is still
    # uninitialized. build_system() starts no tasks, so that state is deterministic here.
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
# `is_hotspot_active=conn.is_hotspot_active` (build_system()'s own real WebserverService(...) call)
# actually reaches the real, wired conn instance, through the real construction graph - not a fake
# callback like tests/test_asy_webserver_service.py's own Section G.2 coverage. No real WiFi task is
# started here (deliberately - see test_digital_twin_real_website_integration.py's own note for the
# same reasoning): conn._conn_phase is set directly, the same test-seam convention this file's own
# networking-PUT scenarios above already use for a real driver's internal state.
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
    expected = {name.upper() for name in _present_optional_instances(module) if name in ("scd30", "sgp40", "bmp3xx")}
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
# Registration: one test_<scenario>_<device> per (scenario, device) pair - microtest.py discovers
# every callable in globals() named test_*, the only parametrization mechanism available here
# (no real pytest on MicroPython - SPECIFICATION.md Part E.1). fn/device are bound as
# default-argument values, not read from the loop variable, since a closure over a `for` loop's own
# variable would otherwise have every generated test share the SAME (last-iteration) device/fn.
# ---------------------------------------------------------------------------

for _scenario_name, _scenario_fn in _SCENARIOS:
    for _device in _DEVICES:

        def _make_test(fn: "Callable[[str], None]" = _scenario_fn, device: str = _device) -> "Callable[[], None]":
            def test() -> None:
                fn(device)

            return test

        globals()[f"test_{_scenario_name}_{_device}"] = _make_test()


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
