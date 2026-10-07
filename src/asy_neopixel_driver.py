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

from print_log import DEFAULT_LOG, LogConfig, PrintLogHistory, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from print_log import ErrorLog

_NAME = const("NEOPIXEL")
# @tunable led.min_signal_s = 0.1
_MIN_SIGNAL_S = const(0.1)  # floor for a signal's ramp duration; also the non-finite fallback
_MAX_SIGNAL_S = const(60.0)  # the REST ceiling of t (buildgen's LED command bound, legacy led_cmd())
# Twice the longest signal: a late frame schedule never drops a queued flash; the deadline only guards a signal task that never restarts.
# @tunable led.signal_wait_ms = 120000
_SIGNAL_WAIT_MS = const(120000)

# One optional live cross-instance dependency (SPECIFICATION.md Parts C.14 and L.4): the FRAM store its logger writes to, passed as log=.
# @wiring fram_target AsyFramManager log optional kwarg

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
        self.pixel = neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)
        self.rgbt: list[int | float] = [0, 0, 0, 0.1]
        self.start_signal_event = asyncio.Event()
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

    def start_asy_neopixel_led_overl(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._led_overl_signal())

    def start_asy_neopixel_signal(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.neopixel_signal())

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_neopixel_led_overl, self.start_asy_neopixel_signal]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape, kept
        # empty rather than omitted so callers can treat every driver uniformly)

    def get_error_sources(self) -> "list[Any]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2), same shape as base_classes.py's
        # SensorReader.get_error_sources() - duck-typed, not inherited (no schema at all, see this
        # module's own docstring).
        return [self]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr]

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

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
        values = _signal_values(r, g, b, t)
        if values is None:
            return False
        if self.start_signal_event.is_set():
            self.pr.evt("External LED command refused: busy, retry later.")
            return False
        self.rgbt = values
        self.start_signal_event.set()
        return True

    # Internal requests are bounded in number and rate, so one waits for a running signal, then queues; an external command is refused instead, and told to retry (owner, 2026-10-02).
    async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:
        values = _signal_values(r, g, b, t)
        if values is None:
            return False
        deadline = time.ticks_add(time.ticks_ms(), _SIGNAL_WAIT_MS)
        while self.start_signal_event.is_set():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                self.pr.evt("Internal LED command dropped: signal still busy.")
                return False
            await asyncio.sleep(self.neopixel_dt)
        self.rgbt = values
        self.start_signal_event.set()
        return True

    async def neopixel_signal(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors, matches every other module's own main-loop convention
        self.pixel[0] = (0, 0, 0)
        self.pixel.write()
        while True:
            await self.start_signal_event.wait()
            self.pr.evt("Signal started.")
            try:
                t = self.rgbt[3]  # ramp duration, finite and within its bounds since _signal_values()
                steps = max(int(t * 0.5 * self.neopixel_freq), 1)  # per dim half; at least 1, so never a divide-by-zero
                steps_inv = 1.0 / steps
                r_s = self.rgbt[0] * steps_inv  # red
                g_s = self.rgbt[1] * steps_inv  # green
                b_s = self.rgbt[2] * steps_inv  # blue

                async with self.led_overl_lock:
                    for n in range(1, steps + 1):
                        self.pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                        self.pixel.write()
                        await asyncio.sleep(self.neopixel_dt)
                    for n in range(steps - 1, -1, -1):
                        self.pixel[0] = (int(r_s * n), int(g_s * n), int(b_s * n))
                        self.pixel.write()
                        await asyncio.sleep(self.neopixel_dt)
            finally:  # also on a cancel or failure mid-ramp: the slot freed first, then the defined off state
                self.start_signal_event.clear()
                self.led_overl_start.set()  # restore last overlay value, written after the black frame (no await here)
                self.pixel[0] = (0, 0, 0)
                self.pixel.write()
