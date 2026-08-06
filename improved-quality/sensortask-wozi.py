import frozen_html  # type: ignore[import-not-found] # noqa: F401
import time
import asyncio
from uasyncio import ThreadSafeFlag
from system_service import SystemService
import asy_i2c_driver
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_bmp3xx_driver import BMP3xx_Reader
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_wifi_service import asy_conn_time
from asy_ntp_client import asy_ntp_client
from microdot import Microdot, send_file, Request, Response
from machine import Timer, WDT
from micropython import const
import api_response as ar
import config_manager as cm
from typing import Any, Callable, Coroutine, Dict, List, Tuple

_MAX_I2C_ERR = const(5)
_FRAM_PAUSE_SEC = const(300)  # 5min communication pause for FRAM

# api_helpers.py migration (2026-08-04, owner-authorized scoped exception to the usual
# "don't edit improved-quality/ source" rule - this file was its last remaining importer): every
# route below now goes through api_response.py's parse_cmd_request()/handle_set_cmd()/
# make_response(), or - for fields with no SensorReaderConfig-backed schema at all (SCD30's own
# hand-rolled setters, the LED-only/system-only commands below that never persisted anything to
# begin with) - a small local per-field cm.type_or_range_error() check, matching the same result
# shape without needing base_classes.py's full push-dispatch machinery where it was never used.
#
# One real bug surfaced and fixed along the way, not just a mechanical import removal: the old
# residual "system-level config" schema below (_VAL_SGP_SYS_FIELDS/_VAL_BMP_SYS_FIELDS, config_
# SYSTEM.cfg) was a SEPARATE, PARALLEL config file from sgp_reader's/bmp_reader's own real
# config_SGP40.cfg/config_BMP3XX.cfg - the setSGP/setBMP handlers below persisted into the former,
# but neither promoted driver's actual internal logic ever reads from it (each reads only its own
# cfgmgr - see asy_sgp40_driver.py's/asy_bmp3xx_driver.py's own __init__/_setup()), so a REST client
# setting these fields never actually changed real sensor behavior, only a dead, disconnected copy
# of the same-named settings with even different defaults from the real ones. The migration below
# routes these fields directly through sgp_reader.get_cfg_schema()/bmp_reader.get_cfg_schema()
# instead, which fixes this disconnect as a direct consequence (writes now reach the config file
# each driver's own logic actually reads) - see BACKLOG.md for the full writeup. The now-fully-
# superseded _VAL_SGP_SYS_FIELDS/_VAL_BMP_SYS_FIELDS/_VAL_SYSTEM_FIELDS consts and the standalone
# config_SYSTEM.cfg-backed `cfgmgr` are removed entirely - nothing else in this file used them.
#
# Two consequences worth knowing (both deliberate, matching already-settled decisions elsewhere in
# this same refactor, not new policy calls): (1) the wire field names for setSGP/setBMP drop their
# "SGP"/"BMP" prefix to match each driver's own real schema field names directly (e.g.
# "BackupPeriod" not "SGPBackupPeriod") - the endpoint itself is already scoped by command name, so
# the prefix was redundant; (2) setBMP's PressOvers/TempOvers/FiltCoeff now take the raw
# multiplier/coefficient value on the wire, not the legacy 0-5/0-7 index - already the owner-
# confirmed, settled wire format for these fields (see BACKLOG.md's "raw value" item), just not
# previously reachable through this specific route. Every bool-typed field project-wide (LedWifiOn,
# SelfCal, SGPResetVOC, ContMeas, and this file's own Error_Status/Synced status fields) is native
# JSON true/false end to end now too, completing the same already-settled convention (legacy's
# "switch"/"On"/"Off" string dtype has no equivalent anywhere in config_manager.py and needs none).
# The HTML/JS frontend is unchanged by this pass (known brittle, explicitly deferred - see
# BACKLOG.md) and will need matching updates whenever it's next touched.


async def sgp_comp_callback() -> List[float | None]:
    data = await scd_reader.get_data()
    if data is None:
        return [None, None]
    try:
        return [float(data.Temp), float(data.Hum)]
    except:
        return [None, None]


async def co2_value_callback() -> int | float | None:
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.CO2 is None:
        return None
    return float(scd_data.CO2)


async def voc_value_callback() -> int | float | None:
    sgp_data = await sgp_reader.get_data()
    if sgp_data is None or sgp_data.VOC is None:
        return None
    return int(sgp_data.VOC)


async def hum_value_callback() -> int | float | None:
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.Hum is None:
        return None
    return float(scd_data.Hum)


debug = False
watchdog = WDT(timeout=8000)
# None of the promoted sensor Readers or asy_conn_time contribute to a shared config.json anymore -
# see BACKLOG.md's sensortask-wozi.py integration notes:
# - SGP40_Reader/BMP3xx_Reader (src/asy_sgp40_driver.py, src/asy_bmp3xx_driver.py) each own a
#   private per-sensor config_<NAME>.cfg file via base_classes.py's SensorReaderConfig, and no
#   longer expose a get_default_cfg() classmethod.
# - SCD30_Reader (src/asy_scd30_driver.py) has no local config file at all - its params live
#   on-sensor - so it never had a get_default_cfg() to call in the first place.
# - asy_conn_time (asy_wifi_service.py, promoted) now owns its own config_WIFI.cfg internally
#   (base_classes.py's SensorReaderConfig, same as asy_ntp_client below) - no more
#   externally-injected cfgmgr, no more get_default_cfg()/_DEFAULT_CONFIG merge step. Every REST
#   route below that reads or writes a WIFI-schema field (Country/Hostname/SSID/PW/LedWifiOn) goes
#   through conn.cfgmgr, not a shared cfgmgr - see BACKLOG.md for the full writeup.
# - Neopixel_Signal (neopixel_signal.py) is now split into two promoted src/ files (see CLAUDE.md/
#   BACKLOG.md): asy_neopixel_driver.py's NeopixelDriver (pure LED hardware - overlay, dimmed ramp
#   signal, request_signal()/led_signal() arbitration; deliberately has no config schema of its own,
#   confirmed by the project owner - neopixel_pin/neopixel_freq/led_overl_bri stay plain constructor
#   args) and asy_notification_service.py's NotificationCoordinator (generic threshold-triggered
#   signalling, owns its own config_NOTIFY.cfg via staged registration - see that module's own
#   docstring). Every REST route below that reads or writes an Auto*/Warn* field now goes through
#   notify_service.cfgmgr, not pixel.cfgmgr - field names drop the "Led" prefix as a deliberate
#   wire-format change (WarnCO2 not LedWarnCO2; the frontend isn't updated to match yet, see
#   BACKLOG.md). NTP_Host/NTP_Offset_S/NTP_Interv_H/GMTOffset/DSTOffset already live on ntp.cfgmgr
#   (asy_ntp_client.py's own schema) - /time/* below goes through that, not a shared one.
conn = asy_conn_time(conn_fail_to_hotspot=5, hotspot_time_min=8, max_i2c_err=_MAX_I2C_ERR, debug=debug)
# max_i2c_err: consecutive-failure-streak threshold, not literally about I2C - conn/ntp neither have
# an I2C bus, they just inherit this generically-named base_classes.py parameter (see BACKLOG.md).
# TODO: rename it project-wide to something bus-agnostic in a later, separate pass.
# The leaf timeouts asy_ntp_client forwards to its own async DNS lookup/NTP fetch are set here, the
# one place this class is instantiated - see BACKLOG.md's timing-restructure writeup for why these
# (and not a hidden module constant, and not any computation inside asy_ntp_client.py itself) are
# the only place a real device's timing behavior actually gets decided.
_DNS_TIMEOUT_MS = const(500)  # per-server, per-attempt DNS lookup budget
_DNS_TRIES = const(1)  # retry budget per DNS server
_NTP_FETCH_TIMEOUT_MS = const(5000)  # timeout for the actual NTP request/reply round trip
ntp = asy_ntp_client(
    conn.get_wifi_mode_lock(),
    conn.network_available,
    conn.get_dns_server_ip,
    max_i2c_err=_MAX_I2C_ERR,
    dns_timeout_ms=_DNS_TIMEOUT_MS,
    dns_tries=_DNS_TRIES,
    ntp_fetch_timeout_ms=_NTP_FETCH_TIMEOUT_MS,
    debug=debug,
)
app = Microdot()  # type: ignore[no-untyped-call]
i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)
spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
fram = AsyFramManager(spi0, 1, max_size=0x2000, debug=debug)
sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, debug=debug)
# fram_storage/fram_ntp_callback replace the old ts_storage= kwarg - SGP40_Reader now carves its
# own timestamped FRAM chunk internally (VOCAlgorithm.get_params_memsize(), not a class method on
# SGP40_Reader itself anymore) instead of taking a pre-built chunk from the caller. ntp_issynced now
# lives on the promoted asy_ntp_client (ntp), not asy_conn_time (conn) - see BACKLOG.md's
# sensortask-wozi.py integration notes.
sgp_reader = SGP40_Reader(
    i2c1,
    sgp_comp_callback,
    fram_storage=fram,
    fram_ntp_callback=ntp.ntp_issynced,
    max_i2c_err=_MAX_I2C_ERR,
    debug=debug,
)
# address defaults to 0x77 (Sparkfun breakout's SDO-high default) - unlike SCD30_Reader/
# SGP40_Reader's cfgmgr callback-based config, BMP3xx_Reader owns its own ConfigManager
# internally (base_classes.py's SensorReaderConfig), so the system cfgmgr isn't passed here.
bmp_reader = BMP3xx_Reader(i2c1, max_i2c_err=_MAX_I2C_ERR, debug=debug)
scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, max_i2c_err=_MAX_I2C_ERR, debug=debug)
pixel = NeopixelDriver(15, fram=fram, debug=debug)
# Staged registration (see asy_notification_service.py's own module docstring): construct every
# NotificationSignal, register() each in the same order the original file's hardcoded
# CO2/VOC/Humidity if-blocks checked them in (this becomes the poll loop's own deterministic check
# order), then finalize() exactly once - the one point notify_service.pr/notify_service.cfgmgr
# actually come into existence - before get_task_starters() is ever called on it below.
notify_service = NotificationCoordinator(
    pixel.request_signal,
    ntp.cettime,
    max_i2c_err=_MAX_I2C_ERR,
    fram=fram,
    debug=debug,
)
_FIELD_WARN_CO2: "cm.ConfigSchema" = (("WarnCO2", "int", 1600, 0, 3000, None),)
_FIELD_WARN_VOC: "cm.ConfigSchema" = (("WarnVOC", "int", 350, 0, 500, None),)
_FIELD_WARN_HUM: "cm.ConfigSchema" = (("WarnHum", "float", 65.0, 0.0, 100.0, None),)
notify_service.register(NotificationSignal("WarnCO2", co2_value_callback, _FIELD_WARN_CO2, (1, 0, 0)))
notify_service.register(NotificationSignal("WarnVOC", voc_value_callback, _FIELD_WARN_VOC, (0, 1, 0)))
notify_service.register(NotificationSignal("WarnHum", hum_value_callback, _FIELD_WARN_HUM, (0, 0, 1)))
notify_service.finalize()
conn.set_ext_led(pixel)  # callback for wifi led
timers_running = ThreadSafeFlag()


# *** api_helpers.py replacement helpers ***
# Fields below have no SensorReaderConfig-backed schema/cfgmgr of their own (SCD30's own hand-rolled
# setters; LED-only/system-only commands that never persisted anything) - validated directly against
# a local FieldSchema tuple via cm.type_or_range_error(), the same primitive base_classes.py's own
# push-dispatch mechanism uses internally, without needing the rest of that machinery.
_FIELD_SCD_TEMP_OFFS: "cm.FieldSchema" = ("TempOffs", "float", 0.0, 0.0, 655.35, None)
_FIELD_SCD_MEAS_INT: "cm.FieldSchema" = ("MeasInt", "int", 2, 2, 1800, None)
# special=0: matches SCD30's own documented AmbPres=0 "disable compensation" convention (see
# CLAUDE.md) - a bypass value outside the ordinary 700-1400 hPa range.
_FIELD_SCD_AMB_PRES: "cm.FieldSchema" = ("AmbPres", "int", 0, 700, 1400, 0)
_FIELD_SCD_ALTITUDE: "cm.FieldSchema" = ("Altitude", "int", 0, 0, 65535, None)
_FIELD_SCD_FORCE_CAL_REF: "cm.FieldSchema" = ("ForceCalRef", "int", 400, 400, 2000, None)
_FIELD_SCD_SELF_CAL: "cm.FieldSchema" = ("SelfCal", "bool", False, None, None, None)
_FIELD_SCD_CONT_MEAS: "cm.FieldSchema" = ("ContMeas", "bool", True, None, None, None)

# ContMeas=True (matches _FIELD_SCD_CONT_MEAS's own default - "keep measuring") is a legitimate,
# already-tested no-op: scd_reader.stop_continuous_measurement()'s own documented contract returns
# False for it, meaning "nothing to do", not "failed" (see test_reader_stop_continuous_measurement_
# true_is_a_pure_noop in tests/test_asy_scd30_driver.py) - only a real stop attempt (value=False)
# can genuinely fail (a bus fault) and must still surface as such. _scd_apply_field() below has no
# way to know this per-field nuance on its own (it just does "Valid" if applied else "Failed"), so
# this thin wrapper normalizes the no-op case to True before that generic check ever sees it -
# mirrors the identical bug already fixed in asy_sgp40_driver.py's _push_reset_voc for the exact
# same reason (a setter's own True=applied/False=no-op contract must not be forwarded as a push-
# success/failure signal without this normalization). Legacy's set_sensor_value() never hit this:
# it only checked whether the setter call raised, never inspected a return value.
async def _push_cont_meas(value: bool) -> bool:
    if value:
        await scd_reader.stop_continuous_measurement(True)
        return True
    return await scd_reader.stop_continuous_measurement(False)


# (key, field, setter) - iterated in the same order the old handler validated them in. Every SCD30
# setter already never raises and self-logs via its own self.pr (see asy_scd30_driver.py's own
# module docstring/DRIVER_SPEC.md section 7) - the try/except below is defense-in-depth against a
# future change to that contract, matching every other caller-supplied-callback call site in this
# codebase (e.g. base_classes.py's own _push_callbacks dispatch).
_SCD_SET_FIELDS: "Tuple[Tuple[str, cm.FieldSchema, Callable[[Any], Coroutine[Any, Any, bool]]], ...]" = (
    ("TempOffs", _FIELD_SCD_TEMP_OFFS, scd_reader.set_temperature_offset),
    ("MeasInt", _FIELD_SCD_MEAS_INT, scd_reader.set_measurement_interval),
    ("AmbPres", _FIELD_SCD_AMB_PRES, scd_reader.set_ambient_pressure),
    ("Altitude", _FIELD_SCD_ALTITUDE, scd_reader.set_altitude),
    ("ForceCalRef", _FIELD_SCD_FORCE_CAL_REF, scd_reader.set_forced_recalibration_reference),
    ("SelfCal", _FIELD_SCD_SELF_CAL, scd_reader.set_self_calibration_enabled),
    ("ContMeas", _FIELD_SCD_CONT_MEAS, _push_cont_meas),
)


async def _scd_apply_field(data: Dict[str, Any], key: str, field: "cm.FieldSchema", setter: Callable[[Any], Coroutine[Any, Any, bool]]) -> str | None:
    # None means "not requested" - matches the project-wide omitted-key convention (see BACKLOG.md's
    # "Settled" item on this), unlike this file's own lightCmdLED/pauseAutoLED commands below, which
    # are genuinely single-shot commands rather than a partial config update.
    if key not in data:
        return None
    value = data[key]
    if cm.type_or_range_error(value, field):
        return "Invalid"
    try:
        applied = await setter(value)
    except Exception as e:  # setter is caller-supplied; its runtime behavior isn't statically known
        await scd_reader.pr.err_s("Error setting", key, "on SCD30:", e, errno=30)
        applied = False
    return "Valid" if applied else "Failed"


def _cfg_subset(schema: "cm.ConfigSchema", keys: "Tuple[str, ...]") -> "cm.ConfigSchema":
    # asy_conn_time (conn) owns exactly one schema/cfgmgr for all of SSID/PW/Country/Hostname/
    # LedWifiOn, but /net/cmd's setNetwork and /led/cmd's setWiFiLED are two separate routes that
    # each only own a subset of those fields (matches the legacy handler's own scoping - see
    # modules/sensortask-wozi.py's setNetwork/setWiFiLED, each of which only ever touched its own
    # named subset of cfgmgr's keys). Passing conn.get_cfg_schema() (the whole thing) to both routes
    # would let setNetwork accept/persist LedWifiOn (and spuriously fire reconnect_wifi() for an
    # LED-only change) and let setWiFiLED silently accept/persist SSID/PW/Country/Hostname with no
    # reconnect at all - this narrows each route back to its own real field subset, the same way
    # ConfigManager.write_config()'s own per-key "not found, skipping" handles a genuinely unknown
    # key: a field outside `keys` is reported "Invalid" for that route, never silently applied.
    fields = cm.schema_dict(schema)
    return tuple(fields[k] for k in keys if k in fields)


def _time_to_dict(gmt_raw: "Tuple[int, ...] | None") -> Dict[str, int | float | str | None]:
    # Relocated verbatim from the now-removed api_helpers.py's own time_to_dict().
    timedict: Dict[str, int | float | str | None] = {
        "Year": None,
        "Month": None,
        "Day": None,
        "Hour": None,
        "Min": None,
        "Sec": None,
    }
    if gmt_raw is None:
        return timedict
    # time.gmtime()-shaped tuples are 8 elements on the real rp2 target or 9 elements on this
    # project's Unix-port test interpreter (trailing isdst=0) - accept either shape; only indices
    # 0-5 (year..sec) are ever read below, regardless of which shape was passed in.
    gmt: "Tuple[int, ...] | None" = gmt_raw if len(gmt_raw) in (8, 9) else None
    if gmt is not None:
        timedict["Year"] = gmt[0]
        timedict["Month"] = gmt[1]
        timedict["Day"] = gmt[2]
        timedict["Hour"] = gmt[3]
        timedict["Min"] = gmt[4]
        timedict["Sec"] = gmt[5]
    return timedict


def start_asy_webserver() -> asyncio.Task[None]:
    evtloop = asyncio.get_event_loop()
    return evtloop.create_task(app.start_server(port=80, debug=debug))  # type: ignore[no-any-return, no-untyped-call]

# *** WEBSERVER ***
# HTML pages
@app.get("/")  # type: ignore[no-untyped-call, misc]
async def root_dir(request: Request) -> Response:
    return send_file("html/index.html", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/index.html")  # type: ignore[no-untyped-call, misc]
async def index(request: Request) -> Response:
    return send_file("html/index.html", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/favicon.ico")  # type: ignore[no-untyped-call, misc]
async def favicon(request: Request) -> Response:
    return send_file("html/favicon.ico", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/nettimeconfig.html")  # type: ignore[no-untyped-call, misc]
async def nettimecfg(request: Request) -> Response:
    return send_file("html/nettimeconfig.html", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/sensorconfig.html")  # type: ignore[no-untyped-call, misc]
async def sensorcfg(request: Request) -> Response:
    return send_file("html/sensorconfig.html", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/systemledconfig.html")  # type: ignore[no-untyped-call, misc]
async def systempage(request: Request) -> Response:
    return send_file("html/systemledconfig.html", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/style.css")  # type: ignore[no-untyped-call, misc]
async def cssconf(request: Request) -> Response:
    return send_file("html/style.css", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


@app.get("/functions.js")  # type: ignore[no-untyped-call, misc]
async def javascript(request: Request) -> Response:
    return send_file("html/functions.js", compressed=True, file_extension=".gz")  # type: ignore[no-any-return, no-untyped-call]


# Networking API
@app.get("/net/status")  # type: ignore[no-untyped-call, misc]
async def network_status(request: Request) -> Dict[str, int | float | str | None]:
    net_data: Dict[str, int | float | str | None] = {
        "IPv4": None,
        "Subnet": None,
        "Gateway": None,
        "DNS": None,
        "Rssi": "---",
    }
    net_config = conn.get_wlan_ifconfig()
    if net_config is not None:
        net_data["IPv4"] = net_config[0]
        net_data["Subnet"] = net_config[1]
        net_data["Gateway"] = net_config[2]
        net_data["DNS"] = net_config[3]
    rssi = conn.get_wlan_rssi()
    if rssi is not None:
        net_data["Rssi"] = rssi
    return net_data


@app.get("/net/config")  # type: ignore[no-untyped-call, misc]
async def network_config(request: Request) -> Dict[str, int | float | str | bool | None] | None:
    cfg_data = await conn.cfgmgr.get_dict(["Country", "Hostname", "SSID"])
    if cfg_data is not None:
        cfg_data["PW"] = "********"
    # else: TODO Create full dict if None! Falls through and returns None below for now, matching
    # /led/config's and /time/config's own "let it be None" convention elsewhere in this file - the
    # previous `cfg_data["PW"] = None` here crashed with a real TypeError on this branch (assigning
    # into a None object), reachable whenever conn.cfgmgr.valid is False (e.g. a corrupted
    # config_WIFI.cfg), not just a hypothetical.
    return cfg_data


@app.put("/net/cmd")  # type: ignore[no-untyped-call, misc]
async def network_cmd(request: Request) -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setNetwork"])
    if err is not None:
        return err
    assert data is not None
    if debug:
        print("Received Set Network command.")
    # SSID's own min length is 0 here (asy_wifi_service.py's real _VAL_SSID), not the legacy
    # handler's own 2 - a small, pre-existing divergence between this route's old hand-rolled check
    # and the schema this route now defers to entirely; flagged in BACKLOG.md, not silently changed
    # back, since asy_wifi_service.py's schema is the intended single source of truth going forward.
    #
    # Scoped to SSID/PW/Country/Hostname only (see _cfg_subset's own comment) - matches legacy's own
    # setNetwork scoping; LedWifiOn lives in this same cfgmgr but belongs to /led/cmd's setWiFiLED
    # below, not here.
    fields = {k: v for k, v in data.items() if k != "cmd"}
    return await ar.handle_set_cmd(
        conn, fields, _cfg_subset(conn.get_cfg_schema(), ("SSID", "PW", "Country", "Hostname")), post_fct=conn.reconnect_wifi
    )  # Reconnect WiFi with new config (has 5 sec delay)


# Timing API
@app.get("/time/status")  # type: ignore[no-untyped-call, misc]
async def timing_status(
    request: Request,
) -> Dict[str, Dict[str, int | float | str | bool | None]]:
    synced = await ntp.ntp_issynced()
    gmt = time.gmtime()
    system: Dict[str, int | float | str | bool | None] = {
        "Synced": synced,
        "Unix": time.mktime(gmt),  # type: ignore[call-arg]
    }
    utc = _time_to_dict(gmt)
    local = _time_to_dict(await ntp.cettime())

    rtc_time = {"System": system, "UTC": utc, "Local": local}
    return rtc_time


@app.get("/time/config")  # type: ignore[no-untyped-call, misc]
async def timing_config(request: Request) -> Dict[str, int | float | str | bool | None] | None:
    ntp_data = await ntp.cfgmgr.get_dict(
        ["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"]
    )
    # TODO what if ntp_data is None
    return ntp_data


@app.put("/time/cmd")  # type: ignore[no-untyped-call, misc]
async def timing_cmd(request: Request) -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setTiming"])
    if err is not None:
        return err
    assert data is not None
    if debug:
        print("Received Set Timing command.")
    fields = {k: v for k, v in data.items() if k != "cmd"}
    return await ar.handle_set_cmd(
        ntp, fields, ntp.get_cfg_schema(), post_asy_fct=ntp.ntp_force_sync
    )  # resync NTP with new config


# Sensors API
@app.get("/sensors/status")  # type: ignore[no-untyped-call, misc]
async def sensor_status(request: Request) -> Dict[str, Dict[str, int | float | str | None]]:
    scd_meas = await scd_reader.get_dict_data()
    sgp_meas = await sgp_reader.get_dict_data()
    bmp_meas = await bmp_reader.get_dict_data()
    return scd_meas | sgp_meas | bmp_meas


@app.get("/sensors/config")  # type: ignore[no-untyped-call, misc]
async def sensor_config(request: Request) -> Dict[str, Dict[str, int | float | str | None]]:
    scd_conf = await scd_reader.get_dict_cfg()
    sgp_conf = await sgp_reader.get_dict_cfg()
    bmp_conf = await bmp_reader.get_dict_cfg()
    return scd_conf | sgp_conf | bmp_conf


@app.put("/sensors/cmd")  # type: ignore[no-untyped-call, misc]
async def sensor_cmd(request: Request) -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["setSCD", "setSGP", "setBMP"])
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}

    if data["cmd"] == "setSCD":
        if debug:
            print("Received Set SCD30 Sensor command.")
        # SCD30 has no schema/cfgmgr of its own (params live on-sensor, see CLAUDE.md) - nothing
        # here was ever persisted anywhere (legacy passed cfg=None/"datamanager = None --> Don't
        # write system config here" too), so there's no config file to correct on a failed setter
        # either - just validate, call the setter, report the outcome, matching each field's own
        # already-exception-safe contract (see asy_scd30_driver.py's own module docstring).
        results: Dict[str, str] = {}
        for key, field, setter in _SCD_SET_FIELDS:
            status = await _scd_apply_field(fields, key, field, setter)
            if status is not None:
                results[key] = status
        return ar.make_response(0, result=results)

    if data["cmd"] == "setSGP":
        if debug:
            print("Received Set SGP40 Sensor command.")
        return await ar.handle_set_cmd(sgp_reader, fields, sgp_reader.get_cfg_schema())

    if data["cmd"] == "setBMP":
        if debug:
            print("Received Set BMP3xx Sensor command.")
        return await ar.handle_set_cmd(bmp_reader, fields, bmp_reader.get_cfg_schema())

    return ar.make_response(100)  # unreachable - parse_cmd_request already restricted cmd above


# LED API
@app.get("/led/status")  # type: ignore[no-untyped-call, misc]
async def led_status(request: Request):
    pausetime = await notify_service.get_override_led()
    return {"pauseTime": pausetime}


@app.get("/led/config")  # type: ignore[no-untyped-call, misc]
async def led_config(request: Request):
    # notify_service.get_cfg_schema() already covers its own 8 fields plus every registered
    # signal's field in one combined schema (see asy_notification_service.py's own docstring on
    # staged registration + finalize()) - no hardcoded field list to keep in sync anymore.
    cfg_data = await notify_service.cfgmgr.get_dict(cm.schema_names(notify_service.get_cfg_schema()))
    # LedWifiOn lives in conn's own config_WIFI.cfg (asy_wifi_service.py), not notify_service's
    # cfgmgr above - get_dict() returns None for the *whole* call if any requested key is unknown
    # to that particular ConfigManager, so this needs its own separate read rather than one combined list.
    wifi_led_data = await conn.cfgmgr.get_dict(["LedWifiOn"])
    if cfg_data is not None and wifi_led_data is not None:
        cfg_data["LedWifiOn"] = wifi_led_data["LedWifiOn"]
    else:
        cfg_data = None
    # AutoOn/LedWifiOn are already native bool here (see this file's own top-of-file note) -
    # get_dict() forwards each config's stored value unconverted, same as every other bool-typed
    # field project-wide; no to_switch() conversion needed or wanted anymore.

    # TODO What if cfg_data is None
    return cfg_data


_FIELD_LED_R: "cm.FieldSchema" = ("r", "int", 0, 0, 255, None)
_FIELD_LED_G: "cm.FieldSchema" = ("g", "int", 0, 0, 255, None)
_FIELD_LED_B: "cm.FieldSchema" = ("b", "int", 0, 0, 255, None)
_FIELD_LED_T: "cm.FieldSchema" = ("t", "float", 1.0, 0.5, 60.0, None)
_FIELD_LED_PAUSE_TIME: "cm.FieldSchema" = ("pauseTime", "int", 0, 0, 3600, None)


@app.put("/led/cmd")  # type: ignore[no-untyped-call, misc]
async def led_cmd(request: Request) -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(
        request, ["lightCmdLED", "pauseAutoLED", "setAutoLED", "setWiFiLED"]
    )
    if err is not None:
        return err
    assert data is not None
    fields = {k: v for k, v in data.items() if k != "cmd"}

    if data["cmd"] == "lightCmdLED":
        if debug:
            print("Received LED Color command.")
        # Unlike a config field, a missing r/g/b/t here is genuinely invalid, not "leave
        # unchanged" - this command always needs all four to mean anything, matching legacy's own
        # behavior for this one request shape (it never used the omitted-key/empty-string
        # convention for this specific command either).
        rgb: Dict[str, int] = {"r": 0, "g": 0, "b": 0}
        t: float = 1.0
        invalid = False
        for key, field in (("r", _FIELD_LED_R), ("g", _FIELD_LED_G), ("b", _FIELD_LED_B)):
            if key not in fields or cm.type_or_range_error(fields[key], field):
                invalid = True
            else:
                rgb[key] = fields[key]
        if "t" not in fields or cm.type_or_range_error(fields["t"], _FIELD_LED_T):
            invalid = True
        else:
            t = fields["t"]
        if invalid:
            return ar.make_response(7, descr="Incomplete or invalid LED command")
        # asy_neopixel_driver.py's led_signal() correctly types t as float (the old neopixel_signal.py's
        # t: int annotation mismatch is fixed as part of this file's promotion - see CLAUDE.md) - no
        # type: ignore needed here anymore.
        if not pixel.led_signal(rgb["r"], rgb["g"], rgb["b"], t):
            return ar.make_response(8, descr="LED is busy")
        return ar.make_response(0)

    if data["cmd"] == "pauseAutoLED":
        if debug:
            print("Received Pause Auto LED command.")
        pause_time = fields.get("pauseTime")
        if pause_time is None or cm.type_or_range_error(pause_time, _FIELD_LED_PAUSE_TIME):
            return ar.make_response(9, descr="Invalid Auto LED Pause time")
        await notify_service.set_override_led(pause_time)
        return ar.make_response(0, result={"pauseTime": "Valid"})

    if data["cmd"] == "setAutoLED":
        if debug:
            print("Received Set Auto LED command.")
        # Unlike the old Neopixel_Signal (no SensorReaderConfig of its own, hence the now-removed
        # _write_cfg_only helper), notify_service is a real SensorReaderConfig - handle_set_cmd()
        # is the standard path every other real Reader route (setSGP/setBMP/setTiming) already
        # uses. No field here registers a live-push callback (every Auto*/Warn* field is polled by
        # notify_service's own task each cycle, never pushed immediately), so this is a pure
        # persist-and-report, identical in effect to the old helper - just via the shared path.
        return await ar.handle_set_cmd(notify_service, fields, notify_service.get_cfg_schema())

    if data["cmd"] == "setWiFiLED":
        if debug:
            print("Received Set WiFi LED command.")
        # Scoped to LedWifiOn only (see _cfg_subset's own comment / /net/cmd's matching note above)
        # - matches legacy's own setWiFiLED scoping; SSID/PW/Country/Hostname live in this same
        # cfgmgr but belong to /net/cmd's setNetwork, not here.
        return await ar.handle_set_cmd(conn, fields, _cfg_subset(conn.get_cfg_schema(), ("LedWifiOn",)))

    return ar.make_response(100)  # unreachable - parse_cmd_request already restricted cmd above


# System API
@app.get("/system/status")  # type: ignore[no-untyped-call, misc]
async def system_status(request: Request):
    sgp_last_backup, sgp_restored = await sgp_reader.get_mem_status()
    if sgp_last_backup is None:
        sgpback = "None"
    elif sgp_last_backup == 0:
        sgpback = "No TS"
    else:
        sgpback = sgp_last_backup

    if sgp_restored is None:
        sgpres = "None"
    elif sgp_restored == -1:
        sgpres = "No TS"
    else:
        sgpres = sgp_restored

    # get_mem_error_counters() (per-chunk crit/uncrit/last counters) no longer exists on the
    # promoted SGP40_Reader - superseded by AsyFramManager.get_error_counter(), a single
    # whole-chip-scope log shared by every driver's FRAM usage (see BACKLOG.md).
    fram_err_log = await fram.get_error_counter()
    FRAM_ErrCnt = fram_err_log["FRAM"]["ErrCount"]
    # base_classes.py's SensorReader.get_error_counter() (used by every promoted *_Reader) returns
    # print_log.py's get_log() shape - {"<NAME>": {"ErrCount": int, "ErrNum": [...], "ErrType":
    # [...]}}, not a bare int; extract the count explicitly instead of comparing the whole dict
    # below, to keep this endpoint's existing flat-int JSON contract unchanged.
    _scd_err_count = (await scd_reader.get_error_counter())["SCD30"]["ErrCount"]
    SCD30_ErrCnt = _scd_err_count if isinstance(_scd_err_count, int) else 0
    _sgp_err_count = (await sgp_reader.get_error_counter())["SGP40"]["ErrCount"]
    SGP40_ErrCnt = _sgp_err_count if isinstance(_sgp_err_count, int) else 0
    _bmp_err_count = (await bmp_reader.get_error_counter())["BMP3XX"]["ErrCount"]
    BMP388_ErrCnt = _bmp_err_count if isinstance(_bmp_err_count, int) else 0
    # notify_service (asy_notification_service.py) has real, loggable failure paths of its own
    # (get_value callback exceptions, threshold config read failures, request_signal_cb failures,
    # local_time_callback failures - errno 1-4) that the old Neopixel_Signal never had (bare
    # PrintLog, no counting at all) - surfaced here the same way every sibling driver already is.
    _notify_err_count = (await notify_service.get_error_counter())["NOTIFY"]["ErrCount"]
    NOTIFY_ErrCnt = _notify_err_count if isinstance(_notify_err_count, int) else 0
    # sysfunct.get_error_counter()'s "Tasks" log now supersedes the old hand-rolled
    # task_error_counter/last_task_err LockedCounter/LockedValue pair, once main() switched to the
    # real, tested start_and_check_tasks() supervisor - same dict shape every *_Reader already uses.
    _task_err_log = (await sysfunct.get_error_counter())["Tasks"]
    _task_err_cnt_val = _task_err_log["ErrCount"]
    Task_ErrCnt = _task_err_cnt_val if isinstance(_task_err_cnt_val, int) else 0
    _task_err_num = _task_err_log["ErrNum"]
    Task_LastErr = (
        _task_err_num[-1] - 1
        if Task_ErrCnt > 0 and isinstance(_task_err_num, list) and _task_err_num and isinstance(_task_err_num[-1], int)
        else -1
    )  # wrnno was recorded as (task index + 1); -1 matches the old "never failed" sentinel
    ErrorStatus = (
        (FRAM_ErrCnt > 0)
        or (SCD30_ErrCnt > 0)
        or (BMP388_ErrCnt > 0)
        or (SGP40_ErrCnt > 0)
        or (Task_ErrCnt > 0)
        or (NOTIFY_ErrCnt > 0)
    )
    system_data = {
        "Sys_Uptime": await sysfunct.get_uptime(),
        "Wifi_Uptime": await conn.get_wifi_uptime(),
        "NTP_LastSync": await ntp.get_last_ntp_sync(),
        "Boot_Signature": await sysfunct.get_boot_signature(),
        "Error_Status": ErrorStatus,
        "Task_ErrCnt": Task_ErrCnt,
        "Task_LastErr": Task_LastErr,
        "SCD30_ErrCnt": SCD30_ErrCnt,
        "SGP40_ErrCnt": SGP40_ErrCnt,
        "SGP40_Backup_TS": sgpback,
        "SGP40_Restore_TS": sgpres,
        "FRAM_ErrCnt": FRAM_ErrCnt,
        "BMP388_ErrCnt": BMP388_ErrCnt,
        "NOTIFY_ErrCnt": NOTIFY_ErrCnt,
    }
    return system_data


_FIELD_SYS_CONTENT: "cm.FieldSchema" = ("content", "str", "reboot", 0, 0, ("reboot", "bootloader", "mempause"))


@app.put("/system/cmd")  # type: ignore[no-untyped-call, misc]
async def system_cmd(request: Request) -> "ar.ResponseEnvelope":
    data, err = ar.parse_cmd_request(request, ["systemCmd"])
    if err is not None:
        return err
    assert data is not None
    if debug:
        print("Received System command.")
    content = data.get("content")
    if content is None or cm.type_or_range_error(content, _FIELD_SYS_CONTENT):
        return ar.make_response(10, descr="Invalid or unknown system command")
    if content == "reboot":
        descr = "Rebooting system now!"
        sysfunct.reboot_system()
    elif content == "bootloader":
        descr = "Rebooting into bootloader!"
        sysfunct.reboot_bootloader()
    else:  # "mempause" - the only remaining member of the discrete allowed-value set above
        descr = "Pausing memory communication for " + str(_FRAM_PAUSE_SEC) + " seconds!"
        sysfunct.pause_permanent_storage(_FRAM_PAUSE_SEC)
    return ar.make_response(0, descr=descr, result={"content": "Valid"})


# Main Function
async def main():
    async_onetime = []  # onetime inits before starting other tasks
    async_onetime.append(fram.setup)

    task_starters = (
        scd_reader.get_task_starters()
        + bmp_reader.get_task_starters()
        + sgp_reader.get_task_starters()
    )
    timer_starters = (
        scd_reader.get_timer_starters()
        + bmp_reader.get_timer_starters()
        + sgp_reader.get_timer_starters()
    )

    task_starters += pixel.get_task_starters() + notify_service.get_task_starters()

    task_starters += [
        sysfunct.start_asy_uptime_counter,
        conn.start_asy_wlan_connect,
        ntp.start_asy_ntp_client,
        ntp.start_asy_ntp_refresh,
        conn.start_asy_uptime_counter,
        ntp.start_asy_sync_age_counter,
        start_asy_webserver,
    ]

    timer_starters += [
        sysfunct.start_uptime_timer,
        conn.start_counter_timer,
        ntp.start_counter_timer,
        ntp.start_ntp_timer,
    ]

    for trigger in async_onetime:
        await trigger()

    await sysfunct.start_timers(timer_starters)

    # Force an initial sync attempt before the ntp task itself even starts - ntp_force_sync() only
    # sets an event flag asy_ntp_time() watches for, so pre-setting it here is equivalent to (and
    # simpler than) waiting for the task to start first, and start_and_check_tasks() below is the
    # last call in this function (it blocks forever, running the real task supervisor).
    await ntp.ntp_force_sync()  # first sync

    await sysfunct.start_and_check_tasks(task_starters)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
