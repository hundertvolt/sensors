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
import socket
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
    from typing import NamedTuple, Protocol, TypedDict, TypeVar

    from _mpy_shed.time_mp import _TicksMs

    from asy_print_log import PrintLogHistory

    T = TypeVar("T")

    class _AttachmentKeys(TypedDict):
        # One chip of a plan bus, in buildgen.twin_wiring.compute_twin_wiring()'s shape.
        driver: str
        name_ext: str
        address: int

    class _Attachment(_AttachmentKeys, total=False):
        irq_pin: int  # scd30 and isl29125 only

    class _SpiAttachment(TypedDict):
        driver: str
        name_ext: str
        max_size: int

    class _UartPair(TypedDict):
        initiator_bus: str
        responder_bus: str

    class _Plan(TypedDict):
        device: str
        buses: dict[str, list[_Attachment]]
        spi: dict[str, _SpiAttachment]
        uart: _UartPair | None
        pins: dict[str, dict[str, int]]

    class _Injector(Protocol):
        # The FaultInjector calls the fault plumbing makes.
        def inject_fault(self, op: str, exc_type: type[BaseException], *args: object, times: int = 1, match: int | None = None) -> None: ...

        def inject_hang(self, op: str, seconds: float, times: int = 1) -> None: ...

        def pending(self, op: str) -> int: ...

    class _Chip(Protocol):
        # What the fault plumbing reads off every wired chip fake.
        @property
        def fault(self) -> _Injector: ...

    class _KnobChip(Protocol):
        # The mode setters and counted knobs a fault that is no queued exception sets.
        silent: bool
        drop_next_wren: int

        def configure_fault(self, op: str) -> None: ...

    FaultSpec = tuple[str, str, int, int | None, str]
    HangSpec = tuple[str, str, float, int]

    class _Build(Protocol):
        def __call__(self, *, watchdog: "machine.WDT", cfg_path: str, debug: int | None, web_host: str, web_port: int) -> "Coroutine[object, object, None]": ...

    class _Booted(Protocol):
        # The generated module's globals and entry this runner reads; the module is chosen at run time (--module).
        @property
        def __file__(self) -> str | None: ...
        def main(self, *, watchdog: "machine.WDT", cfg_path: str, debug: int | None, web_host: str, web_port: int) -> "Coroutine[object, object, None]": ...

        build_system: "_Build"  # rebound by the runner's boot hold (_boot_held())

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

    class _LoggerOwner(Protocol):
        # Any booted object that names its loggers (SPECIFICATION.md Part C.14's fan-in shape).
        def get_loggers(self) -> "list[PrintLogHistory]": ...

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

    class _FramCounts(Protocol):
        # The twin FRAM chip's payload-write counters (digital_twin/_fram_chip.py), read at shutdown.
        write_count: int
        writes_at: dict[int, int]
        writes_at_dropped: int

    class _Direction(Protocol):
        @property
        def wire_log(self) -> _Clearable: ...

    class _Sock(Protocol):
        # A socket from accept() as the Unix port gives it (ports/unix/modsocket.c:192, :384, v1.29.0); the rp2 stub has no fileno().
        def close(self) -> None: ...
        def fileno(self) -> int: ...
        def setsockopt(self, level: int, optname: int, value: int) -> None: ...

    class _Accepted(Protocol):
        s: _Sock  # the asyncio Stream's own socket (extmod/asyncio/stream.py:9, v1.29.0)

    class _Link(Protocol):
        # The two directions of a UART crossover link, each with its bounded wire log.
        @property
        def a_to_b(self) -> _Direction: ...
        @property
        def b_to_a(self) -> _Direction: ...

if "digital_twin/unixport" not in sys.path:
    sys.path.insert(0, "digital_twin/unixport")  # the fake-free directory: the UDP shim, the NTP config writer and responder

import _driven_clock
import _flash_stall
import _unix_port_udp_addr_shim
import _wall_clock
import ffi  # type: ignore[import-not-found]  # the Unix port's own module, no stub: the send buffer's read-back
import machine
import network
from _ntp_responder import NtpResponder
from _offline_ntp_config import write_responder_ntp_config
from _twin_common import Injections, StatePaths, pop_value, saturating_add
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set
from unix_port_unretrieved_report import install

from asy_print_log import PrintLog

_SOURCE = "run_generic_integration.py"
_LINE_PREFIX = "digital_twin/" + _SOURCE

# The --fault/--hang/--wifi-outcome vocabulary and its plumbing: a chip fake's FaultInjector, a WLAN's raise_on.
_FAULT_DEVICE_OPS = {
    "scd30": ("writeto", "readfrom_into"),
    "sgp40": ("writeto", "readfrom_into", "general_call"),
    "bmp3xx": ("writeto", "readfrom_mem", "writeto_mem"),
    "isl29125": ("writeto", "readfrom_mem", "writeto_mem", "int_stuck_high"),
    "fram": ("readinto", "wren", "silent"),
    "uart_link": ("silent",),
    "wlan": ("active", "connect", "disconnect", "deinit", "isconnected", "status", "config", "ifconfig"),
}
# Modes, not counted faults: they stay set for the run, so TIMES and MATCH are refused.
_PERSISTENT_FAULT_OPS = (("isl29125", "int_stuck_high"), ("fram", "silent"), ("uart_link", "silent"))
_STACK_KIND = "stack"
_OSERROR_KIND = "oserror"
# twin-only test knob: no rp2 bus call raises this; it carries a C-stack overflow's exception
# (py/runtime.c:1786) into one read so the reboot path can be proven at L2
_STACK_EXHAUSTED_MESSAGE = "maximum recursion depth exceeded"

_HANG_DEVICE_OPS = {
    # Bus devices only: a WLAN fault is a synchronous raise_on[] check with no blocking HAL call underneath for
    # time.sleep() to stand in for, so wlan is in --fault's vocabulary and not in this one.
    "sgp40": ("writeto", "readfrom_into"),
    "scd30": ("writeto", "readfrom_into"),
    "bmp3xx": ("writeto", "readfrom_mem", "writeto_mem"),
    "isl29125": ("writeto", "readfrom_mem", "writeto_mem"),
    "fram": ("write", "readinto"),
}

_WIFI_OUTCOME_MAP = {
    "success": network.STAT_GOT_IP,
    "no_ap": network.STAT_NO_AP_FOUND,
    "wrong_password": network.STAT_WRONG_PASSWORD,
    "connect_fail": network.STAT_CONNECT_FAIL,
}

# The manual run's persistent defaults (owner, 2026-08-13); "" keeps a chip in memory only.
_FRAM_STATE_DEFAULT = "digital_twin/fram_state.json"
_SCD30_STATE_DEFAULT = "digital_twin/scd30_state.json"
_MEM_BACKUP_STATE_DEFAULT = "digital_twin/mem_backup_state.json"

_PRODUCT_DIRS = ("src", "ext", "generated_src", "portable_src")  # the product's module directories, the ones the wall clock is installed in
# the manual run's persistent default (owner, 2026-08-13); automated callers pass their own --config-dir
_CONFIG_DIR_DEFAULT = "digital_twin/config/"
_NTP_PORT = 123  # the port the product's client sends to (RFC 5905 7.2; src/asy_ntp_client.py _NTP_UDP_PORT)
_EXIT_SIMULATED_RESET = 3
_EXIT_SIMULATED_BOOTLOADER = 4
_EXIT_SIMULATED_POWER_LOSS = 5
_watchdog: "machine.WDT | None" = None  # the WDT main() builds and passes to the booted module's main(),
# read by _print_shutdown_line()'s two call sites: the generated module keeps no watchdog global.
_module: "ModuleType | None" = None  # the booted module, whose FRAM-backed loggers the shutdown line attributes writes to
_shutdown_printed = False
_stop_file: "str | None" = None  # the run's stop file, which a frozen write (_test_freeze()) polls in the loop's place
_boot_phase_device = ""  # the device of the latest in-process main(), which each boot-phase line names
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

_SHUTDOWN_HANG_STEPS = ("S1", "S2", "S4", "S5reset", "S5erase", "S6")
_DROP_TIMER_SITES = ("reset",)  # the product one-shot --test-drop-timer-fire reaches: sysfunct's reset timer
# MICROPY_BYTES_PER_GC_BLOCK, 4 x the object word (py/mpconfig.h:251, v1.29.0): the unit of mem_info()'s max free sz.
_GC_BLOCK_BYTES = 4 * struct.calcsize("P")
_TEST_TRAIN_CMD_ID = 0x02  # the exerciser's ECHO (asy_uart_link_driver.py), the one SET its responder takes
_UART_CLOCK_MODULES = ("asy_uart_driver", "asy_uart_comm", "asy_uart_link_driver")  # the link's clock
_WATCHDOG_FAULT_KINDS = ("supervisor-raise", "main-exit", "block")
_HOLD_CUT = "cut"  # --test-hold-system-entry's unreleased mode: the entry's write frozen inside its first block
_SO_SNDBUF = 7  # Linux's (include/uapi/asm-generic/socket.h): the Unix port's socket module exports none (modsocket.c:722-727, v1.29.0)
_FRAM_STATUS_BUSY = 0x02  # asy_fram_manager.py's _STATUS_BUSY, a const() and so no attribute: a block mid-write
_WDT_FAULT_BLOCK_MS = _WDT_TIMEOUT_MS + 1000  # past the armed timeout: the starved countdown fires once the loop resumes


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
        hold_system_entry: tuple[int, bool] | None  # (errno, cut)
        loop_lag_ms: int | None
        drop_timer_fire: str | None
        watchdog_fault: str | None
        defer_faults: bool
        pin_send_buffer: bool
        uart_driven_clock: bool

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
        ("hold_closing_slot", "stall_loop_ms", "conn_status_interval_ms", "fault_status_interval_ms", "shutdown_hang", "flash_stall_max", "uart_over_cap", "hold_system_entry", "loop_lag_ms", "drop_timer_fire", "watchdog_fault", "defer_faults", "pin_send_buffer", "uart_driven_clock"),
    )
    RunEnvironment = namedtuple("RunEnvironment", ("config_dir", "online_ntp", "instrumentation", "debug_level"))


_NO_TEST_FLAGS = TestFlags(False, None, None, None, None, False, False, None, None, None, None, False, False, False)
_DEFAULT_ENVIRONMENT = RunEnvironment(_CONFIG_DIR_DEFAULT, False, _NO_TEST_FLAGS, None)
_PERSISTENT_STATE = StatePaths(_FRAM_STATE_DEFAULT, _SCD30_STATE_DEFAULT, _MEM_BACKUP_STATE_DEFAULT)


_READY_POLL_MS = 20
_FREEZE_STEP_MS = 50  # a frozen write's sleep step: how often it looks at the WDT's deadline


_WIRE_LOG_CLEAR_INTERVAL_MS = 5000


_STOP_FILE_POLL_MS = 100

_TEST_STDIN_POLL_MS = 50  # how often a --test-* trigger line on stdin is looked for
_LOOP_LAG_REPORT_MS = 5000  # one LOOP_LAG line per window of this length, its figures that window's alone
_LOOP_LAG_BUCKETS = 64  # 1 ms histogram bins, the last one open-ended: a fixed fold, no list grows with the run
_DROP_WINDOW_CALLBACKS = 1_000_000  # more soft callbacks than any one-shot's window can see: the queue stays full to its fire

# The WDT keeps its newest 200 feed times: a span it dropped between two folds lasts under one fold period,
# well below the gaps worth flagging, so folding this often loses none of them; the harness judges the gap.
_FEED_GAP_FOLD_MS = 5000


_USAGE = f"""Usage: micropython digital_twin/run_generic_integration.py --module NAME --wiring-plan PATH [options]
  --module NAME            the generated sensortask_<device> module to boot (required)
  --wiring-plan PATH       its wiring-plan JSON (required)
  --host HOST, --port N    where the webserver listens (default: localhost, 8080)
  --device LABEL           the device name the log lines carry (default: the module name)
  --config-dir PATH/       the product's config directory, ending in "/" (default: {_CONFIG_DIR_DEFAULT})
  --debug-level N          build every logger at level N, until the stored DebugLevel applies (default: off, as on the device)
  --fram-state-path PATH   persist the FRAM image (default: {_FRAM_STATE_DEFAULT}; "" in memory)
  --scd30-state-path PATH  persist the SCD30's NVM (default: {_SCD30_STATE_DEFAULT}; "" in memory)
  --mem-backup-state-path PATH  the watchdog scratch registers' file (default: {_MEM_BACKUP_STATE_DEFAULT}; "" in memory)
  --online-ntp             write no NTP config and start no local responder (default: sync against the responder)
  --seed N                 random seed for the chip fakes (default: none)
  --fault DEVICE:OP[:TIMES[:MATCH]]  inject a fault (repeatable; TIMES default 1, or "stack"; MATCH hex)
  --hang DEVICE:OP:SECONDS[:TIMES]   inject a blocking hang (repeatable; TIMES default 1)
  --wifi-outcome OUTCOME   script a WLAN connect's outcome, in order: success, no_ap or connect_fail (repeatable)
  --duration SECONDS       serve this long (default: forever); --stop-file PATH ends it once the file exists, either way
  --gc-threshold N         gc.threshold() for the run (default: {_GC_THRESHOLD_DEFAULT})
  --mem-sample-interval-ms N  print a MEM_SAMPLE line every N ms (default: off)
  test-only instrumentation, each off by default:
  --test-hold-closing-slot, --test-stall-loop-ms N, --test-conn-status-interval-ms N,
  --test-fault-status-interval-ms N, --test-shutdown-hang S1|S2|S4|S5reset|S5erase|S6,
  --test-flash-stall-max (every flush at its datasheet maximum), --test-uart-over-cap (one train past each link's cap),
  --test-hold-system-entry ERRNO[:cut] (after SYSTEM's entry with that errno its reboot waits for ENTRY_RELEASE; with
        :cut the entry's write freezes inside its first block after the busy mark, never released),
  --test-loop-lag-ms N (a LOOP_LAG line every {_LOOP_LAG_REPORT_MS // 1000} s from a task sleeping N ms at a time, each link's transfers on it),
  --test-drop-timer-fire reset (that one-shot's fire lost as rp2's full scheduler queue loses it),
  --test-watchdog-fault supervisor-raise|main-exit|block (after the supervisor's first feed, one fault that ends the
    feeding; WDT_AT_FAULT <feed_count>)
  --test-defer-faults (every --fault waits for a FAULT_ARM line, then is queued at once; FAULTS_ARMED)
  --test-pin-send-buffer (the send buffer of each socket the server accepts pinned at the kernel's floor, as rp2's lwIP one is small
        and fixed; SNDBUF_PINNED bytes=<n> accepted_bytes=<n>)
  --test-uart-driven-clock (the UART link's modules on one driven clock: no task's compute or turn on the loop spends a
        protocol deadline, a flash hold still does; UART_CLOCK driven modules=<n>, at the end UART_CLOCK released ...)
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


def _apply_fault(fault: "FaultSpec", chips: "dict[str, object]", wlan: "network.WLAN") -> None:
    # A chip fake, or (in the runner) a UART link direction: each fault reaches it through the one seam it has.
    device, op, times, match, kind = fault
    driver = _driver_of(device)
    message = f"{_LINE_PREFIX} --fault {device}:{op}"
    if driver == "wlan":
        wlan.raise_on[op] = (OSError, (errno.EIO, message), times)
        return
    _require_wired(device, chips)
    chip: _Chip = cast("_Chip", chips[device])
    knobs: _KnobChip = cast("_KnobChip", chips[device])
    if (driver, op) == ("isl29125", "int_stuck_high"):
        knobs.configure_fault(f"{driver}:{op}")
    elif op == "silent":
        knobs.silent = True
    elif (driver, op) == ("fram", "wren"):
        knobs.drop_next_wren += times
    elif kind == _STACK_KIND:
        chip.fault.inject_fault(op, RuntimeError, _STACK_EXHAUSTED_MESSAGE)
    else:
        chip.fault.inject_fault(op, OSError, errno.EIO, message, times=times, match=match)


def _apply_hang(hang: "HangSpec", chips: "dict[str, object]") -> None:
    device, op, seconds, times = hang
    _require_wired(device, chips)
    chip: _Chip = cast("_Chip", chips[device])
    chip.fault.inject_hang(op, seconds, times=times)


def _boot_held(loop: "asyncio.AbstractEventLoop", module: "_Booted", watchdog: "machine.WDT", config: "RunConfig") -> "tuple[asyncio.Task[None], tuple[asyncio.Event, asyncio.Event]]":
    # main()'s task, its build_system() returning into a hold _release_after_build() lifts, so the runner's faults reach
    # the setup batch however few suspensions the boot makes before it (scripts/_digital_twin_ci_suite.py counts on that).
    built, released = asyncio.Event(), asyncio.Event()
    real_build = module.build_system

    async def build_then_hold(*, watchdog: "machine.WDT", cfg_path: str, debug: int | None, web_host: str, web_port: int) -> None:
        await real_build(watchdog=watchdog, cfg_path=cfg_path, debug=debug, web_host=web_host, web_port=web_port)
        built.set()
        await released.wait()

    module.build_system = build_then_hold  # the module global main() calls
    task = loop.create_task(module.main(watchdog=watchdog, cfg_path=config.config_dir, debug=config.debug_level, web_host=config.host, web_port=config.port))
    return task, (built, released)


def _collect_chips(plan: "_Plan") -> "dict[str, object]":
    # Every chip the plan wires, keyed by its instance key, found through machine.peripheral(); a bus the
    # booted code never constructed is skipped. The one implementation: the runner imports it.
    chips: dict[str, object] = {}
    for bus_name, attachments in plan["buses"].items():
        bus = machine.peripheral(bus_name)
        if not isinstance(bus, machine.I2C):
            continue
        for attachment in attachments:
            chips[_instance_key(attachment["driver"], attachment["name_ext"])] = bus.devices[attachment["address"]]
    for bus_name, spi_attachment in plan["spi"].items():
        spi = machine.peripheral(bus_name)
        if isinstance(spi, machine.SPI):
            chips[_instance_key(spi_attachment["driver"], spi_attachment["name_ext"])] = spi.device
    return chips


def _debug_level(text: str) -> int:
    # --debug-level's value, refused when the product's own clamp (PrintLog.set_level()) would change it.
    try:
        level = int(text)
    except ValueError as e:
        raise ValueError(f"--debug-level {text!r} is not an integer") from e
    pr = PrintLog()
    pr.set_level(level)
    if pr.level != level:
        raise ValueError(f"--debug-level {level} is no level the product's loggers take")
    return level


def _driver_of(key: str) -> "str | None":
    # A vocabulary key is a driver name or an instance key <driver>_<name_ext>; the longest match wins, so
    # uart_link_init resolves to uart_link.
    found: str | None = None
    for driver in _FAULT_DEVICE_OPS:
        if (key == driver or key.startswith(driver + "_")) and (found is None or len(driver) > len(found)):
            found = driver
    return found


def _ensure_dir(path: str) -> None:
    try:
        os.mkdir(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise OSError(e.errno, f"cannot create config dir {path!r}") from e


def _exit_code(error: "machine.SimulatedRebootError") -> int:
    return _EXIT_SIMULATED_BOOTLOADER if _reset_kind(error) == "bootloader" else _EXIT_SIMULATED_RESET


def _fault_arm(faults: "list[FaultSpec]", chips: "dict[str, object]", wlan: "network.WLAN", *, deferred: bool) -> "Callable[[], None]":
    # The call that queues every --fault on its chip, made here unless deferred (--test-defer-faults arms it at FAULT_ARM).
    def arm() -> None:
        for fault in faults:
            _apply_fault(fault, chips, wlan)

    if not deferred:
        arm()
    return arm


async def _feed_gap_folder(watchdog: "machine.WDT") -> None:
    while True:
        await asyncio.sleep_ms(_FEED_GAP_FOLD_MS)
        _feed_gaps.fold(watchdog)


def _fram_write_fields(module: "object | None", chip: "_FramCounts | None") -> str:
    # The wired FRAM chip's payload writes, then per FRAM-backed logger of the booted module's objects, summed over its
    # chunk's two block addresses (one persisted entry counts 2); the remainder is the non-logger writes (SGP40 backup,
    # clears, erase units). Writes past writes_at's bound are unattributed, so the per-logger counts are short by them.
    if chip is None:
        return " fram_writes=0 fram_writes_by=-"
    counted: dict[int, tuple[str, int]] = {}
    for name in dir(module) if module is not None else ():
        owner = getattr(module, name, None)
        if isinstance(owner, type) or not hasattr(owner, "get_loggers"):
            continue  # a class's get_loggers is unbound; only built objects own loggers
        holder: _LoggerOwner = cast("_LoggerOwner", owner)
        for logger in holder.get_loggers():
            block_addr = getattr(getattr(logger, "fram", None), "_block_addr", None)  # PrintLogHistoryStore's chunk
            if block_addr is not None:
                counted[id(logger)] = (logger.name, sum(chip.writes_at.get(addr, 0) for addr in block_addr))
    by = ",".join(f"{name}:{n}" for name, n in sorted(counted.values()) if n) or "-"
    unattributed = f" fram_writes_unattributed={chip.writes_at_dropped}" if chip.writes_at_dropped else ""
    return f" fram_writes={chip.write_count} fram_writes_by={by}{unattributed}"


def _instance_key(driver: str, name_ext: str) -> str:
    return f"{driver}_{name_ext}" if name_ext else driver


def _link_directions(module_file: str, link: "machine.UARTLink") -> "dict[str, object]":
    # uart_link:silent's targets: each instance's outgoing direction by its instance key.
    directions: dict[str, object] = {}
    for key, bus_name in _uart_links(module_file):
        bus = machine.peripheral(bus_name)
        if isinstance(bus, machine.UART):
            directions[key] = link.direction_from(bus)
    return directions


async def _mem_sampler(interval_ms: int) -> None:
    # Optional (--mem-sample-interval-ms): /status's MemFree is one poll's reading, not a stream, so these lines feed the CI
    # suite's Run 11 memory-trend check (_run_11_soak()); its collect, kept, is the one twin exception the gc site checker
    # allows (scripts/_check_gc_collect_sites.py) - README.md has the reasoning and the calibration.
    while True:
        await asyncio.sleep_ms(interval_ms)
        gc.collect()
        print(f"MEM_SAMPLE {time.ticks_ms()} {gc.mem_free()}")


def _parse_test_flag(arg: str, remaining: "list[str]", flags: "TestFlags") -> "TestFlags | None":
    # `flags` with one --test-* flag set; None for an argument that is no test flag.
    hold, stall, conn, fault, hang, stall_max, over_cap, entry, lag, drop, wdt_fault, defer, pin, uart_clock = flags
    if arg == "--test-hold-closing-slot":
        hold = True
    elif arg == "--test-stall-loop-ms":
        stall = _positive_int(arg, "N", pop_value(remaining, arg))
    elif arg == "--test-conn-status-interval-ms":
        conn = _positive_int(arg, "N", pop_value(remaining, arg))
    elif arg == "--test-fault-status-interval-ms":
        fault = _positive_int(arg, "N", pop_value(remaining, arg))
    elif arg == "--test-shutdown-hang":
        hang = pop_value(remaining, arg)
        if hang not in _SHUTDOWN_HANG_STEPS:
            raise ValueError(f"--test-shutdown-hang {hang!r} not recognized - expected one of {_SHUTDOWN_HANG_STEPS}")
    elif arg == "--test-flash-stall-max":
        stall_max = True
    elif arg == "--test-uart-over-cap":
        over_cap = True
    elif arg == "--test-hold-system-entry":
        errno_text, _sep, mode = pop_value(remaining, arg).partition(":")
        if mode not in ("", _HOLD_CUT):
            raise ValueError(f"{arg} mode {mode!r} not recognized - expected ERRNO or ERRNO:{_HOLD_CUT}")
        entry = (_positive_int(arg, "ERRNO", errno_text), mode == _HOLD_CUT)
    elif arg == "--test-loop-lag-ms":
        lag = _positive_int(arg, "N", pop_value(remaining, arg))
    elif arg == "--test-drop-timer-fire":
        drop = pop_value(remaining, arg)
        if drop not in _DROP_TIMER_SITES:
            raise ValueError(f"--test-drop-timer-fire {drop!r} not recognized - expected one of {_DROP_TIMER_SITES}")
    elif arg == "--test-watchdog-fault":
        wdt_fault = pop_value(remaining, arg)
        if wdt_fault not in _WATCHDOG_FAULT_KINDS:
            raise ValueError(f"--test-watchdog-fault {wdt_fault!r} not recognized - expected one of {_WATCHDOG_FAULT_KINDS}")
    elif arg == "--test-defer-faults":
        defer = True
    elif arg == "--test-pin-send-buffer":
        pin = True
    elif arg == "--test-uart-driven-clock":
        uart_clock = True
    else:
        return None
    return TestFlags(hold, stall, conn, fault, hang, stall_max, over_cap, entry, lag, drop, wdt_fault, defer, pin, uart_clock)


def _parse_wifi_outcome(value: str) -> int:
    if value not in _WIFI_OUTCOME_MAP:
        raise ValueError(f"--wifi-outcome {value!r} not recognized - expected one of {sorted(_WIFI_OUTCOME_MAP)}")
    return _WIFI_OUTCOME_MAP[value]


def _positive_int(flag: str, field: str, text: str) -> int:
    try:
        value = int(text)
    except ValueError as e:
        raise ValueError(f"{flag} {field} {text!r} is not an integer") from e
    if value < 1:
        raise ValueError(f"{flag} {field} must be >= 1, got {value}")
    return value


def _print_boot_phases(device: str) -> None:
    # Each boot-phase mark (asy_system_service's region-1 write) also printed as one line, so a booted run's log shows its
    # boot order (SPECIFICATION.md Part A.7); the write is unchanged. Installed once per process, naming the latest main()'s device.
    global _boot_phase_device
    _boot_phase_device = device
    service = sys.modules.get("asy_system_service")
    if service is None or service._write_region.__name__ == "_boot_phase_line":
        return
    names = {getattr(service, name): name for name in dir(service) if name.startswith("BOOT_")}
    write = service._write_region

    def _boot_phase_line(region: int, magic: int, value: int) -> None:
        write(region, magic, value)
        if region == 1:
            print(f"{_LINE_PREFIX} [{_boot_phase_device}] boot phase: {names.get(value, value)}")

    service.__dict__["_write_region"] = _boot_phase_line  # the module global boot_phase() calls


def _print_shutdown_line(config: RunConfig) -> None:
    # From main()'s finally and the __main__ handlers (an interrupt while main() is suspended skips that finally, F.6),
    # once per process, after the GC summary whose max free sz it is read with; collected first, as an allocation would.
    # Marked only once printed: an interrupt landing before the line leaves the handler's call to print it whole.
    global _shutdown_printed
    if _watchdog is not None and not _shutdown_printed:
        gc.collect()
        micropython.mem_info()  # the largest free block's only reader (py/gc.c gc_info(), v1.29.0)
        print(_shutdown_line(config.device, _watchdog, _feed_gaps, _uart_counts) + _fram_write_fields(_module, machine._current_fram_chip))
        _shutdown_printed = True


def _print_watchdog_would_trigger(watchdog: "machine.WDT") -> None:
    # The moment a starved watchdog would reset silicon, as it happens: a host waiting on a hang ends there.
    print(f"WATCHDOG_WOULD_TRIGGER count={watchdog.would_have_triggered_count}")


async def _release_after_build(held: "tuple[asyncio.Event, asyncio.Event]") -> None:
    # Lifts the hold once built: main() resumes at the runner's next suspension, so after everything the runner arms
    # with no await between it and this call.
    built, released = held
    await built.wait()
    released.set()


def _require_wired(device: str, chips: "dict[str, object]") -> None:
    # A name in the vocabulary is not a chip this run wired: a device carries only what its TOML declares.
    # Without this the miss is a bare KeyError from inside the fault plumbing, naming nothing (Part L.5).
    if device not in chips:
        raise ValueError(f"{_LINE_PREFIX}: --fault/--hang device {device!r} is not wired on this run - wired here: {sorted(chips)}")


def _reset_kind(error: "machine.SimulatedRebootError") -> str:
    return "bootloader" if isinstance(error, machine.SimulatedBootloaderEntryError) else "reset"


def _reset_line(device: str, error: "machine.SimulatedRebootError") -> str:
    return (
        f"{_LINE_PREFIX} [{device}] machine reset: kind={_reset_kind(error)} reset_count={machine.reset_count} "
        f"bootloader_count={machine.bootloader_count}"
    )


def _resolve_device(flag: str, key: str, vocabulary: "dict[str, tuple[str, ...]]") -> str:
    driver = _driver_of(key)
    if driver is None or driver not in vocabulary:
        raise ValueError(f"{flag} device {key!r} not recognized - expected a driver or <driver>_<name_ext> of {sorted(vocabulary)}")
    return driver


async def _serve_until(duration_s: "float | None", stop_file: "str | None") -> None:
    # The whole duration (None: forever), or until stop_file exists: either way serving ends here and the run shuts down
    # on main()'s one clean path, so a caller done early skips the idle tail without a signal.
    if stop_file is None:
        while duration_s is None:
            await asyncio.sleep(3600)
        await asyncio.sleep(duration_s)
        return
    polls = None if duration_s is None else -(-int(duration_s * 1000) // _STOP_FILE_POLL_MS)  # polls, not ticks: never short
    while polls is None or polls > 0:
        try:
            os.stat(stop_file)
        except OSError:
            await asyncio.sleep_ms(_STOP_FILE_POLL_MS)
            polls = None if polls is None else polls - 1
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


def _state_path(value: str) -> "str | None":
    # "" means in memory only, as machine.configure_fram_state_path(None) does.
    return value or None


# Test-only instrumentation (owner, 2026-09-30, paraphrase): the runner, never src/ or the image, may rebind a booted
# object from outside or print internal state when a named --test-* flag asks;
# tests_scripts/test_twin_runner_test_flags.py keeps every one off by default and out of the production entry path.


def _test_arm_faults(arm: "Callable[[], None]", say: "Callable[[str], None]" = print) -> "Callable[[], None]":
    # The FAULT_ARM trigger: the --fault injections main() held back are queued at the first one, so a boot meets none of
    # them; FAULTS_ARMED follows each trigger, and a later one queues nothing more.
    armed: list[bool] = []

    def trigger() -> None:
        if not armed:
            armed.append(True)
            arm()
        say("FAULTS_ARMED")

    return trigger


async def _test_arm_shutdown_hang(module: "ModuleType", step: str) -> None:
    # The steps' targets exist once the supervisor has started every task (start_tasks()); armed earlier, a step finds
    # no task or config store, or holds a lock setup needs. Owns the runner tasks the step started: its cancel ends them.
    sysfunct = module.sysfunct
    while not sysfunct._tasks or any(task is None for task in sysfunct._tasks):
        await asyncio.sleep_ms(_READY_POLL_MS)
    started = _test_shutdown_hang(module, step)
    try:
        await asyncio.Event().wait()
    finally:
        for task in started:
            task.cancel()


async def _test_conn_line(module: "ModuleType") -> str:
    # The webserver's open-connection gauge and its listen backlog, the two numbers a slot scenario reads.
    service = module.webserver
    return f"CONN_SLOTS open={service._open_conns} backlog={service._backlog}"


async def _test_conn_status(module: "ModuleType", interval_ms: int) -> None:
    while True:
        print(await _test_conn_line(module))
        await asyncio.sleep_ms(interval_ms)


def _test_drop_timer_fire(module: "ModuleType", site: str, say: "Callable[[str], None]" = print) -> "Coroutine[object, object, None]":
    # Rebinds, from outside, the next init() of the one product one-shot `site` names, so the host sees what its lost fire
    # costs: the twin's drop knob is set before the arm (rp2's full depth-8 queue) and cleared once that fire was dropped.
    sysfunct = module.sysfunct
    timer: machine.Timer = sysfunct._reset_timer
    armed = asyncio.Event()
    real_init = timer.init

    def init(**kwargs: object) -> None:
        timer.init = real_init  # type: ignore[method-assign]  # the next arm only
        machine.Timer.drop_next_soft_callbacks = _DROP_WINDOW_CALLBACKS
        real_init(**kwargs)  # type: ignore[arg-type]
        armed.set()

    timer.init = init  # type: ignore[method-assign]
    return _test_drops_cleared(timer, armed, site, say)


async def _test_drops_cleared(timer: "machine.Timer", armed: "asyncio.Event", site: str, say: "Callable[[str], None]" = print) -> None:
    # DROP_ARMED once the knob is set, FIRE_DROPPED once the one-shot's own loop ended on its dropped fire; then every
    # other timer's soft callbacks run again, so what follows is that one lost fire's cost alone.
    await armed.wait()
    say(f"DROP_ARMED {site}")
    run = timer._task
    while run is not None and not run.done():
        await asyncio.sleep_ms(1)
    dropped = _DROP_WINDOW_CALLBACKS - machine.Timer.drop_next_soft_callbacks
    machine.Timer.drop_next_soft_callbacks = 0
    say(f"FIRE_DROPPED {site} callbacks={dropped}")


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


def _test_freeze(watchdog: "machine.WDT | None") -> None:
    # The loop frozen for good, as a write that never ends freezes silicon: the WDT's countdown task cannot run, so its
    # elapsed timeout is credited here once; the host's stop file, which the frozen loop cannot poll, ends it as SIGINT.
    credited = False
    while True:
        time.sleep_ms(_FREEZE_STEP_MS)
        if not credited and watchdog is not None and watchdog._armed_at_ms is not None and time.ticks_diff(time.ticks_ms(), watchdog._armed_at_ms) >= watchdog.timeout:
            watchdog._record_would_trigger()
            credited = True
        if _stop_file is not None:
            try:
                os.stat(_stop_file)
            except OSError:
                continue
            raise KeyboardInterrupt


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


def _test_hold_system_entry(module: "ModuleType", errno_held: int, say: "Callable[[str], None]" = print, *, cut: bool = False) -> "Callable[[], None]":
    # SystemService's entry with errno_held (the supervisor's escalation entry) lands, then the escalation holds before
    # its reboot until an ENTRY_RELEASE line, ENTRY_HELD marking the hold; with :cut the entry's own write stops for
    # good after its first block's busy mark, the loop frozen with it (_test_freeze). Returns the release callback.
    sysfunct, gate = module.sysfunct, asyncio.Event()
    logger = sysfunct.pr
    real_err_s = logger.err_s
    if cut:  # the entry's real write starts and freezes after its first block's busy mark, never released
        chunk = getattr(logger, "fram", None)
        if chunk is None:
            raise RuntimeError("SystemService's logger has no FRAM chunk, so no block of its entry can be cut")
        real_status, armed = chunk._handle_status_bytes, [False]

        def status_then_freeze(addr: int, val: int, *, check_idle: bool) -> "bool | None":
            done: bool | None = real_status(addr, val, check_idle=check_idle)
            if armed[0] and val == _FRAM_STATUS_BUSY and done is not None:
                armed[0] = False
                say("ENTRY_HELD")
                _test_freeze(sysfunct._watchdog)
            return done

        def cut_entry(*args: object, **kwargs: object) -> None:
            armed[0] = armed[0] or kwargs.get("errno") == errno_held
            real_err_s(*args, **kwargs)

        logger.err_s, chunk._handle_status_bytes = cut_entry, status_then_freeze
        return lambda: None  # never released: the cut is the mode

    real_reboot, logged = sysfunct._reboot, [False]

    def entry(*args: object, **kwargs: object) -> None:
        real_err_s(*args, **kwargs)
        logged[0] = logged[0] or kwargs.get("errno") == errno_held

    async def held_reboot(code: int, message: str, action: "Callable[[], None]", *, fed: bool = False) -> None:
        if logged[0] and not gate.is_set():
            say("ENTRY_HELD")
            await gate.wait()
        await real_reboot(code, message, action, fed=fed)

    def release() -> None:
        gate.set()
        say("ENTRY_RELEASED")

    logger.err_s, sysfunct._reboot = entry, held_reboot
    return release


async def _test_loop_lag(period_ms: int, say: "Callable[[str], None]" = print, links: "Iterable[tuple[str, _LinkCounts, object]]" = ()) -> None:
    # One task sleeping period_ms at a time: each wake's overshoot past its due time folds into a fixed 1 ms histogram,
    # and each window's maximum, 99th percentile and sample count print as one LOOP_LAG line, with each link's transfers.
    bins = [0 for _ in range(_LOOP_LAG_BUCKETS)]
    worst = samples = 0
    window = time.ticks_ms()
    while True:
        due = time.ticks_add(time.ticks_us(), period_ms * 1000)
        await asyncio.sleep_ms(period_ms)
        lag = max(0, time.ticks_diff(time.ticks_us(), due))
        worst = max(worst, lag)
        bins[min(lag // 1000, _LOOP_LAG_BUCKETS - 1)] += 1
        samples += 1
        if time.ticks_diff(time.ticks_ms(), window) >= _LOOP_LAG_REPORT_MS:
            say(f"LOOP_LAG max_us={worst} p99_us={_test_p99_us(bins, samples, worst)} samples={samples}" + "".join(f" {key}={link._transfers}" for key, link, _bus in links))
            for i in range(_LOOP_LAG_BUCKETS):
                bins[i] = 0
            worst = samples = 0
            window = time.ticks_ms()


def _test_never_pulled(_chunk: int, _buf: "memoryview") -> int:
    return 0  # the over-cap train is refused before its first frame, so nothing is ever pulled


def _test_p99_us(bins: "list[int]", samples: int, worst: int) -> int:
    # The upper edge of the bin holding the 99th-percentile sample, never past the window's own maximum.
    rank, seen = samples - samples // 100, 0
    for i, count in enumerate(bins[:-1]):
        seen += count
        if seen >= rank:
            return min((i + 1) * 1000, worst)
    return worst


def _test_pin_send_buffer(module: "ModuleType", say: "Callable[[str], None]" = print) -> None:
    # WebserverService._serve() gets each stream start_server() accepts; rebound while the setup batch still runs, it
    # pins each socket's send buffer at the kernel's floor first, as rp2's is small and fixed (TCP_SND_BUF in
    # toolchain/versions.toml's [lwip]), so a large body is mid-write at a client's reset on any host.
    service = module.webserver
    real_serve = service._serve

    async def serve(reader: object, writer: "_Accepted") -> None:
        accepted = _test_send_buffer(writer.s)
        writer.s.setsockopt(socket.SOL_SOCKET, _SO_SNDBUF, 1)  # Linux doubles a request and clamps it to its floor (socket(7))
        say(f"SNDBUF_PINNED bytes={_test_send_buffer(writer.s)} accepted_bytes={accepted}")
        await real_serve(reader, writer)

    service._serve = serve


async def _test_raising_report(_task: object, _n: int) -> None:
    raise RuntimeError("the supervisor's dead-task report raised (a test-only watchdog fault)")


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


def _test_send_buffer(sock: "_Sock") -> int:
    # SO_SNDBUF as the kernel reads it back, through libc: the Unix port's socket has no getsockopt().
    value, size = bytearray(4), bytearray(struct.pack("I", 4))
    if ffi.open("libc.so.6").func("i", "getsockopt", "iiipp")(sock.fileno(), socket.SOL_SOCKET, _SO_SNDBUF, value, size) != 0:
        raise OSError(f"getsockopt(SO_SNDBUF) failed on fd {sock.fileno()}")
    return int(struct.unpack("i", value)[0])


def _test_shutdown_hang(module: "ModuleType", step: str) -> "list[asyncio.Task[None]]":
    # Each step rebinds, from outside, the one product object that step of the controlled shutdown waits on, so the host
    # proves the watchdog ends a hung step; returns the runner tasks it started. HANG <step> once armed.
    sysfunct, loop, started = module.sysfunct, asyncio.get_event_loop(), []
    if step == "S1":
        # the supervisor's dead-task report never returns and one supervised task ends: the pass never parks
        sysfunct._log_dead_task = _test_report_then_hang(f"HUNG {step}")
        next(task for task in sysfunct._tasks if task is not None).cancel()
    elif step == "S2":
        sysfunct._config_stores[0].flush_pending = _test_hang_forever  # the store step's flush never returns
    elif step == "S4":
        # a supervised task that swallows its cancel, which the task step awaits; not a runner task (it never ends)
        sysfunct._tasks.append(loop.create_task(_test_swallow_cancel()))
        sysfunct._task_names.append("_test_swallow_cancel")  # the supervisor names each slot's lines
    elif step == "S5reset":
        started.append(loop.create_task(_test_hold(sysfunct._config_stores[0]._config_lock)))  # the reset's store lock
    elif step == "S5erase":
        module.fram.erase_chip = _test_hang_forever  # the erase step never returns
    elif step == "S6":
        sysfunct._reset_timer = _TestInertTimer()  # the reset one-shot never fires: only the watchdog resets
    print(f"HANG {step}")
    return started


def _test_stall_loop(stall_ms: int) -> "Callable[[], None]":
    def stall() -> None:
        time.sleep_ms(stall_ms)  # no await: the whole loop stops, as a long synchronous call on silicon stops it
        print("STALL")

    return stall


def _test_start(
    flags: "TestFlags", module: "ModuleType", chips: "dict[str, object]", links: "list[tuple[str, _ExercisedLink, _RxCounts]]", main_task: "asyncio.Task[None]", watchdog: "_Watchdog", arm: "Callable[[], None]",
) -> "list[asyncio.Task[None]]":
    # Each named flag's instrumentation, and only under its own flag; the runner tasks it started.
    loop, tasks, triggers = asyncio.get_event_loop(), [], {}
    if flags.hold_closing_slot:
        triggers["SLOT_RELEASE"] = _test_hold_closing_slot(module)
    if flags.stall_loop_ms:
        triggers["STALL_TRIGGER"] = _test_stall_loop(flags.stall_loop_ms)
    if flags.hold_system_entry:
        triggers["ENTRY_RELEASE"] = _test_hold_system_entry(module, flags.hold_system_entry[0], cut=flags.hold_system_entry[1])
    if flags.defer_faults:
        triggers["FAULT_ARM"] = _test_arm_faults(arm)
    if flags.pin_send_buffer:
        _test_pin_send_buffer(module)
    if flags.hold_closing_slot or flags.stall_loop_ms or flags.hold_system_entry or flags.defer_faults:
        tasks.append(loop.create_task(_test_stdin_lines(triggers)))
    if flags.conn_status_interval_ms:
        tasks.append(loop.create_task(_test_conn_status(module, flags.conn_status_interval_ms)))
    if flags.fault_status_interval_ms:
        tasks.append(loop.create_task(_test_fault_status(chips, flags.fault_status_interval_ms)))
    if flags.shutdown_hang:
        tasks.append(loop.create_task(_test_arm_shutdown_hang(module, flags.shutdown_hang)))
    if flags.flash_stall_max:
        _test_flash_stall_max()
    if flags.uart_over_cap:
        tasks.append(loop.create_task(_test_uart_over_cap(links)))
    if flags.loop_lag_ms:
        tasks.append(loop.create_task(_test_loop_lag(flags.loop_lag_ms, links=links)))
    if flags.drop_timer_fire:
        tasks.append(loop.create_task(_test_drop_timer_fire(module, flags.drop_timer_fire)))
    if flags.watchdog_fault:
        tasks.append(loop.create_task(_test_watchdog_fault(module, flags.watchdog_fault, main_task, watchdog)))
    if flags.uart_driven_clock:
        tasks.append(loop.create_task(_test_uart_driven_clock()))
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


async def _test_uart_driven_clock(say: "Callable[[str], None]" = print) -> None:
    # The UART link's loaded modules on one driven clock (digital_twin/_driven_clock.py) until the run ends, then released.
    clock = _driven_clock.DrivenClock()
    say(f"UART_CLOCK driven modules={clock.install([sys.modules[name] for name in _UART_CLOCK_MODULES if name in sys.modules])}")
    try:
        await clock.drive()
    finally:
        say(f"UART_CLOCK released virtual_ms={clock.elapsed}")


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


async def _test_watchdog_fault(module: "ModuleType", kind: str, main_task: "asyncio.Task[None]", watchdog: "_Watchdog", say: "Callable[[str], None]" = print) -> None:
    # After the supervisor's first feed (the first once its tasks exist), one fault from outside that ends the feeding: the
    # dead-task report raises as one task ends, the product's main() is cancelled under the live runner loop, or the loop
    # blocks past the timeout. WDT_AT_FAULT names the feed count the watchdog then starves from.
    sysfunct = module.sysfunct
    while not sysfunct._tasks or any(task is None for task in sysfunct._tasks):
        await asyncio.sleep_ms(_READY_POLL_MS)
    fed = watchdog.feed_count
    while watchdog.feed_count == fed:
        await asyncio.sleep_ms(_READY_POLL_MS)
    say(f"WDT_AT_FAULT {watchdog.feed_count}")
    if kind == "supervisor-raise":
        sysfunct._log_dead_task = _test_raising_report  # the supervisor's own report: its raise ends the supervisor loop
        next(task for task in sysfunct._tasks if task is not None).cancel()
    elif kind == "main-exit":
        main_task.cancel()  # the product's main(), as if it returned: this runner's loop and its tasks run on
    else:
        time.sleep_ms(_WDT_FAULT_BLOCK_MS)  # no await: the whole loop stops, as a long synchronous call on silicon stops it


def _twin_host_field() -> str:
    # A TEST_TWIN_HOST moves every server's wildcard off 127.0.0.1, where the host-side talkers look: named when it does.
    host = _unix_port_udp_addr_shim.twin_host
    return "" if host == _unix_port_udp_addr_shim._DEFAULT_TWIN_HOST else f" twin_host={host!r}"


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


async def _wait_until_built(module: "_Booted") -> None:
    # webserver is the last global build_system() assigns before its setup batch; the runner's own boot holds there
    # until its faults are armed (_boot_held())
    while getattr(module, "webserver", None) is None:
        await asyncio.sleep_ms(_READY_POLL_MS)


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


async def main(config: RunConfig) -> None:
    global _watchdog, _shutdown_printed, _feed_gaps, _uart_counts, _module, _stop_file
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
        f"debug_level={config.debug_level!r} injections={injections!r} run={run!r}{_twin_host_field()}",
    )

    booted = load_module(config.module)
    module = cast("_Booted", booted)
    # rp2's RTC is the wall clock: an NTP set must move the product's time.time() here too
    _wall_clock.install(product_modules())
    _flash_stall.install(sys.modules["asy_config_manager"])  # rp2 writes its flash with interrupts off: each flush stalls
    _print_boot_phases(config.device)
    watchdog = machine.WDT(timeout=_WDT_TIMEOUT_MS, on_would_trigger=_print_watchdog_would_trigger)
    _watchdog, _shutdown_printed, _feed_gaps, _uart_counts, _module, _stop_file = watchdog, False, _FeedGaps(), [], booted, run.stop_file
    loop = asyncio.get_event_loop()
    main_task, held = _boot_held(loop, module, watchdog, config)
    tasks = [loop.create_task(_feed_gap_folder(watchdog))]
    if responder is not None:
        tasks.append(loop.create_task(responder.serve()))
    if run.mem_sample_interval_ms is not None:
        tasks.append(loop.create_task(_mem_sampler(run.mem_sample_interval_ms)))
    try:
        await _release_after_build(held)
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
        arm_faults = _fault_arm(injections.faults, chips, wlan, deferred=config.instrumentation.defer_faults)
        for hang in injections.hangs:
            _apply_hang(hang, chips)
        if injections.wifi_outcomes:
            wlan.script_connect_outcomes(injections.wifi_outcomes)
        tasks.extend(_test_start(config.instrumentation, booted, chips, _uart_counts, main_task, watchdog, arm_faults))

        if run.duration is None:
            print(f"Serving forever at http://{config.host}:{config.port}/ - Ctrl+C to stop")
            await _serve_until(None, run.stop_file)
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
            text[arg] = pop_value(remaining, arg)
        elif arg == "--port":
            port = int(pop_value(remaining, arg))
        elif arg == "--online-ntp":
            online_ntp = True
        elif arg == "--seed":
            seed = int(pop_value(remaining, arg))
        elif arg == "--fault":
            faults.append(parse_fault_spec(pop_value(remaining, arg)))
        elif arg == "--hang":
            hangs.append(parse_hang_spec(pop_value(remaining, arg)))
        elif arg == "--wifi-outcome":
            wifi_outcomes.append(_parse_wifi_outcome(pop_value(remaining, arg)))
        elif arg == "--duration":
            duration = float(pop_value(remaining, arg))
        elif arg == "--gc-threshold":
            gc_threshold = int(pop_value(remaining, arg))
        elif arg == "--mem-sample-interval-ms":
            mem_sample_interval_ms = int(pop_value(remaining, arg))
        elif arg == "--debug-level":
            debug_level = _debug_level(pop_value(remaining, arg))
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
    if not text["--config-dir"].endswith("/"):
        # config_filename() appends each file's name to the directory as given: without its "/" they land beside it.
        raise ValueError(f"--config-dir {text['--config-dir']!r} must end with '/' (src/asy_config_manager.py config_filename() appends config_<name>.cfg to it as given)")

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


def _shutdown_cleanup() -> None:
    # The one synchronous cleanup every twin exit path runs (SIGINT, a simulated reset in the runner)
    machine.flush_fram()
    machine.flush_scd30()


def parse_fault_spec(spec: str) -> "FaultSpec":
    # DEVICE:OP[:TIMES[:MATCH]] -> (device, op, times, match, kind); MATCH is hex, and the literal "stack" in the
    # TIMES place queues one stack-exhaustion fault instead of an OSError.
    parts = spec.split(":")
    if not 2 <= len(parts) <= 4:
        raise ValueError(f"malformed --fault {spec!r} - expected DEVICE:OP[:TIMES[:MATCH]]")
    device, op = parts[0], parts[1]
    driver = _resolve_device("--fault", device, _FAULT_DEVICE_OPS)
    if op not in _FAULT_DEVICE_OPS[driver]:
        raise ValueError(f"--fault op {op!r} not recognized for device {device!r} - expected one of {_FAULT_DEVICE_OPS[driver]}")
    if len(parts) == 2:
        return device, op, 1, None, _OSERROR_KIND
    if (driver, op) in _PERSISTENT_FAULT_OPS:
        raise ValueError(f"--fault {driver}:{op} is a mode that stays set for the run - it takes no TIMES or MATCH")
    queued = driver != "wlan" and (driver, op) != ("fram", "wren")  # the ops a FaultInjector queue carries
    if len(parts) == 4 and not queued:
        raise ValueError(f"--fault {driver}:{op} takes no MATCH - only a queued bus fault is matched by its key")
    if parts[2] == _STACK_KIND:
        if not queued or len(parts) == 4:
            raise ValueError(f"--fault {driver}:{op}:stack needs a queued bus fault and takes no MATCH")
        return device, op, 1, None, _STACK_KIND
    times = _positive_int("--fault", "TIMES", parts[2])
    if len(parts) == 3:
        return device, op, times, None, _OSERROR_KIND
    try:
        match = int(parts[3], 16)
    except ValueError as e:
        raise ValueError(f"--fault MATCH {parts[3]!r} is not a hexadecimal key") from e
    return device, op, times, match, _OSERROR_KIND


def parse_hang_spec(spec: str) -> "HangSpec":
    # --hang DEVICE:OP:SECONDS[:TIMES] queues a real blocking sleep, which _fault_injection.py's
    # docstring explains is the only faithful way to wedge a bus against the watchdog. TIMES
    # defaults to 1, since real hardware gets one 8388ms window before the WDT resets it.
    parts = spec.split(":")
    if len(parts) not in (3, 4):
        raise ValueError(f"malformed --hang {spec!r} - expected DEVICE:OP:SECONDS[:TIMES]")
    device, op = parts[0], parts[1]
    driver = _resolve_device("--hang", device, _HANG_DEVICE_OPS)
    if op not in _HANG_DEVICE_OPS[driver]:
        raise ValueError(f"--hang op {op!r} not recognized for device {device!r} - expected one of {_HANG_DEVICE_OPS[driver]}")
    try:
        seconds = float(parts[2])
    except ValueError as e:
        raise ValueError(f"--hang SECONDS {parts[2]!r} is not a number") from e
    if seconds <= 0:
        raise ValueError(f"--hang SECONDS must be > 0, got {seconds}")
    times = _positive_int("--hang", "TIMES", parts[3]) if len(parts) == 4 else 1
    return device, op, seconds, times


def product_modules() -> "list[object]":
    # The loaded src/ and generated modules; the twin's own and this runner's keep the host's time.
    found: list[object] = []
    for module in sys.modules.values():
        path = getattr(module, "__file__", None) or ""
        if "/" in path and path.rsplit("/", 2)[-2] in _PRODUCT_DIRS:
            found.append(module)
    return found


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
