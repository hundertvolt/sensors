"""Cross-module integration: a real NeopixelDriver passed as asy_wifi_service.py's own ext_led=, proving the LEDControl Protocol (on/off/toggle) holds end to end - test_asy_wifi_service.py only exercises a FakeLED double for this.
Only tests/neopixel.py's fake write surface is mocked; every other layer runs for real."""

import asyncio

from _tmp_scratch import TmpScratch

from asy_neopixel_driver import NeopixelDriver
from asy_wifi_service import AsyConnTime, WifiConfig

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


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("neopixel_wifi")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


async def _cancel(task: "asyncio.Task[None]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def test_real_neopixel_driver_on_off_toggle_through_wifi_service_ext_led() -> None:
    pixel = NeopixelDriver(0, neopixel_freq=100)
    conn = AsyConnTime(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_tmp_cfg_dir())

    async def scenario() -> "tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]":
        overlay_task = pixel.start_asy_neopixel_led_overl()
        await asyncio.sleep(0)
        await conn.set_wifi_led(status=True)  # self.led becomes self.ext_led (pixel)
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
