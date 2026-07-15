import asyncio
import struct

from machine import I2C as FakeI2C

from asy_i2c_driver import I2C, I2CDevice

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_i2c() -> I2C:
    return I2C(0, scl_pin=1, sda_pin=0, frequency=100000)


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# init / deinit - real hardware deinit(), not just dropping the reference
# ---------------------------------------------------------------------------


def test_deinit_calls_real_hardware_deinit() -> None:
    i2c = make_i2c()
    mock = fake(i2c)
    i2c.deinit()
    assert mock.deinit_called is True
    assert i2c._i2c is None


def test_reinit_deinits_the_previous_bus_first() -> None:
    i2c = make_i2c()
    first = fake(i2c)
    i2c.init(0, scl_pin=1, sda_pin=0, frequency=100000)
    assert first.deinit_called is True
    assert fake(i2c) is not first


def test_operations_after_deinit_return_none_or_noop() -> None:
    i2c = make_i2c()
    i2c.deinit()
    assert i2c.scan() is None
    assert i2c.writeto(0x50, b"x") is None
    assert i2c.get_bits(0x50, 1, 0x00, 0) is None
    assert i2c.get_register_struct(0x50, 0x00, ">H") is None
    i2c.readfrom_into(0x50, bytearray(2))  # no-op, must not raise
    i2c.set_bits(0x50, 1, 0x00, 0, 1)  # no-op, must not raise
    i2c.set_register_struct(0x50, 0x00, ">H", 1)  # no-op, must not raise


# ---------------------------------------------------------------------------
# scan / readfrom_into / writeto
# ---------------------------------------------------------------------------


def test_scan_reports_addresses_with_registers_minus_nak() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x10, 0x00)] = bytearray(1)
    fake(i2c).registers[(0x20, 0x00)] = bytearray(1)
    fake(i2c).nak_addresses.add(0x20)
    assert i2c.scan() == [0x10]


def test_writeto_returns_ack_count_and_accepts_str() -> None:
    i2c = make_i2c()
    assert i2c.writeto(0x50, b"abc") == 3
    assert i2c.writeto(0x50, "abc") == 3
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"abc", True)


def test_readfrom_into_and_writeto_respect_start_end_slice() -> None:
    i2c = make_i2c()
    buf = bytearray(b"\x00\x00\x00\x00")
    i2c.readfrom_into(0x50, buf, start=1, end=3)
    assert fake(i2c).log[-1][0] == "readfrom_into"
    i2c.writeto(0x50, b"XYZ", start=1, end=3)
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"YZ", True)


def test_writeto_then_readfrom_forwards_both() -> None:
    i2c = make_i2c()
    i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2))
    ops = [entry[0] for entry in fake(i2c).log]
    assert ops == ["writeto", "readfrom_into"]


def test_real_bus_failure_propagates_as_oserror() -> None:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x77)
    try:
        i2c.writeto(0x77, b"x")
        raised = False
    except OSError:
        raised = True
    assert raised
    try:
        i2c.scan()  # scan() itself doesn't touch a single address, must not raise
    except OSError:
        raise AssertionError("scan() must not raise for an unrelated nak'd address") from None


# ---------------------------------------------------------------------------
# get_bits / set_bits - bit-field round trips and range guards
# ---------------------------------------------------------------------------


def test_get_set_bits_round_trip_single_byte() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 3, 0x10, 2, 0x5, reg_width=1)
    assert i2c.get_bits(0x50, 3, 0x10, 2, reg_width=1) == 0x5


def test_get_set_bits_round_trip_multi_byte_lsb_first() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 4, 0x10, 4, 0xA, reg_width=2, lsb_first=True)
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0xA0, 0x00])
    assert i2c.get_bits(0x50, 4, 0x10, 4, reg_width=2, lsb_first=True) == 0xA


def test_get_set_bits_round_trip_multi_byte_msb_first() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 4, 0x10, 4, 0xA, reg_width=2, lsb_first=False)
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0x00, 0xA0])
    assert i2c.get_bits(0x50, 4, 0x10, 4, reg_width=2, lsb_first=False) == 0xA


def test_get_bits_leaves_surrounding_bits_untouched() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x10)] = bytearray([0xFF])
    i2c.set_bits(0x50, 3, 0x10, 2, 0x0, reg_width=1)  # clear only bits 2-4
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0b11100011])


def test_get_bits_rejects_out_of_range_bitfield() -> None:
    i2c = make_i2c()
    assert i2c.get_bits(0x50, 0, 0x10, 0, reg_width=1) is None  # num_bits <= 0
    assert i2c.get_bits(0x50, 1, 0x10, -1, reg_width=1) is None  # start_bit < 0
    assert i2c.get_bits(0x50, 4, 0x10, 6, reg_width=1) is None  # runs past reg_width*8
    assert i2c.get_bits(0x50, 1, 0x10, 0, reg_width=0) is None  # reg_width <= 0


def test_set_bits_rejects_out_of_range_bitfield_without_touching_bus() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 0, 0x10, 0, 1, reg_width=1)
    i2c.set_bits(0x50, 4, 0x10, 6, 1, reg_width=1)
    assert len(fake(i2c).log) == 0  # rejected before any readfrom_mem/writeto_mem


def test_get_bits_boundary_full_register_accepted() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 8, 0x10, 0, 0xFF, reg_width=1)
    assert i2c.get_bits(0x50, 8, 0x10, 0, reg_width=1) == 0xFF


# ---------------------------------------------------------------------------
# get_register_struct / set_register_struct - byte order from reg_format alone
# ---------------------------------------------------------------------------


def test_register_struct_round_trip_respects_format_byte_order() -> None:
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, ">H", 0x1234)
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(b"\x12\x34")
    assert i2c.get_register_struct(0x50, 0x20, ">H") == 0x1234


def test_register_struct_round_trip_little_endian() -> None:
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "<H", 0x1234)
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(b"\x34\x12")
    assert i2c.get_register_struct(0x50, 0x20, "<H") == 0x1234


def test_register_struct_malformed_format_returns_none_and_noop() -> None:
    i2c = make_i2c()
    assert i2c.get_register_struct(0x50, 0x20, "Y") is None  # not a real struct format char
    i2c.set_register_struct(0x50, 0x20, "Y", 1)
    assert len(fake(i2c).log) == 0


def test_set_register_struct_value_out_of_range_truncates_silently() -> None:
    # Confirmed directly against the real interpreter: MicroPython's struct.pack silently
    # truncates an out-of-range value (unlike CPython's struct.error) - set_register_struct's
    # try/except only ever catches a malformed reg_format, never an overflow.
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "B", 999)  # doesn't fit in a byte
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(struct.pack("B", 999))


def test_get_register_struct_float_format() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x20)] = bytearray(struct.pack("f", 1.5))
    assert i2c.get_register_struct(0x50, 0x20, "f") == 1.5


# ---------------------------------------------------------------------------
# I2CDevice - address binding, shared locking, probing
# ---------------------------------------------------------------------------


def test_device_shares_the_bus_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    assert device.asy_lock is i2c.async_lock


def test_device_context_manager_acquires_and_releases_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        assert not i2c.async_lock.locked()
        async with device:
            assert i2c.async_lock.locked()
        assert not i2c.async_lock.locked()

    run(scenario())


def test_probe_succeeds_when_device_acks() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.setup())  # must not raise


def test_probe_raises_value_error_when_device_missing() -> None:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x50)
    device = I2CDevice(i2c, 0x50)
    try:
        run(device.setup())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_probe_raises_runtime_error_when_bus_uninitialized() -> None:
    i2c = make_i2c()
    i2c.deinit()
    device = I2CDevice(i2c, 0x50)
    try:
        run(device.setup())
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_device_readinto_and_write_use_device_address() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.write(b"cmd"))
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"cmd", True)
    run(device.readinto(bytearray(2)))
    assert fake(i2c).log[-1][0:2] == ("readfrom_into", 0x50)


def test_device_write_then_readinto_forwards_both() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.write_then_readinto(b"cmd", bytearray(2)))
    ops = [entry[0] for entry in fake(i2c).log]
    assert ops == ["writeto", "readfrom_into"]


def test_device_get_set_bits_round_trip() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.set_bits(3, 0x10, 2, 0x5, reg_width=1))
    assert run(device.get_bits(3, 0x10, 2, reg_width=1)) == 0x5


def test_device_get_set_register_struct_round_trip() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.set_register_struct(0x20, ">H", 0xBEEF))
    assert run(device.get_register_struct(0x20, ">H")) == 0xBEEF


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
