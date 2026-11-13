import asyncio
import random
import time
from machine import Timer, reset as SystemReset, bootloader as SystemBootloader
from micropython import const
from async_manager import DataManager, TimeCounterManager

_RESET_DELAY = const(5)  # seconds
_MAX_STORAGE_PAUSE = const(3600)  # one hour
_NTP_WAIT_TIME = const(120) # 2 mins

class System_Service:
    def __init__(self, asy_ntp_callback, storage_pause=None, debug=False):
        self.debug = debug
        self.storage_pause = storage_pause  # callback for starting and stopping permanent storage communication
        self.uptime = TimeCounterManager()
        self.uptime_event = asyncio.ThreadSafeFlag()
        self.uptime_timer = Timer()
        self.reset_timer = Timer()
        self.storage_timer = Timer()
        self.ntp_is_synced = asy_ntp_callback
        self.start_time_set = False
        self.boot_signature = DataManager(1)

    def start_asy_uptime_counter(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.status_counter())

    def start_uptime_timer(self):
        self.uptime_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.uptime_event.set())

    def stop_uptime_timer(self):
        self.uptime_timer.deinit()

    def reboot_system(self):
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        if self.debug: print("Reboot triggered")
        if self.storage_pause is not None:
            self.storage_pause(True)
            if self.debug: print("Storage paused")
        self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: SystemReset())

    def reboot_bootloader(self):
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        if self.debug: print("Reboot into bootloader triggered")
        if self.storage_pause is not None:
            self.storage_pause(True)
            if self.debug: print("Storage paused")
        self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: SystemBootloader())

    def pause_permanent_storage(self, duration):
        if self.storage_pause is not None:
            if duration <= 0:
                duration = 0
            elif duration > _MAX_STORAGE_PAUSE:
                duration =  _MAX_STORAGE_PAUSE
            if duration == 0:
                self.storage_timer.deinit()
                if self.debug: print("Storage immediately unpaused.")
                self.storage_pause(False)
            else:
                self.storage_timer.deinit()
                if self.debug: print("Storage paused for", duration, "seconds.")
                self.storage_pause(True)
                self.storage_timer.init(period=duration * 1000, mode=Timer.ONE_SHOT, callback=lambda b: self.storage_pause(False))

    async def get_uptime(self):
        return await self.uptime.get_counter()
    
    async def get_boot_signature(self):  # unique number. UTC timestamp if NTP synced, random number otherwise after wait time
        res = await self.boot_signature.get_data()
        return res[0]
    
    async def status_counter(self):
        await self.uptime.set_counter(0)
        await self.boot_signature.set_data([-1])
        while True:
            await self.uptime_event.wait()
            uptime = await self.uptime.increment()
            if self.debug: print("System uptime incremented to", uptime)
            if not self.start_time_set:
                if await self.ntp_is_synced():
                    await self.boot_signature.set_data([time.mktime(time.gmtime())])
                    if self.debug: print("System boot signature set by NTP.")
                    self.start_time_set = True
                else:  # ntp not synced
                    if uptime >= _NTP_WAIT_TIME:
                        await self.boot_signature.set_data([random.getrandbits(32)])
                        if self.debug: print("System boot signature set by random number.")
                        self.start_time_set = True
