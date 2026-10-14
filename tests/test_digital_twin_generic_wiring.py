"""Unit tests for digital_twin/machine.py's generalized wiring engine (configure_wiring()) - SPECIFICATION.md Part L.4.
Bus-level Pin/I2C/SPI fake behavior itself is already covered by test_digital_twin_machine.py; this file is scoped to the wiring-plan-to-chip-fake construction mechanism only."""

import json
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from _fram_chip import FRAMChip

    T = TypeVar("T")

# digital_twin/ must precede tests/ here - see test_digital_twin_machine.py's own identical comment.
sys.path.insert(0, "digital_twin")

import machine
import microtest
from _async_harness import run
from _bmp3xx_chip import BMP3XXChip
from _error_codes import code
from _isl29125_chip import ISL29125Chip
from _scd30_chip import SCD30Chip
from _sgp40_chip import SGP40Chip
from _tmp_scratch import TmpScratch
from _twin_devices import generated_devices, wiring_plan
from machine import I2C, SPI, Pin

from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig
from asy_spi_driver import SPI as DriverSPI

_CHIP_CLASSES: "dict[str, type]" = {"scd30": SCD30Chip, "sgp40": SGP40Chip, "bmp3xx": BMP3XXChip, "isl29125": ISL29125Chip}
_I2C0 = {"scl": 13, "sda": 12}  # rp2-valid I2C0 pins (boards/rp2040_af.csv)
_I2C1 = {"scl": 15, "sda": 14}  # rp2-valid I2C1 pins
_SPI0 = {"sck": 2, "mosi": 3, "miso": 4}  # rp2-valid SPI0 pins

_scratch = TmpScratch("dt_generic_wiring")
microtest.after_each(machine.reset_test_state)


def _built(make: "Callable[[], T]") -> "T":
    # Builds inside one harness run: an SCD30 chip's own refresh timer runs as a task, ended with the run.
    async def build() -> "T":
        return make()

    return run(build())


def _custom_plan() -> "dict[str, object]":
    return {
        "buses": {"i2c0": [{"driver": "scd30", "name_ext": "", "address": 0x61, "irq_pin": 6}]},
        "spi": {},
        "pins": {"i2c0": _I2C0},
    }


def _fram_plan(max_size: int) -> "dict[str, object]":
    return {"buses": {}, "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": max_size}}, "pins": {"spi0": _SPI0}}


def _pending_rdid(chip: "FRAMChip") -> "bytes | None":
    # The chip's one-shot RDID answer as it stands now, read after the setup that should have consumed it.
    return chip.rdid_once


def _spi0() -> "SPI":
    return SPI(0, sck=Pin(_SPI0["sck"]), mosi=Pin(_SPI0["mosi"]), miso=Pin(_SPI0["miso"]))


# ---------------------------------------------------------------------------
# configure_wiring() - the generic, plan-driven mechanism
# ---------------------------------------------------------------------------


def test_configure_wiring_rejects_a_plan_missing_buses_key() -> None:
    machine.reset_peripherals()
    try:
        machine.configure_wiring({"spi": {}})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_configure_wiring_rejects_a_plan_missing_spi_key() -> None:
    machine.reset_peripherals()
    try:
        machine.configure_wiring({"buses": {}})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_constructing_a_bus_with_no_plan_raises() -> None:
    # No default board: a bus constructed before any configure_wiring() is refused, never wired from a guess.
    machine.reset_peripherals()
    try:
        _built(lambda: I2C(0, scl=Pin(_I2C0["scl"]), sda=Pin(_I2C0["sda"]), freq=50000))
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "no wiring plan" in str(e), e


def test_configure_wiring_wires_a_single_i2c_device_at_its_plan_address() -> None:
    machine.reset_peripherals()
    machine.configure_wiring(_custom_plan())
    i2c = _built(lambda: I2C(0, scl=Pin(_I2C0["scl"]), sda=Pin(_I2C0["sda"]), freq=50000))
    assert i2c.scan() == [0x61]


def test_configure_wiring_wires_multiple_devices_sharing_one_bus() -> None:
    machine.reset_peripherals()
    plan = {
        "buses": {"i2c1": [{"driver": "sgp40", "name_ext": "", "address": 0x59}, {"driver": "bmp3xx", "name_ext": "", "address": 0x76}]},
        "spi": {},
        "pins": {"i2c1": _I2C1},
    }
    machine.configure_wiring(plan)
    i2c = _built(lambda: I2C(1, scl=Pin(_I2C1["scl"]), sda=Pin(_I2C1["sda"]), freq=50000))
    assert i2c.scan() == [0x59, 0x76]


def test_configure_wiring_leaves_an_unlisted_bus_empty() -> None:
    machine.reset_peripherals()
    machine.configure_wiring(_custom_plan())  # only declares i2c0
    i2c1 = _built(lambda: I2C(1, scl=Pin(_I2C1["scl"]), sda=Pin(_I2C1["sda"]), freq=50000))
    assert i2c1.scan() == []


def test_configure_wiring_uses_the_plans_own_irq_pin_for_scd30() -> None:
    # The plan above uses irq_pin=6 (no device's own 8 or 11) - proves the value is threaded through from the plan itself.
    machine.reset_peripherals()
    machine.configure_wiring(_custom_plan())
    _built(lambda: I2C(0, scl=Pin(_I2C0["scl"]), sda=Pin(_I2C0["sda"]), freq=50000))
    assert 6 in Pin._registry
    assert 8 not in Pin._registry


def test_configure_wiring_rejects_an_unknown_driver() -> None:
    machine.reset_peripherals()
    plan = {"buses": {"i2c0": [{"driver": "not_a_real_chip", "name_ext": "", "address": 0x10}]}, "spi": {}, "pins": {"i2c0": _I2C0}}
    machine.configure_wiring(plan)
    try:
        _built(lambda: I2C(0, scl=Pin(_I2C0["scl"]), sda=Pin(_I2C0["sda"]), freq=50000))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_fram_rdid_follows_the_plans_size() -> None:
    # One case per size the twin's RDID table knows (each row cites its datasheet page there).
    for max_size, rdid in machine._FRAM_RDID_BY_MAX_SIZE.items():
        machine.reset_peripherals()
        machine.configure_wiring(_fram_plan(max_size))
        spi = _spi0()
        assert spi.device is not None, max_size
        assert (spi.device.size, spi.device.rdid_response) == (max_size, rdid), (hex(max_size), spi.device.rdid_response)


def test_unknown_fram_size_raises() -> None:
    machine.reset_peripherals()
    machine.configure_wiring(_fram_plan(0x4000))  # 16 KB: no row in the RDID table
    try:
        _spi0()
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "no FRAM RDID for size" in str(e), e


def test_configure_wiring_leaves_spi_bus_unwired_when_plan_has_no_spi_entry() -> None:
    machine.reset_peripherals()
    machine.configure_wiring(_custom_plan())  # empty "spi"
    assert _spi0().device is None


def test_one_shot_bad_rdid_then_good() -> None:
    # The driver's bounded identification retry over the twin chip: one all-zero answer, then the real one; the setup
    # succeeds and leaves one W FRAM_ID_RETRIED.
    machine.reset_peripherals()
    machine.configure_wiring(_fram_plan(0x2000))
    manager = FRAMManager(DriverSPI(0, _SPI0["sck"], _SPI0["mosi"], _SPI0["miso"]), 1, max_size=0x2000, log=LogConfig(None, 10, None))
    chip = manager.fram._spidev.spi._spi.device if manager.fram._spidev.spi._spi is not None else None
    assert chip is not None
    chip.rdid_once = bytes(4)
    assert run(manager.setup()) is True
    assert manager.fram.initialized is True
    assert _pending_rdid(chip) is None, "the one-shot answer was never consumed"
    log = run(manager.fram.pr.get_log())[manager.fram.pr.name]
    assert [log["ErrNum"][i] for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "W"] == [code("W", "FRAM_ID_RETRIED")], log


def test_each_generated_device_boots_its_plans_attachments() -> None:
    # Every generated plan: each bus it lists, constructed on its own pins, carries exactly the plan's chips, each the
    # fake class its driver names; its FRAM the plan's size.
    for device in generated_devices():
        plan = wiring_plan(device)
        machine.reset_peripherals()
        machine.configure_wiring(plan)
        for bus, attachments in sorted(plan["buses"].items()):
            pins = plan["pins"][bus]

            def construct(bus: str = bus, scl: int = pins["scl"], sda: int = pins["sda"]) -> I2C:  # type: ignore[typeddict-item]  # an I2C bus's pins
                return I2C(int(bus[3:]), scl=Pin(scl), sda=Pin(sda), freq=50000)

            i2c = _built(construct)
            assert machine.peripheral(bus) is i2c, (device, bus)
            assert sorted(i2c.devices) == sorted(a["address"] for a in attachments), (device, bus, sorted(i2c.devices))
            for attachment in attachments:
                chip = i2c.devices[attachment["address"]]
                assert type(chip) is _CHIP_CLASSES[attachment["driver"]], (device, bus, attachment, type(chip))
        for bus, spi_attachment in sorted(plan["spi"].items()):
            pins = plan["pins"][bus]
            spi = SPI(int(bus[3:]), sck=Pin(pins["sck"]), mosi=Pin(pins["mosi"]), miso=Pin(pins["miso"]))  # type: ignore[typeddict-item]  # an SPI bus's pins
            assert spi.device is not None and spi.device.size == spi_attachment["max_size"], (device, bus)


def _two_scd30_one_fram_plan() -> "dict[str, object]":
    return {
        "buses": {
            "i2c0": [{"driver": "scd30", "name_ext": "a", "address": 0x61, "irq_pin": 6}],
            "i2c1": [{"driver": "scd30", "name_ext": "b", "address": 0x61, "irq_pin": 7}],
        },
        "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x2000}},
        "pins": {"i2c0": _I2C0, "i2c1": _I2C1, "spi0": _SPI0},
    }


def test_flush_scd30_persists_only_the_last_constructed_chip() -> None:
    # One state file per twin: of two SCD30s, the one constructed last is the one flush_scd30() saves.
    path = _scratch.path("scd30_state.json")
    machine.reset_peripherals()
    machine.configure_scd30_state_path(path)
    machine.configure_wiring(_two_scd30_one_fram_plan())
    first = _built(lambda: I2C(0, scl=Pin(_I2C0["scl"]), sda=Pin(_I2C0["sda"]), freq=50000)).devices[0x61]
    last = _built(lambda: I2C(1, scl=Pin(_I2C1["scl"]), sda=Pin(_I2C1["sda"]), freq=50000)).devices[0x61]
    first._measurement_interval_s, last._measurement_interval_s = 7, 9
    machine.flush_scd30()
    with open(path) as f:
        assert json.load(f)["measurement_interval_s"] == 9, "flush_scd30() saved another chip than the last constructed"


def test_flush_fram_writes_the_one_fram() -> None:
    path = _scratch.path("fram_state.json")
    machine.reset_peripherals()
    machine.configure_fram_state_path(path)
    machine.configure_wiring(_two_scd30_one_fram_plan())
    chip = _spi0().device
    assert chip is not None
    chip.memory[0x10:0x14] = bytearray(b"\x01\x02\x03\x04")
    machine.flush_fram()
    machine.reset_peripherals()
    reloaded = _spi0().device  # a new board over the same state path: the saved image loads
    assert reloaded is not None and reloaded is not chip
    assert bytes(reloaded.memory[0x10:0x14]) == b"\x01\x02\x03\x04", "flush_fram() did not write the plan's one FRAM"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
