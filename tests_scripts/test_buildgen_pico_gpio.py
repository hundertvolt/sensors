"""Tests for buildgen.pico_gpio, the Pico W's GPIO role tables (SPECIFICATION.md Part L.6.5): the tables against
MicroPython's own pin checks, and through build_model() every newly legal bus pin building while a role-transposed
pair and a wireless-reserved GPIO are refused."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _toml_fixtures import base_doc, instance_of, table_at, with_uart_pair, write_doc

from buildgen.errors import BuildError
from buildgen.pico_gpio import I2C_ROLE, SPI_ROLE, UART_ROLE, WIRELESS_RESERVED_GPIOS
from buildgen.validate import build_model

if TYPE_CHECKING:
    from _toml_fixtures import TomlDoc

    from buildgen.model import DeviceModel

_SPI1_HIGH = {"sck_pin": 26, "mosi_pin": 27, "miso_pin": 28}
_UART1_HIGH = {"tx_pin": 20, "rx_pin": 21}


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _build(tmp_path: Path, src_dir: Path, doc: "TomlDoc") -> "DeviceModel":
    return build_model(write_doc(tmp_path, "fixture", doc), src_dir)


def _with_bus_pins(doc: "TomlDoc", bus: str, pins: "dict[str, int]") -> "TomlDoc":
    # base_doc() with `bus` wired to `pins` and a user moved onto it, every partner pin unclaimed.
    if bus.startswith("uart"):
        doc = with_uart_pair(doc)
        table_at(doc, "bus", bus).update(pins)
    elif bus == "i2c0":
        table_at(doc, "bus", "i2c0").update(pins)
    elif bus == "i2c1":
        table_at(doc, "bus")["i2c1"] = {**pins, "frequency": 50000}
        instance_of(doc, "sgp40")["bus"] = "i2c1"
    else:
        del table_at(doc, "bus")["spi0"]
        table_at(doc, "bus")[bus] = {**pins}
        instance_of(doc, "fram")["bus"] = bus
    return doc


def test_pin_table_agrees_with_micropython_pin_macros() -> None:
    # An independent source, MicroPython's pin checks at v1.29.0: ports/rp2/machine_i2c.h:65-66, machine_spi.c:89-95
    # and machine_uart.c:71-77 (the RP2040 branch). The four wireless GPIOs are never offered.
    for pin in range(30):
        if pin in WIRELESS_RESERVED_GPIOS:
            assert all(pin not in table for table in (I2C_ROLE, SPI_ROLE, UART_ROLE)), pin
            continue
        assert I2C_ROLE[pin] == (f"i2c{(pin & 2) >> 1}", "scl" if pin & 1 else "sda"), pin
        spi_role = {0: "miso", 2: "sck", 3: "mosi"}.get(pin & 3)
        assert SPI_ROLE.get(pin) == (None if spi_role is None else (f"spi{(pin & 8) >> 3}", spi_role)), pin
        uart_role = {0: "tx", 1: "rx"}.get(pin & 3)
        assert UART_ROLE.get(pin) == (None if uart_role is None else (f"uart{((pin + 4) & 8) >> 3}", uart_role)), pin


@pytest.mark.parametrize(
    ("bus", "field", "pin", "pins"),
    [
        ("i2c1", "sda_pin", 22, {"sda_pin": 22, "scl_pin": 27}),
        ("i2c0", "sda_pin", 28, {"sda_pin": 28, "scl_pin": 13}),
        ("spi0", "miso_pin", 20, {"sck_pin": 2, "mosi_pin": 3, "miso_pin": 20}),
        ("spi0", "sck_pin", 22, {"sck_pin": 22, "mosi_pin": 3, "miso_pin": 4}),
        ("spi1", "sck_pin", 26, _SPI1_HIGH),
        ("spi1", "mosi_pin", 27, _SPI1_HIGH),
        ("spi1", "miso_pin", 28, _SPI1_HIGH),
        ("uart1", "tx_pin", 20, _UART1_HIGH),
        ("uart1", "rx_pin", 21, _UART1_HIGH),
        ("uart0", "tx_pin", 28, {"tx_pin": 28, "rx_pin": 17}),
    ],
)
def test_newly_legal_pin_is_accepted(tmp_path: Path, src_dir: Path, bus: str, field: str, pin: int, pins: "dict[str, int]") -> None:
    # RP2040 datasheet Table 279 offers each of these on the Pico W's user GPIOs; the old pair tables left them out.
    model = _build(tmp_path, src_dir, _with_bus_pins(base_doc(), bus, dict(pins)))
    buses = model.doc["bus"]
    assert isinstance(buses, dict)
    table = buses[bus]
    assert isinstance(table, dict) and table[field] == pin


def test_i2c_pin_role_transposed_rejected(tmp_path: Path, src_dir: Path) -> None:
    # SPECIFICATION.md Part L.6.5's role check: both pins are real, legal GP12/13 for i2c0 - swapped.
    doc = base_doc()
    table_at(doc, "bus", "i2c0")["scl_pin"] = 12
    table_at(doc, "bus", "i2c0")["sda_pin"] = 13
    with pytest.raises(BuildError, match="pins transposed"):
        _build(tmp_path, src_dir, doc)


def test_spi_pin_role_transposed_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    table_at(doc, "bus", "spi0")["sck_pin"] = 3  # real SPI0 pin, but MOSI's, not SCK's
    table_at(doc, "bus", "spi0")["mosi_pin"] = 2  # SCK's
    with pytest.raises(BuildError, match="pins transposed"):
        _build(tmp_path, src_dir, doc)


def test_uart_pin_role_transposed_rejected(tmp_path: Path, src_dir: Path) -> None:
    # uart0's own pair is (16, 17) = (tx, rx) - swapping them puts the real RX pin in the TX slot.
    doc = with_uart_pair(base_doc())
    table_at(doc, "bus", "uart0")["tx_pin"], table_at(doc, "bus", "uart0")["rx_pin"] = 17, 16
    with pytest.raises(BuildError, match=r"bus\.uart0\.tx_pin=GP17 is uart0's RX pin, not its TX pin - pins transposed\?"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize(("field", "value"), [("irq_pin", 24), ("pin", 25), ("cs_pin", 23)])
def test_wireless_reserved_gpio_rejected_on_any_pin_field(tmp_path: Path, src_dir: Path, field: str, value: int) -> None:
    # GP23/24/25/29 - SPECIFICATION.md Part L.6.5 applies to every claimed pin device-wide, not just
    # bus wire pins (irq_pin/pin/cs_pin here have no peripheral role to check, only existence).
    doc = base_doc()
    if field == "irq_pin":
        table_at(doc, "instance", 0)[field] = value  # scd30
    elif field == "pin":
        table_at(doc, "instance", 3)[field] = value  # neopixel
    else:
        table_at(doc, "instance", 2)[field] = value  # fram
    with pytest.raises(BuildError, match="not a usable Pico W GPIO"):
        _build(tmp_path, src_dir, doc)
