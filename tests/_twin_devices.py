"""The generated device set and the queries the tests share over it: the devices are the stems of the wiring plans the
generator writes from devices/*.toml into build/generated_src/, so a new TOML joins every caller with no edit there, and
a test needing a device with some property asks for it (SPECIFICATION.md E.2.1)."""

import json
import os

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import TypedDict

    from typing_extensions import NotRequired  # this pass's stdlib typing predates it

    # buildgen/twin_wiring.py's declaration restated for mypy, which cannot reach buildgen from here;
    # tests_scripts/test_twin_wiring_contract.py keeps the two equal.
    class I2CAttachment(TypedDict):
        driver: str
        name_ext: str
        address: int
        irq_pin: NotRequired[int]

    class SpiAttachment(TypedDict):
        driver: str
        name_ext: str
        max_size: int

    class I2CPins(TypedDict):
        scl: int
        sda: int

    class SpiPins(TypedDict):
        sck: int
        mosi: int
        miso: int

    class UartPins(TypedDict):
        tx: int
        rx: int

    class UartPair(TypedDict):
        initiator_bus: str
        responder_bus: str

    class TwinWiringPlan(TypedDict):
        device: str
        buses: dict[str, list[I2CAttachment]]
        spi: dict[str, SpiAttachment]
        pins: dict[str, I2CPins | SpiPins | UartPins]
        uart: UartPair | None
        instances: list[str]


_TREE = "build/generated_src"
_PREFIX = "sensortask_"
_SUFFIX = "_wiring_plan.json"


def device_with(*drivers: str) -> str:
    # The first generated device whose plan wires every named driver.
    searched = generated_devices()
    for device in searched:
        instances = wiring_plan(device)["instances"]
        if all(driver in instances for driver in drivers):
            return device
    raise AssertionError(f"no generated device wires every one of {list(drivers)!r} - searched {searched!r}")


def devices_with_shared_bus() -> "list[tuple[str, str, list[str]]]":
    # Every (device, bus, occupants) whose plan puts two or more chips on one bus, in device then bus order.
    found: list[tuple[str, str, list[str]]] = []
    searched = generated_devices()
    for device in searched:
        buses = wiring_plan(device)["buses"]
        for bus in sorted(buses):
            occupants = [attachment["driver"] for attachment in buses[bus]]
            if len(occupants) >= 2:
                found.append((device, bus, occupants))
    if not found:
        raise AssertionError(f"no generated device puts two chips on one bus - searched {searched!r}")
    return found


def generated_devices() -> "list[str]":
    found = sorted(name[len(_PREFIX) : -len(_SUFFIX)] for name in os.listdir(_TREE) if name.startswith(_PREFIX) and name.endswith(_SUFFIX))
    if not found:
        raise AssertionError(f"no {_PREFIX}<device>{_SUFFIX} in {_TREE} - run: uv run scripts/_generate_sensortask_modules.py")
    return found


def wiring_plan(device: str) -> "TwinWiringPlan":
    with open(_TREE + "/" + _PREFIX + device + _SUFFIX) as f:
        plan: TwinWiringPlan = json.load(f)
    return plan
