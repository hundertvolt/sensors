import frozen_html  # type: ignore[import-not-found] # noqa: F401
import time
import json
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
from async_connect import asy_conn_time
from async_manager import TimeCounterManager, LockedValue, ConfigManager
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

_CFG_FILE_NAME = const("config.json")
_DEFAULT_CONFIG = const(
    '{"LedAutoOn": true, "LedAutoInterv": 300, "LedAutoOnH": 10, "LedAutoOnM": 0, "LedAutoOffH": 18, "LedAutoOffM": 0, "LedAutoFlashDur": 2, "LedAutoFlashBri": 200, "LedWarnCO2": 1600, "LedWarnVOC": 350, "LedWarnHum": 65}'
)

_TASK_CHECK_TIME = const(3)
_TASK_FAIL_INCREMENT = const(100)
_TASK_FAIL_MAX = const(300)
_MAX_I2C_ERR = const(5)
_FRAM_PAUSE_SEC = const(300)  # 5min communication pause for FRAM


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
cfgmgr = ConfigManager(
    _CFG_FILE_NAME,
    json.loads(_DEFAULT_CONFIG)
    | SCD30_Reader.get_default_cfg()
    | SGP40_Reader.get_default_cfg()
    | BMP3xx_Reader.get_default_cfg()
    | asy_conn_time.get_default_cfg(),
    debug=debug,
)
# asy_conn_time: led_pin='LED' for onboard WiFi LED
conn = asy_conn_time(cfgmgr, conn_fail_to_hotspot=5, hotspot_time_min=8, debug=debug)
app = Microdot()  # type: ignore[no-untyped-call]
i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)
spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
fram = AsyFramManager(spi0, 1, max_size=0x2000, debug=debug)
sysfunct = SystemService(conn.ntp_issynced, storage_pause=fram.set_pause, debug=debug)
sgp_backup = fram.get_timestamped_chunk(SGP40_Reader.get_params_memsize(), conn.ntp_issynced)
sgp_reader = SGP40_Reader(
    i2c1,
    cfgmgr,
    sgp_comp_callback,
    ts_storage=sgp_backup,
    max_i2c_err=_MAX_I2C_ERR,
    debug=debug,
)
bmp_reader = BMP3xx_Reader(i2c1, cfgmgr, max_i2c_err=_MAX_I2C_ERR, debug=debug)
scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, max_i2c_err=_MAX_I2C_ERR, debug=debug)
pixel = Neopixel_Signal(
    15,
    cfgmgr,
    airqual_meas_callback,
    conn.cettime,
    asy_long_block_lock=conn.get_long_block_lock(),
    debug=debug,
)
conn.set_ext_led(pixel)  # callback for wifi led
task_error_counter = (
    TimeCounterManager()
)  # use inherently limited counter here as overall error counter
last_task_err = LockedValue(-1)
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
async def network_config(request: Request) -> Dict[str, int | float | str | None]:
    cfg_data = await cfgmgr.get_dict(["Country", "Hostname", "SSID"])
    if cfg_data is not None:
        cfg_data["PW"] = "********"
    else:
        # TODO Create full dict if None!
        cfg_data["PW"] = None
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
            res, err = await init_json_from_cfg(cfgmgr, ["Hostname", "Country", "SSID", "PW"])
            if err is not None:
                return err
            if res is not None:
                res = update_valid_json(req_json, "Hostname", "str", res, 1, 63, debug=debug)
                res = update_valid_json(req_json, "Country", "str", res, 2, 2, debug=debug)
                res = update_valid_json(req_json, "SSID", "str", res, 2, 32, debug=debug)
                res = update_valid_json(req_json, "PW", "str", res, 8, 63, debug=debug)
                return await cmd_post_check(
                    res, cfgmgr, post_fct=conn.reconnect_wifi, debug=debug
                )  # Reconnect WiFi with new config (has 5 sec delay)
    return generic_error_return()


# Timing API
@app.get("/time/status")  # type: ignore[no-untyped-call, misc]
async def timing_status(
    request: Request,
) -> Dict[str, Dict[str, int | float | str | None]]:
    synced = await conn.ntp_issynced()
    gmt = time.gmtime()
    system: Dict[str, int | float | str | None] = {
        "Synced": "On" if synced else "Off",
        "Unix": time.mktime(gmt),  # type: ignore[call-arg]
    }
    utc = time_to_dict(gmt)
    local = time_to_dict(await conn.cettime())

    rtc_time = {"System": system, "UTC": utc, "Local": local}
    return rtc_time


@app.get("/time/config")  # type: ignore[no-untyped-call, misc]
async def timing_config(request: Request) -> Dict[str, int | float | str | None]:
    ntp_data = await cfgmgr.get_dict(
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
                cfgmgr, ["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"]
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
                    res, cfgmgr, post_asy_fct=conn.ntp_force_sync, debug=debug
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
        return await cmd_post_check(res, cfgmgr, debug=debug)  # don't save reset flag

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
            special_val=[0],
            weight_fct=lambda x: 2**x,
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
        return await cmd_post_check(res, cfgmgr, debug=debug)


# LED API
@app.get("/led/status")  # type: ignore[no-untyped-call, misc]
async def led_status(request: Request):
    pausetime = await pixel.get_override_led()
    return {"pauseTime": pausetime}


@app.get("/led/config")  # type: ignore[no-untyped-call, misc]
async def led_config(request: Request):
    cfg_data = await cfgmgr.get_dict(
        [
            "LedAutoOn",
            "LedWifiOn",
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
    if cfg_data is not None:
        cfg_data["LedAutoOn"] = to_switch(cfg_data["LedAutoOn"])
        cfg_data["LedWifiOn"] = to_switch(cfg_data["LedWifiOn"])

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
            cfgmgr,
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
        return await cmd_post_check(res, cfgmgr, debug=debug)

    if req_json["cmd"] == "setWiFiLED":
        if debug:
            print("Received Set WiFi LED command.")
        res, err = await init_json_from_cfg(cfgmgr, ["LedWifiOn"])
        if res is None:
            return err
        res = update_valid_json(req_json, "LedWifiOn", "switch", res, None, None, debug=debug)
        res = await set_sensor_value(res, conn.set_wifi_led, cfgmgr, default=True, debug=debug)
        return await cmd_post_check(res, cfgmgr, debug=debug)


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

    sgp_fram_crit, sgp_fram_uncrit, sgp_fram_last = await sgp_reader.get_mem_error_counters()
    SCD30_ErrCnt = await scd_reader.get_error_counter()
    SGP40_ErrCnt = await sgp_reader.get_error_counter()
    BMP388_ErrCnt = await bmp_reader.get_error_counter()
    Task_ErrCnt = await task_error_counter.get_counter()
    ErrorStatus = (
        (sgp_fram_crit > 0)
        or (sgp_fram_uncrit > 0)
        or (SCD30_ErrCnt > 0)
        or (BMP388_ErrCnt > 0)
        or (SGP40_ErrCnt > 0)
        or (Task_ErrCnt > 0)
    )
    system_data = {
        "Sys_Uptime": await sysfunct.get_uptime(),
        "Wifi_Uptime": await conn.get_wifi_uptime(),
        "NTP_LastSync": await conn.get_last_ntp_sync(),
        "Boot_Signature": await sysfunct.get_boot_signature(),
        "Error_Status": to_switch(ErrorStatus),
        "Task_ErrCnt": Task_ErrCnt,
        "Task_LastErr": await last_task_err.get_value(),
        "SCD30_ErrCnt": SCD30_ErrCnt,
        "SGP40_ErrCnt": SGP40_ErrCnt,
        "SGP40_Backup_TS": sgpback,
        "SGP40_Restore_TS": sgpres,
        "SGP40_MemErr_Critical": sgp_fram_crit,
        "SGP40_MemErr_Uncritical": sgp_fram_uncrit,
        "SGP40_MemErr_Last": sgp_fram_last,
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
        conn.start_asy_ntp_client,
        conn.start_asy_ntp_refresh,
        conn.start_asy_uptime_counter,
        start_asy_webserver,
    ]

    timer_starters += [
        sysfunct.start_uptime_timer,
        conn.start_counter_timer,
        conn.start_ntp_timer,
    ]

    all_running = True
    for trigger in async_onetime:
        res = await trigger()
        all_running = all_running and res

    await sysfunct.start_timers(timer_starters, 1000)


    tasks = []
    for starter in task_starters:
        tasks.append(starter())
        await asyncio.sleep(1.0 / len(task_starters))



    task_errors = 0
    while True:
        no_fail = True
        for n in range(0, len(tasks)):
            if tasks[n].done():
                await task_error_counter.increment()
                await last_task_err.set_value(n)
                task_errors += _TASK_FAIL_INCREMENT
                tasks[n] = task_starters[n]()
                no_fail = False
                if debug:
                    print("Task wurde vorzeitig beendet - versuche Neustart!")

        if task_errors > _TASK_FAIL_MAX:
            all_running = False
            if debug:
                print("Mehrfache Task-Fehler, Neustart!")

        if no_fail and (task_errors > 0):
            task_errors -= 1
            if debug:
                print("Task Error Counter:", task_errors)

        if all_running:
            if debug:
                print("Alle Tasks laufen.")
            watchdog.feed()
        await asyncio.sleep(_TASK_CHECK_TIME)


        await conn.ntp_force_sync()  # first sync

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
