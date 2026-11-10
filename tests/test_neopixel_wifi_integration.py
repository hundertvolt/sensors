"""Cross-module seams of a real NeopixelDriver: asy_wifi_service.py's ext_led= on WifiService (the LEDControl Protocol
and its flash task's hotspot patterns), and a generated device's error-source and timer-starter collections. Only fakes/neopixel.py's fake write surface is mocked (and the patterns' sleeps)."""

import asyncio
import os
import sys

sys.path.insert(0, "ext")  # scripts/test.sh's MICROPYPATH excludes ext/, where the real vendored microdot lives

from _async_harness import cancel, run
from _fast_sleep import check_sleep_ms
from _generated_tree import require_fresh
from _sensortask_scenarios import build
from _tmp_scratch import TmpScratch
from _twin_devices import devices_with, distinct_wirings

from asy_neopixel_driver import NeopixelDriver
from asy_wifi_service import WifiConfig, WifiService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from typing_extensions import Self


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("neopixel_wifi")


def test_real_neopixel_driver_on_off_toggle_through_wifi_service_ext_led() -> None:
    pixel = NeopixelDriver(0, neopixel_freq=100)
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_scratch.dir())
    run(conn.setup())

    def last_is(colour: "tuple[int, int, int]") -> "Callable[[], bool]":
        return lambda: pixel._pixel.writes[-1:] == [[colour]]

    async def scenario() -> "tuple[bool, bool, bool]":
        await asyncio.sleep(0)
        await conn.set_wifi_led(status=True)  # self._led becomes self._ext_led (pixel)
        conn._led_on()
        on_seen = await _run_until(last_is((50, 50, 50)), 10)  # the shipped overlay brightness
        conn._led_off()
        off_seen = await _run_until(last_is((0, 0, 0)), 10)
        conn._led_toggle()
        toggle_seen = await _run_until(last_is((50, 50, 50)), 10)  # toggled from off -> on
        return on_seen, off_seen, toggle_seen

    assert run(scenario()) == (True, True, True)


_ON = (50, 50, 50)  # the shipped overlay brightness, as the test above reads it
_OFF = (0, 0, 0)
# Per flash phase: twice the least (2, measured with the overlay's bounded wait as with its plain flag wait) at which
# the overlay's write lands inside the phase, so every phase is written.
_PHASE_YIELDS = 4
_PATTERN_YIELDS = 8 * _PHASE_YIELDS  # four whole on/off cycles of either pattern


class _FlashSleeps:
    # For the block, asyncio.sleep_ms() records each non-zero duration in ms (with a conn, only its flash task's) and
    # both sleeps yield _PHASE_YIELDS times instead of waiting: the flash phases become scheduling steps. Restored on exit.
    def __init__(self, conn: "WifiService | None" = None) -> None:
        self.durations: list[int] = []
        self._conn = conn

    def __enter__(self) -> "Self":
        self._real = (asyncio.sleep, asyncio.sleep_ms)
        real_sleep_ms = self._real[1]
        conn = self._conn

        async def _fast_ms(ms: int) -> None:
            check_sleep_ms(ms)
            if ms and (conn is None or asyncio.current_task() is conn._ledflash):
                self.durations.append(ms)
            for _ in range(_PHASE_YIELDS):
                await real_sleep_ms(0)

        async def _fast(_seconds: float) -> None:
            for _ in range(_PHASE_YIELDS):
                await real_sleep_ms(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # a module-attribute swap, restored in __exit__
        asyncio.sleep_ms = _fast_ms  # type: ignore[assignment]  # likewise, the form every flash phase sleeps in
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep, asyncio.sleep_ms = self._real


def _devices_with_a_neopixel() -> "list[str]":
    # One device per distinct whole wiring among those wiring a neopixel, as the test reads each one's whole timer
    # collection; none wiring one fails in devices_with().
    require_fresh()
    wired = devices_with("neopixel")
    return [device for device in distinct_wirings() if device in wired]


def _blocked_dir() -> str:
    # A config path whose WIFI file is a directory: the store's setup() fails, as with no readable Wi-Fi configuration.
    path = _scratch.dir()
    os.mkdir(path + "config_WIFI.cfg")
    return path


def _frames(pixel: NeopixelDriver, start: int) -> "list[tuple[int, ...]]":
    # The pixel's committed frames from write `start` on, each run of equal frames counted once.
    frames: list[tuple[int, ...]] = []
    for write in pixel._pixel.writes[start:]:
        if not frames or frames[-1] != write[0]:
            frames.append(write[0])
    return frames


def _hotspot_conn(pixel: NeopixelDriver) -> WifiService:
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_scratch.dir())
    run(conn.setup())
    return conn


def _pairs(durations: "list[int]") -> "set[tuple[int, int]]":
    # The (on, off) pairs in ms a flash task slept, starting from its first on phase.
    return {(durations[i], durations[i + 1]) for i in range(0, len(durations) - 1, 2)}


async def _run_until(predicate: "Callable[[], bool]", max_yields: int) -> bool:
    # A bound in yields, not milliseconds: an overlay write follows its flag through three tasks, one turn each
    # (the flag's waiter, the bounded wait's runner, the overlay task).
    for _ in range(max_yields):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


async def _stop_flash(conn: WifiService) -> None:
    # reconnect_wifi() is the product's canceller of the flash task; the cancelled task is then awaited out.
    flash = conn._ledflash
    conn.reconnect_wifi()
    if flash is not None:
        await cancel(flash)


def test_the_hotspot_pattern_blinks_a_real_neopixel_driver_through_the_flash_task() -> None:
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps() as sleeps:

        async def scenario() -> "list[tuple[int, ...]]":
            await conn.set_wifi_led(status=True)
            await conn._hotspot_client_absent()  # no station on the hotspot: its pattern starts
            await _yields(_PATTERN_YIELDS)
            frames = _frames(pixel, 0)
            await _stop_flash(conn)
            return frames

        frames = run(scenario())
    assert frames[:4] == [_ON, _OFF, _ON, _OFF]  # every phase reached the real pixel, on first
    pairs = _pairs(sleeps.durations)
    assert len(pairs) == 1  # one pattern ran, unchanged
    on_ms, off_ms = pairs.pop()
    assert on_ms > off_ms  # the hotspot pattern: mostly on, with a short dark beat


def test_a_station_on_the_hotspot_swaps_the_real_pixels_pattern_and_its_leaving_restores_it() -> None:
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps() as sleeps:

        async def scenario() -> "tuple[list[int], list[int], list[int], list[tuple[int, ...]]]":
            await conn.set_wifi_led(status=True)
            await conn._hotspot_client_absent()
            await _yields(_PATTERN_YIELDS)
            joined_at, joined_write = len(sleeps.durations), len(pixel._pixel.writes)
            conn._hotspot_client_connected()  # a phone joined the hotspot
            await _yields(_PATTERN_YIELDS)
            left_at = len(sleeps.durations)
            client_frames = _frames(pixel, joined_write)
            await conn._hotspot_client_absent()  # ... and left again
            await _yields(_PATTERN_YIELDS)
            await _stop_flash(conn)
            durations = sleeps.durations
            return durations[:joined_at], durations[joined_at:left_at], durations[left_at:], client_frames

        hotspot, client, restored, client_frames = run(scenario())
    assert len(_pairs(hotspot)) == 1
    assert len(_pairs(client)) == 1
    client_on_ms, client_off_ms = _pairs(client).pop()
    assert client_on_ms == client_off_ms  # an even blink, never a steady light that reads as a home link
    assert _pairs(client) != _pairs(hotspot)
    assert _pairs(restored) == _pairs(hotspot)
    assert _OFF in client_frames and client_frames.count(_ON) >= 2  # the client pattern blinks the real pixel


def test_with_the_wifi_led_off_both_hotspot_patterns_leave_the_real_pixel_dark() -> None:
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps():

        async def scenario() -> "list[tuple[int, ...]]":
            await conn.set_wifi_led(status=False)  # LEDWifiOn off: every pattern obeys it
            await conn._hotspot_client_absent()
            await _yields(_PATTERN_YIELDS)
            conn._hotspot_client_connected()
            await _yields(_PATTERN_YIELDS)
            await _stop_flash(conn)
            return _frames(pixel, 0)

        frames = run(scenario())
    assert _ON not in frames


def test_the_silent_mode_leaves_a_real_neopixel_driver_dark_until_a_link() -> None:
    # The second failed streak after a hotspot phase goes silent (owner, 2026-10-08: "It should look like turned off."):
    # the flash task ends and no frame lights the pixel, through a silent attempt's LED calls and LEDWifiOn, until a link.
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps():

        async def scenario() -> "tuple[list[tuple[int, ...]], bool, list[tuple[int, ...]], list[tuple[int, ...]]]":
            await conn.set_wifi_led(status=True)
            await conn._hotspot_client_absent()  # the hotspot pattern blinks
            await _yields(_PATTERN_YIELDS)
            blinking = _frames(pixel, 0)
            flash = conn._ledflash
            conn._hotspot_started_once = True
            conn._connection_failures = conn._conn_fail_to_hotspot - 1  # the next failure ends the second streak
            silent_from = len(pixel._pixel.writes)  # the entry writes its dark frame at once
            await conn._register_sta_connection_failure()
            await _yields(_PATTERN_YIELDS)
            conn._led_toggle()  # a silent attempt's own LED calls
            conn._led_on()
            await conn.set_wifi_led(status=True)
            await _yields(_PATTERN_YIELDS)
            silent = _frames(pixel, silent_from)
            ended = flash is not None and flash.done()
            linked_from = len(pixel._pixel.writes)
            conn._on_sta_connected()  # a later attempt links
            await _yields(_PATTERN_YIELDS)
            linked = _frames(pixel, linked_from)
            await _stop_flash(conn)
            return blinking, ended, silent, linked

        blinking, ended, silent, linked = run(scenario())
    assert _ON in blinking and _OFF in blinking
    assert ended is True
    assert silent == [_OFF], silent  # the entry's dark frame, nothing lit after it
    assert linked == [_ON]  # the link lights the LED as LEDWifiOn says


def test_the_no_configuration_pattern_blinks_a_real_neopixel_driver_and_obeys_led_wifi_on() -> None:
    # Guard: with no readable configuration the connect loop shows its own pattern on the real pixel, a short blink
    # (the hotspot's inverted), dark while LEDWifiOn is off and shown again once it is on (owner, 2026-10-02).
    pixel = NeopixelDriver(0)
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_blocked_dir())
    run(conn.setup())
    assert conn.cfgmgr.valid is False
    with _FlashSleeps(conn) as sleeps:

        async def scenario() -> "tuple[list[tuple[int, ...]], list[tuple[int, ...]], list[tuple[int, ...]]]":
            loop = conn.start_asy_connect()
            await _yields(_PATTERN_YIELDS)
            shown = _frames(pixel, 0)
            dark_from = len(pixel._pixel.writes)  # off writes its dark frame at once
            await conn.set_wifi_led(status=False)
            await _yields(_PATTERN_YIELDS)
            dark = _frames(pixel, dark_from)
            await conn.set_wifi_led(status=True)
            back_from = len(pixel._pixel.writes)
            await _yields(_PATTERN_YIELDS)
            back = _frames(pixel, back_from)
            await cancel(loop)
            await _stop_flash(conn)
            return shown, dark, back

        shown, dark, back = run(scenario())
    assert _ON in shown and _OFF in shown
    pairs = _pairs(sleeps.durations)
    assert len(pairs) == 1
    on_ms, off_ms = pairs.pop()
    assert on_ms < off_ms  # a short blink, the hotspot pattern's inverse
    assert dark == [_OFF], dark
    assert _ON in back


async def _yields(count: int) -> None:
    for _ in range(count):
        await asyncio.sleep(0)


def test_no_generated_device_lists_its_neopixel_among_the_status_error_sources() -> None:
    # The pixel has nothing it can fail at: no /status errcount entry and no ResetErrors source, on every device.
    for device in _devices_with_a_neopixel():
        module = build(device, cfg_path=_scratch.dir())
        names = [source.name for source in module._collect_error_sources()]
        assert "NEOPIXEL" not in names and names, (device, names)


def test_the_drivers_empty_timer_list_reaches_every_generated_device_wiring_it() -> None:
    for device in _devices_with_a_neopixel():
        module = build(device, cfg_path=_scratch.dir())
        assert isinstance(module.neopixel, NeopixelDriver), device
        assert module.neopixel.get_timer_starters() == [], device
        starters = module._collect_timer_starters()  # collects the empty list among the other modules' starters
        assert all(callable(s) for s in starters), device


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
