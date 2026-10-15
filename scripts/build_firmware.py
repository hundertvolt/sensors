#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Assembles a real, deployable firmware.uf2 from a buildgen-generated device module + ext/microdot.py
+ the real website for one device (SPECIFICATION.md Part B.11). A clean build is necessary, not
sufficient, for a device to boot."""

# Usage (from anywhere, via uv): `uv run scripts/build_firmware.py <device>
# [--output build/firmware-<device>.uf2]`. Beside the image it writes its record
# (<output>.json): which build the board will carry.

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "toolchain"))
import micropython_overrides  # noqa: E402
import setup_toolchain as st  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _strip_type_checking import strip_type_checking_blocks  # type: ignore[import-not-found]  # noqa: E402

# buildgen/ sits at the repo root beside scripts/, so it needs no sys.path entry of its own the
# way the toolchain scripts do - but this script runs from an arbitrary cwd, so REPO_ROOT itself
# still has to be on sys.path for `import buildgen` to resolve.
sys.path.insert(0, str(REPO_ROOT))
from buildgen.definitions import definitions_for_toml  # noqa: E402
from buildgen.errors import BuildError  # noqa: E402
from buildgen.generate import generate_device  # noqa: E402
from buildgen.model import load_device  # noqa: E402
from buildgen.validate import device_max_connections  # noqa: E402
from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION, current_build_date  # noqa: E402

# Mirrors the two stock manifests combined: their require()s and freeze("$(PORT_DIR)/modules")
# are reused unchanged, and the {stage_dir} freeze() below adds our modules on top - including
# each device's generated boot entry, staged as "main.py" for the reason the docstring gives.
_MANIFEST_TEMPLATE = """\
include("$(PORT_DIR)/boards/{board}/manifest.py")
freeze({stage_dir!r})
"""


def _stage_stripped(src_file: Path, dest: Path) -> None:
    # Strips this build's staged copy only, never the real src/ or ext/ file (CLAUDE.md's hard
    # rule; _strip_type_checking.py's docstring says why it is safe). A file with no
    # if TYPE_CHECKING: block is written back byte for byte.
    dest.write_text(strip_type_checking_blocks(src_file.read_text()))


def build_stage_dir(stage_dir: Path, device: str, *, device_toml: "Path | None" = None, build_date: "str | None" = None) -> None:
    # Builds from devices/<device>.toml unless another TOML is given. Fail before staging anything,
    # converting buildgen's BuildError into a RuntimeError so this function's contract - RuntimeError
    # on any build-impossible condition - stays uniform across every failure mode below.
    toml = device_toml if device_toml is not None else REPO_ROOT / "devices" / f"{device}.toml"
    try:
        generated = generate_device(toml, REPO_ROOT / "src", REPO_ROOT / "ext", build_date=build_date)
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

    # The generated module carries src/'s own TYPE_CHECKING form, so it is stripped like them. The
    # autostart boot entry is frozen as "main.py", never a custom _boot.py: rp2 starts USB only after
    # _boot.py returns (SPECIFICATION.md Part B.11), and main() never returns.
    (stage_dir / f"{entry_module}.py").write_text(strip_type_checking_blocks(generated.module_source))
    (stage_dir / "main.py").write_text(generated.boot_entry_source)

    # This device's real website, frozen under the "frozen_html" name the generated entry module's
    # own `import frozen_html` expects (SPECIFICATION.md Part A.9).
    log(f"Building the real website for device={device!r}")
    subprocess.run(
        [str(REPO_ROOT / "scripts" / "build_website.sh"), device, str(stage_dir / "frozen_html.py")],
        cwd=REPO_ROOT,
        check=True,
    )


def log(msg: str) -> None:
    print(f"\n== {msg}")


def source_state(repo_root: Path) -> "tuple[str | None, bool | None]":
    # (HEAD commit, uncommitted changes present) of the tree an image is built from; (None, None)
    # where git cannot tell, so the record never claims a clean tree it could not check.
    git_bin = shutil.which("git")

    def git(*argv: str) -> "str | None":
        if git_bin is None:
            return None
        try:
            done = subprocess.run([git_bin, *argv], cwd=repo_root, capture_output=True, text=True, check=False, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return done.stdout if done.returncode == 0 else None

    head = git("rev-parse", "HEAD") if repo_root.is_dir() else None
    status = git("status", "--porcelain") if head is not None else None
    return (head.strip() if head is not None else None, bool(status.strip()) if status is not None else None)


def _uart_crc(device_toml: Path) -> "dict[str, str]":
    # Each UART bus's CRC mode, from the uart_link instances the image wires (none: "none").
    return {str(spec.fields["bus"]): str(spec.fields.get("crc", "none")) for spec in load_device(device_toml).instances.values() if spec.driver == "uart_link"}


def _overrides_in_build(build_dir: Path, micropython_dir: Path, toolchain_dir: Path) -> "list[str]":
    # The optional overrides the build proves compiled in, re-read from its own build dir: a control
    # image built without the modlwip override reads [] here. The copy path is st.build_firmware()'s.
    copy_path = toolchain_dir / "build_overrides" / micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME / micropython_overrides.MODLWIP_COPY_NAME
    try:
        micropython_overrides.verify_modlwip_eagain_in_build(build_dir, micropython_dir, copy_path)
    except micropython_overrides.OverrideError:
        return []
    return [micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME]


def _replace_written(path: Path, data: bytes) -> None:
    # Same-dir tmp plus os.replace, so `path` is either its old content or the whole new one.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_image(uf2: Path, output: Path, record: "dict[str, object]") -> None:
    # Never pairs a new image with an old record: the old record goes first, the image moves in
    # whole, the record comes last - a kill anywhere leaves no record or a matching one.
    record_path = output.with_suffix(".json")
    record_path.unlink(missing_ok=True)
    _replace_written(output, uf2.read_bytes())
    _replace_written(record_path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("device", help='Device name, matching a devices/<device>.toml file, e.g. "wozi"')
    parser.add_argument("--device-toml", type=Path, default=None, metavar="PATH", help="build from this copy of devices/<device>.toml, named <device>.toml (buildgen names the modules after it); it may change only what the website does not show, e.g. a UART link's crc")
    parser.add_argument("--output", type=Path, default=None, help="Output path for the built firmware.uf2 (default: build/firmware-<device>.uf2); its image record lands beside it as .json")
    parser.add_argument(
        "--toolchain-dir",
        type=Path,
        default=Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain")),
        help="Directory holding the already-installed toolchain (see toolchain/setup_toolchain.py) - not built by this script",
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="Parallel make jobs")
    args = parser.parse_args()
    # One absolute path for the lock, the record and every path the build writes into generated files.
    args.toolchain_dir = args.toolchain_dir.expanduser().resolve()

    device_toml = (args.device_toml or REPO_ROOT / "devices" / f"{args.device}.toml").resolve()
    if not device_toml.is_file():
        print(f"error: no device definition at {device_toml}", file=sys.stderr)
        return 1
    if device_toml.stem != args.device:
        print(f"error: {device_toml} builds device {device_toml.stem!r}, not {args.device!r} - name the copy {args.device}.toml", file=sys.stderr)
        return 1
    # scripts/build_website.sh builds the website from devices/<device>.toml, so a copy may change
    # only what the website does not show (a UART link's crc), or image and page would disagree.
    repo_toml = REPO_ROOT / "devices" / f"{args.device}.toml"
    if device_toml != repo_toml and definitions_for_toml(device_toml, REPO_ROOT / "src") != definitions_for_toml(repo_toml, REPO_ROOT / "src"):
        print(f"error: {device_toml} changes what the website shows, but the website is built from {repo_toml} - change only what the definitions do not carry", file=sys.stderr)
        return 1

    versions = st.load_versions(REPO_ROOT / "toolchain" / "versions.toml")
    board = versions["toolchain"]["board"]
    micropython_dir = args.toolchain_dir / "micropython"
    if not (micropython_dir / "ports" / "rp2").is_dir():
        print(f"error: no MicroPython checkout at {micropython_dir} - run `uv run toolchain/setup_toolchain.py setup` first", file=sys.stderr)
        return 1

    output = args.output or (REPO_ROOT / "build" / f"firmware-{args.device}.uf2")
    output.parent.mkdir(parents=True, exist_ok=True)

    # One date for the staged module and the image record, so a board's /system names this build.
    build_date = current_build_date()

    # One build or setup at a time per toolchain directory, held until the image record is written;
    # setup deletes its record first and writes it last, so a directory without one is unfinished.
    with st.toolchain_lock(args.toolchain_dir):
        record = st.read_toolchain_record(args.toolchain_dir)
        if record is None:
            print(f"error: the toolchain at {args.toolchain_dir} is incomplete or predates the build record - run `uv run toolchain/setup_toolchain.py setup` first", file=sys.stderr)
            return 1
        # A record may carry no built ref (a `test` run with none to carry over): the pinned ref is printed, marked so.
        built = record["built_ref"] or f"{record['pinned_ref']} as pinned (built by `test`, ref not recorded)"
        log(f"Toolchain: MicroPython {built} ({record['micropython_commit']}), recorded in {args.toolchain_dir / st.TOOLCHAIN_RECORD}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # The staged modules and the generated manifest.py live in separate sibling directories -
            # same reason write_freeze_manifest() keeps FROZEN_MODULE_SUBDIR out of the manifest's own
            # directory: freeze()'s own directory walk must never pick up manifest.py itself.
            stage_dir = tmp_path / "stage"
            stage_dir.mkdir()
            build_stage_dir(stage_dir, args.device, device_toml=device_toml, build_date=build_date)

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
            uf2 = st.build_firmware(micropython_dir, board, args.jobs, frozen_manifest=manifest_path, toolchain_dir=args.toolchain_dir)
            # Both readers take the port's build dir beside the uf2 it returned, never the copy.
            commit, dirty = source_state(REPO_ROOT)
            image_record: dict[str, object] = {
                "device": args.device,
                "BuildDate": build_date,
                "firmwareVersion": FIRMWARE_VERSION,
                "websiteVersion": WEBSITE_VERSION,
                "commit": commit,
                "dirty": dirty,
                "maxConnections": device_max_connections(device_toml, REPO_ROOT / "src"),
                "lwip": micropython_overrides.read_lwip_macros_from_build(uf2.parent, st.load_lwip_macros()),
                "overrides": _overrides_in_build(uf2.parent, micropython_dir, args.toolchain_dir),
                "deviceToml": device_toml.relative_to(REPO_ROOT).as_posix() if device_toml.is_relative_to(REPO_ROOT) else str(device_toml),
                "uartCrc": _uart_crc(device_toml),
            }
            write_image(uf2, output, image_record)

    print(f"\nWrote {output} and its image record {output.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, st.SetupError, subprocess.CalledProcessError) as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
