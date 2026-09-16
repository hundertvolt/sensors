"""Shared pytest fixtures for tests_hardware/ - fixtures skip (not error) when the hardware they
need isn't reachable, so `uv run pytest tests_hardware --collect-only` always succeeds with
nothing attached. See tests_hardware/README.md for how a dedicated hardware session runs this tier.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests_hardware/ itself, for `import harness`/`import bench_control`

import http_client
from bench_control import BenchBridge
from harness import Board, FlashedBuild, HardwareTestFailureError, wait_until
from soak_tiers import SOAK_TIER_SECONDS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for `import buildgen`

from buildgen.gc_policy import GC_POLICY_THRESHOLDS, PRESSURE_MODULE

if TYPE_CHECKING:
    from collections.abc import Iterator


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--device", default=None, help="Serial device path for the flash-tier board (default: $MPREMOTE_DEVICE or /dev/ttyACM0)")
    parser.addoption(
        "--soak-tier",
        choices=sorted(SOAK_TIER_SECONDS),
        default=None,
        help=(
            "Actually run @pytest.mark.long_soak tests, for this one named duration tier only "
            f"({', '.join(f'{k}={v:.0f}s' for k, v in SOAK_TIER_SECONDS.items())}) - see "
            "scripts/run_bench_soak_tests.sh, the only intended way to pass this. Not set by "
            "default, so long_soak tests always skip in a general suite run."
        ),
    )
    parser.addoption(
        "--allow-flash-cycle",
        action="store_true",
        default=False,
        help="Actually run @pytest.mark.flash_cycle tests (a deliberate re-provisioning flash - counts against the 'no extra flash cycles' constraint, never run as part of a routine pass). Skipped by default.",
    )
    parser.addoption(
        "--expect-gc-policy",
        choices=sorted(GC_POLICY_THRESHOLDS),
        default=None,
        help=(
            "Assert the flashed firmware was built with this GC policy (buildgen/gc_policy.py). "
            "The board's own gc.threshold() is the source of truth - this states what the run "
            "intends, so a run against the wrong flashed build fails loudly instead of quietly "
            "measuring the other one. See scripts/run_bench_gc_matrix.sh."
        ),
    )
    parser.addoption(
        "--allow-multi-day-rollover-wait",
        action="store_true",
        default=False,
        help=(
            "Actually run @pytest.mark.multi_day_rollover tests - a real, fixed ~12.4-day wait "
            "(time.ticks_ms()'s own 2**30 rollover) that cannot be shortened by any duration tier; "
            "deliberately its own separate flag, never bundled with --soak-tier. Skipped by default."
        ),
    )
    parser.addoption(
        "--allow-scd30-writes",
        action="store_true",
        default=False,
        help=(
            "Global permission to spend ANY real NVM-persisted SCD30 write at all - actually run "
            "@pytest.mark.scd30_write tests. The SCD30's on-chip NVM has a finite write-wear "
            "budget, so without this flag a full flash-tier run (dozens of tests) spends zero real "
            "SCD30 writes, including the one routine per-session write "
            "scd30_continuous_measurement_triggered would otherwise make (SPECIFICATION.md Part "
            "C.8). Skipped by default. Every test that touches SCD30's NVM at all needs this flag, "
            "including the one further gated behind --allow-scd30-extra-write below - this is the "
            "single flag that decides whether any real SCD30 NVM write test runs, not one flag per "
            "test group."
        ),
    )
    parser.addoption(
        "--allow-scd30-extra-write",
        action="store_true",
        default=False,
        help=(
            "On top of --allow-scd30-writes, also run the one @pytest.mark.scd30_extra_write test "
            "that spends a SECOND real NVM-persisted SCD30 write beyond the one routine "
            "per-session write --allow-scd30-writes alone already permits (SPECIFICATION.md Part "
            "C.8). AND-gated with --allow-scd30-writes, not an independent flag - passing this "
            "alone, without --allow-scd30-writes, still deselects the test. Skipped by default, "
            "same precedent as --allow-flash-cycle: an explicit, rare, deliberately-opted-into "
            "extra real write, never run as part of a routine pass."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "long_soak: real-hardware passive observation over one of three named duration tiers (short/mid/long) - skipped unless --soak-tier is passed; see scripts/run_bench_soak_tests.sh")
    config.addinivalue_line("markers", "multi_day_rollover: a real, fixed ~12.4-day wait, not tier-selectable - skipped unless --allow-multi-day-rollover-wait is passed")
    config.addinivalue_line("markers", "flash_cycle: a deliberate re-provisioning flash (counts against the 'no extra flash cycles' constraint), skipped unless --allow-flash-cycle is passed")
    config.addinivalue_line("markers", "scd30_write: at least one real NVM-persisted SCD30 write, directly or via a fixture it depends on (e.g. scd30_continuous_measurement_triggered) - deselected unless --allow-scd30-writes is passed")
    config.addinivalue_line("markers", "scd30_extra_write: a SECOND real NVM-persisted SCD30 write beyond the routine per-session one already spent by a scd30_write test - always carried alongside @pytest.mark.scd30_write on the same test, deselected unless BOTH --allow-scd30-writes AND --allow-scd30-extra-write are passed")
    config.addinivalue_line("markers", "memory_pressure: needs a firmware built with --gc-policy reactive --memory-pressure (the frozen churn instrument is absent from every other build) - deselected by the general suite runners, selected by scripts/run_bench_gc_matrix.sh's own pressure pass")
    config.addinivalue_line("markers", "role_reversal: bench radio temporarily stops hosting br0-wifi-ap to join the DUT's own hotspot - informational marker, not skip-gated")


# A board mid-USB-re-enumeration (just reflashed, or just released by another mpremote call) is
# not the same thing as no board attached, but is_reachable() deliberately has no retry of its own
# (allow_recovery=False, so a genuinely expected disconnect isn't masked). Without a settle window
# here, that momentary state turns the WHOLE session into skips - which _require_clean_hardware_run.sh
# then reports as a failed run. Found on the bench, 2026-09-14. Nothing attached still skips, just
# _SETTLE_TIMEOUT_S later; --collect-only bypasses fixtures entirely, so it costs that path nothing.
_SETTLE_TIMEOUT_S = 20.0


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Central deselection point for every real SCD30 NVM write test - AND-gates
    @pytest.mark.scd30_extra_write on top of @pytest.mark.scd30_write, so --allow-scd30-writes alone
    decides whether any real SCD30 write test runs at all; --allow-scd30-extra-write only narrows further."""
    allow_writes = config.getoption("--allow-scd30-writes")
    allow_extra_write = config.getoption("--allow-scd30-extra-write")
    kept: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        lacks_write_permission = item.get_closest_marker("scd30_write") is not None and not allow_writes
        lacks_extra_write_permission = item.get_closest_marker("scd30_extra_write") is not None and not allow_extra_write
        if lacks_write_permission or lacks_extra_write_permission:
            deselected.append(item)
        else:
            kept.append(item)
    if deselected:
        items[:] = kept
        config.hook.pytest_deselected(items=deselected)


@pytest.fixture(scope="session")
def board(request: pytest.FixtureRequest) -> Iterator[Board]:
    b = Board(device=request.config.getoption("--device"))
    deadline = time.monotonic() + _SETTLE_TIMEOUT_S
    while not b.is_reachable():
        if time.monotonic() >= deadline:
            break
        time.sleep(1.0)
    if not b.is_reachable():
        pytest.skip(
            f"no real board reachable at {b.device} after {_SETTLE_TIMEOUT_S:.0f}s - this fixture only runs against real hardware "
            "(see tests_hardware/README.md for provisioning). Not a failure: this tier is meant to "
            "be collectible with nothing attached.",
        )
    yield b


@pytest.fixture(scope="session")
def bench(board: Board) -> Iterator[BenchBridge]:
    """Depends on `board` - a bench test needs both the real board over USB and the real WiFi
    bridge, never just the bridge alone."""
    bridge = BenchBridge()
    if not bridge.is_configured():
        pytest.skip(
            "no bench WiFi bridge configured (br0-wifi-ap missing) - run "
            "`uv run toolchain/setup_toolchain.py env --tier bench` first (see tests_hardware/README.md).",
        )
    yield bridge


_DUT_DEFAULT_HOSTNAME = "SensorNode"  # src/asy_wifi_service.py's _VAL_HOST schema default - this bench's own DUT has never been reconfigured with a different one (dev_legacy/README.md's "Current bench state")
_DUT_HOTSPOT_PASSWORD = "12345678"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap() - same value as test_hotspot_role_reversal.py's own _HOTSPOT_PASSWORD


def _recover_stale_dut_credentials(bench: BenchBridge) -> None:
    """Last-resort recovery for dut_ip(): if the DUT can't join the bench AP after two hard_reset()
    retries, stale stored WiFi credentials are the likely cause - joins the DUT's own hotspot
    fallback and PUTs the bench AP's current credentials to it (see tests_hardware/README.md)."""
    wait_until(
        lambda: bench.is_ssid_visible(_DUT_DEFAULT_HOSTNAME),
        timeout_s=30.0,
        poll_interval_s=2.0,
        description=f"DUT's own hotspot ({_DUT_DEFAULT_HOSTNAME!r}) to become scannable during automatic stale-credential recovery",
    )
    bench.join_dut_hotspot(_DUT_DEFAULT_HOSTNAME, _DUT_HOTSPOT_PASSWORD, timeout_s=45.0)
    try:
        gateway = bench.gateway_ip()
        ssid = bench.ap_ssid()
        password = bench.ap_password()
        res = http_client.fetch(gateway, 80, "PUT", "/networking", {"SSID": ssid, "PW": password}, timeout_s=10.0)
        if res.status_code != 200:
            raise HardwareTestFailureError(f"PUT /networking during automatic stale-credential recovery failed: {res.status_code} {res.body!r}")
        result = res.json().get("result", {})
        accepted = {"Valid", "Unchanged"}
        if result.get("SSID") not in accepted or result.get("PW") not in accepted:
            raise HardwareTestFailureError(f"PUT /networking during automatic stale-credential recovery was rejected: {result!r}")
    finally:
        bench.leave_dut_hotspot_and_restore_bridge()


# The bench is dev-only (CLAUDE.md), so the frozen device module's name is fixed.
_DEVICE_MODULE = "sensortask_dev"


@pytest.fixture(scope="session")
def flashed_build(board: Board, request: pytest.FixtureRequest) -> FlashedBuild:
    """What is ACTUALLY on the board, read off the frozen image: the GC policy the build declares,
    and whether the pressure instrument is present. An --expect-gc-policy mismatch fails here rather
    than letting a whole run silently measure the build nobody meant to test."""
    # BUILD_GC_POLICY, not a live gc.threshold() read. Entering the raw REPL can land before main.py
    # has run, and a fresh interpreter reports the -1 default no matter what the boot entry would
    # have set - which misreads a threshold build as a reactive one and fails 62 tests at setup
    # (seen on the bench, 2026-09-14). Importing the device module only binds names; main() is what
    # starts anything, and the module is already resident on a booted board anyway.
    try:
        output = board.exec(
            "import gc\n"
            f"import {_DEVICE_MODULE}\n"
            f"print('GC_POLICY=' + {_DEVICE_MODULE}.BUILD_GC_POLICY)\n"
            "print('LIVE_THRESHOLD=' + str(gc.threshold()))\n"
            "try:\n"
            f"    import {PRESSURE_MODULE}\n"
            "    print('PRESSURE_MODULE=1')\n"
            "except ImportError:\n"
            "    print('PRESSURE_MODULE=0')",
            timeout_s=30.0,
        )
    finally:
        board.hard_reset()

    policy = None
    live_threshold = None
    has_pressure = False
    for line in output.splitlines():
        if line.startswith("GC_POLICY="):
            policy = line[len("GC_POLICY=") :].strip()
        elif line.startswith("LIVE_THRESHOLD="):
            live_threshold = int(line[len("LIVE_THRESHOLD=") :].strip())
        elif line.startswith("PRESSURE_MODULE="):
            has_pressure = line.strip().endswith("1")
    if policy is None:
        raise HardwareTestFailureError(
            f"could not read {_DEVICE_MODULE}.BUILD_GC_POLICY off the board - a firmware predating "
            f"the GC-policy build option, or a failed import. Full output:\n{output}",
        )
    if policy not in GC_POLICY_THRESHOLDS:
        raise HardwareTestFailureError(f"the board declares an unknown GC policy {policy!r} - expected one of {sorted(GC_POLICY_THRESHOLDS)}")

    build = FlashedBuild(policy=policy, threshold=GC_POLICY_THRESHOLDS[policy], live_threshold=live_threshold, has_pressure_module=has_pressure)
    expected = request.config.getoption("--expect-gc-policy")
    if expected is not None and build.policy != expected:
        raise HardwareTestFailureError(
            f"this run expects a {expected!r} build (--expect-gc-policy) but the board is running a "
            f"{build.policy!r} one. Flash the intended firmware first: "
            f"uv run scripts/flash_dev_firmware.py --gc-policy {expected}",
        )
    return build


@pytest.fixture
def pressure_build(flashed_build: FlashedBuild) -> FlashedBuild:
    """Gate for @pytest.mark.memory_pressure tests: the churn instrument must really be frozen in."""
    if not flashed_build.has_pressure_module:
        pytest.skip(
            f"the flashed {flashed_build.policy!r} build carries no {PRESSURE_MODULE} module - pressure tests "
            "need `uv run scripts/build_firmware.py dev --gc-policy reactive --memory-pressure` "
            "(see scripts/run_bench_gc_matrix.sh)",
        )
    return flashed_build


@pytest.fixture(scope="session")
def dut_ip(board: Board, bench: BenchBridge, flashed_build: FlashedBuild) -> str:
    """The DUT's real STA-mode IP on the bench bridge network, for live-system HTTP checks. Retries
    hard_reset()+kick_all_stations() through known reconnect flakiness, then falls back to
    stale-credential recovery - see tests_hardware/README.md for the full findings trail."""
    ip_holder: list[str] = []

    def _read_ip_and_resume() -> bool:
        # Strands main.py (soft reset via exec() stops it re-running) - always followed by a real
        # hard_reset(). kick_all_stations() first to clear stale AP-side station entries (README).
        try:
            output = board.exec(
                "import network\n"
                "w = network.WLAN(network.STA_IF)\n"
                "print('DUT_IP=' + (w.ifconfig()[0] if w.isconnected() else ''))",
                timeout_s=15.0,
            )
        finally:
            bench.kick_all_stations()
            board.hard_reset()
        for line in output.splitlines():
            if line.startswith("DUT_IP=") and len(line) > len("DUT_IP="):
                ip_holder.append(line[len("DUT_IP=") :].strip())
                return True
        return False

    def _check_http_ready() -> bool:
        return http_client.fetch(ip_holder[-1], 80, "GET", "/status", timeout_s=5.0).status_code == 200

    def _wait_for_sta_ip(timeout_s: float) -> None:
        # Purely passive (tail_log only, no exec()/run()) - the board must already be mid-boot
        # from a prior hard_reset() before this is called.
        lines = board.tail_log(duration_s=timeout_s)
        joined = "\n".join(lines)
        if "Permanently no WLAN connection" in joined:
            raise HardwareTestFailureError(f"DUT fell back to hotspot mode instead of establishing a real STA connection:\n{joined}")
        if "WLAN connection established" not in joined:
            raise TimeoutError(f"no 'WLAN connection established' observed within {timeout_s}s of passive log observation:\n{joined}")
        if not _read_ip_and_resume():
            raise HardwareTestFailureError(f"log showed 'WLAN connection established' but a follow-up check found no real IP:\n{joined}")

    def _wait_for_ip_and_http(timeout_s: float, description_suffix: str = "") -> None:
        _wait_for_sta_ip(timeout_s)
        wait_until(
            _check_http_ready,
            timeout_s=30.0,
            poll_interval_s=2.0,
            description=f"DUT serves real HTTP at {ip_holder[-1]} (webserver task starts only after ntp_force_sync(), up to ~20s after STA connects){description_suffix}",
        )

    # kick_all_stations() before every hard_reset() clears stale AP-side station entries (README).
    bench.kick_all_stations()
    board.hard_reset()  # only a real hard_reset() reliably resumes normal auto-boot; soft reset leaves main.py stopped (README)
    try:
        _wait_for_ip_and_http(60.0)
    except (TimeoutError, HardwareTestFailureError):
        bench.kick_all_stations()
        board.hard_reset()
        try:
            _wait_for_ip_and_http(60.0, description_suffix=" (after one hard_reset() retry - see this fixture's own docstring)")
        except (TimeoutError, HardwareTestFailureError):
            # Neither retry helps if the DUT has stale stored WiFi credentials (e.g. bridge
            # recreated with a fresh SSID/password) - falls back to stale-credential recovery.
            _recover_stale_dut_credentials(bench)
            bench.kick_all_stations()
            board.hard_reset()
            _wait_for_ip_and_http(60.0, description_suffix=" (after automatic stale-WiFi-credential recovery - see _recover_stale_dut_credentials())")
    return ip_holder[-1]
