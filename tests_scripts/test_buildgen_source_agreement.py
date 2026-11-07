"""The facts buildgen restates from src/ and its owner-kept catalogs, pinned to their sources both ways: a
restated value that drifts, a driver a build table or the errcount catalog misses, a stale row, or a label
naming one chip of a family fails here (SPECIFICATION.md K.3, L.6.6)."""

import ast
import functools
import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen import definitions
from buildgen.buildspec import BUS_KIND_BY_DRIVER, REQUIRED_TOML_FIELDS
from buildgen.definitions import definitions_for_toml
from buildgen.driver_registry import _OVERRIDES, DriverInfo, resolve_driver
from buildgen.generate import generate_device
from buildgen.jsontypes import JsonValue
from buildgen.schema_ast import _FIELD_SCHEMA_LEN, extract_field_schemas
from buildgen.web_tag import parse_web_group_tags

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src"
_READER_BASES = frozenset({"SensorReader", "SensorReaderConfig"})
_BUS_KINDS = {"I2C": "i2c", "SPI": "spi", "UART": "uart"}
_PAUSE_LABEL = re.compile(r"Pause backups for (\d+) minutes")


def _base_names(cls: ast.ClassDef) -> "set[str]":
    return {base.id for base in cls.bases if isinstance(base, ast.Name)}


def _bus_kind(info: DriverInfo) -> "str | None":
    # The bus a driver's constructor takes first ("I2C", "'UART | None'", ...), None for a bus-less one.
    cls = next(c for c in _classes(_tree(info.source_path)) if c.name == info.class_name)
    init = next(item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == "__init__")
    annotation = init.args.args[1].annotation
    text = ast.unparse(annotation).strip("'\"") if annotation is not None else ""
    return _BUS_KINDS.get(re.split(r"[\s|]", text)[0])


def _classes(tree: ast.Module) -> "list[ast.ClassDef]":
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _command_callback(device: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(_module_source(device))
    return next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "_system_cmd_callback")


def _command_options(device: str) -> "list[tuple[str, str]]":
    # (value, label) of every option the device's System page offers for SystemCmd.
    found: list[tuple[str, str]] = []
    for section in _dicts(definitions_for_toml(device_toml(device), _SRC)["sections"]):
        for group in _dicts(section.get("groups")):
            for field in _dicts(group.get("fields", [])):
                if field["key"] == "SystemCmd":
                    found += [(str(option["value"]), str(option["label"])) for option in _dicts(field["options"])]
    return found


def _dicts(value: JsonValue) -> "list[dict[str, JsonValue]]":
    assert isinstance(value, list), value
    assert all(isinstance(item, dict) for item in value), value
    return [item for item in value if isinstance(item, dict)]


@functools.cache
def _drivers() -> "dict[str, DriverInfo]":
    # Every driver the registry resolves: each asy_<name>_driver.py defining a reader class, plus the override
    # table; a bus driver (asy_i2c_driver.py, ...) defines none and is no TOML driver.
    named = {p.stem.removeprefix("asy_").removesuffix("_driver"): p for p in sorted(_SRC.glob("asy_*_driver.py"))}
    readers = {name for name, path in named.items() if any(_base_names(cls) & _READER_BASES for cls in _classes(_tree(path)))}
    return {name: resolve_driver(name, _SRC, "scan") for name in sorted(readers | set(_OVERRIDES))}


@functools.cache
def _module_source(device: str) -> str:
    return generate_device(device_toml(device), _SRC, _REPO / "ext").module_source


def _owns_cfgmgr(tree: ast.Module, class_name: "str | None" = None) -> bool:
    # A SensorReaderConfig subclass, or a class assigning a ConfigManager to self.cfgmgr (the system service).
    for cls in (c for c in _classes(tree) if class_name is None or c.name == class_name):
        if "SensorReaderConfig" in _base_names(cls):
            return True
        for node in ast.walk(cls):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func).endswith("ConfigManager") and any(
                isinstance(target, ast.Attribute) and target.attr == "cfgmgr" for target in node.targets
            ):
                return True
    return False


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_the_schema_record_width_is_the_config_managers_field_schema() -> None:
    alias = next(
        node.value for node in ast.walk(_tree(_SRC / "asy_config_manager.py"))
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "FieldSchema" for target in node.targets)
    )
    assert isinstance(alias, ast.Subscript), ast.unparse(alias)
    assert isinstance(alias.slice, ast.Tuple), ast.unparse(alias)
    assert len(alias.slice.elts) == _FIELD_SCHEMA_LEN


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_backup_pause_label_names_the_callbacks_duration(device: str) -> None:
    calls = [node for node in ast.walk(_command_callback(device)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pause_permanent_storage"]
    assert len(calls) == 1, f"{len(calls)} pause_permanent_storage() calls in _system_cmd_callback()"
    (seconds,) = calls[0].args
    assert isinstance(seconds, ast.Constant), ast.unparse(seconds)
    label = dict(_command_options(device))["mempause"]
    match = _PAUSE_LABEL.fullmatch(label)
    assert match is not None, label
    assert int(match.group(1)) * 60 == seconds.value


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_system_command_words_are_the_servers_and_the_callbacks(device: str) -> None:
    # The page offers exactly the words the webserver accepts, in its order, and the callback runs each.
    served = ast.literal_eval(next(
        node.value.args[0] for node in _tree(_SRC / "asy_webserver_service.py").body
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_SYSTEM_CMDS" for t in node.targets) and isinstance(node.value, ast.Call)
    ))
    dispatched = [
        node.comparators[0].value for node in ast.walk(_command_callback(device))
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "cmd" and isinstance(node.comparators[0], ast.Constant)
    ]
    assert [value for value, _label in _command_options(device)] == list(served) == dispatched


def test_every_driver_has_its_build_table_rows() -> None:
    drivers = _drivers()
    assert set(REQUIRED_TOML_FIELDS) == set(drivers), "buildspec.REQUIRED_TOML_FIELDS rows and the resolvable drivers differ"
    for name, info in drivers.items():
        bus = _bus_kind(info)
        assert BUS_KIND_BY_DRIVER.get(name) == bus, f"{name}: its constructor takes a {bus} bus, BUS_KIND_BY_DRIVER says {BUS_KIND_BY_DRIVER.get(name)}"
        assert ("bus" in REQUIRED_TOML_FIELDS[name]) == (bus is not None), f"{name}: a bus field is required iff the driver takes a bus"


def test_every_driver_and_mandatory_module_has_its_errcount_rows() -> None:
    catalog = {key: has_cfgmgr for key, _label, has_cfgmgr in definitions._ERRCOUNT_CATALOG}
    owners = {name: _owns_cfgmgr(_tree(info.source_path), info.class_name) for name, info in _drivers().items()}
    owners |= {key: _owns_cfgmgr(_tree(_SRC / filename)) for key, filename in definitions._MANDATORY_ERRCOUNT_FILES.items()}
    assert catalog == owners, "the errcount catalog's (row, CFGMGR_ companion) pairs differ from the sources"
    assert set(definitions._CFGMGR_LABEL) == {key for key, has_cfgmgr in catalog.items() if has_cfgmgr}


def test_the_bmp3xx_labels_name_the_family() -> None:
    # The driver serves BMP384/388/390: every label names the family, never one chip.
    assert {key: label for key, label, _has_cfgmgr in definitions._ERRCOUNT_CATALOG}["bmp3xx"] == "BMP3xx"
    assert definitions._CFGMGR_LABEL["bmp3xx"] == "BMP3xx Config Store"
    groups = parse_web_group_tags(_SRC / "asy_bmp3xx_driver.py", "scan", "bmp3xx")
    assert [group.label for group in groups] == ["BMP3xx — Pressure, Temperature"] * 2


def test_the_dispatch_fields_page_bounds_are_the_servers_validation_records() -> None:
    # PauseTime's and LightCmdLED's page fields restate the webserver's validation records: their bounds stay equal.
    webserver = _SRC / "asy_webserver_service.py"
    (pause,) = _dicts(definitions._NOTIFICATION_PAUSE_GROUP["fields"])
    _type, _default, low, high, _special = extract_field_schemas(webserver)["PauseTime"]
    assert (pause["key"], pause["min"], pause["max"], pause.get("float", False)) == ("PauseTime", low, high, _type == "float")
    (led,) = _dicts(definitions._NOTIFICATION_FLASH_GROUP["fields"])
    records = ast.literal_eval(next(
        node.value for node in _tree(webserver).body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_LIGHT_CMD_FIELDS" and node.value is not None
    ))
    page = [(sub["key"], sub["min"], sub["max"], sub.get("float", False)) for sub in _dicts(led["subFields"])]
    assert page == [(name, low, high, kind == "float") for name, kind, _default, low, high, _special in records]
