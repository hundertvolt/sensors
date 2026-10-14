#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pre-generates every real device's `sensortask_<device>.py`, both its boot entries, its expected boot
facts and wiring-plan JSON (independent oracles for their consumers), its website definitions, its
REST API reference and the freshness stamps via `buildgen` into gitignored `build/generated_src/` (SPECIFICATION.md E.3)."""

# Usage: uv run scripts/_generate_sensortask_modules.py
# Writes sensortask_<d>.py, sensortask_<d>_main.py, sensortask_<d>_main_noautostart.py, sensortask_<d>_expected.json, sensortask_<d>_wiring_plan.json,
# definitions/<d>.json and api/<d>.json per device, then definitions/index.json, removes every other finished file (a removed device's), then writes .inputs_stamp.json (inputs and outputs) and definitions/inputs_stamp.json; test.sh, typecheck.sh, the twin runners and npm's build:definitions call it.

import contextlib
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from buildgen.api_reference import api_reference_json, generate_api_reference  # noqa: E402
from buildgen.definitions import generate_definitions  # noqa: E402
from buildgen.errors import BuildError  # noqa: E402
from buildgen.generate import generate_device  # noqa: E402
from buildgen.twin_wiring import compute_twin_wiring  # noqa: E402
from buildgen.version import current_build_date  # noqa: E402

# Every file a generation reads besides the device TOMLs: the catalog and lwIP table (buildgen/definitions.py,
# model.py), the overrides validate.py loads by path, this script, and the ext/ modules the frozen closure parses.
_NAMED_INPUTS = ("buildgen/error_catalog.json", "toolchain/versions.toml", "toolchain/micropython_overrides.py", "scripts/_generate_sensortask_modules.py")
_INPUT_GLOBS = ("buildgen/*.py", "src/*.py", "ext/*.py")
_STAMP_NAMES = (".inputs_stamp.json", "definitions/inputs_stamp.json")


def _input_hashes(device_tomls: "list[Path]") -> "dict[str, str]":
    # Taken before any device is generated, so an input edited during the run leaves the tree stale: each input's sha256
    # (tests/_generated_tree.py; MicroPython's os.stat() has whole seconds only).
    inputs = [*device_tomls, *(REPO_ROOT / name for name in _NAMED_INPUTS), *(p for pattern in _INPUT_GLOBS for p in REPO_ROOT.glob(pattern))]
    return {path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs if path.is_file()}


def _remove_all_but(out_dir: Path, kept: "set[Path]") -> bool:
    # Every finished file of the generator's own directories that this run did not write is a removed device's: gone, so no
    # consumer globbing the tree takes it for a device. A .tmp is another run's write before its rename and stays.
    stale = [p for d in {out_dir, *(k.parent for k in kept)} for p in d.iterdir() if p.is_file() and p not in kept and not p.name.endswith(".tmp")]
    try:
        for path in stale:
            path.unlink(missing_ok=True)
    except OSError as e:
        print(f"error: cannot remove {e.filename}: {e.strerror}", file=sys.stderr)
        return False
    return True


def _stamps(hashes: "dict[str, str]", device_tomls: "list[Path]", outputs: "list[str]") -> "dict[str, str]":
    # The inputs read and every file of the tree, stamps included, for tests/_generated_tree.py; each TOML's hash for the JS loader.
    tomls = {path.stem: hashes[path.relative_to(REPO_ROOT).as_posix()] for path in device_tomls}
    return dict(zip(_STAMP_NAMES, (json.dumps({"inputs": hashes, "outputs": sorted([*outputs, *_STAMP_NAMES])}), json.dumps({"tomls": tomls})), strict=True))


def _write_through_rename(files: "dict[Path, str]") -> bool:
    # Each file goes to <name>.tmp beside it and is renamed into place once all are written, so a run
    # reading build/generated_src/ meanwhile meets the old file or the new one, never a truncated one.
    written: list[Path] = []
    try:
        for path, text in files.items():
            written.append(path.with_name(f"{path.name}.tmp"))
            written[-1].write_text(text)
        for tmp in written:
            os.replace(tmp, tmp.with_name(tmp.name.removesuffix(".tmp")))
    except OSError as e:
        for tmp in written:
            with contextlib.suppress(OSError):  # the write error below is the one reported
                tmp.unlink(missing_ok=True)
        print(f"error: cannot write {e.filename or written[-1]}: {e.strerror}", file=sys.stderr)
        return False
    return True


def main() -> int:
    out_dir = REPO_ROOT / "build" / "generated_src"
    definitions_dir = out_dir / "definitions"
    definitions_dir.mkdir(parents=True, exist_ok=True)
    api_dir = out_dir / "api"
    api_dir.mkdir(exist_ok=True)
    # Every real device, discovered from the directory rather than a hand-kept list, so a seventh
    # device needs no edit here. A zz_test_ fixture a concurrent test left in devices/ is never one
    # (the same rule as tests_scripts/_devices.py).
    device_tomls = sorted(p for p in REPO_ROOT.glob("devices/*.toml") if not p.stem.startswith("zz_test_"))
    hashes = _input_hashes(device_tomls)
    written: set[Path] = set()
    # One build_date for the whole batch - every device generated by this one run of this script
    # reports the same "when was this built" answer, rather than drifting by whichever second each
    # device's own generate_device() call happened to land on.
    build_date = current_build_date()
    for device_toml in device_tomls:
        device = device_toml.stem
        # Every output of a device is built before the first is written: a failing stage leaves none of its files.
        try:
            generated = generate_device(device_toml, REPO_ROOT / "src", REPO_ROOT / "ext", build_date=build_date)
            # generate_device() has already put the model in construction order, which the cards follow.
            definitions = generate_definitions(generated.model, REPO_ROOT / "src")
            reference = generate_api_reference(generated.model, REPO_ROOT / "src")
            wiring_plan = compute_twin_wiring(generated.model)
        except BuildError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        outputs = {
            out_dir / f"sensortask_{device}.py": generated.module_source,
            out_dir / f"sensortask_{device}_main.py": generated.boot_entry_source,
            out_dir / f"sensortask_{device}_main_noautostart.py": generated.boot_entry_noautostart_source,
            out_dir / f"sensortask_{device}_expected.json": json.dumps(generated.expected_facts),
            out_dir / f"sensortask_{device}_wiring_plan.json": json.dumps(wiring_plan),
            definitions_dir / f"{device}.json": json.dumps(definitions, indent=2),
            api_dir / f"{device}.json": api_reference_json(reference),
        }
        if not _write_through_rename(outputs):
            return 1
        written |= set(outputs)
    index = {definitions_dir / "index.json": json.dumps({"devices": [p.stem for p in device_tomls]})}
    if not _write_through_rename(index):
        return 1
    written |= set(index)
    stamps = _stamps(hashes, device_tomls, [p.relative_to(out_dir).as_posix() for p in written])
    if not _remove_all_but(out_dir, written | {out_dir / name for name in stamps}):
        return 1
    # Last: a run that stops earlier keeps the previous stamps, so a tree half-written from changed inputs reads as stale.
    if not _write_through_rename({out_dir / name: text for name, text in stamps.items()}):
        return 1
    print(f"Generated {len(device_tomls)} device module(s) + boot entries + expected facts + wiring plan(s) + definitions + API reference(s) into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
