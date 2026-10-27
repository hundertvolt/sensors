"""Digital-twin tier of the boot entry's loop-end record for the device named by TEST_DEVICE: its generated main.py run
over the device's real graph on the twin, an exception made to leave the loop, the starved watchdog's reset applied,
then the next boot's GET /status ResetReason (SPECIFICATION.md A.7, F.5.4); Part E.2.1 has the per-device split."""

import asyncio
import asyncio.core as _core  # type: ignore[import-not-found]  # the loop's own queue and cur_task; no stub covers them
import errno
import os
import sys

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

PER_DEVICE = True
_device = os.getenv("TEST_DEVICE")
if not _device:
    raise RuntimeError("run through scripts/test.sh, or set TEST_DEVICE to one of devices/*.toml")
device: str = _device

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_int  # noqa: E402 - imported after the prewarm and the UDP shim
from _strict_json import strict_loads  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import distinct_wirings, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import ModuleType
    from typing import TypeVar, cast

    from launch import _Plan

    T = TypeVar("T")

else:

    def cast(_typ: object, val: "T") -> "T":  # no typing module on MicroPython: the identity at run time
        return val


_SRC = "src/asy_system_service.py"
_BOOT_DONE = src_int(_SRC, "BOOT_DONE")
_BOOT_SETUP = src_int(_SRC, "BOOT_SETUP")
_TIMER_BIT, _FORCED_BIT = 0x1, 0x2  # ResetBits' watchdog half: REASON TIMER and FORCE
_HAD_POR_BIT = 0x100  # ResetBits' CHIP_RESET HAD_POR: power-on or brown-out
# @tunable l2.loop_end_boot_limit_ms = 20000
_BOOT_LIMIT_MS = 20000  # a boot past it is a failure of its own, never a planted fault
# @tunable l2.loop_end_run_timeout_s = 30.0
_RUN_TIMEOUT_S = 30.0
_POLL_MS = 5

_scratch = TmpScratch(f"dtle_{device}")
_ports = PortAllocator("test_digital_twin_loop_end", device)


class _BootTimeoutError(BaseException):
    # The watcher's own end when the boot never reached the planted phase: told apart from every planted fault.
    pass


class _Plant:
    # The device module as the boot entry sees it: main() runs the real one under the test's config and port, beside a
    # watcher that drives the clock until the boot-phase mark reaches `phase`, then plants `kind` (the loop core's next
    # wait, or the watcher).
    def __init__(self, module: "ModuleType", cfg_path: str, kind: str, phase: int, clock: DrivenTime) -> None:
        self.module, self.cfg_path, self.kind, self.phase, self.clock = module, cfg_path, kind, phase, clock
        self.watchdog: machine.WDT | None = None
        self.interrupt = KeyboardInterrupt()
        self.raised_in_phase = 0
        self.watcher: asyncio.Task[None] | None = None

    async def main(self, *, watchdog: "machine.WDT") -> None:
        self.watchdog = watchdog
        self.watcher = asyncio.create_task(self._watch())
        await self.module.main(watchdog=watchdog, cfg_path=self.cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=_ports.next())

    async def _watch(self) -> None:
        await _wired(self.module)
        phase = machine.mem_backup(1)
        for _ in range(_BOOT_LIMIT_MS // _POLL_MS):
            if self.phase <= phase[1] <= _BOOT_DONE and (self.phase == _BOOT_DONE) == (phase[1] == _BOOT_DONE):
                break
            await self.clock.elapse(_POLL_MS)
        else:
            raise _BootTimeoutError
        self.raised_in_phase = phase[1]
        if self.kind == "core":
            _core._io_queue.wait_io_event = self._failing_wait  # the scheduler's own poll, outside every task
        elif self.kind == "interrupt":
            raise self.interrupt
        else:
            raise SystemExit(3)  # a non-Exception BaseException out of a task: asyncio's loop does not catch it

    def _failing_wait(self, _dt: int) -> None:
        raise OSError(errno.EIO)


class _EntryRuntime:
    # The entry's `gc` and `micropython`: recorded only, so the run keeps the suite's GC stage, and this Unix port has no
    # emergency exception buffer to reserve.
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def alloc_emergency_exception_buf(self, size: int) -> None:
        self.calls.append(("buffer", size))

    def threshold(self, value: int) -> None:
        self.calls.append(("threshold", value))


async def _wired(module: "ModuleType") -> None:
    # The runner's steps once the graph is built: a UART link's bounded pollers, as on CI (the plan crosses by a cast).
    await run_generic_integration._wait_until_built(module)
    plan: _Plan = cast("_Plan", wiring_plan(device))
    run_generic_integration._wire_uart_crossover(module, plan)


def _fresh_board() -> "ModuleType":
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(wiring_plan(device))
    return load_device(device)


def _cfg_dir(label: str) -> str:
    path = _scratch.dir(label)
    write_offline_ntp_config(path)
    write_error_level_config(path)
    return path


def _run_entry(plant: _Plant) -> "BaseException | None":
    # Executes the device's generated main.py from this synchronous scope with the plant as its device module; what
    # leaves it comes back. The ended loop leaves cur_task set, which no later loop on silicon ever sees.
    path = f"build/generated_src/sensortask_{device}_main.py"
    with open(path) as f:
        code = compile(f.read(), path, "exec")
    names = (f"sensortask_{device}", "gc", "micropython")
    saved = {name: sys.modules.get(name) for name in names}
    saved_path, runtime = sys.path[:], _EntryRuntime()
    sys.modules.update({names[0]: plant, names[1]: runtime, names[2]: runtime})  # type: ignore[dict-item]  # stand-ins for the modules
    try:
        exec(code, {"__name__": "__main__"})  # noqa: S102 - the generated entry, run as rp2 runs its frozen main.py
    except BaseException as e:  # what escapes the entry is the observation
        if e is not plant.interrupt:
            raise  # an interrupt the plant did not raise is the per-file timeout's: it ends the run
        return e
    finally:
        asyncio.new_event_loop()  # the entry's own finally already did, unless it failed before its loop
        _core.cur_task = None
        sys.path[:] = saved_path
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    return None


async def _status(port: int) -> "dict[str, object]":
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        writer.write(b"GET /status HTTP/1.0\r\n\r\n")
        await writer.drain()
        raw = b""
        while True:
            chunk = await reader.read(512)
            if not chunk:
                break
            raw += chunk
    finally:
        writer.close()
        await writer.wait_closed()
    body = strict_loads(raw.split(b"\r\n\r\n", 1)[1])
    system = body.get("system") if isinstance(body, dict) else None
    assert isinstance(system, dict), raw
    return system


def _next_boot_reads(cfg_path: str) -> "dict[str, object]":
    # The boot after the watchdog's reset, on a new board: driven to its last phase, then on the real clock (the request,
    # its server and the teardown on the loop's own), its /status system block once it serves.
    async def scenario(clock: DrivenTime) -> "dict[str, object]":
        module = _fresh_board()
        module.__dict__["webserver"] = None  # the global the runner's wait reads: this boot's, not the ended one's
        port = _ports.next()
        main_task = asyncio.create_task(module.main(watchdog=machine.WDT(timeout=8000), cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=port))
        try:
            await _wired(module)
            phase = machine.mem_backup(1)
            try:
                await clock.run_until(lambda: phase[1] == _BOOT_DONE, _BOOT_LIMIT_MS)
            except AssertionError as e:
                raise AssertionError(f"the next boot never reached its last phase - {e}") from None
            finally:
                clock.release()
            for _ in range(_BOOT_LIMIT_MS // _POLL_MS):
                try:
                    return await _status(port)
                except OSError:  # not serving yet
                    await asyncio.sleep_ms(_POLL_MS)
            raise AssertionError("the next boot never served /status")
        finally:
            await cancel(main_task)

    with DrivenTime(*_driven_modules(), sleeps=True) as clock:
        return run_timed(scenario(clock), timeout_s=_RUN_TIMEOUT_S)


def _case(kind: str, phase: int, reset: str = "watchdog") -> "tuple[_Plant, BaseException | None, dict[str, object]]":
    # One ended run from power-on and the boot after the starved watchdog's reset (cause WDT_RESET, REASON TIMER), after a
    # console soft reset (no hard reset: the power-on's cause and both regions kept) or after a power cycle (both cleared).
    machine.power_on()
    cfg_path = _cfg_dir(kind + str(phase) + reset)
    module = _fresh_board()
    with DrivenTime(*_driven_modules(), sleeps=True) as clock:  # the boot's waits, on the clock the watcher drives
        plant = _Plant(module, cfg_path, kind, phase, clock)
        escaped = _run_entry(plant)
    assert plant.raised_in_phase, f"the boot never reached phase {phase}"
    assert plant.watchdog is not None and plant.watchdog.timeout == 8000, plant.watchdog
    if reset == "watchdog":
        plant.watchdog._record_would_trigger()  # the armed watchdog, fed by no one once the entry has ended
        machine.reset_cause_value = machine.WDT_RESET
    elif reset == "power":
        machine.power_on()
    return plant, escaped, _next_boot_reads(cfg_path)


def _driven_modules() -> "list[object]":
    # Every src module holding asyncio and the twin's machine and network: one clock for each sleep and tick read.
    return [m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio]


def _per_distinct_wiring() -> None:
    # The record is written and read beside the device's whole booted graph: a class runs once per distinct wiring of
    # every instance a device wires (SPECIFICATION.md E.2.1), devices wired identically sharing the first one's run.
    chosen = distinct_wirings()
    if device not in chosen:
        raise microtest.Skip(f"runs on {chosen}, one device per distinct wiring of every instance")


def _watchdog_bits(system: "dict[str, object]") -> int:
    bits = system.get("ResetBits")
    assert isinstance(bits, int) and bits & _TIMER_BIT and not bits & _FORCED_BIT, system
    return bits


def _power_on_bits(system: "dict[str, object]") -> None:
    # No watchdog reset since the power-on: REASON reads neither TIMER nor FORCE, CHIP_RESET keeps HAD_POR.
    bits = system.get("ResetBits")
    assert isinstance(bits, int) and bits & _HAD_POR_BIT and not bits & (_TIMER_BIT | _FORCED_BIT), system


def test_a_loop_core_failure_after_boot_reads_22_at_the_next_boot() -> None:
    _plant, escaped, system = _case("core", _BOOT_DONE)
    assert escaped is None, escaped  # recorded and printed, never re-raised
    assert system.get("ResetReason") == 22, system
    _watchdog_bits(system)


def test_a_non_exception_raised_in_a_task_after_boot_reads_22() -> None:
    _per_distinct_wiring()
    _plant, escaped, system = _case("task", _BOOT_DONE)
    assert escaped is None, escaped  # a SystemExit too, which rp2 would turn into a soft reset
    assert system.get("ResetReason") == 22, system
    _watchdog_bits(system)


def test_a_loop_ended_during_boot_reads_10_plus_its_phase() -> None:
    _per_distinct_wiring()
    plant, escaped, system = _case("core", _BOOT_SETUP)
    assert escaped is None, escaped
    assert _BOOT_SETUP <= plant.raised_in_phase < _BOOT_DONE, plant.raised_in_phase
    assert system.get("ResetReason") == src_int(_SRC, "_RR_BOOT_FAILURE") + plant.raised_in_phase, system
    _watchdog_bits(system)


def test_a_console_interrupt_after_boot_still_reads_21() -> None:
    _per_distinct_wiring()
    plant, escaped, system = _case("interrupt", _BOOT_DONE)
    assert escaped is plant.interrupt, escaped  # recorded with its own code and re-raised to the REPL
    assert system.get("ResetReason") == src_int(_SRC, "RR_INTERRUPTED"), system
    _watchdog_bits(system)


def test_a_console_soft_reset_after_ctrl_c_reads_21() -> None:
    # Ctrl-D at the REPL inside the watchdog window re-runs main.py after a power-on boot: the recorded 21 is read.
    _per_distinct_wiring()
    plant, escaped, system = _case("interrupt", _BOOT_DONE, "soft")
    assert escaped is plant.interrupt, escaped
    assert system.get("ResetReason") == src_int(_SRC, "RR_INTERRUPTED"), system
    _power_on_bits(system)


def test_a_console_soft_reset_after_a_loop_end_reads_22() -> None:
    _per_distinct_wiring()
    _plant, escaped, system = _case("core", _BOOT_DONE, "soft")
    assert escaped is None, escaped
    assert system.get("ResetReason") == 22, system
    _power_on_bits(system)


def test_a_console_soft_reset_after_a_loop_ended_during_boot_reads_10_plus_its_phase() -> None:
    # No record during boot: the soft reset's boot reads the phase marker it kept, though the cause is the power-on's.
    _per_distinct_wiring()
    plant, escaped, system = _case("core", _BOOT_SETUP, "soft")
    assert escaped is None, escaped
    assert _BOOT_SETUP <= plant.raised_in_phase < _BOOT_DONE, plant.raised_in_phase
    assert system.get("ResetReason") == src_int(_SRC, "_RR_BOOT_FAILURE") + plant.raised_in_phase, system
    _power_on_bits(system)


def test_a_power_cycle_after_ctrl_c_reads_1() -> None:
    _per_distinct_wiring()
    plant, escaped, system = _case("interrupt", _BOOT_DONE, "power")
    assert escaped is plant.interrupt, escaped
    assert system.get("ResetReason") == src_int(_SRC, "_RR_POWER_ON"), system
    _power_on_bits(system)


microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
