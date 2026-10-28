"""Flash-tier automated tests: real toolchain/flash/boot checks, run after the one-time physical setup. The UF2
flash-and-boot smoke test is gated behind `--allow-flash-cycle` and its `flash_cycle` marker, and the full toolchain
re-verification behind `--allow-toolchain-reverify`: neither runs in a routine pass."""

import subprocess
from typing import TYPE_CHECKING

import pytest
from harness import REPO_ROOT, reflash

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ()

# @tunable l3.toolchain_flash_boot_env_setup_timeout_s = 1200
_ENV_SETUP_TIMEOUT_S = 1200
# @tunable l3.toolchain_flash_boot_build_timeout_s = 600
_BUILD_TIMEOUT_S = 600
# @tunable l3.toolchain_flash_boot_reachability_calls = 5
_REACHABILITY_CALLS = 5


# mpremote connection stability: cheap and first, since every other check here assumes it.
def test_mpremote_connection_is_stable_across_repeated_calls(board: "Board") -> None:
    failures = [i for i in range(_REACHABILITY_CALLS) if not board.is_reachable()]
    assert not failures, f"mpremote connection failed on attempt(s) {failures} out of {_REACHABILITY_CALLS:g} consecutive calls to {board.device}"


# `env --tier flash` re-run: after the one-time physical attach, a clean, idempotent no-op.
@pytest.mark.toolchain_reverify
def test_env_tier_flash_recurring_run_is_idempotent(board: "Board", request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--allow-toolchain-reverify"):
        pytest.skip("a full toolchain re-verification: network fetches and ~8 min of builds; pass --allow-toolchain-reverify")
    # "Idempotent" is the same result on a re-run, not a fast one: run_setup() re-verifies from scratch (~481 s on the
    # bench Pi4), and 1200 s leaves headroom without masking a real hang.
    proc = subprocess.run(
        ["uv", "run", "--no-sync", "toolchain/setup_toolchain.py", "env", "--tier", "flash", "--device", board.device],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_ENV_SETUP_TIMEOUT_S,
        check=False,
    )
    assert proc.returncode == 0, f"env --tier flash re-run failed (exit {proc.returncode}):\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


# The UF2 flash-and-boot smoke test on a provisioned, running board; a blank board has no running firmware to enter
# the bootloader from, which is the manual first flash's case.
@pytest.mark.flash_cycle
def test_real_uf2_reflash_and_boot_smoke_test(board: "Board", bench_device_name: str, request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--allow-flash-cycle"):
        pytest.skip("this IS a real flash cycle - pass --allow-flash-cycle to deliberately run it")
    # The bench board's image, built from its own TOML (a dev-native proof; sessions flash only the bench board, CLAUDE.md).
    uf2_path = REPO_ROOT / "build" / f"firmware-{bench_device_name}.uf2"
    build = subprocess.run(
        ["uv", "run", "--no-sync", "scripts/build_firmware.py", bench_device_name, "--output", str(uf2_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_BUILD_TIMEOUT_S,
        check=False,
    )
    assert build.returncode == 0, f"scripts/build_firmware.py failed (exit {build.returncode}):\n{build.stdout}\n{build.stderr}"
    assert uf2_path.exists(), f"build_firmware.py reported success but {uf2_path} doesn't exist"
    assert uf2_path.with_suffix(".json").exists(), f"build_firmware.py wrote no image record beside {uf2_path}"
    reflash(board, uf2_path)
