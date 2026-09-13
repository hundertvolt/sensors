"""Derives the digital twin's per-device I2C/SPI wiring plan (which chip fake sits at which bus address) from a validated `DeviceModel` - the same shape `digital_twin/machine.py`'s `configure_wiring()` consumes at twin-boot time, replacing the old wozi/dev 2-profile enum (BUILD_CHAIN_PLAN.md's Session 5 mission).
See `digital_twin/README.md`'s "Booting a generated device" section for the twin-side half of this mechanism."""

from typing import Any

from buildgen.buildspec import ADDRESS_CAPABLE_DRIVERS, BUS_ATTACHED_DRIVERS, FIXED_ADDRESS_DRIVERS
from buildgen.model import DeviceModel, instance_label

# scd30/sgp40 carry no TOML `address` field (buildspec.py's own FIXED_ADDRESS_DRIVERS) - their real
# I2C address is fixed in hardware, matching asy_scd30_driver.py's/asy_sgp40_driver.py's own
# defaults - a twin-only named exception, not a broken generalization promise (see README.md).
FIXED_ADDRESSES: "dict[str, int]" = {"scd30": 0x61, "sgp40": 0x59}


def _compute_uart_wiring(model: DeviceModel) -> "dict[str, str] | None":
    # Which two already-constructed uart_link instances are the crossover pair, named by the exact
    # generated Python variable each resolves to (instance_label() - the same identity
    # buildgen.codegen._Ctx.instance_var() derives its own generated variable names from, so a
    # caller can getattr(module, plan["uart"]["initiator_var"]) on the real booted module).
    # None when the device has no uart_link instances at all (every device but "dev" today).
    initiator_var: str | None = None
    responder_var: str | None = None
    for spec in model.instances.values():
        if spec.driver != "uart_link":
            continue
        var = instance_label(spec.key)
        if spec.fields.get("role") == "initiator":
            initiator_var = var
        elif spec.fields.get("role") == "responder":
            responder_var = var
    if initiator_var is None or responder_var is None:
        return None
    return {"initiator_var": initiator_var, "responder_var": responder_var}


def compute_twin_wiring(model: DeviceModel) -> "dict[str, Any]":
    """A JSON-serializable wiring plan - which chip fake sits at which I2C address/bus, which FRAM chip on which SPI bus, and which two UART instances are the crossover pair - covering everything `machine.py`'s `_wire_i2c_devices()`/`_wire_spi_device()`/`configure_wiring()` need, derived straight from `model`'s own validated facts rather than a second hand-maintained table.
    Shape: {"device": str, "buses": {"i2cN": [{"driver", "name_ext", "address", ["irq_pin"]}, ...]}, "spi": {"spiN": {"driver": "fram", "name_ext", "max_size"}}, "uart": {"initiator_var", "responder_var"} | None}. Trusts an already-`build_model()`-validated `model` (no duplicate address within one bus, no more than one initiator/responder pair)."""
    buses: dict[str, list[dict[str, Any]]] = {}
    spi: dict[str, dict[str, Any]] = {}
    uart = _compute_uart_wiring(model)
    for spec in model.instances.values():
        if spec.driver == "uart_link":
            # A point-to-point peripheral, not an address-attached one - handled above, entirely
            # separately from the i2c/spi "device at address" shape the rest of this loop covers.
            continue
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
    return {"device": model.device, "buses": buses, "spi": spi, "uart": uart}
