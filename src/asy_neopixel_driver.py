"""Pure NeoPixel LED hardware service: overlay switch/toggle, a dimmed ramp-up/ramp-down signal, and one lock held by
whatever drives the one shared pixel: an internal request (`request_signal()`) waits its turn on it, an external one
(`led_signal()`) is refused while it is held or a request is pending (owner, 2026-10-02)."""
# No config schema (owner, 2026-08-05), no failure path, so no error log (SPECIFICATION.md Part A.4). Also satisfies the
# WiFi service's LEDControl Protocol via `on()`/`off()`/`toggle()`.

import asyncio

import neopixel
from machine import Pin
from micropython import const

from asy_print_log import DEFAULT_LOG, LogConfig, PrintLog

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_base_classes import ErrorSource, TaskStarter, TimerStarter

_NAME = const("NEOPIXEL")
# @tunable led.min_signal_s = 0.1
_MIN_SIGNAL_S = const(0.1)  # floor for a signal's ramp duration; also the NaN fallback
# @tunable led.refresh_hz = 20
_NEOPIXEL_FREQ_HZ = const(20)
# @tunable led.overlay_brightness = 50
_LED_OVERL_BRI = const(50)


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
        self.pr = PrintLog(log.debug, _NAME)  # event lines only: the console level is all it takes from log
        self.name = _NAME
        self._pixel = neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)
        self._frame = [0, 0, 0]  # every write's one reused pixel value
        self._rgbt: tuple[int, int, int, float] = (0, 0, 0, 0.1)  # the external command the signal task plays
        self._start_signal_event = asyncio.Event()
        self._led_lock = asyncio.Lock()  # held by whatever drives the pixel: a ramp, its waiters queue on it in order
        self._pending = 0  # signals taken and not yet ended, the external one included
        self._overlay_bri = led_overl_bri
        self._overlay_on = False
        self.neopixel_freq = neopixel_freq
        self._frame_ms = 1000 // neopixel_freq  # the frame period as an int: every frame wait is a float-free sleep_ms()

    def _set_overlay(self, *, on: bool) -> None:
        self._overlay_on = on
        if not self._led_lock.locked():  # else the running ramp's end restores it
            self._put_overlay()

    def _put(self, r: int, g: int, b: int) -> None:
        frame = self._frame
        frame[0] = r
        frame[1] = g
        frame[2] = b
        self._pixel[0] = frame
        self._pixel.write()

    def _put_overlay(self) -> None:
        bri = _clamp_byte(self._overlay_bri) if self._overlay_on else 0
        self._put(bri, bri, bri)

    async def _ramp(self, r: int, g: int, b: int, t: float) -> None:
        # Its caller holds the lock. Up in `steps` frames, down to black, a second black, then the overlay; integer
        # steps into the one frame, so no frame allocates.
        self.pr.evt("Signal started.")
        if not t >= _MIN_SIGNAL_S:  # `not >=`, not `<`: a NaN comparison is always False, so the floor kicks in
            t = _MIN_SIGNAL_S
        try:
            steps = max(int(t * 0.5 * self.neopixel_freq), 1)  # one dim half; at least one step at a low rate
        except OverflowError:  # t is +inf
            steps = 1
        r, g, b = _clamp_byte(r), _clamp_byte(g), _clamp_byte(b)
        for i in range(1, 2 * steps + 1):
            n = steps - abs(steps - i)
            self._put(r * n // steps, g * n // steps, b * n // steps)
            await asyncio.sleep_ms(self._frame_ms)
        self._put(0, 0, 0)  # defined off state after signal
        self._put_overlay()

    async def _signal_loop(self) -> None:
        # Plays the external command led_signal() took; cancelled mid-ramp, it leaves the command pending, so a restart plays it.
        self._put(0, 0, 0)
        while True:
            await self._start_signal_event.wait()
            async with self._led_lock:
                await self._ramp(*self._rgbt)
            self._start_signal_event.clear()
            self._pending -= 1

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_signal]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape, kept
        # empty rather than omitted so callers can treat every driver uniformly)

    def start_asy_signal(self) -> asyncio.Task[None]:
        return asyncio.create_task(self._signal_loop())

    def get_error_sources(self) -> "list[ErrorSource]":
        return []  # nothing it can fail at, so no /status error entry (module header)

    def get_loggers(self) -> list[PrintLog]:
        return [self.pr]

    def led_signal(self, r: int, g: int, b: int, t: float) -> bool:
        self.pr.evt("External LED command received.")
        if self._pending:
            self.pr.evt("External LED command refused: busy, retry later.")
            return False
        self._pending = 1
        self._rgbt = (r, g, b, t)
        self._start_signal_event.set()
        return True

    def off(self) -> None:
        self._set_overlay(on=False)

    def on(self) -> None:
        self._set_overlay(on=True)

    # An internal request waits its turn on the lock, in arrival order: every ramp is finite, so every wait ends.
    async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:
        self.pr.evt("Internal LED command received.")
        self._pending += 1
        try:
            async with self._led_lock:
                self.pr.evt("Internal LED command started.")
                await self._ramp(r, g, b, t)
        finally:
            self._pending -= 1
        return True

    def toggle(self) -> None:
        self._set_overlay(on=not self._overlay_on)
