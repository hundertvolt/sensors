"""Declarative bus-topology registry for tests_hardware/ - host-side mirror of digital_twin/
machine.py's wiring declaration (dev is the only bench-tested variant; wozi is documentation-only).
A hand-kept second copy of devices/dev.toml's/wozi.toml's own wiring facts, cross-checked by no
tooling and imported by nothing today (BUILD_CHAIN_PLAN.md's Session 8 closing pass; BACKLOG.md)."""

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
