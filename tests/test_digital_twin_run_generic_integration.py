"""Unit tests for digital_twin/run_generic_integration.py: parse_args(), the grouped config and test flags, the reset and shutdown lines,
the shared chip lookup and fault plumbing, and one smoke boot of a generated module through the generic entry point (every
device's own boot is tests_scripts/test_digital_twin_generated_boot.py's; the soak check is the CI suite's Run 11)."""

import asyncio
import io
import os
import struct
import sys
import time

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import ModuleType
    from typing import ParamSpec, TypeVar

    from launch import _Plan

    T = TypeVar("T")
    P = ParamSpec("P")

sys.path.insert(0, "ext")  # run_generic_integration.py transitively imports a booted sensortask_*
# module -> asy_webserver_service -> microdot - reaches the real, vendored ext/microdot.py.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's fake-free directory

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (unix_port_poll_prewarm.py)
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket exists (_unix_port_udp_addr_shim.py)

import _flash_stall  # noqa: E402 - imported after the prewarm and the UDP shim
import _unix_port_udp_addr_shim  # noqa: E402 - imported after the prewarm and the UDP shim
import _wall_clock  # noqa: E402 - imported after the prewarm and the UDP shim
import launch  # noqa: E402 - imported after the prewarm and the UDP shim
import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration as runner  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, cancel_all, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_tree import require_fresh  # noqa: E402 - imported after the prewarm and the UDP shim
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim
from _recording_print import record_prints  # noqa: E402 - imported after the prewarm and the UDP shim
from _strict_json import strict_loads  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_common import Injections, StatePaths  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_config_manager  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_ntp_client  # noqa: E402 - imported after the prewarm and the UDP shim

require_fresh()  # the smoke boot loads a generated module and its plan
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)

# @tunable l2.run_generic_integration_run_bound_s = 5.0
_RUN_BOUND_S = 5.0
# @tunable l2.run_generic_integration_main_run_bound_s = 15.0
_MAIN_RUN_BOUND_S = 15.0


# MICROPY_BYTES_PER_GC_BLOCK, 4 x the object word (py/mpconfig.h:251, v1.29.0), the unit of mem_info()'s max free sz.
_GC_BLOCK_BYTES = 4 * struct.calcsize("P")

_scratch = TmpScratch("rgi")
_PORTS = PortAllocator("test_digital_twin_run_generic_integration")


def _as_module(stand_in: object) -> "ModuleType":
    return cast("ModuleType", stand_in)  # a stand-in for the booted module, with the attributes the flag reaches


def _flash_stall_installed() -> bool:
    # Whether a run installed the flash stall on the config manager; uninstalled again (the builtin open) for later tests.
    stalling = getattr(asy_config_manager, "open", None)
    if stalling is not None:
        delattr(asy_config_manager, "open")
    return stalling is not None


# ---------------------------------------------------------------------------
# parse_args() - CLI argument parsing
# ---------------------------------------------------------------------------


def test_parse_args_requires_module_and_wiring_plan() -> None:
    assert "--module" in _refused(runner.parse_args, ["--wiring-plan", "plan.json"])
    assert "--wiring-plan" in _refused(runner.parse_args, ["--module", "sensortask_x"])


def test_parse_args_minimal_valid_config_takes_every_persistent_default() -> None:
    config = runner.parse_args(["--module", "sensortask_x", "--wiring-plan", "plan.json"])
    assert config == runner.RunConfig("sensortask_x", "plan.json")
    assert config.device == "sensortask_x"  # defaults to the module name, unset --device
    assert config.state == StatePaths("digital_twin/fram_state.json", "digital_twin/scd30_state.json", "digital_twin/mem_backup_state.json")
    assert config.config_dir == "digital_twin/config/"
    assert config.online_ntp is False
    assert config.debug_level is None  # the boot entry's own: every logger off until the stored level applies
    assert config.injections == Injections(None, [], [], [])
    # @tunable gc.threshold_bytes = 32768
    assert config.run == runner.RunLimits(None, 32768, None, None)
    assert config.instrumentation == runner._NO_TEST_FLAGS


def test_parse_args_takes_the_config_dir_the_online_ntp_switch_and_in_memory_state() -> None:
    config = _parse("--config-dir", "tests/_tmp/x/", "--online-ntp", "--fram-state-path", "", "--scd30-state-path", "", "--mem-backup-state-path", "")
    assert config.config_dir == "tests/_tmp/x/"
    assert config.online_ntp is True
    assert config.state == StatePaths(None, None, None)
    assert _parse("--mem-backup-state-path", "m.json").state.mem_backup == "m.json"


def test_every_test_only_flag_is_off_by_default_and_parses_when_named() -> None:
    assert runner.TestFlags(False, None, None, None, None, False, False, None, False, None, None) == runner._NO_TEST_FLAGS
    config = _parse(
        "--test-hold-closing-slot", "--test-stall-loop-ms", "40", "--test-conn-status-interval-ms", "50",
        "--test-fault-status-interval-ms", "60", "--test-shutdown-hang", "S5erase", "--test-flash-stall-max", "--test-uart-over-cap",
        "--test-hold-system-entry", "25", "--test-kbd-traceback", "--test-loop-lag-ms", "10", "--test-drop-timer-fire", "sequencer",
    )
    assert config.instrumentation == runner.TestFlags(True, 40, 50, 60, "S5erase", True, True, 25, True, 10, "sequencer")
    refused = (("--test-shutdown-hang", "S7"), ("--test-stall-loop-ms", "0"), ("--test-conn-status-interval-ms", "x"), ("--test-hold-system-entry", "0"), ("--test-loop-lag-ms", "0"), ("--test-drop-timer-fire", "ntp"))
    for flags in refused:
        _refused(_parse, *flags)


def test_parse_args_takes_a_debug_level_the_products_loggers_take_and_refuses_any_other() -> None:
    assert (_parse("--debug-level", "1").debug_level, _parse("--debug-level", "5").debug_level) == (1, 5)
    for value in ("-1", "6", "x"):
        assert "--debug-level" in _refused(_parse, "--debug-level", value), value


def test_run_config_compares_and_prints_its_grouped_fields() -> None:
    faulted = runner.RunConfig("m", "p.json", injections=Injections(None, [("sgp40", "writeto", 1, None, "oserror")], [], []))
    assert faulted != runner.RunConfig("m", "p.json")
    assert faulted == runner.RunConfig("m", "p.json", injections=Injections(None, [("sgp40", "writeto", 1, None, "oserror")], [], []))
    assert runner.RunConfig("m", "p.json", environment=runner.RunEnvironment("c/", False, runner._NO_TEST_FLAGS, None)) != runner.RunConfig("m", "p.json")
    text = repr(faulted)
    for field in ("state=", "injections=", "run=", "environment=", "config_dir=", "online_ntp=", "instrumentation=", "debug_level="):
        assert field in text, (field, text)


def test_parse_args_device_host_port_and_the_run_limits() -> None:
    config = _parse("--device", "novel_combo", "--host", "0.0.0.0", "--port", "9090", "--gc-threshold", "-1", "--mem-sample-interval-ms", "25")
    assert (config.device, config.host, config.port) == ("novel_combo", "0.0.0.0", 9090)
    assert config.run == runner.RunLimits(None, -1, 25, None)
    assert _parse("--stop-file", "s").run.stop_file == "s"
    assert _parse("--stop-file", "").run.stop_file is None


def test_parse_args_fault_hang_and_wifi_outcome_reuse_launchs_own_parsers() -> None:
    config = _parse("--fault", "sgp40:writeto:2:59", "--hang", "scd30:readfrom_into:0.5", "--wifi-outcome", "no_ap")
    assert config.injections.faults == [("sgp40", "writeto", 2, 0x59, "oserror")]
    assert config.injections.hangs == [("scd30", "readfrom_into", 0.5, 1)]
    assert config.injections.wifi_outcomes == [network.STAT_NO_AP_FOUND]


def test_parse_args_rejects_an_unrecognized_flag_or_a_missing_value() -> None:
    _refused(_parse, "--bogus")
    _refused(_parse, "--host")  # _pop_value()'s own guard


def test_parse_args_help_exits_zero_before_parsing_anything_else() -> None:
    for argv in (["--help"], ["--port", "x", "-h"]):
        try:
            runner.parse_args(argv)
            raise AssertionError(f"expected SystemExit(0) for {argv}")
        except SystemExit as e:
            assert e.args == (0,), f"{argv}: --help must exit 0, got {e.args}"


# ---------------------------------------------------------------------------
# The exits and their lines: a simulated reset's code and line, and the one shutdown line
# ---------------------------------------------------------------------------


def test_a_simulated_reset_maps_to_its_exit_code_and_its_line() -> None:
    reset, bootloader = machine.SimulatedResetError("r"), machine.SimulatedBootloaderEntryError("b")
    assert (runner._exit_code(reset), runner._exit_code(bootloader)) == (3, 4)
    machine.reset_count, machine.bootloader_count = 2, 1
    assert runner._reset_line("dev", reset) == "digital_twin/run_generic_integration.py [dev] machine reset: kind=reset reset_count=2 bootloader_count=1"
    assert runner._reset_line("dev", bootloader).endswith("machine reset: kind=bootloader reset_count=2 bootloader_count=1")


class _FakeWatchdog:
    # The run's WDT as the shutdown line reads it: its timeout, its counts and its feed times (ticks_ms values).
    def __init__(self) -> None:
        self.timeout = 8000
        self.feed_count = 0
        self.would_have_triggered_count = 0
        self.feed_times: list[int] = []

    def feed_at(self, *stamps: int) -> None:
        self.feed_times.extend(stamps)
        self.feed_count += len(stamps)


class _CountedLink:
    # A link driver's own two counters, as UARTLinkDriver keeps them.
    def __init__(self, transfers: int, failures: int) -> None:
        self._transfers, self._failures = transfers, failures


class _OverrunBus:
    def __init__(self, overruns: int) -> None:
        self.rx_overruns = overruns


def test_the_shutdown_line_carries_the_counts_the_largest_feed_gap_and_the_kept_registers() -> None:
    watchdog, gaps = _FakeWatchdog(), runner._FeedGaps()
    watchdog.feed_at(1000, 1500, 3500)
    gaps.fold(watchdog)
    watchdog.feed_at(3600, 6600)  # the gap across two folds counts too
    watchdog.would_have_triggered_count = 1
    machine.mem_backup(0)[0] = 0xDEADBEEF
    _flash_stall.longest_ms = 7
    try:
        line = runner._shutdown_line("wozi", watchdog, gaps, [("uart_link_init", _CountedLink(3, 1), _OverrunBus(2))])
    finally:
        _flash_stall.longest_ms = 0
    assert line == (
        "digital_twin/run_generic_integration.py [wozi] shutdown: would_have_triggered_count=1 feed_count=5 "
        "largest_feed_gap_ms=3000 wdt_timeout_ms=8000 mem_backup: r0=0xdeadbeef,0x00000000,0x00000000,0x00000000 "
        f"public_destinations_refused={_unix_port_udp_addr_shim.public_destinations_refused} flash_stall_longest_ms=7 "
        f"gc_block_bytes={_GC_BLOCK_BYTES} uart=uart_link_init:transfers=3,failures=1,overruns=2"
    ), line



def test_a_feed_span_the_watchdog_dropped_is_no_gap() -> None:
    watchdog, gaps = _FakeWatchdog(), runner._FeedGaps()
    watchdog.feed_at(0, 100)
    gaps.fold(watchdog)
    watchdog.feed_times = [9000, 9100]  # the bounded log kept only these two of five new feeds
    watchdog.feed_count += 5
    gaps.fold(watchdog)
    assert gaps.largest_ms == 100, gaps.largest_ms


# ---------------------------------------------------------------------------
# The config dir, the chip lookup and the fault plumbing the runner shares with launch.py
# ---------------------------------------------------------------------------


def test_ensure_dir_creates_or_keeps_a_dir_and_names_one_it_cannot_create() -> None:
    path = _scratch.path("cfg")
    runner._ensure_dir(path)
    runner._ensure_dir(path)  # already there: kept
    try:
        runner._ensure_dir(_scratch.path("absent") + "/cfg")
    except OSError as e:
        assert "absent/cfg" in str(e), e
    else:
        raise AssertionError("a config dir whose parent is missing must be refused, not swallowed")


def test_the_runner_shares_launchs_one_chip_lookup_and_fault_plumbing() -> None:
    for name in ("_collect_chips", "_apply_fault", "_apply_hang", "_shutdown_cleanup", "_pop_value", "parse_fault_spec"):
        assert getattr(runner, name) is getattr(launch, name), name


def test_collect_chips_finds_each_chip_through_the_constructed_bus_not_a_wrapper() -> None:
    plan: _Plan = {
        "device": "fixture-device",
        "buses": {"i2c1": [{"driver": "sgp40", "name_ext": "", "address": 0x59}]},
        "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x2000}},
        "uart": None,
        "pins": {},
    }
    machine.configure_wiring(plan)
    i2c1 = machine.I2C(1, scl=machine.Pin(19), sda=machine.Pin(18))
    spi0 = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    chips = launch._collect_chips(plan)
    assert chips == {"sgp40": i2c1.devices[0x59], "fram": spi0.device}, chips


def test_a_fault_naming_a_driver_this_device_does_not_carry_is_refused_by_name() -> None:
    # bmp3xx is in the vocabulary on every device but wired only where a TOML declares it: the refusal names the
    # device asked for, what is wired, and this entry point.
    message = _refused(launch._apply_fault, ("bmp3xx", "readfrom_mem", 1, None, "oserror"), {}, network.WLAN(network.STA_IF), source="run_generic_integration.py")
    assert "bmp3xx" in message and "digital_twin/run_generic_integration.py" in message, message


def test_link_directions_finds_each_instances_bus_by_its_generated_construction_line() -> None:
    source = _scratch.path("sensortask_fixture.py")
    with open(source, "w") as f:
        f.write("    uart_link_init = UARTLinkDriver(uart0, 'initiator', name_ext='init')\n")
        f.write("    uart_link_resp = UARTLinkDriver(uart1, 'responder', name_ext='resp')\n")
    uart0 = machine.UART(0, tx=machine.Pin(0), rx=machine.Pin(1), baudrate=115200)
    uart1 = machine.UART(1, tx=machine.Pin(8), rx=machine.Pin(9), baudrate=115200)
    link, _poll_a, _poll_b = machine.attach_crossover_jumper(uart0, uart1)
    directions = runner._link_directions(source, link)
    assert directions == {"uart_link_init": link.direction_from(uart0), "uart_link_resp": link.direction_from(uart1)}, directions
    assert runner._uart_links(source) == [("uart_link_init", "uart0"), ("uart_link_resp", "uart1")]  # the shutdown line's


def test_the_construction_lines_read_name_each_generated_devices_link_buses() -> None:
    # Against the generator's own output, so a changed construction line cannot silently drop the links' counters.
    for device in generated_devices():
        buses = sorted(bus for _key, bus in runner._uart_links(f"build/generated_src/sensortask_{device}.py"))
        pair = wiring_plan(device)["uart"]
        assert buses == (sorted((pair["initiator_bus"], pair["responder_bus"])) if pair else []), (device, buses)


class _Log:
    def __init__(self) -> None:
        self.clears = 0

    def clear(self) -> None:
        self.clears += 1


class _Direction:
    def __init__(self) -> None:
        self.wire_log = _Log()


class _FakeLink:
    def __init__(self) -> None:
        self.a_to_b, self.b_to_a = _Direction(), _Direction()


def test_the_wire_log_clearer_clears_each_bounded_log_in_place() -> None:
    link = _FakeLink()
    logs = (link.a_to_b.wire_log, link.b_to_a.wire_log)
    saved = runner._WIRE_LOG_CLEAR_INTERVAL_MS
    runner._WIRE_LOG_CLEAR_INTERVAL_MS = 1

    async def scenario() -> None:
        task = asyncio.create_task(runner._wire_log_clearer(link))
        await asyncio.sleep_ms(20)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        run_timed(scenario(), _RUN_BOUND_S)
    finally:
        runner._WIRE_LOG_CLEAR_INTERVAL_MS = saved
    assert (link.a_to_b.wire_log, link.b_to_a.wire_log) == logs, "a cleared log must stay the link's own object"
    assert logs[0].clears >= 1 and logs[1].clears >= 1


# ---------------------------------------------------------------------------
# The test-only instrumentation, on stand-ins for the booted objects each flag reaches
# ---------------------------------------------------------------------------


async def _forever(*_args: object) -> None:
    await asyncio.Event().wait()


def _hang_on(step: str, check: "Callable[[_Booted, _KnobChip], Coroutine[object, object, None]]") -> None:
    # Arms one --test-shutdown-hang step on stand-ins and runs `check` against them; the runner tasks it started end.
    async def scenario() -> None:
        supervised = asyncio.create_task(_forever())
        booted, chip = _Booted(supervised), _KnobChip()
        started = runner._test_shutdown_hang(_as_module(booted), {"fram": chip}, step)
        try:
            await check(booted, chip)
        finally:
            await cancel_all(started + [supervised])

    run_timed(scenario(), _RUN_BOUND_S)


class _Store:
    def __init__(self) -> None:
        self._config_lock = asyncio.Lock()
        self.flushed = 0

    async def flush_pending(self) -> None:
        self.flushed += 1


class _Logger:
    # SystemService's logger as the held-entry flag reaches it: the errno of every entry it wrote, in order.
    def __init__(self) -> None:
        self.written: list[int] = []

    async def err_s(self, *_args: object, errno: int = 0, sep: str = " ", end: str = "\n") -> None:
        del sep, end
        self.written.append(errno)


class _Sysfunct:
    def __init__(self, task: "asyncio.Task[None]") -> None:
        self._tasks: list[asyncio.Task[None] | None] = [None, task]
        self._config_stores = [_Store()]
        self._reset_timer: object = None
        self.logged = 0
        self.pr = _Logger()

    async def _log_dead_task(self, _task: object, _n: int) -> None:
        self.logged += 1


class _Chunk:
    def __init__(self) -> None:
        self._op_lock = asyncio.Lock()


class _FramDriver:
    async def get_size(self) -> int:
        return 0x2000

    async def report_set_values(self, _status: int) -> bool:
        return False


class _FramManager:
    def __init__(self) -> None:
        self._chunks = [_Chunk()]
        self.fram = _FramDriver()

    async def erase_chip(self, step_done: "Callable[[], None]") -> bool:
        await self.fram.get_size()
        step_done()
        return await self.fram.report_set_values(1)  # the first pass-2 unit refused


class _Counter:
    async def get_value(self) -> int:
        return 3


class _Webserver:
    def __init__(self) -> None:
        self._open_conns, self._backlog, self.closed = _Counter(), 7, 0

    async def _close_writer(self, _writer: object) -> None:
        self.closed += 1


class _Booted:
    def __init__(self, task: "asyncio.Task[None]") -> None:
        self.sysfunct, self.fram, self.webserver = _Sysfunct(task), _FramManager(), _Webserver()


class _KnobChip:
    def __init__(self) -> None:
        self.drop_next_wren = 0


def _parse(*flags: str) -> "runner.RunConfig":
    return runner.parse_args(["--module", "m", "--wiring-plan", "p.json"] + list(flags))


def _refused(fn: "Callable[P, object]", *args: "P.args", **kwargs: "P.kwargs") -> str:
    try:
        fn(*args, **kwargs)
    except ValueError as e:
        return str(e)
    raise AssertionError(f"expected ValueError for {args!r}")


def test_the_rebound_report_announces_itself_once_when_first_entered_then_never_returns() -> None:
    said: list[str] = []
    report = runner._test_report_then_hang("HUNG S1", said.append)

    async def scenario() -> None:
        assert said == []  # nothing at arming: the line marks the supervisor's pass meeting the ended task
        assert await _times_out(report(object(), 1))
        assert await _times_out(report(object(), 2))

    run_timed(scenario(), _RUN_BOUND_S)
    assert said == ["HUNG S1"]


def test_the_held_system_entry_waits_for_its_release_and_lets_every_other_entry_through() -> None:
    said: list[str] = []

    async def scenario() -> None:
        booted = _Booted(asyncio.create_task(_forever()))
        logger = booted.sysfunct.pr
        release = runner._test_hold_system_entry(_as_module(booted), 25, said.append)
        await asyncio.wait_for_ms(logger.err_s("Task error counter above", errno=24), 100)  # another errno: not held
        held = asyncio.create_task(logger.err_s("C stack exhausted - reboot triggered", errno=25))
        await asyncio.sleep_ms(5)
        assert logger.written == [24] and not held.done() and said == ["ENTRY_HELD"], (logger.written, said)
        release()
        await asyncio.wait_for_ms(held, 100)
        await asyncio.wait_for_ms(logger.err_s("again", errno=25), 100)  # released for good
        assert logger.written == [24, 25, 25] and said == ["ENTRY_HELD", "ENTRY_RELEASED"], (logger.written, said)
        await cancel_all([t for t in booted.sysfunct._tasks if t is not None])

    run_timed(scenario(), _RUN_BOUND_S)


def test_the_kbd_traceback_flag_catches_the_interrupt_object_by_a_sigint_and_prints_where_it_was_raised() -> None:
    said: list[str] = []
    out = io.StringIO()
    show = runner._test_kbd_traceback(said.append, out)
    assert said == ["KBD_CAPTURED True"], said
    show()
    text = out.getvalue()
    assert said[-1] == "KBD_TRACEBACK" and "KeyboardInterrupt" in text and "in _test_kbd_traceback" in text, (said, text)


class _Holder:
    # The booted module's and its system service's two attributes the drop flag reads.
    pass


def test_the_drop_flag_loses_that_one_shots_next_fire_alone_and_every_timer_runs_again_after_it() -> None:
    said: list[str] = []
    fired: list[int] = []
    ticks: list[int] = []
    sysfunct, module = _Holder(), _Holder()
    sysfunct._reset_timer, sysfunct._sequencer_timer = machine.Timer(), machine.Timer()  # type: ignore[attr-defined]
    module.sysfunct = sysfunct  # type: ignore[attr-defined]

    async def drive() -> int:
        cleared = asyncio.create_task(runner._test_drop_timer_fire(cast("ModuleType", module), "sequencer", said.append))
        ticker = machine.Timer(period=3, callback=lambda _t: ticks.append(1))
        sysfunct._sequencer_timer.init(period=15, mode=machine.Timer.ONE_SHOT, callback=lambda _t: fired.append(1))  # type: ignore[attr-defined]
        await asyncio.wait_for_ms(cleared, 2000)
        during = len(ticks)
        sysfunct._sequencer_timer.init(period=5, mode=machine.Timer.ONE_SHOT, callback=lambda _t: fired.append(2))  # type: ignore[attr-defined]
        await asyncio.sleep_ms(20)
        ticker.deinit()
        await asyncio.sleep_ms(0)  # the deinit's cancel lands before the run ends
        return len(ticks) - during

    after = run_timed(drive(), _RUN_BOUND_S)
    assert said[0] == "DROP_ARMED sequencer" and said[1].startswith("FIRE_DROPPED sequencer callbacks="), said
    assert int(said[1].split("=")[1]) >= 1 and machine.Timer.drop_next_soft_callbacks == 0, (said, machine.Timer.drop_next_soft_callbacks)
    assert fired == [2] and after >= 2, (fired, after)  # the armed fire lost, the next arm's kept, the ticker back


def test_the_flash_stall_flag_puts_every_flush_at_its_datasheet_maximum() -> None:
    assert _flash_stall.use_max is False
    runner._test_flash_stall_max()
    assert _flash_stall.use_max is True  # machine.reset_test_state() puts it back after this test


def test_the_loop_lag_flag_prints_each_windows_maximum_p99_and_samples() -> None:
    said: list[str] = []
    report = runner._LOOP_LAG_REPORT_MS
    runner._LOOP_LAG_REPORT_MS = 20

    async def drive() -> None:
        lag = asyncio.create_task(runner._test_loop_lag(5, said.append))
        await asyncio.sleep_ms(5)
        time.sleep_ms(20)  # one synchronous stall of the whole loop
        await asyncio.sleep_ms(50)
        lag.cancel()
        try:
            await lag
        except asyncio.CancelledError:
            pass

    try:
        run_timed(drive(), _RUN_BOUND_S)
    finally:
        runner._LOOP_LAG_REPORT_MS = report
    windows = [dict(part.split("=") for part in line.split()[1:]) for line in said if line.startswith("LOOP_LAG ")]
    assert len(windows) >= 2 and len(windows) == len(said), said
    assert max(int(w["max_us"]) for w in windows) >= 15000, said  # the stall, past the 5 ms sleep it delayed
    assert all(0 <= int(w["p99_us"]) <= int(w["max_us"]) and int(w["samples"]) > 0 for w in windows), said


def test_each_loop_lag_line_carries_every_links_transfers_so_far() -> None:
    # The count each line names is the link's own at that line, so a load window's transfers are two lines' difference.
    class Link:
        _transfers = 0
        _failures = 0

    link = Link()
    said: list[str] = []
    report = runner._LOOP_LAG_REPORT_MS
    runner._LOOP_LAG_REPORT_MS = 10

    async def drive() -> None:
        lag = asyncio.create_task(runner._test_loop_lag(2, said.append, [("uart_link_init", link, None)]))
        for _ in range(3):
            await asyncio.sleep_ms(12)
            link._transfers += 1
        lag.cancel()
        try:
            await lag
        except asyncio.CancelledError:
            pass

    try:
        run_timed(drive(), _RUN_BOUND_S)
    finally:
        runner._LOOP_LAG_REPORT_MS = report
    counts = [int(dict(part.split("=") for part in line.split()[1:])["uart_link_init"]) for line in said]
    assert len(counts) >= 2 and counts == sorted(counts) and counts[0] < counts[-1] <= 3, said


def test_the_lag_p99_is_its_bins_upper_edge_never_past_the_maximum() -> None:
    bins = [0 for _ in range(runner._LOOP_LAG_BUCKETS)]
    bins[0], bins[1], bins[5] = 98, 1, 1
    assert runner._test_p99_us(bins, 100, 5400) == 2000
    assert runner._test_p99_us(bins, 100, 1500) == 1500
    bins[1], bins[-1] = 0, 2
    assert runner._test_p99_us(bins, 101, 90000) == 90000  # past the last closed bin: the maximum itself


class _OverCapComm:
    # An initiating UARTComm as the over-cap offer meets it: its cap and the stream SET it refuses past it.
    def __init__(self) -> None:
        self._max_transfer_bytes = 12192
        self.offered: list[tuple[int, int]] = []

    async def uart_set_stream(self, set_id: int, total_size: int, _pull: object) -> bool:
        self.offered.append((set_id, total_size))
        return total_size <= self._max_transfer_bytes


class _ExercisedLink(_CountedLink):
    def __init__(self, role: str) -> None:
        super().__init__(0, 0)
        self._role, self._comm = role, _OverCapComm()


def test_the_over_cap_offer_waits_for_each_initiators_next_transfer_then_offers_one_train_past_its_cap() -> None:
    said: list[str] = []
    initiator, responder = _ExercisedLink("initiator"), _ExercisedLink("responder")

    async def scenario() -> None:
        offer = asyncio.create_task(runner._test_uart_over_cap([("uart_link_init", initiator, _OverrunBus(0)), ("uart_link_resp", responder, _OverrunBus(0))], said.append))
        await asyncio.sleep_ms(runner._READY_POLL_MS * 2)  # two of its polls
        assert initiator._comm.offered == []  # no transfer seen yet: a transaction may be in flight
        initiator._transfers += 1
        await asyncio.wait_for_ms(offer, 1000)

    run_timed(scenario(), _RUN_BOUND_S)
    assert initiator._comm.offered == [(0x02, 12193)] and responder._comm.offered == []
    assert said == ["UART_OVER_CAP uart_link_init refused"]


def test_s1_ends_one_supervised_task_and_its_dead_task_report_never_returns() -> None:
    async def check(booted: _Booted, _chip: _KnobChip) -> None:
        await asyncio.sleep_ms(0)
        task = booted.sysfunct._tasks[1]
        assert task is not None and task.done()
        assert await _times_out(booted.sysfunct._log_dead_task(task, 1))

    _hang_on("S1", check)


def test_s2_a_stores_flush_never_returns_and_s5reset_holds_its_lock() -> None:
    async def flush(booted: _Booted, _chip: _KnobChip) -> None:
        store = booted.sysfunct._config_stores[0]
        assert await _times_out(store.flush_pending()) and store.flushed == 0

    async def locked(booted: _Booted, _chip: _KnobChip) -> None:
        await asyncio.sleep_ms(0)
        assert booted.sysfunct._config_stores[0]._config_lock.locked()

    _hang_on("S2", flush)
    _hang_on("S5reset", locked)


def test_s3_holds_one_fram_chunks_lock() -> None:
    async def check(booted: _Booted, _chip: _KnobChip) -> None:
        await asyncio.sleep_ms(0)
        assert booted.fram._chunks[0]._op_lock.locked()

    _hang_on("S3", check)


def test_s5erase_arms_at_pass_two_and_the_refused_units_report_never_returns() -> None:
    async def check(booted: _Booted, chip: _KnobChip) -> None:
        assert chip.drop_next_wren == 0  # nothing armed before the erase reaches pass 2
        assert await _times_out(booted.fram.erase_chip(lambda: None))
        assert chip.drop_next_wren == 1

    _hang_on("S5erase", check)


def test_s6_the_reset_timer_never_fires() -> None:
    async def check(booted: _Booted, _chip: _KnobChip) -> None:
        timer = booted.sysfunct._reset_timer
        assert isinstance(timer, runner._TestInertTimer)
        fired: list[object] = []
        timer.init(period=1, mode=0, callback=fired.append)
        await asyncio.sleep_ms(5)
        assert fired == [] and timer.armed == 1

    _hang_on("S6", check)


def test_a_shutdown_hang_arms_once_every_supervised_task_has_started_and_its_cancel_ends_the_hold() -> None:
    # Armed before start_tasks() has filled the task list, a step meets an empty list or a lock setup still needs.
    async def scenario() -> None:
        supervised = asyncio.create_task(_forever())
        booted = _Booted(supervised)
        lock, poll = booted.fram._chunks[0]._op_lock, 3 * runner._READY_POLL_MS
        booted.sysfunct._tasks = []  # the supervisor's list before start_tasks()
        arming = asyncio.create_task(runner._test_arm_shutdown_hang(_as_module(booted), {"fram": _KnobChip()}, "S3"))
        await asyncio.sleep_ms(poll)
        booted.sysfunct._tasks = [None, supervised]  # start_tasks() mid-way: one task not yet started
        await asyncio.sleep_ms(poll)
        assert not lock.locked() and not arming.done()
        booted.sysfunct._tasks[0] = asyncio.create_task(_forever())
        await asyncio.sleep_ms(poll)
        assert lock.locked() and not arming.done()
        await cancel_all([arming])
        await asyncio.sleep_ms(0)
        assert not lock.locked()
        await cancel_all([t for t in booted.sysfunct._tasks if t is not None])

    run_timed(scenario(), _RUN_BOUND_S)


def test_the_held_closing_slot_releases_on_its_trigger() -> None:
    async def scenario() -> None:
        booted = _Booted(asyncio.create_task(_forever()))
        release = runner._test_hold_closing_slot(_as_module(booted))
        closing = asyncio.create_task(booted.webserver._close_writer(object()))
        await asyncio.sleep_ms(1)
        assert booted.webserver.closed == 1 and not closing.done()  # the real close ran; the slot is still held
        release()
        await asyncio.wait_for_ms(closing, 100)
        await cancel_all([t for t in booted.sysfunct._tasks if t is not None])

    run_timed(scenario(), _RUN_BOUND_S)


def test_the_status_lines_name_the_gauge_the_backlog_and_each_queued_fault() -> None:
    async def scenario() -> str:
        booted = _Booted(asyncio.create_task(_forever()))
        line = await runner._test_conn_line(_as_module(booted))
        await cancel_all([t for t in booted.sysfunct._tasks if t is not None])
        return line

    assert run_timed(scenario(), _RUN_BOUND_S) == "CONN_SLOTS open=3 backlog=7"
    plan: _Plan = {"device": "fixture-device", "buses": {"i2c0": [{"driver": "sgp40", "name_ext": "", "address": 0x59}]}, "spi": {}, "uart": None, "pins": {}}
    machine.configure_wiring(plan)
    machine.I2C(0, scl=machine.Pin(13), sda=machine.Pin(12))
    chips = launch._collect_chips(plan)
    assert runner._test_fault_line(chips) == "FAULT_PENDING -"
    launch._apply_fault(launch.parse_fault_spec("sgp40:writeto:2"), chips, network.WLAN(network.STA_IF))
    assert runner._test_fault_line(chips) == "FAULT_PENDING sgp40:writeto=2"


# ---------------------------------------------------------------------------
# _serve_until() - the duration as an upper bound a caller done early ends with a file
# ---------------------------------------------------------------------------


def test_serving_ends_at_once_when_the_stop_file_already_exists() -> None:
    stop = _scratch.path("stop_present")
    with open(stop, "w"):
        pass
    start = time.ticks_ms()
    run_timed(runner._serve_until(30.0, stop), _RUN_BOUND_S)
    assert time.ticks_diff(time.ticks_ms(), start) < 1000  # a 30 s bound, left on the first look


def test_serving_ends_once_the_stop_file_appears() -> None:
    stop = _scratch.path("stop_later")

    async def scenario() -> int:
        async def write_later() -> None:
            await asyncio.sleep_ms(150)
            with open(stop, "w"):
                pass

        writer = asyncio.create_task(write_later())
        start = time.ticks_ms()
        await runner._serve_until(30.0, stop)
        await writer
        return time.ticks_diff(time.ticks_ms(), start)

    elapsed = run_timed(scenario(), _RUN_BOUND_S)
    assert 150 <= elapsed < 3000, elapsed  # after the write, long before the 30 s bound


def test_serving_without_the_stop_file_lasts_the_whole_duration() -> None:
    for stop in (None, _scratch.path("stop_never")):
        start = time.ticks_ms()
        run_timed(runner._serve_until(0.2, stop), _RUN_BOUND_S)  # two stop-file polls
        assert time.ticks_diff(time.ticks_ms(), start) >= 200, stop


# ---------------------------------------------------------------------------
# main() - one real, short, bounded end-to-end smoke boot of a generated module with one injected fault. Exactly one:
# the supervisor leaves background tasks running after main_task.cancel() (the twin integration suite's docstring).
# ---------------------------------------------------------------------------


async def _times_out(aw: "Coroutine[object, object, object]") -> bool:
    # Every stand-in answers at once, so a call still pending after a few milliseconds is one that never returns.
    try:
        await asyncio.wait_for_ms(aw, 5)
    except asyncio.TimeoutError:
        return True
    return False


async def _until_a_line_from(name: str, lines: "list[tuple[object, ...]]", run: "Coroutine[object, object, None]") -> None:
    # Serves until `name`'s logger has printed a line, then ends the run on main()'s own shutdown path by its cancel.
    task = asyncio.create_task(run)
    while not task.done() and not any(line and line[0] == name for line in lines):
        await asyncio.sleep_ms(runner._READY_POLL_MS)
    await cancel(task)


def test_main_boots_at_the_stored_error_level_arms_a_fault_writes_the_responder_ntp_config_and_shuts_down_cleanly() -> None:
    # The memory gate reads the printed lines (owner, 2026-10-20: "Option 1 is good"): with DebugLevel 1 stored, the first
    # store set up after SYSTEM's prints the error a directory on its path makes, which a default boot keeps silent.
    config_dir = _scratch.dir("boot")
    with open(config_dir + "config_SYSTEM.cfg", "w") as f:
        f.write('{"DebugLevel": 1}')
    os.mkdir(config_dir + "config_WIFI.cfg")
    device = generated_devices()[0]
    config = runner.RunConfig(
        "sensortask_" + device,
        f"build/generated_src/sensortask_{device}_wiring_plan.json",  # buildgen wrote both
        listen=("127.0.0.1", _PORTS.next()),
        state=StatePaths(None, None, None),
        injections=Injections(None, [("sgp40", "writeto", 2, None, "oserror")], [], []),
        run=runner.RunLimits(None, runner._GC_THRESHOLD_DEFAULT, None, None),  # served until that error's line, then cancelled
        environment=runner.RunEnvironment(config_dir, False, runner._NO_TEST_FLAGS, 1),
    )
    with record_prints(echo=True) as printed:
        run_timed(_until_a_line_from("CFGMGR_WIFI", printed.lines, runner.main(config)), timeout_s=_MAIN_RUN_BOUND_S)
    assert any(line and line[0] == "CFGMGR_WIFI" for line in printed.lines), "the blocked config path printed nothing at error level"
    # The WDT the runner built and passed to the booted module's main(): an ordinary boot never starves it.
    watchdog = runner._watchdog
    assert watchdog is not None
    assert watchdog.would_have_triggered_count == 0
    with open(config_dir + "config_NTP.cfg") as f:
        stored = strict_loads(f.read())  # the whole store: the local responder, no fallback, every other key its default
    assert stored == {"NTPHost": "127.0.0.1", "DNSFallback": "", "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 3600, "DSTOffset": 3600}
    # rp2's RTC is the wall clock: every loaded product module reads the one the runner installed, the twin's own the host's
    assert _wall_clock.installed() is not None and asy_ntp_client.__dict__["time"] is _wall_clock.installed()
    clocks = [m.__dict__["time"] for m in (runner, machine)]
    assert not any(isinstance(clock, _wall_clock.WallClock) for clock in clocks), clocks
    assert _flash_stall_installed(), "the runner never installed the flash stall on the config manager"


class _IdleBoot:
    # A booted module that only waits, keeping the keywords its main() was called with: the runner's own boot and
    # shutdown path is what this boot exercises.
    def __init__(self, module_file: str) -> None:
        self.__file__ = module_file
        self.webserver = object()
        self.boot: dict[str, object] = {}

    async def main(self, **boot: object) -> None:
        self.boot = boot
        await asyncio.sleep(3600)


class _InterruptedAwait:
    # The booted main's task as the runner awaits it in its shutdown drain: the interrupt lands in that await.
    def __init__(self, task: "asyncio.Task[None]") -> None:
        self._task = task

    def __iter__(self) -> "_InterruptedAwait":
        raise KeyboardInterrupt

    __await__ = __iter__

    def cancel(self) -> bool:
        return self._task.cancel()


class _InterruptingAsyncio:
    # The runner's asyncio, its event loop's first task (main()'s booted module) awaited as _InterruptedAwait.
    def __init__(self) -> None:
        self._first = True

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    def get_event_loop(self) -> "_InterruptingAsyncio":
        return self

    def create_task(self, coro: "Coroutine[object, object, None]") -> object:
        task = asyncio.create_task(coro)
        if self._first:
            self._first = False
            return _InterruptedAwait(task)
        return task


def test_an_interrupt_in_the_shutdown_drain_is_let_through() -> None:
    # A per-file timeout's SIGINT landing while main() awaits the cancelled boot ends the run (__main__ then flushes the
    # state): the drain takes only the cancel's own end for its own.
    device = generated_devices()[0]
    config = runner.RunConfig(
        "sensortask_idle",
        f"build/generated_src/sensortask_{device}_wiring_plan.json",
        listen=("127.0.0.1", _PORTS.next()),
        state=StatePaths(None, None, None),
        injections=Injections(None, [], [], []),
        run=runner.RunLimits(0.0, runner._GC_THRESHOLD_DEFAULT, None, None),
        environment=runner.RunEnvironment(_scratch.dir("interrupted"), True, runner._NO_TEST_FLAGS, None),
    )
    sys.modules["sensortask_idle"] = _IdleBoot(f"build/generated_src/sensortask_{device}.py")  # type: ignore[assignment]
    runner.asyncio = _InterruptingAsyncio()  # type: ignore[assignment, attr-defined]  # the runner's module global, rebound from outside
    try:
        run_timed(runner.main(config), timeout_s=_MAIN_RUN_BOUND_S)
        interrupted = False
    except KeyboardInterrupt:
        interrupted = True
    finally:
        runner.asyncio = asyncio  # type: ignore[attr-defined]  # as above
        del sys.modules["sensortask_idle"]
        _flash_stall_installed()
    assert interrupted, "the interrupt was swallowed: a per-file timeout could not end this run"


def test_main_builds_the_booted_module_at_the_debug_level_asked_for() -> None:
    device = generated_devices()[0]
    config = runner.RunConfig(
        "sensortask_idle",
        f"build/generated_src/sensortask_{device}_wiring_plan.json",
        listen=("127.0.0.1", _PORTS.next()),
        state=StatePaths(None, None, None),
        run=runner.RunLimits(0.0, runner._GC_THRESHOLD_DEFAULT, None, None),
        environment=runner.RunEnvironment(_scratch.dir("debug"), True, runner._NO_TEST_FLAGS, 3),
    )
    stand_in = _IdleBoot(f"build/generated_src/sensortask_{device}.py")
    sys.modules["sensortask_idle"] = stand_in  # type: ignore[assignment]
    try:
        run_timed(runner.main(config), timeout_s=_MAIN_RUN_BOUND_S)
    finally:
        del sys.modules["sensortask_idle"]
        _flash_stall_installed()
    assert stand_in.boot.get("debug") == 3, stand_in.boot


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
