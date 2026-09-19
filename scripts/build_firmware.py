#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Assembles a real, deployable firmware.uf2 from a buildgen-generated device module + ext/microdot.py
+ the real website for one device (SPECIFICATION.md Part B.11). A clean build is necessary, not
sufficient, for a device to boot."""

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
from _strip_type_checking import strip_type_checking_blocks  # type: ignore[import-not-found]  # noqa: E402

# buildgen/ sits at the repo root beside scripts/, so it needs no sys.path entry of its own the
# way the toolchain scripts do - but this script runs from an arbitrary cwd, so REPO_ROOT itself
# still has to be on sys.path for `import buildgen` to resolve.
sys.path.insert(0, str(REPO_ROOT))
from buildgen.errors import BuildError  # noqa: E402
from buildgen.generate import generate_device  # noqa: E402

# Mirrors the two stock manifests combined: their require()s and freeze("$(PORT_DIR)/modules")
# are reused unchanged, and the {stage_dir} freeze() below adds our modules on top - including
# each device's generated boot entry, staged as "main.py" for the reason the docstring gives.
_MANIFEST_TEMPLATE = """\
include("$(PORT_DIR)/boards/{board}/manifest.py")
freeze({stage_dir!r})
"""


def log(msg: str) -> None:
    print(f"\n== {msg}")


def _stage_stripped(src_file: Path, dest: Path) -> None:
    # Strips this build's staged copy only, never the real src/ or ext/ file (CLAUDE.md's hard
    # rule; _strip_type_checking.py's docstring says why it is safe). A file with no
    # if TYPE_CHECKING: block is written back byte for byte.
    dest.write_text(strip_type_checking_blocks(src_file.read_text()))


def build_stage_dir(stage_dir: Path, device: str) -> None:
    # Every device needs its own devices/<device>.toml. Fail before staging anything, converting
    # buildgen's BuildError into a RuntimeError so this function's contract - RuntimeError on any
    # build-impossible condition - stays uniform across every failure mode below.
    device_toml = REPO_ROOT / "devices" / f"{device}.toml"
    try:
        generated = generate_device(device_toml, REPO_ROOT / "src", REPO_ROOT / "ext")
    except BuildError as e:
        raise RuntimeError(str(e)) from e

    # Resolves buildgen's computed frozen-module set (Part L.2) to real files, so only this
    # device's transitive closure is staged rather than every src/*.py - a genuinely smaller
    # firmware than before buildgen. Each module resolves to exactly one of src/ or ext/.
    module_files: dict[str, Path] = {}
    for module in generated.frozen_modules:
        src_file = REPO_ROOT / "src" / f"{module}.py"
        ext_file = REPO_ROOT / "ext" / f"{module}.py"
        if src_file.is_file():
            module_files[module] = src_file
        elif ext_file.is_file():
            module_files[module] = ext_file
        else:
            raise RuntimeError(f"buildgen computed {module!r} as a frozen module for device {device!r} but no matching file exists under src/ or ext/ - a buildgen bug, not a device misconfiguration")

    # Every resolved module is frozen alongside the infra files into one flat stage_dir, so a
    # future src/ file sharing one of those names would silently overwrite it or be overwritten,
    # shipping wrong firmware content with no error. Fail instead.
    entry_module = f"sensortask_{generated.model.device}"
    reserved = {"main.py", "frozen_html.py", f"{entry_module}.py"}
    collisions = reserved & {f"{m}.py" for m in module_files}
    if collisions:
        raise RuntimeError(f"generated module(s) for device {device!r} collide with this build's own reserved staging names: {sorted(collisions)}")

    for module, path in sorted(module_files.items()):
        _stage_stripped(path, stage_dir / f"{module}.py")

    # The generated device entry module and its boot entry: freshly generated text, never read
    # off disk, so nothing to strip. Frozen as "main.py" rather than "<device>_boot.py" for the
    # source-confirmed reason the docstring gives - a custom _boot.py would cost USB entirely.
    (stage_dir / f"{entry_module}.py").write_text(generated.module_source)
    (stage_dir / "main.py").write_text(generated.boot_entry_source)

    # The real website, built fresh for this device and frozen under the same "frozen_html" name
    # the generated entry module's own `import frozen_html` already expects (SPECIFICATION.md Part
    # A.9) - no generated-module change needed to pick up the real content instead of html_stub/.
    log(f"Building the real website for device={device!r}")
    subprocess.run(
        [str(REPO_ROOT / "scripts" / "build_website.sh"), device, str(stage_dir / "frozen_html.py")],
        cwd=REPO_ROOT,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("device", help='Device name, matching a devices/<device>.toml file, e.g. "wozi"')
    parser.add_argument("--output", type=Path, default=None, help="Output path for the built firmware.uf2 (default: build/firmware-<device>.uf2)")
    parser.add_argument(
        "--toolchain-dir",
        type=Path,
        default=Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain")),
        help="Directory holding the already-installed toolchain (see toolchain/setup_toolchain.py) - not built by this script",
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="Parallel make jobs")
    args = parser.parse_args()

    device_toml = REPO_ROOT / "devices" / f"{args.device}.toml"
    if not device_toml.is_file():
        print(f"error: no device definition at {device_toml}", file=sys.stderr)
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

        # mpy-cross's build/ does not self-clean per build the way ports/rp2/build-{board} does,
        # so it is wiped here - and must then be rebuilt explicitly, since the rp2 port's own
        # implicit sub-build fails from a freshly wiped directory (Part B.11).
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
    except (subprocess.CalledProcessError, st.SetupError, RuntimeError) as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
