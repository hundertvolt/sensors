#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyserial"]
# ///
"""Builds one GC-policy variant of the dev firmware and flashes it to the attached bench board.
Deliberately dev-only: wozi is never physically flashed (CLAUDE.md). Used by
scripts/run_bench_gc_matrix.sh to move the board between the matrix's passes."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests_hardware"))
sys.path.insert(0, str(REPO_ROOT))

from harness import Board, wait_until  # noqa: E402

from buildgen.gc_policy import DEFAULT_GC_POLICY, GC_POLICIES  # noqa: E402

DEVICE = "dev"


def build(gc_policy: str, output: Path, *, memory_pressure: bool) -> None:
    cmd = ["uv", "run", "scripts/build_firmware.py", DEVICE, "--gc-policy", gc_policy, "--output", str(output)]
    if memory_pressure:
        cmd.append("--memory-pressure")
    print(f"== Building {output.name} (gc_policy={gc_policy}, memory_pressure={memory_pressure})")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"build failed (exit {proc.returncode})")
    if not output.exists():
        raise SystemExit(f"build reported success but {output} does not exist")


def flash(board: Board, uf2: Path) -> None:
    print(f"== Flashing {uf2.name}")
    board.enter_bootloader()
    # picotool has no internal retry for BOOTSEL re-enumeration - same bounded retry
    # tests_hardware/flash/test_toolchain_flash_boot.py uses, for the same race.
    for _attempt in range(5):
        load = subprocess.run(["sudo", "picotool", "load", "-x", "-v", str(uf2)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120, check=False)
        if load.returncode == 0:
            break
        time.sleep(2.0)
    else:
        raise SystemExit(f"picotool load failed after 5 attempts:\n{load.stdout}\n{load.stderr}")
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after reflash")
    print(f"== Flashed {uf2.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gc-policy", choices=GC_POLICIES, default=DEFAULT_GC_POLICY)
    parser.add_argument("--memory-pressure", action="store_true")
    parser.add_argument("--device", default=None, help="serial device path (default: $MPREMOTE_DEVICE or /dev/ttyACM0)")
    parser.add_argument("--skip-build", action="store_true", help="flash an already-built uf2 for this variant")
    args = parser.parse_args()

    suffix = "" if args.gc_policy == DEFAULT_GC_POLICY else f"-{args.gc_policy}"
    if args.memory_pressure:
        suffix += "-pressure"
    uf2 = REPO_ROOT / "build" / f"firmware-{DEVICE}{suffix}.uf2"

    if not args.skip_build:
        build(args.gc_policy, uf2, memory_pressure=args.memory_pressure)
    board = Board(device=args.device)
    flash(board, uf2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
