"""Shared TOML fixtures for tests_scripts/test_buildgen_*.py: a minimal valid device dict
(base_doc()) plus a small serializer (dump_toml()), so a negative-path test mutates a dict instead
of hand-editing another near-identical TOML blob."""

# dump_toml() is not a general TOML writer - it covers only the shape buildgen/'s own schema uses
# (BUILD_CHAIN_PLAN.md's "Device TOML schema"), which is all these fixtures ever need.

import copy
import json
from pathlib import Path


def base_doc() -> dict:
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
                {"driver": "scd30", "name_ext": "", "bus": "i2c0", "irq_pin": 8, "trigger_sec": 3, "wiring": {"fram_target": "fram"}},
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
        }
    )


def _dump_scalar(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v)
    return str(v)


def dump_toml(doc: dict) -> str:
    lines: list[str] = []
    device = doc.get("device")
    if device is not None:
        lines.append("[device]")
        for k, v in device.items():
            if k != "wiring":
                lines.append(f"{k} = {_dump_scalar(v)}")
        if "wiring" in device:
            lines += ["", "[device.wiring]"]
            lines += [f"{k} = {_dump_scalar(v)}" for k, v in device["wiring"].items()]

    for bus_name, bus_table in doc.get("bus", {}).items():
        lines += ["", f"[bus.{bus_name}]"]
        lines += [f"{k} = {_dump_scalar(v)}" for k, v in bus_table.items()]

    for inst in doc.get("instance", []):
        lines += ["", "[[instance]]"]
        wiring = inst.get("wiring")
        lines += [f"{k} = {_dump_scalar(v)}" for k, v in inst.items() if k != "wiring"]
        if wiring is not None:
            lines += ["", "[instance.wiring]"]
            subtables = {k: v for k, v in wiring.items() if isinstance(v, dict)}
            lines += [f"{k} = {_dump_scalar(v)}" for k, v in wiring.items() if not isinstance(v, dict)]
            for sk, sv in subtables.items():
                lines += ["", f"[instance.wiring.{sk}]"]
                lines += [f"{k} = {_dump_scalar(v)}" for k, v in sv.items()]

    return "\n".join(lines) + "\n"


def write_doc(tmp_path: Path, name: str, doc: dict) -> Path:
    path = tmp_path / f"{name}.toml"
    path.write_text(dump_toml(doc))
    return path


def write_text(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / f"{name}.toml"
    path.write_text(text)
    return path
