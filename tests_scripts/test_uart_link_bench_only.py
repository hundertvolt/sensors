"""The UART link exerciser stays off every deployed board: only the bench board's TOML declares a uart_link instance,
and no other device's firmware imports or freezes its driver (owner, 2026-10-22: "the guard from being included in
real deployed firmware is the fact that the module is never included in the config files for deployment boards")."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, bench_device, device_toml, devices_with

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "uart_link"
_MODULE = "asy_uart_link_driver"
_BUILD_DATE = "2026-01-01T00:00:00Z"  # fixed, so generation is deterministic; nothing here reads it


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
