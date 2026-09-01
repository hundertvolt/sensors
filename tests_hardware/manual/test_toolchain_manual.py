"""Manual test, Part 2 category D (tmp_hardware_test_candidates.md item 8): the one genuinely
first-time-only manual step in an otherwise fully-automated real-hardware pass (HARDWARE_TEST_PLAN.md
§6.1) - a blank board has no already-running firmware to trigger machine.bootloader() from, so its
very first flash needs a human holding BOOTSEL. Every subsequent flash of that same board is
tests_hardware/flash/test_toolchain_flash_boot.py's automated (`--allow-flash-cycle`-gated) path."""

from __future__ import annotations

import subprocess

from harness import REPO_ROOT
from runner import confirm, print_instruction, register, state_expected_outcome


@register(
    "first_ever_uf2_flash_of_a_blank_board",
    "Hold BOOTSEL while plugging in USB (no already-running firmware to trigger machine.bootloader() from) - confirms the board re-enumerates as mass storage and accepts the real build_firmware.py UF2.",
    "[USB][MANUAL]",
)
def test_first_ever_uf2_flash_of_a_blank_board() -> None:
    uf2_path = REPO_ROOT / "build" / "firmware-wozi.uf2"
    print_instruction(f"Building the real production UF2 first (uv run scripts/build_firmware.py wozi --output {uf2_path})...")
    build = subprocess.run(
        ["uv", "run", "scripts/build_firmware.py", "wozi", "--output", str(uf2_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if build.returncode != 0:
        raise AssertionError(f"scripts/build_firmware.py failed (exit {build.returncode}):\n{build.stdout}\n{build.stderr}")

    print_instruction("Disconnect the blank board's USB cable if it's currently connected.")
    confirm("Press Enter once disconnected")
    print_instruction("Hold the BOOTSEL button down, THEN plug the USB cable back in while still holding it. Keep holding for 2 more seconds after plugging in.")
    confirm("Press Enter once you've held BOOTSEL through the plug-in and released it")
    state_expected_outcome("the board enumerates as a USB mass-storage device (e.g. a drive named RPI-RP2 appears) - check this before continuing.")
    confirm("Press Enter once you've confirmed the mass-storage device appeared")

    print_instruction("Copying the UF2 to the mass-storage device now via picotool.")
    load = subprocess.run(["sudo", "picotool", "load", "-x", "-v", str(uf2_path)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    if load.returncode != 0:
        raise AssertionError(f"picotool load -x -v {uf2_path} failed (exit {load.returncode}):\n{load.stdout}\n{load.stderr}")
    state_expected_outcome("the board reboots on its own into the real firmware and starts running normally (visible in a serial monitor as the usual boot log lines).")
    confirm("Press Enter once you've confirmed the board is running normally")
