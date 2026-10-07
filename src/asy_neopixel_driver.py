"""Pure NeoPixel LED hardware service: overlay switch/toggle, a dimmed ramp-up/ramp-down signal, and internal
(`request_signal()`, waits for a running signal up to a deadline) / external (`led_signal()`, refused at once while
a signal is queued or running) arbitration for the one shared physical pixel."""
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
    from collections.abc import Callable
    from typing import Any

    from asy_base_classes import ErrorSource, TimerStarter
    from asy_print_log import ErrorLog

_NAME = const("NEOPIXEL")
# @tunable led.min_signal_s = 0.1
_MIN_SIGNAL_S = const(0.1)  # floor for a signal's ramp duration; also the non-finite fallback
_MAX_SIGNAL_S = const(60.0)  # the REST ceiling of t (buildgen's LED command bound, legacy led_cmd())
# Twice the longest signal: a late frame schedule never drops a queued flash; the deadline only guards a signal task that never restarts.
# @tunable led.signal_wait_ms = 120000
_SIGNAL_WAIT_MS = const(120000)

# One optional live cross-instance dependency (SPECIFICATION.md Parts C.14 and L.4): the FRAM store its logger writes to, passed as log=.
# @wiring fram_target FRAMManager log optional kwarg

# The value types a signal accepts; bool is listed because it is no int subclass here (SPECIFICATION.md Part F.1).
_NUMERIC = (bool, int, float)


def _clamp_byte(value: object) -> int:
    if not isinstance(value, _NUMERIC):  # anything else has no byte value
        return 0
    try:
        return min(max(int(value), 0), 255)
    except (OverflowError, ValueError):  # int() of +/-inf raises OverflowError, of NaN ValueError
        return 0


def _signal_values(r: object, g: object, b: object, t: object) -> list[int | float] | None:
    # Every value a signal request carries, made safe where it enters: None refuses a non-numeric one.
    if not (isinstance(r, _NUMERIC) and isinstance(g, _NUMERIC) and isinstance(b, _NUMERIC) and isinstance(t, _NUMERIC)):
        return None
    if t - t != 0 or t < _MIN_SIGNAL_S:  # inf - inf and NaN - NaN are NaN: a non-finite t takes the floor
        dur = _MIN_SIGNAL_S
    elif t > _MAX_SIGNAL_S:
        dur = _MAX_SIGNAL_S
    else:
        dur = float(t)
    return [_clamp_byte(r), _clamp_byte(g), _clamp_byte(b), dur]


class NeopixelDriver:
    def __init__(
        self,
        neopixel_pin: int,
        # @tunable led.refresh_hz_default = 20
        neopixel_freq: int = 20,
        # @tunable led.overlay_brightness_default = 50
        led_overl_bri: int = 50,
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
        self.neopixel_dt = 1.0 / neopixel_freq

    async def _overlay_loop(self) -> None:
        while True:
            await self._overlay_start.wait()
            async with self._overlay_lock:
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
            try:
                t = self._rgbt[3]  # ramp duration, finite and within its bounds since _signal_values()
                steps = max(int(t * 0.5 * self.neopixel_freq), 1)  # per dim half; at least 1, so never a divide-by-zero
                steps_inv = 1.0 / steps
                r_s = self._rgbt[0] * steps_inv  # red
                g_s = self._rgbt[1] * steps_inv  # green
                b_s = self._rgbt[2] * steps_inv  # blue

                async with self._overlay_lock:
                    for n in range(1, steps + 1):
                        self._pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                        self._pixel.write()
                        await asyncio.sleep(self.neopixel_dt)
                    for n in range(steps - 1, -1, -1):
                        self._pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                        self._pixel.write()
                        await asyncio.sleep(self.neopixel_dt)
            finally:  # also on a cancel or failure mid-ramp: the slot freed first, then the defined off state
                self._start_signal_event.clear()
                self._overlay_start.set()  # restore last overlay value, written after the black frame (no await here)
                self._pixel[0] = (0, 0, 0)
                self._pixel.write()

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
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
        values = _signal_values(r, g, b, t)
        if values is None:
            return False
        if self._start_signal_event.is_set():
            self.pr.evt("External LED command refused: busy, retry later.")
            return False
        self._rgbt = values
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
        values = _signal_values(r, g, b, t)
        if values is None:
            return False
        deadline = time.ticks_add(time.ticks_ms(), _SIGNAL_WAIT_MS)
        while self._start_signal_event.is_set():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                self.pr.evt("Internal LED command dropped: signal still busy.")
                return False
            await asyncio.sleep(self.neopixel_dt)
        self._rgbt = values
        self._start_signal_event.set()
        return True

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def setup(self) -> bool:
        # The logger's own setup, in the boot batch before either task starts. True = ready: a logger
        # that cannot reach its store has logged it and runs in RAM (Part C.13, as SensorReader).
        await self.pr.setup()
        return True

    def toggle(self) -> None:
        self._overlay_on = not self._overlay_on
        self._overlay_start.set()
