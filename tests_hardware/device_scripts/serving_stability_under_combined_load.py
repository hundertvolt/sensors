"""Isolated-driver device script: the real production boot at MicroPython's OWN reactive gc default,
so the host can hammer every heavy REST endpoint while every sensor task runs and see whether the
board serves it all without a single allocation failure (CLAUDE.md's I.4(e) bar)."""

import asyncio
import gc
import time

import micropython
import sensortask_dev

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_webserver_service import WebserverService

# Set explicitly, not merely left alone: mpremote interrupts main.py but does NOT reset the
# interpreter, so the boot entry's own gc.threshold(32768) is still in force when this starts
# (SPECIFICATION.md Part I.4). -1 is MicroPython's own reactive default.
gc.threshold(-1)
_SAMPLE_INTERVAL_MS = 5000
_COLLECT_BEFORE_SAMPLE = False  # combined_load_sweep.py --margin sets True: each dump then shows only the live
# set, the free-heap margin under load. Instrumentation, never the fix: it also cleans the heap every
# sample, so a margin run's stability verdict is not evidence - the plain run's is.
_PEAK_SAMPLE_MS = 0  # combined_load_sweep.py --peak sets 20: a low-water sampler replaces the maps. It never
# collects and allocates only on a new minimum, so a --peak run's stability verdict IS evidence.
_GC_RISE_BYTES = 2048
_NO_SAMPLER = False  # combined_load_sweep.py --peak --no-sampler sets True: no maps, no sampler, no counter
# wrapper - the control for whether the instrumentation itself costs heap. Footprint printed once.
_WINDOW_S = 150


def _dump(label: str) -> None:
    if _COLLECT_BEFORE_SAMPLE:
        gc.collect()
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


async def _sampler() -> None:
    started = time.ticks_ms()
    index = 0
    while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
        _dump(f"t{index:03d}_{time.ticks_diff(time.ticks_ms(), started)}ms")
        index += 1
        await asyncio.sleep_ms(_SAMPLE_INTERVAL_MS)


_REJECTED = [0]  # reject-when-full closes, counted on the device so the host's "refused" can be checked


def _count_rejections(webserver: "WebserverService") -> None:
    # Installed as soon as the webserver exists, before it accepts: the host's load starts when
    # /status first answers, seconds before READY, and a later install missed those rejections.
    counter, limit, increment = webserver._open_conns, webserver._max_connections, webserver._open_conns.increment

    async def _counting_increment() -> int:
        current = await increment()
        if current > limit:
            _REJECTED[0] += 1
        return current

    counter.increment = _counting_increment  # type: ignore[method-assign]  # instrumentation only, never src/


async def _peak_sampler(webserver: "WebserverService") -> None:
    # Never collects. A rise of >= 2 KB in mem_free() between two 20 ms reads marks a GC the run's own
    # threshold triggered (explicit C-side frees are small: every serving allocation is <= 256 B), so
    # that reading is heap minus live set; a user-class __del__ or weakref sentinel is not on rp2.
    started = time.ticks_ms()
    low: dict[int, int] = {}  # open connections -> lowest post-GC free heap seen at that count
    seen: dict[int, int] = {}  # open connections -> samples taken at that count
    previous, overall, collections = gc.mem_free(), -1, 0
    while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
        if _COLLECT_BEFORE_SAMPLE:  # --peak --margin: an exact live set every sample, at the cost of the verdict
            gc.collect()
        free = gc.mem_free()
        conns = webserver._open_conns.value or 0  # a plain int read: no coroutine, no allocation
        seen[conns] = seen.get(conns, 0) + 1
        if _COLLECT_BEFORE_SAMPLE or free >= previous + _GC_RISE_BYTES:
            collections += 1
            if free < low.get(conns, free + 1):
                low[conns] = free
            if overall < 0 or free < overall:
                overall = free
                print(f"PEAK_NEW_MIN t={time.ticks_diff(time.ticks_ms(), started)}ms conns={conns} free={free}")
                micropython.mem_info()
        previous = free
        await asyncio.sleep_ms(_PEAK_SAMPLE_MS)
    print(f"PEAK_SUMMARY heap={gc.mem_free() + gc.mem_alloc()} min_free_after_gc={overall} collections={collections} rejected={_REJECTED[0]}")
    for conns in sorted(seen):
        print(f"PEAK_AT conns={conns} samples={seen[conns]} min_free_after_gc={low.get(conns, -1)}")


async def _run() -> None:
    print(f"GC_THRESHOLD={gc.threshold()}")
    if _NO_SAMPLER:  # heap before the task graph: this script's compiled code plus the imports production pays too
        gc.collect()
        print(f"FOOTPRINT script_before_boot alloc={gc.mem_alloc()} free={gc.mem_free()}")
    main_task = asyncio.get_event_loop().create_task(sensortask_dev.main())
    if _PEAK_SAMPLE_MS:
        while sensortask_dev.webserver is None:  # assigned during construction, seconds before serving
            await asyncio.sleep_ms(10)
        _count_rejections(sensortask_dev.webserver)
    await asyncio.sleep(20)  # the host waits for READY, then drives the load itself (Part E.9)
    if not _NO_SAMPLER:
        _dump("after_boot")
    print("READY")
    try:
        if _NO_SAMPLER:
            await asyncio.sleep(_WINDOW_S)
        elif _PEAK_SAMPLE_MS:
            assert sensortask_dev.webserver is not None
            await _peak_sampler(sensortask_dev.webserver)
        else:
            await _sampler()
    finally:
        main_task.cancel()
    print("RESULT: PASS window complete")


try:
    asyncio.run(_run())
except Exception as e:  # a failure here is a result, reported rather than raised into the harness
    print(f"RESULT: FAIL {e!r}")
