"""Stage 1 standalone prototype — async-safe rewrite of `improved-quality/sensortask-wozi.py`'s flat, module-level construction sequence. `build_system()` constructs every module as bare module-level globals in the same FRAM-chunk-preserving order, then runs the grouped `await x.setup()` batch; `main()` starts the task/timer supervisor.
Importing this module never blocks — the real "import triggers boot" behavior lives in `boot_entry/wozi_boot.py` instead. See SPECIFICATION.md Part A.7 for the full construction-order/dependency-graph rationale."""

import asyncio
import time
from asyncio import ThreadSafeFlag

# frozen_html: mounts /html on import - see this module's own docstring. frozen_modules/ (built by
# scripts/build_frozen_html.sh, gitignored, never ".frozen" - see that script's own comment) is what
# makes this resolve locally/under test.
import frozen_html  # type: ignore[import-not-found]  # noqa: F401
from machine import WDT

# Vendored ext/microdot.py isn't on this project's mypy search path (mypy_path=["typings","src"]) -
# real device firmware freezes ext/ and src/ flat together, so this resolves fine at runtime; see
# CLAUDE.md's vendoring hard rule and asy_webserver_service.py's own identical import comment.
from microdot import Microdot  # type: ignore[import-not-found]
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
from asy_webserver_service import SettingsGroup, WebserverService
from asy_wifi_service import AsyConnTime
from system_service import SystemService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

# Grouped, generator-fillable constants (owner-confirmed: "keep these variables
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

# Bare module-level globals (owner-confirmed): every
# long-lived object build_system() constructs is reachable the same way the reference file's own
# module-level names would be reached, e.g. by WebserverService's own registration calls. None until
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
webserver: "WebserverService | None" = None
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


def _gmtimestruct_to_dict(t: "Any") -> "dict[str, int] | None":  # t: a GMTimeStruct/8-tuple or None
    if t is None:
        return None
    return {
        "year": t[0],
        "month": t[1],
        "mday": t[2],
        "hour": t[3],
        "minute": t[4],
        "second": t[5],
        "weekday": t[6],
        "yearday": t[7],
    }


async def _system_cmd_callback(cmd: str) -> bool:
    # WebserverService's own _dispatch_system_cmd() already restricts cmd to _SYSTEM_CMDS
    # ("reboot"/"bootloader"/"mempause") before ever calling this - the else branch below is
    # defense-in-depth, not a real reachable case. mempause's duration is the legacy fixed 300s,
    # never client-supplied (see SPECIFICATION.md Part A.8 for the PUT-shape decision).
    assert sysfunct is not None
    if cmd == "reboot":
        sysfunct.reboot_system()
    elif cmd == "bootloader":
        sysfunct.reboot_bootloader()
    elif cmd == "mempause":
        sysfunct.pause_permanent_storage(300)
    else:
        return False
    return True


# r/g/b/t is dispatch-only, not backed by a real ConfigManager - four synthetic FieldSchema
# records (mirroring asy_webserver_service.py's own _PAUSE_TIME_FIELD pattern) so
# type_or_range_error() does both int<->float coercion and range-checking in one step, matching
# legacy's own led_cmd() bounds exactly (modules/sensortask-wozi.py: r/g/b 0-255, t 0.5-60.0).
# The promoted src/ callback used to silently clamp r/g/b (asy_neopixel_driver.py's _clamp_byte())
# and floor/never-bound t instead of rejecting - a "lightCmdLED legacy-vs-src/ divergence" gap,
# now closed.
_FIELD_LED_R: "cm.FieldSchema" = ("r", "int", None, 0, 255, None)
_FIELD_LED_G: "cm.FieldSchema" = ("g", "int", None, 0, 255, None)
_FIELD_LED_B: "cm.FieldSchema" = ("b", "int", None, 0, 255, None)
_FIELD_LED_T: "cm.FieldSchema" = ("t", "float", None, 0.5, 60.0, None)


async def _notification_led_callback(payload: "dict[str, Any]") -> bool:
    # type_or_range_error() coerces (config_manager.py's coerce_numeric() policy - a fractional
    # r/g/b, e.g. 12.5, is rejected rather than silently truncated; an int t coerces to float) and
    # range-checks in one step, rejecting anything outside legacy's own bounds above instead of
    # silently clamping/flooring it (SPECIFICATION.md Part A.8).
    assert pixel is not None
    try:
        r_err, r = cm.type_or_range_error(payload["r"], _FIELD_LED_R)
        g_err, g = cm.type_or_range_error(payload["g"], _FIELD_LED_G)
        b_err, b = cm.type_or_range_error(payload["b"], _FIELD_LED_B)
        t_err, t = cm.type_or_range_error(payload["t"], _FIELD_LED_T)
    except KeyError:
        return False
    if r_err or g_err or b_err or t_err:
        return False
    return await pixel.request_signal(r, g, b, t)


async def _notification_pause_callback(payload: int) -> bool:
    # WebserverService's own _dispatch_notification_pause() already restricts payload to a real int
    # before ever calling this - set_override_led()/LockedCounter.set_value() clamps into
    # [0, _MAX_OVERRIDE_TIME] itself and never raises for a plain int (see asy_notification_service.py).
    assert notify_service is not None
    await notify_service.set_override_led(payload)
    return True


async def _sgp_maintenance_status() -> "dict[str, Any]":
    assert sgp_reader is not None
    backup_ts, restore_ts = await sgp_reader.get_mem_status()
    return {"BackupTS": backup_ts, "RestoreTS": restore_ts}


async def _networking_status() -> "dict[str, Any]":
    assert conn is not None and ntp is not None
    wifi_data = await conn.get_data()
    ifcfg = conn.get_wlan_ifconfig()  # (ip, netmask, gateway, dns) or None
    ntp_data = await ntp.get_data()
    return {
        "WifiUptime": await conn.get_wifi_uptime(),
        "Mode": wifi_data.Mode,
        "Connected": wifi_data.Connected,
        "IP": wifi_data.IP,
        "IPv4": None if ifcfg is None else ifcfg[0],
        "Subnet": None if ifcfg is None else ifcfg[1],
        "Gateway": None if ifcfg is None else ifcfg[2],
        "DNS": None if ifcfg is None else ifcfg[3],
        "Rssi": conn.get_wlan_rssi(),
        "NtpSynced": ntp_data.Synced,
        "NtpLastSyncAge": ntp_data.LastSyncAge,
        "NtpLastSync": ntp_data.TS,
    }


async def _system_status() -> "dict[str, Any]":
    assert sysfunct is not None and ntp is not None and fram is not None
    local_time = await ntp.cettime()
    return {
        "SysUptime": await sysfunct.get_uptime(),
        "BootSignature": await sysfunct.get_boot_signature(),
        "MemPaused": fram.get_pause(),
        "LocalTime": _gmtimestruct_to_dict(local_time),
        "UtcTime": _gmtimestruct_to_dict(time.gmtime()),
    }


async def _notification_status() -> "dict[str, Any]":
    assert notify_service is not None
    data = await notify_service.get_data()
    return {
        "Triggered": data.Triggered,
        "TS": data.TS,
        "PauseTime": await notify_service.get_override_led(),
    }


def _collect_error_sources() -> "list[Any]":
    # Every module + every ConfigManager instance ("CFGMGR_<name>") - same 16-owner enumeration as
    # _collect_level_setters() below (one entry per logger in the whole constructed object graph),
    # just the owning objects themselves rather than their bound set_level() methods. Feeds
    # WebserverService's error_sources= registration list (its /status "errcount" aggregation).
    assert conn is not None and ntp is not None and fram is not None and sysfunct is not None
    assert sgp_reader is not None and bmp_reader is not None and scd_reader is not None
    assert pixel is not None and notify_service is not None
    return [
        conn,
        conn.cfgmgr,
        conn.dns_server,
        ntp,
        ntp.cfgmgr,
        fram,
        sysfunct,
        sysfunct.cfgmgr,
        sgp_reader,
        sgp_reader.cfgmgr,
        bmp_reader,
        bmp_reader.cfgmgr,
        scd_reader,
        pixel,
        notify_service,
        notify_service.cfgmgr,
    ]


def _collect_level_setters() -> "list[Callable[[int], None]]":
    # Every logger in the whole constructed object graph, not just each module's own top-level
    # self.pr - the nested ConfigManager.pr each ConfigManager-backed module owns internally
    # ("CFGMGR_<NAME>"), and AsyConnTime's own separately-named dns_server.pr ("DNSSRV", not
    # covered by conn.pr - see SPECIFICATION.md Part A.7). Owner requirement: a general, system-wide debug
    # level should actually be system-wide, not miss half the loggers in the system - but each
    # logger's own set_level() (already existing on every PrintLog) is what gets called, not a
    # shared mutable value. Mirrors _collect_task_starters()/_collect_timer_starters()'s own shape:
    # collected once, after every module (including notify_service.finalize()) has fully
    # constructed, then handed to sysfunct.set_level_setters() as a plain list of bound methods.
    assert conn is not None and ntp is not None and fram is not None and sysfunct is not None
    assert sgp_reader is not None and bmp_reader is not None and scd_reader is not None
    assert pixel is not None and notify_service is not None and webserver is not None
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
        webserver.pr.set_level,  # no cfgmgr - no config schema (own safety constants only, see BACKLOG.md)
    ]


async def build_system(
    *, cfg_path: str = "", debug: int | None = None, web_host: str = "0.0.0.0", web_port: int = 80
) -> None:
    """Construct every module and run the grouped `setup()` batch; independently callable/testable — no task starting, no infinite loop, always returns.
    `cfg_path` isolates on-disk config files (e.g. for tests); `web_host`/`web_port` override the real `0.0.0.0`/`80` production default. See SPECIFICATION.md Part A.7 for the full construction order."""
    global watchdog, conn, ntp, i2c0, i2c1, spi0, fram, sysfunct
    global sgp_reader, bmp_reader, scd_reader, pixel, notify_service, webserver, timers_running

    # watchdog: hardcoded at construction time, no injection point - "must be hardcoded so no
    # error ever can circumvent it when it is set active" (owner, refined
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
    # i2c0 carries SCD30 (below): datasheets/scd30/..._Interface_Description.pdf p.2 - max 100kHz,
    # Sensirion recommends <=50kHz (matched by frequency=50000); clock stretching is normally
    # <=30ms but can reach 150ms once/day for internal calibration, well past rp2's own I2C
    # timeout default (DEFAULT_I2C_TIMEOUT, ports/rp2/machine_i2c.c, 50ms) - timeout=200000 (200ms)
    # keeps that expected once-daily stretch from surfacing as a spurious OSError.
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000, timeout=200000)
    i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 1, max_size=0x2000, debug=debug)
    # FRAM chunk 1.
    sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, cfg_path=cfg_path, debug=debug)
    # FRAM chunks 2 (own error log) and 3 (VOC backup) - both allocated inside SGP40_Reader.__init__
    # itself, in that sub-order (see SPECIFICATION.md Part A.7 for the full FRAM chunk order).
    sgp_reader = SGP40_Reader(
        i2c1,
        sgp_comp_callback,
        fram_storage=fram,
        fram_ntp_callback=ntp.ntp_issynced,
        max_module_error=_MAX_MODULE_ERROR,
        cfg_path=cfg_path,
        debug=debug,
    )
    # FRAM chunk 4.
    bmp_reader = BMP3xx_Reader(i2c1, max_module_error=_MAX_MODULE_ERROR, cfg_path=cfg_path, fram=fram, debug=debug)
    # FRAM chunk 5.
    scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, max_module_error=_MAX_MODULE_ERROR, fram=fram, debug=debug)
    # FRAM chunk 6.
    pixel = NeopixelDriver(15, fram=fram, debug=debug)
    # Staged registration (asy_notification_service.py's own module docstring): construct every
    # NotificationSignal, register() each in the same order the reference file's hardcoded
    # CO2/VOC/Humidity checks ran in (this becomes the poll loop's own deterministic check order),
    # then finalize() exactly once - the one point notify_service.pr/notify_service.cfgmgr actually
    # come into existence (FRAM chunk 7), before its own setup() below or any task starter runs.
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

    # Registration-based Microdot REST/API service - built here,
    # after every module it registers exists, exactly like conn.set_ext_led()'s own cross-wiring
    # just above. "No Microdot, no routes" was Step 1's own scoping (deliberately excluded then,
    # reference-only in improved-quality/sensortask-wozi.py); this is Step 2's real replacement.
    app = Microdot()
    webserver = WebserverService(
        app,
        # Deliberately no fram= here (stays a plain in-RAM PrintLog, not FRAM-backed) - unlike every
        # other FRAM-chunk-owning module above, this one logs a warning on *every* per-call/outer-cap
        # connection reclaim (BACKLOG.md's decision 8), a rate a hostile or merely flaky client could
        # drive far higher than any sensor's rare-hardware-fault error log ever does; persisting that
        # to FRAM would risk real wear-leveling pressure this module's own diagnostics don't need to
        # survive a reboot to be useful. Keeps the seven-chunk FRAM allocation order (see
        # SPECIFICATION.md Part A.7) exactly as documented - this module allocates no FRAM chunk at all.
        sensors=(scd_reader, bmp_reader, sgp_reader),  # type: ignore[arg-type]  # structurally
        # _ModuleLike-shaped (SensorReader/SensorReaderConfig subclasses) - _ModuleLike is a
        # narrower Protocol defined in asy_webserver_service.py, not importable here without a real
        # coupling to that module's private type; same treatment as that module's own
        # _apply_settings_groups() uses for group.module, applied at every call site below too.
        settings={
            "networking": [
                # Mirrors the legacy setNetwork/setWiFiLED field-scoping split (tests/
                # test_setter_microdot_integration.py's own _wifi_field_schema() precedent) - LedWifiOn
                # gets its own group with no post_fct, so toggling it alone never reconnects WiFi.
                SettingsGroup(conn, ("SSID", "PW", "Country", "Hostname"), post_fct=conn.reconnect_wifi),  # type: ignore[arg-type]
                SettingsGroup(conn, ("LedWifiOn",)),  # type: ignore[arg-type]
                SettingsGroup(ntp, ("NTP_Host", "NTP_Offset_S", "NTP_Interv_H"), post_asy_fct=ntp.ntp_force_sync),  # type: ignore[arg-type]
            ],
            "system": [
                SettingsGroup(sysfunct, ("DebugLevel",)),  # type: ignore[arg-type]
                SettingsGroup(ntp, ("GMTOffset", "DSTOffset")),  # type: ignore[arg-type]  # cettime() reads these live - no post hook needed
            ],
            "notification": [
                # notify_service.get_cfg_schema() is the full combined schema (own fields + every
                # registered NotificationSignal's field, e.g. WarnCO2/WarnVOC/WarnHum) - read
                # dynamically rather than hardcoded, so a future registered signal's field is
                # automatically PUT-able through /notification without an unrelated edit here.
                SettingsGroup(notify_service, cm.schema_names(notify_service.get_cfg_schema())),  # type: ignore[arg-type]
            ],
        },
        system_cmd=_system_cmd_callback,
        notification_led=_notification_led_callback,
        notification_pause=_notification_pause_callback,
        status_sources={
            "networking": _networking_status,
            "system": _system_status,
            "notification": _notification_status,
        },
        maintenance_sensors=(("SGP40", _sgp_maintenance_status),),
        error_sources=_collect_error_sources(),
        debug=debug,
        static_mount="/html",  # see SPECIFICATION.md Part A.9 - matches frozen_html's own
        # freezefs `--target /html` (see scripts/build_frozen_html.sh), mounted as a side effect of
        # this module's own top-level `import frozen_html` above.
        is_hotspot_active=conn.is_hotspot_active,  # captive-portal redirect fallback - see
        # CAPTIVE_PORTAL_HOTSPOT_REDIRECT_PLAN.md and asy_webserver_service.py's own _serve_static().
        host=web_host,
        port=web_port,
    )

    timers_running = ThreadSafeFlag()

    sysfunct.set_level_setters(_collect_level_setters())

    # Grouped await x.setup() phase - see this module's own docstring for why batching here
    # (rather than interleaved with construction above) is the one correct ordering, not just a
    # style choice. sysfunct first - resolves the real persisted debug level as early as possible,
    # so every subsequent setup() call's own diagnostic logging already reflects it. Order among
    # the ConfigManager-domain calls after it matches their own construction order (conn/ntp were
    # both built before fram/sysfunct - the seven-chunk FRAM order (SPECIFICATION.md Part A.7) is about FRAM
    # *chunk allocation* order specifically, unrelated to this ConfigManager-only setup() ordering);
    # fram (a different, FRAM-hardware readiness domain entirely) keeps its existing position from
    # the reference file's own async_onetime list.
    #
    # conn.setup()/ntp.setup() are a real gap fix, not part of Step 1's original three (sgp/bmp/
    # notify) - found directly while wiring Step 2's /networking and /system PUT routes to the real
    # conn/ntp objects: AsyConnTime/AsyNtpClient are SensorReaderConfig subclasses under the exact
    # same sync-__init__/async-setup() pattern (SPECIFICATION.md Part C.13) as sgp/bmp/notify, but
    # nothing anywhere in the previously-constructed system ever called their own cfgmgr.setup() -
    # confirmed directly: without it, conn.cfgmgr.valid stays False forever, so every write to
    # conn's/ntp's config fails with "Failed" (ConfigManager.write_config()'s own "not self.valid"
    # guard), and every read returns None. Neither asy_wifi_service.py's wlan_connect() nor
    # asy_ntp_client.py's own task methods ever call cfgmgr.setup() internally either - this was
    # already a real hole in Step 1's construction sequence, just never exercised by a real
    # config-write path before this session's webserver wiring.
    await sysfunct.setup()
    await fram.setup()
    await conn.setup()
    await ntp.setup()
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
    assert conn is not None and ntp is not None and webserver is not None
    return (
        scd_reader.get_task_starters()
        + bmp_reader.get_task_starters()
        + sgp_reader.get_task_starters()
        + pixel.get_task_starters()
        + notify_service.get_task_starters()
        + sysfunct.get_task_starters()
        + conn.get_task_starters()
        + ntp.get_task_starters()
        + webserver.get_task_starters()  # the webserver's own task, registered as an ordinary task
        # in start_and_check_tasks() like every other module (see SPECIFICATION.md Part A.7
        # - no bespoke whole-server-restart mechanism).
    )


def _collect_timer_starters() -> "list[Callable[[], None]]":
    # Every constructed module's own get_timer_starters() is called uniformly, matching
    # _collect_task_starters()'s own already-uniform pattern above (SPECIFICATION.md Part C.9:
    # "system_service.py's start_and_check_tasks()/start_timers() discover and supervise every
    # driver generically through these, never by name"). pixel/notify_service/webserver all
    # currently return [] here (no machine.Timer in any of the three - each file's own
    # get_timer_starters() docstring says so explicitly, "kept empty rather than omitted so
    # callers can treat every driver uniformly"), so previously omitting them was a
    # behavior-invisible gap today - but a silent one: a future Timer added to any of those three
    # would never actually get started, since this collector picked modules by name instead of
    # calling every constructed module the same way get_task_starters() already does (Step 7
    # second-pass audit finding).
    assert scd_reader is not None and bmp_reader is not None and sgp_reader is not None
    assert pixel is not None and notify_service is not None and sysfunct is not None
    assert conn is not None and ntp is not None and webserver is not None
    return (
        scd_reader.get_timer_starters()
        + bmp_reader.get_timer_starters()
        + sgp_reader.get_timer_starters()
        + pixel.get_timer_starters()
        + notify_service.get_timer_starters()
        + sysfunct.get_timer_starters()
        + conn.get_timer_starters()
        + ntp.get_timer_starters()
        + webserver.get_timer_starters()
    )


async def main(*, cfg_path: str = "", debug: int | None = None, web_host: str = "0.0.0.0", web_port: int = 80) -> None:
    await build_system(cfg_path=cfg_path, debug=debug, web_host=web_host, web_port=web_port)
    assert sysfunct is not None and ntp is not None

    task_starters = _collect_task_starters()
    timer_starters = _collect_timer_starters()

    await sysfunct.start_timers(timer_starters)

    # Force an initial sync attempt before the ntp task itself even starts - matches the reference
    # file's own main(): ntp_force_sync() only sets an event flag asy_ntp_time() watches for, so
    # pre-setting it here is equivalent to (and simpler than) waiting for the task to start first.
    await ntp.ntp_force_sync()

    await sysfunct.start_and_check_tasks(task_starters)  # never returns under normal operation
