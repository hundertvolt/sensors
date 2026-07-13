import frozen_html
import time
import json
import asyncio
from system_service import System_Service
import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_shtc3_driver import SHTC3_Reader
from asy_mprls_driver import MPRLS_Reader
from asy_isl29125_driver import ISL29125_Reader
from neopixel_signal import Neopixel_Signal
from async_connect import asy_conn_time
from async_manager import ConfigManager, TimeCounterManager, LockedValue
from microdot import Microdot, send_file
from machine import Timer, WDT
from micropython import const
from api_helpers import *

_CFG_FILE_NAME = const("config.json")
_DEFAULT_CONFIG = const("{\"LedAutoOn\": true, \"LedWifiOn\": true, \"LedAutoInterv\": 300, \"LedAutoOnH\": 10, \"LedAutoOnM\": 0, \"LedAutoOffH\": 18, \"LedAutoOffM\": 0, \"LedAutoFlashDur\": 2, \"LedAutoFlashBri\": 200, \"LedWarnCO2\": 1600, \"LedWarnVOC\": 350, \"LedWarnHum\": 65, \"GMTOffset\": 3600,  \"DSTOffset\": 3600, \"NTP_Host\": \"pool.ntp.org\", \"SSID\": \"\", \"Hostname\": \"SensorNode\", \"PW\": \"\", \"NTP_Offset_S\": 0, \"Country\": \"DE\", \"NTP_Interv_H\": 12, \"SHTCSampleInterv\": 5, \"SHTCTempOffs\": 0.0, \"SHTCFiltCoeff\": -1.0, \"MPRLSSampleInterv\": 2, \"MPRLSPressOffset\": 0.0, \"MPRLSFiltCoeff\": -1.0, \"ISLSampleInterv\": 1, \"ISLOperationMode\": 5, \"ISLSensingRange\": 1, \"ISLAdcResolution\": 0, \"ISLIrCompensation\": 63,  \"ISLInterruptAssignment\": 0, \"ISLInterruptHighThres\": 65535, \"ISLInterruptLowThres\": 0, \"ISLInterruptAutoClear\": -1, \"ISLPersistentControl\": 0}")

_TASK_CHECK_TIME = const(3)
_TASK_FAIL_INCREMENT = const(100)
_TASK_FAIL_MAX = const(300)

_MAX_I2C_ERR = const(5)

_SCD30_CO2 = const(0)
_SCD30_Temperature = const(1)
_SCD30_Humidity = const(2)
_SCD30_WetBulb = const(3)
_SCD30_DewPoint = const(4)
_SCD30_Timestamp = const(5)

_SGP40_VOC = const(0)
_SGP40_RAW = const(1)
_SGP40_Timestamp = const(2)

_SHTC3_Temperature = const(0)
_SHTC3_Humidity = const(1)
_SHTC3_WetBulb = const(2)
_SHTC3_DewPoint = const(3)
_SHTC3_Timestamp = const(4)

_MPRLS_Pressure = const(0)
_MPRLS_Timestamp = const(1)

_ISL29125_Red = const(0)
_ISL29125_Green = const(1)
_ISL29125_Blue = const(2)
_ISL29125_Timestamp = const(3)


async def wifiCfgCallback():
    return await cfgmgr.get_values(["SSID", "PW", "Country", "Hostname", "LedWifiOn"])

async def shtcCfgCallback():
    return await cfgmgr.get_values(["SHTCSampleInterv", "SHTCTempOffs", "SHTCFiltCoeff"])

async def mprlsCfgCallback():
    return await cfgmgr.get_values(["MPRLSSampleInterv", "MPRLSPressOffset", "MPRLSFiltCoeff"])

async def islCfgCallback():
    return await cfgmgr.get_values(["ISLSampleInterv", "ISLOperationMode", "ISLSensingRange", "ISLAdcResolution",
                                    "ISLIrCompensation", "ISLInterruptAssignment", "ISLInterruptHighThres", 
                                    "ISLInterruptLowThres", "ISLInterruptAutoClear", "ISLPersistentControl"])

def islIrqCallback(rgb):
    print("ISL29125 Interrupt triggered, values:", rgb)

async def ntpCfgCallback():
    return await cfgmgr.get_values(["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"])

async def sgpCompCallback():
    data = await scd_reader.get_data()
    return [data[_SCD30_Temperature], data[_SCD30_Humidity]]

async def airqualCfgCallback():
    return await cfgmgr.get_values(["LedAutoOn", "LedAutoInterv", "LedAutoOnH", "LedAutoOnM",
                                    "LedAutoOffH", "LedAutoOffM", "LedAutoFlashDur", "LedAutoFlashBri",
                                    "LedWarnCO2", "LedWarnVOC", "LedWarnHum"])

async def airqualMeasCallback():
    scd_data = await scd_reader.get_data()
    sgp_data = await sgp_reader.get_data()
    return [scd_data[_SCD30_CO2], sgp_data[_SGP40_VOC], scd_data[_SCD30_Humidity]]

debug=True
#watchdog = WDT(timeout = 8000)
sysfunct = System_Service(debug=debug)
cfgmgr = ConfigManager(_CFG_FILE_NAME, json.loads(_DEFAULT_CONFIG), debug=debug)
app = Microdot()
i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)
scd_reader = SCD30_Reader(i2c1, 11, trigger_sec=3, max_i2c_err=_MAX_I2C_ERR, debug=debug)
sgp_reader = SGP40_Reader(i2c1, sgpCompCallback, trigger_sec=1, max_i2c_err=_MAX_I2C_ERR, debug=debug)
shtc_reader = SHTC3_Reader(i2c0, shtcCfgCallback, trigger_sec=1, max_i2c_err=_MAX_I2C_ERR, debug=debug)
mprls_reader = MPRLS_Reader(i2c0, mprlsCfgCallback, reset_pin=10, eoc_pin=9, trigger_sec=1, max_i2c_err=_MAX_I2C_ERR, debug=debug)
isl_reader = ISL29125_Reader(i2c1, islCfgCallback, irq_callback=islIrqCallback, irq_pin=8, trigger_sec=1, max_i2c_err=_MAX_I2C_ERR, debug=debug)

conn = asy_conn_time(wifiCfgCallback, ntpCfgCallback, conn_fail_to_hotspot=5, hotspot_time_min=8, debug=debug)  # led_pin='LED' for onboard WiFi LED
#pixel = Neopixel_Signal(16, airqualCfgCallback, airqualMeasCallback, conn.cettime, asy_long_block_lock=conn.get_long_block_lock(), debug=debug)
#conn.set_ext_led(pixel) # callback for wifi led
task_error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
last_task_err = LockedValue(-1)
timers_running = asyncio.ThreadSafeFlag()

def start_asy_webserver():
    evtloop = asyncio.get_event_loop()
    return evtloop.create_task(app.start_server(port=80, debug=debug))

def timer_sequencer(timers, base_period_ms, counter=0):
    timers[counter]()
    if debug: print("Timer started:", counter)
    counter += 1
    if counter < len(timers):
        delay = int(base_period_ms / (len(timers) + 1))  # one delay after each start, also (virtually) for last one
        starter = Timer(period=delay, mode=Timer.ONE_SHOT, callback=lambda b: timer_sequencer(timers, base_period_ms, counter=counter))
    else:
        if debug: print("All timers running.")
        timers_running.set()

# *** WEBSERVER ***
# HTML pages
@app.get('/')
async def index(request):
    return send_file('html/index.html', compressed=True, file_extension='.gz')

@app.get('/index.html')
async def index(request):
    return send_file('html/index.html', compressed=True, file_extension='.gz')

@app.get('/favicon.ico')
async def index(request):
    return send_file('html/favicon.ico', compressed=True, file_extension='.gz')

@app.get('/nettimeconfig.html')
async def nettimecfg(request):
    return send_file('html/nettimeconfig.html', compressed=True, file_extension='.gz')

@app.get('/sensorconfig.html')
async def sensorcfg(request):
    return send_file('html/sensorconfig.html', compressed=True, file_extension='.gz')

@app.get('/systemledconfig.html')
async def systempage(request):
    return send_file('html/systemledconfig.html', compressed=True, file_extension='.gz')

@app.get('/style.css')
async def cssconf(request):
    return send_file('html/style.css', compressed=True, file_extension='.gz')

@app.get('/functions.js')
async def javascript(request):
    return send_file('html/functions.js', compressed=True, file_extension='.gz')

# Networking API
@app.get('/net/status')
async def network_status(request):
    netConfig = conn.get_wlan_ifconfig()
    Rssi = conn.get_wlan_rssi()
    net_data = {
        "IPv4": netConfig[0],
        "Subnet": netConfig[1],
        "Gateway": netConfig[2],
        "DNS": netConfig[3],
        "Rssi": Rssi
    }
    return net_data

@app.get('/net/config')
async def network_config(request):
    (valid, cfg_data) = await cfgmgr.get_json(["Country", "Hostname", "SSID"])
    if valid:
        cfg_data["PW"] = "********"
    else:
        cfg_data["PW"] = None
    return cfg_data

@app.put('/net/cmd')
async def network_cmd(request):
    req_json, err_msg = cmd_pre_check(request, ["setNetwork"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "setNetwork":
        if debug: print("Received Set Network command.")
        res, err = await init_json_from_cfg(cfgmgr, ["Hostname", "Country", "SSID", "PW"])
        if res is None:
            return err
        res = update_valid_json(req_json, "Hostname", "str", res, 1, 63, debug=debug)
        res = update_valid_json(req_json, "Country", "str", res, 2, 2, debug=debug)
        res = update_valid_json(req_json, "SSID", "str", res, 2, 32, debug=debug)
        res = update_valid_json(req_json, "PW", "str", res, 8, 63, debug=debug)
        return await cmd_post_check(res, cfgmgr, post_fct=conn.reconnect_wifi, debug=debug)  # Reconnect WiFi with new config (has 5 sec delay)

# Timing API
@app.get('/time/status')
async def timing_status(request):
    gmt = time.gmtime()
    synced = await conn.ntp_issynced()
    system = {"Synced": "On" if synced else "Off", "Unix": time.mktime(gmt)}
    utc = {"Year": gmt[0], "Month": gmt[1], "Day": gmt[2], "Hour": gmt[3], "Min": gmt[4], "Sec": gmt[5]}
    cet = await conn.cettime()
    if cet is None:
        local = {"Year": "None", "Month": "None", "Day": "None", "Hour": "None", "Min": "None", "Sec": "None"}
    else:
        local = {"Year": cet[0], "Month": cet[1], "Day": cet[2], "Hour": cet[3], "Min": cet[4], "Sec": cet[5]}
    rtc_time = {"System": system, "UTC": utc, "Local": local}
    return rtc_time

@app.get('/time/config')
async def timing_config(request):
    (valid, ntp_data) = await cfgmgr.get_json(["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"])
    return ntp_data

@app.put('/time/cmd')
async def timing_cmd(request):
    req_json, err_msg = cmd_pre_check(request, ["setTiming"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "setTiming":
        if debug: print("Received Set Timing command.")
        res, err = await init_json_from_cfg(cfgmgr, ["NTP_Host", "NTP_Offset_S", "NTP_Interv_H", "GMTOffset", "DSTOffset"])
        if res is None:
            return err
        res = update_valid_json(req_json, "NTP_Host", "str", res, 3, 1024, debug=debug)
        res = update_valid_json(req_json, "NTP_Offset_S", "int", res, -43200, 43200, debug=debug)
        res = update_valid_json(req_json, "NTP_Interv_H", "int", res, 1, 24, debug=debug)
        res = update_valid_json(req_json, "GMTOffset", "int", res, -43200, 43200, debug=debug)
        res = update_valid_json(req_json, "DSTOffset", "int", res, -43200, 43200, debug=debug)
        return await cmd_post_check(res, cfgmgr, post_asy_fct=conn.ntp_force_sync, debug=debug)  # resync NTP with new config

# Sensors API
@app.get('/sensors/status')
async def sensor_status(request):
    scd_meas = await scd_reader.get_data()
    sgp_meas = await sgp_reader.get_data()
    shtc_meas = await shtc_reader.get_data()
    mprls_meas = await mprls_reader.get_data()
    isl_meas = await isl_reader.get_data()
    meas_data = {
        "SCD30": {
            "CO2": scd_meas[_SCD30_CO2],
            "Temp": scd_meas[_SCD30_Temperature],
            "Hum": scd_meas[_SCD30_Humidity],
            "WetBulb": "None" if scd_meas[_SCD30_WetBulb] is None else scd_meas[_SCD30_WetBulb],
            "DewPoint": "None" if scd_meas[_SCD30_DewPoint] is None else scd_meas[_SCD30_DewPoint],
            "TS": scd_meas[_SCD30_Timestamp]
        },
        "SGP40": {
            "VOC": sgp_meas[_SGP40_VOC],
            "Raw": sgp_meas[_SGP40_RAW],
            "TS": sgp_meas[_SGP40_Timestamp]
        },
        "SHTC3": {
            "Temp": shtc_meas[_SHTC3_Temperature],
            "Hum": shtc_meas[_SHTC3_Humidity],
            "WetBulb": "None" if shtc_meas[_SHTC3_WetBulb] is None else shtc_meas[_SHTC3_WetBulb],
            "DewPoint": "None" if shtc_meas[_SHTC3_DewPoint] is None else shtc_meas[_SHTC3_DewPoint],
            "TS": shtc_meas[_SHTC3_Timestamp]
        },
        "MPRLS": {
            "Pres": mprls_meas[_MPRLS_Pressure],
            "TS": mprls_meas[_MPRLS_Timestamp]
        },
        "ISL29125": {
            "Red": isl_meas[_ISL29125_Red],
            "Green": isl_meas[_ISL29125_Green],
            "Blue": isl_meas[_ISL29125_Blue],
            "TS": isl_meas[_ISL29125_Timestamp]
        }
    }
    return meas_data

@app.get('/sensors/config')
async def sensor_config(request):
    try:
        scd30_conf = {
            "TempOffs": await scd_reader.get_temperature_offset(),
            "MeasInt": await scd_reader.get_measurement_interval(),
            "AmbPres": await scd_reader.get_ambient_pressure(),
            "Altitude": await scd_reader.get_altitude(),
            "ForceCalRef": await scd_reader.get_forced_recalibration_reference(),
            "SelfCal": toSwitch(await scd_reader.get_self_calibration_enabled())
            }
    except:
        scd30_conf = {
            "TempOffs": "None",
            "MeasInt": "None",
            "AmbPres": "None",
            "Altitude": "None",
            "ForceCalRef": "None",
            "SelfCal": "None"
            }
        
    (valid, shtc_conf) = await cfgmgr.get_json(["SHTCSampleInterv", "SHTCTempOffs", "SHTCFiltCoeff"])
    if not valid:
        shtc_conf = {
            "SHTCSampleInterv": "None",
            "SHTCTempOffs": "None",
            "SHTCFiltCoeff": "None"
            }

    (valid, mprls_conf) = await cfgmgr.get_json(["MPRLSSampleInterv", "MPRLSPressOffset", "MPRLSFiltCoeff"])
    if not valid:
        mprls_conf = {
            "MPRLSSampleInterv": "None",
            "MPRLSPressOffset": "None",
            "MPRLSFiltCoeff": "None"
            }
        
    isl_conf = {
        "ISLSampleInterv": await isl_reader.get_trigger_secs(),
        "ISLOperationMode": await isl_reader.get_operation_mode(),
        "ISLSensingRange": await isl_reader.get_sensing_range(),
        "ISLAdcResolution": await isl_reader.get_adc_resolution(),
        "ISLIrCompensation": await isl_reader.get_ir_compensation(),
        "ISLInterruptAssignment": await isl_reader.get_interrupt_assignment(),
        "ISLInterruptHighThres": await isl_reader.get_high_threshold(),
        "ISLInterruptLowThres": await isl_reader.get_low_threshold(),
        "ISLInterruptAutoClear": await isl_reader.get_irq_auto_clear(),
        "ISLPersistentControl": await isl_reader.get_persistent_control()
        }
        
    sensor_conf = {
        "SCD30": scd30_conf,
        "SHTC3": shtc_conf,
        "MPRLS": mprls_conf,
        "ISL29125": isl_conf
    }   
    return sensor_conf

@app.put('/sensors/cmd')
async def sensor_cmd(request):
    req_json, err_msg = cmd_pre_check(request, ["setSCD", "setSHTC", "setMPRLS", "setISL"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "setSCD":
        if debug: print("Received Set SCD30 Sensor command.")
        if debug: print(req_json)
        data = {}
        try:
            data["TempOffs"] = await scd_reader.get_temperature_offset()
            data["MeasInt"] = await scd_reader.get_measurement_interval(),
            data["AmbPres"] = await scd_reader.get_ambient_pressure(),
            data["Altitude"] = await scd_reader.get_altitude(),
            data["ForceCalRef"] = await scd_reader.get_forced_recalibration_reference(),
            data["SelfCal"] = await scd_reader.get_self_calibration_enabled(),
            data["ContMeas"] = True  # not readable from sensor, just as reference for parsing
            valid = True
        except:
            valid = False

        res, err = await init_json_from_cfg(cfgmgr, None, ext_json=(valid, data))
        if res is None:
            return err
        res = update_valid_json(req_json, "TempOffs", "float", res, 0.0, 655.35, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_temperature_offset, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "MeasInt", "int", res, 2, 1800, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_measurement_interval, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "AmbPres", "int", res, 700, 1400, special_val=[0], debug=debug)
        res = await set_sensor_value(res, scd_reader.set_ambient_pressure, cfgmgr, force=True, debug=debug)
        res = update_valid_json(req_json, "Altitude", "int", res, 0, 65535, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_altitude, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ForceCalRef", "int", res, 400, 2000, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_forced_recalibration_reference, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "SelfCal", "switch", res, None, None, debug=debug)
        res = await set_sensor_value(res, scd_reader.set_self_calibration_enabled, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ContMeas", "switch", res, None, None, debug=debug)  # only understands "Off"
        res = await set_sensor_value(res, scd_reader.stop_continuous_measurement, cfgmgr, debug=debug)
        return await cmd_post_check(res, None, debug=debug) # datamanager = None --> Don't write system config here
    
    if req_json["cmd"] == "setSHTC":
        if debug: print("Received Set SHTC3 Sensor command.")
        res, err = await init_json_from_cfg(cfgmgr, ["SHTCSampleInterv", "SHTCTempOffs", "SHTCFiltCoeff"])
        if res is None:
            return err
        res = update_valid_json(req_json, "SHTCSampleInterv", "int", res, 1, 3600, debug=debug)
        res = await set_sensor_value(res, shtc_reader.set_trigger_secs, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "SHTCTempOffs", "float", res, -10.0, 10.0, debug=debug)
        res = update_valid_json(req_json, "SHTCFiltCoeff", "float", res, 0.0, 1.0, special_val=[-1.0], debug=debug)
        return await cmd_post_check(res, cfgmgr, debug=debug)
    
    if req_json["cmd"] == "setMPRLS":
        if debug: print("Received Set MPRLS Sensor command.")
        res, err = await init_json_from_cfg(cfgmgr, ["MPRLSSampleInterv", "MPRLSPressOffset", "MPRLSFiltCoeff"])
        if res is None:
            return err
        res = update_valid_json(req_json, "MPRLSSampleInterv", "int", res, 1, 3600, debug=debug)
        res = await set_sensor_value(res, mprls_reader.set_trigger_secs, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "MPRLSPressOffset", "float", res, -500.0, 500.0, debug=debug)
        res = update_valid_json(req_json, "MPRLSFiltCoeff", "float", res, 0.0, 1.0, special_val=[-1.0], debug=debug)
        return await cmd_post_check(res, cfgmgr, debug=debug)

    if req_json["cmd"] == "setISL":
        if debug: print("Received Set ISL29125 Sensor command.")
        res, err = await init_json_from_cfg(cfgmgr, ["ISLSampleInterv", "ISLOperationMode", "ISLSensingRange", "ISLAdcResolution",
                                                     "ISLIrCompensation", "ISLInterruptAssignment", "ISLInterruptHighThres", 
                                                     "ISLInterruptLowThres", "ISLInterruptAutoClear", "ISLPersistentControl"])
        if res is None:
            return err
        res = update_valid_json(req_json, "ISLSampleInterv", "int", res, 1, 3600, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_trigger_secs, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLOperationMode", "int", res, 0, 7, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_operation_mode, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLSensingRange", "int", res, 0, 1, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_sensing_range, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLAdcResolution", "int", res, 0, 1, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_adc_resolution, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLIrCompensation", "int", res, -1, 63, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_ir_compensation, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLInterruptAssignment", "int", res, 0, 3, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_interrupt_assignment, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLInterruptHighThres", "int", res, 0, 65536, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_high_threshold, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLInterruptLowThres", "int", res, 0, 65536, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_low_threshold, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLInterruptAutoClear", "int", res, -1, 3600000, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_irq_auto_clear, cfgmgr, debug=debug)
        res = update_valid_json(req_json, "ISLPersistentControl", "int", res, 0, 3, debug=debug)
        res = await set_sensor_value(res, isl_reader.set_persistent_control, cfgmgr, debug=debug)
        return await cmd_post_check(res, cfgmgr, debug=debug)

# LED API
@app.get('/led/status')
async def led_config(request):
    pausetime = await pixel.get_override_led()
    return {"pauseTime": pausetime}

@app.get('/led/config')
async def led_config(request):
    (valid, cfg_data) = await cfgmgr.get_json(["LedAutoOn", "LedWifiOn", "LedAutoOnH", "LedAutoOnM", "LedAutoOffH", "LedAutoOffM", "LedAutoFlashBri",
                                               "LedAutoInterv", "LedAutoFlashDur", "LedWarnCO2", "LedWarnVOC", "LedWarnHum"])
    if valid:
        cfg_data["LedAutoOn"] = toSwitch(cfg_data["LedAutoOn"])
        cfg_data["LedWifiOn"] = toSwitch(cfg_data["LedWifiOn"])

    return cfg_data

@app.put('/led/cmd')
async def led_cmd(request):
    req_json, err_msg = cmd_pre_check(request, ["lightCmdLED", "pauseAutoLED", "setAutoLED", "setWiFiLED"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "lightCmdLED":
        if debug: print("Received LED Color command.")
        default = { "r": 0, "g": 0, "b": 0, "t": 1.0 }
        res, err = await init_json_from_cfg(cfgmgr, None, ext_json=(True, default))
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
        return await cmd_post_check(res, None, specialErr=err, debug=debug)  # don't save anything, use special error in case

    if req_json["cmd"] == "pauseAutoLED":
        if debug: print("Received Pause Auto LED command.")
        default = { "pauseTime": 0 }
        res, err = await init_json_from_cfg(cfgmgr, None, ext_json=(True, default))
        if res is None:
            return err
        res = update_valid_json(req_json, "pauseTime", "int", res, 0, 3600, debug=debug)
        values, valid = get_valid_values(res, ["pauseTime"])
        err = None
        if valid:
            await pixel.set_override_led(values["pauseTime"])
        else:
            err = "pauseLED"
        return await cmd_post_check(res, None, specialErr=err, debug=debug)  # don't save anything, use special error in case

    if req_json["cmd"] == "setAutoLED":
        if debug: print("Received Set Auto LED command.")
        res, err = await init_json_from_cfg(cfgmgr, ["LedAutoOn", "LedAutoOnH", "LedAutoOnM", "LedAutoOffH", "LedAutoOffM", "LedAutoFlashBri",
                                                     "LedAutoInterv", "LedAutoFlashDur", "LedWarnCO2", "LedWarnVOC", "LedWarnHum"])
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
        if debug: print("Received Set WiFi LED command.")
        res, err = await init_json_from_cfg(cfgmgr, ["LedWifiOn"])
        if res is None:
            return err
        res = update_valid_json(req_json, "LedWifiOn", "switch", res, None, None, debug=debug)
        res = await set_sensor_value(res, conn.set_wifi_led, cfgmgr, default=True, debug=debug)
        return await cmd_post_check(res, cfgmgr, debug=debug)

# System API
@app.get('/system/status')
async def system_status(request):
    system_data = {
        "Sys_Uptime": await sysfunct.get_uptime(),
        "Wifi_Uptime": await conn.get_wifi_uptime(),
        "NTP_LastSync": await conn.get_last_ntp_sync(),
        "SCD30_ErrCnt": await scd_reader.get_error_counter(),
        "SGP40_ErrCnt": await sgp_reader.get_error_counter(),
        "SHTC3_ErrCnt": await shtc_reader.get_error_counter(),
        "MPRLS_ErrCnt": await mprls_reader.get_error_counter(),
        "ISL29125_ErrCnt": await isl_reader.get_error_counter(),
        "Task_ErrCnt": await task_error_counter.get_counter(),
        "Task_LastErr": await last_task_err.getValue()
    }
    return system_data

@app.put('/system/cmd')
async def system_cmd(request):
    req_json, err_msg = cmd_pre_check(request, ["systemCmd"])
    if req_json is None:
        return err_msg
    if req_json["cmd"] == "systemCmd":
        if debug: print("Received System command.")
        default = { "content": "" }
        res, err = await init_json_from_cfg(cfgmgr, None, ext_json=(True, default))
        if res is None:
            return err
        res = update_valid_json(req_json, "content", "str", res, 0, 0, special_val=["reboot", "bootloader"], debug=debug) # only special values are valid
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
            else:
                err = "sysCmd"
        else:
            err = "sysCmd"
        return await cmd_post_check(res, None, specialErr=err, okDescr=descr, debug=debug)  # don't save anything, use special error in case

# Main Function
async def main():
    task_starters = []
    task_starters.append(sysfunct.start_asy_uptime_counter)   #  1st: start uptime counter
    task_starters.append(scd_reader.start_asy_read)           #  start sensor readers
    task_starters.append(scd_reader.start_asy_init)
    task_starters.append(sgp_reader.start_asy_read)
    
    task_starters.append(shtc_reader.start_asy_read)
    task_starters.append(shtc_reader.start_asy_trigger)
    task_starters.append(mprls_reader.start_asy_read)
    task_starters.append(mprls_reader.start_asy_trigger)
    
    task_starters.append(isl_reader.start_asy_read)
    task_starters.append(isl_reader.start_asy_trigger)
    task_starters.append(isl_reader.start_irq_handler)
    
    #task_starters.append(pixel.start_asy_neopixel_led_overl)  #  start LED functions
    #task_starters.append(pixel.start_asy_ext_cmd_watcher)
    #task_starters.append(pixel.start_asy_neopixel_signal)
    #task_starters.append(pixel.start_asy_auto_override)
    #task_starters.append(pixel.start_asy_airquality_signal)
    task_starters.append(conn.start_asy_wlan_connect)         #  start networking
    task_starters.append(conn.start_asy_ntp_client)
    task_starters.append(conn.start_asy_ntp_refresh)
    task_starters.append(conn.start_asy_uptime_counter)
    task_starters.append(start_asy_webserver)                 #  last: start webserver (depends on others started)

    timer_starters = []
    timer_starters.append(sysfunct.start_uptime_timer)
    timer_starters.append(scd_reader.start_timer)
    timer_starters.append(sgp_reader.start_timer)
    
    timer_starters.append(shtc_reader.start_timer)
    timer_starters.append(mprls_reader.start_timer)
    timer_starters.append(isl_reader.start_timer)
    
    timer_starters.append(conn.start_counter_timer)
    timer_starters.append(conn.start_ntp_timer)

    timer_sequencer(timer_starters, 1000)
    await timers_running.wait()

    tasks = []
    for starter in task_starters:
        tasks.append(starter())
        await asyncio.sleep(1.0 / len(task_starters))
    all_running = True

    await conn.ntp_force_sync() # first sync

    task_errors = 0
    while True:
        no_fail = True
        for n in range(0, len(tasks)):
            if tasks[n].done():
                await task_error_counter.increment()
                await last_task_err.setValue(n)
                task_errors += _TASK_FAIL_INCREMENT
                tasks[n] = task_starters[n]()
                no_fail = False
                if debug: print("Task wurde vorzeitig beendet - versuche Neustart!")

        if task_errors > _TASK_FAIL_MAX:
            all_running = False
            if debug: print("Mehrfache Task-Fehler, Neustart!")

        if (no_fail and (task_errors > 0)):
            task_errors -= 1
            if debug: print("Task Error Counter:", task_errors)

        if all_running:
            if debug: print("Alle Tasks laufen.")
            #watchdog.feed()
        await asyncio.sleep(_TASK_CHECK_TIME)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
