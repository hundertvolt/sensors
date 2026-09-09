"""Flash-tier automated tests: real toolchain/flash/boot checks, run after the one-time physical
setup. The real UF2 flash-and-boot smoke test is gated behind `--allow-flash-cycle` and its own
`flash_cycle` marker - a deliberate re-provisioning flash, never triggered by a routine run."""

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
    # "Idempotent" means "same result on a re-run," not "fast" - run_setup() always re-verifies from
    # scratch (fresh git fetch, full picotool rebuild, full mpy-cross/Unix-port/firmware pass), which
    # takes ~481s wall clock on this bench's Pi4; 1200s leaves headroom without masking a real hang.
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
        pytest.skip("this IS a real flash cycle - pass --allow-flash-cycle to deliberately run it")

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
    # picotool has no internal retry for USB BOOTSEL re-enumeration (calling it immediately after
    # enter_bootloader() can race it, failing with exit 249) - bounded retry here instead of one
    # fixed sleep, since the real enumeration delay varies by run.
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
