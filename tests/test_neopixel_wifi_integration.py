"""Cross-module seams of a real NeopixelDriver: asy_wifi_service.py's ext_led= (the LEDControl Protocol, on/off/toggle),
a real WebserverService's error_sources (the _ModuleLike shape) and a generated device's timer-starter collection.
Only tests/neopixel.py's fake write surface is mocked; every other layer runs for real."""

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
from asy_wifi_service import AsyConnTime, WifiConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
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


async def _run_until(predicate: "Callable[[], bool]", max_yields: int) -> bool:
    # A bound in yields, not milliseconds: an overlay write needs one wake-up of the overlay task.
    for _ in range(max_yields):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


def test_real_neopixel_driver_on_off_toggle_through_wifi_service_ext_led() -> None:
    pixel = NeopixelDriver(0, neopixel_freq=100)
    conn = AsyConnTime(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=_tmp_cfg_dir())

    def last_is(colour: "tuple[int, int, int]") -> "Callable[[], bool]":
        return lambda: pixel.pixel.writes[-1:] == [[colour]]

    async def scenario() -> "tuple[bool, bool, bool]":
        overlay_task = pixel.start_asy_neopixel_led_overl()
        await asyncio.sleep(0)
        await conn.set_wifi_led(status=True)  # self.led becomes self.ext_led (pixel)
        conn._led_on()
        on_seen = await _run_until(last_is((50, 50, 50)), 10)  # default led_overl_bri
        conn._led_off()
        off_seen = await _run_until(last_is((0, 0, 0)), 10)
        conn._led_toggle()
        toggle_seen = await _run_until(last_is((50, 50, 50)), 10)  # toggled from off -> on
        await _cancel(overlay_task)
        return on_seen, off_seen, toggle_seen

    assert run(scenario()) == (True, True, True)


def test_a_neopixel_driver_is_an_error_source_of_the_webserver() -> None:
    pixel = NeopixelDriver(0)
    app = Microdot()
    routes = RouteSources((), None, None, None, None, None, None, (), [pixel])  # type: ignore[list-item]  # error_sources reads only name, pr and the error-counter pair, all present
    serving = ServingLimits(2048, 256, 3, None, 0.2, 0.5, "0.0.0.0", 80)
    WebserverService(app, routes, serving)  # type: ignore[arg-type]  # the stub's Microdot takes concrete Request/Stream types, src's _MicrodotApp its Protocols - removal trigger: SPECIFICATION.md B.15

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
