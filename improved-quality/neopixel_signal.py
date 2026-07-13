import neopixel
import time
import asyncio
from uasyncio import Lock, ThreadSafeFlag, Event
from machine import Pin
from micropython import const
from async_manager import TimeCounterManager, ConfigManager
from typing import Callable, Any, List, Coroutine
from collections import namedtuple
from async_connect import GMTimeStruct

_MAX_OVERRIDE_TIME = const(3600)

_DEFAULT_CONFIG = const(
    '{ "LedAutoOnH": 10, "LedAutoOnM": 0, "LedAutoOffH": 18, "LedAutoOffM": 0, "LedAutoFlashBri": 200, "LedWarnCO2": 1600, "LedWarnVOC": 350, "LedAutoInterv": 300.0, "LedAutoFlashDur": 2.0, "LedWarnHum": 65.0, "LedAutoOn": true}'
)

LocalConfig = namedtuple(
    "LocalConfig",
    (
        "OnH",
        "OnM",
        "OffH",
        "OffM",
        "FlashBri",
        "WarnCO2",
        "WarnHum",
        "Interv",
        "FlashDur",
        "WarnVOC",
        "AutoOn",
    ),
)


class Neopixel_Signal:
    def __init__(
        self,
        neopixel_pin: int,
        cfgmgr: ConfigManager,
        asy_airquality_meas_callback: Callable[[], Coroutine[Any, Any, List[int | float | None]]],
        asy_local_time_callback: Callable[[], Coroutine[Any, Any, GMTimeStruct | None]],
        neopixel_freq: int = 20,
        led_overl_bri: int = 50,
        asy_long_block_lock: Lock | None = None,
        debug: bool = False,
    ) -> None:
        self.pixel = neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)
        self.rgbt = [0, 0, 0, 1]
        self.ext_rgbt = [0, 0, 0, 1]
        self.led_auto_active = True
        self.ext_start_signal = Event()
        self.auto_signal_timer_event = Event()
        self.start_signal_event = Event()
        self.start_signal_lock = Lock()
        self.asy_long_block_lock = Lock() if asy_long_block_lock is None else asy_long_block_lock
        self.led_overl_lock = Lock()
        self.led_overl_start = ThreadSafeFlag()
        self.led_overl_bri = led_overl_bri
        self.led_overl_rgb = (0, 0, 0)
        self.led_overl_on = False
        self.neopixel_freq = neopixel_freq
        self.neopixel_dt = 1.0 / neopixel_freq
        self.override_secs = TimeCounterManager()
        self.debug = debug
        self.local_time_callback = (
            asy_local_time_callback  # expects gmtime formatted for local time
        )
        self.measurements_callback = asy_airquality_meas_callback  # expects [CO2, Humidity, VOC]
        self.cfgmgr = cfgmgr

    @staticmethod
    def get_default_cfg() -> str:
        return _DEFAULT_CONFIG

    def start_asy_neopixel_led_overl(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_overl_signal())

    def start_asy_neopixel_signal(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.neopixel_signal())

    def start_asy_airquality_signal(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.airquality_auto_signal())

    def start_asy_auto_override(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.auto_led_override())

    def start_asy_ext_cmd_watcher(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_ext_signal_starter())

    async def set_override_led(self, secs: int) -> None:
        if secs < 0:
            await self.override_secs.set_counter(0)
        elif secs > _MAX_OVERRIDE_TIME:
            await self.override_secs.set_counter(_MAX_OVERRIDE_TIME)
        else:
            await self.override_secs.set_counter(secs)

    async def get_override_led(self) -> int:
        return await self.override_secs.get_counter()

    def led_signal(self, r: int, g: int, b: int, t: int) -> bool:
        if self.debug:
            print("Neopixel external LED command received.")
        if self.ext_start_signal.is_set():
            return False
        self.ext_rgbt = [r, g, b, t]
        self.ext_start_signal.set()
        return True

    def get_long_block_lock(self) -> Lock:
        return self.asy_long_block_lock

    def on(self) -> None:
        self.led_overl_on = True
        self.led_overl_start.set()

    def off(self) -> None:
        self.led_overl_on = False
        self.led_overl_start.set()

    def toggle(self) -> None:
        self.led_overl_on = not self.led_overl_on
        self.led_overl_start.set()

    async def _led_overl_signal(self) -> None:
        while True:
            await self.led_overl_start.wait()
            async with self.led_overl_lock:
                if self.led_overl_on:
                    self.led_overl_rgb = (
                        self.led_overl_bri,
                        self.led_overl_bri,
                        self.led_overl_bri,
                    )
                else:
                    self.led_overl_rgb = (0, 0, 0)
                self.pixel[0] = self.led_overl_rgb
                self.pixel.write()

    async def _led_ext_signal_starter(self) -> None:
        while True:
            await self.ext_start_signal.wait()
            if self.debug:
                print("Neopixel external LED flag set.")
            async with self.start_signal_lock:
                while self.start_signal_event.is_set():
                    await asyncio.sleep(0)
                self.rgbt = self.ext_rgbt
                self.start_signal_event.set()
                if self.debug:
                    print("Neopixel external LED command started.")
            self.ext_start_signal.clear()

    async def _led_int_signal_starter(self, r: int, g: int, b: int, t: int) -> None:
        if self.debug:
            print("Neopixel internal LED command received.")
        async with self.start_signal_lock:
            while self.start_signal_event.is_set():
                await asyncio.sleep(0)
            self.rgbt = [r, g, b, t]
            self.start_signal_event.set()
            if self.debug:
                print("Neopixel internal LED command started.")

    async def neopixel_signal(self) -> None:
        self.pixel[0] = (0, 0, 0)
        self.pixel.write()
        while True:
            await self.start_signal_event.wait()
            if self.debug:
                print("Neopixel signal started.")
            self.rgbt[3] = 0.1 if self.rgbt[3] < 0.1 else self.rgbt[3]  # time
            steps = int(self.rgbt[3] * 0.5 * self.neopixel_freq)  # num steps for one dim half
            steps_inv = 1.0 / steps
            r_s = self.rgbt[0] * steps_inv  # red
            g_s = self.rgbt[1] * steps_inv  # green
            b_s = self.rgbt[2] * steps_inv  # blue

            async with self.led_overl_lock:
                async with self.asy_long_block_lock:
                    if self.debug:
                        print("Neopixel Long Block Lock acquired.")
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
                    if self.debug:
                        print("Neopixel Long Block Lock released.")
            self.led_overl_start.set()  # restore last value

    async def airquality_auto_signal(self) -> None:
        while True:
            t0 = time.ticks_ms()
            cfg_int = await self.cfgmgr.get_int_values(
                [
                    "LedAutoOnH",
                    "LedAutoOnM",
                    "LedAutoOffH",
                    "LedAutoOffM",
                    "LedAutoFlashBri",
                    "LedWarnCO2",
                    "LedWarnHum",
                ]
            )
            cfg_float = await self.cfgmgr.get_int_values(
                ["LedAutoInterv", "LedAutoFlashDur", "LedWarnVOC"]
            )
            cfg_bool = await self.cfgmgr.get_bool_values(["LedAutoOn"])
            if (
                cfg_int is None
                or cfg_float is None
                or cfg_bool is None
                or len(cfg_int) != 7
                or len(cfg_float) != 3
                or len(cfg_bool) != 1
            ):
                interv = 600
                if self.debug:
                    print("Error in Air Quality Signal configuration!")
            else:
                cfg = LocalConfig(*cfg_int + cfg_float + cfg_bool)
                del cfg_int, cfg_float, cfg_bool
                interv = cfg.Interv
                if cfg.AutoOn and self.led_auto_active:
                    cur_time = await self.local_time_callback()
                    if cur_time is not None:  # no NTP sync or missing config is both checked
                        on_min_of_day = (cfg.OnH * 60) + cfg.OnM
                        off_min_of_day = (cfg.OffH * 60) + cfg.OffM
                        cur_min_of_day = (cur_time.hour * 60) + cur_time.minute
                        if on_min_of_day <= cur_min_of_day <= off_min_of_day:
                            if self.debug:
                                print("Auto LED Signal checking measurements.")
                            measurements: List[
                                int | float | None
                            ] = await self.measurements_callback()
                            if len(measurements) != 3:
                                measurements = [None, None, None]
                            [CO2, HUM, VOC] = measurements
                            if CO2 is not None and CO2 >= cfg.WarnCO2:
                                if self.debug:
                                    print("Auto LED CO2 warning.")
                                await self._led_int_signal_starter(
                                    cfg.FlashBri, 0, 0, cfg.FlashDur
                                )
                                await asyncio.sleep(2 * cfg.FlashDur)
                            if VOC is not None and VOC >= cfg.WarnVOC:
                                if self.debug:
                                    print("Auto LED VOC warning.")
                                await self._led_int_signal_starter(
                                    0, cfg.FlashBri, 0, cfg.FlashDur
                                )
                                await asyncio.sleep(2 * cfg.FlashDur)
                            if HUM is not None and HUM >= cfg.WarnHum:
                                if self.debug:
                                    print("Auto LED Humidity warning.")
                                await self._led_int_signal_starter(
                                    0, 0, cfg.FlashBri, cfg.FlashDur
                                )
                del cfg
            rem_interv = interv - (
                time.ticks_diff(time.ticks_ms(), t0) * 0.001
            )  # run duration so far in sec
            if self.debug:
                print("Auto LED remaining sleep seconds:", rem_interv)
            if rem_interv < 0.1:
                rem_interv = 0.1
            await asyncio.sleep(rem_interv)

    async def auto_led_override(self) -> None:
        self.led_auto_active = True
        while True:
            secs = await self.override_secs.decrement()
            if secs > 0:
                if self.debug:
                    print("Remaining LED Override seconds:", secs)
                if self.led_auto_active:
                    self.led_auto_active = False
                    if self.debug:
                        print("LED Override active!")
            else:
                if not self.led_auto_active:
                    self.led_auto_active = True
                    if self.debug:
                        print("LED Override off.")
            await asyncio.sleep(1)
