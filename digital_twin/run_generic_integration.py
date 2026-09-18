"""Generic digital-twin entry point: boots ANY `sensortask_<device>` module - most usefully a Session-3 `buildgen.generate.generate_device()`-generated one, written to disk by the caller first - against a `machine.configure_wiring()`-shaped wiring-plan JSON (produced host-side by `buildgen.twin_wiring.compute_twin_wiring()`, since this MicroPython process has no tomllib/buildgen of its own). Not a `tests/test_*.py` file - it can serve forever.
This file's own fault/hang chip lookup is the generalized form of `run_wozi_integration.py`'s/`run_dev_integration.py`'s hardcoded `{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}`. The soak/memory-trend-check machinery itself moved host-side (`scripts/_digital_twin_ci_suite.py`'s own `_run_11_soak()`, 2026-09-14 - SPECIFICATION.md's "Driver/DUT process separation" Part) - this file's only remaining contribution to that check is `--mem-sample-interval-ms`, an optional background `gc.mem_free()` log-line emitter (see `_mem_sampler()`), the one value that check needs and has no source but this process's own heap.
See `digital_twin/README.md`'s "Booting a generated device" section and SPECIFICATION.md Part L.4/6.2 write-ups for the full design account."""

import asyncio
import gc
import json
import sys
import time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

    import network

import machine
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from launch import (
    _parse_wifi_outcome,  # deliberately reused, not reimplemented - see digital_twin/README.md
    parse_fault_spec,
    parse_hang_spec,
)
from unix_port_gc_unwedge import unwedge_heap_after_interrupt
from unix_port_poll_prewarm import prewarm_poll_set

_CONFIG_DIR = "digital_twin/config/"
_booted_module: "Any | None" = None  # set by main(), read by _print_wdt_status()'s two call sites -
# needed explicitly here since this file's own module is only known at runtime (parse_args()'s
# --module), unlike run_wozi_integration.py/run_dev_integration.py's own static imports.

# Matches buildgen.codegen.generate_boot_entry_source()'s own real-firmware boot entry (same value,
# same one-time placement immediately before asyncio.run()) - the twin sets it too, by default, so a
# non-soak run models production's actual memory-safety configuration, not just its allocation code.
# Overridable via --gc-threshold so the whole suite (scripts/_digital_twin_ci_suite.py's main(), not
# just the soak run) can be driven at MicroPython's own real reactive-only default too -
# CLAUDE.md's/SPECIFICATION.md Part I.4(e)'s standing rule that the whole suite must pass at
# gc.threshold(-1) *before* it's ever run with a chosen threshold, which a single hardcoded
# gc.threshold(32768) here could never be checked against.
_GC_THRESHOLD_DEFAULT = 32768


class RunConfig:
    def __init__(
        self,
        module: str,
        wiring_plan_path: str,
        host: str = "localhost",
        port: int = 8080,
        device: "str | None" = None,
        fram_state_path: "str | None" = None,
        scd30_state_path: "str | None" = None,
        seed: "int | None" = None,
        faults: "list[tuple[str, str, int]] | None" = None,
        hangs: "list[tuple[str, str, float, int]] | None" = None,
        wifi_outcomes: "list[int] | None" = None,
        *,
        duration: "float | None" = None,
        gc_threshold: int = _GC_THRESHOLD_DEFAULT,
        mem_sample_interval_ms: "int | None" = None,
    ) -> None:
        self.module = module
        self.wiring_plan_path = wiring_plan_path
        self.host = host
        self.port = port
        self.device = device if device is not None else module
        self.fram_state_path = fram_state_path
        self.scd30_state_path = scd30_state_path
        self.seed = seed
        self.faults = faults if faults is not None else []
        self.hangs = hangs if hangs is not None else []
        self.wifi_outcomes = wifi_outcomes if wifi_outcomes is not None else []
        self.duration = duration
        self.gc_threshold = gc_threshold
        self.mem_sample_interval_ms = mem_sample_interval_ms

    def __eq__(self, other: "object") -> bool:
        if not isinstance(other, RunConfig):
            return NotImplemented
        return (
            self.module == other.module
            and self.wiring_plan_path == other.wiring_plan_path
            and self.host == other.host
            and self.port == other.port
            and self.device == other.device
            and self.fram_state_path == other.fram_state_path
            and self.scd30_state_path == other.scd30_state_path
            and self.seed == other.seed
            and self.faults == other.faults
            and self.hangs == other.hangs
            and self.wifi_outcomes == other.wifi_outcomes
            and self.duration == other.duration
            and self.gc_threshold == other.gc_threshold
            and self.mem_sample_interval_ms == other.mem_sample_interval_ms
        )

    # Value equality without a matching hash: spell out what CPython already does implicitly for
    # any class defining __eq__, so the intent is explicit rather than inherited by accident - same
    # convention run_wozi_integration.py's own RunConfig already uses.
    __hash__ = None  # type: ignore[assignment]  # mypy has no special case for the standard unhashable-by-__eq__ idiom

    def __repr__(self) -> str:
        return (
            f"RunConfig(module={self.module!r}, wiring_plan_path={self.wiring_plan_path!r}, host={self.host!r}, "
            f"port={self.port!r}, device={self.device!r}, fram_state_path={self.fram_state_path!r}, "
            f"scd30_state_path={self.scd30_state_path!r}, seed={self.seed!r}, faults={self.faults!r}, "
            f"hangs={self.hangs!r}, wifi_outcomes={self.wifi_outcomes!r}, duration={self.duration!r}, "
            f"gc_threshold={self.gc_threshold!r}, mem_sample_interval_ms={self.mem_sample_interval_ms!r})"
        )


def _pop_value(remaining: "list[str]", flag: str) -> str:
    if not remaining:
        raise ValueError(f"{flag} requires a value")
    return remaining.pop(0)


def parse_args(argv: "list[str]") -> RunConfig:
    remaining = list(argv)
    module: str | None = None
    wiring_plan_path: str | None = None
    host = "localhost"
    port = 8080
    device: str | None = None
    fram_state_path: str | None = None
    scd30_state_path: str | None = None
    seed: int | None = None
    faults: list[tuple[str, str, int]] = []
    hangs: list[tuple[str, str, float, int]] = []
    wifi_outcomes: list[int] = []
    duration: float | None = None
    gc_threshold = _GC_THRESHOLD_DEFAULT
    mem_sample_interval_ms: int | None = None

    while remaining:
        arg = remaining.pop(0)
        if arg == "--module":
            module = _pop_value(remaining, arg)
        elif arg == "--wiring-plan":
            wiring_plan_path = _pop_value(remaining, arg)
        elif arg == "--host":
            host = _pop_value(remaining, arg)
        elif arg == "--port":
            port = int(_pop_value(remaining, arg))
        elif arg == "--device":
            device = _pop_value(remaining, arg)
        elif arg == "--fram-state-path":
            value = _pop_value(remaining, arg)
            fram_state_path = value or None  # "" means in-memory only, matches
            # machine.configure_fram_state_path(None)'s own documented meaning.
        elif arg == "--scd30-state-path":
            value = _pop_value(remaining, arg)
            scd30_state_path = value or None  # same "" convention as --fram-state-path above
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
        else:
            raise ValueError(f"unrecognized argument: {arg!r}")

    if module is None:
        raise ValueError("--module is required (the sensortask_<device> module to import and boot)")
    if wiring_plan_path is None:
        raise ValueError("--wiring-plan is required (a JSON file in buildgen.twin_wiring.compute_twin_wiring()'s own shape)")

    return RunConfig(
        module,
        wiring_plan_path,
        host=host,
        port=port,
        device=device,
        fram_state_path=fram_state_path,
        scd30_state_path=scd30_state_path,
        seed=seed,
        faults=faults,
        hangs=hangs,
        wifi_outcomes=wifi_outcomes,
        duration=duration,
        gc_threshold=gc_threshold,
        mem_sample_interval_ms=mem_sample_interval_ms,
    )


def _collect_chips(module: "Any", plan: "dict[str, Any]") -> "dict[str, Any]":
    # Generalizes run_wozi_integration.py's/run_dev_integration.py's own hardcoded
    # `{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}` dict by walking the wiring plan and
    # resolving each attachment's bus variable by name. A driver with more than one instance is also
    # keyed by "driver_nameext" (the plain key still exists too, first instance wins - launch.py's
    # parse_fault_spec()/parse_hang_spec() only ever speak the plain-driver-name vocabulary).
    # sorted(): plan["buses"]/plan["spi"] are plain dicts, and MicroPython dicts do NOT preserve
    # insertion order the way CPython's do (confirmed directly) - sorting by bus name is what makes
    # "first instance wins" above actually mean "i2c0 before i2c1", not MicroPython's hash order.
    chips: dict[str, Any] = {}
    for bus_name, attachments in sorted(plan["buses"].items()):
        bus = getattr(module, bus_name, None)
        if bus is None or bus._i2c is None:
            continue
        for attachment in attachments:
            chip = bus._i2c.devices[attachment["address"]]
            driver = attachment["driver"]
            name_ext = attachment["name_ext"]
            chips.setdefault(driver, chip)
            if name_ext:
                chips[f"{driver}_{name_ext}"] = chip
    for bus_name, attachment in sorted(plan["spi"].items()):
        bus = getattr(module, bus_name, None)
        if bus is None or bus._spi is None:
            continue
        chip = bus._spi.device
        driver = attachment["driver"]
        name_ext = attachment["name_ext"]
        chips.setdefault(driver, chip)
        if name_ext:
            chips[f"{driver}_{name_ext}"] = chip
    return chips


def _apply_fault(device: str, op: str, times: int, chips: "dict[str, Any]", wlan: "network.WLAN") -> None:
    # Same shape as digital_twin/launch.py's own _apply_fault() - reads the real bus objects the
    # booted generated module actually constructed.
    import errno

    message = f"digital_twin/run_generic_integration.py --fault {device}:{op}"
    if device == "wlan":
        wlan.raise_on[op] = OSError(errno.EIO, message)
        return
    chips[device].fault.inject_fault(op, OSError(errno.EIO, message), times=times)


def _apply_hang(device: str, op: str, seconds: float, times: int, chips: "dict[str, Any]") -> None:
    chips[device].fault.inject_hang(op, seconds, times=times)


async def _wait_until_built(module: "Any", timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        # webserver is the last module build_system() assigns before its own grouped await
        # x.setup() batch - see tests/test_digital_twin_sensortask_integration.py's own identical
        # poll for why this (not watchdog, assigned first) is the right readiness signal.
        while getattr(module, "webserver", None) is None:
            await asyncio.sleep_ms(20)

    await asyncio.wait_for(poll(), timeout_s)


def _wire_uart_crossover(module: "Any", plan: "dict[str, Any]") -> "Any | None":
    # Generic, wiring-plan-JSON-driven equivalent of what main's own hand-written
    # run_dev_integration.py used to do by hand (device-name-specific): the bench's permanent
    # crossover jumper. Without it the twin models a dev board whose jumper is missing, and the
    # link exerciser the booted module now starts would spend the whole run timing out instead of
    # moving bytes (SPECIFICATION.md Part A.7/J). A no-op for any device with no "uart" key
    # (buildgen.twin_wiring.compute_twin_wiring() only emits one when the device TOML declares a
    # uart_link initiator/responder pair - wozi never does). Returns the built link (or None) so
    # main() can hold a reference - needed for _wire_log_clearer() below, since the link itself is
    # otherwise unreachable once this returns.
    #
    # Deliberately not inside machine.configure_wiring() itself (the plan this was drafted against
    # first suggested that): configure_wiring() runs BEFORE build_system() constructs anything, but
    # attach_crossover_jumper() needs the two already-built asy_uart_driver.UART wrapper objects'
    # own ._uart machine fakes and .poller attributes - those only exist once this generic entry
    # point's own module (the booted sensortask_<device>) has actually built them, the same reason
    # _collect_chips() below is a post-construction step too, not a pre-construction one.
    uart_plan = plan.get("uart")
    if uart_plan is None:
        return None
    initiator = getattr(module, uart_plan["initiator_var"])
    responder = getattr(module, uart_plan["responder_var"])
    assert initiator is not None and responder is not None
    assert initiator.uart is not None and responder.uart is not None
    assert initiator.uart._uart is not None and responder.uart._uart is not None
    link, poll_a, poll_b = machine.attach_crossover_jumper(initiator.uart._uart, responder.uart._uart)
    initiator.uart.poller = poll_a
    responder.uart.poller = poll_b
    return link


async def _mem_sampler(interval_ms: int) -> None:
    # Optional (--mem-sample-interval-ms, unset by default): the ONE piece of this process a
    # host-side driver genuinely cannot get any other way - gc.mem_free() only exists inside this
    # process's own heap, and deliberately has no REST route (SPECIFICATION.md's "Driver/DUT
    # process separation" Part - every request-driving/response-observing responsibility this file
    # used to also carry, in the now-retired _soak(), moved host-side, to
    # scripts/_digital_twin_ci_suite.py's own _run_11_soak(); this is the one thing that couldn't).
    # Decoupled from any request/response path on purpose, running on its own fixed wall-clock timer
    # rather than once per host-driven cycle - the host has no way to signal "a cycle just finished"
    # into this process without adding exactly the kind of extra channel this design avoids, and a
    # denser, timer-driven sample stream is at least as sensitive to a real trend as a
    # once-per-cycle one. Each line is timestamped (time.time(), the same wall clock the host's own
    # process reads) so the host can select just the samples taken during its own measurement
    # window, the same way it already scrapes watchdog.would_have_triggered_count from this
    # process's own stdout via _print_wdt_status() below - never by calling back into this process.
    # gc.collect() here is measurement instrumentation, not a memory-pressure workaround: it runs on
    # a fixed timer, decoupled from request handling, and cannot mask a real MemoryError (nothing
    # here ever calls into the webserver or a driver) - SPECIFICATION.md Part I.4(e)'s own narrow,
    # already-litigated exception for exactly this reason (verified directly, 2026-09-14: the
    # now-retired in-process _soak() briefly ran without this same gc.collect() and the trend check
    # got measurably worse, not better - min=99808/max=1347104 swings on a genuinely healthy run,
    # a false positive from incidental reactive-GC timing, not from anything this collect() hides).
    while True:
        await asyncio.sleep_ms(interval_ms)
        gc.collect()
        print(f"MEM_SAMPLE {time.time():.3f} {gc.mem_free()}")


_WIRE_LOG_CLEAR_INTERVAL_MS = 5000


async def _wire_log_clearer(link: "Any") -> None:
    # digital_twin/machine.py's UARTLink.wire_log is unbounded by design (SPECIFICATION.md's own
    # documented trap, "Clear it inside any measurement loop") - it exists so a unit test with
    # direct object access can assert exactly what crossed the wire (tests/_uart_link_contract.py's
    # check_wire_log_records_what_was_delivered(), tests/test_asy_uart_comm.py's byte-exact check),
    # and every such test clears it itself between assertions. This process has no such access - it
    # boots the twin as a real subprocess and never reads wire_log at all - so left alone it grows
    # for as long as the crossover link carries traffic (src/asy_uart_link_driver.py's own
    # UartLinkExerciser fires every second, independent of HTTP activity), eventually becoming a
    # genuine, permanently-retained allocation and this process's own memory-safety violation -
    # confirmed directly: this is what made Run 11's gc.mem_free() trend check fail for `dev`
    # (the only device with a wired uart_link pair) while `wozi` (no UART bus at all) stayed flat.
    # Clearing it here changes nothing about the link's real over-the-wire behavior - nothing in
    # this process's own request/response path or asy_uart_comm.py ever reads it back.
    while True:
        await asyncio.sleep_ms(_WIRE_LOG_CLEAR_INTERVAL_MS)
        link.a_to_b.wire_log = bytearray()
        link.b_to_a.wire_log = bytearray()


def _print_wdt_status(config: RunConfig) -> None:
    # See both call sites' own comments in run_wozi_integration.py for why this needs to run from
    # two different places - same reasoning applies here.
    watchdog = getattr(_booted_module, "watchdog", None) if _booted_module is not None else None
    if watchdog is not None:
        print(f"digital_twin/run_generic_integration.py [{config.device}] shutdown: would_have_triggered_count={watchdog.would_have_triggered_count}")


def _ensure_dir(path: str) -> None:
    import os

    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists


async def main(config: RunConfig) -> None:
    global _booted_module
    # Must run before anything else in the process registers a poll object - see
    # unix_port_poll_prewarm.py's own module docstring.
    prewarm_poll_set()
    # Must also run before anything constructs a real AsyUDPSocket (captive_dns.py's DNSServer,
    # asy_ntp_client.py's NTP fetch, asy_dns_client.py's own resolver).
    patch_asy_udp_socket_for_unix_port()
    machine.configure_fram_state_path(config.fram_state_path)
    machine.configure_scd30_state_path(config.scd30_state_path)
    with open(config.wiring_plan_path) as f:
        plan = json.load(f)
    machine.configure_wiring(plan)
    if config.seed is not None:
        import random

        random.seed(config.seed)

    _ensure_dir(_CONFIG_DIR)

    print(
        f"digital_twin/run_generic_integration.py starting - device={config.device!r} module={config.module!r} "
        f"host={config.host!r} port={config.port!r} fram_state_path={config.fram_state_path!r} "
        f"scd30_state_path={config.scd30_state_path!r} seed={config.seed!r} "
        f"duration={config.duration!r} faults={config.faults!r} hangs={config.hangs!r} wifi_outcomes={config.wifi_outcomes!r} "
        f"mem_sample_interval_ms={config.mem_sample_interval_ms!r}",
    )

    module = __import__(config.module)
    _booted_module = module
    main_task = asyncio.get_event_loop().create_task(
        module.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port),
    )
    sampler_task = (
        asyncio.get_event_loop().create_task(_mem_sampler(config.mem_sample_interval_ms))
        if config.mem_sample_interval_ms is not None
        else None
    )
    wire_log_clearer_task = None
    try:
        await _wait_until_built(module)
        uart_link = _wire_uart_crossover(module, plan)
        if uart_link is not None:
            wire_log_clearer_task = asyncio.get_event_loop().create_task(_wire_log_clearer(uart_link))

        assert module.conn is not None and module.watchdog is not None
        chips = _collect_chips(module, plan)
        for device, op, times in config.faults:
            _apply_fault(device, op, times, chips, module.conn.wlan)
        for device, op, seconds, times in config.hangs:
            _apply_hang(device, op, seconds, times, chips)
        if config.wifi_outcomes:
            module.conn.wlan.script_connect_outcomes(config.wifi_outcomes)

        if config.duration is None:
            print(f"Serving forever at http://{config.host}:{config.port}/ - Ctrl+C to stop")
            while True:
                await asyncio.sleep(3600)
        elif config.duration > 0:
            await asyncio.sleep(config.duration)
    finally:
        # SPECIFICATION.md Part F.6 (see its amendment: this project's own Unix-port build now
        # forces safe, deferred SIGINT delivery - Part B.14.1 - so this specific race should no
        # longer be reachable at all; kept as defense in depth, not a load-bearing fix anymore):
        # a SIGINT landing inside gc_collect() can leave the heap permanently locked, and this
        # whole block allocates (f-strings, task bookkeeping, flush_fram()/flush_scd30() below) -
        # unwedge unconditionally, first, exactly like the __main__ except KeyboardInterrupt:
        # handler below does, rather than only there. Before this call existed here, a
        # KeyboardInterrupt landing while THIS coroutine (not a sibling task) was the one running
        # never reached that outer handler until after this block's own allocations had already
        # run against a potentially-locked heap.
        unwedge_heap_after_interrupt()
        _print_wdt_status(config)
        if sampler_task is not None:
            sampler_task.cancel()
        if wire_log_clearer_task is not None:
            wire_log_clearer_task.cancel()
        main_task.cancel()
        try:
            await main_task
        except (asyncio.CancelledError, KeyboardInterrupt):
            # A real SIGINT can be re-delivered while this cleanup await is still in flight.
            # Already shutting down either way; a second wedge from this one is caught by the
            # outer except KeyboardInterrupt: handler's own unwedge call below.
            pass
        if sampler_task is not None:
            try:
                await sampler_task
            except asyncio.CancelledError:
                pass
        if wire_log_clearer_task is not None:
            try:
                await wire_log_clearer_task
            except asyncio.CancelledError:
                pass
        machine.flush_fram()
        machine.flush_scd30()


if __name__ == "__main__":
    _config = parse_args(sys.argv[1:])
    # Placed immediately before asyncio.run(), same as buildgen.codegen.generate_boot_entry_source()'s
    # own real-firmware boot entry - _GC_THRESHOLD_DEFAULT (32768) matches it exactly, so an ordinary
    # twin run models production's real memory-safety configuration, not just its allocation code.
    # --gc-threshold overrides it - scripts/_digital_twin_ci_suite.py's own main() runs the WHOLE
    # suite (not just one run) at both gc.threshold(-1) and gc.threshold(32768), in that order, per
    # SPECIFICATION.md Part I.4(e)'s standing rule that the whole suite must pass clean at the real
    # default before it's ever run again with the project's chosen threshold.
    gc.threshold(_config.gc_threshold)
    try:
        asyncio.run(main(_config))
    except KeyboardInterrupt:
        # Reached when the KeyboardInterrupt lands while main()'s own coroutine is suspended (not
        # currently running) - it never enters main()'s try/finally at all in that case, so this is
        # not just a backstop for a wedge missed above; it is the only cleanup that runs at all for
        # that case. See SPECIFICATION.md Part F.6 (and its amendment - Part B.14.1) for the
        # gc_collect()-heap-lock mechanism and why it's defense in depth now, not the live fix.
        unwedge_heap_after_interrupt()
        machine.flush_fram()
        machine.flush_scd30()
        _print_wdt_status(_config)
        print("digital_twin/run_generic_integration.py: interrupted")
