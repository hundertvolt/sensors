#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Assembles a real, deployable firmware.uf2 from src/ + ext/microdot.py + the real website for
one device (SPECIFICATION.md Part B.11, including why boot_entry/<device>_boot.py is frozen under
the literal name "main.py"). A clean build is necessary, not sufficient, for a device to boot."""

# Usage (from anywhere, via uv):
#     uv run scripts/build_firmware.py wozi
#     uv run scripts/build_firmware.py wozi --output build/firmware-wozi.uf2

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "toolchain"))
import setup_toolchain as st  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _strip_type_checking import strip_type_checking_blocks  # noqa: E402

# Mirrors boards/RPI_PICO_W/manifest.py + boards/manifest.py combined - the default manifest's own
# require()s and its freeze("$(PORT_DIR)/modules") (the stock, always-returns _boot.py + rp2.py)
# are reused unchanged; {stage_dir} freeze() below adds our own modules on top, including each
# device's boot_entry/<device>_boot.py content staged under the literal name "main.py" (see this
# file's own docstring for why).
_MANIFEST_TEMPLATE = '''\
include("$(PORT_DIR)/boards/{board}/manifest.py")
freeze({stage_dir!r})
'''


def log(msg: str) -> None:
    print(f"\n== {msg}")


def _stage_stripped(src_file: Path, dest: Path) -> None:
    # Strips this build's temp staged copy only - never the real src/ext files (CLAUDE.md's
    # hard rule; see _strip_type_checking.py's own docstring for why this is safe and what it
    # saves). A file with no if TYPE_CHECKING: blocks (e.g. ext/microdot.py today) is written back
    # byte-for-byte unchanged.
    dest.write_text(strip_type_checking_blocks(src_file.read_text()))


def build_stage_dir(stage_dir: Path, device: str) -> None:
    # Every device needs its own boot_entry/<device>_boot.py real entry point (see
    # boot_entry/wozi_boot.py's/boot_entry/dev_boot.py's own docstrings). Fail loud, before staging
    # anything, if the device this build was asked for has no boot entry point at all.
    boot_module = f"{device}_boot"
    boot_entry_file = REPO_ROOT / "boot_entry" / f"{boot_module}.py"
    if not boot_entry_file.is_file():
        raise RuntimeError(f"no boot_entry/{boot_module}.py for device {device!r} - every device needs its own boot_entry/<device>_boot.py")

    # This script freezes src/*.py alongside its own infra files (microdot.py, main.py,
    # frozen_html.py) into the SAME flat stage_dir - a future src/ file sharing one of those names
    # would be silently overwritten (or would silently overwrite the infra file copied after it)
    # with no error, shipping wrong firmware content. Fail loud instead.
    reserved = {"microdot.py", "main.py", "frozen_html.py"}
    src_files = sorted((REPO_ROOT / "src").glob("*.py"))
    collisions = reserved & {f.name for f in src_files}
    if collisions:
        raise RuntimeError(f"src/ file(s) collide with this build's own reserved staging names: {sorted(collisions)}")

    for py_file in src_files:
        _stage_stripped(py_file, stage_dir / py_file.name)
    _stage_stripped(REPO_ROOT / "ext" / "microdot.py", stage_dir / "microdot.py")
    # Frozen under the literal name "main.py", not "<device>_boot.py" - see this module's own
    # docstring for the source-confirmed reason (pyexec_file_if_exists("main.py") checks the frozen
    # table before the filesystem, and runs after mp_usbd_init(); a custom _boot.py that never
    # returns means USB never initializes at all).
    _stage_stripped(boot_entry_file, stage_dir / "main.py")

    # The real website, built fresh for this device and frozen under the same "frozen_html" name
    # src/sensortask_wozi.py's own `import frozen_html` already expects (SPECIFICATION.md Part
    # A.9) - no src/ code change needed to pick up the real content instead of html_stub/.
    log(f"Building the real website for device={device!r}")
    subprocess.run(
        [str(REPO_ROOT / "scripts" / "build_website.sh"), device, str(stage_dir / "frozen_html.py")],
        cwd=REPO_ROOT,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("device", help='Device name, matching an html/definitions/<device>.json file, e.g. "wozi"')
    parser.add_argument("--output", type=Path, default=None, help="Output path for the built firmware.uf2 (default: build/firmware-<device>.uf2)")
    parser.add_argument(
        "--toolchain-dir",
        type=Path,
        default=Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain")),
        help="Directory holding the already-installed toolchain (see toolchain/setup_toolchain.py) - not built by this script",
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="Parallel make jobs")
    args = parser.parse_args()

    definitions_file = REPO_ROOT / "html" / "definitions" / f"{args.device}.json"
    if not definitions_file.is_file():
        print(f"error: no definitions file at {definitions_file}", file=sys.stderr)
        return 1

    versions = st.load_versions(REPO_ROOT / "toolchain" / "versions.toml")
    board = versions["toolchain"]["board"]
    micropython_dir = args.toolchain_dir / "micropython"
    if not (micropython_dir / "ports" / "rp2").is_dir():
        print(f"error: no MicroPython checkout at {micropython_dir} - run `uv run toolchain/setup_toolchain.py setup` first", file=sys.stderr)
        return 1

    output = args.output or (REPO_ROOT / "build" / f"firmware-{args.device}.uf2")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # The staged modules and the generated manifest.py live in separate sibling directories -
        # same reason write_freeze_manifest() keeps FROZEN_MODULE_SUBDIR out of the manifest's own
        # directory: freeze()'s own directory walk must never pick up manifest.py itself.
        stage_dir = tmp_path / "stage"
        stage_dir.mkdir()
        build_stage_dir(stage_dir, args.device)

        manifest_path = tmp_path / "manifest.py"
        manifest_path.write_text(_MANIFEST_TEMPLATE.format(board=board, stage_dir=str(stage_dir)))

        # mpy-cross's own build/ doesn't self-clean per build (unlike ports/rp2/build-{board}), so
        # it's wiped here too - but must be explicitly rebuilt right after, not left to the rp2
        # port's own implicit sub-build, which fails from a freshly-wiped dir (see SPECIFICATION.md
        # Part B.11's mpy-cross-rebuild finding).
        mpy_cross_build_dir = micropython_dir / "mpy-cross" / "build"
        if mpy_cross_build_dir.exists():
            log(f"Cleaning {mpy_cross_build_dir} before rebuilding")
            shutil.rmtree(mpy_cross_build_dir)
        st.build_mpy_cross(micropython_dir, args.jobs)

        log(f"Building firmware for BOARD={board}, device={args.device!r}")
        uf2 = st.build_firmware(micropython_dir, board, args.jobs, frozen_manifest=manifest_path)
        shutil.copy(uf2, output)

    print(f"\nWrote {output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (subprocess.CalledProcessError, st.SetupError) as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
