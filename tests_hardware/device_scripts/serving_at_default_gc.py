"""The real task graph at MicroPython's own gc default while the HOST sweeps concurrent requests:
heap dumps idle, under load and idle again - phases read off the server's own connection count -
plus a map at the instant any GET route fails. Ends once the load has stopped (Part I.3)."""

import asyncio
import gc
import time

import micropython
import sensortask_dev

from asy_webserver_service import WebserverService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    _Route = Callable[..., Awaitable[object]]

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force -
# the boot entry's 32768, or -1 if the attach interrupted main.py first (MEASUREMENTS M3.8).
gc.threshold(-1)
_BOOT_S = 20
_POLL_MS = 1000
_DUMP_EVERY = 5  # polls per dump
_BUSY_TO_ENTER = 2  # busy polls out of the last 3 before it counts as load, so one probe is not
_QUIET_TO_LEAVE = 10  # consecutive idle polls; the host's own gaps between levels stay below this
_POST_DUMPS = 3
_WINDOW_S = 600  # hard bound, whatever the host does
_MAX_FAILURE_MAPS = 3  # the first few are the evidence; more would only flood the console
_ROUTES = ("_get_status", "_get_measurements", "_get_sensors", "_get_networking", "_get_system", "_get_notification", "_get_static_index", "_get_static")
_failure_maps = [0]


def _dump(label: str) -> None:
    # heap_map.parse_labelled()'s own delimiters, matched exactly.
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


def _dumping_on_failure(route: "_Route") -> "_Route":
    # Re-raises unchanged, so the served outcome is exactly production's; no collect before the
    # dump - MicroPython already ran one before it raised.
    async def wrapped(self: "WebserverService", *args: object, **kwargs: object) -> object:
        try:
            return await route(self, *args, **kwargs)  # kwargs: microdot passes URL parts by name
        except MemoryError:
            if _failure_maps[0] < _MAX_FAILURE_MAPS:
                _failure_maps[0] += 1
                _dump(f"fail{_failure_maps[0]}")
            raise

    return wrapped


# On the CLASS, before build_system(): each route binds self._get_* when it is registered.
for _name in _ROUTES:
    setattr(WebserverService, _name, _dumping_on_failure(getattr(WebserverService, _name)))


async def _observe(webserver: "WebserverService") -> None:
    # Idle dumps collect first, so they are the LIVE layout the next request inherits. Load dumps
    # do not: a collect there would change the very sawtooth being observed.
    phase, recent, quiet, polls, dumps = "pre", [0, 0, 0], 0, 0, {"pre": 0, "load": 0, "post": 0}
    started = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
        busy = 1 if webserver._open_conns.value else 0  # plain int: no lock, no coroutine, no allocation
        recent = recent[1:] + [busy]
        quiet = 0 if busy else quiet + 1
        if phase == "pre" and sum(recent) >= _BUSY_TO_ENTER:
            phase, polls = "load", 0
        elif phase == "load" and quiet >= _QUIET_TO_LEAVE:
            phase, polls = "post", 0
        if polls % _DUMP_EVERY == 0:
            if phase != "load":
                gc.collect()
            _dump(f"{phase}{dumps[phase]:02d}")
            dumps[phase] += 1
            if phase == "post" and dumps["post"] >= _POST_DUMPS:
                return
        polls += 1
        await asyncio.sleep_ms(_POLL_MS)
    print(f"PHASES_INCOMPLETE {dumps}")  # the window ran out: the host never loaded, or never stopped


async def _run() -> None:
    print(f"GC_THRESHOLD={gc.threshold()}")
    main_task = asyncio.get_event_loop().create_task(sensortask_dev.main())
    await asyncio.sleep(_BOOT_S)
    try:
        assert sensortask_dev.webserver is not None
        await _observe(sensortask_dev.webserver)
    finally:
        main_task.cancel()
    print(f"FAILURE_MAPS={_failure_maps[0]}")
    print("RESULT: PASS window complete")


try:
    asyncio.run(_run())
except Exception as e:  # a failure here is a result, reported rather than raised into the harness
    print(f"RESULT: FAIL {e!r}")
