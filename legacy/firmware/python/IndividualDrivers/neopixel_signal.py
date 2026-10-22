import asyncio
import neopixel
import time
from machine import Pin, Timer
from micropython import const
from async_manager import TimeCounterManager

_MAX_OVERRIDE_TIME = const(3600)

class Neopixel_Signal:
    def __init__(self, neopixel_pin, asy_airquality_cfg_callback, asy_airquality_meas_callback, asy_local_time_callback, neopixel_freq=20, led_overl_bri=50, asy_long_block_lock=None, debug=False):
        self.pixel = neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)
        self.rgbt = [0, 0, 0, 1]
        self.ext_rgbt = [0, 0, 0, 1]
        self.led_auto_active = True
        self.ext_start_signal = asyncio.Event()
        self.auto_signal_timer_event = asyncio.Event()
        self.start_signal_event = asyncio.Event()
        self.start_signal_lock = asyncio.Lock()
        self.asy_long_block_lock = asyncio.Lock() if asy_long_block_lock is None else asy_long_block_lock
        self.led_overl_lock = asyncio.Lock()
        self.led_overl_start = asyncio.ThreadSafeFlag()
        self.led_overl_bri = led_overl_bri
        self.led_overl_rgb = (0, 0, 0)
        self.led_overl_on = False
        self.neopixel_freq = neopixel_freq
        self.neopixel_dt = 1.0 / neopixel_freq
        self.override_secs = TimeCounterManager()
        self.debug = debug
        self.local_time_callback = asy_local_time_callback  # expects gmtime formatted for local time
        self.measurements_callback = asy_airquality_meas_callback  # expects [CO2, VOC, Humidity]
        self.airquality_cfg_callback = asy_airquality_cfg_callback
            # expects (valid, [LedAutoOn, LedAutoInterv, LedAutoOnH, LedAutoOnM, LedAutoOffH, LedAutoOffM,
            #                  LedAutoFlashDur, LedAutoFlashBri, LedWarnCO2, LedWarnVOC, LedWarnHum])

    def start_asy_neopixel_led_overl(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_overl_signal())

    def start_asy_neopixel_signal(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.neopixel_signal())

    def start_asy_airquality_signal(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.airquality_auto_signal())

    def start_asy_auto_override(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.auto_led_override())

    def start_asy_ext_cmd_watcher(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_ext_signal_starter())

    async def set_override_led(self, secs):
        if secs < 0:
            await self.override_secs.set_counter(0)
        elif secs > _MAX_OVERRIDE_TIME:
            await self.override_secs.set_counter(_MAX_OVERRIDE_TIME)
        else:
            await self.override_secs.set_counter(secs)

    async def get_override_led(self):
        return await self.override_secs.get_counter()

    def led_signal(self, r, g, b, t):
        if self.debug: print("Neopixel external LED command received.")
        if self.ext_start_signal.is_set():
            return False
        self.ext_rgbt = [r, g, b, t]
        self.ext_start_signal.set()
        return True

    def get_long_block_lock(self):
        return self.asy_long_block_lock

    def on(self):
        self.led_overl_on = True
        self.led_overl_start.set()

    def off(self):
        self.led_overl_on = False
        self.led_overl_start.set()

    def toggle(self):
        self.led_overl_on = not self.led_overl_on
        self.led_overl_start.set()

    async def _led_overl_signal(self):
        while True:
            await self.led_overl_start.wait()
            async with self.led_overl_lock:
                if self.led_overl_on:
                    self.led_overl_rgb = (self.led_overl_bri, self.led_overl_bri, self.led_overl_bri)
                else:
                    self.led_overl_rgb = (0, 0, 0)
                self.pixel[0] = self.led_overl_rgb
                self.pixel.write()

    async def _led_ext_signal_starter(self):
        while True:
            await self.ext_start_signal.wait()
            if self.debug: print("Neopixel external LED flag set.")
            async with self.start_signal_lock:
                while self.start_signal_event.is_set():
                    await asyncio.sleep(0)
                self.rgbt = self.ext_rgbt
                self.start_signal_event.set()
                if self.debug: print("Neopixel external LED command started.")
            self.ext_start_signal.clear()

    async def _led_int_signal_starter(self, r, g, b, t):
        if self.debug: print("Neopixel internal LED command received.")
        async with self.start_signal_lock:
            while self.start_signal_event.is_set():
                await asyncio.sleep(0)
            self.rgbt = [r, g, b, t]
            self.start_signal_event.set()
            if self.debug: print("Neopixel internal LED command started.")

    async def neopixel_signal(self):
        self.pixel[0] = (0, 0, 0)
        self.pixel.write()
        while True:
            await self.start_signal_event.wait()
            if self.debug: print("Neopixel signal started.")
            self.rgbt[3] = 0.1 if self.rgbt[3] < 0.1 else self.rgbt[3]  # time
            steps = int(self.rgbt[3] * 0.5 * self.neopixel_freq)  # num steps for one dim half
            steps_inv = 1.0 / steps
            r_s = self.rgbt[0] * steps_inv  # red
            g_s = self.rgbt[1] * steps_inv  # green
            b_s = self.rgbt[2] * steps_inv  # blue

            async with self.led_overl_lock:
                async with self.asy_long_block_lock:
                    if self.debug: print("Neopixel Long Block Lock acquired.")
                    for n in range(1, steps + 1, 1):
                        self.pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                        self.pixel.write()
                        await asyncio.sleep(self.neopixel_dt)
                    for n in range(steps - 1, -1, -1):
                        self.pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                        self.pixel.write()
                        await asyncio.sleep(self.neopixel_dt)
                    self.pixel[0] = (0, 0, 0)  # defined off state after signal
                    self.pixel.write()
                    self.start_signal_event.clear()
                    if self.debug: print("Neopixel Long Block Lock released.")
            self.led_overl_start.set() # restore last value

    async def airquality_auto_signal(self):
        while True:
            t0 = time.ticks_ms()
            (valid,
            [autoOn, Interv, onHrs, onMin, offHrs, offMin,
            flashDur, flashBri, warnCO2, warnVOC, warnHum]) = await self.airquality_cfg_callback()

            if not valid:
                autoOn = False
                Interv = 600
                if self.debug: print("Error in Air Quality Signal configuration!")

            if autoOn and self.led_auto_active:
                currentTime = await self.local_time_callback()
                if currentTime is not None:    # no NTP sync or missing config is both checked
                    onMinOfDay = (onHrs * 60) + onMin
                    offMinOfDay = (offHrs * 60) + offMin
                    curMinOfDay = (currentTime[3] * 60) + currentTime[4]
                    if onMinOfDay <= curMinOfDay <= offMinOfDay:
                        if self.debug: print("Auto LED Signal checking measurements.")
                        [curCO2, curVOC, curHum] = await self.measurements_callback()
                        if curCO2 is not None:
                            if curCO2 >= warnCO2:
                                if self.debug: print("Auto LED CO2 warning.")
                                await self._led_int_signal_starter(flashBri, 0, 0, flashDur)
                                await asyncio.sleep(2 * flashDur)
                        if curVOC is not None:
                            if curVOC >= warnVOC:
                                if self.debug: print("Auto LED VOC warning.")
                                await self._led_int_signal_starter(0, flashBri, 0, flashDur)
                                await asyncio.sleep(2 * flashDur)
                        if curHum is not None:
                            if curHum >= warnHum:
                                if self.debug: print("Auto LED Humidity warning.")
                                await self._led_int_signal_starter(0, 0, flashBri, flashDur)

            rem_interv = Interv - (time.ticks_diff(time.ticks_ms(), t0) * 0.001)  # run duration so far in sec
            if self.debug: print("Auto LED remaining sleep seconds:", rem_interv)
            if (rem_interv < 0.1):
                rem_interv = 0.1
            await asyncio.sleep(rem_interv)

    async def auto_led_override(self):
        self.led_auto_active = True
        while True:
            secs = await self.override_secs.decrement()
            if secs > 0:
                if self.debug: print("Remaining LED Override seconds:", secs)
                if self.led_auto_active:
                    self.led_auto_active = False
                    if self.debug: print("LED Override active!")
            else:
                if not self.led_auto_active:
                    self.led_auto_active = True
                    if self.debug: print("LED Override off.")
            await asyncio.sleep(1)
