"""The bench board's facts as one dict a device script receives rendered (harness.render_device_script()): its buses,
instances, addresses and FRAM, and the driver and port values a script would otherwise copy, each read from its one
source - the device TOML through buildgen, src/ by ast, the pinned MicroPython checkout. Host CPython only."""

import os
import re
import sys
from pathlib import Path
from typing import TypeAlias

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from buildgen.driver_registry import parse_name_constant
from buildgen.generate import _DEVICE_FRAM_CONSUMERS, expected_facts
from buildgen.model import DeviceModel
from buildgen.schema_ast import extract_field_schemas
from buildgen.signals import WARN_SIGNALS
from buildgen.twin_wiring import compute_twin_wiring
from buildgen.validate import _VALID_BUS_IDS, build_model, module_int_const

REPO_ROOT = Path(__file__).resolve().parent.parent

# A rendered fact: what repr() writes and MicroPython's parser reads back, nothing else.
Fact: TypeAlias = bool | int | float | str | list["Fact"] | tuple["Fact", ...] | dict[str, "Fact"] | None
FactDict: TypeAlias = dict[str, Fact]

SRC_DIR = REPO_ROOT / "src"
DEVICES_DIR = REPO_ROOT / "devices"
_UART_COMM = "asy_uart_comm.py"
_INSTANCE_PINS = ("irq_pin", "cs_pin", "pin")
_SCHEDULER_DEPTH = re.compile(r"^#define MICROPY_SCHEDULER_DEPTH\s+\(?(\d+)\)?", re.MULTILINE)


def _bus_facts(model: DeviceModel) -> FactDict:
    # Each [bus.*] table's full parameter set as the TOML states it, plus its peripheral id; a key the TOML leaves out
    # stays out, so a script passes only what the build passes. A UART bus also carries its link's crc mode ("none"
    # when unset) and max_transfer_bytes, as the uart_link instance on it declares them.
    tables = model.doc.get("bus", {})
    buses: FactDict = {}
    for bus_id, table in _fact_dict(tables, "[bus]").items():
        facts = {"id": int(bus_id[-1]), **_fact_dict(table, f"[bus.{bus_id}]")}
        if _VALID_BUS_IDS[bus_id] == "uart":
            link = next((spec for spec in model.instances.values() if spec.driver == "uart_link" and spec.fields.get("bus") == bus_id), None)
            facts["crc"] = _fact(link.fields.get("crc", "none") if link is not None else "none", f"bus {bus_id} crc")
            if link is not None and "max_transfer_bytes" in link.fields:
                facts["max_transfer_bytes"] = _fact(link.fields["max_transfer_bytes"], f"{link.label}.max_transfer_bytes")
        buses[bus_id] = facts
    return buses


def _fact(value: object, where: str) -> Fact:
    # value as a Fact, or a TypeError naming where it came from: a TOML date or a schema object repr() cannot round-trip.
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        items = [_fact(item, where) for item in value]
        return items if isinstance(value, list) else tuple(items)
    if isinstance(value, dict):
        return _fact_dict(value, where)
    raise TypeError(f"{where}: {value!r} is no literal a device script can be rendered with")


def _fact_dict(value: object, where: str) -> FactDict:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise TypeError(f"{where}: {value!r} is no table of named facts")
    return {key: _fact(item, f"{where}.{key}") for key, item in value.items()}


def _float_fields(model: DeviceModel) -> FactDict:
    # Every float schema field of the modules the device builds, keyed "<logger>.<field>" so two modules' fields of
    # one name keep their own ranges, plus the notification thresholds the generator emits (buildgen/signals.py).
    files = {spec.resolved_name: spec.driver_info.source_path for spec in model.instances.values() if spec.resolved_name and spec.driver_info}
    for filename in _DEVICE_FRAM_CONSUMERS.values():
        files[parse_name_constant(SRC_DIR / filename, model.device, filename)] = SRC_DIR / filename
    found: FactDict = {}
    for logger, path in sorted(files.items()):
        for name, (kind, _default, low, high, _special) in extract_field_schemas(path).items():
            if kind == "float" and isinstance(low, float) and isinstance(high, float):
                found[f"{logger}.{name}"] = (low, high)
    for spec in model.instances.values():
        if spec.driver == "notification" and spec.resolved_name:
            for signal in WARN_SIGNALS.values():
                if signal.field_type == "float":
                    found[f"{spec.resolved_name}.{signal.name}"] = (float(signal.min), float(signal.max))
    return found


def _instance_facts(model: DeviceModel) -> "tuple[FactDict, FactDict]":
    # Per instance label: driver, bus, address and pins; and the label -> I2C address table, both through the twin
    # wiring plan's own address reader (buildgen.twin_wiring), never a second table.
    plan = compute_twin_wiring(model)
    attached = {(a["driver"], a["name_ext"]): a["address"] for attachments in plan["buses"].values() for a in attachments}
    instances: FactDict = {}
    addresses: FactDict = {}
    for spec in model.instances.values():
        facts: FactDict = {"driver": spec.driver, "name_ext": spec.name_ext}
        for key in ("bus", *_INSTANCE_PINS):
            if key in spec.fields:
                facts[key] = _fact(spec.fields[key], f"{spec.label}.{key}")
        if spec.key in attached:
            facts["address"] = addresses[spec.label] = attached[spec.key]
        instances[spec.label] = facts
    return instances, addresses


def _resync_bound_ms(timeout_ms: int) -> int:
    # The UART link's resync bound: the drain bound (_DRAIN_BOUND_MULT x _RESYNC_NUM/_RESYNC_DEN x timeout, the
    # largest deadline asy_uart_comm derives from its timeout) plus one more timeout, from the module's const()s.
    def read(name: str) -> int:
        return module_int_const(SRC_DIR, _UART_COMM, name)

    return read("_DRAIN_BOUND_MULT") * read("_RESYNC_NUM") * timeout_ms // read("_RESYNC_DEN") + timeout_ms


def _scheduler_depth() -> int:
    # MICROPY_SCHEDULER_DEPTH as the pinned checkout defines it: the rp2 port's own value, else py/mpconfig.h's default.
    checkout = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain")) / "micropython"
    for header in (checkout / "ports" / "rp2" / "mpconfigport.h", checkout / "py" / "mpconfig.h"):
        if header.is_file():
            match = _SCHEDULER_DEPTH.search(header.read_text(encoding="utf-8"))
            if match is not None:
                return int(match.group(1))
    raise FileNotFoundError(f"no MICROPY_SCHEDULER_DEPTH under {checkout} - run `uv run toolchain/setup_toolchain.py setup` first")


def _schema(filename: str) -> FactDict:
    # A module's config schema, field name -> (type, default, min, max, special), read by buildgen's own schema reader.
    return {name: _fact(schema, f"{filename} {name}") for name, schema in extract_field_schemas(SRC_DIR / filename).items()}


def build(device: str) -> FactDict:
    # Everything a device script reads of the board, from devices/<device>.toml; per-run values are the caller's
    # extras, never facts (harness.render_device_script()).
    model = build_model(DEVICES_DIR / f"{device}.toml", SRC_DIR)
    instances, addresses = _instance_facts(model)
    expected = expected_facts(model, SRC_DIR)
    fram = next((spec for spec in model.instances.values() if spec.driver == "fram"), None)
    return {
        "device_module": f"sensortask_{model.device}",
        "bus": _bus_facts(model),
        "instances": instances,
        "addresses": addresses,
        "fram_max_size": _fact(fram.fields["max_size"], "fram.max_size") if fram is not None else None,
        "fram_wired": _fact(expected["fram_wired"], "fram_wired"),
        "fram_backed_loggers": _fact(expected["fram_backed_loggers"], "fram_backed_loggers"),
        "isl29125": {"mode_rgb": module_int_const(SRC_DIR, "asy_isl29125_driver.py", "_MODE_RGB")},
        "system_schema": _schema("asy_system_service.py"),
        "scd30_schema": _schema("asy_scd30_driver.py"),
        "float_fields": _float_fields(model),
        "resync_bound_ms": _resync_bound_ms(module_int_const(SRC_DIR, _UART_COMM, "_DEFAULT_TIMEOUT_MS")),
        "depth": _scheduler_depth(),
    }
