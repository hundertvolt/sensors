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
_ADDITIONAL_FIELDS = const(4)  # locally added datafields (wet bulb temperature, dew point, timestamp, sensor uptime)
_MEAS_VALID_FLAG = const(-2)   # measurement valid flag is always the before-last
_MEAS_NEW_FLAG = const(-1)     # new measurement flag is always the last

class BME688_Reader:
    def __init__(self, uart_id, tx, rx, asy_cfg_callback, bsec_num_datafields,
                 ts_storage=None, t_h_indices=None, max_comm_err=5, baudrate=115200, rxbuf=64, txbuf=64, payload_size=48, timeout=1000,
                 trigger_sec=5, debug=False):
        self.bme = BSEC_UART(uart_id, tx, rx, baudrate=baudrate, rxbuf=rxbuf, txbuf=txbuf, payload_size=payload_size, timeout=timeout, debug=debug)
        self.meas_data = DataManager(bsec_num_datafields + _ADDITIONAL_FIELDS)
        self.last_errors = DataManager(2)
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.main_ready = asyncio.Event()
        self.debug = debug
        self.max_comm_err = max_comm_err
        self.cfg_callback = asy_cfg_callback    # expects [backup period(mins), max restore age(mins), backup wait time for ntp synced(secs)]
        self.ts_storage = ts_storage  # timestamped backup storage (FRAM)
        self.last_backup = None
        self.restored_from = None
        self.reset = False
        self.debug = debug
        if t_h_indices is not None:
            self.idx_temp = t_h_indices[0]
            self.idx_hum = t_h_indices[1]
        else:  # indices of temperature and humidity in the returned struct from sensor for wet bulb temp and dew point
            self.idx_temp = None
            self.idx_hum = None

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

    async def get_error_counter(self):
        return await self.error_counter.get_counter()
    
    async def get_last_errors(self):
        return await self.last_errors.get_data()
     
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

    async def _check_status(self, status):
        if status is None:
            return False
        res = ( (status[_SYSTEM_STATUS_MEAS_RUNNING] != _SYSTEM_MEAS_ERROR) and
                (status[_SYSTEM_STATUS_STATE_UPDATED] != _SYSTEM_STATE_ERROR) )
        if not res:
            await self.last_errors.set_data([status[_SYSTEM_STATUS_LAST_BSEC_ERROR],
                                             status[_SYSTEM_STATUS_LAST_SENSOR_ERROR]])
        return res
 
    async def _trigger_reset(self):
        try:
            success, status = await self.bme.reset()
        except:
            if self.debug: print("Exception in BME688 reset!")
            await self.error_counter.increment()
            return None
        if not success:
            if self.debug: print("BME688 reset command not successful!")
            await self.error_counter.increment()
            return None
        if not await self._check_status(status):
            await self.error_counter.increment()
            if self.debug: print("BME688 in error after reset!")
            return None
        return status

    async def read_bme(self):
        error = False
        backup_counter = 0
        config_init = 1
        config_write = 1
        
        num_datafields = await self.meas_data.get_size()
        num_datafields -= _ADDITIONAL_FIELDS
        
        if self.ts_storage is None:
            bsec_state_size = None
        else:  # get expected size of BSEC state from memory size
            bsec_state_size = await self.ts_storage.get_size()

        try:
            success, sys_status = await self.bme.setup(num_datafields, bsec_state_size=bsec_state_size)
        except:
            success = False
            sys_status = None
        if not success:
            error = True
        if not await self._check_status(sys_status):
            error = True
        del num_datafields, bsec_state_size

        (valid, [backup_period, backup_maxage, wait_ntp]) = await self.cfg_callback()
        if valid:
            if (self.ts_storage is not None) and (backup_period > 0): # backup verification period setting
                await self.ts_storage.set_verify(int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period) * 0.1))
            if 1 <= wait_ntp <= 600:  # wait ntp between 1sec and 10mins
                config_init = wait_ntp
                config_write = wait_ntp
        else:
            error = True
        del wait_ntp
        
        if error:
            await self.error_counter.increment()
            if self.debug: print("Error reading BME688 config data / setting sensor at startup!")
            return False
        del error
        self.main_ready.set()
        while True:
            await self.trigger_event.wait()
            
            (backup_cfg_valid, [backup_period, backup_maxage, wait_ntp]) = await self.cfg_callback()
            if not backup_cfg_valid:
                if self.debug: print("Error reading BME688 config data!")
                await self.error_counter.increment()
                serialize = False
            
            if self.reset:
                if self.debug: print("BME688 Reset Trigger")
                if self.ts_storage is not None:
                    if not await self.ts_storage.clear():
                        await self.error_counter.increment()
                        if self.debug: print("BME688 Fehler beim FRAM löschen!")
                sys_status = await self._trigger_reset()
                if sys_status is None:
                    if self.debug: print("BME688 reset failed, cancelling task!")
                    return False
                self.reset = False

            Timestamp = time.mktime(time.gmtime())
            try:
                measurements, sys_status = await self.bme.get_measurements()
            except:
                measurements = None
                sys_status = None
            if not await self._check_status(sys_status):
                await self.error_counter.increment()
                if self.debug: print("BME688 get_measurements in error state, triggering reset!")
                sys_status = await self._trigger_reset()
                if sys_status is None:
                    if self.debug: print("BME688 reset failed, cancelling task!")
                    return False
            
            if (config_init == 0 and                                                  # system is not in init phase
                sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_WAITING and   # measurement not yet started
                sys_status[_SYSTEM_STATUS_STATE_UPDATED] == _SYSTEM_STATE_DEFAULT):   # no config uploaded yet --> all together True when sensor was reset
                if self.debug: print("BME688 was reset; start initialization.")
                backup_counter = 0
                config_init = wait_ntp
                config_write = wait_ntp
                self.last_backup = None
                self.restored_from = None
                
            if (backup_cfg_valid and config_init > 0):     # valid config and in init phase
                    start_measurement = False
                    bsec_state = None
                    ts = None
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
                            else: # backup has valid timestamp
                                if age is None:
                                    if config_init > 0:
                                        if self.debug: print("BME688 Backup mit Zeitstempel gefunden, NTP Wartezeit:", config_init)
                                        bsec_state = None
                                else:
                                    if self.debug: print("BME688 Backup mit Zeitstempel geladen")
                                    config_init = 0
                                    start_measurement = True  # Messung in jedem Fall starten
                                    if (backup_maxage > 0) and (age > (60 * backup_maxage)):
                                        if self.debug: print("BME688 Backup ist zu alt")
                                        bsec_state = None
                                        
                    if start_measurement:
                        cmd_tries = 0
                        success = False  # only make sure the variable exists for later "del"
                        if bsec_state is not None:
                            while True:
                                try:
                                    success, sys_status = await self.bme.set_bsec_state(bsec_state)
                                except:
                                    success = False
                                    sys_status = None
                                if (not await self._check_status(sys_status)) or (cmd_tries >= self.max_comm_err):
                                    await self.error_counter.increment()
                                    if self.debug: print("BME688 does not update state or is in error, triggering reset!")
                                    sys_status = await self._trigger_reset()
                                    if sys_status is None:
                                        if self.debug: print("BME688 reset failed, cancelling task!")
                                        return False
                                if success:
                                    self.restored_from = ts
                                    break
                                if self.debug: print("BME688 set state command failed!")
                                await self.error_counter.increment()
                                cmd_tries += 1
                                
                        # start measurement now
                        cmd_tries = 0
                        while True:
                            try:  
                                success, sys_status = await self.bme.start_measurement()
                            except:
                                success = False
                                sys_status = None
                            if (not await self._check_status(sys_status)) or (cmd_tries >= self.max_comm_err):
                                await self.error_counter.increment()
                                if self.debug: print("BME688 does not start or is in error, triggering reset!")
                                sys_status = await self._trigger_reset()
                                if sys_status is None:
                                    if self.debug: print("BME688 reset failed, cancelling task!")
                                    return False
                            if success:
                                break
                            if self.debug: print("BME688 start measurement command failed!")
                            await self.error_counter.increment()
                            cmd_tries += 1
                        del cmd_tries, success
                    del ts, age, start_measurement, bsec_state
    
            if (backup_cfg_valid and
                sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
                backup_counter += await self.trigger_period.getValue()
                if (self.ts_storage is not None) and (backup_period > 0) and (backup_counter >= (60 * backup_period)):
                    if self.debug: print("BME688 Backup Trigger.")
                    backup_counter = 0
                    bsec_state = None
                    cmd_tries = 0
                    while True:
                        try:  
                            bsec_state, sys_status = await self.bme.get_bsec_state()
                        except:
                            bsec_state = None
                            sys_status = None
                        if (not await self._check_status(sys_status)) or (cmd_tries >= self.max_comm_err):
                            await self.error_counter.increment()
                            if self.debug: print("BME688 does not send state or is in error, triggering reset!")
                            sys_status = await self._trigger_reset()
                            if sys_status is None:
                                if self.debug: print("BME688 reset failed, cancelling task!")
                                return False
                        if bsec_state is not None:
                            break
                        if self.debug: print("BME688 get BSEC state command failed!")
                        await self.error_counter.increment()
                        cmd_tries += 1
                    del cmd_tries
                    
                    current_verify = await self.ts_storage.get_verify()  # check storage verification period settings
                    desired_verify = int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period) * 0.1)
                    if current_verify != desired_verify:
                        await self.ts_storage.set_verify(desired_verify)
                    del current_verify, desired_verify
                    
                    if (bsec_state is not None and 
                        sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):  # still running without error or reset occured
                        if config_write > 0:
                            config_write -= 1
                        if self.debug: print("BME688 Schreibe Backup.")
                        require_ntp = (config_write > 0)
                        ntp_synced, ts, res = await self.ts_storage.write(bsec_state, require_ntp=require_ntp)
                        if require_ntp:
                            if ntp_synced:
                                config_write = 0
                                self.last_backup = ts
                                if self.debug: print("BME688 Backup mit Zeitstempel geschrieben.")
                            else:
                                res = True
                                backup_counter = 60 * backup_period  # retrigger next iteration
                                if self.debug: print("BME688 Backup NTP Wartezeit:", config_write)
                        else:  # require_ntp
                            self.last_backup = ts
                            if self.debug: print("BME688 Backup ohne Zeitstempel geschrieben.")
                        if not res:
                            await self.error_counter.increment()
                            if self.debug: print("BME688 Schreibfehler beim Backup!")
                        del require_ntp, ntp_synced, ts, res
                    del bsec_state
            if backup_counter >= 100000: # # counts seconds, resets at 86400 = 1 day, give it some more space
                backup_counter = 0
            
            if (measurements is not None and
                sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
                print(measurements)
                if measurements[_MEAS_VALID_FLAG] == 0:    # valid
                    if measurements[_MEAS_NEW_FLAG] > 0:  # new
                        if (self.idx_temp is not None) and (self.idx_hum is not None):
                            await self.meas_data.set_data(list(measurements[0:-2]) +
                                [math_helpers.wet_bulb_temperature(measurements[self.idx_temp], measurements[self.idx_hum]),
                                 math_helpers.dew_point(measurements[self.idx_temp], measurements[self.idx_hum]),
                                 Timestamp,
                                 sys_status[_SYSTEM_STATUS_SYSTEM_UPTIME]])
                        else:
                            await self.meas_data.set_data(list(measurements[0:-2]) +
                                [None,
                                 None,
                                 Timestamp,
                                 sys_status[_SYSTEM_STATUS_SYSTEM_UPTIME]])
                else: # not valid
                    num_datafields = await self.meas_data.get_size()
                    await self.meas_data.set_data([None] * num_datafields)
                    del num_datafields
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
            return None
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
        if not await self.comm.uart_set(_UART_SET_START_MEASUREMENT, None):
            return False, None
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_RUNNING):
            if self.debug: print("Measurement successfully started")
            return True, sys_status
        if self.debug: print("Measurement could not be started!")
        return False, sys_status
    
    async def set_bsec_state(self, state):
        if self.debug: print("Issuing set BSEC state command")
        sys_status = await self.get_system_status()
        if sys_status is None:
            return False, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] != _SYSTEM_MEAS_WAITING) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] != _SYSTEM_STATE_DEFAULT) ):
            if self.debug: print("BSEC Set State: System running / error or already updated / update error!")
            return False, sys_status
        if not (await self.comm.uart_set(_UART_SET_BSEC_STATE, state)):
            return False, None
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
        if self.debug: print("Send set BSEC state command successful")
        return True, sys_status
    
    async def set_temp_comp(self, temperature):
        if self.debug: print("Issuing Set Temperature Compensation command")
        sys_status = await self.get_system_status()
        if sys_status is None:
            return False, None
        if ( (sys_status[_SYSTEM_STATUS_MEAS_RUNNING] == _SYSTEM_MEAS_ERROR) or
             (sys_status[_SYSTEM_STATUS_STATE_UPDATED] == _SYSTEM_STATE_ERROR) ):
            if self.debug: print("Set Temperature Compensation: System or state is in error!")
            return False, sys_status
        temperature = temperature if temperature <= 100 else 100
        temperature = temperature if temperature >= -100 else -100
        temperature_bytes = struct.pack("l", int(temperature * 1000))
        if not (await self.comm.uart_set(_UART_SET_TEMP_COMP, temperature_bytes)):
            return False, None
        sys_status = await self.get_system_status()
        if sys_status is None:
            if self.debug: print("Error reading system status!")
            return False, None
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

