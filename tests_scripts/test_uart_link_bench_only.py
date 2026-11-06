"""The UART link exerciser stays off every deployed board: only the bench board's TOML declares a uart_link instance,
and no other device's firmware imports or freezes its driver (owner, 2026-10-22: "the guard from being included in
real deployed firmware is the fact that the module is never included in the config files for deployment boards")."""

import ast
import json
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, bench_device, device_toml, devices_with

from buildgen.api_reference import api_reference_json, generate_api_reference
from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "uart_link"
_MODULE = "asy_uart_link_driver"
_BUILD_DATE = "2026-01-01T00:00:00Z"  # fixed, so generation is deterministic; nothing here reads it
# What the link brings when wired: its key, route, website form and generated route line, and the /status hook it replaced.
_TRACES = ("UartHazards", "uartHazards", "Hazard Run", "hazard_run", "/uart", "add_routes", "status_command")


def _imported_modules(source: str) -> "set[str]":
    tree = ast.parse(source)
    names = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    return names | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}


def test_only_the_bench_board_declares_a_uart_link() -> None:
    # The allow-set is the one board with [device] bench = true, read from the TOMLs rather than named.
    declared = devices_with(_DRIVER)
    allowed = {bench_device()}
    assert declared, f"no device TOML declares driver = {_DRIVER!r}: the bench board lost its link, so this guard checks nothing"
    stray = sorted(set(declared) - allowed)
    assert not stray, f"driver = {_DRIVER!r} is bench-only, allowed on {sorted(allowed)}; also declared in " + ", ".join(f"devices/{d}.toml" for d in stray)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_only_the_bench_boards_firmware_carries_the_uart_link_driver(device: str) -> None:
    generated = generate_device(device_toml(device), REPO_ROOT / "src", REPO_ROOT / "ext", build_date=_BUILD_DATE)
    sources = (generated.module_source, generated.boot_entry_source, generated.boot_entry_noautostart_source)
    imported = any(_MODULE in _imported_modules(source) for source in sources)
    frozen = _MODULE in generated.frozen_modules
    expected = device == bench_device()
    assert (imported, frozen) == (expected, expected), f"{device}: imports {_MODULE}: {imported}, freezes it: {frozen}; only the bench board's firmware carries it"


@pytest.mark.parametrize("device", [name for name in DEVICE_NAMES if name != bench_device()])
def test_a_build_without_the_link_carries_no_trace_of_it(device: str) -> None:
    # The owner (2026-11-06): "If the module is not imported, as in all non-dev builds, there is not a single trace of
    # anything about it, no hook, no website, no endpoint, no lines." Every generated text and every frozen source is read.
    generated = generate_device(device_toml(device), REPO_ROOT / "src", REPO_ROOT / "ext", build_date=_BUILD_DATE)
    texts = {
        "generated module": generated.module_source, "boot entry": generated.boot_entry_source, "no-autostart entry": generated.boot_entry_noautostart_source,
        "website definitions": json.dumps(generate_definitions(generated.model, REPO_ROOT / "src")),
        "REST reference": api_reference_json(generate_api_reference(generated.model, REPO_ROOT / "src")),
    }
    texts |= {f"src/{name}.py": (REPO_ROOT / "src" / f"{name}.py").read_text(encoding="utf-8") for name in generated.frozen_modules if (REPO_ROOT / "src" / f"{name}.py").is_file()}
    found = sorted(f"{where}: {trace!r}" for where, text in texts.items() for trace in _TRACES if trace in text)
    assert not found, f"{device} carries traces of the bench-only UART link: {found}"
