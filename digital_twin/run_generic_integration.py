"""Generic twin entry point: boots any buildgen-generated sensortask_<device> module against its wiring-plan JSON and
serves until stopped; chips are found through machine.peripheral() by walking the plan. Its --test-* flags are test-only
instrumentation, off by default (owner, 2026-09-30)."""

import asyncio
import errno
import gc
import json
import os
import random
import select
import struct
import sys
import time
from collections import namedtuple

import micropython

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable
    from types import ModuleType
    from typing import NamedTuple, Protocol, TypeVar

    from _mpy_shed import IOBase_mp
    from _mpy_shed.time_mp import _TicksMs
    from launch import FaultSpec, HangSpec, _Chip, _KnobChip, _Plan

    T = TypeVar("T")

    class _Booted(Protocol):
        # The generated module's globals and entry this runner reads; the module is chosen at run time (--module).
        @property
        def __file__(self) -> str | None: ...
        def main(self, *, watchdog: "machine.WDT", cfg_path: str, debug: int | None, web_host: str, web_port: int) -> "Coroutine[object, object, None]": ...

        @property
        def webserver(self) -> object: ...  # read only: any built module's own WebserverService type matches

    class _Watchdog(Protocol):
        # What the shutdown line reads off the run's watchdog.
        @property
        def feed_count(self) -> int: ...
        @property
        def feed_times(self) -> Iterable[_TicksMs | int]: ...
        @property
        def timeout(self) -> int: ...
        @property
        def would_have_triggered_count(self) -> int: ...

    class _Clearable(Protocol):
        def clear(self) -> None: ...

    class _OverCapComm(Protocol):
        # The instance's UARTComm as the over-cap offer reaches it: its cap and its stream SET.
        @property
        def _max_transfer_bytes(self) -> int: ...
        async def uart_set_stream(self, set_id: int, total_size: int, pull: "Callable[[int, memoryview], object]") -> bool: ...

    class _LinkCounts(Protocol):
        # A uart_link instance's own counters (asy_uart_link_driver.UARTLinkDriver), read at shutdown.
        _transfers: int
        _failures: int

    class _ExercisedLink(_LinkCounts, Protocol):
        # The same instance as the over-cap offer reaches it: the role its TOML names and its UARTComm.
        @property
        def _comm(self) -> _OverCapComm: ...
        @property
        def _role(self) -> str: ...

    class _RxCounts(Protocol):
        rx_overruns: int  # the receive path's laps and errors (asy_uart_driver.UART)

    class _Direction(Protocol):
        @property
        def wire_log(self) -> _Clearable: ...

    class _Link(Protocol):
        # The two directions of a UART crossover link, each with its bounded wire log.
        @property
        def a_to_b(self) -> _Direction: ...
        @property
        def b_to_a(self) -> _Direction: ...

if "digital_twin/unixport" not in sys.path:
    sys.path.insert(0, "digital_twin/unixport")  # the fake-free directory: the UDP shim, the NTP config writer and responder

import _flash_stall
import _unix_port_udp_addr_shim
import _wall_clock
import ffi  # type: ignore[import-not-found]  # the Unix port's own module, no stub: --test-kbd-traceback's self-SIGINT
import machine
import network
from _ntp_responder import NtpResponder
from _offline_ntp_config import write_responder_ntp_config
from _twin_common import Injections, StatePaths, saturating_add
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from launch import (  # one implementation of each, in launch.py
    _FAULT_DEVICE_OPS,
    _FRAM_STATE_DEFAULT,
    _MEM_BACKUP_STATE_DEFAULT,
    _SCD30_STATE_DEFAULT,
    _apply_fault,
    _apply_hang,
    _collect_chips,
    _driver_of,
    _parse_wifi_outcome,
    _pop_value,
    _positive_int,
    _shutdown_cleanup,
    _state_path,
    parse_fault_spec,
    parse_hang_spec,
)
from unix_port_poll_prewarm import prewarm_poll_set
from unix_port_unretrieved_report import install

from asy_print_log import PrintLog

_SOURCE = "run_generic_integration.py"
_LINE_PREFIX = "digital_twin/" + _SOURCE
_PRODUCT_DIRS = ("src", "ext", "generated_src")  # the product's module directories, the ones the wall clock is installed in
# the manual run's persistent default (owner, 2026-08-13); automated callers pass their own --config-dir
_CONFIG_DIR_DEFAULT = "digital_twin/config/"
_NTP_PORT = 123  # the port the product's client sends to (RFC 5905 7.2; src/asy_ntp_client.py _NTP_UDP_PORT)
_EXIT_SIMULATED_RESET = 3
_EXIT_SIMULATED_BOOTLOADER = 4
_EXIT_SIMULATED_POWER_LOSS = 5
_watchdog: "machine.WDT | None" = None  # the WDT main() builds and passes to the booted module's main(),
# read by _print_shutdown_line()'s two call sites: the generated module keeps no watchdog global.
_shutdown_printed = False
_uart_counts: "list[tuple[str, _ExercisedLink, _RxCounts]]" = []  # each wired uart_link's counters, for the shutdown line

# The same value and one-time placement the real firmware boot entry uses, so a twin run models
# production's memory-safety configuration and not just its allocation code. --gc-threshold
# overrides it, since Part I.4(e) requires the whole suite to pass at -1 first.
# @tunable gc.threshold_bytes = 32768
_GC_THRESHOLD_DEFAULT = 32768

# The watchdog a device's boot entry arms and passes to main(); this runner stands in for that entry,
# and the twin's in-process tests build theirs from this one value.
# @tunable wdt.timeout_ms = 8000
_WDT_TIMEOUT_MS = 8000

_SHUTDOWN_HANG_STEPS = ("S1", "S2", "S3", "S4", "S5reset", "S5erase", "S6")
# MICROPY_BYTES_PER_GC_BLOCK, 4 x the object word (py/mpconfig.h:251, v1.29.0): the unit of mem_info()'s max free sz.
_GC_BLOCK_BYTES = 4 * struct.calcsize("P")
_TEST_TRAIN_CMD_ID = 0x02  # the exerciser's ECHO (asy_uart_link_driver.py), the one SET its responder takes
_SIGINT = 2  # Linux's signal number (signal(7)): MicroPython has no signal module


if TYPE_CHECKING:

    class RunLimits(NamedTuple):
        # How long the run serves (None: forever), its gc.threshold(), the optional heap sampler period
        # and the optional file whose appearance ends the serving early (_serve_until()).
        duration: float | None
        gc_threshold: int
        mem_sample_interval_ms: int | None
        stop_file: str | None

    class TestFlags(NamedTuple):
        # The test-only instrumentation a run asks for by name; _NO_TEST_FLAGS is every one off.
        hold_closing_slot: bool
        stall_loop_ms: int | None
        conn_status_interval_ms: int | None
        fault_status_interval_ms: int | None
        shutdown_hang: str | None
        flash_stall_max: bool
        uart_over_cap: bool
        hold_system_entry: int | None
        kbd_traceback: bool

    class RunEnvironment(NamedTuple):
        # The product's config directory, whether NTP may go online instead of the local responder, the test flags, and
        # the level the loggers are built at (None: off until the stored DebugLevel applies, as the boot entry passes).
        config_dir: str
        online_ntp: bool
        instrumentation: TestFlags
        debug_level: int | None

else:
    RunLimits = namedtuple("RunLimits", ("duration", "gc_threshold", "mem_sample_interval_ms", "stop_file"))
    TestFlags = namedtuple(
        "TestFlags",
        ("hold_closing_slot", "stall_loop_ms", "conn_status_interval_ms", "fault_status_interval_ms", "shutdown_hang", "flash_stall_max", "uart_over_cap", "hold_system_entry", "kbd_traceback"),
    )
    RunEnvironment = namedtuple("RunEnvironment", ("config_dir", "online_ntp", "instrumentation", "debug_level"))


_NO_TEST_FLAGS = TestFlags(False, None, None, None, None, False, False, None, False)
_DEFAULT_ENVIRONMENT = RunEnvironment(_CONFIG_DIR_DEFAULT, False, _NO_TEST_FLAGS, None)
_PERSISTENT_STATE = StatePaths(_FRAM_STATE_DEFAULT, _SCD30_STATE_DEFAULT, _MEM_BACKUP_STATE_DEFAULT)


# @tunable l2.twin_ready_poll_ms = 20
_READY_POLL_MS = 20


# @tunable l2.twin_wire_log_clear_interval_ms = 5000
_WIRE_LOG_CLEAR_INTERVAL_MS = 5000


# @tunable l2.twin_stop_file_poll_ms = 100
_STOP_FILE_POLL_MS = 100

# @tunable l2.twin_test_stdin_poll_ms = 50
_TEST_STDIN_POLL_MS = 50  # how often a --test-* trigger line on stdin is looked for
_KBD_CAPTURE_SPINS = 1000  # loop passes after the self-SIGINT, each jump a pending-exception check (py/vm.c:575, v1.29.0)

# The WDT keeps its newest 200 feed times: a span it dropped between two folds lasts under one fold period,
# well below the gaps worth flagging, so folding this often loses none of them; the harness judges the gap.
# @tunable l2.twin_feed_gap_fold_ms = 5000
_FEED_GAP_FOLD_MS = 5000


_USAGE = f"""Usage: micropython digital_twin/run_generic_integration.py --module NAME --wiring-plan PATH [options]
  --module NAME            the generated sensortask_<device> module to boot (required)
  --wiring-plan PATH       its wiring-plan JSON (required)
  --host HOST, --port N    where the webserver listens (default: localhost, 8080)
  --device LABEL           the device name the log lines carry (default: the module name)
  --config-dir PATH        the product's config directory (default: {_CONFIG_DIR_DEFAULT})
  --debug-level N          build every logger at level N, until the stored DebugLevel applies (default: off, as on the device)
  --fram-state-path PATH   persist the FRAM image (default: {_FRAM_STATE_DEFAULT}; "" in memory)
  --scd30-state-path PATH  persist the SCD30's NVM (default: {_SCD30_STATE_DEFAULT}; "" in memory)
  --mem-backup-state-path PATH  the watchdog scratch registers' file (default: {_MEM_BACKUP_STATE_DEFAULT}; "" in memory)
  --online-ntp             write no NTP config and start no local responder (default: sync against the responder)
  --seed N, --fault SPEC, --hang SPEC, --wifi-outcome OUTCOME   as digital_twin/launch.py --help
  --duration SECONDS       serve this long (default: forever); --stop-file PATH ends it early once the file exists
  --gc-threshold N         gc.threshold() for the run (default: {_GC_THRESHOLD_DEFAULT})
  --mem-sample-interval-ms N  print a MEM_SAMPLE line every N ms (default: off)
  test-only instrumentation, each off by default:
  --test-hold-closing-slot, --test-stall-loop-ms N, --test-conn-status-interval-ms N,
  --test-fault-status-interval-ms N, --test-shutdown-hang S1|S2|S3|S4|S5reset|S5erase|S6,
  --test-flash-stall-max (every flush at its datasheet maximum), --test-uart-over-cap (one train past each link's cap),
  --test-hold-system-entry ERRNO (SYSTEM's entry with that errno waits for ENTRY_RELEASE),
  --test-kbd-traceback (KBD_TRACEBACK prints the interrupt object's traceback)
  -h, --help               print this and exit 0"""


_TEXT_FLAGS = (
    "--module", "--wiring-plan", "--host", "--device", "--fram-state-path", "--scd30-state-path", "--mem-backup-state-path",
    "--config-dir", "--stop-file",
)


class RunConfig:
    def __init__(
        self,
        module: str,
        wiring_plan_path: str,
        listen: "tuple[str, int]" = ("localhost", 8080),
        device: "str | None" = None,
        state: "StatePaths | None" = None,
        injections: "Injections | None" = None,
        *,
        run: "RunLimits | None" = None,
        environment: "RunEnvironment | None" = None,
    ) -> None:
        self.module = module
        self.wiring_plan_path = wiring_plan_path
        self.host, self.port = listen  # where the webserver listens
        self.device = device if device is not None else module
        self.state = state if state is not None else _PERSISTENT_STATE
        self.injections = injections if injections is not None else Injections(None, [], [], [])
        self.run = run if run is not None else RunLimits(None, _GC_THRESHOLD_DEFAULT, None, None)
        self.environment = environment if environment is not None else _DEFAULT_ENVIRONMENT
        self.config_dir, self.online_ntp, self.instrumentation, self.debug_level = self.environment

    def __eq__(self, other: "object") -> bool:
        if not isinstance(other, RunConfig):
            return NotImplemented
        return self._fields() == other._fields()

    # Value equality without a matching hash: spell out what CPython already does implicitly for
    # any class defining __eq__, so the intent is explicit rather than inherited by accident.
    __hash__ = None  # type: ignore[assignment]  # mypy has no special case for the standard unhashable-by-__eq__ idiom

    def __repr__(self) -> str:
        return (
            f"RunConfig(module={self.module!r}, wiring_plan_path={self.wiring_plan_path!r}, listen=({self.host!r}, {self.port!r}), "
            f"device={self.device!r}, state={self.state!r}, injections={self.injections!r}, "
            f"run={self.run!r}, environment={self.environment!r})"
        )

    def _fields(self) -> "tuple[object, ...]":
        return (self.module, self.wiring_plan_path, self.host, self.port, self.device, self.state, self.injections, self.run, self.environment)


class _FeedGaps:
    # The largest gap between two consecutive feeds of the run's watchdog, folded from its feed times.
    def __init__(self) -> None:
        self.largest_ms = 0
        self._seen = 0
        self._last: _TicksMs | int | None = None

    def fold(self, watchdog: "_Watchdog") -> None:
        new = watchdog.feed_count - self._seen
        if new <= 0:
            return
        times = list(watchdog.feed_times)
        previous = self._last if new <= len(times) else None  # feeds dropped past the bound: that span is no gap
        for stamp in times[-new:]:
            if previous is not None:
                self.largest_ms = max(self.largest_ms, time.ticks_diff(stamp, previous))
            previous = stamp
        self._last = previous
        self._seen = watchdog.feed_count


_feed_gaps = _FeedGaps()


def _debug_level(text: str) -> int:
    # --debug-level's value, refused unless the product's own validator takes it (PrintLog.set_level()).
    try:
        level = int(text)
    except ValueError as e:
        raise ValueError(f"--debug-level {text!r} is not an integer") from e
    if not PrintLog().set_level(level):
        raise ValueError(f"--debug-level {level} is no level the product's loggers take")
    return level


def _ensure_dir(path: str) -> None:
    try:
        os.mkdir(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise OSError(e.errno, f"cannot create config dir {path!r}") from e


def _exit_code(error: "machine.SimulatedRebootError") -> int:
    return _EXIT_SIMULATED_BOOTLOADER if _reset_kind(error) == "bootloader" else _EXIT_SIMULATED_RESET


async def _feed_gap_folder(watchdog: "machine.WDT") -> None:
    while True:
        await asyncio.sleep_ms(_FEED_GAP_FOLD_MS)
        _feed_gaps.fold(watchdog)


def _link_directions(module_file: str, link: "machine.UARTLink") -> "dict[str, object]":
    # uart_link:silent's targets: each instance's outgoing direction by its instance key.
    directions: dict[str, object] = {}
    for key, bus_name in _uart_links(module_file):
        bus = machine.peripheral(bus_name)
        if isinstance(bus, machine.UART):
            directions[key] = link.direction_from(bus)
    return directions


async def _mem_sampler(interval_ms: int) -> None:
    # Optional (--mem-sample-interval-ms): gc.mem_free() lives in this heap with no REST route, so these lines feed the CI
    # suite's Run 11 memory-trend check (_run_11_soak()); its collect is the one twin exception the gc site checker allows
    # (scripts/_check_gc_collect_sites.py) - README.md has the reasoning and measurement.
    while True:
        await asyncio.sleep_ms(interval_ms)
        gc.collect()
        print(f"MEM_SAMPLE {time.time():.3f} {gc.mem_free()}")


def _parse_test_flag(arg: str, remaining: "list[str]", flags: "TestFlags") -> "TestFlags | None":
    # `flags` with one --test-* flag set; None for an argument that is no test flag.
    hold, stall, conn, fault, hang, stall_max, over_cap, entry, kbd = flags
    if arg == "--test-hold-closing-slot":
        hold = True
    elif arg == "--test-stall-loop-ms":
        stall = _positive_int(arg, "N", _pop_value(remaining, arg))
    elif arg == "--test-conn-status-interval-ms":
        conn = _positive_int(arg, "N", _pop_value(remaining, arg))
    elif arg == "--test-fault-status-interval-ms":
        fault = _positive_int(arg, "N", _pop_value(remaining, arg))
    elif arg == "--test-shutdown-hang":
        hang = _pop_value(remaining, arg)
        if hang not in _SHUTDOWN_HANG_STEPS:
            raise ValueError(f"--test-shutdown-hang {hang!r} not recognized - expected one of {_SHUTDOWN_HANG_STEPS}")
    elif arg == "--test-flash-stall-max":
        stall_max = True
    elif arg == "--test-uart-over-cap":
        over_cap = True
    elif arg == "--test-hold-system-entry":
        entry = _positive_int(arg, "ERRNO", _pop_value(remaining, arg))
    elif arg == "--test-kbd-traceback":
        kbd = True
    else:
        return None
    return TestFlags(hold, stall, conn, fault, hang, stall_max, over_cap, entry, kbd)


def _print_shutdown_line(config: RunConfig) -> None:
    # From main()'s finally and the __main__ handlers (an interrupt while main() is suspended skips that finally, F.6),
    # once per process, after the GC summary whose max free sz it is read with; collected first, as an allocation would.
    global _shutdown_printed
    if _watchdog is not None and not _shutdown_printed:
        _shutdown_printed = True
        gc.collect()
        micropython.mem_info()  # the largest free block's only reader (py/gc.c gc_info(), v1.29.0)
        print(_shutdown_line(config.device, _watchdog, _feed_gaps, _uart_counts))


def _print_watchdog_would_trigger(watchdog: "machine.WDT") -> None:
    # The moment a starved watchdog would reset silicon, as it happens: a host waiting on a hang ends there.
    print(f"WATCHDOG_WOULD_TRIGGER count={watchdog.would_have_triggered_count}")


def _reset_kind(error: "machine.SimulatedRebootError") -> str:
    return "bootloader" if isinstance(error, machine.SimulatedBootloaderEntryError) else "reset"


def _reset_line(device: str, error: "machine.SimulatedRebootError") -> str:
    return (
        f"{_LINE_PREFIX} [{device}] machine reset: kind={_reset_kind(error)} reset_count={machine.reset_count} "
        f"bootloader_count={machine.bootloader_count}"
    )


async def _serve_until(duration_s: float, stop_file: "str | None") -> None:
    # The whole duration, or until stop_file exists: either way serving ends here and the run shuts down
    # on main()'s one clean path, so a caller done early skips the idle tail without a signal.
    if stop_file is None:
        await asyncio.sleep(duration_s)
        return
    for _ in range(-(-int(duration_s * 1000) // _STOP_FILE_POLL_MS)):  # polls, not ticks: never short of the duration
        try:
            os.stat(stop_file)
        except OSError:
            await asyncio.sleep_ms(_STOP_FILE_POLL_MS)
            continue
        print(f"{_LINE_PREFIX}: stop file seen, ending the run")
        return


def _shutdown_line(device: str, watchdog: "_Watchdog", gaps: _FeedGaps, links: "Iterable[tuple[str, _LinkCounts, _RxCounts]]" = ()) -> str:
    gaps.fold(watchdog)
    r0 = ",".join(f"0x{word:08x}" for word in machine.mem_backup(0))
    uarts = "".join(f" uart={key}:transfers={link._transfers},failures={link._failures},overruns={bus.rx_overruns}" for key, link, bus in links)
    return (
        f"{_LINE_PREFIX} [{device}] shutdown: would_have_triggered_count={watchdog.would_have_triggered_count} "
        f"feed_count={watchdog.feed_count} largest_feed_gap_ms={gaps.largest_ms} wdt_timeout_ms={watchdog.timeout} mem_backup: r0={r0} "
        f"public_destinations_refused={_unix_port_udp_addr_shim.public_destinations_refused} "
        f"flash_stall_longest_ms={_flash_stall.longest_ms} gc_block_bytes={_GC_BLOCK_BYTES}{uarts}"
    )


# Test-only instrumentation (owner, 2026-09-30, paraphrase): the runner, never src/ or the image, may rebind a booted
# object from outside or print internal state when a named --test-* flag asks; tests_scripts/test_twin_runner_test_flags.py
# keeps every one off by default and out of the production entry path.


async def _test_arm_shutdown_hang(module: "ModuleType", chips: "dict[str, object]", step: str) -> None:
    # The steps' targets exist once the supervisor has started every task (start_tasks()); armed earlier, a step finds
    # no task or config store, or holds a lock setup needs. Owns the runner tasks the step started: its cancel ends them.
    sysfunct = module.sysfunct
    while not sysfunct._tasks or any(task is None for task in sysfunct._tasks):
        await asyncio.sleep_ms(_READY_POLL_MS)
    started = _test_shutdown_hang(module, chips, step)
    try:
        await asyncio.Event().wait()
    finally:
        for task in started:
            task.cancel()


async def _test_conn_line(module: "ModuleType") -> str:
    # The webserver's open-connection gauge and its listen backlog, the two numbers a slot scenario reads.
    service = module.webserver
    return f"CONN_SLOTS open={await service._open_conns.get_value()} backlog={service._backlog}"


async def _test_conn_status(module: "ModuleType", interval_ms: int) -> None:
    while True:
        print(await _test_conn_line(module))
        await asyncio.sleep_ms(interval_ms)


def _test_fault_line(chips: "dict[str, object]") -> str:
    # Every queued chip fault by instance and op, so the host learns a fault was consumed before it reads on.
    pending: list[str] = []
    for key in sorted(chips):
        driver = _driver_of(key)
        if driver is None or driver == "uart_link":
            continue  # a link direction carries no fault queue
        chip: _Chip = cast("_Chip", chips[key])
        pending.extend(f"{key}:{op}={chip.fault.pending(op)}" for op in _FAULT_DEVICE_OPS[driver] if chip.fault.pending(op))
    return "FAULT_PENDING " + (" ".join(pending) or "-")


async def _test_fault_status(chips: "dict[str, object]", interval_ms: int) -> None:
    while True:
        print(_test_fault_line(chips))
        await asyncio.sleep_ms(interval_ms)


def _test_flash_stall_max() -> None:
    _flash_stall.use_max = True  # every flush from here on stalls the loop for its datasheet maximum


async def _test_hang_forever(*_args: object) -> None:
    await asyncio.Event().wait()


async def _test_hold(lock: "asyncio.Lock") -> None:
    async with lock:
        await asyncio.Event().wait()


def _test_hold_closing_slot(module: "ModuleType") -> "Callable[[], None]":
    # WebserverService._close_writer() is what frees a connection slot when it returns: rebound so each close, after the
    # client has its FIN, holds its slot until a SLOT_RELEASE line arrives; the returned callback releases every one.
    service, gate = module.webserver, asyncio.Event()
    real_close_writer = service._close_writer

    async def close_then_hold(writer: object) -> None:
        await real_close_writer(writer)
        if not gate.is_set():
            print("SLOT_HELD")
            await gate.wait()

    def release() -> None:
        gate.set()
        print("SLOT_RELEASED")

    service._close_writer = close_then_hold
    return release


def _test_hold_system_entry(module: "ModuleType", errno_held: int, say: "Callable[[str], None]" = print) -> "Callable[[], None]":
    # SystemService's logger writes its entry with errno_held only after ENTRY_RELEASE: ENTRY_HELD marks the call's start,
    # so the host acts inside that write (the supervisor's escalation entry); the returned callback releases it.
    logger, gate = module.sysfunct.pr, asyncio.Event()
    real_err_s = logger.err_s

    async def held(*args: object, **kwargs: object) -> None:
        if kwargs.get("errno") == errno_held and not gate.is_set():
            say("ENTRY_HELD")
            await gate.wait()
        await real_err_s(*args, **kwargs)

    def release() -> None:
        gate.set()
        say("ENTRY_RELEASED")

    logger.err_s = held
    return release


def _test_kbd_traceback(say: "Callable[[str], None]" = print, out: "IOBase_mp | None" = None) -> "Callable[[], None]":
    # Every SIGINT raises the interpreter's one KeyboardInterrupt object (py/scheduler.c:48-52, v1.29.0): caught once here
    # through a SIGINT to this process, so KBD_TRACEBACK prints where the newest one was raised and how far it got.
    libc = ffi.open("libc.so.6")
    caught: list[BaseException] = []
    try:
        libc.func("i", "kill", "ii")(libc.func("i", "getpid", "")(), _SIGINT)
        for _ in range(_KBD_CAPTURE_SPINS):  # the VM raises a pending interrupt at its next check
            pass
    except KeyboardInterrupt as e:
        caught.append(e)
    say(f"KBD_CAPTURED {bool(caught)}")

    def show() -> None:
        say("KBD_TRACEBACK")
        for interrupt in caught:
            if out is None:
                sys.print_exception(interrupt)  # stdout, the log the host reads
            else:
                sys.print_exception(interrupt, out)

    return show


def _test_never_pulled(_chunk: int, _buf: "memoryview") -> int:
    return 0  # the over-cap train is refused before its first frame, so nothing is ever pulled


def _test_report_then_hang(line: str, say: "Callable[[str], None]" = print) -> "Callable[[object, int], Coroutine[object, object, None]]":
    # A rebound report that says `line` the first time it is entered, then never returns: the host's wait ends there.
    entered = False

    async def report(_task: object, _n: int) -> None:
        nonlocal entered
        if not entered:
            entered = True
            say(line)
        await asyncio.Event().wait()

    return report


def _test_shutdown_hang(module: "ModuleType", chips: "dict[str, object]", step: str) -> "list[asyncio.Task[None]]":
    # Each step rebinds, from outside, the one product object that step of the controlled shutdown waits on, so the host
    # proves the watchdog ends a hung step; returns the runner tasks it started. HANG <step> once armed.
    sysfunct, loop, started = module.sysfunct, asyncio.get_event_loop(), []
    if step == "S1":
        # the supervisor's dead-task report never returns and one supervised task ends: the pass never parks
        sysfunct._log_dead_task = _test_report_then_hang(f"HUNG {step}")
        next(task for task in sysfunct._tasks if task is not None).cancel()
    elif step == "S2":
        sysfunct._config_stores[0].flush_pending = _test_hang_forever  # the store step's flush never returns
    elif step == "S3":
        started.append(loop.create_task(_test_hold(module.fram._chunks[0]._op_lock)))  # the storage quiesce waits on it
    elif step == "S4":
        # a supervised task that swallows its cancel, which the task step awaits; not a runner task (it never ends)
        sysfunct._tasks.append(loop.create_task(_test_swallow_cancel()))
    elif step == "S5reset":
        started.append(loop.create_task(_test_hold(sysfunct._config_stores[0]._config_lock)))  # the reset's store lock
    elif step == "S5erase":
        _test_stall_erase_pass_two(module, cast("_KnobChip", chips["fram"]))
    elif step == "S6":
        sysfunct._reset_timer = _TestInertTimer()  # the reset one-shot never fires: only the watchdog resets
    print(f"HANG {step}")
    return started


def _test_stall_erase_pass_two(module: "ModuleType", chip: "_KnobChip") -> None:
    # Pass 2 of the FRAM erase writes unit by unit after one get_size() read: armed at that read, the chip drops the
    # first unit's WREN and the driver's report of the refused write never returns, so neither boot nor pass 1 meets it.
    manager = module.fram
    real_erase, real_size = manager.erase_chip, manager.fram.get_size

    async def size_then_arm() -> int:
        size: int = await real_size()
        chip.drop_next_wren = 1
        manager.fram.report_set_values = _test_hang_forever
        return size

    async def erase(step_done: "Callable[[], None]") -> bool:
        manager.fram.get_size = size_then_arm
        done: bool = await real_erase(step_done)
        return done

    manager.erase_chip = erase


def _test_stall_loop(stall_ms: int) -> "Callable[[], None]":
    def stall() -> None:
        time.sleep_ms(stall_ms)  # no await: the whole loop stops, as a long synchronous call on silicon stops it
        print("STALL")

    return stall


def _test_start(flags: "TestFlags", module: "ModuleType", chips: "dict[str, object]", links: "list[tuple[str, _ExercisedLink, _RxCounts]]") -> "list[asyncio.Task[None]]":
    # Each named flag's instrumentation, and only under its own flag; the runner tasks it started.
    loop, tasks, triggers = asyncio.get_event_loop(), [], {}
    if flags.hold_closing_slot:
        triggers["SLOT_RELEASE"] = _test_hold_closing_slot(module)
    if flags.stall_loop_ms:
        triggers["STALL_TRIGGER"] = _test_stall_loop(flags.stall_loop_ms)
    if flags.hold_system_entry:
        triggers["ENTRY_RELEASE"] = _test_hold_system_entry(module, flags.hold_system_entry)
    if flags.kbd_traceback:
        triggers["KBD_TRACEBACK"] = _test_kbd_traceback()
    if flags.hold_closing_slot or flags.stall_loop_ms or flags.hold_system_entry or flags.kbd_traceback:
        tasks.append(loop.create_task(_test_stdin_lines(triggers)))
    if flags.conn_status_interval_ms:
        tasks.append(loop.create_task(_test_conn_status(module, flags.conn_status_interval_ms)))
    if flags.fault_status_interval_ms:
        tasks.append(loop.create_task(_test_fault_status(chips, flags.fault_status_interval_ms)))
    if flags.shutdown_hang:
        tasks.append(loop.create_task(_test_arm_shutdown_hang(module, chips, flags.shutdown_hang)))
    if flags.flash_stall_max:
        _test_flash_stall_max()
    if flags.uart_over_cap:
        tasks.append(loop.create_task(_test_uart_over_cap(links)))
    return tasks


async def _test_stdin_lines(triggers: "dict[str, Callable[[], None]]") -> None:
    # Each line on stdin names a trigger; an unknown one is printed, never ignored. Ends at end of file.
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    while True:
        if any(event & select.POLLIN for _obj, event in poller.ipoll(0)):
            line = sys.stdin.readline()
            if not line:
                return
            name = line.strip()
            if name in triggers:
                triggers[name]()
            else:
                print(f"UNKNOWN_TRIGGER {name}")
        await asyncio.sleep_ms(_TEST_STDIN_POLL_MS)


async def _test_swallow_cancel() -> None:
    while True:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            continue


async def _test_uart_over_cap(links: "list[tuple[str, _ExercisedLink, _RxCounts]]", say: "Callable[[str], None]" = print) -> None:
    # One train one byte past each initiating link's cap, right after its next exercise transfer, so none is in flight:
    # the protocol refuses it before its first frame and logs it (J.8); UART_OVER_CAP names the outcome per link.
    for key, link, _bus in links:
        if link._role != "initiator":  # the role a uart_link instance's TOML names
            continue
        seen = link._transfers + link._failures
        while link._transfers + link._failures == seen:
            await asyncio.sleep_ms(_READY_POLL_MS)
        sent = await link._comm.uart_set_stream(_TEST_TRAIN_CMD_ID, link._comm._max_transfer_bytes + 1, _test_never_pulled)
        say(f"UART_OVER_CAP {key} {'sent' if sent else 'refused'}")


class _TestInertTimer:
    # A Timer whose callback never fires: init() records the arm and schedules nothing.
    def __init__(self) -> None:
        self.armed = 0

    def deinit(self) -> None:
        pass

    def init(self, **_settings: object) -> None:
        self.armed = saturating_add(self.armed, 1)


def _uart_links(module_file: str) -> "list[tuple[str, str]]":
    # Each wired uart_link's instance key and bus name: the plan names the pair's buses by role only, so an instance's
    # bus is the first argument of its generated construction line.
    found: list[tuple[str, str]] = []
    with open(module_file) as f:
        for line in f:
            key, built, rest = line.strip().partition(" = UARTLinkDriver(")
            if built:
                found.append((key, rest.split(",", 1)[0]))
    return found


async def _wait_until_built(module: "_Booted", timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        # webserver is the last global build_system() assigns before its setup batch, so faults applied after it
        # reach setup (the CI suite counts on that, scripts/_digital_twin_ci_suite.py)
        while getattr(module, "webserver", None) is None:
            await asyncio.sleep_ms(_READY_POLL_MS)

    await asyncio.wait_for(poll(), timeout_s)


async def _wire_log_clearer(link: "_Link") -> None:
    # Each direction's wire_log keeps the newest bytes in a bounded log nothing in this process reads; cleared on a
    # timer, its bytes never accumulate over a long run - unbounded, they made Run 11's trend check fail for `dev`.
    while True:
        await asyncio.sleep_ms(_WIRE_LOG_CLEAR_INTERVAL_MS)
        link.a_to_b.wire_log.clear()  # the bounded log object stays: the link keeps appending to it
        link.b_to_a.wire_log.clear()


def _wire_uart_crossover(module: "_Booted", plan: "_Plan") -> "machine.UARTLink | None":
    # Wires the bench's permanent crossover jumper between the two generated UART buses once the module has built them;
    # the bounded pollers replace the product's public poller from outside, since a real select.poll() over the twin's
    # UART never reports readiness on CI runners (CLAUDE.md known hang cause).
    uart_plan = plan.get("uart")
    if uart_plan is None:
        return None
    initiator = machine.peripheral(uart_plan["initiator_bus"])
    responder = machine.peripheral(uart_plan["responder_bus"])
    if initiator is None or responder is None:
        raise RuntimeError("the plan names a UART pair the booted module never constructed")
    if not isinstance(initiator, machine.UART) or not isinstance(responder, machine.UART):
        raise TypeError("the plan's UART pair names a bus that is no UART")
    link, poll_a, poll_b = machine.attach_crossover_jumper(initiator, responder)
    getattr(module, uart_plan["initiator_bus"]).poller = poll_a
    getattr(module, uart_plan["responder_bus"]).poller = poll_b
    return link


def load_module(name: str) -> "ModuleType":
    # A generated device module by name, at the one named load site (SPECIFICATION.md F.1): this runner's boot, and a
    # twin test that picks its device from the generated plans.
    return __import__(name)


def product_modules() -> "list[object]":
    # The loaded src/ and generated modules; the twin's own and this runner's keep the host's time.
    found: list[object] = []
    for module in sys.modules.values():
        path = getattr(module, "__file__", None) or ""
        if "/" in path and path.rsplit("/", 2)[-2] in _PRODUCT_DIRS:
            found.append(module)
    return found


async def main(config: RunConfig) -> None:
    global _watchdog, _shutdown_printed, _feed_gaps, _uart_counts
    install()  # before the firmware: start_tasks() keeps it, so every task death prints (Part I.4(e))
    prewarm_poll_set()  # before anything registers a poll object (unix_port_poll_prewarm.py)
    patch_asy_udp_socket_for_unix_port()  # then before any UDPSocket exists (_unix_port_udp_addr_shim.py)
    injections, run = config.injections, config.run
    machine.configure_fram_state_path(config.state.fram)
    machine.configure_scd30_state_path(config.state.scd30)
    machine.configure_mem_backup_state_path(config.state.mem_backup)
    with open(config.wiring_plan_path) as f:
        plan: _Plan = json.load(f)
    machine.configure_wiring(plan)
    if injections.seed is not None:
        random.seed(injections.seed)
    _ensure_dir(config.config_dir)
    responder = None
    if not config.online_ntp:
        responder = NtpResponder(_NTP_PORT)
        if not responder.holding:  # one responder per port: until the holder frees it, that one answers this client
            print(f"{_LINE_PREFIX}: UDP port {_NTP_PORT} is held by another NTP responder - this run's takes it once freed")
        write_responder_ntp_config(config.config_dir)

    print(
        f"{_LINE_PREFIX} starting - device={config.device!r} module={config.module!r} host={config.host!r} "
        f"port={config.port!r} state={config.state!r} config_dir={config.config_dir!r} online_ntp={config.online_ntp!r} "
        f"debug_level={config.debug_level!r} injections={injections!r} run={run!r}",
    )

    booted = load_module(config.module)
    module = cast("_Booted", booted)
    # rp2's RTC is the wall clock: an NTP set must move the product's time.time() here too
    _wall_clock.install(product_modules())
    _flash_stall.install(sys.modules["asy_config_manager"])  # rp2 writes its flash with interrupts off: each flush stalls
    watchdog = machine.WDT(timeout=_WDT_TIMEOUT_MS, on_would_trigger=_print_watchdog_would_trigger)
    _watchdog, _shutdown_printed, _feed_gaps, _uart_counts = watchdog, False, _FeedGaps(), []
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(module.main(watchdog=watchdog, cfg_path=config.config_dir, debug=config.debug_level, web_host=config.host, web_port=config.port))
    tasks = [loop.create_task(_feed_gap_folder(watchdog))]
    if responder is not None:
        tasks.append(loop.create_task(responder.serve()))
    if run.mem_sample_interval_ms is not None:
        tasks.append(loop.create_task(_mem_sampler(run.mem_sample_interval_ms)))
    try:
        await _wait_until_built(module)
        module_file = module.__file__
        if module_file is None:
            raise RuntimeError(f"{config.module} has no __file__ to read its construction lines from")
        _uart_counts = [(key, getattr(booted, key), getattr(booted, bus)) for key, bus in _uart_links(module_file)]
        link = _wire_uart_crossover(module, plan)
        chips = _collect_chips(plan)
        if link is not None:
            tasks.append(loop.create_task(_wire_log_clearer(link)))
            chips.update(_link_directions(module_file, link))
        wlan = network.WLAN(network.STA_IF)  # the product's own station object: one per interface, as on rp2
        for fault in injections.faults:
            _apply_fault(fault, chips, wlan, source=_SOURCE)
        for hang in injections.hangs:
            _apply_hang(hang, chips, source=_SOURCE)
        if injections.wifi_outcomes:
            wlan.script_connect_outcomes(injections.wifi_outcomes)
        tasks.extend(_test_start(config.instrumentation, booted, chips, _uart_counts))

        if run.duration is None:
            print(f"Serving forever at http://{config.host}:{config.port}/ - Ctrl+C to stop")
            while True:
                await asyncio.sleep(3600)
        elif run.duration > 0:
            await _serve_until(run.duration, run.stop_file)
    finally:
        _print_shutdown_line(config)
        for task in tasks:
            task.cancel()
        main_task.cancel()
        try:
            await main_task
        except asyncio.CancelledError:
            # The cancel's own end. An interrupt landing here (a per-file timeout's SIGINT) ends the run instead, and
            # __main__ flushes the state; a reset leaves the loop before it could reach here (a BaseException).
            pass
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        if responder is not None:
            responder.close()
        _shutdown_cleanup()


def parse_args(argv: "list[str]") -> RunConfig:
    if "-h" in argv or "--help" in argv:
        print(_USAGE)
        sys.exit(0)
    remaining = list(argv)
    text = {
        "--host": "localhost", "--fram-state-path": _FRAM_STATE_DEFAULT, "--scd30-state-path": _SCD30_STATE_DEFAULT,
        "--mem-backup-state-path": _MEM_BACKUP_STATE_DEFAULT, "--config-dir": _CONFIG_DIR_DEFAULT, "--stop-file": "",
    }
    port = 8080
    online_ntp = False
    seed: int | None = None
    faults: list[FaultSpec] = []
    hangs: list[HangSpec] = []
    wifi_outcomes: list[int] = []
    duration: float | None = None
    gc_threshold = _GC_THRESHOLD_DEFAULT
    mem_sample_interval_ms: int | None = None
    debug_level: int | None = None
    flags = _NO_TEST_FLAGS

    while remaining:
        arg = remaining.pop(0)
        if arg in _TEXT_FLAGS:
            text[arg] = _pop_value(remaining, arg)
        elif arg == "--port":
            port = int(_pop_value(remaining, arg))
        elif arg == "--online-ntp":
            online_ntp = True
        elif arg == "--seed":
            seed = int(_pop_value(remaining, arg))
        elif arg == "--fault":
            faults.append(parse_fault_spec(_pop_value(remaining, arg)))
        elif arg == "--hang":
            hangs.append(parse_hang_spec(_pop_value(remaining, arg)))
        elif arg == "--wifi-outcome":
            wifi_outcomes.append(_parse_wifi_outcome(_pop_value(remaining, arg)))
        elif arg == "--duration":
            duration = float(_pop_value(remaining, arg))
        elif arg == "--gc-threshold":
            gc_threshold = int(_pop_value(remaining, arg))
        elif arg == "--mem-sample-interval-ms":
            mem_sample_interval_ms = int(_pop_value(remaining, arg))
        elif arg == "--debug-level":
            debug_level = _debug_level(_pop_value(remaining, arg))
        else:
            parsed = _parse_test_flag(arg, remaining, flags)
            if parsed is None:
                raise ValueError(f"unrecognized argument: {arg!r}")
            flags = parsed

    module = text.get("--module")
    if module is None:
        raise ValueError("--module is required (the sensortask_<device> module to import and boot)")
    wiring_plan_path = text.get("--wiring-plan")
    if wiring_plan_path is None:
        raise ValueError("--wiring-plan is required (a JSON file in buildgen.twin_wiring.compute_twin_wiring()'s own shape)")

    return RunConfig(
        module,
        wiring_plan_path,
        listen=(text["--host"], port),
        device=text.get("--device"),
        state=StatePaths(_state_path(text["--fram-state-path"]), _state_path(text["--scd30-state-path"]), _state_path(text["--mem-backup-state-path"])),
        injections=Injections(seed, faults, hangs, wifi_outcomes),
        run=RunLimits(duration, gc_threshold, mem_sample_interval_ms, text["--stop-file"] or None),  # "" as the state paths
        environment=RunEnvironment(text["--config-dir"], online_ntp, flags, debug_level),
    )


if __name__ == "__main__":
    _config = parse_args(sys.argv[1:])
    # Immediately before asyncio.run(), where the real firmware boot entry also sets it, so an
    # ordinary twin run models production's configuration. --gc-threshold overrides it: the CI
    # suite runs the WHOLE suite at -1 and then at 32768, in that order (Part I.4(e)).
    gc.threshold(_config.run.gc_threshold)
    try:
        asyncio.run(main(_config))
    except KeyboardInterrupt:
        # Reached when the interrupt lands while main() is suspended or in its shutdown drain: the rest of its finally
        # never runs, so this is the cleanup (SPECIFICATION.md F.1, asyncio.run() catches only CancelledError and Exception).
        _shutdown_cleanup()
        _print_shutdown_line(_config)
        print(f"{_LINE_PREFIX}: interrupted")
    except machine.SimulatedRebootError as e:
        # A reset leaves the loop (a BaseException): the regions a reset keeps go to their file, then exit 3 or 4.
        _shutdown_cleanup()
        machine.flush_mem_backup()
        print(_reset_line(_config.device, e))
        _print_shutdown_line(_config)
        sys.exit(_exit_code(e))
    except machine.SimulatedPowerLoss:
        _shutdown_cleanup()  # no mem-backup flush: a power loss clears those registers
        print(f"{_LINE_PREFIX} [{_config.device}] power lost")
        sys.exit(_EXIT_SIMULATED_POWER_LOSS)
