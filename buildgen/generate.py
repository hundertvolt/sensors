"""Top-level orchestration: `generate_device()` runs validate -> topological sort -> codegen for
one device TOML and returns the module/boot-entry source as strings; callers decide where to write
them (Session 6 owns the real `build/<device>/` tree). The CLI wrapper is for manual use."""

import argparse
import sys
from pathlib import Path

from buildgen.codegen import generate_boot_entry_source, generate_module_source
from buildgen.errors import BuildError
from buildgen.frozen_modules import compute_frozen_modules
from buildgen.gc_policy import DEFAULT_GC_POLICY, GC_POLICIES
from buildgen.graph import build_construction_order
from buildgen.model import DeviceModel
from buildgen.validate import build_model
from buildgen.version import current_build_date

REPO_ROOT = Path(__file__).resolve().parent.parent


class GeneratedDevice:
    def __init__(self, model: DeviceModel, module_source: str, boot_entry_source: str, frozen_modules: "frozenset[str]", gc_policy: str = DEFAULT_GC_POLICY, *, memory_pressure: bool = False) -> None:
        self.model = model
        self.module_source = module_source
        self.boot_entry_source = boot_entry_source
        self.frozen_modules = frozen_modules
        self.gc_policy = gc_policy
        self.memory_pressure = memory_pressure


def generate_device(toml_path: Path, src_dir: Path, ext_dir: "Path | None" = None, build_date: "str | None" = None, gc_policy: str = DEFAULT_GC_POLICY, *, memory_pressure: bool = False) -> GeneratedDevice:
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    module_source = generate_module_source(model, model.construction_order, build_date if build_date is not None else current_build_date(), gc_policy)
    boot_entry_source = generate_boot_entry_source(model.device, gc_policy, memory_pressure=memory_pressure)
    frozen = compute_frozen_modules(model, src_dir, ext_dir)
    return GeneratedDevice(model, module_source, boot_entry_source, frozen, gc_policy, memory_pressure=memory_pressure)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Generate sensortask_<device>.py + boot entry from a device TOML.")
    parser.add_argument("device_toml", type=Path)
    parser.add_argument("--src-dir", type=Path, default=REPO_ROOT / "src")
    parser.add_argument("--ext-dir", type=Path, default=REPO_ROOT / "ext")
    parser.add_argument("--out-dir", type=Path, default=None, help="write sensortask_<device>.py/<device>_boot.py here instead of printing to stdout")
    parser.add_argument("--gc-policy", choices=GC_POLICIES, default=DEFAULT_GC_POLICY, help="gc.threshold() value the generated boot entry sets (see buildgen/gc_policy.py)")
    parser.add_argument("--memory-pressure", action="store_true", help="also start the frozen memory_pressure churn task from the boot entry (needs --gc-policy reactive)")
    args = parser.parse_args(argv)

    try:
        result = generate_device(args.device_toml, args.src_dir, args.ext_dir, gc_policy=args.gc_policy, memory_pressure=args.memory_pressure)
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
