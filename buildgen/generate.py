"""Top-level orchestration: `generate_device()` runs validate -> topological sort -> codegen for
one device TOML and returns the module and both boot-entry sources as strings, with the frozen closure."""

import argparse
import contextlib
import sys
from pathlib import Path

from buildgen.codegen import generate_boot_entry_source, generate_module_source
from buildgen.errors import BuildError
from buildgen.frozen_modules import compute_frozen_modules
from buildgen.graph import build_construction_order
from buildgen.model import DeviceModel
from buildgen.validate import build_model
from buildgen.version import current_build_date

REPO_ROOT = Path(__file__).resolve().parent.parent


class GeneratedDevice:
    def __init__(self, model: DeviceModel, module_source: str, boot_entry_source: str, boot_entry_noautostart_source: str, frozen_modules: "frozenset[str]") -> None:
        self.model = model
        self.module_source = module_source
        self.boot_entry_source = boot_entry_source
        self.boot_entry_noautostart_source = boot_entry_noautostart_source
        self.frozen_modules = frozen_modules


def _output_names(device: str) -> "tuple[str, str, str]":
    # The module, its boot entry (frozen as main.py) and the no-autostart variant, as the CLI writes them.
    return f"sensortask_{device}.py", f"sensortask_{device}_main.py", f"sensortask_{device}_main_noautostart.py"


def _write_outputs(device: str, out_dir: Path, outputs: "dict[str, str]") -> None:
    # Each file goes to <name>.tmp and is renamed into place only once every one is written, so a
    # failed write leaves no output file: the .tmp files it did write are removed.
    written: list[Path] = []
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, text in outputs.items():
            written.append(out_dir / f"{name}.tmp")
            written[-1].write_text(text, encoding="utf-8")
        for tmp in written:
            tmp.replace(tmp.with_suffix(""))
    except OSError as e:
        for tmp in written:
            with contextlib.suppress(OSError):  # the write error below is the one reported
                tmp.unlink(missing_ok=True)
        raise BuildError(device, f"cannot write {e.filename or out_dir}: {e.strerror}", rule="cli.out-dir-unwritable", fix="check that the output directory is writable") from e


def generate_device(toml_path: Path, src_dir: Path, ext_dir: "Path | None" = None, build_date: "str | None" = None, *, test_overrides: "tuple[str, ...]" = ()) -> GeneratedDevice:
    # test_overrides names the test-only firmware overrides an image carries in its build info; never set for a release.
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    module_source = generate_module_source(model, model.construction_order, build_date if build_date is not None else current_build_date(), src_dir, test_overrides=test_overrides)
    return GeneratedDevice(
        model,
        module_source,
        generate_boot_entry_source(model.device),
        generate_boot_entry_source(model.device, autostart=False),
        # A caller giving no ext/ root resolves the closure against src/ alone, as it always did.
        compute_frozen_modules(module_source, src_dir, src_dir if ext_dir is None else ext_dir, device=model.device),
    )


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Generate sensortask_<device>.py and its two boot entries from a device TOML.")
    parser.add_argument("device_toml", type=Path)
    parser.add_argument("--src-dir", type=Path, default=REPO_ROOT / "src")
    parser.add_argument("--ext-dir", type=Path, default=REPO_ROOT / "ext")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="write sensortask_<device>.py, its boot entry (frozen as main.py) sensortask_<device>_main.py and the no-autostart sensortask_<device>_main_noautostart.py here instead of printing the module to stdout",
    )
    args = parser.parse_args(argv)

    try:
        result = generate_device(args.device_toml, args.src_dir, args.ext_dir)
        if args.out_dir is None:
            print(result.module_source)
            return 0
        names = _output_names(result.model.device)
        _write_outputs(result.model.device, args.out_dir, dict(zip(names, (result.module_source, result.boot_entry_source, result.boot_entry_noautostart_source), strict=True)))
    except BuildError as e:
        print(f"buildgen: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
