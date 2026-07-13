import asyncio
import os
import json
from micropython import const

_50_YEARS_SEC = const(1576800000)   # seconds of 50 years(!!) perfectly fits into 32bit signed

class TimeCounterManager:
    def __init__(self, init_value=0):
        self.uptime = init_value
        self.uptime_lock = asyncio.Lock()

    async def set_counter(self, value):
        async with self.uptime_lock:
            self.uptime = value

    async def get_counter(self):
        async with self.uptime_lock:
            ret = self.uptime
        return ret

    async def increment(self):
        async with self.uptime_lock:
            if self.uptime < _50_YEARS_SEC:
                self.uptime += 1
            ret = self.uptime
        return ret

    async def decrement(self):
        async with self.uptime_lock:
            if self.uptime > 0:
                self.uptime -= 1
            ret = self.uptime
        return ret

class LockedFlag:
    def __init__(self, init_value=False):
        self.flag = init_value
        self.flag_lock = asyncio.Lock()

    async def setTrue(self):
        async with self.flag_lock:
            self.flag = True

    async def setFalse(self):
        async with self.flag_lock:
            self.flag = False

    async def getValue(self):
        async with self.flag_lock:
            ret = self.flag
        return ret
    
class LockedValue:
    def __init__(self, init_value):
        self.value = init_value
        self.value_lock = asyncio.Lock()

    async def setValue(self, value):
        async with self.value_lock:
            self.value = value

    async def getValue(self):
        async with self.value_lock:
            ret = self.value
        return ret

class DataManager:
    def __init__(self, num_elements, default_value=None):
        self.data_lock = asyncio.Lock()
        self.size = num_elements
        self.default = default_value
        self.datastruct = [self.default] * self.size

    def _index_valid(self, startIdx, endIdx):
        return (startIdx < endIdx) and (startIdx >= 0) and (endIdx <= self.size)

    async def get_size(self):
        return self.size

    async def get_data(self, startIdx=0, length=-1):
        if length <= 0:
            endIdx = self.size
        else:
            endIdx = startIdx + length
        if self._index_valid(startIdx, endIdx):
            async with self.data_lock:
                ret = self.datastruct[startIdx:endIdx]
            return ret
        return [self.default] * length

    async def set_data(self, data, startIdx=0):
        endIdx = startIdx + len(data)
        if self._index_valid(startIdx, endIdx):
            async with self.data_lock:
                self.datastruct[startIdx:endIdx] = data
            return True
        return False

class ConfigManager:
    def __init__(self, filename, default_config, debug=False):
        self.config_lock = asyncio.Lock()
        self.config_file = filename
        self.debug = debug
        try:
            valid_config = (os.stat(self.config_file)[0] & 0x4000) == 0  # file exists
            if valid_config:
                try:
                    with open(self.config_file, "r") as f:
                        data = json.load(f)
                except:
                    if self.debug: print("No valid JSON data in file!")
                    data = {}
                    valid_config = False
                if valid_config:  # JSON is valid
                    if self.debug: print("JSON Data in config file found.")
                    for key in default_config:
                        if not key in data:
                            if self.debug: print("Missing keys in config data!")
                            valid_config = False
        except OSError:
            valid_config = False

        if not valid_config:
            if self.debug: print("Missing or invalid configuration data!")
            with open(self.config_file, "w") as f:
                json.dump(default_config, f)
                valid_config = True
                if self.debug: print("Default config data was written.")
        else:
            if self.debug: print("Valid configuration data found.")

    async def get_json(self, keys):
        ret_json = {}
        await self.config_lock.acquire()
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                ret_json = {}
                for key in keys:
                    ret_json[key] = data[key]
                valid = True
        except:  # mainly file errors, key errors
            for key in keys:
                ret_json[key] = None
            valid = False
        finally:
            self.config_lock.release()
        return valid, ret_json

    async def get_values(self, keys):
        await self.config_lock.acquire()
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                ret_values = []
                for key in keys:
                    ret_values.append(data[key])
                valid = True
        except:  # mainly file errors, key errors
            ret_values = [None] * len(keys)
            valid = False
        finally:
            self.config_lock.release()
        return valid, ret_values

    async def write_config(self, data):
        await self.config_lock.acquire()
        try:
            with open(self.config_file, "r") as f:
                conf_data = json.load(f)
            for key in data:
                if key in conf_data:
                    conf_data[key] = data[key]
                else:
                    if self.debug: print("Config data key error.")
                    return False
            with open(self.config_file, "w") as f:
                json.dump(conf_data, f)
                valid = True
                if self.debug: print("Config data was written.")
        except:  # mainly file errors, key errors
            valid = False
            if self.debug: print("Error writing config data!")
        finally:
            self.config_lock.release()
        return valid
