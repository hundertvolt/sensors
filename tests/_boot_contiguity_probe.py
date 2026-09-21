# Boots one real generated device and prints a labelled micropython.mem_info(1) map at each end of
# the two one-time boot lists, with the emitted gc.collect() calls either live or suppressed.
# Not a test_*.py file, so scripts/test.sh's glob never runs it - see the header of its own consumer.
#
# Its consumer is tests_scripts/test_digital_twin_boot_contiguity.py, which spawns this under the
# Unix-port binary and measures the captured maps with tests_hardware/heap_map.py. The map goes to
# the platform print rather than sys.stdout, so it cannot be read back in-process (Part I.4(f.1)).
import gc
import sys

sys.path.insert(0, "ext")  # same reason as tests/_sensortask_scenarios.py's own insert

import asyncio
import time

import micropython
from _sensortask_scenarios import fram_fake_class

import asy_spi_driver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from system_service import SystemService

    _Starter = Callable[[], asyncio.Task[Any]]

# Bounds mirroring tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py's, so a
# twin reading and a board reading are taken at the same positions of the same sequence.
_STARTER_LOOP_TIMEOUT_MS = 20000
_STARTER_LOOP_GRACE_MS = 250
_TIMERS_TIMEOUT_S = 15

_ARM_LIVE = "collects"
_ARM_SUPPRESSED = "suppressed"


def _dump(label: str) -> None:
    # mem_info(1) allocates nothing, so it cannot perturb what it measures - which is why every
    # position here is a map rather than a probe allocation (MEASUREMENTS 7F.8's pinning artefact).
    gc.collect()
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


class _ProbeGc:
    """Stands in for the `gc` module at the emitted collect sites: dumps a map at the positions
    asked for, then forwards to the real collect only on the live arm. Module-attribute
    reassignment is this project's mocking mechanism (MicroPython has no unittest.mock)."""

    def __init__(self, tag: str, *, live: bool, dump_at: "tuple[int, ...]") -> None:
        self.tag = tag
        self.live = live
        self.dump_at = dump_at
        self.calls = 0

    def collect(self) -> None:
        if self.calls in self.dump_at:
            _dump(f"{self.tag}_{self.calls:02d}")
        if self.live:
            gc.collect()
        self.calls += 1


async def _drive_timers(sysfunct: "SystemService", timer_starters: "list[Callable[[], None]]") -> bool:
    # main()'s own next step. tests/machine.py's Timer fake never fires by itself, so the chain is
    # advanced with the same sequencer_timer.trigger() tests/test_system_service.py uses.
    task = asyncio.create_task(sysfunct.start_timers(timer_starters))
    for _ in range(max(len(timer_starters) - 1, 0)):
        await asyncio.sleep(0)
        sysfunct.sequencer_timer.trigger()
    try:
        await asyncio.wait_for(task, _TIMERS_TIMEOUT_S)
    except asyncio.TimeoutError:
        print(f"NOTE start_timers did not complete within {_TIMERS_TIMEOUT_S}s - a timer never fired")
        return False
    return True


async def _run_starter_loop(sysfunct: "SystemService", task_starters: "list[_Starter]") -> bool:
    # start_and_check_tasks() never returns - it falls into the supervisor - and its task list is a
    # local, so the loop's own end is only observable by counting the starters as they land.
    started: list[int] = []
    inner = sysfunct._start_task

    async def counting(starter: "_Starter", n: int) -> "asyncio.Task[Any] | None":
        task = await inner(starter, n)
        started.append(n)
        return task

    sysfunct._start_task = counting  # type: ignore[method-assign]
    supervisor = asyncio.create_task(sysfunct.start_and_check_tasks(task_starters))
    deadline = time.ticks_add(time.ticks_ms(), _STARTER_LOOP_TIMEOUT_MS)
    while len(started) < len(task_starters) and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        await asyncio.sleep_ms(20)
    if len(started) < len(task_starters):
        print(f"NOTE only {len(started)} of {len(task_starters)} starters ran within {_STARTER_LOOP_TIMEOUT_MS} ms")
        supervisor.cancel()
        return False
    # The last starter has landed but the loop has not: its final sleep and its final collect are
    # still to come, and that collect is part of what is being measured.
    await asyncio.sleep_ms(1000 // max(len(task_starters), 1) + _STARTER_LOOP_GRACE_MS)
    _dump("after_starter_loop_end")
    supervisor.cancel()
    return True


async def _main(device: str, arm: str, cfg_path: str, settle_ms: int) -> int:
    # Checked, not assumed: an unrecognised arm would silently measure the suppressed one and
    # turn the live bound into a confusing failure rather than an obvious argument mistake.
    assert arm in (_ARM_LIVE, _ARM_SUPPRESSED), f"unknown arm {arm!r} - expected {_ARM_LIVE!r} or {_ARM_SUPPRESSED!r}"
    live = arm == _ARM_LIVE
    asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
    module: Any = __import__(f"sensortask_{device}")
    import system_service

    batch_gc = _ProbeGc("batch", live=live, dump_at=(0,))
    starter_gc = _ProbeGc("starter", live=live, dump_at=())
    module.gc = batch_gc
    system_service.gc = starter_gc  # type: ignore[assignment]

    _dump("baseline")
    started_ms = time.ticks_ms()
    await module.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=0)
    build_ms = time.ticks_diff(time.ticks_ms(), started_ms)
    _dump("after_batch")

    sysfunct = module.sysfunct
    if sysfunct is None:
        print("RESULT: FAIL build_system() completed but left sysfunct unset")
        return 1
    task_starters = module._collect_task_starters()
    timer_starters = module._collect_timer_starters()
    print(f"LISTS starters={len(task_starters)} timers={len(timer_starters)} batch_collects={batch_gc.calls}")

    if not await _drive_timers(sysfunct, timer_starters):
        return 1
    if not await _run_starter_loop(sysfunct, task_starters):
        return 1
    print(f"COUNTS batch_collects={batch_gc.calls} starter_collects={starter_gc.calls}")

    if settle_ms > 0:  # reported, never asserted on: the run phase undoes most of it (7F.9)
        await asyncio.sleep_ms(settle_ms)
        _dump("after_settle")
    print(f"BOOT device={device} arm={arm} build_system_ms={build_ms} settle_ms={settle_ms}")
    print("RESULT: PASS")
    return 0


# sys.exit() unconditionally: the real supervised task graph leaves siblings parked in the shared
# task queue, which hangs the interpreter at exit (CLAUDE.md's known hang cause #2).
sys.exit(
    asyncio.run(
        _main(
            sys.argv[1],
            sys.argv[2],
            sys.argv[3],
            int(sys.argv[4]) if len(sys.argv) > 4 else 0,
        ),
    ),
)
