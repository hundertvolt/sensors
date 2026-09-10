"""Dev-variant end-to-end digital-twin entry point - mirrors `run_wozi_integration.py` exactly,
only the underlying module and bus wiring differ. Not a `tests/test_*.py` file - it can serve
forever. See `digital_twin/README.md`'s "Swapping the twin in" section for the full reference."""

import asyncio
import gc
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

    import network  # type-only: only _apply_fault()'s wlan parameter needs the twin's WLAN type

import _http_client
import machine
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from launch import (
    _parse_wifi_outcome,  # deliberately reused, not reimplemented - see digital_twin/README.md
    parse_fault_spec,
    parse_hang_spec,
)
from unix_port_poll_prewarm import prewarm_poll_set

import sensortask_dev

_DEFAULT_FRAM_STATE_PATH = "digital_twin/fram_state.json"
_DEFAULT_SCD30_STATE_PATH = "digital_twin/scd30_state.json"  # same folder as the FRAM state file
# above, own individual file - see digital_twin/_scd30_chip.py's module docstring for what's persisted.
_CONFIG_DIR = "digital_twin/config/"
_SOAK_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/")
_SOAK_WARMUP_CYCLES = 40  # see run_wozi_integration.py's own identical constant/comment - this
# soak drives the real object graph the same way, so the same warm-up transient applies here too.
#
# _MEM_TREND_*: see run_wozi_integration.py's own identical constants/comment for the full
# methodology and measurement history behind this trend-check shape and tolerance - unchanged here,
# since nothing about this variant's own construction graph (only its bus/pin wiring differs from
# wozi's) would plausibly shift the steady-state memory-noise band this tolerance was measured
# against.
_MEM_TREND_TOLERANCE_BYTES = 8192
_SOAK_CYCLES_DEFAULT = 20


class RunConfig:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        fram_state_path: "str | None" = _DEFAULT_FRAM_STATE_PATH,
        scd30_state_path: "str | None" = _DEFAULT_SCD30_STATE_PATH,
        seed: "int | None" = None,
        faults: "list[tuple[str, str, int]] | None" = None,
        hangs: "list[tuple[str, str, float, int]] | None" = None,
        wifi_outcomes: "list[int] | None" = None,
        *,
        soak: bool = False,
        soak_cycles: int = _SOAK_CYCLES_DEFAULT,
        duration: "float | None" = None,
    ) -> None:
        self.host = host
        self.port = port
        self.fram_state_path = fram_state_path
        self.scd30_state_path = scd30_state_path
        self.seed = seed
        self.faults = faults if faults is not None else []
        self.hangs = hangs if hangs is not None else []
        self.wifi_outcomes = wifi_outcomes if wifi_outcomes is not None else []
        self.soak = soak
        self.soak_cycles = soak_cycles
        self.duration = duration

    def __eq__(self, other: "object") -> bool:
        if not isinstance(other, RunConfig):
            return NotImplemented
        return (
            self.host == other.host
            and self.port == other.port
            and self.fram_state_path == other.fram_state_path
            and self.scd30_state_path == other.scd30_state_path
            and self.seed == other.seed
            and self.faults == other.faults
            and self.hangs == other.hangs
            and self.wifi_outcomes == other.wifi_outcomes
            and self.soak == other.soak
            and self.soak_cycles == other.soak_cycles
            and self.duration == other.duration
        )

    def __repr__(self) -> str:
        return (
            f"RunConfig(host={self.host!r}, port={self.port!r}, fram_state_path={self.fram_state_path!r}, "
            f"scd30_state_path={self.scd30_state_path!r}, seed={self.seed!r}, faults={self.faults!r}, "
            f"hangs={self.hangs!r}, wifi_outcomes={self.wifi_outcomes!r}, soak={self.soak!r}, soak_cycles={self.soak_cycles!r}, "
            f"duration={self.duration!r})"
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
    scd30_state_path: str | None = _DEFAULT_SCD30_STATE_PATH
    seed: int | None = None
    faults: list[tuple[str, str, int]] = []
    hangs: list[tuple[str, str, float, int]] = []
    wifi_outcomes: list[int] = []
    soak = False
    soak_cycles = _SOAK_CYCLES_DEFAULT
    duration: float | None = None

    while remaining:
        arg = remaining.pop(0)
        if arg == "--host":
            host = _pop_value(remaining, arg)
        elif arg == "--port":
            port = int(_pop_value(remaining, arg))
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
        else:
            raise ValueError(f"unrecognized argument: {arg!r}")

    return RunConfig(
        host=host,
        port=port,
        fram_state_path=fram_state_path,
        scd30_state_path=scd30_state_path,
        seed=seed,
        faults=faults,
        hangs=hangs,
        wifi_outcomes=wifi_outcomes,
        soak=soak,
        soak_cycles=soak_cycles,
        duration=duration,
    )


def _apply_fault(device: str, op: str, times: int, chips: "dict[str, Any]", wlan: "network.WLAN") -> None:
    # Same shape as digital_twin/launch.py's own _apply_fault() - reads the real bus objects
    # sensortask_dev.build_system() actually constructed rather than launch.py's own local vars.
    import errno

    message = f"digital_twin/run_dev_integration.py --fault {device}:{op}"
    if device == "wlan":
        wlan.raise_on[op] = OSError(errno.EIO, message)
        return
    chips[device].fault.inject_fault(op, OSError(errno.EIO, message), times=times)


def _apply_hang(device: str, op: str, seconds: float, times: int, chips: "dict[str, Any]") -> None:
    # Same shape as _apply_fault() above - see digital_twin/_fault_injection.py's own module
    # docstring for why a real blocking time.sleep() (not an exception) is what this expresses.
    chips[device].fault.inject_hang(op, seconds, times=times)


async def _wait_until_built(timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        # webserver is the last module build_system() assigns before its own grouped await
        # x.setup() batch - see tests/test_digital_twin_sensortask_integration.py's own identical
        # poll for why this (not watchdog, assigned first) is the right readiness signal.
        while sensortask_dev.webserver is None:
            await asyncio.sleep_ms(20)

    await asyncio.wait_for(poll(), timeout_s)


async def _wait_until_serving(host: str, port: int, timeout_s: float = 10.0) -> None:
    # The real socket doesn't bind until start_and_check_tasks() reaches the webserver's own
    # staggered task starter - retrying the connection is simpler than predicting that timing.
    async def poll() -> None:
        while True:
            try:
                await _http_client.fetch(host, port, "GET", "/")
            except OSError:
                await asyncio.sleep_ms(50)
            else:
                return

    await asyncio.wait_for(poll(), timeout_s)


async def _soak(host: str, port: int, cycles: int) -> "list[str]":
    # Deliberately strictly-sequential (one fetch() awaited at a time, never asyncio.gather()'d) -
    # see run_wozi_integration.py's own identical comment for the full reasoning (a real
    # MicroPython Unix-port interpreter segfault found by exceeding WebserverService's own
    # max_connections=4 ceiling with concurrent clients) - this soak's own sequential pattern never
    # approaches that and must stay that way.
    failures: list[str] = []
    for _ in range(_SOAK_WARMUP_CYCLES):
        for path in _SOAK_ENDPOINTS:
            try:
                await _http_client.fetch(host, port, "GET", path)
            except OSError as e:
                failures.append(f"warmup: GET {path} -> {e!r}")
    gc.collect()
    mem_samples: list[int] = [gc.mem_free()]  # index 0: post-warmup baseline, excluded from the
    # trend comparison below (it's a single point, not a quarter average, and every real cycle
    # already starts from it).
    for cycle in range(cycles):
        for path in _SOAK_ENDPOINTS:
            try:
                res = await _http_client.fetch(host, port, "GET", path)
            except OSError as e:
                failures.append(f"cycle {cycle}: GET {path} -> {e!r}")
                continue
            if res.status_code != 200:
                failures.append(f"cycle {cycle}: GET {path} -> {res.status_code}")
        gc.collect()
        mem_samples.append(gc.mem_free())
    # Trend check (see run_wozi_integration.py's own _MEM_TREND_* module-level comment for why this
    # replaced a flat two-point delta): compare the mean of the first and last quarter of per-cycle
    # samples - averaging each quarter absorbs single-sample GC-timing noise a raw two-point diff
    # can't. Needs at least 4 per-cycle samples (cycles >= 4) for the quarters to mean anything;
    # skipped below that (a --soak-cycles this small is a manual smoke run, not a real memory-trend
    # check).
    per_cycle_samples = mem_samples[1:]
    quarter = len(per_cycle_samples) // 4
    if quarter >= 1:
        early = per_cycle_samples[:quarter]
        late = per_cycle_samples[-quarter:]
        early_avg = sum(early) / len(early)
        late_avg = sum(late) / len(late)
        trend = early_avg - late_avg  # positive: memory declined between quarters
        print(
            f"digital_twin/run_dev_integration.py memory trend: baseline={mem_samples[0]} "
            f"min={min(per_cycle_samples)} max={max(per_cycle_samples)} early_avg={early_avg:.0f} "
            f"late_avg={late_avg:.0f} trend={trend:.0f} tolerance={_MEM_TREND_TOLERANCE_BYTES} "
            f"quarter_size={quarter} samples={len(per_cycle_samples)}",
        )
        if trend > _MEM_TREND_TOLERANCE_BYTES:
            failures.append(
                f"gc.mem_free() trend declined by {trend:.0f} bytes (early_avg={early_avg:.0f} -> "
                f"late_avg={late_avg:.0f}) over {cycles} cycles, exceeding the "
                f"{_MEM_TREND_TOLERANCE_BYTES}-byte tolerance",
            )
    return failures


def _print_wdt_status() -> None:
    # See both call sites' own comments for why this needs to run from two different places.
    if sensortask_dev.watchdog is not None:
        print(f"digital_twin/run_dev_integration.py shutdown: would_have_triggered_count={sensortask_dev.watchdog.would_have_triggered_count}")


def _ensure_dir(path: str) -> None:
    import os

    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists


async def main(config: RunConfig) -> "dict[str, Any]":
    # Must run before anything else in the process registers a poll object - see
    # unix_port_poll_prewarm.py's own module docstring and digital_twin/README.md's "Known gaps"
    # section (a confirmed Unix-port-only MicroPython bug this pre-warming avoids triggering).
    prewarm_poll_set()
    # Must also run before anything constructs a real AsyUDPSocket (captive_dns.py's DNSServer,
    # asy_ntp_client.py's NTP fetch, asy_dns_client.py's own resolver) - see
    # _unix_port_udp_addr_shim.py's own module docstring for the confirmed Unix-port-only
    # socket.bind()/connect() quirk this works around, entirely from twin-side code.
    patch_asy_udp_socket_for_unix_port()
    machine.configure_fram_state_path(config.fram_state_path)
    machine.configure_scd30_state_path(config.scd30_state_path)
    # Selects the dev-bench bus wiring (i2c0=BMP3xx alone, i2c1=SCD30+SGP40, SCD30 IRQ=GPIO11) -
    # machine.py's own _wire_i2c_devices() defaults to wozi's reversed layout otherwise. Must run
    # before sensortask_dev.build_system() (below, inside main_task) ever constructs i2c0/i2c1.
    machine.configure_i2c_wiring("dev")
    if config.seed is not None:
        import random

        random.seed(config.seed)  # reseeds the one shared generator every chip fake's own
        # random_source=None default falls back to - same approach digital_twin/launch.py's own
        # main() already uses, for the same reason (see that module's own comment).

    _ensure_dir(_CONFIG_DIR)

    print(
        f"digital_twin/run_dev_integration.py starting - host={config.host!r} port={config.port!r} "
        f"fram_state_path={config.fram_state_path!r} scd30_state_path={config.scd30_state_path!r} "
        f"seed={config.seed!r} soak_cycles={config.soak_cycles!r} "
        f"duration={config.duration!r} faults={config.faults!r} hangs={config.hangs!r} wifi_outcomes={config.wifi_outcomes!r}",
    )

    main_task = asyncio.get_event_loop().create_task(
        sensortask_dev.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port),
    )
    summary: dict[str, Any] = {"failures": [], "would_have_triggered_count": 0}
    try:
        await _wait_until_built()

        assert sensortask_dev.i2c0 is not None and sensortask_dev.i2c1 is not None and sensortask_dev.spi0 is not None
        assert sensortask_dev.conn is not None and sensortask_dev.watchdog is not None
        # asy_i2c_driver.I2C/asy_spi_driver.SPI wrap the real machine.I2C/machine.SPI at their own
        # private _i2c/_spi attributes - the twin's chip-fake registry (.devices/.device) lives on
        # the wrapped object. Always set by the time build_system() returns, just not statically
        # provable from the type alone.
        assert sensortask_dev.i2c0._i2c is not None and sensortask_dev.i2c1._i2c is not None and sensortask_dev.spi0._spi is not None
        # dev_legacy/README.md's wiring table (this bench unit, not wozi's): SCD30 and SGP40 share
        # i2c1; BMP3xx sits alone on i2c0 (wozi: SCD30 alone on i2c0, SGP40+BMP3xx sharing i2c1).
        chips = {
            "scd30": sensortask_dev.i2c1._i2c.devices[0x61],
            "sgp40": sensortask_dev.i2c1._i2c.devices[0x59],
            "bmp3xx": sensortask_dev.i2c0._i2c.devices[0x77],
            "fram": sensortask_dev.spi0._spi.device,
        }
        for device, op, times in config.faults:
            _apply_fault(device, op, times, chips, sensortask_dev.conn.wlan)
        for device, op, seconds, times in config.hangs:
            _apply_hang(device, op, seconds, times, chips)
        if config.wifi_outcomes:
            sensortask_dev.conn.wlan.script_connect_outcomes(config.wifi_outcomes)

        # A queued --hang can fire during setup() (before this point) via a real, blocking
        # time.sleep() that freezes the whole interpreter, including this very poll loop - the
        # default 10s bound isn't enough to survive that, so it's widened by the total configured
        # hang time (plus its own normal margin) whenever any are armed.
        total_hang_s = sum(seconds * times for _device, _op, seconds, times in config.hangs)
        await _wait_until_serving(config.host, config.port, timeout_s=10.0 + total_hang_s)

        if config.soak:
            failures = await _soak(config.host, config.port, config.soak_cycles)
            if sensortask_dev.watchdog.would_have_triggered_count != 0:
                failures.append(f"watchdog would have triggered {sensortask_dev.watchdog.would_have_triggered_count} time(s)")

            summary = {
                "soak_cycles": config.soak_cycles,
                "failures": failures,
                "would_have_triggered_count": sensortask_dev.watchdog.would_have_triggered_count,
            }
            print("digital_twin/run_dev_integration.py soak summary:", summary)
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
        # Unconditional, not just under --soak: an external observer driving this as a subprocess
        # has no in-process access to sensortask_dev.watchdog otherwise. Called before
        # main_task.cancel()/await, since a real SIGINT shutdown never reaches a statement placed
        # after that pair - see the __main__ block below for the other call site this needs (a
        # SIGINT that lands while parked in the scheduler's own poll wait skips this whole block).
        _print_wdt_status()
        main_task.cancel()
        try:
            await main_task
        except (asyncio.CancelledError, KeyboardInterrupt):
            # A second SIGINT can arrive while this cleanup await is still in flight - without
            # catching it here too, it would propagate out, skipping the flush calls below.
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
        # asyncio.run()'s own KeyboardInterrupt gap while parked in the scheduler's poll wait - see
        # SPECIFICATION.md Part F.1. A harmless no-op if main()'s own finally already ran.
        machine.flush_fram()
        machine.flush_scd30()
        _print_wdt_status()
        print("digital_twin/run_dev_integration.py: interrupted")
    if _summary is not None and _summary["failures"]:
        sys.exit(1)
