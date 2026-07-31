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
from neopixel_signal import Neopixel_Signal
from asy_wifi_service import asy_conn_time
from asy_ntp_client import asy_ntp_client
from config_manager import ConfigManager
from microdot import Microdot, send_file, Request, Response
from machine import Timer, WDT
from micropython import const
from api_helpers import (
    JsonValidity,
    init_json_from_cfg,
    init_json_from_ext,
    cmd_pre_check,
    update_valid_json,
    cmd_post_check,
    to_switch,
    set_sensor_value,
    get_valid_values,
    generic_error_return,
    time_to_dict,
)
from typing import List, Callable, Dict

_MAX_I2C_ERR = const(5)
_FRAM_PAUSE_SEC = const(300)  # 5min communication pause for FRAM

# Residual system-level config: fields with no per-driver setter/schema of their own yet (the
# generic REST config-setter mechanism is deferred, tracked separately in BACKLOG.md - not part of
# this fix) - own schema, own config_SYSTEM.cfg file, same global scheme every other module with
# user-settable configuration now follows (LED config moved into neopixel_signal.py itself; NTP
# timing config already lives on ntp.cfgmgr - see /time/*, /led/* routes below). Ranges/defaults for
# the BMP fields mirror asy_bmp3xx_driver.py's own internal schema (_VAL_SI/_VAL_POV/etc.) exactly,
# since these are REST-layer aliases of the same real fields, not independently-designed values.
_VAL_SGP_BACKUP_PERIOD = const((("SGPBackupPeriod", "int", 0, 0, 1440, None),))
_VAL_SGP_BACKUP_MAXAGE = const((("SGPBackupMaxAge", "int", 0, 0, 10080, None),))
_VAL_SGP_WAIT_NTP = const((("SGPWaitTimeNTP", "int", 60, 0, 600, None),))
_VAL_BMP_SAMPLE_INTERV = const((("BMPSampleInterv", "int", 2, 1, 3600, None),))
_VAL_BMP_PRESS_OVERS = const((("BMPPressOvers", "int", 1, 1, 32, None),))
_VAL_BMP_TEMP_OVERS = const((("BMPTempOvers", "int", 1, 1, 32, None),))
_VAL_BMP_FILT_COEFF = const((("BMPFiltCoeff", "int", 0, 0, 127, None),))
_VAL_BMP_PRESS_OFFSET = const((("BMPPressOffset", "float", 0.0, -500.0, 500.0, None),))
_VAL_BMP_TEMP_OFFSET = const((("BMPTempOffset", "float", 0.0, -10.0, 10.0, None),))
_VAL_BMP_SEALEVEL_OFFS = const((("BMPSeaLevelOffs", "float", 0.0, -1000.0, 5000.0, None),))
_VAL_BMP_MEAN_ATM_TEMP = const((("BMPMeanAtmTemp", "float", 15.0, -50.0, 50.0, None),))

_VAL_SGP_SYS_FIELDS = _VAL_SGP_BACKUP_PERIOD + _VAL_SGP_BACKUP_MAXAGE + _VAL_SGP_WAIT_NTP
_VAL_BMP_SYS_FIELDS = (
    _VAL_BMP_SAMPLE_INTERV
    + _VAL_BMP_PRESS_OVERS
    + _VAL_BMP_TEMP_OVERS
    + _VAL_BMP_FILT_COEFF
    + _VAL_BMP_PRESS_OFFSET
    + _VAL_BMP_TEMP_OFFSET
    + _VAL_BMP_SEALEVEL_OFFS
    + _VAL_BMP_MEAN_ATM_TEMP
)
_VAL_SYSTEM_FIELDS = _VAL_SGP_SYS_FIELDS + _VAL_BMP_SYS_FIELDS


async def sgp_comp_callback() -> List[float | None]:
    data = await scd_reader.get_data()
    if data is None:
        return [None, None]
    try:
        return [float(data.Temp), float(data.Hum)]
    except:
        return [None, None]


async def airqual_meas_callback() -> List[int | float | None]:
    scd_data = await scd_reader.get_data()
    sgp_data = await sgp_reader.get_data()
    if scd_data is None or sgp_data is None:
        return [None, None, None]
    try:
        return [float(scd_data.CO2), float(scd_data.Hum), int(sgp_data.VOC)]
    except:
        return [None, None, None]


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
# - Neopixel_Signal (neopixel_signal.py, promoted) now owns its own config_NEOPIXEL.cfg internally
#   too - every REST route below that reads or writes an LedAuto*/LedWarn* field goes through
#   pixel.cfgmgr. NTP_Host/NTP_Offset_S/NTP_Interv_H/GMTOffset/DSTOffset already live on
#   ntp.cfgmgr (asy_ntp_client.py's own schema) - /time/* below goes through that, not a shared one.
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
# Residual system-level config (see _VAL_SYSTEM_FIELDS above) - reuses sysfunct's own logger
# (self.pr) rather than a second, separately-tracked PrintLog instance.
cfgmgr = ConfigManager("config_SYSTEM.cfg", _VAL_SYSTEM_FIELDS, sysfunct.pr)
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
pixel = Neopixel_Signal(
    15,
    airqual_meas_callback,
    ntp.cettime,
    debug=debug,
)
conn.set_ext_led(pixel)  # callback for wifi led
timers_running = ThreadSafeFlag()


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
async def network_cmd(request: Request) -> Dict[str, str | int | JsonValidity]:
    req_json, err_msg = cmd_pre_check(request, ["setNetwork"])
    if err_msg is not None:
        return err_msg
    if req_json is not None:
        if req_json["cmd"] == "setNetwork":
            if debug:
                print("Received Set Network command.")
            res, err = await init_json_from_cfg(conn.cfgmgr, ["Hostname", "Country", "SSID", "PW"])
            if err is not None:
                return err
            if res is not None:
                res = update_valid_json(req_json, "Hostname", "str", res, 1, 32, debug=debug)
                # 32, not 63: network.hostname()'s real, documented hard cap on rp2 (see
                # asy_wifi_service.py's own _VAL_HOST schema, which this bound now matches).
                res = update_valid_json(req_json, "Country", "str", res, 2, 2, debug=debug)
                res = update_valid_json(req_json, "SSID", "str", res, 2, 32, debug=debug)
                res = update_valid_json(req_json, "PW", "str", res, 8, 63, debug=debug)
                return await cmd_post_check(
                    res, conn.cfgmgr, conn.cfg_schema, post_fct=conn.reconnect_wifi, debug=debug
                )  # Reconnect WiFi with new config (has 5 sec delay)
    return generic_error_return()


# Timing API
@app.get("/time/status")  # type: ignore[no-untyped-call, misc]
async def timing_status(
    request: Request,
) -> Dict[str, Dict[str, int | float | str | None]]:
    synced = await ntp.ntp_issynced()
    gmt = time.gmtime()
    system: Dict[str, int | float | str | None] = {
        "Synced": "On" if synced else "Off",
        "Unix": time.mktime(gmt),  # type: ignore[call-arg]
    }
    utc = time_to_dict(gmt)
    local = time_to_dict(await ntp.cettime())

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
async def timing_cmd(request: Request) -> Dict[str, str | int | JsonValidity]:
    req_json, err_msg = cmd_pre_check(request, ["setTiming"])
    if err_msg is not None:
        return err_msg
    if req_json is not None:
        if req_json["cmd"] == "setTiming":
            if debug:
                print("Received Set Timing command.")
            res, err = await init_json_from_cfg(
                ntp.cfgmgr, ["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"]
            )
            if err is not None:
                return err
            if res is not None:
                res = update_valid_json(req_json, "NTP_Host", "str", res, 3, 1024, debug=debug)
                res = update_valid_json(
                    req_json, "NTP_Offset_S", "int", res, -43200, 43200, debug=debug
                )
                res = update_valid_json(req_json, "NTP_Interv_H", "int", res, 1, 24, debug=debug)
                res = update_valid_json(
                    req_json, "GMTOffset", "int", res, -43200, 43200, debug=debug
                )
                res = update_valid_json(
                    req_json, "DSTOffset", "int", res, -43200, 43200, debug=debug
                )
                return await cmd_post_check(
                    res, ntp.cfgmgr, ntp.cfg_schema, post_asy_fct=ntp.ntp_force_sync, debug=debug
                )  # resync NTP with new config
    return generic_error_return()


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
async def sensor_cmd(request: Request):
    req_json, err_msg = cmd_pre_check(request, ["setSCD", "setSGP", "setBMP"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "setSCD":
        if debug:
            print("Received Set SCD30 Sensor command.")
        if debug:
            print(req_json)
        data = {}
        try:
            data["TempOffs"] = await scd_reader.get_temperature_offset()
            data["MeasInt"] = (await scd_reader.get_measurement_interval(),)
            data["AmbPres"] = (await scd_reader.get_ambient_pressure(),)
            data["Altitude"] = (await scd_reader.get_altitude(),)
            data["ForceCalRef"] = (await scd_reader.get_forced_recalibration_reference(),)
            data["SelfCal"] = (await scd_reader.get_self_calibration_enabled(),)
            data["ContMeas"] = True  # not readable from sensor, just as reference for parsing
            valid = True
        except:
            valid = False

        res, err = await init_json_from_ext(valid, data)
        if res is None:
            return err
        res = update_valid_json(req_json, "TempOffs", "float", res, 0.0, 655.35, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_temperature_offset, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "MeasInt", "int", res, 2, 1800, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_measurement_interval, cfgmgr, debug=debug)
        res = update_valid_json(
            req_json, "AmbPres", "int", res, 700, 1400, special_val=[0], debug=debug
        )
        res = await set_sensor_value(
            res, scd_reader.set_ambient_pressure, cfgmgr, force=True, debug=debug
        )
        res = update_valid_json(req_json, "Altitude", "int", res, 0, 65535, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_altitude, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ForceCalRef", "int", res, 400, 2000, debug=debug)
        res = await set_sensor_value(
            res, scd_reader.set_forced_recalibration_reference, cfgmgr, debug=debug
        )
        res = update_valid_json(req_json, "SelfCal", "switch", res, None, None, debug=debug)
        res = await set_sensor_value(
            res, scd_reader.set_self_calibration_enabled, cfgmgr, debug=debug
        )
        res = update_valid_json(
            req_json, "ContMeas", "switch", res, None, None, debug=debug
        )  # only understands "Off"
        res = await set_sensor_value(
            res, scd_reader.stop_continuous_measurement, cfgmgr, debug=debug
        )
        return await cmd_post_check(
            res, None, debug=debug
        )  # datamanager = None --> Don't write system config here

    if req_json["cmd"] == "setSGP":
        if debug:
            print("Received Set SGP40 Sensor command.")
        res, err = await init_json_from_cfg(
            cfgmgr,
            ["SGPBackupPeriod", "SGPBackupMaxAge", "SGPWaitTimeNTP"],
            cmd_keys={"SGPResetVOC": False},
        )
        if res is None:
            return err
        res = update_valid_json(req_json, "SGPBackupPeriod", "int", res, 0, 1440, debug=debug)
        res = update_valid_json(req_json, "SGPBackupMaxAge", "int", res, 0, 10080, debug=debug)
        res = update_valid_json(req_json, "SGPWaitTimeNTP", "int", res, 0, 600, debug=debug)
        res = update_valid_json(
            req_json, "SGPResetVOC", "switch", res, None, None, debug=debug
        )  # only understands "On"
        res = await set_sensor_value(res, sgp_reader.reset_voc, cfgmgr, default=False, debug=debug)
        return await cmd_post_check(res, cfgmgr, _VAL_SGP_SYS_FIELDS, debug=debug)  # don't save reset flag

    if req_json["cmd"] == "setBMP":
        if debug:
            print("Received Set BMP3xx Sensor command.")
        res, err = await init_json_from_cfg(
            cfgmgr,
            [
                "BMPSampleInterv",
                "BMPPressOvers",
                "BMPTempOvers",
                "BMPFiltCoeff",
                "BMPPressOffset",
                "BMPTempOffset",
                "BMPSeaLevelOffs",
                "BMPMeanAtmTemp",
            ],
        )
        if res is None:
            return err
        res = update_valid_json(req_json, "BMPSampleInterv", "int", res, 1, 3600, debug=debug)
        res = await set_sensor_value(res, bmp_reader.set_trigger_secs, cfgmgr, debug=debug)
        res = update_valid_json(
            req_json, "BMPPressOvers", "int", res, 0, 5, weight_fct=lambda x: 2**x, debug=debug
        )
        res = await set_sensor_value(
            res,
            bmp_reader.set_pressure_oversampling,
            cfgmgr,
            getter=bmp_reader.get_pressure_oversampling,
            default=1,
            debug=debug,
        )
        res = update_valid_json(
            req_json, "BMPTempOvers", "int", res, 0, 5, weight_fct=lambda x: 2**x, debug=debug
        )
        res = await set_sensor_value(
            res,
            bmp_reader.set_temperature_oversampling,
            cfgmgr,
            getter=bmp_reader.get_temperature_oversampling,
            default=1,
            debug=debug,
        )
        res = update_valid_json(
            req_json,
            "BMPFiltCoeff",
            "int",
            res,
            0,
            7,
            weight_fct=lambda x: 2**x - 1,
            debug=debug,
        )
        res = await set_sensor_value(
            res,
            bmp_reader.set_filter_coefficient,
            cfgmgr,
            getter=bmp_reader.get_filter_coefficient,
            debug=debug,
        )
        res = update_valid_json(
            req_json, "BMPPressOffset", "float", res, -500.0, 500.0, debug=debug
        )
        res = update_valid_json(req_json, "BMPTempOffset", "float", res, -10.0, 10.0, debug=debug)
        res = update_valid_json(
            req_json, "BMPSeaLevelOffs", "float", res, -1000.0, 5000.0, debug=debug
        )
        res = update_valid_json(req_json, "BMPMeanAtmTemp", "float", res, -50.0, 50.0, debug=debug)
        return await cmd_post_check(res, cfgmgr, _VAL_BMP_SYS_FIELDS, debug=debug)


# LED API
@app.get("/led/status")  # type: ignore[no-untyped-call, misc]
async def led_status(request: Request):
    pausetime = await pixel.get_override_led()
    return {"pauseTime": pausetime}


@app.get("/led/config")  # type: ignore[no-untyped-call, misc]
async def led_config(request: Request):
    cfg_data = await pixel.cfgmgr.get_dict(
        [
            "LedAutoOn",
            "LedAutoOnH",
            "LedAutoOnM",
            "LedAutoOffH",
            "LedAutoOffM",
            "LedAutoFlashBri",
            "LedAutoInterv",
            "LedAutoFlashDur",
            "LedWarnCO2",
            "LedWarnVOC",
            "LedWarnHum",
        ]
    )
    # LedWifiOn lives in conn's own config_WIFI.cfg (asy_wifi_service.py), not pixel's cfgmgr above
    # - get_dict() returns None for the *whole* call if any requested key is unknown to that
    # particular ConfigManager, so this needs its own separate read rather than one combined list.
    wifi_led_data = await conn.cfgmgr.get_dict(["LedWifiOn"])
    _led_auto_on = cfg_data["LedAutoOn"] if cfg_data is not None else None
    _led_wifi_on = wifi_led_data["LedWifiOn"] if wifi_led_data is not None else None
    if (
        cfg_data is not None
        and wifi_led_data is not None
        and isinstance(_led_auto_on, bool)
        and isinstance(_led_wifi_on, bool)
    ):
        cfg_data["LedAutoOn"] = to_switch(_led_auto_on)
        cfg_data["LedWifiOn"] = to_switch(_led_wifi_on)
    else:
        cfg_data = None

    # TODO What if cfg_data is None
    return cfg_data


@app.put("/led/cmd")  # type: ignore[no-untyped-call, misc]
async def led_cmd(request: Request):
    req_json, err_msg = cmd_pre_check(
        request, ["lightCmdLED", "pauseAutoLED", "setAutoLED", "setWiFiLED"]
    )
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "lightCmdLED":
        if debug:
            print("Received LED Color command.")
        default = {"r": 0, "g": 0, "b": 0, "t": 1.0}
        res, err = await init_json_from_ext(True, default)
        if res is None:
            return err
        res = update_valid_json(req_json, "r", "int", res, 0, 255, debug=debug)
        res = update_valid_json(req_json, "g", "int", res, 0, 255, debug=debug)
        res = update_valid_json(req_json, "b", "int", res, 0, 255, debug=debug)
        res = update_valid_json(req_json, "t", "float", res, 0.5, 60.0, debug=debug)
        values, valid = get_valid_values(res, ["r", "g", "b", "t"])
        err = None
        if valid:
            if not pixel.led_signal(values["r"], values["g"], values["b"], values["t"]):
                err = "busyLED"
        else:
            err = "invalidLED"
        return await cmd_post_check(
            res, None, special_err=err, debug=debug
        )  # don't save anything, use special error in case

    if req_json["cmd"] == "pauseAutoLED":
        if debug:
            print("Received Pause Auto LED command.")
        default = {"pauseTime": 0}
        res, err = await init_json_from_ext(True, default)
        if res is None:
            return err
        res = update_valid_json(req_json, "pauseTime", "int", res, 0, 3600, debug=debug)
        values, valid = get_valid_values(res, ["pauseTime"])
        err = None
        if valid:
            await pixel.set_override_led(values["pauseTime"])
        else:
            err = "pauseLED"
        return await cmd_post_check(
            res, None, special_err=err, debug=debug
        )  # don't save anything, use special error in case

    if req_json["cmd"] == "setAutoLED":
        if debug:
            print("Received Set Auto LED command.")
        res, err = await init_json_from_cfg(
            pixel.cfgmgr,
            [
                "LedAutoOn",
                "LedAutoOnH",
                "LedAutoOnM",
                "LedAutoOffH",
                "LedAutoOffM",
                "LedAutoFlashBri",
                "LedAutoInterv",
                "LedAutoFlashDur",
                "LedWarnCO2",
                "LedWarnVOC",
                "LedWarnHum",
            ],
        )
        if res is None:
            return err
        res = update_valid_json(req_json, "LedAutoOn", "switch", res, None, None, debug=debug)
        res = update_valid_json(req_json, "LedAutoOnH", "int", res, 0, 23, debug=debug)
        res = update_valid_json(req_json, "LedAutoOnM", "int", res, 0, 59, debug=debug)
        res = update_valid_json(req_json, "LedAutoOffH", "int", res, 0, 23, debug=debug)
        res = update_valid_json(req_json, "LedAutoOffM", "int", res, 0, 59, debug=debug)
        res = update_valid_json(req_json, "LedAutoFlashBri", "int", res, 1, 255, debug=debug)
        res = update_valid_json(req_json, "LedAutoInterv", "float", res, 60.0, 3600.0, debug=debug)
        res = update_valid_json(req_json, "LedAutoFlashDur", "float", res, 0.5, 10.0, debug=debug)
        res = update_valid_json(req_json, "LedWarnCO2", "int", res, 0, 3000, debug=debug)
        res = update_valid_json(req_json, "LedWarnVOC", "int", res, 0, 500, debug=debug)
        res = update_valid_json(req_json, "LedWarnHum", "float", res, 0.0, 100.0, debug=debug)
        return await cmd_post_check(res, pixel.cfgmgr, pixel.cfg_schema, debug=debug)

    if req_json["cmd"] == "setWiFiLED":
        if debug:
            print("Received Set WiFi LED command.")
        res, err = await init_json_from_cfg(conn.cfgmgr, ["LedWifiOn"])
        if res is None:
            return err
        res = update_valid_json(req_json, "LedWifiOn", "switch", res, None, None, debug=debug)
        res = await set_sensor_value(res, conn.set_wifi_led, conn.cfgmgr, default=True, debug=debug)
        return await cmd_post_check(res, conn.cfgmgr, conn.cfg_schema, debug=debug)


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
    )
    system_data = {
        "Sys_Uptime": await sysfunct.get_uptime(),
        "Wifi_Uptime": await conn.get_wifi_uptime(),
        "NTP_LastSync": await ntp.get_last_ntp_sync(),
        "Boot_Signature": await sysfunct.get_boot_signature(),
        "Error_Status": to_switch(ErrorStatus),
        "Task_ErrCnt": Task_ErrCnt,
        "Task_LastErr": Task_LastErr,
        "SCD30_ErrCnt": SCD30_ErrCnt,
        "SGP40_ErrCnt": SGP40_ErrCnt,
        "SGP40_Backup_TS": sgpback,
        "SGP40_Restore_TS": sgpres,
        "FRAM_ErrCnt": FRAM_ErrCnt,
        "BMP388_ErrCnt": BMP388_ErrCnt,
    }
    return system_data


@app.put("/system/cmd")  # type: ignore[no-untyped-call, misc]
async def system_cmd(request: Request):
    req_json, err_msg = cmd_pre_check(request, ["systemCmd"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "systemCmd":
        if debug:
            print("Received System command.")
        default = {"content": ""}
        res, err = await init_json_from_ext(True, default)
        if res is None:
            return err
        res = update_valid_json(
            req_json,
            "content",
            "str",
            res,
            0,
            0,
            special_val=["reboot", "bootloader", "mempause"],
            debug=debug,
        )  # only special values are valid
        values, valid = get_valid_values(res, ["content"])
        err = None
        descr = ""
        if valid:
            if values["content"] == "reboot":
                descr = "Rebooting system now!"
                sysfunct.reboot_system()
            elif values["content"] == "bootloader":
                descr = "Rebooting into bootloader!"
                sysfunct.reboot_bootloader()
            elif values["content"] == "mempause":
                descr = "Pausing memory communication for " + str(_FRAM_PAUSE_SEC) + " seconds!"
                sysfunct.pause_permanent_storage(_FRAM_PAUSE_SEC)
            else:
                err = "sysCmd"
        else:
            err = "sysCmd"
        return await cmd_post_check(
            res, None, special_err=err, ok_descr=descr, debug=debug
        )  # don't save anything, use special error in case


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

    task_starters += [
        sysfunct.start_asy_uptime_counter,
        pixel.start_asy_neopixel_led_overl,
        pixel.start_asy_ext_cmd_watcher,
        pixel.start_asy_neopixel_signal,
        pixel.start_asy_auto_override,
        pixel.start_asy_airquality_signal,
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
