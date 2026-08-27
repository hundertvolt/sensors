import struct
import asyncio
import math
import math_helpers
import time
from machine import Timer
from micropython import const
from asy_uart import AsyUART, CRC16
from asy_uart_comm import UART_Comm
from async_manager import DataManager, LockedValue, TimeCounterManager

# communication commands
_UART_GET_MEASUREMENTS = const(0x20)
_UART_GET_BSEC_STATE = const(0x21)

_UART_GET_SYSTEM_STATE = const(0x22)
_UART_SYSTEM_STATE_SIZE = const(8)

_UART_SET_START_MEASUREMENT = const(0x30)
_UART_SET_BSEC_STATE = const(0x31)
_UART_SET_SYSTEM_RESET = const(0x32)
_UART_SET_TEMP_COMP = const(0x33)
_UART_SET_DEBUG_MODE = const(0x34)

# return states
_SYSTEM_MEAS_RUNNING = const(1)
_SYSTEM_MEAS_WAITING = const(0)
_SYSTEM_MEAS_ERROR = const(-1)

_SYSTEM_STATE_UPDATED = const(1)
_SYSTEM_STATE_DEFAULT = const(0)
_SYSTEM_STATE_ERROR = const(-1)

_BSEC_NO_ERROR = const(0)
_BME_NO_ERROR = const(0)

# system status indices
_SYSTEM_STATUS_MEAS_RUNNING = const(0)
_SYSTEM_STATUS_STATE_UPDATED = const(1)
_SYSTEM_STATUS_LAST_BSEC_ERROR = const(2)
_SYSTEM_STATUS_LAST_SENSOR_ERROR = const(3)
_SYSTEM_STATUS_SYSTEM_UPTIME = const(4)

# general params
_FRAM_VERIFY_MINS = const(60)
_ADDITIONAL_FIELDS = const(5)  # locally added datafields (wet bulb temperature, dew point, sea level pressure, timestamp, sensor uptime)
_MEAS_VALID_FLAG = const(-2)   # measurement valid flag is always the before-last
_MEAS_NEW_FLAG = const(-1)     # new measurement flag is always the last

# comm error IDs
_ERR_NO_ERROR = const(-1)
_ERR_GET_MEAS = const(20)
_ERR_GET_BSEC_STATE = const(21)
_ERR_START_MEAS = const(30)
_ERR_SET_BSEC_STATE = const(31)
_ERR_SET_RESET = const(32)
_ERR_SET_TEMP_COMP = const(33)

class BME688_Reader:
    def __init__(self, uart_id, tx, rx, asy_cfg_callback, bsec_num_datafields, t_h_p_indices,
                 ts_storage=None, external_th_comp=True, max_comm_err=5, baudrate=115200, rxbuf=32, txbuf=32, payload_size=20, timeout=1000,
                 trigger_sec=5, debug=False):
        self.bme = BSEC_UART(uart_id, tx, rx, baudrate=baudrate, rxbuf=rxbuf, txbuf=txbuf, payload_size=payload_size, timeout=timeout, debug=debug)
        self.meas_data = DataManager(bsec_num_datafields + _ADDITIONAL_FIELDS)
        self.last_sensor_errors = DataManager(2, default_value=_ERR_NO_ERROR)
        self.last_comm_errors = DataManager(2, default_value=_ERR_NO_ERROR)
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.main_ready = asyncio.Event()
        self.debug = debug
        self.max_comm_err = max_comm_err
        self.comm_err_count = 0
        self.sys_status = (0, 0, 0, 0, 0)
        self.cfg_callback = asy_cfg_callback  # expects [SampleInterval, TemperatureOffset, PressureOffset, TempHumFilterCoefficient,      
        # PressureFilterCoefficient, Altitude above sea level, mean atmospheric temperature, BackupPeriod(mins), MaxRestoreAge(mins), BackupWaitNTPSync(secs)])
        self.ts_storage = ts_storage  # timestamped backup storage (FRAM)
        self.last_backup = None
        self.restored_from = None
        self.reset = False
        self.ext_th_comp = external_th_comp  # True: compensate temperature in sensor. False: compensate temperature here.
        self.set_t_comp = None
        self.idx_temp = t_h_p_indices[0]
        self.idx_hum = t_h_p_indices[1]
        self.idx_press = t_h_p_indices[2]

    def start_asy_read(self):
        self.main_ready.clear()
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_bme())

    def start_asy_trigger(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._base_trigger())

    def start_timer(self):
        self.trigger_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.base_trigger_event.set())

    def stop_timer(self):
        self.trigger_timer.deinit()

    async def set_trigger_secs(self, value):
        await self.trigger_period.setValue(int(value))
        
    async def set_temp_comp(self, temperature):
        self.set_t_comp = temperature
        
    async def get_errors(self):
        counter = await self.error_counter.get_counter()
        last_bsec, last_sensor = await self.last_sensor_errors.get_data()
        last_comm, last_reset = await self.last_comm_errors.get_data()
        return counter, last_bsec, last_sensor, last_comm, last_reset
    
    async def clear_last_errors(self, flag):
        if flag:
            await self.last_sensor_errors.set_data([_ERR_NO_ERROR, _ERR_NO_ERROR])
            await self.last_comm_errors.set_data([_ERR_NO_ERROR, _ERR_NO_ERROR])
        
    async def get_mem_error_counters(self):
        if self.ts_storage is None:
            return 0, 0, -1
        return await self.ts_storage.get_error_counters()

    async def get_mem_status(self):
        return self.last_backup, self.restored_from

    async def get_data(self, startIdx=0, length=-1):
        return await self.meas_data.get_data(startIdx=startIdx, length=length)

    async def reset_config(self, flag):
        if flag:
            self.reset = True

    async def _base_trigger(self):
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.getValue():
                if self.main_ready.is_set():
                    self.main_ready.clear()
                    self.trigger_event.set()
                    if self.debug: print("BME688 sensor trigger, period:", self.trigger_counter)
                else:
                    if self.debug: print("BME688 sensor busy, waiting one trigger period:", self.trigger_counter)
                self.trigger_counter = 0

    async def _check_status(self, status, sys_on_none=False):
        if status is None:
            return sys_on_none
        self.sys_status = status               # in any case of valid status, store it in the system variable
        sys_ok = ( (status[_SYSTEM_STATUS_MEAS_RUNNING] != _SYSTEM_MEAS_ERROR) and     # check for reported system errors
                   (status[_SYSTEM_STATUS_STATE_UPDATED] != _SYSTEM_STATE_ERROR) )
        if not sys_ok:                         # store last errors if system in error
            await self.last_sensor_errors.set_data([status[_SYSTEM_STATUS_LAST_BSEC_ERROR],
                                             status[_SYSTEM_STATUS_LAST_SENSOR_ERROR]])
        return sys_ok

    async def _check_get_result(self, result, callerId):
        (data, status) = result
        last_comm, last_reset = await self.last_comm_errors.get_data()
        if ( (data is None) or (status is None) ): # something went wrong in the communication
            data = None                            # invalidate data if system status is unknown
            last_comm = callerId
            self.comm_err_count += 2               # increment by 2 for every error, decerement by 1 for each successful communication
            if self.debug: print("Comm error count increased to", self.comm_err_count)
            if self.comm_err_count >= (2 * self.max_comm_err):
                last_reset = callerId
                await self.last_comm_errors.set_data([last_comm, last_reset])
                return False, None                 # maximum comm error count reached means severe error
        else:                                      # valid communication
            if self.comm_err_count > 0:
                self.comm_err_count -= 1
                if self.debug: print("Comm error count decreased to", self.comm_err_count)

        sys_ok = await self._check_status(status, sys_on_none=True) # allow retries on None status
        if not sys_ok:
            last_reset = callerId
        await self.last_comm_errors.set_data([last_comm, last_reset])
        return sys_ok, data

    async def _check_set_result(self, result, callerId):
        comm_ok = True
        (success, status) = result
        last_comm, last_reset = await self.last_comm_errors.get_data()
        if ( (not success) or (status is None) ):  # something went wrong in the communication
            comm_ok = False
            last_comm = callerId
            self.comm_err_count += 2               # increment by 2 for every error, decerement by 1 for each successful communication
            if self.debug: print("Comm error count increased to", self.comm_err_count)
            if self.comm_err_count >= (2 * self.max_comm_err):
                last_reset = callerId
                await self.last_comm_errors.set_data([last_comm, last_reset])
                return False, False                # maximum comm error count reached means severe error
        else:                                      # valid communication
            if self.comm_err_count > 0:
                self.comm_err_count -= 1
                if self.debug: print("Comm error count decreased to", self.comm_err_count)

        sys_ok = await self._check_status(status, sys_on_none=True) # allow retries on None status
        if not sys_ok:
            last_reset = callerId
        await self.last_comm_errors.set_data([last_comm, last_reset])
        return sys_ok, comm_ok

    async def _trigger_reset(self):
        err = False
        try:
            success, status = await self.bme.reset()
        except:
            err = True
            if self.debug: print("Exception in BME688 reset!")
        if not success:
            err = True
            if self.debug: print("BME688 reset command not successful!")
        if not await self._check_status(status):  # returning "None" means error here
            err = True
            if self.debug: print("BME688 in error or unknown state after reset!")
        if err:
            await self.error_counter.increment()
            await self.last_comm_errors.set_data([_ERR_SET_RESET, _ERR_SET_RESET])
            return False
        return True

    async def read_bme(self):
        error = False
        backup_counter = 0
        config_init = 1
        config_write = 1
        Timestamp = time.mktime(time.gmtime())
        self.comm_err_count = 0
        self.last_backup = None
        self.restored_from = None
        self.sys_status = (_SYSTEM_MEAS_WAITING, _SYSTEM_STATE_DEFAULT, _BSEC_NO_ERROR, _BME_NO_ERROR, 0)
        num_datafields = await self.meas_data.get_size()
        num_datafields -= _ADDITIONAL_FIELDS

        if self.ts_storage is None:
            bsec_state_size = None
        else:  # get expected size of BSEC state from memory size
            bsec_state_size = await self.ts_storage.get_size()

        try:
            success, status = await self.bme.setup(num_datafields, bsec_state_size=bsec_state_size)
        except:
            success = False
            status = None
        if not success:
            error = True
        if not await self._check_status(status):
            error = True
        del num_datafields, bsec_state_size, success, status

        if not await self.bme.set_debug(self.debug):
            error = True

        (cfg_valid, [SInt, TOffs, POffs, THFiltCoeff, PFiltCoeff, SeaLevel, AtmTemp, BackupPer, BackupAge, wait_ntp]) = await self.cfg_callback()
        if cfg_valid:
            await self.trigger_period.setValue(SInt)
            self.set_t_comp = TOffs if self.ext_th_comp else None
            if (self.ts_storage is not None) and (BackupPer > 0): # backup verification period setting
                await self.ts_storage.set_verify(int(math.ceil((10 * _FRAM_VERIFY_MINS) / BackupPer) * 0.1))
            if 1 <= wait_ntp <= 600:  # wait ntp between 1sec and 10mins
                config_init = wait_ntp
                config_write = wait_ntp
        else:
            error = True
        del cfg_valid, SInt, TOffs, POffs, THFiltCoeff, PFiltCoeff, SeaLevel, AtmTemp, BackupPer, BackupAge, wait_ntp

        if error:
            await self.error_counter.increment()
            if self.debug: print("Error reading BME688 config data / setting sensor at startup!")
            return False
        del error
        self.main_ready.set()
        while True:
            await self.trigger_event.wait()
            measurements = None
            (cfg_valid, [SInt, TOffs, POffs, THFiltCoeff, PFiltCoeff, SeaLevel, AtmTemp, BackupPer, BackupAge, wait_ntp]) = await self.cfg_callback()
            del SInt
            if not cfg_valid:
                if self.debug: print("Error reading BME688 config data!")
                TOffs = 0.0
                POffs = 0.0
                THFiltCoeff = 0.0
                PFiltCoeff = 0.0
                BackupPer = 0
                BackupAge = 0
                wait_ntp = 1
                serialize = False
                await self.error_counter.increment()

            if self.reset:
                if self.debug: print("BME688 Reset / Clear Storage Trigger")
                if self.ts_storage is not None:
                    if not await self.ts_storage.clear():
                        await self.error_counter.increment()
                        if self.debug: print("BME688 Fehler beim FRAM löschen!")
                if not await self._trigger_reset():
                    if self.debug: print("BME688 reset failed, cancelling task!")
                    return False
                self.reset = False
                
            temp_ts = None
            while True:
                try:
                    temp_ts = time.mktime(time.gmtime())
                    res = await self.bme.get_measurements()
                except:
                    temp_ts = None
                    res = (None, None)
                sys_ok, measurements = await self._check_get_result(res, _ERR_GET_MEAS)  # allow retry on comm failures
                if sys_ok and (measurements is not None):
                    Timestamp = temp_ts
                    break
                if not sys_ok:
                    await self.error_counter.increment()
                    if self.debug: print("BME688 get_measurements in error state, triggering reset!")
                    if not await self._trigger_reset():
                        if self.debug: print("BME688 reset failed, cancelling task!")
                        return False
            del temp_ts

            if (config_init == 0 and                                                       # system is not in init phase
                self.sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_WAITING and   # measurement not yet started
                self.sys_status[_SYSTEM_STATUS_STATE_UPDATED] == _SYSTEM_STATE_DEFAULT):   # no config uploaded yet --> all together True when sensor was reset
                if self.debug: print("BME688 was reset; start initialization.")
                if await self.bme.set_debug(self.debug):
                    backup_counter = 0
                    config_init = wait_ntp
                    config_write = wait_ntp
                    self.last_backup = None
                    self.restored_from = None
                    self.set_t_comp = TOffs
                else:
                    await self.error_counter.increment()
                    if self.debug: print("Error setting BME688 debug prints at re-initialization, triggering reset!")
                    if not await self._trigger_reset():
                        if self.debug: print("BME688 reset failed, cancelling task!")
                        return False

            if (cfg_valid and config_init > 0):     # valid config and in init phase
                    start_measurement = False
                    bsec_state = None
                    ts = -1
                    age = None
                    if self.ts_storage is None:
                        config_init = 0
                        start_measurement = True  # Messung direkt starten
                    else:
                        if self.debug: print("BME688 Config Backup laden Trigger")
                        config_init -= 1
                        ts, age, bsec_state = await self.ts_storage.read()  # any value returns as None if not valid
                        if bsec_state is None:
                            if self.debug: print("BME688 Kein Backup gefunden!")
                            config_init = 0
                            start_measurement = True  # Messung direkt starten
                        else:  # backup found
                            if ts is None:
                                if self.debug: print("BME688 Backup ohne Zeitstempel geladen")
                                config_init = 0
                                ts = -1
                                start_measurement = True
                            else: # backup has valid timestamp
                                if age is None:
                                    if config_init > 0:
                                        if self.debug: print("BME688 Backup mit Zeitstempel gefunden, NTP Wartezeit:", config_init)
                                        bsec_state = None
                                else:
                                    if self.debug: print("BME688 Backup mit Zeitstempel geladen")
                                    config_init = 0
                                    start_measurement = True  # Messung in jedem Fall starten
                                    if (BackupAge > 0) and (age > (60 * BackupAge)):
                                        if self.debug: print("BME688 Backup ist zu alt")
                                        bsec_state = None

                    if start_measurement:
                        if bsec_state is not None:
                            while True:
                                try:
                                    res = await self.bme.set_bsec_state(bsec_state)
                                except:
                                    res = (False, None)
                                sys_ok, comm_ok = await self._check_set_result(res, _ERR_SET_BSEC_STATE)  # internally allows some retries on comm failures
                                if sys_ok and comm_ok:
                                    self.restored_from = ts
                                    if self.debug: print("BME688 BSEC state restored.")
                                    break
                                if not sys_ok:
                                    await self.error_counter.increment()
                                    if self.debug: print("BME688 does not update state or is in error, triggering reset!")
                                    if not await self._trigger_reset():
                                        if self.debug: print("BME688 reset failed, cancelling task!")
                                        return False

                        # start measurement now
                        while True:
                            try:
                                res = await self.bme.start_measurement()
                            except:
                                res = (False, None)
                            sys_ok, comm_ok = await self._check_set_result(res, _ERR_START_MEAS)  # internally allows some retries on comm failures
                            if sys_ok and comm_ok:
                                if self.debug: print("BME688 Measurement started.")
                                break
                            if not sys_ok:
                                await self.error_counter.increment()
                                if self.debug: print("BME688 does not start or is in error, triggering reset!")
                                if not await self._trigger_reset():
                                    if self.debug: print("BME688 reset failed, cancelling task!")
                                    return False
                    del ts, age, start_measurement, bsec_state

            if self.set_t_comp is not None:
                if self.debug: print("BME688 setting BSEC temperature compensation.")
                measurements = None # invalidate measurements until compensation is set
                while True:
                    try:
                        res = await self.bme.set_temp_comp(self.set_t_comp)
                    except:
                        res = (False, None)
                    sys_ok, comm_ok = await self._check_set_result(res, _ERR_SET_TEMP_COMP)  # internally allows some retries on comm failures
                    if sys_ok and comm_ok:
                        self.set_t_comp = None
                        break
                    if not sys_ok:
                        await self.error_counter.increment()
                        if self.debug: print("BME688 set_temp_comp in error state, triggering reset!")
                        if not await self._trigger_reset():
                            if self.debug: print("BME688 reset failed, cancelling task!")
                            return False

            if (cfg_valid and
                self.sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
                backup_counter += await self.trigger_period.getValue()
                if (self.ts_storage is not None) and (BackupPer > 0) and (backup_counter >= (60 * BackupPer)):
                    if self.debug: print("BME688 Backup Trigger.")
                    backup_counter = 0
                    bsec_state = None
                    while True:
                        try:
                            res = await self.bme.get_bsec_state()
                        except:
                            res = (None, None)
                        sys_ok, bsec_state = await self._check_get_result(res, _ERR_GET_BSEC_STATE)  # allow retry on comm failures
                        if sys_ok and (bsec_state is not None):
                            break
                        if not sys_ok:
                            await self.error_counter.increment()
                            if self.debug: print("BME688 does not send state or is in error, triggering reset!")
                            if not await self._trigger_reset():
                                if self.debug: print("BME688 reset failed, cancelling task!")
                                return False
                    current_verify = await self.ts_storage.get_verify()  # check storage verification period settings
                    desired_verify = int(math.ceil((10 * _FRAM_VERIFY_MINS) / BackupPer) * 0.1)
                    if current_verify != desired_verify:
                        await self.ts_storage.set_verify(desired_verify)
                    del current_verify, desired_verify

                    if (bsec_state is not None and
                        self.sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):  # still running without error or reset occured
                        if config_write > 0:
                            config_write -= await self.trigger_period.getValue()
                            if config_write < 0: config_write = 0
                        if self.debug: print("BME688 Schreibe Backup.")
                        require_ntp = (config_write > 0)
                        ntp_synced, ts, res = await self.ts_storage.write(bsec_state, require_ntp=require_ntp)
                        if require_ntp:
                            if ntp_synced:
                                config_write = wait_ntp
                                self.last_backup = ts
                                if self.debug: print("BME688 Backup mit Zeitstempel geschrieben.")
                            else:
                                res = True
                                backup_counter = 60 * BackupPer  # retrigger next iteration
                                if self.debug: print("BME688 Backup NTP Wartezeit:", config_write)
                        else:  # require_ntp
                            self.last_backup = ts
                            if ntp_synced:
                                config_write = wait_ntp
                                if self.debug: print("BME688 Backup wieder mit Zeitstempel geschrieben.")
                            else:
                                if self.debug: print("BME688 Backup ohne Zeitstempel geschrieben.")
                        if not res:
                            await self.error_counter.increment()
                            if self.debug: print("BME688 Schreibfehler beim Backup!")
                        del require_ntp, ntp_synced, ts, res
                    del bsec_state
            if backup_counter >= 100000: # # counts seconds, resets at 86400 = 1 day, give it some more space
                backup_counter = 0

            if (measurements is not None and
                self.sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
                if measurements[_MEAS_VALID_FLAG] > 0:    # valid
                    if measurements[_MEAS_NEW_FLAG] > 0:  # new
                        t_meas = measurements[self.idx_temp]
                        h_meas = measurements[self.idx_hum]
                        p_meas = measurements[self.idx_press]
                        if not self.ext_th_comp:  # local temperature and relative humidity compensation
                            tc = t_meas - TOffs
                            rh = None  #  temperature offset compensation for humidity
                            ah = math_helpers.abs_humidity(t_meas, h_meas)
                            if ah is not None:
                                rh = math_helpers.rel_humidity(tc, ah)
                            if rh is None:
                                rh = h_meas
                                if self.debug: print("Error compensating BME688 humidity data!")
                            t_meas = tc
                            h_meas = rh
                            del tc, rh, ah
                        p_meas -= POffs  # pressure offset compensation

                        if THFiltCoeff > 0.0:  # optional first-order lowpass filter for temperature and humidity
                            if THFiltCoeff > 1.0: FiltCoeff = 1.0
                            [t_old] = await self.meas_data.get_data(startIdx=self.idx_temp, length=1)
                            [h_old] = await self.meas_data.get_data(startIdx=self.idx_hum, length=1)
                            if (t_old is not None) and (h_old is not None):
                                t_meas = t_old + (THFiltCoeff * (t_meas - t_old))
                                h_meas = h_old + (THFiltCoeff * (h_meas - h_old))
                        
                        if PFiltCoeff > 0.0:  # optional first-order lowpass filter for pressure
                            if PFiltCoeff > 1.0: PFiltCoeff = 1.0
                            [p_old] = await self.meas_data.get_data(startIdx=self.idx_press, length=1)
                            if p_old is not None:
                                p_meas = p_old + (PFiltCoeff * (p_meas - p_old))
                        
                        meas_list = list(measurements[0:-2])  # all measurements but valid and new flags excluded
                        meas_list[self.idx_temp] = t_meas     # overwrite processed values
                        meas_list[self.idx_hum] = h_meas
                        meas_list[self.idx_press] = p_meas
                        meas_list += [math_helpers.wet_bulb_temperature(t_meas, h_meas),
                                      math_helpers.dew_point(t_meas, h_meas),
                                      math_helpers.altitude_baro(p_meas, -SeaLevel, AtmTemp),
                                      self.sys_status[_SYSTEM_STATUS_SYSTEM_UPTIME],
                                      Timestamp]
                        await self.meas_data.set_data(meas_list)
                        del meas_list
                else: # not valid
                    num_datafields = await self.meas_data.get_size()
                    await self.meas_data.set_data([None] * num_datafields)
                    del num_datafields
            del cfg_valid, measurements, TOffs, POffs, THFiltCoeff, PFiltCoeff, SeaLevel, AtmTemp, BackupPer, BackupAge, wait_ntp
            self.main_ready.set()

class BSEC_UART:
    def __init__(self, uart_id, tx, rx, baudrate=115200, rxbuf=64, txbuf=64, payload_size=48, timeout=1000, debug=False):
        self.crc16 = CRC16()
        self.timeout = timeout
        self.debug = debug
        self.bsec_state_size = None
        self.num_datafields = 0
        self.uart = AsyUART(uart_id, tx, rx, baudrate=baudrate, rxbuf=rxbuf, txbuf=64, crc=self.crc16)
        self.comm = UART_Comm(self.uart, payload_size=payload_size, timeout=self.timeout, debug=debug)

    async def setup(self, num_datafields, bsec_state_size=None):
        self.num_datafields = num_datafields  # 32bit float -> 4 bytes per measurement
        self.bsec_state_size = bsec_state_size
        if self.debug: print("BSEC start setup sequence, expected BSEC state size:", self.bsec_state_size)
        await self.comm.clear()
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] != _SYSTEM_MEAS_WAITING) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] != _SYSTEM_STATE_DEFAULT) ):
            if self.debug: print("BSEC System is not in idle state, resetting!")
            return await self.reset()
        return True, sys_status

    async def get_measurements(self):
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return None, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_ERROR) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] == _SYSTEM_STATE_ERROR) ):
            if self.debug: print("System is in error state!")
            return None, sys_status
        if self.debug: print("Issuing get measurements command")
        res = await self.comm.uart_get(_UART_GET_MEASUREMENTS, exp_size=((4 * self.num_datafields) + 4))
        if res is None:    # 32bit float -> 4 bytes per measurement + 2x 2 bytes
            if self.debug: print("Get Measurements returns None!")
            return None, sys_status
        try:  # number of floats to be decoded + valid, new_data (2x uint16t always at the end)
            measurements = struct.unpack(self.num_datafields * "f" + "HH", res)
        except:
            measurements = None
            if self.debug: print("Measurements unpacking failed!")
        return measurements, sys_status

    async def get_bsec_state(self):
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return None, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_ERROR) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] == _SYSTEM_STATE_ERROR) ):
            if self.debug: print("System is in error state!")
            return None, sys_status
        if self.debug: print("Issuing get BSEC state command")
        bsec_state = await self.comm.uart_get(_UART_GET_BSEC_STATE, exp_size=self.bsec_state_size)
        return bsec_state, sys_status

    async def get_system_status(self):
        if self.debug: print("Issuing get system state command")
        res = await self.comm.uart_get(_UART_GET_SYSTEM_STATE, exp_size=_UART_SYSTEM_STATE_SIZE)
        if res is None:
            if self.debug: print("System state returns None!")
            return None
        try:
            sys_status = struct.unpack("bbbbL", res)
        except:
            sys_status = None
            if self.debug: print("System state unpacking failed!")
        return sys_status

    async def start_measurement(self):
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
            if self.debug: print("Measurement already running!")
            return True, sys_status
        if (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_ERROR):
            if self.debug: print("Measurement in error state!")
            return False, sys_status
        if self.debug: print("Issuing start measurement command")
        res = await self.comm.uart_set(_UART_SET_START_MEASUREMENT, None)
        sys_status = await self.get_system_status()
        if ((not res) or (sys_status is None)):
            print("Error issuing start command or reading system status!")
            return res, sys_status
        if (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
            if self.debug: print("Measurement successfully started")
            return True, sys_status
        if self.debug: print("Measurement could not be started!")
        return False, sys_status

    async def set_bsec_state(self, state):
        if self.debug: print("Issuing set BSEC state command")
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] != _SYSTEM_MEAS_WAITING) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] != _SYSTEM_STATE_DEFAULT) ):
            if self.debug: print("BSEC Set State: System running / error or already updated / update error!")
            return False, sys_status
        res = await self.comm.uart_set(_UART_SET_BSEC_STATE, state)
        sys_status = await self.get_system_status()
        if ((not res) or (sys_status is None)):
            print("Error setting BSEC state or reading system status!")
            return res, sys_status
        if self.debug: print("Send set BSEC state command successful")
        return True, sys_status

    async def set_temp_comp(self, temperature):
        if self.debug: print("Issuing Set Temperature Compensation command")
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_ERROR) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] == _SYSTEM_STATE_ERROR) ):
            if self.debug: print("Set Temperature Compensation: System or state is in error!")
            return False, sys_status
        temperature = temperature if temperature <= 100 else 100
        temperature = temperature if temperature >= -100 else -100
        temperature_bytes = struct.pack("l", int(temperature * 1000))
        res = await self.comm.uart_set(_UART_SET_TEMP_COMP, temperature_bytes)
        sys_status = await self.get_system_status()
        if ((not res) or (sys_status is None)):
            print("Error setting temperature compensation or reading system status!")
            return res, sys_status
        if self.debug: print("Send Set Temperature Compensation command successful")
        return True, sys_status

    async def reset(self):
        if self.debug: print("Issuing reset command")
        if not await self.comm.uart_set(_UART_SET_SYSTEM_RESET, None):
            return False, None
        await asyncio.sleep(3) # give reset 3s time and then clear buffers
        await self.comm.clear()
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if self.debug: print("Reset successful")
        return True, sys_status

    async def set_debug(self, mode):
        if self.debug: print("Issuing set debug command")
        if mode:
            cmd = struct.pack("b", 1)
        else:
            cmd = struct.pack("b", 0)
        if not await self.comm.uart_set(_UART_SET_DEBUG_MODE, cmd):
            print("Error setting debug mode!")
            return False
        return True
        # no system status dependency here, as it's the debug console prints only
        # and they should especially work in case of system status errors

