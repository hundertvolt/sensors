"""Boots one real generated device and prints a labelled micropython.mem_info(1) map at each end of the two one-time
boot lists. Not a test_*.py file: scripts/test.sh never runs it.

Its consumer, tests_scripts/test_digital_twin_boot_contiguity.py, spawns it under the Unix-port binary and measures the
maps with tests_hardware/heap_map.py; the map goes to the platform print, not sys.stdout, so it is never read in-process
(Part I.4(f.1))."""

import gc
import sys

sys.path.insert(0, "ext")  # same reason as tests/_sensortask_scenarios.py's own insert
sys.path.append("digital_twin")  # the PC tiers' asyncio report; appended and dropped again, so tests/machine.py stays the one
import unix_port_unretrieved_report  # type: ignore[import-not-found, unused-ignore]  # unresolved only in CI's narrowed mypy pass

sys.path.pop()

import asyncio
import time

import machine
import micropython
import uctypes
from _async_harness import run
from _generated_module import boot_generated, fram_fake_class

import asy_spi_driver
import asy_system_service
import asy_uart_driver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from asy_base_classes import SetupFct, TaskStarter
    from asy_system_service import SystemService

# The bound mirroring tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py's, so a
# twin reading and a board reading are taken at the same positions of the same sequence.
_TIMERS_TIMEOUT_S = 15


def _keep_nothing(_log: object, _entry: object) -> None:
    pass


# The fakes' call and wire logs are test bookkeeping with no board counterpart, and their entries were
# 92-96% of a batch's new blocks: every log is one shared instance made here, before the seam, that keeps
# nothing, so the maps hold the firmware's own survivors. Each fake still builds its entry, as garbage.
_NO_CALL_LOG: "machine._CallLog[object]" = machine._CallLog()
_NO_WIRE_LOG = machine._WireLog(0)
machine._CallLog.append = _keep_nothing  # type: ignore[assignment, method-assign]
machine._WireLog.append = _keep_nothing  # type: ignore[assignment, method-assign]
machine._CallLog = lambda _maxlen=0: _NO_CALL_LOG  # type: ignore[assignment, misc, return-value]
machine._WireLog = lambda _maxlen=0: _NO_WIRE_LOG  # type: ignore[assignment, misc]
machine.Pin.value_log = staticmethod(lambda _id: _NO_CALL_LOG)  # type: ignore[assignment, method-assign]


async def _drive_timers(sysfunct: "SystemService", trigger_starters: "list[Callable[[], None]]", timer_starters: "list[Callable[[], None]]") -> bool:
    # main()'s step after the task starts: the trigger stagger's deadline sleeps, under 1 s in all.
    task = asyncio.create_task(sysfunct.start_timers(trigger_starters, timer_starters))
    deadline = time.ticks_add(time.ticks_ms(), int(_TIMERS_TIMEOUT_S * 1000))
    while not task.done() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        await asyncio.sleep(0)
    if not task.done():
        print(f"NOTE start_timers did not complete within {_TIMERS_TIMEOUT_S}s - a timer never fired")
        task.cancel()
        return False
    return True


def _dump(label: str) -> None:
    # mem_info(1) allocates nothing, so it cannot perturb what it measures - which is why every
    # position here is a map rather than a probe allocation (MEASUREMENTS M2.2's pinning artefact).
    gc.collect()
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


def _rings(label: str, module: "ModuleType") -> None:
    # One RING line per UART bus the device built: its receive ring's address and length, or "none".
    # Its consumer checks each ring sits with the boot's survivors and keeps its address afterwards.
    for name in sorted(dir(module)):
        bus = getattr(module, name)
        if isinstance(bus, asy_uart_driver.UART):
            ring = getattr(bus, "_ring", None)
            where = "none 0" if ring is None else f"0x{uctypes.addressof(ring):x} {len(ring)}"
            print(f"RING {label} {name} {where}")


async def _run_starter_loop(sysfunct: "SystemService", task_starters: "list[TaskStarter]", task_names: "list[str]") -> None:
    # main()'s step after the setup list. The map follows start_tasks() at once; the supervisor is never entered.
    await sysfunct.start_tasks(task_starters, task_names=task_names)
    _dump("after_starter_loop_end")


async def _main(device: str, cfg_path: str, settle_ms: int) -> int:
    unix_port_unretrieved_report.install()  # as microtest does for the suite this probe measures (Part I.4(e))
    asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
    module = __import__(f"sensortask_{device}")
    real_run_setups = asy_system_service.SystemService.run_setups

    async def seamed_run_setups(self: "SystemService", setups: "list[SetupFct]") -> None:
        _dump("batch_00")  # the seam: right before the setup list's first unit
        await real_run_setups(self, setups)

    asy_system_service.SystemService.run_setups = seamed_run_setups  # type: ignore[method-assign]

    _dump("baseline")
    started_ms = time.ticks_ms()
    module, _watchdog = await boot_generated(module, device, cfg_path=cfg_path, web_host="127.0.0.1", web_port=0)
    build_ms = time.ticks_diff(time.ticks_ms(), started_ms)
    _dump("after_batch")
    _rings("after_batch", module)

    sysfunct = getattr(module, "sysfunct", None)
    if sysfunct is None:
        print("RESULT: FAIL build_system() completed but left sysfunct unset")
        return 1
    # main()'s order: the task lists at the task starts, the trigger and timer lists once start_tasks() returned, then
    # the timers; the supervisor is never entered.
    task_starters = module._collect_task_starters()
    task_names = module._collect_task_names()
    await _run_starter_loop(sysfunct, task_starters, task_names)
    _rings("after_starter_loop_end", module)
    trigger_starters = module._collect_trigger_starters()
    timer_starters = module._collect_timer_starters()
    print(f"LISTS starters={len(task_starters)} triggers={len(trigger_starters)} timers={len(timer_starters)}")
    if not await _drive_timers(sysfunct, trigger_starters, timer_starters):
        return 1

    if settle_ms > 0:  # reported, never asserted on: the run phase undoes most of it (MEASUREMENTS M3.9)
        await asyncio.sleep_ms(settle_ms)
        _dump("after_settle")
    print(f"BOOT device={device} build_system_ms={build_ms} settle_ms={settle_ms}")
    print("RESULT: PASS")
    return 0


# sys.exit() unconditionally: the real supervised task graph leaves siblings parked in the shared
# task queue, which hangs the interpreter at exit (CLAUDE.md's known hang cause #2).
sys.exit(
    run(
        _main(
            sys.argv[1],
            sys.argv[2],
            int(sys.argv[3]) if len(sys.argv) > 3 else 0,
        ),
    ),
)
