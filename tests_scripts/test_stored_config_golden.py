"""Every device's stored config - each config file name and its stored key -> type map, special-alone
fields excluded - derived two independent ways (the buildgen device model, the generated module's own
constructions) must agree; from the release on the map is pinned as a golden fixture (C.5)."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.driver_registry import parse_name_constant
from buildgen.generate import generate_device
from buildgen.graph import build_construction_order
from buildgen.schema_ast import _eval_literal, extract_field_schemas
from buildgen.signals import WARN_SIGNALS
from buildgen.validate import build_model

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
# The fixed core every device constructs, by its construction-order key.
_CORE = {"conn": "asy_wifi_service.py", "ntp": "asy_ntp_client.py", "sysfunct": "asy_system_service.py"}

StoredConfig = dict[str, dict[str, str]]  # config file name -> {stored key: type}
Fields = dict[str, tuple[object, ...]]  # field name -> (type, default, min, max, special)


def _classes(src: Path) -> "dict[str, tuple[Path, ast.ClassDef]]":
    found: dict[str, tuple[Path, ast.ClassDef]] = {}
    for path in sorted(src.glob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                found[node.name] = (path, node)
    return found


def _is_store(name: str, classes: "dict[str, tuple[Path, ast.ClassDef]]") -> bool:
    # A class that (or whose ancestor) constructs a ConfigManager owns a config file.
    todo, seen = [name], set()
    while todo:
        current = todo.pop()
        if current in seen or current not in classes:
            continue
        seen.add(current)
        node = classes[current][1]
        if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "ConfigManager" for n in ast.walk(node)):
            return True
        todo.extend(b.id for b in node.bases if isinstance(b, ast.Name))
    return False


def _fields(path: Path) -> Fields:
    return {name: tuple(spec) for name, spec in extract_field_schemas(path).items()}


def _stored_keys(fields: Fields) -> "dict[str, str]":
    # Special-alone fields (no default, one scalar special) are never written to the file (C.5).
    return {name: str(spec[0]) for name, spec in fields.items() if not (spec[1] is None and not isinstance(spec[4], (tuple, list)))}


def from_model(toml: Path, src: Path) -> StoredConfig:
    # Derivation 1: the validated device model - its construction order, drivers, resolved names and wiring.
    model = build_model(toml, src)
    build_construction_order(model)
    classes = _classes(src)
    stored: StoredConfig = {}
    for key in model.construction_order:
        if isinstance(key, str):
            path = src / _CORE[key]
            class_name = next(n for n, (p, _) in classes.items() if p == path and _is_store(n, classes))
            name = parse_name_constant(path, model.device, key)
            fields = _fields(path)
        else:
            inst = model.instances[key]
            assert inst.driver_info is not None and inst.resolved_name is not None
            class_name, path, name = inst.driver_info.class_name, inst.driver_info.source_path, inst.resolved_name
            fields = _fields(path)
            for signal in sorted(k for k in inst.wiring if k in WARN_SIGNALS):
                warn = WARN_SIGNALS[signal]
                fields[warn.name] = (warn.field_type, warn.default, warn.min, warn.max, None)
        if _is_store(class_name, classes):
            stored[f"config_{name}.cfg"] = _stored_keys(fields)
    return stored


def from_generated(module_source: str, src: Path) -> StoredConfig:
    # Derivation 2: the generated module's own build_system() constructions and the constants it emits.
    tree = ast.parse(module_source)
    consts = {n.target.id: n.value for n in tree.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None}
    classes = _classes(src)
    build = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "build_system")
    stored: StoredConfig = {}
    for call in (n for n in ast.walk(build) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in classes):
        class_name = call.func.id if isinstance(call.func, ast.Name) else ""
        if not _is_store(class_name, classes):
            continue
        path = classes[class_name][0]
        ext = ""
        for k in call.keywords:
            if k.arg == "name_ext" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
                ext = k.value.value
        base = parse_name_constant(path, "generated", class_name)
        fields = _fields(path)
        signals = [k.value for k in call.keywords if k.arg == "signals"]
        for group in (g for g in signals if isinstance(g, ast.Tuple)):
            for signal in (s for s in group.elts if isinstance(s, ast.Call)):
                schema = _eval_literal(signal.args[2], consts)
                assert isinstance(schema, tuple)
                fields.update({field[0]: tuple(field[1:]) for field in schema})
        stored[f"config_{base}_{ext}.cfg" if ext else f"config_{base}.cfg"] = _stored_keys(fields)
    return stored


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_both_derivations_of_the_stored_config_agree(device: str) -> None:
    toml = REPO_ROOT / "devices" / f"{device}.toml"
    model_view = from_model(toml, SRC)
    generated_view = from_generated(generate_device(toml, SRC, build_date="2026-01-01").module_source, SRC)
    assert model_view == generated_view
    assert {"config_SYSTEM.cfg", "config_WIFI.cfg", "config_NTP.cfg"} <= set(model_view), model_view


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_a_construction_the_model_does_not_know_fails(device: str) -> None:
    toml = REPO_ROOT / "devices" / f"{device}.toml"
    source = generate_device(toml, SRC, build_date="2026-01-01").module_source
    tampered = source.replace("cfg_path=cfg_path, log=log_fram)", "cfg_path=cfg_path, log=log_fram, name_ext='x')", 1)
    assert tampered != source
    assert from_model(toml, SRC) != from_generated(tampered, SRC)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_special_alone_fields_are_not_stored(device: str) -> None:
    toml = REPO_ROOT / "devices" / f"{device}.toml"
    stored = from_model(toml, SRC)
    assert stored["config_SYSTEM.cfg"] == {"DebugLevel": "int"}
    # ResetVOC carries a special value only: a device with an SGP40 stores the rest of its schema, never that field.
    if any(spec.driver == "sgp40" for spec in build_model(toml, SRC).instances.values()):
        sgp_files = [name for name in stored if name.startswith("config_SGP40")]
        assert sgp_files, sorted(stored)
        assert all("ResetVOC" not in stored[name] for name in sgp_files), {name: stored[name] for name in sgp_files}
