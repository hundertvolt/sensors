"""Generic digital-twin entry point: boots ANY `sensortask_<device>` module - most usefully a Session-3 `buildgen.generate.generate_device()`-generated one, written to disk by the caller first - against a `machine.configure_wiring()`-shaped wiring-plan JSON (produced host-side by `buildgen.twin_wiring.compute_twin_wiring()`, since this MicroPython process has no tomllib/buildgen of its own). Not a `tests/test_*.py` file - it can serve forever.
This file's own fault/hang chip lookup is the generalized form of `run_wozi_integration.py`'s/`run_dev_integration.py`'s hardcoded `{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}`; `--soak`/`--soak-cycles` (Session 6.2) is the same generalization applied to their own soak/memory-trend-check machinery - see `_soak()`'s own comment for the methodology, ported verbatim from `run_wozi_integration.py`.
See `digital_twin/README.md`'s "Booting a generated device" section and BUILD_CHAIN_PLAN.md's Session 5/6.2 write-ups for the full design account."""

import asyncio
import gc
import json
import math
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
# needed explicitly here since this file's own module is only known at runtime (parse_args()'s
# --module), unlike run_wozi_integration.py/run_dev_integration.py's own static imports.

# Ported verbatim from run_wozi_integration.py (BUILD_CHAIN_PLAN.md's Session 6.2 - confirmed by
# direct comparison against run_dev_integration.py's own byte-identical copy that this machinery is
# genuinely device-generic already, not wozi-specific: the same warm-up transient/noise band shows
# up driving either module, since both boot the same shape of real object graph).
_SOAK_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/")
_SOAK_WARMUP_CYCLES = 40
_SOAK_CYCLES_DEFAULT = 20
# _MEM_TREND_*: originally calibrated (run_wozi_integration.py, since retired - its own module
# docstring carried the full account, recovered from git history below since nothing else still
# states it) from five independent 100-cycle soaks - 25-sample first/last quarters - measuring
# trend deltas of +2623, +796, -410, +1729, -116 bytes (positive = memory declined): max magnitude
# 2623, scattered around zero rather than a consistent decline (the evidence against a real leak,
# not the absence of variance). The flat 8192-byte tolerance that produced (~3.1x that magnitude)
# was calibrated for a 25-sample quarter; _SOAK_CYCLES_DEFAULT=20's own 5-sample quarters are
# noisier, a mismatch the original comment already named but never corrected. Harmless while
# digital_twin/_http_client.py's own fetch() called gc.collect() twice per request - that extra,
# unrelated collection incidentally smoothed this measurement too - until removing it (a real fix,
# see that file's own history) let the 20-cycle default's genuine noise floor through: a real CI
# run measured a 9203-byte trend with zero HTTP failures and no leak (confirmed: run_generic_
# integration.py's own soak methodology already rules that out the same way the original
# calibration did). Scaled by quarter size instead of a flat constant - trend is a difference of
# two quarter means, so its standard error scales with 1/sqrt(quarter_size); at the calibration's
# own 25-sample quarters this reduces to exactly the original 8192.
_MEM_TREND_TOLERANCE_BYTES_AT_25_SAMPLES = 8192
# Matches buildgen.codegen.generate_boot_entry_source()'s own real-firmware boot entry (same value,
# same one-time placement immediately before asyncio.run()) - the twin sets it too, by default, so a
# non-soak run models production's actual memory-safety configuration, not just its allocation code.
# Overridable via --gc-threshold specifically so _soak() (the one entry point this file exposes that
# is genuinely a stress/hammer test, not a feature-behavior smoke run) can be driven at MicroPython's
# own real reactive-only default too - CLAUDE.md's/SPECIFICATION.md Part I.4(e)'s standing rule that
# a stress test must pass at gc.threshold(-1) *before* it's ever run with a chosen threshold, which a
# single hardcoded gc.threshold(32768) here could never be checked against. See
# scripts/_digital_twin_ci_suite.py's own Run 11a/11b for where that check actually happens.
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
        soak: bool = False,
        soak_cycles: int = _SOAK_CYCLES_DEFAULT,
        duration: "float | None" = None,
        gc_threshold: int = _GC_THRESHOLD_DEFAULT,
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
        self.soak = soak
        self.soak_cycles = soak_cycles
        self.duration = duration
        self.gc_threshold = gc_threshold

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
            and self.soak == other.soak
            and self.soak_cycles == other.soak_cycles
            and self.duration == other.duration
            and self.gc_threshold == other.gc_threshold
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
            f"hangs={self.hangs!r}, wifi_outcomes={self.wifi_outcomes!r}, soak={self.soak!r}, "
            f"soak_cycles={self.soak_cycles!r}, duration={self.duration!r}, gc_threshold={self.gc_threshold!r})"
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
    soak = False
    soak_cycles = _SOAK_CYCLES_DEFAULT
    duration: float | None = None
    gc_threshold = _GC_THRESHOLD_DEFAULT

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
        elif arg == "--soak":
            soak = True
        elif arg == "--soak-cycles":
            soak_cycles = int(_pop_value(remaining, arg))
            soak = True  # passing a cycle count is itself opting into running the soak
        elif arg == "--duration":
            duration = float(_pop_value(remaining, arg))
        elif arg == "--gc-threshold":
            gc_threshold = int(_pop_value(remaining, arg))
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
        soak=soak,
        soak_cycles=soak_cycles,
        duration=duration,
        gc_threshold=gc_threshold,
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


def _wire_uart_crossover(module: "Any", plan: "dict[str, Any]") -> None:
    # Generic, wiring-plan-JSON-driven equivalent of what main's own hand-written
    # run_dev_integration.py used to do by hand (device-name-specific): the bench's permanent
    # crossover jumper. Without it the twin models a dev board whose jumper is missing, and the
    # link exerciser the booted module now starts would spend the whole run timing out instead of
    # moving bytes (SPECIFICATION.md Part A.7/J). A no-op for any device with no "uart" key
    # (buildgen.twin_wiring.compute_twin_wiring() only emits one when the device TOML declares a
    # uart_link initiator/responder pair - wozi never does).
    #
    # Deliberately not inside machine.configure_wiring() itself (the plan this was drafted against
    # first suggested that): configure_wiring() runs BEFORE build_system() constructs anything, but
    # attach_crossover_jumper() needs the two already-built asy_uart_driver.UART wrapper objects'
    # own ._uart machine fakes and .poller attributes - those only exist once this generic entry
    # point's own module (the booted sensortask_<device>) has actually built them, the same reason
    # _collect_chips() below is a post-construction step too, not a pre-construction one.
    uart_plan = plan.get("uart")
    if uart_plan is None:
        return
    initiator = getattr(module, uart_plan["initiator_var"])
    responder = getattr(module, uart_plan["responder_var"])
    assert initiator is not None and responder is not None
    assert initiator.uart is not None and responder.uart is not None
    assert initiator.uart._uart is not None and responder.uart._uart is not None
    _link, poll_a, poll_b = machine.attach_crossover_jumper(initiator.uart._uart, responder.uart._uart)
    initiator.uart.poller = poll_a
    responder.uart.poller = poll_b


async def _wait_until_serving(host: str, port: int, timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        while True:
            try:
                # read_body=False: only ever checks that the request didn't raise - see fetch()'s
                # own comment for why materializing a body nothing looks at is an avoidable
                # allocation, not a free one.
                await _http_client.fetch(host, port, "GET", "/", read_body=False)
            except (OSError, MemoryError):  # MemoryError isn't an OSError subclass here
                await asyncio.sleep_ms(50)
            else:
                return

    await asyncio.wait_for(poll(), timeout_s)


async def _soak(host: str, port: int, cycles: int) -> "list[str]":
    # Ported verbatim from run_wozi_integration.py's own _soak() (BUILD_CHAIN_PLAN.md's Session
    # 6.2) - deliberately strictly-sequential, see that function's own comment for why (a real
    # MicroPython Unix-port interpreter segfault, found by exceeding WebserverService's own
    # max_connections=4 with concurrent clients; tests/test_digital_twin_webserver_concurrency.py
    # is the project's real regression coverage for that concurrency scale, never this soak).
    failures: list[str] = []
    for _ in range(_SOAK_WARMUP_CYCLES):
        for path in _SOAK_ENDPOINTS:
            try:
                # read_body=False: this loop never reads a response body - see fetch()'s own
                # comment for the real regression found by materializing one nothing looked at
                # (a real MemoryError on the dev device's own, largest frozen website under
                # gc.threshold(-1) - SPECIFICATION.md Part I.4(g)).
                await _http_client.fetch(host, port, "GET", path, read_body=False)
            except (OSError, MemoryError) as e:  # MemoryError isn't an OSError subclass here
                # (CLAUDE.md's platform-facts note) - a real soak run must record a genuine
                # allocation failure as one more failure, never let it crash the whole run
                # uncaught before the summary below ever prints (found via a real CI failure).
                failures.append(f"warmup: GET {path} -> {e!r}")
    # gc.collect() here is measurement instrumentation, not a memory-pressure workaround - it never
    # runs anywhere near a request/response and cannot mask a real MemoryError (every fetch() above
    # already catches and records its own, independently of this). Tried removing it (2026-09-14,
    # auditing c691cb3's own port from run_wozi_integration.py against CLAUDE.md's/SPECIFICATION.md
    # Part I.4(e)'s sharpened rule) and confirmed directly it makes the trend check *worse*, not
    # better: without a settled baseline, gc.mem_free() swings with incidental reactive-GC timing
    # alone (measured on a genuinely healthy wozi run: min=99808, max=1347104 across 20 cycles, a
    # false-positive "trend declined by 413990 bytes" against an 18318-byte tolerance calibrated for
    # the collected regime) - a false failure has no diagnostic value and would train reviewers to
    # ignore this check. Restored: this gc.collect() stabilizes what the *next* line measures, it
    # does not relieve any allocation pressure the fetch() calls above already faced on their own.
    gc.collect()
    mem_samples: list[int] = [gc.mem_free()]  # index 0: post-warmup baseline, excluded from the
    # trend comparison below (it's a single point, not a quarter average).
    for cycle in range(cycles):
        for path in _SOAK_ENDPOINTS:
            try:
                # read_body=False: only res.status_code is ever read below - see fetch()'s own
                # comment and the warmup loop's above for why.
                res = await _http_client.fetch(host, port, "GET", path, read_body=False)
            except (OSError, MemoryError) as e:
                failures.append(f"cycle {cycle}: GET {path} -> {e!r}")
                continue
            if res.status_code != 200:
                failures.append(f"cycle {cycle}: GET {path} -> {res.status_code}")
        gc.collect()  # see the post-warmup baseline's own comment above - same reasoning, per cycle.
        mem_samples.append(gc.mem_free())
    # Trend check - see this file's own _MEM_TREND_* module-level comment for the full methodology
    # and why the tolerance below is scaled, not flat. Needs at least 4 per-cycle samples
    # (cycles >= 4) for the quarters to mean anything; skipped below that (a --soak-cycles this
    # small is a manual smoke run).
    per_cycle_samples = mem_samples[1:]
    quarter = len(per_cycle_samples) // 4
    if quarter >= 1:
        early = per_cycle_samples[:quarter]
        late = per_cycle_samples[-quarter:]
        early_avg = sum(early) / len(early)
        late_avg = sum(late) / len(late)
        trend = early_avg - late_avg  # positive: memory declined between quarters
        # trend's own standard error scales with 1/sqrt(quarter_size) (it's a difference of two
        # quarter means) - this reduces to exactly the original flat constant at the calibration's
        # own 25-sample quarters, and widens correctly for a smaller/noisier one instead of
        # silently re-applying a tolerance measured at a different sample size.
        tolerance = _MEM_TREND_TOLERANCE_BYTES_AT_25_SAMPLES * math.sqrt(25 / quarter)
        print(
            f"digital_twin/run_generic_integration.py memory trend: baseline={mem_samples[0]} "
            f"min={min(per_cycle_samples)} max={max(per_cycle_samples)} early_avg={early_avg:.0f} "
            f"late_avg={late_avg:.0f} trend={trend:.0f} tolerance={tolerance:.0f} "
            f"quarter_size={quarter} samples={len(per_cycle_samples)}",
        )
        if trend > tolerance:
            failures.append(
                f"gc.mem_free() trend declined by {trend:.0f} bytes (early_avg={early_avg:.0f} -> "
                f"late_avg={late_avg:.0f}) over {cycles} cycles, exceeding the "
                f"{tolerance:.0f}-byte tolerance (quarter_size={quarter})",
            )
    return failures


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
        f"scd30_state_path={config.scd30_state_path!r} seed={config.seed!r} soak_cycles={config.soak_cycles!r} "
        f"duration={config.duration!r} faults={config.faults!r} hangs={config.hangs!r} wifi_outcomes={config.wifi_outcomes!r}",
    )

    module = __import__(config.module)
    _booted_module = module
    main_task = asyncio.get_event_loop().create_task(
        module.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port),
    )
    summary: dict[str, Any] = {"failures": [], "would_have_triggered_count": 0}
    try:
        await _wait_until_built(module)
        _wire_uart_crossover(module, plan)

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

        if config.soak:
            failures = await _soak(config.host, config.port, config.soak_cycles)
            if module.watchdog.would_have_triggered_count != 0:
                failures.append(f"watchdog would have triggered {module.watchdog.would_have_triggered_count} time(s)")

            summary = {
                "soak_cycles": config.soak_cycles,
                "failures": failures,
                "would_have_triggered_count": module.watchdog.would_have_triggered_count,
            }
            print(f"digital_twin/run_generic_integration.py [{config.device}] soak summary:", summary)
            if failures:
                for failure in failures:
                    print("FAIL:", failure)
            else:
                print(f"PASS - {config.soak_cycles} soak cycles across every endpoint, watchdog never starved")

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
    # Placed immediately before asyncio.run(), same as buildgen.codegen.generate_boot_entry_source()'s
    # own real-firmware boot entry - _GC_THRESHOLD_DEFAULT (32768) matches it exactly, so an ordinary
    # (non-soak) twin run models production's real memory-safety configuration, not just its
    # allocation code. --gc-threshold overrides it, which is what actually matters here: the real
    # fix for PR #80's Run 11 MemoryError (repeated ~6-7.5KB `allocating N bytes` failures on GET /
    # and GET /status during _soak()) was digital_twin/_http_client.py's own _read_exact()/
    # _read_until_close() replacing Stream.readexactly()/read(-1)'s growth-by-concatenation
    # accumulation with one right-sized buffer per fetch() (see that file's own history) - not this
    # threshold. Verified directly: _soak() passes clean at gc.threshold(-1) (MicroPython's real
    # reactive-only default, no proactive collection at all) with those two fixes in place and no
    # threshold change whatsoever, matching SPECIFICATION.md Part I.4(e)'s standing rule that a
    # stress test must prove this *before* it's ever run with a chosen threshold - a rule an earlier
    # version of this comment (2026-09-13) violated by treating "the twin never set gc.threshold(32768)"
    # itself as the root cause. Kept at 32768 by default anyway, same as every real boot: I.4(f) - a
    # threshold is defense in depth on top of an already-safe design, never the fix for one that still
    # needs it. scripts/_digital_twin_ci_suite.py's Run 11a/11b exercise both configurations.
    gc.threshold(_config.gc_threshold)
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
