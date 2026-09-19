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

# The same value and one-time placement the real firmware boot entry uses, so a twin run models
# production's memory-safety configuration and not just its allocation code. --gc-threshold
# overrides it, since Part I.4(e) requires the whole suite to pass at -1 first.
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
    # Generalizes the retired entry points' hardcoded device dicts by walking the wiring plan.
    # A multi-instance driver is also keyed "driver_nameext"; the plain key stays, first instance
    # winning, since the fault vocabulary only speaks plain driver names.

    # sorted() because MicroPython dicts do not preserve insertion order as CPython's do, so
    # sorting by bus name is what makes "first instance wins" mean i2c0 before i2c1.
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
    _require_wired(device, chips)
    chips[device].fault.inject_fault(op, OSError(errno.EIO, message), times=times)


def _apply_hang(device: str, op: str, seconds: float, times: int, chips: "dict[str, Any]") -> None:
    _require_wired(device, chips)
    chips[device].fault.inject_hang(op, seconds, times=times)


def _require_wired(device: str, chips: "dict[str, Any]") -> None:
    # Being in launch.py's shared op vocabulary only says the NAME is spelled right; whether the
    # chip exists depends on this device's own TOML (bmp3xx is wozi/dev-only, isl29125 dev-only).
    # A bare KeyError here would name neither the device nor what was actually wired.
    if device not in chips:
        raise ValueError(f"--fault/--hang device {device!r} is not wired on this device - wired here: {sorted(chips)}")


async def _wait_until_built(module: "Any", timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        # webserver is the last module build_system() assigns before its own grouped await
        # x.setup() batch - see tests/test_digital_twin_sensortask_integration.py's own identical
        # poll for why this (not watchdog, assigned first) is the right readiness signal.
        while getattr(module, "webserver", None) is None:
            await asyncio.sleep_ms(20)

    await asyncio.wait_for(poll(), timeout_s)


def _wire_uart_crossover(module: "Any", plan: "dict[str, Any]") -> "Any | None":
    # The wiring-plan-driven equivalent of what the retired per-device entry point did by hand:
    # the bench's permanent crossover jumper. Without it the twin models a dev board whose jumper
    # is missing, and the exerciser spends the run timing out instead of moving bytes (Part J).

    # A no-op for a device with no "uart" key, which only a declared initiator/responder pair
    # produces. Returns the built link so main() can hold a reference for _wire_log_clearer(),
    # which has no other way to reach it.

    # Not inside machine.configure_wiring(), which runs BEFORE anything is constructed: the
    # jumper needs the two built UART wrappers' own fakes and pollers, which exist only once the
    # booted module has made them - the same reason _collect_chips() is post-construction too.
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
    # Optional (--mem-sample-interval-ms): the one thing a host-side driver cannot get any other
    # way, gc.mem_free() living in this heap with no REST route. Fixed timer, timestamped lines,
    # and an instrumentation-only gc.collect() - README.md has the reasoning and measurement.
    while True:
        await asyncio.sleep_ms(interval_ms)
        gc.collect()
        print(f"MEM_SAMPLE {time.time():.3f} {gc.mem_free()}")


_WIRE_LOG_CLEAR_INTERVAL_MS = 5000


async def _wire_log_clearer(link: "Any") -> None:
    # UARTLink.wire_log is unbounded by design, and nothing in this process ever reads it, so
    # left alone it grows for as long as the link carries traffic - which is what made Run 11's
    # trend check fail for `dev` and not `wozi`. README.md's own section has the account.
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
        # Part F.6, defense in depth now that Part B.14.1 forces safe SIGINT delivery: an
        # interrupt inside gc_collect() can leave the heap locked, and this whole block
        # allocates, so unwedge first rather than only in the outer handler.

        # Before this call existed here, an interrupt landing while THIS coroutine was running
        # reached that outer handler only after these allocations had already run.
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
    # Immediately before asyncio.run(), where the real firmware boot entry also sets it, so an
    # ordinary twin run models production's configuration. --gc-threshold overrides it: the CI
    # suite runs the WHOLE suite at -1 and then at 32768, in that order (Part I.4(e)).
    gc.threshold(_config.gc_threshold)
    try:
        asyncio.run(main(_config))
    except KeyboardInterrupt:
        # Reached when the interrupt lands while main()'s coroutine is suspended: it never
        # enters main()'s try/finally then, so this is the only cleanup that runs at all, not a
        # backstop for a wedge missed above. Part F.6 has the mechanism.
        unwedge_heap_after_interrupt()
        machine.flush_fram()
        machine.flush_scd30()
        _print_wdt_status(_config)
        print("digital_twin/run_generic_integration.py: interrupted")
