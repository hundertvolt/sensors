"""Top-level orchestration: `generate_device()` runs validate -> topological sort -> codegen for
one device TOML and returns the module and both boot-entry sources as strings, with the device's
expected boot facts (`scripts/_generate_sensortask_modules.py` and `scripts/build_firmware.py` write them)."""

import argparse
import contextlib
import os
import sys
from pathlib import Path

from buildgen.codegen import generate_boot_entry_source, generate_module_source
from buildgen.errors import BuildError, BuildInternalError
from buildgen.frozen_modules import compute_frozen_modules
from buildgen.graph import build_construction_order
from buildgen.jsontypes import JsonDict
from buildgen.model import DeviceModel, instance_label
from buildgen.validate import build_model
from buildgen.version import current_build_date

REPO_ROOT = Path(__file__).resolve().parent.parent

# The generated main()'s statements in order: each awaited call by name, each boot-phase mark by its
# constant (SPECIFICATION.md Part A.7). The boot-sequence scenarios record a real run against it.
BOOT_PHASES = ("build_system", "BOOT_SETUP", "run_setups", "BOOT_TASKS", "start_tasks", "BOOT_TIMERS", "start_timers", "BOOT_NTP", "ntp_force_sync", "BOOT_DONE", "supervise_tasks")

# The mandatory modules a device-level [device.wiring].fram_target wires to the FRAM store.
_DEVICE_FRAM_CONSUMERS = ("conn", "ntp", "sysfunct", "webserver")


class GeneratedDevice:
    def __init__(self, model: DeviceModel, module_source: str, boot_entry_source: str, boot_entry_noautostart_source: str, frozen_modules: "frozenset[str]", expected_facts: JsonDict) -> None:
        self.model = model
        self.module_source = module_source
        self.boot_entry_source = boot_entry_source
        self.boot_entry_noautostart_source = boot_entry_noautostart_source
        self.frozen_modules = frozen_modules
        self.expected_facts = expected_facts


def _compiled(device: str, filename: str, source: str) -> str:
    # The generator emits only Python that compiles: a SyntaxError is its own bug, never the TOML's.
    try:
        compile(source, filename, "exec")
    except SyntaxError as e:
        raise BuildInternalError(f"{device}: generated {filename} does not compile: line {e.lineno}: {e.msg}") from e
    return source


def _expected_setups(model: DeviceModel, order: "list[str | tuple[str, str]]") -> "list[str]":
    # fram first (sysfunct's config store logs to it), then the mandatory services, then every other
    # instance needing setup() in construction order, webserver last: the rule _collect_setups() emits.
    instances = [node for node in order if isinstance(node, tuple)]
    fram = [instance_label(key) for key in instances if key[0] == "fram"]
    rest = [instance_label(key) for key in instances if key[0] != "fram" and (info := model.instances[key].driver_info) is not None and info.needs_setup]
    return [*fram, "sysfunct", "conn", "ntp", *rest, "webserver"]


def _fram_wired(model: DeviceModel) -> "list[str]":
    # Every module whose logs go to FRAM: each instance whose TOML sets fram_target, plus the
    # mandatory modules when [device.wiring] sets it (codegen's _fram_var()/_device_fram_var() rule).
    wired = [spec.label for spec in model.instances.values() if "fram_target" in spec.wiring]
    device_table = model.doc.get("device")
    device_wiring = device_table.get("wiring") if isinstance(device_table, dict) else None
    if isinstance(device_wiring, dict) and "fram_target" in device_wiring:
        wired.extend(_DEVICE_FRAM_CONSUMERS)
    return sorted(wired)


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
            os.replace(tmp, tmp.with_suffix(""))
    except OSError as e:
        for tmp in written:
            with contextlib.suppress(OSError):  # the write error below is the one reported
                tmp.unlink(missing_ok=True)
        raise BuildError(device, f"cannot write {e.filename or out_dir}: {e.strerror}", rule="cli.out-dir-unwritable", fix="check that the output directory is writable") from e


def expected_facts(model: DeviceModel) -> JsonDict:
    # What the generated module must do at boot, derived from the model alone, never read back from
    # the generated text: the oracle the mock and twin boot scenarios assert a real run against.
    order = build_construction_order(model)
    return {
        "boot_sequence": {
            "construction": [node if isinstance(node, str) else instance_label(node) for node in order],
            "setups": list(_expected_setups(model, order)),
            "phases": list(BOOT_PHASES),
        },
        "fram_wired": list(_fram_wired(model)),
    }


def generate_device(toml_path: Path, src_dir: Path, ext_dir: "Path | None" = None, build_date: "str | None" = None) -> GeneratedDevice:
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    module_name, entry_name, noautostart_name = _output_names(model.device)
    module_source = _compiled(model.device, module_name, generate_module_source(model, model.construction_order, build_date if build_date is not None else current_build_date(), src_dir))
    return GeneratedDevice(
        model,
        module_source,
        _compiled(model.device, entry_name, generate_boot_entry_source(model.device)),
        _compiled(model.device, noautostart_name, generate_boot_entry_source(model.device, autostart=False)),
        # A caller giving no ext/ root resolves the closure against src/ alone, as it always did.
        compute_frozen_modules(module_source, src_dir, src_dir if ext_dir is None else ext_dir, device=model.device),
        expected_facts(model),
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
