"""Loads a device TOML into the generator's own working model: `load_device()` parses the file
(wrapping `tomllib.TOMLDecodeError` into the same fail-loud `BuildError` every other check in this
package raises); `InstanceSpec`/`DeviceModel` carry a `[[instance]]` entry (plus, once
`validate.build_model()` has run, its resolved driver/wiring/`@requires` facts) through the rest of
the pipeline (validation, topological sort, code generation) as one shared shape."""

from dataclasses import dataclass, field
from pathlib import Path

import tomllib

from buildgen.driver_registry import DriverInfo
from buildgen.errors import BuildError
from buildgen.limits import LimitField
from buildgen.requires_tag import RequiresTag
from buildgen.wiring import WiringField


def instance_key(inst: dict) -> tuple[str, str]:
    # The TOML's own driver/name_ext identity - deliberately never instance_name()/_NAME
    # (SPECIFICATION.md Part C.14.1's separate, unrelated naming space; see wiring.py's own
    # module docstring and BUILD_CHAIN_PLAN.md's quality-bar section for the confirmed-real bug
    # this distinction closes: NotificationCoordinator's _NAME is "NOTIFY", not "NOTIFICATION").
    return (inst["driver"], inst.get("name_ext", ""))


def instance_label(key: tuple[str, str]) -> str:
    driver, name_ext = key
    return f"{driver}_{name_ext}" if name_ext else driver


@dataclass
class InstanceSpec:
    driver: str
    name_ext: str
    fields: dict  # the raw [[instance]] table, minus "wiring"
    wiring: dict  # the raw [instance.wiring] table (may itself hold sub-tables, e.g. warn_co2), {} if absent
    order_index: int  # original declaration order - stable tie-break when nothing else orders two nodes
    driver_info: DriverInfo | None = None
    wiring_schema: "tuple[WiringField, ...]" = ()
    requires_tags: "tuple[RequiresTag, ...]" = ()
    limits_schema: "tuple[LimitField, ...]" = ()
    resolved_name: str | None = None  # instance_name(_NAME, name_ext) - filled in by validate.py

    @property
    def key(self) -> tuple[str, str]:
        return (self.driver, self.name_ext)

    @property
    def label(self) -> str:
        return instance_label(self.key)


@dataclass
class DeviceModel:
    device: str
    path: Path
    doc: dict
    instances: "dict[tuple[str, str], InstanceSpec]" = field(default_factory=dict)
    construction_order: "list[str | tuple[str, str]]" = field(default_factory=list)  # "conn"/"ntp"/"sysfunct" or an instance key


def resolve_instance_key(model: DeviceModel, value: str) -> "tuple[str, str]":
    # A wiring value is always a plain "driver" or "driver_ext" string (never a (driver, ext)
    # pair) - try the bare, unextended reading first (the common case - every real device's own
    # wiring values name an unextended instance), then fall back to splitting the last "_"-group
    # off as name_ext for a target that itself used one (e.g. this session's own synthetic
    # multi-instance fixture, tests_scripts/buildgen_fixtures/novel_combo.toml).
    key = (value, "")
    if key in model.instances:
        return key
    if "_" in value:
        driver_part, _, ext_part = value.rpartition("_")
        alt = (driver_part, ext_part)
        if alt in model.instances:
            return alt
    return key  # unresolved - the caller is responsible for erroring (validate.py already has by the time graph.py/codegen.py ever see this)


def load_device(path: Path) -> DeviceModel:
    device = path.stem
    try:
        with open(path, "rb") as f:
            doc = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise BuildError(device, f"{path} is not valid TOML: {e}") from e
    except OSError as e:
        raise BuildError(device, f"could not read {path}: {e}") from e

    if not isinstance(doc, dict):
        raise BuildError(device, f"{path} did not parse to a table at the top level")

    instances: dict[tuple[str, str], InstanceSpec] = {}
    for i, inst in enumerate(doc.get("instance", [])):
        if not isinstance(inst, dict) or "driver" not in inst:
            raise BuildError(device, f"[[instance]] entry #{i} is missing a 'driver' field")
        if not isinstance(inst["driver"], str) or not inst["driver"]:
            raise BuildError(device, f"[[instance]] entry #{i}'s 'driver' field must be a non-empty string, got {inst['driver']!r}")
        if "name_ext" in inst and not isinstance(inst["name_ext"], str):
            # Left unvalidated, a non-string name_ext crashes downstream as a raw TypeError (e.g.
            # validate._instance_name()'s `base_name + "_" + name_ext` string concatenation) instead
            # of this package's own fail-loud BuildError contract.
            raise BuildError(device, f"{inst['driver']!r} instance's 'name_ext' field must be a string, got {inst['name_ext']!r}", instance=inst["driver"])
        wiring = inst.get("wiring", {})
        fields_only = {k: v for k, v in inst.items() if k != "wiring"}
        key = instance_key(inst)
        if key in instances:
            raise BuildError(device, f"duplicate [[instance]] entry for {instance_label(key)!r} (driver+name_ext must be unique)", instance=instance_label(key))
        instances[key] = InstanceSpec(inst["driver"], inst.get("name_ext", ""), fields_only, wiring, i)

    return DeviceModel(device, path, doc, instances)
