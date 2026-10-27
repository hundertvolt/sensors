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


def _constructs(statement: str, driver: str) -> bool:
    # An assignment to the driver's module global: its own name, or the name with "_" and its name extension.
    name = statement.split(" = ", 1)[0]
    return " = " in statement and (name == driver or name.startswith(driver + "_"))


def _identifiers(statement: str) -> "list[str]":
    # The statement's names: every run of letters, digits and "_" in it.
    return "".join(c if c.isalpha() or c.isdigit() or c == "_" else " " for c in statement).split()


def _items(mapping: "I2CAttachment | SpiAttachment | I2CPins | SpiPins | UartPins") -> "list[tuple[str, object]]":
    # A plan mapping as its items in key order: a json-loaded dict's own order is not one to compare by.
    return sorted(mapping.items(), key=lambda item: item[0])


def device_with(*drivers: str) -> str:
    # The first generated device whose plan wires every named driver.
    return devices_with(*drivers)[0]


def devices_with(*drivers: str) -> "list[str]":
    # Every generated device whose plan wires every named driver, in device order; none fails naming the devices searched.
    searched = generated_devices()
    found = [device for device in searched if all(driver in wiring_plan(device)["instances"] for driver in drivers)]
    if not found:
        raise AssertionError(f"no generated device wires every one of {list(drivers)!r} - searched {searched!r}")
    return found


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


def distinct_wirings(*drivers: str) -> "list[str]":
    # One device per distinct wiring_read() of the named drivers (none named: of every instance a device wires), the first
    # of each in device order: identical wirings share its run, any read key differing runs on its own (SPEC E.2.1).
    reads: list[list[object]] = []
    found: list[str] = []
    for device in devices_with(*drivers):
        read = wiring_read(device, *(drivers or wiring_plan(device)["instances"]))
        if read not in reads:
            reads.append(read)
            found.append(device)
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


def wiring_read(device: str, *drivers: str) -> "list[object]":
    # What a scenario on these drivers reads of a device: each one's generated construction statement and every module
    # constant it names (its TOML settings), and for each bus, SPI bus or UART pair one sits on, its pins and occupants.
    plan = wiring_plan(device)
    with open(_TREE + "/" + _PREFIX + device + ".py") as f:
        lines = [line.strip() for line in f]
    read: list[object] = [statement for statement in lines if any(_constructs(statement, driver) for driver in drivers)]
    named = {name for statement in read for name in _identifiers(str(statement)) if name[:1] == "_"}
    read += [line for line in lines if " = " in line and line.split(" = ", 1)[0].split(":", 1)[0] in named]
    for bus in sorted(plan["buses"]):
        if any(a["driver"] in drivers for a in plan["buses"][bus]):
            read.append((bus, _items(plan["pins"][bus]), [_items(a) for a in plan["buses"][bus]]))
    for bus in sorted(plan["spi"]):
        if plan["spi"][bus]["driver"] in drivers:
            read.append((bus, _items(plan["pins"][bus]), _items(plan["spi"][bus])))
    uart = plan["uart"]
    if uart is not None and "uart_link" in drivers:
        read.append([(bus, _items(plan["pins"][bus])) for bus in (uart["initiator_bus"], uart["responder_bus"])])
    return read
