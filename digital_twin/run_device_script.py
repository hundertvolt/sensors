"""Runs one tests_hardware device script unchanged under the twin, as Board.run_isolated() runs it on silicon: the
device's wiring plan, the one armed watchdog, the requested GC stage. Every instrument passes here before the
hardware queue (scripts/record_twin_instrument_runs.py; tests_hardware/twin_board.py launches it)."""

import gc
import json
import sys

# The fake-free directory beside this runner (the UDP shim), found from the runner's own path: a TwinBoard run works
# from the board's own filesystem directory, not the checkout.
if sys.argv[0].rsplit("/", 1)[0] + "/unixport" not in sys.path:
    sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0] + "/unixport")

import machine
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from launch import _pop_value, _shutdown_cleanup
from unix_port_poll_prewarm import prewarm_poll_set
from unix_port_unretrieved_report import install

_LINE_PREFIX = "digital_twin/run_device_script.py"
_USAGE = "usage: run_device_script.py <wiring-plan.json> <script.py> [--gc-threshold N] [--state-dir DIR]"
# The runner's own exit codes beside the script's: a simulated reset or bootloader entry as the generic runner
# reports them (scripts/_twin_process.py), and a run whose script starved the watchdog silicon would have reset.
_EXIT_SIMULATED_RESET = 3
_EXIT_SIMULATED_BOOTLOADER = 4
_EXIT_WATCHDOG_STARVED = 6
# @tunable wdt.timeout_ms = 8000
_WDT_TIMEOUT_MS = 8000


class _Args:
    def __init__(self, plan: str, script: str, gc_threshold: int, state_dir: "str | None") -> None:
        self.plan = plan
        self.script = script
        self.gc_threshold = gc_threshold
        self.state_dir = state_dir


def _configure_state(state_dir: "str | None") -> None:
    # One directory per board kept across runs, as silicon keeps its FRAM and SCD30 NVM across a reset: a seed script
    # and the verify script that follows it see one chip. Without it every run starts on blank in-memory chips.
    if state_dir is None:
        return
    machine.configure_fram_state_path(state_dir + "/fram.bin")
    machine.configure_scd30_state_path(state_dir + "/scd30.json")
    machine.configure_mem_backup_state_path(state_dir + "/mem_backup.json")


def _attach_jumper(plan: "dict[str, object]") -> None:
    # The bench's permanent UART crossover jumper, as on silicon: a plan naming a UART pair has its two buses joined
    # before the script runs, and UART objects are one per id, so the script's own UART(n) is the jumpered one.
    pair = plan.get("uart")
    if isinstance(pair, dict):
        a, b = (int(str(pair[end])[len("uart") :]) for end in ("initiator_bus", "responder_bus"))
        machine.attach_crossover_jumper(machine.UART(a), machine.UART(b))


def _exit_status(stop: SystemExit) -> int:
    # sys.exit()'s status as CPython reads it: none is 0, an int is itself, anything else is printed and 1. MicroPython's
    # SystemExit carries it in args only (no .code attribute on the Unix port, v1.29.0).
    status = stop.args[0] if stop.args else None
    if status is None or isinstance(status, int):
        return status or 0
    print(status)
    return 1


def _one_watchdog(armed: "machine.WDT") -> None:
    # rp2 keeps one watchdog: a second construction re-enables it with the new timeout (ports/rp2/machine_wdt.c:45-62,
    # v1.29.0). The twin's WDT makes a fresh one per call, so the script gets the armed one back, re-armed.
    def construct(wdt_id: int = 0, timeout: int = 5000) -> "machine.WDT":
        if wdt_id != 0:
            raise ValueError(f"WDT({wdt_id}) doesn't exist")
        armed.timeout = timeout
        armed.feed()
        return armed

    machine.WDT = construct  # type: ignore[assignment, misc]


def _parse(argv: "list[str]") -> "_Args | None":
    # None for -h/--help; a ValueError naming the problem for anything malformed.
    remaining = list(argv)
    positional: list[str] = []
    gc_threshold = -1
    state_dir: str | None = None
    while remaining:
        arg = remaining.pop(0)
        if arg in ("-h", "--help"):
            return None
        if arg == "--gc-threshold":
            gc_threshold = int(_pop_value(remaining, arg))
        elif arg == "--state-dir":
            state_dir = _pop_value(remaining, arg)
        elif arg.startswith("-"):
            raise ValueError(f"unknown option {arg}")
        else:
            positional.append(arg)
    if len(positional) != 2:
        raise ValueError("expected a wiring plan and a script")
    return _Args(positional[0], positional[1], gc_threshold, state_dir)


def main(argv: "list[str]") -> int:
    prewarm_poll_set()  # before anything registers a poll object (unix_port_poll_prewarm.py)
    patch_asy_udp_socket_for_unix_port()  # then before any UDPSocket exists (_unix_port_udp_addr_shim.py)
    install()  # every unretrieved task exception printed, at every DebugLevel (unix_port_unretrieved_report.py)
    try:
        args = _parse(argv)
    except ValueError as e:
        print(f"{_LINE_PREFIX}: {e}\n{_USAGE}")
        return 2
    if args is None:
        print(_USAGE)
        return 0
    with open(args.plan) as f:
        plan = json.load(f)
    machine.configure_wiring(plan)
    _configure_state(args.state_dir)
    _attach_jumper(plan)
    # armed before the script runs, as Board.run_isolated() does; a script constructing WDT again gets this one
    # (ports/rp2/machine_wdt.c:44-61: one static object, re-armed and returned by every construction)
    watchdog = machine.WDT(timeout=_WDT_TIMEOUT_MS)
    _one_watchdog(watchdog)
    with open(args.script) as f:
        source = f.read()
    gc.threshold(args.gc_threshold)
    try:
        # runs the device script by path, as the board runs it; no module is imported
        exec(compile(source, args.script, "exec"), {"__name__": "__main__", "__file__": args.script})
    except SystemExit as e:
        return _exit_status(e)
    except machine.SimulatedRebootError as e:
        bootloader = isinstance(e, machine.SimulatedBootloaderEntryError)
        print(f"{_LINE_PREFIX}: machine reset: kind={'bootloader' if bootloader else 'reset'}")
        return _EXIT_SIMULATED_BOOTLOADER if bootloader else _EXIT_SIMULATED_RESET
    except Exception as e:  # the script's own failure: its traceback, then a failing exit
        sys.print_exception(e)
        return 1
    finally:
        _shutdown_cleanup()
    if watchdog.would_have_triggered_count:
        print(f"{_LINE_PREFIX}: the watchdog would have reset the board {watchdog.would_have_triggered_count} time(s)")
        return _EXIT_WATCHDOG_STARVED
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
