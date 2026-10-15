"""Tests for digital_twin/_sgp40_chip.py's replies, resets and faults, plus two cases driving the real
asy_sgp40_driver.py over the twin bus (CRC recovery; VOCState through the blackout)."""

import errno
import sys

sys.path.insert(0, "digital_twin")  # digital_twin/ is not on scripts/test.sh's MICROPYPATH; this file reaches it itself.

import machine
import microtest
from _async_harness import run
from _crc8 import crc8, word
from _fast_sleep import FastAsyncSleep
from _sgp40_chip import SGP40Chip
from _tmp_scratch import TmpScratch
from _twin_common import Walk
from _twin_devices import device_with, wiring_plan
from _twin_random import FixedRandom

import asy_i2c_driver
from asy_base_classes import ValueRef
from asy_sgp40_driver import SGP40_I2C, SGP40_Reader, _DefaultHumiditySource, _DefaultTemperatureSource

_SGP40_ADDRESS = 0x59  # datasheet section 4.2
_BLACKOUT_SAMPLES = 46  # the VOC algorithm's initial blackout, as asy_sgp40_driver.py's VOCState code 0 states
_scratch = TmpScratch("digital_twin_sgp40")
microtest.after_each(machine.reset_test_state)
_MEASURE_RAW_DEFAULT = b"\x26\x0f\x80\x00\xa2\x66\x66\x93"  # measure-raw without compensation, the datasheet's own example


def test_crc8_matches_datasheet_worked_example() -> None:
    assert crc8(b"\xbe\xef") == 0x92


def test_word_appends_correct_crc_trailer() -> None:
    payload = word(0x1234)
    assert payload[:2] == b"\x12\x34"
    assert payload[2] == crc8(b"\x12\x34")


def test_get_serial_number_command_replies_with_word0_zero() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000], getrandbits_values=[0x1234, 0x5678]))
    chip.handle_writeto(b"\x36\x82")
    reply = chip.handle_readfrom_into(9)
    assert reply[0:3] == word(0x0000)
    # Two more CRC-valid words follow - exact content is opaque to the real driver (only word[0]
    # is checked), but must still be well-formed (each SGP40's own CRC over the reply).
    assert reply[5] == crc8(reply[3:5])
    assert reply[8] == crc8(reply[6:8])


def test_self_test_command_replies_pass() -> None:
    chip = SGP40Chip()
    chip.handle_writeto(b"\x28\x0e")
    reply = chip.handle_readfrom_into(3)
    assert reply == word(0xD400)


def test_measure_raw_default_command_replies_with_a_ticks_value_in_range() -> None:
    # First value: the draw at construction. Second: the step delta measure_raw below draws -
    # zeroed so the reply stays exactly at the constructed initial value.
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 0]))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    reply = chip.handle_readfrom_into(3)
    assert reply == word(30000)


def test_measure_raw_steps_from_the_previous_value_on_every_call() -> None:
    # Construction draws 30000; each call below steps by its own fresh delta rather than a
    # fresh independent draw - proving both that the walk is real and that each call gets its own
    # scripted delta (not the same one reused).
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 500, -800]))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    first = chip.handle_readfrom_into(3)
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    second = chip.handle_readfrom_into(3)
    assert first == word(30500)  # 30000 + 500
    assert second == word(29700)  # 30500 + -800
    assert first != second


def test_measure_raw_default_range_stays_inside_the_sgp40_datasheets_own_tick_range() -> None:
    # SRAW_VOC 0-65 535 ticks, SGP40 datasheet Table 1; the twin's walk is a sub-range.
    chip = SGP40Chip()
    assert chip.raw.lo >= 0 and chip.raw.hi <= 65535
    assert chip.raw.lo < chip.raw.hi


def test_custom_range_is_honored() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[100, 0]), raw=Walk(50, 150, 1000))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    reply = chip.handle_readfrom_into(3)
    assert reply == word(100)


def test_construction_draws_an_initial_value_within_range_without_a_measure_raw_command() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[29500]))
    assert chip._raw == 29500


def test_measure_raw_step_is_clamped_to_the_configured_max() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[33800, 1000]), raw=Walk(26000, 34000, 1000))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    reply = chip.handle_readfrom_into(3)
    assert reply == word(34000)  # 33800 + 1000 would be 34800 - clamped to the walk's hi


def test_measure_raw_step_is_clamped_to_the_configured_min() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[26300, -1000]), raw=Walk(26000, 34000, 1000))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    reply = chip.handle_readfrom_into(3)
    assert reply == word(26000)  # 26300 + -1000 would be 25300 - clamped to the walk's lo


def test_raw_step_is_configurable_via_the_constructor() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 50]), raw=Walk(26000, 34000, 50))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)  # would violate the default 1000 bound - proves the override took
    reply = chip.handle_readfrom_into(3)
    assert reply == word(30050)


def test_readfrom_into_returns_exactly_the_requested_length_zero_padded() -> None:
    chip = SGP40Chip()
    chip.handle_writeto(b"\x28\x0e")
    reply = chip.handle_readfrom_into(10)  # more than the 3-byte real reply
    assert len(reply) == 10
    assert reply[:3] == word(0xD400)
    assert reply[3:] == bytes(7)


def test_unrecognized_command_does_not_raise() -> None:
    chip = SGP40Chip()
    chip.handle_writeto(b"\xff\xff")  # not a real SGP40 command
    reply = chip.handle_readfrom_into(3)
    assert len(reply) == 3  # no crash - real hardware would just not respond usefully either


def test_fault_injection_on_writeto() -> None:
    chip = SGP40Chip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "no ACK from device")
    try:
        chip.handle_writeto(b"\x36\x82")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    # Fault only fires once (times=1 default) - the next call must succeed normally.
    chip.handle_writeto(b"\x36\x82")


def test_fault_injection_on_readfrom_into() -> None:
    chip = SGP40Chip()
    chip.handle_writeto(b"\x28\x0e")
    chip.fault.inject_fault("readfrom_into", OSError, errno.EIO, "bus timeout")
    try:
        chip.handle_readfrom_into(3)
        raise AssertionError("expected OSError")
    except OSError:
        pass
    assert chip.handle_readfrom_into(3) == word(0xD400)


def test_fault_injection_can_simulate_a_corrupted_crc_reply() -> None:
    # A real bus disturbance flipping a payload bit is exactly what the real driver's
    # test_initialize_corrupted_response_raises_crc_error/test_get_raw_crc_mismatch_raises guard
    # against - the twin should be able to provoke that same condition on demand.
    chip = SGP40Chip()
    chip.corrupt_next()
    chip.handle_writeto(b"\x28\x0e")
    reply = chip.handle_readfrom_into(3)
    assert reply[2] != crc8(reply[0:2])  # CRC trailer deliberately wrong
    # One-shot: the flag clears itself, next reply is CRC-valid again.
    chip.handle_writeto(b"\x28\x0e")
    reply2 = chip.handle_readfrom_into(3)
    assert reply2[2] == crc8(reply2[0:2])


def test_a_read_fault_keyed_to_the_measure_command_spares_the_self_test_read() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 0]))
    chip.fault.inject_fault("readfrom_into", OSError, errno.EIO, "measure read", match=0x260F)
    chip.handle_writeto(b"\x28\x0e")
    assert chip.handle_readfrom_into(3) == word(0xD400)
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    try:
        chip.handle_readfrom_into(3)
        raise AssertionError("expected the keyed fault on the measure read")
    except OSError as e:
        assert e.errno == errno.EIO
    assert chip.fault.pending("readfrom_into") == 0
    assert chip.handle_readfrom_into(3) == word(30000)


def test_a_general_call_reset_clears_the_pending_reply_and_counts_one_reset() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 0]))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    assert chip._measuring
    chip.handle_general_call(b"\x06")
    assert chip.handle_readfrom_into(3) == bytes(3)
    assert chip.resets == 1
    assert not chip._measuring


def test_a_general_call_with_another_byte_keeps_the_pending_reply() -> None:
    chip = SGP40Chip()
    chip.handle_writeto(b"\x28\x0e")
    chip.handle_general_call(b"\x04")
    assert chip.handle_readfrom_into(3) == word(0xD400)
    assert chip.resets == 0


def test_power_cycle_returns_the_chip_to_idle() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 0]))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    chip.power_cycle()
    assert chip.handle_readfrom_into(3) == bytes(3)
    assert not chip._measuring


def test_heater_off_clears_the_pending_measure_reply_and_the_next_measure_answers() -> None:
    chip = SGP40Chip(random_source=FixedRandom(randint_values=[30000, 0, 0]))
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    chip.handle_writeto(b"\x36\x15")  # datasheet Table 14
    assert chip.handle_readfrom_into(3) == bytes(3)
    assert (chip.heater_offs, chip._measuring) == (1, False)
    chip.handle_writeto(_MEASURE_RAW_DEFAULT)
    assert chip.handle_readfrom_into(3) == word(30000)
    assert (chip.heater_offs, chip._measuring) == (1, True)


def _chip_on(bus_name: str) -> SGP40Chip:
    bus = machine.peripheral(bus_name)
    assert isinstance(bus, machine.I2C)
    chip = bus.devices[_SGP40_ADDRESS]
    assert isinstance(chip, SGP40Chip)
    return chip


def _sgp40_bus() -> "tuple[asy_i2c_driver.I2C, str]":
    # The bus a generated device wires its SGP40 on, built as that device's own plan describes it.
    plan = wiring_plan(device_with("sgp40"))
    machine.reset_peripherals()
    machine.configure_wiring(plan)
    bus = next(name for name, attached in plan["buses"].items() if any(a["driver"] == "sgp40" for a in attached))
    pins = plan["pins"][bus]
    scl, sda = pins.get("scl"), pins.get("sda")
    assert isinstance(scl, int)
    assert isinstance(sda, int)
    return asy_i2c_driver.I2C(int(bus[3:]), scl_pin=scl, sda_pin=sda), bus


def test_the_driver_recovers_from_a_crc_failure_with_the_next_initialize() -> None:
    i2c, bus_name = _sgp40_bus()
    sgp = SGP40_I2C(i2c)

    async def scenario() -> None:
        assert await sgp.setup() is True
        chip = _chip_on(bus_name)
        chip.corrupt_next()
        try:
            await sgp.measure_raw()
            raise AssertionError("expected the driver's CRC error")
        except RuntimeError as e:
            assert "CRC" in str(e), e
        await sgp.initialize()  # the serial reply passes its CRC again

    with FastAsyncSleep():
        run(scenario())


def test_the_real_reader_publishes_vocstate_0_through_the_blackout_then_1() -> None:
    i2c, _bus_name = _sgp40_bus()
    reader = SGP40_Reader(i2c, ValueRef(_DefaultTemperatureSource(), "value"), ValueRef(_DefaultHumiditySource(), "value"), cfg_path=_scratch.dir())

    async def scenario() -> "list[int | None]":
        assert await reader._init_sgp() is True
        states = []
        for _ in range(_BLACKOUT_SAMPLES + 2):
            data, _compensated, _serialize = await reader._read_sgp(None, serialize=False, deserialize=False)
            await reader._store_sgp(data)
            states.append((await reader.get_data()).VOCState)
        return states

    with FastAsyncSleep():
        states = run(scenario())
    assert 0 in states
    first_learning = states.index(1)
    assert states[:first_learning] == [0] * first_learning
    assert states[first_learning:] == [1] * (len(states) - first_learning)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
