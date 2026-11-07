"""Shared TOML fixtures for tests_scripts/test_buildgen_*.py: a minimal valid device dict (base_doc(),
with_uart_pair()) that a negative-path test edits through checked accessors (table_at(), array_at(),
instances()) and writes with dump_toml(), instead of hand-editing another near-identical TOML blob."""

# dump_toml() is not a general TOML writer - it covers only the shape buildgen/'s own schema uses
# (SPECIFICATION.md Part L.3's device TOML schema), which is all these fixtures ever need.

import copy
import datetime
import json
from pathlib import Path
from typing import TypeAlias

# Same shape as buildgen.model.TomlDoc, kept local: this module never imports buildgen/.
TomlValue: TypeAlias = str | int | float | bool | datetime.date | datetime.time | datetime.datetime | list["TomlValue"] | dict[str, "TomlValue"]
TomlDoc: TypeAlias = dict[str, TomlValue]


def _dump_scalar(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(_dump_scalar(x) for x in v) + "]"
    if isinstance(v, dict):
        # An inline table, for a value a negative-path test plants where a scalar belongs.
        return ("{ " + ", ".join(f"{k} = {_dump_scalar(x)}" for k, x in v.items()) + " }") if v else "{}"
    return str(v)


def _walk(doc: TomlDoc, path: tuple[str | int, ...]) -> TomlValue:
    node: TomlValue = doc
    for step in path:
        if isinstance(node, dict) and isinstance(step, str):
            node = node[step]
            continue
        if isinstance(node, list) and isinstance(step, int):
            node = node[step]
            continue
        raise TypeError(f"{step!r} cannot index a {type(node).__name__} in a fixture document")
    return node


def array(value: TomlValue) -> list[TomlValue]:
    # Narrows by checking, so a fixture of the wrong shape fails here and never as a later lookup.
    if not isinstance(value, list):
        raise TypeError(f"expected a TOML array, got {type(value).__name__}")
    return value


def array_at(doc: TomlDoc, *path: str | int) -> list[TomlValue]:
    # The array reached by str keys into tables and int indices into arrays.
    return array(_walk(doc, path))


def base_doc() -> TomlDoc:
    # A minimal, valid device: one of everything (scd30/sgp40/fram/neopixel/notification), deep
    # copy per call so tests can freely mutate their own instance.
    return copy.deepcopy(
        {
            "device": {
                "name": "Test",
                "hostname": "SensorStationTest",
                "hotspot_password": "12345678",
                "conn_fail_to_hotspot": 5,
                "hotspot_time_min": 8,
                "wiring": {"led_target": "neopixel", "fram_target": "fram"},
            },
            "bus": {
                "i2c0": {"scl_pin": 13, "sda_pin": 12, "frequency": 50000, "timeout": 200000},
                "spi0": {"sck_pin": 2, "mosi_pin": 3, "miso_pin": 4},
            },
            "instance": [
                {"driver": "scd30", "name_ext": "", "bus": "i2c0", "irq_pin": 8, "trigger_s": 3, "wiring": {"fram_target": "fram"}},
                {
                    "driver": "sgp40",
                    "name_ext": "",
                    "bus": "i2c0",
                    "wiring": {
                        "temperature_source": {"source": "scd30", "field": "Temp"},
                        "humidity_source": {"source": "scd30", "field": "Hum"},
                        "fram_target": "fram",
                    },
                },
                {"driver": "fram", "bus": "spi0", "cs_pin": 1, "max_size": 8192},
                {"driver": "neopixel", "pin": 15, "wiring": {"fram_target": "fram"}},
                {
                    "driver": "notification",
                    "wiring": {
                        "signal_sink": "neopixel",
                        "fram_target": "fram",
                        "warn_co2": {"source": "scd30", "field": "CO2"},
                    },
                },
            ],
        },
    )


def dump_toml(doc: TomlDoc) -> str:
    lines: list[str] = []
    device = doc.get("device")
    if device is not None:
        lines.append("[device]")
        # A non-table wiring is written as the plain value it is, for the check that refuses it.
        lines += [f"{k} = {_dump_scalar(v)}" for k, v in table(device).items() if k != "wiring" or not isinstance(v, dict)]
        device_wiring = table(device).get("wiring")
        if isinstance(device_wiring, dict):
            lines += ["", "[device.wiring]"]
            lines += [f"{k} = {_dump_scalar(v)}" for k, v in device_wiring.items()]

    for bus_name, bus_table in table(doc.get("bus", {})).items():
        lines += ["", f"[bus.{bus_name}]"]
        lines += [f"{k} = {_dump_scalar(v)}" for k, v in table(bus_table).items()]

    for inst in array(doc.get("instance", [])):
        lines += ["", "[[instance]]"]
        wiring = table(inst).get("wiring")
        lines += [f"{k} = {_dump_scalar(v)}" for k, v in table(inst).items() if k != "wiring" or not isinstance(v, dict)]
        if isinstance(wiring, dict):
            lines += ["", "[instance.wiring]"]
            subtables = {k: v for k, v in wiring.items() if isinstance(v, dict)}
            lines += [f"{k} = {_dump_scalar(v)}" for k, v in wiring.items() if not isinstance(v, dict)]
            for sk, sv in subtables.items():
                lines += ["", f"[instance.wiring.{sk}]"]
                lines += [f"{k} = {_dump_scalar(v)}" for k, v in sv.items()]

    return "\n".join(lines) + "\n"


def instance_of(doc: TomlDoc, driver: str) -> TomlDoc:
    # The first [[instance]] of `driver`.
    return next(inst for inst in instances(doc) if inst["driver"] == driver)


def instances(doc: TomlDoc) -> list[TomlDoc]:
    # Every [[instance]] table, each checked; a new list over the same tables, so edits to one reach `doc`.
    return [table(inst) for inst in array_at(doc, "instance")]


def table(value: TomlValue) -> TomlDoc:
    # Narrows by checking, as array() does.
    if not isinstance(value, dict):
        raise TypeError(f"expected a TOML table, got {type(value).__name__}")
    return value


def table_at(doc: TomlDoc, *path: str | int) -> TomlDoc:
    # The table reached by `path`, as array_at() walks it.
    return table(_walk(doc, path))


def with_uart_pair(doc: TomlDoc) -> TomlDoc:
    # A uart0 initiator and a uart1 responder, the shape a crossover pair takes, each on a datasheet-legal
    # pin pair (GP16/17, GP8/9) no base_doc() pin claims once scd30's irq_pin moves off GP8.
    instance_of(doc, "scd30")["irq_pin"] = 6
    # The bench pair's bus knobs too, so the link checks run against tuning a real link ships with.
    knobs = {"baudrate": 115200, "rxbuf": 512, "txbuf": 512, "poll_wait_ms": 2, "poll_idle_ms": 50}
    table_at(doc, "bus")["uart0"] = {"tx_pin": 16, "rx_pin": 17, **knobs}
    table_at(doc, "bus")["uart1"] = {"tx_pin": 8, "rx_pin": 9, **knobs}
    array_at(doc, "instance").append({"driver": "uart_link", "name_ext": "init", "bus": "uart0", "role": "initiator"})
    array_at(doc, "instance").append({"driver": "uart_link", "name_ext": "resp", "bus": "uart1", "role": "responder"})
    return doc


def write_doc(tmp_path: Path, name: str, doc: TomlDoc) -> Path:
    path = tmp_path / f"{name}.toml"
    path.write_text(dump_toml(doc), encoding="utf-8")
    return path


def write_text(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / f"{name}.toml"
    path.write_text(text, encoding="utf-8")
    return path
