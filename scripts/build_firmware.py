#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Assembles a deployable firmware.uf2 for one device: its generated module, the stripped src/ and ext/ modules it
imports and its website (SPECIFICATION.md Part B.11); --no-autostart freezes the REPL-start boot entry. Intermediates
stay in build/firmware/<device>/ until that device's next build. A clean build is necessary, not sufficient, to boot."""

# Usage: uv run scripts/build_firmware.py <device>
#        uv run scripts/build_firmware.py <device> --output build/firmware-<device>.uf2
# Beside the image it writes its record (<output>.json): which build the board will carry.

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "toolchain"))
import micropython_overrides  # noqa: E402 - the toolchain/ insert above makes it importable
import setup_toolchain as st  # noqa: E402 - the toolchain/ insert above makes it importable

sys.path.insert(0, str(REPO_ROOT))
from buildgen.definitions import definitions_for_toml  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.errors import BuildError, BuildInternalError  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.generate import GeneratedDevice, generate_device  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.model import load_device  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.validate import device_max_connections  # noqa: E402 - the repo-root insert above makes it importable
from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION, current_build_date  # noqa: E402 - the repo-root insert above makes it importable
from scripts._strip_type_checking import StripError, strip_type_checking_blocks  # noqa: E402 - the repo-root insert above makes it importable

# Each device's work directory (stage/ and manifest.py) lives here, wiped at its next build and kept after it.
WORK_ROOT = REPO_ROOT / "build" / "firmware"
_NO_AUTOSTART_SUFFIX = "-noautostart"
_FLASH_BASE = 0x10000000  # the RP2040's XIP flash window, where the image's first byte sits
_NM_FIELDS = 3  # a defined symbol's nm line: value, type, name

# freeze() of a directory walks it in the host filesystem's order (tools/manifestfile.py:317, v1.29.0), so every walk
# the board's manifests make is sorted, and the staged modules are named sorted: the image's frozen-module order is
# the same on every host (owner, 2026-10-05: 'Apart from that, everything shall be byte-identical.').
_MANIFEST_TEMPLATE = """\
import os as _os

_walk = _os.walk


def _sorted_walk(top, *args, **kwargs):
    for dirpath, dirnames, filenames in _walk(top, *args, **kwargs):
        dirnames.sort()
        filenames.sort()
        yield dirpath, dirnames, filenames


_os.walk = _sorted_walk
include("$(PORT_DIR)/boards/{board}/manifest.py")
freeze({stage_dir!r}, {files!r})
"""


@dataclass(frozen=True)
class ImageReport:
    # The image's flash use against the filesystem's first byte, read from the linked firmware.elf.
    used: int
    fs_base: int

    @property
    def free(self) -> int:
        return self.fs_base - self.used


def _stage_stripped(source: str, path: str, dest: Path) -> None:
    # Strips this build's staged copy only, never src/ or ext/; the stripper is line-preserving, so a field
    # traceback's line numbers equal the source's.
    dest.write_text(strip_type_checking_blocks(source, path), encoding="utf-8")


def _module_files(generated: GeneratedDevice) -> "dict[str, Path]":
    # buildgen's frozen set (Part L.2) resolved to files, each in exactly one of src/ and ext/.
    found: dict[str, Path] = {}
    for module in generated.frozen_modules:
        candidates = [root / f"{module}.py" for root in (REPO_ROOT / "src", REPO_ROOT / "ext") if (root / f"{module}.py").is_file()]
        if not candidates:
            raise BuildInternalError(f"buildgen computed {module!r} as a frozen module for device {generated.model.device!r} but no matching file exists under src/ or ext/")
        found[module] = candidates[0]
    return found


def stage_python_modules(stage_dir: Path, generated: GeneratedDevice, *, autostart: bool = True) -> None:
    # Every Python file the image freezes: the stripped src/ and ext/ modules, the generated device module through
    # the same strip, and the boot entry frozen as main.py (rp2 starts USB only after _boot.py returns, Part B.11).
    module_files = _module_files(generated)
    entry_module = f"sensortask_{generated.model.device}"
    collisions = {"main.py", "frozen_html.py", f"{entry_module}.py"} & {f"{m}.py" for m in module_files}
    if collisions:
        raise BuildInternalError(f"generated module(s) for device {generated.model.device!r} collide with this build's own reserved staging names: {sorted(collisions)}")
    for module, path in sorted(module_files.items()):
        _stage_stripped(path.read_text(encoding="utf-8"), str(path), stage_dir / f"{module}.py")
    _stage_stripped(generated.module_source, f"build/generated_src/{entry_module}.py", stage_dir / f"{entry_module}.py")
    entry = generated.boot_entry_source if autostart else generated.boot_entry_noautostart_source
    (stage_dir / "main.py").write_text(entry, encoding="utf-8")


# build_date is an input: real builds stamp their UTC build time, the reproducibility check passes a fixed one
# (owner, 2026-10-05: 'They must differ for being genuine.').
def build_stage_dir(stage_dir: Path, device_toml: Path, *, autostart: bool = True, build_date: "str | None" = None, test_overrides: "tuple[str, ...]" = ()) -> None:
    generated = generate_device(device_toml, REPO_ROOT / "src", REPO_ROOT / "ext", build_date=build_date, test_overrides=test_overrides)
    stage_python_modules(stage_dir, generated, autostart=autostart)
    # The site carries the module's own build date, so page and image name one build (frozen as frozen_html, Part A.9).
    device = generated.model.device
    log(f"Building the real website for device={device!r}")
    stamp = ["--build-date", build_date] if build_date is not None else []
    subprocess.run([str(REPO_ROOT / "scripts" / "build_website.sh"), *stamp, device, str(stage_dir / "frozen_html.py")], cwd=REPO_ROOT, check=True)


def render_manifest(board: str, stage_dir: Path) -> str:
    files = tuple(sorted(p.name for p in stage_dir.glob("*.py")))
    return _MANIFEST_TEMPLATE.format(board=board, stage_dir=str(stage_dir), files=files)


def image_report(build_dir: Path) -> ImageReport:
    # The four link symbols from firmware.elf beside the image, with the ARM nm the build itself runs on PATH.
    # The link already refuses an overlap (ports/rp2/memmap_rp2/memory_flash.incl), so one here is a toolchain bug.
    nm = shutil.which("arm-none-eabi-nm", path=st.BUILD_ENV_PATH)
    if nm is None:
        raise st.SetupError(f"arm-none-eabi-nm is not on {st.BUILD_ENV_PATH} - install the toolchain's apt packages (uv run toolchain/setup_toolchain.py setup)")
    listing = subprocess.run([nm, str(build_dir / "firmware.elf")], capture_output=True, text=True, check=True, timeout=120).stdout
    symbols = {parts[2]: int(parts[0], 16) for parts in (line.split() for line in listing.splitlines()) if len(parts) == _NM_FIELDS}
    wanted = ("__flash_binary_end", "__micropy_flash_size__", "__micropy_flash_storage_bytes__", "__micropy_romfs_bytes__")
    missing = [name for name in wanted if name not in symbols]
    if missing:
        raise BuildInternalError(f"{build_dir / 'firmware.elf'} carries no {', '.join(missing)} - the rp2 link no longer defines what the image report reads")
    report = ImageReport(used=symbols["__flash_binary_end"] - _FLASH_BASE, fs_base=symbols["__micropy_flash_size__"] - symbols["__micropy_flash_storage_bytes__"] - symbols["__micropy_romfs_bytes__"])
    if report.used > report.fs_base:
        raise BuildInternalError(f"image report shows an overlap of {report.used - report.fs_base} B the linker should have refused")
    return report


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
    # The optional overrides the build proves compiled in, re-read from its own build dir: a control image built
    # without the modlwip override reads none of it, the rollover round's test image names tick_offset_test.
    copy_path = toolchain_dir / "build_overrides" / micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME / micropython_overrides.MODLWIP_COPY_NAME
    found = []
    try:
        micropython_overrides.verify_modlwip_eagain_in_build(build_dir, micropython_dir, copy_path)
        found.append(micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME)
    except micropython_overrides.OverrideError:
        pass
    if micropython_overrides.tick_offset_in_build(build_dir):
        found.append(micropython_overrides.TICK_OFFSET_DIR_NAME)
    return found


def _replace_written(path: Path, data: bytes) -> None:
    # Same-dir tmp plus a rename over it, so `path` is either its old content or the whole new one.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def write_image(uf2: Path, output: Path, record: "dict[str, object]") -> None:
    # Never pairs a new image with an old record: the old record goes first, the image moves in
    # whole, the record comes last - a kill anywhere leaves no record or a matching one.
    record_path = output.with_suffix(".json")
    record_path.unlink(missing_ok=True)
    _replace_written(output, uf2.read_bytes())
    _replace_written(record_path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("device", help="a devices/<device>.toml stem")
    parser.add_argument("--device-toml", type=Path, default=None, metavar="PATH", help="build from this copy of devices/<device>.toml, named <device>.toml (buildgen names the modules after it); it may change only what the website does not show, e.g. a UART link's crc")
    parser.add_argument("--output", type=Path, default=None, help="Output path for the built firmware.uf2 (default: build/firmware-<device>.uf2, with -noautostart or -tickoffset before .uf2 for those images); its image record lands beside it as .json")
    parser.add_argument(
        "--no-autostart",
        action="store_true",
        help="freeze the boot entry that prints its manual start line and returns to the REPL instead of running main(); the board's filesystem must hold no boot.py/main.py (erase it first, see the reflash runbook) - a frozen entry that returns lets them run",
    )
    parser.add_argument(
        "--tick-offset-test",
        action="store_true",
        help="build the rollover round's test image: MicroPython's millisecond count starts 2**32 ms minus 15 minutes after boot (SPECIFICATION.md B.14); never a release image",
    )
    parser.add_argument(
        "--toolchain-dir",
        type=Path,
        default=Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain")),
        help="Directory holding the already-installed toolchain (see toolchain/setup_toolchain.py) - not built by this script",
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="Parallel make jobs")
    return parser


def _checked_toml(device: str, given: "Path | None") -> Path:
    # The TOML this image builds from: devices/<device>.toml, or a copy of it that changes only what the website (built
    # from the repo's own TOML) does not show, or image and page would disagree.
    device_toml = (given or REPO_ROOT / "devices" / f"{device}.toml").resolve()
    if not device_toml.is_file():
        raise BuildError(device, f"no device definition at {device_toml}", rule="firmware.device-toml-missing", fix="name a devices/<device>.toml stem, or a --device-toml file that exists")
    if device_toml.stem != device:
        raise BuildError(device, f"{device_toml} builds device {device_toml.stem!r}, not {device!r}", rule="firmware.device-toml-other-device", fix=f"name the copy {device}.toml")
    repo_toml = REPO_ROOT / "devices" / f"{device}.toml"
    if device_toml != repo_toml and definitions_for_toml(device_toml, REPO_ROOT / "src") != definitions_for_toml(repo_toml, REPO_ROOT / "src"):
        raise BuildError(device, f"{device_toml} changes what the website shows, but the website is built from {repo_toml}", rule="firmware.device-toml-changes-website", fix="change only what the definitions do not carry")
    return device_toml


def _unwritable_output(device: str, output: Path, error: OSError) -> BuildError:
    # An --output the build cannot write is the caller's to fix: one line naming it (L.5), never a traceback.
    return BuildError(device, f"cannot write {output}: {error.strerror or error}", rule="firmware.output-unwritable", fix="name an --output path in a writable directory")


def _build(args: argparse.Namespace, work_dir: "list[Path]") -> int:
    # One absolute path for the lock, the record and every path the build writes into generated files.
    toolchain_dir = args.toolchain_dir.expanduser().resolve()
    device_toml = _checked_toml(args.device, args.device_toml)
    board = st.load_versions(REPO_ROOT / "toolchain" / "versions.toml")["toolchain"]["board"]
    micropython_dir = toolchain_dir / "micropython"
    if not (micropython_dir / "ports" / "rp2").is_dir():
        raise st.SetupError(f"no MicroPython checkout at {micropython_dir} - run `uv run toolchain/setup_toolchain.py setup` first")
    suffix = (_NO_AUTOSTART_SUFFIX if args.no_autostart else "") + (micropython_overrides.TICK_OFFSET_BUILD_SUFFIX if args.tick_offset_test else "")
    output = args.output or (REPO_ROOT / "build" / f"firmware-{args.device}{suffix}.uf2")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise _unwritable_output(args.device, output, e) from e
    # One date for the staged module, its website and the image record, so a board's /system names this build.
    build_date = current_build_date()
    test_overrides = (micropython_overrides.TICK_OFFSET_DIR_NAME,) if args.tick_offset_test else ()

    # One build or setup at a time per toolchain directory, held until the image record is written;
    # setup deletes its record first and writes it last, so a directory without one is unfinished.
    with st.toolchain_lock(toolchain_dir):
        record = st.read_toolchain_record(toolchain_dir)
        if record is None:
            raise st.SetupError(f"the toolchain at {toolchain_dir} is incomplete or predates the build record - run `uv run toolchain/setup_toolchain.py setup` first")
        # A record may carry no built ref (a `test` run with none to carry over): the pinned ref is printed, marked so.
        built = record["built_ref"] or f"{record['pinned_ref']} as pinned (built by `test`, ref not recorded)"
        log(f"Toolchain: MicroPython {built} ({record['micropython_commit']}), recorded in {toolchain_dir / st.TOOLCHAIN_RECORD}")
        work = WORK_ROOT / f"{args.device}{suffix}"
        if work.exists():
            shutil.rmtree(work)
        stage_dir = work / "stage"
        stage_dir.mkdir(parents=True)
        work_dir.append(work)
        log(f"Staged modules and manifest: {work}")
        build_stage_dir(stage_dir, device_toml, autostart=not args.no_autostart, build_date=build_date, test_overrides=test_overrides)
        # manifest.py sits beside stage/, not inside it, so freeze()'s walk of stage/ cannot pick up the manifest itself.
        manifest_path = work / "manifest.py"
        manifest_path.write_text(render_manifest(board, stage_dir), encoding="utf-8")

        # mpy-cross's build/ does not self-clean per build the way ports/rp2/build-{board} does,
        # so it is wiped here - and must then be rebuilt explicitly, since the rp2 port's own
        # implicit sub-build fails from a freshly wiped directory (Part B.11).
        mpy_cross_build_dir = micropython_dir / "mpy-cross" / "build"
        if mpy_cross_build_dir.exists():
            log(f"Cleaning {mpy_cross_build_dir} before rebuilding")
            shutil.rmtree(mpy_cross_build_dir)
        st.build_mpy_cross(micropython_dir, args.jobs)

        log(f"Building firmware for BOARD={board}, device={args.device!r}")
        uf2 = st.build_firmware(micropython_dir, board, args.jobs, frozen_manifest=manifest_path, toolchain_dir=toolchain_dir, tick_offset_test=args.tick_offset_test)
        # Every reader takes the port's build dir beside the uf2 it returned, never the copy.
        report = image_report(uf2.parent)
        log(f"Image: {report.used} B of {report.fs_base} B before the filesystem ({100 * report.used / report.fs_base:.1f} %), {report.free} B free")
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
            "overrides": _overrides_in_build(uf2.parent, micropython_dir, toolchain_dir),
            "deviceToml": device_toml.relative_to(REPO_ROOT).as_posix() if device_toml.is_relative_to(REPO_ROOT) else str(device_toml),
            "uartCrc": _uart_crc(device_toml),
            "imageUsedBytes": report.used,
            "filesystemBaseBytes": report.fs_base,
            "imageFreeBytes": report.free,
            "autostart": not args.no_autostart,
        }
        try:
            write_image(uf2, output, image_record)
        except OSError as e:
            raise _unwritable_output(args.device, output, e) from e

    print(f"\nWrote {output} and its image record {output.with_suffix('.json')}")
    if args.no_autostart:
        print("Built without autostart: start with the line the board prints at boot")
    return 0


def main(argv: "list[str] | None" = None) -> int:
    args = _parser().parse_args(argv)
    work_dir: list[Path] = []
    try:
        return _build(args, work_dir)
    except (BuildError, StripError, st.SetupError, micropython_overrides.OverrideError, subprocess.CalledProcessError) as exc:
        kept = f" (staged modules and manifest kept in {work_dir[0]})" if work_dir else ""
        print(f"build_firmware: {exc}{kept}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
