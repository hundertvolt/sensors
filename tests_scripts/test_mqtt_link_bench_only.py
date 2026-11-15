"""The MQTT link exerciser stays off every deployed board, as the UART one does (test_uart_link_bench_only.py): only the
bench board's TOML declares an mqtt_link instance, and no other device's firmware, website or REST reference carries
it (owner, 2026-11-12, asked what dev's MQTT test target should do: "Exerciser (Recommended)", no other device's)."""

import json
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, bench_device, device_toml, devices_with

from buildgen.api_reference import api_reference_json, generate_api_reference
from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device
from buildgen.model import MAINTENANCE_NAMES

REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "mqtt_link"
_MODULE = "asy_mqtt_link_driver"
_BUILD_DATE = "2026-01-01T00:00:00Z"  # fixed, so generation is deterministic; nothing here reads it
_TRACES = (MAINTENANCE_NAMES[_DRIVER], "MQTTLinkDriver", _DRIVER, "link/echo")  # its /status key, class, variable and topic


def test_only_the_bench_board_declares_an_mqtt_link() -> None:
    # The allow-set is the one board with [device] bench = true, read from the TOMLs rather than named.
    declared = devices_with(_DRIVER)
    assert declared, f"no device TOML declares driver = {_DRIVER!r}: the bench board lost its exerciser, so this guard checks nothing"
    stray = sorted(set(declared) - {bench_device()})
    assert not stray, f"driver = {_DRIVER!r} is bench-only, allowed on {bench_device()}; also declared in " + ", ".join(f"devices/{d}.toml" for d in stray)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_only_the_bench_boards_firmware_carries_the_mqtt_link_driver(device: str) -> None:
    generated = generate_device(device_toml(device), REPO_ROOT / "src", REPO_ROOT / "ext", build_date=_BUILD_DATE)
    imported = f"from {_MODULE} import " in generated.module_source
    frozen = _MODULE in generated.frozen_modules
    expected = device == bench_device()
    assert (imported, frozen) == (expected, expected), f"{device}: imports {_MODULE}: {imported}, freezes it: {frozen}; only the bench board's firmware carries it"


@pytest.mark.parametrize("device", [name for name in DEVICE_NAMES if name != bench_device()])
def test_a_build_without_the_exerciser_carries_no_trace_of_it(device: str) -> None:
    # Every generated text and every frozen source is read, as for the UART link.
    generated = generate_device(device_toml(device), REPO_ROOT / "src", REPO_ROOT / "ext", build_date=_BUILD_DATE)
    texts = {
        "generated module": generated.module_source, "boot entry": generated.boot_entry_source, "no-autostart entry": generated.boot_entry_noautostart_source,
        "website definitions": json.dumps(generate_definitions(generated.model, REPO_ROOT / "src")),
        "REST reference": api_reference_json(generate_api_reference(generated.model, REPO_ROOT / "src")),
    }
    texts |= {f"src/{name}.py": (REPO_ROOT / "src" / f"{name}.py").read_text(encoding="utf-8") for name in generated.frozen_modules if (REPO_ROOT / "src" / f"{name}.py").is_file()}
    found = sorted(f"{where}: {trace!r}" for where, text in texts.items() for trace in _TRACES if trace in text)
    assert not found, f"{device} carries traces of the bench-only MQTT exerciser: {found}"
