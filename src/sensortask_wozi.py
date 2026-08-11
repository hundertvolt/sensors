"""Stage 1 standalone prototype - async-safe rewrite of
improved-quality/sensortask-wozi.py's flat, module-level construction sequence (Step 1 of the
final-wiring effort; see FINAL_WIRING_PLAN.md's Step 1 section and WIRING_CONTRACT.md for the full
rationale, including the FRAM chunk-order determinism rule this file must preserve exactly).

build_system() constructs every module the reference file constructs, in the same FRAM-chunk-
preserving relative order, as bare module-level globals (owner-confirmed - no wrapper container).
It also runs the grouped await x.setup() batch every SensorReaderConfig-descended module now needs
(SPECIFICATION.md Part C.13's sync-__init__/async-setup() pattern) - sysfunct first (resolves the
persisted debug level as early as possible), then fram, then sgp_reader, then bmp_reader, then
notify_service, deliberately batched together after all synchronous construction (including
notify_service's own register()/finalize() staged construction) rather than interleaved:
notify_service.setup() is only valid to call after finalize() has run (asy_notification_service.py's
own documented contract), so batching at the end is the one ordering that's correct for every
module, not just tidy for the rest.

Every logger in the whole constructed object graph - not just each module's own top-level self.pr,
but every nested cfgmgr.pr and AsyConnTime's own dns_server.pr too - has its own set_level() bound
method collected into sysfunct's level-setter registry (see _collect_level_setters() below and
system_service.py's set_level_setters()/_apply_level()). A change via sysfunct.set_debug_level()
(once Step 2 wires a REST route to it) calls every one of these set_level() methods directly - no
shared mutable value anywhere, each PrintLog instance stays a plain, independent object.

Deliberately excluded from this file (owner-confirmed, see FINAL_WIRING_PLAN.md's refined plan):
Microdot/routes (Step 2's job entirely, as a registration-based service, not a copy of the
reference file's route-decorator shape) and `import frozen_html` (Step 4's job). No top-level
blocking call anywhere in this module either - importing it and calling build_system() must always
return; the real "importing this triggers boot" firmware behavior lives in
boot_entry/wozi_boot.py instead, kept deliberately separate so this module stays independently
testable the way every other src/ module already is.
"""

import asyncio
from asyncio import ThreadSafeFlag

from machine import WDT
from micropython import const

import asy_i2c_driver
import asy_spi_driver
import config_manager as cm
from asy_bmp3xx_driver import BMP3xx_Reader
from asy_fram_manager import AsyFramManager
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_ntp_client import AsyNtpClient
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_wifi_service import AsyConnTime
from system_service import SystemService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

# Grouped, generator-fillable constants (FINAL_WIRING_PLAN.md's refined plan: "keep these variables
# in a well readable place, we will fill them in via the generator script once this will be set
# up"). Values copied verbatim from improved-quality/sensortask-wozi.py - no re-tuning.
_MAX_MODULE_ERROR = const(5)  # consecutive-failure-streak threshold shared by every module's own
# _error_check() give-up decision - renamed project-wide from the old, I2C-specific-sounding
# max_i2c_err this session (SPECIFICATION.md C.2).
_DNS_TIMEOUT_MS = const(500)  # per-server, per-attempt DNS lookup budget
_DNS_TRIES = const(1)  # retry budget per DNS server
_NTP_FETCH_TIMEOUT_MS = const(5000)  # timeout for the actual NTP request/reply round trip

_FIELD_WARN_CO2: "cm.ConfigSchema" = (("WarnCO2", "int", 1600, 0, 3000, None),)
_FIELD_WARN_VOC: "cm.ConfigSchema" = (("WarnVOC", "int", 350, 0, 500, None),)
_FIELD_WARN_HUM: "cm.ConfigSchema" = (("WarnHum", "float", 65.0, 0.0, 100.0, None),)

# Bare module-level globals (owner-confirmed - FINAL_WIRING_PLAN.md's refined plan Q3): every
# long-lived object build_system() constructs is reachable the same way the reference file's own
# module-level names would be reached, e.g. by Step 2's future registration calls. None until
# build_system() runs - unlike the reference file, importing this module alone constructs nothing.
watchdog: "WDT | None" = None
conn: "AsyConnTime | None" = None
ntp: "AsyNtpClient | None" = None
i2c0: "asy_i2c_driver.I2C | None" = None
i2c1: "asy_i2c_driver.I2C | None" = None
spi0: "asy_spi_driver.SPI | None" = None
fram: "AsyFramManager | None" = None
sysfunct: "SystemService | None" = None
sgp_reader: "SGP40_Reader | None" = None
bmp_reader: "BMP3xx_Reader | None" = None
scd_reader: "SCD30_Reader | None" = None
pixel: "NeopixelDriver | None" = None
notify_service: "NotificationCoordinator | None" = None
timers_running: "ThreadSafeFlag | None" = None


async def sgp_comp_callback() -> "list[float | None]":
    assert scd_reader is not None  # only ever registered on sgp_reader after build_system() runs
    # get_data() never returns None (SCD30_Reader.get_data() -> SCD30) - only its Temp/Hum fields
    # can individually be None (pre-first-read sentinel state); float(None) raises, caught below.
    data = await scd_reader.get_data()
    try:
        return [float(data.Temp), float(data.Hum)]
    except Exception:
        return [None, None]


async def co2_value_callback() -> "int | float | None":
    assert scd_reader is not None  # only ever registered on notify_service after build_system() runs
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.CO2 is None:
        return None
    return float(scd_data.CO2)


async def voc_value_callback() -> "int | float | None":
    assert sgp_reader is not None  # only ever registered on notify_service after build_system() runs
    sgp_data = await sgp_reader.get_data()
    if sgp_data is None or sgp_data.VOC is None:
        return None
    return int(sgp_data.VOC)


async def hum_value_callback() -> "int | float | None":
    assert scd_reader is not None  # only ever registered on notify_service after build_system() runs
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.Hum is None:
        return None
    return float(scd_data.Hum)


def _collect_level_setters() -> "list[Callable[[int], None]]":
    # Every logger in the whole constructed object graph, not just each module's own top-level
    # self.pr - the nested ConfigManager.pr each ConfigManager-backed module owns internally
    # ("CFGMGR_<NAME>"), and AsyConnTime's own separately-named dns_server.pr ("DNSSRV", not
    # covered by conn.pr - see WIRING_CONTRACT.md). Owner requirement: a general, system-wide debug
    # level should actually be system-wide, not miss half the loggers in the system - but each
    # logger's own set_level() (already existing on every PrintLog) is what gets called, not a
    # shared mutable value. Mirrors _collect_task_starters()/_collect_timer_starters()'s own shape:
    # collected once, after every module (including notify_service.finalize()) has fully
    # constructed, then handed to sysfunct.set_level_setters() as a plain list of bound methods.
    assert conn is not None and ntp is not None and fram is not None and sysfunct is not None
    assert sgp_reader is not None and bmp_reader is not None and scd_reader is not None
    assert pixel is not None and notify_service is not None
    return [
        conn.pr.set_level,
        conn.cfgmgr.pr.set_level,
        conn.dns_server.pr.set_level,
        ntp.pr.set_level,
        ntp.cfgmgr.pr.set_level,
        fram.pr.set_level,
        sysfunct.pr.set_level,
        sysfunct.cfgmgr.pr.set_level,
        sgp_reader.pr.set_level,
        sgp_reader.cfgmgr.pr.set_level,
        bmp_reader.pr.set_level,
        bmp_reader.cfgmgr.pr.set_level,
        scd_reader.pr.set_level,  # no cfgmgr - SCD30 has no config schema (params live on-sensor, see CLAUDE.md)
        pixel.pr.set_level,  # no cfgmgr - no config schema (owner-confirmed, see SPECIFICATION.md A.4)
        notify_service.pr.set_level,
        notify_service.cfgmgr.pr.set_level,
    ]


async def build_system(*, cfg_path: str = "", debug: int | None = None) -> None:
    """Construct every module + run the grouped setup() batch. Independently callable/testable -
    no task starting, no infinite loop, always returns. cfg_path lets a caller (a test, or a future
    per-variant build) isolate every ConfigManager-backed module's on-disk config file; defaults to
    "" (the real device filesystem root), matching the reference file's own behavior. debug is each
    module's own construction-time logger level, exactly as before - sysfunct.setup() (in the
    grouped batch below) then pushes the real persisted level out to every logger's own set_level()
    via the registry _collect_level_setters() builds, overriding this initial value.
    """
    global watchdog, conn, ntp, i2c0, i2c1, spi0, fram, sysfunct
    global sgp_reader, bmp_reader, scd_reader, pixel, notify_service, timers_running

    # watchdog: hardcoded at construction time, no injection point - "must be hardcoded so no
    # error ever can circumvent it when it is set active" (owner, FINAL_WIRING_PLAN.md's refined
    # plan).
    watchdog = WDT(timeout=8000)
    conn = AsyConnTime(
        conn_fail_to_hotspot=5,
        hotspot_time_min=8,
        max_module_error=_MAX_MODULE_ERROR,
        cfg_path=cfg_path,
        debug=debug,
    )
    ntp = AsyNtpClient(
        conn.get_wifi_mode_lock(),
        conn.network_available,
        conn.get_dns_server_ip,
        max_module_error=_MAX_MODULE_ERROR,
        dns_timeout_ms=_DNS_TIMEOUT_MS,
        dns_tries=_DNS_TRIES,
        ntp_fetch_timeout_ms=_NTP_FETCH_TIMEOUT_MS,
        cfg_path=cfg_path,
        debug=debug,
    )
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
    i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 1, max_size=0x2000, debug=debug)
    # FRAM chunk 1.
    sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, cfg_path=cfg_path, debug=debug)
    # FRAM chunks 2 (own error log) and 3 (VOC backup) - both allocated inside SGP40_Reader.__init__
    # itself, in that sub-order (WIRING_CONTRACT.md item 8).
    sgp_reader = SGP40_Reader(
        i2c1,
        sgp_comp_callback,
        fram_storage=fram,
        fram_ntp_callback=ntp.ntp_issynced,
        max_module_error=_MAX_MODULE_ERROR,
        cfg_path=cfg_path,
        debug=debug,
    )
    bmp_reader = BMP3xx_Reader(i2c1, max_module_error=_MAX_MODULE_ERROR, cfg_path=cfg_path, debug=debug)
    scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, max_module_error=_MAX_MODULE_ERROR, debug=debug)
    # FRAM chunk 4.
    pixel = NeopixelDriver(15, fram=fram, debug=debug)
    # Staged registration (asy_notification_service.py's own module docstring): construct every
    # NotificationSignal, register() each in the same order the reference file's hardcoded
    # CO2/VOC/Humidity checks ran in (this becomes the poll loop's own deterministic check order),
    # then finalize() exactly once - the one point notify_service.pr/notify_service.cfgmgr actually
    # come into existence (FRAM chunk 5), before its own setup() below or any task starter runs.
    notify_service = NotificationCoordinator(
        pixel.request_signal,
        ntp.cettime,
        max_module_error=_MAX_MODULE_ERROR,
        cfg_path=cfg_path,
        fram=fram,
        debug=debug,
    )
    notify_service.register(NotificationSignal("WarnCO2", co2_value_callback, _FIELD_WARN_CO2, (1, 0, 0)))
    notify_service.register(NotificationSignal("WarnVOC", voc_value_callback, _FIELD_WARN_VOC, (0, 1, 0)))
    notify_service.register(NotificationSignal("WarnHum", hum_value_callback, _FIELD_WARN_HUM, (0, 0, 1)))
    notify_service.finalize()
    conn.set_ext_led(pixel)  # callback for wifi led - after both conn and pixel exist
    timers_running = ThreadSafeFlag()

    sysfunct.set_level_setters(_collect_level_setters())

    # Grouped await x.setup() phase - see this module's own docstring for why batching here
    # (rather than interleaved with construction above) is the one correct ordering, not just a
    # style choice. sysfunct first - resolves the real persisted debug level as early as possible,
    # so every subsequent setup() call's own diagnostic logging already reflects it. Order among
    # the three ConfigManager-domain calls after it matches their own construction order; fram (a
    # different, FRAM-hardware readiness domain entirely) keeps its existing position from the
    # reference file's own async_onetime list.
    await sysfunct.setup()
    await fram.setup()
    await sgp_reader.setup()
    await bmp_reader.setup()
    await notify_service.setup()


def _collect_task_starters() -> "list[Callable[[], asyncio.Task[Any]]]":
    # Every constructed module's own get_task_starters() is the authoritative list for that
    # module (SPECIFICATION.md Part C's driver/service architecture shape) - called uniformly
    # here, not hand-copied from the reference file's own flat list. That distinction is not
    # cosmetic: AsyConnTime.get_task_starters() includes start_hotspot_timeout_watcher, a real task
    # (_watch_hotspot_timeout(), tied to the hotspot_time_min constructor arg passed below) that
    # the reference file's hand-written task_starters list never actually starts - confirmed by
    # direct comparison against asy_wifi_service.py's own get_task_starters(). Flagged to the
    # project owner rather than silently carried forward or silently dropped; calling
    # conn.get_task_starters() here is what actually starts it, a real (believed-correct) behavior
    # change from today's deployed flow, not a mechanical rewrite artifact.
    assert scd_reader is not None and bmp_reader is not None and sgp_reader is not None
    assert pixel is not None and notify_service is not None and sysfunct is not None
    assert conn is not None and ntp is not None
    return (
        scd_reader.get_task_starters()
        + bmp_reader.get_task_starters()
        + sgp_reader.get_task_starters()
        + pixel.get_task_starters()
        + notify_service.get_task_starters()
        + sysfunct.get_task_starters()
        + conn.get_task_starters()
        + ntp.get_task_starters()
    )


def _collect_timer_starters() -> "list[Callable[[], None]]":
    assert scd_reader is not None and bmp_reader is not None and sgp_reader is not None
    assert sysfunct is not None and conn is not None and ntp is not None
    return (
        scd_reader.get_timer_starters()
        + bmp_reader.get_timer_starters()
        + sgp_reader.get_timer_starters()
        + sysfunct.get_timer_starters()
        + conn.get_timer_starters()
        + ntp.get_timer_starters()
    )


async def main(*, cfg_path: str = "", debug: int | None = None) -> None:
    await build_system(cfg_path=cfg_path, debug=debug)
    assert sysfunct is not None and ntp is not None

    task_starters = _collect_task_starters()
    timer_starters = _collect_timer_starters()

    await sysfunct.start_timers(timer_starters)

    # Force an initial sync attempt before the ntp task itself even starts - matches the reference
    # file's own main(): ntp_force_sync() only sets an event flag asy_ntp_time() watches for, so
    # pre-setting it here is equivalent to (and simpler than) waiting for the task to start first.
    await ntp.ntp_force_sync()

    await sysfunct.start_and_check_tasks(task_starters)  # never returns under normal operation
