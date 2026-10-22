"""The real task graph at MicroPython's own gc default while the HOST sweeps concurrent requests:
heap dumps idle, under load and idle again - phases read off the server's own connection count -
plus a map at the instant any GET route fails. Ends once the load has stopped (Part I.3)."""

import asyncio
import gc
import time

import _bench_device as device  # rendered: the bench device's generated module

from asy_print_log import PrintLog
from asy_webserver_service import ROUTES, WebserverService, _StaticRoutes

# @include _shared/facts.py
# @include _shared/map_dump.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from typing import Protocol

    from _shared.facts import done, fact
    from _shared.map_dump import dump
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts
    from machine import WDT

    class _Route(Protocol):
        # A GET handler as the class holds it, unbound: the owner first, then microdot's request and URL parts.
        def __call__(self, owner: object, *args: object, **kwargs: object) -> Awaitable[object]: ...

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force -
# the boot entry's 32768, or -1 if the attach interrupted main.py first (MEASUREMENTS M3.8).
gc.threshold(-1)
# A fixed wait, never an in-process readiness request: one would share the heap under measurement (Part E.9).
# @tunable l3.heap_under_connection_ceiling_boot_wait_s = 20
_BOOT_WAIT_S = 20
# @tunable l3.serving_at_default_gc_poll_ms = 1000
_POLL_MS = 1000
# @tunable l3.serving_at_default_gc_dump_every = 5
_DUMP_EVERY = 5  # polls per dump
# @tunable l3.serving_at_default_gc_busy_to_enter = 2
_BUSY_TO_ENTER = 2  # busy polls out of the last 3 before it counts as load, so one stray probe is not load
# @tunable l3.serving_at_default_gc_quiet_to_leave = 10
_QUIET_TO_LEAVE = 10  # consecutive idle polls; the host's own gaps between levels stay below this
# @tunable l3.serving_at_default_gc_post_dumps = 3
_POST_DUMPS = 3
# @tunable l3.serving_at_default_gc_window_s = 600
_WINDOW_S = 600  # hard bound, whatever the host does
_MAX_FAILURE_MAPS = 3  # the first few are the evidence; more would only flood the console
# Every GET handler of the webserver's one route table, and the static site's two.
_ROUTES = (
    (WebserverService, tuple(name for method, _path, name in ROUTES if method == "GET")),
    (_StaticRoutes, ("get_index", "get")),
)
_failure_maps = [0]
# The product's own unretrieved-task report at the error level, so it prints whatever level the board's config holds.
_REPORT = PrintLog(level=1, name="UNRETRIEVED TASK EXCEPTION:")


def _dumping_on_failure(route: "_Route") -> "_Route":
    # Re-raises unchanged, so the served outcome is exactly production's; no collect before the
    # dump - MicroPython already ran one before it raised.
    async def wrapped(owner: object, *args: object, **kwargs: object) -> object:
        try:
            return await route(owner, *args, **kwargs)  # kwargs: microdot passes URL parts by name
        except MemoryError:
            if _failure_maps[0] < _MAX_FAILURE_MAPS:
                _failure_maps[0] += 1
                dump(f"fail{_failure_maps[0]}")
            raise

    return wrapped


async def _observe(webserver: "WebserverService", wdt: "WDT") -> None:
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
            dump(f"{phase}{dumps[phase]:02d}")
            dumps[phase] += 1
            if phase == "post" and dumps["post"] >= _POST_DUMPS:
                return
        polls += 1
        wdt.feed()
        await asyncio.sleep_ms(_POLL_MS)
    fact("phases_incomplete", dumps)  # the window ran out: the host never loaded, or never stopped


async def _run() -> None:
    asyncio.get_event_loop().set_exception_handler(_REPORT.report_unretrieved)  # before main(): the firmware keeps it
    fact("gc_threshold", gc.threshold())
    wdt = arm()
    # Production config path: the only writes it can cause are the ones a production boot makes anyway (an absent
    # file's first write, a malformed file's repair).
    main_task = asyncio.get_event_loop().create_task(device.main(watchdog=wdt))
    try:
        await fed_sleep_ms(wdt, _BOOT_WAIT_S * 1000)
        webserver = device.webserver  # None until main() has built it
        fact("webserver_built", webserver is not None)
        if webserver is not None:
            await _observe(webserver, wdt)
    finally:
        main_task.cancel()
    fact("failure_maps", _failure_maps[0])
    done()


# On the CLASSES, before build_system(): each route binds its handler when it is registered.
for _cls, _names in _ROUTES:
    for _name in _names:
        setattr(_cls, _name, _dumping_on_failure(getattr(_cls, _name)))


asyncio.run(_run())
