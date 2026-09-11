"""Unit tests for digital_twin/machine.py's generalized wiring engine (configure_wiring()) and its "wozi"/"dev" legacy sugar (configure_i2c_wiring()) - BUILD_CHAIN_PLAN.md's Session 5 write-up.
Bus-level Pin/I2C/SPI fake behavior itself is already covered by test_digital_twin_machine.py; this file is scoped to the wiring-plan-to-chip-fake construction mechanism only."""

import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

# digital_twin/ must precede tests/ here - see test_digital_twin_machine.py's own identical comment.
sys.path.insert(0, "digital_twin")

import machine
from machine import I2C, SPI, Pin

_DEV_FRAM_RDID = bytes([0x04, 0x7F, 0x48, 0x03])
_DEFAULT_FRAM_RDID = bytes([0x04, 0x7F, 0x03, 0x02])  # _fram_chip.py's own _DEFAULT_RDID (MB85RS64V)


def _custom_plan() -> "dict[str, Any]":
    return {
        "buses": {"i2c0": [{"driver": "scd30", "name_ext": "", "address": 0x61, "irq_pin": 6}]},
        "spi": {},
    }


# ---------------------------------------------------------------------------
# configure_wiring() - the generic, plan-driven mechanism
# ---------------------------------------------------------------------------


def test_configure_wiring_rejects_a_plan_missing_buses_key() -> None:
    try:
        machine.configure_wiring({"spi": {}})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_configure_wiring_rejects_a_plan_missing_spi_key() -> None:
    try:
        machine.configure_wiring({"buses": {}})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_configure_wiring_wires_a_single_i2c_device_at_its_plan_address() -> None:
    Pin.reset_registry()
    machine.configure_wiring(_custom_plan())
    i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    assert i2c.scan() == [0x61]


def test_configure_wiring_wires_multiple_devices_sharing_one_bus() -> None:
    Pin.reset_registry()
    plan = {
        "buses": {"i2c1": [{"driver": "sgp40", "name_ext": "", "address": 0x59}, {"driver": "bmp3xx", "name_ext": "", "address": 0x76}]},
        "spi": {},
    }
    machine.configure_wiring(plan)
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    assert i2c.scan() == [0x59, 0x76]


def test_configure_wiring_leaves_an_unlisted_bus_empty() -> None:
    Pin.reset_registry()
    machine.configure_wiring(_custom_plan())  # only declares i2c0
    i2c1 = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    assert i2c1.scan() == []


def test_configure_wiring_uses_the_plans_own_irq_pin_for_scd30() -> None:
    # The plan above uses irq_pin=6 (not wozi's 8 or dev's 11) - proves the value is threaded
    # through from the plan itself, not still hardcoded per-profile.
    Pin.reset_registry()
    machine.configure_wiring(_custom_plan())
    I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    assert 6 in Pin._registry
    assert 8 not in Pin._registry


def test_configure_wiring_rejects_an_unknown_driver() -> None:
    Pin.reset_registry()
    plan = {"buses": {"i2c0": [{"driver": "not_a_real_chip", "name_ext": "", "address": 0x10}]}, "spi": {}}
    machine.configure_wiring(plan)
    try:
        I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_configure_wiring_wires_fram_with_the_plans_own_max_size() -> None:
    Pin.reset_registry()
    plan = {"buses": {}, "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x4000}}}
    machine.configure_wiring(plan)
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    assert spi.device is not None
    assert spi.device.size == 0x4000
    assert spi.device.rdid_response == _DEFAULT_FRAM_RDID  # not dev's 256KB size - default RDID


def test_configure_wiring_wires_fram_with_devs_own_rdid_for_devs_own_size() -> None:
    Pin.reset_registry()
    plan = {"buses": {}, "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x40000}}}
    machine.configure_wiring(plan)
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    assert spi.device is not None
    assert spi.device.size == 0x40000
    assert spi.device.rdid_response == _DEV_FRAM_RDID


def test_configure_wiring_leaves_spi_bus_unwired_when_plan_has_no_spi_entry() -> None:
    Pin.reset_registry()
    machine.configure_wiring(_custom_plan())  # empty "spi"
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    assert spi.device is None


# ---------------------------------------------------------------------------
# configure_i2c_wiring() - "wozi"/"dev" legacy sugar over configure_wiring(), regression-checked
# against the exact behavior the old hardcoded 2-profile _wire_i2c_devices()/_wire_spi_device()
# produced (BUILD_CHAIN_PLAN.md's Session 5 write-up).
# ---------------------------------------------------------------------------


def test_configure_i2c_wiring_rejects_an_unknown_profile() -> None:
    try:
        machine.configure_i2c_wiring("not-a-real-profile")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_configure_i2c_wiring_wozi_matches_the_documented_layout() -> None:
    Pin.reset_registry()
    machine.configure_i2c_wiring("wozi")
    i2c0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    i2c1 = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    spi0 = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    assert i2c0.scan() == [0x61]  # SCD30 alone
    assert i2c1.scan() == [0x59, 0x77]  # SGP40 + BMP3xx sharing the bus
    assert spi0.device is not None
    assert spi0.device.size == 0x2000
    assert spi0.device.rdid_response == _DEFAULT_FRAM_RDID


def test_configure_i2c_wiring_dev_matches_the_documented_layout() -> None:
    Pin.reset_registry()
    machine.configure_i2c_wiring("dev")
    i2c0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    i2c1 = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000)
    spi0 = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    assert i2c0.scan() == [0x77]  # BMP3xx alone
    assert i2c1.scan() == [0x59, 0x61]  # SCD30 + SGP40 sharing the bus
    assert spi0.device is not None
    assert spi0.device.size == 0x40000
    assert spi0.device.rdid_response == _DEV_FRAM_RDID


def test_configure_i2c_wiring_dev_uses_scd30_irq_pin_11_not_wozis_8() -> None:
    Pin.reset_registry()
    machine.configure_i2c_wiring("dev")
    I2C(1, scl=Pin(15), sda=Pin(14), freq=50000)  # dev's SCD30 sits on i2c1
    assert 11 in Pin._registry
    assert 8 not in Pin._registry


def test_configure_i2c_wiring_wozi_uses_scd30_irq_pin_8_not_devs_11() -> None:
    Pin.reset_registry()
    machine.configure_i2c_wiring("wozi")
    I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)  # wozi's SCD30 sits on i2c0
    assert 8 in Pin._registry
    assert 11 not in Pin._registry


def test_default_wiring_before_any_configure_call_is_wozi() -> None:
    # Regression check for the old module-level `_i2c_wiring_profile = "wozi"` default - the very
    # first test function to run in a fresh Unix-port process (before any other test's
    # configure_i2c_wiring()/configure_wiring() call) must still see wozi's own layout, matching
    # every caller that never calls either function at all (run_wozi_integration.py's own main()).
    # Re-asserted here explicitly (not just relied upon via test order) since machine._wiring_plan
    # is process-global state that later tests' configure_*() calls mutate.
    machine.configure_i2c_wiring("wozi")  # restore the default explicitly - this test must not
    # depend on running before every other test in this file for its own assertion to hold.
    Pin.reset_registry()
    i2c0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    assert i2c0.scan() == [0x61]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
