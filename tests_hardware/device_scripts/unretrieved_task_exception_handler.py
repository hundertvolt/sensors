"""Isolated-driver device script: SYSTEM's unretrieved-task-exception report on real silicon, at both GC stages. It
reports the locked-heap report's allocations at DebugLevel 0 and 1, the USB console path, and the collected heap across
detached deaths through the real loop; the host gives the verdict. No FRAM, no flash write (SPECIFICATION.md Part F.1).
"""

import asyncio
import asyncio.core as asyncio_core  # type: ignore[import-not-found]  # asyncio's own context dict, read back below
import gc
import sys
import time

import micropython

from asy_system_service import SystemService

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _mpy_shed.time_mp import _TicksMs
    from _shared.facts import done, fact
    from _shared.watchdog import _FEED_STEP_MS, arm

_MESSAGE = "Task exception wasn't retrieved"  # asyncio's own (extmod/asyncio/core.py:27 at v1.29.0)
_ROUNDS = 10
_TASKS_PER_ROUND = 100
_LARGE_LOCAL = 2048  # a dead task's frame holding this much is what a kept context would pin
_DRIFT_BYTES = _LARGE_LOCAL // 4  # below one large local, so a single kept dead task exceeds it
_SETTLE_YIELDS = 8
_ERR = 1  # DebugLevel 1, errors (SPECIFICATION.md Part A.8)
# @tunable gc.threshold_bytes = 32768
_GC_THRESHOLD = 32768
_STAGES = (-1, _GC_THRESHOLD)


class _ExhaustionError(MemoryError):
    """A MemoryError printed under its own name: a level-1 print of it stays clear of the memory gate's words."""


def _at_threshold(svc: SystemService, wdt: "machine.WDT", threshold: int) -> "dict[str, object]":
    # Each GC stage set, never inherited (SPECIFICATION.md I.4(e)): a soft reset keeps the boot entry's threshold.
    gc.threshold(threshold)
    result: dict[str, object] = {"gc_threshold": gc.threshold(), "reports": _locked_reports(svc), "console_allocates": _console_path_allocates()}
    # The hammer at DebugLevel 0: silent, so the genuine allocation failures never reach the console.
    wdt.feed()
    fed = time.ticks_ms()
    settled = _deaths(_TASKS_PER_ROUND)  # first-use allocations land before the baseline
    drift = [0] * _ROUNDS
    baseline = _settled_alloc()
    free_before = gc.mem_free()
    started = time.ticks_ms()
    for i in range(_ROUNDS):
        settled = _deaths(_TASKS_PER_ROUND) and settled
        drift[i] = _settled_alloc() - baseline
        fed = _feed_due(wdt, fed)
    result["hammer_ms"] = time.ticks_diff(time.ticks_ms(), started)
    result["settled"] = settled
    result["context_held"] = asyncio_core._exc_context["exception"] is not None or asyncio_core._exc_context["future"] is not None
    result["drift"] = drift
    result["baseline_alloc"] = baseline
    result["free_before"] = free_before
    # The contrast: asyncio's default handler keeps the last dead task; it prints that one probe.
    asyncio.get_event_loop().set_exception_handler(None)
    before = _settled_alloc()
    _deaths(1)
    result["default_handler_kept"] = _settled_alloc() - before
    svc.pr.report_unretrieved(None, asyncio_core._exc_context)
    asyncio.get_event_loop().set_exception_handler(svc.pr.report_unretrieved)
    wdt.feed()
    gc.collect()
    result["free_after"] = gc.mem_free()
    return result


def _console_path_allocates() -> bool:
    # The USB CDC write path, through mp_hal_stdout_tx_strn(), with the heap locked.
    exc = _raised(ValueError("probe"))
    micropython.heap_lock()
    try:
        print("SYSTEM", _MESSAGE)
        sys.print_exception(exc)
    except MemoryError:
        return True
    finally:
        micropython.heap_unlock()
    return False


def _deaths(n_tasks: int) -> bool:
    # True when every dying task had ended within the settle yields.
    settled = [False]

    async def scenario() -> None:
        tasks = [asyncio.create_task(_dies(n)) for n in range(n_tasks)]  # held, never awaited
        for _ in range(_SETTLE_YIELDS):
            await asyncio.sleep(0)
        settled[0] = all(task.done() for task in tasks)

    asyncio.run(scenario())
    return settled[0]


async def _dies(n: int) -> None:
    # Every other death a genuine allocation failure; every fourth holds a large local in its frame.
    if n % 2:
        micropython.heap_lock()
        try:
            bytearray(16)
        finally:
            micropython.heap_unlock()
    held = bytearray(_LARGE_LOCAL if n % 4 == 0 else 16)
    raise ValueError("probe", len(held))


def _feed_due(wdt: "machine.WDT", fed: "_TicksMs") -> "_TicksMs":
    # Feeds between rounds once half a feed step has passed: on silicon a feed allocates nothing, while the twin's
    # watchdog model allocates a record and a countdown task per feed, which a measured window must not hold.
    now = time.ticks_ms()
    if time.ticks_diff(now, fed) < _FEED_STEP_MS // 2:
        return fed
    wdt.feed()
    return now


def _genuine_memory_error() -> BaseException:
    caught: BaseException | None = None
    micropython.heap_lock()
    try:
        bytearray(16)
    except MemoryError as e:
        caught = e
    finally:
        micropython.heap_unlock()
    if caught is None:
        raise RuntimeError("bytearray() allocated with the heap locked")
    return caught


async def _install(svc: SystemService) -> None:
    # The real install path: start_tasks() sets the report where nothing is set yet; no supervisor is needed.
    await svc.start_tasks([_parked_starter], task_names=["parked"])


def _locked_reports(svc: SystemService) -> "list[dict[str, object]]":
    # The report itself with the heap locked (raises if it allocates), then unlocked with its allocation measured.
    reports: list[dict[str, object]] = []
    cases = (
        ("raised", 0, _raised(ValueError("probe"))),
        ("locked_heap", 0, _genuine_memory_error()),
        ("raised", _ERR, _raised(ValueError("probe"))),
        ("exhaustion_subclass", _ERR, _raised(_ExhaustionError("simulated allocation failure"))),
    )
    for case, level, exc in cases:
        svc.pr.set_level(level)
        context = {"message": _MESSAGE, "exception": exc, "future": svc}
        micropython.heap_lock()
        try:
            svc.pr.report_unretrieved(None, context)
        finally:
            micropython.heap_unlock()
        cleared = context["exception"] is None and context["future"] is None
        gc.collect()
        context = {"message": _MESSAGE, "exception": exc, "future": svc}
        before = gc.mem_alloc()
        started = time.ticks_us()
        svc.pr.report_unretrieved(None, context)
        took = time.ticks_diff(time.ticks_us(), started)
        delta = gc.mem_alloc() - before
        reports.append({"case": case, "level": level, "cleared": cleared, "alloc_delta": delta, "us": took})  # a label: a class name could be a gate word
    svc.pr.set_level(0)
    return reports


def _main() -> None:
    wdt = arm()
    fact("gc_threshold", list(_STAGES))
    # The premise, as on a fresh board: no handler set (a PC-tier runner installs its own, which start_tasks() keeps).
    asyncio.get_event_loop().set_exception_handler(None)
    svc = SystemService(_ntp_never_synced, watchdog=wdt)
    asyncio.run(_install(svc))
    fact("installed", asyncio.get_event_loop().get_exception_handler() == svc.pr.report_unretrieved)
    fact("bounds", {"drift_bytes": _DRIFT_BYTES, "large_local": _LARGE_LOCAL, "deaths": _ROUNDS * _TASKS_PER_ROUND})
    for n, threshold in enumerate(_STAGES):
        fact(f"stage_{n}", _at_threshold(svc, wdt, threshold))
    done()


async def _ntp_never_synced() -> bool:
    return False


async def _parked() -> None:
    await asyncio.Event().wait()


def _parked_starter() -> "asyncio.Task[None]":
    return asyncio.create_task(_parked())


def _raised(exc: BaseException) -> BaseException:
    try:
        raise exc
    except BaseException as caught:
        return caught


def _settled_alloc() -> int:
    # Read once asyncio.run() returned: its main task, which can keep a stale queue link to the last task, is gone.
    gc.collect()
    return gc.mem_alloc()


_main()
