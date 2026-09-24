"""The largest contiguous block each webserver data source and each GET route needs, measured by
running it on a heap pre-shaped so no free run exceeds S, for rising S. No network: the host
parses the NEED lines and the mem_info() summary after each sieve (SPECIFICATION.md Part I.3)."""

import asyncio
import gc
import sys

import micropython
import sensortask_dev

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any

    from asy_webserver_service import WebserverService

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force -
# the boot entry's 32768, or -1 if the attach interrupted main.py first (MEASUREMENTS 0B.7).
gc.threshold(-1)
# Hole sizes in GC blocks, ascending: 16-2,048 B on the RP2040, twice that on the twin. The effective
# largest free run is printed after each sieve too, so the host never has to trust the arithmetic.
_LADDER = (1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96, 128)
_BLOCK = 32 if sys.maxsize > 2**32 else 16  # GC block: 16 B on the RP2040, 32 B on the 64-bit twin
# The real WDT.feed() is C and allocates nothing, so on the board it runs before every probe; the
# twin's fake allocates, so there it runs once per rung, off the sieve (a rung is well under 8 s).
_FEED_PER_PROBE = sys.platform == "rp2"
_NO_REQUEST: "Any" = None  # every probed route ignores its request argument
_sieve: "list[Any]" = [None, None]  # the two chains' heads: holes, blockers


def _feed() -> None:
    if sensortask_dev.watchdog is not None:
        sensortask_dev.watchdog.feed()


def _build_sieve(hole_blocks: int) -> None:
    # Every free block, bottom-up, filled with 1-block chain nodes - k for the hole chain, then one
    # keeper - until nothing is left. A 1-block allocation advances the allocator's scan hint, so
    # they land in address order; dropping the hole chain leaves runs of at most k blocks.
    holes: Any = None
    keepers: Any = None
    gc.collect()  # no garbage may sit inside the pattern: freed later, it would merge two holes
    try:
        while True:
            count = 0  # a counter, not range(): the loop itself must allocate nothing but nodes
            while count < hole_blocks:
                holes = (holes,)
                count += 1
            keepers = (keepers,)
    except MemoryError:
        pass
    _sieve[0], _sieve[1] = None, keepers
    del holes
    gc.collect()


def _release_sieve() -> None:
    _sieve[0] = _sieve[1] = None
    gc.collect()


def _sources(ws: "WebserverService") -> "list[tuple[str, Callable[[], Awaitable[Any]]]]":
    probes: list[tuple[str, Callable[[], Awaitable[Any]]]] = []
    for key, fct in ws._status_sources.items():
        probes.append((f"status:{key}", fct))
    for name, fct in ws._maintenance_sensors.items():
        probes.append((f"maintenance:{name}", fct))
    for name, module in ws._error_sources.items():
        probes.append((f"errcount:{name}", module.get_error_counter))
    probes.append(("errcount:WEBSERVER", ws.pr.get_log))
    for name, module in ws._sensors.items():
        probes.append((f"data:{name}", module.get_dict_data))
        probes.append((f"cfg:{name}", module.get_dict_cfg))
    for endpoint, groups in ws._settings.items():
        for index, group in enumerate(groups):
            probes.append((f"settings:{endpoint}:{index}", group.module.get_dict_cfg))
    for path, handler in (
        ("/status", ws._get_status),
        ("/measurements", ws._get_measurements),
        ("/sensors", ws._get_sensors),
        ("/networking", ws._get_networking),
        ("/system", ws._get_system),
        ("/notification", ws._get_notification),
    ):
        probes.append((f"route:{path}", _whole_route(handler)))
    if ws._static_mount is not None:  # the page the 2026-09-23 sitting saw cut off, 1 KB per read
        probes.append(("route:/", _whole_route(ws._get_static_index)))
    return probes


def _whole_route(handler: "Callable[[Any], Awaitable[Any]]") -> "Callable[[], Awaitable[Any]]":
    # The handler AND microdot's own body loop (Response.body_iter(), a file's chunked reads
    # included) - everything but the socket write and microdot's own request parsing.
    async def run() -> int:
        response = await handler(_NO_REQUEST)
        total = 0
        async for piece in response.body_iter():
            total += len(piece)
        return total

    return run


async def _run() -> None:
    print(f"GC_THRESHOLD={gc.threshold()}")
    await sensortask_dev.build_system(web_host="127.0.0.1", web_port=8080)
    ws = sensortask_dev.webserver
    assert ws is not None
    probes = _sources(ws)
    # Warm-up and churn, off-sieve: first calls initialise caches that are not per-request cost.
    for label, fct in probes:
        await fct()
        gc.collect()
        before = gc.mem_alloc()
        result = await fct()
        print(f"CHURN {label} {gc.mem_alloc() - before}")
        del result
        _feed()
    print(f"BLOCK={_BLOCK} PROBES={len(probes)}")
    # Every probe at every rung, never pruned on success: a probe that degrades internally (a caught
    # MemoryError, logged) still returns normally, and only the host can see that in the log. Every
    # line printed on a sieve is built before it, so the instrument itself needs no block.
    lines = [(f"TRY {label}", f"RES {label} ok", f"RES {label} fail", fct) for label, fct in probes]
    rungs = [f"SIEVE {blocks}" for blocks in _LADDER]
    for rung, blocks in enumerate(_LADDER):
        _release_sieve()
        _feed()  # off-sieve, every rung, on both targets
        _build_sieve(blocks)
        print(rungs[rung])
        micropython.mem_info()  # the host reads "max free sz" from this: the effective S
        for try_line, ok_line, fail_line, fct in lines:
            if _FEED_PER_PROBE:
                _feed()
            print(try_line)
            try:
                await fct()
                print(ok_line)
            except MemoryError:
                print(fail_line)
    _release_sieve()
    print("RESULT: PASS")


try:
    asyncio.run(_run())
except Exception as e:  # a failure here is a result, reported rather than raised into the harness
    print(f"RESULT: FAIL {e!r}")
