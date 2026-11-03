"""Pure NeoPixel LED hardware service: overlay switch/toggle, a dimmed ramp-up/ramp-down signal, and internal
(`request_signal()`, waits for a running signal up to a deadline, then queues) / external (`led_signal()`, refused at
once while a signal is queued or running) arbitration for the one shared physical pixel."""
# No config schema (owner, 2026-08-05). Also satisfies the WiFi service's LEDControl Protocol via `on()`/
# `off()`/`toggle()`.

import asyncio
import time

import neopixel
from machine import Pin
from micropython import const

from asy_print_log import DEFAULT_LOG, LogConfig, PrintLogHistory, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_base_classes import ErrorSource, TaskStarter, TimerStarter
    from asy_print_log import ErrorLog

_NAME = const("NEOPIXEL")
# @tunable led.min_signal_s = 0.1
_MIN_SIGNAL_S = const(0.1)  # floor for a signal's ramp duration; also the NaN fallback
# @tunable led.refresh_hz = 20
_NEOPIXEL_FREQ_HZ = const(20)
# @tunable led.overlay_brightness = 50
_LED_OVERL_BRI = const(50)
# Twice the REST ceiling of t (60 s), so a late frame schedule never cuts a queued flash short; past it the request queues anyway.
# @tunable led.signal_wait_ms = 120000
_SIGNAL_WAIT_MS = const(120000)

# One optional live cross-instance dependency (SPECIFICATION.md Parts C.14 and L.4): the FRAM store its logger writes to, passed as log=.
# @wiring fram_target FRAMManager log optional kwarg

def _clamp_byte(value: int | float) -> int:
    try:
        return min(max(int(value), 0), 255)
    except (ValueError, OverflowError):  # NaN/inf: int() raises for both
        return 0


class NeopixelDriver:
    def __init__(
        self,
        neopixel_pin: int,
        neopixel_freq: int = _NEOPIXEL_FREQ_HZ,
        led_overl_bri: int = _LED_OVERL_BRI,
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        self.pr: PrintLogHistory = make_logger(log, _NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        self._pixel = neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)
        self._rgbt: list[int | float] = [0, 0, 0, 0.1]
        self._start_signal_event = asyncio.Event()
        self._overlay_lock = asyncio.Lock()  # serialises the pixel and its write() between the overlay and a signal ramp
        self._overlay_start = asyncio.ThreadSafeFlag()
        self._overlay_bri = led_overl_bri
        self._overlay_rgb: tuple[int, int, int] = (0, 0, 0)
        self._overlay_on = False
        self.neopixel_freq = neopixel_freq
        self._frame_ms = 1000 // neopixel_freq  # the frame period as an int: every frame and poll wait is a float-free sleep_ms()

    async def _overlay_loop(self) -> None:
        while True:
            await self._overlay_start.wait()
            async with self._overlay_lock:  # a running ramp holds it, so an overlay write never cuts into a signal
                bri = _clamp_byte(self._overlay_bri)
                self._overlay_rgb = (bri,) * 3 if self._overlay_on else (0, 0, 0)
                self._pixel[0] = self._overlay_rgb
                self._pixel.write()

    async def _signal_loop(self) -> None:
        self._pixel[0] = (0, 0, 0)
        self._pixel.write()
        while True:
            await self._start_signal_event.wait()
            self.pr.evt("Signal started.")
            t = self._rgbt[3]  # ramp duration
            if not t >= _MIN_SIGNAL_S:  # `not >=`, not `<`: a NaN comparison is always False, so the floor kicks in
                t = _MIN_SIGNAL_S
            try:
                steps = int(t * 0.5 * self.neopixel_freq)  # num steps for one dim half
            except OverflowError:  # t is +inf
                steps = 1
            steps = max(steps, 1)  # avoid 0 steps (low freq) and a divide-by-zero below
            steps_inv = 1.0 / steps
            r_s = _clamp_byte(self._rgbt[0]) * steps_inv  # red
            g_s = _clamp_byte(self._rgbt[1]) * steps_inv  # green
            b_s = _clamp_byte(self._rgbt[2]) * steps_inv  # blue

            async with self._overlay_lock:
                for n in range(1, steps + 1):
                    self._pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                    self._pixel.write()
                    await asyncio.sleep_ms(self._frame_ms)
                for n in range(steps - 1, -1, -1):
                    self._pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                    self._pixel.write()
                    await asyncio.sleep_ms(self._frame_ms)
                self._pixel[0] = (0, 0, 0)  # defined off state after signal
                self._pixel.write()
                self._start_signal_event.clear()
            self._overlay_start.set()  # restore last overlay value

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_overlay, self.start_asy_signal]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape, kept
        # empty rather than omitted so callers can treat every driver uniformly)

    def start_asy_overlay(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._overlay_loop())

    def start_asy_signal(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._signal_loop())

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2), same shape as asy_base_classes.py's
        # SensorReader.get_error_sources() - duck-typed, not inherited (no schema at all, see this
        # module's own docstring).
        return [self]

    def get_loggers(self) -> list[PrintLogHistory]:
        return [self.pr]

    def led_signal(self, r: int, g: int, b: int, t: float) -> bool:
        if self._start_signal_event.is_set():
            self.pr.evt("External LED command refused: busy, retry later.")
            return False
        self._rgbt = [r, g, b, t]
        self._start_signal_event.set()
        return True

    def off(self) -> None:
        self._overlay_on = False
        self._overlay_start.set()

    def on(self) -> None:
        self._overlay_on = True
        self._overlay_start.set()

    # Internal requests are bounded in number and rate, so one waits for a running signal, then queues; an external command is refused instead, and told to retry (owner, 2026-10-02).
    async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:
        deadline = time.ticks_add(time.ticks_ms(), _SIGNAL_WAIT_MS)
        while self._start_signal_event.is_set() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            await asyncio.sleep_ms(self._frame_ms)
        self._rgbt = [r, g, b, t]
        self._start_signal_event.set()
        return True

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def setup(self) -> None:
        # The logger's own setup, in the boot batch before either task starts: a logger that cannot reach its
        # store has logged it and runs in RAM (Part C.13, as SensorReader).
        await self.pr.setup()

    def toggle(self) -> None:
        self._overlay_on = not self._overlay_on
        self._overlay_start.set()
