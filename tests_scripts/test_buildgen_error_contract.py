"""Every build-error rule proven through a CLI (SPECIFICATION.md Part L.5): one malformed-fixture row per
`rule` id exits 1 with one line naming place and fix and no traceback, the rows cover every `rule=` literal
under buildgen/, and a generator bug propagates as BuildInternalError with its traceback."""

import ast
import errno
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
import tomllib
from _script_loader import load_script_module
from _toml_fixtures import TomlDoc, base_doc, dump_toml, write_doc

from buildgen import api_reference, buildspec, codegen, definitions, generate, model, validate
from buildgen.codegen import generate_boot_entry_source, generate_module_source
from buildgen.errors import BuildError, BuildInternalError
from buildgen.requires_tag import check_requires_tags, parse_requires_tags

if TYPE_CHECKING:
    from collections.abc import Callable

_REPO = Path(__file__).resolve().parent.parent
_DEVICE = "contract"
_PREFIX = {"generate": "buildgen: ", "definitions": "buildgen: ", "batch": "error: ", "direct": ""}
_SCD30 = "asy_scd30_driver.py"
_SCD30_TRIGGER_LIMITS = "# @limits trigger_s 1..1800"
_SCD30_TIMEOUT_TAG = "# @requires bus.timeout>=200000"
_AMB_PRES_SPECIAL = ' special:0="Compensation off / use Altitude"'
_FIRST_ROUTE = '    ("GET", "/measurements", "_get_measurements"),'


def _api_page_only_without_description(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # A definitions key the reference no longer classifies: the only way a new key reaches that check.
    monkeypatch.setattr(api_reference, "_PAGE_ONLY", api_reference._PAGE_ONLY - {"description"})


def _compare_a_string_timeout(_tmp: Path) -> None:
    # No CLI reaches this check: validate.py types every bus field it knows before any @requires tag is compared.
    tags = parse_requires_tags(_REPO / "src" / _SCD30, _DEVICE, "scd30")
    check_requires_tags(tags, {"timeout": "200000"}, _DEVICE, "scd30", "i2c0")


def _doc_bus_timeout(value: object) -> "Callable[[TomlDoc], None]":
    def edit(doc: TomlDoc) -> None:
        if value is None:
            del doc["bus"]["i2c0"]["timeout"]
        else:
            doc["bus"]["i2c0"]["timeout"] = value

    return edit


def _doc_extra_instance(instance: TomlDoc) -> "Callable[[TomlDoc], None]":
    def edit(doc: TomlDoc) -> None:
        doc["instance"].append(instance)

    return edit


def _doc_instance_field(driver: str, key: str, value: object) -> "Callable[[TomlDoc], None]":
    def edit(doc: TomlDoc) -> None:
        next(i for i in doc["instance"] if i["driver"] == driver)[key] = value

    return edit


def _doc_unchanged(_doc: TomlDoc) -> None:
    return


def _drop(*path: str) -> "Callable[[TomlDoc], None]":
    def edit(doc: TomlDoc) -> None:
        table = doc
        for key in path[:-1]:
            table = _instance(doc, key[1:]) if key.startswith("@") else table[key]
        del table[path[-1]]

    return edit


def _i2c0_renamed_i2c7(doc: TomlDoc) -> None:
    doc["bus"]["i2c7"] = doc["bus"].pop("i2c0")
    for instance in doc["instance"]:
        if instance.get("bus") == "i2c0":
            instance["bus"] = "i2c7"


def _instance(doc: TomlDoc, driver: str) -> TomlDoc:
    found: TomlDoc = next(i for i in doc["instance"] if i["driver"] == driver)
    return found


def _paired(*edits: "Callable[[TomlDoc], None]") -> "Callable[[TomlDoc], None]":
    # base_doc() plus a UART crossover pair on uart0/uart1 (scd30's IRQ moved off GP8, one of uart1's pins), then the edits.
    def edit(doc: TomlDoc) -> None:
        _instance(doc, "scd30")["irq_pin"] = 6
        knobs = {"baudrate": 115200, "rxbuf": 512, "txbuf": 512, "poll_wait_ms": 2, "poll_idle_ms": 50}
        doc["bus"]["uart0"] = {"tx_pin": 16, "rx_pin": 17, **knobs}
        doc["bus"]["uart1"] = {"tx_pin": 8, "rx_pin": 9, **knobs}
        doc["instance"] += [{"driver": "uart_link", "name_ext": "init", "bus": "uart0", "role": "initiator"}, {"driver": "uart_link", "name_ext": "resp", "bus": "uart1", "role": "responder"}]
        for further in edits:
            further(doc)

    return edit


def _set(*path_and_value: object) -> "Callable[[TomlDoc], None]":
    # _set("bus", "i2c0", "timeout", 0); a key "@scd30" steps into that driver's [[instance]].
    *path, value = path_and_value

    def edit(doc: TomlDoc) -> None:
        table = doc
        for key in path[:-1]:
            assert isinstance(key, str)
            table = _instance(doc, key[1:]) if key.startswith("@") else table.setdefault(key, {})
        table[str(path[-1])] = value

    return edit


def _then(*edits: "Callable[[TomlDoc], None]") -> "Callable[[TomlDoc], None]":
    def edit(doc: TomlDoc) -> None:
        for each in edits:
            each(doc)

    return edit


def _foo_drivers_whose_labels_collide(monkeypatch: pytest.MonkeyPatch, tmp: Path) -> None:
    # Drivers "foo_bar" and "foo" with name_ext "bar" both render the generated name foo_bar; no shipped driver
    # name carries an underscore, so the two drivers are planted in the src/ copy and given buildspec rows.
    for driver, name in (("foo_bar", "FOOBAR"), ("foo", "FOO")):
        _write_own(tmp / "src" / f"asy_{driver}_driver.py", f'from asy_base_classes import SensorReader\n\n_NAME = "{name}"\n\n\nclass Reader(SensorReader):\n    pass\n')
        monkeypatch.setitem(buildspec.REQUIRED_TOML_FIELDS, driver, ())
        monkeypatch.setitem(buildspec.ALLOWED_INSTANCE_FIELDS, driver, frozenset())


def _gain_allowed_on_scd30(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # A float limit needs a float field, which no shipped driver declares: scd30 gains a synthetic one here.
    monkeypatch.setitem(buildspec.ALLOWED_INSTANCE_FIELDS, "scd30", buildspec.ALLOWED_INSTANCE_FIELDS["scd30"] | {"gain"})


def _no_bus_kind_row_for_scd30(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # A table patch: every shipped bus-attached driver has its row, so no TOML reaches the check.
    monkeypatch.delitem(buildspec.BUS_KIND_BY_DRIVER, "scd30")


def _overrides_unloadable(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # A toolchain patch: toolchain/micropython_overrides.py cannot be removed from under the test.
    monkeypatch.setattr("buildgen.validate.importlib", SimpleNamespace(util=SimpleNamespace(spec_from_file_location=lambda *_a, **_k: None)))


def _settings_key_served_twice(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # A table patch: SETTINGS_GROUPS serves Hostname a second time, from the NTP group.
    monkeypatch.setattr(validate, "SETTINGS_GROUPS", (*validate.SETTINGS_GROUPS, ("networking", "ntp", ("Hostname",), None)))


def _signal_sink_default_without_request_signal(_monkeypatch: pytest.MonkeyPatch, tmp: Path) -> None:
    path = tmp / "src" / "asy_notification_service.py"
    text = path.read_text(encoding="utf-8")
    block = re.search(r"class _DefaultSignalSink.*?(?=\nclass |\Z)", text, re.DOTALL)
    assert block, "asy_notification_service.py no longer has _DefaultSignalSink - the row's edit has to follow"
    _write_own(path, text.replace(block.group(0), block.group(0).replace("request_signal", "request_signal_gone")))


def _lwip_table_gone(monkeypatch: pytest.MonkeyPatch, tmp: Path) -> None:
    # The toolchain's [lwip] table is read from toolchain/versions.toml; this row points that read at a copy without it.
    versions = tmp / "versions.toml"
    versions.write_text('[toolchain]\nboard = "RPI_PICO_W"\n')
    real = model.lwip_macros
    monkeypatch.setattr(validate, "lwip_macros", lambda: real(versions))


def _no_patch(_monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    return


def _out_dir_is_a_file(_monkeypatch: pytest.MonkeyPatch, tmp: Path) -> None:
    (tmp / "out").write_text("a file where the output directory belongs\n")


def _recipe_table_without_neopixel(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # Reachable only past every buildspec check: the recipe table loses one declared driver for this run.
    monkeypatch.delitem(codegen._BUILD_ARGS_HANDLERS, "neopixel")


def _toml_parses_to_a_list(monkeypatch: pytest.MonkeyPatch, _tmp: Path) -> None:
    # tomllib always returns a table for a file, so a non-table top level is planted at the parser.
    monkeypatch.setattr(model, "tomllib", SimpleNamespace(load=lambda _f: [], TOMLDecodeError=tomllib.TOMLDecodeError))


@dataclass(frozen=True)
class Row:
    # One malformed input: the CLI that reaches the rule first, the place its one stderr line starts with,
    # the device TOML (base_doc() edited, raw text or absent), edits to a copy of src/ (every occurrence), a monkeypatch.
    entry: str
    place: str
    doc: "Callable[[TomlDoc], None]" = _doc_unchanged
    toml: str | None = None
    absent: bool = False
    edits: "tuple[tuple[str, str, str], ...]" = ()
    subs: "tuple[tuple[str, str, str], ...]" = ()
    drop: "tuple[str, ...]" = ()
    copy_src: bool = False
    call: "Callable[[Path], None] | None" = None  # the "direct" entry: a function no CLI reaches, called as is
    patch: "Callable[[pytest.MonkeyPatch, Path], None]" = _no_patch
    extra: "tuple[str, ...]" = ()


def _tag_row(old: str, new: str, where: str = "/scd30") -> Row:
    # A plant in one scd30 tag comment; `where` is the place after the device, e.g. "/scd30.trigger_s".
    return Row("generate", f"[{_DEVICE}{where}] ", edits=((_SCD30, old, new),))


def _web_row(new: str, old: str = '# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s"', where: str = "/scd30.MeasInterval") -> Row:
    # A plant in one scd30 @web tag, read by the website definitions build.
    return Row("definitions", f"[{_DEVICE}{where}] ", edits=((_SCD30, old, new),))


_X_DRIVER = 'from asy_base_classes import SensorReader\n\n_NAME = "X"\n'

# rule id -> its row; each row names the entry it runs through.
_ROWS: "dict[str, Row]" = {
    # buildgen/generate.py and buildgen/twin_wiring.py
    "cli.out-dir-unwritable": Row("generate", f"[{_DEVICE}] cannot write ", patch=_out_dir_is_a_file, extra=("--out-dir", "{tmp}/out")),
    "twin.no-address-rule": Row("batch", f"[{_DEVICE}/scd30] ", edits=((_SCD30, "_SCD30_ADDR = const(", "_SCD30_ADDRESS = const("),)),
    # buildgen/codegen.py
    "driver.no-build-recipe": Row("generate", f"[{_DEVICE}/neopixel] ", patch=_recipe_table_without_neopixel),
    "names.not-an-identifier": Row("generate", f"[{_DEVICE}/sgp40_a-b.name_ext] ", doc=_doc_instance_field("sgp40", "name_ext", "a-b")),
    # buildgen/model.py
    "toml.syntax": Row("generate", f"[{_DEVICE}] ", toml="x = [\n"),
    "toml.unreadable": Row("generate", f"[{_DEVICE}] ", absent=True),
    "toml.not-a-table": Row("generate", f"[{_DEVICE}] ", patch=_toml_parses_to_a_list),
    "instance.single-table": Row("generate", f"[{_DEVICE}] ", toml='[instance]\ndriver = "scd30"\n'),
    "instance.not-an-array": Row("generate", f"[{_DEVICE}] ", toml="instance = 5\n"),
    "instance.driver-missing": Row("generate", f"[{_DEVICE}] ", toml='[[instance]]\nbus = "i2c0"\n'),
    "instance.driver-not-a-string": Row("generate", f"[{_DEVICE}] ", toml="[[instance]]\ndriver = 3\n"),
    "instance.name-ext-not-a-string": Row("generate", f"[{_DEVICE}/scd30] ", toml='[[instance]]\ndriver = "scd30"\nname_ext = 1\n'),
    "instance.wiring-not-table": Row("generate", f"[{_DEVICE}/neopixel.wiring] ", doc=_doc_instance_field("neopixel", "wiring", "fram")),
    "instance.duplicate": Row("generate", f"[{_DEVICE}/scd30] ", toml='[[instance]]\ndriver = "scd30"\n\n[[instance]]\ndriver = "scd30"\n'),
    "toolchain.lwip-table": Row("generate", "[<toolchain>.max_connections] ", patch=_lwip_table_gone),
    # buildgen/driver_registry.py and buildgen/graph.py
    "driver.unknown": Row("generate", f"[{_DEVICE}/nonexistent_chip] ", doc=_doc_extra_instance({"driver": "nonexistent_chip"})),
    "driver.module-missing": Row("generate", f"[{_DEVICE}/fram] ", drop=("asy_fram_manager.py",)),
    "driver.no-reader-class": Row("generate", f"[{_DEVICE}/x] ", doc=_doc_extra_instance({"driver": "x"}), edits=(("asy_x_driver.py", "", _X_DRIVER + "\n\nclass X:\n    pass\n"),)),
    "driver.ambiguous-reader-class": Row(
        "generate", f"[{_DEVICE}/x] ", doc=_doc_extra_instance({"driver": "x"}), edits=(("asy_x_driver.py", "", _X_DRIVER + "\n\nclass X(SensorReader):\n    pass\n\n\nclass Y(SensorReader):\n    pass\n"),),
    ),
    "source.syntax-error": Row("generate", f"[{_DEVICE}/scd30] ", edits=((_SCD30, "", "\nclass Broken(:\n"),)),
    "source.name-missing": Row("generate", f"[{_DEVICE}/scd30] ", edits=((_SCD30, '_NAME = const("SCD30")', '_NAME_GONE = const("SCD30")'),)),
    "source.name-not-literal": Row("generate", f"[{_DEVICE}/scd30] ", edits=((_SCD30, '_NAME = const("SCD30")', "_NAME = const(42)"),)),
    # sgp40's temperature_source names scd30's Temp, but scd30's get_data() no longer declares a namedtuple result.
    "source.fields-unreadable": Row("generate", f"[{_DEVICE}/scd30] ", edits=((_SCD30, "async def get_data(self) -> SCD30:", "async def get_data(self) -> tuple:"),)),
    "wiring.cycle": Row(
        "generate", f"[{_DEVICE}] ",
        doc=lambda d: next(i for i in d["instance"] if i["driver"] == "scd30")["wiring"].update({"fake_dep": "sgp40"}),
        edits=((_SCD30, _SCD30_TRIGGER_LIMITS, _SCD30_TRIGGER_LIMITS + "\n# @wiring fake_dep SGP40_Reader fake_dep required kwarg"),),
    ),
    # buildgen/tag_comments.py, limits.py, requires_tag.py, wiring.py, value_wiring.py, web_tag.py
    "tag.malformed": _tag_row(_SCD30_TIMEOUT_TAG, "# @requires timeout>=200000"),
    "tag.missing-sigil": _tag_row(_SCD30_TIMEOUT_TAG, "# requires bus.timeout>=200000"),
    "tag.misspelled": _tag_row(_SCD30_TIMEOUT_TAG, "# @require bus.timeout>=200000"),
    "tag.not-module-level": _tag_row("    async def get_data(self) -> SCD30:\n", "    async def get_data(self) -> SCD30:\n        # @limits trigger_s 1..1800\n"),
    "tag.duplicate-field": _tag_row(_SCD30_TRIGGER_LIMITS, _SCD30_TRIGGER_LIMITS + "\n" + _SCD30_TRIGGER_LIMITS, where="/scd30.trigger_s"),
    "tag.not-a-number": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s x..1800"),
    "tag.non-finite-number": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s 1..inf"),
    "limits.empty-choice-set": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s in {}", where="/scd30.trigger_s"),
    "limits.choice-not-int": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s in {1.5}", where="/scd30.trigger_s"),
    "limits.payload-shape": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s in {3", where="/scd30.trigger_s"),
    "limits.missing-bound": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s 1..", where="/scd30.trigger_s"),
    "limits.checks-nothing": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s *..*", where="/scd30.trigger_s"),
    "limits.inverted-range": _tag_row(_SCD30_TRIGGER_LIMITS, "# @limits trigger_s 1800..1", where="/scd30.trigger_s"),
    "requires.missing-bus-field": Row("generate", f"[{_DEVICE}/scd30.timeout] ", doc=_doc_bus_timeout(None)),
    "requires.not-comparable": Row("direct", f"[{_DEVICE}/scd30.timeout] ", call=_compare_a_string_timeout),
    "requires.unsatisfied": Row("generate", f"[{_DEVICE}/scd30.timeout] ", doc=_doc_bus_timeout(1000)),
    "web.not-a-bool": _web_row('# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s" mask=yes', where="/scd30"),
    "web.path-malformed": _web_row(
        '# @web CO2 section=measurements submitGroup=self kind=readonly label="CO2" unit="ppm" path="RGB."',
        '# @web CO2 section=measurements submitGroup=self kind=readonly label="CO2" unit="ppm"',
        where="/scd30.CO2",
    ),
    "web.decimals-range": _web_row('# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s" decimals=101'),
    "web.key-needs-readonly": _web_row('# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s" format=epoch'),
    "web.key-needs-string": _web_row('# @web MeasInterval section=sensors submitGroup=self kind=number label="Measurement Interval" unit="s" bytes=true'),
    "web.value-not-in-set": _web_row(
        '# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" format=iso',
        '# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" format=epoch',
        where="/scd30.TS",
    ),
    "web.always-executed-and-dispatch": _web_row('# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s" alwaysExecuted=true dispatch=true'),
    "web.unknown-key": _web_row('# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s" bogus=1'),
    "web.missing-key": _web_row('# @web MeasInterval section=sensors submitGroup=self unit="s"'),
    "web.kind-unknown": _web_row('# @web MeasInterval section=sensors submitGroup=self kind=bogus label="Measurement Interval" unit="s"'),
    "web.malformed-pairs": _web_row('# @web MeasInterval section=sensors submitGroup=self label= unit="s"'),
    "web.hidden-not-alone": _web_row('# @web MeasInterval hidden="why" label="L"'),
    "web.hidden-no-reason": _web_row('# @web MeasInterval hidden=""'),
    "web.hidden-and-tagged": _web_row('# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s"\n# @web MeasInterval hidden="why"'),
    "web.duplicate-group": _web_row(
        '# @web-group section=sensors submitGroup=self label="SCD30 — CO2, Temperature, Humidity" submit=true\n# @web-group section=sensors submitGroup=self label="Again" submit=true',
        '# @web-group section=sensors submitGroup=self label="SCD30 — CO2, Temperature, Humidity" submit=true',
        where="/scd30",
    ),
    # buildgen/schema_ast.py and buildgen/definitions.py
    "schema.unreadable": Row("definitions", f"[{_DEVICE}/scd30] ", edits=((_SCD30, "_VAL_TEMP_OFFSET = ", '_VAL_X = const((("X", "int", 1, None, None, _UNDEFINED),))\n_VAL_TEMP_OFFSET = '),)),
    "schema.malformed": Row("definitions", f"[{_DEVICE}/scd30] ", edits=((_SCD30, "_VAL_TEMP_OFFSET = ", '_VAL_X = const((("X", "int", 1, None, None),))\n_VAL_TEMP_OFFSET = '),)),
    "schema.value-not-json": Row("definitions", f"[{_DEVICE}.MeasInterval] ", edits=((_SCD30, '(("MeasInterval", "int", None, 2, 1800, None),)', '(("MeasInterval", "int", None, b"\\x00", 1800, None),)'),)),
    "web.schema-field-untagged": Row("definitions", f"[{_DEVICE}/scd30.AmbPres] ", edits=((_SCD30, "# @web AmbPres section=sensors", "# AmbPres section=sensors"),)),
    "web.special-unlabelled": Row("definitions", f"[{_DEVICE}.AmbPres] ", edits=((_SCD30, _AMB_PRES_SPECIAL, ""),)),
    "web.special-not-in-schema": Row("definitions", f"[{_DEVICE}.PW] ", edits=(("asy_wifi_service.py", 'special:""="Open network"', 'special:""="Open network" special:"guest"="Guest"'),)),
    "web.kind-unresolved": Row("definitions", f"[{_DEVICE}.ContMeas] ", edits=((_SCD30, '_CONT_MEAS_FIELD: "FieldSchema" = ("ContMeas", "bool", None, None, None, None)\n', ""), (_SCD30, " kind=toggle", ""))),
    "web.enum-without-choices": Row("definitions", f"[{_DEVICE}.ContMeas] ", edits=((_SCD30, "kind=toggle", "kind=enum"),)),
    "web.group-undeclared": Row("definitions", f"[{_DEVICE}] ", edits=(("asy_system_service.py", '# @web-group section=system submitGroup=settings label="System Settings" submit=true\n', ""),)),
    "web.group-declared-twice": Row("definitions", f"[{_DEVICE}] ", edits=(("asy_ntp_client.py", "", '\n# @web-group section=system submitGroup=settings label="System Settings" submit=true\n'),)),
    # Every notification field tag turned hidden: the autoConfig group stays declared with no field left in it.
    "web.group-without-fields": Row("definitions", f"[{_DEVICE}] ", subs=(("asy_notification_service.py", r"^# @web (\w+) .*$", r'# @web \1 hidden="test"'),)),
    "web.instance-group-missing": Row("definitions", f"[{_DEVICE}/scd30] ", edits=((_SCD30, '# @web-group section=measurements submitGroup=self label="SCD30 — CO2, Temperature, Humidity"\n', ""),)),
    "web.maintenance-tag-missing": Row("definitions", f"[{_DEVICE}/sgp40] ", edits=(("asy_sgp40_driver.py", "section=status submitGroup=maintenance", "section=status submitGroup=elsewhere"),)),
    "web.codes-unknown-table": Row("definitions", f"[{_DEVICE}.FRCState] ", edits=((_SCD30, "codes=FRCState", "codes=NoSuchTable"),)),
    "web.string-key-off-string": Row(
        "definitions", f"[{_DEVICE}.MeasInterval] ",
        edits=((_SCD30, '# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s"', '# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s" shape=hostLabel'),),
    ),
    "web.quoted-special-off-string": Row("definitions", f"[{_DEVICE}.AmbPres] ", edits=((_SCD30, ' special:0="Compensation', ' special:"0"="Compensation'),)),
    "web.string-special-unquoted": Row("definitions", f"[{_DEVICE}.PW] ", edits=(("asy_wifi_service.py", 'special:""="Open network"', 'special:open="Open network"'),)),
    # buildgen/validate.py: [device]
    "device.table-missing": Row("generate", f"[{_DEVICE}] ", doc=_drop("device")),
    "device.field-missing": Row("generate", f"[{_DEVICE}.hostname] ", doc=_drop("device", "hostname")),
    "device.field-type": Row("generate", f"[{_DEVICE}.name] ", doc=_set("device", "name", 5)),
    "device.wiring-not-table": Row("generate", f"[{_DEVICE}.wiring] ", doc=_set("device", "wiring", "neopixel")),
    "device.field-unknown": Row("generate", f"[{_DEVICE}.colour] ", doc=_set("device", "colour", 1)),
    "device.hotspot-password-length": Row("generate", f"[{_DEVICE}.hotspot_password] ", doc=_set("device", "hotspot_password", "short")),
    "device.hostname-convention": Row("generate", f"[{_DEVICE}.hostname] ", doc=_set("device", "hostname", "SensorStationOther")),
    "device.hostname-label": Row("generate", f"[{_DEVICE}.hostname] ", doc=_then(_set("device", "name", "Te_st"), _set("device", "hostname", "SensorStationTe_st"))),
    "device.hostname-length": Row("generate", f"[{_DEVICE}.hostname] ", doc=_then(_set("device", "name", "T" * 60), _set("device", "hostname", "SensorStation" + "T" * 60))),
    "device.hotspot-time-min-range": Row("generate", f"[{_DEVICE}.hotspot_time_min] ", doc=_set("device", "hotspot_time_min", 35792)),
    "device.conn-fail-to-hotspot-range": Row("generate", f"[{_DEVICE}.conn_fail_to_hotspot] ", doc=_set("device", "conn_fail_to_hotspot", 0)),
    "device.max-connections-range": Row("generate", f"[{_DEVICE}.max_connections] ", doc=_set("device", "max_connections", 0)),
    "device.max-connections-lwip": Row("generate", f"[{_DEVICE}.max_connections] ", doc=_set("device", "max_connections", 64)),
    "device.backlog-below-ceiling": Row("generate", f"[{_DEVICE}.backlog] ", doc=_then(_set("device", "max_connections", 4), _set("device", "backlog", 3))),
    "device.backlog-above-ceiling": Row("generate", f"[{_DEVICE}.backlog] ", doc=_then(_set("device", "max_connections", 4), _set("device", "backlog", 6))),
    "device.ntp-retry-below-tick": Row("generate", f"[{_DEVICE}.ntp_retry_s] ", doc=_set("device", "ntp_retry_s", 1)),
    "device.ntp-retry-max-below-retry": Row("generate", f"[{_DEVICE}.ntp_retry_max_s] ", doc=_then(_set("device", "ntp_retry_s", 120), _set("device", "ntp_retry_max_s", 60))),
    "device.ntp-retry-max-range": Row("generate", f"[{_DEVICE}.ntp_retry_max_s] ", doc=_set("device", "ntp_retry_max_s", 536870912)),
    "device.wiring-field-unknown": Row("generate", f"[{_DEVICE}.bogus_target] ", doc=_set("device", "wiring", "bogus_target", "fram")),
    "device.wiring-no-tag": Row("generate", f"[{_DEVICE}.led_target] ", edits=(("asy_wifi_service.py", "# @wiring led_target NeopixelDriver ext_led optional kwarg", "#"),)),
    "device.wiring-field-missing": Row(
        "generate", f"[{_DEVICE}.led_target] ", doc=_drop("device", "wiring", "led_target"),
        edits=(("asy_wifi_service.py", "# @wiring led_target NeopixelDriver ext_led optional kwarg", "# @wiring led_target NeopixelDriver ext_led required kwarg"),),
    ),
    # buildgen/validate.py: [bus.*]
    "bus.unknown-id": Row("generate", f"[{_DEVICE}.i2c7] ", doc=_i2c0_renamed_i2c7),
    "bus.not-a-table": Row("generate", f"[{_DEVICE}.spi0] ", toml=dump_toml(base_doc()).replace("[bus.spi0]", "[bus]\nspi0 = 5\n[bus.spi0x]", 1)),
    "bus.field-missing": Row("generate", f"[{_DEVICE}.scl_pin] ", doc=_drop("bus", "i2c0", "scl_pin")),
    "bus.field-unknown": Row("generate", f"[{_DEVICE}.speed] ", doc=_set("bus", "i2c0", "speed", 1)),
    "bus.field-type": Row("generate", f"[{_DEVICE}.timeout] ", doc=_set("bus", "i2c0", "timeout", "200ms")),
    "bus.i2c-frequency-range": Row("generate", f"[{_DEVICE}.frequency] ", doc=_set("bus", "i2c0", "frequency", 1000001)),
    "bus.i2c-timeout-range": Row("generate", f"[{_DEVICE}.timeout] ", doc=_set("bus", "i2c0", "timeout", 0)),
    "bus.i2c-timeout-max": Row("generate", f"[{_DEVICE}.timeout] ", doc=_set("bus", "i2c0", "timeout", 10000000)),
    "bus.uart-baudrate-range": Row("generate", f"[{_DEVICE}.baudrate] ", doc=_paired(_set("bus", "uart0", "baudrate", 7812501))),
    "bus.uart-rxbuf-range": Row("generate", f"[{_DEVICE}.rxbuf] ", doc=_paired(_set("bus", "uart0", "rxbuf", 32767))),
    "bus.uart-txbuf-range": Row("generate", f"[{_DEVICE}.txbuf] ", doc=_paired(_set("bus", "uart0", "txbuf", 31))),
    "bus.uart-poll-wait-range": Row("generate", f"[{_DEVICE}/uart_link_init.poll_wait_ms] ", doc=_paired(_set("bus", "uart0", "poll_wait_ms", 0))),
    "bus.uart-poll-idle-range": Row("generate", f"[{_DEVICE}/uart_link_init.poll_idle_ms] ", doc=_paired(_set("bus", "uart0", "poll_idle_ms", 1))),
    "bus.uart-timeout-floor": Row("generate", f"[{_DEVICE}/uart_link_resp.poll_idle_ms] ", doc=_paired(_set("bus", "uart1", "poll_idle_ms", 976))),
    "bus.uart-rxbuf-floor": Row("generate", f"[{_DEVICE}/uart_link_init.rxbuf] ", doc=_paired(_set("bus", "uart0", "rxbuf", 79))),
    "bus.uart-rx-ring": Row("generate", f"[{_DEVICE}/uart_link_init.rx_ring] ", doc=_paired(_set("bus", "uart0", "rx_ring", 64))),
    "bus.unused": Row("generate", f"[{_DEVICE}.i2c1] ", doc=_set("bus", "i2c1", {"scl_pin": 7, "sda_pin": 6, "frequency": 50000})),
    "bus.uart-shared": Row("generate", f"[{_DEVICE}/uart_link_resp.bus] ", doc=_paired(_drop("bus", "uart1"), lambda d: d["instance"][-1].__setitem__("bus", "uart0"))),
    "bus.fixed-address-collision": Row("generate", f"[{_DEVICE}/scd30_b] ", doc=_doc_extra_instance({"driver": "scd30", "name_ext": "b", "bus": "i2c0", "irq_pin": 9, "trigger_s": 3})),
    "bus.address-collision": Row(
        "generate", f"[{_DEVICE}/bmp3xx_b.address] ",
        doc=_then(_doc_extra_instance({"driver": "bmp3xx", "name_ext": "a", "bus": "i2c0", "address": 0x76}), _doc_extra_instance({"driver": "bmp3xx", "name_ext": "b", "bus": "i2c0", "address": 0x76})),
    ),
    "bus.boot-clear-budget": Row(
        "generate", f"[{_DEVICE}.timeout] ",
        doc=_then(_set("bus", "i2c0", "timeout", 200000), _set("bus", "i2c1", {"scl_pin": 7, "sda_pin": 6, "frequency": 50000, "timeout": 200000}), _doc_extra_instance({"driver": "bmp3xx", "name_ext": "", "bus": "i2c1", "address": 0x76})),
        edits=(("asy_i2c_driver.py", "_CLEAR_PULSES = const(9)", "_CLEAR_PULSES = const(18)"),),
    ),
    # buildgen/validate.py: [[instance]]
    "instance.name-ext-singleton": Row("generate", f"[{_DEVICE}/notification_x.name_ext] ", doc=_set("@notification", "name_ext", "x")),
    "instance.name-ext-missing": Row("generate", f"[{_DEVICE}/scd30.name_ext] ", doc=_drop("@scd30", "name_ext")),
    "instance.field-missing": Row("generate", f"[{_DEVICE}/scd30.irq_pin] ", doc=_drop("@scd30", "irq_pin")),
    "instance.address-not-selectable": Row("generate", f"[{_DEVICE}/scd30.address] ", doc=_set("@scd30", "address", 0x61)),
    "instance.field-type": Row("generate", f"[{_DEVICE}/scd30.bus] ", doc=_set("@scd30", "bus", 0)),
    "instance.bus-undeclared": Row("generate", f"[{_DEVICE}/scd30.bus] ", doc=_set("@scd30", "bus", "i2c1")),
    "instance.bus-kind": Row("generate", f"[{_DEVICE}/scd30.bus] ", doc=_set("@scd30", "bus", "spi0")),
    "instance.no-bus-kind-row": Row("generate", f"[{_DEVICE}/scd30] ", patch=_no_bus_kind_row_for_scd30),
    "instance.uart-role": Row("generate", f"[{_DEVICE}/uart_link_resp.role] ", doc=_paired(lambda d: d["instance"][-1].__setitem__("role", "peer"))),
    "instance.uart-crc-mode": Row("generate", f"[{_DEVICE}/uart_link_init.crc] ", doc=_paired(lambda d: d["instance"][-2].__setitem__("crc", "crc32"))),
    "instance.irq-pull-up-type": Row("generate", f"[{_DEVICE}/scd30.irq_pull_up] ", doc=_set("@scd30", "irq_pull_up", 1)),
    "instance.field-unknown": Row("generate", f"[{_DEVICE}/scd30.colour] ", doc=_set("@scd30", "colour", 1)),
    "instance.uart-transfer-cap": Row("generate", f"[{_DEVICE}/uart_link_init.max_transfer_bytes] ", doc=_paired(lambda d: d["instance"][-2].__setitem__("max_transfer_bytes", 47))),
    "instance.uart-link-pair": Row("generate", f"[{_DEVICE}] ", doc=_paired(lambda d: d["instance"][-1].__setitem__("role", "initiator"))),
    "instance.uart-baud-mismatch": Row("generate", f"[{_DEVICE}/uart_link_resp.baudrate] ", doc=_paired(_set("bus", "uart1", "baudrate", 57600))),
    "instance.uart-crc-mismatch": Row("generate", f"[{_DEVICE}/uart_link_resp.crc] ", doc=_paired(lambda d: d["instance"][-2].__setitem__("crc", "crc16"))),
    "instance.uart-timeout-max": Row("generate", f"[{_DEVICE}/uart_link_init] ", doc=_paired(), edits=(("asy_uart_comm.py", "_DEFAULT_TIMEOUT_MS = const(1000)", "_DEFAULT_TIMEOUT_MS = const(100000000)"),)),
    "instance.requires-without-bus": Row(
        "generate", f"[{_DEVICE}/neopixel] ",
        edits=(("asy_neopixel_driver.py", "# @wiring fram_target FRAMManager log optional kwarg", "# @requires bus.timeout>=1\n# @wiring fram_target FRAMManager log optional kwarg"),),
    ),
    "instance.no-buildspec-row": Row(
        "generate", f"[{_DEVICE}/bogus2] ", doc=_doc_extra_instance({"driver": "bogus2", "name_ext": ""}),
        edits=(("asy_bogus2_driver.py", "", '_NAME = "BOGUS2"\n\n\nclass Bogus2_Reader(SensorReader):\n    pass\n'),),
    ),
    "instance.field-not-in-set": Row("generate", f"[{_DEVICE}/fram.max_size] ", doc=_set("@fram", "max_size", 4096)),
    "instance.field-out-of-range": Row("generate", f"[{_DEVICE}/scd30.trigger_s] ", doc=_set("@scd30", "trigger_s", 1801)),
    "instance.field-not-finite": Row(
        "generate", f"[{_DEVICE}/scd30.gain] ", doc=_set("@scd30", "gain", float("nan")), patch=_gain_allowed_on_scd30,
        edits=((_SCD30, _SCD30_TRIGGER_LIMITS, _SCD30_TRIGGER_LIMITS + "\n# @limits gain 0.5..2.5"),),
    ),
    # buildgen/validate.py: names, GPIOs
    "names.logger-collision": Row(
        "generate", f"[{_DEVICE}/bmp3xx] ", doc=_doc_extra_instance({"driver": "bmp3xx", "name_ext": "", "bus": "i2c0"}),
        edits=(("asy_bmp3xx_driver.py", '_NAME = const("BMP3XX")', '_NAME = const("NTP")'),),
    ),
    "names.settings-key-collision": Row("generate", f"[{_DEVICE}.Hostname] ", patch=_settings_key_served_twice),
    "names.label-collision": Row(
        "generate", f"[{_DEVICE}/foo_bar] ", patch=_foo_drivers_whose_labels_collide,
        doc=_then(_doc_extra_instance({"driver": "foo_bar", "name_ext": ""}), _doc_extra_instance({"driver": "foo", "name_ext": "bar"})), copy_src=True,
    ),
    "gpio.type": Row("generate", f"[{_DEVICE}/scd30.irq_pin] ", doc=_set("@scd30", "irq_pin", "8")),
    "gpio.not-usable": Row("generate", f"[{_DEVICE}/scd30.irq_pin] ", doc=_set("@scd30", "irq_pin", 23)),
    "gpio.claimed-twice": Row("generate", f"[{_DEVICE}/neopixel.pin] ", doc=_set("@neopixel", "pin", 8)),
    "gpio.no-function": Row("generate", f"[{_DEVICE}/bus.uart0.tx_pin] ", doc=_paired(_set("bus", "uart0", "tx_pin", 18))),
    "gpio.wrong-bus": Row("generate", f"[{_DEVICE}/bus.i2c0.scl_pin] ", doc=_then(_set("bus", "i2c0", "scl_pin", 11), _set("bus", "i2c0", "sda_pin", 10))),
    "gpio.wrong-role": Row("generate", f"[{_DEVICE}/bus.i2c0.scl_pin] ", doc=_then(_set("bus", "i2c0", "scl_pin", 12), _set("bus", "i2c0", "sda_pin", 13))),
    # buildgen/validate.py: wiring, sources, src/ facts and the toolchain
    "wiring.target-unresolved": Row("generate", f"[{_DEVICE}/sgp40.fram_target] ", doc=_set("@sgp40", "wiring", "fram_target", "nothing")),
    "wiring.target-class": Row("generate", f"[{_DEVICE}/notification.signal_sink] ", doc=_set("@notification", "wiring", "signal_sink", "fram")),
    "wiring.target-type": Row("generate", f"[{_DEVICE}/scd30.fram_target] ", doc=_set("@scd30", "wiring", "fram_target", 5)),
    "wiring.source-shape": Row("generate", f"[{_DEVICE}/sgp40.temperature_source] ", doc=_set("@sgp40", "wiring", "temperature_source", {"source": "scd30"})),
    "wiring.source-unresolved": Row("generate", f"[{_DEVICE}/sgp40.temperature_source] ", doc=_set("@sgp40", "wiring", "temperature_source", {"source": "bme", "field": "Temp"})),
    "source.field-unknown": Row("generate", f"[{_DEVICE}/sgp40.temperature_source] ", doc=_set("@sgp40", "wiring", "temperature_source", {"source": "scd30", "field": "Tmp"})),
    "wiring.default-key-unknown": Row("generate", f"[{_DEVICE}/sgp40.temperature_source] ", doc=_set("@sgp40", "wiring", "temperature_source", {"default": True, "temperature": 20, "bogus": 1})),
    "wiring.default-key-missing": Row(
        "generate", f"[{_DEVICE}/sgp40.temperature_source] ", doc=_set("@sgp40", "wiring", "temperature_source", {"default": True}),
        edits=(("asy_sgp40_driver.py", "def __init__(self, temperature: float = 25) -> None:", "def __init__(self, *, temperature: float) -> None:"),),
    ),
    "wiring.default-class-missing": Row("generate", f"[{_DEVICE}/sgp40.fram_target] ", doc=_set("@sgp40", "wiring", "fram_target", {"default": True})),
    "wiring.default-attr-missing": Row(
        "generate", f"[{_DEVICE}/notification.signal_sink] ", doc=_set("@notification", "wiring", "signal_sink", {"default": True}),
        copy_src=True, patch=_signal_sink_default_without_request_signal,
    ),
    "wiring.warn-outside-notification": Row("generate", f"[{_DEVICE}/scd30.warn_co2] ", doc=_set("@scd30", "wiring", "warn_co2", {"source": "scd30", "field": "CO2"})),
    "wiring.warn-unknown": Row("generate", f"[{_DEVICE}/notification.warn_radon] ", doc=_set("@notification", "wiring", "warn_radon", {"source": "scd30", "field": "CO2"})),
    "wiring.field-unknown": Row("generate", f"[{_DEVICE}/scd30.led_target] ", doc=_set("@scd30", "wiring", "led_target", "neopixel")),
    "wiring.field-missing": Row("generate", f"[{_DEVICE}/notification.signal_sink] ", doc=_drop("@notification", "wiring", "signal_sink")),
    "src.unreadable": Row("generate", "[<src>.HotspotPW] ", drop=("asy_wifi_service.py",)),
    "src.const-missing": Row("generate", "[<src>._NTP_CHECK_INTERV] ", doc=_set("device", "ntp_retry_s", 60), edits=(("asy_ntp_client.py", "_NTP_CHECK_INTERV = const(", "_NTP_CHECK_INTERVAL_X = const("),)),
    "src.schema-missing": Row("generate", "[<src>.HotspotPW] ", edits=(("asy_wifi_service.py", '("HotspotPW", "str", "12345678", 8, 63, None)', '("HotspotPW", "str", "12345678", 8, None, None)'),)),
    "src.default-missing": Row("generate", "[<src>.rx_ring] ", doc=_paired(), edits=(("asy_uart_driver.py", "rx_ring: int = 512,", "rx_ring: int = RING,"),)),
    "toolchain.overrides-unloadable": Row("generate", "[<toolchain>.max_connections] ", patch=_overrides_unloadable),
    # buildgen/api_reference.py, written by the batch script alone
    "api.source-name-missing": Row("batch", f"[{_DEVICE}.ROUTES] ", edits=(("asy_webserver_service.py", "ROUTES = (", "ROUTES_GONE = ("),)),
    "api.source-not-literal": Row("batch", f"[{_DEVICE}.ROUTES] ", edits=(("asy_webserver_service.py", "ROUTES = (", "ROUTES = () + ("),)),
    "api.routes-not-tuple": Row("batch", f"[{_DEVICE}.ROUTES] ", edits=(("asy_webserver_service.py", "ROUTES = (", 'ROUTES = "rows"\n_ROUTES_ROWS = ('),)),
    "api.routes-row-malformed": Row("batch", f"[{_DEVICE}.ROUTES] ", edits=(("asy_webserver_service.py", _FIRST_ROUTE, _FIRST_ROUTE.replace('"GET"', '"POST"')),)),
    "api.routes-duplicate": Row("batch", f"[{_DEVICE}.ROUTES] ", edits=(("asy_webserver_service.py", '    ("GET", "/sensors", "_get_sensors"),', '    ("GET", "/measurements", "_get_sensors"),'),)),
    "api.route-unregistered": Row("batch", f"[{_DEVICE}] ", edits=(("asy_webserver_service.py", '    ("PUT", "/sensors", "_put_sensors"),\n', ""),)),
    "api.result-word-not-string": Row("batch", f"[{_DEVICE}.FAILED] ", edits=(("asy_config_manager.py", 'FAILED: "Final" = "Failed"', 'FAILED: "Final" = 4'),)),
    "api.envelope-codes-malformed": Row("batch", f"[{_DEVICE}._STANDARD_CODES] ", edits=(("asy_api_response.py", "_STANDARD_CODES: dict[int, str] = {", "_STANDARD_CODES: dict[int, str] = {999: 999, "),)),
    # A syntax error there fails the frozen set first (source.syntax-error); a src/ tree without the file reaches the reference.
    "api.source-unreadable": Row("batch", f"[{_DEVICE}._STANDARD_CODES] ", drop=("asy_api_response.py",)),
    "api.field-key-unclassified": Row("batch", f"[{_DEVICE}] ", patch=_api_page_only_without_description),
}


def _rule_literals() -> "dict[str, list[str]]":
    # rule id -> the buildgen/ sites passing it; a rule= that is no literal cannot be tabled, so it fails here.
    found: dict[str, list[str]] = {}
    for path in sorted((_REPO / "buildgen").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
            if isinstance(node, ast.keyword) and node.arg == "rule":
                value = node.value
                assert isinstance(value, ast.Constant) and isinstance(value.value, str), f"buildgen/{path.name}:{value.lineno}: rule= must be a string literal"
                found.setdefault(value.value, []).append(f"buildgen/{path.name}:{value.lineno}")
    return found


def _run(row: Row, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> "tuple[int, str, list[BuildError]]":
    # Runs the row's CLI; every BuildError built on the way is kept, so the printed one's rule can be checked.
    built: list[BuildError] = []
    real_init = BuildError.__init__

    def recording_init(self: BuildError, device: str, message: str, *, rule: str, fix: str, instance: str | None = None, field: str | None = None) -> None:
        real_init(self, device, message, rule=rule, fix=fix, instance=instance, field=field)
        built.append(self)

    monkeypatch.setattr(BuildError, "__init__", recording_init)
    src = _REPO / "src"
    if row.edits or row.subs or row.drop or row.copy_src or row.entry == "batch":
        src = _src_copy(tmp_path, row)
    devices = tmp_path / "devices"
    devices.mkdir()
    toml = devices / f"{_DEVICE}.toml"
    if row.toml is not None:
        toml.write_text(row.toml)
    elif not row.absent:
        doc: TomlDoc = base_doc()
        row.doc(doc)
        write_doc(devices, _DEVICE, doc)
    row.patch(monkeypatch, tmp_path)
    argv = [str(toml), "--src-dir", str(src), *(arg.format(tmp=tmp_path) for arg in row.extra)]
    if row.call is not None:
        try:
            row.call(tmp_path)
        except BuildError as e:
            return 1, f"{e}\n", built
        return 0, "", built
    if row.entry == "generate":
        code = generate.main(argv)
    elif row.entry == "definitions":
        code = definitions.main(argv)
    else:
        (tmp_path / "ext").symlink_to(_REPO / "ext")
        script = load_script_module(_REPO / "scripts" / "_generate_sensortask_modules.py", "_generate_sensortask_modules")
        monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
        code = script.main()
    return code, capsys.readouterr().err, built


def _src_copy(tmp_path: Path, row: Row) -> Path:
    # src/ mirrored by symlinks, each edited file a real file of its own: a row breaks what a src/ file states
    # without touching src/, and writes only the files it edits, never a copy of the whole tree.
    src = tmp_path / "src"
    src.mkdir()
    for entry in (_REPO / "src").iterdir():
        (src / entry.name).symlink_to(entry)
    for name in row.drop:
        (src / name).unlink()
    for filename, old, new in row.edits:
        path = src / filename
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if old:
            assert old in text, f"{filename} no longer contains {old!r} - the row's edit has to follow"
            text = text.replace(old, new)
        else:
            text += new
        _write_own(path, text)
    for filename, pattern, replacement in row.subs:
        text, count = re.subn(pattern, replacement, (src / filename).read_text(encoding="utf-8"), flags=re.MULTILINE)
        assert count, f"{filename} no longer matches {pattern!r} - the row's edit has to follow"
        _write_own(src / filename, text)
    return src


def _write_own(path: Path, text: str) -> None:
    # Replaces the symlink first: writing through it would edit the real src/ file.
    path.unlink(missing_ok=True)
    path.write_text(text, encoding="utf-8")


def test_every_rule_in_buildgen_has_exactly_one_row() -> None:
    literals = _rule_literals()
    missing = {rule: sites for rule, sites in sorted(literals.items()) if rule not in _ROWS}
    assert not missing, f"rule ids raised under buildgen/ with no row here - add one malformed input per id: {missing}"
    assert sorted(set(_ROWS) - set(literals)) == [], "rows for rule ids no buildgen/ site raises any more - delete them"


@pytest.mark.parametrize("rule", sorted(_ROWS))
def test_each_rule_aborts_with_one_line_naming_place_and_fix(rule: str, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    row = _ROWS[rule]
    code, err, built = _run(row, tmp_path, capsys, monkeypatch)
    assert code == 1, err
    lines = err.strip().splitlines()
    assert len(lines) == 1, err
    assert lines[0].startswith(_PREFIX[row.entry] + row.place), err
    assert " - fix: " in lines[0]
    assert "Traceback" not in err
    # The line printed is this row's rule, not another one the input happened to break first.
    assert [e.rule for e in built if lines[0] == _PREFIX[row.entry] + str(e)] == [rule], err


def test_a_bus_less_device_generates(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A device with no [bus.*] table is legal (only a NeoPixel here): it builds instead of failing on a missing key.
    doc: TomlDoc = base_doc()
    del doc["bus"]
    doc["instance"] = [{"driver": "neopixel", "pin": 15}]
    doc["device"]["wiring"] = {"led_target": "neopixel"}
    out = tmp_path / "out"
    assert generate.main([str(write_doc(tmp_path, _DEVICE, doc)), "--out-dir", str(out)]) == 0, capsys.readouterr().err
    assert sorted(p.name for p in out.iterdir()) == [f"sensortask_{_DEVICE}.py", f"sensortask_{_DEVICE}_main.py", f"sensortask_{_DEVICE}_main_noautostart.py"]


def test_a_write_failing_part_way_leaves_no_output_file(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # A full disk on the second file: one line and exit 1, and neither a final file nor a .tmp left behind.
    toml = write_doc(tmp_path, _DEVICE, base_doc())
    out = tmp_path / "out"
    real_write_text = Path.write_text
    writes: list[str] = []

    def write_text_until_the_disk_is_full(self: Path, data: str, encoding: str | None = None) -> int:
        writes.append(self.name)
        if len(writes) == 2:
            raise OSError(errno.ENOSPC, "No space left on device", str(self))
        return real_write_text(self, data, encoding=encoding)

    monkeypatch.setattr(Path, "write_text", write_text_until_the_disk_is_full)
    assert generate.main([str(toml), "--out-dir", str(out)]) == 1
    err = capsys.readouterr().err
    assert err.startswith(f"buildgen: [{_DEVICE}] cannot write ") and "No space left on device - fix: " in err
    assert sorted(p.name for p in out.iterdir()) == []


@pytest.mark.parametrize("broken", ["module", "boot entry", "no-autostart boot entry"])
def test_a_generated_source_that_does_not_compile_is_a_build_internal_error(broken: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A generator bug, never a TOML mistake: it propagates past the CLI with its traceback, naming the device and line.
    real_module, real_entry = generate_module_source, generate_boot_entry_source
    invalid = "x = 1\ndef broken(:\n"
    monkeypatch.setattr(generate, "generate_module_source", lambda *a, **k: invalid if broken == "module" else real_module(*a, **k))
    monkeypatch.setattr(
        generate,
        "generate_boot_entry_source",
        lambda device, *, autostart=True: invalid if broken == ("boot entry" if autostart else "no-autostart boot entry") else real_entry(device, autostart=autostart),
    )
    with pytest.raises(BuildInternalError, match=rf"^{_DEVICE}: generated sensortask_{_DEVICE}\S*\.py does not compile: line 2: "):
        generate.main([str(write_doc(tmp_path, _DEVICE, base_doc()))])
