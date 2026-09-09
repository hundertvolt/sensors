"""Top-level orchestration: `generate_device()` runs the full pipeline (validate -> topologically
sort -> generate source) for one device TOML and returns the generated module/boot-entry source as
strings - callers decide whether/where to write them (this session's own tests write to a tmp_path;
wiring this into the real `build/<device>/` output tree is Session 6's job, not this one's - see
BUILD_CHAIN_PLAN.md's session breakdown). A thin CLI wrapper is included for convenience/manual
use, not because any other part of this repo calls it yet."""

import argparse
import sys
from pathlib import Path

from buildgen.codegen import generate_boot_entry_source, generate_module_source
from buildgen.errors import BuildError
from buildgen.frozen_modules import compute_frozen_modules
from buildgen.graph import build_construction_order
from buildgen.model import DeviceModel
from buildgen.validate import build_model

REPO_ROOT = Path(__file__).resolve().parent.parent


class GeneratedDevice:
    def __init__(self, model: DeviceModel, module_source: str, boot_entry_source: str, frozen_modules: "frozenset[str]") -> None:
        self.model = model
        self.module_source = module_source
        self.boot_entry_source = boot_entry_source
        self.frozen_modules = frozen_modules


def generate_device(toml_path: Path, src_dir: Path, ext_dir: "Path | None" = None) -> GeneratedDevice:
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    module_source = generate_module_source(model, model.construction_order)
    boot_entry_source = generate_boot_entry_source(model.device)
    frozen = compute_frozen_modules(model, src_dir, ext_dir)
    return GeneratedDevice(model, module_source, boot_entry_source, frozen)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Generate sensortask_<device>.py + boot entry from a device TOML.")
    parser.add_argument("device_toml", type=Path)
    parser.add_argument("--src-dir", type=Path, default=REPO_ROOT / "src")
    parser.add_argument("--ext-dir", type=Path, default=REPO_ROOT / "ext")
    parser.add_argument("--out-dir", type=Path, default=None, help="write sensortask_<device>.py/<device>_boot.py here instead of printing to stdout")
    args = parser.parse_args(argv)

    try:
        result = generate_device(args.device_toml, args.src_dir, args.ext_dir)
    except BuildError as e:
        print(f"buildgen: {e}", file=sys.stderr)
        return 1

    if args.out_dir is None:
        print(result.module_source)
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"sensortask_{result.model.device}.py").write_text(result.module_source)
    (args.out_dir / f"{result.model.device}_boot.py").write_text(result.boot_entry_source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
