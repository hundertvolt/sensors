"""Shared pytest fixtures for tests_hardware/ - fixtures skip (not error) when the hardware they
need isn't reachable, so `uv run pytest tests_hardware --collect-only` always succeeds with
nothing attached. See tests_hardware/README.md for how a dedicated hardware session runs this tier.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests_hardware/ itself, for `import harness`/`import bench_control`

import http_client
from bench_control import BenchBridge
from harness import Board, HardwareTestFailureError, wait_until
from soak_tiers import SOAK_TIER_SECONDS

if TYPE_CHECKING:
    from collections.abc import Iterator


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--device", default=None, help="Serial device path for the flash-tier board (default: $MPREMOTE_DEVICE, else the board's stable /dev/serial/by-id symlink - see harness.resolve_board_device())")
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
    parser.addoption(
        "--allow-neopixel-sweep",
        action="store_true",
        default=False,
        help=(
            "Actually run @pytest.mark.neopixel_sweep tests - the two long ISL29125 light programs "
            "that drive the board's own WS2812 and read the part back. They need a PHYSICAL rig the "
            "bench does not have by default: the on-board NeoPixel aimed at the ISL29125's window at "
            "a fixed distance with ambient light excluded (set up and recorded by the manual tier's "
            "own isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry). Without that rig "
            "they do not merely mis-measure, they fail - and they cost ~10 minutes of real light "
            "programs when they do run. Spends no write of any kind, so it is its own flag rather "
            "than a persistence one. Skipped by default."
        ),
    )
    parser.addoption(
        "--allow-persistence-writes",
        action="store_true",
        default=False,
        help=(
            "Global kill switch for ANY real limited-endurance persistence write - actually run "
            "@pytest.mark.persistence_write tests. Covers every store with a finite write-wear "
            "budget, not just one chip: the SCD30's own on-chip NVM, and the RP2040's flash "
            "filesystem, which every accepted config-persisting PUT writes through "
            "config_manager.py's own json.dump(). FRAM is deliberately NOT in scope - its endurance "
            "is effectively unbounded for this project's write rates. Without this flag a run spends "
            "no write that a test OWNS; it is not zero writes overall, because a persisting write "
            "that is a shared PREREQUISITE (joined_hotspot clearing the SSID, "
            "_recover_stale_dut_credentials()) stays unmarked and still runs - gating those would "
            "deselect exactly the tests they exist to enable. Skipped by default. Every test that "
            "owns one needs this flag, including the one further gated behind "
            "--allow-scd30-extra-write below - this is the single flag that decides whether any "
            "real persistence write happens, not one flag per test group."
        ),
    )
    parser.addoption(
        "--allow-scd30-extra-write",
        action="store_true",
        default=False,
        help=(
            "On top of --allow-persistence-writes, also run the one @pytest.mark.scd30_extra_write "
            "test that spends a SECOND real NVM-persisted SCD30 write beyond the one routine "
            "per-session write --allow-persistence-writes alone already permits (SPECIFICATION.md "
            "Part C.8). Stays SCD30-specific, and stays AND-gated with the global flag - passing "
            "this alone, without --allow-persistence-writes, still deselects the test. Skipped by default, "
            "same precedent as --allow-flash-cycle: an explicit, rare, deliberately-opted-into "
            "extra real write, never run as part of a routine pass."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "long_soak: real-hardware passive observation over one of three named duration tiers (short/mid/long) - skipped unless --soak-tier is passed; see scripts/run_bench_soak_tests.sh")
    config.addinivalue_line("markers", "multi_day_rollover: a real, fixed ~12.4-day wait, not tier-selectable - skipped unless --allow-multi-day-rollover-wait is passed")
    config.addinivalue_line("markers", "flash_cycle: a deliberate re-provisioning flash (counts against the 'no extra flash cycles' constraint), skipped unless --allow-flash-cycle is passed")
    config.addinivalue_line("markers", "persistence_write: the TEST ITSELF spends a real limited-endurance write (SCD30 on-chip NVM, or the RP2040 flash filesystem behind any config-persisting PUT), directly or through a helper it drives - deselected unless --allow-persistence-writes is passed. A write that is a shared PREREQUISITE rather than the thing under test stays unmarked and allowed - see tests_hardware/README.md")
    config.addinivalue_line("markers", "scd30_extra_write: a SECOND real NVM-persisted SCD30 write beyond the routine per-session one already spent by a persistence_write test - always carried alongside @pytest.mark.persistence_write on the same test, deselected unless BOTH --allow-persistence-writes AND --allow-scd30-extra-write are passed")
    config.addinivalue_line("markers", "neopixel_sweep: needs the physical NeoPixel-aimed-at-the-ISL29125 rig (manual tier records its geometry) - skipped unless --allow-neopixel-sweep is passed; ~10 minutes of real light programs when it runs, and a hard failure rather than a soft one without the rig")
    config.addinivalue_line("markers", "role_reversal: bench radio temporarily stops hosting br0-wifi-ap to join the DUT's own hotspot - informational marker, not skip-gated")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Central deselection point for every real limited-endurance persistence write. AND-gates
    scd30_extra_write on top of persistence_write: the global flag alone decides whether any such
    write happens, and --allow-scd30-extra-write only narrows further, for SCD30's second write."""
    allow_writes = config.getoption("--allow-persistence-writes")
    allow_extra_write = config.getoption("--allow-scd30-extra-write")
    kept: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        lacks_write_permission = item.get_closest_marker("persistence_write") is not None and not allow_writes
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
    if not b.is_reachable():
        pytest.skip(
            f"no real board reachable at {b.device} - this fixture only runs against real hardware "
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


# The DUT's hotspot SSID is its Hostname config value, whose DEFAULT a build injects from
# devices/<device>.toml since 2026-09-18 - so a board with an older config file still answers to
# the persisted "SensorNode". Both are live; newest first, so a fresh board is found first.
_DUT_HOSTNAME_CANDIDATES = ("SensorStationDev", "SensorNode")
_DUT_HOTSPOT_PASSWORD = "12345678"  # src/asy_wifi_service.py's _VAL_HOTSPOT_PW default, which every devices/*.toml also declares - same value as test_hotspot_role_reversal.py's own _HOTSPOT_PASSWORD


def _recover_stale_dut_credentials(bench: BenchBridge) -> None:
    """Last-resort recovery for dut_ip(): if the DUT can't join the bench AP after two hard_reset()
    retries, stale stored WiFi credentials are the likely cause - joins the DUT's own hotspot
    fallback and PUTs the bench AP's current credentials to it (see tests_hardware/README.md)."""
    found: list[str] = []

    def _any_candidate_visible() -> bool:
        for ssid in _DUT_HOSTNAME_CANDIDATES:
            if bench.is_ssid_visible(ssid):
                found.append(ssid)
                return True
        return False

    wait_until(
        _any_candidate_visible,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description=f"DUT's own hotspot (one of {list(_DUT_HOSTNAME_CANDIDATES)}) to become scannable during automatic stale-credential recovery",
    )
    bench.join_dut_hotspot(found[0], _DUT_HOTSPOT_PASSWORD, timeout_s=45.0)
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
