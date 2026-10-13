"""Derives the digital twin's per-device wiring plan (which chip fake sits at which bus address, the FRAM on its SPI bus, the UART crossover pair, every declared driver) from a validated `DeviceModel` - the same shape `digital_twin/machine.py`'s `configure_wiring()` consumes at twin-boot time (SPECIFICATION.md Part L.4).
See `digital_twin/README.md`'s "Booting a generated device" section for the twin-side half of this mechanism."""

from typing import NotRequired, TypedDict, cast

from buildgen.buildspec import ADDRESS_CAPABLE_DRIVERS, BUS_ATTACHED_DRIVERS, FIXED_ADDRESS_DRIVERS
from buildgen.driver_registry import DriverInfo
from buildgen.errors import BuildError
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.validate import module_int_const

_NO_ADDRESS_FIX = "declare the driver's I2C address as a module-level const in its src/ file, or add it to buildspec.ADDRESS_CAPABLE_DRIVERS"


class I2CAttachment(TypedDict):
    driver: str
    name_ext: str
    address: int
    irq_pin: NotRequired[int]  # scd30 and isl29125 only: the INT/RDY line the chip fake drives edges on


class SpiAttachment(TypedDict):
    driver: str
    name_ext: str
    max_size: int


class UartPair(TypedDict):
    # The two UART buses carrying the crossover pair, named by the generated global each bus is
    # bound to (its [bus.<id>] table), so a caller can getattr() the built driver off the booted module.
    initiator_bus: str
    responder_bus: str


class TwinWiringPlan(TypedDict):
    device: str
    buses: dict[str, list[I2CAttachment]]
    spi: dict[str, SpiAttachment]
    uart: UartPair | None  # None on a device without a uart_link pair.
    instances: list[str]  # every driver the TOML declares, bus-attached or not, sorted


def _compute_uart_wiring(model: DeviceModel) -> "UartPair | None":
    initiator_bus: str | None = None
    responder_bus: str | None = None
    for spec in model.instances.values():
        if spec.driver != "uart_link":
            continue
        if spec.fields.get("role") == "initiator":
            initiator_bus = str(spec.fields["bus"])
        elif spec.fields.get("role") == "responder":
            responder_bus = str(spec.fields["bus"])
    if initiator_bus is None or responder_bus is None:
        return None
    return {"initiator_bus": initiator_bus, "responder_bus": responder_bus}


def _validated_int(spec: InstanceSpec, field: str) -> int:
    # build_model() refused anything but an int in this field (Part L.5); the cast only narrows the TOML value's type.
    return cast("int", spec.fields[field])


def compute_twin_wiring(model: DeviceModel) -> TwinWiringPlan:
    # A JSON-serializable wiring plan covering everything `machine.py`'s `_wire_i2c_devices()`/`_wire_spi_device()`/`configure_wiring()` need, derived straight from `model`'s own validated facts rather than a second hand-maintained table.
    # Trusts an already-`build_model()`-validated `model` (no duplicate address within one bus, no more than one initiator/responder pair).
    buses: dict[str, list[I2CAttachment]] = {}
    spi: dict[str, SpiAttachment] = {}
    for spec in model.instances.values():
        if spec.driver == "uart_link":
            # A point-to-point peripheral, not an address-attached one - handled by
            # _compute_uart_wiring(), entirely apart from the i2c/spi "device at address" shape.
            continue
        if spec.driver not in BUS_ATTACHED_DRIVERS:
            continue
        bus_name = str(spec.fields["bus"])
        if spec.driver == "fram":
            spi[bus_name] = {"driver": "fram", "name_ext": spec.name_ext, "max_size": _validated_int(spec, "max_size")}
            continue
        if spec.driver in ADDRESS_CAPABLE_DRIVERS:
            address = _validated_int(spec, "address")
        elif spec.driver in FIXED_ADDRESS_DRIVERS and spec.driver_info is not None:
            address = fixed_address(spec.driver_info, device=model.device, instance=spec.label)
        else:
            # Unreachable for today's driver set: every BUS_ATTACHED_DRIVERS member is address-
            # capable, fixed-address or fram by buildspec.py's own definitions. This guards a
            # future bus-attached driver added there without an address rule here.
            message = f"the twin's wiring plan has no address rule for bus-attached driver {spec.driver!r}"
            raise BuildError(model.device, message, instance=spec.label, rule="twin.no-address-rule", fix=_NO_ADDRESS_FIX)
        attachment: I2CAttachment = {"driver": spec.driver, "name_ext": spec.name_ext, "address": address}
        if spec.driver in ("scd30", "isl29125"):
            # Both wire a real INT/RDY line the twin's chip fake has to drive edges on
            # (machine._build_i2c_chip()) - bmp3xx/sgp40 have no such pin at all.
            attachment["irq_pin"] = _validated_int(spec, "irq_pin")
        buses.setdefault(bus_name, []).append(attachment)
    instances = sorted({spec.driver for spec in model.instances.values()})
    return {"device": model.device, "buses": buses, "spi": spi, "uart": _compute_uart_wiring(model), "instances": instances}


def fixed_address(info: DriverInfo, *, device: str = "<src>", instance: str | None = None) -> int:
    # A fixed-address chip's I2C address: its driver file's own module-level `_<DRIVER>_ADDR = const(<int>)`,
    # read by AST, so the plan follows the driver rather than a second table here.
    name = f"_{info.driver.upper()}_ADDR"
    try:
        return module_int_const(info.source_path.parent, info.source_path.name, name)
    except BuildError as e:
        message = f"{info.source_path.name} has no readable module-level {name} = const(<int>), so the twin cannot place a {info.driver!r} chip on its bus"
        raise BuildError(device, message, instance=info.driver if instance is None else instance, rule="twin.no-address-rule", fix=_NO_ADDRESS_FIX) from e
