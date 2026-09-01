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

import http_client  # noqa: E402
from bench_control import BenchBridge  # noqa: E402
from harness import Board, HardwareTestFailure, wait_until  # noqa: E402


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

    THIRD REAL FINDING, fixed (the big one - found after the project owner pushed back on the
    WiFi-flakiness writeup and asked "are you sure you didn't miss something"): this fixture used
    to POLL for a real IP by calling `board.exec()` in a loop every few seconds. Confirmed
    directly against mpremote's own source (`transport_serial.py`'s `enter_raw_repl()`): entering
    raw REPL with the default `soft_reset=True` sends a literal Ctrl-D and waits for the real
    "soft reboot" banner - this is a genuine `machine.soft_reset()`, which (confirmed against the
    pinned MicroPython C source, `ports/rp2/main.c`) tears down the *entire* running Python VM/
    heap and re-executes `_boot.py`/`boot.py`/`main.py` from scratch, killing whatever WiFi
    connection attempt (or established connection) `sensortask_wozi.main()`'s own already-running
    `AsyConnTime` task was mid-way through. Meanwhile `cyw43_init()` only runs once, before the
    soft-reset loop (same source) - the CYW43 chip's own firmware-level radio state is untouched
    by a soft reset. Net effect: a polling loop built entirely out of `board.exec()` calls was, on
    every single poll, destructively restarting the very reconnection attempt it was waiting to
    see finish - self-inflicted churn that plausibly explains a meaningfully worse real-world
    success rate through this fixture than through a plain, undisturbed `hard_reset()` (see
    tests_hardware/README.md's "First real run" list, which used no `board.exec()` polling at all
    and reproduced a real, independent hardware/firmware-level flakiness at a lower rate - that
    finding stands; this fixture's own polling was very likely making things meaningfully worse
    on top of it, not the whole explanation for it).

    FOURTH REAL FINDING, fixed (supersedes the "single exec() call" fix originally described here):
    a single `board.exec()` call is not actually safe either. Empirically confirmed on real
    hardware (an A/B test: `exec "..."` alone vs. `exec "..." soft-reset` vs. `run <script>
    soft-reset` - all three left the board completely silent afterward, no `main.py` output at
    all, for as long as observed): entering raw REPL sets the interpreter's `pyexec_mode_kind` to
    `RAW_REPL`; `ports/rp2/main.c`'s own soft-reset path only re-runs `main.py` when
    `pyexec_mode_kind == PYEXEC_MODE_FRIENDLY_REPL`. A trailing `soft-reset` command (or
    `run_isolated()`'s `soft_reset_after=True`) returns the connection to an idle friendly-REPL
    *prompt*, but does not retroactively make the *already-completed* soft-reset's boot sequence
    re-check that condition - `main.py` stays stopped. This directly answers (the wrong way) this
    tier's own long-standing open question, `harness.py`'s `run_isolated()` docstring's "NEEDS
    VERIFICATION ON FIRST REAL RUN" note and this file's "First real run" list item 1 - both
    assumed the trailing soft-reset "hands the board back to its normal auto-booted state"; it
    does not. That assumption was harmless everywhere else in this tier (every isolated-driver
    test constructs its own driver objects directly and never depends on the live `main.py`
    system still running afterward) but is exactly wrong for this fixture's own purpose. Only a
    genuine `hard_reset()` (a real `machine.reset()`, confirmed throughout this session to
    reliably resume normal auto-boot - the RP2040 restarts from its own reset vector, where
    `pyexec_mode_kind` starts fresh at its compiled-in `FRIENDLY_REPL` default) is safe to use here.

    Fixed: this fixture now never calls `board.exec()`/`board.run_isolated()` while expecting
    `main.py` to keep running afterward. It passively watches (`board.tail_log()`, which opens the
    serial port directly and sends nothing) for `asy_wifi_service.py`'s own real log lines ("WLAN
    connection established" / "Permanently no WLAN connection - activating hotspot!"). Reading the
    actual IP back still needs one `board.exec()` call - unavoidable, no other way to ask the
    running interpreter for `network.WLAN(...).ifconfig()` - so that call is always immediately
    followed by a real `board.hard_reset()` to resume normal operation before anything else uses
    the board. Since the CYW43 chip's own already-good radio association survives a soft reset
    (it's the *chip*, not `main.py`, that stays connected) and only `main.py`'s own object graph
    needed rebuilding, the post-hard_reset reconnect is expected to be the same "already
    associated, `_run_sta_mode()`'s fast isconnected() path" case, not a fresh cold connect - still
    given the same hard_reset()-retry tolerance as everywhere else in this fixture, since it's
    still a real reconnect attempt subject to the same underlying flakiness either way.

    SECOND REAL FINDING, fixed earlier: having a real STA IP does NOT mean the webserver is
    already serving - confirmed directly, real hardware: `sensortask_wozi.main()` only starts the
    webserver's own task (via `start_and_check_tasks()`) *after* `ntp_force_sync()`, which is
    itself bounded by a 20s `asyncio.wait_for()` - so a fresh boot can have a fully-connected STA
    IP for up to ~20s before anything is listening on port 80. Fixed by waiting for actual HTTP
    reachability (a real `GET /status`), not just link-level connectivity - this is what every
    caller of this fixture actually needs anyway, per this fixture's own docstring purpose.

    FIRST REAL FINDING, fixed earlier: a real, not-yet-fully-root-caused WiFi reconnection
    flakiness exists on this bench unit (see tests_hardware/README.md's "First real run" list for
    the full investigation). A single bad boot used to fail this fixture outright, which - being
    session-scoped - then cascaded into every other bench test failing/erroring for a reason with
    nothing to do with what that test actually checks. Fixed the same way `joined_hotspot`'s own
    fixture teardown already recovers from an analogous stuck-state risk: one bounded
    `hard_reset()` retry before giving up for real. None of these three fixes paper over the
    underlying flakiness (still fully documented and still worth the project owner's attention) -
    they stop this fixture's own mechanics from making it worse than it has to be."""
    ip_holder: list[str] = []

    def _read_ip_and_resume() -> bool:
        # This call itself strands main.py (see this fixture's own docstring) - always followed
        # immediately by a real hard_reset() to resume normal operation, never left dangling.
        try:
            output = board.exec(
                "import network\n"
                "w = network.WLAN(network.STA_IF)\n"
                "print('DUT_IP=' + (w.ifconfig()[0] if w.isconnected() else ''))",
                timeout_s=15.0,
            )
        finally:
            board.hard_reset()
        for line in output.splitlines():
            if line.startswith("DUT_IP=") and len(line) > len("DUT_IP="):
                ip_holder.append(line[len("DUT_IP=") :].strip())
                return True
        return False

    def _check_http_ready() -> bool:
        return http_client.fetch(ip_holder[-1], 80, "GET", "/status", timeout_s=5.0).status_code == 200

    def _wait_for_sta_ip(timeout_s: float) -> None:
        # Purely passive - never touches the board via exec()/run(), which would strand main.py
        # (see this fixture's own docstring). board.hard_reset() must have already put the board
        # into a real, currently-booting state before this is called.
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

    board.hard_reset()  # start from a known, genuinely-booting state - see this fixture's own docstring on why only a real hard_reset() is safe here
    try:
        _wait_for_ip_and_http(60.0)
    except (TimeoutError, HardwareTestFailure):
        board.hard_reset()
        _wait_for_ip_and_http(60.0, description_suffix=" (after one hard_reset() retry - see this fixture's own docstring)")
    return ip_holder[-1]
