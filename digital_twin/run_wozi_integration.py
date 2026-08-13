"""End-to-end entry point for FINAL_WIRING_PLAN.md's Step 5 - "full Unix-port integration": boots
the real src/sensortask_wozi.py object graph (build_system()/main(), unchanged - zero
twin-awareness anywhere in src/) against the real digital_twin buses, then drives real HTTP traffic
against the real, real-socket asyncio.start_server()-backed WebserverService (owner decision 2:
"full HTTP, real sockets, real server", the same as the real system - never
app.dispatch_request() bypass, which tests/test_sensortask_wozi.py's own suite already covers
without a twin, and tests/test_digital_twin_sensortask_integration.py's own middle tier now covers
against the twin too). Deliberately not a tests/test_*.py file and not run by scripts/test.sh's
own default loop: unlike that middle tier (which only ever starts the one task a given test needs,
see that file's own module docstring), this module always runs the real, full
start_and_check_tasks() supervisor for real, optionally forever (a bare
--duration-omitted run just keeps serving so a real browser on this machine can hit
http://<host>:<port>/ - owner decision 3) - a `tests/test_*.py` name would make scripts/test.sh's
own glob loop pick this up and hang it. Invoked via scripts/run_unix_port_integration.sh, which
sets the twin-only MICROPYPATH ("src:digital_twin:frozen_modules:.frozen" - never combined with a
"tests" segment, digital_twin/README.md's own "never together" rule) this module needs.

Reuses digital_twin/launch.py's own parse_fault_spec()/_parse_wifi_outcome() directly (same
device/op/wifi-outcome vocabulary a fault-injecting flag on *this* module needs - owner decision 7:
"I want it to be unit tested, and see it if it happens on a manual run", so --fault/--wifi-outcome
stay available for deliberate manual exploration) rather than reimplementing them - launch.py's own
module docstring already anticipated this ("Step 5's own entry point is expected to reuse
parse_args()/main() the same way").

FRAM/config persistence default to a fixed, persistent location inside digital_twin/ (owner decision
6: "why not a persistent file inside the digital twin dir? Only written when really shutting down,
in memory only during interpreter runtime") - _config_dir()/RunConfig's own fram_state_path default,
both gitignored build/run artifacts, never committed. This is deliberately different from
tests/test_digital_twin_sensortask_integration.py's own per-test ephemeral-state convention, which
stays that way for its own reasons (see that file's own module docstring).

The soak loop (owner decisions 4/9): real HTTP round trips fired back-to-back against every real
endpoint, not gated by the twin's own real-time sensor-poll Timer cadence (which keeps running
concurrently and unaffected in the background, at real intervals, exactly like the real system) -
"everything is supposed to be async... it should run realtime on the server interface". Reuses Step
2's own exact memory-flat methodology and tolerance (tests/test_asy_webserver_service.py's F.9:
gc.collect() -> baseline -> N cycles -> gc.collect() -> assert after >= baseline - 4096) - owner
decision 9, "reuse step 2" - applied here to the real end-to-end object graph instead of Step 2's
own fake reader/writer.
"""

import asyncio
import gc
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

import _http_client
import machine
from launch import (
    _parse_wifi_outcome,  # deliberately reused, not reimplemented - see module docstring
    parse_fault_spec,  # noqa: F401 - re-exported for callers that only need the spec parser
)

import sensortask_wozi

_DEFAULT_FRAM_STATE_PATH = "digital_twin/fram_state.json"
_CONFIG_DIR = "digital_twin/config/"
_SOAK_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/")
_MEM_FLAT_TOLERANCE_BYTES = 4096  # identical to tests/test_asy_webserver_service.py's own F.9 tolerance (owner decision 9)
_SOAK_WARMUP_CYCLES = 40  # FINAL_WIRING_PLAN.md's Step 5 baseline-verification pass found the
# original 2-cycle warm-up (Step 2's own F.9 convention, copied verbatim) isn't enough for *this*
# soak: unlike F.9's fake reader/writer, this soak drives the real object graph, where every
# settings GET re-reads and re-parses its config file from disk (ConfigManager's own per-call
# design). A 100-cycle diagnostic run showed gc.mem_free() drop ~52KB over the first 30 cycles, then
# settle into a noisy +-15KB band for the remaining 70 - a real, bounded, converging warm-up
# transient, not an unbounded leak (confirmed: no crash/no would-have-triggered watchdog event
# across the full 100 cycles either). 40 cycles clears the steepest part of it - real runs now fail
# by ~7KB instead of the original ~32KB - but not all the way inside _MEM_FLAT_TOLERANCE_BYTES's
# tight 4096-byte budget: doubling the warm-up from 20->40 barely moved the residual (6.7KB vs
# 7.9KB), pointing at ordinary steady-state allocator noise rather than a residual transient more
# warm-up would burn off. Whether 4096 bytes is tight enough for this real object graph's natural
# noise (as opposed to Step 2's synthetic fake-based F.9 test that value was copied from) is a real,
# open question flagged to the project owner rather than silently resolved by loosening it here -
# the tolerance itself was an explicit owner decision ("reuse step 2") this fix deliberately leaves
# alone.


class RunConfig:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        fram_state_path: "str | None" = _DEFAULT_FRAM_STATE_PATH,
        seed: "int | None" = None,
        faults: "list[tuple[str, str, int]] | None" = None,
        wifi_outcomes: "list[int] | None" = None,
        soak_cycles: int = 20,
        duration: "float | None" = None,
    ) -> None:
        self.host = host
        self.port = port
        self.fram_state_path = fram_state_path
        self.seed = seed
        self.faults = faults if faults is not None else []
        self.wifi_outcomes = wifi_outcomes if wifi_outcomes is not None else []
        self.soak_cycles = soak_cycles
        self.duration = duration

    def __eq__(self, other: "object") -> bool:
        if not isinstance(other, RunConfig):
            return NotImplemented
        return (
            self.host == other.host
            and self.port == other.port
            and self.fram_state_path == other.fram_state_path
            and self.seed == other.seed
            and self.faults == other.faults
            and self.wifi_outcomes == other.wifi_outcomes
            and self.soak_cycles == other.soak_cycles
            and self.duration == other.duration
        )

    def __repr__(self) -> str:
        return (
            f"RunConfig(host={self.host!r}, port={self.port!r}, fram_state_path={self.fram_state_path!r}, "
            f"seed={self.seed!r}, faults={self.faults!r}, wifi_outcomes={self.wifi_outcomes!r}, "
            f"soak_cycles={self.soak_cycles!r}, duration={self.duration!r})"
        )


def _pop_value(remaining: "list[str]", flag: str) -> str:
    if not remaining:
        raise ValueError(f"{flag} requires a value")
    return remaining.pop(0)


def parse_args(argv: "list[str]") -> RunConfig:
    remaining = list(argv)
    host = "localhost"
    port = 8080
    fram_state_path: str | None = _DEFAULT_FRAM_STATE_PATH
    seed: int | None = None
    faults: list[tuple[str, str, int]] = []
    wifi_outcomes: list[int] = []
    soak_cycles = 20
    duration: float | None = None

    while remaining:
        arg = remaining.pop(0)
        if arg == "--host":
            host = _pop_value(remaining, arg)
        elif arg == "--port":
            port = int(_pop_value(remaining, arg))
        elif arg == "--fram-state-path":
            value = _pop_value(remaining, arg)
            fram_state_path = value if value else None  # "" means in-memory only, matches
            # machine.configure_fram_state_path(None)'s own documented meaning.
        elif arg == "--seed":
            seed = int(_pop_value(remaining, arg))
        elif arg == "--fault":
            faults.append(parse_fault_spec(_pop_value(remaining, arg)))
        elif arg == "--wifi-outcome":
            wifi_outcomes.append(_parse_wifi_outcome(_pop_value(remaining, arg)))
        elif arg == "--soak-cycles":
            soak_cycles = int(_pop_value(remaining, arg))
        elif arg == "--duration":
            duration = float(_pop_value(remaining, arg))
        else:
            raise ValueError(f"unrecognized argument: {arg!r}")

    return RunConfig(
        host=host,
        port=port,
        fram_state_path=fram_state_path,
        seed=seed,
        faults=faults,
        wifi_outcomes=wifi_outcomes,
        soak_cycles=soak_cycles,
        duration=duration,
    )


def _apply_fault(device: str, op: str, times: int, chips: "dict[str, Any]", wlan: "Any") -> None:
    # Same shape as digital_twin/launch.py's own _apply_fault() - reads the real bus objects
    # sensortask_wozi.build_system() actually constructed rather than launch.py's own local vars.
    import errno

    message = f"digital_twin/run_wozi_integration.py --fault {device}:{op}"
    if device == "wlan":
        wlan.raise_on[op] = OSError(errno.EIO, message)
        return
    chips[device].fault.inject_fault(op, OSError(errno.EIO, message), times=times)


async def _wait_until_built(timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        # webserver is the last module build_system() assigns before its own grouped await
        # x.setup() batch - see tests/test_digital_twin_sensortask_integration.py's own identical
        # poll for why this (not watchdog, assigned first) is the right readiness signal.
        while sensortask_wozi.webserver is None:
            await asyncio.sleep_ms(20)

    await asyncio.wait_for(poll(), timeout_s)


async def _wait_until_serving(host: str, port: int, timeout_s: float = 10.0) -> None:
    # webserver being constructed (waited for above) only means build_system() finished - the real
    # socket doesn't actually bind until sensortask_wozi.main()'s own start_and_check_tasks()
    # reaches the webserver's own task starter, which can be delayed by up to
    # len(task_starters)-1 * its own per-starter stagger (system_service.py's own startup loop) -
    # confirmed directly (a fixed post-build sleep alone raced ECONNREFUSED here). Retrying the
    # real connection is simpler and more robust than trying to predict that stagger's timing, and
    # matches what a real client (e.g. a browser) would face during this same brief window anyway.
    async def poll() -> None:
        while True:
            try:
                await _http_client.fetch(host, port, "GET", "/")
                return
            except OSError:
                await asyncio.sleep_ms(50)

    await asyncio.wait_for(poll(), timeout_s)


async def _soak(host: str, port: int, cycles: int) -> "list[str]":
    failures: list[str] = []
    for _ in range(_SOAK_WARMUP_CYCLES):
        for path in _SOAK_ENDPOINTS:
            await _http_client.fetch(host, port, "GET", path)
    gc.collect()
    baseline = gc.mem_free()
    for cycle in range(cycles):
        for path in _SOAK_ENDPOINTS:
            res = await _http_client.fetch(host, port, "GET", path)
            if res.status_code != 200:
                failures.append(f"cycle {cycle}: GET {path} -> {res.status_code}")
    gc.collect()
    after = gc.mem_free()
    if after < baseline - _MEM_FLAT_TOLERANCE_BYTES:
        failures.append(f"gc.mem_free() dropped from {baseline} to {after} over {cycles} cycles")
    return failures


def _ensure_dir(path: str) -> None:
    import os

    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists


async def main(config: RunConfig) -> "dict[str, Any]":
    machine.configure_fram_state_path(config.fram_state_path)
    if config.seed is not None:
        import random

        random.seed(config.seed)  # reseeds the one shared generator every chip fake's own
        # random_source=None default falls back to - same approach digital_twin/launch.py's own
        # main() already uses, for the same reason (see that module's own comment).

    _ensure_dir(_CONFIG_DIR)

    print(
        f"digital_twin/run_wozi_integration.py starting - host={config.host!r} port={config.port!r} "
        f"fram_state_path={config.fram_state_path!r} seed={config.seed!r} soak_cycles={config.soak_cycles!r} "
        f"duration={config.duration!r} faults={config.faults!r} wifi_outcomes={config.wifi_outcomes!r}"
    )

    main_task = asyncio.get_event_loop().create_task(
        sensortask_wozi.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port)
    )
    summary: dict[str, Any] = {"failures": [], "would_have_triggered_count": 0}
    try:
        await _wait_until_built()

        assert sensortask_wozi.i2c0 is not None and sensortask_wozi.i2c1 is not None and sensortask_wozi.spi0 is not None
        assert sensortask_wozi.conn is not None and sensortask_wozi.watchdog is not None
        # asy_i2c_driver.I2C/asy_spi_driver.SPI wrap the real machine.I2C/machine.SPI at their own
        # private _i2c/_spi attributes (confirmed directly against those modules' own __init__) -
        # the twin's own chip-fake registry (.devices/.device) lives on the wrapped object, not the
        # wrapper - same real gap digital_twin/launch.py never had to deal with (it constructs
        # machine.I2C/machine.SPI directly, with no asy_*_driver wrapper in between). Each wrapper's
        # own _i2c/_spi is only None before init() runs (asy_i2c_driver.I2C.__init__ calls it
        # itself, unconditionally) - always set by the time build_system() returns, just not
        # statically provable from the type alone.
        assert sensortask_wozi.i2c0._i2c is not None and sensortask_wozi.i2c1._i2c is not None and sensortask_wozi.spi0._spi is not None
        chips = {
            "scd30": sensortask_wozi.i2c0._i2c.devices[0x61],
            "sgp40": sensortask_wozi.i2c1._i2c.devices[0x59],
            "bmp3xx": sensortask_wozi.i2c1._i2c.devices[0x77],
            "fram": sensortask_wozi.spi0._spi.device,
        }
        for device, op, times in config.faults:
            _apply_fault(device, op, times, chips, sensortask_wozi.conn.wlan)
        if config.wifi_outcomes:
            sensortask_wozi.conn.wlan.script_connect_outcomes(config.wifi_outcomes)

        await _wait_until_serving(config.host, config.port)

        failures = await _soak(config.host, config.port, config.soak_cycles)
        if sensortask_wozi.watchdog.would_have_triggered_count != 0:
            failures.append(f"watchdog would have triggered {sensortask_wozi.watchdog.would_have_triggered_count} time(s)")

        summary = {
            "soak_cycles": config.soak_cycles,
            "failures": failures,
            "would_have_triggered_count": sensortask_wozi.watchdog.would_have_triggered_count,
        }
        print("digital_twin/run_wozi_integration.py soak summary:", summary)
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
        main_task.cancel()
        try:
            await main_task
        except asyncio.CancelledError:
            pass
        machine.flush_fram()

    return summary


if __name__ == "__main__":
    _config = parse_args(sys.argv[1:])
    _summary: "dict[str, Any] | None" = None
    try:
        _summary = asyncio.run(main(_config))
    except KeyboardInterrupt:
        print("digital_twin/run_wozi_integration.py: interrupted")
    if _summary is not None and _summary["failures"]:
        sys.exit(1)
