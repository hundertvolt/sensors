"""Derives the digital twin's per-device I2C/SPI wiring plan (which chip fake sits at which bus address) from a validated `DeviceModel` - the same shape `digital_twin/machine.py`'s `configure_wiring()` consumes at twin-boot time, replacing the old wozi/dev 2-profile enum (BUILD_CHAIN_PLAN.md's Session 5 mission).
See `digital_twin/README.md`'s "Booting a generated device" section for the twin-side half of this mechanism."""

from typing import Any

from buildgen.buildspec import ADDRESS_CAPABLE_DRIVERS, BUS_ATTACHED_DRIVERS, FIXED_ADDRESS_DRIVERS
from buildgen.model import DeviceModel

# scd30/sgp40 carry no TOML `address` field (buildspec.py's own FIXED_ADDRESS_DRIVERS) - their real
# I2C address is fixed in hardware, matching asy_scd30_driver.py's/asy_sgp40_driver.py's own
# defaults - a twin-only named exception, not a broken generalization promise (see README.md).
FIXED_ADDRESSES: "dict[str, int]" = {"scd30": 0x61, "sgp40": 0x59}


def compute_twin_wiring(model: DeviceModel) -> "dict[str, Any]":
    """A JSON-serializable wiring plan - which chip fake sits at which I2C address/bus, which FRAM chip on which SPI bus - covering everything `machine.py`'s `_wire_i2c_devices()`/`_wire_spi_device()` need, derived straight from `model`'s own validated facts rather than a second hand-maintained table.
    Shape: {"device": str, "buses": {"i2cN": [{"driver", "name_ext", "address", ["irq_pin"]}, ...]}, "spi": {"spiN": {"driver": "fram", "name_ext", "max_size"}}}. Trusts an already-`build_model()`-validated `model` (no duplicate address within one bus)."""
    buses: dict[str, list[dict[str, Any]]] = {}
    spi: dict[str, dict[str, Any]] = {}
    for spec in model.instances.values():
        if spec.driver not in BUS_ATTACHED_DRIVERS:
            continue
        bus_name = spec.fields["bus"]
        if spec.driver == "fram":
            spi[bus_name] = {"driver": "fram", "name_ext": spec.name_ext, "max_size": spec.fields["max_size"]}
            continue
        if spec.driver in ADDRESS_CAPABLE_DRIVERS:
            address = spec.fields["address"]
        elif spec.driver in FIXED_ADDRESS_DRIVERS:
            address = FIXED_ADDRESSES[spec.driver]
        else:
            # Unreachable for today's real driver set (scd30/sgp40/bmp3xx/fram) - every
            # BUS_ATTACHED_DRIVERS member is one of ADDRESS_CAPABLE_DRIVERS/FIXED_ADDRESS_DRIVERS/
            # "fram" by buildspec.py's own definitions. Guards a future bus-attached driver added to
            # buildspec.py without a matching FIXED_ADDRESSES entry here.
            raise ValueError(f"digital twin twin_wiring has no address rule for bus-attached driver {spec.driver!r} - add it to buildgen.twin_wiring.FIXED_ADDRESSES or ADDRESS_CAPABLE_DRIVERS")
        attachment: dict[str, Any] = {"driver": spec.driver, "name_ext": spec.name_ext, "address": address}
        if spec.driver == "scd30":
            attachment["irq_pin"] = spec.fields["irq_pin"]
        buses.setdefault(bus_name, []).append(attachment)
    return {"device": model.device, "buses": buses, "spi": spi}
