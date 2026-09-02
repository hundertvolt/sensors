#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Assembles a real, deployable firmware.uf2 from src/ + ext/microdot.py + the real website
(scripts/build_website.sh) for one device (SPECIFICATION.md Part B.11). This script's own
automated checks (this module's own docstring used to say so) are build-only - "compiles clean and
produces a firmware.uf2", not an on-device functional check - but `tests_hardware/flash/
test_toolchain_flash_boot.py::test_real_uf2_reflash_and_boot_smoke_test` (gated behind
`--allow-flash-cycle`, a deliberate real flash cycle) DOES exercise this script's own output on
real hardware, and the first time it actually ran (this session) it immediately caught a real bug
here - see build_stage_dir()'s own comment for the full account (a UF2 that "built clean" per this
script's own checks left the board unable to mount its filesystem or run any application at all).
Treat this script's own success as necessary, not sufficient, for a real device to actually boot.

What gets frozen, and why this needs its own manifest.py rather than reusing the board's default
one (boards/RPI_PICO_W/manifest.py -> boards/manifest.py): that default manifest's own
`freeze("$(PORT_DIR)/modules")` line freezes ports/rp2/modules/_boot.py (the port's stock
filesystem-mount boot file) under the frozen name "_boot.py" - the exact name
shared/runtime/pyexec.c's rp2 main.c looks up via `pyexec_frozen_module("_boot.py", ...)` at every
boot (confirmed directly against the pinned v1.28.0 source, same verification standard as every
other MicroPython-facing fact in this repo - see CLAUDE.md's "Platform target" section). src/'s own
real entry point needs a _boot.py that imports `wozi_boot` (boot_entry/wozi_boot.py, this repo's
own "the real 'import triggers boot' behavior" module) instead of anything from ports/rp2/modules -
freezing a second, different file under the same "_boot.py" name via a second freeze() call would
either collide with or silently shadow the default manifest's own copy, so this script skips
including the board's default manifest.py entirely and instead re-states its other `require()`s
verbatim (bundle-networking, aioble, asyncio, onewire, ds18x20, dht, neopixel) alongside its own
single freeze() of a self-built staging directory. See _BOOT_PY below for the new boot file's own
content - the *port's own stock* ports/rp2/modules/_boot.py content plus one added `import
wozi_boot` line (no literal ".py" - unlike the still-unresolved BACKLOG.md #1 case, this is new
code, free to do it the documented way) - this repo's own top-level modules/_boot.py is never read,
copied from, or touched by this script, per CLAUDE.md's hard rule.

REAL FINDING, confirmed on real hardware (see build_stage_dir()'s own comment for the full
account): skipping `freeze("$(PORT_DIR)/modules")` entirely also drops ports/rp2/modules/rp2.py -
the pure-Python module _boot.py's own `import machine, rp2` line needs (a separate module from the
low-level `_rp2` C extension) - not just this script's replaced _boot.py. build_stage_dir() now
copies that one file into the same staging directory unmodified alongside its own generated
_boot.py, so it freezes normally without needing a second manifest freeze() call at all.

Usage (from anywhere, via uv):

    uv run scripts/build_firmware.py wozi
    uv run scripts/build_firmware.py wozi --output build/firmware-wozi.uf2
"""

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

# The port's own stock ports/rp2/modules/_boot.py content (confirmed directly against the pinned
# v1.28.0 checkout - identical to what boards/manifest.py's freeze("$(PORT_DIR)/modules") would
# otherwise freeze), plus the one line that makes it ours: importing boot_entry/wozi_boot.py's
# real entry point instead of leaving the filesystem mounted with nothing to run.
_BOOT_PY = '''\
import vfs
import machine, rp2

# Try to mount the filesystem, and format the flash if it doesn't exist.
# Note: the flash requires the programming size to be aligned to 256 bytes.
bdev = rp2.Flash()
try:
    fs = vfs.VfsLfs2(bdev, progsize=256)
except:
    vfs.VfsLfs2.mkfs(bdev, progsize=256)
    fs = vfs.VfsLfs2(bdev, progsize=256)
vfs.mount(fs, "/")

del vfs, bdev, fs

import wozi_boot
'''

# Mirrors boards/RPI_PICO_W/manifest.py + boards/manifest.py combined, minus their own
# freeze("$(PORT_DIR)/modules") line (see this file's own docstring for why) - the {stage_dir}
# freeze() below takes over that one job with our own boot file instead.
_MANIFEST_TEMPLATE = '''\
include("$(MPY_DIR)/extmod/asyncio")
require("onewire")
require("ds18x20")
require("dht")
require("neopixel")
require("bundle-networking")
require("aioble")
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


def build_stage_dir(stage_dir: Path, device: str, micropython_dir: Path) -> None:
    # This script freezes src/*.py alongside its own infra files (microdot.py, wozi_boot.py,
    # _boot.py, frozen_html.py, rp2.py) into the SAME flat stage_dir - a future src/ file sharing
    # one of those names would be silently overwritten (or would silently overwrite the infra file
    # copied after it) with no error, shipping wrong firmware content. Fail loud instead.
    reserved = {"microdot.py", "wozi_boot.py", "_boot.py", "frozen_html.py", "rp2.py"}
    src_files = sorted((REPO_ROOT / "src").glob("*.py"))
    collisions = reserved & {f.name for f in src_files}
    if collisions:
        raise RuntimeError(f"src/ file(s) collide with this build's own reserved staging names: {sorted(collisions)}")

    for py_file in src_files:
        _stage_stripped(py_file, stage_dir / py_file.name)
    _stage_stripped(REPO_ROOT / "ext" / "microdot.py", stage_dir / "microdot.py")
    _stage_stripped(REPO_ROOT / "boot_entry" / "wozi_boot.py", stage_dir / "wozi_boot.py")
    (stage_dir / "_boot.py").write_text(_BOOT_PY)
    # REAL FINDING, confirmed on real hardware (a genuine flash+boot smoke test - the very check
    # this module's own docstring says this tooling never does - immediately failed): omitting the
    # board's default manifest.py entirely (see this module's docstring for why) also throws away
    # its own `freeze("$(PORT_DIR)/modules")` line - which doesn't just freeze this script's own
    # replaced _boot.py, it ALSO freezes ports/rp2/modules/rp2.py, the pure-Python module providing
    # the friendly `rp2.Flash`/`rp2.PIO`/etc. names our own _BOOT_PY's `import machine, rp2` line
    # depends on (the low-level C extension is a separate, differently-named module - confirmed
    # directly, `import rp2` raised ImportError while `_rp2` remained importable). Without it,
    # _boot.py's own `rp2.Flash()` call fails before the filesystem is ever mounted, silently
    # dropping to a bare, unmounted REPL with no application ever starting - no build-time error or
    # warning of any kind (matching this module's own "verified means compiles clean, not an
    # on-device check" caveat exactly). ports/rp2/modules/_boot_fat.py (the FAT-filesystem
    # alternative to this board's real lfs2 _boot.py) is deliberately NOT staged here - unused by
    # this board, and this script's own _BOOT_PY already fully replaces the lfs2 variant.
    shutil.copy(micropython_dir / "ports" / "rp2" / "modules" / "rp2.py", stage_dir / "rp2.py")

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
        build_stage_dir(stage_dir, args.device, micropython_dir)

        manifest_path = tmp_path / "manifest.py"
        manifest_path.write_text(_MANIFEST_TEMPLATE.format(stage_dir=str(stage_dir)))

        # st.build_firmware() already wipes ports/rp2/build-{board} unconditionally before every
        # call (its own shutil.rmtree()) - the one directory that doesn't self-clean per build is
        # mpy-cross's own build/ (st.build_mpy_cross() relies on make's incremental rebuild
        # instead, same as toolchain/setup_toolchain.py's own default flow). Wiped here too so a
        # firmware build never depends on a previous session's mpy-cross artifacts.
        #
        # REAL FINDING, confirmed via CI (firmware-build-verify): wiping mpy-cross/build/ alone,
        # without an explicit rebuild, breaks the rp2 port's own BUILD_FROZEN_CONTENT step - it
        # invokes mpy-cross as an implicit sub-build to cross-compile the frozen manifest, which
        # (from a wiped build/ dir specifically) fails to regenerate `mp_qstr_frozen_const_pool`,
        # a linker error ("undefined reference to `mp_qstr_frozen_const_pool'") that only surfaces
        # here, never in a plain `st.build_mpy_cross()` standalone call. st.clean_build_dirs()
        # never hits this: every one of its callers immediately follows it with a full setup() that
        # explicitly calls st.build_mpy_cross() again (its own step 2) before anything else ever
        # touches mpy-cross - the earlier comment here ("mirrors st.clean_build_dirs()'s own
        # handling") only mirrored the wipe half of that pattern, not the required rebuild half.
        # Fixed the same way: rebuild mpy-cross explicitly, through the same already-proven
        # st.build_mpy_cross() path, right after wiping it and before it's ever needed again.
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
