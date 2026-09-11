"""Generic digital-twin entry point: boots ANY `sensortask_<device>` module - most usefully a
Session-3 `buildgen.generate.generate_device()`-generated one, written to disk by the caller first
- against a `machine.configure_wiring()`-shaped wiring-plan JSON (produced host-side by
`buildgen.twin_wiring.compute_twin_wiring()`, since this MicroPython process has no tomllib/buildgen
of its own - see BUILD_CHAIN_PLAN.md's Session 5 write-up). `run_wozi_integration.py`/
`run_dev_integration.py` stay unchanged, thin, device-specific wrappers rather than being rewritten
onto this (documented design decision, same write-up) - this file's own fault/hang chip lookup is
the generalized form of their hardcoded `{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}`.
Not a `tests/test_*.py` file - it can serve forever; deliberately lean relative to those two siblings
(no --soak, no default state-persistence paths) since proving a generated module boots and serves
real HTTP is this file's whole job. See `digital_twin/README.md`'s "Swapping the twin in" section."""

import asyncio
import json
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

    import network

import _http_client
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
# same "module-level singleton the interrupted-shutdown path can still reach" shape
# run_wozi_integration.py/run_dev_integration.py get for free from their own static
# `import sensortask_wozi`/`import sensortask_dev`, needed here explicitly since this file's own
# module is only known at runtime (parse_args()'s --module).


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
            f"hangs={self.hangs!r}, wifi_outcomes={self.wifi_outcomes!r}, duration={self.duration!r})"
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
    )


def _collect_chips(module: "Any", plan: "dict[str, Any]") -> "dict[str, Any]":
    # Generalizes run_wozi_integration.py's/run_dev_integration.py's own hardcoded
    # `{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}` dict: walks the same wiring plan
    # configure_wiring() was given, resolving each attachment's own bus variable on the booted
    # module by name instead of a hand-picked i2c0/i2c1 literal. A driver with more than one
    # instance on this device (e.g. tests_scripts/buildgen_fixtures/novel_combo.toml's two scd30s)
    # is reachable unambiguously only via its own "driver_nameext" key - the plain driver-name key
    # still exists too (first instance wins), purely because parse_fault_spec()/parse_hang_spec()
    # (launch.py) only ever speak the plain-driver-name vocabulary and can't address one specific
    # instance among several at all.
    chips: dict[str, Any] = {}
    for bus_name, attachments in plan["buses"].items():
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
    for bus_name, attachment in plan["spi"].items():
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


async def _wait_until_serving(host: str, port: int, timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        while True:
            try:
                await _http_client.fetch(host, port, "GET", "/")
            except OSError:
                await asyncio.sleep_ms(50)
            else:
                return

    await asyncio.wait_for(poll(), timeout_s)


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


async def main(config: RunConfig) -> "dict[str, Any]":
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
        f"scd30_state_path={config.scd30_state_path!r} seed={config.seed!r} duration={config.duration!r} "
        f"faults={config.faults!r} hangs={config.hangs!r} wifi_outcomes={config.wifi_outcomes!r}",
    )

    module = __import__(config.module)
    _booted_module = module
    main_task = asyncio.get_event_loop().create_task(
        module.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port),
    )
    summary: dict[str, Any] = {"failures": []}
    try:
        await _wait_until_built(module)

        assert module.conn is not None and module.watchdog is not None
        chips = _collect_chips(module, plan)
        for device, op, times in config.faults:
            _apply_fault(device, op, times, chips, module.conn.wlan)
        for device, op, seconds, times in config.hangs:
            _apply_hang(device, op, seconds, times, chips)
        if config.wifi_outcomes:
            module.conn.wlan.script_connect_outcomes(config.wifi_outcomes)

        # A queued --hang can fire during setup() (before this point) via a real, blocking
        # time.sleep() that freezes the whole interpreter - the default 10s bound isn't enough to
        # survive that, so it's widened by the total configured hang time whenever any are armed.
        total_hang_s = sum(seconds * times for _device, _op, seconds, times in config.hangs)
        await _wait_until_serving(config.host, config.port, timeout_s=10.0 + total_hang_s)

        if config.duration is None:
            print(f"Serving forever at http://{config.host}:{config.port}/ - Ctrl+C to stop")
            while True:
                await asyncio.sleep(3600)
        elif config.duration > 0:
            await asyncio.sleep(config.duration)
    finally:
        _print_wdt_status(config)
        main_task.cancel()
        try:
            await main_task
        except (asyncio.CancelledError, KeyboardInterrupt):
            # A real SIGINT can be re-delivered while this cleanup await is still in flight - see
            # run_wozi_integration.py's own identical comment. Already shutting down either way.
            pass
        machine.flush_fram()
        machine.flush_scd30()

    return summary


if __name__ == "__main__":
    _config = parse_args(sys.argv[1:])
    _summary: "dict[str, Any] | None" = None
    try:
        _summary = asyncio.run(main(_config))
    except KeyboardInterrupt:
        # See run_wozi_integration.py's own identical comment for the confirmed MicroPython
        # Unix-port asyncio.run()/KeyboardInterrupt gap this works around.
        unwedge_heap_after_interrupt()
        machine.flush_fram()
        machine.flush_scd30()
        _print_wdt_status(_config)
        print("digital_twin/run_generic_integration.py: interrupted")
    if _summary is not None and _summary["failures"]:
        sys.exit(1)
