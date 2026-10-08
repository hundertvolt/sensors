# Boots one real generated device and prints a labelled micropython.mem_info(1) map at each end of
# the two one-time boot lists, with SystemService's gc.collect() calls either live or suppressed.
# Not a test_*.py file, so scripts/test.sh's glob never runs it - see the header of its own consumer.
#
# Its consumer is tests_scripts/test_digital_twin_boot_contiguity.py, which spawns this under the
# Unix-port binary and measures the captured maps with tests_hardware/heap_map.py. The map goes to
# the platform print rather than sys.stdout, so it cannot be read back in-process (Part I.4(f.1)).
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
from _generated_module import boot_generated
from _sensortask_scenarios import fram_fake_class

import asy_spi_driver
import asy_uart_driver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType
    from typing import Any

    from asy_base_classes import SetupFct
    from asy_system_service import SystemService

    _Starter = Callable[[], asyncio.Task[Any]]

# Bounds mirroring tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py's, so a
# twin reading and a board reading are taken at the same positions of the same sequence.
# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms = 20000
_STARTER_LOOP_TIMEOUT_MS = 20000
# @tunable l3.heap_layout_after_full_boot_sequence_timers_timeout_s = 15
_TIMERS_TIMEOUT_S = 15

_ARM_LIVE = "collects"
_ARM_SUPPRESSED = "suppressed"


def _keep_nothing(_log: object, _entry: object) -> None:
    pass


# The fakes' call and wire logs are test bookkeeping with no board counterpart, and their entries were
# 92-96% of a batch's new blocks: every log is one shared instance made here, before the seam, that keeps
# nothing, so the maps hold the firmware's own survivors. Each fake still builds its entry, as garbage.
_NO_CALL_LOG = machine._CallLog()
_NO_WIRE_LOG = machine._WireLog(0)
machine._CallLog.append = _keep_nothing  # type: ignore[method-assign, assignment]
machine._WireLog.append = _keep_nothing  # type: ignore[method-assign, assignment]
machine._CallLog = lambda _maxlen=0: _NO_CALL_LOG  # type: ignore[assignment, misc]
machine._WireLog = lambda _maxlen=0: _NO_WIRE_LOG  # type: ignore[assignment, misc]
machine.Pin.value_log = staticmethod(lambda _id: _NO_CALL_LOG)  # type: ignore[method-assign, assignment]


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


class _ProbeGc:
    # Stands in for asy_system_service's `gc` at both boot lists' collect sites: dumps a map at the positions
    # asked for, then forwards to the real collect only on the live arm. Its label names the list running,
    # "batch" inside SystemService.run_setups(), else "starter"; reassigning the module attribute is the mock.

    # A dumped position collects on BOTH arms, via _dump() - the seam map has to be post-collect or
    # the two arms anchor at different places and nothing is comparable. So the suppressed arm keeps
    # the leading collect and loses the per-module ones, which makes it a conservative control.

    def __init__(self, *, live: bool, dump_at: "dict[str, tuple[int, ...]]") -> None:
        self.live = live
        self.dump_at = dump_at
        self.label = "starter"
        self.calls = {"batch": 0, "starter": 0}

    def collect(self) -> None:
        n = self.calls[self.label]
        if n in self.dump_at.get(self.label, ()):
            _dump(f"{self.label}_{n:02d}")
        if self.live:
            gc.collect()
        self.calls[self.label] = n + 1


async def _drive_timers(sysfunct: "SystemService", trigger_starters: "list[Callable[[], None]]", timer_starters: "list[Callable[[], None]]") -> bool:
    # main()'s step after the task starts. tests/machine.py's Timer fake never fires by itself, so each armed
    # stagger wait is fired with the same _sequencer_timer.trigger() tests/test_asy_system_service.py uses.
    task = asyncio.create_task(sysfunct.start_timers(trigger_starters, timer_starters))
    deadline = time.ticks_add(time.ticks_ms(), int(_TIMERS_TIMEOUT_S * 1000))
    while not task.done() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        await asyncio.sleep(0)
        if sysfunct._sequencer_timer.callback is not None:
            sysfunct._sequencer_timer.trigger()
    if not task.done():
        print(f"NOTE start_timers did not complete within {_TIMERS_TIMEOUT_S}s - a timer never fired")
        task.cancel()
        return False
    return True


async def _run_starter_loop(sysfunct: "SystemService", task_starters: "list[_Starter]") -> bool:
    # main()'s step after the setup list. start_tasks() returns after its final collect, so the map follows at
    # once; the supervisor is never entered.
    try:
        await asyncio.wait_for_ms(sysfunct.start_tasks(task_starters), _STARTER_LOOP_TIMEOUT_MS)
    except asyncio.TimeoutError:
        print(f"NOTE start_tasks did not return within {_STARTER_LOOP_TIMEOUT_MS} ms")
        return False
    _dump("after_starter_loop_end")
    return True


async def _main(device: str, arm: str, cfg_path: str, settle_ms: int) -> int:
    unix_port_unretrieved_report.install()  # as microtest does for the suite this probe measures (Part I.4(e))
    # Checked, not assumed: an unrecognised arm would silently measure the suppressed one and
    # turn the live bound into a confusing failure rather than an obvious argument mistake.
    assert arm in (_ARM_LIVE, _ARM_SUPPRESSED), f"unknown arm {arm!r} - expected {_ARM_LIVE!r} or {_ARM_SUPPRESSED!r}"
    live = arm == _ARM_LIVE
    asy_spi_driver._SPI = fram_fake_class(device)  # type: ignore[misc]
    module: Any = __import__(f"sensortask_{device}")
    import asy_system_service

    probe_gc = _ProbeGc(live=live, dump_at={"batch": (0,)})
    asy_system_service.gc = probe_gc  # type: ignore[assignment]
    real_run_setups = asy_system_service.SystemService.run_setups

    async def labelled_run_setups(self: "SystemService", setups: "list[SetupFct]") -> None:
        probe_gc.label = "batch"
        try:
            await real_run_setups(self, setups)
        finally:
            probe_gc.label = "starter"

    asy_system_service.SystemService.run_setups = labelled_run_setups  # type: ignore[method-assign]

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
    task_starters = module._collect_task_starters()
    trigger_starters = module._collect_trigger_starters()
    timer_starters = module._collect_timer_starters()
    print(f"LISTS starters={len(task_starters)} triggers={len(trigger_starters)} timers={len(timer_starters)} batch_collects={probe_gc.calls['batch']}")

    # main()'s order: the task starts, then the timers; the supervisor is never entered.
    if not await _run_starter_loop(sysfunct, task_starters):
        return 1
    _rings("after_starter_loop_end", module)
    if not await _drive_timers(sysfunct, trigger_starters, timer_starters):
        return 1
    print(f"COUNTS batch_collects={probe_gc.calls['batch']} starter_collects={probe_gc.calls['starter']}")

    if settle_ms > 0:  # reported, never asserted on: the run phase undoes most of it (MEASUREMENTS M3.9)
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
