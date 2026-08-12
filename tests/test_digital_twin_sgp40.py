"""Deterministic unit tests for digital_twin/_sgp40_chip.py's own transaction-response logic -
answers the exact raw I2C command/reply shapes tests/test_asy_sgp40_driver.py's fixtures already
lock in for the real driver (see that file's queue_successful_init()/measure_raw() assertions),
but generated instead of hand-scripted. No real machine.I2C/asy_sgp40_driver involved here - this
tests Sgp40Chip in isolation, matching this step's "deterministic tests of the twin's own
transaction responses" criterion (FINAL_WIRING_PLAN.md's Step 3).
"""

import sys

# digital_twin/ isn't on scripts/test.sh's own MICROPYPATH ("src:tests:.frozen") - deliberately
# kept separate from the unit-test set (FINAL_WIRING_PLAN.md's Step 3). Extending sys.path at
# runtime, scoped to this one file, reaches it without touching scripts/test.sh/MICROPYPATH at all
# - same confirmed-safe pattern as test_setter_microdot_integration.py's own ext/ insertion.
sys.path.insert(0, "digital_twin")

from _crc8 import crc8, word  # noqa: E402
from _sgp40_chip import Sgp40Chip  # noqa: E402


class _FixedRandom:
    # Deterministic stand-in for the real `random` module's subset Sgp40Chip actually calls -
    # scripted return values, one per call, in order.
    def __init__(self, randint_values: "list[int] | None" = None, getrandbits_values: "list[int] | None" = None) -> None:
        self._randint_values = list(randint_values or [])
        self._getrandbits_values = list(getrandbits_values or [])

    def randint(self, a: int, b: int) -> int:
        assert self._randint_values, "randint() called more times than scripted"
        value = self._randint_values.pop(0)
        assert a <= value <= b, f"scripted value {value} outside requested range [{a},{b}]"
        return value

    def getrandbits(self, k: int) -> int:
        assert self._getrandbits_values, "getrandbits() called more times than scripted"
        value = self._getrandbits_values.pop(0)
        assert 0 <= value < (1 << k)
        return value


def test_crc8_matches_datasheet_worked_example() -> None:
    assert crc8(b"\xbe\xef") == 0x92


def test_word_appends_correct_crc_trailer() -> None:
    payload = word(0x1234)
    assert payload[:2] == b"\x12\x34"
    assert payload[2] == crc8(b"\x12\x34")


def test_get_serial_number_command_replies_with_word0_zero() -> None:
    chip = Sgp40Chip(random_source=_FixedRandom(getrandbits_values=[0x1234, 0x5678]))
    chip.handle_writeto(b"\x36\x82")
    reply = chip.handle_readfrom_into(9)
    assert reply[0:3] == word(0x0000)
    # Two more CRC-valid words follow - exact content is opaque to the real driver (only word[0]
    # is checked), but must still be well-formed (each SGP40's own CRC over the reply).
    assert reply[5] == crc8(reply[3:5])
    assert reply[8] == crc8(reply[6:8])


def test_self_test_command_replies_pass() -> None:
    chip = Sgp40Chip()
    chip.handle_writeto(b"\x28\x0e")
    reply = chip.handle_readfrom_into(3)
    assert reply == word(0xD400)


def test_measure_raw_default_command_replies_with_a_ticks_value_in_range() -> None:
    chip = Sgp40Chip(random_source=_FixedRandom(randint_values=[30000]))
    chip.handle_writeto(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")  # datasheet's own no-compensation example
    reply = chip.handle_readfrom_into(3)
    assert reply == word(30000)


def test_measure_raw_draws_a_fresh_value_on_every_call() -> None:
    chip = Sgp40Chip(random_source=_FixedRandom(randint_values=[28000, 31500]))
    chip.handle_writeto(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")
    first = chip.handle_readfrom_into(3)
    chip.handle_writeto(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")
    second = chip.handle_readfrom_into(3)
    assert first == word(28000)
    assert second == word(31500)


def test_measure_raw_default_range_stays_inside_the_sgp40_datasheets_own_tick_range() -> None:
    # SRAW_VOC is documented as 0-65'535 ticks (datasheets/sgp40, Table 1) - the twin's own default
    # range must be a sensible sub-range of that, not the datasheet's full extremes.
    chip = Sgp40Chip()
    assert 0 <= chip._min_raw and chip._max_raw <= 65535
    assert chip._min_raw < chip._max_raw


def test_custom_range_is_honored() -> None:
    chip = Sgp40Chip(random_source=_FixedRandom(randint_values=[100]), min_raw=50, max_raw=150)
    chip.handle_writeto(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")
    reply = chip.handle_readfrom_into(3)
    assert reply == word(100)


def test_readfrom_into_returns_exactly_the_requested_length_zero_padded() -> None:
    chip = Sgp40Chip()
    chip.handle_writeto(b"\x28\x0e")
    reply = chip.handle_readfrom_into(10)  # more than the 3-byte real reply
    assert len(reply) == 10
    assert reply[:3] == word(0xD400)
    assert reply[3:] == bytes(7)


def test_unrecognized_command_does_not_raise() -> None:
    chip = Sgp40Chip()
    chip.handle_writeto(b"\xff\xff")  # not a real SGP40 command
    reply = chip.handle_readfrom_into(3)
    assert len(reply) == 3  # no crash - real hardware would just not respond usefully either


def test_fault_injection_on_writeto() -> None:
    chip = Sgp40Chip()
    chip.fault.inject_fault("writeto", OSError(5, "no ACK from device"))
    try:
        chip.handle_writeto(b"\x36\x82")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    # Fault only fires once (times=1 default) - the next call must succeed normally.
    chip.handle_writeto(b"\x36\x82")


def test_fault_injection_on_readfrom_into() -> None:
    chip = Sgp40Chip()
    chip.handle_writeto(b"\x28\x0e")
    chip.fault.inject_fault("readfrom_into", OSError(5, "bus timeout"))
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
    chip = Sgp40Chip(corrupt_next_reply=True)
    chip.handle_writeto(b"\x28\x0e")
    reply = chip.handle_readfrom_into(3)
    assert reply[2] != crc8(reply[0:2])  # CRC trailer deliberately wrong
    # One-shot: the flag clears itself, next reply is CRC-valid again.
    chip.handle_writeto(b"\x28\x0e")
    reply2 = chip.handle_readfrom_into(3)
    assert reply2[2] == crc8(reply2[0:2])


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
