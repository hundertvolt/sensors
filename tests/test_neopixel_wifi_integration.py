"""Cross-module integration: a real asy_neopixel_driver.py.NeopixelDriver passed as
asy_wifi_service.py's own ext_led=, proving the LEDControl Protocol (on/off/toggle) still holds
end to end through the real WiFi driver - today's tests/test_asy_wifi_service.py only ever
exercises a local FakeLED double for this (deliberately, since it tests the Protocol boundary, not
a concrete class - see this repo's promotion plan). Only tests/neopixel.py's fake write surface is
mocked; every other layer (overlay task, arbitration) runs for real.
"""

import asyncio
import os

from asy_neopixel_driver import NeopixelDriver
from asy_wifi_service import AsyConnTime

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # Sweeps pre-existing <prefix>* scratch dirs left behind by an earlier scripts/test.sh run on
    # this machine - _next_dir always restarts at 0 per process, so without this a later run
    # silently reuses an earlier run's real, persisted config_*.cfg files instead of a genuinely
    # fresh directory. See tests/test_sensortask_wozi.py's own _sweep_stale_tmp_dirs() for the full
    # root-cause writeup (this exact _tmp_cfg_dir() shape is copy-pasted across every test file with
    # its own _TMP_DIR/_next_dir pair - same fix applied uniformly to each).
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return  # tests/_tmp itself doesn't exist yet - nothing to clean
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("neopixel_wifi_")


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/neopixel_wifi_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    _remove_any(path + "/config_WIFI.cfg")
    return path + "/"


async def _cancel(task: "asyncio.Task[None]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def test_real_neopixel_driver_on_off_toggle_through_wifi_service_ext_led() -> None:
    pixel = NeopixelDriver(0, neopixel_freq=100)
    conn = AsyConnTime(led_pin=None, ext_led=pixel, cfg_path=_tmp_cfg_dir())

    async def scenario() -> "tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]":
        overlay_task = pixel.start_asy_neopixel_led_overl()
        await asyncio.sleep(0)
        await conn.set_wifi_led(True)  # led_pin is None -> self.led becomes self.ext_led (pixel)
        conn._led_on()
        await asyncio.sleep(0.05)
        on_write = pixel.pixel.writes[-1][0]
        conn._led_off()
        await asyncio.sleep(0.05)
        off_write = pixel.pixel.writes[-1][0]
        conn._led_toggle()
        await asyncio.sleep(0.05)
        toggle_write = pixel.pixel.writes[-1][0]
        await _cancel(overlay_task)
        return on_write, off_write, toggle_write

    on_write, off_write, toggle_write = run(scenario())
    assert on_write == (50, 50, 50)  # default led_overl_bri
    assert off_write == (0, 0, 0)
    assert toggle_write == (50, 50, 50)  # toggled from off -> on


def test_set_ext_led_swaps_in_a_real_driver_after_construction() -> None:
    # set_ext_led() is asy_wifi_service.py's own post-construction hook (used when the real device
    # wiring passes a driver in after both objects already exist) - proves the real class works
    # through that path too, not just the constructor kwarg.
    pixel = NeopixelDriver(0, neopixel_freq=100)
    conn = AsyConnTime(led_pin=None, ext_led=None, cfg_path=_tmp_cfg_dir())
    conn.set_ext_led(pixel)

    async def scenario() -> "tuple[int, ...]":
        overlay_task = pixel.start_asy_neopixel_led_overl()
        await asyncio.sleep(0)
        await conn.set_wifi_led(True)
        conn._led_on()
        await asyncio.sleep(0.05)
        write = pixel.pixel.writes[-1][0]
        await _cancel(overlay_task)
        return write

    assert run(scenario()) == (50, 50, 50)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
