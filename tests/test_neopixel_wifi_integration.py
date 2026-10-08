"""Cross-module seams of a real NeopixelDriver: asy_wifi_service.py's ext_led= on WifiService (the LEDControl Protocol and
its flash task's hotspot patterns), a real WebserverService's error_sources (the _ModuleLike shape) and a generated device's
timer-starter collection. Only tests/neopixel.py's fake write surface is mocked (and, for the patterns, the sleeps)."""

import asyncio
import json
import os
import sys

sys.path.insert(0, "ext")  # scripts/test.sh's MICROPYPATH excludes ext/, where the real vendored microdot lives

from _sensortask_scenarios import build
from _shared_rest_roundtrip import drain_json_response_body
from _tmp_scratch import TmpScratch
from microdot import Microdot, Request, Response

from asy_neopixel_driver import NeopixelDriver
from asy_webserver_service import RouteSources, ServingLimits, WebserverService
from asy_wifi_service import WifiConfig, WifiService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from typing_extensions import Self

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


async def _run_until(predicate: "Callable[[], bool]", max_yields: int) -> bool:
    # A bound in yields, not milliseconds: an overlay write needs one wake-up of the overlay task.
    for _ in range(max_yields):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


def test_real_neopixel_driver_on_off_toggle_through_wifi_service_ext_led() -> None:
    pixel = NeopixelDriver(0)
    pixel.neopixel_freq = 100  # the driver's own fixed state, set from outside
    pixel.neopixel_dt = 0.01
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_tmp_cfg_dir())

    def last_is(colour: "tuple[int, int, int]") -> "Callable[[], bool]":
        return lambda: pixel._pixel.writes[-1:] == [[colour]]

    async def scenario() -> "tuple[bool, bool, bool]":
        overlay_task = pixel.start_asy_overlay()
        await asyncio.sleep(0)
        await conn.set_wifi_led(status=True)  # self._led becomes self._ext_led (pixel)
        conn._led_on()
        on_seen = await _run_until(last_is((50, 50, 50)), 10)  # the shipped overlay brightness
        conn._led_off()
        off_seen = await _run_until(last_is((0, 0, 0)), 10)
        conn._led_toggle()
        toggle_seen = await _run_until(last_is((50, 50, 50)), 10)  # toggled from off -> on
        await _cancel(overlay_task)
        return on_seen, off_seen, toggle_seen

    assert run(scenario()) == (True, True, True)


_ON = (50, 50, 50)  # the shipped overlay brightness, as the test above reads it
_OFF = (0, 0, 0)
_PHASE_YIELDS = 4  # per flash phase: the overlay task's flag wake-up lands inside it, so every phase is written
_PATTERN_YIELDS = 32  # several whole on/off cycles of either pattern


class _FlashSleeps:
    # For the block, asyncio.sleep() records each non-zero duration and yields _PHASE_YIELDS times instead of
    # waiting: the flash task's phases become scheduling steps. Process-wide, restored however the block exits.
    def __init__(self) -> None:
        self.durations: list[float] = []

    def __enter__(self) -> "Self":
        self._real = asyncio.sleep

        async def _fast(seconds: float) -> None:
            if seconds:
                self.durations.append(seconds)
            for _ in range(_PHASE_YIELDS):
                await self._real(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # a module-attribute swap, restored in __exit__
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real


async def _yields(count: int) -> None:
    for _ in range(count):
        await asyncio.sleep(0)


def _frames(pixel: NeopixelDriver, start: int) -> "list[tuple[int, ...]]":
    # The pixel's committed frames from write `start` on, each run of equal frames counted once.
    frames: list[tuple[int, ...]] = []
    for write in pixel._pixel.writes[start:]:
        if not frames or frames[-1] != write[0]:
            frames.append(write[0])
    return frames


def _pairs(durations: "list[float]") -> "set[tuple[float, float]]":
    # The (on, off) pairs a flash task slept, starting from its first on phase.
    return {(durations[i], durations[i + 1]) for i in range(0, len(durations) - 1, 2)}


def _hotspot_conn(pixel: NeopixelDriver) -> WifiService:
    conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_tmp_cfg_dir())
    run(conn.setup())
    return conn


async def _stop_flash(conn: WifiService) -> None:
    # reconnect_wifi() is the product's canceller of the flash task; the cancelled task is then awaited out.
    flash = conn._ledflash
    conn.reconnect_wifi()
    if flash is not None:
        await _cancel(flash)


def test_the_hotspot_pattern_blinks_a_real_neopixel_driver_through_the_flash_task() -> None:
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps() as sleeps:

        async def scenario() -> "list[tuple[int, ...]]":
            overlay_task = pixel.start_asy_overlay()
            await conn.set_wifi_led(status=True)
            await conn._hotspot_client_absent()  # no station on the hotspot: its pattern starts
            await _yields(_PATTERN_YIELDS)
            frames = _frames(pixel, 0)
            await _stop_flash(conn)
            await _cancel(overlay_task)
            return frames

        frames = run(scenario())
    assert frames[:4] == [_ON, _OFF, _ON, _OFF]  # every phase reached the real pixel, on first
    pairs = _pairs(sleeps.durations)
    assert len(pairs) == 1  # one pattern ran, unchanged
    on_s, off_s = pairs.pop()
    assert on_s > off_s  # the hotspot pattern: mostly on, with a short dark beat


def test_a_station_on_the_hotspot_swaps_the_real_pixels_pattern_and_its_leaving_restores_it() -> None:
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps() as sleeps:

        async def scenario() -> "tuple[list[float], list[float], list[float], list[tuple[int, ...]]]":
            overlay_task = pixel.start_asy_overlay()
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
            await _cancel(overlay_task)
            durations = sleeps.durations
            return durations[:joined_at], durations[joined_at:left_at], durations[left_at:], client_frames

        hotspot, client, restored, client_frames = run(scenario())
    assert len(_pairs(hotspot)) == 1
    assert len(_pairs(client)) == 1
    client_on_s, client_off_s = _pairs(client).pop()
    assert client_on_s == client_off_s  # an even blink, never a steady light that reads as a home link
    assert _pairs(client) != _pairs(hotspot)
    assert _pairs(restored) == _pairs(hotspot)
    assert _OFF in client_frames and client_frames.count(_ON) >= 2  # the client pattern blinks the real pixel


def test_with_the_wifi_led_off_both_hotspot_patterns_leave_the_real_pixel_dark() -> None:
    pixel = NeopixelDriver(0)
    conn = _hotspot_conn(pixel)
    with _FlashSleeps():

        async def scenario() -> "list[tuple[int, ...]]":
            overlay_task = pixel.start_asy_overlay()
            await conn.set_wifi_led(status=False)  # LEDWifiOn off: every pattern obeys it
            await conn._hotspot_client_absent()
            await _yields(_PATTERN_YIELDS)
            conn._hotspot_client_connected()
            await _yields(_PATTERN_YIELDS)
            await _stop_flash(conn)
            await _cancel(overlay_task)
            return _frames(pixel, 0)

        frames = run(scenario())
    assert _ON not in frames


async def _uptime_s() -> int:  # the drop window's clock; no connection is served here
    return 0


def test_a_neopixel_driver_is_an_error_source_of_the_webserver() -> None:
    pixel = NeopixelDriver(0)
    app = Microdot()
    routes = RouteSources((), None, None, None, None, None, None, (), [pixel])
    serving = ServingLimits(2048, 256, 3, None, 0.2, 0.5, "0.0.0.0", 80)
    WebserverService(app, routes, serving, uptime_s=_uptime_s)  # type: ignore[arg-type]  # the stub's Microdot takes concrete Request/Stream types, src's _MicrodotApp its Protocols - removal trigger: SPECIFICATION.md B.15

    def dispatch(method: str, body: "dict[str, Any] | None") -> Response:
        raw = b"" if body is None else json.dumps(body).encode()
        headers = {"Content-Length": str(len(raw)), "Content-Type": "application/json"}
        return run(app.dispatch_request(Request(app, ("127.0.0.1", 12345), method, "/status", "1.1", headers, body=raw)))  # type: ignore[no-any-return]  # the upstream stub leaves dispatch_request() unannotated - removal trigger: SPECIFICATION.md B.15

    def neopixel_entry() -> "dict[str, Any]":
        entry: dict[str, Any] = json.loads(drain_json_response_body(dispatch("GET", None).body))["errcount"]["NEOPIXEL"]
        return entry

    run(pixel.pr.err_s("boom", errno=1))
    before = neopixel_entry()
    assert before["counter"] == 1
    assert before["history"][-1] == {"num": 1, "type": "E"}  # the newest slot holds the logged entry
    reset = dispatch("PUT", {"ResetErrors": True})
    assert reset.status_code == 200
    assert json.loads(reset.body)["res"] == "OK"
    after = neopixel_entry()
    assert after["counter"] == 0
    assert {"num": 1, "type": "E"} not in after["history"]


def _a_device_with_a_neopixel() -> str:
    # The device comes from the generated wiring plans, chosen by its neopixel instance, never by name.
    for name in sorted(os.listdir("build/generated_src")):
        if name.endswith("_wiring_plan.json"):
            with open("build/generated_src/" + name) as f:
                plan = json.load(f)
            if "neopixel" in plan["instances"]:
                return str(plan["device"])
    raise AssertionError("no generated device declares a neopixel instance")


def test_the_drivers_empty_timer_list_reaches_a_generated_device() -> None:
    module = build(_a_device_with_a_neopixel(), cfg_path=_tmp_cfg_dir())
    assert isinstance(module.neopixel, NeopixelDriver)
    assert module.neopixel.get_timer_starters() == []
    starters = module._collect_timer_starters()  # collects the empty list among the other modules' starters
    assert all(callable(s) for s in starters)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
