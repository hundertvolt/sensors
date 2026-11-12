"""The largest contiguous block each webserver data source and each GET route needs, measured by
running it on a heap pre-shaped so no free run exceeds S, for rising S. No network: the host
parses the NEED lines and the mem_info() summary after each sieve (SPECIFICATION.md Part I.3)."""

import asyncio
import gc
import os
import sys

import _bench_device as device  # rendered: the bench device's generated module
import micropython
from microdot import Microdot

from asy_system_service import BOOT_DONE
from asy_webserver_service import ROUTES

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

    from asy_webserver_service import WebserverService

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force -
# the boot entry's 32768, or -1 if the attach interrupted main.py first (MEASUREMENTS M3.8).
gc.threshold(-1)
# Hole sizes in GC blocks, ascending: 16-2,048 B on the RP2040, twice that on the twin. The effective
# largest free run is printed after each sieve too, so the host never has to trust the arithmetic.
_LADDER = (1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96, 128)
_BLOCK = 32 if sys.maxsize > 2**32 else 16  # GC block: 16 B on the RP2040, 32 B on the 64-bit twin
# The real WDT.feed() is C and allocates nothing, so on the board it runs before every probe; the
# twin's fake allocates, so there it runs once per rung, off the sieve (a rung is well under 8 s).
_FEED_PER_PROBE = sys.platform == "rp2"
# A scratch config directory: the build's first writes land there, never on the production config, and go after.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
_sieve: "list[object]" = [None, None]  # the two chains' heads: holes, blockers
_wdt = arm()  # the script's own: build_system() takes it, run_setups() and _feed() feed it


class _NoopHolder:  # a request's sock half: the static route hands its opened file to hold()
    def hold(self, closable: object) -> None:
        pass


class _ProbeRequest:  # every probed route ignores its request but the static one, which reads only this pair
    sock = (_NoopHolder(), _NoopHolder())


_PROBE_REQUEST = _ProbeRequest()


def _build_sieve(hole_blocks: int) -> None:
    # Every free block, bottom-up, filled with 1-block chain nodes - k for the hole chain, then one
    # keeper - until nothing is left. A 1-block allocation advances the allocator's scan hint, so
    # they land in address order; dropping the hole chain leaves runs of at most k blocks.
    holes: object = None
    keepers: object = None
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


def _feed() -> None:
    _wdt.feed()


async def _measure(probes: "list[tuple[str, Callable[[], Awaitable[object]]]]") -> None:
    # Warm-up and churn, off-sieve: first calls initialise caches that are not per-request cost.
    churn: dict[str, int] = {}
    for label, fct in probes:
        await fct()
        gc.collect()
        before = gc.mem_alloc()
        result = await fct()
        churn[label] = gc.mem_alloc() - before
        del result
        _feed()
    fact("churn", churn)
    fact("block", _BLOCK)
    fact("probes", len(probes))
    fact("rungs", list(_LADDER))
    print(f"BLOCK={_BLOCK}")  # the sieve lines below stay raw: heap_map.parse_allocation_need()'s input
    # Every probe at every rung, never pruned on success: a probe that degrades internally (a caught
    # MemoryError, logged) still returns normally, and only the host can see that in the log. Every
    # line printed on a sieve is built before it, so the instrument itself needs no block.
    lines = [(f"TRY {label}", f"RES {label} ok", f"RES {label} fail", fct) for label, fct in probes]
    rungs = [f"SIEVE {blocks}" for blocks in _LADDER]
    for rung, blocks in enumerate(_LADDER):
        _release_sieve()
        await asyncio.sleep_ms(0)  # off-sieve: the loop runs between rungs
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
            await asyncio.sleep_ms(0)  # a singleton generator: yielding allocates nothing, so the sieve stays as built
    _release_sieve()


def _release_sieve() -> None:
    _sieve[0] = _sieve[1] = None
    gc.collect()


def _remove_scratch() -> None:
    # Every config file the scratch build wrote, then the directory: the board keeps nothing of this script's config.
    for name in os.listdir(_SCRATCH_CFG_PATH):
        os.remove(_SCRATCH_CFG_PATH + name)
    os.rmdir(_SCRATCH_CFG_PATH.rstrip("/"))


async def _run() -> None:
    fact("gc_threshold", gc.threshold())
    try:
        os.mkdir(_SCRATCH_CFG_PATH.rstrip("/"))
    except OSError:  # left by an aborted run: reused, then removed below - and it must exist, or the stat raises
        os.stat(_SCRATCH_CFG_PATH.rstrip("/"))
    try:
        await device.build_system(watchdog=_wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, ws = device.sysfunct, device.webserver
        assert sysfunct is not None and ws is not None
        await sysfunct.run_setups(device._collect_setups())  # main()'s next step: the sources as a boot leaves them
        probes, index_handlers = _sources(ws)
        fact("index_handlers", index_handlers)
        await _measure(probes)
    finally:
        sysfunct = device.sysfunct
        if sysfunct is not None:
            sysfunct.boot_phase(BOOT_DONE)  # the reset after this script reads as the harness's, never a boot failure
        _remove_scratch()
    done()


def _sources(ws: "WebserverService") -> "tuple[list[tuple[str, Callable[[], Awaitable[object]]]], int]":
    # Every data source and every GET route as a probe, the routes from the webserver's one table; with the count of
    # "/" handlers the app registered, which the host requires to be one.
    probes: list[tuple[str, Callable[[], Awaitable[object]]]] = []
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
    for method, path, name in ROUTES:
        if method == "GET":
            probes.append((f"route:{path}", _whole_route(getattr(ws, name))))
    app: object = ws._app  # typed by the service's own Protocol, which declares no route table
    assert isinstance(app, Microdot)
    index_handlers = 0
    for methods, pattern, handler, _prefix, _subapp in app.url_map:
        if pattern.url_pattern == "/" and "GET" in methods:  # the page the 2026-09-23 sitting saw cut off, 1 KB per read
            probes.append(("route:/", _whole_route(handler)))
            index_handlers += 1
    return probes, index_handlers


def _whole_route(handler: "Callable[[_ProbeRequest], Awaitable[object]]") -> "Callable[[], Awaitable[object]]":
    # The handler AND microdot's own body loop (Response.body_iter(), a file's chunked reads
    # included) - everything but the socket write and microdot's own request parsing.
    async def run() -> int:
        response = await handler(_PROBE_REQUEST)
        total = 0
        async for piece in response.body_iter():  # type: ignore[attr-defined]  # microdot's Response, unannotated
            total += len(piece)
        return total

    return run


asyncio.run(_run())
