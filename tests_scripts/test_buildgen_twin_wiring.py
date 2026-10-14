"""Tests for buildgen.twin_wiring (SPECIFICATION.md Part L.4): the plan's shape and JSON round trip per device,
addresses read from the drivers, the bus pins and UART pair, the twin loading an explicit plan, and the two
synthetic fixtures beyond the real devices."""

import ast
import contextlib
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml, devices_with
from _script_loader import load_script_module

from buildgen import twin_wiring
from buildgen.buildspec import BUS_KIND_BY_DRIVER, FIXED_ADDRESS_DRIVERS
from buildgen.driver_registry import DriverInfo, resolve_driver
from buildgen.errors import BuildError
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.twin_wiring import compute_twin_wiring, fixed_address
from buildgen.validate import build_model

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType


def _driver_address_const(src_dir: Path, driver: str) -> int:
    # The test's own AST read of the driver file's `_<DRIVER>_ADDR = const(<int>)`, kept apart from
    # buildgen's reader so the two can disagree.
    tree = ast.parse((src_dir / f"asy_{driver}_driver.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == [f"_{driver.upper()}_ADDR"]:
            call = node.value
            assert isinstance(call, ast.Call) and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int)
            return call.args[0].value
    raise AssertionError(f"asy_{driver}_driver.py has no _{driver.upper()}_ADDR")


def _toml_uart_pair(toml_path: Path) -> "dict[str, str] | None":
    # The expected pair read straight from the TOML, independent of build_model()'s own parse.
    with toml_path.open("rb") as f:
        links = [i for i in tomllib.load(f).get("instance", []) if i.get("driver") == "uart_link"]
    if not links:
        return None
    return {f"{i['role']}_bus": i["bus"] for i in links}


def _loaded_from(directory: Path, names: "set[str]") -> "list[str]":
    return sorted(n for n in names if Path(getattr(sys.modules[n], "__file__", None) or "/").resolve().parent == directory)


@contextlib.contextmanager
def _on_path(directory: str) -> "Iterator[None]":
    # A failing body restores too. Only the modules loaded from `directory` go: a stdlib module they
    # imported shadows nothing, and dropping it would split one module into two copies in this process.
    before, inserted = set(sys.modules), directory not in sys.path
    if inserted:
        sys.path.insert(0, directory)
    try:
        yield
    finally:
        if inserted:
            sys.path.remove(directory)
        for name in _loaded_from(Path(directory).resolve(), set(sys.modules) - before):
            del sys.modules[name]


@pytest.fixture
def digital_twin_machine(repo_root: Path) -> "Iterator[ModuleType]":
    # digital_twin/machine.py has no MicroPython-only import at module scope (only individual method
    # bodies do), so plain `import machine` under this suite's own CPython/pytest process works.
    with _on_path(str(repo_root / "digital_twin")):
        import machine  # type: ignore[import-not-found]  # only resolvable once digital_twin/ is on sys.path, above

        yield machine


@pytest.mark.parametrize("body", ["passes", "raises"])
def test_the_twin_directory_leaves_no_module_and_no_path_entry_behind(repo_root: Path, body: str) -> None:
    # The twin's `machine` would shadow any other `machine` a later test imports in this process.
    twin_dir = (repo_root / "digital_twin").resolve()
    modules, path = set(sys.modules), list(sys.path)
    with contextlib.suppress(RuntimeError), _on_path(str(twin_dir)):
        load_script_module(twin_dir / "machine.py", "zz_twin_machine_probe")
        if body == "raises":
            raise RuntimeError("a failing test body")
    assert (_loaded_from(twin_dir, set(sys.modules) - modules), sys.path) == ([], path)


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


# ---------------------------------------------------------------------------
# The twin applies each device's real, generated plan - not a hand-typed literal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_configure_wiring_applies_each_devices_real_generated_plan(tmp_path: Path, src_dir: Path, digital_twin_machine: "ModuleType", device: str) -> None:
    # The plan file every twin consumer reads, written and read back as JSON, then applied: the twin
    # holds exactly the generated plan, with no hand-kept literal.
    expected = compute_twin_wiring(build_model(device_toml(device), src_dir))
    plan_file = tmp_path / f"sensortask_{device}_wiring_plan.json"
    plan_file.write_text(json.dumps(expected), encoding="utf-8")
    digital_twin_machine.configure_wiring(json.loads(plan_file.read_text(encoding="utf-8")))
    assert digital_twin_machine._current_wiring_plan() == expected


def test_a_twin_with_no_plan_configured_has_no_default_wiring(digital_twin_machine: "ModuleType") -> None:
    # Every plan is explicit: a bus asked for before configure_wiring() fails loudly, never one device's layout.
    with pytest.raises(RuntimeError, match=r"^no wiring plan configured - call machine\.configure_wiring\(plan\) before constructing a bus$"):
        digital_twin_machine._current_wiring_plan()


# ---------------------------------------------------------------------------
# Shape / JSON-round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_generated_plan_is_json_round_trippable(repo_root: Path, src_dir: Path, device: str) -> None:
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert json.loads(json.dumps(plan)) == plan


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_wires_fram_on_its_own_declared_spi_bus(repo_root: Path, src_dir: Path, device: str) -> None:
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert set(plan["spi"]) == {"spi0"}
    assert plan["spi"]["spi0"]["driver"] == "fram"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_uart_pair_names_the_two_generated_bus_globals(repo_root: Path, src_dir: Path, device: str) -> None:
    toml_path = repo_root / "devices" / f"{device}.toml"
    assert compute_twin_wiring(build_model(toml_path, src_dir))["uart"] == _toml_uart_pair(toml_path)


@pytest.mark.parametrize("toml_path", [*(f"devices/{d}.toml" for d in DEVICE_NAMES), "tests_scripts/buildgen_fixtures/multi_instance.toml", "tests_scripts/buildgen_fixtures/novel_combo.toml"])
def test_the_plan_carries_every_declared_bus_s_pins_by_role(repo_root: Path, src_dir: Path, toml_path: str) -> None:
    # Read straight from the TOML: each [bus.<id>] table's `<role>_pin` fields, keyed by role, in TOML order.
    with (repo_root / toml_path).open("rb") as f:
        buses = tomllib.load(f).get("bus", {})
    expected = {bus: {key[: -len("_pin")]: value for key, value in table.items() if key.endswith("_pin")} for bus, table in buses.items()}
    plan = compute_twin_wiring(build_model(repo_root / toml_path, src_dir))
    assert (list(plan["pins"]), plan["pins"]) == (list(expected), expected)


def test_at_least_one_shipped_device_wires_a_uart_pair(repo_root: Path) -> None:
    # Keeps the per-device check above from passing vacuously on an all-None device set.
    pairs = [_toml_uart_pair(repo_root / "devices" / f"{d}.toml") for d in DEVICE_NAMES]
    assert any(p is not None and set(p) == {"initiator_bus", "responder_bus"} for p in pairs)


@pytest.mark.parametrize("device", devices_with("bmp3xx"))
def test_bmp3xx_address_is_read_from_the_toml_not_the_fixed_table(src_dir: Path, device: str) -> None:
    # bmp3xx is ADDRESS_CAPABLE, not FIXED_ADDRESS - proves compute_twin_wiring() actually reads
    # spec.fields["address"] for it rather than (incorrectly) falling back to a driver constant.
    stated = [i["address"] for i in tomllib.loads(device_toml(device).read_text(encoding="utf-8"))["instance"] if i["driver"] == "bmp3xx"]
    plan = compute_twin_wiring(build_model(device_toml(device), src_dir))
    bmp_attachments = [a for attachments in plan["buses"].values() for a in attachments if a["driver"] == "bmp3xx"]
    assert [a["address"] for a in bmp_attachments] == stated


# The fixed-address I2C drivers, derived: uart_link is fixed-address too, but has no address at all.
_FIXED_I2C_DRIVERS = sorted(d for d in FIXED_ADDRESS_DRIVERS if BUS_KIND_BY_DRIVER[d] == "i2c")


@pytest.mark.parametrize("driver", _FIXED_I2C_DRIVERS)
def test_fixed_address_reads_the_drivers_own_address_constant(src_dir: Path, driver: str) -> None:
    assert fixed_address(resolve_driver(driver, src_dir, "test")) == _driver_address_const(src_dir, driver)


@pytest.mark.parametrize("toml_path", [*(f"devices/{d}.toml" for d in DEVICE_NAMES), "tests_scripts/buildgen_fixtures/multi_instance.toml", "tests_scripts/buildgen_fixtures/novel_combo.toml"])
def test_every_fixed_address_in_a_plan_is_the_drivers_own_constant(repo_root: Path, src_dir: Path, toml_path: str) -> None:
    plan = compute_twin_wiring(build_model(repo_root / toml_path, src_dir))
    attachments = [a for bus in plan["buses"].values() for a in bus if a["driver"] in FIXED_ADDRESS_DRIVERS]
    assert [a["address"] for a in attachments] == [_driver_address_const(src_dir, a["driver"]) for a in attachments]


@pytest.mark.parametrize("toml_path", [*(f"devices/{d}.toml" for d in DEVICE_NAMES), "tests_scripts/buildgen_fixtures/multi_instance.toml", "tests_scripts/buildgen_fixtures/novel_combo.toml"])
def test_the_plan_lists_every_declared_driver_once(repo_root: Path, src_dir: Path, toml_path: str) -> None:
    # compute_twin_wiring() is the plan's one producer: "instances" is its own key, read here straight from the TOML.
    with (repo_root / toml_path).open("rb") as f:
        declared = sorted({i["driver"] for i in tomllib.load(f)["instance"]})
    assert compute_twin_wiring(build_model(repo_root / toml_path, src_dir))["instances"] == declared


def test_twin_machine_has_no_chip_fake_for_an_unknown_driver_fails_loud(digital_twin_machine: "ModuleType") -> None:
    # _build_i2c_chip()'s analogue of the no-address-rule test below: an attachment naming a
    # driver the twin has no fake for must fail loud, not produce a bus with a missing device.
    # Driven directly, since the two sides are hand-kept in sync for one fixed driver set.
    with pytest.raises(ValueError, match=r"digital twin has no I2C chip fake for driver 'not_a_real_driver'"):
        digital_twin_machine._build_i2c_chip({"driver": "not_a_real_driver"})


def test_bus_attached_driver_with_no_address_rule_fails_loud_not_silently_miswired(monkeypatch: pytest.MonkeyPatch) -> None:
    # Guards compute_twin_wiring()'s defensive fallback: a driver added to BUS_ATTACHED_DRIVERS
    # without a matching address rule here must fail loud, never silently mis-wire the twin.

    # Unreachable through any real TOML, buildspec.py's three classification sets partitioning
    # BUS_ATTACHED_DRIVERS exhaustively, so the gap is constructed by monkeypatch - the same
    # technique the missing-buildspec-entry test uses for its own unreachable branch.
    monkeypatch.setattr(twin_wiring, "BUS_ATTACHED_DRIVERS", frozenset({"fakebus"}))
    spec = InstanceSpec(driver="fakebus", name_ext="", fields={"bus": "i2c0"}, wiring={}, order_index=0)
    model = DeviceModel(device="test", path=Path("test.toml"), doc={}, instances={("fakebus", ""): spec})
    # A BuildError, not a ValueError: the generator's one error contract, a line naming rule, place and fix.
    with pytest.raises(BuildError, match=r"^\[test/fakebus\] .*no address rule.* - fix: ") as caught:
        compute_twin_wiring(model)
    assert caught.value.rule == "twin.no-address-rule"


def test_a_fixed_address_driver_without_its_address_constant_fails_the_twin_rule(tmp_path: Path) -> None:
    # A driver file that lost its _<DRIVER>_ADDR const: the plan cannot place the chip, so the build says which rule broke.
    (tmp_path / "asy_scd30_driver.py").write_text("_SCD30_TIMEOUT_MS = const(20)\n")
    info = DriverInfo("scd30", "asy_scd30_driver", "SCD30_Reader", "sensor", tmp_path / "asy_scd30_driver.py", True)
    with pytest.raises(BuildError, match=r"_SCD30_ADDR.* - fix: ") as caught:
        fixed_address(info)
    assert caught.value.rule == "twin.no-address-rule"

    spec = InstanceSpec(driver="scd30", name_ext="", fields={"bus": "i2c0", "irq_pin": 2}, wiring={}, order_index=0, driver_info=info)
    model = DeviceModel(device="test", path=Path("test.toml"), doc={}, instances={("scd30", ""): spec})
    with pytest.raises(BuildError, match=r"^\[test/scd30\] ") as caught:
        compute_twin_wiring(model)
    assert caught.value.rule == "twin.no-address-rule"


# ---------------------------------------------------------------------------
# Mandatory synthetic fixtures - proving generality beyond the real, hand-verified devices
# (mirrors test_buildgen_definitions.py's own fixture coverage)
# ---------------------------------------------------------------------------


def test_novel_combo_fixture_wires_two_scd30_instances_on_separate_buses(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "novel_combo.toml", src_dir)
    plan = compute_twin_wiring(model)
    i2c0_scd30 = next(a for a in plan["buses"]["i2c0"] if a["driver"] == "scd30")
    i2c1_scd30 = next(a for a in plan["buses"]["i2c1"] if a["driver"] == "scd30")
    assert i2c0_scd30 == {"driver": "scd30", "name_ext": "primary", "address": 0x61, "irq_pin": 2}
    assert i2c1_scd30 == {"driver": "scd30", "name_ext": "secondary", "address": 0x61, "irq_pin": 10}
    # Same fixed address on two different buses - never a collision (buildgen.validate's own
    # per-bus address-collision check only scopes within one bus).
    bmp3xx = next(a for a in plan["buses"]["i2c0"] if a["driver"] == "bmp3xx")
    assert bmp3xx["address"] == 0x76  # the alternate hardwired-address-select value
    assert plan["spi"]["spi0"]["max_size"] == 0x40000


def test_multi_instance_fixture_wires_three_devices_sharing_one_bus(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "multi_instance.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert len(plan["buses"]["i2c0"]) == 3  # scd30_a + bmp3xx_only + sgp40_b, all distinct addresses
    addresses = {a["driver"]: a["address"] for a in plan["buses"]["i2c0"]}
    assert addresses == {"scd30": 0x61, "bmp3xx": 0x76, "sgp40": 0x59}
    i2c1_addresses = {a["driver"]: a["address"] for a in plan["buses"]["i2c1"]}
    assert i2c1_addresses == {"scd30": 0x61, "sgp40": 0x59}
    assert plan["spi"]["spi0"]["max_size"] == 0x40000
