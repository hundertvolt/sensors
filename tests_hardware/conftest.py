"""Shared pytest fixtures for tests_hardware/ - fixtures skip (not error) when the hardware they
need isn't reachable, so `uv run pytest tests_hardware --collect-only` always succeeds with
nothing attached. See tests_hardware/README.md for how a dedicated hardware session runs this tier.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests_hardware/ itself, for `import harness`/`import bench_control`

import http_client  # noqa: E402
from bench_control import BenchBridge  # noqa: E402
from harness import Board, HardwareTestFailure, wait_until  # noqa: E402
from soak_tiers import SOAK_TIER_SECONDS  # noqa: E402


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
        "--allow-multi-day-rollover-wait",
        action="store_true",
        default=False,
        help=(
            "Actually run @pytest.mark.multi_day_rollover tests - a real, fixed ~12.4-day wait "
            "(time.ticks_ms()'s own 2**30 rollover) that cannot be shortened by any duration tier; "
            "deliberately its own separate flag, never bundled with --soak-tier. Skipped by default."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "long_soak: real-hardware passive observation over one of three named duration tiers (short/mid/long) - skipped unless --soak-tier is passed; see scripts/run_bench_soak_tests.sh")
    config.addinivalue_line("markers", "multi_day_rollover: a real, fixed ~12.4-day wait, not tier-selectable - skipped unless --allow-multi-day-rollover-wait is passed")
    config.addinivalue_line("markers", "flash_cycle: a deliberate re-provisioning flash (counts against the 'no extra flash cycles' constraint), skipped unless --allow-flash-cycle is passed")
    config.addinivalue_line("markers", "role_reversal: bench radio temporarily stops hosting br0-wifi-ap to join the DUT's own hotspot - informational marker, not skip-gated")


@pytest.fixture(scope="session")
def board(request: pytest.FixtureRequest) -> Iterator[Board]:
    b = Board(device=request.config.getoption("--device"))
    if not b.is_reachable():
        pytest.skip(
            f"no real board reachable at {b.device} - this fixture only runs against real hardware "
            "(see tests_hardware/README.md for provisioning). Not a failure: this tier is meant to "
            "be collectible with nothing attached."
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
            "`uv run toolchain/setup_toolchain.py env --tier bench` first (see tests_hardware/README.md)."
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
            raise HardwareTestFailure(f"PUT /networking during automatic stale-credential recovery failed: {res.status_code} {res.body!r}")
        result = res.json().get("result", {})
        accepted = {"Valid", "Unchanged"}
        if result.get("SSID") not in accepted or result.get("PW") not in accepted:
            raise HardwareTestFailure(f"PUT /networking during automatic stale-credential recovery was rejected: {result!r}")
    finally:
        bench.leave_dut_hotspot_and_restore_bridge()


@pytest.fixture(scope="session")
def dut_ip(board: Board, bench: BenchBridge) -> str:
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
            raise HardwareTestFailure(f"DUT fell back to hotspot mode instead of establishing a real STA connection:\n{joined}")
        if "WLAN connection established" not in joined:
            raise TimeoutError(f"no 'WLAN connection established' observed within {timeout_s}s of passive log observation:\n{joined}")
        if not _read_ip_and_resume():
            raise HardwareTestFailure(f"log showed 'WLAN connection established' but a follow-up check found no real IP:\n{joined}")

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
    except (TimeoutError, HardwareTestFailure):
        bench.kick_all_stations()
        board.hard_reset()
        try:
            _wait_for_ip_and_http(60.0, description_suffix=" (after one hard_reset() retry - see this fixture's own docstring)")
        except (TimeoutError, HardwareTestFailure):
            # Neither retry helps if the DUT has stale stored WiFi credentials (e.g. bridge
            # recreated with a fresh SSID/password) - falls back to stale-credential recovery.
            _recover_stale_dut_credentials(bench)
            bench.kick_all_stations()
            board.hard_reset()
            _wait_for_ip_and_http(60.0, description_suffix=" (after automatic stale-WiFi-credential recovery - see _recover_stale_dut_credentials())")
    return ip_holder[-1]
