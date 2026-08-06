"""Pure Neopixel LED hardware service: overlay switch/toggle, a dimmed ramp-up/ramp-down signal, and
internal (`request_signal()`)/external (`led_signal()`) arbitration for the one shared physical
pixel. Promoted from improved-quality/neopixel_signal.py's proven arbitration mechanism (see
CLAUDE.md/BACKLOG.md). No config schema (confirmed by the project owner). Also satisfies
asy_wifi_service.py's LEDControl Protocol via `on()`/`off()`/`toggle()`.
"""

import asyncio

import neopixel
from machine import Pin
from micropython import const

from print_log import PrintLogHistory, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from asy_fram_manager import AsyFramManager

_NAME = const("NEOPIXEL")


def _clamp_byte(value: "int | float") -> int:
    try:
        return min(max(int(value), 0), 255)
    except (ValueError, OverflowError):  # NaN/inf: int() raises for both
        return 0


class NeopixelDriver:
    def __init__(
        self,
        neopixel_pin: int,
        neopixel_freq: int = 20,
        led_overl_bri: int = 50,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        if fram is None:
            self.pr: PrintLogHistory = PrintLogHistory(history_length, debug)
            self.pr.one(_NAME, "Init with memory logging.")
        else:
            self.pr = PrintLogHistoryStore(fram, history_length, debug)
            self.pr.one(_NAME, "Init with FRAM logging.")
        self.pixel = neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)
        self.rgbt: list[int | float] = [0, 0, 0, 0.1]
        self.ext_rgbt: list[int | float] = [0, 0, 0, 0.1]
        self.ext_start_signal = asyncio.Event()
        self.start_signal_event = asyncio.Event()
        self.start_signal_lock = asyncio.Lock()
        self.led_overl_lock = asyncio.Lock()
        self.led_overl_start = asyncio.ThreadSafeFlag()
        self.led_overl_bri = led_overl_bri
        self.led_overl_rgb: tuple[int, int, int] = (0, 0, 0)
        self.led_overl_on = False
        self.neopixel_freq = neopixel_freq
        self.neopixel_dt = 1.0 / neopixel_freq

    async def _led_overl_signal(self) -> None:
        while True:
            await self.led_overl_start.wait()
            async with self.led_overl_lock:
                bri = _clamp_byte(self.led_overl_bri)
                self.led_overl_rgb = (bri,) * 3 if self.led_overl_on else (0, 0, 0)
                self.pixel[0] = self.led_overl_rgb
                self.pixel.write()

    async def _led_ext_signal_starter(self) -> None:
        while True:
            await self.ext_start_signal.wait()
            self.pr.evt(_NAME, "External LED flag set.")
            async with self.start_signal_lock:
                while self.start_signal_event.is_set():
                    await asyncio.sleep(0)
                self.rgbt = self.ext_rgbt
                self.start_signal_event.set()
                self.pr.evt(_NAME, "External LED command started.")
            self.ext_start_signal.clear()

    def start_asy_neopixel_led_overl(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_overl_signal())

    def start_asy_neopixel_signal(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.neopixel_signal())

    def start_asy_ext_cmd_watcher(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_ext_signal_starter())

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_neopixel_led_overl, self.start_asy_neopixel_signal, self.start_asy_ext_cmd_watcher]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return []  # no machine.Timer anywhere in this file (DRIVER_SPEC.md section 9 shape, kept
        # empty rather than omitted so callers can treat every driver uniformly)

    def on(self) -> None:
        self.led_overl_on = True
        self.led_overl_start.set()

    def off(self) -> None:
        self.led_overl_on = False
        self.led_overl_start.set()

    def toggle(self) -> None:
        self.led_overl_on = not self.led_overl_on
        self.led_overl_start.set()

    def led_signal(self, r: int, g: int, b: int, t: float) -> bool:
        self.pr.evt(_NAME, "External LED command received.")
        if self.ext_start_signal.is_set():
            return False
        self.ext_rgbt = [r, g, b, t]
        self.ext_start_signal.set()
        return True

    async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:
        self.pr.evt(_NAME, "Internal LED command received.")
        async with self.start_signal_lock:
            while self.start_signal_event.is_set():
                await asyncio.sleep(0)
            self.rgbt = [r, g, b, t]
            self.start_signal_event.set()
            self.pr.evt(_NAME, "Internal LED command started.")
        return True

    async def neopixel_signal(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors, matches every other module's own main-loop convention
        self.pixel[0] = (0, 0, 0)
        self.pixel.write()
        while True:
            await self.start_signal_event.wait()
            self.pr.evt(_NAME, "Signal started.")
            t = self.rgbt[3] if self.rgbt[3] >= 0.1 else 0.1  # time; a NaN comparison is always False, floor kicks in
            try:
                steps = int(t * 0.5 * self.neopixel_freq)  # num steps for one dim half
            except OverflowError:  # t is +inf
                steps = 1
            steps = steps if steps >= 1 else 1  # avoid 0 steps (low freq) and a divide-by-zero below
            steps_inv = 1.0 / steps
            r_s = _clamp_byte(self.rgbt[0]) * steps_inv  # red
            g_s = _clamp_byte(self.rgbt[1]) * steps_inv  # green
            b_s = _clamp_byte(self.rgbt[2]) * steps_inv  # blue

            async with self.led_overl_lock:
                for n in range(1, steps + 1):
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
            self.led_overl_start.set()  # restore last overlay value
