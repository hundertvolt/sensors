"""End-to-end: buildgen.generate.generate_device() against all 6 real devices/*.toml plus the
mandatory synthetic "novel combination" fixture (BUILD_CHAIN_PLAN.md acceptance criteria #2) -
the full validate -> sort -> generate pipeline from one TOML file, no code changes elsewhere."""

# Correctness-proof scope: generated output is proven syntactically valid Python matching the
# documented construction-order/wiring shape (ast.parse() + structural inspection), never executed
# under a real interpreter - booting a generated module is Session 5's digital-twin work.

import ast
from pathlib import Path

import pytest
from _toml_fixtures import base_doc, write_doc

from buildgen.errors import BuildError
from buildgen.generate import generate_device

DEVICE_NAMES = ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"]


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_generates_syntactically_valid_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    tree = ast.parse(result.module_source, filename=f"sensortask_{device}.py")
    assert any(isinstance(n, ast.AsyncFunctionDef) and n.name == "build_system" for n in tree.body)
    assert any(isinstance(n, ast.AsyncFunctionDef) and n.name == "main" for n in tree.body)
    ast.parse(result.boot_entry_source, filename=f"{device}_boot.py")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_imports_the_right_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert f"from sensortask_{device} import main" in result.boot_entry_source


def test_novel_combo_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    # The mandatory synthetic "novel combination" fixture (BUILD_CHAIN_PLAN.md's acceptance
    # criteria #2): existing drivers mixed in a layout none of the 6 real devices use (two SCD30s,
    # SGP40 independently compensated - temperature from the second SCD30, humidity from the first
    # (§2.9) - BMP3xx at the alternate address, a partial notification signal set) - proving the
    # generator's generality, not just the 6 hand-verified real files.
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_primary" in result.module_source
    assert "scd30_secondary" in result.module_source
    assert "SGP40_Reader(i2c1, temperature_source=scd30_secondary, temperature_field='Temp'" in result.module_source
    assert "humidity_source=scd30_primary, humidity_field='Hum'" in result.module_source
    # Only warn_co2 is wired - warn_voc/warn_hum must not appear at all.
    assert "WarnCO2" in result.module_source
    assert "WarnVOC" not in result.module_source
    assert "WarnHum" not in result.module_source


def test_novel_combo_construction_order_is_topologically_valid(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "secondary")) < order.index(("sgp40", ""))
    assert order.index(("fram", "")) < order.index(("scd30", "primary"))
    assert order.index(("neopixel", "")) < order.index(("notification", ""))


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    # Axis 9's own dedicated multi-instance fixture (§10.7 item 1): 2x scd30 + 2x sgp40 (on
    # different buses - sgp40 has no address-select pin), one sgp40 wired entirely to a real scd30,
    # the other mixing a cross-driver-type reference (bmp3xx's own Temp) with an explicit default -
    # proving §2.9's "any producer exposing a matching attribute name" claim directly, not just
    # satisfying it structurally.
    result = generate_device(fixtures_dir / "multi_instance.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_a" in result.module_source
    assert "scd30_b" in result.module_source
    assert "sgp40_a" in result.module_source
    assert "sgp40_b" in result.module_source
    assert "temperature_source=scd30_b, temperature_field='Temp'" in result.module_source
    assert "humidity_source=scd30_b, humidity_field='Hum'" in result.module_source
    assert "temperature_source=bmp3xx_only, temperature_field='Temp'" in result.module_source
    assert "humidity_source=_DefaultHumiditySource(relative_humidity=35)" in result.module_source
    assert "_DefaultSignalSink().request_signal" in result.module_source
    # led_target/fram_target both left unwired - conn.set_ext_led/sysfunct's fram kwarg both absent.
    assert "conn.set_ext_led(" not in result.module_source
    assert "SystemService(ntp.ntp_issynced, watchdog=watchdog, cfg_path=cfg_path" in result.module_source
    # Only sgp40_a is monitored via warn_voc - exactly one NotificationSignal is registered
    # (warn_co2/warn_hum are absent from this fixture entirely, and sgp40_b is never a warn_* source).
    assert result.module_source.count("NotificationSignal(") == 1
    assert "NotificationSignal('WarnVOC', sgp40_a, 'VOC'" in result.module_source


def test_device_without_notification_or_neopixel_omits_their_wiring(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] not in ("neopixel", "notification")]
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "minimal", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "notification_led=" not in result.module_source
    assert "notification_pause=" not in result.module_source
    assert '"notification":' not in result.module_source.split("status_sources=")[1].split("\n")[0] if "status_sources=" in result.module_source else True


def test_wiring_defaults_generate_inline_provider_construction(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # §2.6's generated-code shape: the default provider is constructed inline, at the exact
    # call-site the real wiring expression would occupy, with no separate named global.
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = {"default": True}
    doc["instance"][1]["wiring"]["temperature_source"] = {"default": True, "temperature": 20}
    result = generate_device(write_doc(tmp_path, "with_defaults", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "_DefaultSignalSink().request_signal" in result.module_source
    assert "temperature_source=_DefaultTemperatureSource(temperature=20)" in result.module_source
    # Every defaulted per-value field always resolves to (provider, "value") - the fixed contract
    # every _Default<Field> class's get_data() follows (§10.1 item 1) - not the real field name.
    assert "temperature_field='value'" in result.module_source
    # humidity_source stays a real reference - not defaulted in this fixture.
    assert "humidity_source=scd30, humidity_field='Hum'" in result.module_source


def test_device_level_led_target_unwired_omits_set_ext_led(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # §7.1 #5: test_device_wiring_optional_field_absent_is_fine (test_buildgen_validate.py) already
    # confirms validate.py accepts neopixel-present-but-led_target-unwired - but nothing confirmed
    # the generated module itself comes out right (conn.set_ext_led(...) correctly omitted).
    doc = base_doc()
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "no_led_target", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "conn.set_ext_led(" not in result.module_source


def test_device_without_sgp40_omits_maintenance_sensors(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "sgp40"]
    del doc["instance"][0]["wiring"]  # scd30's own optional fram_target - unrelated to sgp40's removal
    result = generate_device(write_doc(tmp_path, "nosgp40", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "maintenance_sensors=" not in result.module_source


def test_build_error_reports_device_and_field(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["device"]["hotspot_time_min"]
    path = write_doc(tmp_path, "broken_device", doc)
    with pytest.raises(BuildError) as exc_info:
        generate_device(path, src_dir)
    assert "broken_device" in str(exc_info.value)
    assert "hotspot_time_min" in str(exc_info.value)


def test_cli_writes_module_and_boot_entry_to_out_dir(repo_root: Path, tmp_path: Path) -> None:
    from buildgen.generate import main

    out_dir = tmp_path / "out"
    exit_code = main([str(repo_root / "devices" / "wozi.toml"), "--out-dir", str(out_dir)])
    assert exit_code == 0
    assert (out_dir / "sensortask_wozi.py").is_file()
    assert (out_dir / "wozi_boot.py").is_file()
    ast.parse((out_dir / "sensortask_wozi.py").read_text())


def test_cli_prints_module_source_without_out_dir(repo_root: Path, capsys: pytest.CaptureFixture) -> None:
    from buildgen.generate import main

    exit_code = main([str(repo_root / "devices" / "wozi.toml")])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "async def build_system(" in captured.out


def test_cli_reports_build_error_on_stderr_and_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from buildgen.generate import main

    doc = base_doc()
    del doc["device"]["hotspot_time_min"]
    path = write_doc(tmp_path, "broken_device", doc)
    exit_code = main([str(path), "--src-dir", str(Path(__file__).resolve().parent.parent / "src")])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "hotspot_time_min" in captured.err


def test_hostname_and_hotspot_password_are_not_yet_wired_into_generated_code(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # Documents a real, pre-existing gap found during this session's own review (see
    # buildgen/validate.py's _check_device_table() comment for the full account): [device].name/
    # hostname/hotspot_password are validated (presence, shape, the SensorStation<name> formula)
    # but neither this generator nor any hand-written sensortask_*.py actually has a
    # constructor-time injection point for them - AsyConnTime's Hostname/HotspotPW are
    # ConfigManager-persisted runtime values with one hardcoded default shared by every device's
    # build. This test is a tripwire: it should start failing (and get deleted/updated) the day a
    # future session actually wires either value into generated code.
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "SensorStationWozi" not in result.module_source
    assert "12345678" not in result.module_source
