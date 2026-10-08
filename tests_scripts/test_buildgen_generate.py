"""End-to-end: buildgen.generate.generate_device() against all 6 real devices/*.toml plus the
mandatory synthetic "novel combination" fixture (SPECIFICATION.md Part L.1's acceptance criterion #2) -
the full validate -> sort -> generate pipeline from one TOML file, no code changes elsewhere."""

# Correctness-proof scope: generated output is proven syntactically valid Python matching the
# documented construction-order/wiring shape (ast.parse() + structural inspection), never executed
# under a real interpreter - booting a generated module is Session 5's digital-twin work.

import ast
import re
import shutil
from datetime import datetime
from itertools import pairwise
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES
from _toml_fixtures import base_doc, write_doc

from buildgen.codegen import trigger_spread
from buildgen.definitions import definitions_for_toml
from buildgen.errors import BuildError
from buildgen.generate import GeneratedDevice, generate_device
from buildgen.model import instance_label
from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION


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
def test_real_device_constructs_watchdog_exactly_once(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # The CPython half of test_reset_call_site_invariant.py's WDT check: that one scans
    # committed src/ files and skips sensortask_*.py, which is now vacuous since none is ever
    # committed (Part L.4). The generated module's single WDT() site needs its own proof.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert result.module_source.count("WDT(") == 1


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_feeds_the_watchdog_after_every_setup_call_in_order(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # The boot setup batch must not starve the watchdog however many modules a device wires
    # (Part D.9/G.2), which a feed after every await X.setup() - never inside a loop - is what
    # guarantees. feed_watchdog() itself is unit-tested; this proves codegen emits every call.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    lines = result.module_source.splitlines()
    setup_lines = [i for i, line in enumerate(lines) if re.match(r"\s*await \w+\.setup\(\)\s*$", line)]
    assert len(setup_lines) > 0, "no setup() calls found in the generated boot sequence"
    for i in setup_lines:
        assert lines[i + 1].strip() == "sysfunct.feed_watchdog()", f"{device}: {lines[i].strip()!r} not immediately followed by a feed"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_collects_once_before_and_after_every_setup_call_and_nowhere_else(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # Measure B (PLAN B.1.1, SPECIFICATION.md I.4(f.1)): a placement reset, not hygiene and not
    # compaction. The "nowhere else" half is the load-bearing one - this is a boot-only exception to
    # I.4, so the generated module must not grow a collect anywhere the run phase reaches.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    lines = result.module_source.splitlines()
    setup_lines = [i for i, line in enumerate(lines) if re.match(r"\s*await \w+\.setup\(\)\s*$", line)]
    assert len(setup_lines) > 0, "no setup() calls found in the generated boot sequence"

    for i in setup_lines:
        assert lines[i + 2].strip() == "gc.collect()", (
            f"{device}: {lines[i].strip()!r} feed is not followed by the placement-reset collect"
        )
    first_setup = setup_lines[0]
    assert lines[first_setup - 1].strip() == "gc.collect()", (
        f"{device}: the start-of-list collect is missing before the first setup() call"
    )

    # One per module plus the one before the loop, and not a single one anywhere else in the module.
    assert result.module_source.count("gc.collect()") == len(setup_lines) + 1, (
        f"{device}: expected {len(setup_lines) + 1} collects, found {result.module_source.count('gc.collect()')}"
    )
    assert re.search(r"^import gc$", result.module_source, re.MULTILINE), f"{device}: generated module never imports gc"

    # main() runs the webserver forever after build_system() returns - a collect reaching it would
    # be a run-phase collect, which I.4 forbids outright.
    main_at = next(i for i, line in enumerate(lines) if line.startswith("async def main("))
    assert "gc.collect()" not in "\n".join(lines[main_at:]), f"{device}: main() must carry no collect"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_imports_the_right_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert f"from sensortask_{device} import main" in result.boot_entry_source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_embeds_and_reports_version_and_build_date_exactly_once(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # Part L.7: buildgen.version is the one source of truth for the two version constants, and
    # the build date is explicitly injected rather than computed on-device - which is what lets
    # this assert an exact match instead of a moving "now".
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir, build_date="2026-09-12T10:00:00Z")
    assert result.module_source.count("_FIRMWARE_VERSION = const(") == 1
    assert result.module_source.count("_WEBSITE_VERSION = const(") == 1
    assert result.module_source.count("_BUILD_DATE = const(") == 1
    assert f"_FIRMWARE_VERSION = const({FIRMWARE_VERSION!r})" in result.module_source
    assert f"_WEBSITE_VERSION = const({WEBSITE_VERSION!r})" in result.module_source
    assert "_BUILD_DATE = const('2026-09-12T10:00:00Z')" in result.module_source
    assert 'build_info={"FirmwareVersion": _FIRMWARE_VERSION, "WebsiteVersion": _WEBSITE_VERSION, "BuildDate": _BUILD_DATE}' in result.module_source
    # Regression guard against an earlier, corrected design: the version no longer
    # lives on GET /status's "system" section, so build_info above is its only key.
    assert result.module_source.count('"FirmwareVersion": _FIRMWARE_VERSION') == 1


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_defaults_to_a_real_current_build_date_when_none_is_given(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    match = re.search(r"_BUILD_DATE = const\('([^']+)'\)", result.module_source)
    assert match is not None
    datetime.fromisoformat(match.group(1))  # raises ValueError if malformed; "Z" is UTC, not naive


def _function(source: str, name: str) -> "ast.FunctionDef | ast.AsyncFunctionDef":
    tree = ast.parse(source)
    return next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def _awaited_setups(source: str) -> "list[str]":
    return re.findall(r"^\s*await (\w+)\.setup\(\)\s*$", source, re.MULTILINE)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_main_starts_read_triggers_apart_from_the_timer_starters(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    main = ast.unparse(_function(result.module_source, "main"))
    assert "await sysfunct.start_timers(_collect_trigger_starters(), _collect_timer_starters())" in main
    # start_timers() awaits its own stagger inline, so the old completion flag has no reader left.
    assert "timers_running" not in result.module_source
    assert "ThreadSafeFlag" not in result.module_source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_sets_up_every_sensor_reader_and_the_webserver_last(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # Every logger store is set up in the boot batch, first in its module's setup(): a plain SensorReader
    # (SCD30) included, and the webserver, constructed last, set up last.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    setups = _awaited_setups(result.module_source)
    sensors = [instance_label(spec.key) for spec in result.model.instances.values() if spec.driver_info is not None and spec.driver_info.kind == "sensor"]
    assert sensors
    assert set(sensors) <= set(setups)
    assert setups[-1] == "webserver"
    assert setups.count("webserver") == 1


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_types_every_global_by_the_class_build_system_constructs(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    tree = ast.parse(result.module_source)
    declared = {n.target.id: ast.unparse(n.annotation) for n in tree.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and isinstance(n.value, ast.Constant) and n.value.value is None}
    built = _function(result.module_source, "build_system")
    constructed = {
        n.targets[0].id: ast.unparse(n.value.func)
        for n in ast.walk(built)
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Call) and n.targets[0].id in declared
    }
    assert constructed, device
    for var, class_expr in constructed.items():
        assert declared[var] == f"{class_expr} | None", (var, declared[var])
    assert not [var for var, annotation in declared.items() if "Any" in annotation]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_networking_status_reads_one_wifi_snapshot_and_no_radio(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # One response, one consistent snapshot: every address and the RSSI come from conn.get_data()'s tuple.
    fn = _function(generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source, "_networking_status")
    calls = [ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)]
    assert calls.count("conn.get_data") == 1
    assert not [c for c in calls if c.startswith("conn.") and c not in ("conn.get_data", "conn.get_wifi_uptime")], calls
    snapshot = next(n.targets[0].id for n in ast.walk(fn) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and "conn.get_data()" in ast.unparse(n.value))
    returned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict)
    entries = {k.value: ast.unparse(v) for k, v in zip(returned.keys, returned.values, strict=True) if isinstance(k, ast.Constant)}
    assert "IP" not in entries
    fields = {"IPv4": "IP", "Subnet": "Subnet", "Gateway": "Gateway", "DNS": "DNS", "RSSI": "RSSI", "Mode": "Mode", "Connected": "Connected", "WifiTS": "TS"}
    assert {key: entries[key] for key in fields} == {key: f"{snapshot}.{field}" for key, field in fields.items()}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_networking_status_reads_the_webservers_drop_window(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    fn = _function(generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source, "_networking_status")
    returned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict)
    entries = {k.value: ast.unparse(v) for k, v in zip(returned.keys, returned.values, strict=True) if isinstance(k, ast.Constant)}
    assert entries["HTTPDropped"] == "await webserver.get_dropped_count()"
    guards = [ast.dump(n.test) for n in fn.body if isinstance(n, ast.Assert)]
    assert guards == [ast.dump(ast.parse("conn is not None and ntp is not None and webserver is not None", mode="eval").body)], guards


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_led_callback_takes_the_validated_values_and_only_signals(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # The webserver validates R/G/B/T against its own schemas, so the callback is a plain hand-over.
    source = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source
    fn = _function(source, "_notification_led_callback")
    assert ast.unparse(fn.args) == "r: int, g: int, b: int, t: float"
    assert fn.returns is not None and ast.unparse(fn.returns) == "bool"
    assert [ast.unparse(n) for n in fn.body] == ["assert neopixel is not None", "return neopixel.led_signal(r, g, b, t)"]
    assert "_FIELD_LED_" not in source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_webserver_reads_the_system_uptime_for_its_drop_window(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    source = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source
    call = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and ast.unparse(n.func) == "WebserverService")
    assert [k.arg for k in call.keywords] == ["routes", "serving", "uptime_s", "static", "log"]
    assert next(ast.unparse(k.value) for k in call.keywords if k.arg == "uptime_s") == "sysfunct.get_uptime"


def _settings_groups(source: str, page: str) -> "list[tuple[str, tuple[str, ...], dict[str, str]]]":
    # (module, field names, hook keywords) of each SettingsGroup the generated RouteSources lists for `page`.
    routes = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and ast.unparse(n.func) == "RouteSources")
    settings = next(k.value for k in routes.keywords if k.arg == "settings")
    assert isinstance(settings, ast.Dict)
    groups = next(v for k, v in zip(settings.keys, settings.values, strict=True) if isinstance(k, ast.Constant) and k.value == page)
    assert isinstance(groups, ast.List)
    out = []
    for call in groups.elts:
        assert isinstance(call, ast.Call) and ast.unparse(call.func) == "SettingsGroup"
        out.append((ast.unparse(call.args[0]), ast.literal_eval(call.args[1]), {str(k.arg): ast.unparse(k.value) for k in call.keywords}))
    return out


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_networking_settings_publish_the_hotspot_password_and_the_dns_fallback(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # HotspotPW reconnects with the identity group; DNSFallback needs no hook, the next NTP attempt reads it.
    source = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source
    assert _settings_groups(source, "networking") == [
        ("conn", ("SSID", "PW", "Country", "Hostname", "HotspotPW"), {"post_fct": "conn.reconnect_wifi"}),
        ("conn", ("LEDWifiOn",), {}),
        ("ntp", ("NTPHost", "NTPOffset", "NTPInterval"), {"post_asy_fct": "ntp.ntp_force_sync"}),
        ("ntp", ("DNSFallback",), {}),
    ]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_settings_groups_accept_exactly_what_their_page_shows_as_writable(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # One source: the page's writable fields are what its PUT route's settings groups accept, group by
    # group on Networking (HotspotPW in identity, DNSFallback alone) and as one set on System.
    toml = repo_root / "devices" / f"{device}.toml"
    source = generate_device(toml, src_dir, ext_dir).module_source
    sections = {s["key"]: s for s in definitions_for_toml(toml, src_dir)["sections"]}
    shown = {page: [tuple(f["key"] for f in g["fields"] if f.get("kind") != "readonly" and not f.get("dispatch")) for g in sections[page]["groups"] if "fields" in g] for page in ("networking", "system")}
    accepted = {page: [fields for _module, fields, _hooks in _settings_groups(source, page)] for page in ("networking", "system")}
    assert shown["networking"] == accepted["networking"]
    assert sorted(k for group in shown["system"] for k in group) == sorted(k for group in accepted["system"] for k in group)


def _src_with_read_triggers(src_dir: Path, tmp_path: Path, drivers: "tuple[str, ...]") -> Path:
    # A src/ copy in which exactly the named drivers' reader classes declare their own read triggers.
    copy = tmp_path / "src"
    shutil.copytree(src_dir, copy)
    for path in copy.glob("asy_*_driver.py"):
        text = path.read_text()
        path.write_text(re.sub(r"^    def get_trigger_starters\(self\)[^\n]*:\n        return \[[^\n]*\]\n\n", "", text, flags=re.MULTILINE))
    for driver in drivers:
        path = copy / f"asy_{driver}_driver.py"
        text = path.read_text()
        match = re.search(r"^class \w+_Reader\(SensorReader(?:Config)?\):\n", text, re.MULTILINE)
        assert match is not None, driver
        method = "    def get_trigger_starters(self):\n        return [self.start_timer]\n\n"
        path.write_text(text[: match.end()] + method + text[match.end() :])
    return copy


def _trigger_modules(source: str) -> "list[str]":
    func = _function(source, "_collect_trigger_starters")
    loops = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    if not loops:
        return []
    assert isinstance(loops[0].iter, ast.Tuple)
    return [elt.id for elt in loops[0].iter.elts if isinstance(elt, ast.Name)]


@pytest.mark.parametrize(
    ("device", "expected"),
    # dev: sgp40 and isl29125 share i2c1, bmp3xx sits alone on i2c0 - slots 0, 250, 500 ms;
    # wozi: sgp40 and bmp3xx share i2c1 (scd30 keeps its own tick) - slots 0, 333 ms.
    [("dev", ["sgp40", "bmp3xx", "isl29125"]), ("wozi", ["sgp40", "bmp3xx"])],
)
def test_read_triggers_are_collected_with_bus_sharing_readers_furthest_apart(repo_root: Path, src_dir: Path, ext_dir: Path, tmp_path: Path, device: str, expected: "list[str]") -> None:
    src = _src_with_read_triggers(src_dir, tmp_path, ("bmp3xx", "isl29125", "sgp40"))
    result = generate_device(repo_root / "devices" / f"{device}.toml", src, ext_dir)
    assert _trigger_modules(result.module_source) == expected
    assert "scd30" not in _trigger_modules(result.module_source)


def _collected_modules(source: str, collector: str) -> "list[str]":
    (loop,) = [n for n in ast.walk(_function(source, collector)) if isinstance(n, ast.For)]
    assert isinstance(loop.iter, ast.Tuple)
    return [elt.id for elt in loop.iter.elts if isinstance(elt, ast.Name)]


def _fram_var(result: GeneratedDevice) -> str:
    (key,) = [key for key in result.model.instances if key[0] == "fram"]
    return instance_label(key)


@pytest.mark.parametrize("device", DEVICE_NAMES)
@pytest.mark.parametrize("collector", ["_collect_task_starters", "_collect_timer_starters"])
def test_real_device_collects_the_fram_managers_starters(repo_root: Path, src_dir: Path, ext_dir: Path, device: str, collector: str) -> None:
    # A declared chip that fails setup escalates through its supervised task like any other chip.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert _fram_var(result) in _collected_modules(result.module_source, collector)


@pytest.mark.parametrize("collector", ["_collect_task_starters", "_collect_timer_starters"])
def test_a_fixture_without_fram_target_still_collects_its_declared_fram(fixtures_dir: Path, src_dir: Path, ext_dir: Path, collector: str) -> None:
    result = generate_device(fixtures_dir / "multi_instance.toml", src_dir, ext_dir)
    assert "storage=None" in result.module_source  # [device.wiring].fram_target unwired
    assert _fram_var(result) in _collected_modules(result.module_source, collector)


def test_bus_spread_takes_the_largest_group_first_and_keeps_construction_order_on_ties() -> None:
    order = trigger_spread([("a", "i2c0"), ("b", "i2c1"), ("c", "i2c1"), ("d", "i2c0"), ("e", "i2c1"), ("f", "spi0")])
    assert order == ["b", "a", "f", "c", "d", "e"]
    assert trigger_spread([]) == []


def test_a_device_whose_readers_declare_no_read_triggers_collects_none(repo_root: Path, src_dir: Path, ext_dir: Path, tmp_path: Path) -> None:
    src = _src_with_read_triggers(src_dir, tmp_path, ())
    for path in src.glob("asy_*_driver.py"):
        assert "def get_trigger_starters" not in path.read_text(), path.name
    result = generate_device(repo_root / "devices" / "dev.toml", src, ext_dir)
    assert _trigger_modules(result.module_source) == []
    assert ast.unparse(_function(result.module_source, "_collect_trigger_starters")).rstrip().endswith("return []")


def test_novel_combo_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    # The mandatory synthetic novel-combination fixture (Part L.1's criterion 2): existing
    # drivers in a layout no real device uses - two SCD30s, an SGP40 compensated from each,
    # BMP3xx at its alternate address - proving generality beyond the six hand-verified files.
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_primary" in result.module_source
    assert "scd30_secondary" in result.module_source
    assert "SGP40_Reader(i2c1, temperature=ValueRef(scd30_secondary, 'Temp')" in result.module_source
    assert "humidity=ValueRef(scd30_primary, 'Hum')" in result.module_source
    # Only warn_co2 is wired - warn_voc/warn_hum must not appear at all.
    assert "WarnCO2" in result.module_source
    assert "WarnVOC" not in result.module_source
    assert "WarnHum" not in result.module_source
    # ISL29125 on i2c0 with no fram_target - proves the driver generalizes beyond dev.toml's own
    # i2c1/GPIO6/fram-wired instance.
    isl_call = next(line for line in result.module_source.splitlines() if "ISL29125_Reader(" in line)
    assert "ISL29125_Reader(i2c0, 3, trigger_s=5" in isl_call
    assert "log=log_ram" in isl_call


def test_novel_combo_construction_order_is_topologically_valid(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "secondary")) < order.index(("sgp40", ""))
    assert order.index(("fram", "")) < order.index(("scd30", "primary"))
    assert order.index(("neopixel", "")) < order.index(("notification", ""))


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    # The dedicated multi-instance fixture: two SCD30s and two SGP40s on separate buses, one
    # SGP40 wired to a real SCD30 and the other mixing a cross-driver reference with an explicit
    # default - proving the "any producer exposing a matching attribute name" claim directly.
    result = generate_device(fixtures_dir / "multi_instance.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_a" in result.module_source
    assert "scd30_b" in result.module_source
    assert "sgp40_a" in result.module_source
    assert "sgp40_b" in result.module_source
    assert "temperature=ValueRef(scd30_b, 'Temp')" in result.module_source
    assert "humidity=ValueRef(scd30_b, 'Hum')" in result.module_source
    assert "temperature=ValueRef(bmp3xx_only, 'Temp')" in result.module_source
    assert "humidity=ValueRef(_DefaultHumiditySource(relative_humidity=35), 'value')" in result.module_source
    assert "_DefaultSignalSink().request_signal" in result.module_source
    # led_target/fram_target both left unwired - conn gets no LED, sysfunct no storage, both RAM logs.
    assert "ext_led=None" in result.module_source
    assert "SystemService(ntp.ntp_issynced, watchdog=watchdog, storage=None, level_setters=_collect_level_setters, cfg_path=cfg_path, log=log_ram)" in result.module_source
    # Only sgp40_a is monitored via warn_voc - exactly one NotificationSignal is passed
    # (warn_co2/warn_hum are absent from this fixture entirely, and sgp40_b is never a warn_* source).
    assert result.module_source.count("NotificationSignal(") == 1
    assert "signals=(NotificationSignal('WarnVOC', ValueRef(sgp40_a, 'VOC'), _FIELD_WARN_VOC, (0, 1, 0)),)" in result.module_source
    # Two scd30 instances and two sgp40 instances share one module each - one import line per
    # module, not one per instance, merging whichever _Default* extras either instance needs.
    assert result.module_source.count("from asy_scd30_driver import") == 1
    assert result.module_source.count("from asy_sgp40_driver import") == 1
    assert "from asy_sgp40_driver import SGP40_Reader, _DefaultHumiditySource" in result.module_source


def test_multi_instance_same_module_merges_distinct_default_extras(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # codegen's per-module import dedup unions whichever _Default* extras any instance needs.
    # Here the two sgp40 instances default DIFFERENT fields, so the merged import line must
    # carry both even though neither instance alone needs both.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 19, "sda_pin": 18, "frequency": 50000, "timeout": 200000}
    sgp40 = next(i for i in doc["instance"] if i["driver"] == "sgp40")
    sgp40["name_ext"] = "a"
    sgp40["wiring"]["humidity_source"] = {"default": True, "relative_humidity": 35}
    doc["instance"].append(
        {
            "driver": "sgp40",
            "name_ext": "b",
            "bus": "i2c1",
            "wiring": {
                "temperature_source": {"default": True, "temperature": 20},
                "humidity_source": {"source": "scd30", "field": "Hum"},
            },
        },
    )
    result = generate_device(write_doc(tmp_path, "merge_extras", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert result.module_source.count("from asy_sgp40_driver import") == 1
    import_line = next(line for line in result.module_source.splitlines() if line.startswith("from asy_sgp40_driver import"))
    assert "_DefaultHumiditySource" in import_line
    assert "_DefaultTemperatureSource" in import_line


def test_device_level_fram_target_wires_fram_into_conn_ntp_sysfunct_and_webserver(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # CLAUDE.md's implicit-FRAM-wiring rule (WP1/Topic 2): every mandatory-infra module inherits the
    # device's own FRAM chip, exactly like every FRAM-wirable [[instance]] already can - base_doc()
    # already declares [device.wiring].fram_target = "fram", so this is the happy path.
    doc = base_doc()
    result = generate_device(write_doc(tmp_path, "device_fram_present", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    conn_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("conn = WifiService("))
    ntp_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("ntp = NTPClient("))
    sysfunct_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("sysfunct = SystemService("))
    assert "log=log_fram" in conn_line
    assert "log=log_fram" in ntp_line
    assert "log=log_fram" in sysfunct_line
    assert "storage=fram" in sysfunct_line
    assert "log=log_fram," in result.module_source.split("webserver = WebserverService(")[1].split("\n    )\n")[0]
    # fram must actually be constructed before all three consume it - a real NameError on device,
    # not just a codegen-shape check.
    fram_pos = result.module_source.index("fram = FRAMManager(")
    assert fram_pos < result.module_source.index(conn_line)
    assert fram_pos < result.module_source.index(ntp_line)
    assert fram_pos < result.module_source.index(sysfunct_line)


def test_neither_ntp_nor_notification_is_handed_a_give_up_streak(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Regression (C.7.2): both constructors dropped max_module_error, so emitting it again would be a
    # TypeError at boot on every device - caught here rather than by a bench flash.
    source = generate_device(write_doc(tmp_path, "no_streak", base_doc()), src_dir, ext_dir).module_source
    calls = [line for line in source.splitlines() if "NTPClient(" in line or "NotificationService(" in line]
    assert len(calls) == 2, calls
    assert all("max_module_error" not in line for line in calls), calls


def test_ntp_timing_carries_the_effective_backoff_pair(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    def ntp_line(doc: "dict[str, object]", name: str) -> str:
        source = generate_device(write_doc(tmp_path, name, doc), src_dir, ext_dir).module_source
        ast.parse(source)
        return next(line for line in source.splitlines() if line.strip().startswith("ntp = NTPClient("))

    doc = base_doc()
    unstated = ntp_line(doc, "ntp_backoff_unstated")
    # Unstated, the src/ defaults (_DEFAULT_RETRY_S/_DEFAULT_RETRY_MAX_S) are passed as literals.
    assert "NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _NTP_FETCH_TIMEOUT_MS, 10, 600)" in unstated
    assert "max_module_error" not in unstated  # NTP keeps no give-up streak (Part C.7.2)
    doc["device"]["ntp_retry_s"] = 30
    doc["device"]["ntp_retry_max_s"] = 900
    assert "NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _NTP_FETCH_TIMEOUT_MS, 30, 900)" in ntp_line(doc, "ntp_backoff_stated")


def test_device_with_no_fram_target_leaves_conn_ntp_sysfunct_and_webserver_ram_only(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Regression/fallback path: a device that never wires [device.wiring].fram_target at all (or
    # has no fram instance) must build byte-for-byte as it always has - no fram= kwarg anywhere on
    # the mandatory-infra constructors, and no forced construction-order dependency on fram either.
    doc = base_doc()
    del doc["device"]["wiring"]["fram_target"]
    del doc["device"]["wiring"]["led_target"]  # its FRAM-logged NeoPixel would rightly precede conn
    result = generate_device(write_doc(tmp_path, "device_fram_absent", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    conn_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("conn = WifiService("))
    ntp_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("ntp = NTPClient("))
    sysfunct_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("sysfunct = SystemService("))
    assert "log=log_ram" in conn_line
    assert "log=log_ram" in ntp_line
    assert "log=log_ram" in sysfunct_line
    assert "storage=None" in sysfunct_line
    webserver_call = result.module_source.split("webserver = WebserverService(")[1].split("\n    )\n")[0]
    assert "log=log_ram," in webserver_call
    # conn is still built first among mandatory infra - nothing forces fram ahead of it when there's
    # no device-level fram_target to justify that dependency.
    order = [n if isinstance(n, str) else f"{n[0]}_{n[1]}" if n[1] else n[0] for n in result.model.construction_order]
    assert order.index("conn") < order.index("fram")


def test_multi_instance_same_module_dedupes_identical_default_extra(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # The same mechanism's opposite corner: both sgp40 instances default the SAME field, with
    # different constants. default_class_name() maps the field name alone, so the import line
    # must list the class once rather than twice.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 19, "sda_pin": 18, "frequency": 50000, "timeout": 200000}
    sgp40 = next(i for i in doc["instance"] if i["driver"] == "sgp40")
    sgp40["name_ext"] = "a"
    sgp40["wiring"]["humidity_source"] = {"default": True, "relative_humidity": 35}
    doc["instance"].append(
        {
            "driver": "sgp40",
            "name_ext": "b",
            "bus": "i2c1",
            "wiring": {
                "temperature_source": {"source": "scd30", "field": "Temp"},
                "humidity_source": {"default": True, "relative_humidity": 45},
            },
        },
    )
    result = generate_device(write_doc(tmp_path, "dedupe_extras", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert result.module_source.count("from asy_sgp40_driver import") == 1
    import_line = next(line for line in result.module_source.splitlines() if line.startswith("from asy_sgp40_driver import"))
    assert import_line.count("_DefaultHumiditySource") == 1


def test_device_without_notification_or_neopixel_omits_their_wiring(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] not in ("neopixel", "notification")]
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "minimal", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "notification_led=None" in result.module_source
    assert "notification_pause=None" in result.module_source
    assert '"notification":' not in result.module_source.split("status_sources=")[1].split("\n")[0] if "status_sources=" in result.module_source else True


def test_wiring_defaults_generate_inline_provider_construction(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # SPECIFICATION.md Part L.6.2's generated-code shape: the provider is constructed inline, at the exact
    # call-site the real wiring expression would occupy, with no separate named global.
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = {"default": True}
    doc["instance"][1]["wiring"]["temperature_source"] = {"default": True, "temperature": 20}
    result = generate_device(write_doc(tmp_path, "with_defaults", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "_DefaultSignalSink().request_signal" in result.module_source
    # Every defaulted per-value field always resolves to (provider, "value") - the fixed contract
    # every _Default<Field> class's get_data() follows - not the real field name.
    assert "temperature=ValueRef(_DefaultTemperatureSource(temperature=20), 'value')" in result.module_source
    # humidity_source stays a real reference - not defaulted in this fixture.
    assert "humidity=ValueRef(scd30, 'Hum')" in result.module_source


def test_device_level_led_target_unwired_passes_no_led(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # test_device_wiring_optional_field_absent_is_fine (test_buildgen_validate.py) already
    # confirms validate.py accepts neopixel-present-but-led_target-unwired; the generated conn
    # line then passes ext_led=None.
    doc = base_doc()
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "no_led_target", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    conn_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("conn = WifiService("))
    assert "ext_led=None" in conn_line


def test_a_device_with_led_target_builds_the_neopixel_first_and_passes_it_to_conn(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(write_doc(tmp_path, "led_target", base_doc()), src_dir, ext_dir)
    source = result.module_source
    conn_line = next(line for line in source.splitlines() if line.strip().startswith("conn = WifiService("))
    assert "ext_led=neopixel" in conn_line
    assert source.index("neopixel = NeopixelDriver(") < source.index(conn_line)
    assert "set_ext_led" not in source


def test_every_constructor_logs_through_its_fram_targets_log_config(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # One LogConfig per FRAM store, built right after it; the FRAM manager itself gets the FRAM-less
    # one, and so does any module with no fram_target (here: the notification).
    doc = base_doc()
    del doc["instance"][4]["wiring"]["fram_target"]
    source = generate_device(write_doc(tmp_path, "log_configs", doc), src_dir, ext_dir).module_source
    lines = [line.strip() for line in source.splitlines()]
    assert "log_ram = LogConfig(None, DEFAULT_LOG.history_length, debug)" in lines
    fram_line, after = next((line, nxt) for line, nxt in pairwise(lines) if line.startswith("fram = FRAMManager("))
    assert fram_line == "fram = FRAMManager(spi0, 1, max_size=0x2000, log=log_ram)"
    assert after == "log_fram = LogConfig(fram, DEFAULT_LOG.history_length, debug)"
    calls = {line.split(" = ")[0]: line for line in lines if re.match(r"\w+ = [A-Z]\w*\(", line) and not line.startswith(("log_", "watchdog", "app"))}
    for var in ("scd30", "sgp40", "neopixel", "conn", "ntp", "sysfunct"):
        assert "log=log_fram" in calls[var], calls[var]
    assert "log=log_ram" in calls["notification"]
    assert "debug=debug" not in source.split("async def build_system(")[1].split("async def main(")[0].split(") -> None:")[1]
    assert "fram=" not in source


def test_device_without_sgp40_omits_maintenance_sensors(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "sgp40"]
    del doc["instance"][0]["wiring"]  # scd30's own optional fram_target - unrelated to sgp40's removal
    result = generate_device(write_doc(tmp_path, "nosgp40", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "maintenance_sensors=()," in result.module_source


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


def test_cli_prints_module_source_without_out_dir(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from buildgen.generate import main

    exit_code = main([str(repo_root / "devices" / "wozi.toml")])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "async def build_system(" in captured.out


def test_cli_reports_build_error_on_stderr_and_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from buildgen.generate import main

    doc = base_doc()
    del doc["device"]["hotspot_time_min"]
    path = write_doc(tmp_path, "broken_device", doc)
    exit_code = main([str(path), "--src-dir", str(Path(__file__).resolve().parent.parent / "src")])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "hotspot_time_min" in captured.err


def test_hostname_and_hotspot_password_are_wired_into_generated_code(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # The inverse of the tripwire this replaces: hostname and hotspot_password were validated
    # and then reached nothing, so every device booted as the shared "SensorNode". They are
    # passed to WifiService now, as the two persisted fields' per-device defaults.
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "WifiConfig('SensorStationWozi', '12345678', " in result.module_source
    ast.parse(result.module_source)


def test_bmp3xx_trigger_s_is_rendered_into_the_constructor_call(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # trigger_s is declared only on scd30 in every real device and fixture, so bmp3xx's own
    # trigger_s rendering had never been exercised - despite Phase 3 giving bmp3xx a
    # `@limits trigger_s 1..3600` domain specifically. Found by an error-path coverage sweep.
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": 0x77, "trigger_s": 42, "wiring": {"fram_target": "fram"}})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    assert "trigger_s=42" in result.module_source
    ast.parse(result.module_source)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_constructs_scd30_with_the_boot_config_path(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # SCD30 keeps its three FRC readiness settings in a config file, so it is built like the other config readers.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    calls = [line for line in result.module_source.splitlines() if "SCD30_Reader(" in line]
    assert calls, f"{device} constructs no SCD30_Reader - the check holds nothing"
    for call in calls:
        assert ", cfg_path=cfg_path, log=" in call, call


def test_isl29125_irq_pin_and_trigger_s_are_rendered_into_the_constructor_call(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # irq_pin is a required positional arg (like scd30's own shape); trigger_s is optional (like
    # bmp3xx's own shape) - ISL29125_Reader is the one driver combining both.
    doc = base_doc()
    doc["instance"].append({"driver": "isl29125", "bus": "i2c0", "irq_pin": 6, "trigger_s": 5, "wiring": {"fram_target": "fram"}})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    assert "ISL29125_Reader(i2c0, 6, trigger_s=5" in result.module_source
    call = next(line for line in result.module_source.splitlines() if "ISL29125_Reader(" in line)
    assert "log=log_fram" in call
    ast.parse(result.module_source)


def test_isl29125_without_trigger_s_or_fram_target_omits_both(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Both are optional - a device wiring neither must still generate a valid, minimal call.
    doc = base_doc()
    doc["instance"].append({"driver": "isl29125", "bus": "i2c0", "irq_pin": 6})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    call = next(line for line in result.module_source.splitlines() if "ISL29125_Reader(" in line)
    assert "trigger_s" not in call
    assert "log=log_ram" in call
    assert "irq_pull_up" not in call
    ast.parse(result.module_source)


def test_isl29125_irq_pull_up_false_is_rendered_into_the_constructor_call(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # A board with its own external pull-up resistor (the real dev bench) sets this - the driver's
    # own default (omitted here) is True, the internal pull-up, for a board with no resistor of
    # its own.
    doc = base_doc()
    doc["instance"].append({"driver": "isl29125", "bus": "i2c0", "irq_pin": 6, "irq_pull_up": False})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    assert "irq_pull_up=False" in result.module_source
    ast.parse(result.module_source)


def test_unknown_warn_signal_is_a_fail_loud_build_error(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # The generator owns a fixed catalog of notification signals; a warn_* key outside it must
    # abort and name the catalog, never be silently dropped from the generated module.
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_bogus"] = {"source": "scd30", "field": "CO2"}
    with pytest.raises(BuildError, match="built-in signal catalog"):
        generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)


def test_identifier_rejects_a_name_python_could_not_use(src_dir: Path) -> None:
    # No real bus id or instance label can reach this today (both are drawn from closed sets), so
    # it is driven directly - it is the one guard standing between a bad name and generated source
    # that would not parse.
    from buildgen.codegen import _identifier

    for bad in ("class", "not-an-identifier", "9leading_digit", ""):
        with pytest.raises(BuildError, match="not usable as a generated Python identifier"):
            _identifier(bad, "dev")
    assert _identifier("i2c0", "dev") == "i2c0"


def test_codegen_has_no_build_recipe_for_an_unknown_driver(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # driver_registry can resolve a driver that codegen has no constructor recipe for - the build
    # must say exactly that, and name where to add one.
    from buildgen.codegen import _build_call, _Ctx
    from buildgen.validate import build_model

    # Driven at the _build_call() level: an instance of such a driver can't be carried through a
    # whole build, because _check_required_fields() rejects a driver with no buildspec.py entry
    # long before codegen sees it (the onboarding-gap check added in Phase 4).
    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    spec = model.instances[("scd30", "")]
    spec.driver = "not_a_real_driver"
    with pytest.raises(BuildError, match="no build recipe for driver"):
        _build_call(spec, _Ctx(model))


def test_notification_with_no_signal_sink_wiring_field_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _build_args_notification()'s internal invariant: signal_sink is always resolved by
    # validate.py before codegen runs, so no real TOML reaches this. Driven by mutating an
    # already-validated spec, the same way the unknown-driver test above reaches its branch.
    from buildgen.codegen import _build_args_notification, _Ctx
    from buildgen.validate import build_model

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    spec = model.instances[("notification", "")]
    spec.wiring_schema = tuple(wf for wf in spec.wiring_schema if wf.toml_field != "signal_sink")
    with pytest.raises(BuildError, match="no signal_sink wiring field by codegen time"):
        _build_args_notification(spec, _Ctx(model))


def test_instance_with_no_driver_info_fails_loud_at_codegen_time(tmp_path: Path, src_dir: Path) -> None:
    # _emit_header_and_imports()'s internal invariant: driver_info is always resolved before
    # codegen runs. Driven through generate_module_source(), the same seam generate_device()
    # uses, on a valid model with one instance's driver_info cleared afterwards.
    from buildgen.codegen import generate_module_source
    from buildgen.graph import build_construction_order
    from buildgen.validate import build_model

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    build_construction_order(model)
    model.instances[("scd30", "")].driver_info = None
    with pytest.raises(BuildError, match="driver_info unresolved by codegen time"):
        generate_module_source(model, model.construction_order, "2026-01-01T00:00:00Z", src_dir)


def test_construction_order_entry_that_is_neither_a_bare_node_nor_an_instance_key_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _emit_build_system()'s internal invariant: build_construction_order() only emits the three
    # infra names or a real instance key, so no TOML reaches this. Driven by inserting a bogus
    # bare string into an already-computed construction order.
    from buildgen.codegen import generate_module_source
    from buildgen.graph import build_construction_order
    from buildgen.validate import build_model

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    build_construction_order(model)
    mutated_order = [*model.construction_order, "bogus_node"]
    with pytest.raises(BuildError, match="is not a known bare node or an instance key"):
        generate_module_source(model, mutated_order, "2026-01-01T00:00:00Z", src_dir)


def test_cli_entry_point_writes_both_files_and_exits_zero(tmp_path: Path, repo_root: Path) -> None:
    # The one real entry point a person invokes by hand. Run as a subprocess so the __main__ guard
    # and the process exit code are both genuinely exercised, not just main()'s return value.
    import subprocess
    import sys

    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "-m", "buildgen.generate", str(repo_root / "devices" / "wozi.toml"), "--out-dir", str(out)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (out / "sensortask_wozi.py").is_file()
    assert (out / "wozi_boot.py").is_file()
    ast.parse((out / "sensortask_wozi.py").read_text())


def test_cli_entry_point_reports_a_build_error_and_exits_nonzero(tmp_path: Path, repo_root: Path) -> None:
    import subprocess
    import sys

    bad = write_doc(tmp_path, "dev", {"device": {"name": "Test"}})
    result = subprocess.run(
        [sys.executable, "-m", "buildgen.generate", str(bad)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "buildgen:" in result.stderr  # a human-readable reason, never a raw traceback
    assert "Traceback" not in result.stderr


def _webserver_keywords(source: str) -> dict[str, object]:
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ServingLimits"]
    assert len(calls) == 1, len(calls)
    return {kw.arg: ast.literal_eval(kw.value) for kw in calls[0].keywords if kw.arg in ("max_connections", "backlog")}


@pytest.mark.parametrize(
    ("stated", "expected"),
    [
        ({"max_connections": 3, "backlog": 4}, {"max_connections": 3, "backlog": 4}),
        ({"max_connections": 5}, {"max_connections": 5, "backlog": None}),
        ({}, {"max_connections": 6, "backlog": None}),  # asy_webserver_service._DEFAULT_MAX_CONNECTIONS
    ],
)
def test_the_stated_connection_ceiling_reaches_the_webserver_and_an_absent_one_is_its_src_default(tmp_path: Path, src_dir: Path, ext_dir: Path, stated: dict[str, int], expected: dict[str, int]) -> None:
    # validate.py checks the stated values against the firmware's lwIP pools; that check is only
    # worth anything if the same values are the ones the device is then built with.
    doc = base_doc()
    for key in ("max_connections", "backlog"):
        doc["device"].pop(key, None)
    doc["device"].update(stated)
    result = generate_device(write_doc(tmp_path, "ceiling", doc), src_dir, ext_dir)
    assert _webserver_keywords(result.module_source) == expected
