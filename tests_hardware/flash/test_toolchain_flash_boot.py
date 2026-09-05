"""Flash-tier automated tests, Part 1 category E/G subset (tmp_hardware_test_candidates.md items
19, 20, 23) - real toolchain/flash/boot checks, run after the one-time physical setup
(HARDWARE_TEST_PLAN.md §6.1). Item 20 (a real UF2 flash-and-boot smoke test) is gated behind
`--allow-flash-cycle` and its own `flash_cycle` marker - it IS the one deliberate re-provisioning
flash HARDWARE_TEST_PLAN.md §6.1 allows, never something the routine automated pass should trigger
on its own."""

from __future__ import annotations

import subprocess
import time

import pytest
from harness import REPO_ROOT, Board, HardwareTestFailure, wait_until

# ---------------------------------------------------------------------------
# Item 23 - scripts/mpremote_connect.sh connection-stability baseline. Cheap, run first: every
# other test in this tier assumes basic mpremote connectivity already works.
# ---------------------------------------------------------------------------


def test_mpremote_connection_is_stable_across_repeated_calls(board: Board) -> None:
    failures = [i for i in range(5) if not board.is_reachable()]
    assert not failures, f"mpremote connection failed on attempt(s) {failures} out of 5 consecutive calls to {board.device}"


# ---------------------------------------------------------------------------
# Item 19 - `env --tier flash`/`--tier bench` recurring verification: after the one-time physical
# attach (BACKLOG.md), re-running `env --tier flash` must be a clean, idempotent no-op.
# ---------------------------------------------------------------------------


def test_env_tier_flash_recurring_run_is_idempotent(board: Board) -> None:
    # REAL FINDING: "idempotent" here means "same result on a re-run," not "fast" - run_setup()
    # (SPECIFICATION.md Part B.3) always re-verifies from scratch: a fresh git fetch, a full
    # picotool CMake+make rebuild (build_and_install_picotool() unconditionally rmtree()s its own
    # build dir first), and a full mpy-cross/Unix-port/firmware freeze-verify pass - never a
    # no-op short-circuit. Confirmed directly: a real run on this bench's Raspberry Pi 4 took
    # ~481s wall clock (8m33s of CPU time across 4 cores) with nothing else needing to change -
    # the original 300s timeout was calibrated for faster (x86, or more cores) dev/CI hardware,
    # not a Pi4 doing real parallel compilation. 1200s leaves comfortable headroom without being
    # so generous a genuine hang would go unnoticed for a very long time.
    proc = subprocess.run(
        ["uv", "run", "toolchain/setup_toolchain.py", "env", "--tier", "flash", "--device", board.device],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    assert proc.returncode == 0, f"env --tier flash re-run failed (exit {proc.returncode}):\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


# ---------------------------------------------------------------------------
# Item 20 - real UF2 flash-and-boot smoke test on an already-provisioned, already-running board
# (the BOOTSEL-button first-ever flash is Part 2 item 8, genuinely manual - a blank board has no
# already-running firmware to trigger machine.bootloader() from). Deliberate re-provisioning only.
# ---------------------------------------------------------------------------


@pytest.mark.flash_cycle
def test_real_uf2_reflash_and_boot_smoke_test(board: Board, request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--allow-flash-cycle"):
        pytest.skip("this IS a real flash cycle (HARDWARE_TEST_PLAN.md §6.1) - pass --allow-flash-cycle to deliberately run it")

    # dev, never wozi - wozi is never physically flashed (CLAUDE.md's hard rule), and its
    # hardcoded pins don't match this bench's real wiring.
    uf2_path = REPO_ROOT / "build" / "firmware-dev.uf2"
    build = subprocess.run(
        ["uv", "run", "scripts/build_firmware.py", "dev", "--output", str(uf2_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, f"scripts/build_firmware.py failed (exit {build.returncode}):\n{build.stdout}\n{build.stderr}"
    assert uf2_path.exists(), f"build_firmware.py reported success but {uf2_path} doesn't exist"

    board.enter_bootloader()  # drops the already-running board into BOOTSEL/mass-storage mode
    # REAL FINDING, fixed (2026-09-04): this comment used to claim "a plain bounded wait" here, but
    # no such wait was ever actually implemented - picotool was called immediately after
    # enter_bootloader() with zero delay, racing the real USB BOOTSEL re-enumeration. Confirmed
    # directly, real hardware: a real run failed with picotool's own "No accessible RP-series
    # devices in BOOTSEL mode were found" (exit 249) - not a flaky one-off, a genuine missing-wait
    # bug. Retried here (bounded, short interval) rather than a single fixed sleep, since picotool
    # itself has no internal retry of its own for this - a real BOOTSEL enumeration delay varies by
    # run, and a bounded retry adapts to that instead of guessing one fixed number.
    load: subprocess.CompletedProcess[str] | None = None
    for _attempt in range(5):
        load = subprocess.run(
            ["sudo", "picotool", "load", "-x", "-v", str(uf2_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if load.returncode == 0:
            break
        time.sleep(2.0)
    assert load is not None
    if load.returncode != 0:
        raise HardwareTestFailure(f"picotool load -x -v {uf2_path} failed after 5 attempts (exit {load.returncode}):\n{load.stdout}\n{load.stderr}")

    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after real UF2 reflash")
