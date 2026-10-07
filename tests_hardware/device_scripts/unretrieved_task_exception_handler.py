"""Isolated-driver device script: SYSTEM's unretrieved-task-exception report on real silicon. With the heap locked it
returns, allocates nothing and releases the dead task at DebugLevel 0 and 1, the USB console path included; detached
deaths through the real loop leave the collected heap where it was. No FRAM, no flash write (SPECIFICATION.md Part F.1)."""

import asyncio
import asyncio.core as asyncio_core  # type: ignore[import-not-found]  # asyncio's own context dict, read back below
import gc
import sys
import time

import machine
import micropython

from asy_system_service import SystemService

# @tunable wdt.timeout_ms = 8000
_WDT_TIMEOUT_MS = 8000
_MESSAGE = "Task exception wasn't retrieved"  # asyncio's own (extmod/asyncio/core.py:27 at v1.29.0)
_ROUNDS = 10
_TASKS_PER_ROUND = 100
_LARGE_LOCAL = 2048  # a dead task's frame holding this much is what a kept context would pin
_DRIFT_BYTES = _LARGE_LOCAL // 4  # below one large local, so a single kept dead task fails it
_SETTLE_YIELDS = 8
_ERR = 1  # DebugLevel 1, errors (SPECIFICATION.md Part A.8)
# @tunable gc.threshold_bytes = 32768
_GC_THRESHOLD = 32768

wdt = machine.WDT(timeout=_WDT_TIMEOUT_MS)


class _ExhaustionError(MemoryError):
    """A MemoryError printed under its own name: a level-1 print of it stays clear of the memory gate's words."""


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


def _deaths(n_tasks: int) -> None:
    async def scenario() -> None:
        tasks = [asyncio.create_task(_dies(n)) for n in range(n_tasks)]  # held, never awaited
        for _ in range(_SETTLE_YIELDS):
            await asyncio.sleep(0)
        if not all(task.done() for task in tasks):
            raise RuntimeError("a dying task had not ended within the settle yields")

    asyncio.run(scenario())
    wdt.feed()


def _settled_alloc() -> int:
    # Read once asyncio.run() returned: its main task, which can keep a stale queue link to the last task, is gone.
    gc.collect()
    return gc.mem_alloc()


async def _install(svc: SystemService) -> None:
    # The real install path: start_and_check_tasks() sets the report where nothing is set yet, then supervises.
    supervisor = asyncio.create_task(svc.start_and_check_tasks([_parked_starter]))
    while svc._supervisor_task is None:
        await asyncio.sleep_ms(50)
        wdt.feed()
    supervisor.cancel()
    try:
        await supervisor
    except asyncio.CancelledError:
        pass


def _locked_report_failures(svc: SystemService) -> "list[str]":
    # (1) The report itself with the heap locked, then its two outputs with nothing to swallow a failure.
    failures: list[str] = []
    cases = (
        (0, _raised(ValueError("probe"))),
        (0, _genuine_memory_error()),
        (_ERR, _raised(ValueError("probe"))),
        (_ERR, _raised(_ExhaustionError("simulated allocation failure"))),
    )
    for level, exc in cases:
        svc.pr.set_level(level)
        context = {"message": _MESSAGE, "exception": exc, "future": svc}
        micropython.heap_lock()
        try:
            svc.pr.report_unretrieved(None, context)
        finally:
            micropython.heap_unlock()
        if context["exception"] is not None or context["future"] is not None:
            failures.append(f"level {level} {type(exc).__name__}: context not cleared")
        gc.collect()
        context = {"message": _MESSAGE, "exception": exc, "future": svc}
        before = gc.mem_alloc()
        started = time.ticks_us()
        svc.pr.report_unretrieved(None, context)
        took = time.ticks_diff(time.ticks_us(), started)
        delta = gc.mem_alloc() - before
        print(f"REPORT level={level} exc={type(exc).__name__} alloc_delta={delta} us={took}")
        if delta != 0:
            failures.append(f"level {level} {type(exc).__name__}: report left {delta} B allocated")
    exc = _raised(ValueError("probe"))
    micropython.heap_lock()
    try:
        print(svc.pr.name, _MESSAGE)  # the USB CDC write path, through mp_hal_stdout_tx_strn()
        sys.print_exception(exc)
    except MemoryError:
        failures.append("print() or sys.print_exception() allocated on the console path")
    finally:
        micropython.heap_unlock()
    svc.pr.set_level(0)
    return failures


def _stage(svc: SystemService, threshold: int) -> "list[str]":
    # Both GC stages (SPECIFICATION.md I.4(e)): set, never inherited - a soft reset keeps the boot entry's threshold.
    gc.threshold(threshold)
    print(f"GC_THRESHOLD={gc.threshold()}")
    failures = _locked_report_failures(svc)
    wdt.feed()

    # (2) Hammer at DebugLevel 0: silent, so the genuine allocation failures never reach the console.
    _deaths(_TASKS_PER_ROUND)  # first-use allocations land before the baseline
    drift = [0] * _ROUNDS
    baseline = _settled_alloc()
    free_before = gc.mem_free()
    started = time.ticks_ms()
    for i in range(_ROUNDS):
        _deaths(_TASKS_PER_ROUND)
        drift[i] = _settled_alloc() - baseline
    hammer_ms = time.ticks_diff(time.ticks_ms(), started)
    if asyncio_core._exc_context["exception"] is not None or asyncio_core._exc_context["future"] is not None:
        failures.append("asyncio's context still holds the last dead task")
    if max(drift) > _DRIFT_BYTES:
        failures.append(f"collected heap drifted {max(drift)} B over {_ROUNDS * _TASKS_PER_ROUND} deaths")

    # (3) The contrast: asyncio's default handler keeps the last dead task; it prints that one probe.
    asyncio.get_event_loop().set_exception_handler(None)
    before = _settled_alloc()
    _deaths(1)
    kept = _settled_alloc() - before
    svc.pr.report_unretrieved(None, asyncio_core._exc_context)
    asyncio.get_event_loop().set_exception_handler(svc.pr.report_unretrieved)
    gc.collect()
    print(f"HEAP threshold={threshold} baseline_alloc={baseline} free_before={free_before} free_after={gc.mem_free()} drift={drift}")
    print(f"HAMMER threshold={threshold} deaths={_ROUNDS * _TASKS_PER_ROUND} ms={hammer_ms} default_handler_kept={kept}")
    if kept < _LARGE_LOCAL:
        failures.append(f"the default handler kept only {kept} B - the contrast measured nothing")
    return [f"threshold {threshold}: {f}" for f in failures]


def _main() -> None:
    svc = SystemService(_ntp_never_synced, watchdog=wdt)
    asyncio.run(_install(svc))
    if asyncio.get_event_loop().get_exception_handler() != svc.pr.report_unretrieved:
        print("RESULT: FAIL start_and_check_tasks() did not install SYSTEM's report on a loop with no handler")
        return
    failures = _stage(svc, -1) + _stage(svc, _GC_THRESHOLD)
    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(f"RESULT: PASS report allocation-free at levels 0 and 1 and both GC stages, {2 * _ROUNDS * _TASKS_PER_ROUND} deaths without drift")


_main()
