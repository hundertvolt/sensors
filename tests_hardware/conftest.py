"""Shared pytest fixtures for tests_hardware/ - see tests_hardware/README.md for how a dedicated
session with real hardware attached runs this tier, and HARDWARE_TEST_PLAN.md §6 for the design.

Every fixture here skips (not errors) when the hardware it needs isn't reachable, so this whole
tier stays collectible and readable even with nothing physically attached (the state this repo is
in right now) - `uv run pytest tests_hardware --collect-only` must always succeed."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests_hardware/ itself, for `import harness`/`import bench_control`

from bench_control import BenchBridge  # noqa: E402
from harness import Board, wait_until  # noqa: E402


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--device", default=None, help="Serial device path for the flash-tier board (default: $MPREMOTE_DEVICE or /dev/ttyACM0)")
    parser.addoption(
        "--run-long-soak",
        action="store_true",
        default=False,
        help="Actually run @pytest.mark.long_soak tests (multi-hour/multi-day passive observations - see HARDWARE_TEST_PLAN.md item A.1/A.6). Skipped by default.",
    )
    parser.addoption(
        "--allow-flash-cycle",
        action="store_true",
        default=False,
        help="Actually run @pytest.mark.flash_cycle tests (a deliberate re-provisioning flash, per HARDWARE_TEST_PLAN.md §6.1 - counts against the 'no extra flash cycles' constraint, never run as part of a routine pass). Skipped by default.",
    )
    parser.addoption(
        "--long-soak-seconds",
        type=float,
        default=6 * 3600.0,
        help="Duration for a long_soak test's own watch window (default 6h) - independent of any test's own internally-computed wait (e.g. the ticks-rollover test computes its own ~12.4-day target from a live reading, this flag only bounds tests that watch for a fixed window instead).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "long_soak: multi-hour/multi-day passive real-hardware observation, skipped unless --run-long-soak is passed")
    config.addinivalue_line("markers", "flash_cycle: a deliberate re-provisioning flash (counts against the 'no extra flash cycles' constraint), skipped unless --allow-flash-cycle is passed")
    config.addinivalue_line("markers", "role_reversal: bench radio temporarily stops hosting br0-wifi-ap to join the DUT's own hotspot (HARDWARE_TEST_PLAN.md §11) - informational marker, not skip-gated")


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
    """Depends on `board` (bench ⊇ flash, HARDWARE_TEST_PLAN.md §3) - a bench test needs both the
    real board over USB and the real WiFi bridge, never just the bridge alone."""
    bridge = BenchBridge()
    if not bridge.is_configured():
        pytest.skip(
            "no bench WiFi bridge configured (br0-wifi-ap missing) - run "
            "`uv run toolchain/setup_toolchain.py env --tier bench` first (see tests_hardware/README.md)."
        )
    yield bridge


@pytest.fixture(scope="session")
def dut_ip(board: Board, bench: BenchBridge) -> str:
    """The DUT's real STA-mode IP on the bench bridge network, for live-system HTTP checks.

    CONFIRMED ON FIRST REAL RUN: `board.exec()`'s always-implicit soft-reset (see
    harness.Board.run_isolated()'s own docstring) does interrupt whatever's currently running,
    but `network.WLAN(network.STA_IF)` reads persistent hardware/firmware-level state that
    survives it either way - the real driver itself, asy_wifi_service.py, calls it fresh each
    time rather than caching a handle - so `_check()` below is safe to call repeatedly.

    REAL FINDING, fixed: a real, not-yet-fully-root-caused WiFi reconnection flakiness exists on
    this bench unit (see tests_hardware/README.md's "First real run" list for the full
    investigation - confirmed independent of this fixture's own polling, reproduced identically
    via plain hard_reset() + passive observation with no test code involved at all: 6/8 trials in
    one session fell back to hotspot mode). A single bad boot used to fail this fixture outright
    (TimeoutError after 60s), which - being session-scoped - then cascaded into every other bench
    test failing/erroring for a reason with nothing to do with what that test actually checks.
    Fixed the same way `joined_hotspot`'s own fixture teardown already recovers from an analogous
    stuck-state risk: one bounded `hard_reset()` retry if the first wait_until() times out, before
    giving up for real. This does not paper over the underlying flakiness (still fully documented
    and still worth the project owner's attention) - it just stops one unlucky boot from taking
    down bench coverage that has nothing to do with WiFi at all."""
    ip_holder: list[str] = []

    def _check() -> bool:
        output = board.exec(
            "import network\n"
            "w = network.WLAN(network.STA_IF)\n"
            "print('DUT_IP=' + (w.ifconfig()[0] if w.isconnected() else ''))",
            timeout_s=15.0,
        )
        for line in output.splitlines():
            if line.startswith("DUT_IP=") and len(line) > len("DUT_IP="):
                ip_holder.append(line[len("DUT_IP=") :].strip())
                return True
        return False

    try:
        wait_until(_check, timeout_s=60.0, poll_interval_s=3.0, description="DUT reports a real STA IP address")
    except TimeoutError:
        board.hard_reset()
        wait_until(
            _check,
            timeout_s=60.0,
            poll_interval_s=3.0,
            description="DUT reports a real STA IP address (after one hard_reset() retry - see this fixture's own docstring)",
        )
    return ip_holder[-1]
