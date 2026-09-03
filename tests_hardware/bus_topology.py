"""Declarative bus-topology registry for tests_hardware/ - the host-side mirror of
digital_twin/machine.py's `_wire_i2c_devices()`/`_wire_spi_device()`, which is the canonical
per-variant wiring declaration (cross-checked automatically on every push by
tests/test_digital_twin_bus_hazard_concurrency.py's own real build_system() boot - a wiring typo
there fails loudly with a real NAK, not a silent gap). This file exists because tests_hardware/ is
host-side CPython/pytest and cannot import that MicroPython-only module directly.

This bench's real board always runs the `dev` build - wozi is never physically flashed
(CLAUDE.md's hard rule) - so DEV_I2C_BUSES/DEV_SPI is what every flash/bench test should expect.
WOZI_I2C_BUSES/WOZI_SPI is kept here for documentation parity only (never bench-tested; the digital
twin is the real verification tier for that variant).

**No flash/bench device script imports this file** (device_scripts/ are single, self-contained
files transmitted via `mpremote run` - no sibling-file imports possible, confirmed against every
existing script). Each device script that needs this topology keeps its own small inline copy of
KNOWN_ADDRESSES (with a comment pointing back here) and, more importantly, live-verifies its own
assumptions via a real `i2c.scan()` before doing anything else - see
device_scripts/bus_topology_autodetect_and_hazard_sweep.py's own docstring for the auto-detection
mechanism this enables, which is what actually makes this tier resilient to *undeclared* wiring
changes and future devices, not this file's own declared data alone.

**Standing rule - read before adding a new bus-facing device to src/, or wiring one onto an
existing bus:** update this file's KNOWN_ADDRESSES/DEV_I2C_BUSES/WOZI_I2C_BUSES, the matching entry
in digital_twin/machine.py's `_wire_i2c_devices()`, and every device-script's own inline
KNOWN_ADDRESSES copy - a device missing from KNOWN_ADDRESSES here still gets picked up by
i2c.scan()'s live auto-detection (reported as "unknown@0xNN"), so nothing silently disappears, but
its bus-hazard coverage stays generic/unlabeled until this registry catches up. See
SPECIFICATION.md Part C.8's own note on this."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class I2CDeviceSpec:
    name: str
    address: int


@dataclass(frozen=True)
class I2CBusSpec:
    port_id: int
    scl: int
    sda: int
    devices: tuple[I2CDeviceSpec, ...]


# dev bench wiring - sensortask_dev.py's own construction comments (the only variant ever
# physically bench-tested).
DEV_I2C_BUSES: tuple[I2CBusSpec, ...] = (
    I2CBusSpec(port_id=0, scl=13, sda=12, devices=(I2CDeviceSpec("BMP3xx", 0x77),)),
    I2CBusSpec(port_id=1, scl=15, sda=14, devices=(I2CDeviceSpec("SCD30", 0x61), I2CDeviceSpec("SGP40", 0x59))),
)
DEV_SPI_CS = 5  # FRAM (MB85RS2MTA, 256KB), spi0

# wozi production wiring - sensortask_wozi.py's own construction comments. Documentation only: see
# module docstring above.
WOZI_I2C_BUSES: tuple[I2CBusSpec, ...] = (
    I2CBusSpec(port_id=0, scl=13, sda=12, devices=(I2CDeviceSpec("SCD30", 0x61),)),
    I2CBusSpec(port_id=1, scl=19, sda=18, devices=(I2CDeviceSpec("SGP40", 0x59), I2CDeviceSpec("BMP3xx", 0x77))),
)
WOZI_SPI_CS = 1  # FRAM (MB85RS64V, 8KB), spi0

KNOWN_ADDRESSES: dict[int, str] = {0x61: "SCD30", 0x59: "SGP40", 0x77: "BMP3xx"}
GENERAL_CALL_ADDRESS = 0x00
# I2C spec reserved address ranges: 0x00-0x07 (general call/CBUS/reserved/Hs-mode), 0x78-0x7F
# (10-bit addressing/reserved). No promoted device's own address may ever fall inside either.
RESERVED_I2C_RANGES: tuple[tuple[int, int], ...] = ((0x00, 0x07), (0x78, 0x7F))


def is_reserved(address: int) -> bool:
    return any(lo <= address <= hi for lo, hi in RESERVED_I2C_RANGES)


assert not any(is_reserved(spec.address) for bus in DEV_I2C_BUSES for spec in bus.devices), "a declared dev device address falls in a reserved I2C range"
assert not any(is_reserved(spec.address) for bus in WOZI_I2C_BUSES for spec in bus.devices), "a declared wozi device address falls in a reserved I2C range"
